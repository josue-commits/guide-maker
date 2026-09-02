# Manual workflow: the bundle and the checklist

`dm_tool.provider: manual` is the default because most people run keyword
automations from a tool with no API, or from their own inbox. The CLI does
everything it can do offline and hands you a folder for the rest.

## What `schedule` writes

```
<out-dir>/dm-bundle/
  post.txt              the post copy, exactly as it should be pasted
  dm-primary.txt        the DM your tool sends when someone comments the keyword
  dm-variant-1.txt      rotated variants, one file each (from --dm-variant)
  comment-replies.txt   public replies to rotate, plus the reply for people outside your network
  graphic.png|jpg       a copy of the post graphic (the one with the keyword bar)
  schedule.json         keyword, time (UTC and local), adapter, file list
  checklist.md          the steps below, filled in for this post
```

`attach` writes the same bundle without `post.txt` and with the live post URL in
the checklist. Both run the DM lint and the em-dash guard before writing
anything, so a bundle on disk is a bundle that passed.

The bundle is a snapshot. Re-run `schedule` after editing a DM; do not edit the
files in `dm-bundle/` by hand and expect the lint to have seen them.

## The checklist

This is what `checklist.md` says, in order. It is the same list for every tool
because the failure points are the same everywhere.

1. **Attach the graphic.** It carries the keyword bar. Without it the post asks
   the reader for nothing and the automation has nothing to fire on. Read the
   keyword on the graphic character by character before you post: a misspelled
   keyword on the image silently breaks the trigger and the copy cannot save it.
2. **Paste `post.txt`.** The copy must not name the keyword. The image asks,
   the text points down.
3. **Set the trigger keyword** on the post in your tool. One keyword per guide,
   unique across your account. If your tool matches substrings, a keyword that
   is also a common word fires on every comment.
4. **Paste the DM(s).** One paragraph per line, blank lines between. Leave the
   merge tag exactly as written; that is the spelling your tool substitutes.
   If your tool uses a different tag, set `dm.merge_tag` in the config and
   re-render.
5. **Add the public replies** if your tool rotates them. A public "Sent!" under
   the comment tells the next reader the mechanism works.
6. **Turn on auto-connect** or the equivalent. A large share of commenters are
   outside your network and cannot receive a DM until they connect. The
   non-first-degree reply covers them in public.
7. **Confirm the guide link resolves for a stranger.** The checklist prints a
   `curl` line for every URL in the DM. A Notion page answers 200 only after
   you publish it to the web from the Notion app. The copy-link button gives
   you the workspace URL, which is dead for everyone outside it.
8. **Post inside your window.** The checklist shows the time in
   `dm_tool.timezone` and in UTC so a date off by one is visible.
9. **After the first comment lands**, check that the DM fired and the link
   opened. Then leave it alone.

## Reading results without an adapter

`stats` has nothing to read on the manual adapter. Track three numbers per post
in your tool or by hand: comments, DMs sent, and connection requests accepted.
Comments minus DMs sent is the reach you are leaving on the table to people
who have not connected yet.

## Moving to an adapter later

Nothing in the bundle changes. Set `dm_tool.provider` to the adapter name, put
the API key where `references/leadshark-notes.md` (or your adapter's notes)
says, run `test`, then run the same `schedule` command with `--dry-run` and
compare the payload with the bundle you used to paste by hand.
