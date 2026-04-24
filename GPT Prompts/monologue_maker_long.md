# YOUTUBE COMMENTARY SCRIPT GENERATION PROMPT (v3.4 — ROBUST IMAGE SOURCING WITH ENFORCED VERIFICATION)

## GENERATIVE PRINCIPLE

All descriptions of voice patterns in this prompt are structural, not textual. Any quoted language is illustrative only and must not be copied verbatim into the script. The model is required to generate original prose that fulfills the described function for the specific subject.

You are writing a YouTube commentary script. Work through all steps in order. Do not skip steps or combine them. Show your work at each step before proceeding.

---

## STEP 1 — READ THE SOURCE MATERIAL

Read the input source material carefully. The source may be a video transcript, a written article, a set of facts, or previously discussed information. Produce:

**A. Plain summary** — what the source is actually arguing or presenting, in 2–3 sentences.

**B. Core factual claims** — list every specific claim made that could be verified: names, titles, numbers, dates, prices, statistics, platform policies, statements attributed to named people. Number each one.

**For each claim, also classify its type:**
- **Empirical** – verifiable fact
- **Prescriptive** – advice, opinion, or strategy (not subject to factual verification)
- **Anecdotal** – single‑source experience
- **Causal** – “X causes Y” (flag as requiring evidence)

Do not editorialize yet. Do not verify yet. Just extract, list, and classify.

---

## STEP 2 — VERIFY EVERY FACTUAL CLAIM

For each **empirical** claim from Step 1B, run a web search and verify it independently. Correct anything wrong. For each claim, note:

- Confirmed / Corrected / Unverifiable
- The verified version of the fact
- The source

**Prescriptive and causal claims** are not subject to empirical verification. Note them as “expert opinion” or “unsubstantiated causal claim” and handle accordingly in the script (present as the speaker’s view, not established fact).

**Claim‑type verification:** For empirical claims, establish not just truth but **type** (confirmed cash figure vs. conditional warrant; named source vs. anonymous estimate; legal filing vs. journalist approximation). The type determines how the claim can be used.

**Timeline verification:** For any story involving multiple people departing, resigning, or leaving, establish the exact sequence. Get this right before writing.

Note any claims that originate from a single source — these must be presented with epistemic hedging. Note any claims whose figures come from legal documents, court filings, or official disclosures — identify these as more credible.

**Single‑source numeric figures — removal, not hedging:** If a specific numeric figure originates from a single anonymous source (forum post, social media comment, unattributed estimate), default to **removal**. Replace with general language confirmed by industry consensus, or cut entirely.

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

This step replaces the former creator-specific baselines with a single, dynamic voice architecture. The voice operates on a **five‑stage cognitive loop** that repeats for each major revelation in the script. The model must ensure each loop contains all five stages in order, but may select the **texture** for each stage from the libraries provided below.

All descriptions are structural, not textual. Generate original prose that fulfills the described function for the specific subject.

---

### THE FIVE‑STAGE COGNITIVE LOOP

| Stage | Function | Texture A (Discovery‑Focused) | Texture B (Analysis‑Focused) |
| :--- | :--- | :--- | :--- |
| **1. DISCOVERY** | How did the speaker encounter this information? | Real‑time narration: “I’m reading this document and…”; “I found this post that…” | Established deep dive: “I’ve spent way too much time looking at…”; “The forums for this are a rabbit hole.” |
| **2. REACTION** | Genuine, unperformed emotional response to the fact. | Flat affect: “Man.”; “That’s… a lot.”; “Wow.” | Understatement pivot: “Which is insane.”; “Okay.”; “I don’t know.” |
| **3. PROCESSING** | Working through implications, reasoning aloud. | Clause‑by‑clause building: Sentences that discover their endpoint mid‑flight; hedge and un‑hedge in real time. | Setup‑Verdict: Long analytical stretch, then short declarative landing; layered parentheticals. |
| **4. VERDICT** | The point of the section — plain, direct, no hedging. | Short, flat declarative statement. | Short, flat declarative statement. (Identical — this is the anchor that prevents incoherence.) |
| **5. RELEASE** | Ending a topic or the video; releasing tension. | Pivot: “Anyway.” (shifts register); or flat signoff (6‑10 word declarative sentence, flat tone, signals end). | Deflation: A small, specific, personal grievance or petty callback; pettiness reasserts itself. |

---

### DYNAMIC ROUTING RULES

The model selects texture based on the argument’s current need, not on a fixed persona.

- **If the information is surprising to the speaker** → Lean Discovery Texture A; Reaction Texture A.
- **If the information is absurd in its detail** → Lean Reaction Texture B.
- **If the logic is murky and being worked out live** → Processing Texture A.
- **If the logic is clear but the outcome is wild** → Processing Texture B.
- **If the section is concluding and the tone has been deadpan/discovery‑heavy** → Release Texture A (flat signoff).
- **If the section has featured extended logic traps or petty grievances** → Release Texture B (deflation callback).

**Anchor Rule:** Texture may only change at **paragraph boundaries** or at **explicit transition markers** (“Anyway,” “So,” “But look,”). Within a single spoken paragraph, the sentence architecture must remain consistent. Switching mid‑paragraph creates procedural incoherence.

---

### VERBAL FINGERPRINT — WORDS AND PHRASES THAT MAY APPEAR

The following vocabulary items are available across both texture families. Use them where they naturally fit the register.

**Discovery‑Family Markers:**
- “Man” (exclamation, not sarcastic)
- “From the sound of things”
- “It appears to be / it appears that”
- “Many moons ago”
- “Assuming all of this is true” / “assuming of course”
- “Kitten caboodle” (confident malapropism, use sparingly)
- “Apparently” (for sourced but indirect claims)
- “Legitimately” / “truly incredible” / “genuinely incredible”

**Analysis‑Family Markers:**
- “I don’t know” (honest acknowledgment)
- “I guess” (genuine hedging)
- “which is insane” / “which makes sense” / “which doesn’t mean much”
- “okay” (reset after something disturbing)
- “anyway” (dismissal or return to thread)
- “I mean” (clarification or concession)
- “this guy’s a [noun]” (character introduction by flat function description)

**Internet Culture Vocabulary (native references, not explained):**
- karma farmers
- AI‑generated content / slop
- Reddit posting conventions

**Never Use:**
- Academic vocabulary
- Marketing or corporate language
- Aggressive irony or sarcasm as primary register
- “Chat” as audience address
- Profanity as comedic mechanism
- Filler transitions (“moving on,” “next up,” “let’s talk about”)
- Summarizing own point after making it
- Recapping what was just said
- Previewing what’s about to be said
- Explaining a joke after it lands

---

### PARAGRAPH OPENER PROTOCOL

**Native Opener Categories (Allowed):**
- Subject‑led: opens directly on the person, thing, or fact being discussed
- Narrative‑led: opens on an event or action
- Sourcing‑led: opens by flagging where information comes from
- Observation‑led: opens with a direct observation or reaction
- Process‑narration: opens with the discovery process
- Transition word (limited): “Anyway,” is native. Used to shift back to warmth or to wrap something up.

**Prohibited Openers:**
- “So” as a paragraph launcher
- “And” as a paragraph launcher
- “But” as a paragraph launcher
- “Because” as a paragraph launcher
- “And here's...” in any form
- “So here's the thing...”
- “Here's what's wild...”
- “What's interesting is...”
- Any compound connector opener of the form “[connector] + [here's/what's/the thing]”

**Enforcement Rule:** After writing the script, list the first word of every paragraph. Any single word appearing more than twice as an opener is a pattern that does not exist in natural speech. Rebuild until no word appears more than twice.

---

### HOOK STRUCTURE — UNIFIED THREE‑MOVE PATTERN

The hook always contains three moves, but the first move is dynamically selected based on subject type.

**Move 1 — Entry Point (Choose One):**
- **Option A (Grand Claim):** For abstract/systemic subjects. Make a sweeping, confident claim about the specific subject. Use superlative language without irony. Establishes immensity.
- **Option B (In Medias Res):** For narrative/specific subjects. Start mid‑scene or mid‑sketch. The viewer does not know what they are watching until it is over. No wind‑up.

**Move 2 — Populate the Category:** Provide two or three legitimate, subject‑relevant examples that genuinely belong in the established category.

**Move 3 — Puncture with Specific Absurdity:** Add one absurdly personal, trivial example from the speaker’s own life — video game moments, minor domestic failures, pet interactions, small physical embarrassments. The absurd example sits alongside the legitimate ones as if it belongs. The humor comes entirely from juxtaposition and deadpan delivery. Then, without pause or transition, enter the story.

The hook is not a preview; it is the first scene.

---

### HUMOR MECHANICS — STRUCTURAL DESCRIPTIONS

These techniques are available regardless of texture selection. The model should deploy them intentionally and note which technique is being used in delivery notes.

**Technique 1: The Grandiose Deadpan** — Apply maximum superlative framing to something ordinary or absurd, delivered completely straight.

**Technique 2: The Fully Committed Roleplay / Extended Analogy** — Inhabit a scenario completely, with invented specific dialogue, for far longer than the point requires. The length is the joke.

**Technique 3: The Sincere Enthusiasm That Sneaks Up** — Frame self as not easily moved, then clearly be moved. Do not announce the emotional response; let it appear in the warmth of language while still technically being analytical.

**Technique 4: The Archaic or Formal Register Drop** — Use slightly elevated, formal, or archaic vocabulary completely straight in casual speech.

**Technique 5: The Confident Malapropism** — Use a wrong word or slightly mangled phrase with complete confidence. Use sparingly (once per script maximum).

**Technique 6: The Logic Trap** — Take something at exact face value and follow the logic wherever it actually goes, refusing to make the silent accommodations the text is asking for. Keep asking “but why?” with sincere confusion.

**Technique 7: Precision of Image** — Find the exact right image — not clever, not elevated, *right*. Slightly wrong scale or context. The specificity is the entire joke.

**Technique 8: Underreaction** — Genuinely alarming things get small, tired responses. The gap between the scale of the event and the scale of the response is the humor.

**Technique 9: Layered Parentheticals** — Add a second observation mid‑observation, which undercuts or complicates the first without ever abandoning it.

**Technique 10: Callbacks and Escalating Returns** — Establish something early — a detail, a grievance, a joke — and return to it later in a slightly different form, often as the emotional button at the end.

---

### WHAT NEVER HAPPENS (NEGATIVE CONSTRAINTS)

- Rhetorical triplets of the “Not X. Not Y. Z.” form
- Elegant closing thesis statements that wrap up a paragraph’s argument
- Formal academic transitions (“Furthermore,” “Moreover,” “In contrast”)
- Aggressive irony or sarcasm as a default register
- Compound connector openers
- Announcing jokes — if signaling a joke is coming, it has already arrived
- Steelmanning positions thought wrong
- Addressing the audience formally — no “you, the viewer” or “those watching”
- Building to a poetic final line — endings are flat or deflationary, not constructed
- Summarizing own point after making it
- Recapping what was just said
- Previewing what’s about to be said
- Apologizing for going long
- Padding with filler enthusiasm
- Explaining a joke after it lands

---

## STEP 4 — SOURCE MATERIAL COMPLETENESS AUDIT

**Important:** Step 4 is not only housekeeping — it is frequently where the central argument and best material are discovered. The most interesting angle, the reframe that makes the story matter, and the ironic specificity that makes it land are often buried in the source and only surface under systematic audit. Treat Step 4 as generative, not just corrective.

Before choosing an angle or writing a single word of script, conduct a systematic audit comparing all source material against what could appear in the script.

For each section of the source material, check:

**A. Named individuals.** Who is named who might be absent from the script? For each absent named individual, ask whether their presence adds specificity, irony, credibility, or emotional weight. If yes, include them.

**B. Specific mechanisms behind general descriptions.** Does the source explain specifically *why* something happened — a specific technical constraint, a specific chain of causation? Identify every place where the source says not just what happened but why, and make sure the script captures the why.

**C. Comedic or ironic specificity.** Are there details that are funny or ironic in their precision? These details prove points more powerfully than general descriptions. Identify them and flag them for inclusion. Assign the named humor technique each flagged moment will use.

**D. Active decisions vs passive neglect.** Does the source distinguish between things that happened by neglect and things that were active choices? Flag every place where a passive‑seeming event was actually a deliberate decision.

**E. Full emotional context behind known facts.** Are there details that reframe the weight of something the viewer already knows? Identify these and include them.

**F. Forward‑looking details.** Does the source describe what comes next for the subject? These details need to be as specific and grounded as the details about the problem.

**G. Legal and official sourcing.** Are any figures or facts traceable to legal documents, court filings, official disclosures, or regulatory records? Note this — it adds credibility and should be mentioned in the script.

**H. Structural continuity details.** Does the source contain information about what happened after the main events — roles that kept being filled, structures that continued, mechanisms that persisted? These details demonstrate that the argument is about systems, not individuals. Flag them.

**I. Fun and personality moments.** Are there details that are inherently funny, surprising, or characterful — details the speaker would genuinely react to rather than just report? Flag these. Assign the named humor technique each will use.

**J. Argument‑Driven Gap Identification.**

After completing the source audit, read the planned argument structure and ask: what does this argument implicitly assume, compare, or lean on that did not originate in the source material?

Check for:
- **Implicit comparisons** — to another institution, era, sport, policy framework. Verify before entering the script. Add to living fact sheet.
- **Historical context** — events, quotes, institutional history predating the source. Verify independently.
- **Assumed facts** — figures, standards, statistics that seem obvious but haven’t been checked. Verify and add to fact sheet.
- **Framework assumptions** — claims about how a system works that haven’t been explicitly sourced. Source them or flag as assumed.
- **Unverifiable assumptions** — flag for either verification, reframing as explicit speculation, or cutting.

Produce a completeness report listing every gap, missing detail, underdeveloped section, humor technique assignment, and argument‑driven gap before proceeding. Only proceed to Step 5 when the completeness audit is finished.

---

## STEP 5 — CHOOSE AN ANGLE

Based on the verified facts and the completeness audit, identify the single most compelling angle for an original commentary script. The angle must be:

- **Specific:** not “this is a big problem” but a precise, arguable claim
- **Non‑obvious:** something the source touched on or missed, not just a summary
- **Emotionally activating:** it should make someone want to argue about it in the comments
- **Supportable:** fully grounded in verified facts
- **Takes a clear stance:** supported by evidence. Do not give intellectual credibility to positions the evidence does not support.
- **Connects the viewer’s own experience to the argument:** the viewer has been living inside the evidence without knowing it
- **Has a universal extension:** connects to something bigger than the specific subject

Name the angle in one sentence. Briefly explain why it is better than the two most obvious alternatives. Identify the universal pattern the angle reveals.

---

## REPETITION VS. REINFORCEMENT

**This section applies during drafting and every revision.**

Not all repeated information is redundancy. Before cutting any information that appears more than once, apply this test:

*Is this information doing the same argumentative job in both locations — making the same point, for the same reason, to the same effect?*

- **Yes — Redundancy:** Cut the weaker instance. Keep the one where the information lands with more force, specificity, or emotional weight.
- **No — Potential Reinforcement:** Ask: does the second appearance reframe the information, extend it, or make a new point by placing it in a new context? If yes, keep both. Make the difference explicit in the prose.

**Reinforcement is earned, not assumed.** If you cannot articulate in one sentence what new argumentative work the repeated information is doing in its second location, it is redundancy. Cut it.

---

## STEP 6 — ESTABLISH SPOKEN STARTING POINTS, THEN WRITE THE SCRIPT

### PART A — ESTABLISH SPOKEN STARTING POINTS FIRST

Before writing a single word of prose, establish a spoken starting point for every paragraph in the script. Use the three‑column table format:

| Para | Raw thing being communicated | First 6 words |
|------|------------------------------|----------------|

1. **The raw thing being communicated** — one sentence, no craft, just the information
2. **The first six words out of the speaker’s mouth** if they were live right now

These are not topic sentences. They are the literal first words before any sentence structure has been decided.

**Test every starting point against these five questions before proceeding:**

- Does the starting point know where the sentence is going to end? If yes, it's written. Rebuild.
- Does it start with a filler phrase announcement like “okay so,” “so here’s the thing,” “and here’s what’s insane,” or “and look”? If yes, rebuild.
- Does it use the speaker’s actual mode of address rather than formal “you”?
- Could this starting point have been produced by someone writing prose and then adding informal words on top? If yes, it's a written patch. Rebuild from a genuinely spoken starting point.
- **Does this starting point begin with a connector word (So, And, But, Because) that could be removed to leave a complete subject‑led opener?** If yes, remove the connector and test whether the paragraph still launches. If it does, the connector was a written patch. Rebuild from the subject itself. Cross‑reference against the native openers list — if the connector is not documented as native, it is prohibited regardless of how natural it feels.

Mark personality moments and intended humor techniques in the table before prose generation. Do not leave them to emerge naturally.

Only proceed to prose generation when every starting point passes all five tests.

---

### PART B — WRITE THE SCRIPT

Write a 9–11 minute commentary script using the verified facts, the unified voice architecture, the chosen angle, and all structures described below. Generate each paragraph from its spoken starting point and only from its spoken starting point.

---

#### THE HOOK

Apply the unified three‑move hook pattern. Select Move 1 (Grand Claim or In Medias Res) based on the subject. Generate fresh content for all three moves.

---

#### THE DETECTIVE REVELATION STRUCTURE — CORE CREATIVE PHILOSOPHY

This is the most important creative requirement. Everything else serves it.

The detective revelation structure is built on one insight: **the audience has been living inside this mystery without knowing there was one.** They experienced the effects without knowing the cause. The script’s job is not to explain what happened to them. It is to show them what they were living through.

**Every structural and tonal decision flows from this philosophy.**

---

**TECHNIQUE 1 — OPEN WITH THE VIEWER’S OWN EXPERIENCE**

The first act does not open with biography or context. It opens by establishing that the viewer has been experiencing the effects of this story without knowing the cause. Once the viewer recognizes their own experience, they are no longer an outside observer.

**Note:** For Grand Claim hooks, this technique applies in the body of the script. For In Medias Res hooks, it can be embedded in the credential + framing layer.

---

**TECHNIQUE 2 — NAME EFFECTS BEFORE CAUSES**

Before explaining why something happened, briefly name the experience the viewer already had. Each moment should say: you already felt this. Here is what was causing it.

---

**TECHNIQUE 3 — REFRAME MOMENTS**

The most powerful moments. A reframe is when something the viewer already knew gets completely reinterpreted by new information. Each reframe should land with: *oh. Oh, that’s what that was.* State it explicitly.

---

**TECHNIQUE 4 — BREADCRUMB SEQUENCING**

Plant specific details early that seem like context but pay off later as evidence. Introduce them so they register but don’t reveal full significance. By Act 4, the viewer realizes they were given the clue early.

---

**TECHNIQUE 5 — THE INVESTIGATOR’S REGISTER**

A specific tonal mode distinct from outrage or excitement. The tone of someone who has looked at all the evidence, followed it to its conclusion, and is now laying it out with controlled energy — not performing emotion but needing the viewer to understand what the evidence shows.

---

**TECHNIQUE 6 — ESCALATING CRIME STRUCTURE ACROSS ACTS**

Each act makes the viewer feel they are investigating a bigger crime than they thought in the previous act.

- **Act 1:** One person’s story — a mystery the audience lived with
- **Act 2:** An entire ecosystem dismantled — effects revealed as connected damage
- **Act 3:** A specific coercive act — the scale of personal wrongdoing becomes clear
- **Act 4:** A mechanism that outlasted everyone and is still running — this is not historical, it is current

---

**TECHNIQUE 7 — ACT 4 AS THE VERDICT**

Act 4 is not analysis. It is the detective laying the evidence on the table and demonstrating the proven chain. Not a theory — the mechanism, the proof, the demonstration that the viewer has been seeing the evidence every week. The crystallising line at the end of the mechanism demonstration is the verdict.

---

**TECHNIQUE 8 — THE “NOW YOU KNOW WHY” PAYOFF**

The detective novel’s final reveal — the moment where the viewer’s own ongoing experience gets reframed as evidence they have been unwittingly collecting. Stated explicitly. The viewer stops being an observer of a historical story and understands they have been living inside the evidence.

---

#### THE CONCLUSION — UNIFIED FOUR‑BEAT STRUCTURE

The conclusion always contains these four beats in order, with texture selected dynamically.

**Beat 1 — The Verdict:** Plain, direct, no hedging. Short. After everything that preceded it, it doesn’t need to be long.

**Beat 2 — The Universal Extension:** Move from the specific subject to a universal pattern. Name that pattern explicitly. Connect back to something established earlier — a breadcrumb paying off.

**Beat 3 — The Emotional Coda:** Genuine, unironic, usually brief. Allow the speaker to feel something and state it plainly, without softening it with a joke. (This beat is mandatory; it anchors the sincerity of the argument.)

**Beat 4 — The Exit (Select One):**
- **Option A — Flat Signoff:** A single declarative sentence of 6–10 words. Flat in tone, definitive, signals the end. Does not recap, does not summarize, does not thank the viewer. Feels like the speaker ran out of things to say at this specific moment. *Select this option when the script’s dominant texture has been Discovery‑Focused (clause‑building, deadpan).*
- **Option B — Deflation Callback:** A small, specific, personal grievance reasserts itself. The petty callback planted earlier pays off here. The deflation doesn’t undercut the emotion; it reasserts that the speaker is a specific person with petty complaints who also happens to have just made a serious argument. *Select this option when the script has featured extended logic traps, precision‑of‑image moments, or layered parentheticals.*

---

#### THE FUN TO LISTEN TO REQUIREMENTS

A script that is only argument is compelling the way a documentary is compelling. It is not fun to be with. The following techniques must be distributed throughout — not concentrated at the end.

**Technique 1 — Genuine reactions before analysis:** When something genuinely surprising or absurd lands, let the speaker experience it slightly before analysis arrives.

**Technique 2 — Absurdity acknowledged before moving past it:** Absurdity needs a beat. Not a punchline — just space for the listener to recognize it and enjoy it before analysis continues.

**Technique 3 — The speaker’s personality in the tangents:** Moments where the speaker’s personal voice breaks through — not arguing anything, just being themselves for a moment.

**Technique 4 — Varying sentence energy:** Fast and loose sections, slow and deliberate sections, genuinely funny moments, genuinely heavy moments. Built into the text itself through paragraph length and clause density.

**Technique 5 — Giving the listener something to do:** Occasional moments that make the listener feel like they’re in the room.

**Technique 6 — Humor that serves the argument:** Observations that are both funny and true, where laughing means accepting the point.

**Technique 7 — The humor toolkit:** Every comedic moment must use a named technique from the list in Step 3. Generic humor is prohibited.

**Self‑narration:** The speaker sounds like someone who found these things out and is now telling you. Narration of the discovery process is structural to the voice.

**Density variation:** The density of humor and analysis is deliberately variable. Long analytical stretches with no humor (building the case), followed by rapid‑fire observations where almost every sentence has a payoff. Do not regularize the rhythm.

---

#### STRUCTURE REQUIREMENTS

**HOOK [0:00–0:30]** — Unified three‑move hook pattern. No trailer. No tease. Max 30 seconds.

**ACTS — rising stakes through escalating crime structure:** Each act answers the primary question raised by the previous act and raises a bigger one. Each act gets one short production note immediately below the act heading, before any speech.

**RE‑ENGAGEMENT MICRO‑HOOKS:** Place three at approximately the 2‑minute, 5‑minute, and 7‑minute marks. Each is a forward pull — a specific promise of something not yet seen that creates an unresolved question. Not summaries. Formatted as visual callouts. Not spoken.

**Test each re‑engagement hook:** Does reading it make the viewer form a specific unresolved question? If they could feel satisfied without watching further, it’s a summary. Rebuild.

**After any revision to act content, re‑audit all downstream re‑engagement hooks.**

**CRYSTALLISING LINE:** One line that captures the entire argument as a shareable verdict. In the final third. The payoff of the detective case. Not an observation — a proven conclusion. Highlighted visually. Spoken.

**TONAL VARIATION:** The highest drop‑off window is approximately minutes 3–7. The tonal variation in this window is the investigator’s register — an entertaining section revealing itself as evidence of something worse.

**CONCLUSION:** Apply the unified four‑beat structure. Select Exit Option A or B based on dominant script texture.

---

#### PROSE REQUIREMENTS

The single most common failure mode is writing prose and then making it sound spoken. This produces written sentences with informal vocabulary on top. It is not spoken language.

**The correct generation process:** Start from the spoken starting point established in the table. Let the sentence build clause by clause the way a person actually builds a thought out loud — not by executing a pre‑planned structure but by adding each clause because the previous clause prompted it. The sentence does not know where it is going when it starts.

**Never edit existing written text to make it sound spoken. Always rebuild from the spoken starting point.**

---

**PROHIBITED** (absolute):

- Rhetorical triplets
- Short declarative punch lines standing alone — except the crystallising line or verdict line
- Paired contrast constructions used more than once
- Setup‑payoff paragraph structure — paragraphs closing with a thesis statement
- Formal pivot openers used as templates: “So here’s the thing,” “And here’s what’s insane,” “And look”
- “Okay so” as an opener
- Announced emotional moments
- Overly clean reported consequence sentences
- Double‑hedged opinion markers
- “And like” as a written patch
- Written foreshadowing: “And that matters later”
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
- Connector words as paragraph openers — unless documented as native
- Em‑dashes for mid‑sentence asides (use only in Discovery‑Mode clause‑building when natural)
- Formal audience address
- Building to a poetic final line
- Summarizing own point after making it
- Recapping what was just said
- Previewing what’s about to be said
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
- Natural speech markers appear where they naturally fall
- Detective revelation structure active throughout
- Genuine reactive discovery moments — at least two places where the speaker appears to realize something as they say it
- Pace variation built into text itself through paragraph length and clause density
- Context established before every specific detail
- Personality moments distributed throughout — marked in the spoken starting points table before prose generation
- Humor techniques distributed throughout — not concentrated at the end; each comedic moment assigned a named technique
- Timeline accuracy — verified sequence of events stated correctly every time it appears
- Self‑narration present as documented
- At least one extended analogy or fully committed roleplay running at full length (the length is the joke)
- At least one logic trap running to its full length (if Analysis‑Focused texture dominates)
- At least one precision‑of‑image moment
- At least one underreaction landing correctly

---

#### THE NATURALNESS AUDIT — APPLY BEFORE FINALIZING ANY PARAGRAPH

Check every paragraph for:

- Redundancy: words or phrases doing the same job twice in the same clause
- Temporal anchors: references to “last week,” “yesterday,” “recently” — use relative time references instead
- Overlong setup clauses: the actual point buried after too many subordinate clauses
- Wrong article usage
- Written sentence openers: infinitive clauses, formal pivots
- Abrupt emotional transitions: jumping between registers without a connective breath
- Corporate or formal language in casual register
- Passive constructions
- Written connector words used as formal definitions: “meaning,” “which is to say”
- Register mismatches: formal vocabulary in casual register, or vice versa
- Dictionary‑style definitions
- Odd participial constructions
- Mixed metaphors
- Clinical language in emotional sections
- Redundant sentence endings
- Double instances of the same word
- Comma splices creating abrupt fragments
- Terms defined after use instead of before
- Tense inconsistencies: mixing historical narrative past with present‑tense narration
- Paragraph opener audit: List the first word of every paragraph. Any word appearing more than twice is a pattern. Cross‑reference against the native openers list. Any opener not on that list must be rebuilt.

---

#### REVISION INTEGRATION CHECKLIST

Run this checklist in full any time new material is added to an existing draft.

**A. Living fact sheet**
- Does the new material introduce any factual claim not present in the original source?
- If yes: verify now using Step 2 standards, classify its type, and add to living fact sheet before it enters the script.
- If the claim is single‑source anonymous numeric: remove it.
- If the claim cannot be verified: cut or reframe as explicit speculation.

**B. Upstream effects**
- Does the new material assume anything that earlier paragraphs haven’t established? If yes, add the setup earlier or move the new material later.
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

---

#### CREDIBILITY AND INTEGRITY REQUIREMENTS

- **False first‑person ownership — strictly prohibited:** Never present another person’s lived experience as the speaker’s own.
- **Distinctive phrases from other creators:** Rewrite in original language or attribute lightly without naming.
- **Single‑source claims:** Hedge with “apparently,” “from what’s come out,” “according to accounts that have been reported.”
- **Single‑source numeric figures:** Default to removal, not hedging.
- **Legal and official sourcing:** Note in script when figures come from court documents or official disclosures.
- **Timeline accuracy:** Verified sequence stated correctly every time it appears.
- **Direct quotes:** Clearly framed as the subject’s words — cannot be misread as the speaker’s own sentiment.

---

#### FORMATTING REQUIREMENTS

**In the script body (inside the code block):**
- Spoken paragraphs only
- Production notes at act headings only — shaded, before any speech (use `> *` or similar plain‑text markers)
- Re‑engagement hooks as visual callouts — not spoken (use `[HOOK: text]` or similar)
- Crystallising line formatted distinctly — spoken (use `**line**` or similar)
- Zero inline stage directions — move all to delivery notes

**Code block requirement:**  
The entire script (from the hook to the final line of spoken content) must be placed inside a **single code block** using triple backticks (```` ``` ``...`` ``` ``). This separates the script from the analysis, delivery notes, and source notes that follow.

---

## STEP 7 — IMAGE SOURCING (WITH ROBUST VERIFICATION — ENFORCED)

After writing the script and before the DELIVERY NOTES, perform an image sourcing pass.

**Objective:** For each key visual moment in the script, find a **working, directly downloadable** image URL that can be used in a commentary video under fair use / educational purposes.

**When to source images:**
- Major subjects or named individuals introduced
- Key locations, products, or artifacts central to the story
- Screenshots or documents referenced in the script
- Visual punchlines or ironic juxtapositions identified in Step 4
- Reframe moments where a visual would strengthen the "oh, that's what that was" realization

**Image Acceptability Criteria:**
- **Direct URL required:** Must be a raw image file link (ending in .jpg, .jpeg, .png, .gif, .webp, .svg) that returns the image directly, not an HTML page.
- **Watermark policy:** Images with visible watermarks are **prohibited**. Licensed stock images are **acceptable** if the direct URL delivers a clean, unwatermarked file.
- **Source stability preferred:** Wikimedia Commons, official press kits, Internet Archive, and reputable image hosts (Imgur, Flickr with original file access) are ideal. Licensed stock sites (Alamy, Getty, Shutterstock) are acceptable **only** if a direct, unwatermarked URL is accessible — do not link to preview pages or galleries.
- **Fair use context:** The script is commentary/educational, so use of third-party images for critique and illustration is presumed fair use. No licensing purchase is required for this workflow; the editor will handle final clearance.

### Mandatory verification protocol — strict, not optional

**1. Obtain a candidate URL using proper source navigation.**
- **Never** use Google Images search result URLs. Open the image in its own tab, then copy the URL from the browser’s address bar.
- **For Wikimedia Commons:**
  - Navigate to the file’s description page (e.g., `https://commons.wikimedia.org/wiki/File:Example.jpg`). Scroll to “Original file” and **copy that link**. This link begins with `https://upload.wikimedia.org/wikipedia/commons/…`.
  - Do **not** reconstruct the URL by guessing a hash directory (like `/4/4e/`). The hash is derived from the filename by an internal algorithm and cannot be guessed.
  - **If you cannot find the file’s description page** (e.g., searching for “File:Example.jpg” returns no results), the file may exist on English Wikipedia instead of Commons. Search `https://en.wikipedia.org/wiki/File:<filename>`. If found, use the “Original file” link from that page.
  - **If no file description page can be found at all:** Mark as `NO WORKING IMAGE FOUND`. Never guess the direct URL from a filename alone.
- **For Wikipedia articles with infobox images:**
  - If the image is used in an infobox, you can find the filename by viewing the article source: search for `|image = File:…`. Then navigate to `https://en.wikipedia.org/wiki/File:<filename>` to get the direct URL.
- **For WordPress uploads (`wp-content/uploads/…`):** These are inherently unstable. The URL may break if the site reorganises its media. Only use such URLs if they are currently live (verified below) and note in the sourcing notes that they may become unavailable later.

**2. Verify the URL with a partial GET request (not just HEAD).**
- Use the model’s browsing tool to perform a `GET` request with a `Range: bytes=0-1023` header.
- **Success criteria:**
  - HTTP status code `206` (Partial Content) or `200` (if server ignores range).
  - `Content-Type` header must begin with `image/` (e.g., `image/jpeg`, `image/png`, `image/svg+xml`).
  - The first 1024 bytes must **not** contain any of the following: `<html`, `<!DOCTYPE`, `<body`, `<?xml`. This catches servers that return a 200‑OK HTML error page.
- If the URL fails any criterion, discard it immediately.

**3. Ensure correct URL encoding.**
- Filenames **and query parameter values** containing spaces, commas, parentheses, ampersands, or other special characters **must be percent‑encoded**.
- For example: `My file, (1).jpg` becomes `My%20file%2C%20%281%29.jpg`. In query strings, `&` is a parameter separator; if an ampersand appears inside a parameter value, encode it as `%26`.
- If the copied URL already shows encoded characters (`%20`, `%2C`, etc.), leave it as‑is. If it shows raw punctuation, encode it before testing.
- Test the URL with the partial GET; if the response contains character decode errors or returns an HTML error page, the encoding is likely wrong. Discard and try an alternative.

**4. Retry up to 2 alternative sources** if the first candidate fails verification. For each candidate, repeat steps 1–3.

**5. Final inclusion rule:**
- If after 3 attempts (primary + 2 alternatives) no URL passes verification, output:  
  `NO WORKING IMAGE FOUND` for that insertion point.
- **Never** include a URL that has not passed the full verification. Do not include “likely correct but unverifiable” links.

**6. Absolute prohibition on unverified inclusion.**
- **Never** include a URL accompanied by notes like “constructed from known stable sources,” “expected to work,” or “could not be verified in this environment.” If verification was not performed, the URL is unverified and must not be included.
- Output `NO WORKING IMAGE FOUND — verification unavailable` if the browsing tool cannot execute the partial GET and no alternative verification method is available.

**Output format — Two lists:**

**First list (mapped to script insertion points):**  
Plain text, each line formatted as:  
`[After line X / During paragraph starting "text..."]: VERIFIED_URL`  
or  
`[After line X / During paragraph starting "text..."]: NO WORKING IMAGE FOUND`  
or  
`[After line X / During paragraph starting "text..."]: NO WORKING IMAGE FOUND — verification unavailable`

**Second list (batch download links):**  
A code block (triple backticks) containing **only the verified URLs**, one per line. No extra text, no commentary inside the code block.

**Example:**
[After "And that's when the filing dropped."]: https://upload.wikimedia.org/wikipedia/commons/thumb/example.jpg
[During paragraph starting "The interface itself looks"]: https://i.imgur.com/abc123def.png
[After "The CEO's statement was"]: NO WORKING IMAGE FOUND

text

**Image sourcing notes (mandatory):** After the two lists, provide brief notes on:
- Any images requiring watermark verification (e.g., “Verify no watermark on this Alamy direct link”).
- Licensing considerations (public domain, Creative Commons, fair use rationale).
- Stability warnings for WordPress `wp-content/uploads` URLs.
- Hotlink protection issues encountered, and any alternative sources attempted.

---

**After the code block and image sourcing output**, provide:

**DELIVERY NOTES:** One note per meaningful delivery decision. References specific lines by quoting them. Includes notes on where personality moments should break through. Includes at least one note per active humor technique identifying where it appears and how long to let it run.

**SOURCE NOTES:** Every factual claim mapped to its verified source. Single‑source claims flagged. Anonymous‑source numeric figures noted as removed. Legal sources identified. Timeline sources noted separately. Unsourced claims removed.

---

#### QUALITY CHECKS

**If any check fails: stop. Return to the spoken starting point for that paragraph and rebuild from scratch. Do not patch existing prose — rebuild.**

**HOOK CHECKS:**
- [ ] Unified three‑move hook pattern applied
- [ ] Move 1 selected appropriately (Grand Claim or In Medias Res)
- [ ] No teasing, no trailer — goes directly into the story after hook
- [ ] Hook is 30 seconds maximum — read aloud and time it
- [ ] No conditionals, no narrator mode, no unattributed quotes in the first line

**SPOKEN FLOW CHECKS:**
- [ ] Spoken starting points table completed before any prose was written
- [ ] All five starting point tests passed for every paragraph — including the connector word test
- [ ] Personality moments and humor techniques marked in the table before prose generation
- [ ] No “okay so” openers
- [ ] No formal pivot opener templates — count instances, more than one is a template
- [ ] No paired contrast constructions used more than once
- [ ] No short declarative punch lines standing alone except the crystallising/verdict line
- [ ] No setup‑payoff paragraph endings
- [ ] Planning test passed — could any first sentence have been planned before the speaker opened their mouth?
- [ ] Aloud test passed — sounds like someone explaining to a friend
- [ ] Patch test passed — remove all informal words, no formal sentence should remain
- [ ] Naturalness audit passed on every paragraph
- [ ] Paragraph opener audit completed — no single word appears more than twice
- [ ] No em‑dashes in spoken text unless in natural clause‑building discovery mode
- [ ] Hook Move 1 matches subject type
- [ ] Absurd self‑insertion present in Move 3, delivered deadpan

**VOICE ARCHITECTURE CHECKS:**
- [ ] Five‑stage cognitive loop observable in each major revelation
- [ ] Texture switches occur only at paragraph boundaries or transition markers
- [ ] No mid‑paragraph texture switching
- [ ] Verdict beats are plain, declarative, no hedging
- [ ] Release texture selected matches dominant script mode (Flat Signoff for Discovery‑heavy; Deflation for Analysis‑heavy)

**STRUCTURE CHECKS:**
- [ ] Stakes rise at every act break
- [ ] Re‑engagement hooks are forward pulls not summaries
- [ ] Re‑engagement hooks re‑audited against current act content after any revision
- [ ] Crystallising line exists, is in the final third, arrives as the verdict
- [ ] Conclusion follows four‑beat structure: Verdict → Universal Extension → Emotional Coda → Exit
- [ ] Exit option correctly selected and executed
- [ ] If Deflation Exit, callback planted earlier and retrieved

**DETECTIVE REVELATION CHECKS:**
- [ ] Hook opens with unified entry point
- [ ] Effects named before causes at every major revelation point
- [ ] At least three explicit reframe moments — stated clearly not implied
- [ ] Breadcrumb details planted in Act 1 pay off in Act 4
- [ ] Investigator's register breaks through at the escalation point in the drop‑off window
- [ ] Act 4 demonstrates the mechanism as a proven step‑by‑step chain
- [ ] "Now you know why" payoff exists in Act 4
- [ ] Reactive discovery moments exist — at least two

**FUN TO LISTEN TO CHECKS:**
- [ ] Personality moments distributed throughout — not concentrated at the end
- [ ] At least one genuine reaction before analysis in the first half
- [ ] At least one absurdity acknowledged with a beat before moving past it
- [ ] Humor that serves the argument exists — at least one observation that is both funny and makes the point
- [ ] Sentence energy varies throughout
- [ ] At least one moment that gives the listener something to do
- [ ] Every comedic moment has a named humor technique assigned — no generic humor
- [ ] Self‑narration present — at least two moments where the speaker sounds like someone who found something out
- [ ] "Apparently" deployed at semantically correct moments only
- [ ] At least one extended analogy or fully committed roleplay running at full length
- [ ] At least one logic trap running to its full length (if Analysis‑Focused texture used)
- [ ] At least one precision‑of‑image moment
- [ ] Density variation is deliberate — long analytical stretches and rapid‑fire observations both present
- [ ] At least one underreaction landing correctly

**CONTENT CHECKS:**
- [ ] Source material completeness audit completed and all gaps addressed
- [ ] Argument‑driven gap identification completed — all implicit comparisons, historical context, assumed facts, and framework assumptions verified and added to living fact sheet
- [ ] Humor technique assignments from Step 4 carried into the script
- [ ] Named individuals present where inclusion adds specificity, irony, credibility, or emotional weight
- [ ] Specific mechanisms behind general descriptions included
- [ ] Active decisions distinguished from passive neglect
- [ ] Full emotional context behind known facts included
- [ ] Forward‑looking sections as specific and grounded as the problem sections
- [ ] Legal and official sources noted with brief explanation of why they are more credible
- [ ] Context before detail — every term explained before the detail depending on it
- [ ] Timeline accuracy — verified sequence stated correctly throughout
- [ ] Repetition vs. Reinforcement test applied to every element appearing more than once

**IMAGE SOURCING CHECKS (ENFORCED):**
- [ ] Image sourcing completed for all key visual moments identified
- [ ] All URLs obtained via proper navigation (not guessed from filename patterns)
- [ ] All URLs verified with partial GET (Range: bytes=0-1023) — status 200/206, Content-Type image/*, response body does not contain `<html`, `<!DOCTYPE`, `<body`, `<?xml`
- [ ] All URLs properly percent‑encoded (filenames and query parameters)
- [ ] No Google search result URLs, HTML pages, or hotlink‑protected previews included
- [ ] Watermarked preview images excluded; any uncertain stock‑direct URLs flagged for review
- [ ] **No URL included with notes claiming it "could not be verified" or is "expected to work"**
- [ ] If partial GET verification was unavailable for any source, all URLs from that source are marked `NO WORKING IMAGE FOUND — verification unavailable`
- [ ] Failed verifications noted as "NO WORKING IMAGE FOUND" (or "verification unavailable" variant)
- [ ] First list maps URLs to script insertion points
- [ ] Second list (batch download) contains only verified URLs in plain code block
- [ ] Image sourcing notes provided (stability warnings, licensing, hotlink issues)

**REVISION CHECKS (apply after any revision):**
- [ ] Revision Integration Checklist completed in full
- [ ] Living fact sheet updated with all new claims introduced during revision
- [ ] All new claims verified to Step 2 standards before entering script
- [ ] Upstream contradictions resolved
- [ ] Downstream hooks re‑audited against revised content
- [ ] Affected existing paragraphs assessed — cut, reshaped, or kept with documented reason
- [ ] Conclusion and crystallising line re‑audited against full revised script
- [ ] Delivery notes updated
- [ ] Source table updated
- [ ] Image sourcing re‑run if new visual moments introduced
- [ ] Paragraph opener audit re‑run on full revised script

**CREDIBILITY CHECKS:**
- [ ] Clear stance supported by evidence — no intellectual credibility given to positions the evidence does not support
- [ ] False first‑person ownership check
- [ ] No borrowed personal accounts presented as speaker's own
- [ ] No lifted distinctive phrases presented as original
- [ ] No false credentials claimed
- [ ] Single‑source claims hedged
- [ ] Single‑source anonymous numeric figures removed, not hedged — confirmed in source notes
- [ ] Direct quotes clearly attributed
- [ ] No floating passive constructions
- [ ] Every fact sourced — unsourced claims removed
- [ ] Timeline verified and correctly stated throughout

---

## END OF PROMPT (v3.4)
