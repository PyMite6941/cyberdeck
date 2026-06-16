#!/usr/bin/env bash
# Shared virtualenv for all deck apps. Run on any machine (the Pi, or Windows
# via git-bash):
#   ./setup-venv.sh
# Creates apps/.venv and installs every app's requirements.txt into it, so the
# lightweight apps share one environment instead of N duplicate venvs.
# Idempotent. The venv is machine-specific and gitignored — never commit it;
# re-run this on each machine (a Windows venv won't work on the Pi).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/.venv"
PY="${PYTHON:-python3}"

[ -d "$VENV" ] || "$PY" -m venv "$VENV"
VPY="$VENV/bin/python"; [ -x "$VPY" ] || VPY="$VENV/Scripts/python.exe"   # linux | windows
"$VPY" -m pip install -q --upgrade pip

shopt -s nullglob
found=0
for req in "$HERE"/*/requirements.txt; do
    found=1
    echo "installing deps: ${req#$HERE/}"
    "$VPY" -m pip install -q -r "$req" \
        || echo "  (some deps in ${req#$HERE/} failed — that app may need its own venv)"
done
[ "$found" = 1 ] || echo "no */requirements.txt found yet"

echo "shared venv ready: $VENV"
echo "use it by activating:  source apps/.venv/bin/activate   (or .../Scripts/activate on Windows)"
