#!/usr/bin/env bash
# install.sh: copy the guide-maker skills into a Claude Code project (or your user skills dir),
# fetch the topic-finder sibling skill if it is missing, and run the doctor.
#
# Usage:
#   ./install.sh /path/to/your/project        # installs into <project>/.claude/skills/
#   ./install.sh --global                     # installs into ~/.claude/skills/
#   ./install.sh /path/to/project --no-topic-finder
#
# Re-running is safe: files are overwritten, config.yaml is never touched.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOPIC_FINDER_REPO="https://github.com/josue-commits/topic-finder.git"
TOPIC_FINDER_REF="v2.0.0"
WITH_TOPIC_FINDER=1
TARGET=""

for arg in "$@"; do
  case "$arg" in
    --global) TARGET="$HOME/.claude/skills" ;;
    --no-topic-finder) WITH_TOPIC_FINDER=0 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) TARGET="$arg/.claude/skills" ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "usage: ./install.sh /path/to/project | --global   [--no-topic-finder]" >&2
  exit 2
fi

mkdir -p "$TARGET"
echo "Installing into $TARGET"

for skill in guide-maker graphics-maker dm-automation; do
  src="$HERE/skills/$skill"
  dst="$TARGET/$skill"
  if [[ ! -d "$src" ]]; then
    echo "  skip $skill (not in this checkout)"; continue
  fi
  mkdir -p "$dst"
  # rsync keeps an existing config.yaml; fall back to cp -R when rsync is missing
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude 'config.yaml' --exclude 'config.json' --exclude '__pycache__' --exclude 'format-usage-log.jsonl' "$src/" "$dst/"
  else
    (cd "$src" && find . -type d -exec mkdir -p "$dst/{}" \; )
    (cd "$src" && find . -type f ! -name 'config.yaml' ! -name 'config.json' ! -name '*.pyc' -exec cp "{}" "$dst/{}" \; )
  fi
  echo "  ok   $skill"
done

if [[ "$WITH_TOPIC_FINDER" == "1" ]]; then
  tf="$TARGET/topic-finder"
  if [[ -d "$tf/scripts" ]]; then
    echo "  keep topic-finder (already present at $tf)"
  elif [[ -d "$HERE/skills/topic-finder/scripts" ]]; then
    mkdir -p "$tf"
    cp -R "$HERE/skills/topic-finder/." "$tf/"
    echo "  ok   topic-finder (from this checkout)"
  elif command -v git >/dev/null 2>&1; then
    echo "  fetching topic-finder $TOPIC_FINDER_REF"
    if git clone --quiet --depth 1 --branch "$TOPIC_FINDER_REF" "$TOPIC_FINDER_REPO" "$tf" 2>/dev/null \
       || git clone --quiet --depth 1 "$TOPIC_FINDER_REPO" "$tf"; then
      rm -rf "$tf/.git"
      echo "  ok   topic-finder"
    else
      echo "  warn topic-finder clone failed; Phase 0 (topic research) will be disabled until you install it:"
      echo "       git clone $TOPIC_FINDER_REPO $tf"
    fi
  else
    echo "  warn git not found; install topic-finder by hand: $TOPIC_FINDER_REPO -> $tf"
  fi
fi

# never let a project commit the config with ids and keys
if [[ ! -f "$TARGET/guide-maker/.gitignore" ]]; then
  printf 'config.yaml\nconfig.json\n__pycache__/\n*.pyc\n' > "$TARGET/guide-maker/.gitignore"
fi
if [[ ! -f "$TARGET/graphics-maker/.gitignore" && -d "$TARGET/graphics-maker" ]]; then
  printf 'format-usage-log.jsonl\n__pycache__/\n*.pyc\n' > "$TARGET/graphics-maker/.gitignore"
fi

if [[ ! -f "$TARGET/guide-maker/config.yaml" ]]; then
  cp "$TARGET/guide-maker/config.example.yaml" "$TARGET/guide-maker/config.yaml"
  echo
  echo "Created $TARGET/guide-maker/config.yaml from the example. Fill in the REQUIRED block, then run:"
  echo "  python3 $TARGET/guide-maker/scripts/doctor.py"
else
  echo
  echo "Running doctor (offline checks):"
  python3 "$TARGET/guide-maker/scripts/doctor.py" --offline || true
fi

echo
echo "Done. Start Claude Code in your project and say: \"make a guide from this video: <url>\""
