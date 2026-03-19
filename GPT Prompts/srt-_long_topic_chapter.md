# SRT- long topic chapter


**Please analyze the following SRT transcript and generate a new SRT file containing only chapter markers based on the content.**

**Key Principle: The goal is to provide navigable chapter points based exclusively on major topic changes in the video, regardless of the duration between these changes. Chapters should only be created when the core subject of the conversation makes a distinct and significant shift.**

**Follow these instructions carefully:**

**1\. Identify Chapters (Major Topic Shifts Only):**  
**Read through the source transcript and identify only the significant and clear shifts in the main topics being discussed. A new chapter should mark the point where the conversation moves to a distinctly new subject. Ignore sub-points, minor transitions, or the length of time a single topic is discussed. A chapter could be 5 minutes long or 50 minutes long; the only trigger for a new chapter is a change in the primary subject matter.**

**2\. Chapter Placement:**  
**Reference Original SRT Timestamps: Determine the start time for each chapter directly from the original SRT transcript. Specifically, use the start timestamp of the subtitle line where a new major topic begins as the basis for the chapter's start time.**

**3\. Adjusted Chapter Start Timestamp (Explicit Overlap Prevention):**  
**Identify Original Start Time: For each new chapter, note the original start timestamp (Toriginal\_start​) of the subtitle line where the new topic begins.**  
**Retrieve Previous Subtitle End Time: Find the end timestamp (Tprevious\_end​) of the immediately preceding subtitle in the original SRT. If this is the very first chapter, consider Tprevious\_end​ to be 00:00:00,000.**  
**Calculate Potential Adjusted Time: Subtract one frame (approximately 00:00:00,017 for 60 FPS) from the original start time to get a potential adjusted start time (Tadjusted\_potential​).**  
**Overlap Check: Compare Tadjusted\_potential​ with Tprevious\_end​.**

* **If Tadjusted\_potential​ is less than or equal to Tprevious\_end​: This indicates a potential overlap. Do not adjust the start time. Use the original start time: Chapter Start Time \= Toriginal\_start​.**  
* **If Tadjusted\_potential​ is greater than Tprevious\_end​: There is no overlap. Use the adjusted start time: Chapter Start Time \= Tadjusted\_potential​.**  
  **Set Chapter Start Timestamp: Assign the determined Chapter Start Time as the starting timestamp for the chapter marker in the output SRT.**

**4\. Chapter Marker Display Duration:**  
**Each generated chapter marker in the output SRT must have a display duration of exactly 1 second. Calculate the end time by adding precisely 00:00:01,000 to the chapter's start timestamp.**

**5\. End Time Capping:**  
**For the final chapter marker, if the calculated end time extends beyond the end time of the last subtitle in the source transcript, adjust the final marker's end time to match the last subtitle's end time exactly.**

**6\. Framerate Compliance:**  
**Ensure that all timestamps comply with a 60 FPS framerate standard, meaning all mmm millisecond values must be frame-accurate and consistent with 60 FPS rounding (increments of approximately 16.666... ms).**

**7\. Chapter Title Generation (Strategic & Effective 'Legit Bait' Method):**  
**Craft a chapter title for each segment by creating a compelling, honest, and highly clickable title that maximizes viewer engagement and satisfaction.**

* **Identify the Core Promise & Frame the Hook: Determine the chapter's central idea and frame the title around this core promise to create a "curiosity gap."**  
* **Optimize for a Broad Audience: Translate any niche or technical jargon into simple, relatable concepts.**  
* **The 'Legit Bait' Test (Honesty is Key): The title must be an enticing hook that accurately reflects the chapter's content without overpromising.**  
* **ABSOLUTELY NO EMOJIS, NO APOSTROPHES (‘), NO COLON (:), NO QUOTATION MARKS (“), NO QUESTION MARKS (?), AND NO EXCLAMATION MARKS (\!): Frame questions as declarative statements.**  
* **Maximum Character Utilization (75-character limit): Use the space to add descriptive keywords that make the title's hook more understandable and discoverable.**  
* **Deep Integration of Primary Keywords: Naturally weave relevant keywords into the title.**  
* **Accurate (but Compelling): Ensure the final title accurately represents the core takeaway of that chapter in the most interesting way possible.**

**Output Format:**  
**The output must be a valid SRT file containing only the chapter markers. Each entry should include:**

* **A sequential number (starting from 1).**  
* **A timestamp line in the format HH:MM:SS,mmm \--\> HH:MM:SS,mmm.**  
* **The YouTube-Style Chapter Title.**  
* **A blank line separating entries.**

**WARNING: MAKE SURE TO FULLY PROCESS THE SRT TEXT FROM BEGINNING TO THE END.**

