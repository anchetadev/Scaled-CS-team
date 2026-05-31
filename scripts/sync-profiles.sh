#!/bin/bash
# sync-profiles.sh — Sync repo-controlled files into live Hermes profiles.
#
# Source of truth: <repo>/agents/<name>/
# Target:          ~/.hermes/profiles/<name>/
#
# Synced (one-way, repo → live):
#   SOUL.md, README.md, and EACH SPECIFIC custom skill directory present in
#   the repo at agents/<name>/skills/<category>/<skill>/. Sync is per-skill
#   with --delete so removals within a custom skill propagate; the parent
#   skills/ and skills/<category>/ are never touched as a whole, so the
#   Hermes skill-hub overlay (apple/, creative/, yuanbao/, .hub/, etc.) is
#   left intact.
#
# Never touched (runtime-owned):
#   config.yaml, config.yaml.bak.*, .env, *.db, sessions/, memories/,
#   cache/, auth.*, gateway.{pid,lock}, gateway_state.json, logs/,
#   sandboxes/, plugins/, pairing/, channel_directory.json, kanban.db,
#   ssh-fix-notes.md, node/, bin/, slack-manifest.json, the global skills
#   hub state (.hub/, .bundled_manifest, .curator_state, .usage.json*).
#
# Usage:
#   ./scripts/sync-profiles.sh                     # sync installed profiles
#   ./scripts/sync-profiles.sh --install-missing   # also bootstrap missing workers
#   ./scripts/sync-profiles.sh --dry-run           # preview only, change nothing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
AGENTS_DIR="$REPO_DIR/agents"
PROFILES_DIR="$HOME/.hermes/profiles"

DRY_RUN=0
INSTALL_MISSING=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --install-missing) INSTALL_MISSING=1 ;;
        --help|-h)
            sed -n '2,26p' "$0" | sed 's/^# //; s/^#//'
            exit 0 ;;
        *) echo "Unknown flag: $arg" >&2; exit 2 ;;
    esac
done

RSYNC_DRY=""
[ "$DRY_RUN" = "1" ] && RSYNC_DRY="--dry-run"

if [ ! -d "$AGENTS_DIR" ]; then
    echo "❌ Repo agents/ directory not found: $AGENTS_DIR" >&2
    exit 1
fi

CHANGED_PROFILES=()
INSTALLED_PROFILES=()
SKIPPED_PROFILES=()

echo "Repo:    $REPO_DIR"
echo "Live:    $PROFILES_DIR"
[ "$DRY_RUN" = "1" ] && echo "Mode:    DRY RUN (no changes will be written)"
echo

# Helper: run rsync, return non-empty change indicator on stdout if anything differs.
# Uses -ai (itemize) + --no-times not set so byte-identical files don't show as changes.
sync_path() {
    local src="$1"  # file or dir; dir paths MUST end with /
    local dst="$2"
    local with_delete="${3:-0}"
    local rsync_args=(-aic)
    [ "$with_delete" = "1" ] && rsync_args+=(--delete)
    [ -n "$RSYNC_DRY" ] && rsync_args+=("$RSYNC_DRY")
    rsync "${rsync_args[@]}" "$src" "$dst" 2>&1 || true
}

# Helper: detect whether rsync output reports any actual change.
# rsync -ai prints lines starting with [<>ch.*] for changes or "*deleting" for deletions.
# A no-op produces no output (or just info lines we filter out).
has_changes() {
    local out="$1"
    echo "$out" | grep -qE '^[<>ch*]|deleting' || return 1
    return 0
}

for agent_dir in "$AGENTS_DIR"/*/; do
    agent=$(basename "$agent_dir")
    live_dir="$PROFILES_DIR/$agent"

    if [ ! -d "$live_dir" ]; then
        if [ "$INSTALL_MISSING" = "1" ]; then
            echo "→ $agent: NOT INSTALLED — bootstrapping"
            if [ "$DRY_RUN" = "0" ]; then
                if ! command -v hermes >/dev/null 2>&1; then
                    echo "  ❌ hermes binary not found in PATH; cannot install" >&2
                    SKIPPED_PROFILES+=("$agent")
                    continue
                fi
                hermes profile install "$agent_dir" --name "$agent" --alias \
                  || { echo "  ⚠️  install failed for $agent"; SKIPPED_PROFILES+=("$agent"); continue; }
                INSTALLED_PROFILES+=("$agent")
                CHANGED_PROFILES+=("$agent")
            else
                echo "  (dry-run: would install)"
            fi
        else
            echo "  $agent: not installed (skip — pass --install-missing to bootstrap)"
            SKIPPED_PROFILES+=("$agent")
        fi
        continue
    fi

    profile_changed=0
    profile_log=""

    # 1. SOUL.md
    if [ -f "$agent_dir/SOUL.md" ]; then
        out=$(sync_path "$agent_dir/SOUL.md" "$live_dir/SOUL.md" 0)
        if has_changes "$out"; then
            profile_changed=1
            profile_log+="    SOUL.md\n"
        fi
    fi

    # 2. README.md
    if [ -f "$agent_dir/README.md" ]; then
        out=$(sync_path "$agent_dir/README.md" "$live_dir/README.md" 0)
        if has_changes "$out"; then
            profile_changed=1
            profile_log+="    README.md\n"
        fi
    fi

    # 3. Custom skills — walk repo's skills/<category>/<skill>/ and sync each one
    #    individually with --delete (so removals WITHIN a custom skill propagate).
    #    NEVER touches skills/, skills/<category>/, or any sibling dir not in the repo.
    if [ -d "$agent_dir/skills" ]; then
        while IFS= read -r -d '' skill_md; do
            skill_dir=$(dirname "$skill_md")
            rel="${skill_dir#$agent_dir/skills/}"
            dst_skill_dir="$live_dir/skills/$rel"
            mkdir -p "$(dirname "$dst_skill_dir")"
            out=$(sync_path "$skill_dir/" "$dst_skill_dir/" 1)
            if has_changes "$out"; then
                profile_changed=1
                profile_log+="    skills/$rel/\n"
                # Show specifics under each changed skill for clarity
                while IFS= read -r line; do
                    [ -z "$line" ] && continue
                    profile_log+="        $line\n"
                done < <(echo "$out" | grep -E '^[<>ch*]|deleting' || true)
            fi
        done < <(find "$agent_dir/skills" -name SKILL.md -print0 2>/dev/null)
    fi

    if [ "$profile_changed" = "1" ]; then
        echo "→ $agent: CHANGES"
        printf "%b" "$profile_log"
        CHANGED_PROFILES+=("$agent")
    else
        echo "  $agent: in sync"
    fi
done

echo
echo "═══════════════════════════════════════════════════════════"
if [ "$DRY_RUN" = "1" ]; then
    if [ ${#CHANGED_PROFILES[@]} -eq 0 ]; then
        echo "DRY RUN: all profiles in sync, nothing to do"
    else
        echo "DRY RUN: ${#CHANGED_PROFILES[@]} profile(s) WOULD change: ${CHANGED_PROFILES[*]}"
    fi
elif [ ${#CHANGED_PROFILES[@]} -eq 0 ]; then
    echo "✓ All installed profiles in sync — nothing to do."
else
    echo "Profiles updated — restart each to load changes:"
    for p in "${CHANGED_PROFILES[@]}"; do
        unit="hermes-gateway-${p}.service"
        if systemctl --user list-unit-files 2>/dev/null | grep -q "^${unit}"; then
            echo "  → systemctl --user restart $unit"
        else
            echo "  → $p: no systemd unit found; restart however $p was launched"
        fi
    done
fi
[ ${#SKIPPED_PROFILES[@]} -gt 0 ] && echo "Skipped (not installed): ${SKIPPED_PROFILES[*]}"
[ ${#INSTALLED_PROFILES[@]} -gt 0 ] && echo "Newly installed: ${INSTALLED_PROFILES[*]}"
echo "═══════════════════════════════════════════════════════════"
