# setup-guide-maker

## What it does

`setup-guide-maker` asks the questions the other skills need answered once per project (which Notion databases, whose name and channels, which DM tool, which image provider, which topic sources) and records the answers as files under `.guide-maker/` in your project, plus one `## Agent skills` block in your `CLAUDE.md` or `AGENTS.md`. It ends by running the doctor and does not say "done" while a line is red.

It writes files you can read; the skill files never change. Every answer lands in a commented `config.yaml` or a markdown file you can edit by hand later, and the six skill folders are identical before and after. It is a prompt-driven skill, not a script: it reads what is already there (an existing config, a token in your environment, `yt-dlp` on PATH, a `CLAUDE.md`) and proposes before it writes.

## When to reach for it

You invoke this by typing `/setup-guide-maker`; the agent will not reach for it on its own, and no other skill can fire it.

| Your situation | What to do |
|---|---|
| Fresh install, first guide | Run it once, before anything else |
| Upgrading from v2, config inside the old skill folder | Run it; the first question offers to move the config with `doctor.py --init --from <old>` |
| Switching DM tool or image provider | Run it again, or edit `.guide-maker/config.yaml` directly; both are fine |
| One operator, many project folders | Run it once with the user-level home (`~/.config/guide-maker/`) and skip it in every folder |
| Something stopped working after `npx skills update` | Run the doctor first (`doctor.py`); re-run setup only if it reports a missing or unknown key |

## Prerequisites

| It needs | Notes |
|---|---|
| A Notion integration token | In `NOTION_API_KEY`, in `~/.config/notion/api_key`, or pasted when asked. Without one it prints the three steps to create an integration and pauses |
| The two databases, already created and shared with the integration | It lists them with `doctor.py --list-databases` so you pick, never paste a 32-character id. It does not create databases; missing properties print the table from [notion-databases.md](../notion-databases.md) and stop |
| `pyyaml` and `pillow` | It offers the `pip install` line when the doctor's deps line is not OK |

## The three things it writes

| It writes | Where | What is in it |
|---|---|---|
| `config.yaml` | `.guide-maker/` | Every key from `config.example.yaml`, with its comments kept, and your answers filled in. Secrets are not inlined when an env var or key file already holds them |
| Overrides | `.guide-maker/voice.md`, `top-performers.md`, `topic-finder/*.json` | Only the ones you say yes to. Voice is three questions; topic sources are the example lists copied in, with the `ai-coding` preset offered |
| An `## Agent skills` block | whichever of `CLAUDE.md` / `AGENTS.md` exists | Where the config is, what is set, the sentence to start with, and `/ask-guide-maker` |

The sections it walks, recommended answer first, skipped when something already settled them: config home, Notion, author and accounts, community, secondary channel, DM tool (`manual` recommended; `leadshark` only with a key present), image provider (`none` recommended; `kieai` or `openai` only with a key), gates and workflow, topic sources, voice. Most runs are a handful of confirmations.

## Common questions

**Can I keep the config outside the project?**

Yes. `~/.config/guide-maker/config.yaml` is the fourth place the loader looks, after the project's `.guide-maker/`. Setup calls it the user-level home and offers it when you say you run one operation across many folders. Overrides and state still come from a `.guide-maker/` folder in the project you run in, when one exists; the home only holds the config.

**It wrote to `CLAUDE.md`, but I use Codex.**

It writes the block into whichever of `CLAUDE.md` / `AGENTS.md` exists, asks which to create when neither does, and never writes both. A leftover `CLAUDE.md` from another tool gets the block. Move the block by hand, or make `AGENTS.md` a symlink to `CLAUDE.md`, which is what this repo does for itself.

**It did not create my databases.**

It does not. `--list-databases` lists the databases your integration can see; the property tables in [notion-databases.md](../notion-databases.md) are what you build once in Notion. Creating them through the API is a candidate for a later release, not a promise.

**I have a v2 config. Do I have to answer everything again?**

No. `doctor.py --init --from <old-config>` moves the config, the graphics usage log, the topic-finder JSON lists and any voice file you had edited (detected by diff against the shipped one) into `.guide-maker/`. Setup runs that as its first step and then only asks about what the old config left empty.

**Isn't it strange that a skill configures the other skills?**

The alternative is pasting the same Notion and author questions into every skill that publishes. The mitigation is that the output is plain files: read `config.yaml`, change a key, run the doctor. Day-to-day changes are that, not another run.

## It's working if

- `.guide-maker/config.yaml` exists in your project, with comments, and `doctor.py --print-paths` names it as the config source.
- `doctor.py` prints no FAIL line.
- The `## Agent skills` block is in the instruction file your harness actually reads, and it names the config path.
- `git status` shows `.guide-maker/state/` ignored and `config.yaml` tracked, unless you pasted a secret into it, in which case it is ignored too.
- Nothing under the skill folders changed. If setup edited a `SKILL.md`, something went wrong.

## Where it fits

`setup-guide-maker` is the run-once setup, the precondition rather than a step in the chain. [make-guide](./make-guide.md) and [dm-automation](./dm-automation.md) stop without it, because they publish to ids only the config holds; [graphics-maker](./graphics-maker.md) and [topic-finder](./topic-finder.md) run on defaults without it and get sharper with it. For what to type next, [ask-guide-maker](./ask-guide-maker.md) is the map.
