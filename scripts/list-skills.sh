#!/usr/bin/env bash
# list-skills.sh: print every skill in this checkout, one per line, from its SKILL.md.
#
# Usage:
#   scripts/list-skills.sh            # name, invocation, first sentence of the description
#   scripts/list-skills.sh --names    # names only (for scripts and CI)
#   scripts/list-skills.sh --paths    # SKILL.md paths only
#
# A skill is any SKILL.md up to three levels under skills/ (the same rule the
# `npx skills` CLI uses). Invocation is "user" when the frontmatter has
# `disable-model-invocation: true`, else "model".

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-table}"

case "$MODE" in
  --names|--paths|table) ;;
  -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
  *) echo "usage: scripts/list-skills.sh [--names | --paths]" >&2; exit 2 ;;
esac

found=0
while IFS= read -r skill_md; do
  found=$((found + 1))
  dir="$(dirname "$skill_md")"
  # frontmatter: between the first two --- lines
  fm="$(awk 'NR==1 && $0=="---" {infm=1; next} infm && $0=="---" {exit} infm {print}' "$skill_md")"
  name="$(printf '%s\n' "$fm" | sed -n 's/^name:[[:space:]]*//p' | head -1 | tr -d '"'"'"'')"
  [[ -n "$name" ]] || name="$(basename "$dir")"
  if printf '%s\n' "$fm" | grep -qE '^disable-model-invocation:[[:space:]]*true'; then
    invocation="user"
  else
    invocation="model"
  fi
  desc="$(printf '%s\n' "$fm" | sed -n 's/^description:[[:space:]]*//p' | head -1 | sed -E 's/^"//; s/"$//; s/\. .*$/./')"
  case "$MODE" in
    --names) echo "$name" ;;
    --paths) echo "${skill_md#$HERE/}" ;;
    table) printf '%-20s %-6s %s\n' "$name" "$invocation" "$desc" ;;
  esac
done < <(find "$HERE/skills" -mindepth 2 -maxdepth 4 -name SKILL.md -not -path '*/node_modules/*' | sort)

if [[ "$found" -eq 0 ]]; then
  echo "no SKILL.md found under $HERE/skills" >&2
  exit 1
fi
