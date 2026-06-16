#!/usr/bin/env bash
# Shared launcher preamble — source at the top of each run.sh.
# Usage:
#   . "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_run_helper.sh"
#   run_app "deck-myapp.py" "$@"

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"

for py in "$DIR/../.venv/bin/python" "$DIR/../.venv/Scripts/python"; do
    [[ -f "$py" ]] && { PYTHON="$py"; break; }
done
PYTHON="${PYTHON:-$(command -v python3 || echo python)}"

run_app() {
    exec "$PYTHON" "$DIR/$1" "${@:2}"
}
