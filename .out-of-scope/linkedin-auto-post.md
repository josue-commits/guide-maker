# Posting to LinkedIn from the skill

The skill never publishes a post to LinkedIn. It writes three variations, lints them, attaches the graphic and the DM bundle to a Content Board card, and stops. Requests to add a "post it" step are out of scope.

## Why

- The last human gate is the one that matters. Picking a variation is an editorial decision the operator makes with the whole week in view; an auto-post turns a bad hook into a public post before anyone read it.
- The keyword in the graphic, the keyword in the DM tool and the keyword on the card have to match exactly, and the operator reads the bar character by character before anything goes out. An auto-post skips the one check that decides whether the DM fires.
- LinkedIn's own API for personal-profile posts is gated and changes; every adapter would be permanent maintenance surface for a step that takes the operator thirty seconds.

## What to do instead

- `dm_tool.provider: leadshark` schedules the post, the graphic and the keyword automation through the adapter, after `--dry-run` and after the operator has read the payload. That is scheduling, not posting, and the automation is created paused.
- Any other scheduler: the manual bundle (`dm-bundle/post.txt`, the graphic, `checklist.md`) is written to be pasted into it.
