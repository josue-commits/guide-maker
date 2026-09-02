# Content Board Entries

After publishing the guide, uploading the cover, and generating the post graphic, create the Content Board card.

**Target:** Content Board database (ID from config.yaml) on your Notion workspace.

## Entry Structure

Create one card per guide (`workflow.one_card_per: guide`; `account` makes one per account). Each card contains:

### LinkedIn Copy (3 toggle blocks)
- Toggle title = hook type: "Contrarian Hook", "Problem/Pain Hook", "Quantity/Build Hook"
- Toggle content = code block (plain text) for easy copy/paste
- The keyword is absent from every variation; it lives on the graphic

### DM Templates (below copy)
- Divider
- H2: "DM Templates"
- One H3 toggle per generated DM version (see `references/dm/dm-guide.md`): "Direct" always; "Combined" and "Community only" when `community.url` is set; "Secondary channel" when `secondary_channel.url` is set. Each uses the `dm.merge_tag` placeholder (`{{firstName}}`), never `{name}`.

### Properties to Set

The Content Board database has 14 properties:

| Property | Type | Description |
|----------|------|-------------|
| Title | title | `KEYWORD \| Day MM/DD` |
| Account | select | Account name (from config.yaml) |
| Post Date | date | Scheduled post date |
| Day | select | Monday/Wednesday/Friday |
| Type | select | `guide` (default) |
| Status | select | `Draft` (default; the select must contain it) |
| Keyword | rich_text | Same as guide keyword |
| Guide Link | url | Link to published guide in Guide Database |
| Graphic | files | The post graphic with the CTA band. Attached with `--graphic`, never as a body image block: calendar and gallery views only surface the property |
| Scheduled | checkbox | Whether the post has been scheduled |
| Impressions | number | Post impressions (tracked after posting) |
| Comments | number | Comment count (tracked after posting) |
| DMs Sent | number | DMs sent by the DM tool (tracked after posting) |
| Notes | rich_text | Any additional notes |

## Toggle Format

Toggle blocks use this structure:
- Title = angle name (visible without expanding)
- Content = code block containing the full post text (plain text, easy copy/paste)

This lets each account holder scan the hook lines, pick their favorite variation, and copy-paste it directly.

## Creating the card

```bash
python3 {SKILL_DIR}/scripts/md_to_notion.py create-content-entry --config {SKILL_DIR}/config.yaml \
  --title "KEYWORD | Mon 09/07" --keyword KEYWORD --post-date 2026-09-07 --day Monday \
  --guide-link "https://www.notion.so/..." --status Draft --type guide \
  --variation "Contrarian Hook|@{WORK_DIR}/copy/main-contrarian.txt" \
  --variation "Problem/Pain Hook|@{WORK_DIR}/copy/main-problem_pain.txt" \
  --variation "Quantity/Build Hook|@{WORK_DIR}/copy/main-quantity_build.txt" \
  --dm "Direct|@{WORK_DIR}/dm/direct.txt" \
  --dm "Combined|@{WORK_DIR}/dm/combined.txt" \
  --graphic {WORK_DIR}/graphic.png \
  --dry-run
```

Drop `--dry-run` once the plan looks right. `--variation` and `--dm` take `Label|text` or `Label|@file`. `Guide Link` is the in-app URL (what Notion's copy-link gives you); the public `notion.site` URL belongs in the DMs, not here.

If the Content Board has no `Graphic` property yet, add one of type **files** first; `doctor.py` checks for it.
