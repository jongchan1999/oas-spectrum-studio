# Demo video — silent-screencast script (caption-only, beginner-friendly)

> **Format**: a silent screen recording with **on-screen text captions only
> (no voice-over)**. The style matches a typical journal *Supplementary
> Video* (`mmc4.mp4` style): clean cuts, every step labelled with a short
> caption, ~2-3 minutes total. The viewer doesn't need to know what OAS,
> linear regression, ML inference, or continual learning is — every concept
> is introduced as it appears.
>
> **Goal**: someone who lands on the GitHub README, watches once, and
> immediately can (a) understand what the tool does and (b) use it on their
> own data — without ever hearing a word.

---

## 0. Recording setup

### Tools

| Need | Recommended | Why |
|---|---|---|
| Screen capture | [ScreenPal](https://screenpal.com/screen-recorder) (browser, free for 15-min clips) **or** [OBS Studio](https://obsproject.com) | Both record clean 1080p, no watermark. ScreenPal lets you bake captions in directly. |
| Caption overlay | ScreenPal's built-in caption editor, **or** [Shotcut](https://shotcut.org) (free) | Add text to each clip after recording — much easier than typing live. |
| Short hero GIF (optional) | [ScreenToGif](https://www.screentogif.com) (Windows free) | 12-second silent loop for the README header. |

### Recording profile (OBS / ScreenPal)

```
Resolution:      1920 × 1080
Frame rate:      30 fps
Format:          MP4 (H.264)
Audio:           DISABLED (silent)
Mouse cursor:    visible, with click-highlight if your tool supports it
```

### Pre-flight checklist (do once before pressing Record)

- [ ] Streamlit Cloud app is **awake** — open it, log in, wait for the
      hero card to render. Cloud apps sleep after inactivity.
- [ ] Browser zoom = **100%**, window maximised, bookmarks bar **hidden**
      (`Ctrl+Shift+B` on Chrome).
- [ ] Notifications **off** (Windows: Focus Assist → Alarms only).
- [ ] Cursor moves are deliberate and smooth. Pause **2 seconds** on each
      important UI element so the caption has time to read.
- [ ] Pre-load demo files on the desktop in a folder named `OAS_demo/`:
  - `Source_70_2_00000.txt` — I₀ reference
  - `Source_70_2_00100.txt` — single mid-experiment frame (best LR result)
  - the full 343-file `Source_70_2/` folder for the time-series scene
- [ ] Auth: log in with one allow-list user (e.g. `sanghoopark`) before
      the recording starts. The login screen is **not** part of the demo —
      it would expose a username.

---

## 1. Storyboard — 9 scenes, ≈ 2:50

Each block has:

- **What to film**: exact actions on screen.
- **Caption (English)**: text that appears on screen. Designed for a
  general scientific audience with no OAS / ML background. Keep each line
  ≤ 80 characters.
- **Caption (Korean, optional)**: drop in if you want a Korean-localised
  cut. The English caption alone is enough for international submission.
- **Duration**: target seconds (recording can be ±20 %).

### Scene 1 — Title card (0:00 → 0:10, 10 s)

**Film.** Static frame. Either show
[`docs/conference/poster-thumbnail.svg`](conference/poster-thumbnail.svg)
exported as PNG, or just the app's hero on Single OAS analysis.

**Caption (EN).**
```
OAS Spectrum Studio
A single-screen tool for optical absorption spectroscopy.
github.com/jongchan1999/oas-spectrum-studio
```

**Caption (KO).**
```
OAS Spectrum Studio
광흡수 분광 분석을 위한 단일 화면 도구.
github.com/jongchan1999/oas-spectrum-studio
```

---

### Scene 2 — What is OAS? (0:10 → 0:25, 15 s)

**Film.** Title fades; show a stylised illustration (use the
spectroscopy schematic in [`docs/conference/key-visual.svg`](conference/key-visual.svg)
or the hero image inside the app). Optionally a small animated arrow from
"lamp → cell → spectrum".

**Caption (EN, two text blocks shown sequentially).**
```
Optical absorption spectroscopy measures how much light a gas absorbs
at each wavelength.
```
```
From that absorption pattern, we can tell which chemical species are
present, and in what concentrations.
```

**Caption (KO).**
```
광흡수 분광법(OAS): 가스가 각 파장의 빛을 얼마나 흡수하는지 측정합니다.
```
```
그 흡수 패턴으로 어떤 화학종이 얼마나 있는지 알 수 있습니다.
```

---

### Scene 3 — App tour, sidebar (0:25 → 0:40, 15 s)

**Film.**

1. Browser address bar → Streamlit Cloud URL → Enter.
2. App lands on Single OAS analysis.
3. Cursor pans the left sidebar slowly, top to bottom (≈ 5 s).
4. Briefly expand **Advanced fit configuration** to show the sliders,
   then collapse it again.
5. Hover near the green "ML checkpoint" pill at the bottom.

**Caption (EN, 3 blocks).**
```
Two modes in the sidebar: a single spectrum, or a time-series.
```
```
Advanced sliders let scientists tune the fit — defaults are fine for
most users.
```
```
The green status pills confirm the ML model and reference data are
loaded.
```

**Caption (KO).**
```
사이드바: 단일 스펙트럼 분석, 또는 시계열 분석 — 두 가지 모드.
```
```
Advanced fit configuration 슬라이더로 fit 을 세밀하게 조정할 수 있습니다.
```
```
좌측 하단의 녹색 상태 표시로 모델·데이터 준비 완료를 확인합니다.
```

---

### Scene 4 — Uploading your spectra (0:40 → 1:05, 25 s)

**Film.**

1. Stay on Single OAS analysis.
2. Fitting method = **Linear regression** (radio button on top).
3. Drag-and-drop `Source_70_2_00000.txt` into the **Reference I₀** drop
   zone. Caption is layered while the chip animates in.
4. Drag-and-drop `Source_70_2_00100.txt` into **Measured It**.
5. Preview chart renders. Hover legend briefly to highlight the two
   curves.

**Caption (EN, 3 blocks).**
```
Drag in two text files — the reference spectrum I₀ and your measurement.
```
```
The app reads them in any standard format: txt, csv, dat.
```
```
The preview shows reference (red) vs. measurement (blue) on a log axis.
```

**Caption (KO).**
```
텍스트 파일 두 개를 드래그하면 됩니다 — 기준 스펙트럼 I₀ 와 측정값.
```
```
일반적인 형식 모두 지원합니다 (txt, csv, dat).
```
```
빨강은 기준값, 파랑은 측정값. 로그 스케일로 함께 표시됩니다.
```

---

### Scene 5 — Linear regression (1:05 → 1:40, 35 s)

**Film.**

1. Click **Run linear regression analysis**.
2. Results panel slides in. Hold for 2 s.
3. Show metric tiles (R², RMSE, MAE, MAPE). Caption appears.
4. Click **Chemical extraction** tab. Hold 4 s.
5. Click **Validation overlay** tab. The dashed per-species traces are
   visible by default.
6. Click **Downloads** tab; cursor hovers over the CSV button.

**Caption (EN, 4 blocks — staggered).**
```
Linear regression: fits the measurement as a sum of known chemical
species spectra.
```
```
R² above 0.92 — the reconstruction matches the measurement very closely.
```
```
The Chemical extraction tab lists the eight species and their estimated
number densities.
```
```
Validation overlay shows measured vs reconstructed, plus each species'
contribution.
```

**Caption (KO).**
```
선형 회귀: 측정 스펙트럼을 알려진 화학종 스펙트럼의 합으로 해석합니다.
```
```
결정계수(R²) 0.92 이상 — 재구성이 측정값과 거의 일치합니다.
```
```
Chemical extraction 탭에 8개 화학종의 추정 농도가 표로 표시됩니다.
```
```
Validation overlay 에서 측정값 vs 재구성, 그리고 종별 기여도까지 한눈에 봅니다.
```

---

### Scene 6 — Machine learning + consent (1:40 → 2:10, 30 s)

**Film.**

1. Top of the page, switch Fitting method to **Machine learning**.
   Preview chart and inputs don't change.
2. Tick the consent checkbox **"Yes, contribute this analysis to the
   global model"** — the purple banner expands.
3. Click **Run machine learning analysis**.
4. Results render. Show that R² is lower than the LR run (this is
   intentional).
5. Click **Downloads** tab.
6. Click **📡 Submit this analysis to the global model**.
7. Linger on the green confirmation toast with the submission ID.

**Caption (EN, 4 blocks).**
```
Same UI, different brain — Machine learning replaces the fit with a
neural network.
```
```
The current model was trained on simulated spectra, so it doesn't yet
match real data perfectly.
```
```
With one click, you can contribute your analysis to the next model
release.
```
```
Submitted ✓ — your data joins the continual-learning corpus.
```

**Caption (KO).**
```
같은 화면, 다른 두뇌 — 머신러닝 모드는 신경망이 fit 을 대체합니다.
```
```
현재 모델은 시뮬레이션 데이터로 학습돼서, 실측에는 아직 완벽하지 않습니다.
```
```
동의 후 클릭 한 번이면, 이 분석이 다음 모델 학습에 포함됩니다.
```
```
Submitted ✓ — 데이터가 continual learning 코퍼스에 들어갔습니다.
```

---

### Scene 7 — Time-series (2:10 → 2:35, 25 s)

**Film.**

1. Sidebar → **Time-series OAS analysis**.
2. Fitting method = **Linear regression**.
3. In the file uploader, drag the whole `Source_70_2/` folder (or select
   all 344 files in the picker). Chip shows `📁 344 files loaded.`
4. Click **Run linear regression analysis**. The progress bar fills.
5. Results pane: metric tiles `Timepoints 343 · Detected species 5/8 ·
   Duration 343 s · Method Linear`.
6. **Trend** tab — log-scaled species trajectories.
7. Hover one species curve to show tooltip.

**Caption (EN, 3 blocks).**
```
Got a whole experiment? Drag a folder, hit Run.
```
```
343 frames processed in under a minute. Progress bar shows live status.
```
```
The Trend tab plots every species over time on a log axis.
```

**Caption (KO).**
```
실험 전체 폴더를 드래그 → Run 한 번이면 끝.
```
```
343개 프레임이 1분 내 처리됩니다. 진행률 바로 실시간 확인.
```
```
Trend 탭에서 모든 화학종의 시간 변화를 로그 스케일로 한눈에.
```

---

### Scene 8 — Continual learning explained (2:35 → 2:50, 15 s)

**Film.** Cut to a still slide. Use
[`docs/conference/key-visual.svg`](conference/key-visual.svg) as the
background and animate three bullets in sequentially (just fade them
in).

**Caption (EN, 3 blocks shown one at a time, with the diagram visible).**
```
Continual learning loop:
① You opt in and submit analyses.
```
```
② A weekly curation worker validates and packs them.
```
```
③ The next model release is fine-tuned on the growing corpus, and every
contributor is credited.
```

**Caption (KO).**
```
Continual learning 흐름:
① 동의 후 분석을 제출.
```
```
② 매주 큐레이션 워커가 검증해 정리.
```
```
③ 다음 모델 릴리스가 새 데이터로 fine-tune 되고, 기여자가 명시됩니다.
```

---

### Scene 9 — Outro (2:50 → 3:00, 10 s)

**Film.** End card. Three lines, static. Use the same gradient
background as the title card for visual symmetry.

**Caption (EN).**
```
Try it:     oas-spectrum-studio.streamlit.app
Source:     github.com/jongchan1999/oas-spectrum-studio
Request access via GitHub Issues.
```

**Caption (KO).**
```
체험:       oas-spectrum-studio.streamlit.app
소스:       github.com/jongchan1999/oas-spectrum-studio
접근 권한:  GitHub Issues 로 요청해주세요.
```

---

## 2. Caption style guide

Keep the entire video legible to someone who has *never* heard the terms
"optical absorption spectroscopy", "linear regression", or "neural
network".

- **One concept per caption.** Don't pack two ideas in one line.
- **No formulas.** If something is a formula, paraphrase it ("the model
  fits the measurement as a sum of known species spectra").
- **Active voice.** "The app reads them" beats "Files are read by the
  app".
- **Avoid acronyms** the first time. Spell "optical absorption
  spectroscopy" in Scene 2, then use "OAS" later.
- **Font**: Inter / Helvetica / Arial (whichever your tool offers).
  - English: 36 pt regular for body, 48 pt bold for the title card.
  - Korean: 32 pt regular for body, 44 pt bold for the title card.
- **Position**: lower-third for narration; top-third only for the title
  card and the outro.
- **Background**: 75 %-opaque dark rectangle behind every caption for
  contrast against a busy UI.
- **Duration**: each caption visible at least `length_in_chars × 0.06`
  seconds. A 60-character caption needs ≥ 3.6 s on screen.

## 3. Optional: 12-second silent GIF for the README hero

Drop this in `docs/assets/demo-hero.gif` and the README hero
auto-resolves it. Recipe with ScreenToGif:

1. `Recorder` → 1280 × 720 window, 24 fps, **place over the Streamlit
   app**.
2. Record this 12-second sequence (no cursor pauses):
   - 1 s — page loaded, single mode selected
   - 2 s — drop I₀ + It files (fast)
   - 2 s — preview chart renders
   - 1 s — Run button clicked
   - 3 s — Results panel scrolls in
   - 2 s — Click Validation tab — overlay appears
   - 1 s — hold on the final overlay
3. `Editor` → **Save as → GIF** → palette `Octree`, 64 colours, target
   **≤ 8 MB**. Save as `docs/assets/demo-hero.gif`.

## 4. Hosting + sharing

### YouTube (recommended)

1. Upload as **Unlisted** (link-only).
2. Title: `OAS Studio — silent 3-minute walkthrough`.
3. Description (first line is what appears in embed previews):
   ```
   A 3-minute silent walkthrough of OAS Studio — drop in spectra, get
   8-species concentrations, opt in to grow the next model.

   Try it:   https://oas-spectrum-studio.streamlit.app
   Source:   https://github.com/jongchan1999/oas-spectrum-studio
   ```
4. Chapters (paste timestamps in the description so YouTube renders the
   in-player chapter strip):
   ```
   0:00 Intro
   0:10 What is OAS?
   0:25 App tour
   0:40 Uploading spectra
   1:05 Linear regression
   1:40 Machine learning + consent
   2:10 Time-series
   2:35 Continual learning
   2:50 Outro
   ```
5. Tags: `optical absorption spectroscopy, OAS, NO2, ozone, plasma
   diagnostics, continual learning, Streamlit, ResNet, NNLS`.
6. After upload, copy the 11-char video ID (the part after `v=`).

### Drop the YouTube ID into the README

Edit [`README.md`](../README.md) once: search for `REPLACE_WITH_YT_ID`
and replace with the real ID. Both the hero "Watch the 3-minute demo"
link and the *At a glance* row resolve automatically. **Nothing else
needs to change.**

### Conference / lab share

- The Unlisted link works in slide PDFs, posters, and abstracts — no
  Google account required for viewers.
- Keep an MP4 backup on a USB at the venue (YouTube Studio →
  `Manage videos → ⋮ → Download`).

## 5. Things that must not appear in the recording

- The `[cl]` block of `secrets.toml` (it shows the anon key — minor risk
  but still). Close any Streamlit "Manage app" panel before recording.
- The Supabase dashboard with the **service_role** key revealed —
  *never* in any frame.
- The login form. Sign in before pressing Record.
- Other people's filenames in the time-series scene. The included
  `Source_70_2_*` set is fine.
- Browser tabs unrelated to the project (gmail, slack, etc.).
- The OS taskbar with personal app icons. Press F11 in Chrome for
  fullscreen if needed.

## 6. Post-recording polish (10 minutes)

In ScreenPal / Shotcut:

1. Trim every gap longer than 1 second.
2. Add 0.5 s cross-fades between scenes.
3. Drop captions on the lower-third using the style guide above.
4. Bake in the title and outro cards (10 s static + 10 s static).
5. Export as MP4 H.264, 1080p 30 fps. Target file size ≤ 50 MB so
   YouTube doesn't re-encode aggressively.

Total time from "press record" to "uploaded": about an hour. The script
above is meant to be filmed in one continuous take with the captions
added afterwards.
