You are acting as a Documentary Researcher, Visual Editor, and DaVinci Resolve Automation Engineer.

Video Track 1 (`V1`) contains the assembled talking-head / monologue edit (with vocals on `A5` / `A6`). Your mission is to analyze the spoken dialogue on `V1` (alongside the reference script in `<resolve_proj_dir>`), identify key moments where real-world people, historical events, institutions, companies, locations, or physical objects are discussed, source **100% authentic archival/editorial photographs**, save them into `<resolve_proj_dir>/img/`, import them into the Media Pool bin **`"B-Roll"`**, and insert them onto **Video Track 7 (`V7`)** sample-accurately synced to the spoken words (avoiding collisions with any Motion Graphics on **`V9`** and keeping **`V6`** strictly reserved for effects and color grading).

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & 3-TIER TIMESTAMP RESOLUTION

1. **Connect, Inspect & Backup Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for `FPS`, resolution (`width x height`), `tl.GetStartFrame()`, and existing items on `V1`, `V7`, and `V9`.
   - **Track Reservation Rule**: Never modify, unlock, or place clips on **Video Track 6 (`V6`)**—that track is reserved for color grading and timeline-wide effects (e.g., `Film Look Creator`).
   - Duplicate the active timeline into a safety backup named `f"{tl.GetName()} - Backup Before Image Insertion (V7)"` before making any edits, then switch back to the original timeline (`proj.SetCurrentTimeline(tl)`).

2. **Resolve True Project Root Directory (`resolve_proj_dir`) — NEVER Create an `o/` Folder**:
   - Inspect the first clip on `V1` and step up out of the `v/` subfolder so `<resolve_proj_dir>/img/` is always created directly under the true project root. **Strictly NEVER create or write files into an `o/` subfolder**:
     ```python
     v1_items = tl.GetItemListInTrack("video", 1) or []
     first_path = v1_items[0].GetMediaPoolItem().GetClipProperty("File Path")
     clip_dir = os.path.dirname(first_path)
     resolve_proj_dir = os.path.dirname(clip_dir) if os.path.basename(clip_dir).lower() == "v" else clip_dir
     img_dir = os.path.join(resolve_proj_dir, "img")
     qa_dir = os.path.join(img_dir, "qa")
     os.makedirs(img_dir, exist_ok=True)
     os.makedirs(qa_dir, exist_ok=True)
     ```

3. **3-Tier Word-Level Timestamp Resolution**:
   - Do NOT rely solely on `MediaPoolItem.GetTranscription()`, which returns `None` unless manual Resolve transcription was run. Resolve word-level timeline positions using the first available source:
     - **Tier 1 (Preferred — Whisper Word Cache from `DVR_Editing.md`)**: Load `<resolve_proj_dir>/v/whisper_words_cache.json` and map each spoken word's source frame (`round(word_start_sec * fps)`) inside its `v1_item` (`[v1_item.GetLeftOffset(), v1_item.GetLeftOffset() + v1_item.GetDuration()]`) to its exact timeline frame:
       ```python
       timeline_frame = v1_item.GetStart() + (word_source_frame - v1_item.GetLeftOffset())
       ```
     - **Tier 2 (Timeline Master `.srt` in `v/` or `output/`)**: Parse `<resolve_proj_dir>/v/<timeline_name>.srt` (or `<resolve_proj_dir>/output/<timeline_name>.srt` if rendered from Resolve Deliver page).
     - **Tier 3 (Fallback Transcription)**: Check `mpi.GetTranscription()` or run `faster-whisper` (`word_timestamps=True`) on stream `0:a:0` of the `V1` clips and cache to `<resolve_proj_dir>/v/whisper_words_cache.json`.

---

### PHASE 1: EDITORIAL SPOTTING & COLLISION AVOIDANCE (`V7` vs. `V9`)

1. **Entity & Visual Spotting**:
   - Read `* - monologue.txt` (or `* - essay.txt`) in `resolve_proj_dir` alongside the timed transcript of `V1`.
   - Identify every high-value mention of specific real-world people (politicians, executives, historical figures), companies, institutions, legislation, hardware/products, or geographic locations where an authentic photograph strengthens the visual storytelling.
   - Anchor each image's `recordFrame` to the exact timeline frame where the subject/entity is first spoken.

2. **Display Duration & Track Collision Rules**:
   - Target display duration: **`110–150 frames` (`~4.5–6.2 seconds` at 24fps)** depending on how long the subject is discussed.
   - **No Overlap on `V7`**: Ensure consecutive `V7` images never overlap (`next_start_frame >= prev_end_frame`).
   - **Cross-Track Awareness (`V9` Motion Graphics)**: Inspect `tl.GetItemListInTrack("video", 9)` (`V9`). If a `V9` Left-Third card or Full-Screen chart already exists at the same timeline range, avoid placing a competing `V7` Left-Side PiP overlay on those frames (either time-shift the `V7` image to an adjacent clause or skip that slot).

---

### PHASE 2: ZERO-AI ARCHIVAL SOURCING & PRE-IMPORT VALIDATION (`<resolve_proj_dir>/img/`)

1. **Strict Zero-AI Image Policy**:
   - Do **NOT** generate or use AI images under any circumstances.
   - Source 100% real, authentic historical, archival, public-domain, or editorial photographs (Wikimedia Commons, Library of Congress, official government/agency portraits, museum open-access archives, or verified product/editorial photos).

2. **Deterministic Wikimedia Commons API Search & Download**:
   - Always query the Wikimedia Commons API (`https://commons.wikimedia.org/w/api.php`) with a compliant `User-Agent` header (`User-Agent: DaVinciResolveEditorialBot/1.0 (https://commons.wikimedia.org/)`) to avoid `HTTP 403 Forbidden` errors:
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
   - Save all downloaded images directly into **`<resolve_proj_dir>/img/<alpha_slug>.jpg`** (or `.png`) using **strictly digit-free alphabetic-sort slugs** (e.g., `aa_subject_name`, `ab_other_subject` — **NEVER include numeric digits `[0-9]` anywhere in image filenames**, or Resolve's sequence detector may import them as `Type: Video` image sequences instead of `Still`)—NEVER solely in the workspace or temp directory so the DaVinci Resolve project never goes `"Media Offline"`.

3. **Mandatory Pre-Import Image Validation Gate**:
   - Before importing into DaVinci Resolve, validate every file in `<resolve_proj_dir>/img/`:
     - Confirm the file is a valid raster image (`.jpg` or `.png`, NOT an HTML error page, `.svg`, or un-decoded `.webp`—if `.webp`, convert to high-quality RGB `.jpg` via Pillow or FFmpeg).
     - Verify resolution (`width >= 600` and `height >= 600`) and record its exact aspect ratio (`aspect = width / height`).
     - Visually inspect each downloaded image using `read_file` to confirm it accurately and cleanly depicts the intended person, place, or object.

---

### PHASE 3: MEDIA POOL `"B-Roll"` BIN IMPORT & `V7` PLACEMENT

1. **Idempotent Media Pool Bin `"B-Roll"`**:
   - Check the root folder of the Media Pool (`root = mp.GetRootFolder()`) for an existing subfolder named **`"B-Roll"`** (`for f in root.GetSubFolderList(): ...`).
   - Only call `mp.AddSubFolder(root, "B-Roll")` if `"B-Roll"` does not already exist (since `AddSubFolder` creates duplicate bins if called blindly).
   - Set `"B-Roll"` as the active folder (`mp.SetCurrentFolder(broll_bin)`) and import the verified images from `<resolve_proj_dir>/img/` via `mp.ImportMedia([...])` (avoiding re-importing files already present in `"B-Roll"`). Assert right after import that every imported image returns `img_mpi.GetClipProperty("Type") == "Still"` (if Resolve ever returns `"Video"`, stop and verify digit-free filenames and Media Storage *Frame Display Mode $\rightarrow$ Individual*).

2. **Still Image Duration Handling & `V7` Insertion**:
   - In DaVinci Resolve, imported still images have a finite default clip frame count (`int(img_mpi.GetClipProperty("Frames"))`, typically `120 frames` / `5 seconds`).
   - When appending each still image to **Video Track 7 (`V7`)** via `mp.AppendToTimeline()`, always specify `"mediaType": 1` (Video only, so audio tracks are untouched), `"trackIndex": 7`, and clamp `endFrame` to the still's MediaPool frame count:
     ```python
     max_still_frames = int(img_mpi.GetClipProperty("Frames") or 120)
     clip_end_frame = min(desired_duration_frames - 1, max_still_frames - 1)
     appended = mp.AppendToTimeline([{
         "mediaPoolItem": img_mpi,
         "startFrame": 0,
         "endFrame": clip_end_frame,
         "mediaType": 1,
         "trackIndex": 7,
         "recordFrame": int(target_timeline_frame),
     }])
     ```

---

### PHASE 4: MANDATORY `SCALE_FIT` ANTI-CROP RULE, PiP vs. FULL-SCREEN & VISUAL QA

> **CRITICAL ANTI-CROP MANDATE (`Scaling = resolve.SCALE_FIT`)**:
> DaVinci Resolve projects often default to `timelineInputResMismatchBehavior = "scaleToCrop"` (`Scale full frame with crop`). If a `V7` image clip is left at `"Scaling": 0` (`resolve.SCALE_USE_PROJECT`), Resolve zooms in and crops off the top/bottom of vertical photos and the left/right of wide photos *before* `ZoomX` is even applied!
> You **MUST** set `item.SetProperty("Scaling", resolve.SCALE_FIT)` (`2` = `"Scale entire image to fit"`) on **every single `V7` image** so 100% of the photograph is fitted properly without cropping. On Full-Screen / Center-Fitted images, use `Scaling = resolve.SCALE_FIT` (`2`), `ZoomX = 1.0`, `ZoomY = 1.0`, `Pan = 0.0`, `Tilt = 0.0`, and `DynamicZoomEnabled = False`—it is completely fine and expected for parts of the background video (`V1`) to remain visible around the edges when the image's aspect ratio differs from the timeline!

1. **Dynamic Timeline Resolution Support (`1920x1080` 16:9 AND `1440x1080` 4:3)**:
   - Query the active timeline's exact resolution dynamically:
     ```python
     tl_w = int(tl.GetSetting("timelineResolutionWidth") or 1920)
     tl_h = int(tl.GetSetting("timelineResolutionHeight") or 1080)
     tl_aspect = tl_w / tl_h  # 1.778 for 1920x1080 (16:9), 1.333 for 1440x1080 (4:3)
     ```
   - Never hardcode `1920x1080` assumptions—scale horizontal PiP `Pan` coordinates proportionally to `tl_w` (e.g., `pan_scale = tl_w / 1920.0`, so `Pan = -550 * pan_scale` is `-550` on `1920x1080` and `-412` on `1440x1080`).

2. **Editorial Decision Framework: Full-Screen Fitted Cutaway vs. Left-Side PiP Overlay**:
   - First, on **EVERY** `V7` clip (both Full-Screen and PiP), enforce uncropped fitting:
     ```python
     item.SetProperty("Scaling", resolve.SCALE_FIT)  # 2 = Scale entire image to fit (0% cropping!)
     item.SetProperty("CropLeft", 0.0)
     item.SetProperty("CropRight", 0.0)
     item.SetProperty("CropTop", 0.0)
     item.SetProperty("CropBottom", 0.0)
     item.SetProperty("DynamicZoomEnabled", False)
     ```
   - **Full-Screen / Center-Fitted Cutaway (`Scaling = resolve.SCALE_FIT`, `ZoomX = 1.0`, `ZoomY = 1.0`, `Pan = 0.0`, `Tilt = 0.0`, `DynamicZoomEnabled = False`)**:
     - Fits **100% of the image** edge-to-edge on its longest axis inside the timeline frame (`1440x1080` or `1920x1080`) with zero cropping, allowing the background `V1` video layer to show naturally behind any top/bottom or left/right aspect-ratio margins.
     - **Contextual Monologue Triggers — Use a FULL-SCREEN FITTED CUTAWAY whenever ANY of these 6 editorial conditions apply**:
       1. **"Show, Don't Tell" Visual Evidence & Inspection**: The speaker directs the audience to look at specific proof (`"if you look at the coverage..."`, `"look at the paperwork..."`, headlines, filings, ballots, maps, or physical hardware like RAM sticks/chips) that requires full-screen legibility.
       2. **Vivid Analogies, Metaphors & Visual Punchlines**: The monologue delivers a concrete metaphor, comparison, or comedic punchline (e.g., *"a reasonably reliable used Honda Civic"*, *"plugging six commercial deep-fryers into a three-dollar extension cord"*, *"a storage shed in rural Japan"*). Cutting full-screen on the punchline maximizes comedic/rhetorical payoff.
       3. **Dramatic / Emotional Turning Points**: High-stakes moments, market crashes, geopolitical clashes, or thesis reveals where removing the talking head lets the visual gravity land without distraction.
       4. **Talking-Head Fatigue Reset ("20-Second Breather Rule")**: Whenever the speaker on `V1` has remained continuously visible (solo or with only small PiP cards) for **`> 20–25 seconds` (`480–600 frames`)**, promote the next image to a **Full-Screen Fitted Cutaway** to reset the viewer's eye and break static framing monotony.
       5. **Masking `V1` Jump-Cuts**: When a visual lands across a seam between two different `V1` takes (`v1_items[i]` $\rightarrow$ `v1_items[i+1]`) with a noticeable posture shift, use a **Full-Screen Fitted Cutaway** to hide the jump-cut seamlessly.
       6. **Scale, Environment & Multi-Person Scenes**: Establishing shots of infrastructure, data centers, fabs, trading floors, crowds, or historical scenes where scale and detail would be cramped inside a PiP box.
   - **When to Use LEFT-SIDE PiP OVERLAY (`Scaling = resolve.SCALE_FIT`, The Analytical / Conversational Layer)**:
     - Use Left-Side PiP when the speaker's facial expressions and conversational delivery drive the point and you are **tagging a named individual, executive, politician, or company** in passing:
       - **Portrait (`aspect < 0.85`, e.g., official headshots/portraits)**:
         - With `Scaling = resolve.SCALE_FIT` (`2`), scale proportionally (`ZoomX = 0.34–0.38`, `Pan = round(-560 * (tl_w / 1920.0))`, `Tilt = 40 to 80`, `CropTop = 0`, `CropBottom = 0`).
       - **Square / Compact (`0.85 <= aspect < 1.30`, or `4:3` single-person headshots kept as PiP)**:
         - Frame cleanly in the upper-left/mid-left zone (`ZoomX = 0.35–0.40`, `Pan = round(-550 * (tl_w / 1920.0))`, `Tilt = 40 to 100`).
       - **Landscape Kept as PiP (`aspect >= 1.30` when used for a quick conversational entity tag rather than a full-screen beat)**:
         - Frame as a left card (`ZoomX = 0.36–0.42`, `Pan = round(-520 * (tl_w / 1920.0))`, `Tilt = 40 to 100`).

3. **Subtle Animation (`Dynamic Zoom`) & Per-Project Consistent Transitions**:
   - Enable eased Ken Burns motion (`item.SetProperty("DynamicZoomEnabled", True)`, `item.SetProperty("DynamicZoomEase", 2)`) on `V7` image overlays *(using `Scaling = resolve.SCALE_FIT` first so full-screen & PiP photos never crop)*.
   - Design **one cohesive editorial transition look per project** (`10` frames, `category="simple"`, `position="start"/"right"` and `position="end"/"left"`) and apply it consistently across all `V7` items by framing (`pip` vs `fullscreen`) using Resolve's verified transparent-safe built-ins: **`Blur Dissolve`**, **`Edge Wipe`**, **`Split`**, **`Non-Additive Dissolve`**, **`Center Wipe`**, or **`Cross Dissolve`**. *(When authoring live inside Resolve scripts, `"Pop Wobble"` IN + `"Crash Zoom"` OUT via `category="fusion"` are also valid, whereas `Pop Wobble Reverse` only animates incoming `MainInput2` and stays static on `Clip -> Empty Gap` exits; avoid `Push`, `Clock Wipe`, and mirror-tiled `Slide Up`/`Slide Down`/`Zoom In`.)*

4. **Visual Verification Gate (`ExportCurrentFrameAsStill`)**:
   - Move the playhead (`tl.SetCurrentTimecode(...)`) to the midpoint of each inserted `V7` image.
   - Export a verification still frame to `<resolve_proj_dir>/img/qa/qa_v7_<slug>.jpg` via `proj.ExportCurrentFrameAsStill(...)` and inspect it with `read_file` to verify:
     - The image is sharp, properly proportioned, and has zero decapitation/face cropping.
     - The speaker on `V1` is clearly visible and unobstructed on the center/right.
     - No visual collision occurs with `V9` graphics, and `V6` remains completely untouched.
