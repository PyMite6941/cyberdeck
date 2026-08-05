# Cyberdeck OS layer

A minimal, documented layer on top of stock **Raspberry Pi OS (64-bit, with desktop)**.
No custom image, no re-flashing to change things — everything is plain bash + systemd,
editable on the Pi or here and re-applied by re-running `setup.sh` (it is idempotent).

**Compatibility:** Raspberry Pi 4B (any RAM size) and newer, Raspberry Pi OS
Bookworm or later. `vcgencmd`, zram, and systemd behave identically on the 4B.
Pi 5 extras: PCIe Gen 3 NVMe tuning (`35-storage-tune.sh`), onboard RTC,
optional `temp_limit` in config.txt. On a 1–2 GB Pi 4, FreeCAD will run but
expect to lean on the zram swap heavily — 4 GB+ recommended.

## Install

```bash
# On this PC: copy os/ to the Pi (or git clone the project there)
scp -r os/ pi@<deck-ip>:~/cyberdeck-os
# On the Pi:
cd ~/cyberdeck-os && chmod +x install.sh && sudo ./install.sh
sudo reboot
```

`install.sh` is a **whiptail-based TUI installer** with DFCD branding, step
selection (base / AI / extras / upgrades), and progress gauges. It delegates
to the individual setup scripts.

Alternatively, run the plain `setup.sh` directly (no TUI, same result):
```bash
sudo ./setup.sh
```

**Prefer zero-touch?** Use the bootable-image pipeline in `image/` instead —
flash + `inject-to-sd.ps1` and the Pi installs all of this by itself on first
boot. See `image/README.md`.

`setup.sh` does six things:

| Step | What | Where it lands on the Pi |
|---|---|---|
| 1 | Packages: `git curl vim htop tmux dos2unix zram-tools ufw fastfetch` + **freecad** (with `--no-install-recommends`) | apt |
| 2 | Memory management (zram swap + VM tuning, SD swapfile retired) | `/etc/default/zramswap`, `/etc/sysctl.d/90-cyberdeck-vm.conf` |
| 3 | DFCD display/input config (commented dtoverlays: rotary encoder, GPIO buttons, safe shutdown, panel notes, PCIe Gen 3) | marker-guarded section in `/boot/firmware/config.txt` |
| 4 | Boot-script system | `/opt/cyberdeck/` + `/etc/systemd/system/cyberdeck-boot.service` |
| 5 | Theme (prompt, aliases, banner, fastfetch, tmux) | `/opt/cyberdeck/`, `/etc/update-motd.d/10-cyberdeck`, one line in `~/.bashrc`, `~/.tmux.conf` (if absent) |
| 6 | Security hardening + maintenance | UFW firewall, SSH key-only, kernel sysctls, journald size limit, boot-log rotation |

## Memory management

FreeCAD is the heaviest thing this deck runs, and the stock Pi OS setup
(100 MB swapfile on the SD card) handles memory pressure badly. `setup.sh`
replaces it (`os/memory/`):

- **zram swap** (`zram-tools`): a zstd-compressed swap device in RAM sized at
  50% of total RAM — roughly RAM/3 of extra effective memory at near-RAM speed.
  Pi 4 4GB → ~6 GB effective; Pi 5 8GB → ~10+ GB effective. Zero SD-card wear.
  On Pi 5 (4 cores), uncomment `NZM_NUM_DEVICES=4` in `zramswap.conf` for
  parallel compression streams.
- **VM tuning** (`/etc/sysctl.d/90-cyberdeck-vm.conf`): the kernel-documented
  settings for RAM-backed swap — `swappiness=180`, `page-cluster=0` (single-page
  reads suit zram), `watermark_boost_factor=0`, `watermark_scale_factor=125`.
- **dphys-swapfile disabled** — the SD-card swapfile is slow and wears out the
  card; zram replaces it. Re-enable with `sudo systemctl enable --now
  dphys-swapfile` if you ever want disk-backed overflow too.
- **journald capped** at 200 MB (`/etc/systemd/journald.conf.d/99-cyberdeck.conf`).
- **Boot log rotated** weekly via `/etc/logrotate.d/cyberdeck-boot`.

Check it's working after reboot: `swapon --show` (should list `/dev/zram0`)
and `free -h` (swap row = zram). The login banner also shows swap usage.

## Boot scripts — run custom code on every boot

Drop any executable `NN-name.sh` into `/opt/cyberdeck/boot.d/` on the Pi
(keep a copy in `os/boot/boot.d/` here so it's version-controlled):

Currently shipped boot scripts:

| Script | What it does |
|---|---|
| `10-example.sh` | Working example — replace or delete |
| `20-noatime.sh` | Adds `noatime` + `commit=600` to root mount (reduces SD wear, improves compile/git perf). Idempotent — checks before editing. Uses `awk` for safe fstab edits. |
| `30-cpugovernor.sh` | Sets CPU scaling governor to `performance` for best throughput in CAD/compilation/inference. `deck-mode` overrides this at runtime. |
| `35-storage-tune.sh` | Tunes I/O scheduler (BFQ for SD/eMMC, none for NVMe), enables TRIM/discard, adds `commit=600` to root fstab entry. |

```bash
sudo nano /opt/cyberdeck/boot.d/20-my-thing.sh
sudo chmod +x /opt/cyberdeck/boot.d/20-my-thing.sh
```

Rules:
- Scripts run **as root**, once per boot, after the network is up,
  in lexical order (`10-` before `20-`).
- A failing script is logged and skipped — it never blocks boot or other scripts.
- All output goes to `/var/log/cyberdeck-boot.log` (alias: `bootlog`).
- Test without rebooting: `sudo systemctl restart cyberdeck-boot.service`
- Test off-Pi: `BOOT_D=./boot.d LOG=/tmp/t.log bash cyberdeck-boot.sh`

`boot.d/10-example.sh` ships as a working example — replace or delete it.

## Bash is the deck's shell of record

Everything the deck adds — the prompt, `deck-lite`/`deck-gui`, `temp`, `fs`, the
`deck-ide` auto-resume — is bash, loaded from `~/.bashrc`. Under a different
login shell none of it exists and the deck comes up as a plain terminal, so
`setup.sh` **pins the login shell to bash** for both the deck user and root
(via `chsh`, only when it's actually wrong — re-running is a no-op) and wires
`/opt/cyberdeck/bashrc-cyberdeck.sh` into both accounts so `sudo -i` lands in
the same environment. Raspberry Pi OS already defaults to bash; this makes it
guaranteed rather than assumed.

That's also why the file explorer is bash: `pcmanfm` only exists on the desktop
image and disappears the moment you run `deck-ide` or `deck-lite`. See
**`deck-fs`** under Extras.

## Theme

- **Prompt** — green/cyan two-line prompt with exit-status indicator
  (`theme/bashrc-cyberdeck.sh`). Aliases/helpers: `ll`, `mem`, `bootlog`, `deck`,
  `temp` (SoC °C via `vcgencmd`, sysfs fallback), and `fs` (browse + cd, see
  `deck-fs`).
- **Login banner** — DFCD ASCII art + live host/ip/temp/mem/swap/disk/uptime,
  with the temperature coloured green/yellow/red at 65°/75°
  (`theme/motd.sh` → `/etc/update-motd.d/10-cyberdeck`).
- **fastfetch** runs once per interactive session using the themed
  `theme/fastfetch.jsonc` (green/cyan, shows CPU temp, memory, zram swap).
- **tmux** — matching green/black status bar (`theme/tmux.conf` → `~/.tmux.conf`,
  only installed if you don't already have one).

To change the look, edit the files in `theme/` and re-run `sudo ./setup.sh`
(or edit `/opt/cyberdeck/bashrc-cyberdeck.sh` and `/etc/update-motd.d/10-cyberdeck`
directly on the Pi — but mirror changes back here).

## AI layer (optional — `ai/setup-ai.sh`)

Run `sudo ./ai/setup-ai.sh` after the base setup to make the deck an AI
workstation. It is opt-in (not part of the image first-boot) because it adds
~2 GB of downloads. What it does:

- **Idle-RAM trim**: disables `cups`/`cups-browsed`/`ModemManager` (Bluetooth
  is kept for wireless peripherals) and installs **earlyoom** so a model that
  outgrows RAM+zram gets killed cleanly instead of freezing the deck
  (sshd/desktop are on earlyoom's avoid list — inference dies first).
- **Claude Code**: Node 22 (NodeSource) + `@anthropic-ai/claude-code`; run
  `claude` once to log in. Cloud-hosted, so it's fast even on a Pi 4.
- **Ollama, memory-tuned** via systemd override (`ai/` keeps the source):
  models auto-unload after 2 min idle, one model resident at a time, flash
  attention + q8_0 KV cache (~halves per-context RAM).
- **`deck-lite` / `deck-gui`** (in the shell theme): drop to console to free
  ~500 MB before a heavy inference run; restore the desktop after.

Model guidance: `qwen2.5-coder:3b` (Pi 5) / `qwen2.5:1.5b` (Pi 4). See
`../BOM.md` → "AI add-on" for the hardware side (16GB Pi, NVMe HAT, cooling).

## Extras layer (optional — `extras/setup-extras.sh`)

Physical-deck conveniences. Run `sudo ./extras/setup-extras.sh` after the base
setup. Adds:

- **`deck-mode stealth|work|bright`** — dim/normal/max screen + status-LED
  behaviour + **CPU governor switching** (powersave/ondemand/performance).
  gammastep dimming, ddcutil backlight where the panel speaks DDC. `show` mode
  now displays the active CPU governor.
- **`deck-vault init|open|close`** — a LUKS2-encrypted file container mounted at
  `/mnt/vault` (chosen over root FDE: no initramfs risk, headless-boot safe).
- **Conky status overlay** — always-on top-right panel (time/ip/temp/cpu/mem/
  swap/disk/uptime + **throttling warning** when `vcgencmd get_throttled` is
  non-zero), autostarted on the desktop. IP auto-detects wlan0 or eth0.
- **RTC** — Pi 5: plug the J5 battery; Pi 4: DS3231 + `i2c-rtc` overlay. Removes
  `fake-hwclock` only after verifying the RTC is functional (`hwclock -r`).
- **Status LED + radio** — `gpio-led` overlay (GPIO26 + 330Ω) driven by
  `deck-mode`; RTL-SDR tools (`rtl_fm`, gqrx) for AM/FM/SDR receive.
- **`deck-check`** — read-only health check: verifies **hardware OpenGL** (V3D,
  not `llvmpipe` software fallback — the #1 FreeCAD performance killer), zram
  active, swappiness, thermals/throttling, CPU governor, and optional hardware
  (encoder, Ollama, RTC). Installs `mesa-utils` for `glxinfo`. `--quiet` for a
  one-line summary; exits non-zero on any FAIL.
- **`deck-help [section]`** — coloured reference of every deck command (only
  shows commands actually installed).

## Programming optimizations for the deck

Developing on a 10.1" screen with an ARM CPU means optimising TUI, AI
performance, and storage. These are built into or documented alongside the
existing layer:

### TUI maximalism

- **Tmux** (`theme/tmux.conf`) — green-on-black status bar, mouse on, 256-color.
  Extend with keybindings for a development layout (code + logs + Claude Code):
  ```
  bind-key -n M-C split-window -h \; send-keys 'claude' Enter
  bind-key -n M-M split-window -v \; send-keys 'htop' Enter
  ```
- **`deck-lite` / `deck-gui`** (theme bashrc) — drop to console multi-user.target
  to free ~500 MB; restore the desktop when needed. Survives reboot.
- **`deck-ide`** (`extras/bin/deck-ide`) — drops the desktop (kills the display
  manager, frees ~2 GB), starts a tmux session with Neovim (left 60%),
  Claude Code (right-top), and htop (right-bottom). Run `deck-desktop` to
  restore the GUI. Both installed by `setup-extras.sh`.

### Ollama performance tuning (model level)

The AI layer's systemd override handles memory-level tuning. For **code generation**
performance, constrain the model at pull/create time:

- **Quantization**: use `Q4_K_M` or `IQ4_XS` (4-bit) only — keeps the model
  in RAM without hitting swap.
- **Context window**: set `num_ctx 2048` or `4096` in `Modelfile` or API calls.
  Higher = drastically slower tok/s on ARM.
- **Thread pinning**: set `num_thread 4` in `Modelfile` — Pi 5 has 4 performance
  cores; letting the LLM fight system threads stutters the whole OS.

A helper script (`ai/tune-ollama.sh`) automates this — run it after
`setup-ai.sh` to create a `deckcoder` model with optimal Pi settings:
```bash
sudo ./ai/tune-ollama.sh qwen2.5-coder:3b   # creates tuned "deckcoder" model
```

### Flash storage optimization

Compiling code and pulling git branches cause thousands of tiny writes. If
running from an SD card:

- **noatime + commit=600** are applied automatically by `20-noatime.sh` and
  `35-storage-tune.sh` on every boot (noatime stops "last accessed" writes;
  commit=600 delays ext4 journal flushes to 10 min — both reduce wear).
- **I/O scheduler** auto-tuned per device by `35-storage-tune.sh`: BFQ for
  SD/eMMC (better desktop responsiveness), `none` for NVMe (best throughput).
- **NVMe TRIM/discard** enabled automatically if a NVMe root is detected.
- **PCIe Gen 3** (Pi 5 only): uncomment `dtparam=pciex1_gen=3` in config.txt
  to double NVMe throughput (~500 → ~800 MB/s).

## Virtual parts layer (optional — `extras/setup-virtual.sh`)

"Hardware" that's real but lives elsewhere on the network — the deck stays light
and borrows power on demand. Run `sudo ./extras/setup-virtual.sh`.

- **Moonlight (virtual GPU)** — pairs with **Sunshine** on a home PC and streams
  its GPU output to the deck at near-zero LAN latency. A 12 W Pi effectively
  "has" your desktop's GPU whenever it's on your Wi-Fi — best path for CAD
  rendering or heavy local-LLM work without carrying a dGPU.
- **`deck-ide`** / **`deck-desktop`** — headless IDE toggle. `deck-ide` drops
  the desktop, kills the display manager (~2 GB freed), and starts a tmux
  session with Neovim + Claude Code + htop. `deck-desktop` restores the GUI.
- **`deck-fs`** — the file explorer, written in bash: no python, no ncurses, no
  deps beyond coreutils, so it works on the console after `deck-ide`/`deck-lite`
  when `pcmanfm` is gone. `j/k` move, `l`/`h` in and out, `e` edit, `v` view,
  `/` filter, `.` toggle hidden, `c` copy path, `x` run a command on the
  selection, `q` quit. It prints the directory you quit in and nothing else, so
  `cd "$(deck-fs)"` works — the `fs` shell function does exactly that, which is
  the everyday way to use it (an alias can't work; a subshell can't `cd` its
  parent).
- **`deck-drive`** — attach network/cloud storage as a local disk:
  - `deck-drive iscsi <nas-ip>` → a NAS target appears as `/dev/sdX` (partition,
    format, even put a `deck-vault` on it).
  - `deck-drive cloud <remote:path>` → `rclone` mount at `~/CloudDrive`
    (run `rclone config` once first).
  - `deck-drive list | off` → show / detach everything.

These pair naturally with the v2 compute ideas in `../BOM.md`: even a Pi can
feel like it has a GPU + terabytes of disk when docked on the home LAN.

## Committed Upgrades layer (optional — `upgrades/setup-upgrades.sh`)

User-requested upgrades — see `upgrades/README.md` for full usage:

- **`deck-assistant`** — offline Ollama persona "DECK" (pulled model + Modelfile
  customisation, not training).
- **`deck-hid`** — USB HID keyboard mode; type into another machine over USB-C
  (Pi 4/Zero solid; Pi 5 USB-C device mode is limited — test first).
- **`deck-nas`** — Samba share of `~/Share` over WiFi.
- **`deck-rfid`** — PN532 NFC reader over I2C (needs the ~$5 module).
- **`deck-lora`** — SX127x LoRa, defaulting to 923 MHz **AS923 (Thailand-legal)**
  (needs the ~$12 module — buy the AS923 variant).
- **`deck-scroll`** — scroll-handle daemon: reads the rotary encoder and maps
  turns to **FreeCAD zoom** when FreeCAD is focused, **system volume** otherwise.
  Runs as a `systemctl --user` service; needs `python3-evdev` + `xdotool`.
- **`deck-comms`** — client for the Pico-bridge comms module (NFC + LoRa
  presented as one USB serial device — see `upgrades/comms-module/`).

Hardware helpers use a venv at `/opt/cyberdeck/venv`; bus enables ship commented
in `upgrades/config-upgrades.txt`.

## Security

The base layer (`setup.sh` step 6) installs and configures:

- **UFW firewall**: default-deny incoming, allow SSH/Samba/Moonlight from LAN
  subnets only (192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12).
- **SSH hardening** (`/etc/ssh/sshd_config.d/99-cyberdeck.conf`): key-only
  auth, no root login, 3-auth-try limit, 5-min client alive interval.
- **Kernel sysctls** (`/etc/sysctl.d/90-cyberdeck-security.conf`): reverse-path
  filtering, source-route rejection, dmesg/kptr restriction, ptrace scope
  (`kernel.yama.ptrace_scope=1`).

Stealth mode (`deck-mode stealth`) also switches the CPU governor to
`powersave`, reducing power and thermal signature.

## Design constraints (for humans and AI agents)

1. **Minimal** — stock Raspberry Pi OS underneath; this layer is a few dozen
   small files. Don't add packages beyond what a script actually needs.
2. **Idempotent** — `setup.sh` must always be safe to re-run. Use marker-guarded
   appends and `[[ -e ]]` checks; never blind-append or blind-overwrite user files.
3. **Never overwrite Pi-side customisations** — `setup.sh` skips `boot.d/` scripts
   that already exist on the Pi.
4. **Document every change** in `../CHANGELOG.md`.
5. **LF line endings** for all `.sh` files (enforced by `.gitattributes`;
   `setup.sh` also runs `dos2unix` defensively).
