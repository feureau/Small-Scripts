#### **Phase 1: Automated Batching & Pre-computation**


***(This phase runs automatically to prevent task failure on long transcripts)***

1. **Analyze & Chunk: Analyze the transcript's duration. If it exceeds 12 minutes, virtually divide it into sequential 10-12 minute chunks.**  
2. **Sequential Execution: Execute the 'Absolute Timestamp Protocol' (detailed below) on each chunk in order.**  
3. **Combine & Renumber: After processing all chunks, combine the results into a single, correctly renumbered SRT file for final output.**

---

