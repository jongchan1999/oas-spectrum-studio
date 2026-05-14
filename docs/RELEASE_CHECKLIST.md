# Going public — release checklist

> Work through this list once before sharing the live link / repo URL
> outside the immediate group. Most items are one-time; revisit only when
> something material changes (model release, allow-list, licence).

## 1. Repository hygiene

- [ ] `LICENSE` committed and reviewed (default: MIT — confirm with PI).
- [ ] `README.md` hero shows the demo GIF or YouTube thumbnail.
- [ ] No plaintext secrets in tracked files.
  - Sanity check: `git grep -nE 'sk_live|service_role|password\s*=\s*"[^"]'`
- [ ] `.streamlit/secrets.toml` is gitignored (it is — verify with
  `git check-ignore .streamlit/secrets.toml`).
- [ ] Open issues / TODO comments triaged or filed as GitHub Issues.
- [ ] Latest commit is signed if your institution requires it (optional).
- [ ] `docs/STATUS.md` reflects current state (so cold readers know
  what's done vs. pending).

## 2. App configuration (Streamlit Cloud)

- [ ] **Secrets** include both `[auth]` and `[cl]` blocks. Open the live
  app in an incognito window and confirm the login form appears.
- [ ] Allow-list users are real people you trust to share the link with.
  Rotate passwords every quarter.
- [ ] The "ML checkpoint" sidebar status pill is **green** (= `.pth`
  resolved via LFS).
- [ ] The "Cross-sections" sidebar pill is **green** (= 8 species files
  found under `Cross_sections_modified/`).
- [ ] App URL is the slug you want long-term (default
  `oas-spectrum-studio.streamlit.app`). Renaming later breaks every link
  you've shared.

## 3. Supabase posture

- [ ] `cl_submissions` RLS is **on**; no anon policies exist.
- [ ] Storage bucket `cl-raw` is **private** (no public read).
- [ ] `CL_HASH_SALT` is set as an Edge Function secret (≥ 32 chars).
- [ ] The Supabase project's **service_role** key is **only** in:
  - your local `~/.bashrc` / `~/.zshrc` / PowerShell profile (optional)
  - GitHub repo Action secret `SUPABASE_SERVICE_ROLE_KEY`
- [ ] The **anon** key is in:
  - Streamlit Cloud secrets (`cl.anon_key`)
- [ ] No service_role key in any frame of the demo video.
- [ ] Bucket size + DB row count are within free-tier limits (check
  Supabase dashboard → Settings → Usage).

## 4. GitHub repo posture

- [ ] Repository **visibility = Private** for now (Education Pro
  allows unlimited private repos).
- [ ] Collaborators added by username via *Settings → Collaborators*.
  Use email invites only for users who don't have GitHub accounts (they
  can sign up free).
- [ ] *Settings → Branches*: protect `main` (require PR, prevent force
  push). Optional but recommended for shared writes.
- [ ] *Settings → Secrets and variables → Actions* contains:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`  (service_role, not anon — common pitfall)
- [ ] `LICENSE` file present and matches the licence stated in the
  paper / abstract.
- [ ] First release tag: `v1.0-demo` (or whatever matches the YouTube
  video). Use `git tag v1.0-demo && git push --tags` after recording.

## 5. Invitee onboarding template

Use this message verbatim when inviting external researchers, replacing
the URL and credentials:

```
Hi <name>,

I'm sharing early access to OAS Studio, a Streamlit-hosted analyser for
optical absorption spectroscopy. It runs both a NNLS linear regression
and a ResNet101 ML model on uploaded spectra, with an opt-in continual-
learning loop that lets your runs improve the next model release.

  Live app : https://oas-spectrum-studio.streamlit.app
  Username : <one we assign per invitee>
  Password : <unique, rotate quarterly>
  Source   : https://github.com/jongchan1999/oas-spectrum-studio (private)

A 3-minute walkthrough is at <YouTube unlisted URL>.

If you contribute analyses via the Submit button, you will be credited
in the next model release's `releases/vN.md`. We curate weekly.

Please don't share the credentials further; if you need additional seats
for your group, ping me and I'll create a per-person login.

If you publish results obtained with this tool, please cite the two
references in our README's "Citation" section (the methodology paper —
Sensors and Actuators B: Chemical, 2026, doi 10.1016/j.snb.2025.139369 —
and the plasma-OAS paper — Plasma Sources Sci. Technol. 33 075007,
2024).

Thanks!
Jongchan Kim (developer)            kimjongchan@kaist.ac.kr
Sanghoo Park (principal investigator) sanghoopark@kaist.ac.kr
APRIL Lab · KAIST
https://sites.google.com/view/plasmalab/
```

## 6. Licensing — pick one

Place the appropriate text in `LICENSE` before going wider.

| Licence | When to use | Caveats |
|---|---|---|
| **MIT** *(default)* | Maximum reuse; no patent restrictions. Most popular in research code. | If the model could conceivably be patented, MIT does not grant a patent licence. |
| **Apache 2.0** | Same permissions as MIT + explicit patent grant. | Header boilerplate is wordier. |
| **CC BY 4.0** | Better fit for *data* than for *code*; OK for the model checkpoint. | Not designed for executable code. |
| **CC BY-NC 4.0** | Block commercial reuse but allow academic. | "Non-commercial" definitions get hairy — talk to your tech transfer office. |
| **Custom + dual licensing** | Spin-out / startup play: GPL for academics, commercial licence for industry. | Requires legal review. |

**Recommendation for first public release**: MIT. Switch later if a
clear commercialisation path emerges.

## 7. After-release maintenance cadence

- **Daily** (automated): nothing — the app and Supabase run themselves.
- **Weekly** (manual or via the GitHub Action): run the curation
  workflow. Review `report.md` of the new release for surprising
  rejection reasons.
- **Per release (~ monthly)**: Phase 3 fine-tune job (once implemented),
  evaluation report, write `releases/vN.md`, tag the repo, swap
  `models/latest.json` to the new checkpoint.
- **Quarterly**: rotate Streamlit allow-list passwords. Re-check
  Supabase usage versus free-tier limits.

## 8. Done means

- A first-time visitor lands on the repo, sees the hero video, scrolls
  the README, understands what the tool does in 60 seconds.
- They click the live app link, see the login page, request access.
- An invitee they log in, runs an analysis, opts in, hits Submit — and
  shows up as a row in `cl_submissions` within seconds.

When that loop holds end-to-end with a real external user, the launch is
considered shipped.
