Use the DaVinci Resolve MCP to populate my current active timeline with frame-accurate B-roll clips based on the spotting sheet at @[path/to/spotting_sheet.md]:

1. **Safety Backup:** Duplicate the current timeline to `<Timeline Name> - Backup (Pre-B-Roll)` before making any changes, then switch back to the main timeline.
2. **Preserve Locked Tracks:** Keep all locked video and audio tracks (such as finalized monologue vocals, camera A-roll, and look/grading generators) 100% untouched and locked. If any unlocked/unused video tracks sit between Video 2 and the top grading track and obscure the view, disable them.
3. **Media Pool Matching:** Resolve each source video referenced in the spotting sheet from the Media Pool. Filter strictly by `Type == "Video + Audio"` so nested timeline items with similar names are never accidentally used.
4. **Include Both Video & Audio:** Import both Video and Audio from every source clip onto the timeline.
5. **Checkerboard Track Layout (V1/A1 & V2/A2):** Alternate clips between **Video 1 / Audio 1** (Clips 1, 3, 5...) and **Video 2 / Audio 2** (Clips 2, 4, 6...) using `MediaPool.AppendToTimeline()` so adjacent cuts never collide and transitions can be added easily.
6. **Bridge Micro-Gaps (Zero Black Frames):** Read the timeline frame rate and convert timestamps to frames. Extend each B-roll clip's duration forward until the exact start frame of the next B-roll clip (`end_frame = next_clip_start_frame`) to cover natural speech pauses between sentences with 100% continuous coverage and zero black frames.
7. **Verification:** After insertion, verify that all spotting entries were placed, all clips are Online, locked tracks are untouched, and there are 0 continuity gaps or overlaps across the timeline.
