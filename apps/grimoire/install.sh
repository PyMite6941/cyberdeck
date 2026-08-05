#!/usr/bin/env bash
# grimoire — installer / updater. Clones the real app into src/ with a private
# venv; offers fast-forward updates and wipes caches after each pull.
# Usage: ./install.sh [--check-updates=on|off]
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"
vendor_sync "grimoire" "https://github.com/PyMite6941/grimoire.git" "$DIR/src" "$@"
