# Content Board Entries

After publishing the guide, generating the banner, and embedding screenshots, create Content Board entries for each LinkedIn account.

**Target:** Content Board database (ID from config.yaml) on your Notion workspace.

## Entry Structure

Create one entry per account (accounts from config.yaml). Each entry contains:

### LinkedIn Copy (3 toggle blocks)
- Toggle title = hook type: "Contrarian Hook", "Problem/Pain Hook", "Quantity/Build Hook"
- Toggle content = code block (plain text) for easy copy/paste
- CTA pre-baked per account:
  - Primary account (owner): community link (if configured in config.yaml)
  - Other accounts: Direct Notion guide link

### DM Templates (below copy)
- Divider
- H2: "DM Templates"
- One H3 toggle per generated DM version (see `references/dm/dm-guide.md`): "Direct" always; "Combined" and "Community only" when `community.url` is set; "Secondary channel" when `secondary_channel.url` is set. Each uses the `dm.merge_tag` placeholder (`{{firstName}}`), never `{name}`.

### Properties to Set

The Content Board database has 14 properties:

| Property | Type | Description |
|----------|------|-------------|
| Title | title | Post title |
| Account | select | Account name (from config.yaml) |
| Post Date | date | Scheduled post date |
| Day | select | Monday/Wednesday/Friday |
| Type | select | guide/sales-resource |
| Status | select | Draft |
| Keyword | rich_text | Same as guide keyword |
| Guide Link | url | Link to published guide in Guide Database |
| Graphic | files | Post graphic (uploaded separately) |
| Scheduled | checkbox | Whether the post has been scheduled |
| Impressions | number | Post impressions (tracked after posting) |
| Comments | number | Comment count (tracked after posting) |
| DMs Sent | number | DMs sent via auto-DM tool (tracked after posting) |
| Notes | rich_text | Any additional notes |

## Toggle Format

Toggle blocks use this structure:
- Title = angle name (visible without expanding)
- Content = code block containing the full post text (plain text, easy copy/paste)

This lets each account holder scan the hook lines, pick their favorite variation, and copy-paste it directly.

## Creating Entries

Use `scripts/md_to_notion.py` create_content_entry() function or direct API calls with /tmp/ JSON files for complex payloads.
