#!/usr/bin/env bash
#
# cyberdeck OS setup — run ON the Raspberry Pi after flashing Raspberry Pi OS.
#
# Usage:
#   sudo ./setup.sh
#
# Target: Raspberry Pi 4B or newer, Raspberry Pi OS 64-bit (Bookworm or later).
#
# What it does (idempotent — safe to re-run):
#   1. Installs the minimal package set (incl. FreeCAD — the DFCD's whole purpose)
#   2. Configures memory management (zram swap + VM tuning; retires SD-card swap)
#   3. Appends DFCD display/input config to config.txt (commented dtoverlays)
#   4. Installs the boot-script system to /opt/cyberdeck/ (systemd unit + boot.d/)
#   5. Installs the cyberdeck shell theme (prompt, aliases, MOTD banner, tmux)
#   6. Security hardening + maintenance (UFW firewall, SSH hardening, logrotate)
#
# Everything this script touches on the Pi:
#   /opt/cyberdeck/                       <- boot runner + boot.d/ + theme files
#   /etc/systemd/system/cyberdeck-boot.service
#   /etc/default/zramswap                 <- zram swap config
#   /etc/sysctl.d/90-cyberdeck-vm.conf    <- VM tuning for zram
#   /etc/sysctl.d/90-cyberdeck-security.conf <- kernel security hardening
#   /etc/systemd/journald.conf.d/99-cyberdeck.conf <- journald size limit
#   /etc/logrotate.d/cyberdeck-boot       <- boot log rotation
#   /etc/ssh/sshd_config.d/99-cyberdeck.conf <- SSH hardening
#   /boot/firmware/config.txt             <- marker-guarded DFCD section appended
#   /etc/update-motd.d/10-cyberdeck       <- login banner
#   ~/.bashrc                             <- one marker-guarded source line appended
#   ~/.tmux.conf                          <- only created if absent
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo ./setup.sh" >&2
    exit 1
fi

# The real (non-root) user — sudo invoker, else the first regular user (uid
# 1000; covers the image first-boot path where there is no SUDO_USER).
DECK_USER="${SUDO_USER:-$(getent passwd 1000 | cut -d: -f1)}"
DECK_USER="${DECK_USER:-pi}"
DECK_HOME="$(getent passwd "$DECK_USER" | cut -d: -f6)"
if [[ -z $DECK_HOME ]]; then
    echo "Could not resolve home dir for user '$DECK_USER'" >&2
    exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/6] Installing packages"
apt-get update
# Minimal set. freecad is large (~1 GB with deps) but is the point of this deck.
apt-get install -y --no-install-recommends \
    git curl vim htop tmux dos2unix zram-tools ufw
# fastfetch is in the Raspberry Pi OS repo (Bookworm+); tolerate its absence.
apt-get install -y --no-install-recommends fastfetch \
    || echo "  (fastfetch unavailable — skipping, banner still works)"
# freecad with --no-install-recommends to avoid pulling 200+ MB of extras.
apt-get install -y --no-install-recommends freecad

echo "==> [2/6] Configuring memory management (zram swap + VM tuning)"
# zram: compressed swap in RAM. On a Pi 4 (4 GB) this is the difference between
# FreeCAD swapping to a slow SD card vs. staying responsive. Also kills SD wear.
install -m 644 "$SCRIPT_DIR/memory/zramswap.conf" /etc/default/zramswap
install -m 644 "$SCRIPT_DIR/memory/90-cyberdeck-vm.conf" /etc/sysctl.d/90-cyberdeck-vm.conf
dos2unix -q /etc/default/zramswap /etc/sysctl.d/90-cyberdeck-vm.conf || true
sysctl --system > /dev/null
systemctl enable zramswap.service
systemctl restart zramswap.service
# Retire the default SD-card swapfile — zram replaces it (faster, no SD wear).
if systemctl list-unit-files dphys-swapfile.service --no-legend 2>/dev/null | grep -q dphys-swapfile; then
    systemctl disable --now dphys-swapfile.service || true
fi

echo "==> [3/6] Applying display/input config (config.txt additions)"
# DFCD hardware overlays (rotary encoder, GPIO buttons, safe shutdown) —
# shipped commented-out; uncomment in /boot/firmware/config.txt after wiring.
CONFIG_TXT=/boot/firmware/config.txt
[[ -f $CONFIG_TXT ]] || CONFIG_TXT=/boot/config.txt
if [[ -f $CONFIG_TXT ]] && ! grep -q "CYBERDECK-CONFIG" "$CONFIG_TXT"; then
    cat "$SCRIPT_DIR/image/config-additions.txt" >> "$CONFIG_TXT"
    echo "  appended DFCD section to $CONFIG_TXT"
fi

echo "==> [4/6] Installing boot-script system"
mkdir -p /opt/cyberdeck/boot.d
install -m 755 "$SCRIPT_DIR/boot/cyberdeck-boot.sh" /opt/cyberdeck/cyberdeck-boot.sh
# Copy boot.d scripts; never overwrite ones already customised on the Pi.
for f in "$SCRIPT_DIR"/boot/boot.d/*.sh; do
    dest="/opt/cyberdeck/boot.d/$(basename "$f")"
    [[ -e $dest ]] || install -m 755 "$f" "$dest"
done
# Strip CRLF in case files came from a Windows checkout.
dos2unix -q /opt/cyberdeck/cyberdeck-boot.sh /opt/cyberdeck/boot.d/*.sh || true
install -m 644 "$SCRIPT_DIR/boot/cyberdeck-boot.service" /etc/systemd/system/cyberdeck-boot.service
systemctl daemon-reload
systemctl enable cyberdeck-boot.service

echo "==> [5/6] Installing theme"
install -m 644 "$SCRIPT_DIR/theme/bashrc-cyberdeck.sh" /opt/cyberdeck/bashrc-cyberdeck.sh
install -m 644 "$SCRIPT_DIR/theme/fastfetch.jsonc" /opt/cyberdeck/fastfetch.jsonc
install -m 755 "$SCRIPT_DIR/theme/motd.sh" /etc/update-motd.d/10-cyberdeck
dos2unix -q /opt/cyberdeck/bashrc-cyberdeck.sh /etc/update-motd.d/10-cyberdeck || true
# Silence the stock Debian MOTD so only the deck banner shows.
[[ -f /etc/motd ]] && : > /etc/motd
# Marker-guarded append so re-running never duplicates the line.
if ! grep -q "cyberdeck-theme" "$DECK_HOME/.bashrc" 2>/dev/null; then
    printf '\n# cyberdeck-theme\n[ -f /opt/cyberdeck/bashrc-cyberdeck.sh ] && . /opt/cyberdeck/bashrc-cyberdeck.sh\n' \
        >> "$DECK_HOME/.bashrc"
fi
# tmux theme — only if the user doesn't already have one.
if [[ ! -e "$DECK_HOME/.tmux.conf" ]]; then
    install -m 644 -o "$DECK_USER" -g "$DECK_USER" \
        "$SCRIPT_DIR/theme/tmux.conf" "$DECK_HOME/.tmux.conf"
fi
# Desktop look (icons/wallpaper/dark GTK) — no-op on Lite images.
bash "$SCRIPT_DIR/theme/setup-desktop.sh" "$DECK_USER" "$DECK_HOME"

# ── 6/6: Security hardening + maintenance ──
echo "==> [6/6] Security hardening + maintenance"

# UFW firewall
bash "$SCRIPT_DIR/security/ufw.sh"
echo "  firewall enabled (UFW)"

# SSH hardening drop-in
install -m 644 "$SCRIPT_DIR/security/99-cyberdeck-ssh.conf" \
    /etc/ssh/sshd_config.d/99-cyberdeck.conf
echo "  SSH hardened (key-only, no root)"

# Kernel security sysctls
install -m 644 "$SCRIPT_DIR/security/90-cyberdeck-security.conf" \
    /etc/sysctl.d/90-cyberdeck-security.conf

# journald size limit
mkdir -p /etc/systemd/journald.conf.d
install -m 644 "$SCRIPT_DIR/memory/99-cyberdeck-journald.conf" \
    /etc/systemd/journald.conf.d/99-cyberdeck.conf

# Logrotate for boot log
install -m 644 "$SCRIPT_DIR/memory/logrotate-cyberdeck-boot" \
    /etc/logrotate.d/cyberdeck-boot

sysctl --system > /dev/null
systemctl reload systemd-journald 2>/dev/null || true

echo
echo "Done. Memory now: "
free -h | sed 's/^/  /'
echo
echo "Reboot to see the boot scripts + banner: sudo reboot"
echo "Add your own boot scripts to /opt/cyberdeck/boot.d/ (NN-name.sh, chmod +x)."
echo "Boot log: /var/log/cyberdeck-boot.log"
