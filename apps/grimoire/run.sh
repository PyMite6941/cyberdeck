#!/usr/bin/env bash
# grimoire — launcher (offline search + RAG). Thin wrapper: real code lives at
# github.com/PyMite6941/grimoire, installed by ./install.sh into src/ (gitignored)
# with its own private venv.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"
case "${1:-}" in --check-updates=*) exec "$DIR/install.sh" "$@" ;; esac
"$DIR/install.sh"
exec "$(vendor_python "$DIR/src")" "$DIR/src/run.py" "$@"
