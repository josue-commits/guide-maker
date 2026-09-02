# Strategy: why the skill is shaped this way

Everything below is a rule the skill enforces by default. Each one has a reason and, where we have numbers, the numbers. If your data says otherwise, most of it is a config change. The few that are not are marked.

## 1. The keyword lives in the graphic, never in the copy

LinkedIn suppresses the reach of posts whose text carries an engagement instruction: "comment X", "like this post", "repost this to get it". The classic lead-magnet closer (`Like this post 👍 / Comment "KEYWORD"`) is exactly that instruction, so the post that asks the most gets shown the least.

Two observations from the same account, same audience, same month:

| What changed | Impressions |
|---|---|
| Same graphic, same guide, keyword removed from the copy and put in the graphic | 95 before, 11,432 after |
| A post that carried `Comment "KEYWORD"` in the text, one week after a post without it did 62,000 | 43 |

So the keyword has exactly one carrier: the post graphic, in a full-width bar at the bottom edge, in one of two sanctioned strings:

```
COMMENT "[KEYWORD]" TO GET IT FOR FREE
```
```
Comment "[KEYWORD]" for the guide
```

The copy ends on one value line and the pointing-down emoji. Seven closers ship in `copy.closers`; the writer rotates them so three posts in a row never end the same way.

Consequences the skill enforces:
- `lint_copy.py` fails any copy that contains the keyword, `Comment "`, "Like this post", "Connect with me" or "Repost this" when `copy.cta_mode` is `graphic` (the default).
- The graphic is not shippable until the operator reads the keyword in the bar character by character. A misspelled keyword breaks the DM trigger silently and the copy cannot rescue it. With `graphics.cta_bar.renderer: pillow` the string is typeset locally, so this gate is about legibility, not spelling.
- `copy.cta_mode: copy` still exists. Some platforms and some audiences do not show the suppression, and you may want to test it. Lint and doctor print the two numbers above every time it is on.

## 2. Two image assets, not one

Every guide has two images and they are not interchangeable:

| Asset | Made by | Carries the keyword |
|---|---|---|
| Notion page cover | `banner_generator.py` | Never |
| LinkedIn post graphic | `graphics-maker` | Always, in the CTA bar |

The cover is what a reader sees after they already have the guide. A keyword on it is noise at best and a leaked trigger at worst. `banner_generator.py` refuses a title equal to the configured keyword.

## 3. Copy structure: prose, 180 to 250 words

The default body is an eight-beat prose essay, not an arrow list. A stack of "what is inside the guide" bullets is the tell of the older format and reads as a table of contents. The public post that set the pattern (a lead-magnet post with 494 comments) keeps the guide invisible until the last line.

Word range is an editorial default, not a performance finding: the previous 250 to 350 range drifted to the ceiling every week and the operator read every post as long. Change `copy.words` if your audience disagrees.

Three variations per post, one hook type each (`contrarian`, `problem_pain`, `quantity_build`), same body skeleton. The point is to A/B the hook, not to write three different posts.

## 4. Three topic sources, correlated, with a health gate

YouTube tells you what creators are publishing. Reddit tells you what your audience is asking. X tells you what landed first: lectures, first-party engineer talks, repos, before YouTube flattens them into tutorials.

Rules that come with each source:
- YouTube is scanned in two tracks, `tool` and `business`, scored separately and never merged. A business video scored on the tool rubric either never surfaces or produces a get-rich-quick guide.
- X is ranked on bookmark rate, never views. Views track jokes; bookmarks track "I will come back and study this". Above 0.8 percent is substance, below 0.1 percent is noise. Example from one scan: a 1.8M-view meme scored 0.07 percent, an 81K-view explainer scored 1.33 percent.
- Tweet text is a lead, not a source. Engagement accounts recycle real talks under invented numbers. Every figure you quote gets verified against a first-party page.
- A topic that appears on two or more sources in the same week is the strongest signal there is. `correlate.py` does the matching and every resource from every source feeds the one guide.
- A dead source is a failure, not a fallback. If a scanner returns nothing, Phase 0 stops and says so. Falling back to web search silently is how good topics get missed; the skill refuses to do it.

## 5. What gets a guide

The depth gate: official documentation exists, at least three authoritative sources, at least one long-form source (a 20 minute video or 10 pages of docs), and enough material for four to seven subpages. Hard rejects: news and drama, a single feature announcement without docs, opinion pieces, and topics where every source says the same thing.

`excluded_topics` in config is where you list competitors or subjects you never want proposed. The skill checks both Content Board keywords and Guide DB titles before proposing, so a topic you shipped last month under a different keyword does not come back.

## 6. Sources policy

Official docs are always citable. Institutional talks (university lectures, vendor courses, named-role engineer talks) are citable and get one attribution line in the body. Creator videos are research input only: they never appear in the published Sources section. Readers arrive cold from one LinkedIn post, so the body never references another guide or keyword either.

## 7. Human gates

The skill never publishes a Notion page to the web and never posts to LinkedIn. Those stay with you. What it asks you to approve:

1. The outline. Always.
2. The written content. Only with `workflow.gates: two` (the default). Teams that trust the writer set `one` and get the bundle with defaults.
3. The winning scene for the graphic.
4. The keyword in the CTA bar, read at feed scale.
5. Publishing the guide to the web, by hand. Until you do, the public link in the DMs does not resolve; the publisher checks the URL and tells you.
6. Picking a variation, scheduling the post, setting the keyword in your DM tool.

## 8. What is a hypothesis, not a rule

- "Open with the reader's state or the tool's state, never with yourself." Observed on 20 posts from one account (mean engagement 340 and 317 versus 189 for creator-state openers). Shipped as guidance in the writer prompt, not as a lint rule.
- Hook multipliers. Contrarian outperformed the other two on the same sample. Not enough data to make it a default beyond "first variation is contrarian".

## 9. Humanizer, always on

Every sentence the writer produces passes the banned-vocabulary and pattern list in `references/writing/humanizer.md`: no em dashes, no "delve", "leverage", "seamless", "game-changer", no "the takeaway is", no negative parallelisms, no rule-of-three padding, no collaborative sign-offs. This is the one rule with no config switch. Sterile AI prose is as obvious as a keyword in the copy, and it costs more.
