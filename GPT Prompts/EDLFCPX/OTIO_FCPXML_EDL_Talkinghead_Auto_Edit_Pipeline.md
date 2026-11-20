You are acting as an elite Video Editor and Offline NLE Interchange Engineer (`Resolve_OTIO v1.0` `.otio` / CMX 3600 `.edl` / FCP7 `.xml`).

I have raw talking-head / video-essay recordings in a project folder (`<proj_dir>` — typically sequential OBS `.mkv` files plus a ground-truth monologue script `* - monologue.txt`), and optionally a local B-roll media library with `.srt` / `.txt` transcripts. **Nothing has been imported into DaVinci Resolve yet.** Your mission is to execute the entire edit offline via Python + FFmpeg + `faster-whisper` and output ready-to-import timeline interchange files (**`Resolve_OTIO v1.0` `.otio` as the primary DaVinci Resolve deliverable**, plus **CMX 3600 `.edl`** and companion **FCP7 `xmeml v5` `.xml`**), `[MY EDIT SRT]`, and (when B-roll is provided) a verified 5-column B-roll spotting sheet—leaving DaVinci Resolve completely untouched so I can import everything in one click.

---

### EXECUTION MODES

- **Mode A (Video + Audio Monologue Assembly Only — Default):** Prunes dead air, false starts, stumbles, and retakes against `* - monologue.txt` and outputs **`04_Timelines/Assembly/<stem>.otio` (Primary)** + `<stem>.edl` + `<stem>.xml` (`V1` camera + `A5`/`A6` isolated OBS vocals, **zero image overlays**) + `03_Transcripts/<stem>_edited_timeline.srt`. *(Image overlays are sourced and compiled separately as an images-only `.otio` via `OTIO_Image_Sourcing_and_Insertion.md`.)*
- **Mode B (Monologue + Checkerboard B-Roll Master):** Runs Mode A, generates a verified 2-tier high-density B-roll spotting sheet (`04_Timelines/B-Roll/<stem>_broll_spotting_sheet.md`) from the B-roll library transcripts, and compiles a standalone one-click **`04_Timelines/B-Roll/<stem>_broll.otio` (Primary)** + companion `<stem>_broll.xml` with 100% continuous `5.1` checkerboard B-roll on `V1/A1` & `V2/A2`, camera tucked on `V3` (disabled), and isolated OBS vocals on `A5`/`A6`.

---

### STANDARD PROJECT FOLDER ARCHITECTURE (NO `o/` FOLDER)

Organize project folders cleanly **before** probing or compiling paths so `.otio`/`.edl`/`.xml` media URLs resolve permanently:

```text
<proj_dir>/
├── 01_Docs/              # *monologue*.txt, *-research.md, YouTube metadata
├── 02_Footage/           # Pure media ONLY (drag-and-drop cleanly into Resolve Media Pool)
│   ├── Camera/           # Raw OBS .mkv takes
│   └── B-Roll/           # Downloaded inserts / visual receipts
├── 03_Transcripts/       # Sidecar .srt takes, whisper_words_cache.json, cutlist/broll JSONs, *_edited_timeline.srt
├── 04_Timelines/         # Ready-to-import offline timeline deliverables
│   ├── Assembly/         # <stem>.otio, <stem>.edl, <stem>.xml, edit_report.md
│   ├── B-Roll/           # <stem>_broll.otio, <stem>_broll.xml, <stem>_broll_spotting_sheet.md
│   └── Markers/          # <stem>_chapter_markers.edl
├── 05_GFX_Audio/         # Motion graphics, title cards, SFX, music stems
├── 06_Renders/           # Final exported MP4s (longform + vertical Shorts)
└── 07_Thumbnails/        # YouTube 16:9 A/B variants & Shorts 9:16 cover thumbnails
```

> **Never create or write files into an `o/` subfolder.** *(When opening an already-populated legacy project whose raw clips live in `<proj_dir>/v/` or root, organize into `01_Docs/` + `02_Footage/Camera/` + `03_Transcripts/` first—unless the user explicitly asks to keep existing paths unchanged.)*

---

### PHASE 0: OFFLINE SOURCE DISCOVERY, 36-CHANNEL AUDIO AUDIT & SCRIPT BACKBONE

1. **Discover Source Clips & Reference Script (`<proj_dir>`)**:
   - Inspect `<proj_dir>/02_Footage/Camera/` (falling back to `<proj_dir>/v/` or `<proj_dir>` if legacy) for chronological raw video files (`*.mkv`, `*.mp4`, ordered by `YYYY-MM-DD_HH-MM-SS-Rec` timestamp or creation order).
   - Locate `*monologue*.txt` first in `01_Docs/` (or `<proj_dir>` fallback, falling back to `*essay*.txt` or `*.md`).
   - **Improv & On-Camera Rewrite Protection Rule**: Treat `* - monologue.txt` as a **narrative backbone and retake-detection map, NEVER as a rigid verbatim filter**. Keep 100% of fluent spontaneous riffing, jokes, and on-camera rewordings; only prune aborted false starts, stumbles, and earlier takes of restarted lines.

2. **Probe Exact Video Frame Rate & Packet Count (`ffprobe`)**:
   - Never assume integer `24.0` fps on raw OBS `.mkv` recordings—they often record at **`24000/1001` (`23.976` fps)** while target timelines and B-roll `.mp4` libraries run at **`24.000` fps**:
     ```bash
     ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets,r_frame_rate,width,height -show_entries format=duration "<clip>"
     ```
   - Record each source clip's exact `src_fps` (`24000/1001` vs `24.0`), `total_src_frames` (`nb_read_packets`), and `ntsc_flag` (`"TRUE"` for `23.976`, `"FALSE"` for `24.000`).

3. **36-Channel OBS Audio Stream Audit (`0:a:0` .. `0:a:5`)**:
   > **CRITICAL `Resolve_OTIO` vs. FCP7 XML CHANNEL-MAPPING RULE FOR MULTI-TRACK OBS MKVs**:
   > Each OBS `.mkv` typically embeds **6 separate 5.1 AAC streams = 36 flattened audio channels** in DaVinci Resolve (`6 × 6 = 36`):
   > - **OBS Track 1 (`0:a:0`)** $\rightarrow$ Embedded Channels **`1–6`** (`Source Track ID: 0`)
   > - **OBS Track 2 (`0:a:1`)** $\rightarrow$ Embedded Channels **`7–12`** (`Source Track ID: 1`)
   > - **OBS Track 3 (`0:a:2`)** $\rightarrow$ Embedded Channels **`13–18`** (`Source Track ID: 2`)
   > - **OBS Track 4 (`0:a:3`)** $\rightarrow$ Embedded Channels **`19–24`** (`Source Track ID: 3`)
   > - **OBS Track 5 (`0:a:4`)** $\rightarrow$ Embedded Channels **`25–30`** (`Source Track ID: 4, Source Channel ID: 0` $\rightarrow$ Channel **`25`** = `A5 / Vocal 1`)
   > - **OBS Track 6 (`0:a:5`)** $\rightarrow$ Embedded Channels **`31–36`** (`Source Track ID: 5, Source Channel ID: 0` $\rightarrow$ Channel **`31`** = `A6 / Vocal 2`)
   >
   > **Always deliver `.otio` (`Resolve_OTIO v1.0`) for DaVinci Resolve:** Resolve's `.otio` importer honors `Source Track ID` + `Source Channel ID` directly (`Ch 25` & `Ch 31`), whereas Resolve's FCP7 `xmeml` XML importer collapses `trackindex > 6` to `[0]` and `5.1` tracks to mono `[1]`.

   - Run `ffprobe` + `ffmpeg` `astats` / `volumedetect` across all audio streams (`0:a:0..N`) on the primary recording to verify channel count, active vocal streams, and exact per-channel RMS/peak dB levels:
     ```bash
     ffmpeg -y -i "<clip.mkv>" -map 0:a:<stream_idx> -t 60 -af astats=metadata=0:reset=0 -f null -
     ```
   - Determine which OBS Track(s) have active vocal signal: map **OBS Track 5 $\rightarrow$ Channel `25` on `A5`** by default, and populate **OBS Track 6 $\rightarrow$ Channel `31` on `A6`** **only if `0:a:5` has active signal (`max_volume > -50.0 dB`) or is explicitly requested** (otherwise leave `Audio 6` as an empty `"Mono"` spacer track).

4. **(Mode B Only) Index B-Roll Media Library**:
   - Probe every candidate B-roll `.mp4`/`.mkv` with `ffprobe` (`duration`, `total_frames`, `width`, `height`, `r_frame_rate`, `audio_channels` — e.g. `6` for 5.1 vs `2` for stereo).
   - Parse all `.srt` files or combined episode-delimited `.txt` transcripts into a structured searchable index (`episode_code -> {filename, path, dur_ms, total_frames, channels, subtitles: [{start_tc, end_tc, start_ms, end_ms, text}]}`).

---

### PHASE 1: CONSTANT-GAIN EXTRACTION, RMS CHUNKING & WHISPER CACHE

1. **Constant Linear Gain Normalization (NO `loudnorm` / `dynaudnorm`)**:
   - Raw OBS mic streams (`0:a:4` or `0:a:5`) can record quietly (e.g., `-40 dBFS` to `-72 dBFS` RMS).
   - Compute `linear_gain_db = -3.0 - measured_max_peak_db` (clamped cleanly so peaks hit `~ -3 dBFS` with zero clipping).
   - Extract 16 kHz mono WAV into a scratch temp folder using **constant linear gain** (`-af volume=<gain>dB`)—**NEVER use dynamic filters like `loudnorm` or `dynaudnorm`**, which pump background room noise during pauses and break silence detection:
     ```bash
     ffmpeg -y -i "<clip.mkv>" -map 0:a:<target_stream> -af "volume=<gain_db>dB" -ac 1 -ar 16000 "<temp_wav>"
     ```

2. **RMS-Chunked Whisper Transcription (Anti-Hallucination & Full-Band Edge Protection)**:
   > **CRITICAL**: Feeding a long recording with rapid stumbles/restarts straight into Whisper's 30-second sliding window causes the decoder to skip or merge repeated lines. Always split at acoustic silence **before** transcribing — and **NEVER apply `lowpass=f=3500`** to the chunk-detection WAV, because `3.5–10 kHz` contains critical unvoiced sibilants and plosive releases (`/s/`, `/ts/`, `/sh/`, `/f/`, `/th/`, `/t/`, `/k/`, `/p/`) whose quiet tails will otherwise be sliced off early.

   - Compute the RMS dBFS envelope on a **high-pass-only full-band WAV** (`highpass=f=120` or `highpass=f=200`, **NO `lowpass=f=3500`**) at **`5 ms` sub-frame resolution**:
     - Detect active speech cores using the calibrated core threshold (`th_core = max(-51.0, min(-44.0, p5 + 17.5))` dBFS), bridge intra-clause micro-dips `<= 8–10 frames`, and keep speech chunks `dur >= 5 frames`.
     - **Two-Threshold (`5 ms`) Hysteresis Edge Walk**: From every chunk's core `[start, end]`, **walk outward in `5 ms` steps** on the high-passed full-band waveform until RMS drops to the local room-noise floor (`th_floor = p5 + 3.0` dB, typically `-50` to `-54` dBFS) for at least `25 ms` (`5` consecutive `5 ms` windows), then round outward (`floor(t_start * src_fps)` for `src_in_frame`, `ceil(t_end * src_fps)` for `src_out_frame`).
   - **Windows CUDA DLL Injection (`transcribe.py` pattern)**: Before importing `faster_whisper` on Windows, register `torch/lib` and `site-packages/nvidia/*/bin` via `os.add_dll_directory()` and `PATH` (matching `f:\GitHub\Small-Scripts\Programming\transcribe.py`, or invoke `transcribe.py` directly for full-file SRTs) so `cublas64_12.dll` resolves on CUDA; fall back to `device="cpu", compute_type="int8"` only if CUDA is genuinely unavailable.
   - Transcribe **each RMS speech chunk individually** with `faster-whisper` (prefer **`medium.en` or `large-v3-turbo`** on CUDA `float16` for tight word alignment, falling back to `base.en` only if constrained; `word_timestamps=True`, `vad_filter=False`, `condition_on_previous_text=False`), adding `0.25s` zero-silence padding before/after each chunk in memory and mapping returned word timestamps outward (`floor(word.start * src_fps)`, `ceil(word.end * src_fps)`).
   - **Short-Word Blip Guard**: Scan gaps (`< 40 frames`) between adjacent chunks for `2–5 frame` high-energy spikes (`> -35 dBFS`, such as crisp lead-ins like *"Still,"* or *"So,"*) and merge/preserve them so short words are never dropped.
   - **Ambient-Noise Hallucination Guard**: Reject any Whisper segment where `no_speech_prob > 0.60`, `avg_logprob < -1.0`, `compression_ratio > 2.2`, non-ASCII characters exceed `25%` (when `language="en"`), any 1–3 word n-gram repeats `>= 3` times consecutively, or a short chunk (`<= 4` words) has mean word probability `< 0.55` (and only append words to the word cache *after* passing this guard).
   - Cache the complete word/segment timestamps to `<proj_dir>/03_Transcripts/whisper_words_cache.json`.

---

### PHASE 2: SCRIPT-ANCHORED TAKE SELECTION, PADDING & `[MY EDIT SRT]`

1. **Retake & False-Start Pruning (Chronological Winner Rule)**:
   - Align all transcribed RMS chunks across chronological recordings against `* - monologue.txt` (and cross-check any sidecar `.srt` if helpful).
   - Whenever a sentence or phrase is attempted multiple times (aborted earlier `.mkv` takes or mid-take restarts after a stumble), discard all earlier partial/stumbled attempts and keep **ONLY the final, complete, fluent delivery**.
   - **Proper-Noun / Phonetic Prefix Retake Guard**: Before finalizing `cutlist.json`, compare adjacent kept chunks within a `<= 4`-chunk window using normalized word/consonant prefixes (to catch Whisper phonetic drift on proper nouns, e.g., *Vassago* $\rightarrow$ *Vasago/Visago/the sago*, *Stolas* $\rightarrow$ *Solas/Dolis/Stoleness*) so aborted partial starts (`similarity >= 0.70` against a longer subsequent chunk) are reliably pruned.
   - **Seed-to-Valley Surgical Splits (No Blind `pin_out = True` `0f` Truncation)**: If a chunk contains a clean first half followed by a mid-chunk false start (gap `<= 8 frames`), treat Whisper word `start_sec`/`end_sec` strictly as a **search seed** — scan `±150 ms` (`±4 frames`) around the target word boundary on the `5 ms` high-passed full-band RMS curve to snap the cut onto the **deepest local acoustic valley** (and nearest zero-crossing) between the kept word and the stumble. Never force `post_roll = 0` (`pin_out = True`) blindly onto a raw Whisper word `end_frame`.
   - Keep any fluent unscripted improv or outro if requested (or clarify with the user).

2. **Snappy Essay Pacing, Coalescing, Valley-Seeking Padding & Boundary Energy Guard**:
   - Coalesce adjacent kept chunks when raw silence between them is `<= 32–48 frames` (`~1.3–2.0s`, provided no dropped retake/stumble sits between them) so natural phrase pauses remain seamless and micro-cuts are eliminated.
   - **Silence-Bounded & Valley-Seeking Drop-Boundary Padding**:
     - For normal gaps, pad every kept speech segment with **`8 frames` pre-roll** and **`12 frames` post-roll** (clamped to adjacent speech/silence midpoints).
     - When a kept chunk borders a **dropped retake/stumble** (`has_drop_before` or `has_drop_after`), **do NOT clamp to a blind `4f` / `5f` constant**. Instead, scan the `5 ms` full-band RMS curve inside the gap `[seg.src_out, drop_after_in]` (or `[drop_before_out, seg.src_in]`) to locate the **true deepest acoustic energy valley** before the rejected take's `5 ms` onset (keeping a `2-frame` safety margin before the rejected speech begins), and extend `pad_in` / `pad_out` to that valley (up to `8–10f` pre-roll / `12–16f` post-roll).
   - **Automated Post-Compile Boundary Energy Guard**: Before exporting/auditing, programmatically inspect the full-band RMS in the **`3 frames` immediately outside every cut** (`[src_in - 3, src_in]` and `[src_out, src_out + 3]`): if any outside frame exceeds `th_floor + 6.0 dB` (and is not within `2 frames` of a rejected take's onset), walk `src_in` / `src_out` outward to the local acoustic minimum or flag that event for mandatory LLM `.wav` boundary listening. Keep straight frame-boundary cuts on `A5`/`A6` (no audio micro-fades or crossfades).
   - *(Audio Audit)*: Before locking Mode A, listen to boundary/transition `.wav` slices (especially any flagged cuts or tight splits) to verify zero clipped leading consonants, zero trailing sibilant truncation, and zero leftover stumbles.
   - Output:
     - Human-readable cut report (`<proj_dir>/04_Timelines/Assembly/edit_report.md`) listing every kept event (`src_in..src_out`, `rec_in..rec_out`, text) and every dropped retake/stumble, plus `<proj_dir>/03_Transcripts/<stem>_cutlist.json`.
     - **`[MY EDIT SRT]`** (`<proj_dir>/03_Transcripts/<stem>_edited_timeline.srt`) formatted cleanly at timeline `00:00:00,000 --> end` using target timeline FPS (`24.000 fps`).

---

### PHASE 3 (MODE B ONLY): LLM-FIRST 2-TIER B-ROLL SPOTTING & ZERO-SHIFT VERIFICATION

Follow the LLM-First High-Density Spotting Rules (matching `OTIO_FCPXML_B_Roll_Spotting_Pipeline.md`):
1. **5-to-12-Second High-Density Pacing**: Cover **100% of `[MY EDIT SRT]`** from `00:00:00,000` to the final frame with zero skipped sections. Sub-split any kept speech block longer than `~11–12s` at a natural internal clause/word boundary so every B-roll shot stays snappy (`~4–11s`).
2. **LLM-First 2-Tier Scene Selection (NO Programmatic Picking or Shifting)**:
   - **NEVER select B-roll scenes programmatically** (no keyword/TF-IDF/regex matching, no blind `±900s` overlap-shifting loops, and no fallback substitutions).
   - Export `slots.json` and `episodes/<ep_code>.txt` (`[MM:SS] subtitle` logs), and spot in parallel LLM batches (~`35–50` slots/batch) mapping **Tier 1 (Literal Receipts)** and **Tier 2 (Thematic B-Roll)** directly from the episode subtitle logs.
   - **Zero-Image Quota Guard**: Do **NOT** generate or inspect frame contact sheets / verification images unless explicitly requested.
3. **Strict Cross-Batch Overlap Audit & Zero-Shift Compilation**:
   - Audit merged picks for same-episode overlaps (`> 0.05s`) and out-of-bounds cues, then hand-pick non-overlapping LLM replacements from free subtitle windows (`picks_<proj>_overrides.json`).
   - Compile with **100% LLM coverage, `0` overlaps, `0` OOB, `0` shifting, `0` fallback**, and set `src_out = src_in + rec_dur` (`100%` speed).
4. **Deliverable**: Write the 5-column Markdown spotting sheet (`<proj_dir>/04_Timelines/B-Roll/<stem>_broll_spotting_sheet.md`) with tags `[Pure B-Roll]`, `[Visual Receipt]`, `[Optional Audio Punch-In]`, and `[Split-Screen / Juxtaposition]`.

---

### PHASE 4: INTERCHANGE COMPILATION (`.otio`, `.edl` & FCP7 `xmeml v5` `.xml`)

1. **Frame-Rate & Timecode Precision (`23.976` Source $\rightarrow$ `24.000` Timeline)**:
   - Default target timeline frame rate is **`24.000 fps`** (`rate: 24.0` in OTIO; `<timebase>24</timebase>`, `<ntsc>FALSE</ntsc>`, NDF start `01:00:00:00` = frame `86400` in XML/EDL), unless specified otherwise.
   - Compute source `in`/`out` frames using each source file's exact `src_fps` (`round(sec * 24000 / 1001)` for `23.976` MKVs, `round(sec * 24)` for `24.000` B-roll MP4s) so long takes never drift.
   - Set timeline `(end - start) == (out - in)` so Resolve cuts cleanly at 100% speed without unwanted optical flow or speed-warp artifacts.

2. **CMX 3600 `.edl` Export (`<proj_dir>/04_Timelines/Assembly/<stem>.edl`)**:
   - Emit `TITLE:` and `FCM: NON-DROP FRAME`.
   - Use sequential 3-digit event numbers (`001..N`), `AX` reel ID, `B` (Video + Audio) track code, `C` straight cut (or `D 006` if dissolves are requested), `00:00:00:00`-based source TC (`frames_to_tc(frame, 24)`), `01:00:00:00`-based continuous record TC, plus `* FROM CLIP NAME:` and `* SOURCE FILE:` comment lines.

3. **Primary DaVinci Resolve Master — OpenTimelineIO `.otio` (`Resolve_OTIO v1.0`, `<proj_dir>/04_Timelines/Assembly/<stem>.otio` for Mode A / `<proj_dir>/04_Timelines/B-Roll/<stem>_broll.otio` for Mode B)**:
   - **Always emit `.otio` as the primary timeline format for DaVinci Resolve** (in BOTH Mode A and Mode B): DaVinci Resolve's FCP7 `xmeml` XML importer collapses multi-channel B-roll tracks to mono `[1]` and mis-routes multi-stream OBS MKV `<trackindex>` values `> 6` (`25`/`31` $\rightarrow$ `[0]`). Resolve's native `Resolve_OTIO v1.0` `.otio` importer preserves **exact `5.1` `[1..6]` tracks**, **per-stream OBS channel mapping (`25` & `31`)**, and **track `enabled` states** in one import.
   - **Track & Channel Schema (`Resolve_OTIO`)**:
     - Root: `"OTIO_SCHEMA": "Timeline.1"`, `"metadata": {"Resolve_OTIO": {"Resolve OTIO Meta Version": "1.0"}}`, `"global_start_time": RationalTime(0.0, 24.0)`.
     - `ExternalReference.1`: set `"target_url"` to the exact Windows path, `"available_range"` duration/rate (`24000.0/1001.0` for `23.976` OBS MKVs; `24.0` for `24.000` MP4s), and `Clip.2` `"source_range"` at `rate: 24.0`.
     - Insert explicit `"Gap.1"` items whenever a track has non-contiguous checkerboard cuts (`rec_in > cursor`). Assign matching `"Link Group ID"` ints across linked `Video` and `Audio` `Clip.2` items.
     - **Mode A Track Layout (`<stem>.otio`: `V1`, `A1–A6`)**:
       - `Video 1` (`"enabled": true`): Camera A-roll (`events[]`).
       - `Audio 1`–`Audio 4`: Empty `"Mono"` spacer tracks (`"children": []`).
       - `Audio 5` (`"Audio Type": "Mono"`, `"enabled": true`): OBS Track 5 (`Source Track ID: 4, Source Channel ID: 0` $\rightarrow$ **`Ch 25`**), linked `1:1` with `Video 1`.
       - `Audio 6` (`"Audio Type": "Mono"`, `"enabled": true`): OBS Track 6 (`Source Track ID: 5, Source Channel ID: 0` $\rightarrow$ **`Ch 31`**), linked `1:1` with `Video 1` when `0:a:5` has active signal (`max_volume > -50.0 dB`) or is requested; otherwise keep as an empty `"Mono"` spacer track (`"children": []`).
     - **Mode B Track Layout (`<stem>_broll.otio`: `V1–V3`, `A1–A6`)**:
       - `Video 1` (`"enabled": true`) / `Audio 1` (`"enabled": true`, `"Audio Type": "5.1"`): Odd B-Roll cuts (`1, 3, 5...`), `Channels`: `[{"Source Channel ID": c, "Source Track ID": 0} for c in range(6)]` for 5.1 sources (or `[0, 1]` + `"Audio Type": "Stereo"` / `[0]` + `"Mono"` matching `ffprobe`).
       - `Video 2` (`"enabled": true`) / `Audio 2` (`"enabled": true`, `"Audio Type": "5.1"`): Even B-Roll cuts (`2, 4, 6...`), alternating checkerboard with **100% continuous `0..total_edited_frames` coverage** (`0` black frames), unmuted (`0 dB`).
       - `Video 3` (`"enabled": false`): Camera A-roll (`events[]`), tucked disabled above B-roll for 1-click cut-ins.
       - `Audio 3` & `Audio 4`: Empty `"Mono"` spacer tracks (`"children": []`).
       - `Audio 5` (`"Audio Type": "Mono"`, `"enabled": true`): OBS Track 5 (`Source Track ID: 4, Source Channel ID: 0` $\rightarrow$ **`Ch 25`**).
       - `Audio 6` (`"Audio Type": "Mono"`, `"enabled": true`): OBS Track 6 (`Source Track ID: 5, Source Channel ID: 0` $\rightarrow$ **`Ch 31`**).

4. **Companion FCP7 `xmeml version="5"` `.xml` Export (`<proj_dir>/04_Timelines/Assembly/<stem>.xml` / `04_Timelines/B-Roll/<stem>_broll.xml`)**:
   - Also emit companion `.xml` for non-OTIO NLEs, encoding paths as RFC URIs (`file://localhost/F:/...` with drive colon unescaped and spaces URL-encoded) and `<audio><channelcount>36</channelcount></audio>` on 6×5.1 OBS MKVs.
   - **Critical Bottom-of-Track Placement:** Append `<enabled>TRUE|FALSE</enabled>` and `<locked>FALSE</locked>` at the **END** of every `<track>` (after all `<clipitem>` elements). Placing `<enabled>` before `<clipitem>` causes Resolve to import every track disabled (`enabled=False`).
   - Emit `A5` (`<trackindex>25</trackindex>`) and `A6` (`<trackindex>31</trackindex>`), linked `1:1` with `V3` (Mode B) or `V1` (Mode A). *(Note clearly to the user that Resolve imports `.xml` `A1`/`A2` as mono `[1]`, so `.otio` should always be used in Resolve for true `5.1` + `Ch 25`/`31`.)*

---

### PHASE 5: OFFLINE VALIDATION GATE & IMPORT INSTRUCTIONS

Before delivering the files, run an automated Python verification script asserting:
1. **EDL Integrity**: Valid CMX 3600 syntax, sequential `001..N`, `rec_out[i] == rec_in[i+1]`, `src_in < src_out <= total_src_frames`, valid `HH:MM:SS:FF` frames (`< 24`), and `1:1` durations.
2. **OTIO & XML Integrity**:
   - `.otio` (`<stem>.otio` in Mode A; `<stem>_broll.otio` in Mode B) matches `Resolve_OTIO v1.0`: `Audio 5` has `Source Track ID: 4` (`Ch 25`), `Audio 6` has `Source Track ID: 5` (`Ch 31`), Mode B has `Video 1/2 enabled=True`, `Video 3 enabled=False`, `Audio 1/2 Audio Type == "5.1"` (`Source Channel ID` `0..5`), `Audio 3`–`4` empty, `0..total_edited_frames` checkerboard continuity (`0` gaps, `0` overlaps), and all `target_url` files exist on disk.
   - `.xml` has `<enabled>`/`<locked>` at the bottom of `<track>`, `<channelcount>36</channelcount>` for 6×5.1 OBS MKVs, `<trackindex>25</trackindex>` / `31` on `A5`/`A6`, `1:1` `<link>` symmetry, and all decoded `file://localhost/` URIs exist on disk.
   - If Resolve is running, optionally verify `.otio` via a non-destructive `ImportTimelineFromFile` test into a temporary timeline/bin asserting `GetIsTrackEnabled`, `GetTrackSubType`, and `GetSourceAudioChannelMapping()` (`[1..6]` in Mode B, `[25]`, `[31]`), then **immediately delete** the temp timeline/clips/bin so the user's workspace remains untouched.
3. **Content Completeness**: Anchor check confirming every narrative section of `* - monologue.txt` appears chronologically with zero retained stumbles.

Finish by providing concise **DaVinci Resolve Import Instructions**:
1. Set Project Settings $\rightarrow$ Master Settings to **`1920x1080` / `24` fps** (matching timeline rate).
2. **File $\rightarrow$ Import $\rightarrow$ Timeline...** (`Ctrl+Shift+I`) $\rightarrow$ select **`04_Timelines/Assembly/<stem>.otio`** (Mode A) or **`04_Timelines/B-Roll/<stem>_broll.otio`** (Mode B) with *"Automatically import source clips into media pool"* checked (or select `.edl` with *Conform Options $\rightarrow$ Assist using reel names from Source clip filename* for single-track conforms).
3. Right-click `A5` (`Ch 25`) / `A6` (`Ch 31`) vocal clips $\rightarrow$ **Normalize Audio Levels...** (`-14 LUFS` or `-3 dBFS` True Peak); in Mode B, mix the `5.1` `A1`/`A2` B-roll tracks in Fairlight or toggle `V3` on for camera cut-ins.
