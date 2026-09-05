# Writing docs pages

Every skill under `skills/` has a human-facing docs page at `docs/skills/<name>.md`. The page is not the skill and not a copy of `SKILL.md`. Its job is to orient one reader around one skill: what it is, when to reach for it, where it sits. The six pages together are a distributed router; each is a node, and [ask-guide-maker](../docs/skills/ask-guide-maker.md) is the map.

Act whenever a skill is added, renamed, or has its behaviour changed: create or re-sync its page. A rename moves the file too (`docs/skills/<old>.md` becomes `docs/skills/<new>.md`); no stale page survives.

Links are **repo-relative**. From `docs/skills/`, a sibling page is `./<name>.md`, a skill file is `../../skills/<name>/SKILL.md`, a top-level doc is `../<file>.md`. `docs.yml` resolves every relative link in CI and fails on a dead one. `http` links are allowed for third parties (Notion, LinkedIn, yt-dlp) and never for this repo's own files.

The page opens with one H1, the bare skill name (`# make-guide`). GitHub renders the page; there is no separate site.

## Page structure

Fill the template below, in this order. The fixed frame (`## What it does`, `## When to reach for it`, `## Where it fits`) is on every page. `## Prerequisites`, the free-form middle, `## Common questions` and `## It's working if` carry only what the skill needs.

<page-template>

## What it does

One or two plain paragraphs. Lead with the skill's one-sentence job, then state the **defining constraint**: the single fact that makes this skill behave differently from the obvious default. Write it as a plain declarative sentence, never a labelled aside ("The key thing:"). The six constraints:

| Skill | Defining constraint |
|---|---|
| `make-guide` | The keyword never appears in the copy, and the skill never posts or publishes a page to the web |
| `setup-guide-maker` | It writes files you can read; the skill files never change |
| `ask-guide-maker` | It maps situations to entry points; it runs nothing |
| `topic-finder` | A dead source is a stop, never a web-search fallback |
| `graphics-maker` | The CTA bar is typeset locally, never generated |
| `dm-automation` | Manual is the default; an adapter is an upgrade |

## When to reach for it

Two beats, both always present:

- **Invocation mode.** User-invoked: "You invoke this by typing `/<name>`; the agent will not reach for it on its own." Model-invoked: "Type `/<name>`, or the agent reaches for it when a task fits."
- **Trigger boundary.** "Reach for this when...". Where the skill is confusable with a sibling, add the other half: `for X instead, use [sibling](./sibling.md).` Branches go in a table, situation left, entry right.

## Prerequisites

Only when the skill needs something in place: the **config keys it reads** (take them from the "Config keys this skill reads" block in its `SKILL.md` where one exists; group by top-level key, do not restate every leaf), **secrets** (env var, key file), **tools** on PATH, and **prior setup** (`/setup-guide-maker` for the hard-dependency skills). Omit the heading for a skill that runs anywhere.

## <free-form middle>

One to three short sections in the skill's own vocabulary. Surface the skill's **leading word**: gates for `make-guide`, the two-pass and the bar for `graphics-maker`, the bundle for `dm-automation`, the health gate and bookmark rate for `topic-finder`, the three files for `setup-guide-maker`, on-ramps for the router. The reader learns what the skill is and the word they will later think with to reach for it.

## Common questions

The questions readers really ask, each in bold with the answer beneath. No sub-headings. Find them before writing any:

- `docs/troubleshooting.md`: every entry there is a question someone hit.
- `CHANGELOG.md`: anything renamed, moved or changed generates a "where did it go?".
- GitHub issues: `gh issue list --repo josue-commits/guide-maker --search "<skill>" --state all`. A question filed twice is one the page owes an answer to.

**The count stays honest to the evidence.** A skill with a long troubleshooting section earns five; a new skill earns one or two, or none. Padding a thin skill to match a rich one fills the section with questions nobody has. Say the unflattering thing where it is true. Omit the heading where there is nothing worth answering.

## It's working if

A few bullets naming what the reader sees when the skill is doing its job, each checkable **without opening `SKILL.md`**: a signal in their own Notion, their own terminal, the trace in front of them. "The doctor prints the config path under `.guide-maker/`" passes; "the frontmatter has `disable-model-invocation`" is a compliance check wearing this section's name.

## Where it fits

Always present, one or two sentences:

- **Role.** A **chain step** (the pipeline), a **run-once setup**, a **map**, or a **reach-for-it-anytime standalone**.
- **Neighbours.** The one or two siblings that matter, each with a because-clause, linked.
- **The map.** Point at the router page (`[ask-guide-maker](./ask-guide-maker.md)` from a skill page) so this page stays a node and never redraws the graph.

</page-template>

## Conventions

- **A page carries no install block.** Install wording lives in [install-block.md](./install-block.md) and the README owns the one copy. A page that needs it links `../../README.md#installation-30-second-setup`.
- **Never name the author.** The page is a technical document. State substance as a plain claim about the skill and drop the frame. Quoting an anonymous user ("one user reported...") is fine; it is evidence about the skill in the wild.
- Explain the **why**, not the process. The page never reproduces `SKILL.md` steps or command dumps; one command is fine when it is the thing the reader will type.
- **Branches go in a table or a list, never a paragraph.** The reader is scanning for the one row that matches their situation.
- Use the skill's leading words so the page and the skill speak one language: gate, bar, bundle, health, override, on-ramp.
- No em dashes. No private strings (CI greps for both).
- Keep the page low-load. Spare headings and restated links are the thing it argues against.

## Done when

- The page exists at `docs/skills/<name>.md` and no stale page survives a rename.
- It carries no install command.
- `## What it does` states the defining constraint as plain prose.
- It names no author.
- `## When to reach for it` states invocation mode and the trigger boundary.
- `## Prerequisites` lists the config keys the skill reads, or is absent.
- The middle surfaces the leading word.
- `## Common questions` is sized to what the hunt found.
- Every `## It's working if` bullet is checkable without `SKILL.md`.
- `## Where it fits` names the role and links the router page.
- Every relative link resolves (`docs.yml`).
