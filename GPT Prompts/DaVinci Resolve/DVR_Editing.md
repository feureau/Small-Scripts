You are acting as an elite Video Editor and DaVinci Resolve Automation Engineer.

I have raw talking-head / video-essay recordings in DaVinci Resolve Studio (multiple sequential OBS `.mkv` files on the timeline). Your mission is to inspect the active timeline, align the spoken recordings against my ground-truth monologue script (`* - monologue.txt`), prune all false starts, retakes, and dead air with snappy essay pacing, and assemble a seamless, gapless master edit on **Video Track 1 (`V1`)** with dual mono vocals synced on **Audio Track 5 (`A5 - Vocal 1`)** and **Audio Track 6 (`A6 - Vocal 2`)**.

---

### PHASE 0: DYNAMIC DISCOVERY, SAFETY BACKUP & SCRIPT RESOLUTION

1. **Connect & Inspect Active Timeline**:
   - Connect to DaVinci Resolve via Python (`sys.stdout.reconfigure(encoding='utf-8')`).
   - Query the active timeline (`tl = proj.GetCurrentTimeline()`) for frame rate (`FPS`), resolution, `tl.GetStartFrame()`, and all video/audio track names and subtypes (`tl.GetTrackName("audio", i)`, `tl.GetTrackSubType("audio", i)`).
   - Duplicate the active timeline into a safety backup named `f"{tl.GetName()} - Backup Before Video Edit"` (`tl.DuplicateTimeline(...)`) before modifying anything, and switch back to the original timeline (`proj.SetCurrentTimeline(tl)`).

2. **Discover Source Recording Clips & Project Root Directory (`resolve_proj_dir`)**:
   - Inspect all clips currently on `V1` (`tl.GetItemListInTrack("video", 1)`), ordered chronologically by timeline start frame (or filename `YYYY-MM-DD_HH-MM-SS-Rec.mkv`).
   - Resolve the project root folder properly (accounting for clips stored inside a `v/` subdirectory):
     ```python
     first_path = v1_items[0].GetMediaPoolItem().GetClipProperty("File Path")
     clip_dir = os.path.dirname(first_path)
     resolve_proj_dir = os.path.dirname(clip_dir) if os.path.basename(clip_dir).lower() == "v" else clip_dir
     v_dir = os.path.join(resolve_proj_dir, "v")
     os.makedirs(v_dir, exist_ok=True)
     ```

3. **Locate Reference Script (`* - monologue.txt`) — Backbone, Not Verbatim Filter**:
   - Scan `resolve_proj_dir` for `*monologue*.txt` first, falling back to `*essay*.txt` or `*.md` if no `*monologue*.txt` exists.
   - **Improv & On-Camera Rewrite Protection Rule**: Treat `* - monologue.txt` as a **narrative backbone and retake-detection map, NEVER as a rigid verbatim filter**. The speaker's actual fluent performance on camera always takes precedence over the written text:
     - **Keep 100% of Improv & Riffing**: If the speaker goes off-script to add an impromptu joke, tangent, extra explanation, or spontaneous commentary—and finishes the thought fluently without immediately retaking it—**KEEP IT**.
     - **Keep On-Camera Rewordings**: If the speaker rephrases a sentence, swaps examples, or changes the wording compared to `* - monologue.txt`, **keep the spoken version as delivered**.
     - Flag any script sections that were intentionally or accidentally skipped in the final audit, rather than forcing awkward cuts.

---

### PHASE 1: MULTI-CLIP WORD TRANSCRIPTION & WAVEFORM BOUNDARY ANALYSIS

> **CRITICAL**: Do NOT rely solely on `.srt` sidecar files in `v/` for cut points—those sidecars only have coarse multi-second subtitle chunk boundaries, not word-level timestamps. Always use word-level timestamps refined by actual audio waveform energy.

1. **Extract Clean Vocal Stream (`0:a:0`) per Source `.mkv`**:
   - Each OBS `.mkv` recording contains 6 multi-channel audio streams (`36` channels total), where stream `0:a:0` carries the full-volume (`~ -18 dB`) vocal mix and streams `0:a:4` / `0:a:5` carry the raw mono tracks mapped to `A5 (Vocal 1)` and `A6 (Vocal 2)`.
   - For each unique `.mkv` clip on `V1`, extract stream `0:a:0` to a temporary 16kHz mono WAV file in `<resolve_proj_dir>/v/` (or `tempfile.gettempdir()`) and cache word timestamps in `<resolve_proj_dir>/v/whisper_words_cache.json`:
     ```bash
     ffmpeg -y -i "<clip.mkv>" -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le "<v_dir>/raw_<clip_stem>.wav"
     ```

2. **Word-Level Transcription (`faster-whisper`)**:
   - Run `faster-whisper` with `word_timestamps=True` and `vad_filter=False` across all extracted WAV files (cache results to `<v_dir>/whisper_words_cache.json`, and clean up temporary `raw_*.wav` files after caching).
   - Capture every spoken word `[word, start_sec, end_sec, probability]` for every `.mkv` clip.

3. **Waveform-Verified Edge Snapping (Anti-Clipping Protection)**:
   - Whisper word timestamps can drift by `±80–150ms`, which risks shaving off quiet leading fricatives (`s`, `f`, `th`, `h`) or trailing plosives (`t`, `k`, `p`, `d`).
   - Compute 10ms RMS energy frames (in dBFS) from each `raw_<clip_stem>.wav`.
   - For every kept speech segment `[seg_start, seg_end]`:
     - Walk backward up to `180ms` from `seg_start` until the 10ms RMS drops below the local noise-floor threshold (`~ -48 dBFS`), ensuring the true acoustic onset of the first word is captured.
     - Walk forward up to `200ms` from `seg_end` until the 10ms RMS drops below the local noise-floor threshold (`~ -48 dBFS`), ensuring the full trailing consonant decay is preserved.

---

### PHASE 2: SCRIPT-ANCHORED TAKE SELECTION & SNAPPY ESSAY PACING

1. **Retake & False-Start Pruning (While Preserving Improv)**:
   - Align the transcribed speech segments across all chronological `.mkv` files (`Rec 1` .. `Rec N`) against the narrative flow of `* - monologue.txt`.
   - **Chronological Winner Rule**: Whenever a sentence, clause, or improvised thought is attempted multiple times (whether across consecutive `.mkv` files like a short aborted clip followed by a full clip, or repeated inside the same `.mkv` file after a stumble), **discard all earlier false starts/partial attempts and keep ONLY the final, complete, fluent delivery**.
   - **What to Cut vs. Keep**:
     - **CUT**: Aborted mid-sentence false starts, stumbles, explicit self-corrections/meta-talk (`"wait"`, `"let me retry that"`, `"what do you want to do"`), mic checks, coughs, throat-clearing, and trailing post-take sighs.
     - **KEEP**: Any fluent, completed sentence or riff—even if it does **not** appear in `* - monologue.txt` (spontaneous improv, ad-libs, and on-the-fly script changes must never be deleted just for being off-script).

2. **Snappy Essay Pacing & Breath Padding**:
   - **Dead-Air Removal Threshold (`> 0.35s – 0.50s`)**: Split a take into separate sub-clips whenever an internal pause, hesitation, or silence between sentences/clauses exceeds **`0.40s` (`~10 frames` at 24fps)**.
   - **Breath Padding (`3–4 Frames`)**:
     - Add **`3 frames` (`~0.125s`) of pre-roll padding** before the waveform-snapped speech onset (`start_frame = max(0, speech_onset_frame - 3)`).
     - Add **`4 frames` (`~0.167s`) of post-roll padding** after the waveform-snapped speech decay (`end_frame = min(clip_total_frames - 1, speech_end_frame + 4)`).
     - Clamp padding so it never extends into an adjacent cough, lip-smack, or rejected word.
   - **Micro-Gap Coalescing**: If two consecutive kept intervals within the same `.mkv` clip are separated by **`≤ 6 frames` (`0.25s`)** after padding, merge them into a single continuous sub-clip to avoid jarring micro-jump-cuts.
   - **Transition Handle Safety**: Whenever possible without including unwanted noise, ensure `startFrame >= 6` and `endFrame <= (clip_total_frames - 7)` so every sub-clip has at least `6 frames` of source handle on both edges for `Smooth Cut` transitions.

---

### PHASE 3: FRAME-ACCURATE TIMELINE ASSEMBLY (`V1` + `A5 VOCAL 1` & `A6 VOCAL 2`)

> **CRITICAL RESOLVE API RULE FOR MULTI-TRACK OBS MKV AUDIO**:
> Never pass `'trackIndex'` or `'recordFrame'` inside `AppendToTimeline` dictionaries for these 36-channel `.mkv` clips! Passing `'trackIndex': 1` forces audio onto `A1 (dolbyatmos5.1.2)` and breaks the routing to `A5 (Vocal 1)` and `A6 (Vocal 2)`.
> Instead, call `mediaPool.AppendToTimeline(clip_infos)` using **only** `{'mediaPoolItem': mpi, 'startFrame': src_in, 'endFrame': src_out}`. DaVinci Resolve will automatically place Video on **`V1`**, OBS Streams 1–4 on **`A1–A4`**, and the dual mono vocals on **`A5 (Vocal 1)`** and **`A6 (Vocal 2)`** in 100% locked sync. Then immediately delete all clips on `A1–A4`!

1. **Clear Unlocked Assembly Tracks**:
   - Gather all existing timeline items on `V1` and `A1` through `A6`, deduplicate by `.GetUniqueId()`, and remove them via `tl.DeleteClips(items_to_delete, False)`.

2. **Batch Append Sub-Clips**:
   - Build the ordered list of sub-clip dictionaries:
     ```python
     clip_infos = [
         {
             "mediaPoolItem": seg["mediaPoolItem"],
             "startFrame": int(seg["startFrame"]),
             "endFrame": int(seg["endFrame"]),
         }
         for seg in final_segments
     ]
     appended_items = media_pool.AppendToTimeline(clip_infos)
     ```
   - Note: In DaVinci Resolve's Python API, `endFrame` in `AppendToTimeline` is inclusive (`duration = endFrame - startFrame + 1`, or verify exact frame count on `V1` after appending).

3. **Purge Unused OBS Audio Tracks (`A1` – `A4`)**:
   - Immediately collect all items placed on `A1`, `A2`, `A3`, and `A4` (`dolbyatmos5.1.2` tracks reserved for B-Roll/Atmos) and delete them without ripple:
     ```python
     unused_audio = []
     for track_idx in (1, 2, 3, 4):
         unused_audio.extend(tl.GetItemListInTrack("audio", track_idx) or [])
     if unused_audio:
         tl.DeleteClips(unused_audio, False)
     ```
   - Verify that:
     - **`V1 (Video 1)`** contains 100% of the pruned host video sub-clips, contiguous from `tl.GetStartFrame()` to the end with **0 gaps**.
     - **`A5 (Vocal 1)`** and **`A6 (Vocal 2)`** contain the exact matching number of mono audio clips with identical `GetStart()` and `GetEnd()` frames as `V1`.
     - **`A1` – `A4`** have `0` clips.

---

### PHASE 4: TRANSITIONS, TRACK STATE & DOWNSTREAM PIPELINE EXPORT

1. **Apply `Smooth Cut` Transitions on `V1`**:
   - Iterate through the assembled items on `V1` (`v1_items = tl.GetItemListInTrack("video", 1)`).
   - At each cut boundary between `v1_items[i]` and `v1_items[i+1]`, attempt to add a centered `Smooth Cut` transition (`6` to `12` frames, defaulting to `6` frames on tight jump-cuts or `12` frames where handles allow):
     ```python
     v1_items[i].AddTransition({
         "type": "Smooth Cut",
         "category": "simple",
         "position": "end",
         "alignment": "center",
         "duration": 6
     })
     ```

2. **Vocal Track State (`A5` / `A6`) & Track Locking**:
   - Leave **`A6 (Vocal 2)`** clips enabled (`True`) and **`A5 (Vocal 1)`** clips enabled (or disable `A5` clips via `item.SetClipEnabled(False)` if the project uses `Vocal 2` as the solo active mic).
   - Leave `V1`, `A5`, and `A6` unlocked so cuts can be inspected and tweaked before locking them for B-Roll insertion.

3. **Export Assembled Master Timeline `.srt` to `<resolve_proj_dir>/v/` (NEVER Create an `o/` Folder)**:
   - Automatically generate `<resolve_proj_dir>/v/<timeline_name>.srt` by shifting the kept word timestamps to their exact new timeline-relative positions (`00:00:00,000` to end).
   - **Strictly NEVER create or write files into an `o/` subfolder**—all recording caches and timeline `.srt` files belong in `<resolve_proj_dir>/v/`. This ensures downstream prompts (**Visuals (`V7`/`V9`)**, **Frame-Accurate B-Roll Creation/Editing**, and **Shorts Chapter Markers**) can immediately read the assembled timeline transcript from `<resolve_proj_dir>/v/`.

---

### DELIVERABLES

1. Execute the full pipeline (or present the cut list first if `/plan` is active).
2. Output a **Paragraph-by-Paragraph Script Completeness Audit** comparing `* - monologue.txt` against the assembled `V1` timeline:
   - Total raw duration vs. final edited duration (`frames` and `MM:SS`).
   - Which `.mkv` takes/false starts were discarded vs. kept for each paragraph.
   - Confirmation that `V1`, `A5 (Vocal 1)`, and `A6 (Vocal 2)` are 100% contiguous (`0` gaps) and `A1–A4` are clean (`0` clips).
