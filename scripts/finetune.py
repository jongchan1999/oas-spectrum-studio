#!/usr/bin/env python
"""CLI: fine-tune the ML checkpoint on a curated release pack, then evaluate.

Usage (after Phase 2 has produced `curated/v2/dataset.npz`):

    python scripts/finetune.py --release-id v2

What it does:

1. Loads the previous release's checkpoint from `models/latest.json`
   (or `--base-checkpoint`) and fine-tunes on `curated/<release>/dataset.npz`.
2. Evaluates the fine-tuned candidate vs the baseline on the same dataset.
3. Writes:

       releases/<release>/<release>.pth                 # candidate weights
       releases/<release>/training_log.csv              # epoch losses
       releases/<release>/training_summary.json
       releases/<release>/eval.json
       releases/<release>/report.md

4. If the evaluation gates pass, updates `models/latest.json` to point at
   the new checkpoint (pass `--no-promote` to skip the promotion step).

Required env vars: none. Inputs are all local files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from machine_learning.finetune import (
    FineTuneConfig,
    fine_tune,
    write_summary_json,
    write_training_log,
)
from machine_learning.evaluate import (
    EvalConfig,
    PromotionGates,
    evaluate,
    write_eval_json,
    write_eval_report,
)


DEFAULT_BASE_CHECKPOINT = ROOT / "machine_learning" / "exp_4_epoch_3000.pth"
LATEST_POINTER = ROOT / "models" / "latest.json"


def _resolve_base_checkpoint(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    if LATEST_POINTER.exists():
        info = json.loads(LATEST_POINTER.read_text(encoding="utf-8"))
        path = info.get("path")
        if path and (ROOT / path).exists():
            return (ROOT / path).resolve()
    return DEFAULT_BASE_CHECKPOINT


def _write_latest_pointer(release_id: str, checkpoint_path: Path) -> None:
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "release_id": release_id,
        "path": str(checkpoint_path.relative_to(ROOT)),
    }
    LATEST_POINTER.write_text(json.dumps(info, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release-id", required=True,
                        help="Curated release tag (e.g. v2). Must match a "
                             "folder under curated/.")
    parser.add_argument("--curated-root", default="curated",
                        help="Where Phase 2 wrote the release packs.")
    parser.add_argument("--output-root", default="releases",
                        help="Where to write the fine-tune artefacts.")
    parser.add_argument("--base-checkpoint", default=None,
                        help="Override starting .pth. Default: latest "
                             "promoted release, falling back to "
                             "machine_learning/exp_4_epoch_3000.pth.")
    parser.add_argument("--baseline-pool", default=None,
                        help="Optional .npz of synthetic baseline samples "
                             "to mix in (catastrophic-forgetting guard).")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1.0e-5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--include-ml", action="store_true",
                        help="Also use ML-method submissions as training "
                             "targets (default: only LR-method labels).")
    parser.add_argument("--no-promote", action="store_true",
                        help="Run fine-tune + eval but do NOT update "
                             "models/latest.json even if gates pass.")
    parser.add_argument("--strict", action="store_true",
                        help="Tighter promotion gates: 2%% R² drop allowed,"
                             " 5%% per-species RMSE regression allowed.")
    args = parser.parse_args()

    release_id = args.release_id
    curated_dataset = Path(args.curated_root) / release_id / "dataset.npz"
    if not curated_dataset.exists():
        print(f"[finetune] FAILED: {curated_dataset} not found. Run Phase 2 "
              f"(scripts/curate.py) first.", file=sys.stderr)
        return 1

    release_dir = Path(args.output_root) / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    output_checkpoint = release_dir / f"{release_id}.pth"
    base_checkpoint = _resolve_base_checkpoint(args.base_checkpoint)

    print(f"[finetune] release_id={release_id}")
    print(f"           base_checkpoint   = {base_checkpoint}")
    print(f"           curated_dataset   = {curated_dataset}")
    print(f"           output_checkpoint = {output_checkpoint}")
    print(f"           epochs={args.epochs} lr={args.lr} batch_size={args.batch_size}"
          f" include_ml={args.include_ml}")

    summary = fine_tune(FineTuneConfig(
        base_checkpoint=base_checkpoint,
        curated_dataset=curated_dataset,
        output_checkpoint=output_checkpoint,
        baseline_pool=Path(args.baseline_pool) if args.baseline_pool else None,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        include_ml=args.include_ml,
    ))
    write_training_log(summary, release_dir / "training_log.csv")
    write_summary_json(summary, release_dir / "training_summary.json")
    print(f"[finetune] training done. final_loss={summary['final_loss']}"
          f"  n_main={summary['n_main_samples']}"
          f"  n_baseline={summary['n_baseline_samples']}")

    # Evaluation
    gates = (
        PromotionGates(r2_drop_tolerance=0.02, species_rmse_relax=0.05)
        if args.strict
        else PromotionGates()
    )
    eval_summary = evaluate(EvalConfig(
        eval_dataset=curated_dataset,
        candidate_checkpoint=output_checkpoint,
        baseline_checkpoint=base_checkpoint,
        gates=gates,
    ))
    write_eval_json(eval_summary, release_dir / "eval.json")
    write_eval_report(eval_summary, release_id, release_dir / "report.md")

    print("\n[finetune] evaluation:")
    print(f"           promote = {eval_summary['promote']}")
    if eval_summary["promotion_reasons_blocking"]:
        print("           blocking:")
        for reason in eval_summary["promotion_reasons_blocking"]:
            print(f"             - {reason}")

    if eval_summary["promote"] and not args.no_promote:
        _write_latest_pointer(release_id, output_checkpoint)
        print(f"[finetune] promoted: models/latest.json now points to {output_checkpoint}")
    elif not eval_summary["promote"]:
        print("[finetune] NOT promoted (gates blocked). Inspect report.md.")
    else:
        print("[finetune] promotion skipped (--no-promote).")

    return 0 if eval_summary["promote"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
