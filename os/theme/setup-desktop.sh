#!/usr/bin/env bash
# Desktop look for the PIXEL desktop (icons + wallpaper + dark GTK).
# Called by setup.sh as: setup-desktop.sh <user> <home>   (root, idempotent).
# Skipped entirely on Lite images (no pcmanfm).
set -euo pipefail

DECK_USER="$1"
DECK_HOME="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v pcmanfm >/dev/null 2>&1 || { echo "  no desktop found - skipping"; exit 0; }

# 1. Icon theme: Papirus (dark variant) — full coverage, looks right on the
#    green/black deck. User-custom icons can additionally be dropped into
#    ~/.local/share/icons/ and selected the same way.
apt-get install -y --no-install-recommends papirus-icon-theme

# 2. Wallpaper (generated, not stored in git).
if python3 -c "import PIL" 2>/dev/null; then
    python3 "$SCRIPT_DIR/make_wallpaper.py" /opt/cyberdeck/wallpaper.png
else
    echo "  python3-pil missing - skipping wallpaper generation"
fi

as_user() { sudo -u "$DECK_USER" mkdir -p "$(dirname "$1")"; }

# 3. GTK icon theme + dark preference (create-if-absent; never clobber a
#    user-customised file).
GTK_INI="$DECK_HOME/.config/gtk-3.0/settings.ini"
if [[ ! -f $GTK_INI ]]; then
    as_user "$GTK_INI"
    cat > "$GTK_INI" <<'EOF'
[Settings]
gtk-icon-theme-name=Papirus-Dark
gtk-application-prefer-dark-theme=1
EOF
    chown "$DECK_USER:$DECK_USER" "$GTK_INI"
fi
LXS="$DECK_HOME/.config/lxsession/LXDE-pi/desktop.conf"
if [[ ! -f $LXS ]]; then
    as_user "$LXS"
    printf '[GTK]\nsNet/IconThemeName=Papirus-Dark\n' > "$LXS"
    chown "$DECK_USER:$DECK_USER" "$LXS"
fi

# 4. Desktop background via pcmanfm config (applies at next login).
PCM="$DECK_HOME/.config/pcmanfm/LXDE-pi/desktop-items-0.conf"
if [[ -f $PCM ]]; then
    sed -i -e 's|^wallpaper=.*|wallpaper=/opt/cyberdeck/wallpaper.png|' \
           -e 's|^wallpaper_mode=.*|wallpaper_mode=stretch|' \
           -e 's|^desktop_bg=.*|desktop_bg=#070B08|' "$PCM"
else
    as_user "$PCM"
    cat > "$PCM" <<'EOF'
[*]
wallpaper_mode=stretch
wallpaper=/opt/cyberdeck/wallpaper.png
desktop_bg=#070B08
desktop_fg=#39FF14
desktop_shadow=#070B08
EOF
    chown "$DECK_USER:$DECK_USER" "$PCM"
fi
echo "  desktop theme installed (icons: Papirus-Dark; relog to apply)"
