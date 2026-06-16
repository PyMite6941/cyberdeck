#!/usr/bin/env bash
#
# cyberdeck "Committed Upgrades" (OPT-IN) — run after the base setup.sh:
#   sudo ./setup-upgrades.sh
#
# Installs five upgrades. The three software ones work immediately; the two
# hardware ones (RFID, LoRa) install their libraries + helper commands and
# activate once you wire the part and uncomment the bus in config.txt.
#   1. Offline Ollama assistant 'DECK'  (pull base model + Modelfile persona)
#   2. USB HID keyboard mode            (deck-hid)
#   3. NAS file sharing over WiFi        (deck-nas, Samba)
#   4. NFC/RFID reader helper            (deck-rfid, PN532 over I2C)
#   5. LoRa radio helper                 (deck-lora, SX127x over SPI, AS923)
# Idempotent — safe to re-run.
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./setup-upgrades.sh" >&2; exit 1; }
DECK_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"
DECK_USER="${DECK_USER:-pi}"
DECK_HOME="$(getent passwd "$DECK_USER" | cut -d: -f6)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN=/usr/local/bin
mkdir -p /opt/cyberdeck

inst() { install -m 755 "$SCRIPT_DIR/bin/$1" "$BIN/$1"; dos2unix -q "$BIN/$1" 2>/dev/null || true; }

echo "==> [1/5] Offline assistant (Ollama + DECK persona)"
if ! command -v ollama >/dev/null 2>&1; then
    echo "  installing ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    sleep 3   # let the systemd service come up before we talk to it
fi
ram_mb=$(free -m | awk 'NR==2{print $2}')
if (( ram_mb >= 7000 )); then BASE=qwen2.5:3b; else BASE=qwen2.5:1.5b; fi
echo "  pulling base model: $BASE (${ram_mb} MB RAM detected)"
ollama pull "$BASE"
sed "s|^FROM .*|FROM $BASE|" "$SCRIPT_DIR/assistant/Modelfile" > /opt/cyberdeck/Modelfile.deck
ollama create deck -f /opt/cyberdeck/Modelfile.deck
inst deck-assistant
echo "  ready:  deck-assistant \"how do I check the deck temperature?\""

echo "==> [2/5] USB HID keyboard mode (deck-hid)"
inst deck-hid
# udev rule so 'deck-hid type/key' work without sudo once the gadget is up.
echo "KERNEL==\"hidg*\", MODE=\"0660\", GROUP=\"$DECK_USER\"" \
    > /etc/udev/rules.d/99-cyberdeck-hidg.rules
udevadm control --reload 2>/dev/null || true

echo "==> [3/5] NAS file sharing (deck-nas, Samba)"
apt-get update
apt-get install -y --no-install-recommends samba samba-common-bin
# Prevent Samba from auto-starting — deck-nas on/off controls it manually.
systemctl disable smbd nmbd 2>/dev/null || true
SHARE="$DECK_HOME/Share"
sudo -u "$DECK_USER" mkdir -p "$SHARE"
if ! grep -q '^\[deck\]' /etc/samba/smb.conf; then
    cat >> /etc/samba/smb.conf <<EOF

[global]
   server min protocol = SMB3_00
   server max protocol = SMB3_11

[deck]
   comment = DFCD cyberdeck share
   path = $SHARE
   browseable = yes
   read only = no
   guest ok = no
   valid users = $DECK_USER
EOF
fi
inst deck-nas
echo "  set the share password:  deck-nas user   (then: deck-nas on)"

echo "==> [4/5]+[5/5] Hardware-helper libraries (PN532 NFC + SX127x LoRa)"
apt-get install -y --no-install-recommends python3-venv python3-dev
[[ -x /opt/cyberdeck/venv/bin/python3 ]] || python3 -m venv /opt/cyberdeck/venv
/opt/cyberdeck/venv/bin/pip install -q --upgrade pip
/opt/cyberdeck/venv/bin/pip install -q \
    adafruit-blinka adafruit-circuitpython-pn532 adafruit-circuitpython-rfm9x pyserial
inst deck-rfid
inst deck-lora
# deck-comms drives the Pico-bridge comms module over USB serial (pyserial).
inst deck-comms

# Append the hardware-enable section to config.txt (commented; marker-guarded).
CONFIG_TXT=/boot/firmware/config.txt
[[ -f $CONFIG_TXT ]] || CONFIG_TXT=/boot/config.txt
if [[ -f $CONFIG_TXT ]] && ! grep -q "CYBERDECK-UPGRADES" "$CONFIG_TXT"; then
    cat "$SCRIPT_DIR/config-upgrades.txt" >> "$CONFIG_TXT"
    echo "  appended hardware-enable section to $CONFIG_TXT (lines commented)"
fi

echo "==> [6/6] Scroll-handle input daemon (deck-scroll)"
apt-get install -y --no-install-recommends python3-evdev xdotool
inst deck-scroll

# Let the deck user create virtual input devices (uinput) and read the encoder.
cat > /etc/udev/rules.d/99-cyberdeck-uinput.rules <<'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660"
EOF
usermod -aG input "$DECK_USER" 2>/dev/null || true
udevadm control --reload 2>/dev/null || true

# Install the systemd user service.
svc_dir="$DECK_HOME/.config/systemd/user"
mkdir -p "$svc_dir"
install -m 644 "$SCRIPT_DIR/scroll-handle.service" "$svc_dir/deck-scroll.service"
chown -R "$DECK_USER:$DECK_USER" "$DECK_HOME/.config/systemd/user"
# enable-linger keeps user services alive without an active session.
loginctl enable-linger "$DECK_USER" 2>/dev/null || true

echo
echo "Done. Live now (software):"
echo "  deck-assistant                 offline AI persona"
echo "  sudo deck-hid on && deck-hid type \"hello\""
echo "  deck-nas user && deck-nas on   share ~/Share over WiFi"
echo "After wiring the hardware (uncomment in $CONFIG_TXT, reboot):"
echo "  PN532 NFC (I2C):   deck-rfid read"
echo "  LoRa SX127x (SPI): deck-lora recv     # 923 MHz, AS923 / Thailand"
echo "  Scroll handle:     systemctl --user enable --now deck-scroll"
echo "  NOTE: log out + back in (or reboot) for the 'input' group to take effect"
