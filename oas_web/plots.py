from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go


SPECIES_COLORS: dict[str, str] = {
    "O3": "#0ea5e9",
    "NO": "#22c55e",
    "NO2": "#eab308",
    "NO3": "#f97316",
    "HONO": "#a855f7",
    "HONO2": "#ec4899",
    "N2O4": "#14b8a6",
    "N2O5": "#ef4444",
}

PALETTE = list(SPECIES_COLORS.values())

PLOT_TEMPLATE = "plotly_white"
PRIMARY_COLOR = "#0f172a"
ACCENT_COLOR = "#f97316"


def _base_layout(title: str, height: int = 420) -> dict:
    return {
        "title": {
            "text": title,
            "font": {"family": "Inter, system-ui, -apple-system, sans-serif", "size": 16, "color": "#0f172a"},
            "x": 0.0,
            "xanchor": "left",
        },
        "template": PLOT_TEMPLATE,
        "height": height,
        "margin": {"l": 48, "r": 24, "t": 56, "b": 48},
        "font": {"family": "Inter, system-ui, -apple-system, sans-serif", "color": "#334155"},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
            "bgcolor": "rgba(255,255,255,0.6)",
            "bordercolor": "rgba(15,23,42,0.1)",
            "borderwidth": 1,
        },
        "hoverlabel": {"bgcolor": "white", "font": {"family": "Inter", "size": 12}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(248,250,252,0.6)",
    }


def make_overlay_figure(
    wavelengths: np.ndarray,
    measured: np.ndarray,
    reconstructed: np.ndarray,
    species_frame: pd.DataFrame | None = None,
    title: str = "Measured vs Reconstructed",
    log_y: bool = False,
) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=wavelengths,
            y=measured,
            mode="lines",
            name="Measured OD",
            line={"color": PRIMARY_COLOR, "width": 2.4},
            hovertemplate="<b>Measured</b><br>%{x:.2f} nm<br>%{y:.3e}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=wavelengths,
            y=reconstructed,
            mode="lines",
            name="Reconstructed OD",
            line={"color": ACCENT_COLOR, "width": 2.4, "dash": "solid"},
            hovertemplate="<b>Reconstructed</b><br>%{x:.2f} nm<br>%{y:.3e}<extra></extra>",
        )
    )
    if species_frame is not None and species_frame.shape[1] > 1:
        for column in species_frame.columns[1:]:
            color = SPECIES_COLORS.get(str(column), "#64748b")
            figure.add_trace(
                go.Scatter(
                    x=species_frame.iloc[:, 0],
                    y=species_frame[column],
                    mode="lines",
                    name=str(column),
                    line={"color": color, "width": 1.2, "dash": "dot"},
                    opacity=0.75,
                    visible="legendonly",
                )
            )

    layout = _base_layout(title)
    layout["xaxis_title"] = "Wavelength (nm)"
    layout["yaxis_title"] = "Optical depth"
    figure.update_layout(**layout)
    figure.update_xaxes(gridcolor="rgba(15,23,42,0.06)", zeroline=False)

    if log_y:
        figure.update_yaxes(type="log", gridcolor="rgba(15,23,42,0.06)", zeroline=False)
    else:
        figure.update_yaxes(
            type="linear",
            tickformat=".2e",
            gridcolor="rgba(15,23,42,0.06)",
            zeroline=False,
        )
    return figure


def make_reconstruction_heatmap(
    wavelengths: np.ndarray,
    measured: np.ndarray,
    reconstructed: np.ndarray,
) -> go.Figure:
    """Stack measured vs reconstructed as a 2-row heatmap for visual diff."""
    residual = np.asarray(reconstructed, dtype=float) - np.asarray(measured, dtype=float)
    z = np.vstack([measured, reconstructed, residual])
    figure = go.Figure(
        data=[
            go.Heatmap(
                z=z,
                x=wavelengths,
                y=["Measured", "Reconstructed", "Residual"],
                colorscale="Plasma",
                colorbar={"title": "OD", "thickness": 12, "tickfont": {"size": 11}},
                hovertemplate="%{y}<br>%{x:.2f} nm<br>%{z:.3e}<extra></extra>",
            )
        ]
    )
    layout = _base_layout("Spectral reconstruction map", height=240)
    layout["xaxis_title"] = "Wavelength (nm)"
    layout["yaxis_title"] = ""
    figure.update_layout(**layout)
    figure.update_yaxes(autorange="reversed")
    return figure


def make_species_bar(
    species: Iterable[str],
    values: Iterable[float],
    title: str = "Number density by species",
) -> go.Figure:
    species_list = [str(s) for s in species]
    value_list = [float(v) for v in values]
    colors = [SPECIES_COLORS.get(s, "#64748b") for s in species_list]
    figure = go.Figure(
        data=[
            go.Bar(
                x=species_list,
                y=value_list,
                marker={"color": colors, "line": {"color": "rgba(15,23,42,0.15)", "width": 1}},
                hovertemplate="<b>%{x}</b><br>%{y:.3e} molec/cm3<extra></extra>",
                text=[f"{v:.2e}" for v in value_list],
                textposition="outside",
                textfont={"family": "Inter", "size": 11, "color": "#475569"},
            )
        ]
    )
    layout = _base_layout(title, height=320)
    layout["xaxis_title"] = "Chemical species"
    layout["yaxis_title"] = "Number density (molec/cm³)"
    figure.update_layout(**layout)
    figure.update_yaxes(type="log", tickformat=".0e", gridcolor="rgba(15,23,42,0.06)")
    return figure


def make_intensity_preview(
    wavelengths: np.ndarray,
    reference: np.ndarray,
    measured: np.ndarray,
    title: str = "Reference vs Measured intensity",
) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=wavelengths,
            y=reference,
            mode="lines",
            name="Reference I₀",
            line={"color": "#dc2626", "width": 2.0},
            hovertemplate="<b>Reference</b><br>%{x:.2f} nm<br>%{y:.3e}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=wavelengths,
            y=measured,
            mode="lines",
            name="Measured It",
            line={"color": "#2563eb", "width": 2.0},
            hovertemplate="<b>Measured</b><br>%{x:.2f} nm<br>%{y:.3e}<extra></extra>",
        )
    )
    layout = _base_layout(title, height=320)
    layout["xaxis_title"] = "Wavelength (nm)"
    layout["yaxis_title"] = "Intensity"
    figure.update_layout(**layout)
    figure.update_yaxes(type="log", gridcolor="rgba(15,23,42,0.06)")
    figure.update_xaxes(gridcolor="rgba(15,23,42,0.06)")
    return figure


def make_timeseries_trend(
    summary_table: pd.DataFrame,
    title: str = "Number density over time",
) -> go.Figure:
    if "Time (s)" not in summary_table.columns:
        raise ValueError("summary_table must contain a 'Time (s)' column.")

    species_cols = [c for c in summary_table.columns if c != "Time (s)"]
    figure = go.Figure()
    for species in species_cols:
        color = SPECIES_COLORS.get(str(species), "#64748b")
        figure.add_trace(
            go.Scatter(
                x=summary_table["Time (s)"],
                y=summary_table[species],
                mode="lines+markers",
                name=str(species),
                line={"color": color, "width": 2.0},
                marker={"size": 5, "color": color, "line": {"color": "white", "width": 1}},
                hovertemplate=f"<b>{species}</b><br>t=%{{x:.1f}} s<br>%{{y:.3e}}<extra></extra>",
            )
        )

    layout = _base_layout(title, height=400)
    layout["xaxis_title"] = "Time (s)"
    layout["yaxis_title"] = "Number density (molec/cm³)"
    figure.update_layout(**layout)
    figure.update_yaxes(type="log", tickformat=".0e", gridcolor="rgba(15,23,42,0.06)")
    figure.update_xaxes(gridcolor="rgba(15,23,42,0.06)")
    return figure
