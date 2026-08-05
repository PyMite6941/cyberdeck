"""Per-app install status, git-commit tracking, and update detection.

Status values:
    installed  ✓  vendored app cloned and up to date with its remote
    update     ⟳  vendored app cloned but behind its remote  -> Update tab
    available  ○  vendored app not cloned yet
    builtin    ◆  ships with the deck (lives in this repo; no separate update)

Update detection is explicit (call ``refresh()``), not automatic, so opening the
store never blocks on the network. Results are cached in ``state.json`` (next to
the store, gitignored) so the loaded commit / update flag persist between runs
and are readable offline.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict

from .registry import App

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.dirname(HERE)                     # .../apps
STATE_PATH = os.path.join(HERE, "state.json")

INSTALLED = "installed"
UPDATE = "update"
AVAILABLE = "available"
BUILTIN = "builtin"


def _git(src: str, *args: str, timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", "-C", src, *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or p.stderr).strip()
    except Exception as e:
        return 1, str(e)


def app_dir(app: App) -> str:
    return os.path.join(APPS_DIR, app.id)


def src_dir(app: App) -> str:
    return os.path.join(app_dir(app), "src")


def is_cloned(app: App) -> bool:
    return os.path.isdir(os.path.join(src_dir(app), ".git"))


def local_commit(app: App) -> str:
    if not is_cloned(app):
        return ""
    rc, out = _git(src_dir(app), "rev-parse", "--short", "HEAD")
    return out if rc == 0 else ""


@dataclass
class Status:
    id: str
    state: str                 # INSTALLED | UPDATE | AVAILABLE | BUILTIN
    local: str = ""            # short commit loaded (vendored apps)
    remote: str = ""           # short commit on origin (after a refresh)
    behind: int = 0            # commits behind origin
    checked_at: float = 0.0    # unix time of last remote check

    @property
    def update_available(self) -> bool:
        return self.state == UPDATE

    @property
    def installed(self) -> bool:
        return self.state in (INSTALLED, UPDATE, BUILTIN)


class StateStore:
    """Owns state.json and computes live status per app."""

    def __init__(self):
        self.cache: dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                self.cache = json.load(f)
        except Exception:
            self.cache = {}

    def _save(self):
        try:
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def status(self, app: App) -> Status:
        """Current status, using cached remote info from the last refresh."""
        if not app.is_vendored:
            # Builtin: installed iff its folder exists in the repo.
            present = os.path.isdir(app_dir(app))
            return Status(app.id, BUILTIN if present else AVAILABLE)

        if not is_cloned(app):
            return Status(app.id, AVAILABLE)

        local = local_commit(app)
        c = self.cache.get(app.id, {})
        remote = c.get("remote", "")
        behind = int(c.get("behind", 0) or 0)
        checked = float(c.get("checked_at", 0) or 0)
        # If a prior refresh saw us behind AND we're still on that local commit,
        # keep flagging the update; otherwise we're current as far as we know.
        state = UPDATE if (behind > 0 and local and local == c.get("local", local)) else INSTALLED
        return Status(app.id, state, local=local, remote=remote, behind=behind, checked_at=checked)

    def refresh(self, app: App) -> Status:
        """Hit the network: fetch origin and recompute behind-count. Caches it."""
        if not app.is_vendored or not is_cloned(app):
            return self.status(app)
        src = src_dir(app)
        _git(src, "fetch", "--quiet", "origin", timeout=60)
        rc, branch = _git(src, "symbolic-ref", "--short", "HEAD")
        if rc != 0:
            branch = app.branch
        rc, local_full = _git(src, "rev-parse", "HEAD")
        rc2, remote_full = _git(src, "rev-parse", f"origin/{branch}")
        behind = 0
        if rc == 0 and rc2 == 0 and local_full != remote_full:
            rc3, cnt = _git(src, "rev-list", "--count", f"{local_full}..{remote_full}")
            behind = int(cnt) if rc3 == 0 and cnt.isdigit() else 0
        local = local_commit(app)
        rc4, remote_short = _git(src, "rev-parse", "--short", f"origin/{branch}")
        remote = remote_short if rc4 == 0 else ""
        self.cache[app.id] = {
            "local": local, "remote": remote,
            "behind": behind, "checked_at": time.time(),
        }
        self._save()
        return self.status(app)

    def refresh_all(self, apps: list[App]) -> dict[str, Status]:
        return {a.id: self.refresh(a) for a in apps if a.is_vendored}

    def mark_updated(self, app: App):
        """Clear the update flag after a successful upgrade."""
        self.cache[app.id] = {
            "local": local_commit(app), "remote": local_commit(app),
            "behind": 0, "checked_at": time.time(),
        }
        self._save()
