"""Continual-learning evaluation harness (Phase 3.B).

Given two checkpoints (the previous release and a fine-tuned candidate)
plus a held-out dataset (a curated `dataset.npz`), this module:

1. Runs both checkpoints over every sample.
2. Computes per-species RMSE, R², and bias (signed mean of predicted -
   target).
3. Aggregates the overall reconstruction-OD R² (so we can compare to the
   linear-regression baseline used as pseudo-ground-truth).
4. Decides whether to **promote** the candidate to the next release based
   on simple gates:
   - overall R² on the eval set must not regress by more than `r2_tol`
     (default 0.02);
   - no species RMSE may regress by more than `species_rmse_tol`
     (default 20 %).
5. Writes a human-readable `report.md` and a machine-readable
   `eval.json`.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from oas_web.ml import (
    FACTORS,
    MAX_VALS,
    SPECIES_ORDER as ML_SPECIES_ORDER,
    SpectrumCNN,
    prepare_image,
    denormalize_prediction,
)
from oas_web.curation import SPECIES_ORDER as OAS_SPECIES_ORDER


# Mirror of finetune._OAS_TO_ML_PERM but in the inverse direction so we
# can put predictions back into OAS order for human-friendly reporting.
_ML_TO_OAS_PERM = np.asarray(
    [ML_SPECIES_ORDER.index(name) for name in OAS_SPECIES_ORDER], dtype=int
)
# (8,) — predictions_ml_order[..., _ML_TO_OAS_PERM] gives OAS-order arrays.


def _predict_one(model: SpectrumCNN, measured_row: np.ndarray, exp_id: int,
                 device: str) -> np.ndarray:
    """Forward pass on a single (191,) OD curve. Returns (8,) ND in OAS order."""
    image = prepare_image(measured_row).to(device)
    with torch.no_grad():
        raw = model(image)[0].cpu()
    scaled = torch.clamp(denormalize_prediction(raw, exp_id), min=0.0)
    number_density_ml = (scaled * FACTORS).numpy()                # (8,) ML order
    return number_density_ml[_ML_TO_OAS_PERM]                     # → OAS order


def _predict_many(checkpoint: Path, measured: np.ndarray, exp_id: int = 4
                  ) -> np.ndarray:
    """Predict number densities for every row. Returns (N, 8) OAS-order."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SpectrumCNN(num_classes=len(ML_SPECIES_ORDER), exp_id=exp_id)
    state = torch.load(checkpoint, map_location=device)
    model.load_state_dict(state)
    model.to(device).eval()
    preds = np.zeros((measured.shape[0], len(OAS_SPECIES_ORDER)), dtype=float)
    for index, row in enumerate(measured):
        preds[index] = _predict_one(model, row, exp_id=exp_id, device=device)
    return preds


def _per_species_metrics(pred: np.ndarray, target: np.ndarray) -> list[dict]:
    """One dict per species, in OAS_SPECIES_ORDER."""
    eps = 1e-12
    out: list[dict] = []
    for i, name in enumerate(OAS_SPECIES_ORDER):
        p = pred[:, i]
        t = target[:, i]
        rmse = float(np.sqrt(np.mean((p - t) ** 2)))
        mae = float(np.mean(np.abs(p - t)))
        bias = float(np.mean(p - t))
        var = float(np.var(t)) if np.var(t) > eps else float("nan")
        r2 = float("nan") if np.isnan(var) else 1.0 - float(np.var(p - t)) / var
        out.append(
            {"species": name, "rmse": rmse, "mae": mae, "bias": bias, "r2": r2}
        )
    return out


def _overall_metrics(pred: np.ndarray, target: np.ndarray) -> dict:
    rmse_per_sample = np.sqrt(np.mean((pred - target) ** 2, axis=1))
    return {
        "rmse_mean": float(np.mean(rmse_per_sample)),
        "rmse_median": float(np.median(rmse_per_sample)),
        "mae_mean": float(np.mean(np.abs(pred - target))),
    }


# ────────────────────────────────────────────────────────────────────────────
# Promotion gates
# ────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class PromotionGates:
    """Cap regression vs the previous release. Pass `--strict` for tighter
    thresholds in production; defaults work for v1 with very small N."""
    r2_drop_tolerance: float = 0.05         # overall R² may drop by ≤ 5 pp
    species_rmse_relax: float = 0.20         # per-species RMSE may worsen ≤ 20 %


def _evaluate_gates(
    candidate_overall: dict,
    baseline_overall: dict,
    candidate_species: list[dict],
    baseline_species: list[dict],
    gates: PromotionGates,
) -> tuple[bool, list[str]]:
    """Return (promote, reasons_list). reasons_list is empty when promoted."""
    reasons: list[str] = []

    cand_rmse = candidate_overall["rmse_mean"]
    base_rmse = baseline_overall["rmse_mean"]
    if base_rmse > 0 and cand_rmse > base_rmse * (1 + gates.r2_drop_tolerance):
        reasons.append(
            f"overall RMSE regressed: {base_rmse:.3e} -> {cand_rmse:.3e} "
            f"(> {gates.r2_drop_tolerance:.0%} worse)"
        )

    for cand, base in zip(candidate_species, baseline_species):
        sp = cand["species"]
        if base["rmse"] <= 0:
            continue
        if cand["rmse"] > base["rmse"] * (1 + gates.species_rmse_relax):
            reasons.append(
                f"{sp}: RMSE regressed {base['rmse']:.3e} -> {cand['rmse']:.3e} "
                f"(> {gates.species_rmse_relax:.0%} worse)"
            )

    return (len(reasons) == 0, reasons)


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class EvalConfig:
    eval_dataset: Path              # curated/<release>/dataset.npz used as held-out
    candidate_checkpoint: Path      # new fine-tuned .pth
    baseline_checkpoint: Path       # the previously promoted .pth
    exp_id: int = 4
    gates: PromotionGates = dataclasses.field(default_factory=PromotionGates)
    only_lr_truth: bool = True      # use only LR-method rows as ground truth


def evaluate(config: EvalConfig) -> dict:
    data = np.load(config.eval_dataset)
    measured = data["measured_od"]                  # (N, 191)
    nd = data["number_density"]                     # (N, 8) OAS order
    method = data["method"]                         # (N,) 0=LR 1=ML

    if config.only_lr_truth:
        mask = method == 0
        measured = measured[mask]
        nd = nd[mask]
    if measured.shape[0] == 0:
        raise ValueError(
            "Eval dataset has no LR-method rows to use as ground truth. "
            "Pass --include-ml-truth (careful: ML labels are noisy)."
        )

    cand_preds = _predict_many(config.candidate_checkpoint, measured, config.exp_id)
    base_preds = _predict_many(config.baseline_checkpoint, measured, config.exp_id)

    cand_overall = _overall_metrics(cand_preds, nd)
    base_overall = _overall_metrics(base_preds, nd)
    cand_species = _per_species_metrics(cand_preds, nd)
    base_species = _per_species_metrics(base_preds, nd)

    promote, reasons = _evaluate_gates(
        candidate_overall=cand_overall,
        baseline_overall=base_overall,
        candidate_species=cand_species,
        baseline_species=base_species,
        gates=config.gates,
    )

    return {
        "eval_dataset": str(config.eval_dataset),
        "candidate_checkpoint": str(config.candidate_checkpoint),
        "baseline_checkpoint": str(config.baseline_checkpoint),
        "exp_id": config.exp_id,
        "n_samples": int(measured.shape[0]),
        "candidate_overall": cand_overall,
        "baseline_overall": base_overall,
        "candidate_per_species": cand_species,
        "baseline_per_species": base_species,
        "gates": dataclasses.asdict(config.gates),
        "promote": promote,
        "promotion_reasons_blocking": reasons,
    }


def write_eval_report(eval_summary: dict, release_id: str, path: Path) -> None:
    lines = [
        f"# Release `{release_id}` — evaluation report",
        "",
        f"- **Candidate**: `{eval_summary['candidate_checkpoint']}`",
        f"- **Baseline**:  `{eval_summary['baseline_checkpoint']}`",
        f"- **Eval set**:  `{eval_summary['eval_dataset']}` ({eval_summary['n_samples']} samples)",
        f"- **Promote**:   {'✅ yes' if eval_summary['promote'] else '⛔ no'}",
        "",
    ]
    if eval_summary["promotion_reasons_blocking"]:
        lines.append("## Blocking reasons")
        lines.append("")
        for reason in eval_summary["promotion_reasons_blocking"]:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append("| metric        | baseline      | candidate     | Δ |")
    lines.append("|---------------|--------------:|--------------:|---:|")
    for key in ("rmse_mean", "rmse_median", "mae_mean"):
        base = eval_summary["baseline_overall"][key]
        cand = eval_summary["candidate_overall"][key]
        delta = cand - base
        lines.append(
            f"| {key:13s} | {base:>13.3e} | {cand:>13.3e} | {delta:+.3e} |"
        )
    lines.append("")
    lines.append("## Per species")
    lines.append("")
    lines.append("| species | baseline RMSE | candidate RMSE | Δ% | candidate bias |")
    lines.append("|---------|--------------:|---------------:|---:|---------------:|")
    for cand, base in zip(
        eval_summary["candidate_per_species"], eval_summary["baseline_per_species"]
    ):
        sp = cand["species"]
        pct = (
            (cand["rmse"] - base["rmse"]) / base["rmse"] * 100.0
            if base["rmse"] > 0
            else float("nan")
        )
        lines.append(
            f"| {sp:7s} | {base['rmse']:>13.3e} | {cand['rmse']:>14.3e} | "
            f"{pct:+5.1f}% | {cand['bias']:>14.3e} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_eval_json(eval_summary: dict, path: Path) -> None:
    path.write_text(json.dumps(eval_summary, indent=2), encoding="utf-8")
