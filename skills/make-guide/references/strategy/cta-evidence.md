# The keyword lives in the graphic, never in the copy

This is the one rule in the repo that outranks everything else about LinkedIn copy. Read it before writing a post, and read it again if you are tempted to put `Comment "X"` back into the text.

## What changed

LinkedIn suppresses the reach of posts whose copy carries an engagement instruction. "Comment X to get it", "Like this post", "Repost for early access", a numbered 1-2-3 block: any of them, and the post is throttled before the first hour is over. The pattern that built the lead-magnet playbook in 2024 and 2025 now kills the post that uses it.

The fix is mechanical. The copy says the thing is free and points down. The graphic carries the instruction. The reader gets the offer from the text and the keyword from the image, and the auto-DM tool still watches the comments for the keyword exactly as before.

## The two numbers

These come from one operator's account, measured in August 2026. They are not a study. They are the reason this repo defaults the way it does.

| What | Copy | Impressions |
|------|------|-------------|
| Same graphic, same guide, reposted with the keyword moved out of the copy and into the image | `Comment "X" and I'll send it` | 95 |
| | Value line + pointing-down emoji, keyword in the graphic only | 11,432 |
| The account's own post the week after a 62,000-impression post | copy carried `Comment "SKILLS"` | 43 |

Same asset, 95 to 11,432. Same account, 62,000 to 43. Nothing else about the posts changed.

Treat these as strong evidence for a default, not as a law. If your account behaves differently, `copy.cta_mode: copy` exists so you can test it. The linter and the doctor will remind you what the numbers were every time it is on.

## What the copy is allowed to do

The last line of every lead-magnet post is one value line ending in the pointing-down emoji:

```
[Value line]. 👇
```

That is the entire CTA. No second line, no instruction, no keyword, no thumbs-up emoji.

Seven closers are sanctioned by default (`copy.closers` in the config). Rotate them: never close all three variations of one week on the same line, and never run the same closer three weeks straight. A closer that repeats verbatim reads as a template to anyone who follows the account.

```
Free Access 👇
Get free access 👇
Get access for free 👇
I'm giving away the complete guide for free 👇
I'm giving away the complete guide. For free. 👇
The guide and the full setup are free 👇
Give me a shout if you want the full setup 👇
```

## What is banned in the copy

Any of these gets the post suppressed and fails `lint_copy.py` in graphic mode:

- `Comment "KEYWORD"` in any form, including "and I'll send it your way" and "DM me"
- The keyword itself, anywhere in the text, even inside a sentence
- "Like this post", "Connect with me", "Repost this to get early access"
- Any numbered instruction block ("1. Connect + like 2. Comment")
- The thumbs-up emoji. The only emoji allowed is the pointing-down one, and only as the final character

## Where the keyword goes instead

The post graphic carries a full-width band across its bottom edge with one of two canonical strings. Use the primary unless the layout physically cannot fit it.

```
COMMENT "[KEYWORD]" TO GET IT FOR FREE
```

```
Comment "[KEYWORD]" for the guide
```

Do not invent a third phrasing. The band is the only capture mechanism the post has, so it is a release gate: read the rendered keyword character by character before the post ships. `ENGNE` instead of `ENGINE` silently breaks the auto-DM trigger, and the copy can no longer save it because the copy does not mention the keyword at all.

The band goes on the **post graphic** only. The Notion cover never carries the keyword; it is a different asset with a different job (see `references/banner-guide.md`).

## `copy.cta_mode: copy`

Set it if you want to test the old pattern on your own account. When it is on:

- the writer agent puts the keyword in the last line as `Comment "KEYWORD" and I'll send it 👇`
- `lint_copy.py copy` downgrades `keyword-in-copy` and `old-cta` from failures to warnings and prints the two numbers above
- `doctor.py` shows a WARN line with the same numbers every run

Nothing else changes. The graphic still gets its band, so switching back is a one-line config edit.
