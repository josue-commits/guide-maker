# Notion databases

Two databases. The Guide Database is required. The Content Board is optional and unlocks Phase 3d (the post card with copy toggles, DM toggles and the post graphic).

Share both with your integration (database page, `...` menu, Connections, add the integration). `doctor.py` reads both and reports any missing property or select option.

## Guide Database (required)

`notion.guide_database_id`

| Property | Type | Values | Written by |
|---|---|---|---|
| Guide Title | Title | | `publish_guide_hub.py` |
| Type | Select | Technical Tutorial, Strategic Framework, Comparison/Persuasion, Use-case Stack | `publish_guide_hub.py --type` |
| Week | Date | | `publish_guide_hub.py --week` |
| Keyword | Rich text | | `publish_guide_hub.py --keyword` |
| Status | Select | Draft, Review, Published | `publish_guide_hub.py` (Published) |

The select options must match `notion.guide_types` in your config. The fourth type is new in v2; add it or remove it from the config list.

The hub page's cover is set by `banner_generator.py ... --upload-to <page_id>`. Subpages are children of the hub page.

## Content Board (optional)

`notion.content_board_database_id`

| Property | Type | Values | Written by |
|---|---|---|---|
| Title | Title | `KEYWORD \| Mon Jan 05` | `md_to_notion.py create-content-entry` |
| Account | Select | your account names | `--account` |
| Post Date | Date | | `--post-date` |
| Day | Select | Monday, Wednesday, Friday (or your `workflow.post_days`) | `--day` |
| Type | Select | guide | `--type` (default guide) |
| Status | Select | Draft, Review, Published | `--status` (default Draft) |
| Keyword | Rich text | | `--keyword` |
| Guide Link | URL | | `--guide-link` |
| Graphic | Files & media | | `--graphic` (new in v2) |
| Scheduled | Checkbox | | you |
| Impressions | Number | | you or your metrics scraper |
| Comments | Number | | same |
| DMs Sent | Number | | same |
| Notes | Rich text | | you |

New in v2: the `Graphic` property. Calendar and gallery views only surface a files property, so the post graphic is uploaded there and never as an image block in the page body.

Page body layout written by `create-content-entry`:

```
H2  LinkedIn Copy
    Toggle  Contrarian Hook        (code block, plain text)
    Toggle  Problem/Pain Hook
    Toggle  Quantity/Build Hook
Divider
H2  DM Templates
    Toggle  Direct
    Toggle  Combined               (only if community.url is set)
    Toggle  Community only         (only if community.url is set)
    Toggle  Secondary channel      (only if secondary_channel.url is set)
```

## Public URLs

Notion's API cannot publish a page to the web. You do that in the app (Share, Publish). Until then, `https://<your-space>.notion.site/...` returns 404 and any DM that carries it is dead.

Set `notion.public_domain` (for example `yourname.notion.site`) and the skill computes the public URL for you. `md_to_notion.py public-url --page-id <id> --check` does a HEAD request and exits non-zero until the page is live. The DM templates never use `app.notion.com` or workspace `notion.so` links; `lint_copy.py dm` rejects them.

## Finding a database id

Open the database as a full page. The URL looks like `https://www.notion.so/<workspace>/<32 hex characters>?v=...`. The 32 hex characters are the id. Dashes are optional. If the database is inline in another page, open it as a full page first.
