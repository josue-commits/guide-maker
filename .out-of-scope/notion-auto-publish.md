# Publishing a Notion page to the web from the skill

The skill creates the hub page and the subpages, sets the cover and writes the Content Board card. It does not publish the page to the web. Requests to add that step are out of scope, because it cannot be done.

## Why

Notion's API has no endpoint that publishes a page to the web. The switch lives in the app (Share, Publish) and nowhere else. Every "auto-publish" implementation would be a browser automation against the Notion UI, which breaks on every redesign and needs the operator's session.

## What to do instead

- The operator publishes the page from the Notion app once per guide.
- `md_to_notion.py public-url --page-id <id> --check` sends a HEAD request to the `notion.site` URL and exits non-zero until the page is live. `dm-automation` runs it before any DM goes out, and the Content Board card carries the in-app link until the public one resolves.
- `dm.guide_link_must_be_public: true` (the default) makes the linter refuse `app.notion.com` and workspace `notion.so` links in DMs, so a dead link cannot ship by accident.
