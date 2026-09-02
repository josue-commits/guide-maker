#!/usr/bin/env python3
"""
Banner Generator for Notion Guide Pages

Two modes:
  - Simple (Pillow): Brand-colored banners with typography. No API cost.
  - AI (KieAI): AI-generated banners for tech guides. Requires API key.

Both modes output 1500x600px PNGs (Notion optimal cover size).
Typeface: brand.fonts.* from config, else the bundled Inter (assets/fonts),
else a platform font, else Pillow's default with a warning.
Includes Notion file upload to set banners as page covers.

Usage:
    # Simple banner
    python3 banner_generator.py simple --title "Guide Title" --subtitle "Optional"

    # AI banner
    python3 banner_generator.py ai --prompt "Minimalist banner with terminal theme"

    # Upload to Notion page
    python3 banner_generator.py upload --file /tmp/banner.png --page-id abc123

    # Generate + upload in one step
    python3 banner_generator.py simple --title "Guide Title" --upload-to PAGE_ID
"""

import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --- Constants ---

BANNER_WIDTH = 1500
BANNER_HEIGHT = 600

# Default brand colors (overridden by config.yaml if present)
DARK = "#1A1A1C"
LIGHT = "#F7F7F7"
GREEN = "#A6CB17"
PURPLE = "#8033F4"

# Notion + KieAI config loaded from config.yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_config, cfg_get, secret, add_config_arg
import _notion

_CFG = None
_CFG_PATH = None


def config():
    """Config loaded lazily so `simple` still works with no config at all."""
    global _CFG
    if _CFG is None:
        _CFG = load_config(_CFG_PATH)
        _notion.init(_CFG)
    return _CFG


def get_brand_colors():
    try:
        colors = cfg_get(config(), "brand.colors") or {}
    except FileNotFoundError:
        colors = {}
    return {
        "dark": colors.get("dark") or DARK,
        "light": colors.get("light") or LIGHT,
        "accent_1": colors.get("accent_1") or GREEN,
        "accent_2": colors.get("accent_2") or PURPLE,
    }


def get_kieai_key():
    try:
        return secret(config(), "kieai")
    except FileNotFoundError:
        return secret({}, "kieai")

# KieAI config
KIEAI_API_BASE = "https://api.kie.ai/api/v1"

# --- Fonts ---
#
# Resolution order for the banner typeface:
#   1. brand.fonts.bold / brand.fonts.regular from the config (absolute paths)
#   2. the bundled Inter faces in assets/fonts (OFL, ship with the skill)
#   3. platform fonts: macOS Poppins or HelveticaNeue.ttc, Linux DejaVu or
#      Liberation, Windows Arial
#   4. Pillow's built-in bitmap font, with a warning (banner will look rough)

SKILL_DIR = Path(__file__).resolve().parent.parent
BUNDLED_BOLD = SKILL_DIR / "assets" / "fonts" / "Inter-Bold.ttf"
BUNDLED_REGULAR = SKILL_DIR / "assets" / "fonts" / "Inter-Regular.ttf"

# (path, face index) pairs. A .ttc holds several faces; the index picks one.
# Verified with fonttools against HelveticaNeue.ttc: 0=Regular 1=Bold 2=Italic
# 3=Bold Italic 10=Medium. Index 4 is "Condensed Bold", not Bold. Do not guess
# these, .ttc ordering is not stable across OS versions.
FALLBACK_FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
FALLBACK_FONT_INDEX = 1  # Bold (was 4 = Condensed Bold, a bug)
FALLBACK_FONT_REGULAR_INDEX = 0  # Regular

PLATFORM_FONTS_BOLD = [
    ("/Library/Fonts/Poppins-Bold.ttf", 0),
    ("/Library/Fonts/Poppins-SemiBold.ttf", 0),
    (os.path.expanduser("~/Library/Fonts/Poppins-Bold.ttf"), 0),
    (os.path.expanduser("~/Library/Fonts/Poppins-SemiBold.ttf"), 0),
    (FALLBACK_FONT, FALLBACK_FONT_INDEX),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
    ("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
    ("/usr/share/fonts/liberation/LiberationSans-Bold.ttf", 0),
    ("C:\\Windows\\Fonts\\arialbd.ttf", 0),
]
PLATFORM_FONTS_REGULAR = [
    ("/Library/Fonts/Poppins-Regular.ttf", 0),
    ("/Library/Fonts/Poppins-Medium.ttf", 0),
    (os.path.expanduser("~/Library/Fonts/Poppins-Regular.ttf"), 0),
    (os.path.expanduser("~/Library/Fonts/Poppins-Medium.ttf"), 0),
    (FALLBACK_FONT, FALLBACK_FONT_REGULAR_INDEX),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0),
    ("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", 0),
    ("C:\\Windows\\Fonts\\arial.ttf", 0),
]

_font_warned = set()


def _config_font(bold):
    """Font path from brand.fonts.* in the config, or empty string."""
    try:
        fonts = cfg_get(config(), "brand.fonts") or {}
    except Exception:
        return ""
    return (fonts.get("bold" if bold else "regular") or "").strip()


def resolve_font_path(bold=True):
    """Return (path, index) of the first usable font, or (None, 0)."""
    candidates = []
    configured = _config_font(bold)
    if configured:
        candidates.append((os.path.expanduser(configured), 0))
    candidates.append((str(BUNDLED_BOLD if bold else BUNDLED_REGULAR), 0))
    candidates.extend(PLATFORM_FONTS_BOLD if bold else PLATFORM_FONTS_REGULAR)
    for path, index in candidates:
        if os.path.exists(path):
            return path, index
    return None, 0


def load_font(size, bold=True):
    """Load the best available font at the given size (see resolution order)."""
    path, index = resolve_font_path(bold)
    if path:
        try:
            return ImageFont.truetype(path, size, index=index)
        except Exception as exc:  # corrupt file, unsupported format
            print(f"Warning: could not load font {path}: {exc}", file=sys.stderr)
    key = "bold" if bold else "regular"
    if key not in _font_warned:
        _font_warned.add(key)
        print("Warning: no TrueType font found (bundled Inter missing and no "
              "platform font). Falling back to Pillow's bitmap font; set "
              "brand.fonts.* in your config for a proper banner.",
              file=sys.stderr)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no size argument
        return ImageFont.load_default()


# --- Color Helpers ---

def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# --- Keyword guard ---

KEYWORD_SHAPE = re.compile(r"^[A-Z]{3,12}$")


def refuse_keyword_title(title, keyword=None, allow=False):
    """Exit 2 when the cover title is the lead-magnet keyword.

    The cover never carries the keyword; the post graphic's CTA band does.
    The check fires when --title equals --keyword (or GUIDE_MAKER_KEYWORD),
    and, with no keyword given, when the whole title looks like one
    (a single ALL-CAPS token). --allow-keyword overrides.
    """
    if allow:
        return
    keyword = (keyword or os.environ.get("GUIDE_MAKER_KEYWORD", "") or "").strip()
    text = (title or "").strip()
    looks_like_keyword = KEYWORD_SHAPE.match(text) is not None
    if (keyword and text.upper() == keyword.upper()) or (not keyword and looks_like_keyword):
        print(f"Error: cover title {text!r} is the lead-magnet keyword. The cover never "
              "carries the keyword; it belongs in the post graphic's CTA band "
              "(graphics-maker). Use the guide's short title, or pass "
              "--allow-keyword if this really is the title.", file=sys.stderr)
        sys.exit(2)


# --- Simple Banner Generator ---

def generate_simple_banner(title, subtitle=None, style="dark",
                           output_path="/tmp/banner.png"):
    """
    Generate a brand-colored banner using Pillow.

    Args:
        title: Main banner text
        subtitle: Optional smaller text below title
        style: "dark" (solid dark bg), "gradient" (dark to green),
               "accent" (dark bg + green/purple accent stripe)
        output_path: Where to save the PNG

    Returns:
        Path to the generated banner file
    """
    # Load brand colors from config (if available)
    try:
        colors = get_brand_colors()
        dark, light, green, purple = colors["dark"], colors["light"], colors["accent_1"], colors["accent_2"]
    except Exception:
        dark, light, green, purple = DARK, LIGHT, GREEN, PURPLE

    img = Image.new("RGB", (BANNER_WIDTH, BANNER_HEIGHT), hex_to_rgb(dark))
    draw = ImageDraw.Draw(img)

    if style == "gradient":
        _draw_gradient(draw, dark, green)
    elif style == "accent":
        _draw_accent_stripe(draw, green, purple)

    # Always add a subtle green accent stripe on the left for brand identity
    if style == "dark":
        draw.rectangle(
            [(0, 0), (12, BANNER_HEIGHT)],
            fill=hex_to_rgb(green)
        )

    # Load fonts
    title_font = load_font(68, bold=True)
    subtitle_font = load_font(36, bold=False)

    # Wrap and draw title
    title_lines = _wrap_text(title, title_font, BANNER_WIDTH - 200)
    _draw_centered_text(
        draw, title_lines, title_font,
        hex_to_rgb(light),
        y_offset=-40 if subtitle else 0
    )

    # Draw subtitle if provided
    if subtitle:
        subtitle_lines = _wrap_text(subtitle, subtitle_font, BANNER_WIDTH - 200)
        # Position subtitle below title
        title_block_height = len(title_lines) * (title_font.size + 12)
        subtitle_y = (BANNER_HEIGHT // 2) - 40 + (title_block_height // 2) + 30
        _draw_centered_text(
            draw, subtitle_lines, subtitle_font,
            hex_to_rgb(green),
            y_absolute=subtitle_y
        )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    print(f"Simple banner saved: {output_path} ({BANNER_WIDTH}x{BANNER_HEIGHT})")
    return output_path


def _draw_gradient(draw, dark=DARK, green=GREEN):
    """Draw a dark-to-green horizontal gradient background."""
    dark_rgb = hex_to_rgb(dark)
    green_rgb = hex_to_rgb(green)
    for x in range(BANNER_WIDTH):
        ratio = x / BANNER_WIDTH
        # Only blend to ~30% green intensity for subtlety
        r = int(dark_rgb[0] + (green_rgb[0] - dark_rgb[0]) * ratio * 0.3)
        g = int(dark_rgb[1] + (green_rgb[1] - dark_rgb[1]) * ratio * 0.3)
        b = int(dark_rgb[2] + (green_rgb[2] - dark_rgb[2]) * ratio * 0.3)
        draw.line([(x, 0), (x, BANNER_HEIGHT)], fill=(r, g, b))


def _draw_accent_stripe(draw, green=GREEN, purple=PURPLE):
    """Draw green and purple accent stripes on top and bottom edges."""
    draw.rectangle(
        [(0, 0), (BANNER_WIDTH, 6)],
        fill=hex_to_rgb(green)
    )
    draw.rectangle(
        [(0, BANNER_HEIGHT - 6), (BANNER_WIDTH, BANNER_HEIGHT)],
        fill=hex_to_rgb(purple)
    )
    # Left stripe
    draw.rectangle(
        [(0, 0), (12, BANNER_HEIGHT)],
        fill=hex_to_rgb(green)
    )


def _wrap_text(text, font, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def _draw_centered_text(draw, lines, font, color, y_offset=0, y_absolute=None):
    """Draw multiple lines of text centered on the image."""
    line_height = font.size + 12
    total_height = len(lines) * line_height

    if y_absolute is not None:
        y = y_absolute
    else:
        y = (BANNER_HEIGHT - total_height) // 2 + y_offset

    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (BANNER_WIDTH - text_width) // 2
        draw.text((x, y), line, fill=color, font=font)
        y += line_height


# --- AI Banner Generator (KieAI) ---

def _load_kieai_key():
    """Load KieAI API key from config or default path."""
    key = get_kieai_key()
    if key:
        return key
    print("Error: KieAI API key not configured.", file=sys.stderr)
    print("Set KIEAI_API_KEY, create ~/.config/kieai/api_key, or set "
          "providers.kieai.api_key in config.yaml", file=sys.stderr)
    return None


def _kieai_request(method, path, body=None, api_key=None):
    """Make an authenticated request to the KieAI API."""
    url = f"{KIEAI_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_ai_banner(prompt, reference_urls=None,
                       output_path="/tmp/banner.png",
                       model="nano-banana-2",
                       google_search=False,
                       resolution="2K"):
    """
    Generate an AI banner using KieAI's nano-banana-2 model.

    Args:
        prompt: Description of the desired banner
        reference_urls: Optional list of public image URLs for reference
                       (e.g., tool logos). Up to 14 URLs.
        output_path: Where to save the final cropped PNG
        model: KieAI model name (default: nano-banana-2)
        google_search: Use Google Web Search grounding for real-time info
        resolution: Output resolution: 1K, 2K, or 4K (default: 2K)

    Returns:
        Path to the generated banner file, or None on failure
    """
    api_key = _load_kieai_key()
    if not api_key:
        return None

    print(f"Generating AI banner (model: {model})...")
    print(f"  Prompt: {prompt[:100]}...")
    if reference_urls:
        print(f"  Reference images: {len(reference_urls)}")
    if google_search:
        print(f"  Google Search grounding: enabled")

    # Step 1: Submit generation request via jobs API
    try:
        input_body = {
            "prompt": prompt,
            "aspect_ratio": "3:2",
            "output_format": "png",
            "resolution": resolution,
        }
        if reference_urls:
            input_body["image_input"] = reference_urls[:14]
        if google_search:
            input_body["google_search"] = True

        request_body = {
            "model": model,
            "input": input_body,
        }
        result = _kieai_request("POST", "/jobs/createTask",
                                request_body, api_key)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"KieAI API error {e.code}: {error_body}", file=sys.stderr)
        return None

    task_id = (result.get("data", {}).get("task_id")
               or result.get("data", {}).get("taskId"))
    if not task_id:
        print(f"Error: No task_id in response: {result}", file=sys.stderr)
        return None

    print(f"  Task ID: {task_id}")

    # Step 2: Poll until complete
    max_polls = 60  # 5 minutes max
    for i in range(max_polls):
        time.sleep(5)
        try:
            status = _kieai_request(
                "GET",
                f"/jobs/recordInfo?taskId={task_id}",
                api_key=api_key
            )
        except urllib.error.HTTPError:
            continue

        data = status.get("data", {})
        state = data.get("state", "")

        if state in ("completed", "success"):
            # Try output fields first
            result_url = None
            output = data.get("output", {})
            if output:
                result_url = (output.get("image_url")
                              or output.get("result_url"))
                if not result_url:
                    results = output.get("results", [])
                    if results:
                        result_url = (results[0] if isinstance(results[0], str)
                                      else results[0].get("url"))

            # Try resultJson (nano-banana-2 format)
            if not result_url:
                result_json_str = data.get("resultJson", "")
                if result_json_str:
                    try:
                        result_json = json.loads(result_json_str)
                        result_urls = result_json.get("resultUrls", [])
                        if result_urls:
                            result_url = result_urls[0]
                    except (json.JSONDecodeError, AttributeError):
                        pass

            if result_url:
                print(f"  Generation complete. Downloading...")
                return _download_and_crop(result_url, output_path)

            print(f"Error: Task completed but no result URL: {data}",
                  file=sys.stderr)
            return None

        elif state in ("fail", "failed", "error"):
            error_msg = (data.get("failMsg") or data.get("error")
                         or "Unknown error")
            print(f"Error: Generation failed: {error_msg}", file=sys.stderr)
            return None

        if (i + 1) % 6 == 0:
            print(f"  Still generating... ({(i+1)*5}s)")

    print("Error: Generation timed out after 5 minutes", file=sys.stderr)
    return None


def _download_and_crop(url, output_path):
    """Download image from URL and crop/resize to banner dimensions."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })
    with urllib.request.urlopen(req) as resp:
        image_data = resp.read()

    # Save raw download temporarily. The generation already cost an API call
    # by this point, so create the output dir rather than losing it to a
    # missing path.
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    raw_path = output_path + ".raw.png"
    with open(raw_path, "wb") as f:
        f.write(image_data)

    # Open, crop to 5:2 ratio, resize to exact dimensions
    img = Image.open(raw_path)
    w, h = img.size

    # Calculate crop box for 5:2 aspect ratio (2.5:1)
    target_ratio = BANNER_WIDTH / BANNER_HEIGHT  # 2.5
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Too wide, crop sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Too tall, crop top/bottom
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    # Resize to exact banner size
    img = img.resize((BANNER_WIDTH, BANNER_HEIGHT), Image.LANCZOS)
    img.save(output_path, "PNG", optimize=True)

    # Clean up raw file
    os.remove(raw_path)

    print(f"AI banner saved: {output_path} ({BANNER_WIDTH}x{BANNER_HEIGHT})")
    return output_path


# --- Notion Upload ---

def upload_banner_to_notion(file_path, page_id):
    """Upload a banner image and set it as a Notion page cover.

    Uses the shared file_upload helper in _notion.py (Notion-Version
    2025-09-03 for the upload endpoints, see that module for why two API
    versions coexist).

    Returns True on success, False on failure.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return False

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    print(f"Uploading banner to Notion page {page_id}...")
    print(f"  File: {filename} ({file_size:,} bytes)")
    try:
        print("  [1/2] Uploading file...")
        upload_id = _notion.upload_file(file_path, content_type="image/png")
        print(f"  Upload ID: {upload_id}")
        print("  [2/2] Setting as page cover...")
        _notion.set_page_cover(page_id, upload_id)
        print(f"  Banner set as cover on page {page_id}")
        return True
    except Exception as exc:
        print(f"Error uploading banner: {exc}", file=sys.stderr)
        return False


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Banner generator for Notion guides")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Simple banner
    simple = subparsers.add_parser("simple", help="Generate a simple Pillow banner")
    simple.add_argument("--title", required=True, help="Banner title text")
    simple.add_argument("--subtitle", default=None, help="Optional subtitle")
    simple.add_argument("--style", default="dark",
                        choices=["dark", "gradient", "accent"],
                        help="Banner style (default: dark)")
    simple.add_argument("--output", default="/tmp/banner.png",
                        help="Output file path")
    simple.add_argument("--upload-to", default=None,
                        help="Notion page ID to upload to after generating")
    simple.add_argument("--keyword", default=None,
                        help="The guide's keyword; the title must not equal it "
                             "(also read from GUIDE_MAKER_KEYWORD)")
    simple.add_argument("--allow-keyword", action="store_true",
                        help="Allow a title that equals the keyword")

    # AI banner
    ai = subparsers.add_parser("ai", help="Generate an AI banner via KieAI")
    ai.add_argument("--prompt", required=True, help="Image generation prompt")
    ai.add_argument("--ref-image", action="append", default=[],
                    help="Public URL of reference image (repeatable, max 14)")
    ai.add_argument("--google-search", action="store_true",
                    help="Enable Google Search grounding for real-time info")
    ai.add_argument("--resolution", default="2K",
                    choices=["1K", "2K", "4K"],
                    help="Output resolution (default: 2K)")
    ai.add_argument("--output", default="/tmp/banner.png",
                    help="Output file path")
    ai.add_argument("--upload-to", default=None,
                    help="Notion page ID to upload to after generating")

    # Upload only
    upload = subparsers.add_parser("upload", help="Upload a banner to Notion")
    upload.add_argument("--file", required=True, help="Path to banner image")
    upload.add_argument("--page-id", required=True, help="Notion page ID")

    add_config_arg(parser, [simple, ai, upload])
    args = parser.parse_args()
    global _CFG_PATH
    _CFG_PATH = getattr(args, "config", None)

    if args.command == "simple":
        refuse_keyword_title(args.title, args.keyword, args.allow_keyword)
        path = generate_simple_banner(
            title=args.title,
            subtitle=args.subtitle,
            style=args.style,
            output_path=args.output,
        )
        if args.upload_to and path:
            upload_banner_to_notion(path, args.upload_to)

    elif args.command == "ai":
        ref_urls = args.ref_image if args.ref_image else None
        path = generate_ai_banner(
            prompt=args.prompt,
            reference_urls=ref_urls,
            output_path=args.output,
            google_search=args.google_search,
            resolution=args.resolution,
        )
        if path and args.upload_to:
            upload_banner_to_notion(path, args.upload_to)
        elif not path:
            print("AI generation failed. Falling back to simple banner.")
            fallback = generate_simple_banner(
                title="Guide",
                style="dark",
                output_path=args.output,
            )
            if args.upload_to and fallback:
                upload_banner_to_notion(fallback, args.upload_to)

    elif args.command == "upload":
        upload_banner_to_notion(args.file, args.page_id)


if __name__ == "__main__":
    main()
