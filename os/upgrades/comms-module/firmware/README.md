# Comms-module firmware (CircuitPython on a Pi Pico)

The Pico bridges the NFC + LoRa parts to the deck over USB serial.

## Flash

1. Download CircuitPython for the **Raspberry Pi Pico** (`.uf2`) from
   https://circuitpython.org/board/raspberry_pi_pico/ (9.x or later).
2. Hold **BOOTSEL**, plug the Pico into your PC; it mounts as `RPI-RP2`.
3. Copy the `.uf2` onto it. It reboots and remounts as `CIRCUITPY`.

## Install

Copy onto the `CIRCUITPY` drive:

```
CIRCUITPY/
├── boot.py            # from this folder — enables the USB data serial
├── code.py            # from this folder — the bridge
└── lib/
    ├── adafruit_pn532/         # from the CircuitPython library bundle
    ├── adafruit_rfm9x.mpy
    └── adafruit_bus_device/
```

Get the libraries from the matching **CircuitPython Library Bundle**
(https://circuitpython.org/libraries) — copy the listed items into `lib/`.

After copying `boot.py`, fully replug the Pico once so the second USB serial
(data CDC) appears — that's the port `deck-comms` talks to.

## Verify

- The `CIRCUITPY` drive present = firmware running.
- On the deck: `deck-comms status` → `NFC:ok LORA:ok` (or `absent` for anything
  not yet wired — the firmware tolerates either part missing).
- Serial console (optional debug): the *console* CDC is the normal REPL; the
  *data* CDC carries the protocol — don't confuse them.

## Tuning

- `LORA_FREQ` at the top of `code.py` defaults to **923.0 MHz (AS923 /
  Thailand)**. Match it to your module's band.
- Pin assignments are in the header comment of `code.py` and mirror
  `../README.md`.
