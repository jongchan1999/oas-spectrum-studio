from __future__ import annotations

import base64
import hmac
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from oas_web.analysis import (
    DEFAULT_MAX_REPEAT,
    DEFAULT_MIN_FIT_FRACTION,
    DEFAULT_OD_AVG_COEFF,
    DEFAULT_OD_CLIP_THRESHOLD,
    FitConfig,
    build_continual_learning_frame_single,
    build_continual_learning_frame_timeseries,
    compute_optical_depth_from_reference,
    discover_preferred_cross_section_dir,
    load_cross_sections_from_dir,
    load_spectrum,
    prepare_download_frame,
    run_single_from_intensity_files,
    run_time_series_from_intensity_files,
)
from oas_web.ml import (
    build_continual_learning_frame_ml_single,
    build_continual_learning_frame_ml_timeseries,
    run_ml_inference,
    run_time_series_ml_from_intensity_files,
)
from oas_web.plots import (
    make_intensity_preview,
    make_overlay_figure,
    make_species_bar,
    make_timeseries_trend,
)
from oas_web.cl_submit import (
    SubmissionError,
    build_submission_payload,
    submit_to_global_model,
)


ROOT = Path(__file__).resolve().parent
ML_FALLBACK_PTH = ROOT / "machine_learning" / "exp_4_epoch_3000.pth"
ML_LATEST_POINTER = ROOT / "models" / "latest.json"
ASSETS_DIR = ROOT / "assets"

# Partner logos. Drop a real raster/vector file at either of these names to
# override the bundled placeholder:
#   assets/kaist_logo.png   (or .svg)   → links to https://www.kaist.ac.kr/kr/
#   assets/april_logo.png   (or .svg)   → links to https://april.kaist.ac.kr/
# A text placeholder is rendered when no file is found.
KAIST_URL = "https://www.kaist.ac.kr/kr/"
APRIL_URL = "https://april.kaist.ac.kr/"


def _resolve_active_checkpoint() -> tuple[Path, str]:
    """Return (path, release_id) for the currently active ML release.

    Reads `models/latest.json` first — that's where the fine-tune
    pipeline writes the newest promoted checkpoint. Falls back to the
    bundled baseline so the app keeps working out of the box.
    """
    import json as _json
    if ML_LATEST_POINTER.exists():
        try:
            data = _json.loads(ML_LATEST_POINTER.read_text(encoding="utf-8"))
            rel_path = str(data.get("path", "")).strip()
            release_id = str(data.get("release_id", "baseline")).strip() or "baseline"
            if rel_path:
                candidate = (ROOT / rel_path).resolve()
                if candidate.exists():
                    return candidate, release_id
        except Exception:
            pass
    return ML_FALLBACK_PTH, "baseline"


ML_DEFAULT_PTH, ML_RELEASE_ID = _resolve_active_checkpoint()

st.set_page_config(
    page_title="OAS Spectrum Studio",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def html(body: str) -> None:
    """Inject raw HTML through st.markdown after stripping common indent.

    Streamlit's markdown parser treats 4+ space indents as code blocks, so any
    HTML pasted from indented Python source needs to be dedented first.
    """
    st.markdown(textwrap.dedent(body), unsafe_allow_html=True)


def _encode_image_b64(path: Path) -> str:
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _resolve_logo_data_uri(stem: str) -> str:
    """Return a data: URI for assets/<stem>.png|.svg, or '' if neither exists.

    Prefers a raster .png (real institutional logo) over the bundled .svg
    placeholder so dropping in an official file just works.
    """
    for ext, mime in ((".png", "image/png"), (".svg", "image/svg+xml")):
        candidate = ASSETS_DIR / f"{stem}{ext}"
        b64 = _encode_image_b64(candidate)
        if b64:
            return f"data:{mime};base64,{b64}"
    return ""


KAIST_LOGO_URI = _resolve_logo_data_uri("kaist_logo")
APRIL_LOGO_URI = _resolve_logo_data_uri("april_logo")


# ────────────────────────────────────────────────────────────────────────────
# Styles
# ────────────────────────────────────────────────────────────────────────────


def inject_styles() -> None:
    html("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --accent: #f97316;
        --ink: #0f172a;
        --muted: #64748b;
        --soft: #f1f5f9;
        --border: rgba(15, 23, 42, 0.08);
        --border-strong: rgba(15, 23, 42, 0.14);
        --shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 24px rgba(15,23,42,.06);
        --shadow-lg: 0 4px 12px rgba(15,23,42,.06), 0 24px 48px rgba(15,23,42,.08);
    }

    /* Body-level font — do NOT cover icon spans */
    html, body, .stApp { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }

    .stApp {
        background:
            radial-gradient(1200px 600px at 8% -10%, rgba(99,102,241,.10), transparent 60%),
            radial-gradient(900px 500px at 100% 0%, rgba(249,115,22,.08), transparent 60%),
            linear-gradient(180deg, #fafafa 0%, #f5f7fb 100%);
    }
    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { display: none; }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        padding-left: 1.6rem;
        padding-right: 1.6rem;
        max-width: 1480px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 1px solid var(--border);
    }

    /* Hero */
    /* Hero — refined deep-indigo gradient (less candy, more "lab report") */
    .hero {
        background:
            radial-gradient(900px 400px at 20% 20%, rgba(255,255,255,.10), transparent 60%),
            linear-gradient(135deg, #1e1b4b 0%, #3b2596 38%, #6d28d9 72%, #a21caf 100%);
        border-radius: 22px;
        padding: 1.55rem 1.85rem;
        margin-bottom: 1.05rem;
        box-shadow:
            0 1px 2px rgba(30,27,75,.18),
            0 14px 40px rgba(76, 29, 149, 0.28),
            inset 0 1px 0 rgba(255,255,255,.08);
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .hero::before {
        content: "";
        position: absolute; right: -100px; top: -100px;
        width: 320px; height: 320px;
        background: radial-gradient(circle, rgba(255,255,255,.22), transparent 70%);
        filter: blur(10px);
        pointer-events: none;
    }
    .hero::after {
        /* subtle dot pattern for "scientific" texture */
        content: "";
        position: absolute; inset: 0;
        background-image: radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px);
        background-size: 16px 16px;
        opacity: 0.4;
        pointer-events: none;
    }
    .hero-text { flex: 1.2; min-width: 280px; position: relative; z-index: 1; }
    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: .4rem;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.28);
        border-radius: 999px;
        padding: 4px 12px;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.92);
        margin-bottom: 0.55rem;
        backdrop-filter: blur(6px);
    }
    .hero-pill::before {
        content: "";
        width: 6px; height: 6px; border-radius: 50%;
        background: #34d399;
        box-shadow: 0 0 8px rgba(52,211,153,0.7);
        flex-shrink: 0;
    }
    .hero-text h1 {
        font-size: 1.72rem !important;
        font-weight: 800 !important;
        margin: 0 0 0.3rem 0 !important;
        color: white !important;
        letter-spacing: -0.018em;
        line-height: 1.15;
        text-shadow: 0 1px 0 rgba(0,0,0,.08);
    }
    .hero-text p {
        margin: 0 !important;
        opacity: 0.94;
        font-size: 0.95rem;
        font-weight: 500;
        color: rgba(255,255,255,0.92) !important;
        max-width: 58ch;
        line-height: 1.55;
    }
    .hero-image {
        flex: 1;
        max-width: 400px;
        position: relative;
        z-index: 1;
    }
    .hero-image img {
        width: 100%;
        height: auto;
        border-radius: 14px;
        background: rgba(255,255,255,0.98);
        padding: 8px;
        box-shadow:
            0 6px 20px rgba(15,23,42,.22),
            0 0 0 1px rgba(255,255,255,.4);
    }
    @media (max-width: 880px) {
        .hero { flex-direction: column; align-items: stretch; }
        .hero-image { max-width: 100%; }
    }

    /* Cards — native container as a paper-grade card with top gradient accent */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: white;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        padding: 1.2rem 1.35rem !important;
        box-shadow: var(--shadow);
        margin-bottom: 0.9rem;
        position: relative;
        transition: transform .15s ease, box-shadow .25s ease;
        overflow: hidden;
    }
    [data-testid="stVerticalBlockBorderWrapper"]::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        opacity: 0;
        transition: opacity .25s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover::before {
        opacity: 0.85;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: var(--shadow-lg);
    }

    /* Step header inside cards */
    .step-head { display: flex; align-items: center; gap: .65rem; margin: 0 0 1rem 0; }
    .step-num {
        width: 30px; height: 30px; border-radius: 9px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        display: inline-flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: .9rem;
        box-shadow: 0 1px 3px rgba(79,70,229,.30), 0 4px 10px rgba(79,70,229,.18);
    }
    .step-title {
        font-weight: 700; font-size: 1.05rem;
        color: var(--ink);
        letter-spacing: -0.008em;
    }

    /* Metric cards — premium look, larger numbers, accent stripe */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: .85rem 1rem;
        box-shadow: var(--shadow);
        position: relative;
        overflow: hidden;
    }
    [data-testid="stMetric"]::before {
        content: "";
        position: absolute; top: 0; left: 0; bottom: 0;
        width: 3px;
        background: linear-gradient(180deg, #6366f1 0%, #a855f7 100%);
        opacity: 0.7;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
        font-weight: 600 !important;
        font-size: .72rem !important;
        color: var(--muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
        font-weight: 700 !important;
        font-size: 1.32rem !important;
        color: var(--ink) !important;
        letter-spacing: -0.01em;
    }

    /* Tabs — sophisticated selected state */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: white;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 5px;
        margin-bottom: .85rem;
        box-shadow: var(--shadow);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px !important;
        padding: 0.55rem 1rem !important;
        font-weight: 600 !important;
        color: var(--muted) !important;
        border: none !important;
        transition: background .15s ease, color .15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(99,102,241,.06);
        color: var(--ink) !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%) !important;
        box-shadow: 0 1px 2px rgba(15,23,42,.18), 0 4px 10px rgba(15,23,42,.12);
    }
    .stTabs [aria-selected="true"] * { color: white !important; }

    /* Primary button — premium gradient with glow on hover */
    .stButton > button,
    .stButton > button > div,
    .stButton > button p {
        color: white !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #1e1b4b 0%, #4f46e5 60%, #7c3aed 100%) !important;
        border: none !important;
        border-radius: 11px !important;
        font-weight: 700 !important;
        padding: 0.62rem 1.1rem !important;
        letter-spacing: 0.005em;
        transition: transform .12s ease, box-shadow .2s ease, filter .15s ease;
        box-shadow:
            0 1px 2px rgba(30,27,75,.20),
            0 4px 14px rgba(79,70,229,.22);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.06);
        box-shadow:
            0 2px 6px rgba(30,27,75,.24),
            0 14px 32px rgba(79,70,229,.30);
    }
    .stButton > button[kind="secondary"],
    .stButton > button[kind="secondary"] > div,
    .stButton > button[kind="secondary"] p {
        background: white !important;
        color: var(--ink) !important;
        border: 1px solid var(--border-strong) !important;
        box-shadow: var(--shadow) !important;
    }
    .stDownloadButton > button,
    .stDownloadButton > button > div,
    .stDownloadButton > button p {
        background: white !important;
        color: var(--ink) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 11px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1rem !important;
        transition: border-color .15s ease, box-shadow .15s ease, transform .12s ease;
    }
    .stDownloadButton > button:hover {
        border-color: var(--primary) !important;
        box-shadow: 0 4px 14px rgba(99,102,241,.18);
        transform: translateY(-1px);
    }

    /* File uploader — premium dropzone */
    [data-testid="stFileUploader"] section {
        background: linear-gradient(180deg, #fbfaff 0%, #f5f3ff 100%);
        border: 1.5px dashed rgba(99,102,241,.30) !important;
        border-radius: 14px;
        transition: background .2s ease, border-color .2s ease, box-shadow .2s ease;
    }
    [data-testid="stFileUploader"] section:hover {
        background: linear-gradient(180deg, #f5f3ff 0%, #ede9fe 100%);
        border-color: rgba(99,102,241,.60) !important;
        box-shadow: inset 0 0 0 1px rgba(99,102,241,.12);
    }

    /* Number input */
    [data-testid="stNumberInput"] input {
        border-radius: 10px !important;
        border: 1px solid var(--border-strong) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
    }

    /* Section chip */
    .chip-row { display: flex; gap: .4rem; flex-wrap: wrap; margin-top: .35rem; }
    .chip {
        font-size: 0.72rem; font-weight: 600;
        background: var(--soft); color: var(--muted);
        border: 1px solid var(--border);
        border-radius: 999px; padding: 3px 10px;
    }
    .chip-accent { background: rgba(99,102,241,.10); color: var(--primary-dark); border-color: rgba(99,102,241,.25); }

    /* ML-only consent card (banner that sits above the Run button) */
    .consent-card {
        background: linear-gradient(135deg, #f5f3ff 0%, #fdf4ff 60%, #fef3c7 100%);
        border: 1px solid rgba(168, 85, 247, 0.22);
        border-radius: 14px;
        padding: 0.85rem 1rem;
        margin: .55rem 0 .65rem 0;
        box-shadow: 0 1px 2px rgba(168,85,247,.05), 0 8px 20px rgba(168,85,247,.07);
    }
    .consent-card-title {
        display: flex; align-items: center; gap: .5rem;
        font-weight: 700; font-size: .98rem; color: #4c1d95;
        margin-bottom: .25rem;
    }
    .consent-icon { font-size: 1.05rem; line-height: 1; }
    .consent-card-body {
        font-size: 0.85rem; line-height: 1.5;
        color: #4c1d95; opacity: 0.88;
    }

    .consent-note {
        background: linear-gradient(180deg, #f5f3ff 0%, #fdf4ff 100%);
        border: 1px solid rgba(168,85,247,.18);
        color: #4c1d95;
        border-radius: 12px;
        padding: .65rem .85rem;
        font-size: 0.85rem;
        margin-top: .55rem;
        line-height: 1.45;
    }
    .consent-note strong { color: #312e81; }

    /* Sidebar brand + status panel */
    .sidebar-brand { margin: 0 0 0.3rem 0; }
    .brand-mark {
        display: flex; align-items: center; gap: .55rem;
        font-weight: 800; font-size: 1.22rem; color: var(--ink);
        letter-spacing: -0.018em;
    }
    .brand-logo {
        display: inline-flex; align-items: center; justify-content: center;
        width: 30px; height: 30px; border-radius: 9px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white; font-size: 1.05rem;
        box-shadow: 0 1px 3px rgba(79,70,229,.30), 0 4px 10px rgba(79,70,229,.18);
        flex-shrink: 0;
    }
    .brand-name {
        background: linear-gradient(90deg, #1e1b4b 0%, #6d28d9 100%);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .brand-tagline {
        color: var(--muted); font-size: .78rem; font-weight: 500;
        margin: .25rem 0 0 0;
    }
    .brand-version {
        display: inline-block;
        font-family: 'JetBrains Mono', ui-monospace, monospace;
        font-size: 0.62rem;
        color: var(--primary-dark);
        background: rgba(99,102,241,.10);
        border: 1px solid rgba(99,102,241,.22);
        border-radius: 999px;
        padding: 1px 7px;
        letter-spacing: 0.04em;
        margin-left: auto;        /* push to the right within .brand-mark */
        align-self: center;
        line-height: 1.5;
    }

    .sidebar-status {
        margin: .25rem 0 .75rem 0;
        padding: .55rem .65rem;
        border: 1px solid var(--border);
        border-radius: 11px;
        background: rgba(248, 250, 252, 0.65);
    }
    .status-row {
        display: flex; align-items: flex-start; gap: .5rem;
        padding: .25rem 0;
    }
    .status-dot {
        width: 8px; height: 8px; border-radius: 50%;
        margin-top: 5px; flex-shrink: 0;
    }
    .status-dot.ok {
        background: #22c55e;
        box-shadow: 0 0 6px rgba(34,197,94,.55);
    }
    .status-dot.warn {
        background: #f97316;
        box-shadow: 0 0 6px rgba(249,115,22,.55);
    }
    .status-text { flex: 1; min-width: 0; }
    .status-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.66rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    .status-value {
        font-size: 0.78rem;
        color: var(--ink);
        font-weight: 600;
        word-break: break-all;
    }

    .sidebar-footer {
        margin-top: 1rem;
        padding-top: .1rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: var(--muted);
        opacity: 0.85;
        text-align: center;
    }
    .sidebar-footer a {
        color: var(--primary-dark);
        text-decoration: none;
        font-weight: 600;
    }
    .sidebar-footer a:hover { text-decoration: underline; }

    /* Partner logos (KAIST · APRIL Lab) — small, linked, neutral chips */
    .partner-logos {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin: 0.2rem 0 0.55rem 0;
    }
    .partner-logos a {
        display: inline-flex;
        align-items: center;
        opacity: 0.92;
        transition: opacity .15s ease, transform .15s ease;
    }
    .partner-logos a:hover { opacity: 1; transform: translateY(-1px); }
    .partner-logos img {
        height: 30px;
        width: auto;
        display: block;
    }
    /* Text fallback when no logo file is present */
    .partner-logo-text {
        font-family: 'Inter', system-ui, sans-serif;
        font-weight: 800;
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        color: var(--ink);
        background: white;
        border: 1px solid var(--border-strong);
        border-radius: 8px;
        padding: 5px 10px;
        line-height: 1.1;
        text-decoration: none;
    }
    .partner-logo-text small {
        display: block;
        font-size: 0.58rem;
        font-weight: 600;
        color: var(--muted);
        letter-spacing: 0.08em;
    }

    /* Plotly chart card */
    [data-testid="stPlotlyChart"] {
        background: white;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.5rem;
        box-shadow: var(--shadow);
    }

    /* ── Sidebar layout + bottom-pin + screencast polish (modern) ─── */

    /* Sidebar becomes the positioning context for the absolutely-pinned
       footer below. No internal scroll — the widget stack lives in the
       reserved region above the footer (see padding-bottom). */
    section[data-testid="stSidebar"] {
        position: relative !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    /* Collapse the «« header band entirely — we never collapse the
       sidebar during the demo, and removing it frees ~30 px for the
       widget stack below. */
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
        padding: 0 !important;
        min-height: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    /* The padding-bottom here reserves space for the absolutely-positioned
       footer (≈ 120 px covers OAS Studio · APRIL Lab · PI · Dev block).
       padding-top pushes the brand/mode/expander stack downward. */
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        height: 100% !important;
        max-height: 100% !important;
        overflow: hidden !important;
        padding-top: 1.5rem !important;
        padding-bottom: 168px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        height: 100% !important;
        max-height: 100% !important;
        min-height: 0 !important;
        overflow: hidden !important;
        gap: 1.3rem !important;
    }
    /* Footer wrapper — ONLY the outer stElementContainer becomes absolute.
       The inner wrappers stay in normal flow so the text-align:center on
       .sidebar-footer actually centers the credits inside the full
       sidebar width. */
    section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-footer) {
        position: absolute !important;
        bottom: 2.75rem !important;
        left: 0 !important;
        right: 0 !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 0.75rem !important;
        z-index: 5 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-footer) [data-testid="stMarkdownContainer"] {
        width: 100% !important;
    }
    .sidebar-footer {
        display: block !important;
        width: 100% !important;
    }

    /* Soft, modern separator — fades out at both edges, replaces the
       solid hr line that read as harsh against the surrounding widgets. */
    section[data-testid="stSidebar"] hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(15,23,42,0.10) 18%,
            rgba(15,23,42,0.10) 82%,
            transparent 100%) !important;
        margin: 1.2rem 0 !important;
        opacity: 1 !important;
    }

    /* Strip the default 1px border around the Advanced expander card so
       it reads as part of the sidebar flow rather than a separate panel. */
    section[data-testid="stSidebar"] [data-testid="stExpander"],
    section[data-testid="stSidebar"] [data-testid="stExpander"] details,
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderToggle"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    /* Slightly tighter rhythm between the four sliders inside the
       expander — keeps Streamlit's native slider look but recovers
       enough vertical space that everything still fits. */
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stSlider"] {
        margin-bottom: 0.3rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stCaptionContainer"] {
        margin-bottom: 0.45rem !important;
    }
    /* Fallback: if a user's display is short enough that the expander
       still won't fit, scroll inside the expander only — the rest of
       the sidebar stays untouched (no scrollbar on the sidebar itself). */
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"],
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderContent"],
    section[data-testid="stSidebar"] [data-testid="stExpander"] [role="region"] {
        max-height: calc(100vh - 380px) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }

    /* ML / cross-sections status box — modern spacing */
    .sidebar-status {
        margin: 0.35rem 0 !important;
        padding: 0.55rem 0.7rem !important;
    }
    .status-row { padding: 0.18rem 0 !important; }

    /* Method-picker radio — taller hit zones for clearer 1080p screencasts */
    .stRadio > div[role="radiogroup"] {
        gap: 0.4rem;
        flex-wrap: wrap;
    }
    .stRadio > div[role="radiogroup"] > label {
        padding: 0.3rem 0.7rem;
        border-radius: 9px;
        transition: background .15s ease;
    }
    .stRadio > div[role="radiogroup"] > label:hover {
        background: rgba(99,102,241,.06);
    }

    /* Consent banner — slightly stronger shadow so the click target reads
       at video distance during the Scene-5 pause */
    .consent-card {
        border-width: 1.5px;
        box-shadow:
            0 1px 2px rgba(168,85,247,.08),
            0 10px 24px rgba(168,85,247,.10);
    }
    .consent-card-title { font-size: 1.0rem; }

    /* Alert (success / info / warning) — premium padding + shadow */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        padding: 0.85rem 1rem !important;
        box-shadow:
            0 1px 2px rgba(15,23,42,.04),
            0 8px 24px rgba(15,23,42,.06) !important;
    }
    </style>
    """)


# ────────────────────────────────────────────────────────────────────────────
# Continual-learning submission config
# ────────────────────────────────────────────────────────────────────────────


def _get_cl_endpoint() -> tuple[str, str]:
    """Return (endpoint_url, anon_key) from Streamlit secrets, or ('','')."""
    try:
        cl = st.secrets.get("cl", {})
    except StreamlitSecretNotFoundError:
        cl = {}
    return (str(cl.get("endpoint", "")).strip(), str(cl.get("anon_key", "")).strip())


def _current_username() -> str:
    """Best-effort identifier: authenticated username if login is on, else 'anonymous'."""
    return str(st.session_state.get("username") or "anonymous")


# ────────────────────────────────────────────────────────────────────────────
# UI primitives
# ────────────────────────────────────────────────────────────────────────────


def _partner_logos_html() -> str:
    """Two small linked institutional logos (KAIST · APRIL Lab).

    Uses the bundled placeholder image when present; otherwise renders a
    text badge so the layout never breaks on a fresh checkout.
    """
    def _one(uri: str, url: str, label: str, sub: str) -> str:
        if uri:
            inner = f'<img src="{uri}" alt="{label}" />'
        else:
            inner = (
                f'<span class="partner-logo-text">{label}<small>{sub}</small></span>'
            )
        return (
            f'<a href="{url}" target="_blank" rel="noopener" title="{label}">'
            f'{inner}</a>'
        )

    return (
        '<div class="partner-logos">'
        + _one(KAIST_LOGO_URI, KAIST_URL, "KAIST", "kaist.ac.kr")
        + _one(APRIL_LOGO_URI, APRIL_URL, "APRIL", "LAB · KAIST")
        + "</div>"
    )


def render_partner_logos() -> None:
    html(_partner_logos_html())


def render_hero(title: str, subtitle: str, badge: str) -> None:
    html(f"""
    <div class="hero">
        <div class="hero-text">
            <span class="hero-pill">{badge}</span>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    </div>
    """)


def render_step(num: int, title: str) -> None:
    html(f"""
    <div class="step-head">
        <span class="step-num">{num}</span>
        <span class="step-title">{title}</span>
    </div>
    """)


def render_metric_row(metrics: dict[str, float]) -> None:
    cols = st.columns(4)
    cols[0].metric("R²", f"{metrics.get('r2', float('nan')):.4f}")
    cols[1].metric("RMSE", f"{metrics.get('rmse', float('nan')):.3e}")
    cols[2].metric("MAE", f"{metrics.get('mae', float('nan')):.3e}")
    cols[3].metric("MAPE", f"{metrics.get('mape', float('nan')):.2f}%")


def render_chemical_table(species: list[str], values: np.ndarray) -> None:
    detected = [bool(v > 0) for v in values]
    # Number densities routinely exceed JavaScript's Number.MAX_SAFE_INTEGER
    # (~9.007e15 — e.g. NO/NO2 at ~1e16+), and st.column_config.NumberColumn's
    # client-side "%.3e" formatter falls back to the raw integer for those.
    # Pre-format every value in Python and render as text so all rows show a
    # consistent scientific notation regardless of magnitude.
    frame = pd.DataFrame({
        "Species": species,
        "Detected": ["Yes" if d else "No" for d in detected],
        "Number density": [f"{float(v):.3e}" for v in values],
        "Unit": ["molec/cm³"] * len(species),
    })
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "Species": st.column_config.TextColumn("Species", width="small"),
            "Detected": st.column_config.TextColumn("Detected", width="small"),
            "Number density": st.column_config.TextColumn(
                "Number density (molec/cm³)",
            ),
            "Unit": st.column_config.TextColumn("Unit", width="small"),
        },
    )


def render_diagnostics(
    repeat_count: int | None = None,
    clip_applied: bool | None = None,
    hono_exceed: bool | None = None,
    excluded_species: list[str] | None = None,
) -> None:
    chips = []
    if repeat_count is not None:
        chips.append(f"<span class='chip'>Refit iterations: {repeat_count}</span>")
    if clip_applied is not None:
        chips.append(
            f"<span class='chip {'chip-accent' if clip_applied else ''}'>"
            f"Positive clip: {'on' if clip_applied else 'off'}</span>"
        )
    if hono_exceed is not None:
        chips.append(
            f"<span class='chip {'chip-accent' if hono_exceed else ''}'>"
            f"HONO exceed: {'yes' if hono_exceed else 'no'}</span>"
        )
    if excluded_species:
        chips.append(
            f"<span class='chip chip-accent'>Suppressed: {', '.join(excluded_species)}</span>"
        )
    if chips:
        html(f"<div class='chip-row'>{''.join(chips)}</div>")


# ────────────────────────────────────────────────────────────────────────────
# Sidebar
# ────────────────────────────────────────────────────────────────────────────


# Factory defaults for the four advanced sliders, keyed by their session_state
# key. The sliders are created WITHOUT a `value=` argument and read their value
# straight from session_state — so the reset callback only has to write these
# back. (The older "pass value= + pop the key" trick reliably resets state but
# does not always re-sync the slider thumb in a live browser, which is the bug
# this replaces.)
_FIT_CONFIG_DEFAULTS: dict[str, float | int] = {
    "cfg_min_fit_fraction": float(DEFAULT_MIN_FIT_FRACTION),
    "cfg_od_avg_coeff": float(DEFAULT_OD_AVG_COEFF),
    "cfg_od_clip_threshold": float(DEFAULT_OD_CLIP_THRESHOLD),
    "cfg_max_repeat": int(DEFAULT_MAX_REPEAT),
}


def _seed_fit_config_defaults() -> None:
    """Seed each slider's session_state key once, before the widgets render."""
    for key, value in _FIT_CONFIG_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def _reset_fit_config_defaults() -> None:
    """on_click callback: write the factory defaults back into session_state.

    Runs before the rerun that re-renders the sliders, so the widgets pick the
    default straight up — and because the value lives in session_state (not a
    `value=` arg) the thumb position updates too."""
    for key, value in _FIT_CONFIG_DEFAULTS.items():
        st.session_state[key] = value


def render_sidebar() -> tuple[str, FitConfig]:
    ml_ready = ML_DEFAULT_PTH.exists()
    with st.sidebar:
        html(f"""
        <div class="sidebar-brand">
            <div class="brand-mark">
                <span class="brand-logo">⚛</span>
                <span class="brand-name">OAS Studio</span>
                <span class="brand-version">v1.2</span>
            </div>
            <div class="brand-tagline">Optical Absorption Spectroscopy</div>
        </div>
        """)

        analysis_type = st.radio(
            "Analysis mode",
            options=["Single OAS analysis", "Time-series OAS analysis"],
            index=0,
            key="sidebar_analysis_type",
        )

        st.markdown("---")
        _seed_fit_config_defaults()
        with st.expander("Advanced fit configuration", expanded=False):
            st.caption(
                "Tune the heuristics that drive O₃ clipping and the iterative refit. "
                "These apply to the linear regression path."
            )
            min_fit_fraction = st.slider(
                "Min fit fraction", 0.0, 0.5, step=0.01,
                key="cfg_min_fit_fraction",
                help="Minimum ratio of fit points to total points. Below this, the fit returns zeros.",
            )
            od_avg_coeff = st.slider(
                "False-positive suppression coefficient", 0.5, 4.0, step=0.05,
                key="cfg_od_avg_coeff",
                help=("In the 350–370 nm window, drop a species column whose reconstructed average "
                      "exceeds this multiple of the total OD average."),
            )
            od_clip_threshold = st.slider(
                "OD clipping threshold", 0.05, 0.6, step=0.01,
                key="cfg_od_clip_threshold",
                help="Noise threshold for O₃ peak based positive clipping.",
            )
            max_repeat = st.slider(
                "Max refit iterations", 0, 10, step=1,
                key="cfg_max_repeat",
            )

            # Reset writes the factory defaults back into session_state (see
            # _reset_fit_config_defaults). The sliders read from session_state,
            # so both the values and the thumb positions revert on rerun.
            st.button(
                "↺  Reset to defaults",
                key="cfg_reset_btn",
                type="secondary",
                width="stretch",
                on_click=_reset_fit_config_defaults,
                help="Restore all four sliders above to their factory defaults.",
            )

        config = FitConfig(
            od_clip_threshold=float(od_clip_threshold),
            od_avg_coeff=float(od_avg_coeff),
            min_fit_fraction=float(min_fit_fraction),
            max_repeat=int(max_repeat),
        )

        st.markdown("---")
        html(f"""
        <div class="sidebar-status">
            <div class="status-row">
                <span class="status-dot {'ok' if ml_ready else 'warn'}"></span>
                <div class="status-text">
                    <div class="status-label">ML release</div>
                    <div class="status-value">{ML_RELEASE_ID} · <code>{ML_DEFAULT_PTH.name}</code></div>
                </div>
            </div>
            <div class="status-row">
                <span class="status-dot ok"></span>
                <div class="status-text">
                    <div class="status-label">Cross-sections</div>
                    <div class="status-value">Cross_sections_modified · auto-detected</div>
                </div>
            </div>
        </div>
        """)

        # Footer is rendered in its own html() call so it gets a dedicated
        # stElementContainer wrapper. CSS gives that wrapper margin-top:auto
        # inside the flex-column stVerticalBlock, pinning the credits to
        # the viewport bottom.
        html(f"""
        <div class="sidebar-footer">
            {_partner_logos_html()}
            <div><b>OAS Studio · 2026</b></div>
            <div style="margin-top:2px;">
                <a href="https://sites.google.com/view/plasmalab/" target="_blank" rel="noopener">APRIL Lab · KAIST</a>
                &nbsp;·&nbsp;
                <a href="https://github.com/jongchan1999/oas-spectrum-studio" target="_blank" rel="noopener">github ↗</a>
            </div>
            <div style="margin-top:3px; font-size:0.73rem; line-height:1.3;">
                PI <a href="mailto:sanghoopark@kaist.ac.kr">Sanghoo Park</a><br/>
                Dev <a href="mailto:kimjongchan@kaist.ac.kr">Jongchan Kim</a>
            </div>
        </div>
        """)

    return analysis_type, config


# ────────────────────────────────────────────────────────────────────────────
# Consent (shared — both analysis paths)
# ────────────────────────────────────────────────────────────────────────────


CONSENT_TEXT = (
    "I agree that my data will be used solely for the purpose of "
    "improving the model."
)


def _method_to_payload(method_label: str) -> str:
    """Map the human method label to the payload enum the backend expects."""
    return "machine_learning" if method_label == "Machine learning" else "linear_regression"


def render_consent_block(key: str) -> bool:
    """Consent gate shown for every analysis (single + time-series).

    Checking the box both unlocks the Run button and authorises persisting
    the raw spectra + analysis results to the global corpus on the next run.
    """
    html("""
    <div class="consent-card">
        <div class="consent-card-title">
            <span class="consent-icon">🌐</span>
            <span>Help improve the global model</span>
        </div>
        <div class="consent-card-body">
            When checked, your raw spectra (reference I₀ + measured Iₜ) and the
            analysis results (number densities, reconstruction metrics, and the
            fit settings used) are stored in the continual-learning corpus that
            trains the next model release. You must agree to run an analysis.
        </div>
    </div>
    """)
    return st.checkbox(
        CONSENT_TEXT,
        value=False,
        key=key,
        help="Required to run. Stores the raw spectra + results for model improvement.",
    )


# ────────────────────────────────────────────────────────────────────────────
# Run helpers (method-agnostic adapters)
# ────────────────────────────────────────────────────────────────────────────


def run_single_analysis(
    method: str,
    ref_bytes: bytes,
    meas_bytes: bytes,
    cross_dir: str,
    path_length_cm: float,
    config: FitConfig,
) -> dict:
    """Return a dict with the canonical result shape, regardless of method."""
    if method == "Linear regression":
        result = run_single_from_intensity_files(
            reference_file=ref_bytes,
            measured_file=meas_bytes,
            cross_section_dir=cross_dir,
            path_length_cm=path_length_cm,
            config=config,
        )
        return {
            "kind": "linear",
            "species": list(result.regression.species),
            "number_densities": np.asarray(result.regression.number_densities, dtype=float),
            "wavelengths": np.asarray(result.wavelengths, dtype=float),
            "measured": np.asarray(result.measured_od, dtype=float),
            "reconstructed": np.asarray(result.regression.reconstructed, dtype=float),
            "per_species_od": np.asarray(result.regression.per_species_od, dtype=float),
            "metrics": dict(result.regression.metrics),
            "diagnostics": {
                "repeat_count": int(result.regression.repeat_count),
                "clip_applied": bool(result.regression.clip_applied),
                "hono_exceed": bool(result.regression.hono_exceed),
                "excluded_species": list(result.regression.excluded_species),
            },
            "_native": result,
        }

    if not ML_DEFAULT_PTH.exists():
        raise FileNotFoundError("Default ML checkpoint missing at machine_learning/exp_4_epoch_3000.pth")

    ref_spectrum = load_spectrum(ref_bytes)
    meas_spectrum = load_spectrum(meas_bytes)
    optical_depth = compute_optical_depth_from_reference(
        reference_spectrum=ref_spectrum,
        measured_spectrum=meas_spectrum,
        wave_low=210.0,
        wave_high=400.0,
    )
    cross_data = load_cross_sections_from_dir(cross_dir)
    ml_result = run_ml_inference(
        absorbance=optical_depth,
        cross_sections=cross_data,
        model_file=ML_DEFAULT_PTH,
        exp_id=4,
        path_length_cm=path_length_cm,
    )
    return {
        "kind": "ml",
        "species": list(ml_result.species),
        "number_densities": np.asarray(ml_result.number_densities, dtype=float),
        "wavelengths": np.asarray(ml_result.wavelengths, dtype=float),
        "measured": np.asarray(ml_result.measured_absorbance, dtype=float),
        "reconstructed": np.asarray(ml_result.reconstructed, dtype=float),
        "per_species_od": np.asarray(ml_result.per_species_od, dtype=float),
        "metrics": dict(ml_result.metrics),
        "diagnostics": None,
        "_native": ml_result,
    }


def run_timeseries_analysis(
    method: str,
    file_items: list[tuple[str, bytes]],
    cross_dir: str,
    path_length_cm: float,
    config: FitConfig,
    progress_callback=None,
) -> dict:
    if method == "Linear regression":
        result = run_time_series_from_intensity_files(
            files=file_items,
            cross_section_dir=cross_dir,
            path_length_cm=path_length_cm,
            config=config,
            progress_callback=progress_callback,
        )
        return {
            "kind": "linear",
            "summary_table": result.summary_table,
            "labels": list(result.labels),
            "single_results": result.single_results,
            "_native": result,
        }

    if not ML_DEFAULT_PTH.exists():
        raise FileNotFoundError("Default ML checkpoint missing at machine_learning/exp_4_epoch_3000.pth")

    ts_ml = run_time_series_ml_from_intensity_files(
        files=file_items,
        cross_section_dir=cross_dir,
        model_file=ML_DEFAULT_PTH,
        exp_id=4,
        path_length_cm=path_length_cm,
        progress_callback=progress_callback,
    )
    return {
        "kind": "ml",
        "summary_table": ts_ml.summary_table,
        "labels": list(ts_ml.labels),
        "single_results": ts_ml.single_results,
        "_native": ts_ml,
    }


# ────────────────────────────────────────────────────────────────────────────
# Auto method selection (run both, keep the higher reconstruction R²)
# ────────────────────────────────────────────────────────────────────────────


def _r2_of(metrics: dict | None) -> float:
    """nan-safe reconstruction R² accessor; missing/non-finite → -inf."""
    if not metrics:
        return float("-inf")
    try:
        v = float(metrics.get("r2", float("nan")))
    except (TypeError, ValueError):
        return float("-inf")
    return v if np.isfinite(v) else float("-inf")


def run_single_analysis_auto(
    ref_bytes: bytes,
    meas_bytes: bytes,
    cross_dir: str,
    path_length_cm: float,
    config: FitConfig,
) -> dict:
    """Run both methods and return the payload with the higher reconstruction R².

    Linear regression always runs (it's the dependable baseline). The ML path
    runs only when a checkpoint is present and loads cleanly; any failure falls
    back to linear regression with a human-readable note.
    """
    lr = run_single_analysis(
        "Linear regression", ref_bytes, meas_bytes, cross_dir, path_length_cm, config
    )
    candidates: list[tuple[str, dict]] = [("Linear regression", lr)]
    ml_note: str | None = None

    if ML_DEFAULT_PTH.exists():
        try:
            ml = run_single_analysis(
                "Machine learning", ref_bytes, meas_bytes, cross_dir, path_length_cm, config
            )
            candidates.append(("Machine learning", ml))
        except Exception as exc:                              # noqa: BLE001
            ml_note = f"Machine-learning path failed to load ({exc}); used linear regression."
    else:
        ml_note = "No ML checkpoint found; used linear regression."

    best_name, best = max(candidates, key=lambda kv: _r2_of(kv[1]["metrics"]))
    best = dict(best)
    best["selected_method"] = best_name
    best["compared"] = {name: dict(p["metrics"]) for name, p in candidates}
    best["ml_note"] = ml_note
    return best


def _ts_mean_r2(ts_payload: dict) -> float:
    """Mean per-frame reconstruction R² across a time-series payload."""
    vals: list[float] = []
    for s in ts_payload["single_results"]:
        metrics = s.regression.metrics if ts_payload["kind"] == "linear" else s.metrics
        r2 = _r2_of(metrics)
        if np.isfinite(r2):
            vals.append(r2)
    return float(np.mean(vals)) if vals else float("-inf")


def run_timeseries_analysis_auto(
    file_items: list[tuple[str, bytes]],
    cross_dir: str,
    path_length_cm: float,
    config: FitConfig,
    progress_callback=None,
) -> dict:
    """Time-series analogue of run_single_analysis_auto.

    Compares the mean per-frame reconstruction R² of both methods and returns
    the winner. progress_callback receives (done, total, phase_label).
    """
    def _mk(phase: str):
        if progress_callback is None:
            return None
        def cb(done: int, total: int) -> None:
            progress_callback(done, total, phase)
        return cb

    lr = run_timeseries_analysis(
        "Linear regression", file_items, cross_dir, path_length_cm, config,
        progress_callback=_mk("Linear regression"),
    )
    candidates: list[tuple[str, dict, float]] = [
        ("Linear regression", lr, _ts_mean_r2(lr))
    ]
    ml_note: str | None = None

    if ML_DEFAULT_PTH.exists():
        try:
            ml = run_timeseries_analysis(
                "Machine learning", file_items, cross_dir, path_length_cm, config,
                progress_callback=_mk("Machine learning"),
            )
            candidates.append(("Machine learning", ml, _ts_mean_r2(ml)))
        except Exception as exc:                              # noqa: BLE001
            ml_note = f"Machine-learning path failed to load ({exc}); used linear regression."
    else:
        ml_note = "No ML checkpoint found; used linear regression."

    best_name, best, best_r2 = max(candidates, key=lambda t: t[2])
    best = dict(best)
    best["selected_method"] = best_name
    best["mean_r2"] = best_r2
    best["compared"] = {name: r2 for name, _, r2 in candidates}
    best["ml_note"] = ml_note
    return best


# ────────────────────────────────────────────────────────────────────────────
# Auto-persist to the global corpus (raw spectra + results) on analyse
# ────────────────────────────────────────────────────────────────────────────


def _suffix_key(name: str) -> float:
    import re
    match = re.search(r"(\d+(?:\.\d+)?)$", Path(name).stem)
    return float(match.group(1)) if match else float("inf")


def _autosubmit_single_to_db(
    *,
    result: dict,
    inputs: dict,
    ref_spectrum,
    meas_spectrum,
) -> dict:
    """POST one single-analysis sample (raw + results) to the corpus.

    Returns a status dict: {state: ok|error|unconfigured, id?, msg?}.
    """
    endpoint, anon_key = _get_cl_endpoint()
    if not endpoint or not anon_key:
        return {"state": "unconfigured"}

    payload_method = _method_to_payload(str(result.get("selected_method", "")))
    try:
        payload = build_submission_payload(
            method=payload_method,
            path_length_cm=float(inputs.get("path_length", 15.0)),
            user_id=_current_username(),
            reference_file=str(inputs.get("ref", "")),
            measured_file=str(inputs.get("meas", "")),
            wavelengths=result["wavelengths"],
            measured=result["measured"],
            reconstructed=result["reconstructed"],
            species=result["species"],
            number_densities=result["number_densities"],
            metrics=result["metrics"],
            fit_config=inputs.get("fit_config"),
            selected_method=payload_method,
            raw_reference=(ref_spectrum.wavelengths, ref_spectrum.values),
            raw_measured=(meas_spectrum.wavelengths, meas_spectrum.values),
        )
        sub_id = submit_to_global_model(payload, endpoint=endpoint, anon_key=anon_key)
        return {"state": "ok", "id": sub_id}
    except SubmissionError as exc:
        return {"state": "error", "msg": str(exc)}
    except Exception as exc:                                  # noqa: BLE001
        return {"state": "error", "msg": f"unexpected: {exc}"}


def _autosubmit_timeseries_to_db(
    *,
    ts_payload: dict,
    inputs: dict,
    file_items: list[tuple[str, bytes]],
    progress=None,
) -> dict:
    """POST every time-series frame (shared raw I₀ + that frame's raw Iₜ).

    Best-effort: individual frame failures are counted, not fatal. Returns
    {state: ok|partial|error|unconfigured, sent, total, msg?}.
    """
    endpoint, anon_key = _get_cl_endpoint()
    if not endpoint or not anon_key:
        return {"state": "unconfigured"}

    by_name = {name: data for name, data in file_items}
    # The reference (I₀) is the lowest numeric suffix; everything else is a frame.
    ref_name = min(by_name, key=_suffix_key)
    try:
        ref_spectrum = load_spectrum(by_name[ref_name])
    except Exception as exc:                                  # noqa: BLE001
        return {"state": "error", "msg": f"could not read reference: {exc}"}

    labels = ts_payload["labels"]
    singles = ts_payload["single_results"]
    is_linear = ts_payload["kind"] == "linear"
    payload_method = _method_to_payload(str(ts_payload.get("selected_method", "")))

    total = len(labels)
    sent = 0
    last_err: str | None = None
    for idx, (label, single) in enumerate(zip(labels, singles), start=1):
        raw_bytes = by_name.get(label)
        if raw_bytes is None:
            continue
        try:
            meas_spectrum = load_spectrum(raw_bytes)
            if is_linear:
                species = single.regression.species
                nd = single.regression.number_densities
                reconstructed = single.regression.reconstructed
                metrics = single.regression.metrics
                wavelengths = single.wavelengths
                measured = single.measured_od
            else:
                species = single.species
                nd = single.number_densities
                reconstructed = single.reconstructed
                metrics = single.metrics
                wavelengths = single.wavelengths
                measured = single.measured_absorbance

            payload = build_submission_payload(
                method=payload_method,
                path_length_cm=float(inputs.get("path_length", 15.0)),
                user_id=_current_username(),
                reference_file=str(ref_name),
                measured_file=str(label),
                wavelengths=wavelengths,
                measured=measured,
                reconstructed=reconstructed,
                species=species,
                number_densities=nd,
                metrics=metrics,
                fit_config=inputs.get("fit_config"),
                selected_method=payload_method,
                raw_reference=(ref_spectrum.wavelengths, ref_spectrum.values),
                raw_measured=(meas_spectrum.wavelengths, meas_spectrum.values),
            )
            submit_to_global_model(payload, endpoint=endpoint, anon_key=anon_key)
            sent += 1
        except Exception as exc:                              # noqa: BLE001
            last_err = str(exc)
        if progress is not None:
            progress(idx, total)

    if sent == total:
        return {"state": "ok", "sent": sent, "total": total}
    if sent > 0:
        return {"state": "partial", "sent": sent, "total": total, "msg": last_err}
    return {"state": "error", "sent": 0, "total": total, "msg": last_err}


def render_submit_status(status: dict | None) -> None:
    """Render the outcome of an automatic corpus submission."""
    if not status:
        return
    state = status.get("state")
    if state == "ok":
        if "id" in status:
            st.success(
                f"✓ Raw spectra + results saved to the global corpus. "
                f"Reference id: `{status['id']}`. Thank you for contributing!"
            )
        else:
            st.success(
                f"✓ Saved {status.get('sent', 0)}/{status.get('total', 0)} frames "
                f"(raw spectra + results) to the global corpus."
            )
    elif state == "partial":
        st.warning(
            f"Saved {status.get('sent', 0)}/{status.get('total', 0)} frames to the corpus; "
            f"the rest failed (last error: {status.get('msg', 'unknown')})."
        )
    elif state == "unconfigured":
        st.caption(
            "🌐 *Submission portal not configured for this deployment.* Your consent "
            "is recorded for this session; use the CSV downloads below as a local "
            "backup until the cloud endpoint is wired up."
        )
    elif state == "error":
        st.warning(
            f"Could not save to the global corpus: {status.get('msg', 'unknown error')}. "
            "Use the CSV downloads below as a local backup."
        )


# ────────────────────────────────────────────────────────────────────────────
# Single page
# ────────────────────────────────────────────────────────────────────────────


def render_single_page(selected_cross: str, config: FitConfig) -> None:
    render_hero(
        title="Single OAS analysis",
        subtitle=("Upload a single measured spectrum together with the reference I₀. "
                  "The app computes optical depth, estimates concentrations for 8 chemical "
                  "species, and validates the reconstruction."),
        badge="Single analysis",
    )

    # ── Input card ─────────────────────────────────────────────
    with st.container(border=True):
        render_step(1, "Spectrum inputs")

        col_a, col_b = st.columns(2)
        with col_a:
            ref_file = st.file_uploader(
                "Reference spectrum I₀  (lowest-suffix file)",
                type=["txt", "csv", "dat"],
                key="single_ref",
            )
        with col_b:
            meas_file = st.file_uploader(
                "Measured spectrum Iₜ  (target time file)",
                type=["txt", "csv", "dat"],
                key="single_meas",
            )

        path_length_cm = st.number_input(
            "Absorption path length (cm)",
            min_value=0.1, max_value=10000.0, value=15.0, step=0.1, format="%.2f",
            key="single_path_length",
        )

        cl_enabled = render_consent_block(key="single_cl_consent")

        run_clicked = st.button(
            "Run analysis", type="primary", key="single_run_btn",
            width="stretch", disabled=not cl_enabled,
        )
        if not cl_enabled:
            st.caption("Check the agreement above to enable analysis.")

        # Always show preview if both files are uploaded.
        if ref_file and meas_file:
            try:
                ref_spectrum = load_spectrum(ref_file.getvalue())
                meas_spectrum = load_spectrum(meas_file.getvalue())
                ref_on_meas = np.interp(
                    meas_spectrum.wavelengths,
                    ref_spectrum.wavelengths,
                    ref_spectrum.values,
                    left=np.nan, right=np.nan,
                )
                mask = np.isfinite(ref_on_meas) & np.isfinite(meas_spectrum.values)
                st.plotly_chart(
                    make_intensity_preview(
                        wavelengths=meas_spectrum.wavelengths[mask],
                        reference=ref_on_meas[mask],
                        measured=meas_spectrum.values[mask],
                        title="Uploaded spectra preview",
                    ),
                    width="stretch",
                )
            except Exception as exc:
                st.warning(f"Could not preview the spectra: {exc}")

    # ── Run handler ────────────────────────────────────────────
    if run_clicked:
        if ref_file is None or meas_file is None:
            st.error("Both I₀ and Iₜ files are required before running.")
        elif not cl_enabled:
            st.error("You must agree to the data-use statement before running.")
        else:
            try:
                with st.spinner("Running both methods and selecting the better reconstruction…"):
                    result_payload = run_single_analysis_auto(
                        ref_bytes=ref_file.getvalue(),
                        meas_bytes=meas_file.getvalue(),
                        cross_dir=selected_cross,
                        path_length_cm=float(path_length_cm),
                        config=config,
                    )
                inputs = {
                    "ref": ref_file.name,
                    "meas": meas_file.name,
                    "path_length": float(path_length_cm),
                    "selected_method": result_payload["selected_method"],
                    "cl_consent": True,
                    "fit_config": {
                        "od_clip_threshold": float(config.od_clip_threshold),
                        "od_avg_coeff": float(config.od_avg_coeff),
                        "min_fit_fraction": float(config.min_fit_fraction),
                        "max_repeat": float(config.max_repeat),
                    },
                }
                st.session_state["single_result"] = result_payload
                st.session_state["single_inputs"] = inputs
                # Consent given → persist raw spectra + results to the corpus.
                with st.spinner("Saving raw spectra + results to the global corpus…"):
                    status = _autosubmit_single_to_db(
                        result=result_payload,
                        inputs=inputs,
                        ref_spectrum=load_spectrum(ref_file.getvalue()),
                        meas_spectrum=load_spectrum(meas_file.getvalue()),
                    )
                st.session_state["single_submit_status"] = status
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.session_state.pop("single_result", None)
                st.session_state.pop("single_submit_status", None)

    # ── Result card ────────────────────────────────────────────
    result = st.session_state.get("single_result")
    inputs = st.session_state.get("single_inputs", {})
    with st.container(border=True):
        render_step(2, "Results")
        if result is None:
            st.info("📊  Results appear here once an analysis run completes.")
            return

        # Accuracy is the headline; the method that produced it is a footnote.
        render_metric_row(result["metrics"])

        selected = str(result.get("selected_method", inputs.get("selected_method", "")))
        compared = result.get("compared", {})
        if len(compared) > 1:
            bits = " · ".join(
                f"{name.split()[0]} R²={_r2_of(m):.4f}" for name, m in compared.items()
            )
            st.caption(
                f"🔬 Method auto-selected by reconstruction R²: **{selected}** "
                f"(compared {bits})."
            )
        else:
            st.caption(f"🔬 Method: **{selected}**.")
        if result.get("ml_note"):
            st.caption(f"ℹ️ {result['ml_note']}")

        render_submit_status(st.session_state.get("single_submit_status"))

        tab_extract, tab_validate, tab_downloads = st.tabs(
            ["Chemical extraction", "Validation overlay", "Downloads"]
        )

        with tab_extract:
            c1, c2 = st.columns([1.05, 1.0])
            with c1:
                render_chemical_table(result["species"], result["number_densities"])
                if result["diagnostics"]:
                    render_diagnostics(**result["diagnostics"])
            with c2:
                st.plotly_chart(
                    make_species_bar(result["species"], result["number_densities"]),
                    width="stretch",
                )

        with tab_validate:
            per_species_frame = pd.DataFrame({"wavelength": result["wavelengths"]})
            for idx, name in enumerate(result["species"]):
                per_species_frame[name] = result["per_species_od"][:, idx]
            st.plotly_chart(
                make_overlay_figure(
                    wavelengths=result["wavelengths"],
                    measured=result["measured"],
                    reconstructed=result["reconstructed"],
                    species_frame=per_species_frame,
                    title="Measured vs reconstructed OD",
                ),
                width="stretch",
            )
            st.caption(
                "Solid traces: measured vs full reconstruction. "
                "Dashed traces: per-species contribution. Click a legend entry to toggle."
            )

        with tab_downloads:
            recon_frame = prepare_download_frame(
                wavelengths=result["wavelengths"],
                measured=result["measured"],
                reconstructed=result["reconstructed"],
                species=result["species"],
                per_species_od=result["per_species_od"],
            )
            st.download_button(
                "Download reconstruction (CSV)",
                data=recon_frame.to_csv(index=False).encode("utf-8"),
                file_name="oas_reconstruction.csv",
                mime="text/csv",
                width="stretch",
            )
            # The run already pushed raw spectra + results to the corpus (or
            # noted that the portal is unconfigured). Offer the CL sample as a
            # local backup regardless of which method won.
            if result["kind"] == "ml":
                native = result["_native"]
                cl_frame = build_continual_learning_frame_ml_single(
                    ml_result=native,
                    wavelengths=native.wavelengths,
                    measured_absorbance=native.measured_absorbance,
                    path_length_cm=float(inputs.get("path_length", 15.0)),
                    reference_file=str(inputs.get("ref", "")),
                    measured_file=str(inputs.get("meas", "")),
                )
                cl_name = "oas_cl_sample_ml.csv"
            else:
                cl_frame = build_continual_learning_frame_single(
                    result=result["_native"],
                    path_length_cm=float(inputs.get("path_length", 15.0)),
                    reference_file=str(inputs.get("ref", "")),
                    measured_file=str(inputs.get("meas", "")),
                )
                cl_name = "oas_cl_sample_linear.csv"
            st.download_button(
                "Download continual-learning sample (CSV, local backup)",
                data=cl_frame.to_csv(index=False).encode("utf-8"),
                file_name=cl_name,
                mime="text/csv",
                width="stretch",
            )


# ────────────────────────────────────────────────────────────────────────────
# Time-series page
# ────────────────────────────────────────────────────────────────────────────


def render_timeseries_page(selected_cross: str, config: FitConfig) -> None:
    render_hero(
        title="Time-series OAS analysis",
        subtitle=("Upload a sequence of measured spectra. The file with the lowest numeric "
                  "suffix is treated as I₀, and the rest are processed in order. Observe the "
                  "species trends in real time and download the final summary."),
        badge="Time-series analysis",
    )

    with st.container(border=True):
        render_step(1, "Time-series inputs")

        uploads = st.file_uploader(
            "Upload spectra (I₀ and subsequent timepoints)",
            type=["csv", "txt", "dat"],
            accept_multiple_files=True,
            key="ts_uploads",
        )

        path_length_cm = st.number_input(
            "Absorption path length (cm)",
            min_value=0.1, max_value=10000.0, value=15.0, step=0.1, format="%.2f",
            key="ts_path_length",
        )

        cl_enabled = render_consent_block(key="ts_cl_consent")

        run_clicked = st.button(
            "Run analysis", type="primary", key="ts_run_btn",
            width="stretch", disabled=not cl_enabled,
        )
        if not cl_enabled:
            st.caption("Check the agreement above to enable analysis.")

        if uploads:
            st.caption(f"📁 {len(uploads)} files loaded.")

    if run_clicked:
        if not uploads or len(uploads) < 2:
            st.error("Upload at least two files (I₀ + one measurement).")
        elif not cl_enabled:
            st.error("You must agree to the data-use statement before running.")
        else:
            file_items = [(u.name, u.getvalue()) for u in uploads]
            progress = st.progress(0.0, text="Processing time-series…")

            def _on_step(done: int, total: int, phase: str = "") -> None:
                ratio = done / max(total, 1)
                label = f"{phase} pass" if phase else "Processing"
                progress.progress(ratio, text=f"{label}… {done}/{total}")

            try:
                with st.spinner(f"Running both methods on {len(file_items)} frames…"):
                    ts_payload = run_timeseries_analysis_auto(
                        file_items=file_items,
                        cross_dir=selected_cross,
                        path_length_cm=float(path_length_cm),
                        config=config,
                        progress_callback=_on_step,
                    )
                progress.empty()
                ts_inputs = {
                    "path_length": float(path_length_cm),
                    "selected_method": ts_payload["selected_method"],
                    "cl_consent": True,
                    "fit_config": {
                        "od_clip_threshold": float(config.od_clip_threshold),
                        "od_avg_coeff": float(config.od_avg_coeff),
                        "min_fit_fraction": float(config.min_fit_fraction),
                        "max_repeat": float(config.max_repeat),
                    },
                }
                st.session_state["ts_result"] = ts_payload
                st.session_state["ts_inputs"] = ts_inputs

                # Consent given → persist every frame's raw spectra + results.
                save_progress = st.progress(0.0, text="Saving frames to the global corpus…")

                def _on_save(done: int, total: int) -> None:
                    save_progress.progress(
                        done / max(total, 1),
                        text=f"Saving frames to the global corpus… {done}/{total}",
                    )

                submit_status = _autosubmit_timeseries_to_db(
                    ts_payload=ts_payload,
                    inputs=ts_inputs,
                    file_items=file_items,
                    progress=_on_save,
                )
                save_progress.empty()
                st.session_state["ts_submit_status"] = submit_status
            except Exception as exc:
                progress.empty()
                st.error(f"Time-series analysis failed: {exc}")
                st.session_state.pop("ts_result", None)
                st.session_state.pop("ts_submit_status", None)

    ts_payload = st.session_state.get("ts_result")
    ts_inputs = st.session_state.get("ts_inputs", {})
    with st.container(border=True):
        render_step(2, "Results")
        if ts_payload is None:
            st.info("📈  Run the analysis to see the trend, summary, and per-frame validation.")
            return
        summary_table = ts_payload["summary_table"]
        labels = ts_payload["labels"]
        species_cols = [c for c in summary_table.columns if c != "Time (s)"]
        detected = [sp for sp in species_cols if summary_table[sp].astype(float).abs().sum() > 0]

        if "Time (s)" in summary_table.columns and len(summary_table) > 0:
            time_axis = summary_table["Time (s)"].astype(float)
            duration_s = float(time_axis.max() - time_axis.min())
        else:
            duration_s = 0.0

        mean_r2 = float(ts_payload.get("mean_r2", float("nan")))
        mcols = st.columns(4)
        mcols[0].metric("Timepoints", len(summary_table))
        mcols[1].metric("Detected species", f"{len(detected)} / {len(species_cols)}")
        mcols[2].metric("Duration", f"{duration_s:.0f} s")
        mcols[3].metric("Mean R²", f"{mean_r2:.4f}" if np.isfinite(mean_r2) else "—")

        # Accuracy headline above; method is a small caption only.
        selected = str(ts_payload.get("selected_method", ts_inputs.get("selected_method", "")))
        compared = ts_payload.get("compared", {})
        if len(compared) > 1:
            bits = " · ".join(
                f"{name.split()[0]} mean R²={r2:.4f}" for name, r2 in compared.items()
            )
            st.caption(
                f"🔬 Method auto-selected by mean reconstruction R²: **{selected}** "
                f"(compared {bits})."
            )
        else:
            st.caption(f"🔬 Method: **{selected}**.")
        if ts_payload.get("ml_note"):
            st.caption(f"ℹ️ {ts_payload['ml_note']}")

        render_submit_status(st.session_state.get("ts_submit_status"))

        tab_trend, tab_summary, tab_validate, tab_downloads = st.tabs(
            ["Trend", "Summary table", "Per-frame validation", "Downloads"]
        )

        with tab_trend:
            st.plotly_chart(make_timeseries_trend(summary_table), width="stretch")
            st.caption("Y-axis is log-scaled. Zero values are hidden by Plotly; this is expected.")

        with tab_summary:
            display_table = summary_table.copy()
            for col in species_cols:
                display_table[col] = display_table[col].map(lambda v: f"{v:.3e}")
            st.dataframe(display_table, width="stretch", hide_index=True, height=380)

        with tab_validate:
            if not labels:
                st.info("No timepoints to validate.")
            else:
                sel = st.selectbox(
                    "Pick a timepoint",
                    options=list(range(len(labels))),
                    format_func=lambda i: labels[i],
                    key="ts_validation_sel",
                )
                if ts_payload["kind"] == "linear":
                    s = ts_payload["single_results"][sel]
                    wavelengths = s.wavelengths
                    measured = s.measured_od
                    reconstructed = s.regression.reconstructed
                    metrics = s.regression.metrics
                    per_species_od = s.regression.per_species_od
                    species = s.regression.species
                    diag = {
                        "repeat_count": s.regression.repeat_count,
                        "clip_applied": s.regression.clip_applied,
                        "hono_exceed": s.regression.hono_exceed,
                        "excluded_species": s.regression.excluded_species,
                    }
                else:
                    m = ts_payload["single_results"][sel]
                    wavelengths = m.wavelengths
                    measured = m.measured_absorbance
                    reconstructed = m.reconstructed
                    metrics = m.metrics
                    per_species_od = m.per_species_od
                    species = m.species
                    diag = None

                render_metric_row(metrics)
                per_species_frame = pd.DataFrame({"wavelength": wavelengths})
                for idx, name in enumerate(species):
                    per_species_frame[name] = per_species_od[:, idx]
                st.plotly_chart(
                    make_overlay_figure(
                        wavelengths=wavelengths,
                        measured=measured,
                        reconstructed=reconstructed,
                        species_frame=per_species_frame,
                        title=f"Validation · {labels[sel]}",
                    ),
                    width="stretch",
                )
                if diag:
                    render_diagnostics(**diag)

        with tab_downloads:
            st.download_button(
                "Download summary (CSV)",
                data=summary_table.to_csv(index=False).encode("utf-8"),
                file_name="time_series_oas_summary.csv",
                mime="text/csv",
                width="stretch",
            )
            if ts_inputs.get("cl_consent"):
                if ts_payload["kind"] == "linear":
                    cl_frame = build_continual_learning_frame_timeseries(
                        result=ts_payload["_native"],
                        path_length_cm=float(ts_inputs.get("path_length", 15.0)),
                    )
                    cl_name = "ts_cl_dataset_linear.csv"
                else:
                    cl_frame = build_continual_learning_frame_ml_timeseries(
                        ts_result=ts_payload["_native"],
                        path_length_cm=float(ts_inputs.get("path_length", 15.0)),
                    )
                    cl_name = "ts_cl_dataset_ml.csv"
                if isinstance(cl_frame, pd.DataFrame) and not cl_frame.empty:
                    st.download_button(
                        "Download continual-learning dataset (CSV)",
                        data=cl_frame.to_csv(index=False).encode("utf-8"),
                        file_name=cl_name,
                        mime="text/csv",
                        width="stretch",
                    )
                else:
                    st.info("Continual-learning dataset is empty.")
            else:
                st.caption("Enable the *continual-learning* checkbox above to unlock the CL export.")


# ────────────────────────────────────────────────────────────────────────────
# Auth
# ────────────────────────────────────────────────────────────────────────────


def require_login_if_enabled() -> None:
    try:
        auth = st.secrets.get("auth", {})
    except StreamlitSecretNotFoundError:
        auth = {}
    if not bool(auth.get("enabled", False)):
        return

    if st.session_state.get("authenticated", False):
        # Sign-out button intentionally hidden — kept off the sidebar so
        # the demo screencast doesn't expose the auth control. To sign
        # out, close the browser tab or clear the session.
        return

    render_hero(
        title="Sign in to OAS Studio",
        subtitle="This deployment is access-controlled. Enter your credentials to continue.",
        badge="Protected access",
    )

    users = auth.get("users", None)
    single_username = str(auth.get("username", "")).strip()
    single_password = str(auth.get("password", ""))

    allowed_users: dict[str, str] = {}
    if users is not None:
        from collections.abc import Mapping
        try:
            if isinstance(users, Mapping):
                allowed_users = {str(u).strip(): str(p) for u, p in users.items()}
            else:
                try:
                    allowed_users = {str(u).strip(): str(p) for u, p in users.items()}  # type: ignore[attr-defined]
                except Exception:
                    allowed_users = {}
        except Exception:
            allowed_users = {}
    if not allowed_users and single_username and single_password:
        allowed_users = {single_username: single_password}
    if not allowed_users:
        st.error("Authentication is enabled, but no credentials are configured in `secrets.toml`.")
        st.stop()

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submitted:
        ok = any(
            hmac.compare_digest(str(username).strip(), au)
            and hmac.compare_digest(str(password), ap)
            for au, ap in allowed_users.items()
        )
        if ok:
            st.session_state["authenticated"] = True
            st.session_state["username"] = str(username).strip()
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────


def main() -> None:
    inject_styles()
    require_login_if_enabled()

    analysis_type, config = render_sidebar()

    selected_cross = discover_preferred_cross_section_dir(str(ROOT))
    if selected_cross is None:
        render_hero(
            title="Cross-section data missing",
            subtitle="The expected `Cross_sections_modified` folder with 8 species was not found.",
            badge="Configuration error",
        )
        st.error(
            "Place the following files under `Cross_sections_modified/` and reload:\n\n"
            "- HONO_ordered_cross_section.txt\n"
            "- HONO2_ordered_cross_section.txt\n"
            "- N2O4_ordered_cross_section.txt\n"
            "- N2O5_ordered_cross_section.txt\n"
            "- NO_ordered_cross_section.txt\n"
            "- NO2_ordered_cross_section.txt\n"
            "- NO3_ordered_cross_section.txt\n"
            "- O3_ordered_cross_section.txt"
        )
        return

    if analysis_type == "Single OAS analysis":
        render_single_page(selected_cross=str(selected_cross), config=config)
    else:
        render_timeseries_page(selected_cross=str(selected_cross), config=config)


if __name__ == "__main__":
    main()
