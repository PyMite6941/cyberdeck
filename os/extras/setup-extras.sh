#!/usr/bin/env bash
#
# cyberdeck extras (OPT-IN) — run after the base setup.sh:
#   sudo ./setup-extras.sh
#
# Adds: RTC support, LUKS encrypted vault, deck-mode (stealth/work/bright),
# status-LED control, always-on conky status overlay, RTL-SDR radio tools.
# Idempotent — safe to re-run.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo ./setup-extras.sh" >&2
    exit 1
fi
DECK_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"
DECK_USER="${DECK_USER:-pi}"
DECK_HOME="$(getent passwd "$DECK_USER" | cut -d: -f6)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/4] Packages (RTC tools, LUKS, dimming, conky, SDR)"
apt-get update
apt-get install -y --no-install-recommends \
    i2c-tools cryptsetup gammastep ddcutil conky-all rtl-sdr
# gqrx is the GUI SDR receiver — desktop images only, and it's big (~300 MB).
if command -v pcmanfm >/dev/null 2>&1; then
    apt-get install -y gqrx-sdr || echo "  (gqrx unavailable — rtl_fm CLI still works)"
fi

echo "==> [2/4] Installing deck commands"
install -m 755 "$SCRIPT_DIR/bin/deck-mode"      /usr/local/bin/deck-mode
install -m 755 "$SCRIPT_DIR/bin/deck-vault"     /usr/local/bin/deck-vault
install -m 755 "$SCRIPT_DIR/bin/deck-ide"       /usr/local/bin/deck-ide
install -m 755 "$SCRIPT_DIR/bin/deck-desktop"   /usr/local/bin/deck-desktop
install -m 755 "$SCRIPT_DIR/bin/deck-fs"        /usr/local/bin/deck-fs
install -m 755 "$SCRIPT_DIR/bin/deck-app"       /usr/local/bin/deck-app
install -m 755 "$SCRIPT_DIR/bin/deck-help"      /usr/local/bin/deck-help
install -m 755 "$SCRIPT_DIR/bin/deck-check"     /usr/local/bin/deck-check
install -m 755 "$SCRIPT_DIR/bin/deck-settings"  /usr/local/bin/deck-settings
# Deploy the deck-settings Python app to the staging lib directory.
mkdir -p /opt/cyberdeck/lib/deck-settings
if [[ -d "$SCRIPT_DIR/lib/deck-settings" ]]; then
    cp -r "$SCRIPT_DIR/lib/deck-settings/"* /opt/cyberdeck/lib/deck-settings/
fi
dos2unix -q /usr/local/bin/deck-mode /usr/local/bin/deck-vault \
              /usr/local/bin/deck-ide /usr/local/bin/deck-desktop \
              /usr/local/bin/deck-app /usr/local/bin/deck-help \
              /usr/local/bin/deck-fs /usr/local/bin/deck-check \
              /usr/local/bin/deck-settings 2>/dev/null || true
# mesa-utils provides glxinfo, used by deck-check to verify hardware GL.
apt-get install -y --no-install-recommends mesa-utils 2>/dev/null || true

echo "==> [3/4] RTC"
# Pi 5: onboard RTC — plug the official battery into J5; works out of the box.
# Pi 4: DS3231 on the GPIO header — uncomment dtoverlay=i2c-rtc,ds3231 in
# config.txt (shipped commented in the CYBERDECK-CONFIG section).
# Only remove fake-hwclock if the RTC is actually functional (has battery / time).
if [[ -e /dev/rtc0 ]] && hwclock -r >/dev/null 2>&1; then
    apt-get purge -y fake-hwclock 2>/dev/null || true
    echo "  /dev/rtc0 functional — fake-hwclock removed"
elif [[ -e /dev/rtc0 ]]; then
    echo "  /dev/rtc0 present but not responding — keep fake-hwclock (install J5 battery)"
else
    echo "  no RTC yet (Pi 5: add J5 battery; Pi 4: DS3231 + dtoverlay) — keeping fake-hwclock"
fi

echo "==> [4/4] Conky status overlay (desktop only)"
if command -v pcmanfm >/dev/null 2>&1; then
    install -m 644 "$SCRIPT_DIR/conky.conf" /opt/cyberdeck/conky.conf
    AUTO="$DECK_HOME/.config/autostart/cyberdeck-conky.desktop"
    sudo -u "$DECK_USER" mkdir -p "$(dirname "$AUTO")"
    cat > "$AUTO" <<'EOF'
[Desktop Entry]
Type=Application
Name=Cyberdeck status overlay
Exec=conky -c /opt/cyberdeck/conky.conf
X-GNOME-Autostart-enabled=true
EOF
    chown "$DECK_USER:$DECK_USER" "$AUTO"
    echo "  conky autostarts at next login"
fi

echo
echo "Done. New commands:"
echo "  deck-mode stealth|work|bright   — dim/normal/max + status-LED behaviour"
echo "  deck-vault init|open|close      — LUKS-encrypted storage vault"
echo "  deck-ide                        — headless IDE (drops desktop, tmux + Neovim + Claude + htop)"
echo "  deck-desktop                    — restore the desktop after deck-ide"
echo "  deck-app install|create|list|run — app manager (defaults to ~/apps/)"
echo "  deck-help [section]              — comprehensive command reference"
echo "  deck-check [--quiet]             — health check (GPU/zram/thermal/governor)"
echo "  deck-settings                    — system configuration TUI (WiFi, storage, apps, system, security)"
echo "Radio: plug in an RTL-SDR dongle, then:  rtl_fm -f 99.9M -M wbfm | aplay  (or gqrx)"
