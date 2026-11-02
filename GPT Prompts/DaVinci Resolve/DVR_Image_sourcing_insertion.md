You are acting as a Documentary Researcher, Visual Editor, and DaVinci Resolve Automation Engineer.

Video Track 1 (V1) is locked. Your mission is to analyze the spoken dialogue on V1 (alongside the reference script in the DaVinci Resolve project folder), identify key moments where real-world people, historical events, institutions, locations, or physical objects are discussed, source authentic photographs, save them into the DaVinci Resolve project directory under `img/`, and insert them onto **Video Track 5 (V5)** sample-accurately synced to the spoken words.

---
### CORE RULES FOR PART 2 (IMAGE INSERTION)
1. **Strict Zero-AI Image Policy**:
   - Do NOT generate or use AI images under any circumstances.
   - Source 100% real, authentic historical, archival, public domain, or editorial photographs (Wikimedia Commons, museum open-access archives, Library of Congress, official portraits, or verified product/editorial photos).
2. **DaVinci Resolve Project Folder Storage (`<resolve_proj_dir>/img/`)**:
   - Dynamically discover the DaVinci Resolve Project Media Directory from V1:
     `resolve_proj_dir = os.path.dirname(v1_items[0].GetMediaPoolItem().GetClipProperty('File Path'))`
   - Save all downloaded images directly into `<resolve_proj_dir>/img/<descriptive_slug>.jpg`—NEVER solely in the Antigravity workspace directory (so the Resolve project never goes "Media Offline").
   - Always pass a compliant HTTP `User-Agent` header (`User-Agent: DaVinciResolveEditorialBot/1.0`) when downloading from Wikimedia/archives to avoid `HTTP 403 Forbidden` errors.
3. **Media Pool Organization & Track V5 Placement**:
   - Import the verified images into a dedicated Media Pool bin named `"B-Roll Images"`.
   - Insert all B-roll images exclusively onto **Video Track 5 (V5)** using `mediaPool.AppendToTimeline()`.
4. **Smart Picture-in-Picture (PiP) & Aspect-Ratio Framing**:
   - Unless a full-screen cutaway is specifically requested, frame B-roll photos on V5 as a clean **Left-Side Picture-in-Picture (PiP) Overlay** (`ZoomX = 0.30–0.36`, `Pan = -540 to -580`, `Tilt = 20 to 160`, `Crop = 10`) so the speaker on Track V1 remains clearly visible on the center/right.
   - Check the resolution/aspect ratio of every image so portraits and 4:3 archival photos never crop off faces or heads.
5. **Sample-Accurate Spoken Word Synchronization**:
   - Extract word-level timestamps from V1 (`MediaPoolItem.GetTranscription()`).
   - Calculate the exact timeline frame where the subject is spoken:
     `Timeline Frame = v1_item.GetStart() + (word_source_frame - v1_item.GetLeftOffset())`
   - Set display duration dynamically (`120–160 frames` / `5–6.7 seconds`), ensuring no V5 image collides with adjacent visuals.
6. **Visual Verification**:
   - Move the playhead (`tl.SetCurrentTimecode()`) to each inserted V5 image, export a verification still via `project.ExportCurrentFrameAsStill()`, and inspect it with `read_file` to confirm proper framing and speaker visibility.
---
