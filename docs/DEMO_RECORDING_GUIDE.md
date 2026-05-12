# Demo recording — beginner's walkthrough

> Step-by-step guide for someone who has **never** recorded a screencast
> before. Pairs with [`DEMO_VIDEO_SCRIPT.md`](DEMO_VIDEO_SCRIPT.md), which
> tells you **what to film**; this file tells you **how to film it**.
>
> Reading time: 20 min. Total work time first attempt: 3–4 hours.
> Returning users will be ~1 hour.

---

## Time budget at a glance

| Stage | First time | After practice |
|---|---|---|
| 1. Choose + install tools | 20 min | — |
| 2. Configure OBS (one-time) | 15 min | — |
| 3. Compose your screen | 10 min | 2 min |
| 4. Dry-run the storyboard | 30 min | 10 min |
| 5. Record (1–3 takes) | 30 min | 15 min |
| 6. Edit + add captions | 90 min | 30 min |
| 7. Export + verify | 15 min | 5 min |
| 8. Hand off to me for push | 5 min | 5 min |

The big lift is captions in stage 6 — there are 30+ caption blocks in
the storyboard and you'll spend the most time on them. Everything else
is mechanical once you've done it once.

---

# Part A — Tools

## A.1 What kind of program do I need?

Two separate jobs, two separate programs:

| Job | What it does | Examples |
|---|---|---|
| **Recorder** | Captures your screen + (optionally) mic to an MP4 file. | OBS Studio, ShareV, ScreenPal, Bandicam, Xbox Game Bar |
| **Editor** | Trims clips, adds text captions/overlays, exports the final MP4. | Shotcut, DaVinci Resolve, ScreenPal Editor, Adobe Premiere, CapCut |

You need **one from each column**. Some tools (ScreenPal, Camtasia) do
both jobs in one app — convenient for true beginners but limited or paid.

## A.2 Recorder — comparison & why I recommend OBS Studio

| Tool | Cost | Limit | Watermark | Quality | Notes |
|---|---|---|---|---|---|
| **OBS Studio** ⭐ | Free | None | None | 1080p 60fps | Industry standard. Steep first-time setup but everything is exposed. **Pick this.** |
| ShareX | Free | None | None | 1080p 30fps | Great for short GIFs/clips. UI is dated and the recorder is a side-feature. |
| ScreenPal (browser) | Free / paid | 15 min free | Free tier yes | 720p free / 1080p paid | Easiest UI of any tool, captions built-in. Free tier is too short for our 3-min demo + retakes + watermarked. |
| Bandicam | Paid ($40) | None paid | Trial yes | 1080p 30fps | Old reliable; no reason to pay vs free OBS for this task. |
| Xbox Game Bar (Win+G) | Free, pre-installed | Up to 4 hr | None | Variable | Only captures one window at a time, can't change resolution, can't filter audio. Skip. |

**Recommended: OBS Studio.** Reasons specific to your case:
- Your demo is **silent** — OBS lets you set every audio device to
  "Disabled" so there's zero chance mic noise sneaks in. Browser tools
  often record system audio by default.
- Your demo is **3 minutes long** with possible retakes — ScreenPal's
  free 15-min cap is fine in theory but stressful in practice.
- You'll need **window-only capture** (so the OBS app itself doesn't
  appear in the recording) — OBS does this; many simpler tools don't.

The trade-off is OBS has more knobs. The setup section below covers them
all in order; you only do it once.

## A.3 Editor — comparison & why I recommend Shotcut

| Tool | Cost | Difficulty | Captions | Export quality | Notes |
|---|---|---|---|---|---|
| **Shotcut** ⭐ | Free | Beginner-friendly | Built-in "Text: Simple" filter | 1080p H.264 mp4 | Open-source. Picks up where OBS leaves off. **Pick this.** |
| DaVinci Resolve | Free | Steep | Yes, very capable | Best in class | Hollywood-grade. Overkill, slow on lower-spec machines, requires GPU. |
| ScreenPal Editor | Browser, in same app | Trivial | Yes, drag-on text | 720p/1080p | If you used ScreenPal to record, just continue here. |
| CapCut Desktop | Free | Easy | Auto-caption, AI features | 1080p | Aimed at vertical mobile content; horizontal works but UI is busy. |
| Adobe Premiere Pro | $23/mo | Steep | Yes | Best | Subscription not worth it for one video. |

**Recommended: Shotcut.** Reasons:
- Free, no signup, no internet required after install.
- "Text: Simple" filter lets you copy-paste caption style across clips
  (huge time-saver — you have 30+ captions).
- Exports MP4 H.264 at any bitrate, audio strip toggle is one click.
- Lightweight (~150 MB) and runs on any laptop.

The only real alternative for someone in your position is **ScreenPal
all-in-one** if you don't mind the 15-min cap and watermark for free tier
— but you'd need to pay $4/month to get a clean export. So OBS + Shotcut
remains the right combination.

---

# Part B — Install

## B.1 OBS Studio (~5 minutes)

### Download

1. Open <https://obsproject.com/download> in a browser.
2. Click the big purple **"Windows"** button (the page auto-detects your OS).
3. The installer is named `OBS-Studio-XX.X.X-Windows-Installer.exe`,
   roughly **140 MB**. Save to Downloads.

### Install

4. Double-click the installer. Windows may show a SmartScreen warning
   ("Windows protected your PC"). Click **More info** → **Run anyway**.
5. Click **Next** → **I Agree** → **Next** (default install location is
   `C:\Program Files\obs-studio` — fine) → **Install** → **Finish**.

### First launch — choose the right mode

6. OBS opens with an **Auto-Configuration Wizard**.
7. Choose **"Optimise just for recording, I will not be streaming"** →
   **Next**.
8. Resolution: **1920×1080**, FPS: **30** → **Next**.
9. Wizard runs benchmarks for 30 s and recommends settings. Click
   **Apply Settings**.

You're now at the main OBS window. Don't touch anything yet — section
C below configures everything explicitly.

## B.2 Shotcut (~5 minutes)

### Download

1. Open <https://shotcut.org/download/> in a browser.
2. Scroll to **"Windows installer"** under the latest release. Pick the
   **64-bit installer .exe** (filename like
   `shotcut-win64-XXXXXXXX.exe`, ~150 MB). Save to Downloads.

### Install

3. Double-click the installer. SmartScreen → **More info** → **Run anyway**
   (same as OBS).
4. Next → I Agree → Next → Install → Finish.

### First launch

5. Open Shotcut. Window layout: media library (top-left), preview
   (top-right), timeline (bottom), filters/properties (bottom-right).
6. Don't create a project yet — we'll come back here in Part F.

---

# Part C — Configure OBS (one-time, 15 minutes)

OBS has four settings categories you care about: **Output**, **Video**,
**Audio**, and the **Source** you add at the end. Settings menus first,
then the source.

## C.1 Open Settings

Bottom-right of the OBS window has a **Controls** panel. Click
**Settings** (the gear icon). A dialog opens with a left-side category
list.

## C.2 Settings → Output

Click **Output** in the left sidebar.

| Section | Field | Value | Why |
|---|---|---|---|
| Top | Output Mode | **Simple** | "Advanced" exposes 30 more knobs you don't need. |
| Recording | Recording Path | **`C:\Users\kimjo\Desktop\OAS_demo\raw`** | Easy to find. Create this folder first via Explorer if it doesn't exist. |
| Recording | Recording Quality | **High Quality, Medium File Size** | Balanced — too low looks pixelated on UI text. |
| Recording | Recording Format | **mp4** | The format Shotcut and the README's `<video>` block expect. |
| Recording | Encoder | **Software (x264)** unless you have an NVIDIA GPU, then **NVENC H.264** | Hardware encoder is faster but requires a recent NVIDIA card. |

> ⚠ **mp4 vs mkv:** OBS warns that mp4 can become unrecoverable if the
> program crashes mid-recording. For a 3-minute supervised recording
> this is fine. If you want belt-and-suspenders, set format to **mkv**
> here, then convert to mp4 with **File → Remux Recordings** in OBS
> after stopping (lossless, takes 5 seconds).

## C.3 Settings → Video

Click **Video** in the left sidebar.

| Field | Value | Why |
|---|---|---|
| Base (Canvas) Resolution | **1920×1080** | The canvas — internal working area. |
| Output (Scaled) Resolution | **1920×1080** | The file's actual resolution. Match these two so nothing is resampled. |
| Downscale Filter | (anything) | Irrelevant when base == output. |
| Common FPS Values | **30** | Smooth enough for UI demos. 60 fps doubles file size for no benefit on static screencasts. |

## C.4 Settings → Audio

Click **Audio** in the left sidebar. Section **Global Audio Devices**:

| Device | Set to |
|---|---|
| Desktop Audio | **Disabled** |
| Desktop Audio 2 | **Disabled** |
| Mic/Auxiliary Audio | **Disabled** |
| Mic/Auxiliary Audio 2 | **Disabled** |

All four to **Disabled**. The demo is silent — no Windows ding, no fan
noise, no keyboard click in the file. (You can verify after recording
by right-clicking the MP4 → Properties → Details → no audio streams.)

Click **OK** at the bottom to save all settings.

## C.5 Add a video source

Back at the main OBS window. The **Sources** panel is at the
bottom-middle.

1. Click the **+** button at the bottom of the Sources panel.
2. Pick **Window Capture**. (Not Display Capture — Window Capture
   ignores everything outside the chosen window, so OBS itself won't
   appear in the recording even if it's visible on your screen.)
3. Dialog: name it `Chrome`, click **OK**.
4. Properties dialog opens:
   - **Window**: pick the Chrome window showing the Streamlit app.
     Format is `[chrome.exe]: <tab title> - Google Chrome`.
   - **Capture Method**: `Windows 10 (1903 and up)`.
   - **Window Match Priority**: `Match title, otherwise find window of
     same type`.
   - **Capture Cursor**: ✅ ticked.
   - **Client Area**: ✅ ticked (excludes the title bar and tab strip
     from capture).
5. Click **OK**.

The OBS preview area should now show your Chrome window mirrored. Resize
or position the source in the preview if needed (red bounding box).

> 💡 If you go full-screen later with F11, the Chrome capture follows
> automatically. If Chrome flickers black in the preview, switch
> Capture Method to **BitBlt** in the properties dialog.

## C.6 Test record (30 seconds)

In the **Controls** panel (bottom-right), click **Start Recording**.

- The status bar (very bottom of OBS) shows recording time counting up
  and `REC` in red.
- Wave the mouse around in Chrome for 5 seconds.
- Click **Stop Recording**.

Open `C:\Users\kimjo\Desktop\OAS_demo\raw\` in Explorer. You should see
a file named like `2026-05-12 22-30-15.mp4`. Double-click → it opens in
Films & TV (Windows) and plays smoothly. If it does — you're done with
setup.

### What to do if the test record is broken

| Symptom | Cause | Fix |
|---|---|---|
| Black screen in file | Window Capture failed | Properties → Capture Method = `BitBlt` |
| OBS controls appear in file | You picked Display Capture instead of Window Capture | Delete the source, add **Window Capture** instead |
| File 0 bytes | Wrong recording path / no write permission | Pick a path inside your user folder, e.g. Desktop |
| Mouse cursor invisible | "Capture Cursor" unticked | Source → Properties → tick Capture Cursor |
| Video stutters | Software encoder + heavy CPU | Switch to NVENC if you have NVIDIA, or close other apps |

---

# Part D — Compose your screen (10 minutes)

This is the most-skipped step. A well-composed screen looks
"professional" with zero editing; a busy screen looks amateur even with
perfect captions.

## D.1 Single-monitor layout (most common)

You need to record one Chrome window while controlling OBS without OBS
appearing in the recording. Three options:

**Option 1 — Full-screen Chrome (recommended).** Press **F11** in Chrome
to enter full-screen mode (hides tab bar, address bar, bookmarks,
Windows taskbar). OBS Window Capture follows. To control OBS, press
**Alt+Tab** → OBS becomes the front window. Recording continues
uninterrupted. Press Alt+Tab again to return to Chrome.

**Option 2 — Chrome maximised + OBS minimised.** Maximise Chrome, then
press the OBS taskbar icon to minimise it. Start/stop recording from
the system tray right-click menu on the OBS icon.

**Option 3 — OBS hotkeys.** Settings → Hotkeys → assign **Start
Recording** to `Ctrl+Shift+F9` and **Stop Recording** to
`Ctrl+Shift+F10`. Now you never have to look at OBS during a take.
Recommended once you're past your first recording.

## D.2 Dual-monitor layout (best)

If you have two monitors:

- **Monitor 1 (primary, larger)**: Chrome with Streamlit, full-screen.
- **Monitor 2 (secondary)**: OBS, Streamlit reference page, the demo
  storyboard PDF, your scratchpad — anything you might glance at
  during recording.

Window Capture only records Chrome, so monitor 2 is invisible to the
file.

## D.3 What must NOT appear in the recording

The demo will be public on GitHub. Audit your Chrome window before
pressing record:

| Item | How to hide |
|---|---|
| Bookmarks bar | `Ctrl+Shift+B` to toggle |
| URL bar | `F11` for full-screen Chrome |
| Other tabs | Open Streamlit in a **new window** (`Ctrl+N`) with only that tab |
| Login screen of the Streamlit app | Log in **before** pressing Record |
| Other apps' notifications | Settings → System → Notifications & actions → Focus Assist → **Alarms only** |
| Windows taskbar | F11 full-screen hides it |
| Personal Chrome profile photo / name | Open Chrome in **Guest mode** (top-right profile → Open Guest window) or use a fresh profile |
| Streamlit "Manage app" panel | Close it; it shows your account email |
| Supabase dashboard with the service_role key revealed | Don't open Supabase at all during the recording |
| Browser extensions in the toolbar | Right-click each → Hide in Chrome menu, or use Guest mode |
| Open Notepad / VS Code with random text | Close all unrelated windows |

## D.4 Mouse cursor settings

Two Windows settings worth changing for clarity:

1. **Larger cursor (optional).** Settings → Accessibility → Mouse pointer
   and touch → Size = 2 (one notch up). Makes the cursor easier to
   follow on a 1080p recording.
2. **Click highlight.** Use [PowerToys → Mouse Highlighter](https://github.com/microsoft/PowerToys)
   (free Microsoft tool, optional). It pulses a circle on click,
   so viewers can see exactly when you clicked. Default shortcut is
   `Win+Shift+H` to toggle.

If you don't want to install PowerToys, fine — just click deliberately.

---

# Part E — Dry-run the storyboard (30 minutes — DON'T skip)

Walk through every scene in
[`DEMO_VIDEO_SCRIPT.md`](DEMO_VIDEO_SCRIPT.md) **without recording**.
This catches issues before you waste tape on them.

## E.1 Pre-flight checklist

- [ ] OAS_demo/ folder on Desktop has the 3 files (already staged for you):
      `Source_70_2_00000.txt`, `Source_70_2_00100.txt`, `Source_70_2/`
      (the folder with 344 files).
- [ ] Chrome → <https://oas-spectrum-studio.streamlit.app> → log in
      with `sanghoopark`. Wait for the hero card to fully render.
      Cloud apps sleep after 20 min idle; the first request after sleep
      takes ~10 s.
- [ ] Bookmarks bar hidden (`Ctrl+Shift+B`).
- [ ] Focus Assist → Alarms only.
- [ ] Slack, Discord, KakaoTalk, Gmail tabs **closed**.
- [ ] Chrome in **Guest mode** if you have a personal profile picture.
- [ ] OBS source `Chrome` shows the live app in the preview.

## E.2 Walk through every scene

Go scene-by-scene in the storyboard. Click every button, drag every
file, switch every tab. **Without** pressing Record. You're looking for:

- Files that don't load (wrong path, wrong format).
- Tabs that don't appear (you forgot to run linear regression first).
- Sliders that reset between modes.
- Buttons that are greyed out (consent checkbox not ticked).

### Two non-obvious gotchas

1. **Scene 6 (ML + Submit).** The Submit button is **only enabled after**
   you (a) tick the consent checkbox, (b) click Run ML, and (c) wait
   for the results to render. If you click Submit before any of these,
   nothing happens.

2. **Scene 7 (time-series upload).** Streamlit's drag-and-drop accepts
   **multiple files**, not a folder. Click "Browse files" → navigate
   to `Desktop\OAS_demo\Source_70_2\` → `Ctrl+A` to select all 344 →
   Open. The chip shows `📁 344 files loaded.`

## E.3 Practice the cursor pace

Open the storyboard side-by-side and mime each caption's screen
action. **Pause 2 seconds on every important element** — viewers need
that time to read the caption you'll add later. Hovering on a result
metric for half a second is too fast; for three seconds is just right.

Tip: count "one mississippi, two mississippi" silently after each
click. After 3–5 of these, your timing will be naturally right.

---

# Part F — Record (30 minutes including retakes)

You've done the dry run. Now do the same thing with Record on.

## F.1 Start a take

1. In OBS, click **Start Recording**.
2. Alt-Tab to Chrome.
3. Press **F11** for full-screen.
4. Wait **2 full seconds** with the cursor parked in a neutral spot
   before doing anything. This gives editing a clean "head" frame to
   cut from.
5. Begin Scene 1.

## F.2 Filming guidelines

- **Move slowly.** Cursor speed should feel "deliberate" — about half
  your normal browsing speed. Fast cursor movement reads as nervous
  and is hard to follow.
- **Pause on important elements.** 2-second hold on each click target,
  3-second hold on each result panel, 4-second hold on the species
  metric tiles in Scene 5.
- **Don't fix mistakes.** If you fluff a click, just pause 3 seconds
  (long enough to cut), redo the action, continue. You'll trim the bad
  take in editing — it's seamless if the pause was long enough.
- **No keyboard sound.** Even with audio disabled, the physical
  keyboard might bother **you** during editing playback. Use mouse
  navigation where possible.
- **Don't talk.** Don't even murmur. Mic is off but acoustics can
  sometimes leak via system audio paths.

## F.3 Stop and review

After Scene 7 (time-series Trend tab), wait 2 seconds, **Alt+Tab** to
OBS, click **Stop Recording**.

Open the resulting MP4 from `Desktop\OAS_demo\raw\`. Watch it once at
1.5× speed in Films & TV. Things to spot:

- Stutters or dropped frames → re-record (rare with H.264 + SSD).
- Black flicker when switching tabs → switch OBS capture method.
- Cursor disappears at any point → fix OBS capture cursor setting.
- Accidental popup, taskbar visible, notification toast → re-record.
- Total length is between 2:00 and 3:30 → good.

You don't need a perfect single take. It's normal to retake 1–2 scenes
and stitch them in editing. Each retake is a separate file in
`Desktop\OAS_demo\raw\`.

## F.4 Outro cards (Scenes 8–9)

Scenes 8 (continual learning explainer diagram) and 9 (closing card)
are easier to build entirely in **Shotcut** as still cards rather than
record them. Skip them in OBS; we'll add them in editing.

---

# Part G — Edit + add captions in Shotcut (90 minutes)

This is the longest stage. The good news: every minute spent on
captions is visible to viewers, unlike OBS setup which they never see.

## G.1 Create the project

1. Open Shotcut.
2. **File → New Project**.
3. Name: `oas_demo`, location: `Desktop\OAS_demo\`.
4. Video Mode → **HD 1080p 30fps**.
5. Click **Start**.

## G.2 Import your raw clips

1. Left panel → **Source / Recent / Playlist / Filters** tabs at the
   top. Click **Files** (or open Explorer side-by-side and drag).
2. Drag every MP4 from `Desktop\OAS_demo\raw\` onto the **Playlist**
   panel (top-centre).
3. Each clip becomes a thumbnail. Double-click to preview in the top-
   right preview window.

## G.3 Lay clips on the timeline

1. Bottom of the screen has the timeline. If it's not visible:
   **View → Timeline** (`Alt+1`).
2. Drag your first clip from Playlist onto **V1** (Video track 1) at
   time `00:00:00`. The clip appears as a green bar.
3. If you have multiple takes for one scene: pick the best one for now;
   the others stay in Playlist as backup.

## G.4 Trim long pauses

This single step takes 20–30 minutes but transforms the result.

1. Click on the timeline ruler to move the **playhead** (blue vertical
   line).
2. Watch the preview. When you hit a pause longer than 1 second:
   - Press **S** to **split** the clip at the playhead.
   - Move the playhead to where the pause ends.
   - Press **S** again.
   - Click the middle (pause) segment → press **Delete**.
3. Gap closes automatically (Shotcut "ripple delete" is on by default).
4. Repeat for every awkward pause.

Goal: total length **2:30 to 3:00**.

## G.5 Add the title card (Scene 1)

Scene 1 is a 10-second static title with the app name + URL.

1. **File → Open Other → Color**. Pick a dark navy (`#0b1226` is a good
   match for the storyboard's gradient).
2. Set **Duration**: `00:00:10:00`. Click **OK**.
3. The colour clip opens in the preview. Drag it from Source onto **V1**
   at time `00:00:00` (you may need to drag your real clip rightward
   first to make room).
4. With the colour clip selected, **Filters** panel (right side) →
   click **+** → search "Text" → pick **Text: Simple**.
5. In the Text field, paste:
   ```
   OAS Spectrum Studio
   A single-screen tool for optical absorption spectroscopy.
   github.com/jongchan1999/oas-spectrum-studio
   ```
6. Style it:
   - **Font**: Arial Bold, **64 pt** for the title; switch to Arial
     Regular **36 pt** for lines 2–3. (Shotcut needs three separate
     Text filters for three font sizes — easier alternative: keep all
     three lines at 44 pt regular.)
   - **Colour**: white.
   - **Outline**: 2 px black.
   - **Background**: none (the colour clip already provides the
     background).
   - **Position**: centred, vertically middle.

## G.6 Add the storyboard captions (the meat of the work)

For every caption in the storyboard:

1. Move the playhead to where the caption should appear.
2. Press **S** to split the underlying clip at this point.
3. Move the playhead to where the caption should disappear.
4. Press **S** again. You now have a small segment where the caption
   should be visible.
5. Click that segment → **Filters** → **+** → **Text: Simple**.
6. Paste the storyboard caption text.
7. Style (do this once, then **Copy filters / Paste filters**):
   - **Font**: Arial Regular **36 pt**.
   - **Position**: lower-third — drag the on-canvas text box so its
     vertical centre is at ~75% screen height.
   - **Background**: enable, colour `#000000`, **75% opacity** (RGBA
     `0,0,0,191`).
   - **Padding**: 12 px (so text doesn't touch the box edges).
   - **Maximum width**: 1600 px (leaves 160 px margin on each side).
   - **Outline**: 1 px black (boosts contrast over busy UI).

### Saving caption time with templates

After you style your **first** caption perfectly:

1. With the caption's clip segment selected, in the Filters panel,
   right-click the Text filter → **Copy filters**.
2. Click the next clip segment → right-click in Filters → **Paste
   filters**.
3. Click the pasted Text filter → edit only the **Text** field. Style
   carries over.

This saves you ~2 minutes per caption × 30 captions = 1 hour. Don't
skip it.

### Fade in/out

Optional but professional:

1. Select the Text filter.
2. Look for the **Keyframes** icon (clock symbol) next to a property,
   or open **View → Keyframes**.
3. Add keyframes at the start/end with **Opacity** 0 → 100 → 100 → 0
   over the duration.

If keyframes feel intimidating, skip them. Hard cuts on captions look
fine in screencasts.

## G.7 Cross-fades between scenes

Where one OBS clip ends and the next begins:

1. Click the right-edge of the earlier clip.
2. Drag it leftward, **overlapping** the start of the next clip by
   ~15 frames (0.5 seconds).
3. Shotcut auto-creates a cross-fade transition (a striped section).

Do this for every scene boundary. Adds a polish that's worth the 2
minutes.

## G.8 Outro card (Scene 9)

Same recipe as the title card (G.5), placed at the very end.

## G.9 Full-length preview

Play the entire timeline from start to finish. Watch for:

- [ ] Every caption visible for **at least** `length × 0.06` seconds
      (60 chars → minimum 3.6 s on screen).
- [ ] No caption cut off at the screen edge (left/right margin ≥ 80 px).
- [ ] No frame shows: URL bar, login form, secrets, Supabase dashboard,
      taskbar, unrelated tabs, personal profile photo.
- [ ] Total length between **2:30 and 3:15**.
- [ ] Transitions between scenes feel smooth (no hard cuts mid-action).

---

# Part H — Export + verify (15 minutes)

## H.1 Shotcut export

1. Top toolbar → **Export**.
2. Left panel (Stock presets) → scroll to **YouTube** → click. (The
   preset name is "YouTube" because it matches their recommended H.264
   settings; we'll save locally not upload.)
3. Right panel, **Video** tab:
   - Format: `mp4`
   - Codec: `libx264`
   - Resolution: 1920×1080
   - Aspect ratio: 16:9
   - Frames/sec: 30
   - GOP: 15 (default)
   - Rate control: **Average Bitrate**, Bitrate **5000 kbps** (5 Mbps).
4. **Audio** tab:
   - **Untick** the "Audio" checkbox at the top. This produces a video-
     only MP4 — no audio stream at all. Crucial.
5. **Other** tab: leave defaults.
6. Click **Export File**. Filename dialog:
   - Filename: **`demo.mp4`** (exact name — the README expects this).
   - Save to: `Y:\Share\1_개인자료\김종찬\논문\webpage_OAS\docs\demo\demo.mp4`.
7. Click **Save**.

Encode takes 2–5 minutes for a 3-minute clip on a modern laptop.
Progress shows in the bottom-right **Jobs** panel.

## H.2 Verify locally

Run these three checks in PowerShell (paste the whole block):

```powershell
$mp4 = "Y:\Share\1_개인자료\김종찬\논문\webpage_OAS\docs\demo\demo.mp4"
# 1. File exists and is reasonable size (25–55 MB target)
Get-Item $mp4 | Select-Object Name, @{n='SizeMB';e={[math]::Round($_.Length/1MB,1)}}, LastWriteTime
# 2. Plays locally
Start-Process $mp4
```

**Expected:**
- Size between **25 and 55 MB**. If > 80 MB, your bitrate was too high
  — re-export at 3 Mbps. If < 10 MB, the video stream is under-
  allocated (audio probably leaked in) — re-export with audio disabled.
- Plays in Films & TV with no error. Cursor visible. Captions readable.
- **Silent** — no audio bar in the player.

## H.3 If you have ffmpeg installed (optional verify + shrink)

If `ffmpeg --version` returns a number in PowerShell:

```powershell
# Check streams: should show 1 video stream, 0 audio streams
ffprobe -v error -show_streams "$mp4" | Select-String "codec_type"
# If you need to shrink: re-encode at 2 Mbps (still readable for UI)
ffmpeg -i "$mp4" -c:v libx264 -b:v 2M -an "${mp4}.small.mp4"
```

ffmpeg isn't required — Shotcut + size check is enough.

---

# Part I — Hand off to me (5 minutes)

Once `demo.mp4` is at:
```
Y:\Share\1_개인자료\김종찬\논문\webpage_OAS\docs\demo\demo.mp4
```

…tell me **"demo.mp4 saved"** and I'll run the full sequence:

```powershell
cd "Y:\Share\1_개인자료\김종찬\논문\webpage_OAS"
git lfs install                               # one-time setup
git add docs/demo/demo.mp4
git commit -m "Add 3-minute silent demo video"
git push origin main
git tag v1.0-demo
git push origin v1.0-demo
```

I'll also verify on GitHub that:
- The `<video>` block under the README hero renders with playback controls.
- The "▶ Watch the 3-minute demo" link downloads or streams.
- `v1.0-demo` tag appears in the Releases sidebar.

After that we proceed to [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)
for the public-release punch list.

---

# Part J — Common gotchas (expanded)

| Symptom | Probable cause | Fix |
|---|---|---|
| OBS records black screen | Display Capture on a multi-monitor laptop with Optimus GPU | Use Window Capture, set Capture Method to BitBlt or WGC |
| Cursor invisible in recording | "Capture Cursor" unticked in source | Source → Properties → tick **Capture Cursor** |
| Audio in the file when you wanted silent | One of the four global audio devices wasn't set to Disabled | Settings → Audio → all four to Disabled → **re-record** (you can't strip audio cleanly in Shotcut) |
| Recording stops at random | Disk full, or OBS lost the source window | Check Recording Path drive has > 1 GB free; check the Chrome window wasn't minimised |
| File > 100 MB | Bitrate too high or 60 fps | Re-export at 3 Mbps and 30 fps |
| Captions cut off at screen edge | Text box wider than screen | Drag the on-canvas text box inward; set Maximum Width to 1600 px |
| Streamlit app sluggish during demo | App was asleep when recording started | Open it 30+ seconds before; first request after sleep takes ~10 s |
| File picker doesn't accept the txt drag | Drop zone vs button confusion | Drop on the **dashed border**, not the "Browse files" button |
| Submit button greyed out in Scene 6 | Consent checkbox not ticked **or** Run ML not pressed yet | Tick consent FIRST, then Run, then Submit becomes enabled |
| Time-series upload rejects 344 files | Streamlit per-upload size limit | Adjust `server.maxUploadSize` in `.streamlit/config.toml` if needed (should already be set to 200 MB) |
| Chrome shows "Restore pages?" banner when you start | Last session crashed | Click X to dismiss before recording |
| Profile photo visible in top-right of Chrome | Logged into a personal Chrome profile | Open in Guest mode (`Ctrl+Shift+G` in Chrome menu) or a fresh profile |
| Korean characters in captions look wrong | Default font doesn't have Korean glyphs | Switch font to **Noto Sans CJK KR** or **맑은 고딕** in Text: Simple filter |
| Final MP4 plays but no controls in GitHub README | `docs/demo/demo.mp4` wasn't committed via LFS | Run `git lfs ls-files` — if demo.mp4 is missing, push went through but LFS upload didn't (we'll fix when you hand off) |

---

## Summary: a one-page cheat sheet

```
INSTALL (one-time):
  OBS Studio   https://obsproject.com/download
  Shotcut      https://shotcut.org/download/

OBS SETTINGS (one-time):
  Output  →  Simple, mp4, Desktop\OAS_demo\raw\
  Video   →  1920×1080, 30 fps, base = output
  Audio   →  all 4 devices Disabled
  Source  →  Window Capture, Chrome, Capture Cursor on

RECORDING:
  Chrome  →  F11 fullscreen
  OBS     →  Start Recording
  Pace    →  half normal cursor speed, 2-3s pause per element
  After   →  Alt+Tab to OBS, Stop Recording

EDITING (Shotcut):
  S       split clip at playhead
  Filters →  Text: Simple, Arial 36 pt, lower-third, 75% black bg
  Copy filters / Paste filters to reuse caption style
  Cross-fades by overlapping clips ~15 frames

EXPORT (Shotcut):
  Preset YouTube → mp4, libx264, 1080p 30 fps, 5 Mbps, NO AUDIO
  Save as docs/demo/demo.mp4 (exact name)
  Target size 25-55 MB

HAND OFF:
  Tell me "demo.mp4 saved"  →  I LFS-add, commit, push, tag v1.0-demo
```

That's the whole pipeline. Bookmark this page on a second monitor while
recording.
