### **🔹 YouTube Description**


**Goal:** Write an SEO-optimized, information-dense description based on the provided SRT, ensuring the total combined character count for the entire Description (including all essay sections and Timestamps) and Hashtags ABSOLUTELY DOES NOT EXCEED 5000 characters. The primary objective is to convey maximum SEO value and key information within this strict limit, prioritizing conciseness in the main body to allocate sufficient space for timestamps and hashtags. Enrich the SRT basis extensively with contextual information and a high volume of relevant keywords derived from or related to the SRT.

* **Understanding the Topic:** Infer the main subject/theme deeply from the SRT. Identify specific entities accurately mentioned in the SRT. Use this understanding to target a broad range of relevant search queries.  
* **Formatting:** Use reader-friendly paragraphs. Avoid numbered lists for main content. Structure for readability despite the length.  
* **Opening:** Start with 2–4 compelling sentences summarizing the core value/hook from the SRT, front-loading crucial keywords.  
* **Detailed Elaboration / Main Body:**  
  * The main body of the description (before the timestamps) MUST BE AGGRESSIVELY AND UNCOMPROMISINGLY CONDENSED. Your task is to provide maximum information density with the absolute minimum words necessary, synthesizing the core arguments, pivotal events, key evidence, and significant implications from the SRT. Focus only on *why* events or theories are important, not just what happened, and avoid any non-essential descriptive language. Brevity is paramount in this section.  
  * For each theme, extract core points from the SRT, then synthesize highly relevant external details, context, and key implications directly and concisely. Avoid lengthy elaborations; every word must add critical value or SEO weight.  
  * Quote impactful statements from the SRT transcript when appropriate, but focus primarily on original elaboration.  
  * If discussing specific media mentioned or clearly implied in the SRT, use official titles and incorporate a wide array of related SEO keywords (actors, directors, studios, genre specifics, plot points, fan theories, critical reception, related works).  
  * Weave a rich, dense, and diverse array of highly relevant keywords naturally throughout – include long-tail keywords, semantic variations, question-based keywords, and terms reflecting various facets of viewer search intent related to the SRT topic. Prioritize the most impactful keywords and contextual information, using efficient and direct language to maximize keyword density within the condensed format. Focus on impactful, concise repetition of key concepts where space allows.  
* **Timestamps Section:**  
  * Identify key segments within the SRT data corresponding to major, macro-level topic shifts, distinct historical periods, or pivotal conceptual shifts. The goal is a highly curated list that clearly outlines the primary narrative progression of the video.  
  * **Automatic Video Length Inference:** You MUST automatically determine the total video duration by identifying the LAST TIMESTAMP in the provided SRT content. This last timestamp (e.g., HH:MM:SS,ms or MM:SS,ms) represents the video's end time. Convert this end time to the total duration in minutes.  
  * **Strict Timestamp Count Requirement:** Based on the inferred total video duration (in minutes), you MUST calculate and adhere to a target of 3–4 timestamps per 10 minutes of video length.  
    * 0–10 minutes → 1–4 timestamps  
    * 10–20 minutes → 3–8 timestamps  
    * 20–30 minutes → 6–12 timestamps  
    * and so on.  
  *   
  * You MUST ensure the number of generated timestamps falls within this calculated range.  
  * Prioritize fewer, more impactful timestamps that represent distinct, jumpable sections rather than minor sub-points, while still meeting the calculated count.  
  * Each timestamp description must be a concise, keyword-rich phrase (acting as a chapter title) that clearly indicates a major topic shift. It should be a brief, impactful phrase or short clause – not a full sentence – prioritizing clarity and keyword relevance for quick navigation. Use MM:SS – Descriptive Keyword Title. Ensure the MM:SS reflects the actual time in minutes and seconds within the video, using approximate start times from the SRT.  
* **Closing:** Conclude with a clear Call to Action by encouraging likes, subscriptions, shares, comments, and notification bell clicks. Reinforce the video's value using keywords related to the SRT topic.  
* **IMPORTANT:**  
  * Do not include section titles in the description.  
  * Do not use lists in the description section. All lists must be converted into proper text.

  ---

  ### **🔹 Hashtags**

* Generate **exactly 3** strategically chosen hashtags relevant to the SRT content.  
* Mix broad, specific, and potentially trending terms. Use popular, relevant terms even if not explicitly in SRT but strongly related to the topic.  
* These hashtags must be included in the JSON array and also appended to the end of the description.  
  ---

  ### **🔹 Tags (Keywords)**

* Generate a comprehensive list of keywords/phrases optimized for Youtube based on the SRT content and related external knowledge, maximizing relevance within the strict character limit.  
* Include main topics, specifics, synonyms, common misspellings, long-tail variations, question queries, broader concepts from the SRT and related external knowledge. Focus intensely on search terms relevant to the SRT's subject matter.  
* **Strict character limit:** The total character count for all tags combined absolutely must not exceed 500 characters.  
* If your initial list of generated tags exceeds 500 characters, you MUST shorten the list by removing less relevant or redundant tags until the total character count is strictly below 500 characters.  
* Prioritize the most impactful and diverse tags.  
* Output only the list of tags/keywords as a JSON array.  
  ---

  ### **🛑 Global Instructions**

* **ABSOLUTELY NO FILE REFERENCES IN OUTPUT:** Non-negotiable. Must be completely absent from the final output (this refers to file paths/names).  
* **ABSOLUTELY NO FOOTNOTES AND REFERENCES IN OUTPUT:** Non-negotiable. Must be completely absent from the final output.  
* **NO ANGLED BRACKETS IN OUTPUT:** The final generated Title, Description, Hashtags, and Tags must be completely free of any angled bracket characters (\< and \>). This is a strict requirement for all parts of the output.  
* **Virality & SEO First:** Prioritize maximizing viral potential via strong SEO, engagement hooks, and clickability, all derived from and expanding upon the provided SRT data. Length and detail in the description remain key, within the Description \+ Hashtags character limit.  
* **Extensive External Knowledge REQUIRED:** You MUST use your knowledge base extensively to elaborate, add context, and integrate keywords far beyond the raw SRT, always staying relevant to the core topics identified within the SRT.  
* **SRT as Foundation Only:** The SRT provides the core topic/quotes, but the bulk of the description's text must be expanded information related to that core.  
* **Paragraph Format (Description):** Maintain paragraph structure.  
* **YouTube Best Practices:** Adhere strictly to best practices.  
* **Tone:** Engaging/informative for description; highly attention-grabbing/viral for title.  
* **Final Output Cleaning:** Before presenting the final result, review all generated text (Title, Description, Hashtags, Tags) and remove any citation markers, source indicators, or similar notations. The final output delivered to the user must be completely free of such markers.

  ### **PROMPT END**

