# Biometrics — Fingerprint Scanner (opt-in upgrade)

Add biometric fingerprint authentication to the cyberdeck using a **GT-521F32**
(or compatible R307 / R503) optical fingerprint scanner over UART.

## Hardware

| Part | Price | Notes |
|------|-------|-------|
| GT-521F32 (recommended) | ~$20–30 | 192×192 dpi, 200+ template capacity, 57600 baud |
| R307 / R503 (compatible) | ~$12–18 | Same protocol, often 9600 baud; R503 has "blue ring" indicator |
| GT-521F52 (upgrade) | ~$35–45 | Higher dpi (256×288), same wiring |

All three use the **FPS_GEN2** UART protocol and are interchangeable at the
software level.

### Wiring (to Pi GPIO header)

```
GT-521F32   →   Pi GPIO
──────────       ────────
VCC (red)   →   3.3V (pin 1)
GND (black) →   GND (pin 6)
TX (white)  →   RX / GPIO15 (pin 10)
RX (green)  →   TX / GPIO14 (pin 8)
```

### Enabling UART

Add to `/boot/firmware/config.txt` (or `/boot/config.txt` on older Pi OS):

```
enable_uart=1
```

If you use the Bluetooth module's UART (mini UART), also add:

```
dtoverlay=disable-bt
```

This frees the hardware UART (`/dev/ttyAMA0`) for the fingerprint scanner.
(Without it the scanner uses the mini UART at `/dev/ttyS0`, which is slower
and tied to the GPU clock.)

## Installation

```bash
sudo os/upgrades/biometrics/setup-biometrics.sh
```

Then:
1. Uncomment `enable_uart=1` in config.txt
2. `sudo reboot`
3. `deck-biometric status` — should show sensor info
4. `deck-biometric enroll my-finger-left` — register your finger
5. `deck-biometric verify` — test it

## Usage

```
deck-biometric status              sensor info, template count
deck-biometric enroll <name>       capture finger twice, save
deck-biometric verify              scan finger, check match
deck-biometric list                show all enrolled users
deck-biometric delete <name|id>    remove a specific entry
deck-biometric clear               delete ALL templates
deck-biometric vault-open          scan finger → unlock deck-vault
```

### Integration with deck-vault

Attach your fingerprint to the encrypted vault:

```bash
deck-biometric enroll my-finger    # once
deck-biometric vault-open          # scans → unlocks
```

This bypasses the passphrase prompt for `deck-vault open` — useful when the
deck is in field / handheld mode.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DECK_BIO_DEV` | `/dev/ttyAMA0` | Serial device |
| `DECK_BIO_BAUD` | `57600` | Baud rate (9600 for some R307 modules) |
| `DECK_BIO_DIR` | `~/.deck-biometric/` | Local enrollment name DB |

## Files

| File | Role |
|---|---|
| `bin/deck-biometric` | Scanner driver — enroll, verify, identify, vault-open |
| `setup-biometrics.sh` | One-shot installer |
| `biometric.service` | systemd unit (optional, status check on boot) |
| `README.md` | This file |

## Security notes

- Fingerprint templates are stored **on the sensor** (flash) — they never leave
  the module. Only the name→ID mapping is kept locally in `~/.deck-biometric/`.
- The sensor only matches against templates it stores — a compromised OS cannot
  extract raw fingerprint data.
- `vault-open` uses a simple fingerprint scan as a gate; the vault passphrase
  is still stored in the LUKS header and can be used as a fallback.
- This is **convenience biometrics**, not forensic-grade. A good fake finger
  can fool optical scanners. For threat models requiring high assurance, use
  the passphrase instead.
