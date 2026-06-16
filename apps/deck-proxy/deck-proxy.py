from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.request

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, RichLog, Select, TextArea
from textual import work

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy.db")
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:3b"


PROMPT_TEMPLATES = {
    "explain": "Explain the following in simple terms:\n\n{prompt}",
    "code-review": "Review this code for bugs, security issues, and style:\n\n{prompt}",
    "summarize": "Summarize the following concisely:\n\n{prompt}",
    "translate-to-python": "Translate the following to Python:\n\n{prompt}",
    "write-docs": "Write documentation for the following:\n\n{prompt}",
    "debug": "Debug the following. Identify the issue and suggest a fix:\n\n{prompt}",
    "raw": "{prompt}",
}


def init_db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, model TEXT, template TEXT,
            prompt TEXT, response TEXT)""")
    cx.commit()
    cx.close()


def get_available_backends():
    backends = [("ollama (local)", "ollama")]
    if os.environ.get("ANTHROPIC_API_KEY"):
        backends.append(("claude (cloud)", "claude"))
    if os.environ.get("OPENAI_API_KEY"):
        backends.append(("openai (cloud)", "openai"))
    return backends


def get_ollama_models():
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def call_ollama(prompt, model, template="raw"):
    tmpl = PROMPT_TEMPLATES.get(template, PROMPT_TEMPLATES["raw"])
    full_prompt = tmpl.replace("{prompt}", prompt)
    payload = json.dumps({
        "model": model, "prompt": full_prompt, "stream": False,
        "options": {"num_ctx": 4096, "num_thread": 4}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["response"]


class ProxyApp(App):
    TITLE = "Deck-Proxy"
    SUBTITLE = "AI prompt router"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    #input-area { height: 8; margin: 0 1; }
    #control-row { height: 5; margin: 0 1; }
    RichLog { height: 1fr; }
    DataTable { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+enter", "submit", "Send"),
        Binding("f5", "history", "History"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Deck-Proxy — AI Prompt Router[/bold]", id="toolbar")
        with Horizontal(id="control-row"):
            yield Select(
                [(t.replace("-", " ").title(), t) for t in PROMPT_TEMPLATES],
                prompt="Template", id="template-select", value="raw"
            )
            yield Select([], prompt="Model", id="model-select")
            yield Select([("Ollama (local)", "ollama")], prompt="Backend",
                         id="backend-select", value="ollama")
            yield Button("Send", variant="primary", id="send-btn")
        yield TextArea(id="prompt-input", soft_wrap=True)
        yield RichLog(id="response-log", highlight=True, markup=True)
        yield Static("Type a prompt and press Send (Ctrl+Enter).", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._response_log = self.query_one("#response-log", RichLog)
        self._status = self.query_one("#status-bar", Static)
        models = get_ollama_models()
        sel = self.query_one("#model-select", Select)
        sel.set_options([(m, m) for m in models]) if models else sel.set_options([])
        self.query_one("#prompt-input", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            prompt = self.query_one("#prompt-input", TextArea).text.strip()
            if not prompt:
                return
            template = self.query_one("#template-select", Select).value
            model = self.query_one("#model-select", Select).value
            backend = self.query_one("#backend-select", Select).value
            self._do_send(prompt, template, model, backend)

    def action_submit(self):
        prompt = self.query_one("#prompt-input", TextArea).text.strip()
        if not prompt:
            return
        template = self.query_one("#template-select", Select).value
        model = self.query_one("#model-select", Select).value
        backend = self.query_one("#backend-select", Select).value
        self._do_send(prompt, template, model, backend)

    @work(thread=True)
    def _do_send(self, prompt, template, model, backend):
        self.call_from_thread(self._response_log.clear)
        self.call_from_thread(self._response_log.write,
                              f"[dim]{template.upper()} → {model} ({backend})[/dim]")
        self.call_from_thread(self._response_log.write, f"[dim]Prompt: {prompt[:80]}...[/dim]\n")
        self.call_from_thread(self._status.update, "Generating...")

        try:
            if backend == "ollama":
                response = call_ollama(prompt, model, template)
            else:
                response = f"[yellow]{backend} backend not yet implemented[/yellow]"

            cx = sqlite3.connect(DB_PATH)
            cx.execute(
                "INSERT INTO history(date, model, template, prompt, response) VALUES(?,?,?,?,?)",
                (time.strftime("%Y-%m-%d %H:%M"), model, template, prompt[:200], response[:500]))
            cx.commit()
            cx.close()

            self.call_from_thread(self._response_log.write, response)
            self.call_from_thread(self._status.update, f"Done ({len(response)} chars)")
        except Exception as e:
            self.call_from_thread(self._response_log.write, f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    app = ProxyApp()
    app.run()
