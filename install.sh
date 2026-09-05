#!/usr/bin/env bash
# install.sh: the no-Node route. Copies every skill under skills/ (make-guide,
# topic-finder, graphics-maker, dm-automation, setup-guide-maker, ask-guide-maker)
# into a Claude Code project, or your user skills dir, then runs the doctor.
#
# Usage:
#   ./install.sh /path/to/your/project        # installs into <project>/.claude/skills/
#   ./install.sh --global                     # installs into ~/.claude/skills/
#
# Re-running is safe: skill files are overwritten, a config.yaml that still
# sits inside a skill folder (the v2 location) is never touched.
#
# The config does not live in the skill folder any more. After installing, run
# /setup-guide-maker in Claude Code, or `doctor.py --init`, to create
# <project>/.guide-maker/ (config, topic sources, overrides, state).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET=""
PROJECT=""

for arg in "$@"; do
  case "$arg" in
    --global) TARGET="$HOME/.claude/skills" ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    --*) echo "unknown flag: $arg" >&2; exit 2 ;;
    *) PROJECT="$arg"; TARGET="$arg/.claude/skills" ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "usage: ./install.sh /path/to/project | --global" >&2
  exit 2
fi

mkdir -p "$TARGET"
echo "Installing into $TARGET"

installed=0
for src in "$HERE"/skills/*/; do
  skill="$(basename "$src")"
  [[ -f "$src/SKILL.md" ]] || continue
  dst="$TARGET/$skill"
  mkdir -p "$dst"
  # rsync keeps a v2-era config.yaml and usage log inside the skill folder; cp -R fallback when rsync is missing
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude 'config.yaml' --exclude 'config.json' --exclude '__pycache__' \
      --exclude 'format-usage-log.jsonl' --exclude '.git' "$src" "$dst/"
  else
    (cd "$src" && find . -type d ! -path './.git*' -exec mkdir -p "$dst/{}" \; )
    (cd "$src" && find . -type f ! -path './.git*' ! -name 'config.yaml' ! -name 'config.json' \
      ! -name '*.pyc' ! -name 'format-usage-log.jsonl' -exec cp "{}" "$dst/{}" \; )
  fi
  echo "  ok   $skill"
  installed=$((installed + 1))
done

if [[ "$installed" -eq 0 ]]; then
  echo "no skills found under $HERE/skills; is this a full checkout?" >&2
  exit 1
fi

DOCTOR="$TARGET/make-guide/scripts/doctor.py"
echo
if [[ -f "$TARGET/make-guide/config.yaml" || -f "$TARGET/make-guide/config.json" ]]; then
  echo "A v2 config still sits inside $TARGET/make-guide/. It keeps loading with a deprecation"
  echo "line; move it with:"
  echo "  python3 $DOCTOR --init --from $TARGET/make-guide/config.yaml"
elif [[ -n "$PROJECT" && -f "$PROJECT/.guide-maker/config.yaml" ]]; then
  echo "Project config found at $PROJECT/.guide-maker/config.yaml"
else
  echo "No config yet. In Claude Code run /setup-guide-maker, or from a terminal:"
  if [[ -n "$PROJECT" ]]; then
    echo "  python3 $DOCTOR --init --project $PROJECT"
  else
    echo "  python3 $DOCTOR --init --project /path/to/your/project"
  fi
fi

echo
echo "Running doctor (offline checks):"
if [[ -n "$PROJECT" ]]; then
  (cd "$PROJECT" && python3 "$DOCTOR" --offline) || true
else
  python3 "$DOCTOR" --offline || true
fi

echo
echo "Done. Start Claude Code in your project and say: \"make a guide from this video: <url>\""
