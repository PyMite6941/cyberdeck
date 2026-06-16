# Cyberdeck (DFCD build)

Custom cyberdeck build based on the **DesignatedFreeCadDevice (DFCD)** by
[Jankbu](https://www.youtube.com/@Jankbu) — a modular Raspberry Pi 5 cyberdeck
designed to run FreeCAD, with a sliding 10.1" touchscreen, hidden mechanical
keyboard, trackball, scroll handle, and NP-F battery module.

**Upstream hardware design (CC BY-NC-SA):** [`ArcticEnrichmentCenter/DFCD-cyberdeck-files`](https://github.com/ArcticEnrichmentCenter/DFCD-cyberdeck-files)

| Source | Link |
|---|---|
| GitHub repo (CAD files) | https://github.com/ArcticEnrichmentCenter/DFCD-cyberdeck-files |
| Assembly video | https://www.youtube.com/watch?v=gIWp_F9PPzI |
| Hackaday feature | https://hackaday.com/2026/05/21/sliding-screen-cyberdeck-has-chunky-rugged-design/ |
| Hackster.io feature | https://www.hackster.io/news/why-buy-a-laptop-when-you-can-build-a-cyberdeck-46f56c0f558c |
| Circuitrocks build guide | https://blog.circuit.rocks/build-a-modular-raspberry-pi-5-cyberdeck-with-a-sliding-screen |

## Layout

```
cyberdeck/
├── hardware/        # Git submodule — DFCD upstream CAD files (3D print + CAD);
│   │                #   `git submodule update --remote` to pull upstream updates
│   ├── DFCD mesh files/   # .3mf files, ready to slice & print
│   ├── DFCD STEP files/   # editable CAD — open in FreeCAD to customise
│   ├── Dragchain step/    # dragchain CAD
│   └── Hardware list.md   # full bill of materials with purchase links
├── os/              # Our custom Raspberry Pi OS layer (see os/README.md)
│   │                #   works on Pi 4B and newer, Raspberry Pi OS 64-bit
│   ├── setup.sh     # one-shot installer (or install.sh for a TUI) — run with sudo
│   ├── boot/        # boot-script system (systemd unit + boot.d/: CPU governor, storage tuning)
│   ├── memory/      # zram swap + kernel VM tuning configs
│   ├── security/    # UFW firewall, SSH key-only hardening, kernel sysctls (base layer)
│   ├── theme/       # prompt, banner, fastfetch, tmux, desktop icons/wallpaper
│   ├── ai/          # opt-in: Claude Code + Ollama (memory-tuned) + earlyoom
│   ├── extras/      # opt-in: deck-mode, deck-vault (LUKS), deck-check, deck-ide, conky, SDR, Moonlight
│   ├── upgrades/    # opt-in: DECK assistant, USB HID, NAS, RFID, LoRa, scroll-handle, comms
│   └── image/       # bootable-image pipeline + CAD measurement scripts
├── hardware-custom/ # our parts (raised GFPIO lid, comms module) — upstream stays pristine
├── apps/            # your programs + programming utilities for the deck — see apps/README.md
│   │                #   grimoire (offline search+RAG), deck-gpio (HW prototyper), deck-* tools
├── docs/            # BUILD-GUIDE.pdf — illustrated 11-step assembly + commissioning guide
├── SIZING.md        # measured dimensions of every module (via FreeCADCmd)
├── BOM.md           # priced bill of materials with best-part picks
├── SHOPPING.md      # checkbox price checklists: Amazon (USD) + Shopee/Lazada (THB)
├── CHANGELOG.md     # every change to this project is logged here
└── AGENTS.md        # conventions for AI agents working on this project
```

## Hardware summary (see `hardware/Hardware list.md` for links)

- Raspberry Pi 5 8GB + Joy-IT power module + aluminium cooler case
- 10.1" IPS touch LCD, NOS C-450 TKL keyboard
- NP-F battery (7.2 V → 5.1 V), trackball (Logitech Marble donor), rotary encoder
- Assorted switches, LEDs, self-locking connectors, pogo pins, HDMI ribbon

## Workflow

1. **Customise parts** — open files from `hardware/DFCD STEP files/` in FreeCAD
   (installed on this PC, v1.1.1). Save modified versions into `hardware-custom/`
   (create it when needed) — never overwrite upstream files.
2. **Print** — slice the `.3mf` files from `hardware/DFCD mesh files/`.
3. **Flash the Pi** — Raspberry Pi OS (64-bit, with desktop — FreeCAD needs it)
   via Raspberry Pi Imager.
4. **Install the OS layer** — copy `os/` to the Pi and run `sudo ./setup.sh`
   (or `sudo ./install.sh` for a menu-driven TUI). The base install also hardens
   the deck (UFW firewall, SSH key-only, kernel sysctls) and tunes it for the
   field (CPU governor, storage I/O, noatime). Layer the opt-ins (`ai`, `extras`,
   `upgrades`) afterwards, then run `deck-check` to verify. Full docs in
   `os/README.md`.
