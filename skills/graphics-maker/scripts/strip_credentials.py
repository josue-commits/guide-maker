#!/usr/bin/env python3
"""
Strip Content Credentials (C2PA) + all metadata from a generated graphic so
LinkedIn (and other platforms) do NOT put the "Content Credentials / Generated
by AI" badge on it when posted.

Why this is needed:
- gpt-image / nano-banana style outputs embed a signed C2PA manifest. In a PNG
  it lives in a `caBX` ancillary chunk; in a JPEG it lives in APP11/JUMBF
  markers.
- LinkedIn scans uploaded media for that manifest and flags it. Removing the
  manifest chunk removes the flag. The visible pixels are untouched.

How it works:
- Decode the pixels with Pillow and re-encode to a FRESH file. A plain re-save
  copies ONLY the image data (IHDR/IDAT/IEND for PNG) and drops every ancillary
  chunk, including `caBX`, iTXt/tEXt/zTXt, and eXIf. This is the programmatic
  version of the "canvas reset / flatten" trick.
- PNG is lossless, so the re-encoded pixels are identical to the approved image.
- Optional --nudge applies an imperceptible brightness multiply (0.996) as extra
  insurance against any pixel-hash soft-binding. Off by default so the output
  stays pixel-identical to what was approved.

Usage:
    strip_credentials.py INPUT [-o OUTPUT] [--nudge] [--jpeg-quality N]

If -o is omitted, writes alongside INPUT as "<stem>-clean<ext>".
Exits non-zero if any C2PA/metadata marker survives the strip (fail loud).
"""
import argparse
import os
import sys
from io import BytesIO

# ---- markers we refuse to let survive ----
PNG_META_CHUNKS = {b"caBX", b"iTXt", b"tEXt", b"zTXt", b"eXIf", b"iCCP"}
RAW_C2PA_MARKERS = (b"c2pa", b"jumbf", b"contentauth", b"c2pa.assertions", b"cai\x00")


def png_chunks(data: bytes):
    """Yield (type_bytes, length) for each PNG chunk. Empty if not a PNG."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return
    i = 8
    while i + 8 <= len(data):
        ln = int.from_bytes(data[i:i + 4], "big")
        typ = data[i + 4:i + 8]
        yield typ, ln
        i += 12 + ln
        if typ == b"IEND":
            break


def scan(data: bytes):
    """Return (list of metadata chunk types found, list of raw markers found)."""
    chunks = [t.decode("latin1", "replace") for t, _ in png_chunks(data)
              if t in PNG_META_CHUNKS]
    low = data.lower()
    raw = [m.decode("latin1", "replace") for m in RAW_C2PA_MARKERS if m in low]
    return chunks, raw


def strip(in_path: str, out_path: str, nudge: bool = False,
          jpeg_quality: int = 95) -> None:
    from PIL import Image, ImageEnhance

    with open(in_path, "rb") as f:
        before = f.read()
    b_chunks, b_raw = scan(before)
    print("[strip] %s: meta-chunks=%s raw=%s (%s bytes)"
          % (os.path.basename(in_path), b_chunks or "none", b_raw or "none",
             format(len(before), ",")))

    img = Image.open(in_path)
    img.load()  # realize pixels, detach from source file/metadata

    if nudge:
        # imperceptible brightness multiply: breaks exact/soft pixel hashes
        img = ImageEnhance.Brightness(img.convert(img.mode)).enhance(0.996)

    ext = os.path.splitext(out_path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        img = img.convert("RGB")
        save_kwargs = dict(format="JPEG", quality=jpeg_quality, optimize=True)
    else:
        # fresh PNG: no pnginfo, no exif -> ancillary chunks are dropped
        save_kwargs = dict(format="PNG", optimize=True)

    # Save via buffer first so we can verify BEFORE touching disk
    buf = BytesIO()
    img.save(buf, **save_kwargs)
    out = buf.getvalue()

    a_chunks, a_raw = scan(out)
    if a_chunks or a_raw:
        print("[strip] FAIL: residual metadata survived: chunks=%s raw=%s"
              % (a_chunks, a_raw), file=sys.stderr)
        sys.exit(2)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out)
    print("[strip] OK -> %s (%s bytes) | C2PA removed, pixels %s"
          % (out_path, format(len(out), ","), "nudged" if nudge else "identical"))


def main():
    ap = argparse.ArgumentParser(description="Strip C2PA/Content Credentials from an image.")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--nudge", action="store_true",
                    help="apply imperceptible brightness nudge (extra insurance)")
    ap.add_argument("--jpeg-quality", type=int, default=95)
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print("[strip] input not found: %s" % args.input, file=sys.stderr)
        sys.exit(1)

    out = args.output
    if out is None:
        stem, ext = os.path.splitext(args.input)
        out = "%s-clean%s" % (stem, ext)
    strip(args.input, out, nudge=args.nudge, jpeg_quality=args.jpeg_quality)
    print(out)


if __name__ == "__main__":
    main()
