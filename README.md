# Guide Maker

A Claude Code skill that turns YouTube videos into polished, multi-page Notion guides with LinkedIn lead magnet copy.

**Watch the walkthrough:** [How This Skill Works (YouTube)](https://youtu.be/Z1zx4SivZ2Y)

## What You Get

- **Notion guide** with hub page + 4-7 subpages (formatted with headers, code blocks, tables, callouts)
- **3 LinkedIn post variations** per account (Story, Problem/Pain, Data/Framework angles)
- **DM templates** for auto-sending guides to people who comment on your posts
- **AI-generated banner** for the guide cover (optional, via KieAI)
- **Topic research** scanning YouTube channels for trending topics

## How It Works

1. You provide a YouTube URL (or topic)
2. The skill extracts the transcript, researches the topic, and creates an outline
3. You approve the outline
4. It writes the full guide, LinkedIn copy, and DM templates
5. You approve the content
6. It publishes everything to Notion

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)
- Python 3.8+
- A [Notion](https://notion.so) account (free tier works)
- `pip install pyyaml pillow` (for config parsing and banner generation)
- Optional: [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube transcript extraction
- Optional: [KieAI](https://kie.ai) API key for AI-generated banners ($0.03/banner)

## Quick Start

1. Copy this folder into your Claude Code project:
   ```bash
   cp -r guide-maker/ your-project/.claude/skills/guide-maker/
   ```

2. Start Claude Code in your project and say:
   ```
   Make a guide from this video: https://youtube.com/watch?v=...
   ```

3. Claude will detect the skill, notice `config.yaml` is missing, and walk you through setup.

That's it. The skill handles the rest: transcript extraction, research, outline, writing, publishing.

## Notion Database Setup

You need one database (the Guide Database). A Content Board database is optional.

### Guide Database

Create a new database in Notion with these properties:

| Property | Type | Values |
|----------|------|--------|
| Guide Title | Title | (auto) |
| Type | Select | Technical Tutorial, Strategic Framework, Comparison/Persuasion |
| Week | Date | |
| Keyword | Rich Text | |
| Status | Select | Draft, Review, Published |

Share the database with your Notion integration (the one whose API key you'll add to `config.yaml`).

### Content Board Database (Optional)

If you want to track LinkedIn posts and their performance, create a second database with these properties:

| Property | Type | Values |
|----------|------|--------|
| Title | Title | (auto) |
| Account | Select | (your account names) |
| Post Date | Date | |
| Day | Select | Monday, Wednesday, Friday |
| Type | Select | guide, sales-resource |
| Status | Select | Draft, Review, Published |
| Keyword | Rich Text | |
| Guide Link | URL | |
| Scheduled | Checkbox | |
| Impressions | Number | |
| Comments | Number | |
| DMs Sent | Number | |
| Notes | Rich Text | |

## Configuration

Copy `config.example.yaml` to `config.yaml` and fill in your details. The file is well-documented with comments explaining every field.

### Required Fields

- `notion_api_key` -- Your Notion integration token
- `guide_database_id` -- The database ID where guides are stored
- `author_name` -- Your name for the guide byline
- `linkedin_url` -- Your LinkedIn profile URL

### Optional Fields

- `community_url` -- Link to your community (Skool, Discord, Circle, etc.). When set, guides include a community callout at the top of the hub page.
- `content_board_database_id` -- For LinkedIn post tracking and copy delivery
- `kieai_api_key` -- For AI-generated guide banners. Without it, the skill generates simple Pillow banners using your brand colors.
- `accounts` -- For multi-account LinkedIn posting. Each account has a name, voice type (founder/team/company), and CTA type (community/direct).
- `brand_colors` -- Hex codes for Pillow banner generation
- `ytdlp_path` -- Custom path to the yt-dlp binary

## Customization

### Adding Your Writing Voice

Edit `references/writing/voice.md` to describe your writing personality and tone. The agent reads this file before writing any content.

### Adding LinkedIn Post Examples

Edit `references/linkedin/examples.md` with 5-10 of your best-performing LinkedIn posts. The agent uses these to calibrate voice, rhythm, and style.

### Adding YouTube Channels for Topic Research

Edit `channels.json` to add YouTube channels relevant to your niche. The skill scans these when you ask "find me a topic" or "what's trending." Each entry needs a channel ID and name.

### Changing Guide Structure

Edit `references/guides/hub-page-layout.md` to change how guide pages are structured in Notion. This controls the hub page block order, callout placement, and navigation format.

### Adjusting the Humanizer Filter

Edit `references/writing/humanizer.md` to add or remove banned vocabulary and patterns. The default list catches the most common AI writing tells.

## The Pipeline

The skill runs a multi-phase pipeline with user approval gates:

```
Phase 0 (optional): Topic Research
    Scan YouTube channels, cluster topics, score, return briefing

Phase 1: Research + Outline
    Extract transcript, research topic, classify guide type, create outline
    --> USER APPROVAL GATE <--

Phase 2: Write Everything
    Hub page, subpages, LinkedIn copy (3 variations x N accounts), DM templates
    --> USER APPROVAL GATE <--

Phase 3: Publish
    Create Guide Database entry, publish hub + subpages, generate banner

Phase 4 (optional): Content Board
    Create entries with copy + DM templates for each account
```

Each phase can be run independently. You can say "just write the LinkedIn copy" or "just publish the guide" to run specific steps.

## File Structure

```
guide-maker/
├── SKILL.md                           # Orchestrator (Claude Code skill file)
├── AGENT.md                           # Writer agent (spawned for heavy lifting)
├── config.example.yaml                # Configuration template
├── config.yaml                        # Your configuration (git-ignored)
├── README.md                          # This file
├── LICENSE                            # MIT
├── channels.json                      # YouTube channels for topic research
├── scripts/
│   ├── md_to_notion.py               # Markdown to Notion blocks + publishing
│   ├── publish_guide_hub.py          # Hub page + subpages publisher
│   ├── banner_generator.py           # KieAI or Pillow banner generation
│   └── scan_channels.py             # YouTube channel scanner
├── references/
│   ├── writing/
│   │   ├── guide-spec.md            # Full guide creation specification
│   │   ├── humanizer.md             # AI writing patterns to avoid (24 rules)
│   │   └── voice.md                 # Writing personality and tone
│   ├── linkedin/
│   │   ├── linkedin-prompt.md       # Master prompt for LinkedIn copy
│   │   └── examples.md             # Real post examples for voice calibration
│   ├── guides/
│   │   ├── hub-page-layout.md      # Notion hub page block structure
│   │   ├── guide-types.md          # Guide type definitions and criteria
│   │   └── examples/               # Example guides by type
│   └── troubleshooting.md          # Common issues and fixes
└── templates/
    ├── dm-community.md              # DM template for community CTA
    └── dm-direct.md                 # DM template for direct guide link
```

## Tips

- **Start with one account.** You can always add more later in `config.yaml`.
- **Keep your examples.md fresh.** The more representative your examples are, the better the LinkedIn copy matches your voice.
- **Use the topic research phase.** It saves time vs. guessing what to write about. Add 5-10 YouTube channels in your niche and let it find trending topics.
- **Review the outline carefully.** It's much easier to change direction at the outline stage than after 7 subpages are written.
- **Guides live in Notion, not locally.** The skill uses `/tmp/` for intermediate files and publishes directly. No local markdown files to manage.

## License

MIT
