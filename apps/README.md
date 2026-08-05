# apps/

Your workspace for programs and downloaded apps that run **on the deck** — kept
separate from the upstream hardware files (`../hardware/`) and the OS layer
(`../os/`) so it never collides with `git pull`s of the DFCD repo or changes to
the system scripts.

## What goes here

- **Your own programs** — scripts, small apps, projects you write for the deck.
- **Downloaded app files** — standalone binaries, `.py`/`.sh` tools, AppImages,
  anything you want to carry on the deck.

One subfolder per app keeps things tidy.

## Apps here

- **`deck-store/`** — the deck's **app store**. Browse the catalog, see what's
  installed, install vendored apps (clone + private venv), and get an **Updates**
  tab when a vendored app is behind its remote. CLI + Textual TUI. `./run.sh`
  (or `deck-store list|search|info|install|upgrade|refresh`). See
  `deck-store/README.md`.
- **`grimoire/`** — the deck's offline search engine. Folds a pile of documents
  into one compressed (<1 GB) SQLite tome you can search with no internet.
  CLI (rich) + TUI (Textual) frontends. **Vendored** (real code at
  [PyMite6941/grimoire](https://github.com/PyMite6941/grimoire); `src/` is a
  managed clone with its own private venv). Ships `import_data.py` to pull
  public-domain texts from Project Gutenberg & equivalents. `./run.sh`. See
  `grimoire/README.md`.
- **`security-suite/`** — your security/vault app. Encrypted vault with 2FA,
  password generation, breach checking. CLI (questionary) + TUI (Textual).
  **Vendored**: `install.sh` clones [Security-Suite](https://github.com/PyMite6941/Security-Suite)
  into `src/` with a private venv; `run.sh` launches it; later runs offer
  updates. See `security-suite/README.md`.
- **`deck-sensors/`** — live TUI for Pi HAT / SoC sensors (temp, humidity, IMU,
  memory), logs to SQLite. `./run.sh` / `--once`. See `deck-sensors/README.md`.
- **`deck-radio/`** — RTL-SDR spectrum scanner + FM/ADS-B/AIS/433 MHz decoders.
  `./run.sh` / `--devices` / `--scan`. See `deck-radio/README.md`.
- **`deck-serial/`** — UART / serial console monitor + logger (pyserial). Pairs
  with `deck-gpio`. `./run.sh` / `--list`. See `deck-serial/README.md`.
- **`deck-gpio/`** — GPIO/I2C/SPI rapid prototyper. Pass a pin description and
  it auto-generates, runs, and debugs a Python test script for that layout.
  CLI (argparse). `./run.sh --map i2c 0x3c ssd1306`. See `deck-gpio/README.md`.
- **`deck-dashboard/`** — real-time system monitor TUI. CPU temp, RAM/swap,
  disk, network, top processes. Textual full-screen app. `./run.sh`.
- **`deck-net/`** — network field toolkit. Scan (nmap), packet capture (tcpdump),
  AI-powered analysis via Ollama. Textual TUI. `./run.sh`.
- **`deck-whisper/`** — offline voice recorder & transcriber. Records audio via
  PyAudio, transcribes with `faster-whisper`. Searchable transcript history.
  Textual TUI. `./run.sh`.
- **`deck-eval/`** — local model benchmark harness. Runs HumanEval/GSM8K/MMLU
  against any Ollama model, tracks score + tok/s in SQLite history.
  Textual TUI. `./run.sh`.
- **`deck-lab/`** — portable CTF lab-in-a-box. Docker containers for practice
  labs (web exploit, Linux privesc, network pivot) with built-in note-taking.
  Textual TUI. `./run.sh`.
- **`deck-proxy/`** — AI prompt router/gateway. Prompt templates (explain,
  code-review, debug, summarize, etc.), selectable model + backend.
  Textual TUI. `./run.sh`.
- **`deck-perf/`** — system performance tuner. Real-time CPU freq per core,
  temp, throttling flags, governor switching (P/O/S keys). Textual TUI. `./run.sh`.
- **`deck-bootvis/`** — boot time profiler. Parses `systemd-analyze blame`,
  tracks history in SQLite, suggests optimizations. Textual TUI. `./run.sh`.
- **`deck-ollama-profiler/`** — LLM inference benchmark. Tests models at 5
  context sizes, measures tok/s/TTFT/RAM/temp deltas. Textual TUI. `./run.sh`.
- **`deck-storage-bench/`** — storage benchmark suite. Tests SD/NVMe/USB/zram
  seq + 4K random, auto-recommends best device. Textual TUI. `./run.sh`.
- **deck-settings/** � unified system configuration TUI. Network & WiFi scanning,
  storage usage, app listing, CPU governor switching, display modes, deck-vault,
  fingerprint biometrics, SSH/firewall status, system info. Textual TUI. ./run.sh.
- **deck-lib/** � shared Python helpers (db.py, ollama.py, pi_sensors.py)
  used by the deck-* apps above. Not a standalone app; no un.sh.

```
apps/
├── README.md
├── grimoire/           # offline search + RAG (CLI + Textual TUI)
├── security-suite/     # encrypted vault (CLI + Textual TUI)
├── deck-gpio/          # GPIO/I2C/SPI prototyper (CLI)
├── deck-dashboard/     # system monitor (Textual TUI)
├── deck-net/           # network field toolkit (Textual TUI)
├── deck-whisper/       # offline voice recorder (Textual TUI)
├── deck-eval/          # model benchmark (Textual TUI)
├── deck-lab/           # CTF lab-in-a-box (Textual TUI)
├── deck-proxy/         # AI prompt router (Textual TUI)
├── deck-perf/          # system performance tuner (Textual TUI)
├── deck-bootvis/       # boot time profiler (Textual TUI)
├── deck-ollama-profiler/ # LLM inference benchmark (Textual TUI)
├── deck-storage-bench/ # storage benchmark suite (Textual TUI)
- **deck-settings/** � unified system configuration TUI. Network & WiFi scanning,
  storage usage, app listing, CPU governor switching, display modes, deck-vault,
  fingerprint biometrics, SSH/firewall status, system info. Textual TUI. ./run.sh.
- **deck-lib/** � shared Python helpers (db.py, ollama.py, pi_sensors.py)
  used by the deck-* apps above. Not a standalone app; no un.sh.
├── <your-next-app>/
│   └── run.sh          # optional launch convention (below)
```

## Programming utilities roadmap

The deck is also a portable field terminal for programming, scripting, and
code-automation. Three high-value tools live or are planned here:

| Tool | Status | What it does |
|------|--------|-------------|
| **GRIMOIRE** | `apps/grimoire/` ✅ | Offline search + RAG — FTS5 keyword search + Ollama embeddings + Q&A over your docs. CLI (rich) + TUI (Textual). `./run.sh` |
| **deck-gpio** | `apps/deck-gpio/` ✅ | GPIO/I2C/SPI rapid prototyper — pass a pin description like `--map i2c 0x3c ssd1306`, get a runnable Python test script. |
| **deck-dashboard** | `apps/deck-dashboard/` ✅ | Real-time system monitor — CPU temp, RAM, swap, disk, network, top processes. Textual TUI. |
| **deck-net** | `apps/deck-net/` ✅ | Network field toolkit — nmap/tcpdump scans + Ollama AI analysis. Textual TUI. |
| **deck-whisper** | `apps/deck-whisper/` ✅ | Offline voice recorder & transcriber — faster-whisper + searchable history. Textual TUI. |
| **deck-eval** | `apps/deck-eval/` ✅ | Local model benchmark — HumanEval/GSM8K/MMLU for any Ollama model. Tracks score + tok/s. Textual TUI. |
| **deck-lab** | `apps/deck-lab/` ✅ | Portable CTF lab — Docker containers + note-taking. Textual TUI. |
| **deck-proxy** | `apps/deck-proxy/` ✅ | AI prompt router — templates, model selection, history. Textual TUI. |
| **deck-perf** | `apps/deck-perf/` ✅ | System performance tuner — per-core freq, temp, throttling flags, governor switching. Textual TUI. |
| **deck-bootvis** | `apps/deck-bootvis/` ✅ | Boot time profiler — systemd-analyze parser, history tracking, optimization suggestions. Textual TUI. |
| **deck-ollama-profiler** | `apps/deck-ollama-profiler/` ✅ | LLM inference benchmark — tests models at 5 context sizes, measures tok/s/TTFT/RAM/temp. Textual TUI. |
| **deck-storage-bench** | `apps/deck-storage-bench/` ✅ | Storage benchmark — SD/NVMe/USB/zram speed tests, auto-recommends best device. Textual TUI. |
| **deck-settings** | `apps/deck-settings/` ✅ | Unified system configuration TUI — WiFi scanning, storage, apps, CPU governor, display mode, vault, biometrics, SSH, firewall, system info. |
| **deck-ide** | `os/extras/bin/deck-ide` ✅ | Headless IDE mode — drops console, kills the display manager (~2 GB freed), fires up tmux with Neovim + Claude Code + htop split. `deck-desktop` restores the GUI. |
| **deck-dashboard** | `apps/deck-dashboard/` ✅ | Real-time system monitor TUI (Textual): CPU temp, RAM/swap, disk, network, top processes. |

## Convention (optional but handy)

If an app has a `run.sh` at its root, it can be launched uniformly and, later,
listed/auto-started by the deck. Keep each app self-contained in its own folder.

```bash
# example apps/hello/run.sh
#!/usr/bin/env bash
echo "hello from the deck"
```

Every app should offer at least a **CLI** interface (argparse, questionary, or
rich). Apps with interactive workflows should also provide a **Textual TUI**
full-screen interface.

## Vendoring an external app (`_vendor_launcher.sh`)

If an app's real code lives in someone else's git repo (not written here) —
like `security-suite` — don't add it as a git submodule. Submodules pin an
exact commit in *this* repo's history, so checking whether that pin is stale
needs cross-repo access this repo doesn't always have.

Instead, give the app **two** thin scripts that source `_vendor_launcher.sh`.
The installer must be named `install.sh` (not `run.sh`):

```bash
# myapp/install.sh — installer / updater
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"
vendor_sync "myapp" "https://github.com/user/repo.git" "$DIR/src" "$@"
```

```bash
# myapp/run.sh — launcher
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$DIR/../_vendor_launcher.sh"
case "${1:-}" in --check-updates=*) exec "$DIR/install.sh" "$@" ;; esac
"$DIR/install.sh"
exec "$(vendor_python "$DIR/src")" "$DIR/src/run.py" "$@"
```

`vendor_sync` (in `install.sh`):

- **Clones** the repo into `src/` (gitignored via the generic `*/src/` rule) on
  first run, and builds a **private virtualenv at `src/.venv`** with the app's
  requirements — each vendored app is isolated from the others and from the
  shared `apps/.venv`.
- On later runs **fetches `origin`** and, if there are new commits, prints a
  one-line-per-commit summary and asks `Update now? [y/N]` before
  fast-forwarding — never touching local edits, skipping the check on
  non-interactive runs (no TTY).
- **After a successful update pull, wipes caches**: all `__pycache__`/`*.pyc`
  under `src/`, plus any globs you list in a `.update-clean` file next to `src/`
  (one per line, `#` comments allowed), then re-syncs the venv.
- `./run.sh --check-updates=off` (persisted in a gitignored `.check-updates`
  file) stops the prompt; `--check-updates=on` resumes it.

`vendor_python "$DIR/src"` echoes the private venv's python. See
`security-suite/` and `grimoire/` for worked examples. The deck-store installs
vendored apps by writing exactly this `install.sh`/`run.sh` pair for you.

This convention is for `apps/` only — the `os/` layer is never
auto-update-checked (see `AGENTS.md`).

Both frontends live in `frontend/`; the launcher (`run.py`) offers the choice.

## Installing new apps

Use `deck-app` (on the Pi, installed by `setup-extras.sh`) to download, scaffold,
or run apps into the default `~/apps/` directory:

```bash
deck-app install https://example.com/tool.zip my-tool
deck-app create  my-new-tool
deck-app list
deck-app run my-tool
```

Set `DECK_APPS_DIR` to override the default target directory.

## Getting these onto the Pi

This folder lives in the project on your PC. To use an app on the deck, sync it
over — any of:

- `scp -r apps/<app> pi@<deck-ip>:~/apps/`
- the **NAS share**: `deck-nas on`, then drop files into `~/Share` over WiFi
- the **cloud mount**: `deck-drive cloud <remote:path>` and copy from there
- `git clone` the project on the Pi and `git pull` to update

Nothing here is touched by the OS installers, so it's a safe place to keep work
in progress.
