# Copy Examples (synthetic)

**Replace these with 5-10 of your own posts.** These three are synthetic, written to show the house structure on generic topics. They are voice and shape references, not proof of performance. Once you have posts that worked, put them in `top-performers.md` and the writer agent will match those first.

Each one: prose 8-beat structure, tool named in line 1, 180-250 words, zero emojis in the body, zero em dashes, zero markdown, zero hashtags, no keyword anywhere in the text, one closer ending on the pointing-down emoji. All three pass `scripts/lint_copy.py copy`.

---

## Example 1: Contrarian hook (a CRM automation, 231 words)

```
Your CRM is not a system of record. It is a system of guilt.

Every rep knows the drill. Call ends, you promise yourself you will log it, three calls later the notes are gone and the deal stage is whatever it was last Tuesday. The pipeline review on Friday is a fiction everybody agrees to read out loud.

Here's the thing nobody says out loud: the CRM was never going to get updated by the people it was built to measure. The incentive runs the wrong way.

So I stopped asking. I wired a small agent between the inbox, the calendar and the CRM. Every reply, every booked call, every no-show now moves the deal stage on its own and writes a two-line note about what happened.

It reads the thread. It decides if the stage moved. It logs the reason. I never touch a field.

Four weeks in: 312 activities logged without a human, 0 deals sitting in a stage they had already left, and the Friday review took eleven minutes instead of forty.

The reps did not become more disciplined. The work just stopped depending on them.

I wrote up the whole setup: the three triggers, the stage rules, the prompt that decides when a deal is stuck, and the one guardrail that keeps it from closing deals that are not closed.

I'm giving away the complete guide for free 👇
```

---

## Example 2: Problem/pain hook (a meeting-notes workflow, 226 words)

```
You have 40 meeting summaries in a folder you have never opened.

Every notetaker records the call. Every notetaker writes the summary. Then the summary sits in a tab, the action items sit under it, and by Thursday nobody remembers who owed what to whom.

The old way: record, summarize, forget.

The new way: record, summarize, route.

Here's what nobody admits. The value of a meeting note is not the note. It is the follow-up that happens because of it. A summary that creates zero tasks is a transcript with better formatting.

So I built a small routing step that runs after every call. It reads the summary, pulls out anything with a name and a verb, creates the task in the tool the team already checks, and drafts the follow-up email in the same thread the meeting came from.

Read. Extract. Route. Draft.

Two weeks of data: 27 calls, 61 action items created automatically, 58 of them closed by the owner without a reminder. Before this we were closing about a third.

Nothing about the meetings got better. The notes just started doing something.

The guide has the routing prompt, the task template, the email draft rules, and the one filter that stops it from turning small talk into tickets.

Get free access 👇
```

---

## Example 3: Quantity/build hook (a spreadsheet agent, 227 words)

```
I gave a spreadsheet agent 14 reports to build and went to lunch.

Every ops team has the same Monday. Export the CSVs, paste them into the master sheet, fix the three columns that shifted, rebuild the pivot, screenshot it for the channel. Two hours if nothing breaks. Nothing breaking is rare.

Here's the part that surprised me. The agent was not good at spreadsheets. It was good at the boring layer around them: reading the export, noticing the shifted column, asking one question when a header changed, and refusing to guess.

That refusal is the whole trick. A script that guesses corrupts the sheet quietly. An agent that stops and asks corrupts nothing.

The build took one afternoon. One prompt file that describes each report. One folder the exports land in. One rule: if a column is missing, stop and say which one.

Fourteen reports. Forty minutes of runtime. Zero fixes by hand.

Since then it has caught two vendor exports that silently dropped a currency column, which the old process would have pasted straight into the board deck.

The guide walks through the prompt file, the folder convention, the stop rule, and how to add a fifteenth report without touching the first fourteen.

The guide and the full setup are free 👇
```

---

## What to notice

- The tool or the reader is in line 1. The guide is invisible until the last two lines.
- Beats 3 and 4 give something away (the reframe, the mechanism) before anything is offered.
- One proof line with real numbers. Not a list of five metrics.
- The arrow list is absent. Prose carries it. Use arrows only for a genuine framework.
- Three different closers across the three posts.
