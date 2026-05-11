# Curation scripts

Tools that consume the **Phase 1** submission corpus produced by the Streamlit
app + Supabase edge function, and produce a **Phase 2** release pack ready
for fine-tuning.

```
scripts/
└── curate.py        — pull raw submissions → validate → dedupe → normalise → pack
```

The heavy lifting lives in [`oas_web/curation.py`](../oas_web/curation.py);
this folder is just thin CLI / automation glue.

## Required environment

```bash
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJ......"     # service_role JWT — keep private!
```

The service-role key bypasses RLS and lets the curator both read raw
submissions and update their `status`. **Never** commit it or bake it into
the app.

## Running locally

```bash
# trial — fetches everything but does not PATCH the DB
python scripts/curate.py --dry-run

# real run — pins a tag like "v2"
python scripts/curate.py --release-id v2

# default release id is a UTC timestamp
python scripts/curate.py
```

Outputs land in `curated/<release_id>/`:

```
curated/v2/
├── dataset.npz       # the training tensors (see below)
├── manifest.csv      # one row per processed submission
└── report.md         # human-readable summary
```

### `dataset.npz` contents

| key                 | shape                | dtype | meaning |
|---------------------|----------------------|-------|---------|
| `wavelengths_nm`    | (191,)               | f8    | canonical grid 210–400 nm @ 1 nm |
| `species`           | (8,)                 | U6    | HONO HONO2 N2O4 N2O5 NO NO2 NO3 O3 |
| `submission_ids`    | (N,)                 | U36   | for traceability back to Supabase |
| `measured_od`       | (N, 191)             | f8    | OD on the canonical grid |
| `reconstructed_od`  | (N, 191)             | f8    | OD on the canonical grid |
| `number_density`    | (N, 8)               | f8    | molec/cm³ |
| `method`            | (N,)                 | i1    | 0 = linear regression, 1 = ML |
| `path_length_cm`    | (N,)                 | f8    | as submitted |
| `ml_r2`, `ml_rmse`  | (N,)                 | f8    | NaN for LR submissions |

Phase 3's fine-tune script (`machine_learning/finetune.py`, not yet
implemented) loads this file directly.

## What the curator does

For every row in `cl_submissions` with `status = 'raw'`:

1. **Fetch** the JSON blob from Storage at the row's `storage_key`.
2. **Validate**: schema version, finite arrays, monotonic wavelengths,
   reasonable ranges, 8-species shape, non-negative densities.
3. **Dedupe** against (a) previously `accepted/training` rows via the
   pair `(reference_hash, measured_hash)` and (b) within this run via a
   hash of the post-normalisation measured spectrum.
4. **Normalise** measured + reconstructed OD onto the canonical 1-nm
   grid 210–400 nm (191 points) using `np.interp` with edge fill = 0.
5. **Update** the Supabase row: `accepted` (with `release_id` +
   `accepted_at`) or `rejected` (with `rejection_reason`).
6. **Pack** all accepted rows into a single `dataset.npz`.

Idempotency: re-running the same release_id will just process whatever
new `raw` submissions arrived since last time. Already-accepted rows
stay accepted and don't change `release_id`.

## Automation

The GitHub Action at [`.github/workflows/curate.yml`](../.github/workflows/curate.yml)
runs this script.

- Default trigger: `workflow_dispatch` (manual, "Run workflow" button)
- The optional `schedule:` block is commented out — uncomment it once the
  weekly cadence is locked in.

The action needs two **repo secrets** (`Settings → Secrets and variables
→ Actions → New repository secret`):

| Name                          | Value |
|-------------------------------|-------|
| `SUPABASE_URL`                | same URL as locally |
| `SUPABASE_SERVICE_ROLE_KEY`   | service_role JWT |

The action uploads `curated/<release_id>/` as a workflow artifact you can
download from the run page.

## Common errors

- `Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running curation.`
  → export the two env vars in your current shell.
- `HTTP 401 / 403` on PostgREST → the key isn't a service-role key (you
  probably grabbed the `anon` key by mistake).
- `HTTP 400 ... in.(accepted,training)` → very old Supabase project; try
  upgrading the API or open an issue.
- `permission denied for table` → run the GRANTs from
  [`supabase/schema.sql`](../supabase/schema.sql) section 5b.
