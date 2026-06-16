# Agent conventions for cyberdeck/

Read `README.md` (project map) and `os/README.md` (OS layer docs) first.

1. **Log every change in `CHANGELOG.md`** — date, what, why. This is the project's
   memory across humans and agents.
2. **`hardware/` is upstream** — a git submodule of the DFCD repo. Never edit
   files in it; update with `git submodule update --remote hardware`.
   Customised CAD goes in `hardware-custom/` (create on first use, mirror the
   upstream folder structure).
3. **`os/` must stay minimal and idempotent** — see "Design constraints" in
   `os/README.md`. New boot behaviour = new file in `os/boot/boot.d/`, not edits to
   the runner or the systemd unit.
4. **Shell scripts use LF endings** (`.gitattributes` enforces this; the repo
   lives on a filesystem shared with Windows, so be careful with tools that
   rewrite files).
5. Anything in `os/` must work on **Raspberry Pi 4B and newer** (the DFCD design
   uses a Pi 5, but don't add Pi-5-only assumptions), targeting Raspberry Pi OS
   64-bit (Debian Bookworm+), bash, systemd. Memory configs live in `os/memory/`.
6. Test scripts off-Pi before committing: `bash -n` for syntax, and the boot
   runner accepts `BOOT_D=... LOG=...` overrides for a dry run.
