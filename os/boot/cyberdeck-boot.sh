#!/usr/bin/env bash
#
# cyberdeck boot runner — executed once per boot by cyberdeck-boot.service.
# Runs every executable *.sh in /opt/cyberdeck/boot.d/ in lexical order
# (10-foo.sh before 20-bar.sh). A failing script is logged but does NOT
# stop the others.
#
# Log: /var/log/cyberdeck-boot.log
#
set -u

# Overridable for testing off-Pi: BOOT_D=./boot.d LOG=/tmp/test.log ./cyberdeck-boot.sh
BOOT_D=${BOOT_D:-/opt/cyberdeck/boot.d}
LOG=${LOG:-/var/log/cyberdeck-boot.log}

echo "=== cyberdeck boot $(date -Is) ===" >> "$LOG"

shopt -s nullglob
for script in "$BOOT_D"/*.sh; do
    [[ -x $script ]] || continue
    echo "--- running $(basename "$script")" >> "$LOG"
    if "$script" >> "$LOG" 2>&1; then
        echo "--- ok: $(basename "$script")" >> "$LOG"
    else
        echo "--- FAILED ($?): $(basename "$script")" >> "$LOG"
    fi
done

echo "=== boot scripts done ===" >> "$LOG"
