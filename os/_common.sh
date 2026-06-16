#!/usr/bin/env bash
# Shared preamble for os/ setup scripts.
# Source at the top of each script, then use require_root and detect_user.
#
# Usage:
#   source "$(dirname "$0")/_common.sh"
#   require_root
#   detect_user

require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "Run with sudo: sudo ${0##*/}" >&2
        exit 1
    fi
}

detect_user() {
    DECK_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"
    DECK_USER="${DECK_USER:-pi}"
    DECK_HOME="$(getent passwd "$DECK_USER" | cut -d: -f6)"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
}

fix_eol() {
    dos2unix -q "$@" 2>/dev/null || true
}
