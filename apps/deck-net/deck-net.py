from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, RichLog, Select, TextArea
from textual import work


SCAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scans")

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5-coder:3b"


def check_tool(name):
    try:
        subprocess.run([name, "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


class ScanWorker:
    PROFILES = {
        "quick": ["-sn"],
        "stealth": ["-sS", "-T2"],
        "service": ["-sV", "-T4"],
        "full": ["-p-", "-sV", "-T4"],
        "vuln": ["--script", "vuln", "-sV"],
    }

    @staticmethod
    def run_nmap(target, profile="quick", extra=""):
        cmd = ["nmap"]
        cmd.extend(ScanWorker.PROFILES.get(profile, ScanWorker.PROFILES["quick"]))
        if extra:
            cmd.extend(extra.split())
        cmd.append(target)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            return "nmap timed out after 300s"
        except FileNotFoundError:
            return "nmap not installed"
        except Exception as e:
            return str(e)

    @staticmethod
    def run_tcpdump(interface="any", count=10, filter_expr=""):
        cmd = ["tcpdump", "-i", interface, "-c", str(count), "-nn", "-v"]
        if filter_expr:
            cmd.extend([filter_expr])
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return r.stdout + r.stderr
        except Exception as e:
            return str(e)


class ExplainScreen(ModalScreen):
    def __init__(self, text: str, title: str = "Analysis"):
        super().__init__()
        self.analysis_text = text
        self.dialog_title = title

    def compose(self) -> ComposeResult:
        yield Static(f"[bold cyan]{self.dialog_title}[/bold cyan]", id="explain-title")
        yield RichLog(id="explain-output", highlight=True, markup=True)
        yield Button("Close", variant="primary", id="close-explain")

    def on_mount(self) -> None:
        log = self.query_one("#explain-output", RichLog)
        log.write("[dim]Analyzing with Ollama...[/dim]")
        threading.Thread(target=self._analyze, daemon=True).start()

    def _analyze(self):
        prompt = (
            "You are a cybersecurity expert analyzing network scan results. "
            "Summarize the findings, point out any security risks, and suggest "
            "next steps. Be concise.\n\n"
            f"Scan results:\n{self.analysis_text[:6000]}"
        )
        payload = json.dumps({
            "model": OLLAMA_MODEL, "prompt": prompt,
            "stream": False, "options": {"num_ctx": 4096, "num_thread": 4}
        }).encode()
        try:
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            log = self.query_one("#explain-output", RichLog)
            self.call_from_thread(log.clear)
            self.call_from_thread(log.write, data["response"])
        except Exception as e:
            log = self.query_one("#explain-output", RichLog)
            self.call_from_thread(log.write, f"[red]Ollama error: {e}[/red]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-explain":
            self.app.pop_screen()


class NetApp(App):
    TITLE = "Deck-Net"
    SUBTITLE = "network field toolkit"
    CSS = """
    Screen { background: $surface; }
    #toolbar { height: 3; margin: 1 1 0 1; }
    #scan-row { height: 5; margin: 0 1; }
    #results-box { height: 1fr; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; }
    Button { min-width: 14; }
    Select { width: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+e", "explain_selected", "Explain"),
        Binding("ctrl+p", "toggle_packet", "Packet Capture"),
        Binding("f5", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Network Field Toolkit[/bold]", id="toolbar")
        with Horizontal(id="scan-row"):
            yield Input(placeholder="Target (IP, range, or hostname)...", id="target-input")
            yield Select(
                [(k.upper(), k) for k in ScanWorker.PROFILES],
                prompt="Profile", id="profile-select", value="quick"
            )
            yield Button("Scan", variant="primary", id="scan-btn")
            yield Button("Explain", id="explain-btn")
            yield Button("Capture", id="capture-btn")
        yield RichLog(id="output-log", highlight=True, markup=True)
        yield Static("Ready.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        os.makedirs(SCAN_DIR, exist_ok=True)
        self._log = self.query_one("#output-log", RichLog)
        self._status = self.query_one("#status-bar", Static)
        tools = []
        for t in ["nmap", "tcpdump", "tshark"]:
            if check_tool(t):
                tools.append(f"[green]{t}[/green]")
            else:
                tools.append(f"[dim]{t} (not installed)[/dim]")
        self._log.write(f"Tools: {' | '.join(tools)}")
        self._log.write("Enter a target and press Scan to begin.")
        self.query_one("#target-input", Input).focus()

    @work(thread=True)
    def _do_scan(self, target, profile):
        self.call_from_thread(self._log.clear)
        self.call_from_thread(self._log.write, f"[cyan]Scanning {target} ({profile})...[/cyan]")
        self.call_from_thread(self._status.update, f"Scanning {target}...")
        output = ScanWorker.run_nmap(target, profile)
        safe = re.sub(r'[^a-zA-Z0-9.-]', '_', target)
        filename = f"scan_{safe}_{int(time.time())}.txt"
        path = os.path.join(SCAN_DIR, filename)
        with open(path, "w") as f:
            f.write(output)
        display = output[:5000] if len(output) > 5000 else output
        self.call_from_thread(self._log.write, display)
        self.call_from_thread(self._log.write, f"\n[dim]Full output saved to {path}[/dim]")
        self.call_from_thread(self._status.update, f"Done — {len(output)} bytes from {target}")
        self._last_output = output

    @work(thread=True)
    def _do_capture(self, count=10):
        self.call_from_thread(self._log.clear)
        self.call_from_thread(self._log.write, "[cyan]Capturing packets (10 packets, any interface)...[/cyan]")
        output = ScanWorker.run_tcpdump(count=count)
        self.call_from_thread(self._log.write, output[:5000] if len(output) > 5000 else output)
        self._last_output = output

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "target-input":
            self._do_scan(event.value, "quick")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan-btn":
            target = self.query_one("#target-input", Input).value.strip()
            if target:
                profile = self.query_one("#profile-select", Select).value
                self._do_scan(target, profile)
        elif event.button.id == "explain-btn":
            self._explain_last()
        elif event.button.id == "capture-btn":
            self._do_capture()

    def _explain_last(self):
        output = getattr(self, "_last_output", None)
        if not output:
            log = self.query_one("#output-log", RichLog)
            log.write("[yellow]Nothing to explain — run a scan or capture first[/yellow]")
            return
        self.push_screen(ExplainScreen(output, "Network Scan Analysis"))

    def action_explain_selected(self):
        self._explain_last()


if __name__ == "__main__":
    app = NetApp()
    app.run()
