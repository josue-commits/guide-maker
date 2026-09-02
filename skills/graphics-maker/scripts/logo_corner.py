#!/usr/bin/env python3
"""
Composite your logo into a corner of a generated graphic.

OFF by default. graphics_generate.py only calls this when you pass --logo or
set brand.logo.on_post_graphic: true in config. Post graphics generally ship
without a logo; the CTA bar is the element that earns the click.

Config keys:
    brand.logo.path            PNG with transparency, used on light art
    graphics.logo_on_dark      optional light-colored variant for dark art
    graphics.logo_corner       top-left | top-right | bottom-left | bottom-right
                               (default top-left; the bottom corners are
                               refused when a CTA bar is present, so prefer top)
    graphics.logo_width_pct    logo width as a fraction of image width (0.12)

The placement zone is checked for a flat background first. If the corner has
content (edges, text, a card), the logo is skipped rather than pasted over it.
Pass --force-placement to paste anyway.

Usage:
    python3 logo_corner.py /abs/image.png [--logo /abs/logo.png] [--corner top-right]
                           [--force-variant light|dark] [--force-placement] [--config PATH]

Prints SKIP (reason) or PLACE:<corner> to stdout. Exits 0 in both cases;
exits 1 only on bad input.
"""
import argparse
import os
import sys

from PIL import Image, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cfg import load_config, cfg_get  # noqa: E402

CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
DEFAULT_WIDTH_PCT = 0.12
PADDING_PCT = 0.02
BG_TOLERANCE = 45  # max per-pixel distance from the zone mean to count as "flat"


def zone_is_clear(zone, tolerance=BG_TOLERANCE):
    """True if every pixel in zone is within tolerance of the zone's mean color."""
    small = zone.convert("RGB").resize((48, 48))
    mean = ImageStat.Stat(small).mean
    worst = 0.0
    for px in small.getdata():
        d = ((px[0] - mean[0]) ** 2 + (px[1] - mean[1]) ** 2 + (px[2] - mean[2]) ** 2) ** 0.5
        if d > worst:
            worst = d
    return worst <= tolerance, worst


def zone_is_dark(zone):
    return ImageStat.Stat(zone.convert("L")).mean[0] < 128


def place_logo(image_path, logo_path, logo_on_dark=None, corner="top-left",
               width_pct=DEFAULT_WIDTH_PCT, force_variant=None, force_placement=False):
    """Composite the logo in place. Returns a status string (SKIP ... or PLACE:...)."""
    if corner not in CORNERS:
        raise ValueError("corner must be one of %s" % ", ".join(CORNERS))
    img = Image.open(image_path).convert("RGBA")
    W, H = img.size
    pad = int(W * PADDING_PCT)

    logo = Image.open(logo_path).convert("RGBA")
    lw = int(W * width_pct)
    lh = int(lw * logo.height / logo.width)
    if lw + pad > W or lh + pad > H:
        return "SKIP (image too small for logo)"

    x = pad if corner.endswith("left") else W - lw - pad
    y = pad if corner.startswith("top") else H - lh - pad
    zone = img.crop((x, y, x + lw, y + lh))

    variant = force_variant or ("light" if zone_is_dark(zone) else "dark")
    if variant == "light" and logo_on_dark and os.path.exists(logo_on_dark):
        logo = Image.open(logo_on_dark).convert("RGBA")

    clear, worst = zone_is_clear(zone)
    if not clear and not force_placement:
        return "SKIP (%s not clear, max_distance=%.1f) variant=%s" % (corner, worst, variant)

    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.paste(logo, (x, y), logo)
    img.convert("RGB").save(image_path, "PNG", optimize=True)
    return "PLACE:%s variant=%s size=%dx%d" % (corner, variant, lw, lh)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image_path", help="Absolute path to the PNG to modify in place")
    ap.add_argument("--logo", default=None, help="Logo PNG (default: brand.logo.path from config)")
    ap.add_argument("--logo-on-dark", default=None, help="Light logo variant for dark art (default: graphics.logo_on_dark)")
    ap.add_argument("--corner", choices=CORNERS, default=None, help="Default: graphics.logo_corner or top-left")
    ap.add_argument("--width-pct", type=float, default=None, help="Default: graphics.logo_width_pct or 0.12")
    ap.add_argument("--force-variant", choices=["light", "dark"], default=None)
    ap.add_argument("--force-placement", action="store_true", help="Paste even if the corner has content")
    ap.add_argument("--config", default=None, help="Config file (default: auto-discover)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    logo = args.logo or cfg_get(cfg, "brand.logo.path", "")
    if not logo:
        print("SKIP (no logo configured: set brand.logo.path or pass --logo)")
        return
    logo = os.path.expanduser(str(logo))
    if not os.path.exists(logo):
        print("Error: logo file not found: %s" % logo, file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.image_path):
        print("Error: image not found: %s" % args.image_path, file=sys.stderr)
        sys.exit(1)

    corner = args.corner or cfg_get(cfg, "graphics.logo_corner", "top-left")
    width_pct = args.width_pct or float(cfg_get(cfg, "graphics.logo_width_pct", DEFAULT_WIDTH_PCT))
    on_dark = args.logo_on_dark or cfg_get(cfg, "graphics.logo_on_dark", "") or None
    if on_dark:
        on_dark = os.path.expanduser(str(on_dark))
    try:
        print(place_logo(args.image_path, logo, logo_on_dark=on_dark, corner=corner,
                         width_pct=width_pct, force_variant=args.force_variant,
                         force_placement=args.force_placement))
    except ValueError as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
