#!/usr/bin/env python
"""Batch-submit N analyses to the global model — corpus seeding helper.

Phase 3 needs a non-trivial corpus to demonstrate that fine-tuning helps.
Building that corpus by clicking through the Streamlit UI 20+ times is
tedious; this script does the same thing — load reference + measured
spectra, run linear regression locally, and POST the result through the
Supabase edge function — but unattended.

Each successful POST adds one `raw` row to `public.cl_submissions`,
exactly like a real user submission. The curator (`scripts/curate.py`)
processes them the same way later.

Usage:

    python scripts/seed_submissions.py \\
        --data-dir "C:/Users/kimjo/spectroscopy/OAS tool/260429/.../Source_70_2" \\
        --reference Source_70_2_00000.txt \\
        --n 20 \\
        --user-id seeder

Endpoint + anon-key are read in this order:
  1. CLI flags --endpoint and --anon-key (most explicit)
  2. env vars  CL_ENDPOINT, CL_ANON_KEY
  3. .streamlit/secrets.toml  ([cl] table)

The default fitting method is `linear_regression` (its labels are
trustworthy and what the fine-tuner uses). Pass `--method machine_learning`
to seed ML submissions instead.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import time
from pathlib import Path

import numpy as np


def _parse_minimal_toml_cl_section(text: str) -> dict:
    """Extract the [cl] table's `endpoint` and `anon_key` from a small
    secrets.toml without needing tomllib (Py 3.11+) or tomli.

    The Streamlit secrets format is conventional enough that a regex pass
    is good enough for our flat string keys; if the user has anything
    fancier (multiline strings, etc.) they should set the env vars
    instead.
    """
    cl_match = re.search(r"^\s*\[cl\]\s*$", text, flags=re.MULTILINE)
    if not cl_match:
        return {}
    tail = text[cl_match.end():]
    next_section = re.search(r"^\s*\[[^\]]+\]\s*$", tail, flags=re.MULTILINE)
    block = tail[: next_section.start()] if next_section else tail
    out: dict[str, str] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r'([A-Za-z_][\w-]*)\s*=\s*"(.*?)"\s*(#.*)?$', stripped)
        if m:
            out[m.group(1)] = m.group(2)
    return out

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from oas_web.analysis import (
    FitConfig,
    compute_optical_depth_from_reference,
    discover_preferred_cross_section_dir,
    load_cross_sections_from_dir,
    load_spectrum,
    run_linear_regression,
    SpectrumData,
)
from oas_web.ml import (
    SPECIES_ORDER as ML_SPECIES_ORDER,
    run_ml_inference,
)
from oas_web.cl_submit import (
    SubmissionError,
    build_submission_payload,
    submit_to_global_model,
)


def _read_endpoint_from_secrets(repo_root: Path) -> tuple[str, str]:
    secrets_path = repo_root / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return ("", "")
    try:
        text = secrets_path.read_text(encoding="utf-8")
    except Exception:
        return ("", "")
    cl = _parse_minimal_toml_cl_section(text)
    return (cl.get("endpoint", "").strip(), cl.get("anon_key", "").strip())


def _resolve_endpoint(args: argparse.Namespace) -> tuple[str, str]:
    if args.endpoint and args.anon_key:
        return args.endpoint, args.anon_key
    import os
    env_endpoint = os.environ.get("CL_ENDPOINT", "").strip()
    env_key = os.environ.get("CL_ANON_KEY", "").strip()
    if env_endpoint and env_key:
        return env_endpoint, env_key
    sec_endpoint, sec_key = _read_endpoint_from_secrets(ROOT)
    if sec_endpoint and sec_key:
        return sec_endpoint, sec_key
    return ("", "")


def _pick_frames(
    data_dir: Path,
    reference_name: str,
    n: int,
    seed: int,
) -> tuple[Path, list[Path]]:
    all_files = sorted(p for p in data_dir.glob("*.txt"))
    if not all_files:
        raise SystemExit(f"[seed] no .txt files found under {data_dir}")
    reference = data_dir / reference_name
    if not reference.exists():
        raise SystemExit(f"[seed] reference file not found: {reference}")

    measured = [p for p in all_files if p.name != reference_name]
    if len(measured) == 0:
        raise SystemExit("[seed] no measured frames besides the reference")

    rng = random.Random(seed)
    if n >= len(measured):
        picks = measured
    else:
        picks = rng.sample(measured, k=n)
    picks.sort()
    return reference, picks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", required=True,
                        help="Folder containing the spectra .txt files.")
    parser.add_argument("--reference", required=True,
                        help="Filename inside --data-dir that is I0.")
    parser.add_argument("--n", type=int, default=20,
                        help="How many measured frames to submit. "
                             "Sampled without replacement.")
    parser.add_argument("--user-id", default="seeder",
                        help="Username embedded in the payload (hashed on "
                             "the server).")
    parser.add_argument("--method",
                        choices=["linear_regression", "machine_learning"],
                        default="linear_regression",
                        help="Which analyser to run locally and submit. "
                             "Defaults to linear_regression because its "
                             "labels are trustworthy for fine-tuning.")
    parser.add_argument("--path-length-cm", type=float, default=15.0)
    parser.add_argument("--wave-low", type=float, default=210.0)
    parser.add_argument("--wave-high", type=float, default=400.0)
    parser.add_argument("--cross-section-root", default=str(ROOT / "260429"),
                        help="Where to look for the 8 species cross-section "
                             "files (default: repo's 260429 folder).")
    parser.add_argument("--model-file", default=str(ROOT / "machine_learning" / "exp_4_epoch_3000.pth"),
                        help="ML checkpoint, only used when --method "
                             "machine_learning.")
    parser.add_argument("--endpoint", default="",
                        help="Override the submission endpoint URL.")
    parser.add_argument("--anon-key", default="",
                        help="Override the anon-public key.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true",
                        help="Run the analyses but do NOT POST. "
                             "Useful to verify the pipeline.")
    parser.add_argument("--sleep", type=float, default=0.3,
                        help="Seconds to wait between submissions (be a "
                             "good citizen to the edge function).")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"[seed] data dir does not exist: {data_dir}")

    cross_dir = discover_preferred_cross_section_dir(args.cross_section_root)
    if cross_dir is None:
        raise SystemExit(
            f"[seed] cross-section dir not found under {args.cross_section_root}"
        )

    endpoint, anon_key = _resolve_endpoint(args)
    if not args.dry_run and (not endpoint or not anon_key):
        raise SystemExit(
            "[seed] no CL endpoint configured. Set --endpoint and "
            "--anon-key, or CL_ENDPOINT/CL_ANON_KEY env vars, or fill "
            "the [cl] section of .streamlit/secrets.toml."
        )

    ref_path, picks = _pick_frames(
        data_dir=data_dir,
        reference_name=args.reference,
        n=args.n,
        seed=args.seed,
    )
    print(f"[seed] data_dir       = {data_dir}")
    print(f"[seed] reference      = {ref_path.name}")
    print(f"[seed] frames picked  = {len(picks)}")
    print(f"[seed] method         = {args.method}")
    print(f"[seed] endpoint       = {endpoint or '(dry-run)'}")
    print(f"[seed] user_id        = {args.user_id}")

    ref_spectrum = load_spectrum(ref_path.read_bytes())
    cross_data = load_cross_sections_from_dir(str(cross_dir))

    submitted = 0
    failed = 0
    for index, frame_path in enumerate(picks, start=1):
        meas_spectrum = load_spectrum(frame_path.read_bytes())
        optical_depth = compute_optical_depth_from_reference(
            reference_spectrum=ref_spectrum,
            measured_spectrum=meas_spectrum,
            wave_low=args.wave_low,
            wave_high=args.wave_high,
        )

        if args.method == "linear_regression":
            within = (optical_depth.wavelengths >= cross_data.wavelengths.min()) & \
                     (optical_depth.wavelengths <= cross_data.wavelengths.max())
            od_aligned = SpectrumData(
                wavelengths=optical_depth.wavelengths[within],
                values=optical_depth.values[within],
            )
            regression = run_linear_regression(
                absorbance=od_aligned,
                cross_sections=cross_data,
                path_length_cm=args.path_length_cm,
                config=FitConfig(),
            )
            species = regression.species
            number_densities = regression.number_densities
            wavelengths = od_aligned.wavelengths
            measured = od_aligned.values
            reconstructed = regression.reconstructed
            ml_metrics = None
        else:
            ml_result = run_ml_inference(
                absorbance=optical_depth,
                cross_sections=cross_data,
                model_file=args.model_file,
                exp_id=4,
                path_length_cm=args.path_length_cm,
            )
            species = ml_result.species
            number_densities = ml_result.number_densities
            wavelengths = ml_result.wavelengths
            measured = ml_result.measured_absorbance
            reconstructed = ml_result.reconstructed
            ml_metrics = ml_result.metrics

        payload = build_submission_payload(
            method=args.method,
            path_length_cm=args.path_length_cm,
            user_id=args.user_id,
            reference_file=ref_path.name,
            measured_file=frame_path.name,
            wavelengths=wavelengths,
            measured=measured,
            reconstructed=reconstructed,
            species=species,
            number_densities=number_densities,
            ml_metrics=ml_metrics,
        )

        if args.dry_run:
            print(f"  [{index:>3}/{len(picks)}] DRY  {frame_path.name}: "
                  f"shape={len(payload['spectrum']['wavelength_nm'])} pts, "
                  f"top={species[int(np.argmax(number_densities))]}")
            submitted += 1
            continue

        try:
            sub_id = submit_to_global_model(payload, endpoint=endpoint, anon_key=anon_key)
            submitted += 1
            print(f"  [{index:>3}/{len(picks)}] OK   {frame_path.name} → {sub_id}")
        except SubmissionError as exc:
            failed += 1
            print(f"  [{index:>3}/{len(picks)}] FAIL {frame_path.name}: {exc}")

        time.sleep(max(0.0, args.sleep))

    print(f"\n[seed] done. submitted={submitted} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
