#!/usr/bin/env bash
# Sync Claude's memory notes into knowledge/ in the Claude- repo, then commit
# and push only knowledge/ if anything changed. Run by a global Stop hook
# (~/.claude/settings.json) at the end of every Claude turn. Never blocks.
#
# - Updated notes overwrite their copy wherever it already sits in knowledge/.
# - New notes are filed by their frontmatter type:
#     user / feedback -> preferences/, project -> projects/, reference -> pc-setup/
# - Notes deleted from memory are deleted from knowledge/ too.
# - A note that looks like it holds a secret (API key / token) is skipped.

MEM="${CLAUDE_MEMORY_DIR:-$HOME/.claude/projects/D--Claude/memory}"
REPO="${KNOWLEDGE_REPO:-/d/Claude/Claude-}"
K="$REPO/knowledge"
SECRET_RE='(msy_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})'

[ -d "$MEM" ] && [ -d "$REPO/.git" ] || exit 0
mkdir -p "$K/preferences" "$K/projects" "$K/pc-setup" "$K/racing"
skipped=""

# Copy new and updated notes.
for src in "$MEM"/*.md; do
  name=$(basename "$src")
  [ "$name" = "MEMORY.md" ] && continue
  if grep -qE "$SECRET_RE" "$src"; then skipped="$skipped $name"; continue; fi
  dest=$(find "$K" -name "$name" -type f | head -1)
  if [ -z "$dest" ]; then
    type=$(sed -n 's/^ *type: *//p' "$src" | head -1 | tr -d '\r ')
    case "$type" in
      user|feedback) dest="$K/preferences/$name" ;;
      reference)     dest="$K/pc-setup/$name" ;;
      *)             dest="$K/projects/$name" ;;
    esac
  fi
  cmp -s "$src" "$dest" || cp "$src" "$dest"
done

# Remove notes that no longer exist in memory (global-CLAUDE.md and README stay).
find "$K" -name '*.md' -type f | while read -r f; do
  name=$(basename "$f")
  case "$name" in README.md|global-CLAUDE.md) continue ;; esac
  [ -f "$MEM/$name" ] || rm -f "$f"
done

# Global preferences file.
[ -f "$HOME/.claude/CLAUDE.md" ] && ! grep -qE "$SECRET_RE" "$HOME/.claude/CLAUDE.md" &&
  { cmp -s "$HOME/.claude/CLAUDE.md" "$K/preferences/global-CLAUDE.md" || cp "$HOME/.claude/CLAUDE.md" "$K/preferences/global-CLAUDE.md"; }

# Rebuild the index from MEMORY.md, pointing links at the knowledge/ paths.
{
cat <<'EOF'
# Knowledge base

Confirmed lessons and project facts from Nik's Claude sessions, kept in sync
automatically from Claude's memory notes (`~/.claude/projects/D--Claude/memory/`)
by `tools/sync-knowledge/sync_memory.sh` at the end of every Claude turn.
Each note is one fact or lesson; **Why** / **How to apply** lines explain it.
Project notes hold dated status — newest entries are at the top of each note.

- `preferences/` — how Nik wants work done (lessons learned the hard way), plus `global-CLAUDE.md`
- `projects/` — Setup Coach, Sunbeam, Escort DTM, Nova GTE, physics watchdog
- `pc-setup/` — PC quirks and tool installs (drive space, AppData redirect, Meshy, Tripo, Blender skills)
- `racing/` — Ratty's Racing championship and race server

Other confirmed write-ups in this repo: `tools/ac-wiper/` (wiper report + proven toolkit),
`docs/Blender_3D_Modelling_Guide.md`, `docs/reports/`.

## Index
EOF
while IFS= read -r line; do
  f=$(printf '%s' "$line" | sed -n 's/.*](\([^)]*\)).*/\1/p')
  [ -n "$f" ] || { printf '%s\n' "$line"; continue; }
  p=$(cd "$K" && find . -name "$f" -type f | head -1 | sed 's|^\./||')
  [ -n "$p" ] || continue
  printf '%s\n' "$line" | sed "s|]($f)|]($p)|"
done < "$MEM/MEMORY.md"
} | tr -d '\r' > "$K/README.md.new"
cmp -s "$K/README.md.new" "$K/README.md" && rm -f "$K/README.md.new" || mv -f "$K/README.md.new" "$K/README.md"

# Commit and push knowledge/ only.
cd "$REPO" || exit 0
git add -A -- knowledge >/dev/null 2>&1
msg=""
if ! git diff --cached --quiet -- knowledge; then
  git commit -q -m "Sync knowledge base from Claude memory" -- knowledge >/dev/null 2>&1
  git push -q origin HEAD >/dev/null 2>&1 || msg="Knowledge sync committed but could not push to GitHub. "
fi
[ -n "$skipped" ] && msg="${msg}Knowledge sync skipped (possible secret):$skipped"
[ -n "$msg" ] && printf '{"systemMessage": "%s"}\n' "$(printf '%s' "$msg" | sed 's/["\\]/\\&/g')"
exit 0
