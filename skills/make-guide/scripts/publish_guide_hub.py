#!/usr/bin/env python3
"""
Publish a guide as a hub page + subpages to Notion.

Creates the hub page in the Guide Database, publishes each subpage from
markdown files, then builds the hub content with links to all subpages.

Follows the hub page layout (references/guides/hub-page-layout.md):
  Community callout (only when community.url is set) -> guide description
  callout -> author byline (author.*) -> secondary-channel credit line (only
  when secondary_channel.url is set) -> (child pages auto-render) ->
  What You'll Build -> Who This Is For -> The Guide (step links) -> Sources

Usage:
    python3 publish_guide_hub.py \
        --title "Guide Title" \
        --description "What this guide covers" \
        --keyword "KEYWORD" \
        --type "Technical Tutorial" \
        --week "2026-03-02" \
        --icon "🛠️" \
        --build-item "Outcome the reader gets" \
        --build-item "Another outcome" \
        --audience-item "Who this is for" \
        --audience-item "Another audience" \
        --nav-note "Each step builds on the previous one." \
        --step "⚡|Short Title|Description paragraph|path/to/step.md" \
        --source "official|Tool documentation|https://example.com/docs" \\
        --source "institutional|University lecture on the topic|https://example.edu/talk"

Options:
    --title TEXT          Guide title (required)
    --description TEXT    One-sentence guide description (required)
    --keyword TEXT        Lead magnet keyword, e.g., SKILLS (required)
    --type TEXT           Guide type: Technical Tutorial, Strategic Framework,
                         Comparison/Persuasion or Use-case Stack (default: Technical Tutorial)
    --week DATE           Week date YYYY-MM-DD (required)
    --icon EMOJI          Page icon emoji (default: 📖)
    --build-item TEXT     Repeatable: items for "What You'll Build" section
    --audience-item TEXT  Repeatable: items for "Who This Is For" section
    --nav-note TEXT       Navigation callout text for "The Guide" section
    --step TEXT           Repeatable: "emoji|title|description|md_file"
    --source TEXT         Repeatable: "type|title|url". Types: official, institutional,
                         blog, pdf, repo, changelog, paper, course. Creator channels
                         (youtube, video) are refused unless sources.cite_creator_videos.
    --dry-run             Print plan without publishing
"""

import os
import sys
import argparse

# Add scripts dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md_to_notion import (
    notion_request, md_to_blocks, append_blocks,
    parse_inline, split_rich_text, MAX_BLOCKS_PER_REQUEST
)
from _config import load_config, cfg_get, add_config_arg
import _notion

_CFG = None


def config(path=None):
    global _CFG
    if _CFG is None:
        _CFG = load_config(path)
        _notion.init(_CFG)
    return _CFG


def get_guide_db():
    db = cfg_get(config(), "notion.guide_database_id", "")
    if not db:
        raise SystemExit("notion.guide_database_id is empty in the config.")
    return db


def get_community_info():
    return {
        "platform": cfg_get(config(), "community.platform", "none"),
        "name": cfg_get(config(), "community.name", ""),
        "url": cfg_get(config(), "community.url", ""),
        "callout_line": cfg_get(config(), "community.callout_line", ""),
    }


def get_author_info():
    return {
        "name": cfg_get(config(), "author.name", ""),
        "linkedin_url": cfg_get(config(), "author.linkedin_url", ""),
    }


def get_secondary_channel():
    return {
        "type": cfg_get(config(), "secondary_channel.type", "none"),
        "handle": cfg_get(config(), "secondary_channel.handle", ""),
        "url": cfg_get(config(), "secondary_channel.url", ""),
        "credit_line": cfg_get(config(), "secondary_channel.credit_line", ""),
    }


def create_hub_page(title, keyword, guide_type, week, icon_emoji):
    """Create the hub page in the Guide Database with no content yet."""
    properties = {
        "Guide Title": {
            "title": [{"type": "text", "text": {"content": title}}]
        },
        "Keyword": {
            "rich_text": [{"type": "text", "text": {"content": keyword}}]
        },
        "Type": {"select": {"name": guide_type}},
        "Week": {"date": {"start": week}},
        "Status": {"select": {"name": "Review"}},
    }

    body = {
        "parent": {"database_id": get_guide_db()},
        "icon": {"type": "emoji", "emoji": icon_emoji},
        "properties": properties,
        "children": [],
    }

    result = notion_request("POST", "/pages", body)
    page_id = result["id"]
    url = result["url"]
    print(f"Hub page created: {page_id}")
    print(f"  URL: {url}")
    return page_id, url


def create_subpage(parent_id, title, md_file, icon_emoji):
    """Create a subpage under the hub page from a markdown file."""
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    blocks = md_to_blocks(md_text, skip_first_h1=True)

    first_batch = blocks[:MAX_BLOCKS_PER_REQUEST]
    remaining = blocks[MAX_BLOCKS_PER_REQUEST:]

    body = {
        "parent": {"page_id": parent_id},
        "icon": {"type": "emoji", "emoji": icon_emoji},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
        "children": first_batch,
    }

    result = notion_request("POST", "/pages", body)
    page_id = result["id"]
    url = result["url"]

    if remaining:
        append_blocks(page_id, remaining)

    print(f"  Subpage: {title}")
    print(f"    ID: {page_id}")
    print(f"    URL: {url}")
    print(f"    Blocks: {len(blocks)}")
    return page_id, url


def build_hub_blocks(description, build_items, audience_items, nav_note,
                     steps, subpage_data, sources):
    """Build all hub page blocks following the approved layout."""
    blocks = []

    # 1. Community callout: only when community.url is set. The text is
    #    community.callout_line ("Join 100+ people learning X: "), the link
    #    text is community.name. Nothing here is hardcoded.
    community = get_community_info()
    if community["url"]:
        callout_text = (community["callout_line"] or "Join the community: ").rstrip()
        if not callout_text.endswith(":"):
            callout_text += ":"
        community_name = community["name"] or community["url"]
        blocks.append({
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "💬"},
                "rich_text": [
                    {"type": "text", "text": {"content": callout_text + " "}},
                    {"type": "text",
                     "text": {"content": community_name,
                              "link": {"url": community["url"]}},
                     "annotations": {"bold": True}},
                ],
            }
        })

    # 2. Guide description callout
    blocks.append({
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": "🚀"},
            "rich_text": [
                {"type": "text", "text": {"content": description}},
            ],
        }
    })

    # 3. Author byline
    author = get_author_info()
    if author["name"]:
        byline_parts = [
            {"type": "text", "text": {"content": "By "},
             "annotations": {"color": "gray"}},
        ]
        if author["linkedin_url"]:
            byline_parts.append({
                "type": "text",
                "text": {"content": author["name"],
                         "link": {"url": author["linkedin_url"]}},
                "annotations": {"bold": True, "color": "gray"},
            })
        else:
            byline_parts.append({
                "type": "text",
                "text": {"content": author["name"]},
                "annotations": {"bold": True, "color": "gray"},
            })
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": byline_parts}
        })

    # 3b. Secondary-channel credit line: only when secondary_channel.url is
    #     set. Understated, gray, directly under the byline. A credit, not a
    #     second CTA; it must not compete with the community callout.
    channel = get_secondary_channel()
    if channel["url"]:
        label = channel["credit_line"] or (
            f"{channel['type'].capitalize()}: " if channel["type"] not in ("", "none") else "Also on: ")
        label = label.rstrip()
        if not label.endswith(":"):
            label += ":"
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": [
                {"type": "text", "text": {"content": label + " "},
                 "annotations": {"color": "gray"}},
                {"type": "text",
                 "text": {"content": channel["handle"] or channel["url"],
                          "link": {"url": channel["url"]}},
                 "annotations": {"bold": True, "color": "gray"}},
            ]}
        })

    # 4. Empty line
    blocks.append({"type": "paragraph", "paragraph": {"rich_text": []}})

    # 5. Child pages auto-render here (no blocks needed)

    # 6. Empty line
    blocks.append({"type": "paragraph", "paragraph": {"rich_text": []}})

    # 7. Divider
    blocks.append({"type": "divider", "divider": {}})

    # 8. What You'll Build
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": parse_inline("🎯 What You'll Build"),
            "is_toggleable": False,
        }
    })
    for item in build_items:
        blocks.append({
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": parse_inline(item)}
        })

    # Empty line
    blocks.append({"type": "paragraph", "paragraph": {"rich_text": []}})

    # 9. Who This Is For
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": parse_inline("👤 Who This Is For"),
            "is_toggleable": False,
        }
    })
    for item in audience_items:
        blocks.append({
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": parse_inline(item)}
        })

    # 10. Empty line
    blocks.append({"type": "paragraph", "paragraph": {"rich_text": []}})

    # 11. Divider
    blocks.append({"type": "divider", "divider": {}})

    # 12. The Guide
    blocks.append({
        "type": "heading_2",
        "heading_2": {
            "rich_text": parse_inline("📖 The Guide"),
            "is_toggleable": False,
        }
    })

    # Navigation callout
    if nav_note:
        blocks.append({
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "⚡"},
                "rich_text": [
                    {"type": "text", "text": {"content": nav_note}},
                ],
            }
        })
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": []}})

    # Step entries
    for i, (emoji, short_title, step_description, _) in enumerate(steps):
        url = subpage_data[i]["url"]

        # H3 step title
        blocks.append({
            "type": "heading_3",
            "heading_3": {
                "rich_text": [
                    {"type": "text",
                     "text": {"content": f"{emoji} Step {i+1}: {short_title}"}},
                ],
                "is_toggleable": False,
            }
        })

        # Description paragraph
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": parse_inline(step_description)}
        })

        # Arrow link to subpage
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "→ "}},
                    {"type": "text",
                     "text": {"content": f"Read Step {i+1}: {short_title}",
                              "link": {"url": url}}},
                ]
            }
        })

        # Divider between steps (not after last)
        if i < len(steps) - 1:
            blocks.append({"type": "divider", "divider": {}})

    # 13. Divider before sources
    blocks.append({"type": "divider", "divider": {}})

    # 14. Sources
    if sources:
        blocks.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": parse_inline("📚 Sources"),
                "is_toggleable": False,
            }
        })

        for source_type, source_title, source_url in sources:
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "→ "}},
                        {"type": "text",
                         "text": {"content": f"{source_type}: {source_title}",
                                  "link": {"url": source_url}}},
                    ]
                }
            })

        # 15. Final divider
        blocks.append({"type": "divider", "divider": {}})

    return blocks


def parse_step(step_str):
    """Parse a step string: 'emoji|title|description|md_file'."""
    parts = step_str.split("|", 3)
    if len(parts) != 4:
        print(f"Error: Step must have 4 parts separated by '|': {step_str}",
              file=sys.stderr)
        sys.exit(1)
    return tuple(p.strip() for p in parts)


CREATOR_SOURCE_TYPES = {"youtube", "video", "tiktok", "instagram", "creator", "podcast-episode", "stream"}
KNOWN_SOURCE_TYPES = {"official", "docs", "documentation", "institutional", "lecture", "course",
                      "talk", "blog", "article", "pdf", "repo", "github", "changelog", "paper",
                      "site", "release-notes"}
SOURCE_LABELS = {"official": "Official docs", "docs": "Docs", "documentation": "Docs",
                 "institutional": "Lecture", "lecture": "Lecture", "course": "Course",
                 "talk": "Talk", "blog": "Blog", "article": "Article", "pdf": "PDF",
                 "repo": "Repo", "github": "GitHub", "changelog": "Changelog", "paper": "Paper",
                 "site": "Site", "release-notes": "Release notes"}


def parse_source(source_str):
    """Parse a source string: 'type|title|url' and apply the sources policy.

    Creator-channel types (youtube, video, ...) are refused unless
    sources.cite_creator_videos is true. Institutional talks are citable.
    See references/research/sources-policy.md.
    """
    parts = source_str.split("|", 2)
    if len(parts) != 3:
        print(f"Error: Source must have 3 parts separated by '|': {source_str}",
              file=sys.stderr)
        sys.exit(1)
    stype, title, url = (p.strip() for p in parts)
    key = stype.lower()
    if key in CREATOR_SOURCE_TYPES and not cfg_get(config(), "sources.cite_creator_videos"):
        print(f"Error: source type {stype!r} is a creator channel and sources.cite_creator_videos "
              f"is false. Creator videos are research inputs, not citations. Verify the fact "
              f"against an official page and cite that, or use 'institutional' for a university "
              f"or vendor lecture. ({title})", file=sys.stderr)
        sys.exit(1)
    if key not in KNOWN_SOURCE_TYPES and key not in CREATOR_SOURCE_TYPES:
        print(f"Warning: unknown source type {stype!r}; known types: "
              f"{', '.join(sorted(KNOWN_SOURCE_TYPES))}", file=sys.stderr)
    label = SOURCE_LABELS.get(key, stype)
    return (label, title, url)


def main():
    parser = argparse.ArgumentParser(
        description="Publish a guide hub + subpages to Notion"
    )
    parser.add_argument("--title", required=True, help="Guide title")
    parser.add_argument("--description", required=True,
                        help="One-sentence guide description")
    parser.add_argument("--keyword", required=True,
                        help="Lead magnet keyword")
    parser.add_argument("--type", default="Technical Tutorial",
                        help="Guide type")
    parser.add_argument("--week", required=True,
                        help="Week date YYYY-MM-DD")
    parser.add_argument("--icon", default="📖",
                        help="Page icon emoji")
    parser.add_argument("--build-item", action="append", default=[],
                        help="What You'll Build item (repeatable)")
    parser.add_argument("--audience-item", action="append", default=[],
                        help="Who This Is For item (repeatable)")
    parser.add_argument("--nav-note", default="",
                        help="Navigation callout text")
    parser.add_argument("--step", action="append", default=[],
                        help="Step: 'emoji|title|description|md_file'")
    parser.add_argument("--source", action="append", default=[],
                        help="Source: 'type|title|url'")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without publishing")
    add_config_arg(parser)

    args = parser.parse_args()
    config(args.config)

    if not args.step:
        print("Error: At least one --step is required.", file=sys.stderr)
        sys.exit(1)

    steps = [parse_step(s) for s in args.step]
    sources = [parse_source(s) for s in args.source]

    # Verify all markdown files exist
    for emoji, title, desc, md_file in steps:
        if not os.path.exists(md_file):
            print(f"Error: Markdown file not found: {md_file}",
                  file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN: Guide Hub Publishing Plan")
        print("=" * 60)
        print(f"\nTitle: {args.title}")
        print(f"Description: {args.description}")
        print(f"Keyword: {args.keyword}")
        print(f"Type: {args.type}")
        print(f"Week: {args.week}")
        print(f"Icon: {args.icon}")
        print(f"\nBuild items: {len(args.build_item)}")
        for item in args.build_item:
            print(f"  - {item}")
        print(f"\nAudience items: {len(args.audience_item)}")
        for item in args.audience_item:
            print(f"  - {item}")
        print(f"\nSteps: {len(steps)}")
        for i, (emoji, title, desc, md_file) in enumerate(steps):
            print(f"  {i+1}. {emoji} {title}")
            print(f"     File: {md_file}")
            print(f"     Desc: {desc[:60]}...")
        print(f"\nSources: {len(sources)}")
        for stype, stitle, surl in sources:
            print(f"  - {stype}: {stitle}")
        # Block plan with placeholder subpage URLs, so the hub layout can be
        # checked (callout present or absent, byline, credit line) offline.
        fake_subpages = [{"id": f"step-{i + 1}", "url": f"https://www.notion.so/step-{i + 1}"}
                         for i in range(len(steps))]
        hub_blocks = build_hub_blocks(
            description=args.description, build_items=args.build_item,
            audience_items=args.audience_item, nav_note=args.nav_note,
            steps=steps, subpage_data=fake_subpages, sources=sources)
        print(f"\nHub block plan ({len(hub_blocks)} blocks):")
        for block in hub_blocks:
            kind = block["type"]
            inner = block.get(kind, {}) or {}
            text = "".join(rt.get("text", {}).get("content", "") for rt in inner.get("rich_text", []))
            print(f"  {kind:<20} {text[:70]}")
        print("\nNo changes made (dry run).")
        return

    print("=" * 60)
    print(f"Publishing: {args.title}")
    print("=" * 60)

    # Phase 1: Create hub page (empty)
    print("\n[1/3] Creating hub page...")
    hub_id, hub_url = create_hub_page(
        title=args.title,
        keyword=args.keyword,
        guide_type=args.type,
        week=args.week,
        icon_emoji=args.icon,
    )

    # Phase 2: Create all subpages
    print("\n[2/3] Creating subpages...")
    subpage_data = []
    for emoji, title, desc, md_file in steps:
        page_id, url = create_subpage(hub_id, title, md_file, emoji)
        subpage_data.append({"id": page_id, "url": url})

    # Phase 3: Build hub content and append
    print("\n[3/3] Adding hub page content...")
    hub_blocks = build_hub_blocks(
        description=args.description,
        build_items=args.build_item,
        audience_items=args.audience_item,
        nav_note=args.nav_note,
        steps=steps,
        subpage_data=subpage_data,
        sources=sources,
    )
    print(f"  Hub blocks: {len(hub_blocks)}")
    append_blocks(hub_id, hub_blocks)
    print("  Done!")

    # Summary
    print("\n" + "=" * 60)
    print("PUBLISHED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nHub page: {hub_url}")
    print(f"Hub ID:   {hub_id}")
    print(f"\nSubpages:")
    for i, (emoji, title, _, _) in enumerate(steps):
        print(f"  {emoji} Step {i+1}: {title}")
        print(f"     ID:  {subpage_data[i]['id']}")
        print(f"     URL: {subpage_data[i]['url']}")


if __name__ == "__main__":
    main()
