Use the DaVinci Resolve MCP to add non-destructive Shorts chapter markers to my current active timeline based on @[path/to/transcript_or_spotting_sheet]:

1. **Do Not Edit Tracks:** Do not cut, move, or modify any video or audio clips on the timeline.
2. **Segmentation (Tight ~60s Shorts):** Break the monologue/transcript into self-contained Shorts (~45s–75s each) at natural paragraph or topic breaks so every segment has a strong opening hook, core point, and closing punchline.
3. **Frame-Accurate Alignment:** Read the timeline's frame rate and snap each marker's start frame to the exact B-roll cut or dialogue start boundary.
4. **Marker Style (Point Chapter Markers):**
   - Use Point Markers (`duration = 1`) via `timeline.AddMarker()`.
   - **Color:** Use `Cyan` uniformly for all markers (`Short 01: <Title>`, `Short 02: <Title>`, etc., as well as the final `Outro` marker so the end of the last Short is clearly bounded).
   - **Marker Notes:** Include the segment's duration in seconds, timecode range, opening spoken hook, and closing spoken cue.
   - **Idempotency:** Tag markers with `customData="shorts_chapter"` and clear any previous `"shorts_chapter"` markers before adding new ones.
