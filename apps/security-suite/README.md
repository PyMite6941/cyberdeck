# security-suite

Encrypted vault app — 2FA, password generation, breach checking. CLI
(questionary) + TUI (Textual). Actual source: [PyMite6941/Security-Suite](https://github.com/PyMite6941/Security-Suite).

This folder only holds a launcher (`run.sh`); it is **not** the app itself
and is not a git submodule. That's on purpose — the previous submodule pin
required this repo to be re-committed every time the vault app changed
upstream, and checking whether the pin was stale needed cross-repo access
this repo doesn't always have. The sync logic itself lives in the shared
`apps/_vendor_launcher.sh` (see `apps/README.md` § "Vendoring an external
app") so any future app that wraps an external repo can reuse it — this is
an `apps/`-only convention; the `os/` layer is never auto-update-checked.

## How it works

- **First run**: `./run.sh` clones `Security-Suite` into `src/` (gitignored —
  it's a live clone the deck manages, not vendored code).
- **Every later run**: fetches `origin`, and if there are new commits, prints
  a one-line summary of each and asks `Update now? [y/N]` before launching.
  Only fast-forwards (never overwrites local changes in `src/`).
- Non-interactive runs (no TTY, e.g. cron/automation) skip the check
  entirely rather than blocking on a prompt.

## Turning off the update prompt

```bash
./run.sh --check-updates=off   # stop asking; app launches immediately
./run.sh --check-updates=on    # resume asking
```

The setting persists in `.check-updates` (gitignored) until changed again.
