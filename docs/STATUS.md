# Project status — picked up where this leaves off

> Updated 2026-05-12. Use this as the first thing to read when you resume.

## Where things stand

| Layer | State | Notes |
|---|---|---|
| **Streamlit app (front)** | ✅ Live | `oas-spectrum-studio.streamlit.app`, allow-list login on |
| **Linear regression pipeline** | ✅ Production | R² ≈ 0.92 on the Source_70_2 reference series |
| **ML inference (current ResNet101)** | ✅ Live, ⚠ low accuracy | R² ≈ -0.5 on real measurements; expected and addressed by CL Phase 3 |
| **CL Phase 1 — submission endpoint** | ✅ Shipped & verified live | Supabase edge function `submit`, end-to-end tested |
| **CL Phase 2 — curation worker** | ✅ Shipped, dry-run verified | `scripts/curate.py` + `.github/workflows/curate.yml` |
| **CL Phase 3 — fine-tune + eval** | ⛔ Not started | Blocked on more submissions (target ≥ 20) |
| **Demo video** | 📹 Script ready, recording pending | See `docs/DEMO_VIDEO_SCRIPT.md` |
| **Public release** | 📋 Checklist ready | See `docs/RELEASE_CHECKLIST.md` |

## Open follow-ups (small, can be batched)

1. **GitHub repo secret correction** — the first dry-run of the curation
   action returned `scanned=0`. Most likely cause: the
   `SUPABASE_SERVICE_ROLE_KEY` secret holds the *anon* key. Re-grab the
   service_role key from
   `Supabase → Settings → API → service_role secret (Reveal)` and update
   the repo secret. Then re-run the workflow. Expected: `scanned=1`.

2. **First real release** — after the secret fix, run the curate
   workflow once with `release_id=v1` and Dry-run **off**. The Supabase
   row flips to `accepted`, the artifact contains `curated/v1/`.

3. **Encourage more submissions** — Phase 3 needs ≥ 20 diverse frames in
   `cl_submissions` to make the fine-tune story meaningful. Easiest
   source: submit ~20 time-points from the Source_70_2 series via the
   app (Single mode, ML, consent, Submit — one per frame).

4. **Record the demo video** — follow `docs/DEMO_VIDEO_SCRIPT.md`.
   Replace `REPLACE_WITH_YT_ID` in `README.md` with the uploaded video
   ID. The README's hero auto-resolves the thumbnail + embed link.

5. **Decide the licence** — `LICENSE` currently ships as MIT (most
   permissive, common in research code). Confirm with PI / department
   before announcing the public link in a paper. If a more restrictive
   licence is needed (e.g. CC BY-NC-SA for non-commercial), replace the
   file before publication.

6. **Phase 3 design** — when ready:
   - `machine_learning/finetune.py`: loads
     `curated/v{N}/dataset.npz`, fine-tunes the previous checkpoint,
     evaluates on (a) curated holdout (b) simulated baseline
     (c) golden set.
   - `docs/CONTINUAL_LEARNING.md` already has the architecture and
     promotion gates.

## Latest commit context

```
main (latest) — Phase 2 curation worker + service_role GRANTs fix
                + Phase 1 verified end-to-end
                + paper-grade UI polish
```

To resume tomorrow: open the live app, open this file, work through the
"Open follow-ups" list in order. Items 1–2 are the only ones that touch
production; the rest are local prep.
