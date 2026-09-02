# Sources Policy

What the reader sees under "Sources" on the hub page, and what stays research material. Config: `sources.*`.

## Creator videos are never cited. Institutional talks are.

The reader should only see authoritative, evergreen sources: official docs, changelogs, repos, the tool's own site, blog posts, **and first-party or institutional talks**. If the only place a fact came from was a creator video, verify it against an official source and cite that instead.

The line is who gives the talk its weight:

| Citable (`institutional`) | Not citable (creator research only) |
|---|---|
| A university lecture | A YouTuber's tutorial or review |
| A course published by the vendor of the tool | A channel's "10 tips" or "X vs Y" video |
| A workshop run by the company that builds the tool | A creator's build-along or reaction |
| A talk by a named-role engineer at a named institution | A creator restating someone else's talk |
| A conference or research-lab talk | Anything whose authority rests on the channel |

Test: does the reader trust this because of **where it was given or who published it**, or because of **whose channel it is**? The first is a primary source. The second is research material.

`publish_guide_hub.py` enforces the default: `--source "youtube|..."` and other creator-channel types are refused unless `sources.cite_creator_videos: true`. Accepted types: `official`, `institutional`, `blog`, `pdf`, `repo`, `docs`, `changelog`, `paper`, `article`, `course`.

## Say so in the body when the guide rests on an institutional lecture

It raises credibility and gives readers somewhere to go. One line, placed where it earns trust, plus the link under Sources as an optional deep-dive:

```
This comes out of a one-hour university lecture by engineers who worked on the
tool. The walkthrough below is the practical version. If you want the full
lecture, it is linked at the bottom.
```

Attribution style: name the **institution and the role**, not the individual, unless the individual is a widely known founder. "An engineer at the company that builds the tool" and "the vendor's own course" are right. A rank-and-file speaker's personal name is not.

## No cross-guide references in the published body

`sources.cross_guide_references: false` (default). The gap analysis and any "what is new versus our past guides" reasoning are internal tools for the writer and the orchestrator. They never go into the guide. Do not write "Our earlier guide covered...", "If you read the PLUGINS guide...", "unlike our previous walkthrough", or any heading or paragraph that names another guide or its keyword.

Most readers arrive cold from a single post and have zero context on anything else you published. Each guide stands completely on its own. Self-references inside the same guide ("this is the pattern the whole guide is built on") are fine.

## No authoring directives on the page

A line like `**Page icon:** X` at the top of a subpage is a note to the publisher, not content. `md_to_notion.py` strips every shape of it, and `scan_published_leaks.py` sweeps every published page for the ones that got through (directives, `[Verify: ...]` placeholders, unfilled `[Notion link]` slots, `[Name]` merge tags, TODOs). Run the scanner after any change to the publisher.
