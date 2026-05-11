"""Continual-learning curation worker.

Pulls raw submissions from Supabase, validates them, deduplicates against
previously accepted samples, normalises onto a canonical 1-nm wavelength
grid, and packs the accepted samples into a single .npz dataset for the
next training release.

Designed for two execution modes:

* **Manual** — run `python scripts/curate.py` on your machine after
  setting SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars. Good for
  the first few releases while you read each report.
* **Scheduled** — the GitHub Action in `.github/workflows/curate.yml`
  runs this with `workflow_dispatch` (manual trigger) by default; flip
  the `schedule:` block on once the release cadence is stable.

Storage layout produced:

    curated/<release_id>/
        dataset.npz           # the training pack (see materialise())
        manifest.csv          # one row per processed submission
        report.md             # human-readable summary
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


# ────────────────────────────────────────────────────────────────────────────
# Canonical schema
# ────────────────────────────────────────────────────────────────────────────

CANONICAL_WAVELENGTHS_NM: np.ndarray = np.arange(210.0, 401.0, 1.0)
SPECIES_ORDER: list[str] = ["HONO", "HONO2", "N2O4", "N2O5", "NO", "NO2", "NO3", "O3"]
STORAGE_BUCKET = "cl-raw"
METHOD_CODE = {"linear_regression": 0, "machine_learning": 1}


class CurationError(RuntimeError):
    """Raised on configuration / network errors that abort the run."""


# ────────────────────────────────────────────────────────────────────────────
# Supabase admin client (urllib-based; no extra deps)
# ────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class SupabaseAdmin:
    url: str          # e.g. https://abc.supabase.co
    service_key: str  # service_role JWT

    @classmethod
    def from_env(cls) -> "SupabaseAdmin":
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise CurationError(
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running curation."
            )
        return cls(url=url, service_key=key)

    # ── low-level ─────────────────────────────────────────────────
    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        if extra:
            h.update(extra)
        return h

    def _request(self, method: str, path: str, *, body: bytes | None = None,
                 headers: dict | None = None, timeout: float = 60.0) -> tuple[int, bytes]:
        request = urllib.request.Request(
            self.url + path,
            data=body,
            method=method,
            headers=self._headers(headers),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    # ── PostgREST ─────────────────────────────────────────────────
    def list_raw_submissions(self) -> list[dict]:
        path = "/rest/v1/cl_submissions?status=eq.raw&select=*&order=submitted_at.asc"
        status, body = self._request("GET", path,
                                     headers={"Accept": "application/json"})
        if status >= 400:
            raise CurationError(f"list_raw_submissions: HTTP {status}: {body!r}")
        return json.loads(body.decode("utf-8"))

    def list_accepted_signatures(self) -> set[str]:
        """Return the set of dedupe signatures already accepted in prior runs."""
        path = ("/rest/v1/cl_submissions?status=in.(accepted,training)"
                "&select=reference_hash,measured_hash")
        status, body = self._request("GET", path,
                                     headers={"Accept": "application/json"})
        if status >= 400:
            raise CurationError(f"list_accepted: HTTP {status}: {body!r}")
        rows = json.loads(body.decode("utf-8"))
        return {f"{r['reference_hash']}|{r['measured_hash']}" for r in rows}

    def update_submission(self, sub_id: str, fields: dict) -> None:
        path = f"/rest/v1/cl_submissions?id=eq.{sub_id}"
        body = json.dumps(fields).encode("utf-8")
        status, resp = self._request(
            "PATCH", path,
            body=body,
            headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
        )
        if status >= 400:
            raise CurationError(f"update_submission({sub_id}): HTTP {status}: {resp!r}")

    # ── Storage ───────────────────────────────────────────────────
    def fetch_blob(self, storage_key: str) -> dict:
        path = f"/storage/v1/object/{STORAGE_BUCKET}/{urllib.parse.quote(storage_key)}"
        status, body = self._request("GET", path,
                                     headers={"Accept": "application/json"})
        if status >= 400:
            raise CurationError(f"fetch_blob({storage_key}): HTTP {status}: {body!r}")
        return json.loads(body.decode("utf-8"))


# ────────────────────────────────────────────────────────────────────────────
# Validation
# ────────────────────────────────────────────────────────────────────────────


def validate_payload(payload: dict) -> str | None:
    """Return None if the payload is acceptable, else a short rejection reason."""
    try:
        if payload.get("schema_version") != 1:
            return "schema_version != 1"
        spec = payload["spectrum"]
        w = np.asarray(spec["wavelength_nm"], dtype=float)
        m = np.asarray(spec["measured_absorbance"], dtype=float)
        r = np.asarray(spec["reconstructed_absorbance"], dtype=float)
        if w.size < 20:
            return f"too few points ({w.size})"
        if not (w.shape == m.shape == r.shape):
            return "spectrum arrays have mismatched shape"
        if not np.all(np.isfinite(w)) or not np.all(np.isfinite(m)) or not np.all(np.isfinite(r)):
            return "NaN or Inf in spectrum"
        if not np.all(np.diff(w) > 0):
            return "wavelength axis not strictly increasing"
        if w.min() > 250 or w.max() < 280:
            return f"wavelength range too narrow ({w.min():.1f}-{w.max():.1f} nm)"
        if np.max(np.abs(m)) > 50:
            return "measured OD magnitude implausible (>50)"

        species = payload["predictions"]["species"]
        nd = np.asarray(payload["predictions"]["number_density"], dtype=float)
        if list(species) != SPECIES_ORDER:
            return f"species list != canonical order: {species}"
        if nd.shape != (len(SPECIES_ORDER),) or not np.all(np.isfinite(nd)):
            return "number_density invalid shape/finiteness"
        if np.any(nd < 0):
            return "number_density has negative values"
        # Sanity: all-zero density usually means the ML simply punted on this frame.
        # We still accept it (the corpus needs hard negatives too), but flag it.
        return None
    except (KeyError, TypeError, ValueError) as exc:
        return f"malformed payload: {exc.__class__.__name__}"


# ────────────────────────────────────────────────────────────────────────────
# Normalisation onto the canonical grid
# ────────────────────────────────────────────────────────────────────────────


def normalise_spectrum(payload: dict) -> tuple[np.ndarray, np.ndarray]:
    """Interp measured + reconstructed OD onto CANONICAL_WAVELENGTHS_NM.

    Points outside the original range are filled with 0 — this matches the
    convention used by analysis.align_cross_sections().
    """
    spec = payload["spectrum"]
    w = np.asarray(spec["wavelength_nm"], dtype=float)
    m = np.asarray(spec["measured_absorbance"], dtype=float)
    r = np.asarray(spec["reconstructed_absorbance"], dtype=float)
    measured_canon = np.interp(CANONICAL_WAVELENGTHS_NM, w, m, left=0.0, right=0.0)
    recon_canon = np.interp(CANONICAL_WAVELENGTHS_NM, w, r, left=0.0, right=0.0)
    return measured_canon, recon_canon


def signature(reference_hash: str, measured_hash: str) -> str:
    return f"{reference_hash}|{measured_hash}"


def content_signature(measured_canon: np.ndarray) -> str:
    """Catch the case where two submissions have different hashed filenames
    but the underlying measured spectrum is identical (e.g. user re-uploaded)."""
    digest = hashlib.sha256()
    digest.update(np.round(measured_canon, 6).tobytes())
    return digest.hexdigest()


# ────────────────────────────────────────────────────────────────────────────
# Materialisation
# ────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class AcceptedSample:
    submission_id: str
    method_code: int
    path_length_cm: float
    measured_canon: np.ndarray
    reconstructed_canon: np.ndarray
    number_density: np.ndarray
    ml_r2: float | None
    ml_rmse: float | None


def materialise_dataset(samples: Sequence[AcceptedSample], release_dir: Path) -> Path:
    release_dir.mkdir(parents=True, exist_ok=True)
    out = release_dir / "dataset.npz"
    if not samples:
        np.savez(out, wavelengths_nm=CANONICAL_WAVELENGTHS_NM,
                 species=np.asarray(SPECIES_ORDER),
                 submission_ids=np.empty(0, dtype="<U36"),
                 measured_od=np.empty((0, CANONICAL_WAVELENGTHS_NM.size)),
                 reconstructed_od=np.empty((0, CANONICAL_WAVELENGTHS_NM.size)),
                 number_density=np.empty((0, len(SPECIES_ORDER))),
                 method=np.empty(0, dtype=np.int8),
                 path_length_cm=np.empty(0, dtype=float),
                 ml_r2=np.empty(0, dtype=float),
                 ml_rmse=np.empty(0, dtype=float))
        return out

    np.savez(
        out,
        wavelengths_nm=CANONICAL_WAVELENGTHS_NM,
        species=np.asarray(SPECIES_ORDER),
        submission_ids=np.asarray([s.submission_id for s in samples], dtype="<U36"),
        measured_od=np.stack([s.measured_canon for s in samples]),
        reconstructed_od=np.stack([s.reconstructed_canon for s in samples]),
        number_density=np.stack([s.number_density for s in samples]),
        method=np.asarray([s.method_code for s in samples], dtype=np.int8),
        path_length_cm=np.asarray([s.path_length_cm for s in samples], dtype=float),
        ml_r2=np.asarray([np.nan if s.ml_r2 is None else s.ml_r2 for s in samples]),
        ml_rmse=np.asarray([np.nan if s.ml_rmse is None else s.ml_rmse for s in samples]),
    )
    return out


def write_manifest(rows: Sequence[dict], release_dir: Path) -> Path:
    out = release_dir / "manifest.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def write_report(stats: dict, release_dir: Path) -> Path:
    out = release_dir / "report.md"
    lines = [
        f"# Curation release `{stats['release_id']}`",
        "",
        f"- **Generated:** {stats['generated_at']}",
        f"- **Source submissions scanned:** {stats['scanned']}",
        f"- **Accepted:** {stats['accepted']}",
        f"- **Rejected:** {stats['rejected']}",
        f"- **Duplicates skipped:** {stats['duplicates']}",
        "",
        "## Method breakdown (accepted)",
        "",
    ]
    if stats["method_counts"]:
        for method, count in stats["method_counts"].items():
            lines.append(f"- {method}: {count}")
    else:
        lines.append("- (no accepted samples)")

    if stats["rejection_reasons"]:
        lines.append("")
        lines.append("## Rejection reasons")
        lines.append("")
        for reason, count in stats["rejection_reasons"].items():
            lines.append(f"- `{reason}` — {count}")

    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ────────────────────────────────────────────────────────────────────────────


def run_curation(
    *,
    release_id: str,
    output_root: Path = Path("curated"),
    dry_run: bool = False,
    client: SupabaseAdmin | None = None,
) -> dict:
    """Pull every raw submission, validate / dedupe / normalise / materialise.

    If `dry_run` is True, no PATCH calls are made — useful for trial runs.
    """
    client = client or SupabaseAdmin.from_env()
    raw_rows = client.list_raw_submissions()
    prior_sigs = client.list_accepted_signatures()
    seen_content: set[str] = set()

    accepted: list[AcceptedSample] = []
    manifest_rows: list[dict] = []
    rejection_counts: dict[str, int] = {}
    method_counts: dict[str, int] = {}
    duplicates = 0
    scanned = len(raw_rows)

    for row in raw_rows:
        sub_id = row["id"]
        sig_pair = signature(row.get("reference_hash", ""), row.get("measured_hash", ""))

        record = {
            "submission_id": sub_id,
            "submitted_at": row.get("submitted_at"),
            "method": row.get("method"),
            "status_before": "raw",
            "status_after": None,
            "reason": None,
        }

        try:
            payload = client.fetch_blob(row["storage_key"])
        except CurationError as exc:
            record.update({"status_after": "rejected", "reason": f"fetch: {exc}"})
            rejection_counts[record["reason"]] = rejection_counts.get(record["reason"], 0) + 1
            if not dry_run:
                client.update_submission(sub_id, {
                    "status": "rejected", "rejection_reason": record["reason"],
                })
            manifest_rows.append(record)
            continue

        reason = validate_payload(payload)
        if reason is not None:
            record.update({"status_after": "rejected", "reason": reason})
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            if not dry_run:
                client.update_submission(sub_id, {
                    "status": "rejected", "rejection_reason": reason,
                })
            manifest_rows.append(record)
            continue

        # Dedupe — both against past releases and within this run.
        if sig_pair in prior_sigs:
            duplicates += 1
            record.update({"status_after": "rejected", "reason": "duplicate (prior release)"})
            if not dry_run:
                client.update_submission(sub_id, {
                    "status": "rejected", "rejection_reason": "duplicate (prior release)",
                })
            manifest_rows.append(record)
            continue

        measured_canon, recon_canon = normalise_spectrum(payload)
        content_sig = content_signature(measured_canon)
        if content_sig in seen_content:
            duplicates += 1
            record.update({"status_after": "rejected", "reason": "duplicate (this run)"})
            if not dry_run:
                client.update_submission(sub_id, {
                    "status": "rejected", "rejection_reason": "duplicate (this run)",
                })
            manifest_rows.append(record)
            continue
        seen_content.add(content_sig)

        ml_metrics = payload.get("predictions", {}).get("ml_metrics") or {}
        sample = AcceptedSample(
            submission_id=sub_id,
            method_code=METHOD_CODE.get(row.get("method", ""), -1),
            path_length_cm=float(row.get("path_length_cm", 0.0)),
            measured_canon=measured_canon,
            reconstructed_canon=recon_canon,
            number_density=np.asarray(
                payload["predictions"]["number_density"], dtype=float
            ),
            ml_r2=ml_metrics.get("r2"),
            ml_rmse=ml_metrics.get("rmse"),
        )
        accepted.append(sample)
        method_counts[row.get("method", "?")] = method_counts.get(row.get("method", "?"), 0) + 1

        record.update({"status_after": "accepted", "reason": None})
        if not dry_run:
            client.update_submission(sub_id, {
                "status": "accepted",
                "release_id": release_id,
                "accepted_at": datetime.now(timezone.utc).isoformat(),
            })
        manifest_rows.append(record)

    # Materialise outputs
    release_dir = output_root / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = materialise_dataset(accepted, release_dir)
    manifest_path = write_manifest(manifest_rows, release_dir)

    stats = {
        "release_id": release_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanned": scanned,
        "accepted": len(accepted),
        "rejected": sum(rejection_counts.values()),
        "duplicates": duplicates,
        "method_counts": method_counts,
        "rejection_reasons": rejection_counts,
        "dataset_path": str(dataset_path),
        "manifest_path": str(manifest_path),
        "dry_run": dry_run,
    }
    stats["report_path"] = str(write_report(stats, release_dir))
    return stats
