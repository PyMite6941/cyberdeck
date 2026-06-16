# Committed Upgrades layer (`os/upgrades/`)

Five opt-in upgrades, installed by one script after the base `setup.sh`:

```bash
sudo ./setup-upgrades.sh
```

Three are pure software (work the moment the script finishes); two need a cheap
part (~$17 total) and activate once you wire it and uncomment the bus in
`config.txt`. All idempotent, Pi 4B+ compatible, LF endings.

| # | Upgrade | Command | Needs |
|---|---|---|---|
| 1 | Offline AI assistant "DECK" | `deck-assistant` | software only |
| 2 | USB HID keyboard mode | `deck-hid` | software (+USB-C cable) |
| 3 | NAS file sharing over WiFi | `deck-nas` | software only |
| 4 | NFC/RFID reader (direct-wire) | `deck-rfid` | PN532 (~$5) |
| 5 | LoRa radio (direct-wire) | `deck-lora` | SX127x AS923 (~$12) |
| 6 | **Comms module** (NFC + LoRa, hot-swap) | `deck-comms` | PN532 + LoRa + Pico (~$21) |

**Two ways to add NFC/LoRa:** wire the parts straight to the Pi's GPIO header
(`deck-rfid` / `deck-lora`, simplest), **or** build the removable
**`comms-module/`** — a Pico-bridged clamp-on pod that hot-swaps on the rail
USB bus (`deck-comms`). The module is the recommended path; see
`comms-module/README.md`.

## 1. Offline assistant — `deck-assistant`

Pulls a pretrained model (`qwen2.5:3b` on 8GB+ Pi, `qwen2.5:1.5b` on 4GB) and
customises it with a **Modelfile persona** ("DECK", an offline deck assistant) —
this is *customisation, not training*. Real fine-tuning would happen on a bigger
machine; the result could then be copied over and `ollama create`d the same way.

```bash
deck-assistant "how do I open the encrypted vault?"   # one-shot
deck-assistant                                          # interactive chat
```

Edit the persona in `assistant/Modelfile`, then re-run the setup (or
`ollama create deck -f /opt/cyberdeck/Modelfile.deck`). Builds on the Ollama
install from `../ai/setup-ai.sh`; if Ollama isn't present, this script installs it.

## 2. USB HID keyboard mode — `deck-hid`

Makes the deck enumerate as a USB keyboard so it can type into another machine
over the USB-C cable — for automating your own boxes, provisioning a headless
machine, or accessibility. Standard `libcomposite` gadget; the kernel does the work.

```bash
sudo deck-hid on                 # creates /dev/hidg0, host sees a keyboard
deck-hid type "sudo reboot"      # types the string (US layout) — no sudo needed
deck-hid key 0x28                # send Enter (raw HID usage code)
sudo deck-hid off
```

A udev rule (installed by setup) lets `type`/`key` run without sudo once the
gadget is on. **Pi caveat:** device mode works on Pi 4 / Zero via dwc2 on the
USB-C power port; on **Pi 5 USB-C peripheral mode is limited — test before
relying on it.** Enable with `dtoverlay=dwc2,dr_mode=peripheral` (shipped
commented in `config-upgrades.txt`).

## 3. NAS mode — `deck-nas`

Shares `~/Share` over the network via Samba.

```bash
deck-nas user      # set your Samba password (once)
deck-nas on        # prints \\<deck-ip>\deck — open it from any PC/phone
deck-nas off
```

## 4. NFC/RFID — `deck-rfid` (needs a PN532)

PN532 in **I2C** mode: SDA=GPIO2 (pin 3), SCL=GPIO3 (pin 5), 3V3, GND. Uncomment
`dtparam=i2c_arm=on`, reboot, then:

```bash
deck-rfid read     # wait for one tag, print its UID
deck-rfid poll     # stream UIDs as tags appear
```

## 5. LoRa — `deck-lora` (needs an SX127x/RFM9x, AS923)

**Buy the AS923 (920–925 MHz) variant** — that's the band legal in Thailand. A US
915 / EU 868 module is illegal to transmit on here and may not tune. Wiring (SPI0):
SCK=11, MOSI=10, MISO=9, CS=CE1/GPIO7, RST=GPIO25, 3V3, GND. Uncomment
`dtparam=spi=on`, reboot, then:

```bash
deck-lora send "hello from the deck"   # default 923.0 MHz (AS923)
deck-lora recv 60                       # listen 60s
DECK_LORA_FREQ=868.0 deck-lora recv     # override band if you must
```

## Files

| File | Role |
|---|---|
| `setup-upgrades.sh` | orchestrator (installs all five) |
| `assistant/Modelfile` | DECK persona; `FROM` line is rewritten to the pulled model |
| `bin/deck-assistant` | Ollama persona wrapper |
| `bin/deck-hid` | USB HID keyboard gadget + `type`/`key` (embedded keymap) |
| `bin/deck-nas` | Samba share control |
| `bin/deck-rfid` | PN532 NFC reader (venv Python over I2C) |
| `bin/deck-lora` | SX127x LoRa send/recv (venv Python over SPI, AS923) |
| `config-upgrades.txt` | commented `dwc2`/`i2c`/`spi` enables appended to config.txt |

Python for the two hardware helpers lives in a venv at `/opt/cyberdeck/venv`
(Bookworm is externally-managed, so a venv is required — not system pip).
