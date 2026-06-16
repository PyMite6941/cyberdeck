#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$DIR/../.venv/bin/python" ]]; then
    PYTHON="$DIR/../.venv/bin/python"
elif [[ -f "$DIR/../.venv/Scripts/python" ]]; then
    PYTHON="$DIR/../.venv/Scripts/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi
exec "$PYTHON" "$DIR/deck-net.py" "$@"
