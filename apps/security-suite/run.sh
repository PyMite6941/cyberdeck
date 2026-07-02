#!/usr/bin/env bash
# security-suite — encrypted vault app (self-updating launcher).
#
# This folder is a thin launcher, not the app itself: real code lives at
# github.com/PyMite6941/Security-Suite and is synced via ../_vendor_launcher.sh
# (clone on first run, fetch + prompt-to-update on later runs). src/ is
# gitignored — it's a live clone the deck manages, not vendored code here.
#
# Usage:
#   ./run.sh                     run the app (checks for updates first)
#   ./run.sh --check-updates=off stop asking about updates
#   ./run.sh --check-updates=on  resume asking about updates
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"

vendor_sync "security-suite" "https://github.com/PyMite6941/Security-Suite.git" "$DIR/src" "$@"
exec "$DIR/src/run.sh" "$@"
