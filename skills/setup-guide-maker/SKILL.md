---
name: setup-guide-maker
description: "Connect guide-maker to your Notion databases, your name and channels, your DM tool and image provider. Run once per project before the first guide."
disable-model-invocation: true
---

# Setup Guide Maker

Write the per-project configuration the guide-maker skills read:

- **`.guide-maker/config.yaml`**: Notion ids, author, channels, DM tool, image provider, gates
- **`.guide-maker/` overrides**: your voice, your best posts, your topic sources
- **An `## Agent skills` block** in the project's `CLAUDE.md` or `AGENTS.md`, so any agent opening the project knows the config exists

This is a prompt-driven skill, not a script. Explore, present what you found, confirm with the user, then write. The doctor does the file system work; you ask the questions and fill in the answers.

Nothing here edits a skill folder. Every file you write lands in the user's project (or in `~/.config/guide-maker/`), so `npx skills update` never undoes a setup.

## Paths

`SKILLS_ROOT` is the parent of this skill's folder. All six guide-maker skills are installed as siblings, so the doctor is always at:

```
{SKILLS_ROOT}/make-guide/scripts/doctor.py
```

Resolve the absolute path once (`dirname` of this file, then `..`) and use it in every command. The working directory is the user's project, never a skill folder. If `{SKILLS_ROOT}/make-guide/` does not exist, stop: this skill configures `make-guide` and cannot run without it. Tell the user to install the full set (`npx skills@latest add josue-commits/guide-maker`, or `./install.sh <project>` from a checkout).

## Process

### 1. Explore

Read the current state before asking anything. The doctor is the source of truth; the rest is context.

```bash
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py --print-paths --json
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py --offline --json
```

`--print-paths --json` gives you `skill_dir`, `skills_root`, `siblings` (each of the other five, path or `null`), `project_dir` and `config_source`. `config_source` names which search step found a config: an explicit path, `GUIDE_MAKER_CONFIG`, a `.guide-maker/` folder walking up from the working directory, `~/.config/guide-maker/`, the legacy config inside a skill folder, or `null` when there is none.

`--offline --json` gives you the twelve check lines (`config`, `deps`, `notion-token`, `notion-db`, `public-domain`, `cta-mode`, `yt-dlp`, `siblings`, `providers`, `fonts`, `work-dir`, `gitignore`) without touching the network.

Then look at:

- `git remote -v`: is this a git repo, and where does it push? Decides whether a `.gitignore` inside `.guide-maker/` matters.
- `CLAUDE.md` and `AGENTS.md` at the project root: does either exist? Is there already an `## Agent skills` block, and does it already have a `### Guide maker` entry?
- A v2 config: `config_source` says `legacy` when `config.yaml` sits inside a skill folder; also check `~/.config/guide-maker/config.yaml`. Either one is a candidate for `--init --from`.
- The Notion token: the `notion-token` line says whether it came from env `NOTION_API_KEY`, the key file `~/.config/notion/api_key`, or nowhere.
- `yt-dlp` on PATH (the `yt-dlp` line). Not required; it gates transcripts and the YouTube scanner.
- Provider keys (the `providers` line): `LEADSHARK_API_KEY`, `KIEAI_API_KEY`, `OPENAI_API_KEY`, `APIFY_TOKEN`, or their key files under `~/.config/<tool>/api_key`. These decide the defaults in sections F, G and I.

Summarise in six lines or fewer: where the config would live, what is already set, which siblings are installed, which keys are present.

### 2. Present findings and ask

Take the sections in order. One section, one answer, then the next. Lead every section with the recommended answer so the user can accept it in a word. Add a one-line explainer only when the choice genuinely branches. Skip a section entirely when exploration already settled it.

**Section A: Config home.**

> Recommended: `<project>/.guide-maker/`.

The project folder is the default because the folder holds more than one file (topic source lists, overrides, state), it travels with the project, and it keeps Notion ids out of any docs folder. Offer `~/.config/guide-maker/` only when one person runs guide-maker across many folders and wants a single config. Overrides and state still resolve through the project folder either way: a `.guide-maker/voice.md` next to any project is picked up even when `config.yaml` lives at home.

A v2 config was found (inside a skill folder or at `~/.config/guide-maker/`): recommend the move. `doctor.py --init --from <old>` carries the config, the graphics usage log, the topic-finder source lists and any edited voice, examples or top-performers file into the new home. Say what will move before it moves.

**Section B: Notion.**

The Guide Database is required. The Content Board is optional and turns on the post card (copy toggles, DM toggles, the graphic on a files property).

Token. If the `notion-token` line is OK, say where the token came from and move on. If not, the three integration steps:

1. https://www.notion.so/my-integrations, New integration, pick the workspace, capabilities: read, update, insert content. Copy the secret.
2. Create the Guide Database and, optionally, the Content Board. The property tables are in `docs/notion-databases.md` at the repo root (link it, do not paste it): five properties on the Guide Database, fourteen on the Content Board, including the `Graphic` files property.
3. Share each database with the integration: database page, `...`, Connections, add the integration.

Then the token goes in env `NOTION_API_KEY` or the key file `~/.config/notion/api_key`. Recommend the key file when the user is unsure. `notion.api_key` inside `config.yaml` is the last resort, and choosing it adds `config.yaml` to the `.gitignore` (Section 3). Never accept a token pasted into the chat as the value to write; tell the user where to put it and re-run the doctor.

Databases. With a token present:

```bash
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py --list-databases
```

prints every database shared with the integration, with its title and id. The user picks the Guide Database and the Content Board from the list by name; you copy the ids into `notion.guide_database_id` and `notion.content_board_database_id`. A database the user expects to see and does not is one that is not shared yet (step 3 above). Without a token, the user pastes the id from the database URL (the 32 hex characters; `docs/notion-databases.md`, "Finding a database id").

Public domain. Propose `notion.public_domain` from the workspace name (`<workspace>.notion.site`); the user corrects it. This is what lets the DM link be public and what the `public-url --check` command verifies before any DM goes live. Leaving it empty is allowed and the doctor warns every run.

Properties. After the ids are in, run the doctor once more without `--offline`. A `notion-db` FAIL naming missing or wrong-typed properties means the database does not match the table yet. Print the pointer to `docs/notion-databases.md` and stop this section until the user has fixed the database; do not continue to Section C with a red `notion-db` line.

`notion.guide_types` must match the options on the Guide Database `Type` select. The doctor checks it; if the user's select has fewer options, offer to trim the list rather than edit the database.

**Section C: Author and accounts.**

> Recommended: your name as the byline, your LinkedIn URL, `voice: founder`, one account.

`author.name` and `author.linkedin_url` are the hub byline. `author.voice` is `founder | team | company`; founder unless the posts go out under a company page. `author.dm_signoff` is the bare first name at the end of every DM; empty means `author.name`. Keep `accounts:` at one entry unless the user says a team posts the same guide; then one entry per person with its own voice and `dm_destination`, and `workflow.one_card_per: account`.

**Section D: Community.**

> Recommended when unsure: leave `community.url` empty.

An empty URL means no callout on the hub page and no community DM versions, which is the right default until there is a community worth sending people to. When there is one: `community.platform` (`skool | discord | circle | slack | none`), `community.name` (the link text), `community.url`, and `community.callout_line`. The callout line never claims a bigger number than the community has.

**Section E: Secondary channel.**

> Recommended when unsure: leave `secondary_channel.url` empty.

Empty means no credit line under the byline and no secondary-channel DM version. When there is one: `secondary_channel.type` (`youtube | newsletter | podcast | none`), `handle`, `url`, `credit_line`.

**Section F: DM tool.**

> Recommended: `dm_tool.provider: manual`.

Manual writes a paste-ready bundle and a checklist for whatever tool the user already has; it never opens a socket. Offer `leadshark` only when the `providers` line shows a LeadShark key present; without a key the adapter cannot do anything. Leave `dm.merge_tag` at the default (`{{firstName}}`) unless the user's tool substitutes a different tag; the linter rejects `{name}` and `[Name]` because they reach the lead as literal text. `dm_tool.timezone` is the zone the checklist prints local times in; default to the user's zone.

**Section G: Image provider.**

> Recommended: `graphics.provider: none` and `cover.mode: simple`.

`none` means a Pillow title card with the CTA bar, free, always works, and the smoke test exercises it. Offer `kieai` or `openai` only when the matching key is present. Either way the CTA bar is typeset locally (`graphics.cta_bar.renderer: pillow`), so the keyword cannot come out misspelled. Brand colors and fonts (`brand.colors`, `brand.fonts`) are optional; the bundled Inter is used when the font paths are empty.

**Section H: Gates and workflow.**

> Recommended: `workflow.gates: two`.

Two stops the pipeline after the outline and again after the content, before anything reaches Notion. One stops only after the outline and ships the bundle with defaults; pick it once the first few guides have taught you what the writer does with your voice. Then `workflow.language` (the language of the shipped guide, copy and DMs), `workflow.post_days` (the day names that appear on the board card), and `workflow.work_dir` (where intermediate files go, never the project; keep the default unless the user has a reason).

**Section I: Topic sources.**

Skip this section when `siblings.topic-finder` is `null`; say so in one line and move on. The rest of the pipeline runs from a URL or a transcript without it.

With topic-finder installed, the source lists live in `<config home>/topic-finder/`: `youtube-channels.json`, `subreddits.json`, `x-accounts.json`, and the optional `topics.json`. Offer the `ai-coding` preset when the niche is AI coding or AI dev tools:

```bash
cp {SKILLS_ROOT}/topic-finder/config/youtube-channels.ai-coding.example.json <home>/topic-finder/youtube-channels.json
cp {SKILLS_ROOT}/topic-finder/config/subreddits.ai-coding.example.json     <home>/topic-finder/subreddits.json
cp {SKILLS_ROOT}/topic-finder/config/x-accounts.example.json               <home>/topic-finder/x-accounts.json
```

For any other niche, copy the generic `*.example.json` files and tell the user to edit them: 8 to 15 channels each tagged `tool` or `business`, 8 to 15 subreddits, 5 to 10 X accounts. Reddit and X need an Apify token (`APIFY_TOKEN` or `~/.config/apify/api_key`); without one, set `topic_finder.sources: [youtube]` so the scan does not fail on a source it cannot reach. Ask for `excluded_topics` in the same breath: competitors and subjects the user never wants proposed.

**Section J: Voice.**

> Recommended: yes to `voice.md`, and an empty `top-performers.md` to fill after the first two or three weeks of posting.

Ask the three questions in [voice-template.md](./voice-template.md): who you sell to, how long your sentences run, words you never use. Write the answers into `<project>/.guide-maker/voice.md` using the skeleton there; it overrides the shipped `references/writing/voice.md` for this project only. Write the `top-performers.md` skeleton next to it. Neither file is required; the writer falls back to the shipped references when they are absent.

### 3. Confirm and edit

Show the user a draft of:

- The `config.yaml` that will be written. Keep the comments from `config.example.yaml`; the user reads this file later. Show secrets as the source they come from (`env NOTION_API_KEY`, `~/.config/notion/api_key`), never a value.
- The `.guide-maker/.gitignore`: `state/` always; `config.yaml` too, only when a secret was inlined in Section B.
- The `## Agent skills` block from [agent-skills-block.md](./agent-skills-block.md) with the placeholders filled.
- The overrides that will be created: `voice.md`, `top-performers.md`, the topic-finder JSON files.

Let them edit before anything is written.

### 4. Write

Run the doctor's init for the home the user chose:

```bash
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py --init --project /absolute/path/to/project
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py --init --home
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py --init --project /absolute/path/to/project --from /absolute/path/to/old/config.yaml
```

`--init` writes the folder skeleton (`config.yaml` from the example, `topic-finder/`, `formats/`, `state/`, `.gitignore`). With `--from` it starts from the old config instead and moves the usage log, the topic-finder source lists and any edited reference files with it.

Then apply the answers from Section 2: edit the values in place in the written `config.yaml` (leave every comment and every key you did not discuss), write `voice.md` and `top-performers.md` if Section J said yes, copy the topic-finder presets if Section I ran, and add `config.yaml` to the `.gitignore` only if a secret was inlined.

**Pick the file for the block:**

- If `CLAUDE.md` exists at the project root, edit it.
- Else if `AGENTS.md` exists, edit it.
- If neither exists, ask the user which one to create; do not pick for them.

Never create `AGENTS.md` when `CLAUDE.md` already exists, or the reverse. If an `## Agent skills` block is already there, update the `### Guide maker` entry in place (or add it under the existing heading) rather than appending a second block. Do not touch the sections around it.

If the `deps` line was not OK in step 1, offer `pip install pyyaml pillow` now. Nothing else is required; the optional tools each gate one feature and the doctor names them.

### 5. Verify

Run the full doctor, online:

```bash
python3 {SKILLS_ROOT}/make-guide/scripts/doctor.py
```

Every FAIL gets fixed before you say "done"; WARN lines are read out with what each one gates (no Content Board, no public domain, no yt-dlp) and left to the user. The `config` line should now name the new home, not the legacy location.

Then print the three sentences that start a guide, and stop:

```
make a guide from this video: <url>
make a guide about <topic>, here is the transcript: <paste>
find me a topic
```

Mention that the config is a plain file they can edit by hand, and that re-running this skill is only for switching Notion databases, changing the DM tool or provider, or moving the config home. Unsure which skill fits a situation: `/ask-guide-maker`.

## Files in this folder

- [agent-skills-block.md](./agent-skills-block.md): the block written into `CLAUDE.md` or `AGENTS.md`, with placeholders
- [voice-template.md](./voice-template.md): the `voice.md` and `top-performers.md` skeletons, with the three questions
