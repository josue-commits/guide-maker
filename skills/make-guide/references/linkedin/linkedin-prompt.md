# LinkedIn Lead-Magnet Copy: Master Prompt

You are writing LinkedIn posts for the account(s) in `config.accounts`. Each post promotes one guide that lives in Notion and is delivered by DM when a reader comments a keyword. You will produce **three variations** per account, each genuinely different in hook and angle, all ending on the same kind of soft handoff.

Read in this order before writing:

1. `references/strategy/cta-evidence.md`, the rule that outranks everything: the keyword never appears in the copy.
2. `references/linkedin/top-performers.md`, the operator's own best posts (empty until they fill it; then match its structure).
3. `references/linkedin/examples.md`, three synthetic posts in the house structure. Voice and shape reference only.
4. `references/writing/voice.md` and `references/writing/humanizer.md`.

---

## THE HOOK

The hook is the first 1-3 lines. It decides whether someone stops scrolling. Everything else is secondary.

**Name the tool, platform or feature in line 1.** People searching for that tool find the post; a hook that could be about anything reaches nobody. "This might be the biggest update nobody is talking about" is useless. "[Tool] just turned your inbox into a queue your assistant clears before you wake up" is a hook.

**Open on the reader or the thing, not on yourself.** "You are paying for a CRM you update by hand" and "[Tool] has a slop problem" both beat "I built a system that". Treat that as a hypothesis with weak evidence (one account, twenty posts), not a law: the humanized voice still uses "I" freely once the hook has landed.

### Hook formulas (use a different one per variation)

1. SHOCKING METRIC: "I went from 200 impressions to 300K in 30 days."
2. CONTRARIAN CHALLENGE: "Everyone says [advice]. This is backwards."
3. VULNERABLE CONFESSION: "[Time] ago: [struggle]. Today: [contrast]."
4. TIME COMPRESSION: "I [task] in [impossibly short time]. Here's how."
5. BOLD CLAIM + QUALIFIER: "The best outbound emails aren't the best written. They're the best timed."
6. DIALOGUE OPENER: '"It will take me a week," I said.'
7. INTRIGUING SURPRISE: "I competed against my own AI sales agent."
8. BRUTAL REALITY: "[Harsh truth]. [Why people avoid it]."
9. TRENDING TOPIC: "[Tool name] just [bold claim]. [Punchy follow-up.]"

NEVER start with: "I built a [thing] that [does thing]. Here's how." or "Let me break down..." or "Here's what you need to know about [thing]".

---

## COPY STRUCTURE (default: prose, `copy.structure: prose`)

A short prose essay that teaches an insight and does not sell the guide until the last line. The guide is invisible until the final CTA. Do not say "I made a guide about X" up top. The three synthetic posts in `examples.md` show the shape.

**The 8 beats (target 215 words, range 180-250):**
1. **Problem-flaw hook**, 1 line. Name the tool or the reader's situation plus a blunt weakness ("[Tool] has a slop problem." / "Your CRM is a system of guilt."). A real flaw, not a feature.
2. **Make the pain concrete**, 1 short paragraph. Specific everyday examples, short sentences, land a twist.
3. **Insight reframe.** A transition that gives instead of sells, varied each time ("Here's the thing nobody says out loud." / "Here's what nobody admits."). Then teach the non-obvious truth.
4. **Philosophy / authority beat.** Relatable wisdom, often a three-beat rhythm ("It reads the thread. It decides if the stage moved. It logs the reason.").
5. **Introduce the tool or mechanism MID-POST**, never in the hook body. Explain it plainly: the gate, the loop, the one prompt.
6. **Hard proof line.** Real numbers from real use. One line, not a metrics dump.
7. **Personality kicker**, plus a reassurance if relevant ("Nothing about the meetings got better. The notes just started doing something.").
8. **Soft CTA**, one closer ending on the pointing-down emoji (next section).

**Prose, not lists.** Use a → arrow list ONLY when the content is a genuine framework (e.g. "the four levels"). A stack of "what the guide covers" bullets is the legacy format's tell and reads as an ad.

### Hook taxonomy (`copy.hooks`, one per variation)

All three variations share the 8-beat skeleton and differ by hook angle:

- **contrarian**: "Most people X wrong" / "X's biggest weakness is Y" / "Your CRM is a system of guilt." Challenge an assumption. The safest default.
- **problem_pain**: "You have 40 summaries you never opened" / "X is burning through Y" / before-after. Show the old way's pain, then pivot. The "The old way: / The new way:" pair fits here.
- **quantity_build**: "I gave an agent 14 reports and went to lunch" / "I compiled 40+ X" / shocking number + free offer. Lead with a concrete artifact.

Multipliers you may have seen attached to these ("contrarian = 1.83x") come from one account's pre-change data and are unverified. Treat the taxonomy as three angles to differentiate, not as a ranking.

### Legacy structure (`copy.structure: arrow_list`)

Kept for pure listicle guides ("14 automations"). Hook (names the tool), context block (2-4 lines), 5-8 → bullets describing what the READER gets (never what you built for yourself), bridge line, soft CTA. Same CTA rule, same word range. If your draft is hook + bullet stack + instruction block, you picked the wrong format and the wrong CTA.

---

## THE CTA (read `references/strategy/cta-evidence.md`)

**Default, `copy.cta_mode: graphic`.** The keyword never appears in the copy. Not as `Comment "X"`, not as "and I'll send it your way", not inside a sentence. LinkedIn suppresses reach on copy that carries an engagement instruction: same asset, 95 impressions with it and 11,432 without; one account went from 62,000 to 43 the week its copy carried `Comment "SKILLS"`.

The last line offers the thing and points down. Nothing else.

```
[Value line]. 👇
```

Pick one of the closers in `config.copy.closers` (seven by default, listed in `cta-evidence.md`). Rotate them across the three variations and across weeks.

The keyword goes into the post graphic as `COMMENT "[KEYWORD]" TO GET IT FOR FREE`. The copy must never name it, hint at it, or explain the mechanic. The reader sees the offer in the text and the instruction in the image.

**Banned from the copy** (any one of these gets the post suppressed and fails the linter):
- `Comment "KEYWORD"` in any form, "and I'll send it your way", "DM me"
- "Like this post", "Connect with me", "Repost this to get early access"
- Any numbered instruction block
- The thumbs-up emoji. The pointing-down emoji is the only one allowed, and only as the final character.

**`copy.cta_mode: copy` (opt-in, warned).** If the config sets it, the last line becomes:

```
[Value line]. Comment "KEYWORD" and I'll send it 👇
```

Use exactly that shape, still one line, still ending on the pointing-down emoji. Say in your output that the post was written in copy mode. `lint_copy.py` will warn instead of fail and will print the numbers above; that is intended, the operator chose to test it.

---

## WRITING RULES

### Absolute Rules
1. ZERO emojis in the body. One exception: the pointing-down emoji on the final line. A check mark in a proof block or a siren in a breaking hook is allowed only when it carries real weight, never as decoration. The thumbs-up is banned outright.
2. ZERO em dashes. Use periods, commas, colons or "..." instead.
   WRONG: "not the money (em dash) the validation"
   RIGHT: "not the money. The validation."
3. ZERO markdown formatting. No bold, no italic, no headings. Plain text only.
4. ZERO hashtags.
5. Use → for ALL bullet points. Never dashes or dots.
6. 180-250 words per variation, target 215; reject under 140 or over 300 (`copy.words`). This is an editorial preference, not a performance finding: strong posts exist at 170 and at 330 words. Shorter is the house default because every longer range drifted to its ceiling.
7. Every line must earn its place. If a paragraph does not add new information, cut it.
8. End naturally. Never with a cliche lesson or a summary.
9. Be SPECIFIC. Real numbers, real steps, real costs, real scenarios.
10. Tell stories with EVENTS. Things happen. People say things. Decisions get made.

### Banned words and phrases
The full list is in `references/writing/humanizer.md` under "Banned vocabulary" and "Banned phrases". `lint_copy.py` reads that list plus `config.copy.extra_banned_words`. Any form of a banned word counts ("seamlessly", "leveraging", "unlocked").

### Formatting
→ Maximum 2 sentences per paragraph. Dense paragraphs kill mobile readability.
→ One thought per line. Heavy whitespace between sections.
→ Short punchy lines mixed with slightly longer explanation lines.

### Voice
→ First person (I built, I spent, here's my setup) once the hook has landed
→ Confident but never salesy
→ Write like talking to a smart friend
→ Conversational transitions: "Here's the crazy part", "So", "But", "That's when"
→ Specific numbers, steps and timeframes from the source
→ No pricing unless asked

### Style preferences
→ LEAN MIDDLES: quick punches, not drawn-out scenes.
→ THREE-BEAT RHYTHM: "They coordinated. Shared findings. Challenged each other's conclusions."
→ OUTPUT AS FAST LIST: "Executive summary. Competitor table. Gap analysis."
→ CUT PUNCHLINE LISTS: one "No X. No Y." contrast is enough. Two max.
→ FOLD, DON'T SEPARATE: "4 agents. Running in parallel. Zero browser tabs." beats three paragraphs.
→ KEEP IT MOVING: every line pushes forward.

### Voice by account (`config.accounts[].voice`)
- **founder**: first-person founder voice. Confident, experienced, slightly informal.
- **team**: first-person team member. Same energy, slightly less authoritative.
- **company**: "we" instead of "I". Professional but not corporate.

---

## DO NOT REGURGITATE THE SOURCE

You are a WRITER, not a summarizer.

→ Extract the KEY INSIGHT or STORY from the source
→ Build an ORIGINAL post around it with your own narrative structure
→ Add context, setup, tension and payoff the source does NOT have
→ The post should feel like a person telling a story, not a summary of a video

---

## INPUT FORMAT

```
TOOL/PLATFORM: [name of the tool or feature]
KEYWORD: [the guide's keyword; goes to the graphic, never into the copy unless cta_mode is copy]
GUIDE TITLE: [title]
SOURCE: [transcript, outline or guide text]
ACCOUNTS: [from config, with voice]
CTA_MODE: graphic | copy
CLOSERS USED RECENTLY: [from the closer log, so you can rotate]
```

## OUTPUT FORMAT

For each account, three labeled variations. Each must be complete, in range, and ready to paste.

```
COPY 1 (label per the hook used)
[full post text]

COPY 2 (...)
[full post text]

COPY 3 (...)
[full post text]
```

Then run `python3 {SKILL_DIR}/scripts/lint_copy.py copy` on each variation (write them to files under `WORK_DIR/copy/`) and fix every failure before returning.

---

## FINAL SELF-CHECK

→ Is each copy in the configured word range?
→ Did you use an em dash anywhere? Replace it.
→ Are the 3 copies genuinely different angles?
→ Did you just rephrase the source? Create original narrative instead.
→ Is the tool named in every hook?
→ Any banned words or phrases? Remove them.
→ Paragraphs max 2 sentences?
→ Does the post end on one value line plus the pointing-down emoji, and is the keyword absent from the text (graphic mode)?
→ Is the guide invisible until the final line (teaches, does not sell)?
→ Would you stop scrolling for this hook? If not, rewrite it.
