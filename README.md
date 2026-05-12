<div align="center">

  <a href="https://oas-spectrum-studio.streamlit.app">
    <img src="docs/conference/poster-thumbnail.svg" alt="OAS Studio — 3-minute walkthrough"
         width="720" />
  </a>

  <h1>OAS Spectrum Studio</h1>

  <p><strong>A single-screen analyser for Optical Absorption Spectroscopy,
  grown by the community.</strong></p>

  <p>
    <a href="https://oas-spectrum-studio.streamlit.app">
      <img alt="Live demo"
           src="https://img.shields.io/badge/live%20demo-streamlit-FF4B4B?logo=streamlit&logoColor=white" />
    </a>
    <a href="https://www.python.org/downloads/release/python-3110/">
      <img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-3776ab?logo=python&logoColor=white" />
    </a>
    <a href="LICENSE">
      <img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-22c55e" />
    </a>
    <a href="docs/CONTINUAL_LEARNING.md">
      <img alt="Continual learning" src="https://img.shields.io/badge/continual--learning-Phase%203-7c3aed" />
    </a>
  </p>

  <p>
    <a href="https://youtu.be/REPLACE_WITH_YT_ID"><b>▶ Watch the 3-minute demo</b></a>
    &nbsp;·&nbsp;
    <a href="https://oas-spectrum-studio.streamlit.app"><b>Try it live</b></a>
    &nbsp;·&nbsp;
    <a href="docs/DEMO_VIDEO_SCRIPT.md"><b>Behind the demo</b></a>
  </p>

</div>

---

## What is OAS Studio?

OAS Studio is a Streamlit web app that takes a measured optical absorption
spectrum, separates it into the contributions of eight chemical species
(HONO, HONO₂, N₂O₄, N₂O₅, NO, NO₂, NO₃, O₃), and gives back number
densities + a validation overlay in well under a second.

Two analysis paths share one UI:

- **Linear regression** — positive NNLS with O₃-peak clipping and iterative
  false-positive suppression. R² > 0.92 on the included reference series.
- **Machine learning** — a ResNet101 model that ingests the OD curve as an
  image. The shipped checkpoint is the simulation-trained baseline; opted-in
  user submissions feed the continual-learning loop that produces the next
  release.

Single-spectrum and time-series modes share the same input/output layout, so
swapping methods or scaling up to a 343-frame run requires no relearning.

## At a glance

| | |
|---|---|
| **Live app** | <https://oas-spectrum-studio.streamlit.app> |
| **Demo video** | `https://youtu.be/REPLACE_WITH_YT_ID` *(3 min, unlisted)* |
| **Tech** | Streamlit · scikit-learn · PyTorch (CPU) · Plotly · Supabase |
| **Continual learning** | App → Supabase Edge Function → curation worker (GitHub Action) → fine-tune (next release) |
| **Status** | Frontend + Phase 1 (submission) + Phase 2 (curation) live · Phase 3 (fine-tune) pending |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open <http://localhost:8501>. Two runtime assets must be present:

1. **`machine_learning/exp_4_epoch_3000.pth`** — the ResNet101 checkpoint
   (≈ 170 MB). Tracked via Git LFS, so it lands automatically after a
   `git lfs install && git clone`. If you cloned without LFS, fetch the
   actual blob with `git lfs pull`.
2. **`260429/260429_analysis_OAS/Cross_sections_modified/*_ordered_cross_section.txt`**
   — the 8 species cross-section files. Small text files, tracked normally.

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

For a time-series upload, the file with the **lowest numeric suffix** is
treated as I₀ (e.g. `Source_70_2_00000.txt`); the rest are processed in
ascending suffix order.

### Cross-section data

Required species: `HONO`, `HONO2`, `N2O4`, `N2O5`, `NO`, `NO2`, `NO3`, `O3`.
Filename pattern: `{SPECIES}_ordered_cross_section.txt`.

## Deployment

### Option A — Streamlit Community Cloud (recommended)

1. Fork / push this repo to GitHub.
2. In Streamlit Cloud, point a new app at `app.py`. Streamlit's runner
   pulls the .pth via LFS automatically.
3. *App settings → Secrets*: paste both blocks below (real values).

```toml
[auth]
enabled = true
users = { "alice" = "pw1", "bob" = "pw2" }

[cl]                                                # optional
endpoint = "https://<project-ref>.functions.supabase.co/submit"
anon_key = "eyJ..."
```

See [DEPLOYMENT_PRIVATE.md](DEPLOYMENT_PRIVATE.md) for the strict
network-layer alternative (Cloudflare Tunnel + Access).

### Option B — self-hosted

Standard `streamlit run app.py` behind any reverse proxy. The
[release checklist](docs/RELEASE_CHECKLIST.md) covers the rest.

## Continual learning

The opt-in continual-learning loop is documented end-to-end in
[`docs/CONTINUAL_LEARNING.md`](docs/CONTINUAL_LEARNING.md).

Components:

| Phase | Path | Status |
|---|---|---|
| 1. Submission endpoint | [`supabase/`](supabase/) (`schema.sql` + `functions/submit/`) + [`oas_web/cl_submit.py`](oas_web/cl_submit.py) | ✅ Live |
| 2. Curation worker | [`scripts/curate.py`](scripts/curate.py) + [`.github/workflows/curate.yml`](.github/workflows/curate.yml) | ✅ Shipped |
| 3. Fine-tune + eval | [`machine_learning/finetune.py`](machine_learning/finetune.py) + [`evaluate.py`](machine_learning/evaluate.py) + [`.github/workflows/finetune.yml`](.github/workflows/finetune.yml) | ✅ Shipped |

Set up your own Supabase project by following [`supabase/README.md`](supabase/README.md).

## Documentation

- 📹 [`docs/DEMO_VIDEO_SCRIPT.md`](docs/DEMO_VIDEO_SCRIPT.md) — shot-by-shot
  recording script (bilingual, ~3 min).
- 🧭 [`docs/STATUS.md`](docs/STATUS.md) — what's done, what's next.
- 🚀 [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — go-public
  punch list.
- 🎓 [`docs/conference/`](docs/conference/) — slide template + key visual
  for talks and posters.
- 🧪 [`docs/CONTINUAL_LEARNING.md`](docs/CONTINUAL_LEARNING.md) — backend
  architecture, paper-track addendum, release versioning.
- 🔒 [`DEPLOYMENT_PRIVATE.md`](DEPLOYMENT_PRIVATE.md) — private hosting
  options.

## Project layout

```text
app.py                          # Streamlit UI (1.4k LOC)
oas_web/
  analysis.py                   # OD computation + NNLS + refit heuristics
  ml.py                         # ResNet101 CNN inference (single + time-series)
  plots.py                      # Plotly figure factories with species palette
  cl_submit.py                  # Continual-learning submission client
  curation.py                   # Curation worker (validate / dedupe / pack)
scripts/
  curate.py                     # CLI for the curation worker
supabase/
  schema.sql                    # cl_submissions tables + RLS + GRANTs
  functions/submit/index.ts     # Edge function: validate → hash → store
machine_learning/
  exp_4_epoch_3000.pth          # ML checkpoint (LFS-tracked)
  RegressionModel_linux.py      # reference training architecture
  train_linux.py / generate_linux.py / inference_window.py
assets/
  spectroscopy.png              # hero illustration
.streamlit/
  config.toml                   # Streamlit theme
  secrets.toml.example          # auth + cl secrets template
260429/260429_analysis_OAS/
  Cross_sections_modified/      # 8 species cross-section text files
docs/                           # see "Documentation" above
.github/workflows/curate.yml    # weekly curation worker (workflow_dispatch)
```

## Citation

If you use this tool in a publication, please cite:

> Jongchan Kim. *OAS Spectrum Studio — a Streamlit-hosted analyser for
> optical absorption spectroscopy with a continual-learning loop.* 2026.
> Available at https://github.com/jongchan1999/oas-spectrum-studio

A formal BibTeX entry will appear once the paper is on arXiv.

## License

[MIT](LICENSE). See note in the licence file before you announce the
public link in a paper — confirm the choice with your PI / tech transfer
office.

---

<div align="center">
  <sub>Built by Jongchan Kim (KAIST plasma group) · 2026<br/>
  Want to contribute or request access?
  <a href="https://github.com/jongchan1999/oas-spectrum-studio/issues/new">Open an issue</a>
  or email the maintainer.</sub>
</div>
