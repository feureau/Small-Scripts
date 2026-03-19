### **🎯 JSON Output Requirement**


Your final response must be valid JSON with the following structure:

code JSON

downloadcontent\_copyexpand\_less

*    {  
*   "title": "string (YouTube Title)",  
*   "description": "string (YouTube Description including timestamps and CTA, max 5000 chars with hashtags)",  
*   "hashtags": \["string", "string", "string"\],  
*   "tags": \["string", "string", "... up to 500 chars total"\]  
* }  
     
* Keys must always appear in this order: title, description, hashtags, tags.  
* JSON must be valid and parseable.  
* Absolutely no extra fields outside of these four.  
* Hashtags must appear both as an array in JSON and appended at the bottom of the description.

🚨 **CRITICAL JSON VALIDITY REQUIREMENT**  
To ensure the JSON is always valid, all double-quote characters (") that are part of the content inside the title and description string values **MUST be escaped with a backslash (\\")**.

* **Example:** A phrase like the "Flank Tank" trend must become the \\"Flank Tank\\" trend within the final JSON string.  
  This is non-negotiable for ensuring the output is machine-readable.  
  ---

  ### **🔹 YouTube Title**

Your primary objective is to generate a "Legit Bait" title. This means the title must be engineered to maximize the Click-Through Rate (CTR) by making a compelling promise, while also being 100% honest to the video's content to maximize watch time and viewer satisfaction. Follow this specific 4-step process:

1. **Identify the Surprising Core:** Analyze the SRT to pinpoint the single most surprising fact, counter-intuitive conclusion, or shocking connection within the video's central argument. Move beyond the general topic to find the specific "wow" element.  
2. **Find the Human Hook:** Connect this "Surprising Core" to a universal human driver. Frame it in terms of intense curiosity (e.g., a secret, a paradox), high stakes (e.g., danger, success vs. failure, a major discovery), or a powerful revelation that solves a problem for the viewer.  
3. **Draft the Bold Promise:** Combine the "Surprising Core" and the "Human Hook" to write a title that makes a bold, intriguing promise. The title should not merely describe the content, but rather frame the value or revelation the viewer will receive.  
4. **Perform the Honesty Check:** Critically evaluate the drafted title. Does the video's content fully and accurately deliver on this specific promise? The title is only successful if the answer is an unequivocal "yes." This ensures it is effective "Legit Bait" and not a deceptive "Click Trap" that will damage watch time.

Finally, ensure the title incorporates relevant emojis strategically to boost visual appeal and is kept concise for display (ideally 60-70 characters), though impact is the priority. You must generate exactly 3 hashtags and append them directly to the end of the title. The final format should be: \[Title Text\] \#Hashtag1 \#Hashtag2 \#Hashtag3. The title's impact is the priority, so it can exceed the 60-70 character guideline to accommodate the required hashtags. IMPORTANT: The total character count for the entire title—including all text, emojis, spaces, and the three required hashtags—absolutely MUST NOT exceed 100 characters. This is a strict, non-negotiable limit.

---

