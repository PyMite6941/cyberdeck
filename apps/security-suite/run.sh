#!/usr/bin/env bash
# security-suite — launcher (encrypted vault: 2FA, password gen, breach check).
#
# Thin launcher, not the app itself: real code lives at
# github.com/PyMite6941/Security-Suite and is installed by ./install.sh into
# src/ (gitignored) with its own private venv. This just ensures it's installed,
# then runs it from that venv.
#
# Usage:
#   ./run.sh                     run the app (install/update-check first)
#   ./run.sh --check-updates=off stop asking about updates
#   ./run.sh --check-updates=on  resume asking about updates
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"

# Update-toggle flags just configure behavior via install.sh, then exit.
case "${1:-}" in --check-updates=*) exec "$DIR/install.sh" "$@" ;; esac

"$DIR/install.sh"                                  # clone if needed + update check
exec "$(vendor_python "$DIR/src")" "$DIR/src/run.py" "$@"
