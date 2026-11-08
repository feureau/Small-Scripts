You are acting as a Documentary Researcher, Senior Remotion Motion Graphics Engineer, Financial Data Visualizer, and DaVinci Resolve Automation Engineer.

Video Track 1 (`V1`) contains the assembled talking-head / monologue edit (with vocals on `A5` / `A6`). Your mission is to perform a **unified visual spotting pass** across `V1` and the reference script in `<resolve_proj_dir>`, and populate:
- **Video Track 7 (`V7`)** with **100% authentic archival/editorial photographs** (stored in `<resolve_proj_dir>/img/` and imported into the Media Pool bin **`"B-Roll"`**), and
- **Video Track 9 (`V9`)** with **3-Tier Remotion Motion Graphics & Animated Data Charts** (built with the **`remotion-best-practices` skill**, rendered as 10-bit **ProRes 4444 `.mov` with alpha transparency** into a dedicated `<resolve_proj_dir>/motion_graphics/` folder, and imported into the Media Pool bin **`"Motion Graphics"`**),
while keeping **`V6` strictly reserved for effects and color grading** and generating Timeline Chapter Markers + YouTube timestamps.

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & 3-TIER TIMESTAMP RESOLUTION

1. **Activate the `remotion-best-practices` Skill**:
   - Before authoring any Remotion compositions, load and follow the installed `remotion-best-practices` skill (`SKILL.md`, `remotion-create/REFERENCE.md`, `remotion-markup/REFERENCE.md`, and `remotion-render/transparent-videos.md`).

2. **Connect, Inspect & Backup Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for `FPS` (e.g., `24` or `23.976`), resolution (`width x height`, e.g., `1920x1080`), `tl.GetStartFrame()`, and track counts.
   - **Track Reservation Rule**: Never modify, unlock, or place clips on **Video Track 6 (`V6`)**—that track is reserved for color grading and timeline-wide effects (e.g., `Film Look Creator`).
   - Duplicate the active timeline into a safety backup named `f"{tl.GetName()} - Backup Before Visuals (V7 & V9)"` before making any edits, then switch back to the original timeline (`proj.SetCurrentTimeline(tl)`).

3. **Resolve True Project Root Directory (`resolve_proj_dir`) & Dedicated Folders — NEVER Create an `o/` Folder**:
   - Inspect the first clip on `V1` and step up out of the `v/` subfolder so `<resolve_proj_dir>/img/` and `<resolve_proj_dir>/motion_graphics/` are created directly under the true project root. **Strictly NEVER create or write files into an `o/` subfolder**:
     ```python
     v1_items = tl.GetItemListInTrack("video", 1) or []
     first_path = v1_items[0].GetMediaPoolItem().GetClipProperty("File Path")
     clip_dir = os.path.dirname(first_path)
     resolve_proj_dir = os.path.dirname(clip_dir) if os.path.basename(clip_dir).lower() == "v" else clip_dir
     img_dir = os.path.join(resolve_proj_dir, "img")
     mg_dir = os.path.join(resolve_proj_dir, "motion_graphics")
     mg_renders_dir = os.path.join(mg_dir, "renders")
     qa_dir = os.path.join(mg_dir, "qa")
     os.makedirs(img_dir, exist_ok=True)
     os.makedirs(mg_renders_dir, exist_ok=True)
     os.makedirs(qa_dir, exist_ok=True)
     ```

4. **3-Tier Word-Level Timestamp Resolution**:
   - Do NOT rely solely on `MediaPoolItem.GetTranscription()`, which returns `None` unless manual Resolve transcription was run. Resolve word-level timeline positions using the first available source:
     - **Tier 1 (Preferred — Whisper Word Cache from `DVR_Editing.md`)**: Load `<resolve_proj_dir>/v/whisper_words_cache.json` and map each spoken word's source frame (`round(word_start_sec * fps)`) inside its `v1_item` (`[v1_item.GetLeftOffset(), v1_item.GetLeftOffset() + v1_item.GetDuration()]`) to its exact timeline frame:
       ```python
       timeline_frame = v1_item.GetStart() + (word_source_frame - v1_item.GetLeftOffset())
       ```
     - **Tier 2 (Timeline Master `.srt` in `v/` or `output/`)**: Parse `<resolve_proj_dir>/v/<timeline_name>.srt` (or `<resolve_proj_dir>/output/<timeline_name>.srt` if rendered from Resolve Deliver page).
     - **Tier 3 (Fallback Transcription)**: Check `mpi.GetTranscription()` or run `faster-whisper` (`word_timestamps=True`) on stream `0:a:0` of the `V1` clips and cache to `<resolve_proj_dir>/v/whisper_words_cache.json`.

---

### PHASE 1: UNIFIED MASTER VISUAL SPOTTING & COLLISION MATRIX (`V7` + `V9`)

1. **Modality Assignment (Right Visual for Every Beat)**:
   - Analyze the spoken dialogue on `V1` alongside `* - monologue.txt` / `* - essay.txt` in `resolve_proj_dir` to build a single **Unified Master Visual Spotting Sheet** before downloading or building anything:
     - **Track `V7` — Archival / Editorial Photographs**: Assign whenever specific real-world people (politicians, executives, historical figures), companies, buildings, hardware/products, institutions, or geographic locations are introduced.
     - **Track `V9` (Tier A) — Top Chapter Banners (Remotion Transparent Overlay)**: Assign at major Act breaks and topic transitions (occupying the top ~14% of the $1920 \times 1080$ canvas so the lower 85% stays completely transparent over the speaker on `V1`).
     - **Track `V9` (Tier B) — Left-Third Data & Alert Cards (Remotion Transparent Overlay)**: Assign when key statistics, percentages, dollar figures, dates, quotes, or punchy analogies are spoken (occupying the left ~35% of the canvas so the center/right stays completely transparent over the speaker on `V1`).
     - **Track `V9` (Tier C) — Full-Screen Animated Charts & Presentations (Remotion Full Canvas)**: Reserve exclusively for multi-point historical trends, multi-company breakdowns, or multi-column comparison tables requiring the full $1920 \times 1080$ canvas.

2. **Spatial & Temporal Collision Matrix (`V7` vs. `V9`)**:
   - **Rule 1 (`V7` Photo vs. `V9` Tier B Left-Third Card / Tier C Full-Screen Chart)**: Strictly **mutually exclusive in time**. Never overlap a `V7` PiP photo and a `V9` Left-Third Card or Full-Screen Chart on the same frames. When a sentence names both a person/company and a statistic (e.g., *"Elon Musk personally dropping $445 million..."*), schedule a **1–2 sequential visual combo**: show the `V7` photo on the entity name (`~90–120 frames`), then cut cleanly to the `V9` Remotion data card on the number (`~150–180 frames`).
   - **Rule 2 (`V7` Left PiP Photo + `V9` Tier A Top Banner)**: Allowed to overlap only if the `V7` photo's vertical `Tilt` stays below the top 15% banner zone (`Tilt <= 20`).
   - **Rule 3 (Intra-Track Spacing)**: Ensure zero overlapping clips on `V7` (`next_start >= prev_end`) and zero overlapping clips on `V9`.

---

### PHASE 2: TRACK `V7` — ZERO-AI ARCHIVAL IMAGE SOURCING & SMART PiP FRAMING

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

4. **Idempotent Media Pool Bin `"B-Roll"` & `V7` Placement**:
   - Find or create the subfolder **`"B-Roll"`** at the root of the Media Pool (`root = mp.GetRootFolder()`), checking `root.GetSubFolderList()` first so duplicate `"B-Roll"` bins are never created.
   - Import the verified images from `<resolve_proj_dir>/img/` into `"B-Roll"`.
   - Clamp `endFrame` to the still clip's MediaPool frame limit (`int(img_mpi.GetClipProperty("Frames") or 120) - 1`) and append onto **Video Track 7 (`V7`)** with `"mediaType": 1` (Video only):
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

5. **Mandatory `SCALE_FIT` Anti-Crop Rule & Editorial Decision Framework (`1920x1080` 16:9 AND `1440x1080` 4:3)**:
   - Query the active timeline's exact resolution dynamically (`tl_w = int(tl.GetSetting("timelineResolutionWidth") or 1920)`, `tl_h = int(tl.GetSetting("timelineResolutionHeight") or 1080)`, `pan_scale = tl_w / 1920.0`) so both **`1920x1080` (16:9)** and **`1440x1080` (4:3)** timelines are natively accommodated.
   - **CRITICAL ANTI-CROP MANDATE (`Scaling = resolve.SCALE_FIT`)**:
     - DaVinci Resolve projects often default to `timelineInputResMismatchBehavior = "scaleToCrop"`. If a `V7` clip is left at `"Scaling": 0` (`resolve.SCALE_USE_PROJECT`), Resolve zooms in and crops off the top/bottom of vertical photos and the left/right of wide photos *before* `ZoomX` is applied!
     - On **every single `V7` image** (both Full-Screen and PiP), you MUST set `item.SetProperty("Scaling", resolve.SCALE_FIT)` (`2` = `"Scale entire image to fit"`), clear all `Crop*` offsets to `0.0`, and set `DynamicZoomEnabled = False` so **100% of the image is visible with zero cropping**.
   - **Full-Screen / Center-Fitted Cutaway (`Scaling = resolve.SCALE_FIT`, `ZoomX = 1.0`, `ZoomY = 1.0`, `Pan = 0.0`, `Tilt = 0.0`, `DynamicZoomEnabled = False`)**:
     - Fits 100% of the image edge-to-edge on its longest axis inside the timeline frame (`1440x1080` or `1920x1080`), allowing the background `V1` video layer to remain naturally visible around any top/bottom or left/right aspect-ratio margins.
   - **Contextual Monologue Triggers — Use a FULL-SCREEN FITTED CUTAWAY whenever ANY of these 6 editorial conditions apply**:
     1. **"Show, Don't Tell" Visual Evidence & Inspection**: The speaker directs the audience to examine specific proof (`"if you look at the coverage..."`, `"look at the paperwork..."`, headlines, filings, ballots, maps, or physical hardware like RAM sticks/chips) that requires full-screen legibility.
     2. **Vivid Analogies, Metaphors & Visual Punchlines**: The monologue delivers a concrete metaphor, comparison, or comedic punchline (e.g., *"a reasonably reliable used Honda Civic"*, *"plugging six commercial deep-fryers into a three-dollar extension cord"*, *"a storage shed in rural Japan"*). Cutting full-screen on the punchline maximizes comedic/rhetorical payoff.
     3. **Dramatic / Emotional Turning Points**: High-stakes moments, market crashes, geopolitical clashes, or thesis reveals where removing the talking head lets the visual gravity land without distraction.
     4. **Talking-Head Fatigue Reset ("20-Second Breather Rule")**: Whenever the speaker on `V1` has remained continuously visible (solo or with only small PiP/Left-Third cards) for **`> 20–25 seconds` (`480–600 frames`)**, promote the next image to a **Full-Screen Fitted Cutaway** to reset the viewer's eye and break static framing monotony.
     5. **Masking `V1` Jump-Cuts**: When a visual lands across a seam between two different `V1` takes (`v1_items[i]` $\rightarrow$ `v1_items[i+1]`) with a noticeable posture shift, use a **Full-Screen Fitted Cutaway** to hide the jump-cut seamlessly.
     6. **Scale, Environment & Multi-Person Scenes**: Establishing shots of infrastructure, data centers, fabs, trading floors, crowds, or historical scenes where scale and detail would be cramped inside a PiP box.
   - **When to Use LEFT-SIDE PiP OVERLAY (`Scaling = resolve.SCALE_FIT`, The Analytical / Conversational Layer)**:
     - Use Left-Side PiP when the speaker's facial expressions and conversational delivery drive the point and you are **tagging a named individual, executive, politician, or company** in passing:
       - **Portrait (`aspect < 0.85`, e.g., official headshots/portraits)**: `Scaling = resolve.SCALE_FIT`, `ZoomX = 0.34–0.38`, `Pan = round(-560 * pan_scale)`, `Tilt = 40 to 80`, `CropTop = 0`, `CropBottom = 0`.
       - **Square / Compact (`0.85 <= aspect < 1.30`, or `4:3` single-person headshots kept as PiP)**: `Scaling = resolve.SCALE_FIT`, `ZoomX = 0.35–0.40`, `Pan = round(-550 * pan_scale)`, `Tilt = 40 to 100`.
       - **Landscape Kept as PiP (`aspect >= 1.30` for quick conversational entity tags)**: `Scaling = resolve.SCALE_FIT`, `ZoomX = 0.36–0.42`, `Pan = round(-520 * pan_scale)`, `Tilt = 40 to 100`.
   - Apply a subtle `Cross Dissolve` (`6–8 frames`) transition on entry/exit where appropriate.

---

### PHASE 3: TRACK `V9` — 3-TIER REMOTION MOTION GRAPHICS & BROADCAST DESIGN SYSTEM

> **CORE DESIGN MANDATE ("DESIGN A VIDEO, NOT A WEBPAGE")**:
> Follow the visual language of premier investigative video essays (**Vox, Bloomberg Originals, Johnny Harris, Financial Times**): one clear focal hero per frame, strict **12–15 word maximum** on cards, tactile multi-layered surfaces, kinetic tabular typography, and 5-stage spring choreography.

1. **Remotion Project Setup & Video-First Typography (`<resolve_proj_dir>/motion_graphics/`)**:
   - Maintain a clean Remotion workspace in `<resolve_proj_dir>/motion_graphics/` matching the DaVinci Resolve timeline resolution dynamically (`width = tl_w`, `height = tl_h` — supporting both **`1920x1080` 16:9** and **`1440x1080` 4:3** timelines) and frame rate (`fps = 24`), with `durationInFrames = max(160, word_count * 8)`.
   - **Editorial Font Pairing (`@remotion/google-fonts`)**:
     - **Display / Headlines**: `Space Grotesk` or `Syne` paired with `Instrument Serif` (italicized accent words / chapter numerals).
     - **Data / Numbers / Tickers**: `JetBrains Mono` or `IBM Plex Mono` with **`fontVariantNumeric: "tabular-nums"`** so rolling animated numbers never jitter horizontally.
     - **Labels / Footers**: `Inter` or `DM Sans`.
   - **Broadcast Font Size Minimums (scaled by `tl_w / 1920.0`)**:
     - **Hero Stat / Counter (`Tier B` / `Tier C`)**: **`96px – 136px`**, `fontWeight: 800`, `letterSpacing: "-0.04em"`, `lineHeight: 0.95`.
     - **Primary Headline / Chapter Title**: **`52px – 76px`**, `fontWeight: 700`, `letterSpacing: "-0.025em"`, `lineHeight: 1.08`.
     - **Sub-Label / Context Callout**: **`30px – 40px`**, `fontWeight: 500`, `color: "rgba(226, 232, 240, 0.88)"`.
     - **Eyebrow Pill / Source Citation Footer**: **`22px – 26px`** (uppercase, `letterSpacing: "0.12em"`, `fontWeight: 600` — never below `22px`!).

2. **Dynamic 3-Tier Visual Hierarchy, Tactile Surfaces & Semantic Color System**:
   - **CRITICAL — Transparent Root `<AbsoluteFill>` (`backgroundColor: 'transparent'`)**:
     - For **Tier A (Top Chapter Banners)** and **Tier B (Left-Third Data & Alert Cards)**, the outer `<AbsoluteFill>` MUST have a 100% transparent background (`backgroundColor: "transparent"`) so the speaker on Track `V1` remains completely visible!
   - **Tactile Layered Glassmorphic Obsidian Surface**:
     - Plate fill: `linear-gradient(145deg, rgba(13, 18, 30, 0.94) 0%, rgba(7, 10, 17, 0.98) 100%)` with an internal SVG micro-grid or dot-matrix pattern at `0.04` opacity, `1px solid rgba(255, 255, 255, 0.12)` inner specular rim, `4px` glowing semantic accent bar, and deep elevation shadow (`0 24px 60px rgba(0, 0, 0, 0.65)`).
   - **Semantic Accent Palette**:
     - **Macro / Tech / Infrastructure**: Electric Cyan (`#38BDF8`).
     - **Capital / Billionaires / Wealth**: Amber Gold (`#F59E0B`).
     - **Market Crash / Debt / Losses / Bans**: Crimson Rose (`#F43F5E`).
     - **Growth / Profit / Recovery**: Emerald (`#10B981`).
   - **Hand-Drawn Callout Annotations (`@remotion/rough-notation`)**:
     - Use `<Highlight>`, `<Underline>`, `<Circle>`, and `<Box>` driven by `interpolate(frame, ...)` to emphasize key words in quotes, ballot measures, or regulatory filings.
   - **3-Tier Layout Zones**:
     - **Tier A — Top Chapter Banners (`V9` Transparent Overlay)**: `top: 48px`, `left: 76px`, `right: 76px`, `height: ~130px` (leaves lower 85% transparent).
     - **Tier B — Left-Third Data & Alert Cards (`V9` Transparent Overlay)**: `left: 72px`, `top: 160px`, `width: round(640 * (tl_w / 1920.0))`, `maxHeight: 740px` (leaves center and right transparent over the speaker).
     - **Tier C — Full-Screen Dedicated Presentations & Charts (`V9` Full Canvas)**: Reserved EXCLUSIVELY for complex multi-column comparison tables, timelines, or multi-point historical charts requiring the full `tl_w x tl_h` canvas.

3. **5-Stage Animation Choreography & Proportional Data Plotting**:
   - Drive all animations via `useCurrentFrame()` and inline `interpolate()` using CSS `scale`, `translate`, and `rotate` properties (never CSS `transition` or Tailwind animation classes):
     - **Stage 1 (`Frames 0–16`)**: Card entrance (`Easing.spring({ damping: 180 })`, `output: "perceptual-scale"`, `translate: "-36px 0px" -> "0px 0px"`) + accent bar sweep.
     - **Stage 2 (`Frames 6–34`)**: Staggered eyebrow badge reveal + hero statistic count-up (`0 -> target` with `Easing.bezier(0.16, 1, 0.3, 1)` and `tabular-nums`).
     - **Stage 3 (`Frames 16–46`)**: SVG chart bar growth, line path `strokeDashoffset` draw-on, or `@remotion/rough-notation` sweep.
     - **Stage 4 (`Frames 46` to `durationInFrames - 16`)**: Subtle ambient micro-motion (pulsing live indicator dot, gentle glow breath, or slow background grid drift) so the graphic never looks frozen.
     - **Stage 5 (`Final 14 Frames`)**: Clean staggered exit (`opacity: 1 -> 0`, `translate: "0px 0px" -> "0px -16px"`).
   - **Proportional Chart Geometry Mandate**:
     - Research and verify all historical numbers; calculate every SVG bar height and line vertex mathematically:
       $$Y_{\text{px}} = Y_{\text{bottom}} - \left(\frac{\text{Value} - \text{Val}_{\min}}{\text{Val}_{\max} - \text{Val}_{\min}}\right) \times \text{ChartHeight}$$

4. **Rendering Transparent ProRes 4444 `.mov` & Inserting onto Track `V9`**:
   - First verify each composition class/tier using `npx remotion still` (rendering a midpoint PNG to `<resolve_proj_dir>/motion_graphics/qa/` and inspecting it via `read_file` to confirm typography, spacing, and zero text overflow).
   - Render every `V9` composition to `<resolve_proj_dir>/motion_graphics/renders/<slug>.mov` using **ProRes 4444 with Alpha (`yuva444p10le`)** (ideal for DaVinci Resolve):
     ```bash
     npx remotion render --image-format=png --pixel-format=yuva444p10le --codec=prores --prores-profile=4444 <CompId> "<resolve_proj_dir>/motion_graphics/renders/<slug>.mov"
     ```
   - Find or create the Media Pool subfolder **`"Motion Graphics"`** at the root of the Media Pool (`root = mp.GetRootFolder()`), import all rendered `.mov` files from `<resolve_proj_dir>/motion_graphics/renders/`, and append each clip directly onto **Video Track 9 (`V9`)** at its exact `recordFrame`:
     ```python
     total_frames = int(mov_mpi.GetClipProperty("Frames"))
     appended = mp.AppendToTimeline([{
         "mediaPoolItem": mov_mpi,
         "startFrame": 0,
         "endFrame": total_frames - 1,
         "mediaType": 1,
         "trackIndex": 9,
         "recordFrame": int(target_timeline_frame),
     }])
     ```
   - Ensure each imported `.mov` on `V9` has its Alpha Mode set properly (`mov_mpi.SetClipProperty("Alpha mode", "Premultiplied")` or `"Straight"` if needed so transparency composites cleanly over `V1`).

---

### PHASE 4: PROTOTYPE & FINAL VISUAL QA GATE + YOUTUBE CHAPTERS

1. **Prototype Visual QA Gate (Before Batch Rendering)**:
   - After rendering and inserting the **FIRST `V7` PiP Image**, **FIRST `V9` Top Banner**, **FIRST `V9` Left-Third Card**, and **FIRST `V9` Full-Screen Chart**, move the DaVinci Resolve playhead (`tl.SetCurrentTimecode(...)`) to the midpoint of each item, export a timeline still frame to `<resolve_proj_dir>/motion_graphics/qa/qa_timeline_<slug>.jpg` via `proj.ExportCurrentFrameAsStill(...)`, and visually inspect the JPGs using `read_file` before batch-rendering the remaining compositions.

2. **Full Visual Verification**:
   - Inspect exported stills across all inserted `V7` and `V9` items to verify:
     - Zero decapitation or awkward face cropping on `V7` photos.
     - True alpha transparency on `V9` Tier A Banners and Tier B Cards over the speaker on `V1` (confirming `"Alpha mode"` is active and not blacking out `V1`).
     - Crisp typography, proportional chart geometry, zero text clipping, and zero visual collisions between `V7` and `V9` (while **`V6` remains completely untouched**).

3. **Timeline Chapter Markers & YouTube Timestamps**:
   - Clear old chapter markers if requested and add a `Blue` timeline marker at the exact start frame of each `V9` Tier A Chapter Banner (subtracting `tl.GetStartFrame()` so the frame offset is 0-based).
   - Export a clean YouTube chapters file (`MM:SS - Title`) directly to `<resolve_proj_dir>/youtube_chapters.txt`.
