# Cyberdeck shopping checklists

Two checklists for the same build — buy each line from whichever side is
cheaper/faster for you. Prices are June 2026 **estimates** (Pi prices are
volatile right now); tick the box and write the real price when ordered.
Exact upstream product links: `hardware/Hardware list.md`. Specs rationale:
`BOM.md` / `SIZING.md`.

## Checklist A — Amazon (USD)

### Core
- [ ] Raspberry Pi 5 8GB (or 16GB for local LLMs) — ~$120–168 (8GB) / ~$205 (16GB)
- [ ] Official Pi 5 Active Cooler — ~$6–10
- [ ] Joy-IT power management board (Pi 3/4/5) — ~$30–40 *(or StromPi 3 equivalent)*
- [ ] SanDisk Extreme 64 GB microSD A2 — ~$12
- [ ] Official RTC battery (Pi 5 J5 connector) — ~$5 *(Pi 4 instead: DS3231 module ~$5)*
- [ ] Official M.2 HAT+ — ~$13–15 *(optional, Pi 5 only)*
- [ ] 256 GB NVMe SSD 2230/2242 — ~$30–40 *(optional)*

### Interface
- [ ] 10.1″ IPS touch LCD 1280×800, HDMI + USB touch — ~$60–75
- [ ] 60–65% mechanical keyboard, ≤310 mm wide — ~$45–60
- [ ] Logitech Trackman Marble (used/renewed, donor) — ~$20–35
- [ ] EC11 rotary encoder with push-click — ~$3
- [ ] NP-F970 10050 mAh battery ×2 (Neewer/Powerextra) — ~$40–60 each
- [ ] NP-F charger (dual-bay) — ~$20

### Electronics small parts
- [ ] Micro-HDMI 90° ribbon adapter + 50 cm HDMI ribbon — ~$8
- [ ] 16 mm momentary switches ×3 — ~$8
- [ ] 12 mm momentary ×1, 6 mm toggles ×2, slide switch ×1 — ~$8
- [ ] 12×12 tactile buttons ×10 — ~$5
- [ ] 3 mm LEDs ×4 + 330 Ω resistors — ~$5
- [ ] Aviation self-locking connectors: 0B-style ×6 pairs, 2B ×1, Y2M 8-pin ×2 — ~$40
- [ ] Pogo pins (battery contacts) ×2 — ~$3
- [ ] RTL-SDR Blog V4 + dipole antenna kit — ~$40 *(optional, AM/FM/SDR)*
- [ ] PN532 NFC/RFID module (I2C) — ~$5 *(optional, deck-rfid or comms module)*
- [ ] LoRa module **AS923 / 920–925 MHz** (RFM95W-class, SX1276) — ~$12 *(optional, deck-lora or comms module; AS923 is the Thailand-legal band — not US 915 / EU 868)*
- [ ] Raspberry Pi Pico (RP2040) — ~$4 *(optional, comms-module USB bridge)*
- [ ] SMA pigtail + 915/923 MHz whip antenna — ~$3 *(optional, comms-module LoRa)*

### Mechanical
- [ ] 8 mm steel rods ×2 + LM8UU-type bearings (screen slide) — ~$15
- [ ] M2.5 + M3 screw/insert assortment (heat-set) — ~$15
- [ ] 2-point tactical/camera sling, 38–50 mm webbing, QD hooks — ~$15–25
- [ ] PETG filament ×1.5 kg — ~$30

**Amazon total ≈ $530–650** (with optional NVMe + SDR; ~$430 without)

## Checklist B — Shopee / Lazada Thailand (THB)

*Same items, Thai-market estimates (~36 ฿/$). Electronics small parts are
dramatically cheaper here; the Pi itself often is not — compare with an
official Thai distributor (Cytron/ThaiEasyElec) before paying marketplace
markup.*

### Core
- [ ] Raspberry Pi 5 8GB — ~฿5,000–6,500 (shortage markup common; check Cytron TH)
- [ ] Pi 5 Active Cooler — ~฿250–350
- [ ] Pi power management board (Joy-IT/StromPi equivalent, X1200-series UPS HAT also works) — ~฿900–1,400
- [ ] SanDisk Extreme 64 GB A2 — ~฿350–450
- [ ] RTC battery for Pi 5 J5 / DS3231 module for Pi 4 — ~฿100–180 / ~฿50–90
- [ ] M.2 HAT+ (official or Waveshare clone) — ~฿450–700 *(optional)*
- [ ] NVMe SSD 256 GB 2242 — ~฿1,100–1,500 *(optional)*

### Interface
- [ ] 10.1″ IPS touch 1280×800 HDMI+USB — ~฿2,000–2,800
- [ ] 60–65% mech keyboard (Royal Kludge R65 class) — ~฿900–1,500
- [ ] Logitech Marble trackball (used, eBay/Kaidee if not on Shopee) — ~฿800–1,500
- [ ] EC11 encoder w/ click — ~฿30–60
- [ ] NP-F970 10050 mAh ×2 — ~฿900–1,400 each
- [ ] NP-F dual charger — ~฿400–600

### Electronics small parts
- [ ] Micro-HDMI ribbon kit — ~฿150–250
- [ ] 16 mm momentary ×3 + 12 mm ×1 + toggles ×2 + slide ×1 — ~฿200–350
- [ ] Tactile buttons ×10 + LEDs ×4 + resistors — ~฿80–150
- [ ] Aviation connectors set (0B ×6, 2B ×1, Y2M ×2) — ~฿900–1,400
- [ ] Pogo pins ×2 — ~฿60–100
- [ ] RTL-SDR V4 + antenna kit — ~฿1,200–1,600 *(optional; generic RTL2832U ~฿500 works for FM but is worse on AM)*
- [ ] PN532 NFC/RFID module (I2C) — ~฿180–250 *(optional, deck-rfid or comms module)*
- [ ] LoRa module **AS923 / 920–925 MHz** (RFM95W-class) — ~฿430–600 *(optional, deck-lora or comms module; AS923 = legal band in Thailand — confirm freq with seller)*
- [ ] Raspberry Pi Pico (RP2040) — ~฿70–120 *(optional, comms-module USB bridge)*
- [ ] SMA pigtail + whip antenna — ~฿100–180 *(optional, comms-module LoRa)*

### Mechanical
- [ ] 8 mm rods + LM8UU bearings — ~฿250–450
- [ ] M2.5/M3 screws + heat-set inserts assortment — ~฿250–400
- [ ] Tactical 2-point sling QD — ~฿250–500
- [ ] PETG 1.5 kg — ~฿500–700

**Shopee/Lazada total ≈ ฿17,000–23,500** (≈ $470–650; ~฿14,000 without optionals)

### Buying tips (TH marketplaces)
- Filter sellers by "ships from Thailand" — China-direct listings add 2–4 weeks.
- For the Pi specifically, Cytron Thailand / ThaiEasyElec list official pricing;
  marketplace sellers often add ฿800+ markup during shortages.
- Search terms that work well: "จอ 10.1 นิ้ว touch HDMI", "NP-F970 แบต",
  "rotary encoder EC11", "RTL-SDR V4", "สายสะพาย tactical".
