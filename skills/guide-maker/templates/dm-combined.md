# DM: combined (guide link + community aside)

Generated when `community.url` is set. Sends the guide link for the instant win and mentions the community as an aside, not a pitch. This is the default version for most weeks: the commenter gets what they asked for, and the community link rides along.

The body is a SHAPE, not a script. Rewrite the opener and `{specific_line}` fresh per guide. Each paragraph is one continuous line.

```
Hey {{firstName}}, glad this one landed. Full thing's here: {guide_url}

{specific_line}

I keep all of these in {community_name} too if you want the rest: {community_url}

{signoff}
```

## Slots

- `{{firstName}}`: the DM tool's merge tag. Keep the double braces exactly.
- `{guide_url}`: the public guide URL, never the in-app link.
- `{specific_line}`: one real, specific thing about the guide, said like a person.
- `{community_name}` / `{community_url}`: from `community.*`. The line that carries them is an aside. Never "I also run a free community where we share stuff that moves the needle"; that sentence is the most obviously templated line a DM can carry.
- `{signoff}`: a bare first name.

## Rules specific to this version

- The community line is one line, and it does not explain what the community is. The name and the link are enough.
- If you find yourself writing "join", "free", "value" or "community of" in that line, rewrite it.
