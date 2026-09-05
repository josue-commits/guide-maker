# make-guide

## What it does

`make-guide` turns a YouTube URL, a pasted transcript or a researched topic into a published Notion guide and the LinkedIn lead-magnet bundle around it: three copy variations, a cover on the hub page, a post graphic that carries the keyword, DM templates and a Content Board card. It is the orchestrator. A writer agent does the research and the writing in the background; the skill runs the scripts, holds the gates and talks to you.

The keyword never appears in the copy, and the skill never posts to LinkedIn or publishes a page to the web. The copy ends on a value line and the pointing-down emoji, the keyword lives in the graphic's CTA bar, and the linter fails any text that breaks that split. Publishing the Notion page to the web, picking a variation and posting stay with you.

## When to reach for it

Type `/make-guide`, or the agent reaches for it when a task fits: a YouTube URL, a pasted transcript, "make a guide from this", "turn this into a lead magnet", "write the copy for the guide", "publish the guide".

| Your situation | Where to go |
|---|---|
| A YouTube URL, a transcript or a document | `make-guide`, from Phase 1 |
| A topic and no source yet | [topic-finder](./topic-finder.md) first; `make-guide` Phase 0 calls it for you when you say "find me a topic" and then "make a guide about the second one" |
| The guide is already in Notion, you only need copy | `make-guide` Phase 2 with the hub page as the input |
| The post is written, you only need the image | [graphics-maker](./graphics-maker.md) |
| The post is scheduled, you only need the DMs | [dm-automation](./dm-automation.md) |
| Not sure which of those you are in | [ask-guide-maker](./ask-guide-maker.md) |

## Prerequisites

`/setup-guide-maker` has to have run in the project. Without a Guide Database id the publish step is wrong, not fuzzy, so the skill stops and tells you to run it.

| It needs | Where it comes from |
|---|---|
| Config | `.guide-maker/config.yaml`. It reads almost every top-level key: `notion`, `author`, `community`, `secondary_channel`, `accounts`, `workflow`, `topic_finder`, `excluded_topics`, `research`, `sources`, `copy`, `dm`, `brand`, `cover`, `tools` |
| Voice | `.guide-maker/voice.md`, `examples.md`, `top-performers.md` when they exist, else the shipped defaults |
| A Notion token | `NOTION_API_KEY`, or `~/.config/notion/api_key`, or `notion.api_key` |
| Two databases | The Guide Database (required) and the Content Board (optional, unlocks the card). Properties in [notion-databases.md](../notion-databases.md) |
| yt-dlp | Only for transcripts from a URL. Paste the transcript and it is not needed |

## Gates

The word to hold onto is **gate**. Two are yours, the rest the skill holds against itself.

| Gate | Who | When |
|---|---|---|
| G1, the outline | you | Always. Nothing is written before you approve type, title, keyword and the subpage list |
| G2, the content | you | With `workflow.gates: two`, the default. `one` ships the bundle after G1 and asks one consolidated question only when something is ambiguous |
| The cover exists on the hub page | the skill | Before "done" |
| The CTA bar reads character for character like the card's keyword | the skill, then you at feed scale | Before the graphic ships |
| Every lint exits 0, the keyword is unique, no `[Verify: ...]` survives | the skill | Before G2 |

Behind G1 is a depth gate the writer applies to the source: official documentation exists, at least three authoritative sources, one of them long-form, enough material for four to seven subpages. Every URL is opened, every price and claim traced to a primary page, and a gap analysis says what the guide adds that the source did not. Creator videos are research input and never appear under Sources; institutional talks do, with one attribution line. The full rationale is in [strategy.md](../strategy.md).

## What comes back

One work folder, never inside your project: `hub.md` and one file per subpage, three copy files (one hook each: contrarian, problem, quantity), every DM version your config allows, a cover recommendation and a graphic brief. Then, after G2: the hub and subpages in Notion, the cover uploaded, the post graphic from `graphics-maker`, the Content Board card with copy toggles, DM toggles and the graphic on the `Graphic` property, and the DM bundle from `dm-automation`. Each of those steps can be run alone.

## Common questions

**Where did `/guide-maker` go?**

It is `/make-guide` since v3. The folder, the frontmatter name and the slash command all changed; nothing about the scripts or the config keys did. There is no redirect skill, because under `npx skills` a redirect is a second skill in your list. Re-run `npx skills@latest add josue-commits/guide-maker` (or `install.sh`) and pick `make-guide`. The old description also carried "find me a topic"; that trigger now belongs to `topic-finder` alone.

**It refuses to start and says there is no config.**

It looked in five places: an explicit `--config`, `$GUIDE_MAKER_CONFIG`, `.guide-maker/config.yaml` in the current folder or any parent, `~/.config/guide-maker/config.yaml`, and the v2 location inside the skill folder. Run `/setup-guide-maker`. If you have a v2 config, setup offers to move it as its first question.

**It proposed a topic I shipped last month.**

It checks Guide Database titles and Content Board keywords before proposing. If the old guide is in neither, add the keyword or title to `excluded_topics`, or backfill the Guide Database.

**The public link in the DMs returns 404.**

You have not published the page to the web. Notion's API cannot do it; you do it in the app (Share, Publish). `md_to_notion.py public-url --page-id <id> --check` turns green once it is live, and `dm-automation` refuses to schedule until then.

**The writer agent returned nothing and the work vanished.**

It spawned a sub-agent, and a sub-agent's sub-agent dies silently. Every spawn prompt in `SKILL.md` carries "Do NOT spawn sub-agents"; if you edited the prompt, put that line back.

**A `Page icon:` line shows on a published page.**

Authoring directives are stripped at conversion since v2. If the page was published with v1, run `scan_published_leaks.py` to find every affected page and republish those subpages.

**Can it post to LinkedIn for me?**

No, and it will not gain that step; the reasons are in [`.out-of-scope/linkedin-auto-post.md`](../../.out-of-scope/linkedin-auto-post.md). With `dm_tool.provider: leadshark` the post is scheduled through the adapter after you read the payload, which is as close as it gets.

## It's working if

- The doctor's first line names a config under `.guide-maker/` and no line is red before the pipeline starts.
- You are shown an outline with type, title, keyword, subpages and tagged sources, and asked, before a single page exists.
- The copy you get has no keyword in it and ends on a value line with the pointing-down emoji.
- Every URL in the guide opens, and nothing on the page reads `[Verify: ...]`.
- The hub page has a cover with no keyword on it, and the Content Board card carries the graphic on the `Graphic` property, not as an image in the body.
- After a full run, the skill folder is unchanged; everything it wrote is in the work dir or under `.guide-maker/state/`.

## Where it fits

`make-guide` drives the chain: `topic-finder` (Phase 0) feeds it a topic, it writes and publishes, then hands the graphic to [graphics-maker](./graphics-maker.md) at step 3c and the DMs to [dm-automation](./dm-automation.md) at step 3e. [setup-guide-maker](./setup-guide-maker.md) is its precondition, because every id it publishes to comes from the config setup wrote. When you are unsure which entry point matches your situation, [ask-guide-maker](./ask-guide-maker.md) routes you.
