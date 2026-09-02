#!/usr/bin/env python3
"""
Add a reference image to the format library.

Local-first: the image is copied to references/format-library/<slug>.png, a
stub card <slug>.md is written from references/format-library/_TEMPLATE.md,
and a row is appended to INDEX.md. Nothing leaves your machine.

--upload additionally publishes the image to a public URL and records it in
the card's frontmatter. Only needed when your provider fetches references by
URL (graphics.provider = kieai). OpenAI reads the local file.

Only ingest images you have the right to reuse: your own past graphics, or
layouts you built yourself. A reference taken from someone else's post
carries their name, wordmark and headshot into your output; see the
failure-modes table in SKILL.md.

Usage:
    python3 ingest_reference.py /abs/path/image.png [--slug my-format] [--upload]
    python3 ingest_reference.py /abs/path/folder/ [--upload]
"""
import argparse
import os
import re
import shutil
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
LIBRARY_DIR = os.path.join(SKILL_DIR, "references", "format-library")
INDEX_PATH = os.path.join(LIBRARY_DIR, "INDEX.md")
TEMPLATE_PATH = os.path.join(LIBRARY_DIR, "_TEMPLATE.md")

sys.path.insert(0, SCRIPT_DIR)
from _cfg import load_config, cfg_get  # noqa: E402

TABLE_MARKER = "<!-- ingest: new rows go above this line -->"


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    if not s:
        raise ValueError("Could not derive a slug from %r; pass --slug" % name)
    return s


def title_from_slug(slug):
    return " ".join(w.capitalize() for w in slug.split("-"))


def render_stub(slug, public_url):
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, encoding="utf-8") as f:
            body = f.read()
    else:
        body = "---\nname: {slug}\n---\n\n# {title}\n"
    return (body.replace("{slug}", slug)
                .replace("{title}", title_from_slug(slug))
                .replace("{public_url}", public_url or "")
                .replace("{today}", date.today().isoformat()))


def append_to_index(slug, note="pending review"):
    if not os.path.exists(INDEX_PATH):
        print("Warning: %s not found, index not updated" % INDEX_PATH, file=sys.stderr)
        return
    with open(INDEX_PATH, encoding="utf-8") as f:
        content = f.read()
    row = "| [%s](%s.md) | %s | %s |" % (slug, slug, "pending", note)
    if TABLE_MARKER in content:
        content = content.replace(TABLE_MARKER, row + "\n" + TABLE_MARKER, 1)
    else:
        content = content.rstrip() + "\n" + row + "\n"
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def ingest_one(image_path, slug=None, upload=False, endpoint=None):
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    slug = slug or slugify(os.path.splitext(os.path.basename(image_path))[0])
    target_png = os.path.join(LIBRARY_DIR, slug + ".png")
    target_md = os.path.join(LIBRARY_DIR, slug + ".md")
    if os.path.exists(target_png) or os.path.exists(target_md):
        raise FileExistsError("%s already exists in the library; pass --slug to rename" % slug)

    os.makedirs(LIBRARY_DIR, exist_ok=True)
    shutil.copy2(image_path, target_png)

    public_url = ""
    if upload:
        from _upload import upload_public
        print("  Uploading %s.png ..." % slug, end=" ", flush=True)
        public_url = upload_public(target_png, endpoint=endpoint)
        print(public_url)

    with open(target_md, "w", encoding="utf-8") as f:
        f.write(render_stub(slug, public_url))
    append_to_index(slug)
    return slug, public_url, target_md


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="Image file or folder of images (absolute path)")
    ap.add_argument("--slug", help="Custom slug (single file only)")
    ap.add_argument("--upload", action="store_true",
                    help="Also publish to a public URL (needed for URL-based providers such as kieai)")
    ap.add_argument("--config", default=None, help="Config file (default: auto-discover)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    endpoint = cfg_get(cfg, "graphics.upload_endpoint", "") or None

    if os.path.isdir(args.path):
        if args.slug:
            print("--slug only works with a single file", file=sys.stderr)
            sys.exit(1)
        files = sorted(f for f in os.listdir(args.path)
                       if f.lower().endswith((".png", ".jpg", ".jpeg")))
        if not files:
            print("No images found in %s" % args.path, file=sys.stderr)
            sys.exit(1)
        ok = 0
        for fname in files:
            print("-> " + fname)
            try:
                ingest_one(os.path.join(args.path, fname), upload=args.upload, endpoint=endpoint)
                ok += 1
            except (FileExistsError, FileNotFoundError, ValueError, RuntimeError) as e:
                print("   failed: %s" % e, file=sys.stderr)
        print("\nIngested %d of %d. Next: open each stub card, look at ITS image, and fill the "
              "card from that one image before moving to the next." % (ok, len(files)))
        sys.exit(0 if ok == len(files) else 1)

    try:
        slug, url, md_path = ingest_one(args.path, slug=args.slug, upload=args.upload, endpoint=endpoint)
    except (FileExistsError, FileNotFoundError, ValueError, RuntimeError) as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)
    print("\nIngested %s" % slug)
    if url:
        print("  Public URL: %s" % url)
    print("  Stub card:  %s" % md_path)
    print("\nNext: open the stub, look at the image, and fill in the card sections.")


if __name__ == "__main__":
    main()
