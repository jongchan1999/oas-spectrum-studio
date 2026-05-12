# Conference 1-pager — slide / poster outline

Drop-in copy + layout cues for a single conference slide or A0 poster
section showcasing the tool. Convert this Markdown to PowerPoint /
Keynote / LaTeX Beamer / PDF using whatever tool you prefer; the
content / order is what matters.

## Layout (single slide)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   ◆ TITLE BAR (deep indigo→violet gradient)                          │
│   OAS Studio — a community-driven analyser for optical               │
│   absorption spectroscopy.                                            │
│   <small> Jongchan Kim · KAIST plasma group · 2026 </small>          │
│                                                                      │
│  ┌───────────────────────────────────┬──────────────────────────┐   │
│  │ ● PROBLEM (3 lines)               │  KEY VISUAL              │   │
│  │   OAS analyses are scattered      │  ┌────────────────────┐  │   │
│  │   across notebooks, lab tools,    │  │  key-visual.svg     │  │   │
│  │   per-PI scripts.                 │  └────────────────────┘  │   │
│  │                                   │   spectroscopy → image   │   │
│  │ ● APPROACH (3 lines)              │   → CNN → 8 species      │   │
│  │   One Streamlit app for           │                          │   │
│  │   single + time-series + ML +     │  QR CODE → live app      │   │
│  │   continual learning.             │  ┌───┐                   │   │
│  │                                   │  │QR │ oas-spectrum-    │   │
│  │ ● RESULTS                         │  └───┘ studio.streamlit │   │
│  │   Linear: R² > 0.92 (live data)   │       .app               │   │
│  │   ML: re-trained per release      │                          │   │
│  │                                   │  github.com/jongchan...  │   │
│  └───────────────────────────────────┴──────────────────────────┘   │
│                                                                      │
│   FOOTER (one line)                                                  │
│   <small>Try it: <URL>  ·  Source: <GitHub URL>  ·  Demo: <YT> </small> │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Copy blocks (English)

### Title

> **OAS Studio — a community-driven analyser for optical absorption spectroscopy.**

### Subtitle / author line

> Jongchan Kim · KAIST plasma group · 2026

### Problem

> Optical absorption spectroscopy analyses are scattered across
> notebooks, lab-private tools, and per-PI scripts — making
> reproducibility and cross-group comparison painful.

### Approach

> A single Streamlit app covers both **linear regression** (positive
> NNLS with iterative refit) and **machine learning** (ResNet101)
> inference for single spectra and time-series. Users opt in to
> contribute consented runs to a continual-learning corpus; each model
> release credits its contributors.

### Results

> - **Linear regression**: R² > 0.92 on real laboratory OAS data,
>   sub-second per frame.
> - **ML inference**: end-to-end pipeline live; first model is the
>   simulation-trained baseline, refined per release.
> - **Submission pipeline**: end-to-end (app → Supabase → curated
>   dataset.npz) verified.

### Call to action

> Live app: `oas-spectrum-studio.streamlit.app`
> Source: `github.com/jongchan1999/oas-spectrum-studio`
> 3-min demo: `<YouTube unlisted link>`

## Copy blocks (Korean)

### 제목

> **OAS Studio — 커뮤니티가 함께 키우는 광흡수 분광 분석 도구.**

### 부제 / 저자

> 김종찬 · KAIST 플라즈마 그룹 · 2026

### 문제

> 광흡수 분광(OAS) 분석은 연구실마다 다른 노트북, 사적 도구, PI 별 스크립트에
> 흩어져 있어 재현성과 그룹 간 비교가 어렵습니다.

### 접근

> 단일 Streamlit 앱이 **선형 회귀**(positive NNLS + 반복 refit)와 **기계학습**
> (ResNet101) 추론을 단일 스펙트럼과 시계열에 동일하게 적용. 사용자는 동의 후
> 분석을 continual-learning 코퍼스에 기여할 수 있고, 모델 릴리스마다 기여자가
> 명시됩니다.

### 결과

> - **선형 회귀**: 실측 OAS 데이터에서 R² > 0.92, frame 당 1초 미만.
> - **ML 추론**: 파이프라인 정상 동작; 1차 모델은 시뮬레이션 기반 baseline,
>   릴리스마다 fine-tune.
> - **제출 파이프라인**: app → Supabase → curated dataset.npz 까지 end-to-end
>   검증 완료.

### Call to action

> 라이브 앱: `oas-spectrum-studio.streamlit.app`
> 소스: `github.com/jongchan1999/oas-spectrum-studio`
> 3분 데모: `<YouTube unlisted 링크>`

## Visual guidelines

- **Palette** mirrors the app:
  - Hero gradient: `#1e1b4b → #4f46e5 → #7c3aed → #a21caf`
  - Accent: `#f97316`
  - Ink: `#0f172a`
- **Type**: Inter (or system sans-serif), JetBrains Mono for code/URLs.
- Embed [`key-visual.svg`](key-visual.svg) on the right half — it scales
  cleanly to A0.
- For the QR code, generate from the live URL via any free generator
  (e.g. `https://qrcode.show/oas-spectrum-studio.streamlit.app`) and
  drop the PNG in the right column.

## Export pipeline (suggested)

1. Open `key-visual.svg` in Figma / Inkscape; place title and copy
   blocks around it on a 16:9 frame (1920 × 1080).
2. Export as PDF for the talk + as PNG (300 dpi) for the poster preview.
3. Drop the same PDF into the GitHub README under `docs/conference/`
   so attendees who scan the QR can grab the slide afterwards.
