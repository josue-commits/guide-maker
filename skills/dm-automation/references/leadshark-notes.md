# LeadShark adapter notes

LeadShark is the reference adapter because its REST API is documented
(`https://apex.leadshark.io/docs/api`) and covers the whole loop: schedule a
post with an image, attach a keyword automation, list keywords, read stats.
Nothing here is required to use the skill; the manual adapter is the default.

## Key

Resolution order, first hit wins:

1. `LEADSHARK_API_KEY` environment variable
2. `~/.config/leadshark/api_key` (one line, `chmod 600`)
3. `providers.leadshark.api_key` in the config

Get it from the LeadShark dashboard under Settings, API Access. `dm_cli.py test
--provider leadshark` makes the cheapest authenticated call and confirms it.
`--dry-run` never needs the key.

## Plan tiers

The REST API is included in the Pro plan. Automations, scheduled posts, leads,
enrichment and posts work there. Pages, links and activity limits need Pro+.
Signals and Discover need Apex. The official MCP server needs Pro+ as well,
which is why this adapter talks REST. On a 403 the adapter appends "(This
endpoint requires the X plan.)" so you do not go looking for a key problem.

Rate limits are enforced server side: 250/hour, 1000/day, 100/minute. The
adapter backs off on 429 (5s, 10s, 20s) and retries connection errors twice.
`keywords` pages through every automation, so it costs several calls.

## Scheduled post vs automation

The one decision that matters is whether the post already exists.

| Situation | Command | Endpoint |
|---|---|---|
| Post not published yet (the normal weekly case) | `schedule` | `POST /api/scheduled-posts`, multipart when `--image` is given |
| Post already live | `attach` | `POST /api/automations` with the post URN |

`schedule` carries the automation inside the scheduled post record. **It does
not appear in the automations list until the post publishes**, because there
is no post URN to bind it to yet. Seeing it absent is correct. Do not create a
second one.

`attach` needs the activity URN. The adapter pulls it from any post URL shape
that contains `urn:li:activity:<digits>` or `activity-<digits>`; if it cannot,
it stops and asks for the post's own URL.

`attach` creates the automation with `dm_tool.leadshark.create_as`, `Paused` by
default. Flip it to Running once the DM reads right:
`PUT /api/automations/<id>/status` (`LeadSharkTool.set_status`).

## Automation fields the adapter sends

```
name                              "KEYWORD - date" unless --automation-name
keywords                          [KEYWORD]
dm_template                       the primary DM
dm_templates                      primary + every --dm-variant, rotated
comment_reply_template            --comment-reply or dm_tool.leadshark.comment_replies, rotated
non_first_degree_reply_template   --non-first-degree-reply or dm_tool.leadshark.non_first_degree_reply
auto_connect                      --auto-connect / --no-auto-connect, else dm_tool.leadshark.auto_connect
auto_like                         --auto-like (Pro+ and above)
```

Supported merge tags in DM text: `{{firstName}}`, `{{lastName}}`,
`{{fullName}}`, `{{linkedinUsername}}`. DM text is plain, max 2000 characters;
the lint enforces the limit when this adapter is selected. Follow-up DMs exist
in the API (`enable_follow_up`, `follow_up_template`, `follow_up_delay_minutes`)
but the adapter does not send them; a follow-up an hour after the first DM
reads as a bot.

`post_as: organization` plus `organization_id` in `dm_tool.leadshark` posts
from a company page instead of the personal profile.

## Attachment ceiling: 4 MiB, and JPEG fixes it

The API rejects uploads above 4,194,304 bytes with a bare `413` and no message.
A 4.57 MB PNG failed; 4.14 MB and 3.95 MB went through. The adapter checks the
file size before uploading and refuses with a pointer to `image-fit`.

`image-fit` re-encodes to JPEG at quality 95 with `subsampling=0`. On flat
vector art with type, which is what a post graphic is, that goes from about
4.5 MB to about 1 MB with no visible difference; LinkedIn re-encodes every
upload anyway. If quality 95 is still over the ceiling the command steps down
by 5 to 75 and then tells you to shrink the pixel dimensions.

Large uploads are also the documented cause of "socket hang up" failures, so
the multipart request uses a 300 second timeout.

## Timestamps

`scheduled_time` is ISO 8601 UTC. Window: 15 minutes minimum ahead, 90 days
maximum. Convert from your posting window with `dm_tool.timezone` (or
`dm_tool.leadshark.timezone`) and check the weekday after converting:

```bash
python3 -c "
import datetime, zoneinfo
t = '2026-09-14T13:00:00Z'
dt = datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
print(dt.astimezone(zoneinfo.ZoneInfo('America/Chicago')).strftime('%Y-%m-%d %H:%M %Z %A'))"
```

## Verifying what you created

The API will mislead you here, so know the shape first.

- Response envelopes differ per endpoint: automations list returns
  `{"data": [...]}`, scheduled posts return `{"posts": [...]}`. Parse
  defensively.
- There is no single-record endpoint for a scheduled post
  (`GET /api/v1/scheduled-posts/<id>` is a 404). Read from the list, or from
  the create call's own response, which is the fullest view you get.
- **The image cannot be confirmed through the API.** No field exposes it. The
  create response shows `"transport": "multipart"` and that is the whole
  confirmation. Open the scheduled post in the dashboard and look. Say plainly
  that the script could not verify it rather than implying it did.
- A scheduled post's automation is absent from the automations list until the
  post publishes. See above.

## Stats

`stats` returns the dashboard activity rollup for `--range` plus, per
automation: `total_comments`, `total_dms_sent`, `total_connections_sent`,
`total_connections_accepted`. That is conversion data, not impressions. The gap
between comments and DMs sent is mostly commenters outside your network who
have not connected yet, and it is the clearest signal of how much reach the
auto-connect setting is recovering.

## What the adapter does not cover

The engagement tools that act on LinkedIn as you (comment, connect, DM
arbitrary people, search) run through LeadShark's own infrastructure and are
not wrapped. Replicating them means hitting LinkedIn's private API directly,
which risks the account. Not worth it.

Any documented endpoint the adapter does not wrap is one `request()` call away
in `scripts/adapters/leadshark.py`.
