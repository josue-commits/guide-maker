# DM: guide link + secondary channel ask

Generated when `secondary_channel.url` is set. Sends the guide link, then asks outright for a follow or subscribe on your secondary channel (YouTube, newsletter, podcast). No community link in this one.

Use it on weeks where the goal is channel growth. The direct and combined versions route to the guide and the community; this one routes to the channel. Never merge the two asks into one DM: two "go here next" instructions means most people do neither.

The ask is explicit, and that is the point. The direct and combined versions weave a link in as an aside. This one asks. The winking ";)" makes a direct ask read light instead of needy. Keep it direct: softening it into "check it out if you want" removes the only reason this version exists.

The body is a SHAPE, not a script. Rewrite `{specific_line}` per guide. Each paragraph is one continuous line; the channel URL sits alone on its own line so it does not break mid-sentence.

```
hey {{firstName}}! Here's the guide: {guide_url}

{specific_line}

I'm also trying to grow my {secondary_channel_type} where I post the longer walkthroughs, feel free to check it out as well. I would appreciate a {secondary_channel_ask} ;)
{secondary_channel_url}

thanks!

{signoff}
```

## Slots

- `{{firstName}}`: the DM tool's merge tag. Keep the double braces exactly.
- `{guide_url}`: the public guide URL. Never the in-app link.
- `{specific_line}`: two or three sentences on what the guide walks through, as ONE unbroken line, one concrete thing said like the person who built it.
- `{secondary_channel_type}`: "YouTube channel", "newsletter", "podcast", from `secondary_channel.type`.
- `{secondary_channel_ask}`: "sub" for YouTube, "signup" for a newsletter, "follow" for a podcast. Pass it with `--set secondary_channel_ask=sub` when rendering; the writer fills it in the Content Board toggle.
- `{secondary_channel_url}`: from `secondary_channel.url`, on its own line.
- `{signoff}`: a bare first name.

## Rules specific to this version

- Keep the lowercase "hey" and "thanks!". They are load-bearing; capitalizing them makes it read like a template.
- Never add the community link. Pick the destination per campaign.
