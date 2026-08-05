#!/usr/bin/env python3
"""deck-serial — UART / serial console monitor + logger.

Lists serial ports, opens one at a chosen baud, streams incoming bytes to a
themed TUI, lets you send lines back, and optionally tees everything to a log
file. Pairs with deck-gpio for board bring-up. Uses pyserial.

    ./run.sh                       TUI (pick a port)
    ./run.sh --list                list serial ports (CLI)
    ./run.sh --port /dev/ttyUSB0 --baud 115200   open directly
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deck-lib"))

try:
    import serial
    import serial.tools.list_ports as list_ports
except Exception:  # pragma: no cover
    serial = None
    list_ports = None

BAUDS = [9600, 19200, 38400, 57600, 115200, 230400]


def ports() -> list[tuple[str, str]]:
    if not list_ports:
        return []
    return [(p.device, p.description) for p in list_ports.comports()]


def cli_list():
    ps = ports()
    if not serial:
        print("pyserial not installed (pip install pyserial)."); return
    if not ps:
        print("No serial ports found."); return
    for dev, desc in ps:
        print(f"{dev:16} {desc}")


def run_tui(port: str | None, baud: int, logfile: str | None):
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, Input, RichLog
        from textual import work
    except Exception as e:
        print(f"Textual unavailable ({e}).")
        cli_list(); return
    try:
        from deck_theme import apply_theme, DECK_CSS, styled
    except Exception:
        def apply_theme(_): pass
        def styled(_n, t): return t
        DECK_CSS = ""

    class Serial(App):
        TITLE = "deck-serial"
        SUB_TITLE = "UART monitor"
        CSS = DECK_CSS + """
        #top { height: 1fr; }
        #ports { width: 32%; }
        RichLog { border: round $primary; background: $surface; }
        #send { margin: 0 1; }
        """
        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("enter", "open", "Open port"),
            Binding("ctrl+l", "clear", "Clear"),
        ]

        def __init__(self):
            super().__init__()
            self.port = port
            self.baud = baud
            self.logfile = logfile
            self.ser = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="top"):
                with Vertical(id="ports"):
                    yield Static(styled("title", "Ports") + "  (Enter to open)")
                    yield ListView(id="portlist")
                with Vertical():
                    yield RichLog(id="log", highlight=True, markup=True, wrap=True)
                    yield Input(placeholder="type + Enter to send…", id="send")
            yield Footer()

        def on_mount(self):
            apply_theme(self)
            lv = self.query_one("#portlist", ListView)
            found = ports()
            if not found:
                lv.append(ListItem(Label(styled("err", "no ports"))))
            for dev, desc in found:
                it = ListItem(Label(styled("ok", "●") + f" {dev}\n  [dim]{desc}[/dim]"))
                it.dev = dev
                lv.append(it)
            lv.index = 0
            log = self.query_one("#log", RichLog)
            if not serial:
                log.write(styled("err", "pyserial not installed — pip install pyserial"))
            else:
                log.write(styled("muted", f"baud {self.baud}. Select a port and press Enter."))
            if self.port:
                self._open(self.port)

        def action_clear(self):
            self.query_one("#log", RichLog).clear()

        def action_open(self):
            it = self.query_one("#portlist", ListView).highlighted_child
            if it is not None and hasattr(it, "dev"):
                self._open(it.dev)

        def _open(self, dev: str):
            if not serial:
                return
            try:
                if self.ser:
                    self.ser.close()
                self.ser = serial.Serial(dev, self.baud, timeout=0.2)
                self.port = dev
                self.query_one("#log", RichLog).write(styled("ok", f"opened {dev} @ {self.baud}"))
                self._reader()
            except Exception as e:
                self.query_one("#log", RichLog).write(styled("err", f"open failed: {e}"))

        @work(thread=True)
        def _reader(self):
            log = self.query_one("#log", RichLog)
            fh = open(self.logfile, "a", encoding="utf-8") if self.logfile else None
            try:
                while self.ser and self.ser.is_open:
                    try:
                        data = self.ser.readline()
                    except Exception:
                        break
                    if data:
                        text = data.decode("utf-8", "replace").rstrip("\r\n")
                        self.call_from_thread(log.write, text)
                        if fh:
                            fh.write(text + "\n"); fh.flush()
                    else:
                        time.sleep(0.02)
            finally:
                if fh:
                    fh.close()

        def on_input_submitted(self, event: Input.Submitted):
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write((event.value + "\n").encode())
                    self.query_one("#log", RichLog).write(styled("primary", f"> {event.value}"))
                except Exception as e:
                    self.query_one("#log", RichLog).write(styled("err", f"write failed: {e}"))
            event.input.value = ""

    Serial().run()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="deck-serial")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--port", help="serial device, e.g. /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--log", metavar="FILE", help="tee output to a log file")
    a = ap.parse_args()
    if a.list:
        cli_list()
    else:
        run_tui(a.port, a.baud, a.log)
