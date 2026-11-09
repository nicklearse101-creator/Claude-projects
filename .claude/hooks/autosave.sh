#!/usr/bin/env bash
# Auto-save: when Claude finishes a turn, commit any uncommitted work in this
# repository and push it to GitHub. Never blocks Claude: always exits 0.

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

branch=$(git symbolic-ref --short -q HEAD) || exit 0
msg=""

if [ -n "$(git status --porcelain)" ]; then
  git add -A

  # GitHub rejects files over 100 MB; leave anything that big out of the commit.
  skipped=""
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    if [ "$(wc -c <"$f")" -gt 95000000 ]; then
      git reset -q -- "$f"
      skipped="$skipped $f"
    fi
  done < <(git diff --cached --name-only)
  [ -n "$skipped" ] && msg="Auto-save skipped files too large for GitHub:$skipped. "

  if ! git diff --cached --quiet; then
    git commit -q -m "Auto-save $(date -u '+%Y-%m-%d %H:%M UTC')" >/dev/null 2>&1
  fi
fi

# Push anything not yet on GitHub (new auto-save commits or earlier ones).
if ! git rev-parse -q --verify '@{u}' >/dev/null 2>&1 ||
   [ -n "$(git log --oneline '@{u}..HEAD' 2>/dev/null)" ]; then
  if ! git push -q -u origin "$branch" >/dev/null 2>&1; then
    msg="${msg}Auto-save could not push to GitHub; work is committed locally."
  fi
fi

if [ -n "$msg" ]; then
  printf '{"systemMessage": "%s"}\n' "$(printf '%s' "$msg" | sed 's/["\\]/\\&/g')"
fi
exit 0
