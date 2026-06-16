from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, RichLog, Select, Label
from textual import work

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval.db")
OLLAMA_URL = "http://localhost:11434"


def init_db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, model TEXT, benchmark TEXT,
            params TEXT, score REAL, tok_s REAL, notes TEXT)""")
    cx.commit()
    cx.close()


def get_models():
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


BENCHMARKS = {
    "HumanEval (Python)": {
        "prompts": [
            "Write a Python function that returns the sum of all multiples of 3 or 5 below n.",
            "Write a Python function that checks if a string is a palindrome.",
            "Write a Python function that finds the longest common prefix of a list of strings.",
            "Write a Python function implementing binary search on a sorted list.",
            "Write a Python function that merges two sorted lists into one sorted list.",
        ],
        "check": lambda code, i: True,
    },
    "GSM8K (Math)": {
        "prompts": [
            "If a train travels 120 km in 2 hours, how far does it travel in 30 minutes?",
            "A store sells apples for $0.50 each and oranges for $0.75 each. "
            "If John buys 3 apples and 2 oranges, how much does he pay?",
            "Solve for x: 3x + 7 = 22",
            "What is 15% of 200?",
            "If it takes 6 people 4 hours to paint a house, how long would it take 3 people?",
        ],
        "check": lambda ans, i: True,
    },
    "MMLU (Knowledge)": {
        "prompts": [
            "What is the boiling point of water at sea level in Celsius?",
            "Which planet is known as the Red Planet?",
            "What is the chemical symbol for gold?",
            "Who wrote 'Romeo and Juliet'?",
            "What is the speed of light in a vacuum (m/s)?",
        ],
        "check": lambda ans, i: True,
    },
}


class BenchmarkRunner:
    @staticmethod
    def run(model, benchmark_name, num_ctx=2048, num_thread=4):
        bench = BENCHMARKS[benchmark_name]
        prompts = bench["prompts"]
        correct = 0
        total_tokens = 0
        total_time = 0

        for i, prompt in enumerate(prompts):
            payload = json.dumps({
                "model": model, "prompt": prompt, "stream": False,
                "options": {"num_ctx": num_ctx, "num_thread": num_thread}
            }).encode()
            try:
                start = time.time()
                req = urllib.request.Request(
                    f"{OLLAMA_URL}/api/generate", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.loads(r.read())
                elapsed = time.time() - start
                total_time += elapsed
                total_tokens += data.get("eval_count", 0)
                correct += 1
            except Exception as e:
                continue

        score = correct / len(prompts) * 100 if prompts else 0
        tok_s = total_tokens / total_time if total_time > 0 else 0
        return score, tok_s


class EvalApp(App):
    TITLE = "Deck-Eval"
    SUBTITLE = "local model benchmark harness"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    #control-row { height: 5; margin: 0 1; }
    DataTable { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f5", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Deck-Eval — Local Model Benchmark[/bold]", id="toolbar")
        with Horizontal(id="control-row"):
            yield Select([], prompt="Model", id="model-select")
            yield Select([(k, k) for k in BENCHMARKS], prompt="Benchmark", id="bench-select")
            yield Button("Run Benchmark", variant="primary", id="run-btn")
            yield Button("Refresh Models", id="refresh-btn")
        yield DataTable(id="results-table")
        yield Static("Select a model and benchmark, then press Run.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._results_table = self.query_one("#results-table", DataTable)
        self._status = self.query_one("#status-bar", Static)
        self._results_table.cursor_type = "row"
        self._results_table.zebra_stripes = True
        self._results_table.add_columns("Date", "Model", "Benchmark", "Score", "tok/s", "Notes")
        self._refresh_models()
        self._load_history()

    def _refresh_models(self):
        models = get_models()
        sel = self.query_one("#model-select", Select)
        sel.set_options([(m, m) for m in models]) if models else sel.set_options([])

    def _load_history(self):
        cx = sqlite3.connect(DB_PATH)
        rows = cx.execute(
            "SELECT date, model, benchmark, score, tok_s, notes "
            "FROM benchmarks ORDER BY id DESC LIMIT 50").fetchall()
        cx.close()
        self._results_table.clear()
        for r in rows:
            self._results_table.add_row(r[0], r[1][:20], r[2][:15], f"{r[3]:.1f}%", f"{r[4]:.1f}", r[5] or "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            model = self.query_one("#model-select", Select).value
            bench = self.query_one("#bench-select", Select).value
            if not model or not bench:
                self._status.update("[yellow]Select a model and benchmark[/yellow]")
                return
            self._run_benchmark(model, bench)
        elif event.button.id == "refresh-btn":
            self._refresh_models()
            self._status.update("Models refreshed.")

    @work(thread=True)
    def _run_benchmark(self, model, bench):
        self.call_from_thread(self._status.update, f"Running {bench} on {model}...")

        score, tok_s = BenchmarkRunner.run(model, bench)

        cx = sqlite3.connect(DB_PATH)
        cx.execute(
            "INSERT INTO benchmarks(date, model, benchmark, params, score, tok_s, notes) "
            "VALUES(?,?,?,?,?,?,?)",
            (time.strftime("%Y-%m-%d %H:%M"), model, bench,
             "num_ctx=2048,threads=4", score, tok_s, ""))
        cx.commit()
        cx.close()

        self.call_from_thread(self._status.update,
                              f"Done: {bench} on {model} — {score:.1f}%, {tok_s:.1f} tok/s")
        self.call_from_thread(self._load_history)


if __name__ == "__main__":
    app = EvalApp()
    app.run()
