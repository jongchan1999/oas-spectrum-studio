# OAS Spectrum Studio

A Streamlit web app for **Optical Absorption Spectroscopy (OAS)** analysis. It
extracts chemical species number densities from a measured absorbance spectrum
and validates the result against a reconstructed spectrum. Built as the
analysis front-end for a continual-learning OAS model.

## Features

- **Single spectrum analysis** — upload I₀ + It, get species number densities,
  reconstruction overlay, residual heatmap, and metric summary.
- **Time-series analysis** — upload a folder of spectra, get a number-density
  trend, per-frame validation, and bulk downloads.
- **Two fitting methods, identical UI** — positive NNLS linear regression
  (with O₃ peak clipping and iterative false-positive suppression) or a
  ResNet101 CNN. Selectable per-page; the result panels stay the same so you
  can compare side by side.
- **Tunable heuristics** — clip threshold, false-positive coefficient, min fit
  fraction, max refit iterations all exposed in the sidebar.
- **Continual-learning exports** — opt-in CSV bundles. ML mode shows an
  explicit consent line ("contribute to global model improvement").
- **Optional login gate** — Streamlit secrets allow-list.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>.

### Runtime assets

For the app to function, you need two things present locally:

1. `machine_learning/exp_4_epoch_3000.pth` — the ResNet101 checkpoint
   (≈ 170 MB). Excluded from git because it exceeds GitHub's per-file limit.
   Place it manually or fetch it from your release storage at deploy time.
2. `260429/260429_analysis_OAS/Cross_sections_modified/*_ordered_cross_section.txt`
   — the 8 species cross-section files. These are small text files and are
   tracked in git.

## Expected file formats

### Spectrum input

Two columns, whitespace/comma/tab separated. SpectraSuite headers are
recognised automatically:

```text
wavelength_nm intensity
210.00 0.0123
210.50 0.0131
...
```

For time-series, the file with the **lowest numeric suffix** is treated as I₀
(e.g. `Source_70_2_00000.txt`).

### Cross-section data

Required species: `HONO`, `HONO2`, `N2O4`, `N2O5`, `NO`, `NO2`, `NO3`, `O3`.
Filename pattern: `{SPECIES}_ordered_cross_section.txt`.

## Deployment

### Option A — Streamlit Community Cloud (fastest)

1. Push this repo to GitHub.
2. On Streamlit Cloud, point to `app.py`.
3. Upload `exp_4_epoch_3000.pth` to a release/object-storage bucket, then
   either commit a small loader script that fetches it on startup, or use
   Git LFS (`git lfs track "*.pth"`).
4. In *App settings → Secrets*, paste:

   ```toml
   [auth]
   enabled = true
   users = { "alice" = "pw1", "bob" = "pw2" }
   ```

   See [DEPLOYMENT_PRIVATE.md](DEPLOYMENT_PRIVATE.md).

### Option B — self-hosted with Cloudflare Tunnel + Access

Stronger network-level allow-list. See [DEPLOYMENT_PRIVATE.md](DEPLOYMENT_PRIVATE.md).

## Project layout

```text
app.py                          # Streamlit UI
oas_web/
  analysis.py                   # OD computation + NNLS + refit heuristics
  ml.py                         # ResNet101 CNN inference (single + time-series)
  plots.py                      # Plotly figure factories
machine_learning/
  exp_4_epoch_3000.pth          # ML checkpoint (gitignored)
  RegressionModel_linux.py      # reference training architecture
  train_linux.py / generate_linux.py / inference_window.py
assets/
  spectroscopy.png              # hero illustration
.streamlit/
  config.toml                   # theme
  secrets.toml.example          # auth template (real secrets are gitignored)
260429/
  260429_analysis_OAS/
    Cross_sections_modified/    # 8 species cross-section .txt files (tracked)
```
