#!/usr/bin/env bash
# 30-cpugovernor — set the CPU scaling governor for best performance on a deck
# that runs on AC power (FreeCAD, compiling, LLM inference).
#
# The Pi 5 / Pi 4 Cortex cores support these governors: ondemand, conservative,
# performance, powersave, schedutil. "ondemand" is the kernel default.
#
# For a cyberdeck on AC power (the common case), "performance" keeps all cores
# at max frequency — best for CAD and inference. If you spend most of your time
# on battery, change this to "ondemand" or "powersave".
#
# In deck-mode: stealth -> powersave, work -> ondemand, bright -> performance.
# This script sets the AC-power default; deck-mode overrides it at runtime.
set -euo pipefail

GOVERNOR="performance"

# Check that the scaling governor interface exists.
GOV_PATH="/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
if [[ ! -r $GOV_PATH ]]; then
    echo "cpugovernor: no cpufreq interface found (maybe a VM or container)"
    exit 0
fi

CURRENT=$(cat "$GOV_PATH")
if [[ "$CURRENT" == "$GOVERNOR" ]]; then
    echo "cpugovernor: already $GOVERNOR — nothing to do"
    exit 0
fi

# Set governor on every online CPU.
for cpu_gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [[ -w $cpu_gov ]] || continue
    echo "$GOVERNOR" | tee "$cpu_gov" >/dev/null 2>&1 || true
done

# Verify and log.
VERIFIED=$(cat "$GOV_PATH")
echo "cpugovernor: set to $VERIFIED (was $CURRENT)"
