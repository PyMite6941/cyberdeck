# security-suite

Encrypted vault app — 2FA, password generation, breach checking. CLI
(questionary) + TUI (Textual). Actual source: [PyMite6941/Security-Suite](https://github.com/PyMite6941/Security-Suite).

This folder only holds two thin scripts (`install.sh`, `run.sh`) plus this
README — it is **not** the app itself and is not a git submodule. That's on
purpose: the previous submodule pin required this repo to be re-committed every
time the vault app changed upstream, and checking whether the pin was stale
needed cross-repo access this repo doesn't always have. The shared sync logic
lives in `apps/_vendor_launcher.sh` (see `apps/README.md` § "Vendoring an
external app") so any app that wraps an external repo reuses it — an `apps/`-only
convention; the `os/` layer is never auto-update-checked.

## Layout

- **`install.sh`** — installer/updater. First run clones `Security-Suite` into
  `src/` and builds a **private** virtualenv at `src/.venv` with the app's
  requirements. Later runs offer to fast-forward to new upstream commits.
- **`run.sh`** — launcher. Ensures it's installed, then runs the app from its
  private venv.
- **`src/`** — the live clone (gitignored — managed by the deck, not vendored
  here). Its `.venv` is private to this app, isolated from other deck apps.

## How updates work

- **First run**: `./run.sh` (or `./install.sh`) clones the repo and sets up the
  private venv.
- **Every later run**: fetches `origin`, and if there are new commits, prints a
  one-line summary of each and asks `Update now? [y/N]` before launching. Only
  fast-forwards (never overwrites local changes in `src/`).
- **After a successful update**: caches are wiped (all `__pycache__`/`*.pyc`
  under `src/`, plus any globs you list in a `.update-clean` file next to
  `src/`) and the venv is re-synced.
- Non-interactive runs (no TTY, e.g. cron/automation) skip the check entirely
  rather than blocking on a prompt.

## Turning off the update prompt

```bash
./run.sh --check-updates=off   # stop asking; app launches immediately
./run.sh --check-updates=on    # resume asking
```

The setting persists in `.check-updates` (gitignored) until changed again.
