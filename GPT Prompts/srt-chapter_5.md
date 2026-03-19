# SRT-chapter 5


**Generate SRT Chapter Markers with YouTube-Style Titles**

**Please analyze the following SRT transcript and generate a new SRT file containing only chapter markers based on the content.**

**Key Principle: The goal is to provide navigable chapter points throughout the video. While major topic shifts are primary chapter markers, if a single topic is discussed for a prolonged period, you must subdivide that long discussion into multiple chapters based on internal sub-points or transitions, rather than allowing one chapter to cover an excessively long, monolithic segment. Additionally, ensure chapters are spaced sufficiently apart to avoid rapid, jarring transitions in the chapter list.**

**Follow these instructions carefully:**

1. **Identify Chapters (Including Sub-topics):**  
   **Read through the source transcript and identify significant shifts in the topics being discussed. Additionally, if a single topic spans a long duration, identify logical sub-points, transitions, or distinct arguments within that main topic. Each point where the conversation moves to a distinctly new topic or to a significant sub-point within a long topic should mark the beginning of a chapter.**  
2. **Chapter Placement & Spacing (Minimum Separation & Mandatory Subdivision):**  
   **Reference Original SRT Timestamps: Determine the start time for each chapter directly from the original SRT transcript. Specifically, use the start timestamp of the subtitle line where a new topic or a significant sub-point within a longer discussion begins as the basis for the chapter's start time.**  
   * **Target Interval & Constraints: Aim to select chapter start times that result in chapters being approximately 30 to 55 seconds apart. Prioritize logical content breaks and meaningful topic/sub-topic shifts over enforcing a strict numerical interval.**  
   * **Minimum Separation Mandate: Ensure that chapters are placed to be generally no closer than 30 seconds apart. While you should look for logical breaks, do not create a chapter marker if the timestamp for that break is less than 30 seconds after the start of the previous chapter. In such cases, skip that minor transition and wait for the next significant break or sub-point that occurs at least 30 seconds after the previous marker. Intervals in the 25-35 second range are acceptable if they correspond to a clear logical break.**  
   * **Mandatory Subdivision for Long Topics (Rule Hierarchy): The rule for subdividing long segments is the highest priority. If a single discussion point results in an interval exceeding 90 seconds, you must create a chapter to enforce the time limit. It is better to create a chapter at a less-than-ideal transition point than to allow a gap to run for several minutes.**  
     * **Priority 1: Find a Logical Break. First, attempt to find a logical sub-break, transition, or shift in focus within the long segment.**  
     * **Priority 2: Find the Best Available Break. If no obvious logical break exists, find the best available transition point, such as a significant pause in speech, a transition phrase, or a minor change in subject.**  
     * **Fallback Titling: If a chapter is created under these fallback conditions (i.e., without a strong topical shift), you must title it using a continuation format. For example: Continuing the Discussion on X or A Deeper Look Into the Previous Point.**  
3. **Chapter Start Timestamp (Use Original Time Exactly):**  
   **The start timestamp for each chapter marker must be identical to the start timestamp of the subtitle in the source SRT file where the new chapter begins. No adjustments, subtractions, or overlap checks should be performed. The original timestamp is used directly.**  
4. **Chapter Marker Display Duration:**  
   **Each generated chapter marker in the output SRT must have a display duration of exactly 1 second. Calculate the end time by adding precisely 00:00:01,000 to the chapter's start timestamp.**  
5. **End Time Capping:**  
   **For the final chapter marker, if the calculated end time extends beyond the end time of the last subtitle in the source transcript, adjust the final marker's end time to match the last subtitle's end time exactly.**  
6. **Framerate Compliance (60 FPS):**  
   **Ensure that all timestamps comply with a 60 FPS framerate standard. This means all millisecond (mmm) values must be frame-accurate and consistent with 60 FPS rounding, representing increments of approximately 16.667 ms (1000 ms / 60 frames). If a source timestamp is not perfectly aligned, it should be rounded to the nearest valid 60 FPS frame value for the output.**  
7. **Chapter Title Generation (Strategic & Effective 'Legit Bait' Method):**  
   **Craft a chapter title for each segment by creating a compelling, honest, and highly clickable title that maximizes viewer engagement and satisfaction. The goal is to spark genuine curiosity ("Legit Bait") without being deceptive ("Click Trap"). Crucially, the final title must not exceed 75 characters, must be a single flowing sentence, and must adhere to all constraints below.**  
   * **Identify the Core Promise & Frame the Hook: First, determine the chapter's central idea: Is it a surprising outcome, a key problem, or an answer to a question? Frame the title around this core promise to create a "curiosity gap" that makes the viewer want to know more.**  
   * **Optimize for a Broad Audience: Translate any niche or technical jargon into simple, relatable concepts. Frame the title using universal themes like secrets, mistakes, reasons, or solutions that appeal to a general viewer who may have no prior context.**  
   * **The 'Legit Bait' Test (Honesty is Key): The title must be an enticing hook that accurately reflects the chapter's content. While it should be compelling, it must not overpromise or mislead. The goal is a click that leads to a satisfied viewer who feels their time was respected.**  
   * **ABSOLUTELY NO EMOJIS, NO APOSTROPHES (‘) BY NOT USING WORDS OR GRAMMAR THAT USES APOSTROPHES ('), NO COLON (:) NO QUOTATION MARKS (“) NO QUESTION MARKS (?), AND NO EXCLAMATION MARKS (\!): This is a non-negotiable, strict enforcement. Achieve compelling hooks without these characters. Frame questions as declarative statements (e.g., "This is why X happens").**  
   * **Maximum Character Utilization for Clarity & SEO: Strive to use the space near the 75-character limit to your advantage. Use the extra characters to add descriptive keywords and clarifying phrases that make the title's hook more understandable and discoverable in search, all while maintaining a single, flowing sentence.**  
   * **Deep Integration of Primary Keywords: Naturally weave relevant keywords into the title. These keywords should enhance the compelling promise of the title, making the honest hook more discoverable to viewers searching for that specific topic.**  
   * **Accurate (but Compelling): Ensure the final title accurately represents the core takeaway of that chapter. Your task is to present this truth in the most interesting and curiosity-inducing way possible, within the given constraints.**

**Output Format:**  
**The output must be a valid SRT file containing only the chapter markers. Each entry should include:**

* **A sequential number (starting from 1).**  
* **A timestamp line in the format HH:MM:SS,mmm \--\> HH:MM:SS,mmm (using the original start time and a duration of exactly 1 second, or capped for the final marker).**  
* **YouTube-Style Chapter Title: Generated according to instruction 7\.**  
* **A blank line separating entries.**

**Do not use python to process the srt text. Do not include any of the original subtitle text in the output.**

