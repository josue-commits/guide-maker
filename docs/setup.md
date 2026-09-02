# Setup

Ten minutes if you already have a Notion account. Everything past the REQUIRED block is optional and can be added later.

## 1. Install

```bash
git clone https://github.com/josue-commits/guide-maker.git
cd guide-maker
./install.sh /path/to/your/project        # or: ./install.sh --global
pip install -r requirements.txt           # pyyaml, pillow
```

`install.sh` copies `skills/guide-maker`, `skills/graphics-maker` and `skills/dm-automation` into `<project>/.claude/skills/`, fetches `topic-finder` next to them, creates `config.yaml` from the example if it does not exist, and runs the doctor.

Optional tools, install only what you will use:

| Tool | Needed for | Install |
|---|---|---|
| yt-dlp | YouTube transcripts and the YouTube scanner | `brew install yt-dlp` or `pip install yt-dlp` (2026.07.04 or newer for `--flat`) |
| Apify token | Reddit and X scanners in topic-finder | https://console.apify.com/account/integrations, export `APIFY_TOKEN` |
| KieAI or OpenAI key | AI-generated cover and post scenes | `KIEAI_API_KEY` or `OPENAI_API_KEY`; `pip install -r requirements-optional.txt` for OpenAI |
| LeadShark key | Scheduling posts and keyword automations through the adapter | `LEADSHARK_API_KEY` |

Without any of them the pipeline still runs end to end: paste a transcript, get a guide, a Pillow cover, a Pillow post graphic with the CTA bar, three copy variations and a DM bundle with a checklist.

## 2. Notion integration

1. https://www.notion.so/my-integrations, New integration, pick the workspace, capabilities: read, update, insert content. Copy the secret (starts with `ntn_`).
2. Create the Guide Database and, optionally, the Content Board. Property tables are in `notion-databases.md`.
3. Share each database with the integration (database page, `...`, Connections).
4. Put the secret in one of three places, in order of preference: env var `NOTION_API_KEY`, key file `~/.config/notion/api_key`, or `notion.api_key` in `config.yaml`.

## 3. Config

`<skills>/guide-maker/config.yaml`. Every key is commented in `config.example.yaml`. The six most people touch:

```yaml
notion:
  guide_database_id: ""        # required
  content_board_database_id: "" # optional, unlocks the post card
  public_domain: ""             # e.g. yourname.notion.site; lets the skill build public DM links
author:
  name: ""                      # byline
  linkedin_url: ""              # byline link
community:
  url: ""                       # leave empty for no community callout and no community DM versions
```

Secrets never need to be in the file. `doctor.py` tells you where it found each one.

## 4. Doctor

```bash
python3 <skills>/guide-maker/scripts/doctor.py
```

Twelve lines, each `OK`, `WARN`, `FAIL` or `SKIP`. Read the FAIL lines first; the skill refuses to start a pipeline while any is red. Typical first-run output:

```
OK    config      skills/guide-maker/config.yaml (schema 2)
OK    python      3.12.4, Pillow 10.4, PyYAML 6.0
OK    notion      token from env NOTION_API_KEY; user: Your Name
OK    guide db    5 properties, 4 types
WARN  board       content_board_database_id empty: Phase 3d (post card) disabled
WARN  public url  notion.public_domain empty: DMs will carry workspace links until you set it
OK    yt-dlp      2026.08.12 at /opt/homebrew/bin/yt-dlp
OK    topic-finder ../topic-finder (youtube: 8 channels in 2 tracks; reddit: 6 subs; x: no config, disabled)
OK    graphics    provider none (Pillow card); sibling ../graphics-maker
OK    dm tool     manual; sibling ../dm-automation
OK    fonts       bundled Inter-Bold.ttf renders the CTA string
OK    work dir    /tmp/guide-maker writable
```

`doctor.py --offline` skips every network check (useful on CI). `doctor.py --print-paths` prints the absolute skill and sibling paths the orchestrator pastes into agent prompts. `doctor.py --migrate-config` turns a v1 `config.yaml` into the v2 layout.

## 5. First run

Start Claude Code in the project and say one of:

```
Make a guide from this video: https://youtube.com/watch?v=...
Make a guide about <topic>. Here is the transcript: <paste>
Find me a topic
```

The skill runs Phase 1, shows you the outline (gate 1), writes everything, shows you the bundle (gate 2 unless `workflow.gates: one`), publishes to Notion, makes the cover and the post graphic, creates the Content Board card if configured, and renders the DM bundle. You then publish the Notion page to the web, pick a variation, and post.

## 6. Platform notes

- macOS: nothing extra. Poppins or Helvetica Neue are used for the cover if installed, otherwise the bundled Inter.
- Linux: `sudo apt install fonts-dejavu` is a fine fallback; the bundled Inter is used first. yt-dlp from pip.
- Windows: use WSL. Native Windows works for everything except `install.sh` (copy the `skills/` folders by hand).
- Fresh machine, no fonts, no keys: `bash tests/run_smoke.sh` must pass. If it does not, open an issue with the output.
