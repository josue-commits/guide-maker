# DM: community only, personalized to this guide

Generated when `community.url` is set. Sends ONLY the community link, with a hook line that names what this specific guide is about. Higher friction than the direct or combined versions (no guide link), so it routes every lead through the community door. Use it on weeks where community growth is the goal, or to A/B community-first against link-first.

The personalization is the whole point. "Join my free community" reads as spam. "That parallel-sessions setup is a good one, I pinned the whole breakdown in the classroom" reads like a person who remembers what the commenter asked for.

The body is a SHAPE, not a script. The hook line MUST be rewritten every week because the guide is different every week. Each paragraph is one continuous line.

```
Hey {{firstName}}, that {specific_line} is a good one. I pinned the whole breakdown in {community_name}, plus everything else I've put together on it: {community_url}

Ask in there if you hit a wall on the setup, people run it too.

{signoff}
```

## Slots

- `{{firstName}}`: the DM tool's merge tag. Keep the double braces exactly.
- `{specific_line}`: here it is a short noun phrase that names the feature, the outcome or the tool ("agent-view setup", "five-session parallel workflow", "spreadsheet stop rule"). It completes the sentence "that ___ is a good one".
- `{community_name}` / `{community_url}`: from `community.*`. Say where the guide sits ("pinned", "in the classroom", "in the resources tab") in the words your platform uses.
- `{signoff}`: a bare first name.

## Rules specific to this version

- Never paste last week's version unchanged. The hook line is the only thing that makes this not spam.
- No "thanks for joining", no "here's some great content", no "the crew runs the same stack". Those are the tells.
