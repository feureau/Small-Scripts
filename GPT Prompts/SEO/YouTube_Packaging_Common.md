# Shared YouTube Packaging Rules

Read this file from disk before using any YouTube metadata or thumbnail prompt in this set. This file owns shared behavior, source fidelity, the packaging handoff, platform limits, upload compatibility, visual defaults, and research provenance. Child prompts own their particular deliverables and output layouts. Do not copy shared rules into child prompts.

## 1. Honor the requested action

- Discuss, review, audit, or plan: return analysis or concepts only. Do not generate images, transcribe, edit video, upload, or write release files.
- Edit or fix prompt files: edit the prompt specifications only; do not execute the workflows they describe.
- Write metadata: produce the requested copy and sidecars. Do not automatically generate thumbnails or change a video.
- Develop thumbnail concepts: produce concepts and title pairings without image generation.
- Generate thumbnails: produce and inspect the requested images and exports. Do not upload or insert frames into a video.
- An explicit request to execute a complete pipeline authorizes its stated deliverables. Continue within that scope without repeated confirmation. A path supplied during an already authorized task identifies its target; a bare path alone does not authorize every workflow.
- Missing optional analytics or reference images is not a reason to halt otherwise feasible work. State material assumptions. Ask only when an unresolved identity, source, or target materially changes the result.

## 2. Source and language contract

1. The exact target video's or Short's corrected transcript is the primary source for subjects, events, scope, quotations, and thesis direction.
2. Approved scripts and reference notes may clarify spelling or supply explicitly authorized companion context. Timeline markers are timing candidates, not proof that the current render has the same timing.
3. Inspect actual frames or supplied images before describing their visual contents, likeness, expression, or composition. Never invent an observed shot from an SRT.
4. Existing approved titles, copy, and packaging briefs are handoff inputs. Do not silently replace an approved selection.
5. Write in the source's dominant language unless the user requests another language. Preserve accurate proper names and natural local search phrasing.
6. Distinguish what the speaker states from an interpretation of motives. Preserve relevant nuance and counterarguments without inventing a defense or forcing a rebuttal.
7. Every title and visual promise must have a supporting source moment. Do not fabricate evidence, alleged leaked material, secret access, events, or quotations.
8. Illustrative visual interpretations must not masquerade as authentic footage, screenshots, or documents. Keep character identities and relationships recognizable.

If only a standalone transcript exists, metadata and source-based concepts can proceed. Do not invent visual inspection, exact render identity, or verified timing.

## 3. Discovery research and editorial judgment

- Establish the intended audience, asset type, release objective, and likely discovery surface before choosing a hook.
- Use supplied channel search terms and audience analytics first. When useful and available, research relevant search suggestions, community terminology, and current official platform guidance.
- External discovery research may inform wording, terminology, and platform mechanics. It must not add unsupported narrative claims to the video.
- Distinguish observed query wording from measured demand. Autocomplete and competitor titles do not establish search volume or causation. Never invent volumes, ranking weights, forecasts, or test results.
- Record research URLs, observation dates, and unavailable evidence in the packaging brief or QA report, outside paste-ready copy and uploader JSON.
- Search-led, curiosity-led, and hybrid are useful candidate approaches, not mandatory formulas. Use only angles the content supports.
- A cited title study can suggest hypotheses; observational view multipliers are not expected gains for this channel. Do not mandate a frame rotation or prohibit all question titles.
- Prefer relevant terms used naturally. Do not enforce keyword density, exact repetition counts, universal preview cutoffs, compulsory emojis/numbers, or a debatable question on every asset.
- Keep the creator's conversational voice and earned wit. Avoid stock openings, repetitive transitions, forced outrage, and boilerplate engagement requests. Do not erase necessary repeated names or exact source quotations to manufacture variety.
- Historic channel metrics may guide a hypothesis without using previous thumbnail images as visual references. Do not reuse old thumbnail designs unless explicitly requested.

## 4. One coordinated packaging handoff

When a file workflow needs to pass concepts between prompts, use <base>-youtube-packaging.md beside the metadata, or an equivalent brief already supplied in the conversation. Do not create a second uploader-looking JSON file in the video directory: yt.py scans JSON files when locating metadata.

Keep the brief concise and include:

- Target video or Short, exact stem, duration if verified, language, audience, objective, source paths, and source limitations.
- Asset mode: long or short. Determine this from the actual intended upload and verified format; a filename or folder label alone is insufficient.
- Testing mode: package, thumbnail, title, or none.
- Visual preferences and available reference assets.
- Keyword/query candidates with their evidence status.
- Up to three concept IDs. For each: candidate title, viewer promise, visual idea, source/timestamp anchor, emotion, and where the opening or later video delivers the promise.
- The selected/default title, selection status (approved or provisional), exact thumbnail pairing, and export filenames when available.
- Research provenance and concise QA findings. Distinguish verified failures from editorial suggestions.

For metadata-only work, do not invent an image result or require an extra file if no handoff is needed. For a file-based coordinated release, persist the brief so subsequent prompts consume the same concepts.

### Long-video testing modes

- Package (default when three coordinated alternatives are requested): three distinct title-thumbnail pairs. This evaluates the whole promise, not the isolated effect of a title or image.
- Thumbnail: one selected title paired with three substantially different images. Other title candidates may remain in the copy file but are not part of this test.
- Title: one selected image paired with three titles. Reuse the image; do not generate three needless copies.
- None: produce only the requested selected assets.
- Use YouTube's native concurrent tests where the account and video are eligible. Shorts are not eligible for this native testing feature. Do not call sequential manual swaps a controlled A/B test.
- Do not promise a statistically significant winner, a universal CTR, or a fixed retention target. Review traffic source, audience, impressions, watch time, and retention in context.

## 5. Shared visual preferences

These are house defaults, not ranking factors. Explicit user preferences override them.

- No creator/host portrait by default. Relevant fictional characters or real subjects may appear when supported by the source.
- No added overlay/headline text by default. Any requested text option must be identified separately and match the user's preference; do not silently bake it into the image.
- No red borders, gratuitous arrows/circles, padded horizontal strips, abstract filler, or glossy plastic 3D aesthetics.
- Use concrete, topic-specific scenes with a clear focal hierarchy and cinematic lighting where suitable.
- Preserve the subject's established visual identity: reference-faithful animated characters for animation; photographic rendering for real people or physical subjects, unless a different treatment is requested.
- When a face appears, default to a closed-mouth expression. Match its emotional intensity to the argument; shock is not compulsory. Recognizability and appropriate emotion matter more than a formula.
- A title and image may share the subject or reinforcing information. The image should add a useful visual stake, contrast, consequence, or question rather than redundantly restating every word.
- Create distinct audience hypotheses, not mandatory differences on every color, lens, subject, and composition axis.
- Treat safe margins as working design guides. Check the actual export with surface-specific crop and overlay previews; no fixed percentage protects every UI.
- Preserve one clear focal idea at small display sizes. Small-size inspection is qualitative QA, not a measured sub-second perception test.

## 6. Platform limits and export profiles

Verified against the official references below on 2026-11-14. Recheck the relevant official source when an upload route changes or a discrepancy arises. Do not silently fall back to obsolete remembered limits.

| Item | Platform requirement or recommendation | House or workflow choice |
| --- | --- | --- |
| Video title | Maximum 100 characters | Child title lengths are soft editorial preferences |
| Description submitted through Data API | Maximum 5,000 UTF-8 bytes; title and description exclude < and > | Validate assembled description after hashtags, links, and chapters |
| Tag budget | Maximum 500 effective characters across tags | yt.py additionally restricts count and character set |
| Long thumbnail | YouTube recommends 3840 x 2160, 16:9 | Optional 1920 x 1080 convenience export |
| Shorts cover | YouTube recommends 2160 x 3840, 9:16 | Optional 1080 x 1920 convenience export |
| Desktop/API thumbnail upload | Maximum 50 MB in the current documentation | Compress appropriately without visible damage |
| Mobile video-thumbnail upload | Maximum 2 MB | Make a separate smaller export only when needed |

- Export JPG or PNG in a suitable display color space. Verify dimensions, aspect ratio, file size, and visible quality on disk.
- Request the needed aspect ratio from the image generator. Prefer sufficient native resolution; resizing does not create genuine detail. Avoid stretching. Inspect any crop or extension.
- A master is a deliverable export, not a claim that the generator produced native 4K detail. Report generation resolution if known and any resizing.
- Desktop Studio currently documents custom Shorts cover uploads. The YouTube app also provides frame selection. Check the actual available route; do not automatically modify a video to manufacture a selectable cover frame.
- The current thumbnails.set API supports Shorts after processing succeeds. A saved image alone does not prove that the uploader applied it.

### Tag compatibility for this repository

Inspect the active Programming/yt.py if a compatibility discrepancy appears. Current local sanitizer behavior requires at most 15 tags, each at most 30 characters, containing only ASCII letters, numbers, and spaces. These are local uploader restrictions, not universal YouTube tag rules.

- Use only useful tags; there is no mandatory minimum and no filler to reach a quota.
- Platform effective tag length = sum of tag lengths + one comma between tags + two extra characters for each tag containing a space. Require the effective total to be <= 500.
- Validate the actual sanitized values. Do not allow silent truncation or empty tags to change intended keywords.
- The ASCII restriction can conflict with localized metadata. Preserve the correct language in titles/descriptions and report the tag limitation; do not describe stripped non-Latin tags as localized SEO.
- Prioritize relevant names and useful spelling variants. Do not claim that a particular tag position receives a documented ranking boost.
- Verify that the chosen upload path actually sends tags. Do not claim prompt output fixes uploader code.

### Chapters

For long videos where chapters are requested and verified timing is available: start at 00:00, use at least three ascending timestamps, make every chapter at least ten seconds long including the last, and keep timestamps within the current duration. Use actual content boundaries and readable labels. Chapter count follows the source, not a compulsory 4-8 quota. If the source cannot support valid chapters, report the limitation rather than inventing timestamps. Shorts metadata does not inherit long-video chapter requirements.

## 7. Validation and scope

- Script-check hard constraints: output layout, JSON types and parsing, title equality, reconstructed-description equality, encoded size limits, effective tag budget, approved pairing, filenames, image dimensions, and file sizes.
- Editorial review covers promise accuracy, source support, clarity, appropriate emotion, style, and whether variants test distinct useful ideas. Do not present these as proven by a character counter.
- Separate hard failures, unresolved evidence, and editorial suggestions.
- Use one initial image batch and at most two targeted revision rounds per failed variant unless the user requests more. Stop and report unresolved issues rather than looping indefinitely or consuming unlimited generation.
- Do not overwrite approved assets or unrelated project files. Save to the requested location; use existing project output conventions and mirror only to already established destinations.
- Use the environment's supported clickable file links. Never report nonexistent files, unperformed uploads, invented visual inspection, or measured performance before publication.

## Official references and evidence notes

- Title and thumbnail guidance: https://support.google.com/youtube/answer/12340300
- Description guidance: https://support.google.com/youtube/answer/12948449
- Video API limits and tag counting: https://developers.google.com/youtube/v3/docs/videos
- Thumbnail sizes and Studio routes: https://support.google.com/youtube/answer/72431
- Thumbnail API: https://developers.google.com/youtube/v3/docs/thumbnails/set
- Native title/thumbnail testing and eligibility: https://support.google.com/youtube/answer/16391400
- Chapters: https://support.google.com/youtube/answer/9884579
- Shorts discovery: https://support.google.com/youtube/answer/11914225
- Shorts app thumbnail selection: https://support.google.com/youtube/answer/10343433
- Tags' limited discovery role: https://support.google.com/youtube/answer/146402
- Optional observational research, not a causal guarantee: https://vidiq.com/research/youtube-title-formulas-study/
