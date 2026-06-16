#!/usr/bin/env bash
#
# cyberdeck virtual parts (OPT-IN) — run after the base setup.sh:
#   sudo ./setup-virtual.sh
#
# Installs the two network-backed "virtual hardware" capabilities:
#   1. Moonlight — borrow a home PC's GPU as a low-latency stream
#      (the PC side needs Sunshine: https://app.lizardbyte.dev)
#   2. deck-drive — attach network/cloud storage as if it were a local disk
#      (iSCSI block devices + rclone cloud mounts)
# Idempotent — safe to re-run.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo ./setup-virtual.sh" >&2
    exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/3] Moonlight (virtual GPU via game-stream)"
if ! command -v moonlight-qt >/dev/null 2>&1 && ! command -v moonlight >/dev/null 2>&1; then
    # Official Moonlight apt repo (works on Raspberry Pi OS Bookworm+).
    if curl -1sLf 'https://dl.cloudsmith.io/public/moonlight-game-streaming/moonlight-qt/setup.deb.sh' \
            | distro=raspbian env -i PATH="$PATH" bash; then
        apt-get update
        apt-get install -y moonlight-qt || echo "  moonlight-qt install failed — try flatpak later"
    else
        echo "  Moonlight repo setup failed — install later via: flatpak install com.moonlight_stream.Moonlight"
    fi
else
    echo "  moonlight already installed"
fi

echo "==> [2/3] Network/cloud storage backends"
apt-get install -y --no-install-recommends open-iscsi rclone

echo "==> [3/3] Installing deck-drive"
install -m 755 "$SCRIPT_DIR/bin/deck-drive" /usr/local/bin/deck-drive
dos2unix -q /usr/local/bin/deck-drive 2>/dev/null || true

echo
echo "Done. Usage:"
echo "  moonlight-qt                          # pair with Sunshine on your PC, stream its GPU"
echo "  deck-drive iscsi 192.168.1.10         # attach a NAS iSCSI target as a local block device"
echo "  deck-drive cloud gdrive:cad           # mount cloud storage at ~/CloudDrive (rclone config first)"
echo "  deck-drive list | off                 # show / detach everything"
