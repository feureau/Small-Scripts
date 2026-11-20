You are acting as a Documentary Researcher, Visual Editor, and DaVinci Resolve Automation Engineer.

Your mission is to analyze the spoken dialogue on the assembled A-roll track (`V5` with `A5` in standard `1. Assembly 24p HDR` templates, or `V1` with `A5`/`A6` in simple timelines) alongside the reference script in `<proj_dir>`, identify key moments where real-world people, historical events, institutions, companies, games/software, locations, or physical objects are discussed, source **100% authentic archival/editorial photographs**, stage them into `<proj_dir>/02_Footage/Images/` (with originals in `raw/` — or `<proj_dir>/img/` in legacy layouts), import them into the Media Pool bin **`"B-Roll"`**, and insert them onto **Video Track 7 (`V7`)** sample-accurately synced to their exact spoken spans (avoiding collisions with any **`V9`** Motion Graphics and keeping **`V8` / `V6`** strictly untouched for color grading and effects).

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & 3-TIER TIMESTAMP RESOLUTION

1. **Connect, Auto-Detect Tracks & Backup Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for `FPS`, resolution (`tl_w x tl_h`), `tl.GetStartFrame()`, and track items:
     - **Dynamic Track Detection**: Detect active A-roll (`aroll_track = 5` if populated, else `1`) and grading track (`grade_track = 8` if populated or `aroll_track == 5`, else `6`). Never modify, unlock, or place clips on `grade_track` (`V8` `Film Look Creator` or `V6`), leaving `V7` *underneath* grading.
     - Duplicate the active timeline into `f"{tl.GetName()} - Backup Before Image Insertion (V7)"`, then switch back (`proj.SetCurrentTimeline(tl)`).

2. **Resolve Project Root (`proj_dir`) & Standard Numbered Folders — NEVER Create an `o/` Folder**:
   - Inspect the first clip on `aroll_track` and step up out of source subfolders (`02_Footage/...`, `v/`) to locate `proj_dir`. Prefer numbered workspaces (`01_Docs/`, `02_Footage/Images/{raw,qa}/`, `03_Transcripts/`) over legacy `img/` when numbered folders exist. **Strictly NEVER create or write files into an `o/` subfolder**:
     ```python
     aroll_track = 5 if (tl.GetItemListInTrack("video", 5) or []) else 1
     grade_track = 8 if ((tl.GetItemListInTrack("video", 8) or []) or aroll_track == 5) else 6
     first_path = (tl.GetItemListInTrack("video", aroll_track) or [])[0].GetMediaPoolItem().GetClipProperty("File Path")
     cur = os.path.dirname(first_path)
     while os.path.basename(cur).lower() in ("v", "video", "audio", "02_footage", "footage"):
         cur = os.path.dirname(cur)
     proj_dir = cur
     use_numbered = os.path.isdir(os.path.join(proj_dir, "03_Transcripts")) or os.path.isdir(os.path.join(proj_dir, "02_Footage"))
     img_dir = os.path.join(proj_dir, "02_Footage", "Images") if use_numbered else os.path.join(proj_dir, "img")
     raw_dir, qa_dir = os.path.join(img_dir, "raw"), os.path.join(img_dir, "qa")
     for d in (img_dir, raw_dir, qa_dir):
         os.makedirs(d, exist_ok=True)
     ```

3. **3-Tier Word-Level Timestamp Resolution (`word@rec_f..rec_end_f`)**:
   - Do NOT rely solely on `MediaPoolItem.GetTranscription()`. Resolve both **`rec_f`** and **`rec_end_f`** via:
     - **Tier 1 (Preferred — Cutlist + Whisper Word Cache)**: Load `<proj_dir>/03_Transcripts/*cutlist*.json` + `<proj_dir>/03_Transcripts/whisper_words_cache.json` (or legacy `v/whisper_words_cache.json`) and map each word's source frame inside its kept A-roll item `[GetLeftOffset(), GetLeftOffset() + GetDuration()]` to timeline frames `tl_start + (word_src_f - left_offset)`.
     - **Tier 2 (Timeline `.srt`)**: Parse `<proj_dir>/03_Transcripts/*edited_timeline*.srt` (or `v/` / `output/`).
     - **Tier 3 (Fallback Transcription)**: Run `faster-whisper` (`word_timestamps=True`) on stream `0:a:0` and cache to `03_Transcripts/whisper_words_cache.json`.

---

### PHASE 1: EDITORIAL SPOTTING, SPOKEN-SPAN BOUNDING & COLLISION AVOIDANCE (`V7` vs. `V9`)

1. **Entity & Visual Spotting with Dual Spoken Anchors (Zero Fixed-Length Cookie-Cutter Durations)**:
   - Read `01_Docs/*monologue*.txt` (or `*essay*.txt`) alongside the timed `aroll_track` word stream.
   - **Never assign fixed `108f` / `120f` / `144f` durations.** Every `V7` cue MUST declare:
     - `start_word`: `"<word>@<rec_f>"` — exact word where the visual subject or list item begins.
     - `end_word`: `"<word>@<rec_end_f>"` — final word of that spoken clause or visual beat before the speaker moves on.
     - `spoken_span_text`: exact transcript substring spanning `start_word..end_word`.
   - **Deterministic `[rec_in, rec_out]` Math**:
     - `rec_in = start_word.rec_f - 0..4f` (snap to an A-roll cut seam **only** if that cut seam sits within `<= 10f` of `start_word.rec_f` — never pad backward into an earlier clause).
     - `rec_out = min(end_word.rec_end_f + 6..10f, next_clause_first_word.rec_f - 2)` so stills exit cleanly before the speaker pivots to an unrelated thought.
   - **Context-Adaptive Duration Profiles**:
     - **Rapid-Fire Spoken Lists (`24–68f` / `1.0–2.8s` per item)**: When listing several titles/companies in one breath, cut each still cleanly from `item[i].start_word.rec_f` to `item[i+1].start_word.rec_f` (`4f` micro-dissolve or hard cut).
     - **Standard Clause Cutaways (`60–216f` / `2.5–9.0s`)**: Match exact spoken clause length.
     - **Sustained Single-Subject Explanations (`168–260f` / `7.0–10.8s`)**: Hold through the end of the thought (or transition between two distinct angles/images at the inter-sentence pause).

2. **Automated 4-Rule Boundary & Track Collision Validation**:
   - **No Overlap on `V7`**: Enforce `next_rec_in >= prev_rec_out`.
   - **Cross-Track Awareness (`V9` Motion Graphics)**: Inspect `tl.GetItemListInTrack("video", 9)`. Keep `V7` Full-Screen stills strictly non-overlapping with any `V9` item, and keep `V7` Left PiP strictly clear of `V9` Tier B/C items (handoff at the clause seam).
   - **Validator Assertions**: Flag any item with early entry `start_word.rec_f - rec_in > 16f`, mid-clause cutoff (`gap < 8f`, no punctuation), next-sentence bleed (`> 10f` past sentence end), or cookie-cutter clustering (**`> 20%`** of `V7` clips having identical integer `duration_frames`).

---

### PHASE 2: 3-TIER ZERO-AI ARCHIVAL SOURCING & CONTACT-SHEET QA

1. **Strict Zero-AI Image Policy**:
   - Do **NOT** generate or use AI images under any circumstances.

2. **3-Tier Deterministic Sourcing Pipeline + Repeated-Entity Variety**:
   - Query sources in strict priority order using compliant `User-Agent` headers and Windows `curl.exe -sSLf` fallback when Python `urllib` hits SSL errors:
     - **Tier 1 (Named People, Buildings, Institutions, Cities)**: **Wikipedia REST Summary Lead Image API** (`https://en.wikipedia.org/api/rest_v1/page/summary/<Canonical_Title>` $\rightarrow$ `originalimage.source`).
     - **Tier 2 (Video Games & Software)**: **Steam Store API** (`storesearch` $\rightarrow$ `https://store.steampowered.com/api/appdetails?appids=<id>` -> `screenshots[].path_full` + `header_image`, skipping index `0` if an accolades banner).
     - **Tier 3 (General B-Roll, Hardware, Scenes)**: Wikimedia Commons concise 2–3 word `intitle:` queries (`filetype:bitmap intitle:<short_query>`) with explicit exclusion filtering (`stamp of `, `colnect`, `189`, `190`, `tropenmuseum`, `haer `, `lccn`, `coat of arms`, `flag of `, `svg`, `logo`, `emblem`, `seal of `, `postcard`, `map`, `diagram`, `blueprint`).
   - **Repeated-Entity Variety Rule**: If any entity receives `> 8` visual beats in one video, supplement Store/Wikipedia imagery with official press-kit assets or distinct detail focal crops—or convert later callbacks to `V9` cards—rather than looping the same screenshots.
   - Save untouched downloads into **`<raw_dir>/<alpha_slug>.jpg`** and staged outputs into **`<img_dir>/<alpha_slug>.jpg`** using **strictly digit-free alphabetic slugs** (no `[0-9]` digits anywhere in filenames).

3. **Mandatory Contact-Sheet Visual QA Gate**:
   - Validate raster integrity (`width >= 720` or `>= 600`, `height >= 450` or `>= 600`, convert `.webp` to RGB `.jpg`), generate numbered 4-column thumbnail contact sheets in `<qa_dir>/sheet_N.jpg`, and **inspect every sheet via `read_file`** to catch bad homonyms, stamps, maps, or cropped portraits before timeline import.

---

### PHASE 3: MEDIA POOL `"B-Roll"` BIN IMPORT, `< 120f` STILL TRIMMING & `V7` PLACEMENT

1. **Idempotent Media Pool Bin `"B-Roll"`**:
   - Check the root folder of the Media Pool (`root = mp.GetRootFolder()`) for an existing subfolder named **`"B-Roll"`** (`for f in root.GetSubFolderList(): ...`). Only call `mp.AddSubFolder(root, "B-Roll")` if absent.
   - Import the verified staged images from `<img_dir>` via `mp.ImportMedia([...])` (avoiding duplicates) and assert right after import that every item returns `img_mpi.GetClipProperty("Type") == "Still"` (no digit sequences). *(If regenerating staged files on disk after import, call `img_mpi.ReplaceClip(staged_path)`.)*

2. **Resolve `< 120f` Still Duration Clamping Fix (`SetRightOffset`) & Sequential Montage Insertion**:
   - In DaVinci Resolve 21+, `img_mpi.GetClipProperty("Frames")` on a `"Still"` returns `"1"`, and `mp.AppendToTimeline` ignores `endFrame < 120` — always inserting **`120` frames (`5.0s`)**.
   - Append each clip onto **Video Track 7 (`V7`)** with `"mediaType": 1` (in batches of **`<= 25` items per MCP `run_script` call**) and **immediately trim any clip where `int(item.GetDuration()) != target_dur` via `SetRightOffset`**:
     ```python
     appended = mp.AppendToTimeline([{
         "mediaPoolItem": img_mpi,
         "startFrame": 0,
         "endFrame": target_dur - 1,
         "mediaType": 1,
         "trackIndex": 7,
         "recordFrame": int(rec_in),
     }])
     item = appended[0]
     cur_dur = int(item.GetDuration())
     if cur_dur != target_dur:
         item.SetRightOffset(int(item.GetRightOffset()) + (cur_dur - target_dur))
     ```
   - When inserting contiguous `< 120f` rapid-list montages, append and `SetRightOffset`-trim each still **sequentially one-by-one** before calling `AddTransition(...)` so `120f` default lengths never push subsequent stills forward (`alignment="center"` between touching stills, `"right"` on isolated entry, `"left"` on isolated exit).

---

### PHASE 4: MANDATORY `SCALE_FIT` ANTI-CROP RULE, OPAQUE FULL-SCREEN MATTE & VISUAL QA

> **CRITICAL ANTI-CROP MANDATE (`Scaling = resolve.SCALE_FIT`) & ZERO SPEAKER BLEED**:
> DaVinci Resolve projects often default to `timelineInputResMismatchBehavior = "scaleToCrop"`. Leaving a `V7` still at `"Scaling": 0` (`resolve.SCALE_USE_PROJECT`) crops off heads/edges before `ZoomX` is even applied!
> You **MUST** set `item.SetProperty("Scaling", resolve.SCALE_FIT)` (`2` = `"Scale entire image to fit"`) and `Crop* = 0.0` on **every `V7` image**.
> **Opaque Full-Screen Canvas Rule**: On Full-Screen `V7` cutaways (e.g., `16:9`, `2:1`, or vertical portraits on a `1440x1080` 4:3 timeline), leaving transparent margins under `SCALE_FIT` exposes the speaker's moving hands/arms/mic on `aroll_track` (`V5`/`V1`). Keep untouched downloads in `raw/<slug>.jpg` and stage Full-Screen `<slug>.jpg` pre-fitted onto an **opaque `tl_w x tl_h` obsidian matte canvas (`#04060A`)** (or subtle darkened blurred backdrop) so `SCALE_FIT` preserves 100% of the image while completely occluding `V5`/`V1`.

1. **Dynamic Timeline Resolution Support (`1920x1080` 16:9 AND `1440x1080` 4:3)**:
   - Query active resolution dynamically:
     ```python
     tl_w = int(tl.GetSetting("timelineResolutionWidth") or 1920)
     tl_h = int(tl.GetSetting("timelineResolutionHeight") or 1080)
     tl_aspect = tl_w / tl_h  # 1.778 for 1920x1080 (16:9), 1.333 for 1440x1080 (4:3)
     pan_scale = tl_w / 1920.0
     ```

2. **Editorial Decision Framework: Full-Screen Cutaway vs. Optional Left-Side PiP Overlay**:
   - First, on **EVERY** `V7` clip, enforce uncropped baseline fitting:
     ```python
     item.SetProperty("Scaling", resolve.SCALE_FIT)  # 2 = Scale entire image to fit (0% cropping!)
     item.SetProperty("CropLeft", 0.0)
     item.SetProperty("CropRight", 0.0)
     item.SetProperty("CropTop", 0.0)
     item.SetProperty("CropBottom", 0.0)
     ```
   - **Full-Screen / Center-Fitted Cutaway (`Scaling = resolve.SCALE_FIT`, `ZoomX = 1.0`, `ZoomY = 1.0`, `Pan = 0.0`, `Tilt = 0.0`, pre-padded onto opaque `tl_w x tl_h` `#04060A` canvas)**:
     - Covers 100% of `V5`/`V1` with zero speaker bleed and zero cropping.
     - Use Full-Screen cutaways whenever: showing documents/filings/screenshots/games/hardware, delivering metaphors/punchlines, hitting dramatic turns, breaking talking-head monotony (`> 20–25s` without a full visual break), masking A-roll jump-cuts (when seam is within `<= 10f`), or showing wide infrastructure/environments.
   - **Optional Left-Side PiP Overlay (`Scaling = resolve.SCALE_FIT`, only when Left PiP is requested alongside talking head)**:
     - **Portrait (`aspect < 0.85`)**: `ZoomX = 0.34–0.38`, `Pan = round(-560 * pan_scale)`, `Tilt = 40..80`, `Crop* = 0.0`.
     - **Square / Compact (`0.85 <= aspect < 1.30`)**: `ZoomX = 0.35–0.40`, `Pan = round(-550 * pan_scale)`, `Tilt = 40..100`.
     - **Landscape PiP (`aspect >= 1.30`)**: `ZoomX = 0.36–0.42`, `Pan = round(-520 * pan_scale)`, `Tilt = 40..100`.
     *(Skip Left PiP entirely when running a Full-Screen-only pass.)*

3. **Subtle Animation (`Dynamic Zoom`) & Per-Project Consistent Transitions**:
   - After enforcing `Scaling = resolve.SCALE_FIT` and `Crop* = 0.0`, enable eased Ken Burns motion (`item.SetProperty("DynamicZoomEnabled", True)`, `item.SetProperty("DynamicZoomEase", 2)`) on standard/sustained Full-Screen cutaways (keep `DynamicZoomEnabled = False` on rapid `< 60f` montage lists and PiP cards).
   - Design **one cohesive transition style per project** (`10` frames normally, `4` frames on rapid-fire lists, `category="simple"`) using verified transparent-safe built-ins: **`Blur Dissolve`**, **`Edge Wipe`**, **`Split`**, **`Non-Additive Dissolve`**, **`Center Wipe`**, or **`Cross Dissolve`** (avoid `Push`, `Clock Wipe`, and mirror-tiled `Slide Up`/`Slide Down`/`Zoom In`).

4. **Visual Verification Gate (`ExportCurrentFrameAsStill`)**:
   - Move the playhead (`tl.SetCurrentTimecode(...)`) to representative midpoints (including `< 120f` trimmed stills, rapid-list seams, and portraits/16:9 stills on `1440x1080` timelines).
   - Export stills to `<qa_dir>/qa_v7_<slug>.jpg` via `proj.ExportCurrentFrameAsStill(...)` and inspect with `read_file` to verify:
     - 0% cropping/decapitation, opaque canvas margins with 0% `V5`/`V1` speaker bleed on Full-Screen cutaways, crisp transition seams, zero `V7`/`V9` overlaps, and `grade_track` (`V8`/`V6`) untouched.
