#!/usr/bin/env bash
# cyberdeck OS installer — TUI frontend for setup.sh and the opt-in layers.
#
# Usage:  sudo ./install.sh
#
# Uses whiptail (pre-installed on Raspberry Pi OS) to provide a guided
# installation with DFCD branding, step selection, and progress gauges.
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo ./install.sh" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DECK_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"
DECK_USER="${DECK_USER:-pi}"

# whiptail is pre-installed on Raspberry Pi OS — verify it's available.
if ! command -v whiptail >/dev/null 2>&1; then
    echo "whiptail not found — falling back to plain setup.sh" >&2
    exec "$SCRIPT_DIR/setup.sh"
fi

# ── helpers ──────────────────────────────────────────────────────────────────

WIDTH=70
HEIGHT=20

banner() {
    whiptail --title "Cyberdeck OS Installer" --msgbox \
"\n\
     ____  ______________
    / __ \/ ____/ ____/ __ \\
   / / / / /_  / /   / / / /
  / /_/ / __/ / /___/ /_/ /
 /_____/_/   \____/_____/   cyberdeck
\n\
Raspberry Pi OS layer for the DFCD cyberdeck.
\n\
This installer will guide you through setting up:
  - Base OS layer  (zram, boot scripts, theme)
  - AI layer       (Claude Code + Ollama, opt-in)
  - Extras layer   (vault, deck-mode, deck-ide, conky, SDR)
  - Upgrades layer (assistant, HID, NAS, RFID, LoRa)
\n\
All scripts are idempotent — safe to re-run." $HEIGHT $WIDTH
}

step_gauge() {
    local title="$1" text="$2" cmd="$3"
    {
        echo "XXX"
        echo "0"
        echo "$text"
        echo "XXX"
        $cmd 2>&1 | while IFS= read -r line; do
            echo "XXX"
            echo "50"
            echo "${line:0:60}"
            echo "XXX"
        done
        echo "XXX"
        echo "100"
        echo "Done."
        echo "XXX"
    } | whiptail --title "$title" --gauge "$text" 8 $WIDTH 0
}

run_step() {
    local title="$1" log="$2"
    shift 2
    whiptail --title "$title" --infobox "$*..." 5 $WIDTH
    if "$@" > "$log" 2>&1; then
        return 0
    else
        whiptail --title "Error" --msgbox "$title failed. Check $log for details." 8 $WIDTH
        return 1
    fi
}

# ── main ─────────────────────────────────────────────────────────────────────

banner

# Step selection menu.
CHOICES=$(whiptail --title "Installation Steps" --checklist \
"Select the layers to install. Base is always required.
\n\
Use SPACE to toggle, TAB to move, ENTER to confirm." \
$HEIGHT $WIDTH 5 \
"1" "Base OS layer  (zram, boot.d, theme, FreeCAD)" ON \
"2" "AI layer       (Claude Code + Ollama + tuned model)" OFF \
"3" "Extras layer   (vault, deck-ide, deck-mode, conky, SDR)" OFF \
"4" "Upgrades layer (assistant, HID, NAS, RFID, LoRa)" OFF \
"5" "Virtual layer  (Moonlight streaming, deck-drive)" OFF \
3>&1 1>&2 2>&3)

[[ -n $CHOICES ]] || exit 0

run_step "Base OS"   "/tmp/cyberdeck-setup.log" "$SCRIPT_DIR/setup.sh"

if echo "$CHOICES" | grep -q '"2"'; then
    run_step "AI layer" "/tmp/cyberdeck-ai.log" "$SCRIPT_DIR/ai/setup-ai.sh"
fi

if echo "$CHOICES" | grep -q '"3"'; then
    run_step "Extras layer" "/tmp/cyberdeck-extras.log" "$SCRIPT_DIR/extras/setup-extras.sh"
fi

if echo "$CHOICES" | grep -q '"4"'; then
    run_step "Upgrades layer" "/tmp/cyberdeck-upgrades.log" "$SCRIPT_DIR/upgrades/setup-upgrades.sh"
fi

if echo "$CHOICES" | grep -q '"5"'; then
    run_step "Virtual layer" "/tmp/cyberdeck-virtual.log" "$SCRIPT_DIR/extras/setup-virtual.sh"
fi

whiptail --title "Installation Complete" --msgbox \
"\
Cyberdeck OS installation finished.
\n\
Next steps:
  - Reboot:        sudo reboot
  - Tune Ollama:   sudo ./ai/tune-ollama.sh        (if you skipped auto-pull)
  - Logs:          /tmp/cyberdeck-*.log
\n\
After reboot, run deck-ide to enter headless development mode,
or deck-lite to free RAM for inference." 14 $WIDTH
