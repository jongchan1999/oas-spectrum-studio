# Demo recording — beginner's walkthrough

> Step-by-step for someone who has never recorded a screencast before.
> Pairs with [`DEMO_VIDEO_SCRIPT.md`](DEMO_VIDEO_SCRIPT.md) (the
> storyboard / what to film) — this file is **how to film it**.
>
> **Time budget (first time): ~4 hours total.**
>
> | Stage | Time |
> |---|---|
> | 1. Install tools | 20 min |
> | 2. Configure OBS | 15 min |
> | 3. Dry-run the storyboard | 30 min |
> | 4. Record (1–3 takes) | 30 min |
> | 5. Edit + add captions in Shotcut | 90 min |
> | 6. Export + verify + push | 20 min |

---

## 1. Install the two tools you need

You only need **two** free programs. Both are Windows-native, no signup.

### A. OBS Studio — for recording

- **Download:** <https://obsproject.com/download> → "Windows" → ~140 MB installer.
- **Why:** the standard free screen recorder. No watermark, no time limit,
  1080p 30 fps MP4 out of the box.
- **Install:** double-click → Next/Next/Next → Finish. Skip the
  "Auto-Configuration Wizard" at first launch (we'll set it up by hand
  in section 2).

### B. Shotcut — for editing + captions

- **Download:** <https://shotcut.org/download/> → "Windows 64-bit installer"
  → ~150 MB.
- **Why:** free, captions/text overlays built in, exports to the same
  MP4 H.264 format. Lighter than DaVinci Resolve and doesn't need a
  beefy GPU.
- **Install:** double-click → Next/Finish.

> **Optional**: [ScreenToGif](https://www.screentogif.com) (3 MB) if you
> want to make the 12-second silent GIF for the README hero later. Not
> needed for the main video.

That's it. No accounts, no plugins.

---

## 2. Configure OBS once (15 minutes)

Open OBS Studio. Bottom-right panel has **Sources**, **Audio Mixer**,
**Scene Transitions**, **Controls**.

### 2.1 Settings → Output

Click **Settings** (bottom-right) → **Output** tab:

| Field | Value |
|---|---|
| Output Mode | **Simple** |
| Recording Path | `C:\Users\kimjo\Desktop\OAS_demo\raw\` (create this folder first) |
| Recording Quality | **High Quality, Medium File Size** |
| Recording Format | **mp4** |
| Encoder | Software (x264) — change to "NVENC H.264" if you have an NVIDIA GPU |

### 2.2 Settings → Video

| Field | Value |
|---|---|
| Base (Canvas) Resolution | **1920×1080** |
| Output (Scaled) Resolution | **1920×1080** |
| Common FPS | **30** |

### 2.3 Settings → Audio

Set **all** four audio device dropdowns to **Disabled**.
(The demo is silent — no mic noise, no system beeps in the file.)

Click **OK**. Settings done.

### 2.4 Add a source

In the **Sources** panel (bottom-centre), click **+** → choose one:

- **Display Capture** — captures the entire monitor. Easiest. Pick this
  if you can dedicate one screen to the recording.
- **Window Capture** — captures only Chrome. Use this if you must keep
  other apps open on the same screen.

For **Window Capture**, in the dialog: Window → pick the Chrome window
showing the Streamlit app. Capture Method = "Windows 10 (1903 and up)".

You should now see your screen mirrored in the OBS preview area.

### 2.5 Test record (30 seconds)

- Hit **Start Recording** (bottom-right Controls panel).
- Move the mouse around for 5 seconds.
- Hit **Stop Recording**.
- Open the file in `C:\Users\kimjo\Desktop\OAS_demo\raw\`. Should be a
  small MP4 that plays in Movies & TV.

If the file is empty or there's no recording, the most common cause is
"Display Capture" returning a black screen on a multi-monitor laptop.
Switch to **Window Capture** and try again.

---

## 3. Dry-run the storyboard (30 minutes — DO NOT skip)

This is the most important step. Walk through all 9 scenes in
[`DEMO_VIDEO_SCRIPT.md`](DEMO_VIDEO_SCRIPT.md) **without recording**, to
make sure every click works and you know the order. First-time recordings
where you skip this step usually have 4–5 retakes.

### Pre-flight checklist

- [ ] OAS_demo/ folder on Desktop has the 3 files (already staged for you):
      `Source_70_2_00000.txt`, `Source_70_2_00100.txt`, `Source_70_2/` (344 files).
- [ ] Open Chrome → <https://oas-spectrum-studio.streamlit.app> → log in
      with `sanghoopark` (login screen is **not** in the recording).
      Wait for the hero card to fully render.
- [ ] Chrome bookmarks bar hidden: `Ctrl+Shift+B`.
- [ ] Press `F11` for fullscreen Chrome (hides URL bar and taskbar).
- [ ] Windows Focus Assist on: Start → search "Focus" → set to **Alarms only**.
- [ ] Close Slack, Discord, KakaoTalk, Gmail tabs. Anything that pings.
- [ ] Disable notifications: Win + A → Focus → Alarms only.
- [ ] Set mouse cursor to "highlight on click" if you want clicks visible —
      Windows Settings → Mouse Pointer → Pointer indicator (optional).

### Walk-through (no recording)

Go through every scene in the storyboard, performing each click. Watch
your wrists — slow, deliberate moves read much better than fast ones.

The two trickiest moments:

- **Scene 6 (consent + submit)**: the consent checkbox must be ticked
  **before** clicking Run, or the Submit button is greyed out.
- **Scene 7 (time-series)**: dragging 344 files at once is fastest with
  the folder picker. Click "Browse files" → navigate to
  `Desktop\OAS_demo\Source_70_2\` → `Ctrl+A` → Open.

If anything breaks (missing column, app not responding, file rejected),
fix it now. Don't fix issues mid-recording.

---

## 4. Record (30 minutes including retakes)

Now do the same walk-through, but with OBS recording.

### 4.1 Start

- OBS window visible on a second monitor or behind Chrome (you'll alt-tab
  to it only at start/end).
- Press **Start Recording** in OBS → switch to Chrome → `F11` →
  pause 2 seconds before doing anything (gives you a clean head frame to
  cut from).

### 4.2 Filming tips

- **Pause 2 seconds on every important element** (button, metric tile,
  tab). The caption you add later needs that time to be readable.
- **Don't speak.** Don't even whisper. The mic is disabled but you might
  pick up keyboard noise resonating.
- **One smooth take is better than 5 perfect-but-stitched takes.** If
  you fluff a click, just pause 3 seconds, redo it, keep going. You'll
  trim the bad attempt in editing.
- **No URL exposed in the recording**: the F11 fullscreen takes care of
  the address bar; double-check before recording.

### 4.3 Stop

After the time-series Trend tab (scene 7), wait 2 seconds, then
`Alt+Tab` to OBS → **Stop Recording**. The remaining scenes (8 outro
diagram, 9 outro card) can be filmed as **separate short clips** or
built entirely in Shotcut as still cards — easier than animating them in
real time.

### 4.4 Quick check

Open the MP4 from `Desktop\OAS_demo\raw\`. Does the playback look smooth?
Any dropped frames or black flickers? If yes, retake the scene only
(OBS records as separate files each time you Start/Stop).

---

## 5. Edit + add captions in Shotcut (90 minutes)

This is the part that takes the most time the first time. Don't rush;
the captions are the entire point of a silent screencast.

### 5.1 Open the project

- Launch Shotcut.
- File → **New Project** → name "oas_demo", set Video Mode →
  "HD 1080p 30fps" → Start.
- Drag your raw MP4 from `Desktop\OAS_demo\raw\` into the **Source**
  panel (top-left).
- Click the source → **B button** ("Append to Playlist") or drag the clip
  to the timeline at the bottom.

### 5.2 Trim long pauses

- Click on the timeline ruler to move the playhead.
- Press **S** to split the clip at the playhead.
- Click the unwanted segment → **Delete** (the keyboard key).
- Repeat for every pause > 1 second.

Goal: total length 2:30 → 3:00 minutes.

### 5.3 Add a caption (do this once, then duplicate)

Select the first clip on the timeline. In the **Filters** panel
(top-right area):

1. Click **+** to add a filter.
2. Search "Text" → pick **Text: Simple**.
3. Type your caption in the **Text** field. Use the storyboard's caption
   for that scene.
4. Settings:
   - **Font**: Arial (or Inter if installed)
   - **Size**: 36 for body, 48 for title card
   - **Position**: drag the on-canvas box to the lower-third
   - **Background colour**: black, **75% opacity** (RGBA: 0,0,0,191)
   - **Outline**: 1 px black, optional
5. To control when the caption shows: in **Filters**, with the text
   filter selected, look for the keyframe icon (top-right of the
   filter). Set the text to fade in over 0.3 s, hold, fade out over
   0.3 s. Or just split the underlying clip so the filter only applies
   to the portion you want.

### 5.4 Duplicate the caption style

For every subsequent caption: right-click your first caption filter →
**Copy filters** → click the next clip segment → right-click → **Paste
filters** → edit the text only. Saves you re-doing the styling.

### 5.5 Title + outro cards

For scenes 1 and 9, you don't need video footage. Use Shotcut's
**Other → Color** generator:

- File → **Open Other** → **Color** → pick a dark gradient or solid
  navy. Length = 10 seconds. Add to timeline.
- Add **Text: Simple** filter for the title text.
- Place at the very start (scene 1) and the very end (scene 9).

### 5.6 Cross-fades between scenes

Drag the start of one clip to **overlap** the end of the previous by
~15 frames (0.5 seconds). Shotcut auto-creates a cross-fade.

### 5.7 Preview

Play the whole thing from start to finish at least twice. Things to
check:

- Every caption is readable for ≥ 2 seconds.
- No frame shows: URL bar, login screen, `secrets.toml`, Supabase
  dashboard, personal taskbar icons, unrelated browser tabs.
- The total length is between **2:30 and 3:15**.

### 5.8 Bilingual (optional)

If you want a Korean cut: duplicate the entire timeline, swap each
English caption text for the Korean caption from the storyboard.
Export as `demo_ko.mp4`. The main file stays `demo.mp4` (English).

---

## 6. Export + verify + push (20 minutes)

### 6.1 Export from Shotcut

Top toolbar → **Export**. Settings:

| Field | Value |
|---|---|
| Preset | **YouTube** (it's just a name — gives the right H.264 settings) |
| Format | mp4 |
| Resolution | 1920 × 1080 |
| Aspect ratio | 16:9 |
| Frame rate | 30 |
| Codec | libx264 |
| Rate control | **Average Bitrate**, ~5000 kbps (5 Mbps) |
| Audio tab | **Disable audio** (uncheck the audio output checkbox) |

Filename: **`demo.mp4`** (exact name — the README's `<video>` block
references this). Save to:

```
Y:\Share\1_개인자료\김종찬\논문\webpage_OAS\docs\demo\demo.mp4
```

Click **Export File** → wait 2–5 minutes for the encode.

### 6.2 Verify the export

Three checks before pushing:

```powershell
$mp4 = "Y:\Share\1_개인자료\김종찬\논문\webpage_OAS\docs\demo\demo.mp4"
# 1. File exists and is reasonable size (25–55 MB target)
Get-Item $mp4 | Select-Object Name, @{n='SizeMB';e={[math]::Round($_.Length/1MB,1)}}
# 2. Plays locally
Start-Process $mp4
# 3. No audio track (use ffprobe if installed, or just trust Shotcut)
```

If the file is > 80 MB, the bitrate was too high — re-export at 3 Mbps.
If < 10 MB, probably the audio track sneaked in and the video stream is
under-allocated; re-export with audio explicitly disabled.

### 6.3 Push via Git LFS

Just tell me "demo.mp4 saved" and I'll run the whole sequence:

```powershell
# (I will run this on your behalf — listed for transparency)
cd "Y:\Share\1_개인자료\김종찬\논문\webpage_OAS"
git lfs install
git add docs/demo/demo.mp4
git commit -m "Add 3-minute silent demo video"
git push origin main
git tag v1.0-demo
git push origin v1.0-demo
```

### 6.4 Final sanity check

Open the repo on GitHub:

- The `<video>` block under the hero should now show a playback bar
  (Chrome renders it inline; Firefox sometimes only offers a download).
- The "▶ Watch the 3-minute demo" link should download or stream.
- The tag `v1.0-demo` should appear in Releases.

---

## Common gotchas

| Symptom | Fix |
|---|---|
| OBS records black screen | Switch source from "Display Capture" to "Window Capture" |
| Audio in the file | Settings → Audio → set all four devices to Disabled, **re-record** (can't strip in Shotcut easily) |
| File > 100 MB | Lower bitrate to 3 Mbps in Shotcut export, or run `ffmpeg -i demo.mp4 -b:v 2M -an demo_small.mp4` |
| Captions cut off at edges | Drag the on-canvas text box inward — keep 80 px margin from each side |
| Streamlit app slow / cold | Open it 30 s before recording; the first request after sleep takes ~10 s |
| Cursor invisible in recording | OBS → Sources → right-click your capture source → Properties → tick **Capture Cursor** |
| Drag-and-drop file picker doesn't accept the txt | Streamlit's drop zone wants the file dropped on the *dashed border*, not the button beside it |

---

## You finished one. What now?

1. Tell me "demo.mp4 saved at `docs/demo/demo.mp4`" — I'll commit, push,
   tag.
2. Open GitHub, refresh the README, watch the video render inline.
3. Move on to [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) for the
   public-release punch list (rotate passwords, run through licence
   confirmation, send invite emails).

That's the entire path from "I've never recorded a screencast" to
"public demo on GitHub". The hardest part is the first dry-run; once
you've done that, the rest is mostly mechanical.
