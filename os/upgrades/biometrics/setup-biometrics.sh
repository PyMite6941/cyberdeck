#!/usr/bin/env bash
# setup-biometrics.sh — Install biometric fingerprint scanner support.
#
# Part of the cyberdeck upgrades layer. Run after the base setup.sh:
#   sudo ./setup-biometrics.sh
#
# Installs:
#   1. pyserial (for UART communication)
#   2. deck-biometric command (GT-521F32 / R307 fingerprint scanner driver)
#   3. UART enable in config.txt (commented)
#   4. dialout group membership for the deck user
#
# Hardware: GT-521F32 (or R307/R503) optical fingerprint scanner on UART.
# Wiring: VCC→3.3V, GND→GND, TX→GPIO15(RX), RX→GPIO14(TX)
# After install: enable_uart=1 in config.txt, reboot.

set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./setup-biometrics.sh" >&2; exit 1; }
DECK_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"
DECK_USER="${DECK_USER:-pi}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN=/usr/local/bin
BIOMETRIC_DIR="$DECK_HOME/.deck-biometric"

inst() { install -m 755 "$SCRIPT_DIR/bin/$1" "$BIN/$1"; dos2unix -q "$BIN/$1" 2>/dev/null || true; }

echo "==> [1/3] Installing Python dependencies (pyserial)"
apt-get install -y --no-install-recommends python3-serial 2>/dev/null || {
    # Fallback: use the system venv if apt package unavailable
    [[ -x /opt/cyberdeck/venv/bin/python3 ]] || python3 -m venv /opt/cyberdeck/venv
    /opt/cyberdeck/venv/bin/pip install -q --upgrade pip
    /opt/cyberdeck/venv/bin/pip install -q pyserial
}

echo "==> [2/3] Installing deck-biometric command"
mkdir -p "$BIOMETRIC_DIR"
chown "$DECK_USER:$DECK_USER" "$BIOMETRIC_DIR"
inst deck-biometric

echo "==> [3/3] Adding user to dialout group (UART access)"
usermod -aG dialout "$DECK_USER" 2>/dev/null || true

# Append UART enable to config.txt (commented, marker-guarded)
CONFIG_TXT=/boot/firmware/config.txt
[[ -f $CONFIG_TXT ]] || CONFIG_TXT=/boot/config.txt
if [[ -f $CONFIG_TXT ]] && ! grep -q "CYBERDECK-BIOMETRICS" "$CONFIG_TXT"; then
    cat >> "$CONFIG_TXT" <<'EOF'

# --- CYBERDECK-BIOMETRICS ---
# UART for GT-521F32 / R307 fingerprint scanner (deck-biometric).
# Wiring: VCC→3.3V, GND→GND, TX→GPIO15(RX), RX→GPIO14(TX)
# Uncomment below, then reboot:
#enable_uart=1
#dtoverlay=disable-bt  # optional: frees UART from Bluetooth if using GPIO14/15
# --- END CYBERDECK-BIOMETRICS ---
EOF
    echo "  added UART section to $CONFIG_TXT (lines commented)"
fi

echo
echo "Done. To activate:"
echo "  1. Enable UART:      sudo nano $CONFIG_TXT  → uncomment enable_uart=1"
echo "  2. Reboot:           sudo reboot"
echo "  3. Check sensor:     deck-biometric status"
echo "  4. Enroll a finger:  deck-biometric enroll my-finger"
echo
echo "Tip: log out and back in (or reboot) for the 'dialout' group to take effect."
