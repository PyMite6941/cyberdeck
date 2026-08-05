#!/usr/bin/env bash
# Shared machinery for apps whose real code lives in an external git repo
# (not vendored into this one) — e.g. security-suite, grimoire.
#
# Two scripts per vendored app, both sourcing this file:
#
#   install.sh  — bootstrap/updater. Clones the repo into src/ on first run;
#                 on later runs checks for updates and (interactively) offers
#                 to fast-forward. Also builds a PRIVATE .venv inside src/ and
#                 installs requirements, and wipes caches after an update.
#   run.sh      — launcher. Ensures installed, then execs the app's own entry
#                 point using that private venv.
#
# install.sh:
#   . "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_vendor_launcher.sh"
#   vendor_sync "grimoire" "https://github.com/PyMite6941/grimoire.git" "$DIR/src" "$@"
#
# run.sh:
#   case "${1:-}" in --check-updates=*) exec "$DIR/install.sh" "$@" ;; esac
#   "$DIR/install.sh"                          # clone if needed + update check
#   exec "$(vendor_python "$DIR/src")" "$DIR/src/run.py" "$@"
#
# vendor_sync handles: clone-on-first-run into $SRC; private venv + requirements;
# on later runs, fetch origin and — if new commits exist and this is an
# interactive terminal — print a one-line-per-commit summary and offer to
# update (fast-forward only, never touching local edits in $SRC). After a
# successful update it wipes caches (see "Cache cleaning" below) and re-syncs
# the venv. Non-interactive runs (no TTY) skip the update check.
#
# The persistent "--check-updates=on/off" toggle lives in a ".check-updates"
# file next to $SRC. Passing either flag exits 0 without cloning/launching.
#
# Cache cleaning: after every successful update pull, __pycache__ dirs and
# *.pyc files under $SRC are removed. To also wipe app-specific caches, drop a
# ".update-clean" file next to $SRC listing extra glob patterns (relative to
# $SRC), one per line ("#" comments allowed) — e.g. "backend/data/*.tmp".
#
# This is an apps/ convention only — the os/ layer is never updated this way;
# see AGENTS.md.

set -euo pipefail

# --- venv helpers ----------------------------------------------------------

# Echo the path to a repo's private venv python (may not exist yet).
vendor_python() {
    local SRC="$1"
    if [[ -x "$SRC/.venv/bin/python" ]]; then
        echo "$SRC/.venv/bin/python"
    elif [[ -x "$SRC/.venv/Scripts/python" ]]; then
        echo "$SRC/.venv/Scripts/python"
    elif command -v python3 &>/dev/null; then
        echo "python3"
    else
        echo "python"
    fi
}

# Create the private venv (if missing) and install requirements.txt.
_vendor_setup_venv() {
    local LABEL="$1" SRC="$2"
    local base_python
    if command -v python3 &>/dev/null; then base_python=python3; else base_python=python; fi
    if [[ ! -d "$SRC/.venv" ]]; then
        echo "$LABEL: creating private virtualenv ..."
        "$base_python" -m venv "$SRC/.venv"
    fi
    local py; py="$(vendor_python "$SRC")"
    if [[ -f "$SRC/requirements.txt" ]]; then
        echo "$LABEL: installing requirements into private venv ..."
        "$py" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
        "$py" -m pip install --quiet -r "$SRC/requirements.txt"
    fi
}

# --- cache cleaning --------------------------------------------------------

_vendor_clean_caches() {
    local LABEL="$1" SRC="$2"
    echo "$LABEL: clearing caches ..."
    # Always: Python bytecode caches.
    find "$SRC" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
    find "$SRC" -type f -name '*.pyc' -delete 2>/dev/null || true
    # Extra, app-declared globs from .update-clean (next to src/).
    local cfg; cfg="$(dirname "$SRC")/.update-clean"
    if [[ -f "$cfg" ]]; then
        local pattern
        while IFS= read -r pattern; do
            pattern="${pattern%%#*}"; pattern="${pattern#"${pattern%%[![:space:]]*}"}"; pattern="${pattern%"${pattern##*[![:space:]]}"}"
            [[ -z "$pattern" ]] && continue
            # shellcheck disable=SC2086
            ( cd "$SRC" && rm -rf $pattern ) 2>/dev/null || true
        done < "$cfg"
    fi
}

# --- main sync -------------------------------------------------------------

vendor_sync() {
    local LABEL="$1" REPO_URL="$2" SRC="$3"
    shift 3
    local CONFIG
    CONFIG="$(dirname "$SRC")/.check-updates"

    case "${1:-}" in
        --check-updates=off)
            echo "off" > "$CONFIG"
            echo "$LABEL: update checks disabled."
            return 0
            ;;
        --check-updates=on)
            echo "on" > "$CONFIG"
            echo "$LABEL: update checks enabled."
            return 0
            ;;
    esac

    local updates_enabled=1
    [[ -f "$CONFIG" ]] && [[ "$(cat "$CONFIG")" == "off" ]] && updates_enabled=0

    if [[ ! -d "$SRC/.git" ]]; then
        echo "$LABEL: first run, cloning $REPO_URL ..."
        git clone --quiet "$REPO_URL" "$SRC"
        _vendor_setup_venv "$LABEL" "$SRC"
        return 0
    fi

    if [[ $updates_enabled -eq 1 ]] && [[ -t 0 ]]; then
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
                    _vendor_clean_caches "$LABEL" "$SRC"
                    _vendor_setup_venv "$LABEL" "$SRC"
                else
                    echo "$LABEL: fast-forward failed (local changes in src/?) — skipping update." >&2
                fi
            else
                echo "$LABEL: skipping update. Run './run.sh --check-updates=off' to stop asking."
            fi
        fi
    fi

    # Safety net: if the venv went missing, rebuild it.
    [[ -d "$SRC/.venv" ]] || _vendor_setup_venv "$LABEL" "$SRC"
    return 0
}
