# DM: direct guide link

Always generated. Sends the commenter the public guide link and one specific line about what is inside. No community pitch, no second ask.

Use it when the guide itself is the win, or when you have no community or secondary channel configured.

The body is a SHAPE, not a script. Rewrite `{specific_line}` fresh for every guide in the human voice described in `references/dm/dm-guide.md`. Everything inside the fence is what gets sent; each paragraph is one continuous line.

```
Hey {{firstName}}, glad this one landed. Full thing's here: {guide_url}

{specific_line}

{signoff}
```

## Slots

- `{{firstName}}`: the DM tool's merge tag (`dm.merge_tag`). Keep the double braces exactly. `[Name]` and `{name}` are not substituted and reach the lead as literal text.
- `{guide_url}`: the **public** guide URL (`notion.public_domain`), never the in-app `app.notion.com` link, which is a dead end for anyone outside your workspace. It resolves only after you publish the page to web by hand.
- `{specific_line}`: one concrete, conversational sentence about what is inside, written like the person who built it ("the whole swap is four env vars and a restart, and I left the benchmarks in so you can see where it holds up and where it doesn't"). Never "It covers everything you need to know".
- `{signoff}`: `author.dm_signoff`, falling back to `author.name`. A bare first name.
