#!/usr/bin/env python3
"""
Banner Generator for Notion Guide Pages

Two modes:
  - Simple (Pillow): Brand-colored banners with typography. No API cost.
  - AI (KieAI): AI-generated banners for tech guides. Requires API key.

Both modes output 1500x600px PNGs (Notion optimal cover size).
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
from _config import get_notion_token, get_kieai_key, get_brand_colors

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION_UPLOAD = "2025-09-03"

# KieAI config
KIEAI_API_BASE = "https://api.kie.ai/api/v1"

# Font paths (macOS)
FONT_PATHS = [
    "/Library/Fonts/Poppins-Bold.ttf",
    "/Library/Fonts/Poppins-SemiBold.ttf",
    os.path.expanduser("~/Library/Fonts/Poppins-Bold.ttf"),
    os.path.expanduser("~/Library/Fonts/Poppins-SemiBold.ttf"),
]
FALLBACK_FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
FALLBACK_FONT_INDEX = 4  # Bold weight

FONT_PATHS_REGULAR = [
    "/Library/Fonts/Poppins-Regular.ttf",
    "/Library/Fonts/Poppins-Medium.ttf",
    os.path.expanduser("~/Library/Fonts/Poppins-Regular.ttf"),
    os.path.expanduser("~/Library/Fonts/Poppins-Medium.ttf"),
]
FALLBACK_FONT_REGULAR = "/System/Library/Fonts/HelveticaNeue.ttc"
FALLBACK_FONT_REGULAR_INDEX = 0  # Regular weight


# --- Font Loading ---

def load_font(size, bold=True):
    """Load Poppins if available, fall back to HelveticaNeue."""
    paths = FONT_PATHS if bold else FONT_PATHS_REGULAR
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fallback
    fallback = FALLBACK_FONT if bold else FALLBACK_FONT_REGULAR
    index = FALLBACK_FONT_INDEX if bold else FALLBACK_FONT_REGULAR_INDEX
    return ImageFont.truetype(fallback, size, index=index)


# --- Color Helpers ---

def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


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
    print("Add kieai_api_key to your config.yaml, or create ~/.config/kieai/api_key", file=sys.stderr)
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

    # Save raw download temporarily
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

def _notion_upload_request(method, path, body=None, headers_extra=None,
                           raw_data=None, content_type=None):
    """
    Make a Notion API request with the file upload API version.
    Separate from md_to_notion's notion_request to avoid changing its version.
    """
    url = f"{NOTION_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_notion_token()}",
        "Notion-Version": NOTION_VERSION_UPLOAD,
    }

    if content_type:
        headers["Content-Type"] = content_type

    if headers_extra:
        headers.update(headers_extra)

    if body and not raw_data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    elif raw_data:
        data = raw_data
    else:
        data = None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Notion API error {e.code}: {error_body}", file=sys.stderr)
        raise


def upload_banner_to_notion(file_path, page_id):
    """
    Upload a banner image and set it as a Notion page cover.

    Uses the Notion file upload API (requires Notion-Version: 2025-09-03).

    Args:
        file_path: Path to the banner PNG file
        page_id: Notion page ID to set the cover on

    Returns:
        True on success, False on failure
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return False

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    print(f"Uploading banner to Notion page {page_id}...")
    print(f"  File: {filename} ({file_size:,} bytes)")

    try:
        # Step 1: Create file upload object
        print("  [1/3] Creating file upload...")
        upload_result = _notion_upload_request("POST", "/file_uploads", {
            "mode": "single_part",
            "filename": filename,
            "content_type": "image/png",
        })
        upload_id = upload_result["id"]
        print(f"  Upload ID: {upload_id}")

        # Step 2: Send the file (multipart/form-data)
        print("  [2/3] Sending file...")
        boundary = "----NotionBannerUpload"
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Build multipart body
        body_parts = []
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
        )
        body_parts.append(b"Content-Type: image/png")
        body_parts.append(b"")
        body_parts.append(file_data)
        body_parts.append(f"--{boundary}--".encode())
        multipart_body = b"\r\n".join(body_parts)

        _notion_upload_request(
            "POST",
            f"/file_uploads/{upload_id}/send",
            raw_data=multipart_body,
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        print("  File sent.")

        # Step 3: Set as page cover
        print("  [3/3] Setting as page cover...")
        _notion_upload_request("PATCH", f"/pages/{page_id}", {
            "cover": {
                "type": "file_upload",
                "file_upload": {"id": upload_id},
            }
        })

        print(f"  Banner set as cover on page {page_id}")
        return True

    except Exception as e:
        print(f"Error uploading banner: {e}", file=sys.stderr)
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

    args = parser.parse_args()

    if args.command == "simple":
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
