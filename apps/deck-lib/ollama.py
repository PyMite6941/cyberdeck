from __future__ import annotations

import json
import urllib.request

OLLAMA_URL = "http://localhost:11434"
DEFAULT_OPTS = {"num_thread": 4}


def generate(model: str, prompt: str, stream: bool = False, num_ctx: int = 4096, **kwargs) -> dict:
    opts = {**DEFAULT_OPTS, "num_ctx": num_ctx, **kwargs}
    payload = json.dumps({"model": model, "prompt": prompt, "stream": stream, "options": opts}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def list_models() -> list[str]:
    req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
    with urllib.request.urlopen(req, timeout=5) as r:
        return [m["name"] for m in json.loads(r.read()).get("models", [])]
