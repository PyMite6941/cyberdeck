#!/usr/bin/env bash
# Example boot script — proves the boot.d system works.
# Replace or delete this; add your own as NN-name.sh (chmod +x).
# Runs as root. stdout/stderr go to /var/log/cyberdeck-boot.log.

echo "cyberdeck online: $(hostname) | $(date) | ip: $(hostname -I 2>/dev/null || echo n/a)"
