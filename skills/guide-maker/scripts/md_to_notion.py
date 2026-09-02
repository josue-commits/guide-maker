#!/usr/bin/env python3
"""
Markdown to Notion Block Converter & Publisher

Converts markdown files to Notion API block format and publishes them
as pages in Notion databases or as subpages under existing pages.

Usage:
    python3 md_to_notion.py publish-guide <md_file> <database_id> [options]
    python3 md_to_notion.py publish-subpage <md_file> <parent_page_id>
    python3 md_to_notion.py create-content-entry [options]
    python3 md_to_notion.py blocks <md_file>

Options for publish-guide:
    --keyword TEXT       Keyword for the guide (e.g., SKILLS)
    --type TEXT          Guide type (e.g., "Technical Tutorial")
    --week DATE          Week date in YYYY-MM-DD format
    --status TEXT        Status (default: Review)
    --dry-run            Print the block plan, do not call Notion

Options for create-content-entry (one card per guide):
    --title TEXT         Card title, e.g. "KEYWORD | Mon 09/07"
    --account TEXT       Account name (select option in the board)
    --post-date DATE     Post date YYYY-MM-DD
    --day TEXT           Day of week (Monday/Wednesday/Friday)
    --type TEXT          Type select option (default: guide)
    --status TEXT        Status select option (default: Draft)
    --keyword TEXT       Keyword (same as the guide's)
    --guide-link URL     In-app guide URL (optional)
    --variation TEXT     Repeatable: "Label|post text" or "Label|@/path/file.txt"
    --dm TEXT            Repeatable: "Label|dm text" or "Label|@/path/file.txt"
    --graphic PATH       PNG to attach to the `Graphic` files property. Never an
                         image block in the body: calendar and gallery views only
                         surface the property.
    --dry-run            Print the payload, do not call Notion

The `blocks` subcommand converts a markdown file and prints the Notion block
JSON. Use it to check fences, directives and tables without touching Notion.
"""

import re
import sys
import json
import argparse
import urllib.request
import urllib.error

# Authoring directives a writer may leave at the top of a subpage. These are
# notes to the publisher, not content, and must never reach the page body.
# Matches "**Page icon:** X", "Page icon: X", "icon: X", "**Icon:** X" and the
# like, but deliberately NOT prose that merely starts with the word icon (the
# value has to be short, so "Icons: here is why they matter" is left alone).
# The page icon is set from --icon at creation time, so these lines carry no
# information the publisher needs. Drop them.
DIRECTIVE_LINE = re.compile(
    r'^\*{0,2}(?:page\s+)?icon\*{0,2}\s*:\s*\**\s*\S{1,8}\s*\**\s*$',
    re.IGNORECASE)

# HTML comments ("<!-- icon: X -->") are never rendered either.
HTML_COMMENT_LINE = re.compile(r'^<!--.*-->$')

# --- Configuration ---

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_config, cfg_get, add_config_arg
import _notion

_CFG = None


def config(path=None):
    """Load (once) and return the config; also primes the Notion token."""
    global _CFG
    if _CFG is None:
        _CFG = load_config(path)
        _notion.init(_CFG)
    return _CFG


def get_content_board_db():
    db = cfg_get(config(), "notion.content_board_database_id", "")
    if not db:
        raise SystemExit("notion.content_board_database_id is empty in the config; "
                         "the Content Board card cannot be created.")
    return db
from _notion import NOTION_VERSION, NOTION_BASE  # re-exported for callers

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
    "sh": "shell", "zsh": "shell", "shell-session": "shell", "console": "shell",
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


# --- HTTP helpers (stdlib only, shared in _notion.py) ---

def notion_request(method, path, body=None):
    """Authenticated Notion request with retry. Kept as a thin alias."""
    return _notion.request(method, path, body)


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

        # HTML comments and authoring directives never render as text
        if HTML_COMMENT_LINE.match(stripped) or DIRECTIVE_LINE.match(stripped):
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


def _toggle_block(level, label, text):
    """A toggleable heading whose child is a plain-text code block.

    The code block gives Notion's native copy button, so a person can paste
    the variation or DM with one click.
    """
    heading = f"heading_{level}"
    return {
        "type": heading,
        heading: {
            "rich_text": [{"type": "text", "text": {"content": label}}],
            "is_toggleable": True,
            "children": [{
                "type": "code",
                "code": {
                    "rich_text": split_rich_text([
                        {"type": "text", "text": {"content": text}}
                    ]),
                    "language": "plain text",
                }
            }],
        },
    }


def build_content_entry(title, account, post_date, day, content_type, keyword,
                        guide_link=None, variations=None, dms=None,
                        status="Draft", notes=""):
    """Return (properties, children) for a Content Board card.

    Variations become H2 toggles, DMs go under a divider and an H2 "DM
    Templates" heading as H3 toggles. Each toggle wraps a plain-text code
    block. The graphic is NOT part of the body; see set_graphic().
    """
    properties = {
        "Title": {"title": [{"type": "text", "text": {"content": title}}]},
        "Post Date": {"date": {"start": post_date}},
        "Type": {"select": {"name": content_type}},
        "Status": {"select": {"name": status}},
        "Keyword": {"rich_text": [{"type": "text", "text": {"content": keyword}}]},
    }
    if account:
        properties["Account"] = {"select": {"name": account}}
    if day:
        properties["Day"] = {"select": {"name": day}}
    if guide_link:
        properties["Guide Link"] = {"url": guide_link}
    if notes:
        properties["Notes"] = {"rich_text": [{"type": "text", "text": {"content": notes[:2000]}}]}

    children = []
    for label, text in (variations or []):
        children.append(_toggle_block(2, label, text))
    if dms:
        children.append({"type": "divider", "divider": {}})
        children.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "DM Templates"}}],
                "is_toggleable": False,
            },
        })
        for label, text in dms:
            children.append(_toggle_block(3, label, text))
    return properties, children


def create_content_entry(title, account, post_date, day, content_type, keyword,
                         guide_link=None, variations=None, dms=None,
                         status="Draft", notes="", graphic=None, database_id=None):
    """
    Create a Content Board card. Returns (page_id, url).

    `variations` and `dms` are lists of (label, text) tuples. `graphic` is a
    local image path attached to the `Graphic` files property.
    """
    properties, children = build_content_entry(
        title, account, post_date, day, content_type, keyword,
        guide_link=guide_link, variations=variations, dms=dms,
        status=status, notes=notes)

    if graphic:
        upload_id = _notion.upload_file(graphic)
        properties["Graphic"] = {"files": [{
            "type": "file_upload",
            "file_upload": {"id": upload_id},
            "name": os.path.basename(graphic),
        }]}

    first_batch = children[:MAX_BLOCKS_PER_REQUEST]
    remaining = children[MAX_BLOCKS_PER_REQUEST:]
    body = {
        "parent": {"database_id": database_id or get_content_board_db()},
        "properties": properties,
        "children": first_batch,
    }
    # A file_upload reference in a property needs the newer API version.
    version = _notion.NOTION_VERSION_UPLOAD if graphic else None
    result = _notion.request("POST", "/pages", body, version=version)
    page_id = result["id"]
    url = result["url"]
    if remaining:
        append_blocks(page_id, remaining)
    return page_id, url


def set_graphic(page_id, graphic_path):
    """Attach a local image to an existing card's `Graphic` files property."""
    upload_id = _notion.upload_file(graphic_path)
    _notion.set_files_property(page_id, "Graphic", upload_id, os.path.basename(graphic_path))
    return upload_id


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
    if args.dry_run:
        print(json.dumps(blocks[:5], indent=2, ensure_ascii=False))
        print("Dry run: no changes made.")
        return None, None

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
    if args.dry_run:
        print(json.dumps(blocks[:5], indent=2, ensure_ascii=False))
        print("Dry run: no changes made.")
        return None, None

    page_id, url = create_subpage(
        parent_page_id=args.parent_page_id,
        title=title,
        blocks=blocks,
    )

    print(f"  Page ID: {page_id}")
    print(f"  URL: {url}")
    return page_id, url


def _parse_labeled(items, kind):
    """Parse repeatable "Label|text-or-@file" arguments into (label, text)."""
    out = []
    for item in items or []:
        if "|" not in item:
            print(f"Error: --{kind} needs the form 'Label|text' or 'Label|@file': {item!r}",
                  file=sys.stderr)
            sys.exit(2)
        label, text = item.split("|", 1)
        label, text = label.strip(), text.strip()
        if text.startswith("@"):
            path = text[1:]
            if not os.path.exists(path):
                print(f"Error: --{kind} file not found: {path}", file=sys.stderr)
                sys.exit(2)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read().strip()
        if not label or not text:
            print(f"Error: empty label or text in --{kind}: {item!r}", file=sys.stderr)
            sys.exit(2)
        out.append((label, text))
    return out


def cmd_create_content_entry(args):
    """Create a Content Board card with copy toggles, DM toggles and graphic."""
    variations = _parse_labeled(args.variation, "variation")
    dms = _parse_labeled(args.dm, "dm")

    if args.graphic and not os.path.exists(args.graphic):
        print(f"Error: graphic not found: {args.graphic}", file=sys.stderr)
        sys.exit(2)
    if args.guide_link and "notion.site" in args.guide_link:
        print("Warning: Guide Link is normally the in-app URL; the public "
              "notion.site URL belongs in the DMs.", file=sys.stderr)

    if args.dry_run:
        properties, children = build_content_entry(
            args.title, args.account, args.post_date, args.day, args.type,
            args.keyword, guide_link=args.guide_link, variations=variations,
            dms=dms, status=args.status, notes=args.notes)
        plan = {
            "database_id": args.database_id or "(content_board_database_id from config)",
            "properties": properties,
            "children": children,
            "graphic": args.graphic,
            "toggles": {"copy": len(variations), "dm": len(dms)},
        }
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        print(f"\nDry run: {len(variations)} copy toggles, {len(dms)} DM toggles, "
              f"graphic={'yes' if args.graphic else 'no'}. No changes made.")
        return None, None

    print(f"Creating content entry: {args.title}")
    page_id, url = create_content_entry(
        title=args.title, account=args.account, post_date=args.post_date,
        day=args.day, content_type=args.type, keyword=args.keyword,
        guide_link=args.guide_link, variations=variations, dms=dms,
        status=args.status, notes=args.notes, graphic=args.graphic,
        database_id=args.database_id)
    print(f"  Page ID: {page_id}")
    print(f"  URL: {url}")
    print(f"  Toggles: {len(variations)} copy, {len(dms)} DM"
          + (", graphic attached" if args.graphic else ""))
    return page_id, url


def cmd_blocks(args):
    """Convert a markdown file and print the Notion block JSON."""
    with open(args.md_file, "r", encoding="utf-8") as fh:
        md_text = fh.read()
    blocks = md_to_blocks(md_text, skip_first_h1=not args.keep_h1)
    print(json.dumps(blocks, indent=2, ensure_ascii=False))
    print(f"\n{len(blocks)} blocks, title: {extract_title(md_text)!r}", file=sys.stderr)


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
    pg.add_argument("--dry-run", action="store_true", help="Print blocks, do not publish")

    # publish-subpage
    ps = subparsers.add_parser("publish-subpage", help="Publish markdown as subpage")
    ps.add_argument("md_file", help="Path to markdown file")
    ps.add_argument("parent_page_id", help="Parent page ID in Notion")
    ps.add_argument("--dry-run", action="store_true", help="Print blocks, do not publish")

    # blocks
    bl = subparsers.add_parser("blocks", help="Print Notion block JSON for a markdown file")
    bl.add_argument("md_file", help="Path to markdown file")
    bl.add_argument("--keep-h1", action="store_true", help="Keep the first H1 as a heading")

    # create-content-entry
    ce = subparsers.add_parser("create-content-entry", help="Create a Content Board card")
    ce.add_argument("--title", required=True, help="Card title")
    ce.add_argument("--account", default="", help="Account name (select option)")
    ce.add_argument("--post-date", required=True, help="Post date YYYY-MM-DD")
    ce.add_argument("--day", default="", help="Day of week")
    ce.add_argument("--type", "--content-type", dest="type", default="guide",
                    help="Type select option (default: guide)")
    ce.add_argument("--status", default="Draft", help="Status select option (default: Draft)")
    ce.add_argument("--keyword", required=True, help="Keyword")
    ce.add_argument("--guide-link", default=None, help="In-app guide URL")
    ce.add_argument("--variation", action="append", default=[],
                    help="Repeatable: 'Label|text' or 'Label|@file'")
    ce.add_argument("--dm", action="append", default=[],
                    help="Repeatable: 'Label|text' or 'Label|@file'")
    ce.add_argument("--graphic", default=None,
                    help="Image to attach to the Graphic files property")
    ce.add_argument("--notes", default="", help="Notes property text")
    ce.add_argument("--database-id", default=None,
                    help="Override content_board_database_id from config")
    ce.add_argument("--dry-run", action="store_true", help="Print payload, do not publish")

    add_config_arg(parser, [pg, ps, bl, ce])
    args = parser.parse_args()
    config_path = getattr(args, "config", None)

    if args.command != "blocks" and not getattr(args, "dry_run", False):
        config(config_path)
    elif config_path:
        config(config_path)

    if args.command == "publish-guide":
        cmd_publish_guide(args)
    elif args.command == "publish-subpage":
        cmd_publish_subpage(args)
    elif args.command == "blocks":
        cmd_blocks(args)
    elif args.command == "create-content-entry":
        cmd_create_content_entry(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
