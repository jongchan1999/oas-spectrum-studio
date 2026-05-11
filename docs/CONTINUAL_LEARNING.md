# Continual Learning Backend — Design

> Status: design only. No code yet. Reviewed → then we implement stage by
> stage. The current app only exports CL samples as CSV; this document
> describes how those samples flow into model retraining.

## Goals

1. Take *consented* user spectra (I₀ + It + reconstruction + metadata) and
   accumulate them into a shared training corpus.
2. Periodically fine-tune the ResNet101 CNN on the growing corpus and ship a
   new checkpoint without breaking the inference contract used by the app.
3. Provide a paper-grade evaluation pipeline so each new model version comes
   with metrics deltas vs. the previous one (and vs. the simulated baseline).

Non-goals (for v1):

- Real-time / online learning.
- Federated learning. Everything is centralised on our infra.
- User-level access controls beyond the existing login allow-list.

## Components

```
┌──────────────────────┐    consent CSV    ┌──────────────────────┐
│  Streamlit app       │ ────────────────▶ │  Submission endpoint  │
│  (oas-spectrum-studio│   (HTTPS POST)    │  (FastAPI on Cloud Run│
│   + ML inference)    │                   │   or Supabase Edge Fn)│
└──────────────────────┘                   └──────────┬───────────┘
                                                      │ write
                                                      ▼
                                           ┌──────────────────────┐
                                           │  Object storage       │
                                           │  (S3 / GCS / Supabase │
                                           │  Storage)             │
                                           │  /raw/YYYY/MM/<uuid>  │
                                           └──────────┬───────────┘
                                                      │ pull
                                                      ▼
                                           ┌──────────────────────┐
                                           │  Curation worker      │
                                           │  - schema validate    │
                                           │  - dedupe (sha256)    │
                                           │  - sanity range check │
                                           │  - augment metadata   │
                                           │  /curated/<release>   │
                                           └──────────┬───────────┘
                                                      │ schedule (weekly)
                                                      ▼
                                           ┌──────────────────────┐
                                           │  Training job         │
                                           │  - fine-tune from     │
                                           │    previous .pth      │
                                           │  - eval on holdout    │
                                           │  - publish .pth + log │
                                           │  /models/v{N}.pth     │
                                           └──────────┬───────────┘
                                                      │ promote
                                                      ▼
                                           ┌──────────────────────┐
                                           │  Live model            │
                                           │  (LFS-backed .pth     │
                                           │   or signed URL fetch)│
                                           └──────────────────────┘
```

## (a) Submission endpoint

Two viable hosting options. Pick one based on operations preference.

| Option | Pros | Cons |
|---|---|---|
| **Supabase** Edge Function + Storage | Free tier covers MVP; built-in row-level security; auth integrates with the same allow-list | Edge Function size limit; Postgres for metadata is fine but not GCS-fast |
| **FastAPI on Cloud Run** + GCS | Full Python control (validation, ML pre-checks); cheap (scales to zero) | Slightly more setup (Cloud project, IAM, container) |

**Recommendation: start with Supabase.** Switch to Cloud Run when we need
custom curation logic per upload.

### Request payload (proposed)

```json
{
  "schema_version": 1,
  "client": {
    "app_version": "1.0.3",
    "method": "machine_learning",
    "path_length_cm": 15.0
  },
  "metadata": {
    "reference_file": "Source_70_2_00000.txt",
    "measured_file":  "Source_70_2_00121.txt",
    "user_id":        "<allow-list username>",
    "timestamp_utc":  "2026-05-11T13:34:00Z",
    "consent":        true
  },
  "spectrum": {
    "wavelength_nm":           [210.0, 210.5, ...],
    "measured_absorbance":     [0.011, 0.012, ...],
    "reconstructed_absorbance":[0.010, 0.012, ...]
  },
  "predictions": {
    "species":          ["HONO","HONO2","N2O4","N2O5","NO","NO2","NO3","O3"],
    "number_density":   [1.2e15, 0.0, 0.0, 0.0, 8.5e14, 0.0, 0.0, 0.0],
    "ml_metrics": { "r2": 0.92, "rmse": 0.0023 }
  }
}
```

Server validates against a JSON Schema (`schemas/cl_submission.v1.json`).
Rejects on shape mismatch or out-of-range values (e.g. negative number
densities, wavelength outside 200–700 nm).

### App-side changes (small)

- Replace today's "Download CL CSV" button with a "Submit to global model"
  button when the consent box is checked.
- Keep the local CSV download as a secondary option (always available).
- On submit, POST the JSON to the endpoint, show a confirmation toast with
  the returned `submission_id`.

```python
# oas_web/cl_submit.py  (sketch — not yet implemented)
def submit_to_global_model(payload: dict, *, endpoint: str, token: str) -> str:
    """POST a CL payload; returns submission_id from server or raises."""
    ...
```

## (b) Curation pipeline

A scheduled worker (Cloud Function / GitHub Action / cron VM):

1. **Pull** all `raw/` objects added since the last run.
2. **Validate**: schema check, NaN/inf check, monotonic wavelength axis, mask
   suspicious frames (e.g. SNR < threshold). Reject and log to `rejects/`.
3. **Dedupe** on `sha256(wavelength + measured + reference_file)`.
4. **Normalise** wavelength grid (interp to canonical 1-nm grid 210–400 nm).
5. **Materialise tensors**: pack into a single Parquet / .npz with columns
   `["wavelength_grid", "measured_od", "reconstructed_od", "target_nd",
   "meta"]`.
6. **Move** validated samples to `curated/{release_id}/sample_{n}.npz`.

Outputs:
- `curated/{release_id}/manifest.csv` listing accepted/rejected counts.
- `curated/{release_id}/dataset.npz` ready for training.

## (c) Fine-tuning job

Triggered weekly (or on-demand) once `curated/{release_id}/dataset.npz` has
enough new samples (threshold: at least 50 new accepted submissions).

### Procedure

1. Load previous checkpoint `models/v{N}.pth` (the one currently in
   production).
2. Mix curated/`{release_id}` with a *frozen* simulated baseline pool (this
   prevents catastrophic forgetting on simulated distribution).
3. Fine-tune for a small number of epochs (e.g. 5) with a reduced learning
   rate (e.g. `1e-5`).
4. Evaluate on:
   - holdout from `curated/`
   - the simulated baseline test set
   - a hand-curated golden set (≈ 50 real measurements with trusted labels)
5. Compare R², per-species RMSE, regression bias against the previous model.
6. If all three suites pass *predefined* gates → publish `models/v{N+1}.pth`
   (LFS commit + signed URL), update README. Otherwise, store as
   `models/v{N+1}-candidate.pth` and surface a Slack/email alert.

### Training script entry point (sketch)

```bash
python machine_learning/finetune.py \
    --base-checkpoint models/v3.pth \
    --new-dataset     curated/2026-W19/dataset.npz \
    --baseline-pool   curated/baseline/sim.npz \
    --epochs 5 --lr 1e-5 \
    --eval-golden     curated/golden/v1.npz \
    --output          models/v4-candidate.pth \
    --report          reports/v4-candidate.md
```

## Versioning + rollout

- **Major (v1 → v2)**: schema-breaking change (new species, different OD
  preprocessing). Requires app-side migration.
- **Minor (v3.0 → v3.1)**: same architecture, new fine-tuned weights. App
  needs no change.

App reads the model checkpoint URL from a small config (`models/latest.json`)
so a new minor version rolls out without redeploying the Streamlit app:

```json
{ "url": "https://.../v3.1.pth", "sha256": "...", "released": "2026-05-13" }
```

The app verifies the sha256 on download and refuses to start if it
mismatches.

## Paper-track evaluation

For the continual-learning paper, log per-release:

| Metric | Source |
|---|---|
| `delta_r2_real` | Δ R² on the curated real-data holdout |
| `delta_r2_sim`  | Δ R² on the simulated baseline (forgetting check) |
| `species_bias`  | per-species number-density bias on the golden set |
| `corpus_size`   | number of accepted real-world samples |
| `coverage_lambda` | wavelength coverage diversity of new submissions |
| `coverage_nd`     | distribution of true number densities seen this release |

Plot these over releases to make the continual-learning story visible.

## Phased plan

| Phase | Deliverable | Estimated effort |
|---|---|---|
| 0 | Pick Supabase vs. Cloud Run; create bucket & dummy schema | 1 day |
| 1 | Submission endpoint + app-side submit button | 2 days |
| 2 | Curation worker (validation + dedupe + Parquet pack) | 2-3 days |
| 3 | Fine-tune script with frozen baseline | 3-4 days |
| 4 | Eval harness (real holdout + sim + golden) | 2-3 days |
| 5 | Promotion rules + model URL config + auto-verify | 1-2 days |
| 6 | Dashboards (Streamlit page for release metrics) | 1-2 days |

## Decisions (locked v1)

Decided on the principle: *every choice should maximise the chance of a
paper-grade demonstration that continual learning improves the model
release-over-release, while keeping the contributor UX trivially simple and
the data lineage auditable.*

1. **Hosting → Supabase (free tier).**
   Auth, Postgres for metadata, S3-compatible Storage for raw spectra. One
   vendor, one place to revoke or export. Edge Functions handle the
   submission endpoint — no separate FastAPI container needed for v1.
   Migration to Cloud Run + GCS stays an option once we outgrow the free
   quota or need per-upload ML pre-checks.

2. **Identity → tied to the Streamlit allow-list username.**
   Required for revocation, traceability, and credit attribution in the
   paper acknowledgements. The username is hashed (SHA-256 + repo-side
   salt) before being written into the corpus, so the public dataset never
   exposes a real identifier.

3. **PII / filenames → server-side hashed.**
   Raw filenames frequently include experiment / facility names. The
   submission endpoint replaces them with `sample_{sha256(name)[:12]}`. The
   original mapping is kept in a private `metadata.filename_map` table
   accessible only to the owner of the upload (RLS policy).

4. **Release threshold → 100 accepted samples + 14 days minimum gap.**
   Avoids retraining on tiny deltas (statistically noisy) while still
   producing several releases per year. First 3 releases are manually
   triggered so we can read each report; cron-promoted afterward.

5. **Rollback → keep last 5 promoted model versions.**
   170 MB × 5 ≈ 850 MB LFS, well within the Education tier. Each release
   gets a tagged commit (`model-v3`, `model-v4`, …) and the live
   `models/latest.json` flips between them. Pin to any earlier version by
   changing one URL.

### Paper-track addendum

Every release publishes a one-page `releases/{vN}.md` with:
- corpus deltas (new samples, species distribution, wavelength coverage diff)
- per-species RMSE / bias deltas vs v(N-1) on (a) curated real holdout
  (b) simulated baseline (c) golden hand-labelled set
- per-user contribution table (hashed handles) so the paper can cite the
  active contributor count over time

These reports are the substrate of the "model improves with continual
learning" narrative — once we have 3–4 releases stacked, the trend itself
becomes the figure.

### Open after v1

Once the basic loop runs, revisit:
- **Federated training** (no spectra leave the user's machine; only gradients
  travel) — only if PII concerns escalate.
- **Active learning** — rank uploads by current-model uncertainty and
  prioritise the most informative ones for curation.
