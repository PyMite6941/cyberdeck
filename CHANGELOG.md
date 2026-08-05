# Changelog

Every addition/change to this project gets an entry: date, who (human or agent), what, why.

## 2026-07-31 — Claude (deck-store app store + 3 new apps; grimoire vendored; install.sh convention)

Added an app store, three new apps, and reworked the vendoring convention so
vendored apps get private venvs, cache-cleaning updates, and commit tracking.

- **apps/deck-store/** — new app store, CLI + Textual TUI (cyberdeck theme).
  Browse a `registry.json` catalog, see per-app **install status** (`✓` current,
  `⟳` update available, `○` not installed, `◆` built-in), install vendored apps
  (clone + private venv), and refresh to check remotes. Tracks **which git
  commit is loaded** per vendored app; when any is behind, an **Updates tab**
  appears and `u` upgrades (fast-forward → wipe caches → re-sync venv). State
  cached in gitignored `state.json`. Modules: `store/registry.py`,
  `store/appstate.py`, `store/actions.py`. Verified: CLI (list/info/refresh) +
  headless Textual compose/tab-filter/detail.
- **apps/deck-sensors/**, **apps/deck-radio/**, **apps/deck-serial/** — three new
  apps, each CLI + themed Textual TUI, degrade gracefully off-Pi. Sensors uses
  `deck-lib/pi_sensors`; radio wraps the rtl-sdr toolchain; serial is a pyserial
  UART monitor. All three headless-compose-tested.
- **apps/deck-lib/deck_theme.py** — shared cyberdeck Textual theme (cyan/phosphor
  palette) + CSS + status glyphs, so new apps share one look. Safe no-op on
  Textual builds without the theme API.
- **Vendoring reworked (`apps/_vendor_launcher.sh`)** — vendored apps now split
  into **`install.sh`** (bootstrap/updater) + **`run.sh`** (launcher). Each gets
  a **private venv at `src/.venv`** (isolated from the shared `apps/.venv`);
  after a successful update pull, **caches are wiped** (`__pycache__`/`*.pyc` +
  configurable `.update-clean` globs) and the venv re-synced. Applied to
  security-suite and grimoire. New `vendor_python` helper.
- **grimoire vendored** — extracted the app to its own repo
  [PyMite6941/grimoire](https://github.com/PyMite6941/grimoire) (public) and
  replaced apps/grimoire with an install.sh/run.sh launcher; the 5.1 GB
  corpus/tome was preserved locally by moving it into the gitignored `src/`
  clone. Added **`import_data.py`** to the repo: pulls public-domain texts from
  **Project Gutenberg** (gutendex API), **Wikisource**, and lists Standard
  Ebooks, optionally folding them into the tome — verified against the live API
  (searched + downloaded a real book).
- **apps/.gitignore** — the earlier generic `*/src/` + `*/.check-updates` rules
  already cover every vendored app's clone and private venv; added
  `deck-store/state.json`.

### Follow-up the same day — deck-store hardening (Claude)

Drove the store headlessly (`App.run_test`) plus an end-to-end install/upgrade
test against a throwaway local git repo. That turned up five real defects:

- **Long jobs no longer freeze the UI.** `git clone`, `pip install` and
  `git fetch` ran on the event loop, so the store locked up for the whole
  install (minutes, on a Pi). They now run on Textual worker threads with every
  UI touch marshalled back through `call_from_thread`; per-app progress streams
  to the status bar, and a `busy` guard stops jobs overlapping.
- **The colour scheme was inert.** `[ok]`/`[warn]`/`[title]`/`[big]`/`[primary]`
  markup resolves against *colour* names, not the stylesheet, so anything tagged
  that way rendered in the default foreground. Added `DECK_MARKUP` + `styled()`
  to `deck-lib/deck_theme.py` (style strings, so `big` keeps its bold) and moved
  every call site onto it. **All four themed apps were affected** — deck-store,
  deck-radio, deck-serial, and deck-sensors, where `[big]` meant the entire
  sensor-card readout (every temp/humidity/pressure value) was unstyled.
  A headless probe now renders each `DECK_MARKUP` name and asserts it resolves
  to an on-palette colour, plus a source audit that fails on any leftover inert
  tag or hardcoded hex.
- **The store opened with nothing selected.** `ListView.clear()`/`append()` only
  *schedule* the un/mounts, so the index was being assigned to a still-empty
  list. Selection is now tracked on the app itself (authoritative and available
  immediately, so an action fired right after a filter can't hit a stale
  widget), with the highlight bar catching up on the next refresh.
- **The Updates tab reset the view.** It was rebuilt by clearing the entire tab
  bar, dropping the user back to "All" after every refresh; it is now inserted
  and removed in place, preserving the active tab.
- **`uninstall` was unreachable and lied on failure.** It had no CLI command and
  no key binding, and `rmtree(ignore_errors=True)` reported success even when
  git's read-only objects left a half-deleted `src/` (which then breaks the next
  clone). It now chmod-and-retries, reports honestly, and is wired up as
  `deck-store uninstall <id>` (prompts; `--yes` to skip) and `x` in the TUI —
  **two presses to confirm**, because `src/` is where grimoire keeps its tome
  and every imported corpus.

### security-suite "advanced tools" — NOT in this repo (Claude)

⚠️ These changes are in `apps/security-suite/src/`, which is a **gitignored
vendored clone** of [PyMite6941/Security-Suite]. They are *not* tracked here and
must be committed and pushed from inside that clone or they are one
`rm -rf src/` from gone. Noting them here because they also explain why that
clone is dirty — `install.sh` will refuse to fast-forward until it's clean.
(It already was dirty before this work: `.gitignore`, `frontend/cli.py`,
`frontend/cool-app.py` and `requirements.txt` all had uncommitted edits.)

- **`backend/advanced tools/log_parser.py` was an empty file** — written. Regex
  parser for auth/system logs, stdlib only (it has to run on a machine that is
  already having a bad day). Parses sshd/sudo/su/useradd/PAM/UFW lines from
  syslog, `journalctl -o short-iso`, or prefix-less `-o cat`, then *correlates*:
  sliding-window brute force, credential spraying across usernames, privilege
  changes, and success-after-failures — a brute force that stops is a brute
  force that worked. `--findings` exits 2 on high/critical so it can gate a
  scheduled check. Unmatched lines are dropped on purpose: this is a detector,
  and auth.log is mostly chatter that would bury the signal.
- **`ai_phishing_detector.py` could not train at all.** `PATH_ROOT` was the
  `advanced tools/` directory, so `DATA_PATH` resolved to
  `backend/advanced tools/tests/urls.csv`, which does not exist — training died
  with FileNotFoundError and `save_model` would have scattered a stray `models/`
  in there. Re-anchored on the app root. Also fixed a `UnicodeEncodeError` that
  killed the CLI at startup whenever the checkout path contains non-ASCII
  characters (it prints `MODEL_PATH`) on a legacy-codepage console.
- **`tests/urls.csv` expanded 4 → 106 rows** (53/53 balanced, no duplicates).
  Four rows could not train anything: a 25% split left a single test sample.
  First pass hit 97.4% CV but still called `http://paypal-verify-login.tk/secure`
  *safe* — every phishing example was long, so the model learnt "long = bad"
  instead of the suspicious TLD. Added short phishing URLs and long legitimate
  ones so the length distributions overlap; that URL now scores 0.93 and a
  held-out set of 10 URLs never seen in training classifies 10/10. 5-fold CV
  93.4% (worst fold 90.5%) — lower than the first pass and more honest, since
  the easy length shortcut is gone.

### Bash as the deck's root environment (Claude)

The deck is console-first — `deck-ide`/`deck-lite` kill the desktop on purpose —
but two things quietly assumed a GUI or a particular shell:

- **`os/setup.sh` now pins the login shell to bash** for the deck user *and*
  root, and wires `bashrc-cyberdeck.sh` into root's `~/.bashrc` too. Everything
  the deck adds (prompt, `deck-lite`/`deck-gui`, `temp`, `fs`, the `deck-ide`
  auto-resume) loads from `~/.bashrc`; under sh/dash/zsh none of it existed and
  `sudo -i` dropped into a bare shell. Raspberry Pi OS defaults to bash, but
  that was an assumption, not a guarantee. Idempotent — `chsh` only runs when
  the shell is actually wrong, and `/etc/shells` is topped up first.
- **`os/extras/bin/deck-fs`** — new file explorer written in bash (no python, no
  ncurses, coreutils only), because `pcmanfm` only exists on the desktop image
  and vanishes the moment you go headless. Vim-style keys, dirs-before-files,
  filter, hidden toggle, `$EDITOR`/pager handoff, copy-path, run-command-on-
  selection. It prints only the directory you quit in, so `cd "$(deck-fs)"`
  works; the new `fs` function in `bashrc-cyberdeck.sh` wraps that (it has to be
  a function — a subshell can't `cd` its parent). Installed by
  `setup-extras.sh`, listed in `deck-help`.
  Verified by driving the real key loop headlessly: navigation in/out/home/last,
  the `cd "$(…)"` stdout contract, case-insensitive filter, empty-filter and
  empty-directory safety, hidden toggle, and filenames containing spaces.

**apps/deck-lib/log_parser.py** — new regex log parser (stdlib only, so it runs
anywhere on the deck). Recognises journald/syslog, kernel dmesg, Python
`logging`, nginx/combined access logs, ISO-stamped app logs and deck-serial's
UART captures, normalising each into a `LogEvent` (ts / level / source / msg /
fields). Unrecognised lines are kept as `fmt="raw"` rather than dropped — on a
field deck the line you can't classify is usually the one you needed. Also folds
Python tracebacks (including the unindented final exception line) into the one
ERROR they belong to, promotes level-less "Failed to start …" syslog lines to
ERROR, derives severity from HTTP status, and `fingerprint()`s messages so
recurring events group in `--stats`. Timestamps normalise to naive UTC and
year-less/time-only stamps get dated against today, since strptime otherwise
lands them in 1900 and wrecks any sort or timespan. CLI:
`log_parser.py FILE… [--level --source --grep --fmt --json --stats]`, `-` reads
stdin. Verified with a 40-check suite over samples of every supported format
plus the CLI surface.

Also: `run_tui` split into `build_store_app()` so the TUI can be driven
headlessly; unknown app ids now report instead of failing silently. Every
launcher (`deck-radio`, `deck-sensors`, `deck-serial`, `deck-store` `run.sh` and
`grimoire`/`security-suite` `install.sh`) is now recorded **100755** — this repo
sets `core.fileMode=false`, so the bit has to be set with
`git update-index --chmod=+x` or the scripts land non-executable on the Pi.

## 2026-07-02 � Claude (generalized vendor-app auto-update into pps/_vendor_launcher.sh)

Extracted the clone/fetch/summarize/prompt logic just built for
security-suite/run.sh into a shared, sourceable library,
pps/_vendor_launcher.sh (mirrors the existing pps/_run_helper.sh
pattern), so any future app whose real code lives in an external repo can
reuse it instead of duplicating the script.

- **pps/_vendor_launcher.sh** � new shared helper exposing endor_sync
  <label> <repo-url> <src-dir> "$@": clone-on-first-run, fetch + prompt
  with a change summary on later runs (interactive only, fast-forward
  only), --check-updates=on/off toggle.
- **pps/security-suite/run.sh** � rewritten to source the shared helper
  instead of inlining the logic; behavior unchanged (re-verified against a
  local fake-upstream repo: clone, decline, accept, toggle off/on).
- **Docs**: pps/README.md gained a "Vendoring an external app" section;
  pps/security-suite/README.md and AGENTS.md cross-reference it.
- **Explicit scope note (per user request)**: this auto-update-check-and-
  prompt pattern is an pps/-only convention. The os/ layer is never
  managed this way � it only changes when a human deliberately re-runs the
  installer for an actual functionality or security update, never via a
  background/automatic check.

## 2026-07-02 � Claude (security-suite: submodule ? self-updating launcher)

Replaced the pps/security-suite git submodule with a self-updating
launcher script. Motivation: the submodule pinned an exact commit of
PyMite6941/Security-Suite in this repo's history, so checking whether that
pin was stale (or updating it) required cross-repo GitHub access this repo's
sessions don't always have � the pin silently drifted out of sync with no
easy way to notice.

- **Removed**: pps/security-suite submodule entry (.gitmodules,
  .git/config, the gitlink itself).
- **Added pps/security-suite/run.sh** � thin launcher, not the app: first
  run clones Security-Suite into src/ (gitignored, a live clone the deck
  manages); every later run fetches origin, and if there are new commits,
  prints a one-line-per-commit summary and asks Update now? [y/N] before
  launching (fast-forward only � never touches local edits in src/).
  Non-interactive runs (no TTY) skip the check instead of blocking.
- **Toggle**: un.sh --check-updates=off stops the prompt (persists in
  .check-updates, gitignored); --check-updates=on resumes it.
- **pps/security-suite/README.md** � documents the above.
- **pps/README.md** / **pps/.gitignore** updated to match.

## 2026-07-02 � Claude (checklist/doc-sync review)

Ran a review pass (security/permissions, shopping-list & BOM completeness,
doc/tree sync) to catch anything the 2026-06-16 audit missed. Findings and fixes:

- **CHANGELOG.md** � backfilled the missing entry for the 2026-06-16 audit-fixes
  commit (added below), which had no changelog entry of its own.
- **pps/README.md** � added the undocumented pps/deck-lib/ shared-helpers
  folder to the app list, tree, and roadmap.
- **SHOPPING.md** � added a USB microphone line item (both checklists);
  pps/deck-whisper records via PyAudio and had no mic anywhere in the parts
  lists.
- **BOM.md** � added the comms/radio subsystem (RTL-SDR, PN532, LoRa module,
  Pi Pico, SMA antenna) that SHOPPING.md already priced but BOM.md omitted
  entirely; added the microphone; clarified Y2M connector count (was ambiguous
  "2 pairs" vs SHOPPING.md's "x2" � confirmed 2 units per BUILD-GUIDE).
- **.gitignore** � added .env/*.env proactively (none currently tracked,
  but nothing was excluding them either).
- Verified clean, no action needed: file permissions (all scripts still
  +x), no secrets or personal-machine paths committed, os/security/*
  firewall/SSH/sysctl hardening still correct.
- **Open item, not fixed**: os/image/make_led_button.py, inspect_screenframe.py,
  and inspect_buttons.py still reference Rigth screen frame.3mf / ...rigth
  retainer.3mf as **input** filenames from the hardware/ submodule (not
  Right). Left alone because those paths must match the submodule's actual
  filenames, which weren't checked out to verify � confirm against upstream
  before renaming.

## 2026-07-01 � Agent (deck-settings: unified system configuration TUI)

**New pps/deck-settings/** � full-featured Textual TUI for managing every
aspect of the deck:
- **Network & WiFi** � scan visible networks, check connection status and IP
- **Storage** � disk usage, zram compression stats, mount points
- **Apps** � list installed project apps with launcher availability
- **System** � hostname, per-core CPU governor switching (P/O/S/C keys),
  display mode (calls deck-mode), uptime & temperature
- **Security** � deck-vault status/open/close, fingerprint scanner status,
  SSH service + configuration status, UFW firewall status
- **About** � Pi model, kernel, OS version, memory, disk, temp, uptime

**New os/extras/bin/deck-settings** � launcher that auto-deploys the app on
first run from /opt/cyberdeck/lib/deck-settings/ to ~/.local/share/deck-settings/.
Installs textual if missing.

**New os/extras/lib/deck-settings/deck-settings.py** � the Textual app source,
deployed by setup-extras.sh to the staging lib directory so it's included in the
bootable SD card image via the inject-to-sd.ps1 pipeline.

**Modified os/extras/setup-extras.sh** � installs deck-settings command +
copies lib. Updated "Done" summary.

**Modified os/extras/bin/deck-help** � added deck-settings to System Commands
section.

**Modified pps/README.md** � added deck-settings to the app listing, directory
tree, and roadmap table.

## 2026-07-01 � Agent (biometric fingerprint scanner support)

**New os/upgrades/biometrics/** � opt-in biometric authentication layer:
- in/deck-biometric � GT-521F32 / R307 / R503 UART fingerprint scanner driver
  with enroll/verify/identify/list/delete/clear/vault-open commands. Implements
  the FPS_GEN2 protocol over pyserial, stores templates on-sensor (never leaves
  the module), keeps local name->ID mapping in ~/.deck-biometric/enrollments.json.
  ault-open integrates with deck-vault for fingerprint-based unlock.
- setup-biometrics.sh � installs pyserial, deploys command, adds user to
  dialout group, appends commented enable_uart=1 to config.txt.
- iometric.service � optional systemd oneshot unit for boot-time status.
- README.md � hardware wiring (VCC->3.3V, GND->GND, TX->GPIO15, RX->GPIO14),
  commands, vault integration, security notes.

**Hardware CAD** hardware-custom/Biometrics/make_fingerprint_mount.py �
parametric FreeCAD generator for a 3D-printed scanner bracket, supporting
GT-521F32 and R307 footprints with M2 screw bosses and deck mounting holes.

**Modified os/upgrades/setup-upgrades.sh** � added step [7/7] calling
biometrics sub-installer. Header updated to list all 7 upgrades.

**Modified os/upgrades/config-upgrades.txt** � added commented UART enable
lines for the fingerprint scanner under # --- CYBERDECK-BIOMETRICS ---.

**Modified os/upgrades/README.md** � added biometrics to the upgrade table,
new section 6 with wiring table and commands, Files table updated.

**Modified SHOPPING.md** � added GT-521F32 (~-30) and R307 (~-18) to
both Amazon and Shopee/Lazada checklists.

**Modified BOM.md** � added "Biometrics add-on" section with scanner picks,
mounting notes, and threat-model disclaimer (convenience, not high-security).

## 2026-06-16 � Agent (post-publish audit fixes)

## 2026-06-16 — Agent (repo made public on GitHub)

- **Root git repo initialised** — `git init`, root `.gitignore` covering
  `.venv/`, `__pycache__`, `*.db`, `*.zim`, `backend/data/`, `*.log`, IDE files.
- **`hardware/` added as submodule** — pins upstream DFCD repo at commit
  `272993758189413395c9b90dbe2b95d7d6134cbd`.
- **`apps/security-suite/` added as submodule** — pins at `d82b193` (includes
  bugfixes from 2026-06-14 that were committed & pushed to its remote).
- **README updated** — added proper attribution to Jankbu's DFCD design with
  all source links (GitHub, YouTube, Hackaday, Hackster.io, Circuitrocks).
- **AGENTS.md updated** — `hardware/` is now a submodule, not a bare clone.
- **security-suite bugfixes pushed to remote** — vault paths, Textual TUI, Linux
  venv activation, rockyou.txt gitignored.

## 2026-06-14 — Claude (doc sync: root README + os/README caught up to current layers)

Audited all docs after the BUILD-GUIDE refresh — the guide was not the only
stale doc. Fixed:

**Root `README.md`** (was most behind — no security mention at all):
- Added `os/security/` to the layout tree (UFW firewall, SSH hardening, sysctls).
- Updated `setup.sh`/`boot/`/`extras/`/`upgrades/` tree lines to name the newer
  pieces (install.sh TUI, CPU governor + storage tuning, deck-check, deck-ide,
  scroll-handle, comms).
- "illustrated 10-step assembly guide" → "11-step assembly + commissioning".
- Workflow step 4 now states the base install hardens (UFW/SSH/sysctls) and
  tunes (governor/IO/noatime) the deck, and points at `deck-check` to verify.

**`os/README.md`** (already had a Security section — good — but missing the two
newest commands):
- Extras layer: added `deck-check` (GPU/zram/thermal/governor health check) and
  `deck-help`.
- Upgrades layer: added `deck-scroll` (scroll-handle → FreeCAD zoom / volume) and
  `deck-comms` (Pico-bridge client); "Five user-requested upgrades" → "User-
  requested upgrades".

Security *features* themselves (os/security/ufw.sh, sshd drop-in, sysctls) were
already present and correct since the 2026-06-14 hardening sweep — only the docs
referencing them lagged.

## 2026-06-14 — Claude (BUILD-GUIDE refreshed for all current layers)

Re-rendered `docs/BUILD-GUIDE.pdf` from updated `docs/BUILD-GUIDE.html` (Edge
headless, 276 KB, 12 pages) — the guide had drifted behind the OS layers added
since the last render.

**Step 10 (OS)** rewritten:
- Base layer now documented as hardening + tuning, not just cosmetics: UFW
  firewall (default-deny inbound, LAN-only services), SSH key-only, kernel
  sysctls, CPU-governor + storage I/O tuning + noatime.
- New **OS-layers table** (Base / AI / Extras / Virtual / Upgrades / Apps) with
  the script and what each installs — including the pieces that were entirely
  missing from the guide: `deck-check`, `deck-ide`, `deck-scroll`, and the
  `apps/` ecosystem (GRIMOIRE offline search + RAG, the `deck-*` tools).
- `os/install.sh` whiptail TUI now named as the simplest install path.
- Check line adds `ufw status` and `deck-check` (hardware-GL-not-llvmpipe).

**Step 11 (commissioning)** — added rows: Health (`deck-check` 0 FAILs),
GPU/render (V3D not llvmpipe), Firewall (`ufw status verbose`), Scroll handle
(`deck-scroll` zoom/volume), Offline library (GRIMOIRE search with WiFi off).

PDF validated: `%PDF-1.4`, 12 page objects, clean `%%EOF`.

## 2026-06-14 — Claude (deck-check health diagnostic + grimoire repo removal)

**New `os/extras/bin/deck-check`** — read-only health diagnostic, the long-
deferred V3D verification finally wired in:
- **GPU**: parses `glxinfo -B` OpenGL renderer; FAILs on `llvmpipe/softpipe/
  swrast` (software rendering — the #1 silent FreeCAD performance killer),
  PASSes on `v3d/vc4/mesa`. Degrades gracefully with no display session or no
  mesa-utils.
- **Memory**: zram active + size, SD-swap detection, swappiness ≥100 check
  (expects our 180).
- **Thermals**: `vcgencmd measure_temp` (70°/80° thresholds) + `get_throttled`
  flag decode.
- **CPU governor**, **cyberdeck-boot.service** state, and optional hardware
  (rotary encoder via /proc/bus/input/devices, Ollama :11434 probe, RTC).
- Color-coded ✔/!/✗ with remediation hints; `--quiet` for a one-line summary;
  exit 1 if any FAIL (scriptable). Makes no changes.
- Wired into `setup-extras.sh` (installs it + `mesa-utils` for glxinfo) and
  `deck-help` system section. `deck-scroll` also added to deck-help (was built
  last entry but never listed).

**Removed `apps/grimoire/.git`** — grimoire won't be published as its own repo,
so the nested git repo was removed (verified first: 0 commits, no remote, only
a staging index — nothing lost). All source files remain; the `.gitignore`
stays in case it's re-inited later. security-suite keeps its own repo
(github.com/PyMite6941/Security-Suite.git) — unaffected.

## 2026-06-14 — Claude (four bugfixes: deck-gpio validator, deck-ide auto-resume, UFW Samba, grimoire deps)

**deck-gpio address validator** (`apps/deck-gpio/deck-gpio.py`):
- Regex `[a-fA-F0-9x,/_]+` was breaking SPI (`cs0` — `s` not in a-f) and UART
  (`/dev/serial0` — `v`, `s`, `r`, `i`, `l` not in a-f). Both template families
  were raising `ValueError` before ever generating a script.
- Fixed: expanded to `[a-zA-Z0-9x,/_]+` — still blocks all shell metacharacters,
  now correctly accepts chip-selects and device paths.

**deck-ide auto-resume after isolation** (`os/extras/bin/deck-ide`, `os/theme/bashrc-cyberdeck.sh`):
- After `systemctl isolate multi-user.target`, the desktop session dies and the
  user was dropped at the VT login prompt with no way back in automatically.
- Fix: `deck-ide` writes `~/.deck-ide-pending` before calling isolate.
- `bashrc-cyberdeck.sh` reads it on the next login shell (VT login, not inside
  tmux): removes the flag, sleeps 300 ms for systemd to settle, then `exec`s
  `deck-ide`. Result: running `deck-ide` from the desktop drops the GUI and
  lands the user straight in the IDE tmux session after login.

**UFW Samba missing 172.16.0.0/12** (`os/security/ufw.sh`):
- Samba rules only covered 192.168.0.0/16 and 10.0.0.0/8 — missing the third
  RFC 1918 block (172.16.0.0/12). Added UDP 137,138 + TCP 139,445 for it.

**grimoire requirements.txt missing libzim** (`apps/grimoire/requirements.txt`):
- `.zim` ingest support was added to the engine but `libzim` wasn't listed.
  Added as a commented optional dep with install instructions (pip install libzim).

## 2026-06-14 — Claude (deck-scroll: scroll-handle input daemon)

**Highest-priority missing hardware bridge — finally built.**
The rotary encoder dtoverlay has been in `config-additions.txt` since day one;
this is the daemon that makes it actually do something.

**New `os/upgrades/bin/deck-scroll`** — evdev input daemon:
- Reads `EV_REL / REL_X` events from the kernel rotary-encoder device
  (created by `dtoverlay=rotary-encoder,relative_axis=1`).
- Auto-detects the encoder by scanning `/dev/input/` for `REL_X`-capable
  devices; pin a specific one with `DECK_SCROLL_DEV=/dev/input/eventN`.
- `--mode auto` (default): checks the focused window name via `xdotool`
  every 100 ms and switches dispatch accordingly.
  - **FreeCAD focused** → synthetic `REL_WHEEL` events via uinput (zoom in/out).
  - **Any other window** → system volume ±5% via pactl, amixer fallback.
  - If xdotool absent, stays in volume mode and logs a hint.
- `--mode freecad` / `--mode volume` force a mode for the whole session.
- `evdev.grab()` gives the daemon exclusive access so events don't leak to
  X while the encoder is active.
- Graceful fallback chain: uinput unavailable → logs warning, skips zoom;
  pactl unavailable → amixer; xdotool unavailable → volume-only auto.

**New `os/upgrades/scroll-handle.service`** — systemd user unit:
- `After=default.target`, `WantedBy=default.target` — starts in both
  graphical and headless user sessions; headless auto-falls back to volume.
- `Environment=DISPLAY=:0` fallback; actual session env overrides it.
- `Restart=on-failure` with 3 s cooldown, burst-limited to 5 per minute.

**Modified `os/upgrades/setup-upgrades.sh`** — new step [6/6]:
- Installs `python3-evdev` + `xdotool`.
- Writes `/etc/udev/rules.d/99-cyberdeck-uinput.rules` (`/dev/uinput` → input group).
- Adds deck user to `input` group.
- Installs `scroll-handle.service` to `~/.config/systemd/user/deck-scroll.service`.
- Calls `loginctl enable-linger` so the user service survives reboots.
- After install: `systemctl --user enable --now deck-scroll` (log out first
  so the new `input` group membership takes effect).

**Encoder wiring reminder** (must be done in config.txt before service is useful):
```
dtoverlay=rotary-encoder,pin_a=17,pin_b=27,relative_axis=1,steps-per-period=2
```
Encoder push-click (gpio-key, keycode 28) is separate and already mapped to
Enter; deck-scroll only handles rotation.

## 2026-06-14 — Claude (retroactive: deck-lib shared utility library)

`apps/deck-lib/` was created by opencode without a CHANGELOG entry.
Logging it here for completeness.

**`apps/deck-lib/`** — shared Python utility library used by the Textual apps:
- `ollama.py` — `generate()` / `list_models()` via Ollama REST API;
  bakes in `num_thread=4` default (correct Pi tuning).
- `db.py` — SQLite helpers shared by the benchmark and monitoring apps.
- `pi_sensors.py` — Pi sensor reading utilities.
- `__init__.py` — empty, makes deck-lib importable as a package.
No `requirements.txt` (stdlib + evdev only); used internally by deck-* apps.

## 2026-06-14 — Claude (4 optimization apps: perf, bootvis, ollama-profiler, storage-bench)

**New `apps/deck-perf/`** — real-time system performance tuner:
- Per-core CPU frequency gauges (color-coded: green/yellow/dim by MHz).
- Live temperature + throttling status from `vcgencmd get_throttled` with 8 flag types.
- CPU governor display & switching: `P`=performance, `O`=ondemand, `S`=powersave.
- Memory, swap, load, uptime at a glance. 2-second auto-refresh, space to pause.
- Textual TUI with colored status indicators.

**New `apps/deck-bootvis/`** — boot time profiler:
- Runs `systemd-analyze blame` and parses all services with timings in seconds.
- Tracks boot history in SQLite — see how changes affect boot time over time.
- Services tab: color-coded by speed (red >2s, yellow >0.5s, green fast).
- Suggestions tab: analyzes slow services, gives actionable optimization advice
  ("mask plymouth", "disable cups", "investigate this custom service").
- Quick wins section: CPU governor, deck-lite, zram optimization tips.

**New `apps/deck-ollama-profiler/`** — LLM inference benchmark suite:
- Tests any Ollama model at 5 context sizes (512, 1024, 2048, 4096, 8192).
- Measures: tok/s, time-to-first-token, total time, output tokens, RAM delta, temp delta.
- Streamed response parsing for accurate TTFT and token counting.
- "Profile All" button runs through all context sizes sequentially with 2s cooldown.
- Results modal + history table for comparing model/config combinations.
- All results saved to SQLite for trend analysis.

**New `apps/deck-storage-bench/`** — storage benchmark suite:
- Auto-detects all block devices: SD card, NVMe, USB, zram swap.
- Sequential read/write via dd (MB/s), random 4K via fio when available (IOPS → MB/s).
- "Benchmark All" runs every detected device for side-by-side comparison.
- Performance recommendations: "NVMe is great for AI models", "SD is slow — consider NVMe".
- Historical tracking to compare storage performance over time.

Bugfix: `deck-storage-bench` had an f-string parsing error (`'?}'` inside expression);
changed to `'?'` to correctly close the string before the brace.

## 2026-06-14 — Claude (6 new apps: RAG, net toolkit, whisper, eval, lab, proxy)

**Grimoire RAG engine** (`apps/grimoire/backend/grimoire.py`):
- Fixed `Grimoire.search()` return format and added `stats()` method for frontends.
- New `embed()` / `embed_corpus()` — calls Ollama embeddings API (`nomic-embed-text`)
  to compute per-doc vectors, stored in new `embeds` table.
- New `query(text)` — RAG pipeline: embed query → cosine-similarity search → build
  context from top-5 docs → call Ollama generate → return answer + sources.
- New CLI commands: `grimoire.py embed` (batch-embed unembedded docs),
  `grimoire.py query "ask anything"` (interactive Q&A).
- Both frontends (`cli.py`, `cool-app.py`) rewritten to use the proper `Grimoire`
  class API. CLI now has "Ask a question (RAG)" menu option; TUI has `Ctrl+R` RAG
  Query screen. Bugs fixed: `g.stats()` no longer crashes, `cmd_*` functions no
  longer called with wrong signatures.
- Requirements.txt cleaned up.

**New `apps/deck-net/`** — portable network field toolkit:
- Textual TUI with scan profiles (quick, stealth, service, full, vuln).
- Wraps nmap/tcpdump, saves full output to `scans/` folder.
- "Explain" button pipes last scan through Ollama for AI analysis.
- Auto-detects installed tools, status bar shows availability.

**New `apps/deck-whisper/`** — offline voice recorder & transcriber:
- Record 30s audio via PyAudio, transcribe with `faster-whisper` (tiny-int8 model).
- Searchable transcript history in SQLite.
- Textual TUI with recording, search, detail views.

**New `apps/deck-eval/`** — local model benchmark harness:
- Runs HumanEval, GSM8K, and MMLU-style benchmarks against any Ollama model.
- Tracks score % and tok/s per run in SQLite history.
- Textual TUI with model selector, run button, results table.

**New `apps/deck-lab/`** — portable CTF lab-in-a-box:
- Starts/stop Docker containers for practice labs (web exploit, Linux privesc, network pivot).
- Built-in note-taking per lab (title + content, saved to SQLite).
- Textual TUI with lab status table, output log.

**New `apps/deck-proxy/`** — AI prompt router/gateway:
- Prompt templates: explain, code-review, summarize, debug, translate, write-docs, raw.
- Selectable model + backend (Ollama local, Claude/OpenAI cloud when API keys set).
- Prompt + response history in SQLite.
- Textual TUI with prompt input, response log, history.

All new apps follow the uniform pattern: `run.sh` launcher, shared venv at `apps/.venv`,
Textual TUI first, requirements.txt, self-contained in `apps/<name>/`.

## 2026-06-14 — Claude (Pi 5 optimisation sweep: security, performance, bugfixes)

**New: Security hardening** (`os/security/`, `os/setup.sh` step 6):
- UFW firewall: default-deny incoming, allow SSH/Samba/Moonlight from LAN only.
  Rule set at `os/security/ufw.sh` (sourced by setup.sh).
- SSH key-only auth drop-in (`os/security/99-cyberdeck-ssh.conf`): no root,
  3-try limit, 5-min alive check.
- Kernel security sysctls (`os/security/90-cyberdeck-security.conf`): rp_filter,
  source-route reject, dmesg/kptr restrict, ptrace scope.
- Journald capped at 200 MB (`os/memory/99-cyberdeck-journald.conf`).
- Boot log rotated weekly (`os/memory/logrotate-cyberdeck-boot`).

**New: CPU governor management** (`os/boot/boot.d/30-cpugovernor.sh`):
- Sets `performance` governor on boot for best CAD/compile/inference throughput.
- `deck-mode` now switches governor per mode: stealth→powersave, work→ondemand,
  bright→performance. `deck-mode show` displays the active governor.

**New: Storage I/O tuning** (`os/boot/boot.d/35-storage-tune.sh`):
- Auto-selects I/O scheduler: BFQ for SD/eMMC (desktop responsiveness), none for
  NVMe (native queuing). Enables TRIM/discard on NVMe.
- Adds `commit=600` (10-min ext4 journal delay) to root mount for reduced SD wear.
- PCIe Gen 3 option added to `config-additions.txt` (commented).

**Bug fixes:**
- `os/setup.sh`: step numbering fixed (was 3/5,4/5,5/5 mid-stream — now
  consistently 1-6/6). freecad now uses `--no-install-recommends` (~200 MB saved).
- `os/ai/setup-ai.sh`: checks if `deckcoder` model exists before overwriting;
  prompts interactively.
- `os/ai/tune-ollama.sh`: auto-detects model template format (qwen/llama/llama3/
  gemma) instead of hardcoding qwen template.
- `os/boot/cyberdeck-boot.sh`: added `shopt -s nullglob` to avoid literal `*`
  iteration when boot.d is empty.
- `os/boot/boot.d/20-noatime.sh`: replaced fragile sed with awk for fstab edits;
  also adds `commit=600` now.
- `os/upgrades/bin/deck-hid`: added `time.sleep(0.02)` between key press/release
  — many USB hosts require minimum keystroke duration.
- `os/upgrades/setup-upgrades.sh`: Samba services now disabled on install
  (deck-nas on/off controls them); SMB3 min protocol enforced.
- `os/extras/setup-extras.sh`: RTC check now verifies `hwclock -r` succeeds
  before purging fake-hwclock (Pi 5 has /dev/rtc0 even without J5 battery).
- `os/extras/conky.conf`: IP now auto-detects wlan0 or eth0; throttling warning
  via `vcgencmd get_throttled`. `wlan0` hardcode removed.
- `os/theme/motd.sh`: throttled indicator (⚠ when `get_throttled` non-zero);
  temperature extraction uses safer pattern stripping.
- `os/image/inject-to-sd.ps1`: `/MIR` → `/E` (mirror was destructive — deleted
  files on SD not in source).
- `os/image/config-additions.txt`: blank first line removed; PCIe Gen 3 +
  temp_limit options added.
- `os/install.sh`: Virtual layer added as step 5 in the TUI checklist.

**deck-help dynamic checking** (`os/extras/bin/deck-help`):
- Only shows commands whose binaries are installed; aliases/shell funcs always
  shown. deckcoder/deck-assistant hidden if Ollama absent.

**zram** (`os/memory/zramswap.conf`):
- Commented `NZM_NUM_DEVICES=4` option for multi-core parallel compression.

**Docs updated:**
- `os/README.md`: setup.sh now documents 6 steps; new Security section; boot
  scripts table includes 30/35-*; storage optimization expanded (scheduler,
  NVMe, PCIe Gen 3); extras/conky/RTC updates; compatibility mentions Pi 5
  extras; "5 small files" → "a few dozen small files".
- `CHANGELOG.md`: this entry.

## 2026-06-14 — Claude (deck-mode fix + deck-help command reference)

**Fixed deck-mode** (`os/extras/bin/deck-mode`):
- `set_led` / `set_pwr` now check `-e` (exists) instead of `-w` (writable) —
  works correctly when sudo is needed to write.
- gammastep now uses `nohup` instead of bare backgrounding.
- Graceful message when gammastep not installed instead of silent failure.
- Added `--help` / `help` flag with full usage and hardware notes.

**New `deck-help`** (`os/extras/bin/deck-help`):
- Comprehensive command reference categorised into 8 sections: base helpers,
  display modes, system commands, storage, app management, network, radio, AI.
- `deck-help` shows all; `deck-help <section>` for focused view.
- ANSI-coloured, terminal-friendly output.
- Installed by setup-extras.sh to `/usr/local/bin/deck-help`.

**MOTD updated** (`os/theme/motd.sh`):
- Shows `run 'deck-help' for all commands` tip line after the stats block
  (only if deck-help is installed).

**Docs updated:**
- `os/extras/setup-extras.sh` — installs deck-help, updated summary.
- `CHANGELOG.md` — this entry.

## 2026-06-14 — Claude (apps: Textual TUIs, fixes, deck-app, dashboard)

**grimoire frontend rebuilt:**
- `frontend/cli.py` — fixed import path (sys.path for backend/), full interactive
  CLI with rich tables, search/ingest/stats/get workflows via questionary menu.
- `frontend/cool-app.py` — new Textual TUI: search input, results DataTable,
  document detail screen, stats modal, live status bar. 50-result FTS5 search.
- `run.py` — fixed launcher (imports frontend modules, offers CLI vs TUI choice).
- `requirements.txt` — added questionary, rich, textual (frontend deps).
- `run.sh` — new uniform launcher.

**security-suite bugs fixed:**
- `backend/vault.py` wipe_vault(): was deleting vault.py instead of vault.json.
- `backend/vault.py` is_password_breached(): rockyou path was hardcoded relative.
- `backend/vault.py` create_backup(): relative path + f-string fix.
- `setup.sh` — Linux-compatible venv activation (detects bin/ vs Scripts/).
- `.gitignore` — removed over-broad `*.md`, `*.txt`, `*.gz` patterns.
- `frontend/cool-app.py` — completed Textual app: screen timeout (auto-lock
  after 5 min), change master password screen, confirm password on creation,
  add entry modal, delete entry, lock action, idle timer.
- `run.sh` — new uniform launcher.

**New `apps/deck-dashboard/`** — Textual TUI system monitor:
- CPU temp, RAM/swap, disk, load, network, uptime, top processes.
- 2-second auto-refresh, keyboard-driven (R=refresh, T=dark mode).
- `run.sh`, `requirements.txt`, `README.md`.

**New `os/extras/bin/deck-app`** — app download/manager for the deck:
- `deck-app install <url> [name]` — download zip/tar.gz/git into ~/apps/.
- `deck-app create <name>` — scaffold a new app folder with run.sh.
- `deck-app list` — list installed apps.
- `deck-app run <name>` — run by folder name.
- Default target: `~/apps/` (override with DECK_APPS_DIR).
- Installed by setup-extras.sh.

**Docs updated:**
- `apps/README.md` — added deck-dashboard, deck-app convention, new app list.
- `os/extras/setup-extras.sh` — installs deck-app, updated summary.
- `CHANGELOG.md` — this entry.

## 2026-06-14 — Claude (auto-tuned models on install + custom TUI installer)

**Modified `os/ai/setup-ai.sh`** — step 4 added: auto-detects total RAM,
picks the right model (`qwen2.5-coder:3b` on ≥7 GB, `qwen2.5:1.5b` on ≥3 GB),
interactively asks before pulling (~1-2 GB download), then creates a tuned
`deckcoder` model with `num_ctx=2048`, `num_thread=4`. Non-TTY sessions
skip the prompt and print instructions instead.

**Built `os/install.sh`** — whiptail-based TUI installer:
- DFCD ASCII art welcome screen
- Multi-select checklist for layers: base, AI, extras, upgrades
- Progress gauge wrappers for long steps
- Infobox for each running step, error dialog on failure
- Summary with next-steps
- Falls back to plain `setup.sh` if whiptail unavailable

**Docs updated:**
- `os/README.md` — install section now leads with `install.sh` TUI
- `os/image/README.md` — step 4 expanded with optional-layer instructions
- `CHANGELOG.md` — this entry

## 2026-06-14 — Claude (image pipeline audit + setup-extras coverage)

**Image pipeline audit:**
- Verified `inject-to-sd.ps1` copies entire `os/` folder — no file-list
  drift, all new scripts (tune-ollama.sh, deck-ide, deck-desktop, 20-noatime.sh)
  are automatically carried. Pipeline steps remain correct: boot 1 stages,
  boot 2 installs via setup.sh. Opt-in layers (ai/extras/upgrades) installed
  manually after base setup, as designed.
- `os/extras/setup-extras.sh` — added `deck-ide` and `deck-desktop` to the
  install step (were missing — they existed in `extras/bin/` but weren't
  deployed). Updated the "Done" summary to show them.
- `os/image/README.md` — expanded the files table to cover the image helper
  scripts (measure_parts, print_check, make_*, inspect_*) that were missing.
  Added note that `os/` is copied verbatim, so ai/extras/upgrades are available
  on the Pi after boot 1.

## 2026-06-14 — Claude (deck-ide headless IDE + central README update)

**Built** `os/extras/bin/deck-ide` + `deck-desktop`:
- `deck-ide` — headless IDE mode: drops to console (multi-user.target), kills
  the display manager to free ~2 GB RAM, auto-starts a tmux session with
  Neovim (left 60%), Claude Code (right-top), and htop (right-bottom).
- `deck-desktop` — companion script to re-enable the display manager and
  restore graphical.target.
- Both deployed by `setup-extras.sh` to `/usr/local/bin/`.

**Docs updated:**
- `README.md` — fixed `apps/` description to mention programming utilities.
- `apps/README.md` — roadmap table: deck-ide moved from "Planned" to ✅.
- `os/README.md` — deck-ide mentioned in TUI section + extras listing.
- `CHANGELOG.md` — this entry.

## 2026-06-14 — Claude (programming utilities + deck optimizations)

**Docs: programming roadmap + optimizations**
- `apps/README.md` — added `deck-gpio` entry + programming utilities roadmap
  table (GRIMOIRE ✅, deck-gpio ✅, deck-ide planned).
- `os/README.md` — added "Programming optimizations" section covering TUI
  maximalism (tmux, deck-lite, planned deck-mode --terminal), Ollama model-level
  tuning (num_ctx/num_thread/Q4_K_M), and flash storage noatime advice.

**Built** `apps/deck-gpio/` — GPIO/I2C/SPI rapid prototyper:
- `deck-gpio.py` — CLI that parses pin descriptions (`--map i2c 0x3c ssd1306`,
  `--map gpio 17 led`, `--map spi cs0 mcp3008`) and auto-generates a runnable
  Python test script with `RPi.GPIO`/`busio`/`adafruit_*` boilerplate,
  executes it, and reports results.
- `run.sh` — launcher with path detection and venv awareness.
- `README.md` — usage, examples, module docs.
- `requirements.txt` — minimal deps (no hardware libs mandatory on generation).

**Enhanced** `os/theme/tmux.conf` — added dev-oriented keybindings:
- `Alt-C` → split right, open Claude Code
- `Alt-M` → split down, open htop
- `Alt-N` → split right, open Neovim
- `Alt-Q` → kill pane

**Added** `os/ai/tune-ollama.sh` — helper that creates a `deckcoder` model
with the recommended Pi tuning (num_ctx 2048, num_thread 4, Q4_K_M).

**Added** `os/boot/boot.d/20-noatime.sh` — boot script that detects SD/NVMe
root and adds `noatime` to `/etc/fstab` if absent (idempotent, safe).

## 2026-06-14 — Claude (GRIMOIRE .zim support + hardening, apps venv/git system)

User had restructured GRIMOIRE into backend/frontend/run.py (engine now at
`apps/grimoire/backend/grimoire.py`) and added ~5 GB of `.zim` corpora in
`backend/data/` (DevDocs, Gutenberg, etc.).

**GRIMOIRE engine** (`backend/grimoire.py`):
- Added `.zim` ingest (openZIM/Kiwix): `iter_zim` (via libzim) + `iter_documents`;
  `cmd_ingest` now indexes plain files AND `.zim` articles into the one store.
  libzim is optional — clear message if absent.
- Hardening: `read_text` now decodes `utf-8-sig` (strips BOM); `main()`
  reconfigures stdout to utf-8/`replace` so CLI output can't crash on a Windows
  cp1252 console (was a real UnicodeEncodeError on a BOM'd title).
- Verified: compiles; file ingest/search/stats work (zstandard now installed →
  zstd codec); public API unchanged so the frontend's `from grimoire import *` holds.

**Apps venv/git system:**
- `apps/setup-venv.sh` — one shared venv at `apps/.venv`, installs each app's
  requirements.txt (handles `bin/` and `Scripts/`). Recommendation: shared venv,
  gitignored + recreated per-machine; an app keeps its own venv only on conflict.
- `apps/.gitignore` + `apps/grimoire/.gitignore` (ignore .venv, __pycache__,
  *.db, *.zim, backend/data/).
- `git init` on `apps/grimoire` → its own repo, separate from security-suite.
  **CAUGHT:** `git add -A` had staged 31 `.zim` corpora (**5.2 GB**); added
  `*.zim`/`backend/data/` to .gitignore and unstaged them before any commit.
  Source-only staging now clean; left uncommitted for the user.
- Added `apps/grimoire/CLAUDE.md` (via `/init`).

## 2026-06-13 — Claude (moved security-suite into apps/, built GRIMOIRE)

**Moved** `portfolio/security-suite/` → `apps/security-suite/` (user's "vault"
app). Copied with robocopy preserving `.git` history + all source; **excluded
`.venv`** (non-portable, was the locked file → recreate with `python -m venv`).
New repo verified healthy: branch `main` → `origin/main`
(github.com/PyMite6941/Security-Suite.git), full history, clean tree. The old
`portfolio/security-suite/` leftover was initially locked (VS Code / cloud
sync) but **has since been deleted — move 100% complete**.

**Added** `apps/grimoire/` — GRIMOIRE, the deck's offline search engine:
- `grimoire.py` — ingest/search/get/stats CLI + `Grimoire` Python API.
- Storage: one SQLite file; bodies compressed **per-document** (zstandard L19
  with a corpus-trained shared dictionary, transparent **zlib fallback** if
  zstandard absent) as BLOBs (random-access from Python); **FTS5 contentless**
  inverted index for BM25 full-text search (no duplicate text). `ingest
  --max-gb 1.0` enforces the budget; `stats` reports usage.
- `requirements.txt` (optional zstandard), `run.sh`, `README.md`.
- Tested end-to-end: ingest 3 docs, multi-term search, get, Python API, stats,
  zlib fallback path all work; fixed a console-unsafe Unicode ellipsis in
  snippets.

## 2026-06-13 — Claude (build guide brought up to date)

**Updated** `docs/BUILD-GUIDE.html` → re-rendered `BUILD-GUIDE.pdf` (Edge
headless, 205 KB). Now 11 steps / 8 figures:
- New **Step 9 — Comms module** with a Pico-bridge diagram (Fig. 7).
- Step 1 + Step 6 point at the custom LED screen frame; Step 6 documents the
  LED sited between the front buttons.
- Step 10 (OS) expanded for all opt-in layers (ai/extras/virtual/upgrades) and
  the `apps/` workspace; OS pipeline is now Fig. 8.
- Step 11 (commissioning) adds rows: comms module, USB HID, NAS, assistant.

## 2026-06-13 — Claude (apps/ workspace + status-LED placement)

**Added** `apps/` — user workspace for programs and downloaded app files,
deliberately separate from `hardware/` (upstream) and `os/` (system) so it's
untouched by git pulls / OS installers. README documents the one-folder-per-app
convention (optional `run.sh`) and how to sync to the Pi (scp / deck-nas /
deck-drive / git).

**Status LED** — user chose "by the buttons". Mapped the button cluster: 3 big
buttons are a vertical column at X266–285 with a switch above, on the screen
frame's front face (Y≈33). First attempt above the column (Z90) failed a
material-removal check (14 mm³ → void), so the script tested 5 candidates and
auto-picked the solid webbing **between the bottom & middle buttons** (X275.5,
Z−35.6): removed 80 mm³, result valid/closed. Exported
`hardware-custom/Screen frame/Right screen frame with LED.{step,3mf,stl}`.
Wires to GPIO26 (gpio-led overlay already in config-additions). `make_led_button.py`
keeps the candidate logic + void check for re-tuning.

## 2026-06-13 — Claude (comms module: Pico-bridged NFC + LoRa)

User decided (via AskUserQuestion): new features go in a NEW clamp-on module,
not by modifying proven core parts; module connects via a **Pico USB bridge**;
NFC + LoRa go in the module; status LED + ports stay on the body.

**Added** `os/upgrades/comms-module/`:
- `firmware/code.py` + `boot.py` — CircuitPython for a Pi Pico: reads PN532
  (I2C GP4/5) + RFM9x LoRa (SPI GP16-20), exposes a line protocol over the USB
  data-CDC (PING/STATUS/NFC/LORA TX/LORA RX). LoRa default 923 MHz (AS923).
- `firmware/README.md` — flash + lib install steps.
- `README.md` — module BOM (~$21), Pico wiring table, assembly, usage.
- `bin/deck-comms` (host) — finds the bridge by PINGing serial ports, drives
  status/nfc/lora; uses pyserial in the venv. Added to setup-upgrades.sh.
- `os/image/make_comms_module.py` — parametric enclosure generator.

**CAD** `hardware-custom/Comms module/` (body + lid, STEP/3MF/STL):
- Body 82×60×32 mm, lid 82×60×3 mm — both validated solids=1 valid=True
  closed=True. Pico standoffs, NFC read-through window (1.2 mm), LoRa SMA hole,
  USB exit slot, 4 lid bosses, 2× M3 floor holes for the rail clamp.
- v1 caveat: floor BOLT_SPACING=30 mm mates to the deck's printed rail clamp —
  fit-check against a physical clamp before printing (rail measured 12.4×26 mm
  via `os/image/inspect_rail.py`).

**Parts** — Pico (~$4) + SMA antenna (~$3) added to both SHOPPING lists.

**Validated** — deck-comms bash + embedded host python compile; firmware
py_compile; enclosure solids valid/closed; all LF.

**Still open** — status LED needs a 3 mm hole where the user wants it visible
on the body (placement is their ergonomic call — not cut yet).

## 2026-06-13 — Claude (pre-print readiness review)

**Added** `os/image/print_check.py` — FreeCAD sweep of all 83 `.3mf` print files
+ the generated raised lid: bbox/bed-fit, isSolid, non-manifold, self-intersection.

**Findings**
- Generated raised lid (`hardware-custom/.../GFPIO lid raised 12mm.step`):
  solids=1, valid=True, closed=True — boolean fusion is clean, printable.
- 15 `.3mf` files flagged non-manifold/self-intersecting — these are
  solid→mesh tessellation artifacts, NOT defects (upstream deck was built &
  printed; slicers auto-repair). No action required to print.
- Bed: largest parts ~215 mm longest edge — fits 220×220 with ~5 mm margin.
  Corrected SIZING.md (previously over-optimistically said "room to spare").
- No read errors; no part exceeds the bed.

**Decision pending (asked user)** — new features (NFC, LoRa, status LED, ports)
to live in a NEW clamp-on module rather than modifying proven core parts.
Blocked on: module bus approach (Pico-USB-bridge vs GPIO-ribbon vs USB-native)
and which features are modular vs fixed.

## 2026-06-12 — Claude (Committed Upgrades layer: assistant/HID/NAS/RFID/LoRa)

**Added** `os/upgrades/` (opt-in `setup-upgrades.sh`, idempotent, Pi 4B+):
- `assistant/Modelfile` + `bin/deck-assistant` — offline Ollama persona "DECK".
  setup picks base by RAM (qwen2.5:3b ≥7GB else 1.5b), rewrites FROM, `ollama
  create deck`. Customisation via Modelfile, NOT training (clarified w/ user).
- `bin/deck-hid` — USB HID keyboard gadget (libcomposite): on/off/status +
  `type "text"` (embedded US-layout keymap) + `key <hex>`. udev rule lets
  type/key run without sudo. dwc2 peripheral overlay shipped commented; Pi 5
  USB-C device-mode caveat documented honestly.
- `bin/deck-nas` — Samba [deck] share of ~/Share; on/off/status/user.
- `bin/deck-rfid` — PN532 NFC over I2C (venv Python, adafruit-pn532).
- `bin/deck-lora` — SX127x/RFM9x LoRa over SPI (venv Python, adafruit-rfm9x),
  default 923.0 MHz = **AS923 (Thailand-legal)**, DECK_LORA_FREQ override.
- `config-upgrades.txt` — commented dwc2/i2c/spi enables (marker CYBERDECK-UPGRADES).
- Hardware helpers use a venv at /opt/cyberdeck/venv (Bookworm externally-managed).

**Docs** — upgrades/README.md; SHOPPING.md +PN532 (~$5/฿180) +LoRa AS923
(~$12/฿430) on both lists; main README tree + os/README sections.

**Verified** — bash -n on all 6 scripts; all 3 embedded Python blocks py_compile;
ran the real deck-hid keymap against a temp file (H→shift+0x0b, 16 bytes/char,
spot-checks pass); all LF.

**Note** — the "vault" in the user's other plan is already shipped here as
`deck-vault` (extras layer, LUKS2 container).

## 2026-06-12 — Claude (virtual parts layer — same thread)

**Added**
- `os/extras/setup-virtual.sh` (opt-in) — installs Moonlight (virtual GPU via
  game-stream from a Sunshine host) + open-iscsi/rclone backends.
- `os/extras/bin/deck-drive` → /usr/local/bin: attach network-backed virtual
  disks — `iscsi <portal>` (NAS target as /dev/sdX), `cloud <remote:path>`
  (rclone mount at ~/CloudDrive), `list`, `off`.
- os/README.md: documented the Extras layer (was previously only in CHANGELOG)
  and the new Virtual parts layer.

**Rationale**
- "Virtual parts" that actually work = network-backed real hardware. Moonlight
  borrows a home GPU; iSCSI/rclone borrow disk. Keeps the deck at ~12 W in the
  field, full power when docked on the LAN. Local-only "virtual GPU/RAM" is a
  myth and deliberately not attempted (zram is the one honest RAM trick, already
  in the base layer).

## 2026-06-11 — Claude (raised lid, desktop theme, extras, checklists, build guide — same session)

**CAD**
- `hardware-custom/Screen frame/GFPIO lid raised 12mm.{step,3mf,stl}` —
  stock lid split at its constant wall section, 12 mm spacer band fused in
  (32.4×24.5×62.2 vs stock ×12.5). Generated by `os/image/make_raised_lid.py`.
  IMPORTANT correction: the GFPIO lid is a 32×62 mm GPIO hatch, NOT a Pi-bay
  cover — the raise gives headroom for an RTC module/cabling over the header,
  but an M.2 HAT+ needs screen-frame cavity space the upstream CAD doesn't
  model (no electronics in the STEP). `inspect_lid.py` added (lid geometry probe).
- Note: FreeCADCmd error "[File does not exist]" in brackets is the *script's*
  exception text — first failure was a wrong 3MF path (missing `Screen` level).

**OS — desktop theme (answers "custom icons?")**
- `os/theme/setup-desktop.sh` (called from setup.sh step 5): Papirus-Dark icon
  theme via apt, GTK dark preference, pcmanfm wallpaper/colors; user icons can
  be dropped in `~/.local/share/icons/`. Create-if-absent, never clobbers.
- `os/theme/make_wallpaper.py` — generates 1280×800 green-grid DFCD wallpaper
  on the Pi with PIL (no binary in repo).

**OS — extras (`os/extras/`, opt-in setup-extras.sh)**
- `deck-mode stealth|work|bright` → /usr/local/bin: gammastep dimming,
  ddcutil backlight (if panel supports DDC), status-LED trigger switching.
- `deck-vault init|open|close` → LUKS2 file container mounted at /mnt/vault
  (deliberate choice over root FDE: no initramfs risk, headless-boot safe).
- Conky always-on status overlay (top-right, green/black) autostarted on desktop.
- RTC handling: Pi 5 = J5 battery only; Pi 4 = DS3231 + i2c-rtc overlay (added
  commented to config-additions.txt); fake-hwclock purged once /dev/rtc0 exists.
- Status LED: gpio-led overlay (GPIO26 + 330Ω, commented in config-additions);
  kernel triggers heartbeat/none/mmc0 driven by deck-mode.
- Radio: rtl-sdr CLI tools (+gqrx on desktop) for RTL-SDR dongle (AM/FM RX).

**Docs & purchasing**
- `SHOPPING.md` — checkbox price checklists: Amazon (USD) + Shopee/Lazada (THB).
- `docs/BUILD-GUIDE.html` + rendered `BUILD-GUIDE.pdf` (Edge headless) —
  10-step assembly/commissioning guide with 7 authored SVG figures and an
  acceptance-test matrix; strap: upstream anchors (Strap mount/Sling mount)
  + bought 2-point QD sling, print anchors at 100% infill.

## 2026-06-11 — Claude (AI workload layer — same session)

**Added**
- `os/ai/setup-ai.sh` — opt-in AI layer: idle-RAM trim (cups/ModemManager off,
  Bluetooth kept), earlyoom with sshd/desktop on the avoid list, Node 22 +
  Claude Code CLI, Ollama with memory-tuned systemd override (KEEP_ALIVE=2m,
  1 model max, flash attention, q8_0 KV cache).
- `deck-lite` / `deck-gui` shell functions in the theme — toggle the desktop
  to free ~500 MB for inference.
- `BOM.md` "AI add-on" section — 16GB Pi 5, M.2 HAT+ + NVMe, active cooler,
  second battery; explicit warning that Hailo/Coral accelerators do NOT help
  LLMs; realistic tok/s expectations for Pi 4/5.

**Decisions**
- AI layer is NOT part of the image first-boot (adds ~2 GB of downloads);
  run it over SSH after the deck is up.

**Also added**
- `os/image/check_pi_clearance.py` — FreeCADCmd analysis of internal chassis
  clearance. Finding: upstream STEP models printed parts only (no Pi/electronics
  solids); chassis body is two shells ~14–20 mm internal depth around a mid
  plate, Pi lives behind the screen under the GFPIO lid — no spare bay for
  internal extra storage without modifying the lid/frame.

## 2026-06-11 — Claude (sizing, BOM, hardware config, bootable image — same session)

**Added**
- `SIZING.md` — measured bounding boxes of all 7 STEP assemblies via headless
  FreeCADCmd (`os/image/measure_parts.py`) + what each dimension implies for
  part selection (10.1" panel, ≤310mm keyboard, NP-F battery, Marble trackball).
  Note: FreeCADCmd needs the short 8.3 path — it can't read
  paths containing multi-byte Unicode characters.
- `BOM.md` — full priced bill of materials with best-pick + budget options;
  ~$430–530 (Pi 5 8GB, shortage pricing) or ~$330–380 (Pi 4B build).
- `os/image/` — bootable-image pipeline (no pi-gen needed):
  `inject-to-sd.ps1` (Windows: payload copy + firstrun hook onto a freshly
  flashed card; chains into Raspberry Pi Imager's firstrun.sh if present),
  `firstrun.sh` (boot 1, offline staging, mountpoint-agnostic),
  `cyberdeck-firstboot.service` (boot 2, runs setup.sh online, self-disables),
  `config-additions.txt` (commented dtoverlays: rotary-encoder scroll handle,
  gpio-key buttons, gpio-shutdown, panel EDID + Pi 4 gpu_mem notes).
- `setup.sh` — new step 3 appends the config.txt section (marker-guarded);
  fixed DECK_USER resolution for the no-SUDO_USER image path (falls back to
  uid 1000); steps renumbered to 5.

**Verified**
- All shell scripts `bash -n` clean, LF endings; `inject-to-sd.ps1` parses
  clean (PS 5.1 AST parser).

## 2026-06-11 — Claude (Pi 4B+ compat, memory management, polish — same session)

**Added**
- `os/memory/zramswap.conf` → `/etc/default/zramswap` — zstd zram swap at 50% of
  RAM (Pi 4 4GB ≈ 6 GB effective, Pi 5 8GB ≈ 10+ GB), zero SD-card wear.
- `os/memory/90-cyberdeck-vm.conf` → `/etc/sysctl.d/` — kernel-recommended VM
  tuning for RAM-backed swap (swappiness=180, page-cluster=0, watermark tweaks).
- `os/theme/fastfetch.jsonc` — themed green/cyan fastfetch (CPU temp, mem, swap).
- `os/theme/tmux.conf` — matching status-bar theme, installed only if
  `~/.tmux.conf` absent.

**Changed**
- `setup.sh` — now 4 steps: adds zram-tools, applies memory configs, enables
  `zramswap.service`, disables `dphys-swapfile` (SD swap); fastfetch install is
  tolerant of missing package; prints `free -h` at the end.
- `bashrc-cyberdeck.sh` — `temp` is now a function (vcgencmd on Pi 4/5, sysfs
  fallback, proper °C); added `ls` color + `mem` alias; fastfetch uses the
  themed config.
- `motd.sh` — added swap row; temperature coloured green/yellow/red (65°/75°
  thresholds); all fields degrade to `n/a` instead of erroring off-Pi.
- `cyberdeck-boot.sh` — `BOOT_D`/`LOG` overridable via env for off-Pi testing.
- READMEs/AGENTS.md updated: Pi 4B+ compatibility statement, memory section.

**Verified (debug pass)**
- `bash -n` clean on all 5 scripts; no CRLF line endings.
- MOTD renders correctly; boot runner executes scripts in order; a failing
  boot.d script is logged as FAILED and does not block the others.
- bashrc sources cleanly off-Pi; `fastfetch.jsonc` parses as valid JSON.
- Nothing Pi-5-specific used anywhere: vcgencmd, zram-tools, systemd units and
  update-motd.d behave identically on Pi 4B (Bookworm+).

## 2026-06-11 — Claude (initial setup)

**Added**
- `hardware/` — cloned https://github.com/ArcticEnrichmentCenter/DFCD-cyberdeck-files
  (93 files: .3mf print meshes, .step CAD, hardware list, README). Kept as a live
  git clone so `git pull` fetches upstream updates. Renamed dir from repo name to
  `hardware/` for clarity.
- `os/setup.sh` — idempotent installer for the Pi: packages (incl. FreeCAD),
  boot-script system, theme.
- `os/boot/cyberdeck-boot.service` — systemd oneshot unit, runs after
  network-online.target.
- `os/boot/cyberdeck-boot.sh` — runner: executes executable `*.sh` in
  `/opt/cyberdeck/boot.d/` in lexical order, logs to `/var/log/cyberdeck-boot.log`,
  failures don't block other scripts.
- `os/boot/boot.d/10-example.sh` — working example boot script.
- `os/theme/bashrc-cyberdeck.sh` — green/cyan prompt with exit-status indicator,
  aliases (`ll`, `temp`, `bootlog`, `deck`), fastfetch greeting.
- `os/theme/motd.sh` — DFCD ASCII banner + live system stats, installed to
  `/etc/update-motd.d/10-cyberdeck`.
- `README.md`, `os/README.md`, `AGENTS.md`, `.gitattributes` (forces LF on `.sh`).

**Decisions**
- Layer on stock Raspberry Pi OS instead of a custom image: re-flashable in
  minutes, every piece is a readable text file, editable by hand or by agents.
- Boot scripts via systemd + drop-in dir (not rc.local/crontab @reboot): ordered,
  logged, testable with `systemctl restart cyberdeck-boot.service`.
- FreeCAD installed on the Pi via apt (the DFCD is built to run it). FreeCAD on
  the Windows PC was already installed (v1.1.1, winget) — verified, no change made.
