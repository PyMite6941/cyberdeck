#!/usr/bin/env bash
# 20-noatime — add noatime to the root mount if it's not already there.
#
# This stops the OS from writing "last accessed" timestamps on every file
# read, reducing SD-card wear and improving compile/git performance.
# Idempotent: safe to run every boot; only edits if needed.
#
set -euo pipefail

FSTAB=/etc/fstab
MARKER="noatime"

# Find the root (/) line, skip comments.
ROOT_LINE=$(grep -E '^\S+\s+/\s+' "$FSTAB" | head -1)
[[ -n $ROOT_LINE ]] || { echo "noatime: could not find root mount in $FSTAB"; exit 0; }

# Check if noatime is already present.
if echo "$ROOT_LINE" | grep -q "$MARKER"; then
    echo "noatime: already set on root mount — nothing to do"
    exit 0
fi

# Add noatime + commit=600 (ext4 journal commit delay — reduces SD write frequency).
ROOT_DEV=$(echo "$ROOT_LINE" | awk '{print $1}')
ROOT_FS=$(echo "$ROOT_LINE" | awk '{print $3}')
ROOT_OPTS=$(echo "$ROOT_LINE" | awk '{print $4}')
ROOT_DUMP=$(echo "$ROOT_LINE" | awk '{print $5}')
ROOT_PASS=$(echo "$ROOT_LINE" | awk '{print $6}')

# noatime implies nodiratime — no need for both.
NEW_OPTS="${ROOT_OPTS},noatime"
# Only add commit=600 if not already present.
if ! echo "$ROOT_OPTS" | grep -q "commit="; then
    NEW_OPTS="${NEW_OPTS},commit=600"
fi

# Use awk for safe in-place edit (avoids sed escaping issues with PARTUUID=).
awk -v dev="$ROOT_DEV" -v opts="$NEW_OPTS" -v dump="$ROOT_DUMP" -v pass="$ROOT_PASS" \
    '{ if ($1 == dev && $2 == "/") print dev, "/", $3, opts, dump, pass; else print }' \
    "$FSTAB" > "${FSTAB}.tmp" && mv "${FSTAB}.tmp" "$FSTAB"
echo "noatime: added to root mount in $FSTAB (remount in progress)"

# Remount root with new options (no reboot needed).
mount -o remount /
echo "noatime: root remounted, verify with: mount | grep ' / '"
