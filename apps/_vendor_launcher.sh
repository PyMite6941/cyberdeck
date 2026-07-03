#!/usr/bin/env bash
# Shared launcher for apps whose real code lives in an external git repo
# (not vendored into this one) — e.g. security-suite. Source this at the top
# of the app's run.sh, then exec the app's own entry point afterward.
#
# Usage (from an app's run.sh):
#   . "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_vendor_launcher.sh"
#   vendor_sync "myapp" "https://github.com/user/repo.git" "$DIR/src" "$@"
#   exec "$DIR/src/run.sh" "$@"
#
# vendor_sync handles: clone-on-first-run into $SRC; on later runs, fetches
# origin and — if new commits exist and this is an interactive terminal —
# prints a one-line-per-commit summary and asks to update (fast-forward
# only, never touches local edits in $SRC). Non-interactive runs (no TTY)
# skip the check. The persistent `--check-updates=on/off` toggle lives in a
# ".check-updates" file next to $SRC and is handled here directly: passing
# either flag as an argument exits 0 without cloning/launching, so an app's
# run.sh should call vendor_sync before doing anything else.
#
# This is an apps/ convention only — the os/ layer is never updated this
# way; see AGENTS.md.

set -euo pipefail

vendor_sync() {
    local LABEL="$1" REPO_URL="$2" SRC="$3"
    shift 3
    local CONFIG
    CONFIG="$(dirname "$SRC")/.check-updates"

    case "${1:-}" in
        --check-updates=off)
            echo "off" > "$CONFIG"
            echo "$LABEL: update checks disabled."
            exit 0
            ;;
        --check-updates=on)
            echo "on" > "$CONFIG"
            echo "$LABEL: update checks enabled."
            exit 0
            ;;
    esac

    local updates_enabled=1
    [[ -f "$CONFIG" ]] && [[ "$(cat "$CONFIG")" == "off" ]] && updates_enabled=0

    if [[ ! -d "$SRC/.git" ]]; then
        echo "$LABEL: first run, cloning $REPO_URL ..."
        git clone --quiet "$REPO_URL" "$SRC"
    elif [[ $updates_enabled -eq 1 ]] && [[ -t 0 ]]; then
        git -C "$SRC" fetch --quiet origin
        local branch local_rev remote_rev
        branch="$(git -C "$SRC" symbolic-ref --short HEAD)"
        local_rev="$(git -C "$SRC" rev-parse HEAD)"
        remote_rev="$(git -C "$SRC" rev-parse "origin/$branch")"
        if [[ "$local_rev" != "$remote_rev" ]]; then
            local count
            count="$(git -C "$SRC" rev-list --count "$local_rev..$remote_rev")"
            echo "$LABEL: $count update(s) available:"
            git -C "$SRC" log --oneline "$local_rev..$remote_rev"
            local ans
            read -rp "Update now? [y/N] " ans
            if [[ "$ans" =~ ^[Yy]$ ]]; then
                if git -C "$SRC" merge --ff-only --quiet "$remote_rev"; then
                    echo "$LABEL: updated to $(git -C "$SRC" rev-parse --short HEAD)."
                else
                    echo "$LABEL: fast-forward failed (local changes in src/?) — skipping update." >&2
                fi
            else
                echo "$LABEL: skipping update. Run './run.sh --check-updates=off' to stop asking."
            fi
        fi
    fi
}
