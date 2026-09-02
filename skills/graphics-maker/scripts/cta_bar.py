#!/usr/bin/env python3
"""
Composite the keyword CTA bar onto a post graphic with Pillow.

The bar is a full-width band across the bottom edge of the image, the last
element, nothing below it. Text is rendered from real glyphs, so the keyword
cannot come out misspelled the way a model-rendered bar can. Zero cost.

Canonical strings (see references/cta-bar.md), nothing else is allowed:

    primary   COMMENT "[KEYWORD]" TO GET IT FOR FREE
    compact   Comment "[KEYWORD]" for the guide

Keyword shape: 3 to 12 uppercase ASCII letters. Anything else is rejected.

Colors: auto by default. The bottom 15 percent of the art is sampled for
luminance; dark art gets an accent band (brand.colors.accent_1) with text in
whichever of brand.colors.dark / light contrasts with it, light art gets a
dark band with light text. --bg / --fg, or graphics.cta_bar.bg / fg in
config, override the auto choice.

Font: --font, else brand.fonts.bold from config, else the bundled Inter Bold
shipped with the guide-maker sibling, else a platform bold sans, else
Pillow's built-in font.

Usage:
    python3 cta_bar.py --image /abs/in.png --keyword FLOWS --output /abs/out.png
    python3 cta_bar.py --image /abs/in.png --keyword FLOWS --output /abs/out.png \
        --string compact --height-pct 0.11 --bg "#1A1A1C" --fg "#F7F7F7"

Prints the exact rendered string on its own line so you can read it
character by character against the keyword in your DM tool.
"""
import argparse
import os
import pathlib
import platform
import re
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cfg import load_config, cfg_get, skills_root  # noqa: E402

KEYWORD_RE = re.compile(r"^[A-Z]{3,12}$")

STRINGS = {
    "primary": 'COMMENT "{kw}" TO GET IT FOR FREE',
    "compact": 'Comment "{kw}" for the guide',
}

DEFAULT_HEIGHT_PCT = 0.11
DEFAULT_COLORS = {"dark": "#1A1A1C", "light": "#F7F7F7", "accent_1": "#A6CB17"}

PLATFORM_BOLD_FONTS = {
    "Darwin": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "Linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ],
    "Windows": [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf",
    ],
}
PLATFORM_REGULAR_FONTS = {
    "Darwin": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "Linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ],
    "Windows": [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
    ],
}


class KeywordError(ValueError):
    pass


def validate_keyword(keyword):
    """Return the keyword if it matches [A-Z]{3,12}, else raise KeywordError."""
    kw = (keyword or "").strip()
    if not KEYWORD_RE.match(kw):
        raise KeywordError(
            'Keyword "%s" is not valid. Use 3 to 12 uppercase ASCII letters, '
            "no digits, spaces, hyphens or quotes (example: FLOWS)." % keyword)
    return kw


def render_string(keyword, variant="primary"):
    """Return the canonical CTA string for the keyword."""
    if variant not in STRINGS:
        raise ValueError("string must be one of %s" % ", ".join(STRINGS))
    return STRINGS[variant].format(kw=validate_keyword(keyword))


def bundled_font_path(weight="bold"):
    """The Inter face shipped with the guide-maker sibling skill, if present."""
    name = "Inter-Bold.ttf" if weight == "bold" else "Inter-Regular.ttf"
    here = pathlib.Path(__file__).resolve()
    cands = [
        here.parents[2] / "guide-maker" / "assets" / "fonts" / name,
        skills_root() / "guide-maker" / "assets" / "fonts" / name,
    ]
    for c in cands:
        if c.exists():
            return str(c)
    return None


def find_font_path(cfg=None, explicit=None, weight="bold"):
    """Resolve a font file path by the documented precedence. None means
    'use Pillow's built-in font'."""
    cfg = cfg or {}
    if explicit:
        if not os.path.exists(explicit):
            raise FileNotFoundError("Font not found: %s" % explicit)
        return explicit
    key = "brand.fonts.bold" if weight == "bold" else "brand.fonts.regular"
    from_cfg = cfg_get(cfg, key, "")
    if from_cfg:
        p = os.path.expanduser(str(from_cfg))
        if os.path.exists(p):
            return p
        print("Warning: %s=%s not found, falling back" % (key, from_cfg), file=sys.stderr)
    bundled = bundled_font_path(weight)
    if bundled:
        return bundled
    table = PLATFORM_BOLD_FONTS if weight == "bold" else PLATFORM_REGULAR_FONTS
    for p in table.get(platform.system(), []):
        if os.path.exists(p):
            return p
    return None


def load_font(path, size):
    """ImageFont for path at size; Pillow's default face when path is None."""
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError as e:
            print("Warning: could not load font %s (%s), using Pillow default" % (path, e),
                  file=sys.stderr)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no size argument
        return ImageFont.load_default()


def hex_to_rgb(value):
    v = str(value).strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6 or not re.match(r"^[0-9a-fA-F]{6}$", v):
        raise ValueError("Bad hex color: %s" % value)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def bottom_luminance(img, pct=0.15):
    """Mean luminance (0-255) of the bottom pct of the image."""
    w, h = img.size
    band_h = max(1, int(h * pct))
    band = img.crop((0, h - band_h, w, h)).convert("L").resize((64, 8))
    px = list(band.getdata())
    return sum(px) / len(px)


def auto_colors(img, cfg=None):
    """(bg_hex, fg_hex) chosen for contrast against the art's bottom band."""
    cfg = cfg or {}
    colors = {k: cfg_get(cfg, "brand.colors.%s" % k, v) or v for k, v in DEFAULT_COLORS.items()}
    art_is_dark = bottom_luminance(img) < 128
    if art_is_dark:
        bg = colors["accent_1"]
        fg = colors["dark"] if luminance(hex_to_rgb(bg)) >= 140 else colors["light"]
    else:
        bg = colors["dark"]
        fg = colors["light"]
    return bg, fg


def fit_font(draw, text, font_path, max_width, max_height):
    """Largest font size whose rendered text fits the box."""
    size = max(8, int(max_height))
    while size > 8:
        font = load_font(font_path, size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if (right - left) <= max_width and (bottom - top) <= max_height:
            return font
        size -= max(1, size // 20)
    return load_font(font_path, 8)


def add_cta_bar(image_path, keyword, output_path, string="primary",
                height_pct=None, bg=None, fg=None, font=None, cfg=None):
    """Draw the bar onto image_path and save to output_path. Returns the
    rendered string. The canvas size does not change: the band overlays the
    bottom edge, which the art is expected to leave empty."""
    cfg = cfg or {}
    text = render_string(keyword, string)
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    pct = height_pct if height_pct is not None else cfg_get(cfg, "graphics.cta_bar.height_pct", DEFAULT_HEIGHT_PCT)
    pct = float(pct)
    if not 0.05 <= pct <= 0.3:
        raise ValueError("height_pct must be between 0.05 and 0.30, got %s" % pct)
    band_h = int(round(h * pct))

    auto_bg, auto_fg = auto_colors(img, cfg)
    bg = bg or cfg_get(cfg, "graphics.cta_bar.bg", "") or auto_bg
    fg = fg or cfg_get(cfg, "graphics.cta_bar.fg", "") or auto_fg
    bg_rgb, fg_rgb = hex_to_rgb(bg), hex_to_rgb(fg)

    draw = ImageDraw.Draw(img)
    draw.rectangle([0, h - band_h, w, h], fill=bg_rgb)

    font_path = find_font_path(cfg, font, "bold")
    font_obj = fit_font(draw, text, font_path, max_width=w * 0.88, max_height=band_h * 0.46)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font_obj)
    tw, th = right - left, bottom - top
    x = (w - tw) / 2 - left
    y = h - band_h + (band_h - th) / 2 - top
    draw.text((x, y), text, font=font_obj, fill=fg_rgb)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    print("CTA bar: %s | band %dpx (%.0f%%) | bg %s fg %s | font %s"
          % (string, band_h, pct * 100, bg, fg, os.path.basename(font_path) if font_path else "pillow-default"))
    print(text)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True, help="Absolute path to the input PNG")
    ap.add_argument("--keyword", required=True, help="3 to 12 uppercase letters, e.g. FLOWS")
    ap.add_argument("--output", required=True, help="Absolute path for the output PNG")
    ap.add_argument("--string", choices=sorted(STRINGS), default=None,
                    help="Which canonical string (default: graphics.cta_bar.string or primary)")
    ap.add_argument("--height-pct", type=float, default=None,
                    help="Band height as a fraction of image height (default 0.11)")
    ap.add_argument("--bg", default=None, help="Band color hex (default: auto contrast)")
    ap.add_argument("--fg", default=None, help="Text color hex (default: auto contrast)")
    ap.add_argument("--font", default=None, help="Path to a bold TTF/OTF (default: config, bundled, platform)")
    ap.add_argument("--config", default=None, help="Config file (default: auto-discover)")
    args = ap.parse_args()

    try:
        cfg = load_config(args.config)
        string = args.string or cfg_get(cfg, "graphics.cta_bar.string", "primary")
        if not os.path.exists(args.image):
            raise FileNotFoundError("Image not found: %s" % args.image)
        add_cta_bar(args.image, args.keyword, args.output, string=string,
                    height_pct=args.height_pct, bg=args.bg, fg=args.fg,
                    font=args.font, cfg=cfg)
        print("Wrote: %s" % args.output)
    except (KeywordError, ValueError, FileNotFoundError, ImportError) as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
