#!/usr/bin/env python3
"""
graphics_generate.py: post graphics for a lead-magnet post.

Subcommands

  card      Pillow only, zero cost, no API. Title block, optional stat row,
            CTA bar. 1:1, 2048px. The guaranteed path on every machine.
  scene     Pass A of the two-pass flow: N text-free scene variants from an
            image provider. Pick a winner before paying for the text pass.
  text      Pass B: add the title/labels onto the winning scene. With
            graphics.cta_bar.renderer = pillow (default) the prompt is
            rewritten to leave the bottom band empty and the bar is
            composited locally; with renderer = model the canonical CTA
            string is injected into the prompt for the model to draw.
  single    One-shot: scene and text in one provider call. For formats built
            around real photos or real screenshots passed as references.
  tweak     Delta-only edit of an existing local PNG through the provider.
  finalize  CTA bar, optional logo, C2PA strip. Runs automatically at the
            end of text / single / tweak unless --no-finalize.
  log       Append one line to format-usage-log.jsonl (rotation tracking).
  rotation  Print the formats used in the last N days.

--dry-run prints what would be sent (provider, prompt, references, cost)
and exits. --estimate prints the cost only. Neither opens a network
connection.

Every path argument should be absolute. Examples:

  python3 /abs/skills/graphics-maker/scripts/graphics_generate.py card \
      --title "Automate your CRM follow-ups" --subtitle "5 workflows" \
      --stat "3|tools" --stat "20 min|setup" --keyword FLOWS \
      --output /abs/work/flows-post.png

  python3 /abs/skills/graphics-maker/scripts/graphics_generate.py scene \
      --prompt "..." --output-prefix /abs/work/flows --variants 2 --estimate

  python3 /abs/skills/graphics-maker/scripts/graphics_generate.py text \
      --scene /abs/work/flows-v1.png --prompt "..." --keyword FLOWS \
      --output /abs/work/flows-post.png
"""
import argparse
import datetime as _dt
import json
import os
import shutil
import sys
import urllib.request

from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from _cfg import load_config, cfg_get, skill_dir  # noqa: E402
from cta_bar import (add_cta_bar, render_string, validate_keyword, KeywordError,  # noqa: E402
                     find_font_path, load_font, hex_to_rgb, STRINGS, DEFAULT_HEIGHT_PCT,
                     DEFAULT_COLORS)
from strip_credentials import strip as strip_credentials  # noqa: E402
from logo_corner import place_logo  # noqa: E402
from providers.base import get_provider, ProviderError, ASPECT_RATIOS, RESOLUTIONS  # noqa: E402

DEFAULT_CARD_SIZE = 2048
DEFAULT_ROTATION_DAYS = 7
USAGE_LOG_NAME = "format-usage-log.jsonl"


class Abort(Exception):
    """User-facing failure. Message printed to stderr, exit 1."""


# ---------------------------------------------------------------- helpers

def _renderer(cfg, override=None):
    r = (override or cfg_get(cfg, "graphics.cta_bar.renderer", "pillow") or "pillow").lower()
    if r not in ("pillow", "model"):
        raise Abort("graphics.cta_bar.renderer must be pillow or model, got %s" % r)
    return r


def _band_pct(cfg):
    return float(cfg_get(cfg, "graphics.cta_bar.height_pct", DEFAULT_HEIGHT_PCT))


def _usage_log_path(cfg):
    p = cfg_get(cfg, "graphics.usage_log", "")
    return os.path.expanduser(str(p)) if p else str(skill_dir() / USAGE_LOG_NAME)


def band_instruction(cfg):
    """Prompt suffix that reserves the bottom band for the Pillow bar."""
    pct = int(round(_band_pct(cfg) * 100))
    return ("\n\nLeave the bottom %d percent of the image completely empty: a flat, "
            "uniform band with no text, no shapes, no lines, no border. Nothing may "
            "touch that band. A caption bar is added there in a later step." % pct)


def inject_cta_string(prompt, keyword, string):
    """For renderer = model: put the canonical string into the prompt."""
    text = render_string(keyword, string)
    out = prompt.replace("[KEYWORD]", keyword)
    if text not in out:
        out += ("\n\nAcross the full width of the bottom edge of the image, render a "
                "single high-contrast band as the last element with nothing below it, "
                "and write in it exactly, character for character: %s" % text)
    return out


def download(url, output_path):
    req = urllib.request.Request(url, headers={"User-Agent": "graphics-maker/2"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(data)


def fetch_result(result, output_path):
    """Provider results are a URL or a local path. Put the file at output_path."""
    if not result:
        raise Abort("Provider returned nothing")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    if str(result).startswith("http"):
        download(result, output_path)
    elif os.path.abspath(result) != os.path.abspath(output_path):
        shutil.move(result, output_path)
    w, h = Image.open(output_path).size
    print("Saved: %s (%dx%d)" % (output_path, w, h))
    return output_path


def require_live(provider):
    """Abort once, before any loop, when no image API is configured."""
    if provider.name == "none":
        raise Abort(provider._MSG)


def resolve_refs(refs, provider, cfg):
    """Local reference paths become public URLs only when the provider needs them."""
    out = []
    for r in refs or []:
        if str(r).startswith("http"):
            out.append(r)
            continue
        p = os.path.expanduser(r)
        if not os.path.exists(p):
            raise Abort("Reference image not found: %s" % r)
        if provider.needs_public_ref_urls():
            from _upload import upload_public
            endpoint = cfg_get(cfg, "graphics.upload_endpoint", "") or None
            print("Uploading reference %s ..." % os.path.basename(p), flush=True)
            out.append(upload_public(p, endpoint=endpoint))
        else:
            out.append(p)
    return out


def _print_plan(label, provider, prompt, refs, cost, extra=None):
    print("[%s] provider=%s estimated_cost=$%.3f" % (label, provider.describe(), cost))
    if extra:
        for k, v in extra.items():
            print("  %s: %s" % (k, v))
    if refs:
        print("  references (%d):" % len(refs))
        for r in refs:
            print("    %s" % r)
    print("  prompt:")
    for line in prompt.splitlines() or [""]:
        print("    " + line)


# ---------------------------------------------------------------- finalize

def finalize(image_path, keyword, cfg, *, output=None, string=None, strip=None,
             logo=None, renderer=None):
    """CTA bar (pillow renderer), optional logo, C2PA strip. Returns output path."""
    output = output or image_path
    if output != image_path:
        os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
        shutil.copyfile(image_path, output)
    renderer = _renderer(cfg, renderer)
    string = string or cfg_get(cfg, "graphics.cta_bar.string", "primary")

    if keyword:
        keyword = validate_keyword(keyword)
        if renderer == "pillow":
            add_cta_bar(output, keyword, output, string=string, cfg=cfg)
        else:
            print("CTA bar: rendered by the model. Expected string, read the image "
                  "character by character against it:")
            print(render_string(keyword, string))
    else:
        print("CTA bar: no keyword given, band not composited")

    if logo is None:
        logo = bool(cfg_get(cfg, "brand.logo.on_post_graphic", False))
    if logo:
        logo_path = os.path.expanduser(str(cfg_get(cfg, "brand.logo.path", "") or ""))
        if not logo_path or not os.path.exists(logo_path):
            print("Logo: SKIP (brand.logo.path not set or missing)")
        else:
            on_dark = cfg_get(cfg, "graphics.logo_on_dark", "") or None
            print("Logo: " + place_logo(
                output, logo_path, logo_on_dark=on_dark,
                corner=cfg_get(cfg, "graphics.logo_corner", "top-left"),
                width_pct=float(cfg_get(cfg, "graphics.logo_width_pct", 0.12))))

    if strip is None:
        strip = bool(cfg_get(cfg, "graphics.strip_c2pa", True))
    if strip:
        strip_credentials(output, output)  # exits 2 if a marker survives
    else:
        print("Credential strip: SKIPPED")
    return output


# ---------------------------------------------------------------- card (Pillow)

def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _blend(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def parse_stat(raw):
    if "|" not in raw:
        raise Abort('--stat must look like "NUMBER|label", got: %s' % raw)
    num, label = raw.split("|", 1)
    num, label = num.strip(), label.strip()
    if not num or not label:
        raise Abort('--stat needs both sides of the pipe: "3|tools"')
    return num, label


def render_card(title, subtitle, stats, keyword, output, cfg, bg_mode="dark",
                size=DEFAULT_CARD_SIZE):
    """Draw the art (title, subtitle, stats) leaving the bottom band empty,
    then finalize (CTA bar + strip)."""
    if bg_mode not in ("dark", "light"):
        raise Abort("--bg must be dark or light")
    if len(stats) > 4:
        raise Abort("At most 4 --stat entries fit on a card")
    if not title.strip():
        raise Abort("--title is empty")
    if title.strip().upper() == keyword.strip().upper():
        raise Abort("The title must not be the keyword itself; the CTA bar carries the keyword")

    colors = {k: cfg_get(cfg, "brand.colors.%s" % k, v) or v for k, v in DEFAULT_COLORS.items()}
    bg = hex_to_rgb(colors["dark"] if bg_mode == "dark" else colors["light"])
    fg = hex_to_rgb(colors["light"] if bg_mode == "dark" else colors["dark"])
    muted = _blend(fg, bg, 0.35)
    rule = _blend(fg, bg, 0.75)

    S = int(size)
    band_h = int(round(S * _band_pct(cfg)))
    margin = int(S * 0.08)
    content_w = S - 2 * margin
    art_bottom = S - band_h - margin

    img = Image.new("RGB", (S, S), bg)
    draw = ImageDraw.Draw(img)
    bold_path = find_font_path(cfg, None, "bold")
    reg_path = find_font_path(cfg, None, "regular") or bold_path

    # Stats block height (drawn at the bottom of the art area)
    stats_h = 0
    num_font = label_font = None
    if stats:
        num_font = load_font(bold_path, int(S * 0.075))
        label_font = load_font(reg_path, int(S * 0.03))
        stats_h = int(S * 0.075 * 1.15) + int(S * 0.03 * 1.4) + int(S * 0.02)

    # Title: shrink until it fits in 3 lines and above the stats block
    sub_font = load_font(reg_path, int(S * 0.038))
    sub_lines = _wrap(draw, subtitle, sub_font, content_w) if subtitle else []
    sub_h = int(len(sub_lines) * S * 0.038 * 1.3)
    title_size = int(S * 0.095)
    while True:
        title_font = load_font(bold_path, title_size)
        title_lines = _wrap(draw, title, title_font, content_w)
        line_h = int(title_size * 1.08)
        title_h = line_h * len(title_lines)
        text_bottom = margin + title_h + (int(S * 0.03) + sub_h if sub_lines else 0)
        limit = art_bottom - stats_h - int(S * 0.04)
        if (len(title_lines) <= 3 and text_bottom <= limit) or title_size <= int(S * 0.04):
            break
        title_size -= max(2, title_size // 25)

    y = margin
    for line in title_lines:
        draw.text((margin, y), line, font=title_font, fill=fg)
        y += line_h
    if sub_lines:
        y += int(S * 0.03)
        for line in sub_lines:
            draw.text((margin, y), line, font=sub_font, fill=muted)
            y += int(S * 0.038 * 1.3)

    if stats:
        n = len(stats)
        col_w = content_w / n
        top = art_bottom - stats_h
        draw.line([(margin, top), (S - margin, top)], fill=rule, width=max(2, S // 1024))
        for i, (num, label) in enumerate(stats):
            x = margin + int(i * col_w)
            ny = top + int(S * 0.02)
            draw.text((x, ny), num, font=num_font, fill=fg)
            draw.text((x, ny + int(S * 0.075 * 1.15)), label, font=label_font, fill=muted)
            if i > 0:
                draw.line([(x - int(S * 0.02), top + int(S * 0.02)),
                           (x - int(S * 0.02), art_bottom - int(S * 0.01))],
                          fill=rule, width=max(2, S // 1024))

    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    img.save(output, "PNG", optimize=True)
    print("Card art: %s (%dx%d, %s, bottom %dpx reserved)" % (output, S, S, bg_mode, band_h))
    return output


# ---------------------------------------------------------------- subcommands

def cmd_card(args):
    cfg = load_config(args.config)
    keyword = validate_keyword(args.keyword)
    stats = [parse_stat(s) for s in (args.stat or [])]
    render_card(args.title, args.subtitle or "", stats, keyword, args.output, cfg,
                bg_mode=args.bg, size=args.size)
    finalize(args.output, keyword, cfg, string=args.string, strip=not args.no_strip,
             logo=True if args.logo else None, renderer="pillow")
    print("\nDone: %s" % args.output)


def cmd_scene(args):
    cfg = load_config(args.config)
    provider = get_provider(cfg, args.provider)
    aspect = args.aspect_ratio or cfg_get(cfg, "graphics.aspect_ratio", "1:1")
    res = args.resolution or cfg_get(cfg, "graphics.resolution", "2K")
    prompt = args.prompt
    if _renderer(cfg) == "pillow":
        prompt += band_instruction(cfg)
    extra = cfg_get(cfg, "graphics.negative_prompt_extra", "")
    if extra:
        prompt += "\n\n" + str(extra)
    cost = provider.estimate_cost("generate") * args.variants
    if args.estimate:
        print("scene: %d variant(s) x $%.3f = $%.3f (provider %s)"
              % (args.variants, provider.estimate_cost("generate"), cost, provider.describe()))
        return
    if args.dry_run:
        _print_plan("scene dry-run", provider, prompt, args.ref_image, cost,
                    {"variants": args.variants, "aspect": aspect, "resolution": res,
                     "thinking_high": args.thinking_high})
        return
    require_live(provider)
    refs = resolve_refs(args.ref_image, provider, cfg)
    outputs = []
    for i in range(1, args.variants + 1):
        print("\n--- Variant %d/%d ---" % (i, args.variants))
        try:
            result = provider.generate(prompt, ref_images=refs, aspect_ratio=aspect,
                                       resolution=res, thinking_high=args.thinking_high)
        except ProviderError as e:
            print("Variant %d failed: %s" % (i, e), file=sys.stderr)
            continue
        outputs.append(fetch_result(result, "%s-v%d.png" % (args.output_prefix, i)))
    if not outputs:
        raise Abort("All scene variants failed")
    print("\n%d scene variant(s), no text yet:" % len(outputs))
    for p in outputs:
        print("  " + p)
    print("Next: pick a winner, then run `text` on it with --keyword.")


def _finalize_after(args, cfg, keyword):
    if args.no_finalize:
        print("finalize: SKIPPED (--no-finalize). Run `finalize --keyword` before shipping.")
        return
    finalize(args.output, keyword, cfg, string=args.string, strip=not args.no_strip,
             logo=True if args.logo else None)


def _require_keyword(args):
    if args.no_finalize:
        return validate_keyword(args.keyword) if args.keyword else None
    if not args.keyword:
        raise Abort("--keyword is required (or pass --no-finalize and run `finalize` yourself)")
    return validate_keyword(args.keyword)


def cmd_text(args):
    cfg = load_config(args.config)
    keyword = _require_keyword(args)
    provider = get_provider(cfg, args.provider)
    aspect = args.aspect_ratio or cfg_get(cfg, "graphics.aspect_ratio", "1:1")
    res = args.resolution or cfg_get(cfg, "graphics.resolution", "2K")
    renderer = _renderer(cfg)
    string = args.string or cfg_get(cfg, "graphics.cta_bar.string", "primary")
    prompt, fallback = args.prompt, args.fallback_prompt
    if renderer == "pillow":
        prompt += band_instruction(cfg)
        if fallback:
            fallback += band_instruction(cfg)
    elif keyword:
        prompt = inject_cta_string(prompt, keyword, string)
        if fallback:
            fallback = inject_cta_string(fallback, keyword, string)
    cost = provider.estimate_cost("edit")
    if args.estimate:
        print("text: 1 edit = $%.3f (provider %s)%s"
              % (cost, provider.describe(),
                 "; fallback would add $%.3f" % provider.estimate_cost("generate") if fallback else ""))
        return
    if args.dry_run:
        _print_plan("text dry-run", provider, prompt, [args.scene], cost,
                    {"renderer": renderer, "aspect": aspect, "resolution": res})
        if fallback:
            print("  fallback prompt:")
            for line in fallback.splitlines():
                print("    " + line)
        return
    require_live(provider)
    if not os.path.exists(args.scene):
        raise Abort("Scene not found: %s" % args.scene)
    result = None
    try:
        result = provider.edit(args.scene, prompt, aspect_ratio=aspect, resolution=res)
    except ProviderError as e:
        if not fallback:
            raise Abort("Text pass failed: %s" % e)
        print("Text pass failed (%s). Falling back to a single-shot generate." % e, file=sys.stderr)
        result = provider.generate(fallback, aspect_ratio=aspect, resolution=res)
    fetch_result(result, args.output)
    _finalize_after(args, cfg, keyword)
    print("\nDone: %s" % args.output)


def cmd_single(args):
    cfg = load_config(args.config)
    keyword = _require_keyword(args)
    provider = get_provider(cfg, args.provider)
    aspect = args.aspect_ratio or cfg_get(cfg, "graphics.aspect_ratio", "1:1")
    res = args.resolution or cfg_get(cfg, "graphics.resolution", "2K")
    renderer = _renderer(cfg)
    string = args.string or cfg_get(cfg, "graphics.cta_bar.string", "primary")
    prompt = args.prompt
    if renderer == "pillow":
        prompt += band_instruction(cfg)
    elif keyword:
        prompt = inject_cta_string(prompt, keyword, string)
    extra = cfg_get(cfg, "graphics.negative_prompt_extra", "")
    if extra:
        prompt += "\n\n" + str(extra)
    cost = provider.estimate_cost("generate")
    if args.estimate:
        print("single: 1 generate = $%.3f (provider %s)" % (cost, provider.describe()))
        return
    if args.dry_run:
        _print_plan("single dry-run", provider, prompt, args.ref_image, cost,
                    {"renderer": renderer, "aspect": aspect, "resolution": res,
                     "thinking_high": args.thinking_high})
        return
    require_live(provider)
    refs = resolve_refs(args.ref_image, provider, cfg)
    try:
        result = provider.generate(prompt, ref_images=refs, aspect_ratio=aspect,
                                   resolution=res, thinking_high=args.thinking_high)
    except ProviderError as e:
        raise Abort("Generation failed: %s" % e)
    fetch_result(result, args.output)
    _finalize_after(args, cfg, keyword)
    print("\nDone: %s" % args.output)


def cmd_tweak(args):
    cfg = load_config(args.config)
    keyword = _require_keyword(args)
    provider = get_provider(cfg, args.provider)
    aspect = args.aspect_ratio or cfg_get(cfg, "graphics.aspect_ratio", "1:1")
    res = args.resolution or cfg_get(cfg, "graphics.resolution", "2K")
    instruction = args.instruction
    if _renderer(cfg) == "pillow":
        instruction += band_instruction(cfg)
    cost = provider.estimate_cost("edit")
    if args.estimate:
        print("tweak: 1 edit = $%.3f (provider %s)" % (cost, provider.describe()))
        return
    if args.dry_run:
        _print_plan("tweak dry-run", provider, instruction, [args.image], cost,
                    {"aspect": aspect, "resolution": res})
        return
    require_live(provider)
    if not os.path.exists(args.image):
        raise Abort("Image not found: %s" % args.image)
    try:
        result = provider.edit(args.image, instruction, aspect_ratio=aspect, resolution=res)
    except ProviderError as e:
        raise Abort("Tweak failed: %s" % e)
    fetch_result(result, args.output)
    _finalize_after(args, cfg, keyword)
    print("\nDone: %s" % args.output)


def cmd_finalize(args):
    cfg = load_config(args.config)
    if not os.path.exists(args.image):
        raise Abort("Image not found: %s" % args.image)
    out = finalize(args.image, validate_keyword(args.keyword), cfg, output=args.output,
                   string=args.string, strip=not args.no_strip,
                   logo=True if args.logo else None, renderer=args.renderer)
    print("\nDone: %s" % out)


def cmd_log(args):
    cfg = load_config(args.config)
    path = _usage_log_path(cfg)
    entry = {
        "date": args.date or _dt.date.today().isoformat(),
        "guide_title": args.title,
        "keyword": validate_keyword(args.keyword),
        "format_slug": args.format,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print("Logged to %s: %s" % (path, json.dumps(entry)))


def cmd_rotation(args):
    cfg = load_config(args.config)
    path = _usage_log_path(cfg)
    days = args.days or int(cfg_get(cfg, "graphics.format_rotation_days", DEFAULT_ROTATION_DAYS))
    cutoff = _dt.date.today() - _dt.timedelta(days=days)
    if not os.path.exists(path):
        print("No usage log at %s yet. Every format is available." % path)
        return
    used = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                d = _dt.date.fromisoformat(str(e.get("date", "")))
            except (ValueError, TypeError):
                continue
            if d >= cutoff:
                used.append(e)
    if not used:
        print("No formats used in the last %d days. Every format is available." % days)
        return
    print("Formats used in the last %d days (avoid these if another fits):" % days)
    for e in used:
        print("  %s  %-28s %s  (%s)" % (e.get("date"), e.get("format_slug"),
                                        e.get("keyword"), e.get("guide_title")))


# ---------------------------------------------------------------- CLI

def _common(p, provider=False):
    p.add_argument("--config", default=None, help="Config file (default: auto-discover)")
    if provider:
        p.add_argument("--provider", default=None, choices=["none", "kieai", "openai"],
                       help="Override graphics.provider")
        p.add_argument("--aspect-ratio", default=None, choices=list(ASPECT_RATIOS),
                       help="Default: graphics.aspect_ratio or 1:1")
        p.add_argument("--resolution", default=None, choices=list(RESOLUTIONS),
                       help="Default: graphics.resolution or 2K")
        p.add_argument("--estimate", action="store_true", help="Print the cost and exit, no network")
        p.add_argument("--dry-run", action="store_true",
                       help="Print provider, prompt, references and cost, then exit, no network")


def _finalize_flags(p, keyword_required=False):
    p.add_argument("--keyword", required=keyword_required, default=None,
                   help="3 to 12 uppercase letters; goes only in the CTA bar")
    p.add_argument("--string", default=None, choices=sorted(STRINGS),
                   help="CTA string variant (default: graphics.cta_bar.string or primary)")
    p.add_argument("--no-strip", action="store_true", help="Keep the C2PA manifest (not recommended)")
    p.add_argument("--logo", action="store_true", help="Composite brand.logo.path (off by default)")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("card", help="Pillow title card with CTA bar, zero cost")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--stat", action="append", default=[], help='"NUMBER|label", up to 4, repeatable')
    p.add_argument("--output", required=True, help="Absolute output PNG path")
    p.add_argument("--bg", choices=["dark", "light"], default="dark")
    p.add_argument("--size", type=int, default=DEFAULT_CARD_SIZE, help="Square size in px (default 2048)")
    _finalize_flags(p, keyword_required=True)
    _common(p)
    p.set_defaults(func=cmd_card)

    p = sub.add_parser("scene", help="Pass A: N text-free scene variants")
    p.add_argument("--prompt", required=True)
    p.add_argument("--output-prefix", required=True, help="Writes <prefix>-v1.png, -v2.png, ...")
    p.add_argument("--variants", type=int, default=2)
    p.add_argument("--ref-image", action="append", default=[], help="URL or local path, repeatable")
    p.add_argument("--thinking-high", action="store_true", help="Provider thinking mode, if supported")
    _common(p, provider=True)
    p.set_defaults(func=cmd_scene)

    p = sub.add_parser("text", help="Pass B: add text onto the winning scene")
    p.add_argument("--scene", required=True, help="Local path to the winning scene PNG")
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--fallback-prompt", default=None, help="Single-shot prompt used if the edit fails")
    p.add_argument("--no-finalize", action="store_true")
    _finalize_flags(p)
    _common(p, provider=True)
    p.set_defaults(func=cmd_text)

    p = sub.add_parser("single", help="One-shot scene + text")
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--ref-image", action="append", default=[], help="URL or local path, repeatable")
    p.add_argument("--thinking-high", action="store_true")
    p.add_argument("--no-finalize", action="store_true")
    _finalize_flags(p)
    _common(p, provider=True)
    p.set_defaults(func=cmd_single)

    p = sub.add_parser("tweak", help="Delta-only edit of an existing PNG")
    p.add_argument("--image", required=True)
    p.add_argument("--instruction", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--no-finalize", action="store_true")
    _finalize_flags(p)
    _common(p, provider=True)
    p.set_defaults(func=cmd_tweak)

    p = sub.add_parser("finalize", help="CTA bar + optional logo + C2PA strip")
    p.add_argument("--image", required=True)
    p.add_argument("--output", default=None, help="Default: in place")
    p.add_argument("--renderer", choices=["pillow", "model"], default=None,
                   help="Override graphics.cta_bar.renderer")
    _finalize_flags(p, keyword_required=True)
    _common(p)
    p.set_defaults(func=cmd_finalize)

    p = sub.add_parser("log", help="Append a shipped graphic to the rotation log")
    p.add_argument("--format", required=True, help="Format slug from the format library")
    p.add_argument("--keyword", required=True)
    p.add_argument("--title", required=True, help="Guide title")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    _common(p)
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("rotation", help="Formats used recently")
    p.add_argument("--days", type=int, default=None, help="Default: graphics.format_rotation_days or 7")
    _common(p)
    p.set_defaults(func=cmd_rotation)
    return ap


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (Abort, KeywordError, ProviderError, FileNotFoundError, ValueError, ImportError) as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
