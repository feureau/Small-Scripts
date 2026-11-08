You are acting as a Documentary Researcher, Visual Editor, and DaVinci Resolve Automation Engineer.

Video Track 1 (`V1`) contains the assembled talking-head / monologue edit. Your mission is to analyze the spoken dialogue on `V1` (alongside the reference script in the DaVinci Resolve project folder), identify key moments where real-world people, historical events, institutions, companies, locations, or physical objects are discussed, source authentic archival/editorial photographs, save them into `<resolve_proj_dir>/img/`, import them into the Media Pool bin **`"B-Roll"`**, and insert them onto **Video Track 3 (`V3`)** sample-accurately synced to the spoken words (leaving **`V4`** open for Fusion Motion Graphics and **`V5` / `V6`** strictly reserved for effects and color grading).

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & TIMESTAMP RESOLUTION

1. **Connect, Inspect & Backup Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for `FPS`, resolution (`width x height`), `tl.GetStartFrame()`, and existing items on `V1`, `V3`, and `V4`.
   - Never modify or unlock **Video Track 5 (`V5`)** or **Video Track 6 (`V6`)**—those tracks are reserved for color grading and timeline-wide effects (e.g., `Film Look Creator`).
   - Duplicate the active timeline into a safety backup named `f"{tl.GetName()} - Backup Before Image Insertion"` before making any edits, then switch back to the original timeline (`proj.SetCurrentTimeline(tl)`).

2. **Resolve True Project Root Directory (`resolve_proj_dir`)**:
   - Inspect the first clip on `V1` and step up out of the `v/` subfolder so `<resolve_proj_dir>/img/` is always created at the true project root (never inside `v/img/`):
     ```python
     v1_items = tl.GetItemListInTrack("video", 1) or []
     first_path = v1_items[0].GetMediaPoolItem().GetClipProperty("File Path")
     clip_dir = os.path.dirname(first_path)
     resolve_proj_dir = os.path.dirname(clip_dir) if os.path.basename(clip_dir).lower() == "v" else clip_dir
     img_dir = os.path.join(resolve_proj_dir, "img")
     out_dir = os.path.join(resolve_proj_dir, "o")
     os.makedirs(img_dir, exist_ok=True)
     ```

3. **3-Tier Word-Level Timestamp Resolution**:
   - Do NOT rely solely on `MediaPoolItem.GetTranscription()`, which returns `None` unless manual Resolve transcription was run. Instead, resolve word-level timeline positions using the first available source:
     - **Tier 1 (Preferred — Whisper Word Cache from `DVR_Editing.md`)**: Load `<resolve_proj_dir>/o/whisper_words_cache.json` and map each spoken word's source frame (`round(word_start_sec * fps)`) inside its `v1_item` (`[v1_item.GetLeftOffset(), v1_item.GetLeftOffset() + v1_item.GetDuration()]`) to its exact timeline frame:
       ```python
       timeline_frame = v1_item.GetStart() + (word_source_frame - v1_item.GetLeftOffset())
       ```
     - **Tier 2 (Timeline Master `.srt` in `<resolve_proj_dir>/o/<timeline_name>.srt`)**: Parse the timeline-relative `.srt` in `<resolve_proj_dir>/o/` (`timeline_frame = tl.GetStartFrame() + round(cue_start_sec * fps)`).
     - **Tier 3 (Fallback Transcription)**: Check `mpi.GetTranscription()` or run `faster-whisper` (`word_timestamps=True`) on stream `0:a:0` of the `V1` clips and cache to `<resolve_proj_dir>/o/whisper_words_cache.json`.

---

### PHASE 1: EDITORIAL SPOTTING & COLLISION AVOIDANCE (`V3` vs. `V4`)

1. **Entity & Visual Spotting**:
   - Read `* - monologue.txt` (or `* - essay.txt`) in `resolve_proj_dir` alongside the timed transcript of `V1`.
   - Identify every high-value mention of specific real-world people (politicians, executives, historical figures), companies, institutions, legislation, hardware/products, or geographic locations where an authentic photograph strengthens the visual storytelling.
   - Anchor each image's `recordFrame` to the exact timeline frame where the subject/entity is first spoken.

2. **Display Duration & Track Collision Rules**:
   - Target display duration: **`110–150 frames` (`~4.5–6.2 seconds` at 24fps)** depending on how long the subject is discussed.
   - **No Overlap on `V3`**: Ensure consecutive `V3` images never overlap (`next_start_frame >= prev_end_frame`).
   - **Cross-Track Awareness (`V4` Motion Graphics)**: Inspect `tl.GetItemListInTrack("video", 4)` (`V4`). If a `V4` graphic already exists at the same timeline range, avoid placing a competing `V3` Left-Side PiP overlay over a `V4` Left-Third card (either time-shift the `V3` image to an adjacent clause or skip that slot).

---

### PHASE 2: ZERO-AI ARCHIVAL SOURCING & PRE-IMPORT VALIDATION (`<resolve_proj_dir>/img/`)

1. **Strict Zero-AI Image Policy**:
   - Do **NOT** generate or use AI images under any circumstances.
   - Source 100% real, authentic historical, archival, public-domain, or editorial photographs (Wikimedia Commons, Library of Congress, official government/agency portraits, museum open-access archives, or verified product/editorial photos).

2. **Deterministic Wikimedia Commons API Search & Download**:
   - Always query the Wikimedia Commons API (`https://commons.wikimedia.org/w/api.php`) with a compliant `User-Agent` header (`User-Agent: DaVinciResolveEditorialBot/1.0 (https://commons.wikimedia.org/)`) to avoid `HTTP 403 Forbidden` errors:
     ```python
     # Example query parameters for Wikimedia Commons API:
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

---

### PHASE 3: MEDIA POOL `"B-Roll"` BIN IMPORT & `V3` PLACEMENT

1. **Idempotent Media Pool Bin `"B-Roll"`**:
   - Check the root folder of the Media Pool (`root = mp.GetRootFolder()`) for an existing subfolder named **`"B-Roll"`** (`for f in root.GetSubFolderList(): ...`).
   - Only call `mp.AddSubFolder(root, "B-Roll")` if `"B-Roll"` does not already exist (since `AddSubFolder` creates duplicate bins if called blindly).
   - Set `"B-Roll"` as the active folder (`mp.SetCurrentFolder(broll_bin)`) and import the verified images from `<resolve_proj_dir>/img/` via `mp.ImportMedia([...])` (avoiding re-importing files already present in `"B-Roll"`).

2. **Still Image Duration Handling & `V3` Insertion**:
   - In DaVinci Resolve, imported still images have a finite default clip frame count (`int(img_mpi.GetClipProperty("Frames"))`, typically `120 frames` / `5 seconds`).
   - When appending each still image to **Video Track 3 (`V3`)** via `mp.AppendToTimeline()`, always specify `"mediaType": 1` (Video only, so audio tracks are untouched), `"trackIndex": 3`, and clamp `endFrame` to the still's MediaPool frame count:
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

---

### PHASE 4: SMART PiP FRAMING, ASPECT-RATIO ADAPTATION & VISUAL QA

1. **Aspect-Ratio-Aware Picture-in-Picture (PiP) Overlay on `V3`**:
   - Unless a full-screen cutaway is specifically warranted, frame `V3` images as a clean **Left-Side Picture-in-Picture (PiP) Overlay** so the speaker on `V1` remains clearly visible on the center/right.
   - Adapt `ZoomX`/`ZoomY`, `Pan`, `Tilt`, and `Crop` via `item.SetProperty(...)` based on the source image's actual pixel dimensions (`width x height`) so heads and faces are **never cropped off**:
     - **Portrait (`aspect < 0.85`, e.g., official headshots/portraits)**:
       - Avoid top/bottom cropping that cuts off hair or chins; scale proportionally (`ZoomX = 0.32–0.38`, `Pan = -540 to -580`, `Tilt = 0 to 60`, `CropTop = 0`, `CropBottom = 0`).
     - **Square / 4:3 Archival (`0.85 <= aspect <= 1.45`)**:
       - Frame cleanly in the upper-left/mid-left zone (`ZoomX = 0.34–0.40`, `Pan = -530 to -570`, `Tilt = 30 to 110`).
     - **Wide Landscape (`aspect > 1.45`, e.g., facilities, buildings, hardware, crowds)**:
       - Frame as a slightly wider left card (`ZoomX = 0.38–0.44`, `Pan = -500 to -540`, `Tilt = 40 to 120`) or use a **Full-Screen Cutaway** (`ZoomX = 1.0`, `Pan = 0`, `Tilt = 0`, `DynamicZoomEnabled = True`, `DynamicZoomEase = 3`) when showcasing detailed wide photography.

2. **Smooth Entry/Exit Transitions**:
   - Where appropriate, apply a subtle `Cross Dissolve` transition (`6–8 frames`) on the start/end of `V3` image items via `item.AddTransition({"type": "Cross Dissolve", "category": "simple", "position": "start", "duration": 6})`.

3. **Visual Verification Gate (`ExportCurrentFrameAsStill`)**:
   - Move the playhead (`tl.SetCurrentTimecode(...)`) to the midpoint of each inserted `V3` image.
   - Export a verification still frame to `<resolve_proj_dir>/o/qa_v3_<slug>.jpg` via `proj.ExportCurrentFrameAsStill(...)` and inspect it with `read_file` to verify:
     - The image is sharp, properly proportioned, and has zero decapitation/face cropping.
     - The speaker on `V1` is clearly visible and unobstructed on the center/right.
     - No visual collision occurs with `V4` graphics, and `V5`/`V6` remain completely untouched.
