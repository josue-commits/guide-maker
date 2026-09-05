# User-invoked vs model-invoked

Every `SKILL.md` under `skills/` is a skill. The one axis that splits them is **invocation**: who can reach it.

- **User-invoked**: reachable only by the human typing its name. Set `disable-model-invocation: true` in the frontmatter. The `description` is human-facing: a one-line summary a person reads while browsing slash commands. No trigger lists ("Use when the user says...").
- **Model-invoked**: reachable by the model or the user. The default: omit `disable-model-invocation`. The `description` is model-facing and keeps the trigger phrasing ("Use when the user provides a YouTube URL, says 'make a guide from this'...") so auto-invocation fires. The test for staying model-invoked: could the model usefully reach for this on its own?

| Skill | Invocation | Why |
|---|---|---|
| `setup-guide-maker` | user | Writes config and edits `CLAUDE.md`; nobody wants that fired mid-task |
| `ask-guide-maker` | user | A map for a person to read; it runs nothing |
| `make-guide` | model | The pipeline; fires on a URL, a transcript, "write the copy" |
| `topic-finder` | model | Fires on "find me a topic"; also called by `make-guide` Phase 0 |
| `graphics-maker` | model | Fires on "make a graphic for this post"; also called at step 3c |
| `dm-automation` | model | Fires on "set the keyword", "schedule the post"; also called at step 3e |

`make-guide`'s description does not carry the "find me a topic" triggers. Those belong to `topic-finder`; two skills claiming the same sentence is a coin flip.

A user-invoked skill may invoke model-invoked skills. Nothing can invoke a user-invoked skill: not the model on its own, not another skill. `README.md` Reference and `skills/README.md` group entries under **User-invoked** and **Model-invoked**.

## Dependencies between them

Dependencies are operative instructions: a skill's own steps telling the agent to go run another skill now. They are expressed as an instruction to **call the Skill tool** with the named skill (`Call the Skill tool with "graphics-maker"`), never as a deep `../other-skill/FILE.md` cross-reference and never as a bare `/name` dropped into prose for the model to interpret. Naming the tool is what gets it fired. The Skill tool takes one skill per call; a step that needs two skills says so (`Call the Skill tool twice, for "graphics-maker" and "dm-automation"`).

This only holds when the named skill is model-invoked. When a step's precondition is a user-invoked skill, phrase it for the human: "tell the user to run `/setup-guide-maker`", never a Skill tool call.

Router prose that names skills for a person to pick from (`ask-guide-maker`, `skills/README.md`, the README) is not invoking anything, so it keeps `/name`-style labels.

## Hard and soft dependency on setup

`/setup-guide-maker` writes `.guide-maker/config.yaml`. Skills split on what they do without it:

| Dependency | Skills | Wording in the SKILL.md |
|---|---|---|
| **Hard** | `make-guide`, `dm-automation` | One line near the top: "The config should have been found by the doctor; if it reports none, tell the user to run `/setup-guide-maker` and stop." Without a Guide DB id the publish is wrong, not fuzzy; without `dm.*` and `community.*` the DM versions are wrong. |
| **Soft** | `graphics-maker`, `topic-finder` | No setup pointer. `graphics-maker card` renders on the shipped defaults (brand colors, bundled Inter, `provider: none`); `topic-finder` takes `--config-dir` and runs from any folder of JSON files. Output is less tailored without setup, not broken. |

The split keeps the soft skills token-light and stops the setup pointer from being pasted where it carries no weight.

## Shared material

Shared reference docs live inside the skill that owns them (`make-guide/references/strategy/cta-evidence.md` is the one source of the 95 to 11,432 numbers). Other skills reach that material by calling the Skill tool with the owner, or by restating the one line they need; they never link across skill folders, because under `npx skills` each skill may be installed alone.
