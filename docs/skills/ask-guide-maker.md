# ask-guide-maker

## What it does

`ask-guide-maker` tells you which skill, and which entry point inside it, fits the situation you are in. It holds the main flow from topic to post, a table of on-ramps for the situations that start in the middle, the things you can run standalone, and the gates you hold yourself.

It maps situations to entry points; it runs nothing. You leave with one sentence to type, not with a guide.

## When to reach for it

You invoke this by typing `/ask-guide-maker`; the agent will not reach for it on its own.

Reach for it when you know what you have (a URL, a scheduled post, a keyword that is taken, a page that leaked a `Page icon:` line) and not which skill takes it from there. If you already know, type the skill.

## On-ramps

The word to hold onto is **on-ramp**: the pipeline is a chain, and most weeks you enter it somewhere other than the start.

| You have | Entry |
|---|---|
| A YouTube URL | `make-guide`, Phase 1 |
| A transcript or a document | `make-guide`, Phase 1, paste it |
| A topic and no source | `topic-finder`, then `make-guide` |
| A post that needs a graphic | `graphics-maker` |
| A keyword that is already taken | `make-guide` picks a new one; `keyword_check.py` confirms |
| A guide in Notion and no copy | `make-guide`, Phase 2 |
| A scheduled post and no DMs | `dm-automation render`, then `schedule` |
| Reach that dropped | Read the copy for the keyword or a "comment" line; `lint_copy.py copy` says which |
| A post that did well and no numbers | `dm-automation stats` with an adapter; otherwise the post's own analytics |
| A published page showing `Page icon:` text | `scan_published_leaks.py`, republish the pages it lists |

The main flow, for the weeks that do start at the start: `topic-finder` (or a URL) into `make-guide` Phase 1, your approval of the outline, Phase 2, your approval of the content, publish and cover, `graphics-maker`, the Content Board card, `dm-automation`, then you publish the page to the web, pick a variation and post. `make-guide` drives the whole chain from one sentence, and every hop can be entered alone.

## Common questions

**Why not ask `make-guide` directly?**

You can, and for the main flow you should. The router exists for the middle of the week: when the question is "which of six things do I run" rather than "run the thing". It also names the gates you hold (outline, content, the keyword in the bar, publishing to the web, posting), so you know what nobody else is going to do.

**It printed the map and stopped.**

That is the whole skill. Copy the sentence it gave you and type it.

## It's working if

- You typed a situation and got one entry point back, with the sentence to say.
- A skill you just installed appears in its map, and one you removed does not.

## Where it fits

`ask-guide-maker` is the map over the other five. [setup-guide-maker](./setup-guide-maker.md) is the precondition it points at first, and [make-guide](./make-guide.md) is where most of its arrows land. Each of the six docs pages is a node; this page is the one the others link back to.
