# YouTube Uploader JSON Serializer

Convert approved YouTube copy into the exact sidecar accepted by Programming/yt.py. This prompt does not independently rewrite titles or descriptions.

## Read first

Read ./YouTube_Packaging_Common.md from disk. It owns mode handling, source fidelity, platform limits, tag counting, and local uploader compatibility.

## Inputs and mode

- Required: approved five-block output from ./SEO_yt_Long.md or ./SEO_yt_Short.md, or equivalently explicit approved title, description, hashtags, and tags.
- Accept mode=long or mode=short, exact target stem, and the shared packaging brief if present.
- Resolve mode from the approved source/brief and actual intended upload. Do not infer it from filename alone.
- Preserve the selected/default title. For five-block input this is Title 1; it must match JSON title exactly after removing only the code fence.
- If approved copy is missing, invoke the appropriate copy prompt within the user's authorized scope, or identify the missing input. Do not make up approval, silently write a second version, or guess the mode where it materially changes the output.
- A Short must retain its Short description. Do not add long-video chapters or length quotas.
- Alternative titles, thumbnail filenames, research, and test hypotheses belong in the packaging brief, not as extra uploader fields.

## Exact schema

Return one object with exactly these keys and types:

{
  "title": "approved selected title",
  "description": "approved description without its terminal hashtag line",
  "hashtags": [],
  "tags": []
}

title and description are strings. hashtags and tags are arrays of strings. Empty arrays are valid where the approved input has none. Do not add mode, alternatives, filename, thumbnail, source notes, or invented uploader settings.

## Lossless conversion

1. Extract the selected title, full description, terminal hashtag line (if any), and comma-separated tags.
2. Move only the terminal standalone hashtag line into hashtags, preserving order. Do not blindly delete # from ordinary text, URLs, quoted material, or topic names.
3. Preserve the approved description body, chapter timestamps, paragraph breaks, links, credits, punctuation, and title characters.
4. Serialize with a real JSON serializer, for example json.dumps(payload, ensure_ascii=False, indent=2). Quotation marks inside values are valid when escaped correctly; do not replace the author's punctuation to avoid escaping.
5. Newlines in a decoded string must be actual line breaks. The JSON file represents those as \n. Do not double-escape them into literal backslash-n text.
6. Reconstruct the final description using yt.py's behavior: description followed by two newlines and space-joined hashtags, then outer whitespace stripped. It must equal the approved complete description after the same outer-whitespace normalization.
7. Require exact selected-title equality and exact tag/hashtag order. If the source conflicts with a hard limit or the reconstruction fails, correct the source through its owner prompt and synchronize all affected files; do not silently mutate only JSON.
8. Keep research, QA notes, local paths, and source citations outside the uploader object.

## Validation

- Parse the written JSON using json.loads(). Require exactly the schema keys above and their declared types.
- Apply the shared title, assembled-description UTF-8 byte limit, tag-count/per-tag sanitizer rules, and platform effective tag-length calculation.
- Confirm no duplicate terminal hashtag line in description, and no duplicate hashtags in the array.
- Validate title and description against the relevant source copy prompt without duplicating its creative rules here.
- For file workflows, require the exact target stem and <base>-youtube.json filename, including for Shorts. Do not write alternative metadata JSONs beside the video; the uploader's fuzzy matching can choose the wrong one.
- Inspect the current uploader integration if requested. Generating a tags array or thumbnail image does not prove the upload path sends or applies it.
- Do not upload, change visibility, schedule, or alter a video from this serialization task.

## Output

Return exactly one valid JSON object, starting with { and ending with }, with no Markdown fences or surrounding prose. When saving, write UTF-8 JSON to <base>-youtube.json. Record QA separately if the surrounding workflow requests it.
