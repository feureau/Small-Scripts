# Universal Master Video Editing & Motion Graphics Prompt System
*Dynamic, Content-Adaptive Production Pipeline for DaVinci Resolve Studio*

---

## Quick Reference: How to Use This Document

- **For One-Shot Automated Editing**: Copy and paste **Section 1: The Master One-Shot Prompt** into Antigravity when you have opened a project in DaVinci Resolve with your raw footage on the timeline.
- **For Iterative Step-by-Step Production**: Use **Section 2: Modular Phase-by-Phase Sub-Prompts** to execute one production stage at a time (Rough Cut $\rightarrow$ Transcript Sync $\rightarrow$ Motion Graphics $\rightarrow$ B-Roll $\rightarrow$ Final Polish).
- **For Technical Scripting & Reference Templates**: Reference **Section 3: The 7 Bulletproof Technical Standards & Code Templates** for exact Fusion Lua node graphs, Resolve API edit patterns, proportional chart math, and zero-AI image downloaders.

---

## Section 1: The Master One-Shot Prompt

> [!TIP]
> **Instructions for the User**:
> 1. Open your project in DaVinci Resolve Studio.
> 2. Put your raw takes/clips on Video Track 1 (V1) and Audio Track 1/5.
> 3. Copy the prompt block below, optionally adjust the `Pacing` or `Style Preset` tag at the top, and paste it to Antigravity.

```markdown
You are acting as an elite Video Editor, Motion Graphics Designer, and DaVinci Resolve Automation Engineer.

I have loaded a batch of raw talking-head / explainer takes into DaVinci Resolve Studio on the active timeline. Your mission is to dynamically inspect, rough-cut, style, illustrate, synchronize, and polish this video into a publish-ready YouTube/editorial master.

---
### PROJECT PARAMETERS
- **Pacing Preset**: Standard (1 visual event every 30–45s) [Options: Fast (15–25s) | Standard (30–45s) | Relaxed (60–90s)]
- **Visual Style**: Sleek Financial / Documentary Dark (#0A0D14 base, 0.88 alpha, subtle glowing borders, modern sans-serif typography)
- **Image Policy**: ZERO AI-generated images. Authentic archival, public domain, or verified editorial photos only.
- **Asset Storage Mandate**: Dynamically discover the DaVinci Resolve Project Media Directory (`resolve_proj_dir = os.path.dirname(v1_clip.GetMediaPoolItem().GetClipProperty('File Path'))`). Store all downloaded images in `<resolve_proj_dir>/img/` and deliverables in `<resolve_proj_dir>/youtube_chapters.txt`—NEVER solely in the Antigravity workspace directory.
- **Track Layout Architecture**:
  - V1 / A1–A5: Primary Host Footage & Clean Dialogue (Untouchable once rough-cut is locked)
  - V4: Fusion Motion Graphics, Chapter Banners, Data Cards, and Dedicated Charts
  - V5: Authentic B-Roll Photos & Archival Still Images
---

Execute this production pipeline dynamically, adjusting to the exact number of takes, duration, and subject matter of this project, while strictly adhering to the 7 Core Technical Safeguards:

### PHASE 1: DISCOVERY, DIRECTORY MAPPING & TIMECODE BASELINE
1. Connect to DaVinci Resolve via the Python API (`sys.stdout.reconfigure(encoding='utf-8')`).
2. Inspect the active timeline: get `fps`, resolution, `tl_zero = timeline.GetStartFrame()` (typically 86,400 at `01:00:00:00`), track counts, and total duration.
3. Discover `resolve_proj_dir` from Track V1 Clip 1's `File Path` and create `<resolve_proj_dir>/img/`.
4. Duplicate the active timeline into a safety backup named: `"[Original Name] - Safety Backup (YYYY-MM-DD)"`.
5. Extract word-level audio transcription from all V1 clips via `MediaPoolItem.GetTranscription()` (or `.srt` sidecar files in `resolve_proj_dir`).

### PHASE 2: MULTI-TRACK LOCKSTEP TAKE PRUNING & ROUGH CUT
1. **Multi-Track Audio Audit (Safeguard #4)**: Inspect all populated audio tracks (`A1` through `A8`) before cutting. Identify whether camera scratch audio is on `A1` and clean master dialogue is on a separate track (e.g., `A5`). All cuts on `V1` MUST be applied identically in lockstep to the master dialogue track.
2. Analyze spoken dialogue continuity across all V1 clips. Detect false starts, stuttered lines, and repeated takes. Retain only the cleanest, final complete take of each thought, and prune dead-air pauses > 1.2s.
3. **Resolve API Edit Pattern (Safeguard #3)**: Never call non-existent methods like `.SetStart()`, `.SetPosition()`, or `.SplitClip()`. Perform cuts and repositionings by building a list of clip dicts `{'mediaPoolItem': mpi, 'startFrame': src_in, 'endFrame': src_out, 'trackIndex': T, 'recordFrame': rec_frame}` and calling `timeline.DeleteClips()` + `mediaPool.AppendToTimeline()`.

### PHASE 3: CONTENT ANALYSIS & DYNAMIC 4-TIER VISUAL TAXONOMY
Extract the full word-level timeline transcript and categorize concepts into our dynamic 4-tier visual hierarchy:
1. **Top Chapter Banners (V4)**: Place at major topic / act shifts (`Center = 0.50, 0.88`, `Size = 0.92 x 0.14`).
2. **Left-Third Data & Alert Cards (V4)**: Place when citing metrics, percents, dollar figures, quotes, or analogies (`Center = 0.22, 0.50`, `Size = 0.35 x 0.65`).
   - **Alpha Transparency Safeguard (Safeguard #1)**: For all Banners and Side Cards, the root canvas `Background` node MUST have `TopLeftAlpha = 0.0` (100% transparent) so Track V1 shows through. Create a second `Background` node (`Alpha = 0.88`) masked by a `RectangleMask` for the card plate, and a third `Background` node masked by an outline `RectangleMask` (`Solid = 0, BorderWidth = 0.002`) for the glowing border. Never use `PaintMode = FuID { "Outline" }` or raw `\n` inside double-quoted Lua strings.
3. **Full-Screen Presentations & Charts (V4)**: Reserved exclusively for multi-column comparison tables or macro charts requiring the entire frame (`Root Alpha = 1.0`).
   - **Data Integrity & Proportional Plotting Safeguard (Safeguard #2)**: Research and verify real historical numbers for every chart. Calculate every bar height and line vertex mathematically:
     `Y_canvas = Y_bottom + ((Value - Val_min) / (Val_max - Val_min)) * (Y_top - Y_bottom)`
     Never draw arbitrary or unscaled decorative graph lines.
4. **Authentic B-Roll Photos (V5)**: Place when real-world entities, historical events, physical goods, institutions, or notable individuals are discussed.

### PHASE 4: AUTHENTIC B-ROLL SOURCING & ASPECT-RATIO FRAMING
1. **Wikimedia & Archival Downloader (Safeguard #5)**: Search authentic sources (Wikimedia Commons, museum archives, Library of Congress, public domain, or verified editorial databases). Always pass a compliant HTTP `User-Agent` header (`User-Agent: ResolveProductionBot/1.0 (https://example.org; contact@example.org)`) when downloading via Python to prevent HTTP 403 errors.
2. Save files to `<resolve_proj_dir>/img/<clean_slug>.jpg`, verify image dimensions, and import into Media Pool bin `"B-Roll Images"`.
3. **Aspect-Ratio Framing**: When placing portrait or non-16:9 archival photos onto Track 5, configure `ZoomX`/`ZoomY` or picture-in-picture framing (`Scale = 0.75`, `PositionX/Y`) so faces and subjects are never awkwardly cropped at the forehead/chin.

### PHASE 5: SAMPLE-ACCURATE DIALOGUE SYNC & PROTOTYPE VISUAL QA
1. For every asset on V4 and V5, anchor its In-Point to the exact timeline frame where the keyword/concept is spoken:
   `Timeline Frame = tl_item_start + (word_source_frame - tl_item_left_offset)`
2. Calculate durations dynamically based on reading speed:
   `Out-Point = In-Point + max(96 frames [4s], word_count * 8 frames)`
   Ensure visuals automatically yield before colliding with subsequent events.
3. **Prototype Visual Gate (Safeguard #6)**: Immediately after generating the FIRST Top Banner, FIRST Side Card, and FIRST Full-Screen Chart, move the playhead (`tl.SetCurrentTimecode()`), export a still via `proj.ExportCurrentFrameAsStill()`, and visually inspect the image using `read_file` to verify transparency, text wrapping, and alignment before batch-generating the remaining clips.

### PHASE 6: CHAPTER MARKERS & PUBLISH READINESS
1. **Zero-Based Marker & Timestamp Math (Safeguard #7)**: Add Blue timeline chapter markers at the start frame of each major chapter on V4 using offset-adjusted frames:
   `marker_frame = clip_start_frame - tl.GetStartFrame()`
   `tl.AddMarker(marker_frame, 'Blue', chapter_name, chapter_note, 1)`
2. Export a formatted YouTube chapter description file (`MM:SS - Chapter Title`, where seconds = `(clip_start_frame - tl.GetStartFrame()) // fps`) directly to `<resolve_proj_dir>/youtube_chapters.txt`.
3. Export final verification stills across key moments to confirm publish readiness.
```

---

## Section 2: Modular Phase-by-Phase Sub-Prompts

Use these modular sub-prompts when you want to review and approve each stage interactively:

### Sub-Prompt 1: Discovery, Backup & Multi-Track Rough Cut
```markdown
Phase 1 & 2: Project Inspection & Lockstep Rough Cut.
1. Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`) and inspect the active timeline. Report timeline name, FPS, resolution, `tl.GetStartFrame()`, total duration, V1 clip count, populated audio tracks (identifying master dialogue track e.g. A5 vs scratch A1), and the DaVinci Resolve Project Media Directory (`resolve_proj_dir`).
2. Create a safety backup duplicate of the timeline named "[Timeline Name] - Backup Before Rough Cut".
3. Extract word-level audio transcription for all V1 clips.
4. Scan the transcript for false starts, aborted lines, repeated takes, and pauses (>1.2s).
5. Present a proposed cut list of takes to keep vs. takes to remove, ensuring V1 and the master dialogue track remain 100% locked in sync. Wait for my approval before executing via `DeleteClips` / `AppendToTimeline`.
```

### Sub-Prompt 2: Semantic Visual Planning & Sizing Audit
```markdown
Phase 3: Semantic Content Analysis & Visual Density Plan.
1. Analyze the locked V1 dialogue transcript from start to finish.
2. Based on a Standard pacing target (~1 visual event every 30–45 seconds), produce a Visual Event Plan categorized into:
   - Top Chapter Banners (topic shifts; Center=(0.50, 0.88), Size=(0.92, 0.14), Root Canvas Alpha=0.0, speaker 85% visible)
   - Left-Third Data Cards (stats, metrics, quotes, analogies; Center=(0.22, 0.50), Size=(0.35, 0.65), Root Canvas Alpha=0.0, speaker visible center/right)
   - Full-Screen Dedicated Presentations (complex multi-asset tables or macro charts only; Root Alpha=1.0, backed by researched real-world data)
   - Authentic B-Roll Photos (real entities, people, locations, physical objects)
3. For each proposed event, list: Target Track, Spoken Cue Phrase, Exact Timeline Start/End Frame, Visual Type, and Proposed Content. Present as an implementation plan for my approval.
```

### Sub-Prompt 3: Authentic Zero-AI Image Sourcing & V5 Insertion
```markdown
Phase 4: Authentic B-Roll Sourcing & V5 Placement.
1. Review the approved B-roll photo cues for Video Track 5.
2. Ensure `<resolve_proj_dir>/img/` exists in the DaVinci Resolve media folder.
3. Adhere strictly to the Zero-AI Image Mandate. Search and retrieve real historical/editorial photos via Wikimedia Commons, museum open archives, or official public domain repositories using a compliant HTTP User-Agent header.
4. Save files into `<resolve_proj_dir>/img/` with clean descriptive filenames, import into Media Pool bin "B-Roll Images", and place onto Track 5 at the exact spoken frame ranges using `AppendToTimeline`.
5. Check aspect ratios of all imported images; apply proper Zoom/Position framing to portrait/square images so faces or subjects are never cropped off.
```

### Sub-Prompt 4: Decorated Fusion Motion Graphics & Prototype QA
```markdown
Phase 5: Decorated Motion Graphics Implementation & Prototype Gate.
1. Generate and install Fusion compositions onto Video Track 4 for all approved Banners, Data Cards, and Full-Screen presentations.
2. Enforce all Fusion Guardrails:
   - Root Canvas Transparency: Base `Background` node MUST have `TopLeftAlpha = 0.0` for all Banners and Cards so V1 shows through.
   - Card/Banner Plate: Masked `Background` (#0A0D14, 0.88 opacity, CornerRadius=0.03) + glowing border (`Solid = 0, BorderWidth = 0.002`, #D4AF37 Gold or #38BDF8 Cyan).
   - Data Accuracy: Research real numbers for all charts and plot coordinates proportionally (`Y = y_min + ((val - v_min) / (v_max - v_min)) * height`).
   - Lua Crash Prevention: Never put raw \n in double-quoted strings; use separate TextPlus nodes. Never use `PaintMode = FuID { "Outline" }`.
3. Prototype Visual Gate: Build the first Banner, first Side Card, and first Chart, export stills via `proj.ExportCurrentFrameAsStill()`, and inspect them with `read_file` before batch-generating the remaining clips.
```

### Sub-Prompt 5: Dialogue Sync Audit & Chapter Markers
```markdown
Phase 6: Sample-Accurate Sync Audit & Final Polish.
1. Cross-reference every item on V4 and V5 against the exact spoken word timestamps from V1 transcription (`tl_start + (word_source_frame - left_offset)`).
2. Reposition any early or late clips using Resolve's `DeleteClips` + `AppendToTimeline` pattern so every visual hits sample-accurately on its spoken cue without overlapping adjacent visuals.
3. Add Blue timeline chapter markers at `clip_start_frame - tl.GetStartFrame()` for every chapter on V4.
4. Export the YouTube chapter list (`MM:SS - Title`) directly to `<resolve_proj_dir>/youtube_chapters.txt`.
5. Export visual verification stills to confirm publish readiness.
```

---

## Section 3: The 7 Bulletproof Technical Standards & Code Templates

### Standard 1: Fusion Overlay Architecture (`TopLeftAlpha = 0.0` Root Canvas)
To prevent overlays on Track 4 from turning the entire screen black and hiding the speaker on Track 1, **never** set the base `Background` node's alpha above `0.0` on Banners or Side Cards. Use this exact node topology:
- `BG_Canvas`: `TopLeftAlpha = 0.0` (1920x1080 transparent root canvas)
- `Mask_Plate`: `RectangleMask` at `(CenterX, CenterY)`, `(Width, Height)`, `CornerRadius = 0.03`
- `BG_Plate`: Dark slate `#0A0D14` (`R=0.039, G=0.051, B=0.078, TopLeftAlpha=0.88`), masked by `Mask_Plate`
- `Mask_Border`: `RectangleMask` at same center/size, `CornerRadius = 0.03`, `Solid = 0`, `BorderWidth = 0.0025`
- `BG_Border`: Accent Gold `#D4AF37` (`R=0.831, G=0.686, B=0.216, TopLeftAlpha=0.95`), masked by `Mask_Border`
- `Text_Header`, `Text_Metric`, `Text_Body`: Dedicated single-line `TextPlus` nodes merged sequentially (`Merge_Plate` $\rightarrow$ `Merge_Border` $\rightarrow$ `Merge_Text1` $\rightarrow$ `Merge_Text2` $\rightarrow$ `MediaOut1`).

### Standard 2: Chart Data Integrity & Proportional Coordinate Math
Every chart or graph must represent researched, real-world data plotted mathematically:
```python
def calc_y(value, val_min, val_max, y_bottom=0.22, y_top=0.75):
    """Maps a real data value proportionally to Fusion Y coordinates (0.0 to 1.0)."""
    ratio = (value - val_min) / float(val_max - val_min)
    return round(y_bottom + ratio * (y_top - y_bottom), 4)

def calc_bar_mask(value, val_min, val_max, x_center, width=0.08, y_bottom=0.22, y_top=0.75):
    """Returns (CenterX, CenterY, Width, Height) for a vertical bar RectangleMask."""
    top_y = calc_y(value, val_min, val_max, y_bottom, y_top)
    bar_h = max(0.005, top_y - y_bottom)
    center_y = y_bottom + (bar_h / 2.0)
    return (round(x_center, 4), round(center_y, 4), round(width, 4), round(bar_h, 4))
```

### Standard 3: DaVinci Resolve API Clip Repositioning & Trimming Pattern
`TimelineItem` objects in `DaVinciResolveScript` do **not** have `.SetStart()`, `.SetEnd()`, `.SetPosition()`, or `.SplitClip()` methods. Always move or trim clips using `DeleteClips` + `AppendToTimeline`:
```python
def move_or_trim_timeline_item(timeline, media_pool, item, track_type, track_index, new_record_start, new_duration):
    """Moves or trims an existing TimelineItem to [new_record_start, new_record_start + new_duration]."""
    mpi = item.GetMediaPoolItem()
    src_in = item.GetLeftOffset()
    src_out = src_in + new_duration
    
    # Note: If the clip has a Fusion composition, save its comp settings before deleting if needed,
    # or for B-roll/generators append the MediaPoolItem directly:
    timeline.DeleteClips([item], False)
    new_items = media_pool.AppendToTimeline([{
        'mediaPoolItem': mpi,
        'startFrame': src_in,
        'endFrame': src_out,
        'trackIndex': track_index,
        'recordFrame': new_record_start,
        'mediaType': 1 if track_type == 'video' else 2
    }])
    return new_items[0] if new_items else None
```

### Standard 4: Multi-Track Audio Lockstep Cut Pattern
Before cutting V1, inspect all audio tracks to detect separate dialogue stems (e.g. A1 camera scratch vs A5 processed microphone):
```python
for a_idx in range(1, timeline.GetTrackCount('audio') + 1):
    a_items = timeline.GetItemListInTrack('audio', a_idx)
    print(f"Audio Track A{a_idx}: {len(a_items)} clips | Track Name: {timeline.GetTrackName('audio', a_idx)}")
```
When assembling a rough cut from transcription segments `(mpi, src_in, src_out)`, append the synchronized audio slice to the master dialogue track at the exact same `recordFrame`.

### Standard 5: Compliant Wikimedia Downloader & Aspect-Ratio Framing
Wikimedia Commons blocks default Python requests with `HTTP 403`. Always include a descriptive `User-Agent`:
```python
import urllib.request
def download_authentic_image(url, dst_path):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'DaVinciResolveEditorialBot/1.0 (https://github.com/; editorial@localhost)'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp, open(dst_path, 'wb') as out_f:
        out_f.write(resp.read())
```
After placing an image onto V5, check its dimensions (`mpi.GetClipProperty('Resolution')`). If portrait or 4:3, set `item.SetProperty('ZoomX', scale)` / `item.SetProperty('Pan', x)` / `item.SetProperty('Tilt', y)` so subjects are cleanly framed.

### Standard 6: Prototype Visual Verification Helper (`ExportCurrentFrameAsStill`)
Always visually verify new Fusion templates by exporting a frame still and reading it with `read_file`:
```python
def frame_to_timecode(frame_num, fps=24):
    h = int(frame_num // (3600 * fps))
    m = int((frame_num // (60 * fps)) % 60)
    s = int((frame_num // fps) % 60)
    f = int(frame_num % fps)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

def export_verification_still(project, timeline, target_frame, out_jpg_path):
    fps = float(timeline.GetSetting('timelineFrameRate'))
    tc = frame_to_timecode(target_frame, fps)
    timeline.SetCurrentTimecode(tc)
    project.ExportCurrentFrameAsStill(out_jpg_path)
    return out_jpg_path
```

### Standard 7: Resolve Timecode Baseline (`tl.GetStartFrame()`) & Marker Math
DaVinci Resolve timelines default to starting at `01:00:00:00` (`tl.GetStartFrame() == 86400` at 24fps), while `Timeline.AddMarker()` expects a frame offset **relative to the start of the timeline (`0`-based)**:
```python
tl_zero = timeline.GetStartFrame()
fps = float(timeline.GetSetting('timelineFrameRate'))

for idx, v4_item in enumerate(timeline.GetItemListInTrack('video', 4)):
    abs_start = v4_item.GetStart()
    rel_frame = abs_start - tl_zero  # 0-based offset required by AddMarker and YouTube timestamps
    timeline.AddMarker(rel_frame, 'Blue', f"Chapter {idx+1}", v4_item.GetName(), 1)
    
    total_sec = int(rel_frame // fps)
    mm, ss = divmod(total_sec, 60)
    youtube_line = f"{mm:02d}:{ss:02d} - {v4_item.GetName()}"
```
