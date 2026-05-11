"""Continual-learning submission client.

Builds the JSON payload expected by the Supabase Edge Function defined in
``supabase/functions/submit/index.ts`` and POSTs it. Keeps the request
shape in one place so the app and the server agree on schema_version=1.

Usage:

    payload = build_submission_payload(
        method="machine_learning",
        path_length_cm=15.0,
        user_id="alice",
        reference_file="ref.txt",
        measured_file="it.txt",
        wavelengths=ml_result.wavelengths,
        measured=ml_result.measured_absorbance,
        reconstructed=ml_result.reconstructed,
        species=ml_result.species,
        number_densities=ml_result.number_densities,
        ml_metrics=ml_result.metrics,
    )
    submission_id = submit_to_global_model(payload, endpoint=..., anon_key=...)
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Iterable

import numpy as np


SCHEMA_VERSION = 1
APP_VERSION = "1.0.0"


def build_submission_payload(
    *,
    method: str,                         # "linear_regression" | "machine_learning"
    path_length_cm: float,
    user_id: str,
    reference_file: str,
    measured_file: str,
    wavelengths: np.ndarray,
    measured: np.ndarray,
    reconstructed: np.ndarray,
    species: Iterable[str],
    number_densities: Iterable[float],
    ml_metrics: dict | None = None,
) -> dict:
    """Build the JSON-serialisable payload matching the edge function schema.

    All arrays are converted to plain Python lists with finite-float filtering.
    Non-finite samples are silently dropped to keep the server validator happy.
    """
    if method not in ("linear_regression", "machine_learning"):
        raise ValueError(f"unknown method: {method}")

    w = np.asarray(wavelengths, dtype=float)
    m = np.asarray(measured, dtype=float)
    r = np.asarray(reconstructed, dtype=float)
    if w.shape != m.shape or w.shape != r.shape:
        raise ValueError("wavelengths / measured / reconstructed must share shape")

    mask = np.isfinite(w) & np.isfinite(m) & np.isfinite(r)
    w = w[mask].tolist()
    m = m[mask].tolist()
    r = r[mask].tolist()

    species_list = [str(s) for s in species]
    nd_list = [float(v) if np.isfinite(v) and v >= 0 else 0.0 for v in number_densities]
    if len(species_list) != len(nd_list):
        raise ValueError("species and number_densities length mismatch")

    payload: dict = {
        "schema_version": SCHEMA_VERSION,
        "client": {
            "app_version": APP_VERSION,
            "method": method,
            "path_length_cm": float(path_length_cm),
        },
        "metadata": {
            "reference_file": str(reference_file),
            "measured_file": str(measured_file),
            "user_id": str(user_id),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "consent": True,
        },
        "spectrum": {
            "wavelength_nm": w,
            "measured_absorbance": m,
            "reconstructed_absorbance": r,
        },
        "predictions": {
            "species": species_list,
            "number_density": nd_list,
        },
    }
    if ml_metrics:
        payload["predictions"]["ml_metrics"] = {
            "r2": float(ml_metrics.get("r2")) if ml_metrics.get("r2") is not None else None,
            "rmse": float(ml_metrics.get("rmse")) if ml_metrics.get("rmse") is not None else None,
        }
    return payload


class SubmissionError(RuntimeError):
    """Raised when the submission endpoint returns a non-2xx response."""


def submit_to_global_model(
    payload: dict,
    *,
    endpoint: str,
    anon_key: str,
    timeout_s: float = 30.0,
) -> str:
    """POST a CL payload to the Supabase edge function. Returns submission_id.

    `endpoint` is the full HTTPS URL of the function — typically
        https://<project-ref>.functions.supabase.co/submit
    `anon_key` is the Supabase project's *anon* public key (safe to ship in
    secrets.toml). The edge function uses the service role internally; the
    anon key only authorises the call.
    """
    if not endpoint or not anon_key:
        raise SubmissionError("Submission endpoint and anon key must be configured.")

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {anon_key}",
            "apikey": anon_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SubmissionError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SubmissionError(f"Network error: {exc.reason}") from exc

    try:
        body_json = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise SubmissionError(f"Server returned non-JSON response: {response_body[:200]}") from exc

    if not body_json.get("ok"):
        raise SubmissionError(body_json.get("error", "Submission failed."))

    submission_id = body_json.get("submission_id")
    if not submission_id:
        raise SubmissionError("Server response missing submission_id.")
    return str(submission_id)
