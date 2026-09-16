from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import BinaryIO
import re

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass
class SpectrumData:
    wavelengths: np.ndarray
    values: np.ndarray


@dataclass
class CrossSectionData:
    wavelengths: np.ndarray
    species: list[str]
    values: np.ndarray


@dataclass
class RegressionResult:
    species: list[str]
    coefficients: np.ndarray
    number_densities: np.ndarray
    reconstructed: np.ndarray
    per_species_od: np.ndarray
    metrics: dict[str, float]
    repeat_count: int
    clip_applied: bool
    hono_exceed: bool
    excluded_species: list[str]
    no_align_shifts: dict[str, float] | None = None
    no_fwhm_delta: float | None = None


@dataclass
class SingleAnalysisResult:
    wavelengths: np.ndarray
    measured_od: np.ndarray
    regression: RegressionResult
    chemical_table: pd.DataFrame
    per_species_frame: pd.DataFrame


@dataclass
class TimeSeriesAnalysisResult:
    summary_table: pd.DataFrame
    single_results: list[SingleAnalysisResult]
    labels: list[str]


SPECIES_ORDER = ["HONO", "HONO2", "N2O4", "N2O5", "NO", "NO2", "NO3", "O3"]

WAVE_LOW_DEFAULT = 210.0
WAVE_HIGH_DEFAULT = 400.0

DEFAULT_OD_CLIP_THRESHOLD = 0.2
DEFAULT_OD_AVG_COEFF = 1.2
DEFAULT_MIN_FIT_FRACTION = 0.15
DEFAULT_MAX_REPEAT = 5

# O3-mode NO/O3 suppression — faithful to the original absorption-fitting
# notebook. In O3-dominated spectra NO (or O3) is often a false positive:
#   "ratio"      — the 20x pair (default): if coeff[NO] > ratio*coeff[O3]
#                  remove O3; if coeff[NO] < ratio*coeff[O3] remove NO.
#   "o3_density" — if O3 number density (coeff[O3]/path_length) > threshold,
#                  remove NO.
#   "off"        — apply neither.
# Removal = zero that cross-section column and refit the remaining species,
# so the survivors re-fit to the residual signal (not a bare post-hoc zero).
DEFAULT_NO_O3_RULE = "ratio"
DEFAULT_NO_O3_RATIO = 20.0
DEFAULT_NO_O3_DENSITY_THRESHOLD = 3.0e14
DEFAULT_ALIGN_NO_BANDS = True

# NO gamma-band auto-alignment: the sharp gamma(1,0)/gamma(0,0) bands are the
# only sub-nm features in the 210-400 nm fit range, so a small wavelength
# mismatch between the tabulated NO cross section and the spectrometer axis
# ruins the NO fit while leaving the broadband species untouched.
NO_GAMMA_BAND_WINDOWS: tuple[tuple[float, float, float], ...] = (
    (215.0, 213.0, 217.0),  # gamma(1,0): band center, window low, window high
    (226.2, 224.0, 228.0),  # gamma(0,0)
)
NO_ALIGN_MAX_SHIFT_NM = 0.5
NO_ALIGN_SHIFT_STEP_NM = 0.02
NO_ALIGN_MIN_CORRELATION = 0.8
NO_ALIGN_MIN_POINTS = 8

# NO resolution (FWHM) matching: the tabulated NO cross section carries the
# resolution of the instrument it was prepared for. A different spectrometer
# sees the gamma bands broader (lower resolution) or narrower (higher
# resolution), so the effective sigma is the tabulated one convolved with —
# or deconvolved by — a Gaussian of FWHM |delta|. delta > 0 broadens, delta < 0
# sharpens (Wiener-regularised deconvolution; band area, and therefore the
# retrieved NO density, is preserved either way).
DEFAULT_NO_FWHM_MODE = "auto"          # "auto" | "manual" | "off"
DEFAULT_NO_FWHM_DELTA = 0.0            # nm, used in "manual" mode
NO_FWHM_DELTA_MIN = -0.35              # sharpening limit (deconvolution stability)
NO_FWHM_DELTA_MAX = 1.5                # broadening limit
NO_FWHM_SCAN_STEP = 0.05               # nm, auto-scan grid
NO_FWHM_TIE_TOLERANCE = 0.003          # prefer delta=0 within this corr margin
NO_FWHM_DECONV_REG = 1e-3              # Wiener regularisation for delta < 0
NO_FWHM_FINE_STEP = 0.02               # nm, uniform grid for the FFT ops

# Backward-compatible aliases (used by existing internal helper functions)
OD_CLIP_THRESHOLD = DEFAULT_OD_CLIP_THRESHOLD
OD_AVG_COEFF = DEFAULT_OD_AVG_COEFF
MIN_FIT_FRACTION = DEFAULT_MIN_FIT_FRACTION


@dataclass(frozen=True)
class FitConfig:
    wave_low: float = WAVE_LOW_DEFAULT
    wave_high: float = WAVE_HIGH_DEFAULT
    od_clip_threshold: float = DEFAULT_OD_CLIP_THRESHOLD
    od_avg_coeff: float = DEFAULT_OD_AVG_COEFF
    min_fit_fraction: float = DEFAULT_MIN_FIT_FRACTION
    max_repeat: int = DEFAULT_MAX_REPEAT
    no_o3_rule: str = DEFAULT_NO_O3_RULE                       # "ratio" | "o3_density" | "off"
    no_o3_ratio: float = DEFAULT_NO_O3_RATIO
    no_o3_density_threshold: float = DEFAULT_NO_O3_DENSITY_THRESHOLD
    align_no_bands: bool = DEFAULT_ALIGN_NO_BANDS
    no_fwhm_mode: str = DEFAULT_NO_FWHM_MODE                   # "auto" | "manual" | "off"
    no_fwhm_delta: float = DEFAULT_NO_FWHM_DELTA               # nm, manual mode only


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "utf-16", "latin1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _load_bytes(file_or_path: str | Path | BinaryIO | bytes) -> bytes:
    if isinstance(file_or_path, bytes):
        return file_or_path
    if isinstance(file_or_path, (str, Path)):
        return Path(file_or_path).read_bytes()
    if hasattr(file_or_path, "getvalue"):
        return file_or_path.getvalue()
    if hasattr(file_or_path, "read"):
        return file_or_path.read()
    raise TypeError("Unsupported file input type")


def _extract_numeric_suffix(name: str) -> float | None:
    stem = Path(name).stem
    match = re.search(r"(\d+(?:\.\d+)?)$", stem)
    if match is None:
        return None
    return float(match.group(1))


def _spectrasuite_pairs(text: str) -> list[tuple[float, float]]:
    lines = text.splitlines()
    data_start = 0
    for index, line in enumerate(lines):
        if "Begin Processed Spectral Data" in line or "Begin Spectral Data" in line:
            data_start = index + 1
            break

    pairs: list[tuple[float, float]] = []
    for line in lines[data_start:]:
        if "End Processed Spectral Data" in line or "End Spectral Data" in line:
            break
        stripped = line.strip()
        if not stripped:
            continue
        parts = [part for part in re.split(r"[\s,;\t]+", stripped) if part]
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[1])
        except ValueError:
            continue
        pairs.append((wavelength, value))
    return pairs


def _has_header(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = [token for token in stripped.replace(",", " ").replace(";", " ").split() if token]
        if not tokens:
            continue
        try:
            [float(token) for token in tokens]
            return False
        except ValueError:
            return True
    return False


def _read_table(text: str, has_header: bool) -> pd.DataFrame:
    return pd.read_csv(
        StringIO(text),
        sep=r"[\s,;\t]+",
        engine="python",
        comment="#",
        header=0 if has_header else None,
    )


def load_spectrum(file_or_path: str | Path | BinaryIO | bytes) -> SpectrumData:
    text = _decode_text(_load_bytes(file_or_path))
    pairs = _spectrasuite_pairs(text)
    if pairs:
        numeric = pd.DataFrame(pairs, columns=["wavelength", "value"])
    else:
        data = _read_table(text, has_header=False)
        numeric = data.apply(pd.to_numeric, errors="coerce")
        numeric = numeric.dropna(how="all")
        if numeric.shape[1] < 2:
            raise ValueError("Spectrum file must contain at least two columns: wavelength and value.")
        numeric = numeric.iloc[:, :2].dropna()

    numeric = numeric.sort_values(numeric.columns[0]).drop_duplicates(subset=numeric.columns[0])
    wavelengths = numeric.iloc[:, 0].to_numpy(dtype=float)
    values = numeric.iloc[:, 1].to_numpy(dtype=float)
    return SpectrumData(wavelengths=wavelengths, values=values)


def load_cross_sections(file_or_path: str | Path | BinaryIO | bytes) -> CrossSectionData:
    text = _decode_text(_load_bytes(file_or_path))
    has_header = _has_header(text)
    data = _read_table(text, has_header=has_header)
    if data.shape[1] < 2:
        raise ValueError("Cross-section file must contain a wavelength column and at least one species column.")

    first_column = data.columns[0]
    numeric = data.copy()
    if has_header:
        numeric.iloc[:, 0] = pd.to_numeric(numeric.iloc[:, 0], errors="coerce")
        for column in numeric.columns[1:]:
            numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    else:
        numeric = numeric.apply(pd.to_numeric, errors="coerce")
        numeric.columns = ["wavelength", *[f"species_{index}" for index in range(1, numeric.shape[1])]]
        first_column = "wavelength"

    numeric = numeric.dropna(how="all").dropna()
    numeric = numeric.sort_values(first_column).drop_duplicates(subset=first_column)
    wavelengths = numeric.iloc[:, 0].to_numpy(dtype=float)
    species = [str(column) for column in numeric.columns[1:]]
    values = numeric.iloc[:, 1:].to_numpy(dtype=float)
    return CrossSectionData(wavelengths=wavelengths, species=species, values=values)


def compute_absorbance(measured: SpectrumData, reference: SpectrumData) -> SpectrumData:
    reference_values = np.interp(
        measured.wavelengths,
        reference.wavelengths,
        reference.values,
        left=np.nan,
        right=np.nan,
    )
    valid = np.isfinite(reference_values)
    wavelengths = measured.wavelengths[valid]
    measured_values = measured.values[valid]
    reference_values = reference_values[valid]
    eps = 1e-12
    absorbance = np.log(np.clip(reference_values, eps, None) / np.clip(measured_values, eps, None))
    absorbance = np.where(np.isfinite(absorbance), absorbance, 0.0)
    return SpectrumData(wavelengths=wavelengths, values=absorbance)


def align_cross_sections(cross_sections: CrossSectionData, target_wavelengths: np.ndarray) -> np.ndarray:
    aligned = np.zeros((target_wavelengths.size, len(cross_sections.species)), dtype=float)
    for index in range(len(cross_sections.species)):
        aligned[:, index] = np.interp(
            target_wavelengths,
            cross_sections.wavelengths,
            cross_sections.values[:, index],
            left=0.0,
            right=0.0,
        )
    return aligned


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred)) if y_true.size > 1 else float("nan")
    denominator = np.where(np.abs(y_true) < 1e-12, np.nan, y_true)
    mape = float(np.nanmean(np.abs((y_true - y_pred) / denominator)) * 100.0)
    return {"rmse": rmse, "mae": mae, "r2": r2, "mape": mape}


def _smooth_signal(values: np.ndarray, window: int = 11) -> np.ndarray:
    if values.size < 3:
        return values.copy()
    window = max(3, int(window))
    if window % 2 == 0:
        window += 1
    if values.size < window:
        window = max(3, values.size // 2 * 2 + 1)
    series = pd.Series(values)
    return series.rolling(window=window, center=True, min_periods=1).mean().to_numpy(dtype=float)


def _fit_nnls_scaled(
    basis: np.ndarray,
    absorbance: np.ndarray,
    total_count: int,
    min_fit_fraction: float = DEFAULT_MIN_FIT_FRACTION,
) -> tuple[np.ndarray, float]:
    if absorbance.size == 0 or basis.shape[0] != absorbance.size:
        return np.zeros(basis.shape[1], dtype=float), 0.0

    if absorbance.size <= min_fit_fraction * max(total_count, 1):
        return np.zeros(basis.shape[1], dtype=float), 0.0

    cross_std = np.std(basis, axis=0)
    cross_std[cross_std == 0] = 1.0
    basis_scaled = basis / cross_std[np.newaxis, :]

    reg = LinearRegression(positive=True, fit_intercept=False)
    reg.fit(basis_scaled, absorbance)
    coefficients = (np.asarray(reg.coef_, dtype=float).reshape(-1) / cross_std)

    if not np.any(coefficients):
        return coefficients, 0.0

    reconstructed = basis @ coefficients
    try:
        r2 = float(r2_score(reconstructed, absorbance))
    except Exception:
        r2 = 0.0
    return coefficients, r2


def _compute_positive_clip_indices(
    wavelengths: np.ndarray,
    absorbance: np.ndarray,
    absorbance_smooth: np.ndarray,
    threshold: float,
) -> np.ndarray:
    ind_240_270 = np.where((wavelengths >= 240.0) & (wavelengths <= 270.0))[0]
    if ind_240_270.size == 0:
        return np.array([], dtype=int)

    od_avg_240_270 = float(np.mean(absorbance[ind_240_270]))
    if od_avg_240_270 <= 1.0:
        return np.array([], dtype=int)

    od_noise = absorbance - absorbance_smooth
    od_noise_240_270 = od_noise[ind_240_270]
    threshold_ind_240_270 = np.where(od_noise_240_270 > threshold)[0]
    if threshold_ind_240_270.size == 0:
        return np.array([], dtype=int)

    ind_254_300 = np.where((wavelengths >= 240.0) & (wavelengths <= 300.0))[0]
    if ind_254_300.size == 0:
        return np.array([], dtype=int)

    od_noise_254_300 = od_noise[ind_254_300]
    under_threshold = np.where(od_noise_254_300 < threshold)[0]
    if under_threshold.size == 0:
        return np.array([], dtype=int)

    threshold_right_x = float(wavelengths[ind_254_300[under_threshold[0]]])
    for i in range(ind_254_300.size - 1):
        if od_noise_254_300[i] > threshold and od_noise_254_300[i + 1] <= threshold:
            threshold_right_x = float(wavelengths[ind_254_300[i + 1]])

    left_guess = 254.0 - (threshold_right_x - 254.0 + 5.0)
    clip = np.where((wavelengths >= left_guess) & (wavelengths <= threshold_right_x))[0]
    return np.unique(clip).astype(int)


def _suppress_false_positives(
    basis: np.ndarray,
    wavelengths: np.ndarray,
    absorbance: np.ndarray,
    coefficients: np.ndarray,
    fit_indices: np.ndarray,
    od_avg_coeff: float = DEFAULT_OD_AVG_COEFF,
    min_fit_fraction: float = DEFAULT_MIN_FIT_FRACTION,
) -> tuple[np.ndarray, list[int]]:
    if coefficients.size == 0:
        return coefficients, []

    win = np.where((wavelengths >= 350.0) & (wavelengths <= 370.0))[0]
    if win.size == 0:
        return coefficients, []

    reconstructed_species = basis * coefficients[np.newaxis, :]
    total_avg = float(np.mean(absorbance[win]))
    if not np.isfinite(total_avg) or total_avg <= 0:
        return coefficients, []

    species_avg = np.mean(reconstructed_species[win, :], axis=0)
    suspicious = (species_avg > od_avg_coeff * total_avg) & (coefficients > 0)
    if not np.any(suspicious):
        return coefficients, []

    keep_cols = np.where(~suspicious)[0]
    excluded_cols = np.where(suspicious)[0].astype(int).tolist()
    if keep_cols.size == 0:
        return np.zeros_like(coefficients), excluded_cols

    fit_basis = basis[np.asarray(fit_indices, dtype=int)][:, keep_cols]
    fit_abs = absorbance[np.asarray(fit_indices, dtype=int)]
    fitted_keep, _ = _fit_nnls_scaled(
        fit_basis,
        fit_abs,
        total_count=absorbance.size,
        min_fit_fraction=min_fit_fraction,
    )
    updated = np.zeros_like(coefficients)
    updated[keep_cols] = fitted_keep
    return updated, excluded_cols


def _estimate_no_band_shift(
    wavelengths: np.ndarray,
    absorbance: np.ndarray,
    cross_wavelengths: np.ndarray,
    cross_no: np.ndarray,
    window_low: float,
    window_high: float,
) -> tuple[float, float] | None:
    """Best wavelength shift of the NO cross section against the measured OD
    inside one gamma-band window, found by normalised cross-correlation.

    Returns (shift_nm, correlation), or None when the band is absent/too noisy
    (low correlation) or the optimum pins at the search edge.
    """
    mask = (wavelengths >= window_low) & (wavelengths <= window_high)
    if int(mask.sum()) < NO_ALIGN_MIN_POINTS:
        return None

    window_wl = wavelengths[mask]
    od_centered = absorbance[mask] - float(np.mean(absorbance[mask]))
    od_norm = float(np.sqrt(np.sum(od_centered**2)))
    if od_norm <= 0.0:
        return None

    shifts = np.arange(
        -NO_ALIGN_MAX_SHIFT_NM,
        NO_ALIGN_MAX_SHIFT_NM + NO_ALIGN_SHIFT_STEP_NM / 2,
        NO_ALIGN_SHIFT_STEP_NM,
    )
    best_shift = 0.0
    best_corr = -np.inf
    for shift in shifts:
        sigma = np.interp(window_wl + shift, cross_wavelengths, cross_no)
        sigma_centered = sigma - float(np.mean(sigma))
        sigma_norm = float(np.sqrt(np.sum(sigma_centered**2)))
        if sigma_norm <= 0.0:
            continue
        corr = float(np.dot(od_centered, sigma_centered) / (od_norm * sigma_norm))
        if corr > best_corr:
            best_corr = corr
            best_shift = float(shift)

    if best_corr < NO_ALIGN_MIN_CORRELATION:
        return None
    if abs(best_shift) >= NO_ALIGN_MAX_SHIFT_NM - NO_ALIGN_SHIFT_STEP_NM / 2:
        return None
    return best_shift, best_corr


def _resolution_adjust_family(sigma_fine: np.ndarray, step: float):
    """Return adjust(delta_fwhm) -> sigma on the same fine grid.

    delta > 0 convolves with a Gaussian of that FWHM (broaden); delta < 0
    applies the Wiener-regularised inverse (sharpen). The forward FFT of the
    edge-padded signal is computed once so an auto-scan over many deltas only
    pays one inverse FFT per candidate. Gaussian (de)convolution preserves
    band area, so the retrieved NO density is insensitive to delta.
    """
    n = sigma_fine.size
    pad = min(n, 512)
    extended = np.concatenate([
        np.full(pad, sigma_fine[0]), sigma_fine, np.full(pad, sigma_fine[-1])
    ])
    forward = np.fft.rfft(extended)
    freq = np.fft.rfftfreq(extended.size, d=step)

    def adjust(delta_fwhm: float) -> np.ndarray:
        if abs(delta_fwhm) < 1e-9:
            return sigma_fine.copy()
        gauss_sigma = abs(delta_fwhm) / 2.35482
        kernel = np.exp(-2.0 * np.pi**2 * gauss_sigma**2 * freq**2)
        if delta_fwhm > 0:
            out = np.fft.irfft(forward * kernel, n=extended.size)
        else:
            out = np.fft.irfft(
                forward * kernel / (kernel**2 + NO_FWHM_DECONV_REG), n=extended.size
            )
        return np.clip(out[pad:pad + n], 0.0, None)

    return adjust


# Per-CrossSectionData cache of (fine grid, resolution-adjust closure). Keyed
# by object identity with the object retained, so time-series runs that reuse
# one CrossSectionData across hundreds of frames pay the FFT setup once.
_NO_SIGMA_FAMILY_CACHE: dict[int, tuple[CrossSectionData, np.ndarray, object]] = {}


def _no_sigma_family_cached(cross_sections: CrossSectionData):
    cached = _NO_SIGMA_FAMILY_CACHE.get(id(cross_sections))
    if cached is not None and cached[0] is cross_sections:
        return cached[1], cached[2]

    index_no = cross_sections.species.index("NO")
    fine_grid = np.arange(
        cross_sections.wavelengths.min(),
        cross_sections.wavelengths.max() + NO_FWHM_FINE_STEP / 2,
        NO_FWHM_FINE_STEP,
    )
    sigma_fine = np.interp(
        fine_grid, cross_sections.wavelengths, cross_sections.values[:, index_no]
    )
    adjust = _resolution_adjust_family(sigma_fine, NO_FWHM_FINE_STEP)

    if len(_NO_SIGMA_FAMILY_CACHE) >= 4:
        _NO_SIGMA_FAMILY_CACHE.pop(next(iter(_NO_SIGMA_FAMILY_CACHE)))
    _NO_SIGMA_FAMILY_CACHE[id(cross_sections)] = (cross_sections, fine_grid, adjust)
    return fine_grid, adjust


def _match_no_basis_column(
    wavelengths: np.ndarray,
    absorbance: np.ndarray,
    cross_sections: CrossSectionData,
    fwhm_mode: str = DEFAULT_NO_FWHM_MODE,
    fwhm_delta: float = DEFAULT_NO_FWHM_DELTA,
) -> tuple[np.ndarray | None, dict[str, float], float | None]:
    """Match the NO cross-section column to the measured gamma bands.

    Two-stage, in this order:
      1. wavelength shift — per-band cross-correlation (always attempted);
      2. resolution — Gaussian FWHM delta relative to the tabulated sigma,
         either scanned automatically ("auto"), taken from the user
         ("manual"), or skipped ("off"). Shifts are re-estimated at every
         candidate delta so the two never fight each other.

    Candidates are ranked by (number of accepted bands, mean band
    correlation); within NO_FWHM_TIE_TOLERANCE of the best correlation the
    smallest |delta| wins, so a spectrometer that already matches the
    tabulated resolution keeps delta = 0 exactly.

    Returns (aligned column at `wavelengths`, per-band shift info,
    chosen delta) — or (None, {}, None) when no band qualifies, leaving the
    fit identical to the unmatched behaviour.
    """
    if "NO" not in cross_sections.species:
        return None, {}, None

    fine_grid, adjust = _no_sigma_family_cached(cross_sections)

    if fwhm_mode == "manual":
        delta_candidates = [float(np.clip(fwhm_delta, NO_FWHM_DELTA_MIN, NO_FWHM_DELTA_MAX))]
    elif fwhm_mode == "auto":
        delta_candidates = list(np.arange(
            NO_FWHM_DELTA_MIN, NO_FWHM_DELTA_MAX + NO_FWHM_SCAN_STEP / 2, NO_FWHM_SCAN_STEP
        ))
        delta_candidates = sorted(set(round(d, 4) for d in delta_candidates) | {0.0})
    else:  # "off" — wavelength shift only, on the tabulated resolution
        delta_candidates = [0.0]

    evaluated: list[tuple[int, float, float, list[tuple[float, float]]]] = []
    for delta in delta_candidates:
        sigma_adj = adjust(delta)
        accepted: list[tuple[float, float]] = []
        correlations: list[float] = []
        for center, low, high in NO_GAMMA_BAND_WINDOWS:
            estimate = _estimate_no_band_shift(
                wavelengths, absorbance, fine_grid, sigma_adj, low, high
            )
            if estimate is None:
                continue
            shift, corr = estimate
            accepted.append((center, shift))
            correlations.append(corr)
        if accepted:
            evaluated.append(
                (len(accepted), float(np.mean(correlations)), float(delta), accepted)
            )

    if not evaluated:
        return None, {}, None

    max_bands = max(item[0] for item in evaluated)
    contenders = [item for item in evaluated if item[0] == max_bands]
    best_corr = max(item[1] for item in contenders)
    within_tol = [
        item for item in contenders if item[1] >= best_corr - NO_FWHM_TIE_TOLERANCE
    ]
    _, _, chosen_delta, accepted = min(within_tol, key=lambda item: abs(item[2]))
    chosen_delta = 0.0 if chosen_delta == 0 else chosen_delta  # normalise -0.0

    sigma_final = adjust(chosen_delta)
    info: dict[str, float] = {
        f"{center:.0f}": round(shift, 3) for center, shift in accepted
    }

    if len(accepted) == 1:
        shift_of_wl = np.full(wavelengths.size, accepted[0][1])
    else:
        centers = np.array([item[0] for item in accepted])
        shifts = np.array([item[1] for item in accepted])
        shift_of_wl = np.interp(wavelengths, centers, shifts)

    aligned = np.interp(
        wavelengths + shift_of_wl,
        fine_grid,
        sigma_final,
        left=0.0,
        right=0.0,
    )
    return aligned, info, (chosen_delta if fwhm_mode != "off" else None)


def _find_local_maxima(values: np.ndarray) -> np.ndarray:
    if values.size < 3:
        return np.array([], dtype=int)
    left = values[1:-1] > values[:-2]
    right = values[1:-1] >= values[2:]
    return np.where(left & right)[0] + 1


def _evaluate_hono_exceed(
    basis: np.ndarray,
    absorbance: np.ndarray,
    coefficients: np.ndarray,
    species: list[str],
) -> bool:
    if "HONO" not in species:
        return False

    idx_hono = species.index("HONO")
    hono_od = basis[:, idx_hono] * coefficients[idx_hono]
    peaks = _find_local_maxima(hono_od)
    if peaks.size == 0:
        return False

    top = peaks[np.argsort(hono_od[peaks])[::-1][:2]]
    reconstructed = basis @ coefficients
    exceed_count = int(np.sum(reconstructed[top] > absorbance[top]))
    return exceed_count == min(2, top.size)


def _iterative_repeat_refit(
    basis: np.ndarray,
    wavelengths: np.ndarray,
    absorbance: np.ndarray,
    fit_indices: np.ndarray,
    max_repeat: int = DEFAULT_MAX_REPEAT,
    od_avg_coeff: float = DEFAULT_OD_AVG_COEFF,
    min_fit_fraction: float = DEFAULT_MIN_FIT_FRACTION,
) -> tuple[np.ndarray, int, list[int]]:
    fit_indices = np.asarray(fit_indices, dtype=int)
    coefficients, _ = _fit_nnls_scaled(
        basis[fit_indices],
        absorbance[fit_indices],
        total_count=absorbance.size,
        min_fit_fraction=min_fit_fraction,
    )

    repeat_count = 0
    excluded_union: set[int] = set()
    for _ in range(max_repeat):
        updated, excluded = _suppress_false_positives(
            basis=basis,
            wavelengths=wavelengths,
            absorbance=absorbance,
            coefficients=coefficients,
            fit_indices=fit_indices,
            od_avg_coeff=od_avg_coeff,
            min_fit_fraction=min_fit_fraction,
        )
        if not excluded:
            break
        repeat_count += 1
        excluded_union.update(excluded)
        if np.allclose(updated, coefficients):
            break
        coefficients = updated

    return coefficients, repeat_count, sorted(excluded_union)


def _o3_no_exclusion_indices(
    coefficients: np.ndarray,
    species: list[str],
    path_length_cm: float,
    rule: str,
    ratio: float,
    density_threshold: float,
) -> list[int]:
    """Species indices to exclude under the O3-mode NO/O3 rule.

    Faithful to the original absorption-fitting notebook:
      "ratio"      — if coeff[NO] > ratio*coeff[O3] remove O3;
                     if coeff[NO] < ratio*coeff[O3] remove NO.
      "o3_density" — if O3 number density (coeff[O3]/path_length) > threshold,
                     remove NO.
      "off"        — nothing.
    `coefficients` are the raw fit coefficients (number density x path length).
    """
    if rule == "off" or "NO" not in species or "O3" not in species:
        return []
    ind_no = species.index("NO")
    ind_o3 = species.index("O3")
    out: list[int] = []
    if rule == "o3_density":
        if coefficients[ind_no] > 0:
            o3_number_density = coefficients[ind_o3] / max(path_length_cm, 1e-12)
            if o3_number_density > density_threshold:
                out.append(ind_no)
    else:  # "ratio" — original 20x pair
        if coefficients[ind_o3] > 0 and coefficients[ind_no] > ratio * coefficients[ind_o3]:
            out.append(ind_o3)
        if coefficients[ind_no] > 0 and coefficients[ind_no] < ratio * coefficients[ind_o3]:
            out.append(ind_no)
    return out


def discover_cross_section_dirs(search_root: str | Path) -> list[Path]:
    root = Path(search_root)
    if not root.exists():
        return []

    def _is_valid_cross_dir(folder: Path) -> bool:
        return folder.is_dir() and all((folder / f"{name}_ordered_cross_section.txt").exists() for name in SPECIES_ORDER)

    discovered: list[Path] = []
    for folder in root.rglob("Cross_sections_modified"):
        if _is_valid_cross_dir(folder):
            discovered.append(folder)
    for folder in root.rglob("Cross_sections_out"):
        if _is_valid_cross_dir(folder):
            discovered.append(folder)
    return sorted(set(path.resolve() for path in discovered))


def discover_preferred_cross_section_dir(search_root: str | Path) -> Path | None:
    root = Path(search_root)
    if not root.exists():
        return None

    def _is_valid_cross_dir(folder: Path) -> bool:
        return folder.is_dir() and all((folder / f"{name}_ordered_cross_section.txt").exists() for name in SPECIES_ORDER)

    modified_candidates: list[Path] = []
    for folder in root.rglob("Cross_sections_modified"):
        if _is_valid_cross_dir(folder):
            modified_candidates.append(folder.resolve())

    if modified_candidates:
        return sorted(set(modified_candidates))[0]

    legacy_candidates = discover_cross_section_dirs(root)
    return legacy_candidates[0] if legacy_candidates else None


def load_cross_sections_from_dir(cross_section_dir: str | Path) -> CrossSectionData:
    cross_dir = Path(cross_section_dir)
    if not cross_dir.exists():
        raise FileNotFoundError(f"Cross-section directory was not found: {cross_dir}")

    tables: list[pd.DataFrame] = []
    for species in SPECIES_ORDER:
        path = cross_dir / f"{species}_ordered_cross_section.txt"
        if not path.exists():
            raise FileNotFoundError(f"Missing cross-section file: {path}")
        table = load_spectrum(path)
        tables.append(
            pd.DataFrame({
                "wavelength": table.wavelengths,
                species: table.values,
            })
        )

    merged = tables[0]
    for table in tables[1:]:
        merged = merged.merge(table, on="wavelength", how="inner")

    wavelengths = merged["wavelength"].to_numpy(dtype=float)
    values = merged[SPECIES_ORDER].to_numpy(dtype=float)
    return CrossSectionData(wavelengths=wavelengths, species=SPECIES_ORDER, values=values)


def compute_optical_depth_from_reference(
    reference_spectrum: SpectrumData,
    measured_spectrum: SpectrumData,
    wave_low: float | None = None,
    wave_high: float | None = None,
) -> SpectrumData:
    interpolated = np.interp(
        reference_spectrum.wavelengths,
        measured_spectrum.wavelengths,
        measured_spectrum.values,
        left=np.nan,
        right=np.nan,
    )
    valid = (
        np.isfinite(interpolated)
        & np.isfinite(reference_spectrum.values)
        & (reference_spectrum.values > 0)
        & (interpolated > 0)
    )

    if wave_low is not None:
        valid &= reference_spectrum.wavelengths >= wave_low
    if wave_high is not None:
        valid &= reference_spectrum.wavelengths <= wave_high

    wavelengths = reference_spectrum.wavelengths[valid]
    od = np.log(reference_spectrum.values[valid] / interpolated[valid])
    finite = np.isfinite(od)
    return SpectrumData(wavelengths=wavelengths[finite], values=od[finite])


def run_linear_regression_with_cross_section_dir(
    optical_depth: SpectrumData,
    cross_section_dir: str | Path,
    path_length_cm: float,
    config: FitConfig | None = None,
) -> SingleAnalysisResult:
    cross_sections = load_cross_sections_from_dir(cross_section_dir)

    aligned_od = SpectrumData(
        wavelengths=optical_depth.wavelengths,
        values=optical_depth.values,
    )
    wavelength_min = cross_sections.wavelengths.min()
    wavelength_max = cross_sections.wavelengths.max()
    within_cross = (aligned_od.wavelengths >= wavelength_min) & (aligned_od.wavelengths <= wavelength_max)
    aligned_od = SpectrumData(
        wavelengths=aligned_od.wavelengths[within_cross],
        values=aligned_od.values[within_cross],
    )
    if aligned_od.wavelengths.size < 10:
        raise ValueError("Not enough overlapping wavelength points between OD and cross sections.")

    regression = run_linear_regression(
        absorbance=aligned_od,
        cross_sections=cross_sections,
        path_length_cm=path_length_cm,
        config=config,
    )

    detected = np.where(regression.number_densities > 0.0, "Yes", "No")
    chemical_table = pd.DataFrame(
        {
            "Chemical species": regression.species,
            "Detected": detected,
            "Estimated concentration": regression.number_densities,
            "Unit": ["molec/cm3"] * len(regression.species),
        }
    )

    per_species_frame = pd.DataFrame({"wavelength": aligned_od.wavelengths})
    for index, species in enumerate(regression.species):
        per_species_frame[species] = regression.per_species_od[:, index]

    return SingleAnalysisResult(
        wavelengths=aligned_od.wavelengths,
        measured_od=aligned_od.values,
        regression=regression,
        chemical_table=chemical_table,
        per_species_frame=per_species_frame,
    )


def run_single_from_intensity_files(
    reference_file: str | Path | BinaryIO | bytes,
    measured_file: str | Path | BinaryIO | bytes,
    cross_section_dir: str | Path,
    path_length_cm: float,
    wave_low: float = WAVE_LOW_DEFAULT,
    wave_high: float = WAVE_HIGH_DEFAULT,
    config: FitConfig | None = None,
) -> SingleAnalysisResult:
    reference = load_spectrum(reference_file)
    measured = load_spectrum(measured_file)
    optical_depth = compute_optical_depth_from_reference(
        reference_spectrum=reference,
        measured_spectrum=measured,
        wave_low=wave_low,
        wave_high=wave_high,
    )
    if optical_depth.wavelengths.size < 10:
        raise ValueError("Optical depth points are too few after preprocessing.")

    return run_linear_regression_with_cross_section_dir(
        optical_depth=optical_depth,
        cross_section_dir=cross_section_dir,
        path_length_cm=path_length_cm,
        config=config,
    )


def sort_time_series_files_by_name(file_items: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    def sort_key(item: tuple[str, bytes]) -> tuple[int, float, str]:
        name = item[0]
        suffix = _extract_numeric_suffix(name)
        if suffix is None:
            return (1, 0.0, name.lower())
        return (0, suffix, name.lower())

    return sorted(file_items, key=sort_key)


def run_time_series_from_intensity_files(
    files: list[tuple[str, bytes]],
    cross_section_dir: str | Path,
    path_length_cm: float,
    wave_low: float = WAVE_LOW_DEFAULT,
    wave_high: float = WAVE_HIGH_DEFAULT,
    config: FitConfig | None = None,
    progress_callback=None,
) -> TimeSeriesAnalysisResult:
    if len(files) < 2:
        raise ValueError("At least two files are required: one reference (I0) and one measured spectrum.")

    sorted_files = sort_time_series_files_by_name(files)
    _, reference_bytes = sorted_files[0]

    # Performance: avoid re-loading reference and cross sections for every time point.
    reference_spectrum = load_spectrum(reference_bytes)
    cross_sections = load_cross_sections_from_dir(cross_section_dir)

    summary_rows: list[dict[str, float]] = []
    labels: list[str] = []
    single_results: list[SingleAnalysisResult] = []

    wavelength_min = cross_sections.wavelengths.min()
    wavelength_max = cross_sections.wavelengths.max()

    for fallback_index, (name, data) in enumerate(sorted_files[1:], start=1):
        measured_spectrum = load_spectrum(data)

        optical_depth = compute_optical_depth_from_reference(
            reference_spectrum=reference_spectrum,
            measured_spectrum=measured_spectrum,
            wave_low=wave_low,
            wave_high=wave_high,
        )
        if optical_depth.wavelengths.size < 10:
            raise ValueError("Optical depth points are too few after preprocessing.")

        aligned_od = SpectrumData(
            wavelengths=optical_depth.wavelengths,
            values=optical_depth.values,
        )
        within_cross = (aligned_od.wavelengths >= wavelength_min) & (aligned_od.wavelengths <= wavelength_max)
        aligned_od = SpectrumData(
            wavelengths=aligned_od.wavelengths[within_cross],
            values=aligned_od.values[within_cross],
        )
        if aligned_od.wavelengths.size < 10:
            raise ValueError("Not enough overlapping wavelength points between OD and cross sections.")

        regression = run_linear_regression(
            absorbance=aligned_od,
            cross_sections=cross_sections,
            path_length_cm=path_length_cm,
            config=config,
        )

        detected = np.where(regression.number_densities > 0.0, "Yes", "No")
        chemical_table = pd.DataFrame(
            {
                "Chemical species": regression.species,
                "Detected": detected,
                "Estimated concentration": regression.number_densities,
                "Unit": ["molec/cm3"] * len(regression.species),
            }
        )

        per_species_frame = pd.DataFrame({"wavelength": aligned_od.wavelengths})
        for index, species in enumerate(regression.species):
            per_species_frame[species] = regression.per_species_od[:, index]

        result = SingleAnalysisResult(
            wavelengths=aligned_od.wavelengths,
            measured_od=aligned_od.values,
            regression=regression,
            chemical_table=chemical_table,
            per_species_frame=per_species_frame,
        )

        explicit_time = _extract_numeric_suffix(name)
        time_value = float(fallback_index if explicit_time is None else explicit_time)
        row: dict[str, float] = {"Time (s)": time_value}
        for species, value in zip(result.regression.species, result.regression.number_densities):
            row[species] = float(value)

        summary_rows.append(row)
        labels.append(name)
        single_results.append(result)

        if progress_callback is not None:
            try:
                progress_callback(fallback_index, len(sorted_files) - 1)
            except Exception:
                pass

    summary_table = pd.DataFrame(summary_rows).sort_values("Time (s)").reset_index(drop=True)
    return TimeSeriesAnalysisResult(
        summary_table=summary_table,
        single_results=single_results,
        labels=labels,
    )


def run_linear_regression(
    absorbance: SpectrumData,
    cross_sections: CrossSectionData,
    path_length_cm: float,
    config: FitConfig | None = None,
) -> RegressionResult:
    cfg = config or FitConfig()
    basis = align_cross_sections(cross_sections, absorbance.wavelengths)

    no_align_shifts: dict[str, float] = {}
    no_fwhm_delta: float | None = None
    if cfg.align_no_bands and "NO" in cross_sections.species:
        aligned_no, align_info, chosen_delta = _match_no_basis_column(
            absorbance.wavelengths,
            absorbance.values,
            cross_sections,
            fwhm_mode=cfg.no_fwhm_mode,
            fwhm_delta=cfg.no_fwhm_delta,
        )
        if aligned_no is not None:
            basis[:, cross_sections.species.index("NO")] = aligned_no
            no_align_shifts = align_info
            no_fwhm_delta = chosen_delta

    coefficients, _ = _fit_nnls_scaled(
        basis,
        absorbance.values,
        total_count=absorbance.values.size,
        min_fit_fraction=cfg.min_fit_fraction,
    )

    smoothed = _smooth_signal(absorbance.values, window=11)
    species_index_o3 = cross_sections.species.index("O3") if "O3" in cross_sections.species else -1
    fit_indices = np.arange(absorbance.values.size, dtype=int)
    clip_applied = False

    if species_index_o3 >= 0 and absorbance.values.size > 20:
        o3_cross = basis[:, species_index_o3]
        if o3_cross.size > 0:
            index_o3_peak = int(np.argmax(o3_cross))
            o3_od_peak = float(o3_cross[index_o3_peak] * coefficients[species_index_o3])
            smoothed_peak = float(smoothed[index_o3_peak])

            if o3_od_peak > smoothed_peak:
                clip_indices = _compute_positive_clip_indices(
                    wavelengths=absorbance.wavelengths,
                    absorbance=absorbance.values,
                    absorbance_smooth=smoothed,
                    threshold=cfg.od_clip_threshold,
                )
                if clip_indices.size > 0:
                    mask_keep = np.ones(absorbance.values.size, dtype=bool)
                    mask_keep[clip_indices] = False
                    fit_indices = np.where(mask_keep)[0]
                    clipped_basis = basis[fit_indices]
                    clipped_absorbance = absorbance.values[fit_indices]
                    coefficients_refit, _ = _fit_nnls_scaled(
                        clipped_basis,
                        clipped_absorbance,
                        total_count=absorbance.values.size,
                        min_fit_fraction=cfg.min_fit_fraction,
                    )
                    if np.any(coefficients_refit):
                        coefficients = coefficients_refit
                        clip_applied = True

    coefficients, repeat_count, excluded_indices = _iterative_repeat_refit(
        basis=basis,
        wavelengths=absorbance.wavelengths,
        absorbance=absorbance.values,
        fit_indices=fit_indices,
        max_repeat=cfg.max_repeat,
        od_avg_coeff=cfg.od_avg_coeff,
        min_fit_fraction=cfg.min_fit_fraction,
    )

    # O3-mode NO/O3 suppression (faithful to the original absorption-fitting
    # notebook): in O3-dominated spectra remove NO — or O3 — when the selected
    # rule fires, by zeroing that cross-section column and refitting the
    # remaining species so they re-fit to the residual signal. Layered after
    # the 350-370 nm refit above and looped until the exclusion set is stable.
    if cfg.no_o3_rule != "off":
        excluded_set = set(excluded_indices)
        fit_idx = np.asarray(fit_indices, dtype=int)
        for _ in range(max(cfg.max_repeat, 1)):
            new = set(_o3_no_exclusion_indices(
                coefficients, cross_sections.species, path_length_cm,
                cfg.no_o3_rule, cfg.no_o3_ratio, cfg.no_o3_density_threshold,
            )) - excluded_set
            if not new:
                break
            excluded_set |= new
            keep_cols = np.array(
                [i for i in range(basis.shape[1]) if i not in excluded_set], dtype=int
            )
            if keep_cols.size == 0:
                coefficients = np.zeros(basis.shape[1], dtype=float)
                repeat_count += 1
                break
            fitted_keep, _ = _fit_nnls_scaled(
                basis[fit_idx][:, keep_cols],
                absorbance.values[fit_idx],
                total_count=absorbance.values.size,
                min_fit_fraction=cfg.min_fit_fraction,
            )
            coefficients = np.zeros(basis.shape[1], dtype=float)
            coefficients[keep_cols] = fitted_keep
            repeat_count += 1
        excluded_indices = sorted(excluded_set)

    hono_exceed = _evaluate_hono_exceed(
        basis=basis,
        absorbance=absorbance.values,
        coefficients=coefficients,
        species=cross_sections.species,
    )

    reconstructed = basis @ coefficients
    per_species_od = basis * coefficients[np.newaxis, :]
    number_densities = coefficients / max(path_length_cm, 1e-12)
    metrics = compute_metrics(absorbance.values, reconstructed)
    return RegressionResult(
        species=cross_sections.species,
        coefficients=coefficients,
        number_densities=number_densities,
        reconstructed=reconstructed,
        per_species_od=per_species_od,
        metrics=metrics,
        repeat_count=repeat_count,
        clip_applied=clip_applied,
        hono_exceed=hono_exceed,
        excluded_species=[cross_sections.species[index] for index in excluded_indices],
        no_align_shifts=no_align_shifts,
        no_fwhm_delta=no_fwhm_delta,
    )


def build_result_table(species: list[str], values: np.ndarray, column_name: str) -> pd.DataFrame:
    return pd.DataFrame({"species": species, column_name: values}).sort_values(column_name, ascending=False)


def prepare_download_frame(
    wavelengths: np.ndarray,
    measured: np.ndarray,
    reconstructed: np.ndarray,
    species: list[str],
    per_species_od: np.ndarray,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "wavelength_nm": wavelengths,
            "measured_absorbance": measured,
            "reconstructed_absorbance": reconstructed,
        }
    )
    for index, name in enumerate(species):
        frame[f"od_{name}"] = per_species_od[:, index]
    return frame


def build_continual_learning_frame_single(
    result: SingleAnalysisResult,
    path_length_cm: float,
    reference_file: str,
    measured_file: str,
) -> pd.DataFrame:
    frame = prepare_download_frame(
        wavelengths=result.wavelengths,
        measured=result.measured_od,
        reconstructed=result.regression.reconstructed,
        species=result.regression.species,
        per_species_od=result.regression.per_species_od,
    )
    frame["path_length_cm"] = float(path_length_cm)
    frame["reference_file"] = str(reference_file)
    frame["measured_file"] = str(measured_file)
    frame["hono_exceed"] = bool(result.regression.hono_exceed)
    frame["clip_applied"] = bool(result.regression.clip_applied)
    frame["repeat_count"] = int(result.regression.repeat_count)
    return frame


def build_continual_learning_frame_timeseries(
    result: TimeSeriesAnalysisResult,
    path_length_cm: float,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for label, single in zip(result.labels, result.single_results):
        frame = prepare_download_frame(
            wavelengths=single.wavelengths,
            measured=single.measured_od,
            reconstructed=single.regression.reconstructed,
            species=single.regression.species,
            per_species_od=single.regression.per_species_od,
        )
        frame["time_label"] = str(label)
        frame["path_length_cm"] = float(path_length_cm)
        frame["hono_exceed"] = bool(single.regression.hono_exceed)
        frame["clip_applied"] = bool(single.regression.clip_applied)
        frame["repeat_count"] = int(single.regression.repeat_count)
        rows.append(frame)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)
