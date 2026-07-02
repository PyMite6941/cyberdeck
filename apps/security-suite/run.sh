#!/usr/bin/env bash
# security-suite — encrypted vault app (self-updating launcher).
#
# This folder is a thin launcher, not the app itself: first run clones
# PyMite6941/Security-Suite into src/, every later run checks upstream for
# new commits and offers to pull them before launching. src/ is gitignored —
# it's a live clone the deck manages, not vendored code in this repo.
#
# Usage:
#   ./run.sh                     run the app (checks for updates first)
#   ./run.sh --check-updates=off stop asking about updates (still auto-skips)
#   ./run.sh --check-updates=on  resume asking about updates
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="https://github.com/PyMite6941/Security-Suite.git"
SRC="$DIR/src"
CONFIG="$DIR/.check-updates"

case "${1:-}" in
    --check-updates=off)
        echo "off" > "$CONFIG"
        echo "security-suite: update checks disabled."
        exit 0
        ;;
    --check-updates=on)
        echo "on" > "$CONFIG"
        echo "security-suite: update checks enabled."
        exit 0
        ;;
esac

updates_enabled() {
    [[ ! -f "$CONFIG" ]] || [[ "$(cat "$CONFIG")" != "off" ]]
}

if [[ ! -d "$SRC/.git" ]]; then
    echo "security-suite: first run, cloning $REPO_URL ..."
    git clone --quiet "$REPO_URL" "$SRC"
elif updates_enabled && [[ -t 0 ]]; then
    git -C "$SRC" fetch --quiet origin
    BRANCH="$(git -C "$SRC" symbolic-ref --short HEAD)"
    LOCAL="$(git -C "$SRC" rev-parse HEAD)"
    REMOTE="$(git -C "$SRC" rev-parse "origin/$BRANCH")"
    if [[ "$LOCAL" != "$REMOTE" ]]; then
        COUNT="$(git -C "$SRC" rev-list --count "$LOCAL..$REMOTE")"
        echo "security-suite: $COUNT update(s) available:"
        git -C "$SRC" log --oneline "$LOCAL..$REMOTE"
        read -rp "Update now? [y/N] " ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            if git -C "$SRC" merge --ff-only --quiet "$REMOTE"; then
                echo "security-suite: updated to $(git -C "$SRC" rev-parse --short HEAD)."
            else
                echo "security-suite: fast-forward failed (local changes in src/?) — skipping update." >&2
            fi
        else
            echo "security-suite: skipping update. Run './run.sh --check-updates=off' to stop asking."
        fi
    fi
fi

exec "$SRC/run.sh" "$@"
