# The `## Agent skills` block

Written by `setup-guide-maker` into whichever of `CLAUDE.md` or `AGENTS.md` exists at the project root. If the heading already exists, only the `### Guide maker` entry is added or updated; the rest of the block belongs to other skills.

Fill every `<placeholder>` from the answers in Sections A to H. Keep it to these four lines; the config file is the source of truth and this block only says where it is.

```markdown
## Agent skills

### Guide maker
Config: `<config path>`. Change it with `/setup-guide-maker`, or edit the file.
Author: <name>. Guide DB: set. Content Board: <set|not set>. DM tool: <manual|leadshark>. Image provider: <none|kieai|openai>. Gates: <two|one>.
Start with "make a guide from this video: <url>". Unsure which skill fits: `/ask-guide-maker`.
```

Placeholders:

| Placeholder | Value |
|---|---|
| `<config path>` | `.guide-maker/config.yaml` for a project home; `~/.config/guide-maker/config.yaml` for a home config |
| `<name>` | `author.name` |
| `<set\|not set>` | whether `notion.content_board_database_id` is filled |
| `<manual\|leadshark>` | `dm_tool.provider` |
| `<none\|kieai\|openai>` | `graphics.provider` |
| `<two\|one>` | `workflow.gates` |

Never write an id, a token or a URL into the block. Ids live in the config; the block is committed with the project.
