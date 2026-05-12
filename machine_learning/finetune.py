"""Continual-learning fine-tune script (Phase 3.A).

Loads a curated release pack produced by Phase 2 (`curated/<release>/dataset.npz`)
and fine-tunes the previous ResNet101 checkpoint on it. Saves a new `.pth`
plus a training log.

Design choices:

* Only **linear-regression-method** submissions are used as supervised
  targets by default. Their labels come from the trustworthy NNLS fit
  (R² ≈ 0.92 on real data). ML-method submissions are *not* trusted as
  ground truth (the current model is the one that produced those numbers
  — circular). Pass `--include-ml` to override.

* The training input is the same image representation the inference path
  uses (`prepare_image()` in `oas_web.ml`), so the model architecture
  stays untouched.

* Targets are the inverse of `denormalize_prediction()` for the same
  `exp_id`. For `exp_id=4` that's `target = number_density / FACTORS *
  1000 / MAX_VALS`. The fine-tuner clamps to `[0, 1]` after the
  inverse-scale (the same way the live inference path clamps the output
  with `torch.clamp(..., min=0)`).

* A small slice of "frozen baseline" data — synthetic spectra generated
  the same way as the original training set — can be mixed in to fight
  catastrophic forgetting. The baseline generator lives in
  `machine_learning/generate_linux.py`; this script accepts a pre-built
  `.npz` via `--baseline-pool` so the fine-tune step itself is fully
  deterministic and reproducible.

Run end-to-end via the CLI wrapper:

    python scripts/finetune.py --release-id v2

The wrapper figures out paths, calls into this module, and writes the
release artefacts.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from oas_web.ml import (
    FACTORS,
    MAX_VALS,
    SPECIES_ORDER as ML_SPECIES_ORDER,
    SpectrumCNN,
    prepare_image,
)
from oas_web.curation import SPECIES_ORDER as OAS_SPECIES_ORDER


# ────────────────────────────────────────────────────────────────────────────
# Dataset
# ────────────────────────────────────────────────────────────────────────────


_OAS_TO_ML_PERM = np.asarray(
    [OAS_SPECIES_ORDER.index(name) for name in ML_SPECIES_ORDER], dtype=int
)
# (8,) permutation: y_ml[i] = y_oas[_OAS_TO_ML_PERM[i]]
# So `arr_oas[..., _OAS_TO_ML_PERM]` reorders an OAS-order array into ML order.


def number_density_to_target(
    number_density_oas: np.ndarray,
    exp_id: int = 4,
) -> np.ndarray:
    """Inverse of `denormalize_prediction` for exp_id=4: scaled∈[0,~1.something].

    Input is in OAS_SPECIES_ORDER (HONO, HONO2, ...). Output is the raw
    scaled tensor the network's final linear+ReLU is asked to reproduce,
    in ML_SPECIES_ORDER (O3, NO, ...).
    """
    nd_ml = number_density_oas[..., _OAS_TO_ML_PERM]            # reorder
    raw = nd_ml / FACTORS.numpy()                               # invert factors
    if exp_id in (2, 6):
        scaled = raw / MAX_VALS.numpy()
    elif exp_id in (3, 7):
        scaled = raw * 100.0 / MAX_VALS.numpy()
    elif exp_id in (4, 8):
        scaled = raw * 1000.0 / MAX_VALS.numpy()
    elif exp_id in (1, 5):
        scaled = raw / MAX_VALS.numpy()                         # identity-ish
    else:
        scaled = raw
    return np.clip(scaled, 0.0, None)


class CuratedDataset(Dataset):
    """Wraps a curated dataset.npz; yields (image_tensor, target_tensor)."""

    def __init__(
        self,
        npz_path: Path | str,
        *,
        include_ml: bool = False,
        exp_id: int = 4,
        max_samples: int | None = None,
    ):
        data = np.load(npz_path)
        measured = data["measured_od"]            # (N, 191)
        nd = data["number_density"]               # (N, 8) in OAS order
        method = data["method"]                   # (N,) 0=LR, 1=ML

        if not include_ml:
            mask = method == 0
        else:
            mask = np.ones(method.shape, dtype=bool)

        measured = measured[mask]
        nd = nd[mask]

        if max_samples is not None and measured.shape[0] > max_samples:
            measured = measured[:max_samples]
            nd = nd[:max_samples]

        if measured.shape[0] == 0:
            raise ValueError(
                f"No training samples in {npz_path} after filtering "
                f"(include_ml={include_ml}). Phase 2 corpus is too small or "
                f"only contains ML-method submissions."
            )

        # Convert each measured OD into the same image tensor the inference
        # path uses. Stored eagerly because the dataset is tiny in v1.
        images = torch.stack([prepare_image(row).squeeze(0) for row in measured])
        targets = torch.from_numpy(
            number_density_to_target(nd, exp_id=exp_id).astype(np.float32)
        )

        self.images = images                       # (N, 3, 500, 640)
        self.targets = targets                     # (N, 8) ML order
        self.exp_id = exp_id
        self.method = method[mask]

    def __len__(self) -> int:
        return self.images.shape[0]

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.images[idx], self.targets[idx]


def concat_datasets(datasets: Iterable[Dataset]) -> Dataset:
    from torch.utils.data import ConcatDataset
    return ConcatDataset([d for d in datasets if d is not None and len(d) > 0])


# ────────────────────────────────────────────────────────────────────────────
# Training loop
# ────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class FineTuneConfig:
    base_checkpoint: Path
    curated_dataset: Path
    output_checkpoint: Path
    baseline_pool: Path | None = None
    epochs: int = 5
    lr: float = 1.0e-5
    batch_size: int = 4
    include_ml: bool = False
    exp_id: int = 4
    seed: int = 7
    weight_decay: float = 0.0


def fine_tune(config: FineTuneConfig) -> dict:
    """Fine-tune from `base_checkpoint` and write a new `.pth` to
    `output_checkpoint`. Returns a summary dict (per-epoch losses, sample
    counts, paths).
    """
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── Datasets ─────────────────────────────────────────────────
    main_ds = CuratedDataset(
        config.curated_dataset,
        include_ml=config.include_ml,
        exp_id=config.exp_id,
    )
    baseline_ds = None
    if config.baseline_pool is not None and Path(config.baseline_pool).exists():
        baseline_ds = CuratedDataset(
            config.baseline_pool,
            include_ml=True,                # synthetic pool labels are trusted
            exp_id=config.exp_id,
        )

    train_ds = concat_datasets([main_ds, baseline_ds])
    train_loader = DataLoader(
        train_ds,
        batch_size=min(config.batch_size, len(train_ds)),
        shuffle=True,
        drop_last=False,
    )

    # ── Model ────────────────────────────────────────────────────
    model = SpectrumCNN(num_classes=len(ML_SPECIES_ORDER), exp_id=config.exp_id)
    state = torch.load(config.base_checkpoint, map_location="cpu")
    model.load_state_dict(state)
    model.to(device)
    model.train()

    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )
    criterion = nn.MSELoss()

    losses_per_epoch: list[float] = []
    for epoch in range(config.epochs):
        epoch_loss = 0.0
        n_batches = 0
        for image_batch, target_batch in train_loader:
            image_batch = image_batch.to(device)
            target_batch = target_batch.to(device)

            optimizer.zero_grad()
            output = model(image_batch)               # (B, 8) ML order
            loss = criterion(output, target_batch)
            loss.backward()
            optimizer.step()

            epoch_loss += float(loss.detach().cpu().item())
            n_batches += 1
        avg_loss = epoch_loss / max(n_batches, 1)
        losses_per_epoch.append(avg_loss)

    # ── Save ─────────────────────────────────────────────────────
    config.output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), config.output_checkpoint)

    return {
        "base_checkpoint": str(config.base_checkpoint),
        "curated_dataset": str(config.curated_dataset),
        "baseline_pool": str(config.baseline_pool) if config.baseline_pool else None,
        "output_checkpoint": str(config.output_checkpoint),
        "epochs": config.epochs,
        "lr": config.lr,
        "batch_size": min(config.batch_size, len(train_ds)),
        "n_main_samples": len(main_ds),
        "n_baseline_samples": len(baseline_ds) if baseline_ds is not None else 0,
        "exp_id": config.exp_id,
        "include_ml": config.include_ml,
        "device": device,
        "losses_per_epoch": losses_per_epoch,
        "final_loss": losses_per_epoch[-1] if losses_per_epoch else None,
    }


def write_training_log(summary: dict, path: Path) -> None:
    rows = [
        "epoch,loss",
        *[
            f"{epoch + 1},{loss:.6e}"
            for epoch, loss in enumerate(summary.get("losses_per_epoch", []))
        ],
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_summary_json(summary: dict, path: Path) -> None:
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
