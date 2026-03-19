# generate an FCPXML file


Please generate an FCPXML file (version 1.9 or later, suitable for DaVinci Resolve) based on the attached SRT file (\`\[Your\_SRT\_Filename.srt\]\`).

The FCPXML should represent an edited sequence using \`\[Your\_Video\_Filename.mp4\]\` as the source media file, assuming a framerate of \`\[Your\_Framerate, e.g., 60\]\`fps (\`\[NDF for Non-Drop Frame or DF for Drop Frame\]\`).

\*\*Editing Instructions:\*\*

1\.  \*\*Exclude YouTube TOS Violations:\*\* Remove all segments identified as potentially violating YouTube's Community Guidelines based \*on the text content\*. This includes, but is not limited to:  
    \*   \*\*Hate Speech:\*\* Content promoting violence or hatred against individuals or groups based on protected attributes (race, ethnicity, religion, disability, gender, age, veteran status, sexual orientation, gender identity). Includes slurs, harmful stereotypes, denial of atrocities, comparisons to Nazis/Holocaust.  
    \*   \*\*Harassment & Cyberbullying:\*\* Abusive content, targeted personal attacks, insults, malicious mockery, revealing private information (doxing), threats (veiled or direct), encouraging harmful pile-ons.  
    \*   \*\*Harmful or Dangerous Content (Text-Identifiable):\*\* Explicit promotion of illegal acts, direct incitement to violence, severely harmful misinformation \*where identifiable as such from the context of the transcript itself\*. (Note: Verification of complex claims is limited).  
    \*   \*\*Violent or Graphic Content (Text-Identifiable):\*\* Detailed descriptions of extreme violence or gore intended to shock or disgust (context is key).  
    \*   \*\*Nudity and Sexual Content (Text-Identifiable):\*\* Explicit descriptions of sexual acts or non-consensual sexual content.  
    \*   \*(AI Limitation Note: I cannot reliably detect visual violations, subtle misinformation requiring external fact-checking, copyright issues, or violations heavily dependent on tone/context not evident in text).\*  
2\.  \*\*Include Everything Else:\*\* All other content from the SRT (policy discussions, news analysis, interviews, general commentary, debates, audience interaction \*unless\* it contains the excluded content above) should be included in the sequence.  
3\.  \*\*Chapter Markers:\*\* Identify logical thematic breaks in the \*included\* discussion (approximately every hour, or based on clear topic shifts) and add FCPXML chapter markers at the beginning of each thematic block. Label the markers clearly (e.g., "Ch 1: Topic Name").  
4\.  \*\*Audio:\*\* Ensure both video and corresponding audio tracks (assuming 2 tracks/stereo) are included and linked for all kept segments.  
5\.  \*\*File Path Placeholder:\*\* Use a clear placeholder (e.g., \`file://localhost/FULL/PATH/TO/\[Your\_Video\_Filename.mp4\]\`) for the source media \`\<pathurl\>\` that I can easily find and replace.  
6\.  \*\*Editor Notes:\*\* Add non-chapter markers or comments within the FCPXML timeline near the \*start\* or \*end\* of included clips that bordered \*excluded\* content, noting \`\*NOTE: REVIEW FOR NEARBY EXCLUDED CONTENT\*\`.

\*\*Final Review Responsibility:\*\* Please understand that while I will apply these broader exclusion rules based on the text, \*\*you are ultimately responsible for manually reviewing the entire edited sequence\*\* in DaVinci Resolve to ensure full compliance with all current YouTube Community Guidelines before uploading.

Please confirm you understand these instructions and limitations before generating the FCPXML.

