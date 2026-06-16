from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import threading

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, RichLog, Select, TextArea
from textual import work

LAB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labs")
NOTES_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.db")


LAB_TEMPLATES = {
    "web-exploit": {
        "image": "vulnerables/web-dvwa",
        "ports": {"80/tcp": "8080"},
        "description": "Damn Vulnerable Web Application — practice SQLi, XSS, CSRF",
    },
    "linux-privesc": {
        "image": "vulnerables/vulnhub",
        "ports": {"22/tcp": "2222"},
        "description": "Linux privilege escalation challenges",
    },
    "network-pivot": {
        "image": "networkboot/dhcpd",
        "ports": {},
        "description": "Network pivoting lab with multiple containers",
    },
}


def init_notes_db():
    cx = sqlite3.connect(NOTES_DB)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab TEXT, date TEXT, title TEXT, content TEXT)""")
    cx.execute("""
        CREATE TABLE IF NOT EXISTS captures(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab TEXT, date TEXT, tool TEXT, output TEXT)""")
    cx.commit()
    cx.close()


def docker_available():
    try:
        subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


class NoteScreen(Screen):
    def __init__(self, lab: str):
        super().__init__()
        self.lab = lab

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="Note title...", id="note-title")
        yield TextArea(id="note-content", soft_wrap=True)
        with Horizontal():
            yield Button("Save Note", variant="primary", id="save-note")
            yield Button("Back", id="back-btn")
        yield DataTable(id="notes-list")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#notes-list", DataTable)
        table.cursor_type = "row"
        table.add_columns("Date", "Title")
        self._refresh()

    def _refresh(self):
        cx = sqlite3.connect(NOTES_DB)
        rows = cx.execute(
            "SELECT id, date, title FROM notes WHERE lab=? ORDER BY id DESC LIMIT 100",
            (self.lab,)).fetchall()
        cx.close()
        table = self.query_one("#notes-list", DataTable)
        table.clear()
        for r in rows:
            table.add_row(r[1], r[2])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-note":
            title = self.query_one("#note-title", Input).value
            content = self.query_one("#note-content", TextArea).text
            if title:
                cx = sqlite3.connect(NOTES_DB)
                cx.execute(
                    "INSERT INTO notes(lab, date, title, content) VALUES(?,?,?,?)",
                    (self.lab, time.strftime("%Y-%m-%d %H:%M"), title, content))
                cx.commit()
                cx.close()
                self.query_one("#note-title", Input).value = ""
                self.query_one("#note-content", TextArea).text = ""
                self._refresh()
                self.query_one("#save-note", Button).label = "Saved!"
                self.set_timer(2, lambda: setattr(self.query_one("#save-note", Button), "label", "Save Note"))
        elif event.button.id == "back-btn":
            self.app.pop_screen()


class LabApp(App):
    TITLE = "Deck-Lab"
    SUBTITLE = "portable CTF lab-in-a-box"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    #control-row { height: 5; margin: 0 1; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "new_note", "Note"),
        Binding("ctrl+s", "save_scan", "Save Scan"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Deck-Lab — Portable CTF Lab[/bold]", id="toolbar")
        with Horizontal(id="control-row"):
            yield Select([(k, k) for k in LAB_TEMPLATES], prompt="Lab", id="lab-select")
            yield Button("Start Lab", variant="primary", id="start-btn")
            yield Button("Stop Lab", variant="error", id="stop-btn")
            yield Button("Notes", id="notes-btn")
        yield DataTable(id="lab-status")
        yield RichLog(id="output-log", highlight=True, markup=True)
        yield Static("Select a lab template and press Start.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        os.makedirs(LAB_DIR, exist_ok=True)
        init_notes_db()
        self._lab_log = self.query_one("#output-log", RichLog)
        self._lab_status = self.query_one("#status-bar", Static)
        self._lab_table = self.query_one("#lab-status", DataTable)
        self._lab_table.add_columns("Lab", "Container ID", "Status", "Ports")
        self._running_containers = {}
        self._containers_lock = threading.Lock()

    @work(thread=True)
    def _start_lab(self, lab_name):
        lines = []
        lines.append(f"[cyan]Starting {lab_name}...[/cyan]")
        self.call_from_thread(self._lab_log.clear)

        tmpl = LAB_TEMPLATES[lab_name]
        port_args = []
        for internal, external in tmpl["ports"].items():
            port_args.extend(["-p", f"{external}:{internal}"])

        try:
            r = subprocess.run(
                ["docker", "run", "-d", "--name", f"deck-{lab_name}",
                 *port_args, tmpl["image"]],
                capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                cid = r.stdout.strip()[:12]
                with self._containers_lock:
                    self._running_containers[lab_name] = cid
                lines.append(f"[green]Container {cid} started[/green]")
                lines.append(f"  Image: {tmpl['image']}")
                for ext, int in tmpl["ports"].items():
                    lines.append(f"  Port: localhost:{ext} -> {int}")
                self.call_from_thread(self._update_status_table)
                self.call_from_thread(self._lab_log.write, "\n".join(lines))
                self.call_from_thread(self._lab_status.update, f"{lab_name} running ({cid})")
            else:
                lines.append(f"[red]Failed: {r.stderr}[/red]")
                self.call_from_thread(self._lab_log.write, "\n".join(lines))
        except Exception as e:
            self.call_from_thread(self._lab_log.write, f"[red]Error: {e}[/red]")

    @work(thread=True)
    def _stop_lab(self, lab_name):
        self.call_from_thread(self._lab_log.write, f"[yellow]Stopping {lab_name}...[/yellow]")
        subprocess.run(["docker", "stop", f"deck-{lab_name}"],
                       capture_output=True, timeout=30)
        subprocess.run(["docker", "rm", f"deck-{lab_name}"],
                       capture_output=True, timeout=30)
        with self._containers_lock:
            self._running_containers.pop(lab_name, None)
        self.call_from_thread(self._update_status_table)
        self.call_from_thread(self._lab_log.write, f"[yellow]{lab_name} stopped[/yellow]")
        self.call_from_thread(self._lab_status.update, f"{lab_name} stopped")

    def _update_status_table(self):
        table = self.query_one("#lab-status", DataTable)
        table.clear()
        with self._containers_lock:
            items = list(self._running_containers.items())
        for lab, cid in items:
            tmpl = LAB_TEMPLATES.get(lab, {})
            ports = ",".join(tmpl.get("ports", {}).values()) if tmpl else ""
            table.add_row(lab, cid[:12], "running", ports)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        lab_name = self.query_one("#lab-select", Select).value
        if not lab_name:
            return
        if event.button.id == "start-btn":
            self._start_lab(lab_name)
        elif event.button.id == "stop-btn":
            self._stop_lab(lab_name)
        elif event.button.id == "notes-btn":
            self.push_screen(NoteScreen(lab_name))


if __name__ == "__main__":
    app = LabApp()
    app.run()
