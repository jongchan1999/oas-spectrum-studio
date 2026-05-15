<h1 align="center">OAS Spectrum Studio</h1>

<p align="center">
  <b>A single-screen analyser for Optical Absorption Spectroscopy, grown by the community.</b>
  <br/>
  <sub>Developed at the
  <a href="https://sites.google.com/view/plasmalab/"><b>APRIL Lab</b></a>
  (Applied Plasma Research &amp; Innovation Lab), <a href="https://www.kaist.ac.kr/">KAIST</a>.</sub>
</p>

<p align="center">
  <a href="https://oas-spectrum-studio.streamlit.app"><img alt="Live demo" src="https://img.shields.io/badge/live%20demo-streamlit-FF4B4B?logo=streamlit&logoColor=white"/></a>
  <a href="https://www.python.org/downloads/release/python-3110/"><img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-3776ab?logo=python&logoColor=white"/></a>
  <a href="LICENSE"><img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-22c55e"/></a>
  <a href="docs/CONTINUAL_LEARNING.md"><img alt="Continual learning" src="https://img.shields.io/badge/continual--learning-Phase%203-7c3aed"/></a>
</p>

<p align="center">
  <a href="https://oas-spectrum-studio.streamlit.app"><b>▶ Try it live</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/jongchan1999/oas-spectrum-studio/releases/download/v1.0/demo_under100mb.mp4"><b>Watch the demo</b></a>
  (3 min 36 s, MP4)
  &nbsp;·&nbsp;
  <a href="#citation"><b>Cite</b></a>
</p>

<br/>

<p align="center">
  <a href="https://oas-spectrum-studio.streamlit.app">
    <img src="docs/conference/poster-thumbnail.svg"
         alt="OAS Spectrum Studio — click to open the live web app"
         width="960" />
  </a>
</p>

<!-- Inline video — GitHub renders the native HTML5 player when the src is
     a user-attachments URL (the only host its README sanitiser whitelists). -->
<div align="center">
  <video src="https://github.com/jongchan1999/oas-spectrum-studio/releases/download/v1.0/demo_under100mb.mp4"
         controls width="100%"
         poster="docs/conference/poster-thumbnail.svg">
    Your browser does not support inline video —
    <a href="https://github.com/jongchan1999/oas-spectrum-studio/releases/download/v1.0/demo_under100mb.mp4">click here to watch / download the MP4</a>.
  </video>
</div>

---

## What it does

OAS Studio takes a measured optical absorption spectrum, separates it into
the contributions of eight chemical species (HONO, HONO₂, N₂O₄, N₂O₅, NO,
NO₂, NO₃, O₃), and returns calibrated number densities together with a
validation overlay — typically in under a second.

Two analysis paths share the same UI, and the same UI scales from a single
spectrum to a 343-frame time-series with no relearning:

| Path | Method | Best for |
|---|---|---|
| **Linear regression** | Positive NNLS + O₃-peak clipping + iterative false-positive suppression | Trusted labels, R² &gt; 0.92 on the reference series |
| **Machine learning** | ResNet-101 over the OD curve rendered as an image | Quick first-pass on novel spectra; opted-in submissions feed the next checkpoint |

Opt-in submissions flow into a Supabase-backed **continual-learning loop**
(see [`docs/CONTINUAL_LEARNING.md`](docs/CONTINUAL_LEARNING.md)).
Each release credits its contributors.

## Quick start

> This repository is private. Code access is by invite only; the live
> app is access-controlled with per-person credentials. See **[Get
> access](#get-access)** below before starting.

### Option 1 — use the live app

No install. Open <https://oas-spectrum-studio.streamlit.app>, sign in with
the credentials you received, and drag in your spectrum files.

### Option 2 — run locally (invited collaborators only)

```bash
git lfs install                              # one-time per machine
git clone https://github.com/jongchan1999/oas-spectrum-studio.git
cd oas-spectrum-studio
pip install -r requirements.txt
streamlit run app.py
```

Then open <http://localhost:8501>.

Two runtime assets must be present (both are pulled automatically by
`git clone` with LFS enabled):

1. **`machine_learning/exp_4_epoch_3000.pth`** — the baseline ResNet-101
   checkpoint (~170 MB, LFS-tracked).
2. **`Cross_sections_modified/*_ordered_cross_section.txt`** — the 8 species
   cross-section reference files. Plain text, tracked normally.

## Input format

A spectrum file is two columns (wavelength · intensity), whitespace / comma
/ tab separated. SpectraSuite headers are recognised automatically.

```text
wavelength_nm intensity
210.00 0.0123
210.50 0.0131
...
```

For a time-series upload, the file with the **lowest numeric suffix** is
treated as I₀ (for example `Source_70_2_00000.txt`); the rest are processed
in ascending suffix order.

## Continual learning loop

| Phase | What it does | Where |
|---|---|---|
| **1. Submit** | Authenticated app POSTs each opted-in analysis to a Supabase Edge Function | [`supabase/`](supabase/) + [`oas_web/cl_submit.py`](oas_web/cl_submit.py) |
| **2. Curate** | Weekly GitHub Action validates, dedupes, and packs new rows into a release pack | [`scripts/curate.py`](scripts/curate.py) + [`.github/workflows/curate.yml`](.github/workflows/curate.yml) |
| **3. Fine-tune** | Same workflow re-trains the ResNet on the growing corpus and gates promotion on per-species RMSE deltas | [`machine_learning/finetune.py`](machine_learning/finetune.py) + [`.github/workflows/finetune.yml`](.github/workflows/finetune.yml) |

End-to-end architecture, paper-track addendum, and release versioning are
documented in [`docs/CONTINUAL_LEARNING.md`](docs/CONTINUAL_LEARNING.md).

Spin up your own Supabase project by following
[`supabase/README.md`](supabase/README.md).

## Project layout

```text
app.py                          Streamlit UI (single page, ~1.5k LOC)
oas_web/
  analysis.py                   OD computation + NNLS + refit heuristics
  ml.py                         ResNet-101 inference (single + time-series)
  plots.py                      Plotly figure factories
  cl_submit.py                  Continual-learning submission client
  curation.py                   Curation worker (validate / dedupe / pack)
machine_learning/
  exp_4_epoch_3000.pth          Baseline checkpoint (LFS)
  finetune.py / evaluate.py     Phase-3 fine-tune + eval harness
  RegressionModel_linux.py      Reference training architecture
  train_linux.py /              Legacy training pipeline kept for transparency
  generate_linux.py /
  inference_window.py
scripts/
  curate.py                     CLI wrapper for the curation worker
  finetune.py                   CLI wrapper for the fine-tune job
  seed_submissions.py           Batch helper for seeding the corpus
supabase/
  schema.sql                    cl_submissions tables + RLS + GRANTs
  functions/submit/index.ts     Edge function — validate, hash, store
Cross_sections_modified/        8 species cross-section text files
assets/                         Hero illustration
docs/                           Continual-learning architecture, demo
                                video script, release checklist, status
                                notes, conference slide template
.github/workflows/              curate.yml (weekly) + finetune.yml (manual)
```

## Documentation

- 🧪 [`docs/CONTINUAL_LEARNING.md`](docs/CONTINUAL_LEARNING.md) — backend
  architecture, paper-track addendum, release versioning.
- 🧭 [`docs/STATUS.md`](docs/STATUS.md) — what's shipped, what's pending,
  how to resume.
- 🚀 [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — go-public
  punch list.
- 📹 [`docs/DEMO_VIDEO_SCRIPT.md`](docs/DEMO_VIDEO_SCRIPT.md) — shot-by-shot
  script for the walkthrough video.
- 🎓 [`docs/conference/`](docs/conference/) — slide / poster template +
  key visual.
- 🔒 [`DEPLOYMENT_PRIVATE.md`](DEPLOYMENT_PRIVATE.md) — private hosting
  (Cloudflare Tunnel + Access).

## Citation

Please cite **all three** entries below — the software entry alone is not
sufficient.

1. **Methodology.** Kim, J., Huh, S.-C., Bae, J. H., Shin, S.-J., & Park, S.
   *Deep spectral deconvolution for image-based broadband spectral data
   analysis.* Sensors and Actuators B: Chemical (2026).
   [doi:10.1016/j.snb.2025.139369](https://doi.org/10.1016/j.snb.2025.139369)

2. **Plasma OAS context.** Huh, S.-C. *et al.*
   Plasma Sources Sci. Technol. **33**, 075007 (2024).
   [doi:10.1088/1361-6595/ad5ebb](https://doi.org/10.1088/1361-6595/ad5ebb)

3. **Software.** Kim, J. & Park, S. *OAS Spectrum Studio — a Streamlit
   analyser for optical absorption spectroscopy with a continual-learning
   loop.* APRIL Lab, KAIST (2026).
   <https://github.com/jongchan1999/oas-spectrum-studio>

<details>
<summary>BibTeX</summary>

```bibtex
@article{Kim2026DeepSpectralDeconvolution,
  title   = {Deep spectral deconvolution for image-based broadband spectral data analysis},
  author  = {Kim, Jongchan and Huh, Seong-Cheol and Bae, Jin Hee and Shin, Su-Jin and Park, Sanghoo},
  journal = {Sensors and Actuators B: Chemical},
  year    = {2026},
  doi     = {10.1016/j.snb.2025.139369}
}
@article{Huh2024PlasmaSources,
  author  = {Huh, Seong-Cheol and others},
  journal = {Plasma Sources Science and Technology},
  volume  = {33}, number = {7}, pages = {075007}, year = {2024},
  doi     = {10.1088/1361-6595/ad5ebb}
}
```

</details>

Machine-readable: [`CITATION.cff`](CITATION.cff).

## License

[MIT](LICENSE) © 2026 Jongchan Kim &amp; APRIL Lab, KAIST. Permissive use,
modification, and redistribution; please keep the copyright notice intact.

## Get access

This project is shared in a controlled way to keep deployment load
predictable and the continual-learning corpus clean. Two access tiers:

| You want to … | What we give you |
|---|---|
| **Use the deployed tool only** | A personal login for the live Streamlit app at <https://oas-spectrum-studio.streamlit.app>. No GitHub account needed. |
| **Read or contribute to the code** | A **collaborator invite** to this private GitHub repository — send us your GitHub username and we add you in *Settings → Collaborators*. |

Send a short note (who you are, which tier you want, and what you plan
to do with it) to either of the maintainers below.

## Contact

| Role | Person | Email |
|---|---|---|
| **Principal investigator** | Sanghoo Park | <sanghoopark@kaist.ac.kr> |
| **Maintainer / lead developer** | Jongchan Kim | <kimjongchan@kaist.ac.kr> |

If you have access to the repo, [open an issue](https://github.com/jongchan1999/oas-spectrum-studio/issues/new)
for bug reports or feature requests; otherwise just email.

<p align="center">
  <sub>Developed at <a href="https://sites.google.com/view/plasmalab/">APRIL Lab</a>
  (Applied Plasma Research &amp; Innovation Lab),
  <a href="https://www.kaist.ac.kr/">KAIST</a> · 2026</sub>
</p>
