# YOUTUBE COMMENTARY SCRIPT GENERATION PROMPT (v3.14 — WITH CONNECTIVITY, COUNTERARGUMENT, AND CALLBACK IMPROVEMENTS)

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
- **Option A (Grand Claim):** For abstract/systemic subjects. Make a sweeping, confident claim about the specific subject. Use superlative language without irony. Establishes immensity. **For long‑form scripts, the Grand Claim must be built around a concrete, pattern‑interrupting fact — a specific piece of evidence that creates a micro‑reframe in the first 10 seconds. Avoid purely abstract thesis statements.**
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

**Technique 10: Callbacks and Escalating Returns** — Establish something early—a detail, a grievance, a joke—and return to it later in a slightly different form, often as the emotional button at the end. **A callback only lands if the exact image or phrase used in the return was planted earlier, delivered in the same deadpan‑annoyance register, and is recognisable to the listener without inference. If the punchline involves a name, the setup must include the speaker complaining about that name specifically. If the punchline involves an image, the setup must describe that image in the same words.** Before finalising, run a **callback‑plant audit**: find the deflation line, trace it back to its first appearance, and confirm the same words/register are used.

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

## STEP 6 — ESTABLISH SPOKEN STARTING POINTS, THEN WRITE THE LONG‑FORM SCRIPT

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

### PART B — WRITE THE LONG‑FORM SCRIPT

Write a 9–11 minute commentary script using the verified facts, the unified voice architecture, the chosen angle, and all structures described below. Generate each paragraph from its spoken starting point and only from its spoken starting point.

---

#### THE HOOK

Apply the unified three‑move hook pattern. Select Move 1 (Grand Claim or In Medias Res) based on the subject. Generate fresh content for all three moves. For Grand Claim, ensure the claim is anchored to a concrete, surprising detail that opens a curiosity gap.

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

**TECHNIQUE 8b — ADDRESSING COUNTERARGUMENTS (THE FINAL PROCESSING BEAT)**

Before the crystallising line (the verdict), the script must briefly acknowledge the strongest counterarguments to its central thesis and rebut them with the same evidence standard used in the rest of the argument. This serves two functions: it demonstrates intellectual honesty, and it strengthens the argument by showing that the thesis holds up against scrutiny.

The counterargument section must follow this structure:
1. **Acknowledge** — name each objection clearly and without caricature.
2. **Rebut** — use existing evidence from the source material to show why each objection falls short.
3. **Return** — end the section by explicitly stating that the objections, examined closely, actually reinforce the main thesis, because every alternative requires introducing new elements while the thesis only requires following through on what's already established.

The tone remains analytical, not defensive.

---

**TECHNIQUE 9 — BRIDGING TOPIC SHIFTS**

Every major topic shift—between sections, between acts, or when introducing a new piece of evidence—must include a one‑sentence bridge that explicitly tells the viewer *why* the argument is moving there. The bridge does two things: it names the question the previous section answered, and it names the question the next section will answer. Without this, the viewer loses the thread.

Example of a bridging sentence: *"Pomni's empathy is the core credential. But a job isn't just about being the right person—it's also about understanding what the job actually is, and how the system came to need a new operator in the first place. That's where Kinger comes in."*

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

#### PLATFORM SAFETY — CONTENT BOUNDARIES

All scripts are generated for distribution on YouTube, TikTok, and Meta platforms. The LLM is aware of the following enforcement tiers and avoids them during writing.

**Hard Boundaries (Content Removal / Account Termination — no exceptions):**
- Hate speech: attacks, slurs, or derogatory language targeting race, religion, gender, sexual orientation, disability, or nationality. Historical quotes containing such language may be reframed as reported speech used once and immediately contextualized.
- Child safety: any sexual or violent content involving minors, including fictional or digital depictions. Do not place terms for minors adjacent to sexual or violent language.
- Graphic violence: real gore, injury detail, animal cruelty, crime‑scene imagery described vividly.
- Sexually explicit content: descriptions of penetrative sex, sexual arousal, fetish content, or pornography.
- Harassment and threats: targeted insults, implied or explicit threats, coordinated abuse.
- Dangerous acts and self‑harm: promotion of suicide, eating disorders, or dangerous challenges.

**Formal terminology for sensitive acts:**
When historical or educational accuracy requires referencing a sensitive act (e.g., sexual assault, domestic abuse, self-harm), use the precise clinical or legal term once and without graphic description. Such terms are explicitly permitted in documentary contexts on all major platforms—YouTube's January 2026 update allows full monetization for non‑graphic discussion of adult sexual abuse, and TikTok permits documentary/educational content on these topics. Avoid vague language that obscures meaning (e.g., “assaults an unmarried woman” when the meaning is sexual assault). Clarity through formal terminology serves both the audience and the platform classifiers.

**YouTube Monetization Tiers (always write for full monetization eligibility):**
- Content on controversial topics is eligible only if non‑graphic and presented as dramatization, documentary, or educational analysis. This applies to adult sexual abuse, domestic abuse, self‑harm, suicide, abortion, and sexual harassment.
- Topics permanently ineligible for full monetization regardless of context: child abuse (including sex trafficking) and eating disorders.
- Profanity: occasional moderate profanity is acceptable. Strong profanity (F‑word, slurs) zero tolerance. Profanity in title, thumbnail, or first 30 seconds reduces advertiser pool. Maximum‑revenue approach: keep all profanity out.
- Graphically descriptive injury or violence: avoid; factual description without vivid detail is safe.

**TikTok & Meta Recommendation Penalties (write to stay in recommendations):**
- Sexual suggestiveness: avoid significant body exposure references, sexually suggestive acts, or framing that could be interpreted as arousing.
- Shocking, graphic, or "sadness" content that could lead to a negative user experience.
- Low‑quality framing: the content must be clearly original, educational, or documentary in nature—not aggregated, recycled, or sensationalized.

---

#### FIRST‑TIME VIEWER CLARITY

The script is written for an audience that has zero prior knowledge of the topic, the historical figures, or any specialised terminology. Assume the viewer has never heard of Hammurabi, Elizabeth I, the Code of Hammurabi, or the biological details being referenced.

**While writing, follow these four rules:**

1. **Define as you go.** Every specialised term, historical figure, or unfamiliar noun gets a grounding clause the moment it appears. "The Serjeant Painter" becomes "a royal official, the Serjeant Painter, who approved every portrait." Never leave the viewer wondering what something is or why it matters.

2. **Connect every section.** Adjacent ideas must be linked by an explicit causal or narrative thread. If the script moves from Hammurabi to Elizabeth, there must be a bridge—even a single sentence—that explains why the second follows from the first. The viewer should never have to guess how two parts relate.

3. **Be specific, not vague.** Vague placeholders like "physical marker," "this idea," "the condition" must resolve to something the viewer can picture or understand. Use clinical, directional language ("anatomical marker") that doesn't over‑explain but still tells the viewer where to look. If a term could mean multiple things, choose the most specific safe alternative.

4. **Track your referents.** Before output, scan the script for every pronoun ("it," "they," "this," "that," "which") and every demonstrative placeholder ("something," "the condition," "the idea"). For each, confirm the exact noun it refers to appears no more than two sentences earlier and is unambiguous. If two different things are called "it" in the same paragraph, rewrite to name at least one of them explicitly.

**External‑Reference Bridging:** Any comparison to an external work (another film, book, historical event) must be introduced with a sentence that explicitly names the parallel before the comparison begins. The viewer must understand *why* this reference is being invoked before any details of the reference are presented. Never assume the viewer knows the reference or understands its relevance without explanation.

**Before output, perform a fast internal check:**

- Read the script once as if you've never encountered the subject. Could a reasonable person understand every sentence without pausing to Google? If not, fix.
- Check every transition. Is there a clear link, or are two blocks just sitting next to each other? If the latter, add a bridge.
- Scan for ambiguous words ("marker," "condition," "this") and ensure their referent was established in the preceding two sentences.
- Run the referent‑tracking scan: every pronoun and placeholder must have a clear, recent antecedent.
- Check every external reference: is a bridging sentence present before the reference is used?

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
- **Bridging sentences** present for every major topic shift
- **Counterargument section** present (Acknowledge‑Rebut‑Return) before the crystallising line
- **External‑reference bridging** present before any comparison to external works
- **Callback‑plant audit** passed if a deflation callback is used

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
- Comma splices: no two independent clauses joined only by a comma
- Terms defined after use instead of before
- Tense inconsistencies: mixing historical narrative past with present‑tense narration
- Pronoun case errors: "his/her/their" correctly matches the intended referent
- Double conjunctions: no "and whether…and most…" or similar collisions
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
- **Re‑run the bridging audit** — ensure all new or modified topic shifts still have explicit connective sentences.
- **Re‑audit the counterargument section** if new evidence has been introduced that affects the objections.

---

#### CREDIBILITY AND INTEGRITY REQUIREMENTS

- **False first‑person ownership — strictly prohibited:** Never present another person’s lived experience as the speaker’s own.
- **Distinctive phrases from other creators:** Rewrite in original language or attribute lightly without naming.
- **Single‑source claims:** Hedge with “apparently,” “from what’s come out,” “according to accounts that have been reported.”
- **Single‑source numeric figures:** Default to removal, not hedging.
- **Legal and official sourcing:** Note in script when figures come from court documents or official disclosures.
- **Timeline accuracy:** Verified sequence stated correctly every time it appears.
- **Direct quotes:** Clearly framed as the subject’s words — cannot be misread as the speaker’s own sentiment.
- **Gender‑neutral narrator default:** The speaker’s identity is gender‑neutral by default. Unless a script explicitly states a specific gender for the speaker, all first‑person anecdotes, memories, and bodily references must be crafted to be universally relatable rather than tied to a particular sex or gender identity. Personal stories should rely on experiences that anyone could have, not experiences that assume a male or female body.

---

#### FORMATTING REQUIREMENTS

**In the script body (inside the code block):**
- Spoken paragraphs only
- Production notes at act headings only — shaded, before any speech (use `> *` or similar plain‑text markers)
- Re‑engagement hooks as visual callouts — not spoken (use `[HOOK: text]` or similar)
- Crystallising line formatted distinctly — spoken (use `**line**` or similar)
- Zero inline stage directions — move all to delivery notes

**Code block requirement:**  
The entire long‑form script (from the hook to the final line of spoken content) must be placed inside a **single code block** using triple backticks (```` ``` ``...`` ``` ``). This separates the script from the analysis, delivery notes, and source notes that follow.

---

## STEP 7 — GENERATE A SHORT‑FORM ADAPTATION (FLEXIBLE LENGTH)

After the long‑form script is complete and its source notes and delivery notes are finished, produce a condensed short‑form script suitable for TikTok, YouTube Shorts, Instagram Reels, or similar.

**Input:** The completed long script, the verified fact sheet, and the chosen angle.

**Objective:** Communicate the identical argument and emotional arc in a self‑contained video short. The short must be built for platforms where the hook must arrest the viewer in the first 1–3 seconds.

**Mandatory Principles:**

1. **Hook reconstruction** — The first spoken line must be the single most surprising, pattern‑interrupting reframe or fact drawn from the long script. Use the “Fact → Source → Reaction” minimal reorder if the discovery voice is active. The hook must open a curiosity gap within the first 5 seconds.

2. **Length constraint (flexible target)** — The short‑form script should total **150–200 words** (approximately 60–80 seconds of spoken runtime). This is a target range, not a hard cut‑off. Material must be selected and condensed to fit naturally within this window. If the first draft exceeds 220 words, iterative cuts are required.

3. **Beat prioritisation (required)** — Before writing the short, extract every major revelation or scene from the long script. Score each on:
   - **Angle Criticality (1–5):** How essential is the beat to the core argument?
   - **Surprise / Virality (1–5):** How likely is it to stop a scroll or open a curiosity gap?
   - **Context Dependency (1–5):** How much setup does it need? (Lower = better for short‑form.)
   
   Compute a priority score: **(Angle Criticality × 2) + Surprise – Context Dependency**.
   
   The **hook**, **verdict**, **emotional coda**, and **exit** are mandatory and are allocated word budget first. Remaining optional beats are selected in descending order of priority score until the word count approaches 150–200. Beats that do not fit are dropped without exception. A summary table must be included in the short‑form delivery notes.

4. **Compression, not summarisation** — Selected beats may be expressed in a single new sentence that merges reframe + context, provided no new information is introduced. Cut exposition and subordinate examples; keep every reframe and the verdict. Merge adjacent ideas where possible. Retain at most one concrete image per section.

5. **Context‑heavy, detail‑light** — Assume zero prior knowledge. Introduce any historical figure, event, or concept with the most minimal grounding clause needed, then immediately deliver the story beat.

6. **Voice preservation** — The short must use the identical five‑stage loop architecture and the same deadpan, discovery‑heavy, or analysis‑focused register as the long script. Every rule from Step 3 applies.

7. **Gender‑neutral narrator** — The gender‑neutral default continues. Personal anecdotes must remain universally relatable.

8. **No new factual claims** — The short must draw exclusively from the verified fact sheet. If a claim cannot be verified or isn’t already sourced, it cannot be used.

9. **Conclusion adaptation** — The four‑beat conclusion (Verdict → Universal Extension → Emotional Coda → Exit) is preserved but compressed. If word count is tight, merge the verdict and universal extension into one sentence.

10. **Pacing and breath** — Paragraphs are very short (maximum two clauses before a natural break). Line breaks act as timing cues for the performer and editor.

11. **Visual‑text readiness** — Write key facts and reframes as short, declarative sentences that can be displayed as on‑screen text overlays while the speaker narrates. Do not add formatting; just ensure the prose is overlay‑friendly.

12. **Image reuse** — The same verified image URLs from Step 8 apply. If certain visuals are especially critical for the compressed timeline, note them in the short‑form delivery notes.

13. **Platform safety** — The short is subject to the same **Platform Safety — Content Boundaries** as the long‑form script (see Step 6B). All writing must stay within those boundaries automatically.

14. **First‑time viewer clarity** — The **First‑Time Viewer Clarity** principle applies identically to the short‑form script. All four rules (define as you go, connect every section, be specific, track referents) must be followed, and the fast internal clarity check must be completed before output. External‑reference bridging and bridging of topic shifts still apply.

15. **Deflation callback planting** — If the exit uses a deflation callback, the exact phrase or image used in the callback must appear verbatim or near‑verbatim earlier in the short script. Before finalising, verify that the callback’s plant is present and recognisable.

16. **Code block requirement** — The entire short‑form script must be placed inside its own single code block (```` ``` ``...`` ``` ``), with a header clearly indicating it is the short‑form adaptation. This code block immediately follows the long‑form script’s delivery notes.

**Output:**
- The short‑form script in a code block labeled “SHORT‑FORM SCRIPT”
- Brief delivery notes for the short script, covering timing cues, register shifts, and the exact moment the hook lands
- The beat‑prioritisation table (required)

---

## STEP 8 — IMAGE SOURCING (WITH ENHANCED VERIFICATION, PAGE‑URL CHECK, AND MULTI‑CATEGORY OUTPUT)

After writing both scripts, perform an image sourcing pass for the long‑form script and note any visuals that also apply to the short.

**Objective:** For each key visual moment in the long script, find a **working, directly downloadable** image URL that can be used in a commentary video under fair use / educational purposes. Where that is impossible, provide as much actionable information as possible (page URLs, manual‑download instructions, or explicit “not found” markers).

**When to source images:**
- Major subjects or named individuals introduced
- Key locations, products, or artifacts central to the story
- Screenshots or documents referenced in the script
- Visual punchlines or ironic juxtapositions identified in Step 4
- Reframe moments where a visual would strengthen the "oh, that’s what that was" realization

**Image Acceptability Criteria:**
- **Direct URL required:** Must be a raw image file link (ending in .jpg, .jpeg, .png, .gif, .webp, .svg) that returns the image directly, not an HTML page.
- **Watermark policy:** Images with visible watermarks are **prohibited**. Licensed stock images are **acceptable** if the direct URL delivers a clean, unwatermarked file.
- **Source stability preferred:** Wikimedia Commons, Internet Archive, official UN/WHO media centres, and reputable image hosts (Imgur, Flickr with original file access) are ideal. Licensed stock sites (Alamy, Getty, Shutterstock) are acceptable **only** if a direct, unwatermarked URL is accessible — do not link to preview pages or galleries.
- **Fair use context:** The script is commentary/educational, so use of third-party images for critique and illustration is presumed fair use. No licensing purchase is required for this workflow; the editor will handle final clearance.

### Mandatory verification protocol — multi‑tier

**1. Obtain a candidate URL using proper source navigation.**
- **Never** use Google Images search result URLs. Open the image in its own tab, then copy the URL from the browser’s address bar.
- **For Wikimedia Commons:**
  - Navigate to the file’s description page (e.g., `https://commons.wikimedia.org/wiki/File:Example.jpg`). Scroll to “Original file” and **copy that link**. This link begins with `https://upload.wikimedia.org/wikipedia/commons/…`.
  - Do **not** reconstruct the URL by guessing a hash directory (like `/4/4e/`). The hash is derived from the filename by an internal algorithm and cannot be guessed.
  - **If you cannot find the file’s description page** (e.g., searching for “File:Example.jpg” returns no results), the file may exist on English Wikipedia instead of Commons. Search `https://en.wikipedia.org/wiki/File:<filename>`. If found, use the “Original file” link from that page.
  - **If no file description page can be found at all:** Move on to alternative sources or mark as `NO WORKING IMAGE FOUND`. Never guess the direct URL from a filename alone.
- **For Wikipedia articles with infobox images:**
  - If the image is used in an infobox, you can find the filename by viewing the article source: search for `|image = File:…`. Then navigate to `https://en.wikipedia.org/wiki/File:<filename>` to get the direct URL.
- **For Internet Archive items:** Navigate to the item’s details page, find the “Download Options” or direct file link, and copy that URL.
- **For official UN/WHO media centres:** Navigate to the media asset page, locate the download link (often labelled “Download high‑res” or right‑click “Save image as…”), and copy that direct URL.
- **For WordPress uploads (`wp-content/uploads/…`):** These are inherently unstable. The URL may break if the site reorganises its media. Only use such URLs if they are currently live (verified below) and note in the sourcing notes that they may become unavailable later.

**2. Verification — three‑tier system.**

**Tier 1 (preferred): Partial GET verification for direct image URLs**
If the model has browsing capability that can perform HTTP requests, execute a `GET` request with a `Range: bytes=0-1023` header on the candidate direct image URL.

- **Success criteria:**
  - HTTP status code `206` (Partial Content) or `200` (if server ignores range).
  - `Content-Type` header must begin with `image/` (e.g., `image/jpeg`, `image/png`, `image/svg+xml`).
  - The first 1024 bytes must **not** contain any of the following: `<html`, `<!DOCTYPE`, `<body`, `<?xml`. This catches servers that return a 200‑OK HTML error page.
- If the URL fails any criterion, discard it immediately and try an alternative.

**Tier 2 (fallback for trusted plain‑HTML repositories): Navigation‑based verification**
If the model’s environment **cannot** perform a partial GET, but the candidate URL comes from a repository where the direct file link is **plainly visible on the file‑description page**, verification may be done via page navigation.

**Trusted repositories for Tier 2:**
- Wikimedia Commons (upload.wikimedia.org)
- Internet Archive (archive.org — only items with an explicit “Download” or direct‑file link on the page)
- Official UN/WHO media centres (who.int, unwomen.org, un.org — **only** if the page provides a static, non‑JavaScript download link)
- Official government sites that host public‑domain images with a clear direct‑download page (e.g., NASA, Library of Congress, National Archives — must have a visible direct image URL)

**Navigation verification steps:**
- Navigate to the file’s description/hosting page.
- Confirm the page explicitly provides a direct download link matching the candidate URL.
- Check that the image is publicly accessible, unwatermarked (or watermark status noted), and that metadata is consistent.
- If all checks pass, the URL is **verified by navigation**.
- If any doubt remains, discard and try an alternative.

**Tier 3 (manual‑download pages): When no direct URL is obtainable**
Many museum collections, digital archives, and institutional sites display public‑domain or Open Access images that can be manually downloaded by a human editor, but do not expose a raw image URL to automated tools (JavaScript viewers, API‑driven delivery, token‑protected asset URLs).

For such cases:
- **Identify the item’s landing page** (the HTML page where the image is viewable and a “Download” button is present, even if script‑driven).
- **Verify the page is reachable** (HTTP 200) if possible. If reachability cannot be checked, mark the page as `MANUAL DOWNLOAD — page: [URL] (unverified reachability)`.
- **Do not guess a direct image URL.** Provide the landing page URL and a brief instruction for the editor (e.g., “Open page, click download button, save full‑resolution file”).
- Mark the insertion point as `MANUAL DOWNLOAD — page: [URL]`.

**3. Page‑URL verification for non‑image links**
Any URL that is not a direct image file (does not end in .jpg, .jpeg, .png, .gif, .webp, .svg) must be verified as reachable before inclusion as a working link.

- If the model can perform HTTP requests, issue a HEAD or GET to the URL and confirm a `200` response.
- If the model cannot perform HTTP requests, the page URL must be marked as `(unverified reachability)` in the output and cannot appear as a guaranteed working link.
- A page URL that cannot be verified must not be presented as a confirmed working link anywhere in the output; it can only appear in the manual‑download list with the unverified note, or in the “no image found” section.

**4. Ensure correct URL encoding.**
- Filenames **and query parameter values** containing spaces, commas, parentheses, ampersands, or other special characters **must be percent‑encoded**.
- For example: `My file, (1).jpg` becomes `My%20file%2C%20%281%29.jpg`. In query strings, `&` is a parameter separator; if an ampersand appears inside a parameter value, encode it as `%26`.
- If the copied URL already shows encoded characters (`%20`, `%2C`, etc.), leave it as‑is. If it shows raw punctuation, encode it before testing.
- After encoding, verify the URL works via Tier 1 (if possible) or Tier 2 (if from a trusted source and navigation checks the encoded URL's page).

**5. Retry up to 2 alternative sources** if the first candidate fails verification. For each candidate, repeat steps 1–4.

**6. Final inclusion rule:**
- If after 3 attempts (primary + 2 alternatives) no URL passes verification (either Tier 1 or Tier 2 for trusted sources), the item is moved to the manual‑download category if a landing page exists, or marked `NO WORKING IMAGE FOUND`.
- **Never** include a direct image URL that has not passed either Tier 1 or Tier 2 verification.

**7. Absolute prohibition on unverified direct‑image inclusion.**
- For **non‑trusted sources**, if verification (Tier 1) was not performed, the URL is unverified and must not appear as a direct image link. It may be listed as a manual‑download page.
- For **trusted sources**, if Tier 1 could not be performed but Tier 2 navigation verification was successfully completed, the URL may be included as a verified direct image with a note.
- If neither Tier 1 nor Tier 2 verification could be performed for a direct image candidate, the URL must not appear as a direct download link.

**Output format — Three lists:**

**List 1 — Verified Direct Image URLs (mapped to script insertion points):**
Plain text, each line formatted as:
`[After line X / During paragraph starting "text..."]: VERIFIED_DIRECT_URL`
or
`[After line X / During paragraph starting "text..."]: NO WORKING IMAGE FOUND`

**List 2 — Batch Download Links (direct images only):**
A code block (triple backticks) containing **only the verified direct image URLs**, one per line. No extra text.

**List 3 — Manual‑Download Pages:**
Plain text, each line formatted as:
`[After line X / During paragraph starting "text..."]: MANUAL DOWNLOAD — page: [URL] (notes)`
Notes should include brief instructions for the editor (e.g., “Open page, click download, save full‑res file”).

**Image sourcing notes (mandatory):** After the three lists, provide notes on:
- Verification tier used for each direct URL (Tier 1 or Tier 2).
- Licensing and public‑domain status.
- Stability warnings for WordPress or other unstable hosts.
- Any pages marked as `(unverified reachability)`.
- Recommendations for text‑card creation if no image is available.

---

**After the image sourcing output**, provide:

**DELIVERY NOTES (for long‑form script):** One note per meaningful delivery decision. References specific lines by quoting them. Includes notes on where personality moments should break through. Includes at least one note per active humor technique identifying where it appears and how long to let it run.

**DELIVERY NOTES (for short‑form script):** Brief notes on the short, focusing on hook timing, compression choices, and emotional beats. Include any different emphasis needed for the faster pace. Note which visuals from the image list are most critical for the short. Include the beat‑prioritisation table.

**SOURCE NOTES:** Every factual claim mapped to its verified source. Single‑source claims flagged. Anonymous‑source numeric figures noted as removed. Legal sources identified. Timeline sources noted separately. Unsourced claims removed.

---

#### QUALITY CHECKS

**If any check fails: stop. Return to the spoken starting point for that paragraph and rebuild from scratch. Do not patch existing prose — rebuild.**

**HOOK CHECKS (Long‑Form):**
- [ ] Unified three‑move hook pattern applied
- [ ] Move 1 selected appropriately (Grand Claim or In Medias Res)
- [ ] If Grand Claim, concrete, curiosity‑opening detail is present and hits in the first 10 seconds
- [ ] No teasing, no trailer — goes directly into the story after hook
- [ ] Hook is 30 seconds maximum — read aloud and time it
- [ ] No conditionals, no narrator mode, no unattributed quotes in the first line

**SHORT‑FORM ADAPTATION CHECKS:**
- [ ] Hook opens with a pattern‑interrupting fact or reframe within 1–3 seconds
- [ ] Curiosity gap is formed and maintained
- [ ] All mandatory beats (hook, verdict, emotional coda, exit) are present
- [ ] Voice matches the long script; five‑stage loop observable
- [ ] No new factual claims introduced
- [ ] Total word count is 150–200 (target); if over 220, beats were re‑prioritised and cut
- [ ] Beat prioritisation table included in delivery notes
- [ ] Paragraphs are short; maximum two clauses before a break
- [ ] Emotional coda and exit are intact
- [ ] If exit uses a deflation callback, the callback’s plant is present earlier in the short script

**PLATFORM SAFETY CHECKS (Both Scripts):**
- [ ] No hate speech, slurs, child‑safety topics, graphic violence, explicit sexual content, harassment, or self‑harm
- [ ] Controversial topics presented non‑graphically, as documentary/educational; no child‑abuse or eating‑disorder focus
- [ ] No strong profanity in title, thumbnail, or first 30 seconds; occasional moderate profanity only if non‑essential
- [ ] No sexual suggestiveness, shocking/graphic content, "sadness" content, or low‑quality/sensational framing
- [ ] All content clearly original, educational, or documentary in nature
- [ ] Sensitive acts referenced using precise clinical/legal terminology; no vague or euphemistic language that obscures meaning

**VIEWER CLARITY CHECKS (Both Scripts):**
- [ ] Every specialised term introduced with a grounding clause upon first appearance
- [ ] Every section transition has an explicit causal or narrative link; no unexplained jumps
- [ ] External‑reference bridging present for any comparison to an external work
- [ ] Vague placeholders replaced with specific, clear language
- [ ] A fresh reader would understand every sentence without external knowledge
- [ ] Referent‑tracking scan passed: every pronoun and placeholder has a clear, recent antecedent; no two different things called "it" in the same paragraph

**SPOKEN FLOW CHECKS (Long‑Form):**
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

**VOICE ARCHITECTURE CHECKS (Both Scripts):**
- [ ] Five‑stage cognitive loop observable in each major revelation
- [ ] Texture switches occur only at paragraph boundaries or transition markers
- [ ] No mid‑paragraph texture switching
- [ ] Verdict beats are plain, declarative, no hedging
- [ ] Release texture selected matches dominant script mode (Flat Signoff for Discovery‑heavy; Deflation for Analysis‑heavy)

**STRUCTURE CHECKS (Long‑Form):**
- [ ] Stakes rise at every act break
- [ ] Re‑engagement hooks are forward pulls not summaries
- [ ] Re‑engagement hooks re‑audited against current act content after any revision
- [ ] Crystallising line exists, is in the final third, arrives as the verdict
- [ ] Conclusion follows four‑beat structure: Verdict → Universal Extension → Emotional Coda → Exit
- [ ] Exit option correctly selected and executed
- [ ] If Deflation Exit, callback planted earlier and retrieved; callback‑plant audit passed
- [ ] Bridging sentences present for all major topic shifts
- [ ] Counterargument section present (Acknowledge‑Rebut‑Return)

**DETECTIVE REVELATION CHECKS (Long‑Form):**
- [ ] Hook opens with unified entry point
- [ ] Effects named before causes at every major revelation point
- [ ] At least three explicit reframe moments — stated clearly not implied
- [ ] Breadcrumb details planted in Act 1 pay off in Act 4
- [ ] Investigator's register breaks through at the escalation point in the drop‑off window
- [ ] Act 4 demonstrates the mechanism as a proven step‑by‑step chain
- [ ] "Now you know why" payoff exists in Act 4
- [ ] Reactive discovery moments exist — at least two

**FUN TO LISTEN TO CHECKS (Long‑Form):**
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

**IMAGE SOURCING CHECKS (ENHANCED):**
- [ ] Image sourcing completed for all key visual moments identified
- [ ] All direct image URLs obtained via proper navigation (not guessed from filename patterns)
- [ ] For trusted repositories (Tier 2): navigation verification completed if partial GET was unavailable, and direct file link is plainly visible on the page
- [ ] For manual‑download pages (Tier 3): landing page URL provided; no direct image URL guessed
- [ ] All page URLs (non‑image) checked for reachability if possible; otherwise marked as `(unverified reachability)`
- [ ] All URLs properly percent‑encoded
- [ ] No Google search result URLs, HTML pages presented as image links, or hotlink‑protected previews
- [ ] Watermarked preview images excluded; any uncertain stock‑direct URLs flagged
- [ ] **No URL included with notes claiming it "could not be verified" unless a trusted‑source navigation check was successfully performed**
- [ ] Failed verifications noted appropriately
- [ ] List 1 maps URLs to script insertion points
- [ ] List 2 contains only verified direct image URLs in plain code block
- [ ] List 3 contains manual‑download pages with instructions
- [ ] Image sourcing notes provided (verification tier, licensing, stability warnings, unverified reachability notes)

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
- [ ] Narrator is gender‑neutral unless explicitly specified otherwise; personal anecdotes avoid gendered bodily references

---

## END OF PROMPT (v3.14)
