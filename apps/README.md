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

- **`grimoire/`** — the deck's offline search engine. Folds a pile of documents
  into one compressed (<1 GB) SQLite tome you can search with no internet.
  CLI (rich) + TUI (Textual) frontends. `./run.sh`. See `grimoire/README.md`.
- **`security-suite/`** — your security/vault app. Encrypted vault with 2FA,
  password generation, breach checking. CLI (questionary) + TUI (Textual).
  `./run.sh`. See `backend/vault.py`.
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
full-screen interface. Both frontends live in `frontend/`; the launcher
(`run.py`) offers the choice.

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
