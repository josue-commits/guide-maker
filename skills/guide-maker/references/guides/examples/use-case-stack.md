# The Recruiter's Agent Stack: 5 Skills That Replace the Monday Admin Block

This is a structural example showing the formatting patterns for a Use-case Stack guide section. A stack guide bundles several small, reusable agent skills (prompt files, configs, scripts) around one professional role. Each subpage ships one skill with its file, its trigger, and a test. Use this as a reference for the skill card format, the file tree, and the "install, run, verify" rhythm.

---

## 🧩 What a Skill Is in This Stack

A skill is a folder your coding agent reads on demand. It has one instruction file that says when to trigger and what to do, plus any scripts the instructions call. You do not paste prompts anymore. You drop the folder in and say the trigger phrase.

```
.agent/skills/
├── screen-resumes/
│   ├── SKILL.md            # trigger + steps
│   └── scripts/score.py    # reads a PDF folder, writes scores.csv
├── write-outreach/
│   └── SKILL.md
├── schedule-loop/
│   ├── SKILL.md
│   └── scripts/calendar.py
├── debrief-notes/
│   └── SKILL.md
└── weekly-report/
    ├── SKILL.md
    └── templates/report.md
```

The five skills share a scratch folder, `~/recruiting/work/`, so the output of one is the input of the next. Screening writes `scores.csv`, outreach reads it, scheduling reads the replies, and the weekly report reads everything.

---

## ⚙️ Skill 1: Screen Resumes

**Trigger:** "screen the new applicants" or any request that names a job title and a folder of PDFs.

**What it does:** Reads every PDF in the folder, scores each candidate against the job's must-have list, writes a CSV, and flags anything the scorer could not read.

The instruction file is short on purpose. The judgment lives in the scoring rubric, which is a separate file you edit per role.

```markdown
---
name: screen-resumes
description: Score a folder of resume PDFs against a role rubric. Use when asked to screen, rank, or shortlist applicants.
---

1. Ask for the role rubric path if it was not given. Default: ~/recruiting/rubrics/<role>.md
2. Run: python3 scripts/score.py --folder <pdf folder> --rubric <rubric> --out ~/recruiting/work/scores.csv
3. Read scores.csv. Present the top 10 as a table: name, score, strongest signal, biggest gap.
4. List every file the script marked UNREADABLE so a human opens it.
5. Never invent a signal that is not in the PDF text. Quote the line you scored.
```

The rubric is plain markdown, one must-have per line, with a weight:

```markdown
# Rubric: Account Executive, mid-market

- [3] Closed deals above $50k ACV (quote the number)
- [3] Sold into a 6+ month sales cycle
- [2] Used a CRM daily (name it)
- [1] Wrote their own outbound (any proof)
- [-2] Every role under 12 months in the last 4 years
```

**Verify it works:** Drop three resumes in a test folder, one obviously strong, one weak, one with a scanned image instead of text. The strong one should top the table, and the scanned one should show up in the UNREADABLE list, not in the ranking.

> ⚠️ **Warning:** The scorer only sees text. A resume that is a photo of a resume scores zero. The UNREADABLE list is not optional output, it is the difference between "we screened 40 people" and "we screened 34 and silently dropped 6".

---

## ⚙️ Skill 2: Write Outreach

**Trigger:** "reach out to the shortlist" or a request that references `scores.csv`.

**What it does:** For every candidate above the cutoff score, drafts one message that quotes the specific line from their resume that earned the top score. No merge-field template. Every draft names something real.

| Input | Where it comes from |
|-------|---------------------|
| Candidate name, score, top signal | `~/recruiting/work/scores.csv` |
| Role summary, comp range, next step | `~/recruiting/rubrics/<role>.md` header block |
| Your voice sample | `~/recruiting/voice.md` (three of your own past messages) |

The output is a folder of `.txt` drafts, one per candidate, and nothing gets sent. The skill has no sending tool on purpose. You read, you edit, you paste.

**Verify it works:** Open two drafts side by side. If you could swap the names and both would still make sense, the skill is not quoting the resume. Check that `voice.md` exists and has real messages in it.

---

## 📋 Quick Reference: The Full Stack

| Skill | Trigger phrase | Reads | Writes | Runtime |
|-------|---------------|-------|--------|---------|
| screen-resumes | "screen the applicants" | PDF folder, rubric | `scores.csv` | ~2 min per 40 PDFs |
| write-outreach | "reach out to the shortlist" | `scores.csv`, voice.md | `drafts/*.txt` | ~30 sec per candidate |
| schedule-loop | "schedule whoever replied" | inbox export, calendar | proposed slots | ~1 min |
| debrief-notes | "write up the interview" | call transcript | `debriefs/<name>.md` | ~1 min |
| weekly-report | "what happened this week" | everything in `work/` | `report.md` | ~2 min |

Install all five, then run them in that order on a real week's data before you trust any of them alone. The stack is worth more than the sum of its skills because every output is already in the shape the next skill expects.
