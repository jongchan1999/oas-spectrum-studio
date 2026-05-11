from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
import re

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.models as models
from PIL import Image

from oas_web.analysis import (
    CrossSectionData,
    SpectrumData,
    align_cross_sections,
    compute_metrics,
    compute_optical_depth_from_reference,
    load_cross_sections_from_dir,
    load_spectrum,
    prepare_download_frame,
    SPECIES_ORDER as OAS_SPECIES_ORDER,
    WAVE_LOW_DEFAULT,
    WAVE_HIGH_DEFAULT,
)


SPECIES_ORDER = ["O3", "NO", "NO2", "NO3", "HONO", "N2O4", "N2O5", "HONO2"]
MAX_VALS = torch.tensor([543.0, 476.0, 13100.0, 520.0, 535.0, 196.0, 900.0, 1500.0], dtype=torch.float32)
FACTORS = torch.tensor([1e14, 1e14, 1e12, 1e12, 1e12, 1e11, 1e13, 1e13], dtype=torch.float32)


@dataclass
class MLResult:
    species: list[str]
    scaled_outputs: np.ndarray
    number_densities: np.ndarray
    wavelengths: np.ndarray
    measured_absorbance: np.ndarray
    reconstructed: np.ndarray
    per_species_od: np.ndarray
    metrics: dict[str, float]


@dataclass
class TimeSeriesMLResult:
    summary_table: pd.DataFrame
    labels: list[str]
    single_results: list[MLResult]
    reference_file: str
    model_file: str


def _extract_numeric_suffix(name: str) -> float | None:
    stem = Path(name).stem
    match = re.search(r"(\d+(?:\.\d+)?)$", stem)
    if match is None:
        return None
    return float(match.group(1))


class SpectrumCNN(nn.Module):
    def __init__(self, num_classes: int = 8, exp_id: int = 4) -> None:
        super().__init__()
        self.backbone = models.resnet101(weights=None)
        in_features = self.backbone.fc.in_features
        if exp_id in [1, 2, 3, 4]:
            self.backbone.fc = nn.Sequential(nn.Linear(in_features, num_classes), nn.ReLU())
        else:
            self.backbone.fc = nn.Linear(in_features, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)


def _load_bytes(file_or_path: str | Path | BinaryIO | bytes) -> bytes:
    if isinstance(file_or_path, bytes):
        return file_or_path
    if isinstance(file_or_path, (str, Path)):
        return Path(file_or_path).read_bytes()
    if hasattr(file_or_path, "getvalue"):
        return file_or_path.getvalue()
    if hasattr(file_or_path, "read"):
        return file_or_path.read()
    raise TypeError("Unsupported model input type")


def prepare_model_cross_sections(cross_sections: CrossSectionData) -> CrossSectionData:
    available = {name.upper(): index for index, name in enumerate(cross_sections.species)}
    missing = [name for name in SPECIES_ORDER if name.upper() not in available]
    if missing:
        if len(cross_sections.species) == len(SPECIES_ORDER) and all(name.startswith("species_") for name in cross_sections.species):
            ordered_values = cross_sections.values[:, : len(SPECIES_ORDER)]
            return CrossSectionData(
                wavelengths=cross_sections.wavelengths,
                species=SPECIES_ORDER,
                values=ordered_values,
            )
        missing_text = ", ".join(missing)
        raise ValueError(f"ML mode requires cross-section columns for: {missing_text}")

    ordered_indices = [available[name.upper()] for name in SPECIES_ORDER]
    ordered_values = cross_sections.values[:, ordered_indices]
    return CrossSectionData(
        wavelengths=cross_sections.wavelengths,
        species=SPECIES_ORDER,
        values=ordered_values,
    )


def prepare_image(absorbance_values: np.ndarray) -> torch.Tensor:
    masked = np.ma.masked_where((absorbance_values < 1e-4) | (absorbance_values > 1.75), absorbance_values)
    normalized = np.clip(masked, 0, 2) / 2
    normalized = normalized.filled(0.0)
    image_array = np.tile(normalized, (500, 1)) * 255
    image = Image.fromarray(image_array.astype(np.uint8)).convert("RGB").resize((640, 500))
    pixels = np.array(image, copy=True).transpose(2, 0, 1)
    tensor = torch.from_numpy(pixels).float() / 255.0
    return tensor.unsqueeze(0)


def denormalize_prediction(prediction: torch.Tensor, exp_id: int) -> torch.Tensor:
    if exp_id in [1, 5]:
        return prediction
    if exp_id in [2, 6]:
        return prediction * MAX_VALS
    if exp_id in [3, 7]:
        return prediction * MAX_VALS / 100.0
    if exp_id in [4, 8]:
        return prediction * MAX_VALS / 1000.0
    return prediction


def run_ml_inference(
    absorbance: SpectrumData,
    cross_sections: CrossSectionData,
    model_file: str | Path | BinaryIO | bytes,
    exp_id: int,
    path_length_cm: float,
) -> MLResult:
    ordered_cross_sections = prepare_model_cross_sections(cross_sections)
    target_wavelengths = ordered_cross_sections.wavelengths
    target_absorbance = np.interp(
        target_wavelengths,
        absorbance.wavelengths,
        absorbance.values,
        left=0.0,
        right=0.0,
    )

    model = SpectrumCNN(num_classes=len(SPECIES_ORDER), exp_id=exp_id)
    state_dict = torch.load(BytesIO(_load_bytes(model_file)), map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    with torch.no_grad():
        output = model(prepare_image(target_absorbance))[0].cpu()

    scaled_outputs = torch.clamp(denormalize_prediction(output, exp_id), min=0.0)
    number_densities = (scaled_outputs * FACTORS).numpy()

    aligned_basis = align_cross_sections(ordered_cross_sections, target_wavelengths)
    per_species_od = aligned_basis * (number_densities * path_length_cm)[np.newaxis, :]
    reconstructed = per_species_od.sum(axis=1)
    # Reorder outputs to match linear regression / analysis SPECIES_ORDER
    # so that UI tables/columns differ only by model (not by ordering).
    internal_available = {name.upper(): idx for idx, name in enumerate(SPECIES_ORDER)}
    oas_indices = [internal_available[name.upper()] for name in OAS_SPECIES_ORDER]

    scaled_outputs_np = scaled_outputs.numpy()
    scaled_outputs_reordered = scaled_outputs_np[oas_indices]
    number_densities_reordered = number_densities[oas_indices]
    per_species_od_reordered = per_species_od[:, oas_indices]
    reconstructed_reordered = per_species_od_reordered.sum(axis=1)

    metrics = compute_metrics(target_absorbance, reconstructed_reordered)

    return MLResult(
        species=list(OAS_SPECIES_ORDER),
        scaled_outputs=scaled_outputs_reordered,
        number_densities=number_densities_reordered,
        wavelengths=target_wavelengths,
        measured_absorbance=target_absorbance,
        reconstructed=reconstructed_reordered,
        per_species_od=per_species_od_reordered,
        metrics=metrics,
    )


def run_time_series_ml_from_intensity_files(
    files: list[tuple[str, bytes]],
    cross_section_dir: str | Path,
    model_file: str | Path | BinaryIO | bytes,
    exp_id: int,
    path_length_cm: float,
    wave_low: float = WAVE_LOW_DEFAULT,
    wave_high: float = WAVE_HIGH_DEFAULT,
) -> TimeSeriesMLResult:
    """Run ML inference for a time-series of spectra.

    Mirrors `analysis.run_time_series_from_intensity_files` so the UI layer
    stays declarative. The first file (smallest numeric suffix) is I0.
    """
    if len(files) < 2:
        raise ValueError("At least two files are required: one reference (I0) and one measured spectrum.")

    ordered = sorted(
        files,
        key=lambda item: float(_extract_numeric_suffix(item[0]) or float("inf")),
    )
    ref_name, ref_bytes = ordered[0]
    ref_spectrum = load_spectrum(ref_bytes)
    cross_data = load_cross_sections_from_dir(cross_section_dir)

    summary_rows: list[dict[str, float]] = []
    labels: list[str] = []
    single_results: list[MLResult] = []

    for fallback_index, (name, data) in enumerate(ordered[1:], start=1):
        time_value = _extract_numeric_suffix(name)
        if time_value is None:
            time_value = float(fallback_index)

        meas_spectrum = load_spectrum(data)
        optical_depth = compute_optical_depth_from_reference(
            reference_spectrum=ref_spectrum,
            measured_spectrum=meas_spectrum,
            wave_low=wave_low,
            wave_high=wave_high,
        )

        ml_result = run_ml_inference(
            absorbance=optical_depth,
            cross_sections=cross_data,
            model_file=model_file,
            exp_id=exp_id,
            path_length_cm=float(path_length_cm),
        )

        row: dict[str, float] = {"Time (s)": float(time_value)}
        for species, value in zip(ml_result.species, ml_result.number_densities):
            row[species] = float(value)

        summary_rows.append(row)
        labels.append(name)
        single_results.append(ml_result)

    summary_table = (
        pd.DataFrame(summary_rows).sort_values("Time (s)").reset_index(drop=True)
    )

    model_label = (
        getattr(model_file, "name", None)
        or (str(model_file) if isinstance(model_file, (str, Path)) else "<bytes>")
    )

    return TimeSeriesMLResult(
        summary_table=summary_table,
        labels=labels,
        single_results=single_results,
        reference_file=str(ref_name),
        model_file=str(model_label),
    )


def build_continual_learning_frame_ml_timeseries(
    ts_result: TimeSeriesMLResult,
    path_length_cm: float,
) -> pd.DataFrame:
    """Aggregate per-timepoint CL frames into a single dataset for export."""
    frames: list[pd.DataFrame] = []
    for label, ml_result in zip(ts_result.labels, ts_result.single_results):
        frame = build_continual_learning_frame_ml_single(
            ml_result=ml_result,
            wavelengths=ml_result.wavelengths,
            measured_absorbance=ml_result.measured_absorbance,
            path_length_cm=float(path_length_cm),
            reference_file=ts_result.reference_file,
            measured_file=label,
        )
        frame["time_label"] = label
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_continual_learning_frame_ml_single(
    ml_result: MLResult,
    wavelengths: np.ndarray,
    measured_absorbance: np.ndarray,
    path_length_cm: float,
    reference_file: str,
    measured_file: str,
) -> pd.DataFrame:
    # Always use ML inference target wavelength grid for consistent table lengths.
    target_wavelengths = ml_result.wavelengths

    w_src = np.asarray(wavelengths, dtype=float)
    m_src = np.asarray(measured_absorbance, dtype=float)
    mask = np.isfinite(w_src) & np.isfinite(m_src)

    if int(mask.sum()) >= 2:
        w_src = w_src[mask]
        m_src = m_src[mask]
        measured_on_target = np.interp(
            target_wavelengths,
            w_src,
            m_src,
            left=0.0,
            right=0.0,
        )
    else:
        measured_on_target = np.zeros_like(target_wavelengths, dtype=float)

    frame = prepare_download_frame(
        wavelengths=target_wavelengths,
        measured=measured_on_target,
        reconstructed=ml_result.reconstructed,
        species=ml_result.species,
        per_species_od=ml_result.per_species_od,
    )
    frame["path_length_cm"] = float(path_length_cm)
    frame["reference_file"] = str(reference_file)
    frame["measured_file"] = str(measured_file)
    frame["ml_metrics_rmse"] = float(ml_result.metrics.get("rmse", np.nan))
    frame["ml_metrics_r2"] = float(ml_result.metrics.get("r2", np.nan))
    return frame
