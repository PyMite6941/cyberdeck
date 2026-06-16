# Bootable image pipeline

Turns a stock Raspberry Pi OS SD card into a self-installing cyberdeck image.
No Linux machine or pi-gen build needed — the boot partition is FAT32, so
Windows can inject everything, and the Pi finishes the job on first boot.

## Make a bootable cyberdeck SD card

1. **Flash** — Raspberry Pi Imager → *Raspberry Pi OS (64-bit) with desktop*
   (Bookworm or later; FreeCAD needs the desktop). In Imager's customisation
   set hostname, user, Wi-Fi, and enable SSH. Works for Pi 4B and Pi 5.
2. **Inject** — with the card still in the reader:
   ```powershell
   cd portfolio\cyberdeck\os\image
   .\inject-to-sd.ps1          # auto-detects the boot partition
   ```
3. **Boot the Pi** —
   - *Boot 1*: Imager applies its settings, our firstrun stages
     `/opt/cyberdeck-staging`, appends the DFCD section to `config.txt`,
     installs `cyberdeck-firstboot.service`, removes the hook, reboots.
   - *Boot 2*: the service waits for network, runs `setup.sh` (packages incl.
     FreeCAD ~1 GB, zram, boot.d, theme), marks `/opt/cyberdeck/.installed`,
     and disables itself. Watch it live: `journalctl -fu cyberdeck-firstboot`.
4. **Optional layers** — after base install, run the TUI installer or the
   individual setup scripts:
   ```bash
   sudo ./install.sh                    # TUI installer (whiptail)
   # or step by step:
   sudo ./ai/setup-ai.sh               # Claude Code + Ollama + tuned model
   sudo ./extras/setup-extras.sh       # vault, deck-ide, deck-mode, conky
   sudo ./extras/setup-virtual.sh      # Moonlight + network drives
   sudo ./upgrades/setup-upgrades.sh   # assistant, HID, NAS, RFID, LoRa
   ```
5. Log in — you should see the DFCD banner; `swapon --show` lists `/dev/zram0`.

## Files

| File | Role |
|---|---|
| `inject-to-sd.ps1` | Windows-side: copies `os/` to the card, installs/chains the firstrun hook, enforces LF endings |
| `firstrun.sh` | Pi-side, boot 1 (offline): stage files, patch config.txt, install the installer service, self-remove |
| `cyberdeck-firstboot.service` | Pi-side, boot 2 (online): runs `setup.sh` once, then disables itself |
| `config-additions.txt` | DFCD hardware section appended to `config.txt` — commented dtoverlays for the rotary encoder, GPIO buttons, safe-shutdown, plus panel-EDID and Pi 4 `gpu_mem` notes |

All files in `os/` are copied verbatim to the card, so new boot scripts (`boot.d/`),
`ai/`, `extras/`, and `upgrades/` are available on the Pi after boot 1 — run the
opt-in installers (`ai/setup-ai.sh`, `extras/setup-extras.sh`, etc.) manually
once the base install finishes.

## Image helpers (Python + FreeCAD, for sizing/CAD measurements)

| Script | Purpose |
|---|---|
| `measure_parts.py` | Headless FreeCAD script: measures bounding boxes of all STEP assemblies → `../../SIZING.md` |
| `print_check.py` | Validates all `.3mf` print files: bbox, solid, manifold, self-intersection |
| `check_pi_clearance.py` | FreeCADCmd chassis clearance analysis |
| `make_raised_lid.py` | Generates the 12mm-raised GFPIO lid STEP/3MF/STL |
| `make_led_button.py` | Generates status-LED button frame cutout |
| `make_comms_module.py` | Generates the comms module (NFC+LoRa) enclosure |
| `inspect_*.py` | Various FreeCAD geometry probes (lid, rail, buttons, screen frame) |

## Notes

- The hook is the exact mechanism Raspberry Pi Imager itself uses
  (`systemd.run=/boot/firstrun.sh …` in `cmdline.txt`). If Imager
  customisation is present, `inject-to-sd.ps1` chains into Imager's
  `firstrun.sh` instead of competing with it.
- `firstrun.sh` finds the boot mountpoint itself (`/boot/firmware` on
  Bookworm+, `/boot` on older), so it survives OS path changes.
- Everything is idempotent: re-running the injector on a used card, or
  `setup.sh` on an installed system, is safe.
- GPIO overlays in `config-additions.txt` ship commented out — uncomment and
  set the real BCM pin numbers after you wire the encoder/buttons.
