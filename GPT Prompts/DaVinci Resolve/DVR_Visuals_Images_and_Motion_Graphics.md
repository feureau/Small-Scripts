You are acting as a Documentary Researcher, Senior Remotion Motion Graphics Engineer, Financial Data Visualizer, and DaVinci Resolve Automation Engineer.

Your mission is to perform a **unified visual spotting pass** across the assembled talking-head / monologue A-roll track (`V5` with `A5` in standard `1. Assembly 24p HDR` templates, or `V1` with `A5`/`A6` in simple timelines) and the reference script in `<proj_dir>`, and populate:
- **Video Track 7 (`V7`)** with **100% authentic archival/editorial photographs** (staged in `<proj_dir>/02_Footage/Images/` with untouched originals in `raw/` — or `<proj_dir>/img/` in legacy layouts — and imported into the Media Pool bin **`"B-Roll"`**), and
- **Video Track 9 (`V9`)** with **3-Tier Remotion Motion Graphics & Animated Data Charts** (built with the **`remotion-best-practices` skill**, rendered as 10-bit **ProRes 4444 `.mov` with alpha transparency** into `<proj_dir>/05_GFX_Audio/motion_graphics/renders/` — or `<proj_dir>/motion_graphics/renders/` — and imported into the Media Pool bin **`"Motion Graphics"`**),
while keeping the grading track (**`V8`** `Film Look Creator`, or **`V6`** in legacy timelines) strictly untouched, so `V7` stills sit **underneath** grading and `V9` UI overlays sit **above** grading, plus exporting YouTube chapters while preserving existing `Blue` Shorts markers.

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & 3-TIER TIMESTAMP RESOLUTION

1. **Activate the `remotion-best-practices` Skill**:
   - Before authoring any Remotion compositions, load and follow the installed `remotion-best-practices` skill (`SKILL.md`, `remotion-create/REFERENCE.md`, `remotion-markup/REFERENCE.md`, and `remotion-render/transparent-videos.md`).

2. **Connect, Auto-Detect Tracks & Backup Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for `FPS` (`24` or `23.976`), resolution (`tl_w x tl_h`, e.g., `1440x1080` 4:3 or `1920x1080` 16:9), `tl.GetStartFrame()`, and track contents:
     - **Dynamic Track Detection**: Check track `5` (`V5`) vs track `1` (`V1`) to locate the populated A-roll track (`aroll_track`), and detect the effects/grading track (`grade_track = 8` if `tl.GetItemListInTrack("video", 8)` or `aroll_track == 5`, else `6`). Never modify, unlock, or place clips on `grade_track` or empty reserved tracks (`V1`/`V2` in `1. Assembly 24p HDR` templates).
     - **Timeline Backup**: Duplicate the active timeline into `f"{tl.GetName()} - Backup Before Visuals (V7 & V9)"`, then switch back (`proj.SetCurrentTimeline(tl)`).

3. **Resolve Project Root (`proj_dir`) & Standard Numbered Folders — NEVER Create an `o/` Folder**:
   - Inspect the first clip on `aroll_track` (`tl.GetItemListInTrack("video", aroll_track)`) and step out of source subfolders (`02_Footage/Audio`, `02_Footage/Video`, `v/`) to locate `proj_dir`. Support numbered workspaces (`01_Docs/`, `02_Footage/Images/{raw,qa}/`, `03_Transcripts/`, `04_Timelines/Images/`, `05_GFX_Audio/motion_graphics/{studio,renders,qa}/`) first, or legacy `img/` + `motion_graphics/` if numbered folders do not exist. **Strictly NEVER create or write files into an `o/` subfolder**:
     ```python
     aroll_track = 5 if (tl.GetItemListInTrack("video", 5) or []) else 1
     grade_track = 8 if ((tl.GetItemListInTrack("video", 8) or []) or aroll_track == 5) else 6
     first_path = (tl.GetItemListInTrack("video", aroll_track) or [])[0].GetMediaPoolItem().GetClipProperty("File Path")
     # Step up from 02_Footage/... or v/ to proj_dir
     cur = os.path.dirname(first_path)
     while os.path.basename(cur).lower() in ("v", "video", "audio", "02_footage", "footage"):
         cur = os.path.dirname(cur)
     proj_dir = cur
     use_numbered = os.path.isdir(os.path.join(proj_dir, "03_Transcripts")) or os.path.isdir(os.path.join(proj_dir, "02_Footage"))
     img_dir = os.path.join(proj_dir, "02_Footage", "Images") if use_numbered else os.path.join(proj_dir, "img")
     img_raw_dir, img_qa_dir = os.path.join(img_dir, "raw"), os.path.join(img_dir, "qa")
     mg_dir = os.path.join(proj_dir, "05_GFX_Audio", "motion_graphics") if use_numbered else os.path.join(proj_dir, "motion_graphics")
     mg_renders_dir, qa_dir = os.path.join(mg_dir, "renders"), os.path.join(mg_dir, "qa")
     for d in (img_dir, img_raw_dir, img_qa_dir, mg_renders_dir, qa_dir):
         os.makedirs(d, exist_ok=True)
     ```

4. **3-Tier Word-Level Timestamp Resolution (`word@rec_f..rec_end_f`)**:
   - Do NOT rely solely on `MediaPoolItem.GetTranscription()`. Resolve both **`rec_f`** (word start) and **`rec_end_f`** (word end) using the first available source:
     - **Tier 1 (Preferred — Cutlist + Whisper Word Cache)**: Load `<proj_dir>/03_Transcripts/*cutlist*.json` + `<proj_dir>/03_Transcripts/whisper_words_cache.json` (or legacy `v/whisper_words_cache.json`) and map each word's source frame inside its kept A-roll item `[GetLeftOffset(), GetLeftOffset() + GetDuration()]` to timeline frames `tl_start + (word_src_f - left_offset)`.
     - **Tier 2 (Timeline `.srt`)**: Parse `<proj_dir>/03_Transcripts/*edited_timeline*.srt` (or `v/` / `output/`).
     - **Tier 3 (Fallback Transcription)**: Run `faster-whisper` (`word_timestamps=True`) on stream `0:a:0` of the kept audio and cache to `03_Transcripts/whisper_words_cache.json`.

---

### PHASE 1: UNIFIED MASTER VISUAL SPOTTING, SPOKEN-SPAN BINDING & COLLISION MATRIX (`V7` + `V9`)

1. **Modality Assignment (Right Visual for Every Beat)**:
   - Analyze the spoken dialogue on `aroll_track` alongside `01_Docs/*monologue*.txt` / `*essay*.txt` in `proj_dir` to build a single **Unified Master Visual Spotting Sheet** before downloading or rendering anything:
     - **Track `V7` — Archival / Editorial Photographs**: Assign whenever specific real-world people (politicians, executives, historical figures), companies, buildings, games/software, hardware/products, institutions, or geographic locations are discussed.
     - **Track `V9` (Tier A) — Top Chapter Banners (Remotion Transparent Overlay)**: Assign at major Act breaks and topic transitions (occupying the top ~14% of the canvas so the lower 85% stays completely transparent over the speaker).
     - **Track `V9` (Tier B) — Left-Third Data & Alert Cards (Remotion Transparent Overlay)**: Assign when key statistics, percentages, dollar figures, dates, quotes, or punchy analogies are spoken (occupying the left ~35% of the canvas so the speaker stays visible on the center/right).
     - **Track `V9` (Tier C) — Full-Screen Animated Charts & Presentations (Remotion Full Canvas)**: Reserve exclusively for multi-point historical trends, multi-company breakdowns, system/hierarchy diagrams, or comparison structures requiring the full `tl_w x tl_h` canvas.

2. **Spoken-Span Boundary Binding (Zero Fixed-Length Cookie-Cutter Durations)**:
   - Never assign a fixed duration constant per tier (e.g., `108f`, `120f`, `144f`, `192f`, `360f`). Every `V7` and `V9` spot MUST declare **dual word anchors** plus its exact spoken text:
     - `start_word`: `"<word>@<rec_f>"` — exact word where the subject, list item, stat, or claim begins.
     - `end_word`: `"<word>@<rec_end_f>"` — final word of that relevant clause/sentence before the speaker pivots.
     - `spoken_span_text`: exact transcript substring from `start_word` through `end_word`.
   - **Deterministic `[rec_in, rec_out]` Math**:
     - **`rec_in`**: For `V7`, set `start_word.rec_f - 0..4f` (snap to an adjacent A-roll cut seam **only** if that cut seam sits within `<= 10f` of `start_word.rec_f` — never back up into an earlier unrelated clause). For `V9`, set `start_word.rec_f - 6f` (`0.25s` lead-in so the 14-frame spring arrival lands cleanly on the spoken keyword/number).
     - **`rec_out`**: Set `end_word.rec_end_f + 6..10f` (brief settle in the natural breath at clause end), strictly clamped to **`<= next_clause_first_word.rec_f - 2f`** so the graphic never bleeds into the next sentence.
   - **Context-Adaptive Duration Expectations (Not Rigid Floors)**:
     - **Rapid-Fire Spoken Lists (`24–68f` / `1.0–2.8s` per item)**: When naming sequential games, companies, or entities in one breath, cut `V7` stills strictly from `item[i].start_word.rec_f` to `item[i+1].start_word.rec_f` using hard cuts or `4f` micro-dissolves + post-append `SetRightOffset` trimming in Resolve.
     - **Standard Spoken Clauses & Tier B Cards (`60–216f` / `2.5–9.0s`)**: Let actual spoken clause length dictate the exact frame count (`end_word.rec_end_f - start_word.rec_f`).
     - **Sustained Single-Subject Discussions (`168–260f` / `7.0–10.8s`)**: Hold across a multi-clause explanation of the same subject (or step cleanly between two distinct stills at the sentence break) rather than cutting mid-thought at a `144f` ceiling.
     - **Tier C Analytical Scenes (`180–432f` / `7.5–18.0s`)**: Span strictly from the setup word of the analysis to the final word of its takeaway sentence.
   - **Automated 4-Rule Boundary & Anti-Cookie-Cutter Validator** (run before any render or timeline edit):
     1. *No Early Entry Padding*: Error/flag if `start_word.rec_f - rec_in > 16f` (`0.67s`).
     2. *No Mid-Clause Cutoffs*: Error if `rec_out` ends between two words in the same clause (`gap < 8f` with no trailing `, . ? ! ; —`).
     3. *No Next-Sentence Bleed*: Error if `rec_out` extends `> 10f` past sentence-ending punctuation into the start of the next sentence.
     4. *Anti-Cookie-Cutter Check*: Warn/fail if **`> 20%`** of `V7` or `V9` clips share the exact same integer `duration_frames`.

3. **Spatial & Temporal Collision Matrix (`V7` vs. `V9`)**:
   - **Rule 1 (`V7` Full-Screen vs. `V9` Tier B/C, and `V7` PiP vs. `V9` Tier B/C)**: Strictly **mutually exclusive in time**. Never overlap a `V7` Full-Screen photo with any `V9` overlay, or a `V7` Left PiP photo with a `V9` Left-Third Card or Full-Screen Chart. When a sentence names both a person/company and a metric (e.g., *"Elon Musk personally dropping $445 million..."*), schedule a **clause-synced 1–2 visual handoff**: `V7` spans the entity clause (`start_word..entity_end_word`), cutting cleanly to `V9` on the stat clause (`stat_word..sentence_end_word`).
   - **Rule 2 (`V7` Left PiP Photo + `V9` Tier A Top Banner)**: Allowed to overlap only when Left-Side PiP is enabled and `V7` vertical `Tilt` keeps the frame below the top 15% banner zone (`Tilt <= 20`).
   - **Rule 3 (Intra-Track Spacing)**: Ensure zero overlapping clips on `V7` (`next_in >= prev_out`) and zero overlapping clips on `V9`.

---

### PHASE 2: TRACK `V7` — 3-TIER ZERO-AI IMAGE SOURCING, OPAQUE MATTE STAGING & `< 120f` TRIMMING

1. **Strict Zero-AI Image Policy**:
   - Do **NOT** generate or use AI images under any circumstances. Source 100% real archival, public-domain, Wikipedia infobox, official press-kit/Store, or Wikimedia Commons photographs.

2. **3-Tier Deterministic Sourcing Pipeline + Repeated-Entity Variety (`<proj_dir>/02_Footage/Images/`)**:
   - Query sources in strict priority order using compliant headers (`User-Agent: DaVinciResolveEditorialBot/1.0`) via Python or Windows `curl.exe -sSLf` fallback (which avoids Python OpenSSL certificate failures against Wikimedia):
     - **Tier 1 — Named People, Buildings, Institutions, Cities**: Query the **Wikipedia REST Summary Lead Image API** (`https://en.wikipedia.org/api/rest_v1/page/summary/<Canonical_Title>` $\rightarrow$ `originalimage.source`) to fetch the human-curated infobox hero photo directly.
     - **Tier 2 — Video Games & Software**: Query the **Steam Store API** (`storesearch` $\rightarrow$ `https://store.steampowered.com/api/appdetails?appids=<id>`) for official unwatermarked `1920x1080` `screenshots[].path_full` + `header_image` (automatically skipping screenshot index `0` if it is a review-accolade splash banner).
     - **Tier 3 — General B-Roll, Hardware & Abstract Scenes**: Query Wikimedia Commons using concise 2–3 word `intitle:` queries (`filetype:bitmap intitle:<terms>`) paired with an **explicit title exclusion filter** rejecting `stamp of `, `colnect`, `189`, `190`, `tropenmuseum`, `haer `, `lccn`, `coat of arms`, `flag of `, `svg`, `logo`, `emblem`, `seal of `, `postcard`, `map`, `diagram`, and `blueprint`:
       ```python
       params = {
           "action": "query", "format": "json", "generator": "search",
           "gsrsearch": f"filetype:bitmap intitle:{short_query}",
           "gsrnamespace": 6, "gsrlimit": 8,
           "prop": "imageinfo", "iiprop": "url|dimensions|mime", "iiurlwidth": 1920,
       }
       ```
   - **Repeated-Entity Variety Rule**: If any single game, person, or institution has `> 8` visual beats in one video, supplement Store/Wikipedia photos with official developer press-kit imagery or distinct focal-detail crops — or convert repeat callbacks to `V9` cards — rather than cycling the same ~8 screenshots.
   - Store untouched source files in **`raw/<alpha_slug>.jpg`** and staged Resolve-ready files in **`<alpha_slug>.jpg`** using **strictly digit-free alphabetic slugs** (e.g., `aa_subject_name`, **NEVER numeric digits `[0-9]` anywhere in filenames** so Resolve's sequence detector never treats them as `Type: Video`).

3. **Mandatory Contact-Sheet Visual QA Gate**:
   - Before importing into Resolve, validate every file (`width >= 720` or `>= 600`, `height >= 450` or `>= 600`, decode raster `.jpg`/`.png` cleanly, convert `.webp` via Pillow/FFmpeg), render numbered 4-column thumbnail contact sheets into `<img_qa_dir>/sheet_N.jpg`, and **inspect every contact sheet with `read_file`** to catch bad homonyms, stamps, maps, or cropped heads before editing the timeline.

4. **Idempotent Media Pool Bin `"B-Roll"`, `SetRightOffset` (`< 120f` Still Fix) & `V7` Placement**:
   - Find or create **`"B-Roll"`** under `root = mp.GetRootFolder()` (checking `root.GetSubFolderList()` first), import verified stills from `img_dir`, and assert `img_mpi.GetClipProperty("Type") == "Still"`.
   - **Resolve `< 120f` Still Clamping Bug**: In Resolve 21+, `img_mpi.GetClipProperty("Frames")` returns `"1"` for stills, and `mp.AppendToTimeline` ignores `endFrame < 120` — always inserting at least **`120` frames (`5.0s`)**. You MUST immediately trim any still whose planned `target_dur != int(item.GetDuration())` using **`SetRightOffset`**:
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
   - For contiguous `< 120f` still montages, append and `SetRightOffset`-trim each still sequentially one-by-one before applying transitions (`alignment="center"` on touching seams, `"right"` on isolated entry, `"left"` on isolated exit), and batch timeline appends in chunks of **`<= 25` items per MCP call** to stay well under Resolve's 10-second timeout.

5. **Mandatory `SCALE_FIT` Anti-Crop Rule, Opaque Full-Screen Matte Staging & Optional Left PiP (`1920x1080` 16:9 AND `1440x1080` 4:3)**:
   - Query timeline resolution dynamically (`tl_w = int(tl.GetSetting("timelineResolutionWidth") or 1920)`, `tl_h = int(tl.GetSetting("timelineResolutionHeight") or 1080)`, `pan_scale = tl_w / 1920.0`).
   - **CRITICAL ANTI-CROP MANDATE (`Scaling = resolve.SCALE_FIT`)**: Enforce `item.SetProperty("Scaling", resolve.SCALE_FIT)` (`2` = `"Scale entire image to fit"`) and `Crop* = 0.0` on **every `V7` image** so 0% of the photograph is auto-cropped by project mismatch settings.
   - **Opaque Matte Canvas Staging for Full-Screen Cutaways (Zero Speaker Bleed)**:
     - On `4:3` (`1440x1080`) or `16:9` (`1920x1080`) Full-Screen cutaways (`ZoomX = 1.0`, `ZoomY = 1.0`, `Pan = 0.0`, `Tilt = 0.0`), leaving transparent letterbox/pillarbox margins around `16:9`, `2:1`, or portrait stills allows the speaker's hands, shirt, and mic arm on `aroll_track` (`V5`/`V1`) to poke out behind the photo.
     - Therefore, keep the untouched image in `raw/<slug>.jpg` and stage the Full-Screen `<slug>.jpg` pre-fitted onto an **opaque `tl_w x tl_h` obsidian matte canvas (`#04060A`)** (or subtle darkened blurred backdrop) so `resolve.SCALE_FIT` displays 100% of the uncropped image while covering **100%** of the speaker underneath. *(If updating files on disk after Media Pool import, call `mpi.ReplaceClip(staged_path)`.)*
   - **Editorial Triggers for Full-Screen Cutaways**: Use whenever showing visual proof/documents/games/hardware, metaphors/punchlines, dramatic pivots, talking-head breather resets (`> 20–25s` without a full visual break), masking A-roll jump-cuts (when seam lies within `<= 10f`), or wide infrastructure/environments.
   - **Optional Left-Side PiP Overlay (`Scaling = resolve.SCALE_FIT`, only when explicitly using PiP)**:
     - Keep `ZoomX = 0.34–0.42`, `Pan = round(-560..-520 * pan_scale)`, `Tilt = 40..100` (clear of center speaker and top Tier A zone). For Full-Screen-only passes, set `0` Left PiP overlays.
   - **Animation (`Dynamic Zoom`) & Per-Project Consistent Transitions**: After setting `Scaling = resolve.SCALE_FIT` and `Crop* = 0.0`, apply subtle eased Ken Burns (`item.SetProperty("DynamicZoomEnabled", True)`, `item.SetProperty("DynamicZoomEase", 2)`) on Full-Screen cutaways (or `False` on `< 60f` rapid-fire montage cuts/PiP) and apply one cohesive `10f` (or `4f` on rapid lists) transition style per project via `AddTransition(..., category="simple")`: e.g., `Blur Dissolve`, `Edge Wipe`, `Split`, `Non-Additive Dissolve`, `Center Wipe`, or `Cross Dissolve` (avoid `Push`, `Clock Wipe`, and mirror-tiled `Slide Up`/`Slide Down`/`Zoom In`).

---

### PHASE 3: TRACK `V9` — 3-TIER REMOTION MOTION GRAPHICS & BROADCAST DESIGN SYSTEM

> **CORE DESIGN MANDATE ("DESIGN A VIDEO, NOT A WEBPAGE")**:
> Follow the visual language of premier investigative video essays (**Vox, Bloomberg Originals, Johnny Harris, Financial Times**): one clear focal hero per frame, strict **12–15 word maximum** on cards, tactile multi-layered surfaces, kinetic tabular typography, and spoken-synced spring choreography.

1. **Remotion Project Setup, Copy Hygiene & Video-First Typography (`<mg_dir>/studio/`)**:
   - Build a clean Remotion workspace in `<mg_dir>/studio/` matching timeline resolution dynamically (`width = tl_w`, `height = tl_h` — supporting `1440x1080` 4:3 and `1920x1080` 16:9) and `fps = 24`, setting `durationInFrames` directly from Spoken-Span Binding (`rec_out - rec_in`).
   - **Hyphen-Only Remotion `<Composition id>`**: Remotion rejects underscores (`_`) in composition IDs (`a-z, A-Z, 0-9, CJK, -` only). Use `id={sc.comp_id.replace(/_/g, "-")}` in `Root.tsx` even if `.mov` outputs keep underscores.
   - **Strict Copy Hygiene & Citation Rules**:
     - Enforce **`eyebrow.toLowerCase() !== headline.toLowerCase()`** across all Tier B cards (`eyebrow` = category/source e.g. `INDONESIA CONNECTIVITY`, `headline` = metric title e.g. `Internet User Base`).
     - **Ban Meta-Prompt Footer Leakage**: Never render internal spotting notes (`"(PER MONOLOGUE)"`, `"PER SCRIPT"`, `"VERIFIED DATA"`, `"SPEAKER ESTIMATE"`) in card footers. Require concrete broadcast attribution (`"SOURCE: WORLD BANK (2025) & PLN"`, `"SOURCE: MSCI EQUITY CONSULTATION"`).
   - **Editorial Font Pairing (`@remotion/google-fonts`)**:
     - Display / Headlines: `Space Grotesk` or `Syne` + `Instrument Serif` (italic accent words / chapter numerals).
     - Data / Numbers / Tickers: `JetBrains Mono` or `IBM Plex Mono` with **`fontVariantNumeric: "tabular-nums"`**.
     - Labels / Footers: `Inter` or `DM Sans`.
   - **Broadcast Font Size Minimums (scaled by `tl_w / 1920.0`)**:
     - Hero Stat / Counter: **`96px – 136px`**, `fontWeight: 800`, `letterSpacing: "-0.04em"`, `lineHeight: 0.95`.
     - Primary Headline / Chapter Title: **`52px – 76px`**, `fontWeight: 700`, `letterSpacing: "-0.025em"`, `lineHeight: 1.08`.
     - Sub-Label / Context Callout: **`30px – 40px`**, `fontWeight: 500`.
     - Eyebrow Pill / Source Citation Footer: **`22px – 26px`** (uppercase, `letterSpacing: "0.12em"`, never below `22px`).

2. **3-Tier Layout Zones, Tactile Surfaces & Diagrammatic Tier C Variety**:
   - **Root Transparency**: Tier A (Top Chapter Banners) and Tier B (Left-Third Cards) MUST render with `backgroundColor: "transparent"` so `aroll_track` (`V5`/`V1`) remains visible underneath.
   - **Safe Zones**:
     - **Tier A — Top Chapter Banners**: `top: 48px`, `left: 76px`, `right: 76px`, `height: ~130px` (bottom 85% transparent).
     - **Tier B — Left-Third Cards**: `left: 50–72px`, `top: 150px`, `width: round(640 * (tl_w / 1920.0))` (`~480–490px` on `1440x1080`), leaving center/right clear of the speaker.
     - **Tier C — Full-Screen Dedicated Analytical Scenes (`tl_w x tl_h`)**: Avoid defaulting every Tier C beat to dense 2/3-column bento text (`SceneComparisonMatrix`). Pick structural diagrammatic archetypes whenever the narrative involves dates, magnitude gaps, hierarchies, or cascades:
       - `SceneAreaCurveChart` (proportional market/time-series curves)
       - `SceneTimelineTrack` / `SceneCalendarCutoff` (chronologies & cutoff/release calendar clashes)
       - `SceneScaleDelta` (proportional capacity/budget comparison bars with animated deficit fills)
       - `SceneHierarchyTree` (reporting chains & governance org diagrams)
       - `SceneWaterfallFlow` (downgrade/outflow step cascades)
       - `SceneSystemDiagram` & `SceneComparisonMatrix` (compact 2/3-column synthesis only when structured prose fits cleanly)
   - **Surface & Palette**: Obsidian glass (`linear-gradient(145deg, rgba(13, 18, 30, 0.94) 0%, rgba(7, 10, 17, 0.98) 100%)`), subtle SVG grid/dot texture (`0.04` opacity), `1px` specular rim, `4px` semantic accent bar (`#38BDF8` Cyan, `#F59E0B` Amber, `#F43F5E` Crimson, `#10B981` Emerald), and `@remotion/rough-notation` emphasis (`<Highlight>`, `<Underline>`, `<Circle>`, `<Box>`).

3. **5-Stage Choreography, Word-Synced `enterAtFrame` & Proportional Data Plotting**:
   - Animate via `useCurrentFrame()` + `interpolate()` (inline CSS `scale`, `translate`, `rotate`; zero CSS transitions):
     - **Stage 1 (`Frames 0–16`)**: Spring card entrance + accent bar sweep.
     - **Stage 2 (`Frames 6–34`)**: Staggered eyebrow reveal + `tabular-nums` counter roll.
     - **Stage 3 (`Frames 16–46` or Word-Synced `enterAtFrame`)**: For multi-element `CardComparisonBar`, `CardMicroChronology`, `SceneTimelineTrack`, `SceneSystemDiagram`, and `SceneComparisonMatrix`, support optional per-item **`enterAtFrame = item_word.rec_f - clip.rec_in`** so bars, steps, nodes, or columns animate on the exact frame the speaker names each item instead of uniform `14 + idx * 14` offsets.
     - **Stage 4 (`Hold -> durationInFrames - 16`)**: Subtle ambient grid drift, live indicator pulse, and glow breath.
     - **Stage 5 (`Final 14 Frames`)**: Clean staggered exit (`opacity: 1 -> 0`, upward drift) completing right before `next_clause_first_word`.
   - **Proportional Chart Math**: Compute every SVG bar/line vertex mathematically from true data values:
     $$Y_{\text{px}} = Y_{\text{bottom}} - \left(\frac{\text{Value} - \text{Val}_{\min}}{\text{Val}_{\max} - \text{Val}_{\min}}\right) \times \text{ChartHeight}$$

4. **Pre-Bundled ProRes 4444 `.mov` Rendering & Batched `V9` Insertion**:
   - Verify prototype compositions with `npx remotion still` into `<qa_dir>/` (`read_file` check).
   - **Pre-Bundle Once Per Studio**: Configure `prores-4444` (`image-format=png`, `pixel-format=yuva444p10le`, `codec=prores`, `prores-profile=4444`) in `remotion.config.ts` (or CLI flags), run **`npx remotion bundle src/index.ts`** once into `build/`, and render every clip from `build/` (`npx remotion render build <hyphen-id> "<mg_renders_dir>/<comp_id>.mov"`) to eliminate per-clip Webpack bundling overhead.
   - Find/create **`"Motion Graphics"`** in the Media Pool, import `.mov` files in **batches of `<= 12` per MCP `run_script` call** (to stay under Resolve's 10s MCP timeout), set `mov_mpi.SetClipProperty("Alpha mode", "Premultiplied")`, and append onto **Video Track 9 (`V9`)** in **batches of `<= 25` items per call** (`mediaType: 1`, `startFrame: 0`, `endFrame: total_frames - 1`, `recordFrame: clip.rec_in`).

---

### PHASE 4: PROTOTYPE & FINAL VISUAL QA GATE + CHAPTERS

1. **Prototype & Full Visual Verification**:
   - Export timeline stills via `proj.ExportCurrentFrameAsStill(...)` across representative `V7` stills (checking `SCALE_FIT`, zero cropped heads, opaque matte hiding `V5`/`V1` speaker movement underneath) and `V9` Tier A / B / C overlays (verifying alpha compositing *above* `grade_track`, `4:3`/`16:9` speaker clearance, crisp typography, and zero `eyebrow == headline` or meta-footer artifacts), and inspect all exported JPGs with `read_file`.
   - Assert zero intra-track overlaps on `V7`/`V9`, `0` cross-track overlaps between `V7` Full-Screen stills and `V9`, and confirm `grade_track` (`V8`/`V6`) remains untouched.

2. **Timeline Chapter Markers & YouTube Timestamps**:
   - **Preserve Existing `Blue` Shorts Chapter Markers** if present (`tl.GetMarkers()`). Add Tier A act markers only at missing act starts (or in distinct marker color if already populated with `Blue` Shorts chapters), offsetting by `- tl.GetStartFrame()`.
   - Save clean `MM:SS - Title` YouTube chapters to `<proj_dir>/01_Docs/<stem>_youtube_chapters.txt` (or `<proj_dir>/youtube_chapters.txt` in legacy layouts) and a unified `<proj_dir>/01_Docs/<stem>_visual_spotting_sheet.md`.
