#!/usr/bin/env python3
"""Lint LinkedIn copy, DM text and closer rotation against the house rules.

Usage:
    lint_copy.py copy FILE... [--cta-mode graphic|copy] [--keyword KW] [--json] [--strict]
    lint_copy.py dm FILE... [--merge-tag TAG] [--json] [--strict]
    lint_copy.py rotation --log FILE [--weeks N] [--json]

A FILE ending in .md is split on fenced code blocks and each block is linted
on its own (so references/linkedin/examples.md and templates/dm-*.md lint
their bodies, not their prose). Any other file is linted whole.

Exit codes: 0 clean, 1 at least one failure, 2 warnings only.
--strict turns warnings into failures.

Copy rules (id, level):
    em-dash          FAIL  U+2014 or U+2013 anywhere
    banned-word      FAIL  any form of a word in the humanizer list + copy.extra_banned_words
    banned-phrase    FAIL  a phrase in the humanizer list
    keyword-in-copy  FAIL  the keyword (or a quoted ALL-CAPS token after "comment") in the text;
                           WARN in --cta-mode copy, and the impression numbers are printed
    banned-cta       FAIL  engagement instructions: like this post, connect with me, repost,
                           numbered instruction block, thumbs-up; the "comment X" family is
                           WARN in --cta-mode copy
    hashtag          FAIL  #tag
    markdown         FAIL  **bold**, headings, underscores
    bullet-style     FAIL  lines starting with "- " or a bullet dot (use the arrow)
    emoji            FAIL  any emoji except the pointing-down one as the final character;
                           check mark and siren are WARN
    closer           FAIL  last line does not end on the pointing-down emoji;
                           WARN when the value line is not one of copy.closers
    word-count       FAIL  outside reject_below..reject_above; WARN outside min..max

DM rules:
    name-tag           FAIL  {name}, [Name], {first_name}, {firstName} (single braces)
    missing-merge-tag  WARN  the configured merge tag is absent
    hard-wrap          FAIL  a paragraph spans more than one line (bare URL or {slot} lines allowed)
    public-url         FAIL  app.notion.com or notion.so link when dm.guide_link_must_be_public
    em-dash            FAIL
    max-lines          WARN  more than dm.max_lines non-blank lines
    formula-opener     FAIL  "thanks for commenting", "thanks for the interest", "thanks for your interest"
    collab-signoff     FAIL  "let me know if you have any questions", "hope this helps", "happy to chat"
    banned-word        FAIL

Rotation (--log FILE, JSONL rows {"date": "YYYY-MM-DD", "closer": "..."}):
    closer-repeat-week  FAIL  same closer twice in one ISO week
    closer-repeat-run   FAIL  same closer in N consecutive weeks (copy.closer_rotation_weeks)
"""

import argparse
import copy as _copy
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_config, cfg_get, skill_dir, DEFAULTS, add_config_arg  # noqa: E402

POINT_DOWN = "\U0001F447"   # the only emoji allowed in copy, final character
THUMBS_UP = "\U0001F44D"
SOFT_EMOJI = {"✅", "\U0001F6A8"}  # check mark, siren: allowed when they carry weight
ARROW = "→"

IMPRESSION_NOTE = ("copy.cta_mode is copy: the keyword is in the text. Evidence for the "
                   "default: same asset 95 impressions with the instruction in the copy, "
                   "11,432 without; one account went from 62,000 to 43 the week its copy "
                   "carried the keyword. See references/strategy/cta-evidence.md")

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF"
    "\U00002B50\U00002B06\U00002B07\U00002B05\U00002934\U00002935⌚⌛⏩-⏳⏸-⏺]")
EMDASH_RE = re.compile("[\u2014\u2013]")  # em dash, en dash
HASHTAG_RE = re.compile(r"(?:^|\s)#[A-Za-z][\w]*")
MARKDOWN_RE = re.compile(r"(\*\*[^*]+\*\*)|(__[^_]+__)|(^#{1,6}\s)|(^>\s)", re.M)
BULLET_RE = re.compile(r"^\s*(?:-|•|\*)\s+\S", re.M)
NUMBERED_BLOCK_RE = re.compile(r"^\s*1[.)]\s.+\n(?:\s*\n)?\s*2[.)]\s", re.M)
QUOTED_KEYWORD_RE = re.compile(r"comment\s+[\"“'‘]([A-Za-z]{3,12})[\"”'’]", re.I)
URL_RE = re.compile(r"https?://\S+")
SLOT_LINE_RE = re.compile(r"^\{[a-z_]+\}$")
NAME_TAG_RE = re.compile(r"\{name\}|\[name\]|\{first_?name\}|\[first_?name\]|\{firstName\}", re.I)
KNOWN_MERGE_TAGS = ["{{firstName}}", "{{lastName}}", "{{fullName}}", "{{linkedinUsername}}"]
APP_URL_RE = re.compile(r"https?://(?:www\.)?(?:app\.notion\.com|notion\.so)/\S+", re.I)
FORMULA_OPENER_RE = re.compile(r"thanks for (?:commenting|the interest|your interest)|thank you for (?:commenting|your interest)", re.I)
COLLAB_SIGNOFF_RE = re.compile(r"let me know if you have any questions|hope this helps|happy to chat|feel free to reach out", re.I)

CTA_INSTRUCTION_ALWAYS = ["like this post", "connect with me", "repost this", "share this post",
                          "follow me and", "hit the like"]
CTA_INSTRUCTION_COMMENT = ["comment \"", "comment '", "comment “", "and i'll send it",
                           "and i will send it", "and i'll dm", "dm me"]


# --- helpers ------------------------------------------------------------------

def _config(path):
    try:
        return load_config(path)
    except FileNotFoundError:
        cfg = _copy.deepcopy(DEFAULTS)
        cfg["_path"] = ""
        return cfg


def _read_marked_list(text, name):
    start = f"<!-- lint:{name}:start -->"
    end = f"<!-- lint:{name}:end -->"
    if start not in text or end not in text:
        return []
    body = text.split(start, 1)[1].split(end, 1)[0]
    sep = ";" if name == "banned-phrases" else ","
    items = []
    for chunk in re.split(rf"[{sep}\n]", body):
        chunk = chunk.strip().strip("`").strip()
        if chunk:
            items.append(chunk)
    return items


def load_banned(cfg):
    """(words, phrases) from the humanizer file plus copy.extra_banned_words."""
    rel = cfg_get(cfg, "copy.banned_words_file") or "references/writing/humanizer.md"
    path = os.path.join(str(skill_dir()), rel) if not os.path.isabs(rel) else rel
    words, phrases = [], []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        words = _read_marked_list(text, "banned-words")
        phrases = _read_marked_list(text, "banned-phrases")
    for extra in cfg_get(cfg, "copy.extra_banned_words") or []:
        if extra and extra not in words:
            words.append(extra)
    return words, phrases


def _word_pattern(word):
    stem = word[:-1] if word.endswith("e") else word
    return re.compile(r"\b" + re.escape(stem) + r"\w{0,3}\b", re.I)


def _normalize(text):
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def split_blocks(path):
    """[(label, text)]: fenced blocks for .md files, the whole file otherwise."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.lower().endswith(".md"):
        blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
        if blocks:
            return [(f"{path}#block{i + 1}", b.strip("\n")) for i, b in enumerate(blocks)]
        # no fences: strip headings and comments and lint the rest
        lines = [l for l in text.splitlines() if not l.startswith("#") and not l.strip().startswith("<!--")]
        return [(path, "\n".join(lines).strip())]
    return [(path, text.strip("\n"))]


class Report:
    def __init__(self, label):
        self.label = label
        self.findings = []

    def fail(self, rule, message, line=None):
        self.findings.append({"rule": rule, "level": "FAIL", "message": message, "line": line})

    def warn(self, rule, message, line=None):
        self.findings.append({"rule": rule, "level": "WARN", "message": message, "line": line})

    @property
    def status(self):
        levels = {f["level"] for f in self.findings}
        if "FAIL" in levels:
            return "FAIL"
        if "WARN" in levels:
            return "WARN"
        return "OK"


def _line_of(text, match_start):
    return text.count("\n", 0, match_start) + 1


# --- copy ---------------------------------------------------------------------

def lint_copy_text(text, cfg, keyword=None, cta_mode=None):
    rep = Report("")
    norm = _normalize(text)
    cta_mode = cta_mode or cfg_get(cfg, "copy.cta_mode") or "graphic"
    copy_mode = cta_mode == "copy"
    words_cfg = cfg_get(cfg, "copy.words") or {}
    closers = [c.rstrip(" ↓") for c in (cfg_get(cfg, "copy.closers") or [])]
    banned_words, banned_phrases = load_banned(cfg)

    for m in EMDASH_RE.finditer(norm):
        rep.fail("em-dash", "em dash or en dash; use a period, comma or colon", _line_of(norm, m.start()))

    for word in banned_words:
        m = _word_pattern(word).search(norm)
        if m:
            rep.fail("banned-word", f"banned word {m.group(0)!r} (from {word!r})", _line_of(norm, m.start()))
    low = norm.lower()
    for phrase in banned_phrases:
        idx = low.find(phrase.lower())
        if idx >= 0:
            rep.fail("banned-phrase", f"banned phrase {phrase!r}", _line_of(norm, idx))

    # keyword in copy
    kw_hits = []
    if keyword:
        for m in re.finditer(r"\b" + re.escape(keyword) + r"\b", norm, re.I):
            kw_hits.append((m.group(0), _line_of(norm, m.start())))
    for m in QUOTED_KEYWORD_RE.finditer(norm):
        token = m.group(1)
        if token.isupper() and (not keyword or token.upper() != keyword.upper()):
            kw_hits.append((token, _line_of(norm, m.start())))
    for token, line in kw_hits:
        msg = f"keyword {token!r} appears in the copy; it belongs in the post graphic only"
        if copy_mode:
            rep.warn("keyword-in-copy", msg + " (allowed by copy.cta_mode: copy)", line)
        else:
            rep.fail("keyword-in-copy", msg, line)

    # engagement instructions
    for needle in CTA_INSTRUCTION_ALWAYS:
        idx = low.find(needle)
        if idx >= 0:
            rep.fail("banned-cta", f"engagement instruction {needle!r}; LinkedIn suppresses it", _line_of(norm, idx))
    for needle in CTA_INSTRUCTION_COMMENT:
        idx = low.find(needle)
        if idx >= 0:
            msg = f"comment instruction {needle.strip()!r} in the copy"
            if copy_mode:
                rep.warn("banned-cta", msg + " (allowed by copy.cta_mode: copy)", _line_of(norm, idx))
            else:
                rep.fail("banned-cta", msg + "; the keyword lives in the graphic", _line_of(norm, idx))
    m = NUMBERED_BLOCK_RE.search(norm)
    if m:
        rep.fail("banned-cta", "numbered instruction block (1. ... 2. ...)", _line_of(norm, m.start()))
    if THUMBS_UP in norm:
        rep.fail("banned-cta", "thumbs-up emoji is banned outright", _line_of(norm, norm.index(THUMBS_UP)))

    for m in HASHTAG_RE.finditer(norm):
        rep.fail("hashtag", f"hashtag {m.group(0).strip()!r}", _line_of(norm, m.start()))
    for m in MARKDOWN_RE.finditer(norm):
        rep.fail("markdown", f"markdown formatting {m.group(0).strip()[:20]!r}; plain text only", _line_of(norm, m.start()))
    for m in BULLET_RE.finditer(norm):
        rep.fail("bullet-style", "bullet with - or dot; use the arrow, and only for a framework", _line_of(norm, m.start()))

    # emoji placement
    stripped = norm.rstrip()
    for m in EMOJI_RE.finditer(norm):
        ch = m.group(0)
        pos = m.start()
        if ch == POINT_DOWN and pos == len(stripped) - 1:
            continue
        if ch in SOFT_EMOJI:
            rep.warn("emoji", f"{ch} allowed only when it carries real weight", _line_of(norm, pos))
            continue
        if ch == POINT_DOWN:
            rep.fail("emoji", "pointing-down emoji must be the final character only", _line_of(norm, pos))
        else:
            rep.fail("emoji", f"emoji {ch!r} in the body", _line_of(norm, pos))

    # closer
    lines = [l for l in stripped.splitlines() if l.strip()]
    last = lines[-1].strip() if lines else ""
    if not last.endswith(POINT_DOWN):
        rep.fail("closer", "last line must be one value line ending on the pointing-down emoji", len(norm.splitlines()))
    else:
        value = last[:-1].strip()
        if copy_mode:
            value = re.sub(r"\.?\s*comment\s+[\"'][A-Za-z]{3,12}[\"']\s+and i(?:'ll| will) send it\s*$", "", value, flags=re.I).strip()
        if closers and value.rstrip(".") not in [c.rstrip(".") for c in closers]:
            rep.warn("closer", f"closer {value!r} is not in copy.closers; fine if deliberate, rotate it", len(norm.splitlines()))

    # word count
    count = len([t for t in norm.split() if EMOJI_RE.sub("", t).strip()])
    lo, hi = int(words_cfg.get("min", 180)), int(words_cfg.get("max", 250))
    rb, ra = int(words_cfg.get("reject_below", 140)), int(words_cfg.get("reject_above", 300))
    if count < rb or count > ra:
        rep.fail("word-count", f"{count} words; hard limits are {rb}-{ra}")
    elif count < lo or count > hi:
        rep.warn("word-count", f"{count} words; target range is {lo}-{hi}")

    rep.count = count
    return rep


# --- dm -----------------------------------------------------------------------

def lint_dm_text(text, cfg, merge_tag=None):
    rep = Report("")
    norm = _normalize(text)
    merge_tag = merge_tag or cfg_get(cfg, "dm.merge_tag") or "{{firstName}}"
    max_lines = int(cfg_get(cfg, "dm.max_lines") or 7)
    must_public = bool(cfg_get(cfg, "dm.guide_link_must_be_public"))
    banned_words, _ = load_banned(cfg)

    for m in EMDASH_RE.finditer(norm):
        rep.fail("em-dash", "em dash or en dash", _line_of(norm, m.start()))
    # blank out the real merge tags first so {{firstName}} never trips the check
    scrubbed = norm
    for tag in set(KNOWN_MERGE_TAGS + [merge_tag]):
        if tag:
            scrubbed = scrubbed.replace(tag, " " * len(tag))
    for m in NAME_TAG_RE.finditer(scrubbed):
        rep.fail("name-tag", f"{m.group(0)!r} is not a merge tag any tool substitutes; use {merge_tag}", _line_of(norm, m.start()))
    if merge_tag and merge_tag not in norm:
        rep.warn("missing-merge-tag", f"merge tag {merge_tag} absent; the DM will not be personalized")

    # hard wrap: a paragraph (blank-line separated) with 2+ lines where a
    # non-URL, non-slot line follows another line
    paragraphs, current = [], []
    for raw in norm.splitlines():
        if raw.strip():
            current.append(raw.strip())
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    line_no = 0
    for para in paragraphs:
        if len(para) > 1:
            soft = [l for l in para if not (URL_RE.fullmatch(l) or SLOT_LINE_RE.fullmatch(l))]
            if len(soft) > 1:
                rep.fail("hard-wrap", "paragraph is hard-wrapped; one paragraph is one line, blank lines separate paragraphs")
        line_no += len(para)

    if must_public:
        for m in APP_URL_RE.finditer(norm):
            rep.fail("public-url", f"{m.group(0)} is the in-app link; leads outside the workspace get a dead end. Use the public notion.site URL", _line_of(norm, m.start()))

    nonblank = [l for l in norm.splitlines() if l.strip()]
    if len(nonblank) > max_lines:
        rep.warn("max-lines", f"{len(nonblank)} non-blank lines; dm.max_lines is {max_lines}")

    m = FORMULA_OPENER_RE.search(norm)
    if m:
        rep.fail("formula-opener", f"formula opener {m.group(0)!r}; open differently every week", _line_of(norm, m.start()))
    m = COLLAB_SIGNOFF_RE.search(norm)
    if m:
        rep.fail("collab-signoff", f"collaborative sign-off {m.group(0)!r}; sign off with the bare first name", _line_of(norm, m.start()))
    for word in banned_words:
        m = _word_pattern(word).search(norm)
        if m:
            rep.fail("banned-word", f"banned word {m.group(0)!r}", _line_of(norm, m.start()))
    return rep


# --- rotation -----------------------------------------------------------------

def lint_rotation(log_path, weeks):
    rep = Report(log_path)
    rows = []
    with open(log_path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                rep.warn("log-format", f"line {n} is not JSON; skipped")
                continue
            closer = (row.get("closer") or "").rstrip(" ↓" + POINT_DOWN).strip()
            date = row.get("date") or row.get("week")
            if not closer or not date:
                rep.warn("log-format", f"line {n} lacks closer or date; skipped")
                continue
            try:
                d = dt.date.fromisoformat(str(date)[:10])
            except ValueError:
                rep.warn("log-format", f"line {n} has an unparseable date {date!r}; skipped")
                continue
            iso = d.isocalendar()
            rows.append((iso[0] * 100 + iso[1], closer))

    by_week = {}
    for week, closer in rows:
        by_week.setdefault(week, []).append(closer)
    for week in sorted(by_week):
        seen = {}
        for closer in by_week[week]:
            seen[closer] = seen.get(closer, 0) + 1
        for closer, n in seen.items():
            if n > 1:
                rep.fail("closer-repeat-week", f"week {week}: {closer!r} used {n} times; one closer per variation")

    ordered = sorted(by_week)
    for i in range(len(ordered)):
        window = ordered[i:i + weeks]
        if len(window) < weeks:
            break
        common = set(by_week[window[0]])
        for w in window[1:]:
            common &= set(by_week[w])
        for closer in common:
            rep.fail("closer-repeat-run", f"{closer!r} used in {weeks} consecutive weeks ending {window[-1]}")
    return rep


# --- CLI ----------------------------------------------------------------------

def _print_reports(reports, as_json, strict):
    exit_code = 0
    for rep in reports:
        for f in rep.findings:
            if strict and f["level"] == "WARN":
                f["level"] = "FAIL"
        if rep.status == "FAIL":
            exit_code = 1
        elif rep.status == "WARN" and exit_code == 0:
            exit_code = 2
    if as_json:
        print(json.dumps({"files": [{"file": r.label, "status": r.status,
                                     "words": getattr(r, "count", None),
                                     "findings": r.findings} for r in reports],
                          "exit": exit_code}, indent=2, ensure_ascii=False))
    else:
        for rep in reports:
            extra = f" ({rep.count} words)" if hasattr(rep, "count") else ""
            print(f"{rep.status:<4} {rep.label}{extra}")
            for f in rep.findings:
                where = f":{f['line']}" if f.get("line") else ""
                print(f"     {f['level']:<4} {f['rule']:<18}{where} {f['message']}")
    return exit_code


def main():
    parser = argparse.ArgumentParser(description="Lint LinkedIn copy, DMs and closer rotation")
    sub = parser.add_subparsers(dest="command")

    pc = sub.add_parser("copy", help="Lint post copy")
    pc.add_argument("files", nargs="+")
    pc.add_argument("--cta-mode", choices=["graphic", "copy"], default=None,
                    help="Override copy.cta_mode from the config")
    pc.add_argument("--keyword", default=None, help="The guide keyword; must not appear in the copy")
    pc.add_argument("--json", action="store_true")
    pc.add_argument("--strict", action="store_true", help="Treat warnings as failures")

    pd = sub.add_parser("dm", help="Lint DM text")
    pd.add_argument("files", nargs="+")
    pd.add_argument("--merge-tag", default=None, help="Override dm.merge_tag")
    pd.add_argument("--json", action="store_true")
    pd.add_argument("--strict", action="store_true")

    pr = sub.add_parser("rotation", help="Check closer rotation in a JSONL log")
    pr.add_argument("--log", required=True, help='JSONL rows {"date": "YYYY-MM-DD", "closer": "..."}')
    pr.add_argument("--weeks", type=int, default=None, help="Override copy.closer_rotation_weeks")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--strict", action="store_true")

    add_config_arg(parser, [pc, pd, pr])
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    cfg = _config(getattr(args, "config", None))

    reports = []
    if args.command == "copy":
        mode = args.cta_mode or cfg_get(cfg, "copy.cta_mode") or "graphic"
        for path in args.files:
            if not os.path.exists(path):
                print(f"Error: file not found: {path}", file=sys.stderr)
                sys.exit(1)
            for label, text in split_blocks(path):
                rep = lint_copy_text(text, cfg, keyword=args.keyword, cta_mode=mode)
                rep.label = label
                reports.append(rep)
        code = _print_reports(reports, args.json, args.strict)
        if mode == "copy":
            print(f"WARN {IMPRESSION_NOTE}", file=sys.stderr)
        sys.exit(code)

    if args.command == "dm":
        for path in args.files:
            if not os.path.exists(path):
                print(f"Error: file not found: {path}", file=sys.stderr)
                sys.exit(1)
            for label, text in split_blocks(path):
                rep = lint_dm_text(text, cfg, merge_tag=args.merge_tag)
                rep.label = label
                reports.append(rep)
        sys.exit(_print_reports(reports, args.json, args.strict))

    if args.command == "rotation":
        if not os.path.exists(args.log):
            print(f"Error: log not found: {args.log}", file=sys.stderr)
            sys.exit(1)
        weeks = args.weeks or int(cfg_get(cfg, "copy.closer_rotation_weeks") or 3)
        sys.exit(_print_reports([lint_rotation(args.log, weeks)], args.json, args.strict))


if __name__ == "__main__":
    main()
