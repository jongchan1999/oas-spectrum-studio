# Supabase setup — continual-learning submission endpoint

This folder contains everything the OAS Studio app needs on the Supabase
side to accept consented continual-learning samples:

```
supabase/
├── schema.sql                        # one-shot SQL migration
└── functions/submit/
    ├── index.ts                      # Deno edge function
    └── deno.json                     # local-dev task config
```

The app POSTs JSON to the `submit` function, which validates the payload,
writes the raw blob to a private Storage bucket, and inserts a row into
`public.cl_submissions`. Identifiers (username, filenames) are hashed on
the server so the corpus never contains plaintext PII.

## One-time setup

### 1. Create a Supabase project

1. Sign in at <https://supabase.com> with the same GitHub account you used
   for the OAS Studio repo (`jongchan1999`). The free tier is enough for
   v1 (500 MB DB + 1 GB Storage + 500K Edge Function invocations / month).
2. **New project** → pick the closest region (e.g. `Northeast Asia (Seoul)`).
3. Set a strong DB password and store it in your password manager.

### 2. Apply the database schema

In the project dashboard:

1. Open **SQL Editor**.
2. Paste the full contents of [`schema.sql`](./schema.sql).
3. Click **Run**. You should see "Success. No rows returned." Re-running
   is safe (everything is `IF NOT EXISTS` / idempotent).

This creates:
- `public.cl_submissions`   — the public corpus index (RLS on, default-deny)
- `public.cl_submission_species` — per-species number-density rows
- `owner_only.filename_map` — owner-only plaintext filename map

### 3. Create the Storage bucket

Dashboard → **Storage** → **New bucket**:

| Field        | Value      |
|--------------|------------|
| Name         | `cl-raw`   |
| Public       | **OFF**    |
| File size limit | 5 MB    |
| Allowed MIME types | `application/json` |

The edge function writes raw payloads to `cl-raw/raw/YYYY/MM/<uuid>.json`.

### 4. Set the hash salt secret

The edge function hashes usernames + filenames with a salt that should
never appear in source code:

```bash
# Replace <unique-string> with a 32+ character random string you keep
# private (e.g. `openssl rand -hex 32`).
supabase secrets set CL_HASH_SALT=<unique-string>
```

If you haven't installed the Supabase CLI yet:

- Mac: `brew install supabase/tap/supabase`
- Windows: `scoop bucket add supabase https://github.com/supabase/scoop-bucket.git && scoop install supabase`
- Linux: `npm install -g supabase`

Then `supabase login` and `supabase link --project-ref <project-ref>` (the
project-ref is the slug in your Supabase URL, e.g. `abcdefghijklmnop`).

### 5. Deploy the edge function

From the repo root:

```bash
supabase functions deploy submit
```

After ~30 seconds the dashboard shows it under **Edge Functions → submit**
with a public URL like:

```
https://<project-ref>.functions.supabase.co/submit
```

### 6. Wire the app

Copy the **anon public API key** (Dashboard → **Project Settings → API →
Project API keys → anon public**) and add a `[cl]` section to the
Streamlit secrets (`.streamlit/secrets.toml` locally, or in the
Streamlit Cloud app settings):

```toml
[cl]
endpoint = "https://<project-ref>.functions.supabase.co/submit"
anon_key = "eyJhbGciOiJI...."   # anon public key
```

Restart / reboot the Streamlit app. The "📡  Submit this analysis to the
global model" button appears in the **Downloads** tab of the ML pipeline
once the user opts in via the consent banner.

## Testing the endpoint manually

```bash
curl -X POST "https://<project-ref>.functions.supabase.co/submit" \
  -H "Authorization: Bearer <anon-key>" \
  -H "apikey: <anon-key>" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "schema_version": 1,
  "client": { "app_version": "1.0.0", "method": "machine_learning", "path_length_cm": 15.0 },
  "metadata": {
    "reference_file": "ref.txt",
    "measured_file": "meas.txt",
    "user_id": "test-user",
    "timestamp_utc": "2026-05-11T10:00:00Z",
    "consent": true
  },
  "spectrum": {
    "wavelength_nm":            [210, 220, 230, 240, 250, 260, 270, 280, 290, 300],
    "measured_absorbance":      [0.01, 0.02, 0.05, 0.10, 0.20, 0.18, 0.10, 0.05, 0.02, 0.01],
    "reconstructed_absorbance": [0.01, 0.02, 0.05, 0.10, 0.20, 0.18, 0.10, 0.05, 0.02, 0.01]
  },
  "predictions": {
    "species":        ["HONO","HONO2","N2O4","N2O5","NO","NO2","NO3","O3"],
    "number_density": [0,0,0,0,1e15,0,0,5e16],
    "ml_metrics": { "r2": 0.95, "rmse": 0.001 }
  }
}
JSON
```

Expected:
```json
{"ok":true,"submission_id":"<uuid>","storage_key":"raw/2026/05/<uuid>.json"}
```

Verify in dashboard:
- **Storage → cl-raw** has a new `raw/2026/05/<uuid>.json`
- **Table Editor → cl_submissions** has a row with that id
- **Table Editor → cl_submission_species** has 8 rows linked to it

## What's next (Phase 2+)

Once submissions are flowing, the curation worker (Phase 2) and fine-tune
job (Phase 3) consume `public.cl_submissions` rows. Those scripts live in
`scripts/` and connect with the **service role key** — never bundle that
key into the app. See [docs/CONTINUAL_LEARNING.md](../docs/CONTINUAL_LEARNING.md).
