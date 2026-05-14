# Project status — picked up where this leaves off

> Updated 2026-05-15. Use this as the first thing to read when you resume.

## Where things stand

| Layer | State | Notes |
|---|---|---|
| **Streamlit app (front)** | ✅ Live | `oas-spectrum-studio.streamlit.app`, allow-list login on |
| **Linear regression pipeline** | ✅ Production | R² ≈ 0.92 on the Source_70_2 reference series |
| **ML inference (current ResNet101)** | ✅ Live, ⚠ low accuracy | Negative R² on real measurements; expected and addressed by CL Phase 3 |
| **CL Phase 1 — submission endpoint** | ✅ Shipped & verified live | Supabase edge function `submit`, end-to-end tested |
| **CL Phase 2 — curation worker** | ✅ Shipped, dry-run verified | `scripts/curate.py` + `.github/workflows/curate.yml` |
| **CL Phase 3 — fine-tune + eval harness** | ✅ Shipped, awaiting data | `scripts/finetune.py` + `.github/workflows/finetune.yml`. Useful results need ≥ 20 submissions. |
| **Demo video** | ✅ Shipped — `docs/demo/demo.mp4` (3 min 36 s, 1080p, silent, LFS) | Walks through login → Single OAS LR → Time-series LR → ML + Supabase DB |
| **Tag `v1.0-demo`** | ✅ Pushed | First public-ready release; matches the demo video |
| **Public release** | 🟡 Repo ready, awaiting visibility flip | All sanity checks in `docs/RELEASE_CHECKLIST.md` pass; remaining step is GitHub Settings → Visibility → Public |

## Recommended pickup order

These are the things you need to do (or can have me do) to take this from
"all phases coded" → "public-ready paper-ready release". Order matters.

1. **Fix the `SUPABASE_SERVICE_ROLE_KEY` GitHub secret.**
   Phase 2 dry-run returned `scanned=0` last time — almost certainly the
   secret holds the anon key, not the service role key. Grab the
   service_role key from
   `Supabase → Settings → API → service_role secret (Reveal)` and
   replace the GitHub repo secret. Re-run the curate workflow; expect
   `scanned ≥ 1` this time. **5 minutes.**

2. **Accumulate a real corpus.** Phase 3 fine-tune needs roughly **20+
   diverse submissions** in `cl_submissions` to demonstrate model
   improvement. Use the helper, not clicks:

   ```powershell
   # PowerShell. Set the cl endpoint either via env vars
   $env:CL_ENDPOINT = "https://bvgsyrxratdkqjfucisl.functions.supabase.co/submit"
   $env:CL_ANON_KEY = "<anon public key>"
   # …or fill the [cl] section of .streamlit/secrets.toml.

   python scripts\seed_submissions.py `
     --data-dir "C:\path\to\your\Source_70_2" `
     --reference Source_70_2_00000.txt `
     --n 20 `
     --user-id seeder
   ```

   Each frame runs locally as linear regression (trusted labels) and
   POSTs through the same edge function the Streamlit app uses. Expect
   ~20 new rows in `cl_submissions` within a minute. Run `--dry-run`
   first if you want to verify the pipeline without touching the DB.

3. **Run the first Phase 2 + Phase 3 release end-to-end on real data.**
   - Curate: workflow `curate.yml` → release_id `v1`, dry-run off.
   - Fine-tune: workflow `finetune.yml` → release_id `v1`, defaults.
   - Result: `releases/v1/v1.pth` (LFS-tracked), `report.md`, `eval.json`.
   - If the eval gates promote, the workflow flips
     `models/latest.json` to the new checkpoint. The Streamlit app reads
     that pointer on next reboot. (Optional: wire it in later — for v1
     just verify the artefact looks right.)

4. **Record + upload the demo video.** Follow
   `docs/DEMO_VIDEO_SCRIPT.md`. Replace `REPLACE_WITH_YT_ID` in
   `README.md` with the uploaded video ID. The hero auto-resolves the
   thumbnail + embed link.

5. **Run through `docs/RELEASE_CHECKLIST.md`.** Confirm the licence,
   rotate Streamlit passwords, double-check that no secret leaks in
   any tracked file, tag `v1.0-demo`.

6. **Private invite-only opening.** Share the live URL + per-person
   credentials per the template in the release checklist. Watch
   `cl_submissions` for incoming rows.

7. **Iterate.** Once contributions accumulate, run curate + finetune
   weekly (or every 100 new accepted samples — gate hard-coded in the
   curation worker once it's wired up). Each release ships a one-page
   `releases/vN/report.md` you can cite in the paper.

## Latest commit context

```
main (latest) — Phase 3 fine-tune + eval harness
                + Phase 2 verified end-to-end (pending service_role key fix)
                + Phase 1 live
                + caption-only demo script
                + pre-release docs (LICENSE, release checklist, conference assets)
```

To resume tomorrow: open the live app, open this file, work through the
"Recommended pickup order" list in sequence. Items 1–3 touch production;
the rest is local prep + public release plumbing.
