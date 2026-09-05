# Voice and top performers

Two optional files that `setup-guide-maker` writes into `<project>/.guide-maker/`. Each one overrides a shipped reference for this project only; delete the file and the writer falls back to the shipped version.

| File | Overrides | Read by the writer |
|---|---|---|
| `.guide-maker/voice.md` | `make-guide/references/writing/voice.md` | before every draft, for who is speaking |
| `.guide-maker/top-performers.md` | `make-guide/references/linkedin/top-performers.md` | first, ahead of `examples.md`, for the structure that works |

## The three questions

Ask them one at a time. Short answers are fine; the skeleton below turns them into prose.

1. **Who do you sell to?** One line: the role, the company size, the problem they pay to make go away. ("Owners of 5 to 50 person home-service companies who miss calls while on a job.")
2. **How long do your sentences run?** Short punches, longer thoughts, or a mix. Whether you use "I". Whether you swear.
3. **Which words do you never use?** Words the humanizer already bans are covered; this is for the user's own list (jargon they hate, competitor names, a phrase they are tired of). Anything listed here also goes into `copy.extra_banned_words` so the linter enforces it.

## `voice.md` skeleton

```markdown
# Voice

## Who I am talking to

<answer to question 1>

## How I sound

<answer to question 2, as two or three sentences: rhythm, first person, tone>

## Words and phrases I never use

<answer to question 3, one per line>

## Analogies and references I reach for

<optional: the domains the reader already knows; leave empty if unsure>

## What good looks like

<optional: one paragraph, in your own words, that sounds like you. The writer matches its rhythm.>
```

The shipped `voice.md` also carries the humanizer rules (banned vocabulary, banned patterns, no em dashes). Those apply whether or not this override exists, because the linter enforces them; this file adds the person, it does not replace the rules.

## `top-performers.md` skeleton

Empty on purpose at setup. The user fills it after the first two or three weeks of posting, with four to eight of their own posts that followed the keyword-in-graphic rule.

```markdown
# Top performers

Four to eight of my own posts that performed after the keyword moved into the graphic. Newest first.

## <short label>, <YYYY-MM-DD>, <impressions> impressions, <comments> comments

<full post text, exactly as published>

**Why it worked:** <one or two lines: the hook type, the beat that carried it, anything to repeat>
**Closer used:** <the last line>
```

Rules the skeleton carries forward from the shipped file: only the user's own posts; only posts that followed the current rules (a post with an engagement instruction in the copy teaches the wrong structure); only numbers verified in their own analytics.
