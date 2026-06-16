from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.request

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, DataTable, RichLog, Button, Select, Label
from textual import work

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ollama-profile.db")
OLLAMA_URL = "http://localhost:11434"

TEST_PROMPTS = {
    512: "What is Python?",
    1024: "Write a detailed explanation of how Linux process scheduling works, including the Completely Fair Scheduler, priority levels, and context switching.",
    2048: "Explain the architecture of a modern C++ compiler. Cover the frontend (lexer, parser, semantic analysis), the IR (LLVM IR, optimization passes), and the backend (instruction selection, register allocation, code generation). Include details about each phase and how they interact.",
    4096: "Write a comprehensive guide to building a real-time operating system for ARM Cortex-M microcontrollers. Cover interrupt handling, task scheduling (preemptive and cooperative), memory management, inter-process communication (queues, semaphores, mutexes), device driver architecture, and power management. Include code examples for key components like the scheduler, context switch routine, and a simple mutex implementation. Also discuss debugging strategies and performance optimization techniques.",
    8192: "Provide a detailed analysis of the TCP/IP protocol stack. Cover each layer: Network Interface (Ethernet, ARP), Internet (IPv4, IPv6, ICMP, routing protocols), Transport (TCP congestion control algorithms — Reno, Cubic, BBR — flow control, window scaling, UDP), and Application (HTTP/2, QUIC, DNS, TLS 1.3). For each protocol, explain the header format, key mechanisms, common vulnerabilities, and performance characteristics. Include a discussion of how these protocols have evolved to meet modern demands, including data center networking, mobile networks, and IoT. Compare Linux and Windows networking stack implementations, highlighting the architectural differences in how they handle interrupts, packet processing (NAPI, RSS), and socket APIs.",
}


def init_db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS profiles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, model TEXT, ctx_len INTEGER,
            prompt_len INTEGER, output_len INTEGER,
            time_s REAL, tok_s REAL, ttft_ms REAL,
            ram_mb_before INTEGER, ram_mb_after INTEGER,
            temp_before REAL, temp_after REAL)""")
    cx.commit()
    cx.close()


def get_ollama_models():
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def get_ram_usage():
    try:
        r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        return int(r.stdout.split("\n")[1].split()[2])
    except Exception:
        return 0


def get_temp():
    try:
        r = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=5)
        return float(r.stdout.split("=")[1].split("'")[0])
    except Exception:
        return 0.0


def profile_model(model, ctx_len, prompt):
    ram_before = get_ram_usage()
    temp_before = get_temp()
    ttft = None

    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"num_ctx": ctx_len, "num_thread": 4}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")

    start = time.time()
    first = True
    output_len = 0
    with urllib.request.urlopen(req, timeout=300) as r:
        for line in r:
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            if first:
                ttft = (time.time() - start) * 1000
                first = False
            if data.get("done"):
                output_len = data.get("eval_count", output_len)
            elif "response" in data:
                output_len += 1

    elapsed = time.time() - start
    ram_after = get_ram_usage()
    temp_after = get_temp()
    tok_s = output_len / elapsed if elapsed > 0 else 0

    return {
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "model": model,
        "ctx_len": ctx_len,
        "prompt_len": len(prompt.split()),
        "output_len": output_len,
        "time_s": round(elapsed, 2),
        "tok_s": round(tok_s, 1),
        "ttft_ms": round(ttft or 0, 1),
        "ram_mb_before": ram_before,
        "ram_mb_after": ram_after,
        "temp_before": round(temp_before, 1),
        "temp_after": round(temp_after, 1),
    }


def save_result(r):
    cx = sqlite3.connect(DB_PATH)
    cx.execute(
        "INSERT INTO profiles(date, model, ctx_len, prompt_len, output_len, "
        "time_s, tok_s, ttft_ms, ram_mb_before, ram_mb_after, temp_before, temp_after) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (r["date"], r["model"], r["ctx_len"], r["prompt_len"], r["output_len"],
         r["time_s"], r["tok_s"], r["ttft_ms"],
         r["ram_mb_before"], r["ram_mb_after"], r["temp_before"], r["temp_after"]))
    cx.commit()
    cx.close()


def get_history(limit=50):
    cx = sqlite3.connect(DB_PATH)
    rows = cx.execute(
        "SELECT date, model, ctx_len, tok_s, ttft_ms, time_s, "
        "ram_mb_after - ram_mb_before, temp_after - temp_before "
        "FROM profiles ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    cx.close()
    return rows


class ProfileScreen(ModalScreen):
    def __init__(self, result: dict):
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        r = self.result
        yield Static(f"[bold cyan]Profile Results[/bold cyan]\n\n"
                     f"Model:         {r['model']}\n"
                     f"Context:       {r['ctx_len']}\n"
                     f"Prompt words:  {r['prompt_len']}\n"
                     f"Output tokens: {r['output_len']}\n"
                     f"Time:          {r['time_s']}s\n"
                     f"Speed:         [green]{r['tok_s']} tok/s[/green]\n"
                     f"TTFT:          {r['ttft_ms']}ms\n"
                     f"RAM delta:     {r['ram_mb_after'] - r['ram_mb_before']} MB\n"
                     f"Temp delta:    {r['temp_after']}°C (was {r['temp_before']}°C)")
        yield Button("Close", variant="primary", id="close-profile")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-profile":
            self.app.pop_screen()


class OllamaProfilerApp(App):
    TITLE = "Deck-Ollama-Profiler"
    SUBTITLE = "LLM inference benchmark"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    #control-row { height: 5; margin: 0 1; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f5", "run_all", "Profile All"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Ollama Profiler[/bold]  (F5=profile all context sizes)")
        with Horizontal(id="control-row"):
            yield Select([], prompt="Model", id="model-select")
            yield Select(
                [(f"ctx={k}", k) for k in sorted(TEST_PROMPTS)],
                prompt="Context", id="ctx-select"
            )
            yield Button("Profile", variant="primary", id="profile-btn")
            yield Button("All Contexts", id="all-btn")
        yield DataTable(id="results-table")
        yield Static("Select a model and context size, then Profile.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._results_table = self.query_one("#results-table", DataTable)
        self._results_table.cursor_type = "row"
        self._results_table.zebra_stripes = True
        self._results_table.add_columns("Date", "Model", "Ctx", "tok/s", "TTFT", "Time", "RAMΔ", "TempΔ")
        self._refresh_models()
        self._load_history()

    def _refresh_models(self):
        models = get_ollama_models()
        sel = self.query_one("#model-select", Select)
        sel.set_options([(m, m) for m in models]) if models else sel.set_options([])

    def _load_history(self):
        self._results_table.clear()
        for row in get_history(50):
            self._results_table.add_row(
                row[0], row[1][:20], str(row[2]),
                f"[green]{row[3]:.1f}[/]",
                f"{row[4]:.0f}ms", f"{row[5]:.1f}s",
                f"{row[6]:+d} MB" if row[6] else "0 MB",
                f"{row[7]:+.1f}°C" if row[7] else "0°C")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "profile-btn":
            model = self.query_one("#model-select", Select).value
            ctx = self.query_one("#ctx-select", Select).value
            if model and ctx:
                self._run_profile(model, ctx)
        elif event.button.id == "all-btn":
            model = self.query_one("#model-select", Select).value
            if model:
                self._run_all(model)

    @work(thread=True)
    def _run_profile(self, model, ctx_len):
        status = self.query_one("#status-bar", Static)
        prompt = TEST_PROMPTS.get(ctx_len, TEST_PROMPTS[2048])
        self.call_from_thread(status.update, f"Profiling {model} at ctx={ctx_len}...")

        try:
            result = profile_model(model, ctx_len, prompt)
            save_result(result)
            self.call_from_thread(self._load_history)
            self.call_from_thread(self.push_screen, ProfileScreen(result))
            self.call_from_thread(status.update,
                                  f"Done: {model} ctx={ctx_len} → {result['tok_s']} tok/s")
        except Exception as e:
            self.call_from_thread(status.update, f"[red]Error: {e}[/red]")

    @work(thread=True)
    def _run_all(self, model):
        status = self.query_one("#status-bar", Static)
        for ctx_len in sorted(TEST_PROMPTS):
            self.call_from_thread(status.update, f"Profiling {model} at ctx={ctx_len}...")
            try:
                prompt = TEST_PROMPTS[ctx_len]
                result = profile_model(model, ctx_len, prompt)
                save_result(result)
                self.call_from_thread(self._load_history)
            except Exception as e:
                self.call_from_thread(status.update, f"[red]Error at ctx={ctx_len}: {e}[/red]")
                break
            time.sleep(2)
        self.call_from_thread(status.update, "All profiles complete.")


if __name__ == "__main__":
    app = OllamaProfilerApp()
    app.run()
