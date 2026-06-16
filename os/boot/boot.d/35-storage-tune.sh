#!/usr/bin/env bash
# 35-storage-tune — tune I/O scheduler and NVMe power-save for the deck.
#
# - SD cards and eMMC: use BFQ (budget fair queuing) for better desktop
#   responsiveness under concurrent I/O.
# - NVMe SSDs: use "none" (no scheduler — NVMe has native command queuing),
#   enable TRIM/discard, and relax power-save latency for better throughput.
# - Adds commit=600 to root mount options (write thrashing reduction) if not
#   already present; 20-noatime.sh handles the noatime part.
set -euo pipefail

# ── I/O scheduler tuning ──
set_scheduler() {
    local dev="$1" sched="$2" path
    path="/sys/block/$dev/queue/scheduler"
    if [[ -w $path ]]; then
        local current
        current=$(cat "$path")
        if ! echo "$current" | grep -q "\[$sched\]"; then
            echo "$sched" | tee "$path" >/dev/null 2>&1 || true
            echo "storage-tune: $dev scheduler -> $sched"
        fi
    fi
}

for dev_path in /sys/block/mmcblk* /sys/block/sd*; do
    [[ -d $dev_path ]] || continue
    dev=$(basename "$dev_path")

    # Check if NVMe (via rotational flag — NVMe reports 0).
    local rot=1
    [[ -r "$dev_path/queue/rotational" ]] && rot=$(cat "$dev_path/queue/rotational")
    local tran=""
    [[ -r "$dev_path/device/type" ]] && tran=$(cat "$dev_path/device/type" 2>/dev/null || echo "")

    if echo "$dev" | grep -q "nvme"; then
        set_scheduler "$dev" "none"
        # Enable discard/TRIM if not already mounted with it.
        local mnt
        mnt=$(mount | grep "^/dev/$dev" | awk '{print $3}' | head -1)
        if [[ -n $mnt ]] && ! mount | grep "^/dev/$dev" | grep -q "discard"; then
            mount -o remount,discard "$mnt" 2>/dev/null || true
        fi
    elif [[ $rot -eq 0 ]]; then
        # SSD / eMMC / SD card (reports rotational=0 on modern kernels).
        set_scheduler "$dev" "bfq"
    else
        # Spinning rust (unlikely on a deck, but handle it).
        set_scheduler "$dev" "mq-deadline"
    fi
done

# ── Add commit=600 to root mount if not already present (extends SD life) ──
FSTAB=/etc/fstab
ROOT_LINE=$(grep -E '^\S+\s+/\s+' "$FSTAB" | head -1)
if [[ -n $ROOT_LINE ]] && ! echo "$ROOT_LINE" | grep -q "commit="; then
    ROOT_DEV=$(echo "$ROOT_LINE" | awk '{print $1}')
    ROOT_FS=$(echo "$ROOT_LINE" | awk '{print $3}')
    ROOT_OPTS=$(echo "$ROOT_LINE" | awk '{print $4}')
    ROOT_DUMP=$(echo "$ROOT_LINE" | awk '{print $5}')
    ROOT_PASS=$(echo "$ROOT_LINE" | awk '{print $6}')
    NEW_OPTS="${ROOT_OPTS},commit=600"
    awk -v dev="$ROOT_DEV" -v fs="$ROOT_FS" -v opts="$NEW_OPTS" -v dump="$ROOT_DUMP" -v pass="$ROOT_PASS" \
        '{ if ($1 == dev && $2 == "/") print dev, "/", fs, opts, dump, pass; else print }' \
        "$FSTAB" > "${FSTAB}.tmp" && mv "${FSTAB}.tmp" "$FSTAB"
    mount -o remount /
    echo "storage-tune: added commit=600 to root mount"
else
    echo "storage-tune: commit=600 already present or root mount not found"
fi
