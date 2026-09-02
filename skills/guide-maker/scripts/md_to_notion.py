#!/usr/bin/env python3
"""
Markdown to Notion Block Converter & Publisher

Converts markdown files to Notion API block format and publishes them
as pages in Notion databases or as subpages under existing pages.

Usage:
    python3 md_to_notion.py publish-guide <md_file> <database_id> [options]
    python3 md_to_notion.py publish-subpage <md_file> <parent_page_id>
    python3 md_to_notion.py create-content-entry [options]

Options for publish-guide:
    --keyword TEXT       Keyword for the guide (e.g., SKILLS)
    --type TEXT          Guide type (e.g., "Technical Tutorial")
    --week DATE          Week date in YYYY-MM-DD format
    --status TEXT        Status (default: Review)

Options for create-content-entry:
    --title TEXT         Post title
    --account TEXT       Account name
    --post-date DATE     Post date YYYY-MM-DD
    --day TEXT           Day of week (Monday/Wednesday/Friday)
    --content-type TEXT  Type (AI Guide/Sales Resource)
    --keyword TEXT       Keyword
    --guide-link URL     Guide link (optional)
    --variation TEXT     Repeatable: "Angle Name|post text"
"""

import re
import sys
import json
import argparse
import urllib.request
import urllib.error

# --- Configuration ---

from _config import get_notion_token, get_content_board_db

NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"
MAX_BLOCKS_PER_REQUEST = 100
MAX_RICH_TEXT_LENGTH = 2000

# Notion only accepts code-block languages from a fixed enum. Anything outside
# it ("js", "text", "sh", "yml", ...) makes the page-create call return 400 and
# the whole publish fails. Normalize every fence tag before it reaches the API.
NOTION_CODE_LANGS = {
    "abap", "agda", "arduino", "ascii art", "assembly", "bash", "basic", "bnf",
    "c", "c#", "c++", "clojure", "coffeescript", "coq", "css", "dart", "dhall",
    "diff", "docker", "ebnf", "elixir", "elm", "erlang", "f#", "flow", "fortran",
    "gherkin", "glsl", "go", "graphql", "groovy", "haskell", "hcl", "html",
    "idris", "java", "javascript", "json", "julia", "kotlin", "latex", "less",
    "lisp", "livescript", "llvm ir", "lua", "makefile", "markdown", "markup",
    "matlab", "mermaid", "nix", "notion formula", "objective-c", "ocaml",
    "pascal", "perl", "php", "plain text", "powershell", "prolog", "protobuf",
    "purescript", "python", "r", "racket", "reason", "ruby", "rust", "sass",
    "scala", "scheme", "scss", "shell", "solidity", "sql", "swift", "toml",
    "typescript", "vb.net", "verilog", "vhdl", "visual basic", "webassembly",
    "xml", "yaml",
}
NOTION_CODE_LANG_ALIASES = {
    "js": "javascript", "jsx": "javascript", "mjs": "javascript",
    "ts": "typescript", "tsx": "typescript", "py": "python", "py3": "python",
    "sh": "bash", "zsh": "bash", "shell-session": "shell", "console": "shell",
    "text": "plain text", "txt": "plain text", "plaintext": "plain text",
    "": "plain text", "yml": "yaml", "dockerfile": "docker", "md": "markdown",
    "node": "javascript", "jsonc": "json", "json5": "json", "env": "bash",
    "dotenv": "bash", "ini": "plain text", "rb": "ruby", "rs": "rust",
    "golang": "go", "cs": "c#", "cpp": "c++", "objc": "objective-c",
    "ps1": "powershell", "pwsh": "powershell", "svg": "xml", "vue": "html",
    "tf": "hcl", "terraform": "hcl", "make": "makefile",
}


def _normalize_code_lang(lang):
    """Map a markdown fence language to a Notion-valid code language."""
    key = (lang or "").strip().lower()
    if key in NOTION_CODE_LANGS:
        return key
    return NOTION_CODE_LANG_ALIASES.get(key, "plain text")


# --- HTTP helpers (stdlib only, no requests dependency) ---

def notion_request(method, path, body=None):
    """Make an authenticated request to the Notion API."""
    url = f"{NOTION_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_notion_token()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Notion API error {e.code}: {error_body}", file=sys.stderr)
        raise


# --- Rich text parsing ---

def split_rich_text(elements, max_len=MAX_RICH_TEXT_LENGTH):
    """Split rich text elements so no single element exceeds max_len."""
    result = []
    for el in elements:
        text = el.get("text", {}).get("content", "")
        if len(text) <= max_len:
            result.append(el)
        else:
            # Split long text into chunks, preserving annotations/link
            annotations = el.get("annotations", {})
            link = el.get("text", {}).get("link")
            for i in range(0, len(text), max_len):
                chunk = text[i:i + max_len]
                new_el = {"type": "text", "text": {"content": chunk}}
                if link:
                    new_el["text"]["link"] = link
                if annotations:
                    new_el["annotations"] = dict(annotations)
                result.append(new_el)
    return result


def parse_inline(text):
    """Parse inline markdown (bold, italic, code, links) into Notion rich_text."""
    elements = []
    # Pattern matches: [text](url), **bold**, *italic*, `code`, or plain text
    pattern = re.compile(
        r'(\[([^\]]+)\]\(([^)]+)\))'   # [text](url)
        r'|(\*\*(.+?)\*\*)'            # **bold**
        r'|(\*(.+?)\*)'                # *italic*
        r'|(`([^`]+)`)'                # `code`
    )
    pos = 0
    for m in pattern.finditer(text):
        # Add plain text before this match
        if m.start() > pos:
            plain = text[pos:m.start()]
            if plain:
                elements.append({"type": "text", "text": {"content": plain}})

        if m.group(1):  # link
            link_text = m.group(2)
            link_url = m.group(3)
            elements.append({
                "type": "text",
                "text": {"content": link_text, "link": {"url": link_url}},
            })
        elif m.group(4):  # bold
            elements.append({
                "type": "text",
                "text": {"content": m.group(5)},
                "annotations": {"bold": True},
            })
        elif m.group(6):  # italic
            elements.append({
                "type": "text",
                "text": {"content": m.group(7)},
                "annotations": {"italic": True},
            })
        elif m.group(8):  # code
            elements.append({
                "type": "text",
                "text": {"content": m.group(9)},
                "annotations": {"code": True},
            })
        pos = m.end()

    # Remaining plain text
    if pos < len(text):
        remaining = text[pos:]
        if remaining:
            elements.append({"type": "text", "text": {"content": remaining}})

    if not elements:
        elements.append({"type": "text", "text": {"content": text}})

    return split_rich_text(elements)


# --- Markdown to Notion blocks ---

# Emoji detection: check if a string starts with an emoji character
EMOJI_PATTERN = re.compile(
    r'^[\U0001F300-\U0001FAD6\U0001FA70-\U0001FAFF\U00002702-\U000027B0'
    r'\U0000FE00-\U0000FE0F\U0001F900-\U0001F9FF\U0001F600-\U0001F64F'
    r'\U00002600-\U000026FF\U00002700-\U000027BF\U0000200D\U00002B50'
    r'\U0000231A-\U0000231B\U000023E9-\U000023F3\U000023F8-\U000023FA'
    r'\U000025AA-\U000025AB\U000025B6\U000025C0\U000025FB-\U000025FE'
    r'\U00002934-\U00002935\U00002B05-\U00002B07\U00002B1B-\U00002B1C'
    r'\U00003030\U0000303D\U00003297\U00003299'
    r'\U0001F004\U0001F0CF\U0001F170-\U0001F171\U0001F17E-\U0001F17F'
    r'\U0001F18E\U0001F191-\U0001F19A\U0001F1E0-\U0001F1FF'
    r'\U0001F201-\U0001F202\U0001F21A\U0001F22F\U0001F232-\U0001F23A'
    r'\U0001F250-\U0001F251\U0001F680-\U0001F6FF'
    r'\U00002702\U00002705\U00002708-\U0000270D\U0000270F'
    r'\U00002712\U00002714\U00002716\U0000271D\U00002721'
    r'\U00002728\U00002733-\U00002734\U00002744\U00002747'
    r'\U0000274C\U0000274E\U00002753-\U00002755\U00002757'
    r'\U00002763-\U00002764\U00002795-\U00002797\U000027A1'
    r'\U000027B0\U0000FE0F\u2611\u2612\u2610'
    r'\u2B50\u26A0\u26A1\u2615\u2764\u2714\u2728\u267B\u2934'
    r'\u274C\u274E\u2705\u270F\u270D\u2712\u2716\u271D\u2721'
    r']'
)

CALLOUT_EMOJIS = {"💡", "⚠️", "🔑", "🚀", "⚠", "💡", "🔑", "🚀"}


def starts_with_emoji(text):
    """Check if text starts with an emoji character."""
    if not text:
        return False
    return bool(EMOJI_PATTERN.match(text))


def extract_leading_emoji(text):
    """Extract the leading emoji from text, return (emoji, rest)."""
    # Try two-char emoji first (emoji + variation selector)
    if len(text) >= 2 and text[1] == '\uFE0F':
        return text[:2], text[2:].lstrip()
    # Single char emoji
    if starts_with_emoji(text):
        # Handle multi-codepoint emoji
        i = 1
        while i < len(text) and (text[i] == '\uFE0F' or text[i] == '\u200D'):
            i += 1
            if i < len(text):
                i += 1
        return text[:i], text[i:].lstrip()
    return None, text


def parse_table(lines):
    """Parse markdown table lines into a Notion table block."""
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Parse cells first
        cell_str = line
        if cell_str.startswith('|'):
            cell_str = cell_str[1:]
        if cell_str.endswith('|'):
            cell_str = cell_str[:-1]
        cells = [c.strip() for c in cell_str.split('|')]
        # Skip separator rows: all cells are just dashes/colons/spaces
        if all(re.match(r'^[\-:]+$', c) for c in cells if c):
            continue
        rows.append(cells)

    if not rows:
        return None

    num_cols = max(len(r) for r in rows)
    # Pad rows to same length
    for r in rows:
        while len(r) < num_cols:
            r.append("")

    table_rows = []
    for row in rows:
        table_rows.append({
            "type": "table_row",
            "table_row": {
                "cells": [parse_inline(cell) for cell in row]
            }
        })

    return {
        "type": "table",
        "table": {
            "table_width": num_cols,
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows,
        }
    }


def md_to_blocks(md_text, skip_first_h1=True):
    """Convert a markdown string to a list of Notion blocks."""
    lines = md_text.split('\n')
    blocks = []
    i = 0
    first_h1_skipped = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty line: skip
        if not stripped:
            i += 1
            continue

        # Divider
        if stripped == '---':
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        # Code block
        if stripped.startswith('```'):
            lang = _normalize_code_lang(stripped[3:].strip())
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_content = '\n'.join(code_lines)
            # Split code content if too long
            rich_text = split_rich_text([
                {"type": "text", "text": {"content": code_content}}
            ])
            blocks.append({
                "type": "code",
                "code": {
                    "rich_text": rich_text,
                    "language": lang,
                }
            })
            continue

        # Table
        if stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            table_block = parse_table(table_lines)
            if table_block:
                blocks.append(table_block)
            continue

        # Headings
        heading_match = re.match(r'^(#{1,3})\s+(.*)', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)

            if level == 1 and skip_first_h1 and not first_h1_skipped:
                first_h1_skipped = True
                i += 1
                continue

            heading_type = f"heading_{level}"
            blocks.append({
                "type": heading_type,
                heading_type: {
                    "rich_text": parse_inline(text),
                    "is_toggleable": False,
                }
            })
            i += 1
            continue

        # Blockquote / Callout
        if stripped.startswith('>'):
            quote_text = stripped[1:].strip()
            # Check if it starts with a callout emoji
            emoji, rest = extract_leading_emoji(quote_text)
            if emoji and emoji.rstrip('\uFE0F') in {'💡', '⚠', '🔑', '🚀', '⚠️'}:
                blocks.append({
                    "type": "callout",
                    "callout": {
                        "rich_text": parse_inline(rest),
                        "icon": {"type": "emoji", "emoji": emoji.rstrip('\uFE0F') if len(emoji) > 1 and emoji[-1] == '\uFE0F' else emoji},
                    }
                })
            else:
                blocks.append({
                    "type": "quote",
                    "quote": {
                        "rich_text": parse_inline(quote_text),
                    }
                })
            i += 1
            continue

        # Numbered list
        num_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if num_match:
            text = num_match.group(2)
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": parse_inline(text),
                }
            })
            i += 1
            continue

        # Checklist: - [ ] item or - [x] item
        checklist_match = re.match(r'^[-*]\s+\[([ xX])\]\s+(.*)', stripped)
        if checklist_match:
            checked = checklist_match.group(1).lower() == 'x'
            text = checklist_match.group(2)
            blocks.append({
                "type": "to_do",
                "to_do": {
                    "rich_text": parse_inline(text),
                    "checked": checked,
                }
            })
            i += 1
            continue

        # Bulleted list: - item, * item
        bullet_match = re.match(r'^[-*]\s+(.*)', stripped)
        if bullet_match:
            text = bullet_match.group(1)
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": parse_inline(text),
                }
            })
            i += 1
            continue

        # Arrow bullet: → item
        arrow_match = re.match(r'^→\s+(.*)', stripped)
        if arrow_match:
            text = arrow_match.group(1)
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": parse_inline(text),
                }
            })
            i += 1
            continue

        # Lines starting with emoji → bulleted list item
        if starts_with_emoji(stripped):
            # Check it's not a heading (those start with #)
            emoji, rest = extract_leading_emoji(stripped)
            if emoji and rest:
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": parse_inline(stripped),
                    }
                })
                i += 1
                continue

        # Regular paragraph
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": parse_inline(stripped),
            }
        })
        i += 1

    return blocks


# --- Notion API functions ---

def append_blocks(page_id, blocks):
    """Append blocks to a page in batches of MAX_BLOCKS_PER_REQUEST."""
    for start in range(0, len(blocks), MAX_BLOCKS_PER_REQUEST):
        batch = blocks[start:start + MAX_BLOCKS_PER_REQUEST]
        notion_request("PATCH", f"/blocks/{page_id}/children", {
            "children": batch,
        })


def create_guide_page(db_id, title, keyword="", guide_type="", week="", status="Review", blocks=None):
    """
    Create a page in a Guide Database.
    Title property name is "Guide Title".
    Returns (page_id, url).
    """
    blocks = blocks or []

    properties = {
        "Guide Title": {
            "title": [{"type": "text", "text": {"content": title}}]
        },
    }
    if keyword:
        properties["Keyword"] = {
            "rich_text": [{"type": "text", "text": {"content": keyword}}]
        }
    if guide_type:
        properties["Type"] = {"select": {"name": guide_type}}
    if week:
        properties["Week"] = {"date": {"start": week}}
    if status:
        properties["Status"] = {"select": {"name": status}}

    # First 100 blocks go in the creation request
    first_batch = blocks[:MAX_BLOCKS_PER_REQUEST]
    remaining = blocks[MAX_BLOCKS_PER_REQUEST:]

    body = {
        "parent": {"database_id": db_id},
        "properties": properties,
        "children": first_batch,
    }

    result = notion_request("POST", "/pages", body)
    page_id = result["id"]
    url = result["url"]

    # Append remaining blocks in batches
    if remaining:
        append_blocks(page_id, remaining)

    return page_id, url


def create_subpage(parent_page_id, title, blocks=None):
    """
    Create a child page under an existing page.
    Uses standard "title" property.
    Returns (page_id, url).
    """
    blocks = blocks or []

    first_batch = blocks[:MAX_BLOCKS_PER_REQUEST]
    remaining = blocks[MAX_BLOCKS_PER_REQUEST:]

    body = {
        "parent": {"page_id": parent_page_id},
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

    return page_id, url


def create_content_entry(title, account, post_date, day, content_type, keyword,
                         guide_link=None, variations=None):
    """
    Create a Content Board entry in the content board database.
    Variations is a list of (angle_name, post_text) tuples that become
    toggle blocks with code block children (language: plain text).
    Returns (page_id, url).
    """
    properties = {
        "Title": {
            "title": [{"type": "text", "text": {"content": title}}]
        },
        "Account": {"select": {"name": account}},
        "Post Date": {"date": {"start": post_date}},
        "Day": {"select": {"name": day}},
        "Type": {"select": {"name": content_type}},
        "Status": {"select": {"name": "Review"}},
        "Keyword": {
            "rich_text": [{"type": "text", "text": {"content": keyword}}]
        },
    }
    if guide_link:
        properties["Guide Link"] = {"url": guide_link}

    # Build toggle blocks for variations
    children = []
    if variations:
        for angle_name, post_text in variations:
            toggle_block = {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": angle_name}}],
                    "is_toggleable": True,
                    "children": [
                        {
                            "type": "code",
                            "code": {
                                "rich_text": split_rich_text([
                                    {"type": "text", "text": {"content": post_text}}
                                ]),
                                "language": "plain text",
                            }
                        }
                    ]
                }
            }
            children.append(toggle_block)

    first_batch = children[:MAX_BLOCKS_PER_REQUEST]
    remaining = children[MAX_BLOCKS_PER_REQUEST:]

    body = {
        "parent": {"database_id": get_content_board_db()},
        "properties": properties,
        "children": first_batch,
    }

    result = notion_request("POST", "/pages", body)
    page_id = result["id"]
    url = result["url"]

    if remaining:
        append_blocks(page_id, remaining)

    return page_id, url


# --- Title extraction ---

def extract_title(md_text):
    """Extract the first H1 title from markdown text."""
    for line in md_text.split('\n'):
        m = re.match(r'^#\s+(.*)', line.strip())
        if m:
            return m.group(1).strip()
    return "Untitled"


# --- CLI ---

def cmd_publish_guide(args):
    """Publish a markdown file as a guide page in a Notion database."""
    with open(args.md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()

    title = extract_title(md_text)
    blocks = md_to_blocks(md_text, skip_first_h1=True)

    print(f"Publishing guide: {title}")
    print(f"  Database: {args.database_id}")
    print(f"  Blocks: {len(blocks)}")

    page_id, url = create_guide_page(
        db_id=args.database_id,
        title=title,
        keyword=args.keyword or "",
        guide_type=args.type or "",
        week=args.week or "",
        status=args.status or "Review",
        blocks=blocks,
    )

    print(f"  Page ID: {page_id}")
    print(f"  URL: {url}")
    return page_id, url


def cmd_publish_subpage(args):
    """Publish a markdown file as a subpage under an existing Notion page."""
    with open(args.md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()

    title = extract_title(md_text)
    blocks = md_to_blocks(md_text, skip_first_h1=True)

    print(f"Publishing subpage: {title}")
    print(f"  Parent: {args.parent_page_id}")
    print(f"  Blocks: {len(blocks)}")

    page_id, url = create_subpage(
        parent_page_id=args.parent_page_id,
        title=title,
        blocks=blocks,
    )

    print(f"  Page ID: {page_id}")
    print(f"  URL: {url}")
    return page_id, url


def cmd_create_content_entry(args):
    """Create a content board entry."""
    variations = []
    if args.variation:
        for v in args.variation:
            if '|' in v:
                angle, text = v.split('|', 1)
                variations.append((angle.strip(), text.strip()))

    print(f"Creating content entry: {args.title}")

    page_id, url = create_content_entry(
        title=args.title,
        account=args.account,
        post_date=args.post_date,
        day=args.day,
        content_type=args.content_type,
        keyword=args.keyword,
        guide_link=args.guide_link,
        variations=variations,
    )

    print(f"  Page ID: {page_id}")
    print(f"  URL: {url}")
    return page_id, url


def main():
    parser = argparse.ArgumentParser(description="Markdown to Notion publisher")
    subparsers = parser.add_subparsers(dest="command")

    # publish-guide
    pg = subparsers.add_parser("publish-guide", help="Publish markdown as guide page")
    pg.add_argument("md_file", help="Path to markdown file")
    pg.add_argument("database_id", help="Notion database ID")
    pg.add_argument("--keyword", default="", help="Guide keyword")
    pg.add_argument("--type", default="", help="Guide type")
    pg.add_argument("--week", default="", help="Week date YYYY-MM-DD")
    pg.add_argument("--status", default="Review", help="Status")

    # publish-subpage
    ps = subparsers.add_parser("publish-subpage", help="Publish markdown as subpage")
    ps.add_argument("md_file", help="Path to markdown file")
    ps.add_argument("parent_page_id", help="Parent page ID in Notion")

    # create-content-entry
    ce = subparsers.add_parser("create-content-entry", help="Create content board entry")
    ce.add_argument("--title", required=True, help="Post title")
    ce.add_argument("--account", required=True, help="Account name")
    ce.add_argument("--post-date", required=True, help="Post date YYYY-MM-DD")
    ce.add_argument("--day", required=True, help="Day of week")
    ce.add_argument("--content-type", required=True, help="Content type")
    ce.add_argument("--keyword", required=True, help="Keyword")
    ce.add_argument("--guide-link", default=None, help="Guide link URL")
    ce.add_argument("--variation", action="append", help="Variation as 'Angle|text'")

    args = parser.parse_args()

    if args.command == "publish-guide":
        cmd_publish_guide(args)
    elif args.command == "publish-subpage":
        cmd_publish_subpage(args)
    elif args.command == "create-content-entry":
        cmd_create_content_entry(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
