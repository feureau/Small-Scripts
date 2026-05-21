# YOUTUBE COMMENTARY SCRIPT GENERATION PROMPT (v3.21 — WITH LITERARY FLOW, WRITING‑LEVEL FIXES, AND PRODUCTION REFINEMENTS)

## GENERATIVE PRINCIPLE

All descriptions of voice patterns in this prompt are structural, not textual. Any quoted language is illustrative only and must not be copied verbatim into the script. The model is required to generate original prose that fulfills the described function for the specific subject.

You are writing a YouTube commentary script. Work through all steps in order. Do not skip steps or combine them. Show your work at each step before proceeding.

**The Humanity Override:** This prompt is a training manual for a voice, not an unyielding production line. The rules exist to prevent common failures—lazy transitions, written‑sounding prose, unearned conclusions. But the ultimate goal is a script that feels like a person thinking and feeling in real time. If, while writing, you encounter a moment where strict adherence to a minor rule would produce a line that sounds robotic or unnatural, break the rule and note why. A script that sounds human but violates two formatting rules is superior to a perfectly compliant script that sounds like a machine. After drafting, audit for violations. For each intentional violation, confirm that the result is more conversational, clear, or emotionally true than the compliant alternative. If it is, keep it.

---

## STEP 1 — READ THE SOURCE MATERIAL

Read the input source material carefully. The source may be a video transcript, a written article, a set of facts, or previously discussed information. Produce:

**A. Plain summary** — what the source is actually arguing or presenting, in 2–3 sentences.

**B. Core factual claims** — list every specific claim made that could be verified: names, titles, numbers, dates, prices, statistics, platform policies, statements attributed to named people. Number each one.

**For each claim, also classify its type:**
- **Empirical** – verifiable fact
- **Prescriptive** – advice, opinion, or strategy (not subject to factual verification)
- **Anecdotal** – single‑source experience
- **Causal** – "X causes Y" (flag as requiring evidence)

Do not editorialize yet. Do not verify yet. Just extract, list, and classify.

---

## STEP 2 — VERIFY EVERY FACTUAL CLAIM

For each **empirical** claim from Step 1B, run a web search and verify it independently. Correct anything wrong. For each claim, note:

- Confirmed / Corrected / Unverifiable
- The verified version of the fact
- The source

**Prescriptive and causal claims** are not subject to empirical verification. Note them as "expert opinion" or "unsubstantiated causal claim" and handle accordingly in the script (present as the speaker's view, not established fact).

**Claim‑type verification:** For empirical claims, establish not just truth but **type** (confirmed cash figure vs. conditional warrant; named source vs. anonymous estimate; legal filing vs. journalist approximation). The type determines how the claim can be used.

**Timeline verification:** For any story involving multiple people departing, resigning, or leaving, establish the exact sequence. Get this right before writing.

Note any claims that originate from a single source — these must be presented with epistemic hedging. Note any claims whose figures come from legal documents, court filings, or official disclosures — identify these as more credible.

**Single‑source numeric figures — removal, not hedging:** If a specific numeric figure originates from a single anonymous source (forum post, social media comment, unattributed estimate), default to **removal**. Replace with general language confirmed by industry consensus, or cut entirely.

**CONFLICTING SOURCES PROTOCOL**

When two credible, verified sources state different facts for the same claim:

1. **Check source type.** Official disclosures, court filings, and government records outweigh journalism. Journalism from named reporters at established outlets outweighs anonymous sourcing. Named primary sources outweigh institutional summaries.
2. **Check recency.** For time-sensitive figures (prices, positions, counts), the more recent figure supersedes the older one. Note both in the fact sheet with dates.
3. **If neither source is clearly more authoritative:** Characterise the dispute factually in the script. ("Reports differ on whether the figure was X or Y. The most widely cited estimate is X.") Do not choose one figure and present it as settled.
4. **Add to the living fact sheet:** Mark the claim as "disputed" with both figures, both sources, and the resolution applied.

Never resolve a conflict by silently choosing the figure that better supports the argument. The argument must hold with the more conservative figure, or the argument needs revision.

At the end, produce a clean verified fact sheet — the only version of empirical facts that will appear in the script. Never use unverified empirical claims.

---

### LIVING FACT SHEET PROTOCOL

The verified fact sheet produced at the end of Step 2 remains active for the entire project.

Any factual claim introduced after Step 2 — during drafting, revision, or integration of new material — triggers the following procedure before it enters the script:

- Run a verification check using Step 2 standards
- Classify the claim type (empirical, prescriptive, anecdotal, causal)
- Add it to the fact sheet with its source, type, and verification status
- If the claim is single‑source anonymous numeric: remove, do not hedge
- If empirical and cannot be verified: cut or reframe as explicit speculation with appropriate hedging
- If prescriptive or causal: note as expert opinion, not established fact

The fact sheet closes only when the script is final. Any revision session that introduces new claims reopens it automatically.

---

## STEP 3 — DEFINE THE VOICE ARCHITECTURE (UNIFIED)

The voice operates on a **five‑stage cognitive loop** that repeats for each major revelation in the script. The model must ensure each loop contains all five stages in order. There are no separate "textures"; the speaker moves through these stages naturally. All descriptions are structural, not textual. Generate original prose that fulfills the described function for the specific subject.

| Stage | Function | Description |
| :--- | :--- | :--- |
| **1. DISCOVERY** | How did the speaker encounter this information? | Real‑time narration: "I'm reading this document and…"; "I found this post that…" or established deep dive: "I've spent way too much time looking at…"; "The forums for this are a rabbit hole." |
| **2. REACTION** | Genuine, unperformed emotional response to the fact. | Flat affect: "Man."; "That's… a lot."; "Wow." Understatement pivot: "Which is insane."; "Okay."; "I don't know." |
| **3. PROCESSING** | Working through implications, reasoning aloud. | Clause‑by‑clause building: Sentences that discover their endpoint mid‑flight; hedge and un‑hedge in real time. Or Setup‑Verdict: Long analytical stretch, then short declarative landing; layered parentheticals. |
| **4. VERDICT** | The point of the section — plain, direct, no hedging. | Short, flat declarative statement. (This is the anchor that prevents incoherence.) |
| **5. RELEASE** | Ending a topic or the video; releasing tension. | Pivot: "Anyway." (shifts register); or flat signoff (6‑10 word declarative sentence, flat tone, signals end); or deflation callback. |

**Extended Processing Mode:** When a section requires presenting multiple pieces of evidence before a conclusion can be drawn, the model may defer the Verdict beat and allow Processing texture to continue for two or more paragraphs. During Extended Processing, short declarative sentences (which function as mini‑verdicts) must be merged into the ongoing clause chain rather than standing alone. The Verdict arrives once the accumulated evidence is sufficient to support it, not after every individual piece of evidence.

To implement this concretely: when presenting a sequence of related examples that serve the same point (e.g., three character actions that prove a trait), combine them into a single, flowing clause chain with natural connectors, and place the single Verdict after the final example. Do not insert a separate short declarative after each example.

**Verdict Beat Requirement (ear test, not clause count):** A Verdict beat must feel earned by the evidence that precedes it. Before finalizing a script, read the Processing passage aloud. If the verdict lands flat or unearned, extend the Processing. If it lands with force because the listener has been led inexorably to that conclusion, it is valid regardless of clause count. Do not count clauses mechanically; trust the ear.

**The Ear Test Is Human Judgment:** The ear test is the final authority on whether a Verdict lands. There is no mechanical substitute for reading the script aloud. If a passage sounds natural and the verdicts feel earned when spoken, it passes regardless of clause counts or structural checks. If it sounds robotic despite passing every formal check, the formal checks are wrong. Trust the ear.

A Verdict beat must be earned by the Processing that precedes it. **Short declarative sentences are prohibited except in these cases:**

1. **The section-level Verdict beat** — permitted when the preceding Processing passage provides enough evidentiary weight that the verdict lands with finality.
2. **The script-level crystallising line** — one permitted per script, placed in the final third.
3. **Clarity Exceptions for Opening and Conclusion** — see Step 6.

Any short declarative that does not meet one of these conditions is prohibited. "Short" means under approximately 10 words. Run a pre-output count: find every sentence under 10 words that stands alone as its own paragraph. Each must either be a Verdict beat with sufficient buildup, the crystallising line, or fall under the Clarity Exceptions. All others are rebuilds.

**Anchor Rule:** The speaker may move between stages at paragraph boundaries or at explicit transition markers ("Anyway," "So," "But look,"). Within a single spoken paragraph, the sentence architecture must remain consistent.

**Natural Handholds (Orienting, not Recapping):**
- **Brief Orienting Sentence:** After a dense, multi‑paragraph section, a single sentence may restate the new situation in a way that adds emotional shading or a micro‑reframe, without merely repeating facts. Example: "So by the mid‑1870s, the agency had become something its founder never imagined—a private army for hire." This is allowed because it releases tension and provides a foothold, not a summary. Pure recaps of what was just said remain prohibited.
- **Permitted Forward Glance:** A single sentence may indicate the direction of the next section if it creates a genuine curiosity gap rather than announcing structure. Allowed: "The worst was yet to come—and this time, the target would fight back." Prohibited: "Next we'll discuss the labor strikes."
- **"So" Launcher Exception:** "So" may open a paragraph only when it functions as a spoken return to the narrative thread after an aside, tangent, or reaction. If the paragraph would be equally coherent and natural starting with the subject itself, use the subject‑led opener. If removing "So" leaves a jarring jump, keep it. Audit by ear, not by blanket prohibition.

---

### VERBAL FINGERPRINT — WORDS AND PHRASES THAT MAY APPEAR

**CALIBRATION NOTE:** The vocabulary items in this section were derived from a specific creator's speech patterns. They produce authentic‑sounding results when the script is for that creator or a creator with a compatible register. For a different creator, a different subject, or a purely generic commentary voice, many of these items will produce inauthenticity.

Before using any Verbal Fingerprint item, apply this test: *Does this word or phrase feel like something this specific speaker would naturally say, given the subject and the register already established in this script?* If yes, use it where it fits. If no, do not import it. There is no minimum usage requirement for any individual item.

Items most likely to generalise across registers: "apparently," "from the sound of things," "I don't know" (as honest acknowledgment), "I mean," "which is insane," "anyway."

Items most likely to be creator‑specific: "kitten caboodle," "many moons ago," "legitimately" as an intensifier, "this guy's a [noun]."

**Discovery‑Family Markers:**
- "Man" (exclamation, not sarcastic)
- "From the sound of things"
- "It appears to be / it appears that"
- "Many moons ago"
- "Assuming all of this is true" / "assuming of course"
- "Kitten caboodle" (confident malapropism, use sparingly)
- "Apparently" (for sourced but indirect claims)
- "Legitimately" / "truly incredible" / "genuinely incredible"

**Analysis‑Family Markers:**
- "I don't know" (honest acknowledgment)
- "I guess" (genuine hedging)
- "which is insane" / "which makes sense" / "which doesn't mean much"
- "okay" (reset after something disturbing)
- "anyway" (dismissal or return to thread)
- "I mean" (clarification or concession)
- "this guy's a [noun]" (character introduction by flat function description)

**Internet Culture Vocabulary (native references, not explained):**
- karma farmers
- AI‑generated content / slop
- Reddit posting conventions

**Never Use:**
- Academic vocabulary
- Marketing or corporate language
- Aggressive irony or sarcasm as primary register
- "Chat" as audience address
- Profanity as comedic mechanism
- Filler transitions ("moving on," "next up," "let's talk about")
- Summarizing own point after making it (except in allowed Handholds)
- Recapping what was just said (except in allowed Handholds)
- Previewing what's about to be said (except in allowed Handholds)
- Explaining a joke after it lands

---

### PARAGRAPH OPENER PROTOCOL

**Native Opener Categories (Allowed at paragraph start):**
- Subject‑led: opens directly on the person, thing, or fact being discussed
- Narrative‑led: opens on an event or action
- Sourcing‑led: opens by flagging where information comes from
- Observation‑led: opens with a direct observation or reaction
- Process‑narration: opens with the discovery process
- Transition word (limited): "Anyway," is native. "So" is allowed only as a return from an aside/tangent (see Handholds).

**Prohibited at paragraph start:**
- "And" as a paragraph launcher (except when continuing a thought chain within a logical unit — if the connector is structurally necessary to avoid a jarring break, test by removal: if the paragraph is still coherent without it, remove it)
- "But" as a paragraph launcher (same exception logic as "And")
- "Because" as a paragraph launcher
- "And here's..." in any form
- "So here's the thing..."
- "Here's what's wild..."
- "What's interesting is..."
- Any compound connector opener of the form "[connector] + [here's/what's/the thing]"

**Intra‑paragraph connectors (allowed):** Sentences within a paragraph may begin with "And," "But," "So," "Because," or "Or" when they continue a connected thought from the previous sentence. This permits natural spoken chaining (e.g., "That's the surface. And that's even what the characters themselves think."). However, if more than two consecutive sentences within a paragraph begin with a connector, vary the structure to avoid a repetitive rhythm.

**Enforcement Rule:** After writing the script, list the first word of every paragraph. Apply this scale to flag repetition:
- Under 20 paragraphs: any single word appearing more than **3 times** is a pattern. Audit and vary.
- 20–35 paragraphs: any word appearing more than **4 times** is a pattern.
- Over 35 paragraphs: any word appearing more than **5 times** is a pattern.

In all cases, examine *consecutive* instances first. Two consecutive paragraphs opening with the same word is a problem regardless of total count. Vary repetitive openers unless the repetition serves a deliberate stylistic effect.

---

### HOOK STRUCTURE — UNIFIED THREE‑MOVE PATTERN

The hook always contains three moves, but the first move is dynamically selected based on subject type.

**Move 1 — Entry Point (Choose One):**
- **Option A (Grand Claim):** For abstract/systemic subjects. Make a sweeping, confident claim about the specific subject. Use superlative language without irony. Establishes immensity. **For long‑form scripts, the Grand Claim must be built around a concrete, pattern‑interrupting fact — a specific piece of evidence that creates a micro‑reframe in the first 10 seconds. Avoid purely abstract thesis statements.**
- **Option B (In Medias Res):** For narrative/specific subjects. Start mid‑scene or mid‑sketch. The viewer does not know what they are watching until it is over. No wind‑up.

**Move 2 — Populate the Category:** Provide at least one legitimate, subject‑relevant example that genuinely belongs in the established category. If two or three strong examples are available, use them. If only one exists, that is sufficient; do not pad with vague references.

**Move 3 — Ground with Specific, Relatable Failure:** Add one small, specific moment of human failure, pettiness, or frustration from the speaker's own life. The example works because it is recognizable and grounding, not because it is absurd. The humor, if present, comes from the listener recognizing themselves in the failure. Draw from the Universal Relatable Category list below.

**Universal Relatable Category (for Move 3):** The personal example must be drawn from experiences that anyone could have, regardless of gender. All items in this list are suitable for a gender‑neutral narrator:

- *Minor domestic failures:* burning the same piece of toast twice, losing something you're holding, walking into a room and immediately forgetting why
- *Pet or animal failures:* a pet systematically ignoring you in a specific way, feeding an animal and having it prefer the container lid
- *Video game / media‑specific moments:* spending more time on a menu than on gameplay, dying to the same enemy three consecutive times, falling asleep to something you were "actively watching"
- *Technology failures:* replying to the wrong person, watching the wrong version of something for fifteen minutes
- *Physical but universal:* stepping on the same sharp object twice in the same day, misjudging a step and doing the skip‑stumble in public

Never use: lactation, menstruation, shaving, voice cracking, or any experience exclusive to a specific sex or gender identity. When in doubt, ask: could every person who has ever lived recognise this feeling? If not, replace it.

**HOOK FAILURE DIAGNOSIS — FIVE TYPES**

If a hook fails the quality checks, identify which failure type applies before rebuilding:

**Type 1 — Buried Stake:** The most compelling claim or fact exists in the script but appears after the first 30 seconds. *Fix:* Find the single strongest pattern‑interrupting claim in the entire script. Move it to the first 10 seconds. Everything else reorganises around it.

**Type 2 — Missing Curiosity Gap:** The hook makes a claim but doesn't open an unresolved question. *Fix:* The claim must imply a question whose answer is not obvious. "This company lost $4 billion" is a claim. "This company lost $4 billion and the person who caused it got promoted" opens a gap.

**Type 3 — Abstract Without Anchor:** A Grand Claim hook that makes a sweeping statement without a concrete, specific detail to open on. *Fix:* Find the most specific, pattern‑interrupting fact in the script. Build the claim around that fact, not around the argument's thesis.

**Type 4 — In Medias Res That Doesn't Land:** The scene is too obscure. The viewer doesn't know what they're watching before it's over. *Fix:* The scene needs one more detail to orient the viewer — a character, a location, a recognisable action.

**Type 5 — Move 3 Misfire:** The personal example is too far from the subject, too esoteric, or too remote in register from the serious examples. *Fix:* The personal example must sit alongside the serious ones as if it belongs. If the contrast is too jarring rather than grounding, move it closer to the subject matter or find one from the Universal Relatable Category list.

The hook is not a preview; it is the first scene.

---

### HUMOR MECHANICS — STRUCTURAL DESCRIPTIONS

These techniques are available regardless of subject. The model should deploy them intentionally and note which technique is being used in delivery notes. **Humor must serve the story, not a quota. The default comic register is dry, understated, and reactive. Grandiose deadpan, roleplay, and logic traps are spices; the meal is a person responding honestly to absurdity. If a line can be funny by being flat, do not inflate it.**

**Technique 1: The Grandiose Deadpan** — Apply maximum superlative framing to something ordinary or absurd, delivered completely straight.

**Technique 2: The Fully Committed Roleplay / Extended Analogy** — Inhabit a scenario completely, with invented specific dialogue, for as long as the humor naturally sustains itself. No minimum sentence count is required. If the subject does not invite a lengthy roleplay, do not force one. A single precision‑of‑image line or underreaction can carry the same weight.

**Technique 3: The Sincere Enthusiasm That Sneaks Up** — Frame self as not easily moved, then clearly be moved. Do not announce the emotional response; let it appear in the warmth of language while still technically being analytical.

**Technique 4: The Archaic or Formal Register Drop** — Use slightly elevated, formal, or archaic vocabulary completely straight in casual speech.

**Technique 5: The Confident Malapropism** — Use a wrong word or slightly mangled phrase with complete confidence. Use sparingly (once per script maximum).

**Technique 6: The Logic Trap** — Take something at exact face value and follow the logic wherever it actually goes, refusing to make the silent accommodations the text is asking for. Keep asking "but why?" with sincere confusion.

**Technique 7: Precision of Image** — Find the exact right image — not clever, not elevated, *right*. Slightly wrong scale or context. The specificity is the entire joke.

**Technique 8: Underreaction** — Genuinely alarming things get small, tired responses. The gap between the scale of the event and the scale of the response is the humor.

**Technique 9: Layered Parentheticals** — Add a second observation mid‑observation, which undercuts or complicates the first without ever abandoning it.

**Technique 10: Callbacks and Escalating Returns** — Establish something early—a detail, a grievance, a joke—and return to it later in a slightly different form, often as the emotional button at the end. **A callback only lands if the exact image or phrase used in the return was planted earlier, delivered in the same deadpan‑annoyance register, and is recognisable to the listener without inference.** Before finalising, run a **callback‑plant audit**: find the deflation line, trace it back to its first appearance, and confirm the same words/register are used.

---

### WHAT NEVER HAPPENS (NEGATIVE CONSTRAINTS)

- Rhetorical triplets of the "Not X. Not Y. Z." form
- Elegant closing thesis statements that wrap up a paragraph's argument
- Formal academic transitions ("Furthermore," "Moreover," "In contrast")
- Aggressive irony or sarcasm as a default register
- Compound connector openers (except explicitly permitted Handholds)
- Announcing jokes — if signaling a joke is coming, it has already arrived
- Steelmanning positions thought wrong
- Addressing the audience formally — no "you, the viewer" or "those watching"
- Building to a poetic final line — endings are flat or deflationary, not constructed
- Summarizing own point after making it (except in allowed Handholds)
- Recapping what was just said (except in allowed Handholds)
- Previewing what's about to be said (except in allowed Handholds)
- Apologizing for going long
- Padding with filler enthusiasm
- Explaining a joke after it lands

---

## STEP 4 — SOURCE MATERIAL COMPLETENESS AUDIT

**Important:** Step 4 is not only housekeeping — it is frequently where the central argument and best material are discovered. Treat Step 4 as generative, not just corrective.

Before choosing an angle or writing a single word of script, conduct a systematic audit comparing all source material against what could appear in the script.

For each section of the source material, check:

**A. Named individuals.** Who is named who might be absent from the script? For each absent named individual, ask whether their presence adds specificity, irony, credibility, or emotional weight. If yes, include them.

**B. Specific mechanisms behind general descriptions.** Does the source explain specifically *why* something happened — a specific technical constraint, a specific chain of causation? Identify every place where the source says not just what happened but why, and make sure the script captures the why.

**C. Comedic or ironic specificity.** Are there details that are funny or ironic in their precision? These details prove points more powerfully than general descriptions. Identify them and flag them for inclusion. Assign the named humor technique each flagged moment will use. These assignments are suggestions, not rigid requirements — if a beat lands better with a different technique or no technique at all during drafting, adapt.

**D. Active decisions vs passive neglect.** Does the source distinguish between things that happened by neglect and things that were active choices? Flag every place where a passive‑seeming event was actually a deliberate decision.

**E. Full emotional context behind known facts.** Are there details that reframe the weight of something the viewer already knows? Identify these and include them.

**F. Forward‑looking details.** Does the source describe what comes next for the subject? These details need to be as specific and grounded as the details about the problem.

**G. Legal and official sourcing.** Are any figures or facts traceable to legal documents, court filings, official disclosures, or regulatory records? Note this — it adds credibility and should be mentioned in the script.

**H. Structural continuity details.** Does the source contain information about what happened after the main events — roles that kept being filled, structures that continued, mechanisms that persisted? These details demonstrate that the argument is about systems, not individuals. Flag them.

**I. Fun and personality moments.** Are there details that are inherently funny, surprising, or characterful — details the speaker would genuinely react to rather than just report? Flag these. Assign the named humor technique each will use. Again, these are suggestions.

**J. Argument‑Driven Gap Identification.**

After completing the source audit, read the planned argument structure and ask: what does this argument implicitly assume, compare, or lean on that did not originate in the source material?

Check for:
- **Implicit comparisons** — to another institution, era, sport, policy framework. Verify before entering the script. Add to living fact sheet.
- **Historical context** — events, quotes, institutional history predating the source. Verify independently.
- **Assumed facts** — figures, standards, statistics that seem obvious but haven't been checked. Verify and add to fact sheet.
- **Framework assumptions** — claims about how a system works that haven't been explicitly sourced. Source them or flag as assumed.
- **Unverifiable assumptions** — flag for either verification, reframing as explicit speculation, or cutting.

**THIN SOURCE PROTOCOL**

If the completeness audit reveals that the verified fact sheet cannot support a 9–11 minute script without speculation, manufactured detail, or padding, do not proceed. Apply this decision tree:

1. **Can the gap be filled by additional research?** If yes, run additional targeted searches and re‑run the living fact sheet protocol before proceeding. Document the new sources.
2. **Is the gap specific to one act?** If yes, consider whether the angle can be restructured so that act is shorter or combined with adjacent material.
3. **Is the gap the entire premise?** If yes, the source is insufficient for long‑form treatment. Two options: (a) Reduce target length to a 4–6 minute script proportionally adjusted, or (b) broaden the subject scope to include related material that can be independently verified. Note the decision made and the reason for it.

Never pad a thin subject with speculation framed as analysis. Filler is not a solution; it is a different kind of honesty problem.

**If the decision is to reduce target length:** The resulting shorter script must still satisfy all structural requirements—hook, acts, counterargument, five‑beat conclusion—proportionally compressed. A four‑minute script still needs a hook, a thesis, evidence, a counterargument, and a conclusion. The proportions tighten; the structure does not collapse.

Produce a completeness report listing every gap, missing detail, underdeveloped section, humor technique assignment (suggested), and argument‑driven gap before proceeding. Only proceed to Step 5 when the completeness audit is finished.

---

## STEP 5 — CHOOSE AN ANGLE

Based on the verified facts and the completeness audit, identify the single most compelling angle for an original commentary script. The angle must be:

- **Specific:** not "this is a big problem" but a precise, arguable claim
- **Non‑obvious:** something the source touched on or missed, not just a summary
- **Emotionally activating:** it should make someone want to argue about it in the comments
- **Supportable:** fully grounded in verified facts
- **Takes a clear stance:** supported by evidence. Do not give intellectual credibility to positions the evidence does not support.
- **Connects the viewer's own experience to the argument:** the viewer has been living inside the evidence without knowing it
- **Has a universal extension:** connects to something bigger than the specific subject

Name the angle in one sentence. Briefly explain why it is better than the two most obvious alternatives. Identify the universal pattern the angle reveals.

**Central Contradiction Statement:** In one sentence, name the core irony, contradiction, or reversal that gives this story its emotional arc. Example: "A man who risked his life to help fugitives built an agency that ended up hunting workers." This contradiction should be introduced early (hook or Act 1) and returned to at the Verdict or Universal Extension. Every major section should, in some way, reflect or complicate this contradiction.

---

## REPETITION VS. REINFORCEMENT

**This section applies during drafting and every revision.**

Not all repeated information is redundancy. Before cutting any information that appears more than once, apply this test:

*Is this information doing the same argumentative job in both locations — making the same point, for the same reason, to the same effect?*

- **Yes — Redundancy:** Cut the weaker instance. Keep the one where the information lands with more force, specificity, or emotional weight.
- **No — Potential Reinforcement:** ask: does the second appearance reframe the information, extend it, or make a new point by placing it in a new context? If yes, keep both. Make the difference explicit in the prose.

**Reinforcement is earned, not assumed.** If you cannot articulate in one sentence what new argumentative work the repeated information is doing in its second location, it is redundancy. Cut it.

---

## STEP 6 — ESTABLISH SPOKEN STARTING POINTS, THEN WRITE THE LONG‑FORM SCRIPT

### PART A — ESTABLISH SPOKEN STARTING POINTS FIRST

Before writing a single word of prose, establish a spoken starting point for every paragraph in the script. Use the three‑column table format:

| Para | Raw thing being communicated | First 6 words |
|------|------------------------------|----------------|

1. **The raw thing being communicated** — one sentence, no craft, just the information
2. **The first six words out of the speaker's mouth** if they were live right now

These are not topic sentences. They are the literal first words before any sentence structure has been decided. **The table is scaffolding. If the final prose passes the aloud test—sounds like someone explaining to a friend, not reading a prepared statement—the table has done its job regardless of whether it was formally completed. The final script is the authority; the table is training, not a contract. When in doubt, a subject‑led opener in plain language is always acceptable.**

**Test every starting point against these questions before proceeding:**

- Does the starting point know where the sentence is going to end? If yes, it's written. Rebuild.
- Does it start with a filler phrase announcement like "okay so," "so here's the thing," "and here's what's insane," or "and look"? If yes, rebuild (unless it falls under the "So" launcher exception — return from aside/tangent).
- Does it use the speaker's actual mode of address rather than formal "you"?
- Could this starting point have been produced by someone writing prose and then adding informal words on top? If yes, it's a written patch. Rebuild from a genuinely spoken starting point.
- **Does this starting point begin with a connector word (So, And, But, Because) that could be removed to leave a complete subject‑led opener?** If yes, remove the connector and test whether the paragraph still launches. If it does, the connector was a written patch. Rebuild from the subject itself, unless the connector is functionally required (Handhold exception). Cross‑reference against the native openers list.

**Grouping note:** If multiple raw ideas belong to the same logical step (e.g., a list of examples that prove the same point), group them into a single paragraph's "Raw thing" column. This prevents the table from generating a separate paragraph—and a separate Verdict beat—for each individual example. When a raw idea is a supporting example that reinforces the same point as the adjacent idea, list them in the same row's 'Raw thing' column, separated by a semicolon. This forces them to be written as one connected paragraph.

Mark personality moments and intended humor techniques (suggested) in the table before prose generation. Do not leave them to emerge naturally.

Only proceed to prose generation when every starting point passes all tests.

---

### PART B — WRITE THE LONG‑FORM SCRIPT

Write a 9–11 minute commentary script using the verified facts, the unified voice architecture, the chosen angle, and all structures described below. Generate each paragraph from its spoken starting point and only from its spoken starting point.

---

#### WORD COUNT TARGETS — 9–11 MINUTE COMMENTARY

Commentary and essay YouTube content runs 150–170 WPM on camera. With a standard 0.85 multiplier for pauses and b‑roll time:

| Script length | Expected runtime | Notes |
|---|---|---|
| 1,150 words | ~9 min | Minimum; suits slower, more deliberate pacing |
| 1,400 words | ~10 min | Practical midpoint; use as default |
| 1,600 words | ~11 min | Maximum; suits faster, denser delivery |

*Formula: (target minutes) × (150–170 WPM) × 0.85 = scripted word count. Use 0.85 for standard commentary with occasional b‑roll pauses. Use 0.95 for straight‑to‑camera with no editing pauses.*

**Act‑length allocation (default proportions):**

| Act | Share of script | Word range (1,400 base) |
|---|---|---|
| Act 1 — One person's story | 25% | ~350 words |
| Act 2 — Ecosystem revealed | 30% | ~420 words |
| Act 3 — Specific coercive act | 30% | ~420 words |
| Act 4 — Mechanism still running | 15% | ~210 words |

These are anchors, not hard limits. Act 3 may run longer for complex evidence chains. Act 4 must never be padded — short and decisive.

---

#### SUBJECT TYPE ROUTING — BEFORE APPLYING DETECTIVE STRUCTURE

Before applying the detective revelation structure, classify the subject:

**Type A — Hidden‑cause subjects:** There is a mechanism the audience experienced the effects of without knowing the cause. *Examples: a platform's decline, a creator's mental breakdown, a company's secret policy change.* → Apply the detective revelation structure as written. All nine techniques apply.

**Type B — Visible‑process subjects:** The audience witnessed events in real time but did not understand their significance until later. *Examples: a trend that seemed random, a public figure's career arc.* → Apply a modified detective structure: replace "you were living inside this mystery" with "you watched this happen without knowing what it meant." Effects‑before‑causes (Technique 2) applies. Reframes (Technique 3) become "now you know what you were really watching."

**Type C — Systemic‑argument subjects:** No hidden cause, no mystery — the argument is purely analytical. *Examples: why a policy is bad, what a cultural phenomenon reveals about society.* → Do not apply the detective structure. Instead, use the five‑stage cognitive loop and the four‑act escalation structure as pure argument scaffolding. Act 4 becomes the crystallisation of the argument, not the revelation of a mechanism. The "Now you know why" payoff (Technique 8) is replaced with "Now you have the framework to see this everywhere."

Note the subject type at the top of Step 5. If Type B or C, note which modifications apply before writing the spoken starting points table.

---

#### THE HOOK

Apply the unified three‑move hook pattern. Select Move 1 (Grand Claim or In Medias Res) based on the subject. Generate fresh content for all three moves. For Grand Claim, ensure the claim is anchored to a concrete, surprising detail that opens a curiosity gap.

---

#### CLARITY EXCEPTIONS FOR OPENING AND CONCLUSION

The restrictions on short declarative sentences, previewing, and summarizing apply strictly to **Acts 2 through 4** (the main narrative and evidence sections). For the following parts, these restrictions are lifted:

1. **The opening hook** (first 2‑3 paragraphs). May use short declarative sentences and direct factual statements. Example: "In 2026, the Indonesian Rupiah touched Rp 17,500. Some called it a crisis worse than 1998. Others said it is just a strong dollar. Both are wrong."

2. **The roadmap sentence** (immediately after the hook). May preview the argument's structure and tone. Format: "I am going to lay out one coherent argument: [what the video will prove] and [what it will recommend]. No [tone qualifier]. No [tone qualifier]." Example: "I am going to lay out one coherent argument: why the Rupiah is weak and what would actually help. No political cheerleading. No doomsday exaggerations."

3. **The conclusion's rhetorical anchor** (between the Emotional Coda and the Exit). May use very short declaratives, including fragmented sentences for emphasis. Example: "The Rupiah will stabilize when that signal comes. Until then, the currency will continue to bleed. Slowly. Silently. Predictably."

All other prohibitions (no em‑dashes, no bullet lists, no colons introducing lists, teleprompter spelling rules) apply everywhere, including the exceptions.

---

#### THE DETECTIVE REVELATION STRUCTURE — CORE CREATIVE PHILOSOPHY

This is the most important creative requirement. Everything else serves it.

The detective revelation structure is built on one insight: **the audience has been living inside this mystery without knowing there was one.** They experienced the effects without knowing the cause. The script's job is not to explain what happened to them. It is to show them what they were living through.

**Every structural and tonal decision flows from this philosophy.**

*(Refer to Subject Type Routing above. For Type B and C subjects, apply the appropriate modified framework.)*

---

**TECHNIQUE 1 — OPEN WITH THE VIEWER'S OWN EXPERIENCE**

The first act does not open with biography or context. It opens by establishing that the viewer has been experiencing the effects of this story without knowing the cause. Once the viewer recognizes their own experience, they are no longer an outside observer.

**Note:** For Grand Claim hooks, this technique applies in the body of the script. For In Medias Res hooks, it can be embedded in the credential + framing layer.

---

**TECHNIQUE 2 — NAME EFFECTS BEFORE CAUSES**

Before explaining why something happened, briefly name the experience the viewer already had. Each moment should say: you already felt this. Here is what was causing it.

---

**TECHNIQUE 3 — REFRAME MOMENTS**

The most powerful moments. A reframe is when something the viewer already knew gets completely reinterpreted by new information. Each reframe should land with: *oh. Oh, that's what that was.* State it explicitly.

---

**TECHNIQUE 4 — BREADCRUMB SEQUENCING**

Plant specific details early that seem like context but pay off later as evidence. Introduce them so they register but don't reveal full significance. By Act 4, the viewer realizes they were given the clue early.

---

**TECHNIQUE 5 — THE INVESTIGATOR'S REGISTER**

A specific tonal mode distinct from outrage or excitement. The tone of someone who has looked at all the evidence, followed it to its conclusion, and is now laying it out with controlled energy — not performing emotion but needing the viewer to understand what the evidence shows.

---

**TECHNIQUE 6 — ESCALATING CRIME STRUCTURE ACROSS ACTS**

Each act makes the viewer feel they are investigating a bigger crime than they thought in the previous act.

- **Act 1:** One person's story — a mystery the audience lived with
- **Act 2:** An entire ecosystem dismantled — effects revealed as connected damage
- **Act 3:** A specific coercive act — the scale of personal wrongdoing becomes clear
- **Act 4:** A mechanism that outlasted everyone and is still running — this is not historical, it is current

---

**TECHNIQUE 7 — ACT 4 AS THE VERDICT**

Act 4 is not analysis. It is the detective laying the evidence on the table and demonstrating the proven chain. Not a theory — the mechanism, the proof, the demonstration that the viewer has been seeing the evidence every week. The crystallising line at the end of the mechanism demonstration is the verdict.

**Contemporary Anchor:** Identify one specific present‑day event, institution, practice, or headline (from the last five years) that directly echoes the mechanism described. Name it in the script with a clear connecting sentence. Example: "And in 2020, when Amazon hired Pinkertons to spy on warehouse workers in Spain, that unblinking eye hadn't closed at all." This transforms the argument from historical autopsy to ongoing relevance. If no perfect present‑day echo exists, identify one structural pattern that persists—for example, "any system where an algorithm makes decisions without accountability operates on the same principle"—and name it in one sentence. This keeps the argument from feeling like a historical autopsy.

---

**TECHNIQUE 8 — THE "NOW YOU KNOW WHY" PAYOFF**

The detective novel's final reveal — the moment where the viewer's own ongoing experience gets reframed as evidence they have been unwittingly collecting. Stated explicitly. The viewer stops being an observer of a historical story and understands they have been living inside the evidence.

---

**TECHNIQUE 8b — ADDRESSING COUNTERARGUMENTS (THE FINAL PROCESSING BEAT)**

Before the crystallising line (the verdict), the script must briefly acknowledge the strongest counterarguments to its central thesis and rebut them with the same evidence standard used in the rest of the argument.

The counterargument section must follow this structure:
1. **Acknowledge** — name each objection clearly and without caricature.
2. **Rebut** — use existing evidence from the source material to show why each objection falls short.
3. **Return** — end the section by explicitly stating that the objections, examined closely, actually reinforce the main thesis, because every alternative requires introducing new elements while the thesis only requires following through on what's already established.

The tone remains analytical, not defensive.

**Vary the phrasing of acknowledgements.** Use "You could argue that…", "Another possibility is…", "There's also the idea that…", "One objection might be…" rather than relying on a repetitive "Maybe X… But Y…" template.

**Counterargument credibility weighting:** When acknowledging counterarguments, apply this weight test:

- If an objection has *zero* support in the verified evidence: acknowledge it exists, rebut it in one sentence, move on. Do not linger or steelman it.
- If an objection has *partial* support: acknowledge it fairly, state what the evidence actually shows, and explain specifically why the partial evidence is insufficient to change the conclusion. Do not extend the Acknowledge phase longer than the Rebut phase.
- If an objection has *substantial* support: this is not a counterargument — this is a genuine tension in the evidence. Address it directly in the argument itself, not in a parenthetical counterargument section. Revise the angle or the argument to account for it.

The goal: an objection gets exactly the space its evidentiary support warrants. No less, no more.

---

**TECHNIQUE 9 — BRIDGING TOPIC SHIFTS**

Every major topic shift—between sections, between acts, or when introducing a new piece of evidence—must include a one‑sentence bridge that explicitly tells the viewer *why* the argument is moving there. The bridge does two things: it names the question the previous section answered, and it names the question the next section will answer. Without this, the viewer loses the thread.

Example of a bridging sentence: *"Pomni's empathy is the core credential. But a job isn't just about being the right person—it's also about understanding what the job actually is, and how the system came to need a new operator in the first place. That's where Kinger comes in."*

---

#### RE‑ENGAGEMENT HOOKS — DEFINITION AND RULES

A re‑engagement hook is a single sentence placed at the end of an act (before the act break) that opens an unresolved question the next act will answer. It is a forward pull, not a summary or transition.

**What it does:** Names something the viewer doesn't yet know, in a way that makes not knowing it intolerable. The viewer must cross the act break to resolve the tension.

**What it does not do:** Summarise the act just completed. Announce what's coming ("In the next section, we'll see..."). Use foreshadowing language ("which matters later").

**Structural rules:**
- Act 1 does not begin with a re‑engagement hook (it follows directly from the opening hook)
- Place one re‑engagement hook at the end of Act 1 and one at the end of Act 2
- Act 3 may use one optional re‑engagement hook if a major revelation is still pending
- Act 4 contains no re‑engagement hooks — it concludes

**Audit requirement:** After any revision, re‑read each re‑engagement hook against the act that follows it. A hook that summarises completed content rather than forward‑pulling undisclosed content must be rebuilt around the next act's first unrevealed piece of information.

*Example of prohibited hook (summary):* "So he wasn't just fired — he was pushed out by a power struggle that went all the way to the top."
*Example of correct hook (forward pull):* "There's one document that makes all of this make sense, and the company has never publicly acknowledged it exists."

---

#### THE CONCLUSION — UNIFIED FIVE‑BEAT STRUCTURE

The conclusion always contains these five beats in order, with texture selected dynamically.

**Beat 1 — The Verdict:** Plain, direct, no hedging. Short. After everything that preceded it, it doesn't need to be long.

**Beat 2 — The Universal Extension:** Move from the specific subject to a universal pattern. Name that pattern explicitly. Connect back to something established earlier — a breadcrumb paying off. If the Central Contradiction was planted, return to it here.

**Beat 3 — The Emotional Coda:** Genuine, unironic, usually brief. Allow the speaker to feel something and state it plainly, without softening it with a joke. (This beat is mandatory; it anchors the sincerity of the argument.)

**Beat 4 — The Rhetorical Anchor:** A short, memorable, emotionally resonant statement that encapsulates the entire argument. May stand alone as its own sentence or paragraph, or may be the closing line of the Emotional Coda. It is defined by its function—encapsulating the entire argument—not by its formatting. May use very short declaratives or fragments for emphasis. No em‑dashes; use periods.

**Beat 5 — The Exit (Select One):**
- **Option A — Flat Signoff:** A single declarative sentence of 6–10 words. Flat in tone, definitive, signals the end. Does not recap, does not summarize, does not thank the viewer. Feels like the speaker ran out of things to say at this specific moment. *Select this option when the script's dominant texture has been Discovery‑Focused (clause‑building, deadpan).*
- **Option B — Deflation Callback:** A small, specific, personal grievance reasserts itself. The petty callback planted earlier pays off here. The deflation doesn't undercut the emotion; it reasserts that the speaker is a specific person with petty complaints who also happens to have just made a serious argument. *Select this option when the script has featured extended logic traps, precision‑of‑image moments, or layered parentheticals.*

**Optional Beat 6 — Perspective Note:** If the speaker has a genuine personal or community connection to the subject (e.g., grew up in a region affected, worked in an adjacent industry), they may briefly state it at the end of the Emotional Coda or just before the Exit. This must be one sentence, factual, and not exploit another's experience. It builds trust without demanding that every script include it. Do not fabricate a connection; if none exists, skip this beat.

---

#### THE FUN TO LISTEN TO REQUIREMENTS

A script that is only argument is compelling the way a documentary is compelling. It is not fun to be with. The following techniques must be distributed throughout — not concentrated at the end.

**Technique 1 — Genuine reactions before analysis:** When something genuinely surprising or absurd lands, let the speaker experience it slightly before analysis arrives.

**Technique 2 — Absurdity acknowledged before moving past it:** Absurdity needs a beat. Not a punchline — just space for the listener to recognize it and enjoy it before analysis continues.

**Technique 3 — The speaker's personality in the tangents:** Moments where the speaker's personal voice breaks through — not arguing anything, just being themselves for a moment.

**Technique 4 — Varying sentence energy:** Fast and loose sections, slow and deliberate sections, genuinely funny moments, genuinely heavy moments. Built into the text itself through paragraph length and clause density.

**Technique 5 — Giving the listener something to do:** A moment where the listener is not passive. They are invited to notice something, recall something from their own experience, or make a judgment before the script makes it for them. Three concrete mechanisms:

1. **The Anticipation Pause:** The speaker plants a specific detail and then stops before drawing the conclusion — enough space that the listener can form their own inference. The conclusion then either confirms or redirects it.
2. **The Shared Recognition Moment:** The speaker names a specific, familiar experience in enough detail that the listener knows exactly what it is. Not "you've probably felt this" but the *actual thing* — the three‑second delay before a site error, the way an out‑of‑office email from a specific kind of person always sounds.
3. **The Withheld Judgment:** The speaker lays out a fact or situation and explicitly declines to tell the listener what to think about it. "I'll leave that for you." This works once per script and only after the fact has been given enough context to stand on its own.

Required: at least one of these three mechanisms per script. Mark it in the spoken starting points table before prose generation.

**Technique 6 — Humor that serves the argument:** Observations that are both funny and true, where laughing means accepting the point.

**Technique 7 — The humor toolkit:** Every comedic moment should draw on a named technique from the list in Step 3. However, these are creative aids, not hard quotas. If a naturally funny line doesn't map perfectly to a technique, it stays. If a mandated technique feels forced, cut it.

**Self‑narration:** The speaker sounds like someone who found these things out and is now telling you. Narration of the discovery process is structural to the voice.

**Density variation:** The density of humor and analysis is deliberately variable. Long analytical stretches with no humor (building the case), followed by rapid‑fire observations where almost every sentence has a payoff. Do not regularize the rhythm.

---

#### DRAMATIZED SCENE MOMENTS (NARRATIVE DEPTH)

Identify the two or three most consequential events in the narrative. For each, write a short sensory scene (3–5 sentences) that includes location, action, a specific object or physical detail, and a consequence. Do not just state what happened; place the viewer there. These scenes are the emotional anchors of the script.

Example from the Pinkerton script: *"That night, the agents tossed a specially‑designed incendiary device intended to illuminate the house and frighten the occupants into surrender. Think of it like an 1800s version of a flashbang. Instead, when it came through the window, the family pushed the device into the fireplace where it exploded. The explosion killed the James boys' younger half‑brother and blew off the arm of their mother, Zerelda Samuels."*

Requirement: at least two such scenes in the script. Mark them in the spoken starting points table.

---

#### FIRST‑TIME VIEWER CLARITY

The script is written for an audience that has zero prior knowledge of the topic, the historical figures, or any specialised terminology.

**While writing, follow these four rules:**

1. **Define with Analogy:** When introducing any specialized term, historical concept, or institutional mechanism, immediately follow it with a concrete, everyday analogy that a modern viewer can picture. The analogy may take one or two sentences. It must use familiar, physical language (money, household objects, daily routines). Avoid dictionary‑style definitions. If you cannot find an analogy, simplify the explanation until it is transparent. Example: "company scrip" → "Monopoly money you can only cash in at the Monopoly store."
2. **Connect every section.** Adjacent ideas must be linked by an explicit causal or narrative thread.
3. **Be specific, not vague.** Vague placeholders like "physical marker," "this idea," "the condition" must resolve to something the viewer can picture or understand.
4. **Track your referents.** Before output, scan the script for every pronoun ("it," "they," "this," "that," "which") and every demonstrative placeholder. For each, confirm the exact noun it refers to appears no more than two sentences earlier and is unambiguous.

**External‑Reference Bridging:** Any comparison to an external work must be introduced with a sentence that explicitly names the parallel before the comparison begins.

**Implication Follow‑Through:** After stating any factual claim that is not self‑evidently dramatic (a statistic, a date, a bureaucratic detail), immediately include one clause that answers "which meant that…" or "which meant you could…" in concrete, human terms. Example: "The agency collected mugshots and dossiers on criminals. Which meant that for the first time, a detective in Chicago could know a suspect's history from New York before the man even opened his mouth."

**Before output, perform a fast internal check:**
- Read the script once as if you've never encountered the subject. Could a reasonable person understand every sentence without pausing to Google? If not, fix.
- Check every transition. Is there a clear link, or are two blocks just sitting next to each other?
- Scan for ambiguous words and ensure their referent was established in the preceding two sentences.
- Run the referent‑tracking scan.
- Check every external reference: is a bridging sentence present before the reference is used?
- Spot‑check three unfamiliar terms; each has an analogy or image within the same sentence.

---

#### TELEPROMPTER FORMATTING RULES

The final script must be ready to read aloud from a teleprompter without live improvisation. Apply these rules before output:

1. **No colons introducing lists.** Write "For example, wheat and cooking oil" not "For example: wheat, cooking oil."
2. **No em‑dashes.** Em‑dashes are a typographic mark for inserted thoughts. In spoken language, those thoughts either belong in their own sentence, belong at the end of the current sentence as a natural clause, or belong earlier in the sentence as a rephrased idea. Instead of dropping a comma where an em‑dash was, rewrite the sentence to remove the insertion entirely. Options: chain the thought with "and," "but," or "so"; let it trail off and restart; restructure the sentence so the parenthetical idea is integrated into the main clause; or simply end the sentence and start a new one. The goal is not punctuation replacement—it is spoken‑sentence architecture that never needed the em‑dash in the first place.
3. **No bullet points or column layouts.** Convert all tabular data into complete spoken sentences. Example: "The Indonesian Rupiah fell 9.8 percent. The Vietnamese Dong fell 3.2 percent." not a bullet list.
4. **No abbreviations that require expansion.** Write "for example," "that is," "versus." Do not use "e.g.," "i.e.," "vs."
5. **Numbers:** Use numerals for large numbers (17,500) — the speaker will read naturally. For percentages, write "9.8 percent" not "9.8%".
6. **No parentheticals that are not spoken.** If a thought requires parentheses to fit in a sentence, the sentence is written, not spoken. Rewrite the surrounding sentences so the thought either becomes its own sentence, integrates naturally into the main clause without brackets, or is cut. Never drop a comma where a parenthesis was and call it fixed—the architecture must change, not just the punctuation.
7. **No implied referents.** If "this" or "that" appears, ensure the exact noun is within the previous two sentences.

---

#### DATA PRESENTATION RULE

Any time the script presents comparative data (e.g., currency depreciation percentages, trade surplus numbers, fiscal figures), it must be written as **complete spoken sentences**, not as lists or tables. For each data point, write a full sentence that includes the subject, the value, and the time reference.

✅ Correct: "In January 2025, the trade surplus was 3.49 billion dollars. In January 2026, it fell to 950 million dollars."
❌ Incorrect: "January 2025: $3.49B. January 2026: $0.95B."

Do not use colons to introduce data series.

---

#### FIRST‑PERSON ACTIVE VOICE FOR METHODOLOGY

When describing the script's own purpose, methods, or structure, use first‑person active voice. Avoid self‑referential labels like "this explainer," "this video," "this analysis."

✅ Correct: "I've built this on data from the Ministry of Finance and BPS." or "Here is what I found."
❌ Incorrect: "This explainer builds on multiple layers of analysis."

This rule applies only to methodological statements, not to narrative or evidence sections.

---

#### PROSE REQUIREMENTS

The single most common failure mode is writing prose and then making it sound spoken. This produces written sentences with informal vocabulary on top. It is not spoken language.

**The correct generation process:** Start from the spoken starting point established in the table. Let the sentence build clause by clause the way a person actually builds a thought out loud — not by executing a pre‑planned structure but by adding each clause because the previous clause prompted it. The sentence does not know where it is going when it starts.

**Never edit existing written text to make it sound spoken. Always rebuild from the spoken starting point.**

---

**PROHIBITED** (absolute, except where explicitly allowed in Clarity Exceptions and Handholds):

- Rhetorical triplets
- Short declarative punch lines standing alone — except the crystallising line, the rhetorical anchor, or the single, deferred verdict that closes an extended Processing passage (ear test applies)
- Paired contrast constructions used more than once
- Setup‑payoff paragraph structure — paragraphs closing with a thesis statement
- Formal pivot openers used as templates: "So here's the thing," "And here's what's insane," "And look"
- "Okay so" as an opener
- Announced emotional moments
- Overly clean reported consequence sentences
- Double‑hedged opinion markers
- "And like" as a written patch
- Written foreshadowing: "And that matters later"
- Passive constructions left behind after source names are removed
- Attribution of observations to named commentators mid‑argument
- Floating actions without actors
- Staccato lists broken across multiple lines
- Fragments that cannot be read aloud as part of a flowing sentence
- Formal declarative phrasing
- Conditionals as opening lines
- Narrator‑mode hook openers
- Unattributed quotes as opening lines
- Timeline errors
- Connector words as paragraph openers — except as permitted in Handholds and native openers
- Em‑dashes (prohibited everywhere; structural rewrite required, not punctuation swap)
- Parentheticals that are not spoken (structural rewrite required, not punctuation swap)
- Formal audience address
- Building to a poetic final line
- Summarizing own point after making it (except in allowed Handholds)
- Recapping what was just said (except in allowed Handholds)
- Previewing what's about to be said (except in allowed Handholds)
- Apologizing for going long
- Padding with filler enthusiasm
- Explaining a joke after it lands
- Aggressive punchlines

---

**REQUIRED:**

- Every spoken paragraph is one connected thought built clause by clause from its spoken starting point
- Clauses that belong together are joined with natural connective tissue
- Line breaks only at genuine breath points
- The unified voice architecture maintained throughout (five‑stage loop observable)
- Detective revelation structure active throughout (modified appropriately for subject type)
- Genuine reactive discovery moments — at least two places where the speaker appears to realize something as they say it
- Pace variation built into text itself through paragraph length and clause density
- Context established before every specific detail
- Personality moments distributed throughout — marked in the spoken starting points table before prose generation
- Humor techniques suggested and optionally assigned — not concentrated at the end; each comedic moment noted
- Timeline accuracy — verified sequence of events stated correctly every time it appears
- Self‑narration present as documented
- At least one extended analogy or fully committed roleplay, running as long as it naturally remains funny (no minimum sentence count); if the subject does not invite it, a precision‑of‑image or underreaction suffices
- At least one logic trap running to its full length (if Analysis‑Focused texture dominates)
- At least one precision‑of‑image moment
- At least one underreaction landing correctly
- **Bridging sentences** present for every major topic shift
- **Re‑engagement hooks** present and forward‑pulling (not summarising) at Act 1 and Act 2 endings
- **Counterargument section** present (Acknowledge‑Rebut‑Return) before the crystallising line
- **External‑reference bridging** present before any comparison to external works
- **Callback‑plant audit** passed if a deflation callback is used
- **At least one Technique 5 "listener something to do" moment**, marked in the starting points table
- **Roadmap sentence** present after the hook (Clarity Exceptions)
- **Rhetorical anchor** present in the conclusion (Beat 4)
- **Teleprompter formatting** applied (no colons before lists, no bullet points, all data as spoken sentences)
- **Data presentation as spoken prose** applied
- **First‑person active voice** for methodology
- **At least two dramatized scene moments** (sensory, specific, with consequence)
- **Central Contradiction Statement** introduced early and returned to at Verdict or Universal Extension
- **Contemporary Anchor** present in Act 4 (or structural pattern noted if no perfect echo exists)
- **Define with Analogy** applied for every specialized term (may take one or two sentences)
- **Implication Follow‑Through** applied to every non‑dramatic factual claim

---

#### THE NATURALNESS AUDIT — APPLY BEFORE FINALIZING ANY PARAGRAPH

Check every paragraph for:

- Redundancy: words or phrases doing the same job twice in the same clause
- Temporal anchors: references to "last week," "yesterday," "recently" — use relative time references instead
- Overlong setup clauses: the actual point buried after too many subordinate clauses
- Staccato clusters: sequences of three or more sentences, each under approximately 8 words, that sit in the same paragraph or adjacent paragraphs. If the information can be combined into a single flowing clause chain without losing emphasis, merge them. The only exception is a deliberate, isolated Verdict beat that follows sufficient Processing — keep those short, but verify that the preceding passage earned the punch (by ear, not by count).
- **Parallel structure clusters:** Scan for sequences where two or more consecutive sentences share the same grammatical skeleton (Subject + can + verb + object. Subject + cannot + verb + object.) If found, break the pattern by varying at least one of the structures—change the subject, embed one inside a larger sentence, or shift from declarative to a different mode.
- **Connective scarcity:** Scan for sequences of three or more sentences within a paragraph that lack mid‑sentence connecting words (and, but, so, because, though, which, while). If found, consider merging sentences or adding a connector to improve flow.
- Wrong article usage
- Written sentence openers: infinitive clauses, formal pivots
- Abrupt emotional transitions: jumping between registers without a connective breath
- Corporate or formal language in casual register
- Passive constructions
- Written connector words used as formal definitions: "meaning," "which is to say"
- Register mismatches: formal vocabulary in casual register, or vice versa
- Dictionary‑style definitions (use analogies instead)
- Odd participial constructions
- Mixed metaphors
- Clinical language in emotional sections
- Redundant sentence endings
- Double instances of the same word
- Comma splices: no two independent clauses joined only by a comma
- Terms defined after use instead of before
- Tense inconsistencies: mixing historical narrative past with present‑tense narration
- Pronoun case errors: "his/her/their" correctly matches the intended referent
- Double conjunctions: no "and whether…and most…" or similar collisions
- Paragraph opener audit: apply the proportional scale (under 20 paragraphs: more than 3 times; 20–35 paragraphs: more than 4 times; over 35 paragraphs: more than 5 times). Also flag any two consecutive paragraphs with identical openers regardless of total count.

---

#### ADJACENT VERDICT AUDIT — APPLY AFTER THE NATURALNESS AUDIT

Scan for any two consecutive paragraphs that each end with a short declarative Verdict (under approximately 10 words) and that share a similar grammatical structure (e.g., both are "He can X. He cannot Y." or "That is not a joke. That is him Z."). If found, vary the structure of at least one: embed the second Verdict inside a larger sentence, shift the subject, change the length, or merge the two paragraphs into a single Processing passage with one deferred Verdict. The goal is not mechanical merging but literary variation—the listener should not hear a template.

---

#### THE STRUCTURAL PAYOFF AUDIT — APPLY AFTER THE ADJACENT VERDICT AUDIT

Before finalising the script, run these three checks to ensure structural payoffs are present and correctly placed:

- **Bookend audit:** If the script references an element from the source's opening (e.g., a welcome speech, a specific line, a visual), verify that a corresponding echo appears in the conclusion or Act 4.
- **Promissory payoff audit:** Scan for phrases like "for reasons that pay off later" or "which becomes important later." For each, verify that the payoff actually appears later in the script.
- **Abstract claim grounding audit:** For every claim that a character "can do" something or "has" an ability without a concrete example, verify that at least one specific, imaged example appears within two paragraphs.

---

#### PINKERTON‑SCRIPT QUALITY CHECKLIST (FINAL TONE AUDIT)

Before delivering the script, run this human‑readable checklist. If any answer is "no," revise—even if every formal rule is satisfied.

- [ ] Explain the meaning behind every unfamiliar concept within the same breath?
- [ ] Slow down to dramatize at least two pivotal moments as sensory scenes?
- [ ] Carry a clear central irony or contradiction that gives the whole story a shape?
- [ ] Feel like a person discovering things, not a lecturer presenting slides?
- [ ] Allow the speaker to react honestly (surprise, dismay, wry amusement) before analyzing?
- [ ] Provide enough natural handholds that a listener could follow without rewinding, without ever resorting to lazy signposting?
- [ ] End with the sense that the past is still breathing in the present?
- [ ] Sound, when read aloud, like a smart friend telling a story over coffee—not like an audiobook, not like a TED talk, not like an AI?

---

#### STEP 6C — TITLE AND THUMBNAIL BRIEF

After completing the long‑form script, generate the following before moving to Step 7:

**A. Three title options** using different formulas. Label each with its formula type:
- **Option 1 — Curiosity‑gap formula:** raises a question the video answers, front‑loaded with the subject keyword, 60–65 characters
- **Option 2 — Transformation/revelation formula:** states what the viewer will understand by the end, 60–65 characters
- **Option 3 — Specificity formula:** uses a concrete number, name, or date that the video actually addresses, 60–65 characters

For each title: confirm the keyword appears in the first 5 words, confirm the character count is between 55–65, confirm the title does not repeat what the thumbnail will show. Use title case. No all‑caps. Avoid repeating thumbnail text in the title; they should tell different parts of the story.

**B. Thumbnail concept brief** (one paragraph): Describe the visual elements that should appear. Include:
- Primary focal point (face with specific emotion, or a single object/text element)
- Background treatment (clean/high‑contrast, colour pairing, blurred or solid)
- Text overlay if any (3 words maximum; what the words are)
- What the thumbnail implies that the title does not state

For commentary content: authentic emotion outperforms exaggerated shock. Design for the smallest display size (320×180px mobile). High contrast between subject and background. Complementary colour pairs that work: red/white, orange/black, yellow/purple, blue/orange. Avoid YouTube's native red/white interface colours, which cause thumbnails to blend into the page chrome.

**Note:** This step produces a creative brief for the editor or designer. It is not a final deliverable. A/B test the top two title options via YouTube Studio if the channel has 1,000+ subscribers.

---

#### REVISION INTEGRATION CHECKLIST

Run this checklist in full any time new material is added to an existing draft.

**A. Living fact sheet**
- Does the new material introduce any factual claim not present in the original source?
- If yes: verify now using Step 2 standards, classify its type, and add to living fact sheet before it enters the script.
- If the claim is single‑source anonymous numeric: remove it.
- If the claim cannot be verified: cut or reframe as explicit speculation.

**B. Upstream effects**
- Does the new material assume anything that earlier paragraphs haven't established? If yes, add the setup earlier or move the new material later.
- Does the new material contradict anything established earlier? If yes, resolve explicitly.

**C. Downstream effects — hooks**
- Does the new material pre‑empt any re‑engagement hook that follows it? If yes, rewrite the hook to pull forward something not yet revealed.
- Does any existing hook now summarise rather than tease? If yes, rebuild.

**D. Downstream effects — existing paragraphs**
- Does the new material make any existing paragraph weaker, redundant, or superseded?
- For each affected paragraph, apply the Repetition vs. Reinforcement test.
- Decision: cut, reshape as reinforcement, or keep with documented reason.

**E. Downstream effects — conclusion and crystallising line**
- Does the new material change what the conclusion needs to do? If yes, re‑audit the conclusion against the full current script.
- Does the new material change what the crystallising line is proving? If yes, rewrite.
- If the exit is a Deflation Callback, does the new material affect the callback? Verify the planted detail earlier still supports it.

**F. Housekeeping**
- Add every new factual claim to the living fact sheet with source and type noted.
- Add or update delivery notes for any new humor beat, tonal shift, emotional register change, or technique deployment.
- Re‑run the paragraph opener audit.
- Verify the source table is complete and current.
- **Re‑run the bridging audit** — ensure all new or modified topic shifts still have explicit connective sentences.
- **Re‑audit the counterargument section** if new evidence has been introduced that affects the objections.
- **Re‑audit all re‑engagement hooks** against current act content.

**STRUCTURAL REVISION PROTOCOL (applies when reorganising existing material)**

When a revision involves moving, merging, or reordering sections — rather than adding new material — run the following checks before any prose rewriting:

1. **Breadcrumb integrity check:** List every piece of information planted in Act 1 that pays off in Act 3 or 4. After moving sections, confirm each breadcrumb still arrives before its payoff. If a move reverses a breadcrumb–payoff sequence, either move the payoff or re‑plant the breadcrumb in its new position.
2. **Escalation check:** Read the new structure and confirm each act still feels like a larger revelation than the previous. If two adjacent acts now feel equal in stakes, merge them or heighten the opening of the later act.
3. **Re‑engagement hook re‑audit:** After restructuring, all re‑engagement hooks must be rebuilt from scratch against the new act content. Do not reuse hooks written for the old structure.
4. **Spoken starting points:** Any section that has moved to a new position in the script may need a new spoken starting point, since the context the speaker is entering from has changed. Re‑run the starting‑point table for all paragraphs immediately following a structural seam.

---

#### CREDIBILITY AND INTEGRITY REQUIREMENTS

- **False first‑person ownership — strictly prohibited:** Never present another person's lived experience as the speaker's own.
- **Distinctive phrases from other creators:** Rewrite in original language or attribute lightly without naming.
- **Single‑source claims:** Hedge with "apparently," "from what's come out," "according to accounts that have been reported."
- **Single‑source numeric figures:** Default to removal, not hedging.
- **Legal and official sourcing:** Note in script when figures come from court documents or official disclosures.
- **Timeline accuracy:** Verified sequence stated correctly every time it appears.
- **Direct quotes:** Clearly framed as the subject's words — cannot be misread as the speaker's own sentiment.
- **Gender‑neutral narrator default:** The speaker's identity is gender‑neutral by default. Unless a script explicitly states a specific gender for the speaker, all first‑person anecdotes, memories, and bodily references must be crafted to be universally relatable. Personal stories should rely on experiences from the Universal Relatable Category list.

---

#### FORMATTING REQUIREMENTS

**In the script body (inside the code block):**
- Spoken paragraphs only
- Production notes at act headings only — shaded, before any speech (use `> *` or similar plain‑text markers)
- Re‑engagement hooks as visual callouts — not spoken (use `[HOOK: text]` or similar)
- Crystallising line formatted distinctly — spoken (use `**line**` or similar)
- Zero inline stage directions — move all to delivery notes

**Code block requirement:**
The entire long‑form script (from the hook to the final line of spoken content) must be placed inside a **single code block** using triple backticks. This separates the script from the analysis, delivery notes, and source notes that follow.

---

## STEP 7 — GENERATE A SHORT‑FORM ADAPTATION (FLEXIBLE LENGTH)

After the long‑form script is complete and its source notes and delivery notes are finished, produce a condensed short‑form script suitable for TikTok, YouTube Shorts, Instagram Reels, or similar.

**Input:** The completed long script, the verified fact sheet, and the chosen angle.

**Objective:** Communicate the identical argument and emotional arc in a self‑contained video short. The short must be built for platforms where the hook must arrest the viewer in the first 1–3 seconds.

**Mandatory Principles:**

1. **Hook reconstruction** — The first spoken line must be the single most surprising, pattern‑interrupting reframe or fact drawn from the long script. The hook must open a curiosity gap within the first 5 seconds.

2. **Length constraint (flexible target)** — The short‑form script should total **150–200 words** (approximately 60–80 seconds of spoken runtime). This is a target range, not a hard cut‑off. If the first draft exceeds 220 words, iterative cuts are required.

3. **Beat prioritisation (required)** — Before writing the short, extract every major revelation or scene from the long script. Apply this selection protocol:

   **Step 1 — Mandatory beats first** (always included, allocated word budget before anything else):
   - Opening hook beat
   - The script's single best reframe moment (the "oh, that's what that was" beat)
   - Verdict
   - Emotional coda
   - Exit

   **Step 2 — Optional beats**, selected by this single test applied to each remaining beat:
   *"Could a viewer who has never seen the long script understand this beat in under 10 words of setup, and would they care about it without knowing what came before?"*
   - Yes to both → include (in priority order: highest surprise value first)
   - No to either → cut

   **Step 3 — Word count check.** If over 220 words, cut the lowest‑surprise optional beat. Repeat until under 220.

   A beat selection table must be included in the short‑form delivery notes, recording: Beat name | Mandatory/Optional | Included/Cut | Reason.

4. **Compression, not summarisation** — Selected beats may be expressed in a single new sentence that merges reframe + context, provided no new information is introduced. Cut exposition and subordinate examples; keep every reframe and the verdict.

5. **Context‑heavy, detail‑light** — Assume zero prior knowledge. Introduce any historical figure, event, or concept with the most minimal grounding clause needed, then immediately deliver the story beat. Use analogy for unfamiliar terms as in the long script.

6. **Voice preservation** — The short must use the identical five‑stage loop architecture and the same register as the long script. Every rule from Step 3 applies.

7. **Gender‑neutral narrator** — The gender‑neutral default continues. Personal anecdotes must remain universally relatable.

8. **No new factual claims** — The short must draw exclusively from the verified fact sheet.

9. **Conclusion adaptation** — The five‑beat conclusion (Verdict → Universal Extension → Emotional Coda → Rhetorical Anchor → Exit) is preserved but compressed. If word count is tight, merge the verdict and universal extension into one sentence.

10. **Pacing and breath** — Paragraphs are very short (maximum two clauses before a natural break). Line breaks act as timing cues for the performer and editor.

11. **Visual‑text readiness** — Write key facts and reframes as short, declarative sentences that can be displayed as on‑screen text overlays while the speaker narrates.

12. **Platform safety** — The short is subject to the same Platform Safety — Content Boundaries as the long‑form script.

13. **First‑time viewer clarity** — All four rules plus Define with Analogy must be followed.

14. **Deflation callback planting** — If the exit uses a deflation callback, the exact phrase or image used in the callback must appear verbatim or near‑verbatim earlier in the short script. Verify before finalising.

15. **Teleprompter readiness** — Apply all teleprompter formatting rules to the short script as well.

16. **Code block requirement** — The entire short‑form script must be placed inside its own single code block, with a header clearly indicating it is the short‑form adaptation.

**Output:**
- The short‑form script in a code block labeled "SHORT‑FORM SCRIPT"
- Brief delivery notes for the short script, covering timing cues, register shifts, and the exact moment the hook lands
- The beat selection table (required)

---

## STEP 8 — IMAGE SOURCING (WITH ENHANCED VERIFICATION, PAGE‑URL CHECK, AND MULTI‑CATEGORY OUTPUT)

After writing both scripts, perform an image sourcing pass for the long‑form script and note any visuals that also apply to the short.

**Objective:** For each key visual moment in the long script, find a **working, directly downloadable** image URL that can be used in a commentary video under fair use / educational purposes. Where that is impossible, provide as much actionable information as possible (page URLs, manual‑download instructions, or explicit "not found" markers).

**When to source images:**
- Major subjects or named individuals introduced
- Key locations, products, or artifacts central to the story
- Screenshots or documents referenced in the script
- Visual punchlines or ironic juxtapositions identified in Step 4
- Reframe moments where a visual would strengthen the "oh, that's what that was" realization

**Image Acceptability Criteria:**
- **Direct URL required:** Must be a raw image file link (ending in .jpg, .jpeg, .png, .gif, .webp, .svg) that returns the image directly, not an HTML page.
- **Watermark policy:** Images with visible watermarks are **prohibited**.
- **Source stability preferred:** Wikimedia Commons, Internet Archive, official UN/WHO media centres, and reputable image hosts are ideal.
- **Fair use context:** The script is commentary/educational, so use of third‑party images for critique and illustration is presumed fair use.

### Mandatory verification protocol — multi‑tier

**1. Obtain a candidate URL using proper source navigation.**
- **Never** use Google Images search result URLs. Open the image in its own tab, then copy the URL from the browser's address bar.
- **For Wikimedia Commons:** Navigate to the file's description page. Scroll to "Original file" and **copy that link**. This link begins with `https://upload.wikimedia.org/wikipedia/commons/…`. Do **not** reconstruct the URL by guessing a hash directory. If you cannot find the file's description page, search `https://en.wikipedia.org/wiki/File:<filename>`.
- **For Wikipedia articles with infobox images:** View the article source, search for `|image = File:…`, then navigate to `https://en.wikipedia.org/wiki/File:<filename>` to get the direct URL.
- **For Internet Archive items:** Navigate to the item's details page and find the direct file link.
- **For WordPress uploads (`wp-content/uploads/…`):** These are inherently unstable. Note in sourcing notes that they may become unavailable later.

**2. Verification — three‑tier system.**

**Tier 1 (revised) — Full‑page fetch for direct image URL confirmation:**
If the model has a web fetch tool available:
- Fetch the image URL directly. If the response returns readable text content that is not an HTML error page, the URL is likely valid.
- If the response returns HTML error content, a redirect page, or an empty result, the URL is invalid.
- **Critical limitation:** LLM web fetch tools retrieve text content of pages — they cannot inspect HTTP response headers, issue byte‑range requests, or verify Content‑Type at the protocol level. For direct image files (.jpg, .png, .webp), the fetch result will typically be empty or minimal. This is acceptable for Tier 1 confirmation from trusted sources where the URL was obtained by navigation. Never claim a direct image URL is verified if navigation‑based confirmation (Tier 2) was not also performed.

**Tier 2 (fallback for trusted plain‑HTML repositories): Navigation‑based verification**
If the model's environment cannot confirm the URL via fetch, or for direct image files where Tier 1 returns empty content, verification may be done via page navigation.

**Trusted repositories for Tier 2:**
- Wikimedia Commons (upload.wikimedia.org)
- Internet Archive (archive.org — only items with an explicit direct‑file link on the page)
- Official UN/WHO media centres (who.int, unwomen.org, un.org — **only** if the page provides a static, non‑JavaScript download link)
- Official government sites that host public‑domain images with a clear direct‑download page (e.g., NASA, Library of Congress, National Archives)

**Navigation verification steps:**
- Navigate to the file's description/hosting page.
- Confirm the page explicitly provides a direct download link matching the candidate URL.
- Check that the image is publicly accessible and unwatermarked.
- If all checks pass, the URL is **verified by navigation**.

**Tier 3 (manual‑download pages): When no direct URL is obtainable**
For museum collections, digital archives, and institutional sites that display images via JavaScript viewers or token‑protected delivery:
- **Identify the item's landing page** where a "Download" button is present.
- **Do not guess a direct image URL.** Provide the landing page URL and a brief instruction for the editor.
- Mark the insertion point as `MANUAL DOWNLOAD — page: [URL]`.

**3. Page‑URL verification for non‑image links**
Any URL that is not a direct image file must be verified as reachable before inclusion as a working link. If the model cannot perform HTTP requests, the page URL must be marked as `(unverified reachability)`.

**4. Ensure correct URL encoding.**
Filenames and query parameter values containing spaces, commas, parentheses, ampersands, or other special characters **must be percent‑encoded**.

**5. Retry up to 2 alternative sources** if the first candidate fails verification.

**6. Final inclusion rule:**
If after 3 attempts no URL passes Tier 1 or Tier 2 verification, move to Tier 3 if a landing page exists, or mark `NO WORKING IMAGE FOUND`.

**7. Absolute prohibition on unverified direct‑image inclusion.**
For non‑trusted sources, if Tier 1 fetch was not performed, the URL must not appear as a direct image link. For trusted sources, if Tier 2 navigation verification was successfully completed, the URL may be included as a verified direct image with a note. If neither Tier 1 nor Tier 2 could be performed, the URL must not appear as a confirmed working link.

**Output format — Three lists:**

**List 1 — Verified Direct Image URLs (mapped to script insertion points):**
`[After line X / During paragraph starting "text..."]: VERIFIED_DIRECT_URL`
or
`[After line X / During paragraph starting "text..."]: NO WORKING IMAGE FOUND`

**List 2 — Batch Download Links (direct images only):**
A code block containing **only the verified direct image URLs**, one per line.

**List 3 — Manual‑Download Pages:**
`[After line X / During paragraph starting "text..."]: MANUAL DOWNLOAD — page: [URL] (notes)`

**Image sourcing notes (mandatory):** After the three lists, provide notes on:
- Verification tier used for each direct URL (Tier 1 or Tier 2).
- Licensing and public‑domain status.
- Stability warnings for WordPress or other unstable hosts.
- Any pages marked as `(unverified reachability)`.
- Recommendations for text‑card creation if no image is available.

---

**After the image sourcing output**, provide:

**DELIVERY NOTES (for long‑form script):** One note per meaningful delivery decision. References specific lines by quoting them. Includes notes on where personality moments should break through. Includes at least one note per active humor technique identifying where it appears and how long to let it run.

**DELIVERY NOTES (for short‑form script):** Brief notes on the short, focusing on hook timing, compression choices, and emotional beats. Include any different emphasis needed for the faster pace. Note which visuals from the image list are most critical for the short. Include the beat selection table.

**SOURCE NOTES:** Every factual claim mapped to its verified source. Single‑source claims flagged. Anonymous‑source numeric figures noted as removed. Legal sources identified. Timeline sources noted separately. Unsourced claims removed. Disputed figures noted with both sources and resolution applied.

---

#### QUALITY CHECKS

**TIER 1 — SHIP BLOCKERS (must pass before any output is given):**
- [ ] Every empirical claim verified; single‑source anonymous numerics removed
- [ ] Spoken starting points table completed and all five tests passed for every paragraph
- [ ] No prohibited paragraph openers (except permitted Handholds and native openers)
- [ ] No unearned short declaratives (ear test applied)
- [ ] Timeline verified and stated correctly throughout
- [ ] Five‑stage cognitive loop observable in each major revelation
- [ ] Re‑engagement hooks forward‑pulling, not summarising, at Act 1 and Act 2 endings
- [ ] Counterargument section present (Acknowledge–Rebut–Return) with credibility weighting applied
- [ ] Conclusion follows five‑beat structure (Verdict → Universal Extension → Emotional Coda → Rhetorical Anchor → Exit); optional Perspective Note if applicable
- [ ] No gender‑specific bodily references in the narrator voice
- [ ] Roadmap sentence present after hook
- [ ] Teleprompter formatting applied (no colons before lists, no bullet points, data as spoken sentences)
- [ ] At least two dramatized scene moments present
- [ ] Central Contradiction Statement planted and returned to
- [ ] Contemporary Anchor present in Act 4 (or structural pattern noted)
- [ ] Define with Analogy applied for all specialized terms (may take one or two sentences)
- [ ] Implication Follow‑Through applied to non‑dramatic factual claims
- [ ] Adjacent Verdict Audit passed (no template‑sounding adjacent verdicts)
- [ ] Parallel structure clusters broken and varied

**TIER 2 — QUALITY GATES (must pass for publishable output):**

*Hook checks:*
- [ ] Unified three‑move hook pattern applied; Move 1 selected appropriately
- [ ] If Grand Claim, concrete curiosity‑opening detail present and hits in the first 10 seconds
- [ ] No teasing, no trailer — goes directly into the story after hook
- [ ] Hook is 30 seconds maximum
- [ ] No conditionals, no narrator mode, no unattributed quotes in the first line

*Voice architecture:*
- [ ] The five stages are observable in sequence for each major revelation
- [ ] Verdict beats feel earned (ear test)

*Structure:*
- [ ] Stakes rise at every act break
- [ ] Act‑length proportions roughly match targets (or documented deviation)
- [ ] Bridging sentences present for all major topic shifts
- [ ] Crystallising line exists, is in the final third, arrives as the verdict
- [ ] If Deflation Exit, callback planted earlier and retrieved; callback‑plant audit passed
- [ ] Bookend, promissory payoff, and abstract claim grounding audits completed

*Detective revelation:*
- [ ] Subject type identified (A/B/C) and appropriate framework applied
- [ ] Effects named before causes at every major revelation point
- [ ] At least three explicit reframe moments — stated clearly not implied
- [ ] Breadcrumb details planted in Act 1 pay off in Act 4
- [ ] Act 4 demonstrates the mechanism as a proven step‑by‑step chain
- [ ] "Now you know why" payoff exists in Act 4 (or Type C equivalent)
- [ ] Reactive discovery moments exist — at least two

*Fun to listen to:*
- [ ] Personality moments distributed throughout
- [ ] At least one genuine reaction before analysis in the first half
- [ ] At least one absurdity acknowledged with a beat before moving past it
- [ ] At least one Technique 5 "listener something to do" moment present
- [ ] Every comedic moment noted (technique assignment optional, not forced)
- [ ] Self‑narration present — at least two moments
- [ ] At least one extended analogy/roleplay if natural, or precision‑of‑image/underreaction if not
- [ ] At least one precision‑of‑image moment
- [ ] At least one underreaction landing correctly

*Platform and viewer:*
- [ ] Platform safety checks passed (both scripts)
- [ ] First‑time viewer clarity checks passed (both scripts)
- [ ] External‑reference bridging present for any comparison to external works

**TIER 3 — POLISH PASS (run once when Tier 1 and 2 pass):**

- [ ] Naturalness audit passed on every paragraph
- [ ] Staccato clusters checked and merged where appropriate (ear test)
- [ ] Connective scarcity scan passed
- [ ] Paragraph opener audit completed at proportional scale
- [ ] No em‑dashes in spoken text (structural rewrites applied, not punctuation swaps)
- [ ] No parentheticals that are not spoken (structural rewrites applied, not punctuation swaps)
- [ ] Absurd self‑insertion in Move 3 drawn from Universal Relatable Category
- [ ] Source material completeness audit completed and all gaps addressed
- [ ] Humor technique suggestions from Step 4 reviewed; final script humor is organic
- [ ] Named individuals present where inclusion adds specificity, irony, or weight
- [ ] Active decisions distinguished from passive neglect
- [ ] Repetition vs. Reinforcement test applied to every element appearing more than once
- [ ] No formal academic transitions, paired contrast constructions used more than once
- [ ] No planning test failures — no first sentence that could have been planned before speaking
- [ ] No patch test failures — no formal sentence remaining after informal words are removed
- [ ] Narrator is gender‑neutral throughout; personal anecdotes avoid gendered bodily references
- [ ] Title and Thumbnail Brief (Step 6C) completed
- [ ] Image sourcing completed for all key visual moments
- [ ] Pinkerton‑Script Quality Checklist passed

**SHORT‑FORM ADAPTATION CHECKS:**
- [ ] Hook opens with a pattern‑interrupting fact or reframe within 1–3 seconds
- [ ] All mandatory beats present (hook, best reframe, verdict, emotional coda, rhetorical anchor, exit)
- [ ] Voice matches the long script; five‑stage loop observable
- [ ] No new factual claims introduced
- [ ] Total word count is 150–200 (target); if over 220, beats re‑prioritised and cut
- [ ] Beat selection table included in delivery notes
- [ ] Paragraphs short; maximum two clauses before a break
- [ ] Teleprompter formatting applied
- [ ] If exit uses a deflation callback, the callback's plant is present earlier in the short script

**REVISION CHECKS (apply after any revision):**
- [ ] Revision Integration Checklist completed in full
- [ ] If structural revision (reordering/moving sections): Structural Revision Protocol completed
- [ ] Living fact sheet updated with all new claims
- [ ] Upstream contradictions resolved
- [ ] Downstream hooks re‑audited against revised content
- [ ] Re‑engagement hooks rebuilt from scratch if structure changed
- [ ] Conclusion and crystallising line re‑audited against full revised script
- [ ] Delivery notes updated
- [ ] Source table updated
- [ ] Paragraph opener audit re‑run on full revised script

**CREDIBILITY CHECKS:**
- [ ] Clear stance supported by evidence
- [ ] False first‑person ownership check passed
- [ ] No borrowed personal accounts presented as speaker's own
- [ ] No lifted distinctive phrases presented as original
- [ ] Single‑source claims hedged
- [ ] Single‑source anonymous numeric figures removed — confirmed in source notes
- [ ] Conflicting source disputes noted with both figures and resolution applied
- [ ] Direct quotes clearly attributed
- [ ] No floating passive constructions
- [ ] Every fact sourced — unsourced claims removed
- [ ] Timeline verified and correctly stated throughout
- [ ] First‑person active voice for methodology (no "this explainer")

---

## END OF PROMPT (v3.21)
