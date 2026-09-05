# Guide Maker

[![skills.sh](https://skills.sh/b/josue-commits/guide-maker)](https://skills.sh/josue-commits/guide-maker)

Six agent skills that turn a YouTube video, a transcript or a trending topic into a published Notion guide, a LinkedIn lead-magnet post with its graphic, and the DMs that deliver the guide to the people who comment. One rule shapes everything: **the keyword lives in the post graphic, never in the copy.** LinkedIn suppresses posts whose text asks for engagement. The same graphic and guide went from 95 to 11,432 impressions when the keyword left the copy; a post that carried `Comment "KEYWORD"` did 43 the week after one did 62,000. The skills write copy that ends on a value line, put the keyword in a CTA bar on the image, and lint anything that breaks the rule. The rest of the rationale is in [docs/strategy.md](docs/strategy.md).

![Pipeline](docs/pipeline.png)

Editable source: [docs/pipeline.drawio](docs/pipeline.drawio) (open at app.diagrams.net).

## Installation (30-second setup)

<!-- install-block:start -->
Two ways in, one result: six skills in your project, as files you own. **[skills.sh](https://skills.sh/josue-commits/guide-maker)** copies them in and updates them with one command; it needs Node. **`install.sh`** does the same from a clone, with no Node. Pick one: installing both leaves every skill twice.

### 1. Get the skills

<details>
<summary><strong>Claude Code, Codex and other agents</strong></summary>

```bash
npx skills@latest add josue-commits/guide-maker
```

The installer lets you choose which skills to take. Take all six, or at least `setup-guide-maker` and `make-guide`. Then the two Python dependencies:

```bash
pip install pyyaml pillow
```

Update later with `npx skills update`.

</details>

<details>
<summary><strong>No Node</strong></summary>

```bash
git clone https://github.com/josue-commits/guide-maker.git
cd guide-maker && ./install.sh /path/to/your/project
pip install pyyaml pillow
```

`install.sh` copies the six skills into `/path/to/your/project/.claude/skills/`. Re-run it after `git pull` to update.

</details>

### 2. Run `/setup-guide-maker`

In your agent, inside the project, once. It asks about your Notion databases (picked from a list, never pasted as ids), your name and LinkedIn URL, your community and secondary channel, your DM tool, your image provider and your topic sources. It writes `.guide-maker/` in the project and an `## Agent skills` block in your `CLAUDE.md` or `AGENTS.md`, then runs the doctor and stops only when every line is green.

### 3. Say it

```
make a guide from this video: <url>
make a guide about <topic>, here is the transcript: <paste>
find me a topic
```

Bam. The skill runs the pipeline, stops for your approval at the outline and again at the content, and hands you the bundle.
<!-- install-block:end -->

## What you get per guide

- A Notion guide: hub page plus 4 to 7 subpages, with a cover image.
- Three LinkedIn post variations (contrarian, problem, quantity hooks), 180 to 250 words, no keyword in the text.
- A post graphic with the keyword CTA bar. Free with Pillow, or generated through an image provider.
- DM templates for every destination you configure: direct link, community, secondary channel.
- A Content Board card with the copy toggles, DM toggles and the graphic on a files property.
- Optional: trending-topic research across YouTube (two tracks), Reddit and X, correlated, with a health gate.

## Why these skills exist

Each one exists because a week went wrong in a specific way.

### #1: The post got 43 impressions

**The problem.** The copy ended with `Like this post 👍 / Comment "KEYWORD"`. That closer is an engagement instruction, and LinkedIn shows the post that asks the most to the fewest people. The week before, the same account had done 62,000 on a post without it.

**The fix.** The keyword has one carrier, the post graphic. [`graphics-maker`](skills/graphics-maker/SKILL.md) typesets it in a full-width bar across the bottom edge, from real glyphs, so it cannot come out misspelled; `lint_copy.py` fails any copy that contains the keyword, `Comment "`, "Like this post" or "Repost this". The numbers behind the rule are in [docs/strategy.md](docs/strategy.md).

### #2: I did not know what to write about this week

**The problem.** A blank Monday, a search engine's top ten, and a guide on whatever paid for placement. Or a topic that was shipped two months ago under a different name.

**The fix.** [`topic-finder`](skills/topic-finder/SKILL.md) scans the channels, subreddits and X accounts you chose, in two YouTube tracks scored apart and with X ranked on bookmarks rather than views, and correlates them: a topic on two sources in one week is the signal. A health gate stops the run when a source is dead instead of filling the gap with web search, and `make-guide` checks Guide Database titles and Content Board keywords before proposing anything.

### #3: The guide was thin, or made things up

**The problem.** Four subpages that restate one video, a price that changed last quarter, a feature the tool never had.

**The fix.** [`make-guide`](skills/make-guide/SKILL.md) applies a depth gate before the outline (official docs exist, three authoritative sources, one of them long-form, enough for four to seven subpages), opens every URL, traces every claim to a primary page, and writes a gap analysis saying what the guide adds. Creator videos are research input and never appear under Sources. You approve the outline before a page is written, always.

### #4: It read like a robot wrote it

**The problem.** "Delve", "game-changer", an em dash every third line, the same closer three weeks running, a voice that belonged to nobody.

**The fix.** The humanizer runs on every sentence with no switch to turn it off. Your own voice comes from three files you own in `.guide-maker/`: `voice.md`, `examples.md` (your real posts) and `top-performers.md` (your best ones, with numbers). `lint_copy.py rotation` flags a closer repeated across weeks. [docs/customizing.md](docs/customizing.md) has the three files.

### #5: The DM went out with a dead link and "{name}"

**The problem.** The guide link was the one Notion's copy button gives, which gates on workspace membership, so every commenter got a 404. The DM opened with a literal `{name}`. The paragraph had been hard-wrapped and read like a broken paste.

**The fix.** [`dm-automation`](skills/dm-automation/SKILL.md) renders every DM version from templates and lints them: the merge tag has to be the one your tool substitutes, the link has to be the public `notion.site` one and has to answer 200 before anything is scheduled, no hard wraps, no em dashes. Manual is the default: a bundle and a checklist you follow in your own tool. An adapter (LeadShark ships) schedules the post with the graphic and the keyword automation attached, created paused.

## Reference

These split on one axis: who can invoke them. **User-invoked** skills are reachable only when you type them; they orchestrate or map. **Model-invoked** skills can be typed or reached for by the agent when a task fits; they hold the work. A user-invoked skill may call model-invoked ones, never the reverse. Each entry links the skill and its page.

### Pipeline

**User-invoked**

- **[setup-guide-maker](skills/setup-guide-maker/SKILL.md)** ([page](docs/skills/setup-guide-maker.md)): Connect the skills to your Notion databases, your name and channels, your DM tool and image provider. Run once per project before the first guide.
- **[ask-guide-maker](skills/ask-guide-maker/SKILL.md)** ([page](docs/skills/ask-guide-maker.md)): Ask which skill and which entry point fits your situation. A map over the set; it runs nothing.

**Model-invoked**

- **[make-guide](skills/make-guide/SKILL.md)** ([page](docs/skills/make-guide.md)): Turn a URL, a transcript or a topic into the Notion guide and the lead-magnet bundle around it: three copy variations, cover, post graphic, DMs, Content Board card. Drives the whole chain from one sentence.
- **[topic-finder](skills/topic-finder/SKILL.md)** ([page](docs/skills/topic-finder.md)): Scan YouTube, Reddit and X for what your niche is talking about, correlated, with a health report. Phase 0 of the chain and a standalone.

### Assets

**Model-invoked**

- **[graphics-maker](skills/graphics-maker/SKILL.md)** ([page](docs/skills/graphics-maker.md)): The post graphic with the keyword CTA bar. Pillow card at zero cost, or two-pass generation through an image provider. Content Credentials stripped.
- **[dm-automation](skills/dm-automation/SKILL.md)** ([page](docs/skills/dm-automation.md)): The DM bundle and checklist, or scheduling through an adapter. Keyword checks, link checks, merge-tag lint.

## The pipeline

| Step | What happens | Who |
|---|---|---|
| 0 | Topic research: three sources scanned, health-checked, correlated, filtered | `topic-finder` |
| 1 | Transcript, research, every URL and price verified, gap analysis, outline, keyword | writer agent |
| G1 | Approve the outline | you |
| 2 | Guide, three copy variations, DM templates, lint until clean | writer agent |
| G2 | Approve the content (`workflow.gates: two`, the default) | you |
| 3 | Publish hub and subpages, cover on the hub, leak scan, Content Board card | `make-guide` |
| 4 | Post graphic with the CTA bar; DM bundle rendered, or scheduled through an adapter | `graphics-maker`, `dm-automation` |
| | Publish the Notion page to the web, pick a variation, post | you |

Every phase can run alone. Unsure where you are: `/ask-guide-maker`.

## Configuration

`/setup-guide-maker` writes one folder in your project. Nothing is ever written inside a skill folder, so `npx skills update` cannot take your settings with it.

```
.guide-maker/
  config.yaml            every key, commented; the same keys as v2 plus an optional paths: block
  voice.md               optional: who you are, for the writer
  examples.md            optional: your real posts, for rhythm
  top-performers.md      optional: your best posts with numbers, for structure
  topic-finder/          the channel, subreddit and X account lists the scanners read
  formats/               your own graphic format cards
  state/                 closer and format logs (gitignored)
  .gitignore
```

Secrets never need to be in the file: an env var wins, then `~/.config/<tool>/api_key`, then `config.yaml`. The doctor tells you where each one came from. Everything you can bend, from the word range to a second LinkedIn account to your own image provider, is in [docs/customizing.md](docs/customizing.md).

## Upgrading from v2

Your v2 config still loads from inside the old skill folder, with one deprecation line. `doctor.py --init --from <old-config>` moves it, the logs and the topic lists into `.guide-maker/`, and `/setup-guide-maker` offers the same move as its first question. `/guide-maker` is `/make-guide` now. See [MIGRATION.md](MIGRATION.md) and [CHANGELOG.md](CHANGELOG.md).

## Repository layout

```
install.sh                    the no-Node route: copies skills/* into a project
skills/setup-guide-maker/     SKILL.md, agent-skills-block.md, voice-template.md
skills/ask-guide-maker/       SKILL.md, FLOWS.md
skills/make-guide/            SKILL.md, AGENT.md, config.example.yaml, scripts/, references/, templates/, assets/fonts/
skills/topic-finder/          git subtree of josue-commits/topic-finder, pinned to a tag; edit upstream
skills/graphics-maker/        SKILL.md, scripts/ (providers/, cta_bar.py, strip_credentials.py), references/format-library/
skills/dm-automation/         SKILL.md, scripts/ (dm_cli.py, adapters/), references/
skills/README.md              the six skills, grouped
docs/                         skills/ (one page each), strategy, customizing, notion-databases, troubleshooting, pipeline diagram
.agents/                      maintainer conventions: install block, invocation, writing docs, config contract, release, ADRs
.out-of-scope/                what the repo will not do, and why
tests/                        smoke test and fixtures (no tokens, no network)
scripts/                      check_version.py, list-skills.sh
```

`CLAUDE.md` (and `AGENTS.md`, a symlink to it) states the invariants a change has to keep.

## Background

Built by [Josue Hernandez](https://www.linkedin.com/in/josue-hernandez04) to run a three-guides-a-week LinkedIn lead-magnet operation, then rewritten for anyone to adapt. The [original walkthrough video](https://youtu.be/Z1zx4SivZ2Y) shows v1: the pipeline is the same shape, but the CTA it demonstrates (keyword in the copy) is the one v2 removed, and the install it shows predates the setup skill. [docs/strategy.md](docs/strategy.md) has what changed and why.

## License

MIT. Fonts under `skills/make-guide/assets/fonts/` are Inter, SIL Open Font License.
