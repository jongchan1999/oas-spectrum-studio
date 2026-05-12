# Demo video — shot-by-shot script

> **Goal**: a 3-minute screencast that lets a first-time viewer (e.g. a
> conference attendee or a fellow OAS researcher who lands on the GitHub
> repo) understand what OAS Studio does, see it work on real data, and
> grasp the continual-learning angle.
>
> Bilingual: every scene has both Korean and English voice-over so we can
> ship one version per audience. Pick whichever you prefer to narrate, or
> overlay both as captions.

---

## 0. Recording setup (30-minute one-shot)

### Tools

| Need | Recommended | Why |
|---|---|---|
| Screen capture | [OBS Studio](https://obsproject.com) (free) **or** [ScreenPal](https://screenpal.com/screen-recorder) (browser, free for 15-min clips) | Both record clean 1080p, no watermark on free tier (ScreenPal cap = 15 min) |
| Short hero GIF | [ScreenToGif](https://www.screentogif.com) (Windows free) | Optimised palettes, ~5 MB for 15 s @ 1080p |
| Voice-over (optional) | Built-in laptop mic + OBS audio track | Re-record audio later if needed |
| Editing (optional) | [Shotcut](https://shotcut.org) (free) or ScreenPal's built-in trim | Only needed if you bake captions into the MP4 |

### OBS settings

```
Output → Recording:
    Format:     mp4
    Quality:    Indistinguishable Quality
    Encoder:    NVENC H.264 (if you have NVIDIA GPU) else x264
Video:
    Base canvas:     1920 × 1080
    Output scaled:   1920 × 1080
    FPS:             30
Audio:
    Sample rate:     48 kHz
    Mic input:       your microphone (only if narrating)
Sources for the scene:
    Display Capture (the browser window) — fullscreen Streamlit Cloud tab
```

### Pre-flight checklist (do once before pressing Record)

- [ ] Streamlit Cloud app is **awake** (open the URL, log in, wait for the
      hero to render). Cloud sleeps after inactivity.
- [ ] Browser zoom = **100%**, window maximised, **no DevTools** open.
- [ ] Hide bookmarks bar (`Ctrl+Shift+B`) for a clean shot.
- [ ] Notifications **off** (Windows: Focus Assist → Alarms only).
- [ ] Pre-load demo files on the desktop in a folder named `OAS_demo/`:
  - `Source_70_2_00000.txt` — I₀ reference
  - `Source_70_2_00100.txt` — single mid-experiment frame (best LR result)
  - all 343 files of `Source_70_2/*.txt` — for the time-series scene
- [ ] Auth: log in with the `sanghoopark` or `jongchankim` allow-list user.

---

## 1. Storyboard (3 min 15 s)

Total scenes: **6**. Each block below has:

- **Visual**: what to show on screen (exact clicks)
- **KO**: Korean narration (read at ~3.5 syllables/sec)
- **EN**: English narration (~145 wpm)
- **Caption** (silent variant): on-screen text overlay if you skip voice-over
- **Duration**: rounded seconds

### Scene 1 — Title (0:00 → 0:15, 15 s)

**Visual.** Static title card. Use a still frame from the SVG poster at
[`docs/conference/poster-thumbnail.svg`](conference/poster-thumbnail.svg)
or just the live app's hero on the Single page.

**KO.** "OAS Studio. 광흡수 분광 데이터를 한 화면에서 분석하고, 모델을 함께
키워가는 도구입니다."

**EN.** "OAS Studio — a single-screen analyser for optical absorption
spectroscopy that lets the research community grow the model together."

**Caption (silent).** `OAS Studio · Optical Absorption Spectroscopy ·
Continual learning for the community`.

---

### Scene 2 — App tour (0:15 → 0:35, 20 s)

**Visual.**

1. Cursor enters the Streamlit Cloud URL bar — hit Enter.
2. Login form briefly visible → enter credentials → land on app.
3. Hover the left sidebar from top to bottom:
   `OAS Studio` brand → `Analysis mode` radio → `Advanced fit configuration`
   expander (don't open yet) → `ML checkpoint` + `Cross-sections` status pills.
4. Scroll the main panel down once to reveal the hero + step-1 + step-2
   cards, then scroll back up.

**KO.** "분석 모드는 단일 스펙트럼과 시계열 두 가지. 사이드바에서 fitting
heuristics 도 그대로 조정할 수 있어요. 좌측 하단의 상태 표시로 ML 체크포인트와
cross-section 데이터가 준비됐는지 한눈에 확인됩니다."

**EN.** "Two analysis modes — single spectrum and time-series. The
sidebar exposes every fitting heuristic, and the status pills at the
bottom confirm that the ML checkpoint and cross-section data are loaded
and ready."

**Caption.** `Sidebar · 2 modes · live status · tunable heuristics`.

---

### Scene 3 — Single OAS analysis, Linear regression (0:35 → 1:25, 50 s)

**Visual.**

1. Stay on the **Single OAS analysis** page.
2. **Fitting method** = `Linear regression`.
3. Drag-and-drop `Source_70_2_00000.txt` into the **Reference I₀** dropzone.
4. Drag-and-drop `Source_70_2_00100.txt` into the **Measured It** dropzone.
5. Wait 1-2 seconds for the **Uploaded spectra preview** to render.
   Mouse-hover briefly to show the legend (Reference I₀ vs Measured It).
6. Click **Run linear regression analysis**.
7. Scroll down to **Results**. Show R² ≈ 0.92 in the metric tile.
8. Click into **Chemical extraction** tab → camera lingers on the table +
   the right-side bar chart for ~4 seconds.
9. Click **Validation overlay** tab → measured (black) + reconstructed
   (orange) + dashed per-species traces appear.
10. Click **Downloads** tab → cursor hovers over **Download reconstruction
    (CSV)** but does **not** click.

**KO.** "I₀ 와 측정 스펙트럼만 올리면, 광학두께 계산부터 화학종별 농도
추정까지 1초 안에 끝납니다. 결정계수는 0.92 이상. 종별로 분리된 재구성
스펙트럼까지 한 화면에 보이고, 다운로드 한 번이면 reproducibility 도 확보됩니다."

**EN.** "Drop in I₀ and a measured spectrum — optical depth, species
densities, and a full reconstruction land in under a second. R² above
zero point nine. Per-species traces sit on the same chart, and a single
click exports the reconstruction CSV for reproducibility."

**Caption.** `Drop files → Run → 8 species + R² in <1 s`.

---

### Scene 4 — Single OAS analysis, Machine learning + consent (1:25 → 2:00, 35 s)

**Visual.**

1. Top of the page, switch **Fitting method** to `Machine learning`.
2. Keep the same two files loaded. The preview re-renders unchanged.
3. **Tick** the consent checkbox **"Yes, contribute this analysis to the
   global model"** — the purple gradient banner expands.
4. Click **Run machine learning analysis**.
5. Scroll down to **Results**.
6. Click **Validation overlay** tab — show that the ML reconstruction is
   weaker (R² ≈ -0.5). **This is intentional**, not a bug.
7. Click **Downloads** tab.
8. Click **📡 Submit this analysis to the global model**.
9. Linger on the green confirmation toast with the `submission_id`.

**KO.** "Machine learning 모드도 동일한 UI 그대로. 다만 현재 모델은
시뮬레이션 데이터로 학습돼 있어서, 실측에 그대로 적용하면 결정계수가 음수까지
떨어집니다. 바로 이 격차를 좁히는 게 우리 continual-learning 파이프라인의
역할입니다. 동의 후 Submit 한 번이면, 사용자의 데이터가 익명화되어 다음 모델
릴리스의 학습 코퍼스에 자동으로 들어갑니다."

**EN.** "Switching to Machine Learning keeps the UI identical — same
preview, same tabs. The current checkpoint was trained on simulated
spectra, so R² goes negative on real measurements. Closing that gap is
exactly what our continual-learning pipeline is for: one opt-in click,
and the analysis becomes a hashed, deidentified training sample for the
next release."

**Caption.** `ML inference · opt-in consent · one-click contribution`.

---

### Scene 5 — Time-series mode (2:00 → 2:40, 40 s)

**Visual.**

1. Sidebar → **Time-series OAS analysis**.
2. **Fitting method** = `Linear regression` (faster for the demo).
3. In the file uploader, drag the **entire `Source_70_2/` folder** (or
   `Ctrl+A` select all 344 .txt files in the picker). The chip at the
   bottom shows `📁 344 files loaded.`
4. Click **Run linear regression analysis**.
5. The progress bar fills (Cloud free-tier ~ 30-60 s; if it's too slow,
   pre-record this scene locally and splice).
6. Scroll to **Results**. Metric tiles: `Timepoints 343`,
   `Detected species 5/8`, `Duration 343 s`, `Method Linear`.
7. **Trend** tab — log-scaled species trajectories animate in. Mouse-hover
   one species (e.g. NO) to show tooltip.
8. **Per-frame validation** tab → pick a mid-experiment frame from the
   dropdown (e.g. `Source_70_2_00120.txt`) → overlay renders.

**KO.** "시계열 분석은 같은 인터페이스로, 한 폴더 통째로 드래그. 343개의
프레임이 30초에서 1분 사이에 처리되고, 종별 농도 변화가 로그 스케일 그래프로
한 번에 보입니다. 특정 시간점만 따로 골라서 재구성 정확도 검증도 즉시 가능합니다."

**EN.** "Time-series is the same UI, scaled up — drag a whole folder,
hit Run, and watch 343 frames complete in well under a minute. Species
trajectories render on a log axis, and any single time-point can be
pulled up for per-frame validation."

**Caption.** `Drop folder → 343 frames in <1 min → log-scale trend`.

---

### Scene 6 — Continual learning + outro (2:40 → 3:15, 35 s)

**Visual.**

1. Cut to a **single static slide** (use
   [`docs/conference/key-visual.svg`](conference/key-visual.svg) as the
   background). Display 3 bullets on top:
   - "Today: ResNet101 trained on simulated spectra."
   - "Tomorrow: ★ your consented submissions → curated → fine-tune."
   - "Next release: every contributor cited in `releases/vN.md`."
2. Fade back to the app — Sidebar `Sign out` button visible.
3. End card with:
   - GitHub URL: `github.com/jongchan1999/oas-spectrum-studio`
   - Live app URL: `oas-spectrum-studio.streamlit.app`
   - "Request access:" + email/lab contact

**KO.** "오늘 보여드린 모델은 시작점일 뿐입니다. 여러분이 동의 후 보내주신
데이터가 다음 릴리스의 학습 데이터가 되고, 모든 기여자는 릴리스 노트에
명시됩니다. GitHub 와 라이브 앱 주소는 화면에 표시된 대로. 함께 광흡수 분광
분야의 표준 도구를 키워가요. 감사합니다."

**EN.** "What you saw today is the starting point. Your opted-in
submissions feed the next release, and every contributor is credited in
the release notes. The repository and the live app are on screen — let's
build the community's reference tool for OAS together. Thank you."

**Caption.** `github.com/jongchan1999/oas-spectrum-studio · request
access`.

---

## 2. Optional: short silent GIF for the README hero (12 s)

A short autoplay GIF makes the GitHub landing more immediately legible
than a video thumbnail. Record this *separately* from the main video,
since GIFs can't carry audio and want a tighter cut.

**ScreenToGif (Windows, recommended):**

1. `Recorder` → 1280 × 720 window, 24 fps, **place over the Streamlit
   app**.
2. Record this 12-second sequence (no narration, no cursor pauses):
   - 1 s — page already loaded, single mode selected
   - 2 s — drop I₀ + It files (fast)
   - 2 s — preview chart renders
   - 1 s — Run button clicked
   - 3 s — Results panel scrolls in with R² + tabs
   - 2 s — Click Validation tab — overlay appears
   - 1 s — hold on the final overlay
3. `Editor` → **Save as → GIF** → palette `Octree`, 64 colours, **target size
   ≤ 8 MB**. Save as `docs/assets/demo-hero.gif`.
4. The README hero section already has a slot that auto-uses this file
   if it exists.

---

## 3. Hosting + sharing

### YouTube (recommended)

1. Upload as **Unlisted** (link-only). Title:
   `OAS Studio — Optical Absorption Spectroscopy analyser (3-min tour)`.
2. Description (first line is what appears in embed previews):
   ```
   Single-screen OAS analyser with linear regression and continual-learning
   ML inference. Try it at oas-spectrum-studio.streamlit.app
   GitHub: github.com/jongchan1999/oas-spectrum-studio
   ```
3. Add chapters by pasting timestamps in the description:
   ```
   0:00 Intro
   0:15 App tour
   0:35 Single OAS — Linear regression
   1:25 Single OAS — Machine learning + consent
   2:00 Time-series
   2:40 Continual learning + outro
   ```
4. Tags: `optical absorption spectroscopy, OAS, NO2, ozone, plasma
   diagnostics, continual learning, Streamlit, ResNet, NNLS`.
5. After upload, copy the 11-char video ID (the part after `v=`).

### Drop the YouTube ID into the README

Edit [`README.md`](../README.md) once: replace the literal
`REPLACE_WITH_YT_ID` token with your video ID. The thumbnail link and
embed both auto-resolve. **Nothing else needs to change.**

### Conference / lab share

- Use the same Unlisted link in slides / abstracts — invitees don't need
  a Google account to watch.
- For an offline backup, download the same MP4 from YouTube Studio
  (`Manage videos → ⋮ → Download`) and keep it on a USB at the venue.

---

## 4. Things that should NOT appear in the recording

- The `[cl]` block of `secrets.toml` (it shows the anon key — minimal
  risk, but still). Ensure Streamlit's Manage app panel is closed.
- The Supabase dashboard with the **service_role** key revealed. Never
  share this in any frame, ever.
- Other users' filenames in the time-series scene. The included
  `Source_70_2_*` set is fine.

## 5. After-shot polish (5-10 minutes)

If you have time, in ScreenPal/Shotcut:

- Trim every gap longer than 1 second.
- Drop a 1-second cross-fade between Scenes 4 → 5 (mode switch).
- Drop the `key-visual.svg` over Scene 6 as a still overlay (no motion
  needed).
- Bake captions in if you didn't narrate. The captions in each scene
  block above are designed to be one-liners at ≤ 60 characters.

That's it. Total recording + upload time should be under one hour.
