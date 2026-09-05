# Top Performers (the template for your slot)

The writer agent reads `<project>/.guide-maker/top-performers.md` before drafting copy, ahead of `examples.md`, so what you put there shapes every post. This shipped file is the template: copy it to `.guide-maker/top-performers.md` in your project and fill it. Do not edit it here; a skill update replaces it, and the writer only reads the project copy once it exists.

## What to put in `.guide-maker/top-performers.md`

Four to eight of **your own** posts that performed after you adopted the keyword-in-graphic rule (see `references/strategy/cta-evidence.md`). For each one:

```
## [Short label], [date], [impressions] impressions, [comments] comments

[full post text, exactly as published]

**Why it worked:** [one or two lines: the hook type, the beat that carried it, anything you would repeat]
**Closer used:** [the last line]
```

Only posts that followed the current rules count. A post that carried `Comment "X"` in the copy tells the agent nothing useful about the structure that works now, even if it did well at the time.

## What not to put here

- Other people's posts. You do not have their voice, and the agent will imitate the wrong things.
- Posts from before the CTA change.
- Metrics you have not verified in your own analytics.

## When it is empty

While `.guide-maker/top-performers.md` does not exist (or is empty), the agent falls back to `examples.md` (three synthetic posts in the house structure, or your `.guide-maker/examples.md` override) for shape and to `voice.md` (shipped, or your `.guide-maker/voice.md`) for voice. Create the project file after your first two or three weeks of posting.
