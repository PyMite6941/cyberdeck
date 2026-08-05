# deck-store

The deck's app store — browse the catalog, see what's installed, install
vendored apps, and get notified when one has an update. CLI + Textual TUI,
cyberdeck theme. A friendly front door over the low-level `deck-app` installer
and the `_vendor_launcher.sh` vendoring convention.

```bash
./run.sh                      # launch the TUI (default)
./run.sh list                 # apps + install status + loaded commit
./run.sh search sdr           # filter by name / tag / category
./run.sh info grimoire        # details, loaded commit, update status
./run.sh install grimoire     # clone a vendored app + build its private venv
./run.sh refresh              # check every vendored app for updates
./run.sh upgrade grimoire     # fast-forward + wipe caches (or: upgrade --all)
./run.sh uninstall grimoire   # delete its src/ clone (prompts; --yes to skip)
```

## Keys (TUI)

| Key | Action |
|---|---|
| `Enter` | install (if not installed) — otherwise run the app |
| `r` | check every vendored app's remote for updates |
| `u` | upgrade the selected app (fast-forward → wipe caches → re-sync venv) |
| `x` | uninstall — **press twice**; see the warning below |
| `/` | jump to search (`Esc` returns to the list) |
| `q` | quit |

Cloning, `pip install` and `git fetch` all run on a background thread, so the
store stays responsive while a job runs; progress shows in the status bar and
only one job runs at a time.

> **Uninstall deletes the whole `src/` directory**, including anything the app
> keeps inside it — for grimoire that's the tome and every corpus you imported,
> which is *not* recoverable. That's why the TUI needs a second `x` to confirm
> (moving the selection cancels it) and the CLI prompts unless you pass `--yes`.
> The `install.sh` / `run.sh` launchers survive, so you can reinstall later.

## Status tags

Every app shows a status glyph, and it updates the moment an action completes:

| Glyph | Meaning |
|---|---|
| `✓` | installed and up to date (vendored app) |
| `⟳` | installed but **update available** — appears in the **Updates** tab |
| `○` | not installed (vendored app you can install) |
| `◆` | built-in — ships with the deck (lives in this repo) |

## Commit tracking & the Updates tab

For vendored (git-backed) apps the store records **which commit is loaded**
(`src/` HEAD) and shows it in the detail pane. Press **`r`** (or run
`deck-store refresh`) to fetch each remote and compare — this is the only step
that touches the network, so opening the store never blocks. If any app is
behind its remote, an **Updates** tab appears listing exactly those apps; press
**`u`** to upgrade (which fast-forwards `src/`, **wipes caches**, and re-syncs
the private venv). Results are cached in `state.json` (gitignored) so the loaded
commit and update flags persist and are readable offline.

## Catalog

Apps come from `registry.json` (bundled, so browsing works offline). Each entry
has a `source.type`:

- `git` — vendored: cloned into `apps/<id>/src/` with a private venv,
  commit-tracked, update-detectable.
- `builtin` — ships with the deck; "installing" is a no-op.

Set a `remote` URL in `registry.json` to allow `deck-store refresh` to merge a
fresher catalog when online.
