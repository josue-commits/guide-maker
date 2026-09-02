# Should You Buy a Meeting Notetaker or Build One?

This is a structural example showing the formatting patterns for a Comparison/Persuasion guide section. Use this as a reference for the thesis-first opening, comparison tables with real numbers, objection handling, and the bottom-line recommendation that closes the type.

---

## ❌ Problem 1: The Built-In Recorder Only Records

Every video call tool now ships a "record and summarize" button. It works. You get a transcript, a paragraph of summary, and a list of action items that reads like a court stenographer wrote it.

What it does not do is anything with that output. The action items sit in a tab nobody opens. The transcript is searchable inside the meeting tool and nowhere else. If your CRM, your task manager, and your inbox are three different products, the built-in recorder gives you a fourth place to look.

A team of five running twelve calls a week produces about 60 summaries a month. In a test over four weeks, 51 of those 60 were never opened again after the day of the call.

> 🔑 **Key Insight:** The value of a meeting note is not the note. It is the follow-up that happens because of it. Judge every option on what it triggers, not on what it stores.

---

## ❌ Problem 2: A Dedicated Tool Costs More Than It Looks

Dedicated notetakers fix the routing problem. They push summaries into the CRM, create tasks, draft the follow-up email. The catch is the pricing page.

| Line item | Advertised | What you actually pay (5 seats) |
|-----------|-----------|----------------------------------|
| Seat price | $19 per user per month | $95 per month |
| CRM integration | "Included" | Only on the $39 tier, so $195 per month |
| Recording storage | "Unlimited" | 90-day retention on lower tiers |
| Custom summary templates | Listed as a feature | Admin-only, needs the top tier |
| Annual total | $1,140 | $2,340 |

Nothing on that table is hidden. It is all on the pricing page. It is just spread across three tiers and two footnotes.

---

## 📊 The Head-to-Head Comparison

| | Built-in recorder | Dedicated notetaker | Build it yourself |
|---|---|---|---|
| Setup time | 0 minutes | 1 to 2 hours | 1 to 2 days |
| Monthly cost (5 seats) | $0 (bundled) | $95 to $195 | $15 to $40 in API usage |
| Pushes to CRM | No | Yes (higher tier) | Yes, anything with an API |
| Custom summary format | No | Limited | Fully yours |
| Drafts the follow-up email | No | Some | Yes |
| Works across call tools | No | Most | Whatever you wire in |
| Who fixes it when it breaks | Vendor | Vendor | You |

The last row is the one people skip. A homegrown pipeline is cheaper every month until the week the transcription API changes its response shape and nobody on the team remembers how the script works.

---

## 💰 Cost Analysis

Assume five people, twelve calls a week, 45 minutes average.

```
Built-in recorder:      $0 per month, but ~6 hours per week of manual follow-up
                        6 h x 4.3 weeks x $60/h (loaded cost)  = $1,548 per month in time

Dedicated notetaker:    $195 per month on the tier with CRM push
                        ~1 hour per week reviewing summaries    = $258 per month in time
                        Total                                   = $453 per month

Build it yourself:      ~$30 per month in transcription + LLM calls
                        ~2 hours per week maintaining it        = $516 per month in time
                        Total                                   = $546 per month
```

The dedicated tool wins on total cost for a five-person team. The homegrown option only pulls ahead past roughly 15 seats, when the per-seat pricing stops scaling and the maintenance hours stay flat.

---

## 🤔 But What About...?

**"We already pay for the video tool, the recorder is free."**
Free to run, not free to use. The six hours a week of manual follow-up is the real invoice. If nobody on the team is doing that follow-up, you have a different problem and a notetaker will not fix it.

**"Our data cannot leave our tenant."**
Then the build path is the only one that keeps recordings inside your own storage. Budget for the maintenance hours honestly. Two hours a week is the floor, not the ceiling.

**"We will switch later if it does not work."**
Switching cost is the transcripts. Export them before you commit to any tool, and check that the export is plain text or JSON, not a proprietary archive.

---

## 🎯 The Bottom Line

| Team size | Pick this | Why |
|-----------|-----------|-----|
| 1 to 3 people | Built-in recorder plus a weekly 30-minute review | Volume is too low to justify anything else |
| 4 to 15 people | Dedicated notetaker on the CRM tier | Cheapest total cost once you count follow-up time |
| 15+ people, or strict data rules | Build it | Per-seat pricing stops making sense and you need control |

Whatever you pick, set one rule on day one: every summary must create at least one task in the system the team already checks. A note that triggers nothing is a note nobody needed.
