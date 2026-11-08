You are acting as a Documentary Researcher, Senior Motion Graphics Designer, Financial Data Visualizer, and DaVinci Resolve Automation Engineer.

Video Track 1 (`V1`) contains the assembled talking-head / monologue edit (with vocals on `A5` / `A6`). Your mission is to perform a **unified visual spotting pass** across `V1` and the reference script in `<resolve_proj_dir>`, and populate:
- **Video Track 3 (`V3`)** with **100% authentic archival/editorial photographs** (stored in `<resolve_proj_dir>/img/` and imported into the Media Pool bin **`"B-Roll"`**), and
- **Video Track 4 (`V4`)** with **3-Tier Fusion Motion Graphics & Proportional Data Charts** (backed up in `<resolve_proj_dir>/o/fusion_comps/`),
while keeping **`V5` and `V6` strictly reserved for effects and color grading** and generating Timeline Chapter Markers + YouTube timestamps.

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & 3-TIER TIMESTAMP RESOLUTION

1. **Connect, Inspect & Backup Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for `FPS`, resolution (`width x height`), `tl.GetStartFrame()`, and track counts.
   - **Track Reservation Rule**: Never modify, unlock, or place clips on **Video Track 5 (`V5`)** or **Video Track 6 (`V6`)**—those tracks are reserved for color grading and timeline-wide effects (e.g., `Film Look Creator`).
   - Duplicate the active timeline into a safety backup named `f"{tl.GetName()} - Backup Before Visuals (V3 & V4)"` before making any edits, then switch back to the original timeline (`proj.SetCurrentTimeline(tl)`).

2. **Resolve True Project Root Directory (`resolve_proj_dir`)**:
   - Inspect the first clip on `V1` and step up out of the `v/` subfolder so `<resolve_proj_dir>/img/` and `<resolve_proj_dir>/o/` are always resolved at the true project root (never inside `v/img/`):
     ```python
     v1_items = tl.GetItemListInTrack("video", 1) or []
     first_path = v1_items[0].GetMediaPoolItem().GetClipProperty("File Path")
     clip_dir = os.path.dirname(first_path)
     resolve_proj_dir = os.path.dirname(clip_dir) if os.path.basename(clip_dir).lower() == "v" else clip_dir
     img_dir = os.path.join(resolve_proj_dir, "img")
     out_dir = os.path.join(resolve_proj_dir, "o")
     comp_dir = os.path.join(out_dir, "fusion_comps")
     os.makedirs(img_dir, exist_ok=True)
     os.makedirs(comp_dir, exist_ok=True)
     ```

3. **3-Tier Word-Level Timestamp Resolution**:
   - Do NOT rely solely on `MediaPoolItem.GetTranscription()`, which returns `None` unless manual Resolve transcription was run. Resolve word-level timeline positions using the first available source:
     - **Tier 1 (Preferred — Whisper Word Cache from `DVR_Editing.md`)**: Load `<resolve_proj_dir>/o/whisper_words_cache.json` and map each spoken word's source frame (`round(word_start_sec * fps)`) inside its `v1_item` (`[v1_item.GetLeftOffset(), v1_item.GetLeftOffset() + v1_item.GetDuration()]`) to its exact timeline frame:
       ```python
       timeline_frame = v1_item.GetStart() + (word_source_frame - v1_item.GetLeftOffset())
       ```
     - **Tier 2 (Timeline Master `.srt` in `<resolve_proj_dir>/o/<timeline_name>.srt`)**: Parse the timeline-relative `.srt` in `<resolve_proj_dir>/o/` (`timeline_frame = tl.GetStartFrame() + round(cue_start_sec * fps)`).
     - **Tier 3 (Fallback Transcription)**: Check `mpi.GetTranscription()` or run `faster-whisper` (`word_timestamps=True`) on stream `0:a:0` of the `V1` clips and cache to `<resolve_proj_dir>/o/whisper_words_cache.json`.

---

### PHASE 1: UNIFIED MASTER VISUAL SPOTTING & COLLISION MATRIX (`V3` + `V4`)

1. **Modality Assignment (Right Visual for Every Beat)**:
   - Analyze the spoken dialogue on `V1` alongside `* - monologue.txt` / `* - essay.txt` in `resolve_proj_dir` to build a single **Unified Master Visual Spotting Sheet** before downloading or building anything:
     - **Track `V3` — Archival / Editorial Photographs**: Assign whenever specific real-world people (politicians, executives, historical figures), companies, buildings, hardware/products, institutions, or geographic locations are introduced.
     - **Track `V4` (Tier A) — Top Chapter Banners**: Assign at major Act breaks and topic transitions (`Center = (0.50, 0.88)`, `Width = 0.92`, `Height = 0.14`).
     - **Track `V4` (Tier B) — Left-Third Data & Alert Cards**: Assign when key statistics, percentages, dollar figures, dates, quotes, or punchy analogies are spoken (`Center = (0.22, 0.50)`, `Width = 0.35`, `Height = 0.65`).
     - **Track `V4` (Tier C) — Full-Screen Proportional Charts & Tables**: Reserve exclusively for multi-point historical trends, multi-company breakdowns, or multi-column comparison tables requiring the full $1920 \times 1080$ canvas.

2. **Spatial & Temporal Collision Matrix (`V3` vs. `V4`)**:
   - **Rule 1 (`V3` Photo vs. `V4` Tier B Left-Third Card / Tier C Full-Screen Chart)**: Strictly **mutually exclusive in time**. Never overlap a `V3` PiP photo and a `V4` Left-Third Card or Full-Screen Chart on the same frames. When a sentence names both a person/company and a statistic (e.g., *"Elon Musk personally dropping $445 million..."*), schedule a **1–2 sequential visual combo**: show the `V3` photo on the entity name (`~90–120 frames`), then cut cleanly to the `V4` data card on the number (`~150–180 frames`).
   - **Rule 2 (`V3` Left PiP Photo + `V4` Tier A Top Banner)**: Allowed to overlap only if the `V3` photo's vertical `Tilt` stays below the top 15% banner zone (`Tilt <= 20`).
   - **Rule 3 (Intra-Track Spacing)**: Ensure zero overlapping clips on `V3` (`next_start >= prev_end`) and zero overlapping clips on `V4`.

---

### PHASE 2: TRACK `V3` — ZERO-AI ARCHIVAL IMAGE SOURCING & SMART PiP FRAMING

1. **Strict Zero-AI Image Policy**:
   - Do **NOT** generate or use AI images under any circumstances.
   - Source 100% real, authentic historical, archival, public-domain, or editorial photographs (Wikimedia Commons, Library of Congress, official government/agency portraits, museum open-access archives, or verified product/editorial photos).

2. **Deterministic Wikimedia Commons API Search & Download (`<resolve_proj_dir>/img/`)**:
   - Query the Wikimedia Commons API (`https://commons.wikimedia.org/w/api.php`) with a compliant `User-Agent` header (`User-Agent: DaVinciResolveEditorialBot/1.0 (https://commons.wikimedia.org/)`) to avoid `HTTP 403 Forbidden` errors:
     ```python
     params = {
         "action": "query",
         "format": "json",
         "generator": "search",
         "gsrsearch": f"filetype:bitmap {search_query}",
         "gsrnamespace": 6,  # File: namespace
         "gsrlimit": 5,
         "prop": "imageinfo",
         "iiprop": "url|dimensions|mime",
         "iiurlwidth": 1600,
     }
     ```
   - Save all downloaded images directly into **`<resolve_proj_dir>/img/<descriptive_slug>.jpg`** (or `.png`)—NEVER solely in the workspace or temp directory so the DaVinci Resolve project never goes `"Media Offline"`.

3. **Mandatory Pre-Import Image Validation Gate**:
   - Before importing into DaVinci Resolve, validate every file in `<resolve_proj_dir>/img/`:
     - Confirm the file is a valid raster image (`.jpg` or `.png`, NOT an HTML error page, `.svg`, or un-decoded `.webp`—if `.webp`, convert to high-quality RGB `.jpg` via Pillow or FFmpeg).
     - Verify resolution (`width >= 600` and `height >= 600`) and record its exact aspect ratio (`aspect = width / height`).
     - Visually inspect each downloaded image using `read_file` to confirm it accurately and cleanly depicts the intended person, place, or object.

4. **Idempotent Media Pool Bin `"B-Roll"` & `V3` Placement**:
   - Find or create the subfolder **`"B-Roll"`** at the root of the Media Pool (`root = mp.GetRootFolder()`), checking `root.GetSubFolderList()` first so duplicate `"B-Roll"` bins are never created.
   - Import the verified images from `<resolve_proj_dir>/img/` into `"B-Roll"`.
   - Clamp `endFrame` to the still clip's MediaPool frame limit (`int(img_mpi.GetClipProperty("Frames") or 120) - 1`) and append onto **Video Track 3 (`V3`)** with `"mediaType": 1` (Video only):
     ```python
     max_still_frames = int(img_mpi.GetClipProperty("Frames") or 120)
     clip_end_frame = min(desired_duration_frames - 1, max_still_frames - 1)
     appended = mp.AppendToTimeline([{
         "mediaPoolItem": img_mpi,
         "startFrame": 0,
         "endFrame": clip_end_frame,
         "mediaType": 1,
         "trackIndex": 3,
         "recordFrame": int(target_timeline_frame),
     }])
     ```

5. **Aspect-Ratio-Aware Picture-in-Picture (PiP) Framing on `V3`**:
   - Frame `V3` images as a clean **Left-Side Picture-in-Picture (PiP) Overlay** so the speaker on `V1` remains clearly visible on the center/right, adapting `ZoomX`/`ZoomY`, `Pan`, `Tilt`, and `Crop` via `item.SetProperty(...)` based on aspect ratio (`width / height`) so faces and heads are **never cropped off**:
     - **Portrait (`aspect < 0.85`, e.g., official headshots/portraits)**: `ZoomX = 0.32–0.38`, `Pan = -540 to -580`, `Tilt = 0 to 60`, `CropTop = 0`, `CropBottom = 0`.
     - **Square / 4:3 Archival (`0.85 <= aspect <= 1.45`)**: `ZoomX = 0.34–0.40`, `Pan = -530 to -570`, `Tilt = 30 to 110`.
     - **Wide Landscape (`aspect > 1.45`, e.g., facilities, buildings, hardware)**: `ZoomX = 0.38–0.44`, `Pan = -500 to -540`, `Tilt = 40 to 120` (or Full-Screen Cutaway `ZoomX = 1.0`, `DynamicZoomEnabled = True`, `DynamicZoomEase = 3` when showcasing detailed wide photography).
   - Apply a subtle `Cross Dissolve` (`6–8 frames`) transition on entry/exit where appropriate.

---

### PHASE 3: TRACK `V4` — 3-TIER FUSION MOTION GRAPHICS & PROPORTIONAL CHARTS

1. **Dynamic 3-Tier Visual Hierarchy & Non-Obscuring Framing**:
   - **Tier A — Top Chapter Banners (`V4`)**: Placed at major Act breaks and topic transitions.
     - Framing: `Center = (0.50, 0.88)`, `Width = 0.92`, `Height = 0.14`. Leaves the lower 85% of the frame open so the speaker on `V1` is completely visible.
   - **Tier B — Left-Third Data & Alert Cards (`V4`)**: Placed when the speaker cites key statistics, percentages, dollar figures, quotes, or memorable analogies.
     - Framing: `Center = (0.22, 0.50)`, `Width = 0.35`, `Height = 0.65`. Leaves the center and right of the frame open so the speaker on `V1` remains visible.
   - **Tier C — Full-Screen Dedicated Presentations & Charts (`V4`)**: Reserved EXCLUSIVELY for complex multi-column comparison tables or multi-point historical charts that require the full $1920 \times 1080$ canvas.

2. **CRITICAL — Root Canvas Transparency (`TopLeftAlpha = 0.0`)**:
   - For all Top Banners and Left-Third Cards, the root canvas `Background` node MUST have `TopLeftAlpha = 0.0` (100% transparent). Never put an unmasked opaque `Background` node on a Banner or Card, or it will black out Track `V1`!
   - Build cards using: `BG_Canvas (Alpha=0.0)` $\rightarrow$ `BG_Plate (#0A0D14, Alpha=0.88)` masked by `RectangleMask (CornerRadius=0.03)` $\rightarrow$ `BG_Border (#D4AF37 Gold or #38BDF8 Cyan)` masked by an outline `RectangleMask (Solid=0, BorderWidth=0.0025)` $\rightarrow$ sequential single-line `TextPlus` nodes $\rightarrow$ `MediaOut1`.

3. **Chart Data Integrity & Proportional Plotting Mandate**:
   - Whenever building a graph or chart, research and verify the actual historical numbers.
   - Calculate every bar height and line vertex mathematically so the visual geometry is 100% proportional to the data:
     $$Y_{\text{canvas}} = Y_{\text{bottom}} + \left(\frac{\text{Value} - \text{Val}_{\min}}{\text{Val}_{\max} - \text{Val}_{\min}}\right) \times (Y_{\text{top}} - Y_{\text{bottom}})$$

4. **Deterministic `V4` Placement & Fusion Lua Crash Safeguards**:
   - **Exact `V4` Placement Carrier Pattern**: Because `tl.InsertFusionCompositionIntoTimeline()` drops a fixed 5-second comp on the lowest unlocked track at the playhead, use a reusable 15-second transparent carrier video (`<resolve_proj_dir>/o/_fusion_carrier.mov` or transparent PNG imported into the `"B-Roll"` bin) when placing graphics via `mp.AppendToTimeline` so you can specify exact `"trackIndex": 4`, `"recordFrame": target_frame`, `"mediaType": 1`, and `"endFrame": duration_frames - 1` (`max(160 frames, word_count * 8 frames)`).
   - **Fusion Lua Safeguards**:
     - Never put raw `\n` newlines inside double-quoted strings in Lua `.comp` files (create separate `TextPlus` nodes for each line).
     - Never pass `PaintMode = FuID { "Outline" }` to a `RectangleMask` (use `Solid = Input { Value = 0 }, BorderWidth = Input { Value = 0.0025 }`).
     - Always save every generated Fusion composition to `<resolve_proj_dir>/o/fusion_comps/<slug>.comp` (`comp.Save(path)`) and load/restore via `v4_item.ImportFusionComp(path)`.

---

### PHASE 4: PROTOTYPE & FINAL VISUAL QA GATE + YOUTUBE CHAPTERS

1. **Prototype Visual QA Gate (Before Batch Generation)**:
   - After inserting the **FIRST `V3` PiP Image**, **FIRST `V4` Top Banner**, **FIRST `V4` Left-Third Card**, and **FIRST `V4` Full-Screen Chart**, move the playhead (`tl.SetCurrentTimecode(...)`) to the midpoint of each item, export a still frame to `<resolve_proj_dir>/o/qa_<slug>.jpg` via `proj.ExportCurrentFrameAsStill(...)`, and visually inspect the JPGs using `read_file` before batch-populating the remaining items.

2. **Full Visual Verification**:
   - Inspect exported stills across all inserted `V3` and `V4` items to verify:
     - Zero decapitation or awkward face cropping on `V3` photos.
     - 100% background transparency (`TopLeftAlpha = 0.0`) on `V4` Tier A Banners and Tier B Cards so the speaker on `V1` is clearly visible.
     - Zero visual collisions between `V3` and `V4`, and **`V5` / `V6` remain completely untouched**.

3. **Timeline Chapter Markers & YouTube Timestamps**:
   - Clear old chapter markers if requested and add a `Blue` timeline marker at the exact start frame of each `V4` Tier A Chapter Banner (subtracting `tl.GetStartFrame()` so the frame offset is 0-based).
   - Export a clean YouTube chapters file (`MM:SS - Title`) directly to `<resolve_proj_dir>/youtube_chapters.txt`.
