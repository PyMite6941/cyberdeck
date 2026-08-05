# grimoire

Offline search + RAG — folds a corpus into one compressed (<1 GB) SQLite tome
you can search with no internet. CLI (rich) + TUI (Textual). Actual source:
[PyMite6941/grimoire](https://github.com/PyMite6941/grimoire).

This folder only holds `install.sh`, `run.sh` and this README — it is **not**
the app; it's a self-updating launcher (same pattern as `security-suite`). See
`apps/README.md` § "Vendoring an external app".

- **`install.sh`** — clones the repo into `src/` with a **private** venv
  (`src/.venv`) and its requirements; later runs offer fast-forward updates and
  wipe caches after a pull.
- **`run.sh`** — ensures installed, then runs the app from that venv.
- **`src/`** — the live clone (gitignored). Your library/tome lives in
  `src/backend/` (the `.db` tome and `data/` corpora) and never leaves the deck.

## Import a library

```bash
./run.sh                                   # launch the search app
python src/import_data.py popular --count 50 --ingest   # pull public-domain books
```

## Update prompt off/on

```bash
./run.sh --check-updates=off
./run.sh --check-updates=on
```
