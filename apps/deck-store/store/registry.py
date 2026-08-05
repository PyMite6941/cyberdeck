"""Load and search the app catalog.

The catalog is a local ``registry.json`` bundled next to the store so browsing
works fully offline. If it declares a ``remote`` URL, ``refresh_remote()`` can
merge a fresher copy over the top when there's a connection.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(HERE, "registry.json")


@dataclass
class App:
    id: str
    name: str
    summary: str
    category: str
    tags: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    requires_pkg: list[str] = field(default_factory=list)
    source: dict = field(default_factory=dict)
    entry: str = "run.sh"

    @property
    def source_type(self) -> str:
        return self.source.get("type", "builtin")

    @property
    def repo_url(self) -> str:
        return self.source.get("url", "")

    @property
    def branch(self) -> str:
        return self.source.get("branch", "main")

    @property
    def is_vendored(self) -> bool:
        return self.source_type == "git"

    def matches(self, query: str) -> bool:
        q = query.lower().strip()
        if not q:
            return True
        hay = " ".join([self.id, self.name, self.summary, self.category, *self.tags]).lower()
        return q in hay


class Registry:
    def __init__(self, data: dict):
        self.version = data.get("version", 1)
        self.updated = data.get("updated", "")
        self.remote = data.get("remote", "")
        self.categories = data.get("categories", [])
        self.apps = [App(**{k: v for k, v in a.items() if k in App.__dataclass_fields__})
                     for a in data.get("apps", [])]

    @classmethod
    def load(cls, path: str = REGISTRY_PATH) -> "Registry":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def get(self, app_id: str) -> App | None:
        for a in self.apps:
            if a.id == app_id:
                return a
        return None

    def search(self, query: str = "", category: str = "") -> list[App]:
        out = []
        for a in self.apps:
            if category and category != "All" and a.category != category:
                continue
            if not a.matches(query):
                continue
            out.append(a)
        return out

    def refresh_remote(self, timeout: int = 8) -> bool:
        """Merge a fresher catalog from ``remote`` if reachable. Returns success."""
        if not self.remote:
            return False
        try:
            with urllib.request.urlopen(self.remote, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:
            return False
        merged = Registry(data)
        # Replace the whole catalog with the remote one (it's authoritative).
        self.version = merged.version
        self.updated = merged.updated
        self.categories = merged.categories
        self.apps = merged.apps
        return True
