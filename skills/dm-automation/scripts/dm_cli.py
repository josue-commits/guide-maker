#!/usr/bin/env python3
"""dm-automation CLI: render DM templates, schedule the post with its keyword
automation, attach an automation to a live post, check keywords, pull stats.

Every command prints JSON to stdout so it can be piped into jq. Exit code is
non-zero on any failure. --dry-run prints the exact payload and never opens a
socket, whichever adapter is configured.

Subcommands:
  render     fill the guide-maker DM templates with config values, lint, write .txt files
  keywords   list keywords already in use in your DM tool (collision check)
  schedule   schedule a post with graphic + keyword automation (manual: writes a bundle)
  attach     attach a keyword automation to a post that is already live
  stats      comments, DMs sent, connections per automation
  test       confirm the adapter is usable
  image-fit  re-encode a graphic to JPEG when it is over the attachment ceiling
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _config_shim import SHARED_LOADER, cfg_get, load_config, secret, sibling  # noqa: E402
from adapters import get_adapter  # noqa: E402

EM_DASHES = ("\u2014", "\u2013")  # em dash, en dash; escaped so this file passes its own grep
DEFAULT_MERGE_TAG = "{{firstName}}"
DEFAULT_MAX_LINES = 7
DEFAULT_ATTACHMENT_MAX_BYTES = 4 * 1024 * 1024
LEADSHARK_MAX_DM_CHARS = 2000

# version id -> (template file in guide-maker/templates, config gate)
VERSIONS = {
    "direct": ("dm-direct.md", None),
    "combined": ("dm-combined.md", "community.url"),
    "community_only": ("dm-community-only.md", "community.url"),
    "secondary": ("dm-secondary-channel.md", "secondary_channel.url"),
}
VERSION_ALIASES = {"community-only": "community_only", "secondary-channel": "secondary", "secondary_channel": "secondary"}

PUBLISH_TO_WEB_MSG = (
    "This is a workspace link, not a public one. Notion's copy-link button hands you the "
    "app.notion.com / notion.so form, which gates on workspace membership: every commenter "
    "gets a dead link. Publish the page to the web from the Notion app (Share, Publish) and use "
    "the <workspace>.notion.site URL. guide-maker's `md_to_notion.py public-url --check` prints it."
)

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
_TOKEN_RE = re.compile(r"\{\{[^{}]*\}\}|\{[^{}]*\}|\[[^\[\]]*\]")
_SLOT_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")
_V1_SLOT_RE = re.compile(r"\[([A-Z][A-Z0-9_]{2,})\]")
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)\n```", re.S)
_NAME_WORDS = {"name", "firstname", "fullname", "lastname", "first", "yourname", "commenter"}
_EXTRA_MERGE_TAGS = {"{{lastName}}", "{{fullName}}", "{{linkedinUsername}}"}


# ----------------------------------------------------------------- utilities


def emit(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def fail(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def read_text_arg(value: Optional[str]) -> Optional[str]:
    """Allow @/abs/path.txt to pass long text without shell quoting pain."""
    if value is None:
        return None
    if value.startswith("@"):
        path = Path(value[1:]).expanduser()
        if not path.is_file():
            fail(f"File not found: {path}")
        return path.read_text(encoding="utf-8")
    return value


def load_cfg(path: Optional[str], required: bool = True) -> dict:
    try:
        return load_config(path) or {}
    except FileNotFoundError as e:
        if required:
            fail(str(e))
        return {}


def assert_no_em_dash(text: str, label: str) -> None:
    for ch in EM_DASHES:
        if ch in (text or ""):
            fail(f"Em dash (U+{ord(ch):04X}) found in {label}. Replace it with a comma, period or colon.")


def guard_payload(obj, label: str = "payload") -> None:
    """Em-dash guard over every string inside an outgoing payload."""
    if isinstance(obj, str):
        assert_no_em_dash(obj, label)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            guard_payload(v, f"{label}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            guard_payload(v, f"{label}[{i}]")


def url_host(url: str) -> str:
    m = re.match(r"https?://([^/?#]+)", url)
    return (m.group(1) if m else "").lower()


def is_workspace_notion_url(url: str) -> bool:
    host = url_host(url)
    return host.endswith("app.notion.com") or host in ("notion.so", "www.notion.so")


def merge_tag_of(cfg: dict) -> str:
    return str(cfg_get(cfg, "dm.merge_tag", DEFAULT_MERGE_TAG) or DEFAULT_MERGE_TAG)


def default_out_dir(cfg: dict, sub: str) -> Path:
    work = cfg_get(cfg, "workflow.work_dir")
    base = Path(str(work)).expanduser() if work else Path.cwd()
    return base / sub


# --------------------------------------------------------------------- lint


def lint_dm(text: str, cfg: dict, max_chars: Optional[int] = None) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (errors, warnings) as lists of (rule_id, message)."""
    errors: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []
    merge_tag = merge_tag_of(cfg)
    allowed_tags = {merge_tag} | _EXTRA_MERGE_TAGS
    max_lines = int(cfg_get(cfg, "dm.max_lines", DEFAULT_MAX_LINES) or DEFAULT_MAX_LINES)
    hard_wrap_ok = bool(cfg_get(cfg, "dm.hard_wrap", False))
    must_be_public = bool(cfg_get(cfg, "dm.guide_link_must_be_public", True))
    public_domain = str(cfg_get(cfg, "notion.public_domain", "") or "").lower().strip()

    for ch in EM_DASHES:
        if ch in text:
            errors.append(("dm-em-dash", f"em dash U+{ord(ch):04X} present; use a comma, period or colon"))
            break

    # merge tag: only the configured spelling reaches the tool
    bad_tokens = []
    unfilled = []
    for tok in _TOKEN_RE.findall(text):
        if tok in allowed_tags:
            continue
        inner = tok.strip("{}[] ").strip()
        key = re.sub(r"[^a-z]", "", inner.lower())
        if key in _NAME_WORDS or key.replace("first", "") in {"name"}:
            bad_tokens.append(tok)
        elif (tok.startswith("{") and not tok.startswith("{{")) or _V1_SLOT_RE.fullmatch(tok):
            # any single-brace slot, including prose shapes like {one specific line}, ships literally
            unfilled.append(tok)
    if bad_tokens:
        errors.append(
            (
                "dm-merge-tag",
                f"{', '.join(sorted(set(bad_tokens)))} ships to the lead as literal text; the merge tag is exactly {merge_tag}",
            )
        )
    if unfilled:
        errors.append(
            (
                "dm-unfilled-slot",
                f"unfilled placeholder(s) {', '.join(sorted(set(unfilled)))}; pass --set slot=value or write the line",
            )
        )
    if merge_tag not in text:
        warnings.append(("dm-no-merge-tag", f"{merge_tag} does not appear; the DM will not greet the lead by name"))

    # links
    for url in _URL_RE.findall(text):
        url = url.rstrip(".,;:")
        if must_be_public and is_workspace_notion_url(url):
            errors.append(("dm-private-link", f"{url} is a workspace link. {PUBLISH_TO_WEB_MSG}"))
        elif public_domain and url_host(url).endswith("notion.site") and url_host(url) != public_domain:
            warnings.append(("dm-other-notion-site", f"{url} is not on notion.public_domain ({public_domain})"))

    # hard wrap: one paragraph = one line; a URL may sit alone on its own line
    if not hard_wrap_ok:
        for para in re.split(r"\n\s*\n", text.strip()):
            lines = [ln for ln in para.split("\n") if ln.strip()]
            if len(lines) < 2:
                continue
            for a, b in zip(lines, lines[1:]):
                if _URL_RE.fullmatch(a.strip()) or _URL_RE.fullmatch(b.strip()):
                    continue
                errors.append(
                    (
                        "dm-hard-wrap",
                        f"hard-wrapped paragraph near '{a.strip()[:40]}'. Keep each paragraph on one line; "
                        "the DM pane wraps it again and it reads like a broken paste. Separate paragraphs with a blank line.",
                    )
                )
                break

    non_blank = [ln for ln in text.split("\n") if ln.strip()]
    if len(non_blank) > max_lines:
        errors.append(("dm-max-lines", f"{len(non_blank)} non-blank lines, dm.max_lines is {max_lines}; people do not read long DMs from strangers"))

    if max_chars and len(text) > max_chars:
        errors.append(("dm-max-chars", f"{len(text)} characters, the tool accepts {max_chars}"))

    return errors, warnings


def print_findings(label: str, errors, warnings) -> None:
    for rule, msg in errors:
        print(f"FAIL {label} [{rule}] {msg}", file=sys.stderr)
    for rule, msg in warnings:
        print(f"WARN {label} [{rule}] {msg}", file=sys.stderr)


# ----------------------------------------------------------------- templates


def template_body(raw: str) -> str:
    """Plain-text DM body from a template file.

    First fenced code block wins when present (prose around it is guidance).
    Otherwise: drop YAML frontmatter, heading lines and HTML comments.
    """
    text = raw.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            text = text[end + 4:]
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1)
    else:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        text = "\n".join(ln for ln in text.split("\n") if not re.match(r"^\s{0,3}#{1,6}\s", ln))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n").rstrip() + "\n"


def fill_template(body: str, values: dict, merge_tag: str) -> str:
    # v1 [GUIDE_URL] style becomes {guide_url} so one substitution pass covers both
    body = _V1_SLOT_RE.sub(lambda m: "{" + m.group(1).lower() + "}", body)
    body = body.replace(DEFAULT_MERGE_TAG, merge_tag)

    def sub(m):
        key = m.group(1)
        if key in values and values[key] not in (None, ""):
            return str(values[key])
        return m.group(0)

    return _SLOT_RE.sub(sub, body)


def resolve_versions(cfg: dict, requested: Optional[list[str]]) -> list[str]:
    """Which DM versions to render. Explicit requests fail loudly when gated off."""
    if requested and requested != ["all"]:
        chosen = []
        for v in requested:
            v = VERSION_ALIASES.get(v, v)
            if v == "all":
                chosen.extend(resolve_versions(cfg, ["all"]))
                continue
            if v not in VERSIONS:
                fail(f"Unknown DM version '{v}'. Choose from: {', '.join(VERSIONS)}, all")
            gate = VERSIONS[v][1]
            if gate and not cfg_get(cfg, gate):
                fail(f"Version '{v}' needs {gate} in the config, and it is empty.")
            if v not in chosen:
                chosen.append(v)
        return chosen
    configured = cfg_get(cfg, "dm.versions", "auto")
    if isinstance(configured, list) and (not requested):
        return resolve_versions(cfg, [str(x) for x in configured])
    out = []
    for v, (_, gate) in VERSIONS.items():
        if gate and not cfg_get(cfg, gate):
            continue
        out.append(v)
    return out


def templates_dir(cfg: dict, override: Optional[str]) -> Path:
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_dir():
            fail(f"--templates-dir {path} is not a directory")
        return path
    try:
        return sibling("guide-maker") / "templates"
    except FileNotFoundError as e:
        fail(f"{e}\nOr pass --templates-dir /abs/path/to/templates.")
    return Path()  # unreachable, keeps type checkers calm


def template_values(cfg: dict, args) -> dict:
    author = str(cfg_get(cfg, "author.name", "") or "")
    values = {
        "guide_url": args.guide_url,
        "guide_title": getattr(args, "guide_title", None) or "",
        "author_name": author,
        "signoff": str(cfg_get(cfg, "author.dm_signoff", "") or author),
        "community_name": str(cfg_get(cfg, "community.name", "") or ""),
        "community_url": str(cfg_get(cfg, "community.url", "") or ""),
        "community_platform": str(cfg_get(cfg, "community.platform", "") or ""),
        "secondary_channel_url": str(cfg_get(cfg, "secondary_channel.url", "") or ""),
        "secondary_channel_handle": str(cfg_get(cfg, "secondary_channel.handle", "") or ""),
        "secondary_channel_type": str(cfg_get(cfg, "secondary_channel.type", "") or ""),
    }
    for item in getattr(args, "set", None) or []:
        if "=" not in item:
            fail(f"--set expects key=value, got '{item}'")
        k, v = item.split("=", 1)
        values[k.strip()] = read_text_arg(v) if v.startswith("@") else v
    return values


def check_guide_url(cfg: dict, url: str, verify: bool) -> None:
    if not re.match(r"https?://", url or ""):
        fail(f"--guide-url must be an absolute http(s) URL, got '{url}'")
    if cfg_get(cfg, "dm.guide_link_must_be_public", True) and is_workspace_notion_url(url):
        fail(f"{url}\n{PUBLISH_TO_WEB_MSG}", code=2)
    public_domain = str(cfg_get(cfg, "notion.public_domain", "") or "").lower()
    host = url_host(url)
    if public_domain and host.endswith("notion.site") and host != public_domain:
        print(f"warning: {host} is not notion.public_domain ({public_domain})", file=sys.stderr)
    if verify:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "dm-automation/2"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        except urllib.error.URLError as e:
            fail(f"--check-url: {url} did not resolve ({e.reason}). Publish the page to the web first.")
        if status != 200:
            fail(f"--check-url: {url} answered {status}. Publish the page to the web first.")
        print(f"ok: {url} answered 200", file=sys.stderr)


# ------------------------------------------------------------------ commands


def cmd_render(args) -> None:
    cfg = load_cfg(args.config)
    check_guide_url(cfg, args.guide_url, args.check_url)
    versions = resolve_versions(cfg, args.version)
    tdir = templates_dir(cfg, args.templates_dir)
    values = template_values(cfg, args)
    merge_tag = merge_tag_of(cfg)
    provider = args.provider or str(cfg_get(cfg, "dm_tool.provider", "manual"))
    max_chars = LEADSHARK_MAX_DM_CHARS if provider == "leadshark" else None
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else default_out_dir(cfg, "dm-render")
    out_dir.mkdir(parents=True, exist_ok=True)

    written, failed = [], []
    for v in versions:
        fname = VERSIONS[v][0]
        src = tdir / fname
        if not src.is_file():
            fail(
                f"Template {fname} not found in {tdir}. Install guide-maker v2 next to this skill "
                "(it ships dm-direct.md, dm-combined.md, dm-community-only.md, dm-secondary-channel.md) "
                "or pass --templates-dir."
            )
        body = fill_template(template_body(src.read_text(encoding="utf-8")), values, merge_tag)
        errors, warnings = lint_dm(body, cfg, max_chars=max_chars)
        print_findings(fname, errors, warnings)
        if errors:
            failed.append({"version": v, "template": str(src), "errors": [r for r, _ in errors]})
            continue
        dest = out_dir / (Path(fname).stem + ".txt")
        dest.write_text(body, encoding="utf-8")
        written.append({"version": v, "file": str(dest), "chars": len(body), "lines": len([l for l in body.split("\n") if l.strip()])})

    emit({"ok": not failed, "out_dir": str(out_dir), "merge_tag": merge_tag, "written": written, "failed": failed})
    if failed:
        sys.exit(1)


def cmd_keywords(args) -> None:
    cfg = load_cfg(args.config)
    tool = get_adapter(cfg, args.provider, dry_run=args.dry_run)
    keywords = tool.list_keywords()
    result = {"adapter": tool.name, "keywords_in_use": keywords}
    detail = getattr(tool, "keyword_detail", None)
    if detail:
        result["detail"] = detail
    if args.check:
        wanted = args.check.strip().upper()
        result["check"] = wanted
        result["taken"] = wanted in {k.upper() for k in keywords}
        if not re.fullmatch(r"[A-Z][A-Z0-9]{2,11}", wanted):
            result["shape_warning"] = "keywords are one word, 3 to 12 upper-case characters, derived from the guide name"
    emit(result)
    if args.check and result.get("taken"):
        sys.exit(1)


def _collect_dms(args, cfg: dict, provider: str) -> tuple[str, list[str]]:
    dm_text = read_text_arg(args.dm) if args.dm else ""
    variants = [read_text_arg(v) for v in (args.dm_variant or [])]
    max_chars = LEADSHARK_MAX_DM_CHARS if provider == "leadshark" else None
    bad = False
    for label, text in [("--dm", dm_text)] + [(f"--dm-variant {i+1}", v) for i, v in enumerate(variants)]:
        if not text:
            continue
        errors, warnings = lint_dm(text, cfg, max_chars=max_chars)
        print_findings(label, errors, warnings)
        bad = bad or bool(errors)
    if bad and not args.skip_lint:
        fail("DM lint failed. Fix the findings above or pass --skip-lint if you really mean it.")
    return dm_text or "", [v for v in variants if v]


def _keyword_in_copy(cfg: dict, content: str, keywords: list[str]) -> None:
    if str(cfg_get(cfg, "copy.cta_mode", "graphic")).lower() == "copy":
        return
    for kw in keywords:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(kw) + r"(?![A-Za-z0-9])", content, flags=re.I):
            fail(
                f'The keyword "{kw}" appears in the post copy. It lives in the graphic only; LinkedIn '
                "suppresses posts whose copy carries an engagement instruction. Remove it from the copy, "
                "or set copy.cta_mode: copy if you accept the reach hit."
            )


def _parse_time(value: str) -> str:
    try:
        dt = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(f"--time must be ISO 8601, e.g. 2026-09-14T13:00:00Z, got '{value}'")
    if dt.tzinfo is None:
        fail("--time needs a timezone suffix (Z or +hh:mm) so nothing fires at the wrong hour.")
    now = _dt.datetime.now(_dt.timezone.utc)
    if dt < now + _dt.timedelta(minutes=15):
        print("warning: --time is less than 15 minutes ahead (or in the past); most tools reject it.", file=sys.stderr)
    if dt > now + _dt.timedelta(days=90):
        print("warning: --time is more than 90 days ahead; most tools reject it.", file=sys.stderr)
    return value


def cmd_schedule(args) -> None:
    cfg = load_cfg(args.config)
    provider = args.provider or str(cfg_get(cfg, "dm_tool.provider", "manual"))
    content = read_text_arg(args.content) or ""
    if not content.strip():
        fail("--content is empty")
    time_iso = _parse_time(args.time)
    keywords = [k.strip().upper() for k in (args.keyword or []) if k.strip()]
    dm_text, variants = _collect_dms(args, cfg, provider)
    if keywords and not dm_text:
        fail("A keyword with no --dm means commenters get nothing. Pass --dm @/abs/path/dm.txt.")
    if dm_text and not keywords:
        fail("A DM with no --keyword fires on every comment, including 'nice post'. Pass --keyword.")
    _keyword_in_copy(cfg, content, keywords)

    if args.image:
        if not Path(args.image).expanduser().is_file():
            fail(f"--image not found: {args.image}")
    else:
        print("warning: no --image. The keyword lives in the graphic; a lead magnet post needs one.", file=sys.stderr)

    replies = args.comment_reply if args.comment_reply else list(cfg_get(cfg, "dm_tool.leadshark.comment_replies") or [])
    nfd_cfg = cfg_get(cfg, "dm_tool.leadshark.non_first_degree_reply")
    nfd = args.non_first_degree_reply or ([nfd_cfg] if isinstance(nfd_cfg, str) and nfd_cfg else list(nfd_cfg or []))
    auto_connect = True if args.auto_connect else bool(cfg_get(cfg, "dm_tool.leadshark.auto_connect", True))
    if args.no_auto_connect:
        auto_connect = False

    automation = {
        "name": args.automation_name or (f"{keywords[0]} - {time_iso[:10]}" if keywords else ""),
        "keywords": keywords,
        "dm_template": dm_text,
        "dm_templates": ([dm_text] + variants) if dm_text else [],
        "comment_reply_template": [read_text_arg(r) for r in replies],
        "non_first_degree_reply_template": [read_text_arg(r) for r in nfd],
        "auto_connect": auto_connect,
        "auto_like": bool(args.auto_like),
    }
    guard_payload({"content": content, "automation": automation}, "schedule")

    out_dir = args.out_dir or str(default_out_dir(cfg, "dm-schedule"))
    tool = get_adapter(cfg, provider, dry_run=args.dry_run, out_dir=out_dir)
    result = tool.schedule_post(content, time_iso, args.image, automation)
    emit(result)


def cmd_attach(args) -> None:
    cfg = load_cfg(args.config)
    provider = args.provider or str(cfg_get(cfg, "dm_tool.provider", "manual"))
    keyword = args.keyword.strip().upper()
    dm_text, variants = _collect_dms(args, cfg, provider)
    if not dm_text:
        fail("--dm is required")
    status = args.status or str(cfg_get(cfg, "dm_tool.leadshark.create_as", "Paused"))
    guard_payload({"dm": dm_text, "variants": variants, "keyword": keyword}, "attach")
    out_dir = args.out_dir or str(default_out_dir(cfg, "dm-schedule"))
    tool = get_adapter(cfg, provider, dry_run=args.dry_run, out_dir=out_dir)
    emit(tool.attach_automation(args.post_url, keyword, dm_text, variants, status))


def cmd_stats(args) -> None:
    cfg = load_cfg(args.config)
    tool = get_adapter(cfg, args.provider, dry_run=args.dry_run)
    emit(tool.stats(args.range))


def cmd_test(args) -> None:
    cfg = load_cfg(args.config, required=False)
    provider = args.provider or str(cfg_get(cfg, "dm_tool.provider", "manual"))
    tool = get_adapter(cfg, provider, dry_run=args.dry_run)
    result = tool.test()
    result["config_loader"] = "guide-maker/_config.py" if SHARED_LOADER else "standalone fallback"
    if provider == "leadshark":
        result["api_key_present"] = bool(secret(cfg, "leadshark"))
    emit(result)


def cmd_image_fit(args) -> None:
    cfg = load_cfg(args.config, required=False)
    max_bytes = int(args.max_bytes or cfg_get(cfg, "dm_tool.leadshark.attachment_max_bytes", DEFAULT_ATTACHMENT_MAX_BYTES))
    src = Path(args.path).expanduser()
    if not src.is_file():
        fail(f"File not found: {src}")
    size = src.stat().st_size
    if size <= max_bytes and not args.force:
        emit({"ok": True, "path": str(src), "bytes": size, "max_bytes": max_bytes, "action": "none, already fits"})
        return
    try:
        from PIL import Image
    except ImportError:
        fail("Pillow is required: python3 -m pip install pillow")
    out = Path(args.output).expanduser() if args.output else src.with_suffix(".jpg")
    if out.resolve() == src.resolve():
        out = src.with_name(src.stem + "-fit.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    quality = 95
    while True:
        # quality 95 with subsampling=0 keeps flat art and type crisp; LinkedIn re-encodes anyway
        im.save(out, "JPEG", quality=quality, optimize=True, subsampling=0)
        new_size = out.stat().st_size
        if new_size <= max_bytes or quality <= 75:
            break
        quality -= 5
    result = {
        "ok": new_size <= max_bytes,
        "input": str(src),
        "input_bytes": size,
        "output": str(out),
        "output_bytes": new_size,
        "quality": quality,
        "max_bytes": max_bytes,
    }
    emit(result)
    if not result["ok"]:
        fail(f"Still {new_size} bytes at quality {quality}. Shrink the pixel dimensions and retry.")


# -------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dm_cli.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="Absolute path to config.yaml (default: GUIDE_MAKER_CONFIG, then the guide-maker skill dir)")
    common.add_argument("--provider", choices=["manual", "leadshark"], help="Override dm_tool.provider for this call")
    common.add_argument("--dry-run", action="store_true", help="Print the exact payload; never open a socket")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", parents=[common], help="Fill the DM templates with config values, lint, write .txt files")
    r.add_argument("--guide-url", required=True, help="Public guide URL that goes in the DM (never app.notion.com)")
    r.add_argument("--guide-title", help="Fills {guide_title} when the template uses it")
    r.add_argument("--version", action="append", help="direct | combined | community_only | secondary | all. Repeatable. Default: dm.versions")
    r.add_argument("--out-dir", help="Where the .txt files go (default: workflow.work_dir/dm-render)")
    r.add_argument("--templates-dir", help="Override the template folder (default: guide-maker/templates next to this skill)")
    r.add_argument("--set", action="append", metavar="KEY=VALUE", help="Fill an extra {slot}; VALUE may be @/abs/path.txt. Repeatable")
    r.add_argument("--check-url", action="store_true", help="GET the guide URL and require a 200 (opens a socket)")
    r.set_defaults(func=cmd_render)

    k = sub.add_parser("keywords", parents=[common], help="Keywords already in use in your DM tool")
    k.add_argument("--check", metavar="KEYWORD", help="Exit 1 if this keyword is taken")
    k.set_defaults(func=cmd_keywords)

    s = sub.add_parser("schedule", parents=[common], help="Schedule a post with its graphic and keyword automation")
    s.add_argument("--content", required=True, help="Post copy, or @/abs/path/post.txt")
    s.add_argument("--image", help="Absolute path to the post graphic (carries the keyword bar)")
    s.add_argument("--time", required=True, help="ISO 8601 with timezone, e.g. 2026-09-14T13:00:00Z")
    s.add_argument("--keyword", action="append", help="Trigger keyword. Repeatable; one per guide is the rule")
    s.add_argument("--dm", help="Primary DM text, or @/abs/path/dm.txt")
    s.add_argument("--dm-variant", action="append", help="Extra DM rotated with the primary, or @file. Repeatable")
    s.add_argument("--comment-reply", action="append", help="Public reply under the comment, rotated. Repeatable. Default: dm_tool.leadshark.comment_replies")
    s.add_argument("--non-first-degree-reply", action="append", help="Reply for people who cannot be DMed yet. Default: dm_tool.leadshark.non_first_degree_reply")
    s.add_argument("--automation-name", help="Label for the automation. Default: KEYWORD - date")
    s.add_argument("--auto-connect", action="store_true", help="Force auto-connect on (default: dm_tool.leadshark.auto_connect)")
    s.add_argument("--no-auto-connect", action="store_true", help="Force auto-connect off")
    s.add_argument("--auto-like", action="store_true", help="Like the comment (tool-dependent)")
    s.add_argument("--out-dir", help="Manual adapter: where dm-bundle/ is written (default: workflow.work_dir/dm-schedule)")
    s.add_argument("--skip-lint", action="store_true", help="Send even when the DM lint fails")
    s.set_defaults(func=cmd_schedule)

    a = sub.add_parser("attach", parents=[common], help="Attach a keyword automation to a post that is already live")
    a.add_argument("--post-url", required=True, help="The live post URL (contains urn:li:activity:<digits>)")
    a.add_argument("--keyword", required=True)
    a.add_argument("--dm", required=True, help="DM text, or @/abs/path/dm.txt")
    a.add_argument("--dm-variant", action="append", help="Extra DM rotated with the primary. Repeatable")
    a.add_argument("--status", choices=["Running", "Paused"], help="Default: dm_tool.leadshark.create_as (Paused)")
    a.add_argument("--out-dir", help="Manual adapter: where dm-bundle/ is written")
    a.add_argument("--skip-lint", action="store_true")
    a.set_defaults(func=cmd_attach)

    st = sub.add_parser("stats", parents=[common], help="Comments, DMs sent, connections per automation")
    st.add_argument("--range", default="weekly", choices=["daily", "weekly", "monthly", "all"])
    st.set_defaults(func=cmd_stats)

    t = sub.add_parser("test", parents=[common], help="Confirm the adapter is usable")
    t.set_defaults(func=cmd_test)

    f = sub.add_parser("image-fit", parents=[common], help="Re-encode a graphic to JPEG when it is over the attachment ceiling")
    f.add_argument("path", help="Absolute path to the PNG or JPEG")
    f.add_argument("--max-bytes", type=int, help="Ceiling in bytes (default: dm_tool.leadshark.attachment_max_bytes, 4194304)")
    f.add_argument("--output", help="Output path (default: same name with .jpg)")
    f.add_argument("--force", action="store_true", help="Re-encode even when the file already fits")
    f.set_defaults(func=cmd_image_fit)
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # adapters raise their own ApiError; keep the JSON contract
        status = getattr(e, "status", None)
        body = getattr(e, "body", None)
        payload = {"error": True, "type": type(e).__name__, "message": str(e)}
        if status is not None:
            payload["status"] = status
        if body is not None:
            payload["body"] = body
        print(json.dumps(payload, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
