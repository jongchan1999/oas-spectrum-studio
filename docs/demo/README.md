# Demo video drop folder

This folder will contain the OAS Spectrum Studio walkthrough video as a
self-contained MP4 — no YouTube account, no internet required for
playback.

## File naming convention

Whatever you record, **save it as exactly** `demo.mp4` here. The repo's
top-level README (and any PPT slide using a relative reference) loads
that exact filename, so no further edits are needed when the file is
dropped in.

```
docs/demo/
├── README.md           <- you're reading this
├── demo.mp4            <- ◀ drop your recorded MP4 here (LFS-tracked)
└── demo-thumbnail.png  <- optional poster frame for embeds
```

## How the video is referenced

| Place | Reference |
|---|---|
| README.md hero "▶ Watch the demo" link | `docs/demo/demo.mp4` |
| README.md "At a glance" row | `docs/demo/demo.mp4` |
| `<video>` element below the hero | `docs/demo/demo.mp4` |
| PowerPoint / Keynote slide | `Insert → Video → This Device → docs/demo/demo.mp4` |
| Conference handout USB | copy the file directly |

## Encoding recommendations

- **Container**: MP4 (H.264/AAC). Plays everywhere — Windows, macOS,
  Linux, iPad, PowerPoint embed, GitHub inline player.
- **Resolution**: 1920×1080 at 30 fps.
- **Bitrate**: ~4–6 Mbps for a clean 3-minute clip; final size ~25–55 MB.
- **Audio**: none (silent screencast with on-screen captions, per
  [`../DEMO_VIDEO_SCRIPT.md`](../DEMO_VIDEO_SCRIPT.md)). Strip the audio
  track entirely if your editor adds one by default.
- **Subtitles**: baked into the picture (no separate `.srt`). This keeps
  the file truly portable.

## Why MP4 + LFS rather than YouTube

- **Offline playable** — works without internet (USB at a conference,
  embedded in a PPT shared via email).
- **Reusable in slides** — PowerPoint / Keynote insert directly.
- **No third-party account** — no Google / YouTube login required for
  viewers. Useful for invited reviewers and external collaborators.
- **Repo size stays sane** — `*.mp4` is tracked via Git LFS
  (configured in [`../../.gitattributes`](../../.gitattributes)), so a
  fresh `git clone` is still fast and the binary lives in LFS storage.

## How to drop a new version in (one-time, ~3 minutes)

1. Make sure Git LFS is installed: `git lfs install` (one-time per machine).
2. Save your recording exactly as `docs/demo/demo.mp4`.
3. From the repo root:
   ```
   git add docs/demo/demo.mp4
   git commit -m "Add demo video"
   git push origin main
   ```
4. Confirm on GitHub: open the repo's README page in a browser — the
   `<video>` element below the hero should render with playback controls.

Replacing the video later? Save the new file at the same path and
repeat steps 3–4 — `git push` automatically supersedes the LFS object.

## Optional: shrink for conference handouts

If a venue caps file size (e.g. supplementary-material zips under 20 MB),
re-encode with `ffmpeg`:

```bash
ffmpeg -i demo.mp4 -vcodec libx264 -crf 28 -preset slow \
       -vf scale=1280:-2 -an demo-small.mp4
```

- `-crf 28`: lower bitrate, still readable.
- `scale=1280:-2`: drop to 720p.
- `-an`: strip any audio that snuck in.
- Result: a 3-minute clip lands around 8–12 MB.
