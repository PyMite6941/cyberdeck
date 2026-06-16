#!/bin/bash
# cyberdeck firstrun — placed in the SD card's boot partition by
# inject-to-sd.ps1 and executed ONCE by the kernel-command-line hook
# (systemd.run=/boot/firstrun.sh), exactly like Raspberry Pi Imager's own
# customisation script. Runs as root, very early, no network yet.
#
# It only does offline work, then installs a oneshot service that runs the
# real setup.sh (which needs network for apt) on the first normal boot.
set +e

# Boot partition mountpoint differs across OS releases — find ourselves.
BOOTDIR=""
for d in /boot/firmware /boot; do
    [[ -d "$d/cyberdeck" ]] && BOOTDIR="$d" && break
done
if [[ -z $BOOTDIR ]]; then
    echo "cyberdeck firstrun: payload not found, skipping" > /dev/kmsg
    exit 0
fi

# 1. Stage the OS layer onto the rootfs.
rm -rf /opt/cyberdeck-staging
cp -r "$BOOTDIR/cyberdeck" /opt/cyberdeck-staging
chmod +x /opt/cyberdeck-staging/setup.sh

# 2. Apply DFCD config.txt additions now (offline, marker-guarded).
if ! grep -q "CYBERDECK-CONFIG" "$BOOTDIR/config.txt"; then
    # strip CR in case the file came from Windows
    tr -d '\r' < /opt/cyberdeck-staging/image/config-additions.txt >> "$BOOTDIR/config.txt"
fi

# 3. Install the first-boot installer service (runs setup.sh once, online).
tr -d '\r' < /opt/cyberdeck-staging/image/cyberdeck-firstboot.service \
    > /etc/systemd/system/cyberdeck-firstboot.service
mkdir -p /etc/systemd/system/multi-user.target.wants
ln -sf /etc/systemd/system/cyberdeck-firstboot.service \
    /etc/systemd/system/multi-user.target.wants/cyberdeck-firstboot.service

# 4. Clean up: remove ourselves and the cmdline hook so this never reruns.
rm -f "$BOOTDIR/firstrun.sh" /boot/firstrun.sh 2>/dev/null
sed -i 's| systemd.run.*||g' "$BOOTDIR/cmdline.txt"
exit 0
