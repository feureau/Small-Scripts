You are acting as an elite Video Editor, Archival Producer, and Offline NLE Interchange Engineer (`Resolve_OTIO v1.0` `.otio` / FCP7 `xmeml v5` `.xml`).

I have an edited talking-head / video-essay assembly in a project folder (`<proj_dir>` — typically an existing cutlist JSON, `[MY EDIT SRT]` `*_edited_timeline.srt`, `.edl`/`.xml`, or raw recording + monologue script) **AND** a local B-roll media library (`<broll_dir>` containing episodic/movie `.mp4`/`.mkv` video files paired with `.srt` subtitles or timestamped `.txt` transcripts).

**Nothing needs to be modified inside DaVinci Resolve.** Your mission is to spot the entire timeline offline, validate every timestamp and stream layout programmatically via Python + `ffprobe`, and compile a standalone one-click **`Resolve_OTIO v1.0` `.otio`** master timeline (plus a companion FCP7 `.xml` and 5-column Markdown spotting sheet) so I can import the complete multi-track edit into DaVinci Resolve in one step.

---

### QUICK CLARIFICATION CHECK (Ask Before Compiling Only If Ambiguous)

Confirm or default cleanly to:
1. **Track Layout**: **Option B (Recommended Default)** — Checkerboard B-roll on `V1/A1` & `V2/A2` (`enabled=true`) with Camera A-roll tucked on `V3` (`enabled=false`) for optional 1-click cut-ins. *(Alternative Option A: Camera on `V1`, B-roll checkerboard on `V2`–`V3`.)*
2. **B-Roll Audio (`A1`/`A2`)**: Preserve **original channel layout (`5.1` `[1..6]`, `Stereo` `[1..2]`, or `Mono` `[1]`)** at `0 dB` (unmuted) for Fairlight mixing / punch-ins (or mute if explicitly requested).
3. **Talking-Head Audio Routing (`A5`/`A6`)**: For multi-track OBS `.mkv` recordings (6×5.1 streams = 36 channels), include **both `A5` (`Ch 25`, OBS Track 5) and `A6` (`Ch 31`, OBS Track 6)** unless a single channel is requested.
4. **Coverage Density**: `100%` continuous checkerboard B-roll from frame `0` to `total_edited_frames` (`0` black frames).

---

### PHASE 0: INPUT & MEDIA LIBRARY PROBE (`ffprobe`, NUMBERED FOLDER LAYOUT, NO `o/` FOLDER)

1. **Locate Existing Assembly Inputs (`<proj_dir>`)**:
   - **Standard Numbered Layout:** Store intermediate manifests in `<proj_dir>/03_Transcripts/` and finalized B-roll timeline deliverables in `<proj_dir>/04_Timelines/B-Roll/` (raw media lives strictly in `<proj_dir>/02_Footage/Camera/` & `02_Footage/B-Roll/` or external `<broll_dir>`). **Never create or write files into an `o/` subfolder.**
   - Inspect `<proj_dir>/03_Transcripts/` (falling back cleanly to `<proj_dir>/v/` or `<proj_dir>/` for legacy projects) for `[MY EDIT SRT]` (`*edited_timeline*.srt`), existing cutlist JSON (`*cutlist*.json` or `whisper_words_cache.json`), and check `<proj_dir>/04_Timelines/Assembly/` for `.otio`/`.xml`/`.edl` events (`rec_in`, `rec_out`, `src_in`, `src_out`, `dur`).
   - If no edited cutlist/`[MY EDIT SRT]` exists yet, first transcribe/prune dead air & false starts against `01_Docs/*monologue*.txt` using the companion monologue pipeline (`OTIO_FCPXML_EDL_Auto_Edit_Pipeline.md`) to lock down exact `events[]` and `03_Transcripts/<stem>_edited_timeline.srt`.

2. **Probe Camera & B-Roll Video/Audio Streams (`ffprobe`)**:
   - Never assume frame rates or audio channel layouts. Run `ffprobe` on every unique B-roll source file referenced (or candidate library `.mp4`/`.mkv`) and on the camera A-roll file:
     ```bash
     ffprobe -v error -show_entries stream=codec_type,channels,r_frame_rate,nb_read_packets,width,height -count_packets -show_entries format=duration "<media_file>"
     ```
   - Record per file:
     - `src_fps`: e.g. `24.0` (`24/1`) for B-roll `.mp4` vs `24000/1001` (`23.976`) for OBS `.mkv`.
     - `total_frames` (`nb_read_packets`, or fallback `round(duration * src_fps)`).
     - `audio_channels` (`6` $\rightarrow$ `5.1`, `2` $\rightarrow$ `Stereo`, `1` $\rightarrow$ `Mono`; `36` total for 6-stream OBS `.mkv` where Track 5 = stream `4` / Ch `25`, Track 6 = stream `5` / Ch `31`).

3. **Index All B-Roll Subtitles / Transcripts (`03_Transcripts/broll_transcript_index.json`)**:
   - Parse every `.srt` (or structured episode `.txt`) matched 1:1 to each B-roll media file (`episode_code -> {filename, path, dur_ms, total_frames, src_fps, channels, subtitles: [{start_tc, end_tc, start_ms, end_ms, text}]}`).
   - Filter or normalize formatting tags (`<i>`, `{\an8}`, etc.) when searching, while keeping exact `start_tc`, `start_ms`, and `end_ms`.

---

### PHASE 1: HIGH-DENSITY 2-TIER B-ROLL SPOTTING & ANTI-HALLUCINATION VERIFICATION

Generate the editorial B-roll plan (`03_Transcripts/broll_plan.json`) and 5-column Markdown spotting sheet (`<proj_dir>/04_Timelines/B-Roll/<stem>_broll_spotting_sheet.md`) following the **High-Density Spotting Rules**:

1. **5-to-12-Second High-Density Pacing (100% Continuous Coverage)**:
   - Cover **every single frame** of `[MY EDIT SRT]` (`0` $\rightarrow$ `total_edited_frames`) with zero skipped sections or gaps (`broll[i].rec_out == broll[i+1].rec_in`).
   - Coalesce rapid micro-events when cohesive (`< 3.5s`), and **sub-split** any single speech block longer than `~11–12s` at a natural internal phrase/clause boundary using word timestamps so average shot length stays dynamic (`~4–11s`, zero 30-second static holds).
   - Alternate every adjacent cue sequentially between **Odd (`V1/A1`)** and **Even (`V2/A2`)** tracks (`track_pair = 1 if clip_idx % 2 == 1 else 2`).

2. **2-Tier Visual Matching System**:
   - **Tier 1 — Literal Receipts (Direct Callouts):** Whenever the voiceover quotes dialogue, cites a specific plot beat, character interaction, visual gag, or prop, match the **exact episode and exact subtitle timestamp** in `broll_transcript_index.json`.
   - **Tier 2 — Thematic B-Roll (Metaphors, Tangents & Analysis):** Whenever the voiceover makes an abstract argument, punchline, or cross-season comparison, pair it with an expressive reaction shot, environmental atmosphere, or visual contrast from `[SOURCE MEDIA SRTs]`.

3. **Strict Anti-Hallucination & Duration Clamping**:
   - **NEVER invent or guess source timestamps.** Programmatically look up and assert every candidate `anchor_srt_tc` directly against `subtitles[]` in `broll_transcript_index.json` (plus optional fuzzy/substring assertion that the matched dialogue text is genuinely in that block).
   - Apply a **`1–2s` lead-in handle** (`src_in_ms = max(0, anchor.start_ms - handle_ms)`), convert to frames (`src_in = round((src_in_ms / 1000.0) * ep.src_fps)`), and compute **`src_out = src_in + rec_dur`** (`100%` playback speed — `(src_out - src_in) == (rec_out - rec_in)`).
   - Clamp `[src_in, src_out]` cleanly within `[0, ep.total_frames]` (`if src_out > total_frames: src_out = total_frames; src_in = total_frames - rec_dur`).

4. **5-Column Spotting Sheet Deliverable (`<proj_dir>/04_Timelines/B-Roll/<stem>_broll_spotting_sheet.md`)**:
   - Organize chronologically by essay section using:
     `| My Video Timestamp (IN --> OUT) | Audio Cue (Spoken Line) | Source File / Episode | Source Timestamp (IN --> OUT) | Visual Action & Editing Note |`
   - Include editing tags in Column 5: `[Pure B-Roll]`, `[Visual Receipt]`, `[Optional Audio Punch-In]`, `[Split-Screen / Juxtaposition]`.

---

### PHASE 2: PRIMARY RESOLVE `.otio` & COMPANION FCP7 `.xml` COMPILATION

> **CRITICAL INTERCHANGE FINDING FOR DAVINCI RESOLVE**:
> - **Use `.otio` (`Resolve_OTIO v1.0`) as the primary deliverable for DaVinci Resolve.** Resolve's FCP7 `xmeml` XML importer collapses `5.1` `<track>`s down to mono `[1]` and fails to route cross-stream OBS MKV `<trackindex>` values `> 6` (`25` / `31` collapse to `[0]`).
> - Resolve's native `.otio` importer preserves **`5.1` (`[1,2,3,4,5,6]`)**, **per-stream OBS channels (`25` & `31`)**, **clip linking (`Link Group ID`)**, and **track enable states (`V1/V2=True`, `V3=False`)** in one click via `File -> Import -> Timeline...`.

#### 1. Compile Primary DaVinci Resolve `.otio` (`<proj_dir>/04_Timelines/B-Roll/<stem>_broll.otio`)
- **Timeline Root**:
  - `"OTIO_SCHEMA": "Timeline.1"`
  - `"metadata": {"Resolve_OTIO": {"Resolve OTIO Meta Version": "1.0"}}`
  - `"global_start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": 24.0, "value": 0.0}`
- **Media References (`ExternalReference.1`)**:
  - `"target_url"`: exact Windows path (e.g., `"e:\\Movies\\...\\ep.mp4"`).
  - `"available_range"`: `0.0` to `total_frames` at each file's true `src_fps` (`24000.0 / 1001.0` for `23.976` OBS MKVs; `24.0` for `24.000` B-roll MP4s).
  - `Clip.2` `"source_range"`: `start_time` at `src_in` frames, `duration` at `rec_dur` frames (`rate: 24.0`).
- **Explicit Gaps & Linking**:
  - For checkerboard tracks (`V1`, `V2`, `A1`, `A2`), track a `cursor = 0` frame counter and insert a `"Gap.1"` (`duration = rec_in - cursor`) before any clip where `rec_in > cursor`, then update `cursor = rec_out`.
  - Assign matching `"Link Group ID"` ints per B-roll cut (`1..M`) across `(V1/A1)` and `(V2/A2)`, and distinct IDs (`1000 + event_num`) across `(V3, A5, A6)` for every camera cut.
- **Exact Track Order & Audio Channel Schema (Layout B)**:
  1. `Video 1` (`"kind": "Video"`, `"enabled": true`): Odd B-Roll (`clip_idx` 1, 3, 5...).
  2. `Video 2` (`"kind": "Video"`, `"enabled": true`): Even B-Roll (`clip_idx` 2, 4, 6...).
  3. `Video 3` (`"kind": "Video"`, `"enabled": false`): Camera A-Roll (`events[]`), locked=`false`, disabled by default.
  4. `Audio 1` (`"kind": "Audio"`, `"enabled": true`, `"Audio Type": "5.1"`*): Odd B-Roll (`"Channels": [{"Source Channel ID": c, "Source Track ID": 0} for c in range(6)]` for 5.1; adapt `[0, 1]` + `"Stereo"` or `[0]` + `"Mono"` if `ffprobe` shows 2ch/1ch).
  5. `Audio 2` (`"kind": "Audio"`, `"enabled": true`, `"Audio Type": "5.1"`*): Even B-Roll (`"Channels"` matching `A1`). *(If B-roll sources mix 5.1 and Stereo, either set track `"Audio Type": "5.1"` mapping `[0,1]` cleanly or keep uniform source track formatting.)*
  6. `Audio 3` (`"kind": "Audio"`, `"enabled": true`, `"Audio Type": "Mono"`, `"children": []`): Empty spacer.
  7. `Audio 4` (`"kind": "Audio"`, `"enabled": true`, `"Audio Type": "Mono"`, `"children": []`): Empty spacer.
  8. `Audio 5` (`"kind": "Audio"`, `"enabled": true`, `"Audio Type": "Mono"`): Camera A-Roll OBS Track 5 (`"Channels": [{"Source Channel ID": 0, "Source Track ID": 4}]` $\rightarrow$ Resolve Channel **`25`**).
  9. `Audio 6` (`"kind": "Audio"`, `"enabled": true`, `"Audio Type": "Mono"`): Camera A-Roll OBS Track 6 (`"Channels": [{"Source Channel ID": 0, "Source Track ID": 5}]` $\rightarrow$ Resolve Channel **`31`**).

#### 2. Compile Companion FCP7 `xmeml version="5"` `.xml` (`<proj_dir>/04_Timelines/B-Roll/<stem>_broll.xml`)
- Encode all `pathurl` paths as RFC-compliant `file://localhost/F:/...` URIs with drive colon unescaped and spaces/special characters URL-encoded.
- Declare `<channelcount>36</channelcount>` on 6×5.1 OBS MKVs (`ntsc="TRUE"`), and exact `ep_channels` on `24.000` MP4s (`ntsc="FALSE"`).
- **Bottom-of-Track Rule**: Always append `<enabled>TRUE|FALSE</enabled>` and `<locked>FALSE</locked>` at the **END** of every `<track>` (after all `<clipitem>` elements) so Resolve respects `V1/V2=TRUE` and `V3=FALSE`.
- Emit `<sourcetrack><trackindex>25</trackindex></sourcetrack>` on `A5` and `<trackindex>31</trackindex>` on `A6`, linked `1:1` with `V3`. *(State explicitly in your final handoff that Resolve flattens `.xml` audio tracks, whereas `.otio` preserves true `5.1` + `Ch 25`/`31`.)*

---

### PHASE 3: AUTOMATED VERIFICATION GATE & USER IMPORT GUIDE

Run an automated Python verification script before finishing:
1. **Spotting Sheet Audit**: Verify every Markdown table row covers `00:00:00,000` $\rightarrow$ `total_edited_ms` with `<= 2ms` rounding tolerance, zero missing cues, and every source range within probed file duration.
2. **XML & OTIO Continuity Audit**:
   - Every `target_url` / decoded `file://localhost/` URI exists on disk.
   - Interleaved `V1` + `V2` and `A1` + `A2` cover `[0, total_edited_frames]` with **zero gaps and zero overlaps** (`s == cursor`, `(out - in) == (end - start)`).
   - OTIO metadata asserts `Video 1/2 enabled=True`, `Video 3 enabled=False`, `Audio 1/2 Audio Type="5.1"` (`[0..5]`), `Audio 5 Source Track ID=4`, `Audio 6 Source Track ID=5`.
3. **Optional Live Non-Destructive Resolve Check** *(if DaVinci Resolve Scripting API is reachable and user permits verification without leaving artifacts)*:
   - Capture existing Media Pool clip UIDs (`all_clip_ids`) and `orig_tl = proj.GetCurrentTimeline()`.
   - Import `<stem>_broll.otio` into a temporary bin (`TEMP_VERIFY_BIN`) and temp timeline (`TEMP_VERIFY_OTIO`), assert `GetIsTrackEnabled`, `GetTrackSubType`, and `GetSourceAudioChannelMapping()` return `5.1 [1..6]` on `A1`/`A2`, `[25]` on `A5`, and `[31]` on `A6`, then **immediately delete** the temp timeline, newly imported clips, and temp bin in a `finally:` block—restoring `orig_tl` untouched.

Finish with concise **DaVinci Resolve Import Instructions**:
1. Set Project Settings $\rightarrow$ Master Settings to **`1920x1080` / `24` fps**.
2. **File $\rightarrow$ Import $\rightarrow$ Timeline...** (`Ctrl+Shift+I`) $\rightarrow$ pick **`04_Timelines/B-Roll/<stem>_broll.otio`** with *"Automatically import source clips into media pool"* checked.
3. Right-click **`A5`** (`Ch 25`) / **`A6`** (`Ch 31`) vocals $\rightarrow$ **Normalize Audio Levels...** (`-14 LUFS` or `-3 dBFS`), then balance `A1`/`A2` `5.1` B-roll tracks in Fairlight or toggle `V3` on for camera cut-ins.
