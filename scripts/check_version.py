#!/usr/bin/env python3
"""Keep VERSION, CHANGELOG.md and the git tag in agreement.

    python3 scripts/check_version.py            print the version from VERSION
    python3 scripts/check_version.py --check    exit 1 unless VERSION equals the first
                                                "## x.y.z" heading in CHANGELOG.md and,
                                                when HEAD sits on a tag, that tag is "v" + VERSION

Stdlib only. Run from anywhere; paths resolve from this file.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEADING = re.compile(r"^## (\d+\.\d+\.\d+)\b", re.M)


def read_version():
    if not VERSION_FILE.exists():
        raise SystemExit(f"FAIL {VERSION_FILE.relative_to(ROOT)}: missing")
    version = VERSION_FILE.read_text().strip()
    if not SEMVER.match(version):
        raise SystemExit(f"FAIL VERSION: {version!r} is not x.y.z")
    return version


def changelog_version():
    if not CHANGELOG.exists():
        raise SystemExit(f"FAIL {CHANGELOG.relative_to(ROOT)}: missing")
    match = HEADING.search(CHANGELOG.read_text())
    if not match:
        raise SystemExit("FAIL CHANGELOG.md: no '## x.y.z' heading found")
    return match.group(1)


def tag_at_head():
    try:
        proc = subprocess.run(
            ["git", "describe", "--exact-match", "--tags"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def check():
    version = read_version()
    changelog = changelog_version()
    problems = []
    if changelog != version:
        problems.append(f"VERSION is {version} but the first CHANGELOG.md heading is {changelog}. "
                        "Retitle '## Unreleased' or bump VERSION.")
    tag = tag_at_head()
    if tag is not None and tag != f"v{version}":
        problems.append(f"HEAD is tagged {tag} but VERSION is {version}; the tag must be v{version}.")
    for line in problems:
        print(f"FAIL {line}", file=sys.stderr)
    if problems:
        return 1
    where = f", tag {tag}" if tag else ""
    print(f"OK VERSION {version} matches CHANGELOG.md{where}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="VERSION, CHANGELOG.md and git tag agreement")
    parser.add_argument("--check", action="store_true", help="verify and exit 1 on any mismatch")
    args = parser.parse_args(argv)
    if args.check:
        return check()
    print(read_version())
    return 0


if __name__ == "__main__":
    sys.exit(main())
