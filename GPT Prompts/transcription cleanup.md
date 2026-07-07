I have a directory of transcription files that I need merged into a single markdown document and cleaned up. Use the following configurable, generalised process:

---

## Source Files
- **Primary directory**: `[PRIMARY_DIR]`
  - Files are named using the pattern: `[FILE_PATTERN]` (e.g., `IMG_XXXX.txt`, `page_*.md`, etc.)
  - They are page‑by‑page transcriptions of a single multi‑page document.
- **Fallback directory (optional)**: `[FALLBACK_DIR]`
  - Use only when a page is missing from the primary directory.

## Step 1: Merge all files
- Read all files matching the given pattern in **numerical/alphabetical order** (according to the filename’s natural sort order).
- If a file does not exist in the primary directory, check the fallback directory.
- Concatenate all content into a single file.
- Between each page, insert a marker line: `## Page [filename]`
- Save as `merged_transcription.md`

## Step 2: Remove all metadata / boilerplate lines
Delete any line that matches the patterns listed below (if provided). If no patterns are given, skip this step.
- `[METADATA_PATTERN_1]`  
- `[METADATA_PATTERN_2]`  
- … (user supplies regex or plain strings)  
*Typical examples: blockquotes like `> Merged from...`, source attribution `*Source: ...*`, horizontal rules `---`, page markers from a previous merge, etc.*

## Step 3: Collapse consecutive blank lines
Replace any occurrence of 2 or more consecutive blank lines with a single blank line.

## Step 4: Remove old artifact headings
The original transcription pages often contain **binder tab labels, file folder labels, or repeated section titles** that are not part of the final document’s content. Remove them as follows:

- If a **list of specific headings** is provided (see below), remove every H1 (`#`), H2 (`##`), and H3 (`###`) line that matches one of these, using **flexible, accent‑insensitive matching** (e.g., normalise diacritics and case).
  - `[HEADING_TO_REMOVE_1]`
  - `[HEADING_TO_REMOVE_2]`
  - …
- **Automatically** detect and remove any other headings that look like page‑level artifacts, using these heuristics:
  - The heading is the very first line of a page’s content (i.e., immediately follows a `## Page …` marker or the start of the file).
  - The heading is short (fewer than ~80 characters), in ALL CAPS, or consists only of a name/date/location with no trailing punctuation.
  - It is an exact duplicate of a heading already seen in another page.
  - It matches generic binder‑label patterns, such as:
    - `# SOLO LETTERS`, `# YOGYA LETTERS`, `# REBELLION …`
    - `## RING FILE`, `## Footnotes`, `## [Date range]`
    - `### GUIDEX`, `### Diary of …`, `### Decision G.G …`
- After removal, **do not** delete headings that appear to be part of the actual document content (e.g., a letter heading like “### 3rd July 1825 – Bulan Kadji 5” if it is unique and embedded within a paragraph flow). If unsure, keep the heading and let the user decide later.

## Step 5: Build the book‑style heading hierarchy
Organise the remaining content into a structured document. Insert new headings as needed. The target structure should follow this model (adjust the number of parts and titles based on the actual content):

```
# [Document Title]: [Date Range]: [Brief Description]

## Cover and Binder Descriptions
[Cover / binder introductory text]

## File Folder Tabs / Organisation
[Description of how the original material was physically organised, if present]

## Part I: [Topic] ([date range])
### [Subtopic or individual document]
…

## Part II: [Topic] ([date range])
…
```

### Guidelines for Part headings:
- Examine the content to identify **logical groupings** (e.g., correspondence, diaries, financial records, legal documents, military reports).
- Assign each group a **Roman numeral** (I, II, III, …) and a **descriptive title**.
- Each Part heading must be `## Part [Roman]: [Descriptive Title] ([date range])`.
- Under each Part, add `###` subsection headings for each distinct document, topic, or sub‑grouping.
- If a Part has no content after organising (just a heading), remove it entirely.
- The document title (`# …`) and the `## Cover…` / `## File Folder Tabs…` sections should be derived from the actual content (e.g., the first page often contains binder‑cover text).

## Step 6: Verify content placement
- Check that content under each Part heading actually belongs to that Part’s topic.
- If content is misplaced, move it or adjust the Part boundary accordingly.
- Use natural text boundaries (e.g., original divider pages, date jumps, salutations) to guide decisions.

## Step 7: Scan and build an abbreviation glossary
- Search the entire document for **abbreviations** (acronyms, initialisms, shortened forms).
- Categories to consider (adjust based on document content):
  - **People**: DP, MB, MN, PA, etc.
  - **Titles / Honorifics**: R.T., R.M., R.A., Patih, Bupati, etc.
  - **Archival / Institutional**: ARA, BPL, G.G., N.I., S.S., V.H.
  - **Publications**: BKI, TNI.
  - **Military / Administrative ranks**: Col., Capt., Lt., Maj., Res., No., etc.
  - **General / Latin abbreviations**: cf., e.g., etc., i.e., viz.
- For each abbreviation, **determine the full form from the surrounding context**. If no clear expansion is found, mark it as “Uncertain / Unidentified”.
- Insert the glossary at the top of the document, immediately after the H1 title, with the heading `## Abbreviation Glossary`.
- Organise the glossary into **sub‑tables by category**, using H3 headings (e.g., `### People`, `### Archival References`, etc.).

## Step 8: Final cleanup
- Remove any remaining metadata artefacts or duplicate headings that were missed.
- **Fix encoding issues**: ensure all accented characters (ë, è, ä, é, etc.) are properly represented in UTF‑8. If you see mojibake (e.g., `Ã«`), convert to the correct Unicode.
- **Verify heading hierarchy**: only one H1 (`#`); all H2s are direct children of the H1; all H3s are under an H2.
- Confirm no **empty sections** remain (remove any section with zero body text).
- Ensure the file ends cleanly (no trailing empty headers).

---

## Output
- Save the final result to `merged_transcription.md` in the working directory.
- The file must use **UTF‑8 encoding**.
- Report final line count and file size when done.
