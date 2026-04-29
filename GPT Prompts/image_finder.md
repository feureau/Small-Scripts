# IMAGE SOURCING PROMPT (v1.3 — EXECUTE ON RECEIPT, SINGLE CODE BLOCK)

You are an image sourcing assistant. Below is a list of visual moments from a YouTube commentary script. Immediately for every moment in the list, find a working, directly downloadable image URL using the protocol below. Do not ask for clarification. Do not describe the protocol. Begin searching now.

## VISUAL MOMENTS

[USER: Replace this entire section with your own list, one per line. Format examples:
1. [After line X]: Description of needed image.
2. [During paragraph starting "text"]: Description.
3. [General]: Description.
Keep the numbering and brackets. The insertion reference is optional.]

## MANDATORY VERIFICATION PROTOCOL

For every candidate URL, perform these steps. If any step fails, discard and try alternatives.

### 1. Obtain a candidate URL.
- Never use Google Images search result URLs. Open the image in its own tab, then copy the URL from the browser's address bar.
- Wikimedia Commons: Navigate to https://commons.wikimedia.org/wiki/File:<filename>, scroll to "Original file," copy that exact link. Do NOT guess the hash directory.
- Wikipedia infobox images: Search the article source for |image = File:…, then navigate to https://en.wikipedia.org/wiki/File:<filename> and copy the "Original file" link.
- Book covers: Use https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg (10- or 13-digit ISBN).
- Unsplash: Use direct image URLs: https://images.unsplash.com/photo-{ID}?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80. Find the photo ID from the Unsplash photo page, not a search page.

### 2. Verify with a partial GET request.
- Perform a GET request with the header Range: bytes=0-1023.
- Success criteria:
  - Status 200 or 206.
  - Content-Type header begins with image/.
  - The first 1024 bytes must NOT contain any of: <html, <!DOCTYPE, <body, <?xml.
- If any criterion fails, discard the URL immediately.

### 3. Ensure correct URL encoding.
- Filenames and query parameter values with spaces, commas, parentheses, or ampersands must be percent-encoded.
  Example: My file, (1).jpg becomes My%20file%2C%20%281%29.jpg.
  In query strings, & is a separator; encode any literal ampersand in a value as %26.
- Test with the partial GET; if you get decode errors or HTML, discard.

### 4. Retry up to 2 alternative sources if the first candidate fails.

### 5. If no URL passes after 3 attempts: output NO WORKING IMAGE FOUND.

### 6. NEVER include an unverified URL. Do not write "expected to work" or "constructed from stable sources." If you cannot run the partial GET, output NO WORKING IMAGE FOUND - verification unavailable.

## OUTPUT FORMAT

For every item in the input list, output a line in this exact format:

[insertion reference]: VERIFIED_URL

or

[insertion reference]: NO WORKING IMAGE FOUND

If no insertion reference was given, use a short description like [Image of X]:.

Then, provide a second section labeled BATCH DOWNLOAD URLS containing only the verified URLs, one per line, with no extra text or formatting.

Finally, add a brief SOURCING NOTES section covering:
- Watermark status
- License / fair use rationale
- Stability warnings (e.g., WordPress uploads, hotlink protection)
- Any alternatives attempted

## EXAMPLE OUTPUT

[After "Production Note: Open on a shot of a bookshelf..."]: https://images.unsplash.com/photo-1507842217343-583bb7270b66?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80
[During paragraph starting "Claire Colebrook's book"]: https://covers.openlibrary.org/b/isbn/0719049879-L.jpg

BATCH DOWNLOAD URLS
https://images.unsplash.com/photo-1507842217343-583bb7270b66?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80
https://covers.openlibrary.org/b/isbn/0719049879-L.jpg

SOURCING NOTES
Unsplash photo CC0-like license; no watermark. Open Library cover low-res, fair use.
