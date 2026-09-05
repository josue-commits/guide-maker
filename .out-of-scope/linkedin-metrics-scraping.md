# Scraping LinkedIn post metrics

The Content Board has `Impressions`, `Comments` and `DMs Sent` columns. The skill does not fill them by scraping LinkedIn. Requests to add a scraper, an Apify actor call, or a browser automation for post analytics are out of scope.

## Why

- Scraping a logged-in LinkedIn session violates the terms the operator agreed to, and the account that pays for it is the operator's.
- Every scraper breaks on the next markup change; the maintenance is permanent and the value is three numbers a week.
- The numbers that decide anything (which hook won, whether the keyword fired) are visible in the LinkedIn post analytics and in the DM tool, and take a minute to copy.

## What to do instead

- Type the three numbers into the card. The columns exist for that.
- With `dm_tool.provider: leadshark`, `dm_cli.py stats --range weekly` returns comments, DMs sent and connections per automation from the adapter's own API, which is data the tool already holds about your account.
- Keep your own metrics pipeline outside the skill and write into the same columns; the property names are in [docs/notion-databases.md](../docs/notion-databases.md).
