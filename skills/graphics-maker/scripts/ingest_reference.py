#!/usr/bin/env python3
"""
Add a reference image to your format library.

Local-first: the image is copied to <project>/.guide-maker/formats/<slug>.png,
a stub card <slug>.md is written there from the shipped
references/format-library/_TEMPLATE.md, and a row is appended to
<project>/.guide-maker/formats/INDEX.md (created from a small template the
first time). Nothing leaves your machine, and nothing is written inside the
skill folder: the shipped catalog under references/format-library/ is read
only. <project> is the folder that holds .guide-maker/ (the config's own
project, else the first ancestor of the working directory with one).

--upload additionally publishes the image to a public URL and records it in
the card's frontmatter. Only needed when your provider fetches references by
URL (graphics.provider = kieai). OpenAI reads the local file.

--dry-run prints every path that would be written and exits.

Only ingest images you have the right to reuse: your own past graphics, or
layouts you built yourself. A reference taken from someone else's post
carries their name, wordmark and headshot into your output; see the
failure-modes table in SKILL.md.

Usage:
    python3 ingest_reference.py /abs/path/image.png [--slug my-format] [--upload] [--dry-run]
    python3 ingest_reference.py /abs/path/folder/ [--upload] [--dry-run]
"""
import argparse
import os
import re
import shutil
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SHIPPED_LIBRARY_DIR = os.path.join(SKILL_DIR, "references", "format-library")
TEMPLATE_PATH = os.path.join(SHIPPED_LIBRARY_DIR, "_TEMPLATE.md")

sys.path.insert(0, SCRIPT_DIR)
from _cfg import load_config, cfg_get, project_file  # noqa: E402

TABLE_MARKER = "<!-- ingest: new rows go above this line -->"

INDEX_TEMPLATE = """# Your format library

Format cards you ingested with `ingest_reference.py`. The shipped catalog and
the decision tree by guide type live in the graphics-maker skill at
`references/format-library/INDEX.md`; this file is yours and survives skill
updates. Open each stub card, look at its image, and fill the card from that
one image before moving to the next.

## Catalog

| Slug | Cost | Bg | When to use |
|---|---|---|---|
""" + TABLE_MARKER + "\n"


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    if not s:
        raise ValueError("Could not derive a slug from %r; pass --slug" % name)
    return s


def title_from_slug(slug):
    return " ".join(w.capitalize() for w in slug.split("-"))


def library_dir(cfg):
    """<project>/.guide-maker/formats, the only place this script writes."""
    return str(project_file("formats", cfg))


def render_stub(slug, public_url, local_path):
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, encoding="utf-8") as f:
            body = f.read()
    else:
        body = "---\nname: {slug}\nlocal_path: {local_path}\n---\n\n# {title}\n"
    return (body.replace("{slug}", slug)
                .replace("{title}", title_from_slug(slug))
                .replace("{public_url}", public_url or "")
                .replace("{local_path}", local_path)
                .replace("{today}", date.today().isoformat()))


def append_to_index(index_path, slug, note="pending review"):
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            content = f.read()
    else:
        content = INDEX_TEMPLATE
    row = "| [%s](%s.md) | %s | %s |" % (slug, slug, "pending", note)
    if TABLE_MARKER in content:
        content = content.replace(TABLE_MARKER, row + "\n" + TABLE_MARKER, 1)
    else:
        content = content.rstrip() + "\n" + row + "\n"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


def ingest_one(image_path, lib_dir, slug=None, upload=False, endpoint=None, dry_run=False):
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    slug = slug or slugify(os.path.splitext(os.path.basename(image_path))[0])
    target_png = os.path.join(lib_dir, slug + ".png")
    target_md = os.path.join(lib_dir, slug + ".md")
    index_path = os.path.join(lib_dir, "INDEX.md")
    if os.path.exists(target_png) or os.path.exists(target_md):
        raise FileExistsError("%s already exists in %s; pass --slug to rename" % (slug, lib_dir))

    if dry_run:
        print("  would copy   %s -> %s" % (image_path, target_png))
        print("  would write  %s" % target_md)
        print("  would %s %s" % ("append to" if os.path.exists(index_path) else "create", index_path))
        if upload:
            print("  would upload %s to %s" % (target_png, endpoint or "the default public host"))
        return slug, "", target_md

    os.makedirs(lib_dir, exist_ok=True)
    shutil.copy2(image_path, target_png)

    public_url = ""
    if upload:
        from _upload import upload_public
        print("  Uploading %s.png ..." % slug, end=" ", flush=True)
        public_url = upload_public(target_png, endpoint=endpoint)
        print(public_url)

    with open(target_md, "w", encoding="utf-8") as f:
        f.write(render_stub(slug, public_url, target_png))
    append_to_index(index_path, slug)
    return slug, public_url, target_md


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="Image file or folder of images (absolute path)")
    ap.add_argument("--slug", help="Custom slug (single file only)")
    ap.add_argument("--upload", action="store_true",
                    help="Also publish to a public URL (needed for URL-based providers such as kieai)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be written and exit")
    ap.add_argument("--config", default=None, help="Config file (default: auto-discover)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    endpoint = cfg_get(cfg, "graphics.upload_endpoint", "") or None
    lib_dir = library_dir(cfg)
    print("Library: %s" % lib_dir)

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
                ingest_one(os.path.join(args.path, fname), lib_dir, upload=args.upload,
                           endpoint=endpoint, dry_run=args.dry_run)
                ok += 1
            except (FileExistsError, FileNotFoundError, ValueError, RuntimeError) as e:
                print("   failed: %s" % e, file=sys.stderr)
        if args.dry_run:
            print("\nDry run: %d of %d would be ingested." % (ok, len(files)))
        else:
            print("\nIngested %d of %d. Next: open each stub card, look at ITS image, and fill the "
                  "card from that one image before moving to the next." % (ok, len(files)))
        sys.exit(0 if ok == len(files) else 1)

    try:
        slug, url, md_path = ingest_one(args.path, lib_dir, slug=args.slug, upload=args.upload,
                                        endpoint=endpoint, dry_run=args.dry_run)
    except (FileExistsError, FileNotFoundError, ValueError, RuntimeError) as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)
    if args.dry_run:
        print("\nDry run: nothing written.")
        return
    print("\nIngested %s" % slug)
    if url:
        print("  Public URL: %s" % url)
    print("  Stub card:  %s" % md_path)
    print("\nNext: open the stub, look at the image, and fill in the card sections.")


if __name__ == "__main__":
    main()
