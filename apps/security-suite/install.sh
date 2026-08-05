#!/usr/bin/env bash
# security-suite — installer / updater.
#
# Clones the real app (github.com/PyMite6941/Security-Suite) into src/ on first
# run, builds a PRIVATE virtualenv inside src/.venv and installs requirements,
# and on later runs offers to fast-forward to new commits (wiping caches after).
# src/ and its venv are gitignored — this folder only tracks install.sh, run.sh
# and README.md. Real code lives upstream, not here.
#
# Usage:
#   ./install.sh                     install or update (interactive check)
#   ./install.sh --check-updates=off stop asking about updates
#   ./install.sh --check-updates=on  resume asking about updates
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"
vendor_sync "security-suite" "https://github.com/PyMite6941/Security-Suite.git" "$DIR/src" "$@"
