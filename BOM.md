# Cyberdeck bill of materials — best picks & prices

Prices are June 2026 estimates in USD (note: Pi prices are inflated right now
by the DRAM shortage — see notes). Upstream links for every item are in
`hardware/Hardware list.md`; size constraints behind each pick are in `SIZING.md`.

## Core electronics

| Role | Best pick | Why | Est. price |
|---|---|---|---|
| Compute | **Raspberry Pi 5 8GB** | FreeCAD wants RAM + the Pi 5's faster single-core; deck chassis fits it natively | ~$120–168 (shortage pricing; MSRP was $80) |
| Compute (budget) | Raspberry Pi 4B 4GB | Same footprint/mounts; our OS layer fully supports it (zram makes FreeCAD viable); rear port cutouts differ slightly | ~$55–65 |
| Power management | **Joy-IT power supply module** (per upstream BOM) | Takes the battery's 7.2 V, gives clean 5.1 V/5 A, safe shutdown button support | ~$30–40 |
| Cooling | **Joy-IT aluminium armor case / official active cooler** | The chassis is vented for it; Pi 5 throttles at 85 °C without it under FreeCAD load | ~$15–25 |
| Storage | SanDisk Extreme 64 GB microSD (A2) | A2 random-IO rating matters for desktop use; 64 GB leaves room for CAD files | ~$12 |

## Interface hardware

| Role | Best pick | Why | Est. price |
|---|---|---|---|
| Screen | **10.1″ IPS touch LCD, 1280×800, HDMI + USB touch** (AliExpress, per BOM) | The 335 mm screen bay is built around exactly this panel size; USB-HID touch needs no driver | ~$60–75 |
| Keyboard | **NOS C-450 Mini Pro RGB** (or any 60–65% mech ≤ 310 mm wide) | Keyboard bay maxes out at ~315 mm — a TKL won't fit despite the upstream BOM naming one | ~$45–60 |
| Trackball | **Used Logitech Trackman Marble** (donor for PCB + 40 mm ball) | Trackball module is dimensioned for this exact PCB; author plans custom electronics later | ~$20–35 used |
| Scroll handle | **EC11 rotary encoder with push-click** | Standard part, fits the encoder mount; wired to GPIO (see `os/image/config-additions.txt`) | ~$2–3 |
| Battery | **Neewer/Powerextra NP-F970 10050 mAh** (USB-C versions exist) | Battery module is moulded for NP-F; brand-name Jupio Ultra C is ~$155 — the ~$40 clones are the value pick; get 2 for hot-swap | ~$40–60 (×2 ≈ $90) |

## Connectors & small parts (mostly AliExpress)

| Item | Qty | Est. price |
|---|---|---|
| 0B-style self-locking connectors (module power/signal) | 6 pairs | ~$25 |
| 2B self-locking connector (battery) | 1 | ~$10 |
| Y2M 8-pin aviation connectors | 2 pairs | ~$6 |
| Pogo pins GF50 (battery contacts) | 2 | ~$3 |
| 16 mm momentary switches ×3, 12 mm ×1, toggles ×2, slide ×1 | — | ~$12 |
| 12×12 tactile buttons ×10, 3 mm LEDs ×4 | — | ~$5 |
| Micro-HDMI 90° ribbon + 50 cm HDMI ribbon kit | 1 | ~$8 |
| 8 mm steel rods + bearings (screen slide), M3 hardware, springs, wire | — | ~$25 |

## AI add-on (optional — for Claude Code + local LLMs, see `os/ai/`)

| Role | Best pick | Why | Est. price |
|---|---|---|---|
| Compute | **Pi 5 16GB** (instead of 8GB) | LLM speed on a Pi is bound by memory bandwidth + RAM size; 16GB runs 7–8B Q4 models with the desktop still up | ~$205 (shortage pricing) |
| Storage | **Official M.2 HAT+ plus 256GB NVMe SSD** (Pi 5 only) | ~800 MB/s vs ~90 MB/s SD: model load drops from minutes to seconds, and swap-on-NVMe actually works; boot from it entirely | ~$15 + $30–40 |
| Cooling | **Official Active Cooler** (mandatory for sustained inference) | LLM generation pins all 4 cores for minutes; without it the Pi throttles at 85 °C and tok/s halves | ~$6–10 |
| Power | Second NP-F970 battery | Sustained inference pulls ~10–12 W — roughly halves battery runtime | ~$40 |

**What NOT to buy:** the Raspberry Pi AI Kit / AI HAT+ (Hailo-8L, 13–26 TOPS)
and Coral TPUs only accelerate **vision** models (object detection etc.) —
they do **not** speed up LLMs at all. There is currently no practical LLM
accelerator for the Pi; the CPU does the work.

**Honest expectations (CPU inference, Q4 models):** Pi 5 ≈ 8–12 tok/s on 3B,
2–4 tok/s on 7–8B; Pi 4 ≈ half that — fine for short answers, not for long
sessions. Claude Code itself is cloud-hosted and runs perfectly on either Pi;
local models are the offline fallback.

## Consumables

| Item | Est. price |
|---|---|
| ~1.5 kg PETG filament (PLA works; PETG handles workshop heat better) | ~$25–35 |

## Totals

- **Recommended build (Pi 5 8GB)**: ≈ **$430–530** at today's shortage prices
- **Budget build (Pi 4B 4GB + single clone battery)**: ≈ **$330–380**
- The single biggest lever is the Pi itself — if the DRAM-shortage pricing
  (8GB at ~$168 vs $80 MSRP) annoys you, the Pi 4B route loses surprisingly
  little: the OS layer's zram config was tuned for exactly that case.

Sources: [raspberrypi.com price update](https://www.raspberrypi.com/news/more-memory-driven-price-rises/),
[Tom's Hardware on Pi 5 shortage pricing](https://www.tomshardware.com/raspberry-pi/raspberry-pi-5-price-increases-drastically-as-ai-shortage-bites-16gb-version-now-usd205-second-price-increase-in-three-months-over-70-percent-more-expensive-than-original-msrp),
[Jupio NP-F970 Ultra C](https://jupious.com/jupio-np-f970-ultra-c-usb-c-20w-pd-input-output-10050mah/),
[Neewer NP-F970 2-pack](https://neewer.com/products/neewer-2-pack-10050mah-np-f970-replacement-battery-charger-set-66601966).
