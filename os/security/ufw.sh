# UFW firewall rules for the cyberdeck.
# Sourced by setup.sh — configures default-deny incoming, allows essential services.
# Idempotent: safe to re-run.
ufw --force disable 2>/dev/null
ufw --force reset 2>/dev/null

ufw default deny incoming
ufw default allow outgoing

# SSH from LAN only (192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12).
ufw allow from 192.168.0.0/16 to any port 22 proto tcp
ufw allow from 10.0.0.0/8 to any port 22 proto tcp
ufw allow from 172.16.0.0/12 to any port 22 proto tcp

# Samba (deck-nas) — LAN only (all three RFC 1918 ranges).
ufw allow from 192.168.0.0/16 to any port 137,138 proto udp
ufw allow from 192.168.0.0/16 to any port 139,445 proto tcp
ufw allow from 10.0.0.0/8    to any port 137,138 proto udp
ufw allow from 10.0.0.0/8    to any port 139,445 proto tcp
ufw allow from 172.16.0.0/12 to any port 137,138 proto udp
ufw allow from 172.16.0.0/12 to any port 139,445 proto tcp

# Moonlight streaming (deck-drive) — LAN only.
ufw allow from 192.168.0.0/16 to any port 47984,47989,48010,47991,48000 proto tcp
ufw allow from 192.168.0.0/16 to any port 47998:48000 proto udp
ufw allow from 10.0.0.0/8 to any port 47984,47989,48010,47991,48000 proto tcp
ufw allow from 10.0.0.0/8 to any port 47998:48000 proto udp

ufw --force enable
