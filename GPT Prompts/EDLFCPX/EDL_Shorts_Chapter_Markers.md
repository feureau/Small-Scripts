You are acting as an elite Video Editor, Content Strategist, and Offline NLE Interchange Engineer (`CMX 3600 Timeline Markers .edl`).

I have an edited talking-head / video-essay timeline in a project folder (`<proj_dir>` — typically organized into `01_Docs/`, `02_Footage/`, `03_Transcripts/`, `04_Timelines/`). **Do NOT insert markers into DaVinci Resolve directly.** Your mission is to segment the edited timeline into high-retention Shorts chapters offline via Python and generate a ready-to-import **DaVinci Resolve Timeline Markers `.edl`** (`<proj_dir>/04_Timelines/Markers/<stem>_chapter_markers.edl`) synced frame-for-frame to the timeline's existing cuts.

---

### QUICK CLARIFICATION CHECK (Ask Only If Ambiguous)

Confirm or default cleanly to:
1. **Marker Color & Style**: **`Blue`** (`|C:ResolveColorBlue`) **point markers (`|D:1`)** with `Short 01: <Title>` ... + a closing **`Outro:`** marker bounding the end of the final Short *(unless range-duration `|D:<frames>` markers or another `ResolveColor<Name>` is requested)*.
2. **Segmentation Density**: Group natural essay paragraphs/topic beats into **`~45s–75s`** self-contained Shorts (keeping crisp standalone `~25s–35s` beats intact rather than forcing awkward mid-thought splits or exceeding `~75s`), covering `100%` of the timeline cleanly.
3. **Timeline Start Timecode Base**: Match the exact start timecode of the target timeline (`00:00:00:00` for `.otio` imports vs `01:00:00:00` / `86400` frames for FCP7 XML / CMX 3600 EDL imports) and `24.000` fps NDF *(or project timeline FPS)*.

---

### PHASE 0: OFFLINE SOURCE DISCOVERY & TIMECODE BASE DETECTION

1. **Locate Timeline Cut Boundaries & Transcripts (`<proj_dir>`)**:
   - **Standard Numbered Layout (NO `o/` Folder):** Save final marker EDLs into `<proj_dir>/04_Timelines/Markers/<stem>_chapter_markers.edl` (falling back to `<proj_dir>/` only if numbered folders aren't used). **Never create or write files into an `o/` subfolder.**
   - Gather exact cut frames and spoken dialogue cues in priority order (checking numbered folders first, with flat/`v/` fallback):
     1. `04_Timelines/B-Roll/*broll_spotting_sheet*.md` & `03_Transcripts/*broll_plan*.json` (gives exact `clip_idx`, `rec_in`, `rec_out`, `audio_cue`, and section headings).
     2. `04_Timelines/B-Roll/*.otio` or `04_Timelines/Assembly/*.otio` + `03_Transcripts/*edited_timeline*.srt`.
     3. `04_Timelines/Assembly/*.xml` / `*.edl` + `03_Transcripts/*cutlist*.json` + `03_Transcripts/whisper_words_cache.json` + `01_Docs/*monologue*.txt`.
   - Note: Never alter video tracks, audio tracks, or existing files (`DVR-Shorts Chapter Markers` non-destructive principle).

2. **Detect Exact Start Timecode & Frame Rate (`00:00:00:00` vs `01:00:00:00`)**:
   > **CRITICAL TIMECODE OFFSET RULE**:
   > If your target timeline starts at **`00:00:00:00`** (default when importing `Resolve_OTIO` `.otio` files with `global_start_time = 0.0`), writing markers at `01:00:00:00` places every marker one full hour past the end of the timeline! Conversely, writing `00:00:00:00` markers into a `01:00:00:00` sequence places them one hour before frame `0` (invisible on the timeline).
   - Detect `offset_frames` automatically before writing:
     - Inspect `<proj_dir>/04_Timelines/**/*.otio` (`global_start_time.value` $\rightarrow$ typically `0` / `00:00:00:00`), `*.xml` (`<sequence><timecode><frame>` $\rightarrow$ typically `86400` / `01:00:00:00`), or existing cut `.edl` record-in timecode.
     - Optionally, if DaVinci Resolve is open and the user confirms which timeline is loaded, perform a strictly **read-only** query (`tl.GetStartTimecode()`, `tl.GetStartFrame()`, `tl.GetSetting("timelineFrameRate")`) — **never** call `AddMarker()`, `ImportTimelineFromFile()`, or modify the active timeline.
     - Expose an `--offset-frames` CLI argument (`0` for `00:00:00:00`, `86400` for `01:00:00:00` @ `24fps`) in your generator script so re-basing takes one command.

---

### PHASE 1: SHORTS SEGMENTATION & CUT-BOUNDARY SNAPPING

1. **Design Self-Contained Shorts Beats (`~45s–75s` Target)**:
   - Divide the full monologue/video chronologically into self-contained Shorts (`Short 01`, `Short 02`, ..., `Short NN`) plus a final **`Outro:`** chapter marker at the end-of-essay / CTA beat so the last Short has an unambiguous end boundary.
   - Ensure every Short has:
     - **Strong opening hook** (clean thesis/question/dramatic beat—never start mid-clause).
     - **Complete core argument or narrative payoff**.
     - **Clean closing punchline** right before the next Short's cut boundary.
   - When a natural standalone beat runs `~25s–35s`, keep it as a tight standalone Short rather than merging unrelated paragraphs past `75s` or slicing mid-sentence.

2. **Exact Cut-Boundary Alignment (Zero Mental Timecode Math)**:
   - Key every Short strictly by `(start_clip_idx, end_clip_idx, title)` (or exact verified cut record frame `rec_in` from the cutlist/OTIO/XML JSON) rather than hardcoding `HH:MM:SS:FF` strings by hand.
   - Assert programmatically that `seg[i].end_clip_idx + 1 == seg[i+1].start_clip_idx` (`0` gaps, `0` overlaps across `0..total_edited_frames`).
   - Compute every `HH:MM:SS:FF` timecode mathematically from `(rec_in + offset_frames)` using integer division against `fps` (`24` default).

---

### PHASE 2: DAVINCI RESOLVE TIMELINE MARKERS EDL COMPILATION

Write `<proj_dir>/04_Timelines/Markers/<stem>_chapter_markers.edl` using DaVinci Resolve's exact **Timeline Markers EDL** syntax:

```text
TITLE: <STEM>_SHORTS_CHAPTER_MARKERS
FCM: NON-DROP FRAME

001  001      V     C        00:00:00:00 00:00:00:01 00:00:00:00 00:00:00:01
|C:ResolveColorBlue |M:Short 01: <Title> (46.4s, 00:00:00:00-00:00:46:09) -- Hook: "<hook>" -> Close: "<close>" |D:1

002  001      V     C        00:00:46:09 00:00:46:10 00:00:46:09 00:00:46:10
|C:ResolveColorBlue |M:Short 02: <Title> (71.3s, 00:00:46:09-00:01:57:17) -- Hook: "<hook>" -> Close: "<close>" |D:1
```

Follow these strict formatting rules:
1. **Header**: `TITLE: <STEM>_SHORTS_CHAPTER_MARKERS` and `FCM: NON-DROP FRAME` (even NDF colons `:`, never `;`).
2. **Event Record**: Sequential 3-digit event numbers (`001..N`), `001` reel ID, `V` track, `C` cut, identical source and record in/out timecodes:
   - Point markers (`|D:1`): `[tc_in, tc_in + 1 frame]` for both source and record columns.
   - Range markers *(only if requested)*: `|D:<dur_frames>` with `[tc_in, tc_in + dur_frames]`.
3. **Metadata Line (`|C:` / `|M:` / `|D:`)**:
   - **`|C:`**: Valid Resolve color prefix (default `ResolveColorBlue`; others: `ResolveColorCyan`, `ResolveColorGreen`, `ResolveColorYellow`, `ResolveColorRed`, `ResolveColorPink`, `ResolveColorPurple`, `ResolveColorFuchsia`, `ResolveColorRose`, `ResolveColorLavender`, `ResolveColorSky`, `ResolveColorMint`, `ResolveColorLemon`, `ResolveColorSand`, `ResolveColorCocoa`, `ResolveColorCream`).
   - **`|M:` Payload**: Pack `<Title> (<dur>s, <IN>-<OUT>) -- Hook: "<opening cue>" -> Close: "<closing cue>"` cleanly on **one physical unbroken line**.
   - **Pipe & Newline Sanitization Guard**: **NEVER leave literal newlines (`\n`/`\r`) or literal `|` pipe characters inside the `|M:` payload** (replace any `|` inside text with `/` or `--`), because Resolve's marker EDL parser splits tokens exclusively on `|` (`|C:`, `|M:`, `|D:`).
   - **`|D:`**: Integer frame duration (`1` for point chapter markers).

---

### PHASE 3: OFFLINE VALIDATION GATE & IMPORT INSTRUCTIONS

Before delivering the `.edl`, run an automated Python verification script asserting:
1. **EDL & Parser Syntax**: Valid `TITLE:` + `FCM: NON-DROP FRAME`, sequential `001..N`, valid NDF `HH:MM:SS:FF` (`mm < 60`, `ss < 60`, `ff < fps`), strict monotonic increase, `rec_out == rec_in + 1` matching `|D:1`, and regex match `^\|C:(ResolveColor\w+)\s+\|M:([^|]+)\s+\|D:(\d+)$` (proving zero embedded `|` pipes or line breaks inside `|M:`).
2. **Cut-Boundary & Duration Coverage**: Every marker frame (`frame - offset_frames`) exists verbatim in the timeline's `rec_in` cut boundaries, starts at relative frame `0`, and ends cleanly with the `Outro:` marker covering `100%` of `total_edited_frames`.
3. **Optional Read-Only Resolve State Assertion** *(only if Resolve is open)*: Assert `tl.GetStartTimecode()`, `timelineFrameRate`, and `len(tl.GetMarkers() or {}) == 0` (confirming the active timeline remained `100%` untouched).

Finish by presenting the Short segmentation summary table (`#`, `Timecode`, `Frame`, `Duration`, `Title`) and concise **DaVinci Resolve Import Instructions**:
1. Open DaVinci Resolve and navigate to the **Media Pool**.
2. **Right-click** your target timeline $\rightarrow$ **Timelines $\rightarrow$ Import $\rightarrow$ Timeline Markers from EDL...**
3. Select **`04_Timelines/Markers/<stem>_chapter_markers.edl`** and verify all `Blue` chapter markers appear directly on the exact B-roll / cut boundaries.

#### Optional: Direct Marker Insertion via DaVinci Resolve MCP
When the user explicitly asks to insert the markers directly into their currently open DaVinci Resolve timeline via MCP, parse the validated `.edl` and call `tl.AddMarker(frame_rel, "Blue", name_part, note_part, 1)` (where `frame_rel` is 0-based relative to `tl.GetStartFrame()`), then assert `len(tl.GetMarkers() or {}) >= expected_count`.
