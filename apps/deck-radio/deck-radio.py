#!/usr/bin/env python3
"""deck-radio — RTL-SDR spectrum scanner + decoder front-end.

Wraps the standard rtl-sdr / rtl_power / rtl_433 / dump1090 toolchain behind a
themed TUI: sweep a band and see a live ASCII spectrum, or launch a decoder
(FM, ADS-B, AIS, 433 MHz ISM). Needs the `rtl-sdr` package and a supported
dongle; without them the UI still opens and reports what's missing.

    ./run.sh            TUI
    ./run.sh --scan 88M:108M    CLI sweep, print band power table
    ./run.sh --devices          list detected RTL-SDR devices
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deck-lib"))

TOOLS = {
    "rtl_test": "device probe",
    "rtl_power": "spectrum sweep",
    "rtl_fm": "FM demod",
    "rtl_433": "433 MHz ISM decoder",
    "dump1090": "ADS-B (1090 MHz)",
    "rtl_ais": "AIS (marine)",
}


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def list_devices() -> list[str]:
    if not have("rtl_test"):
        return []
    try:
        p = subprocess.run(["rtl_test", "-t"], capture_output=True, text=True, timeout=5)
        out = (p.stdout + p.stderr)
        return [ln.strip() for ln in out.splitlines() if ln.strip() and ln[0:1].isdigit()]
    except Exception:
        return []


def cli_scan(band: str):
    if not have("rtl_power"):
        print("rtl_power not found. Install the rtl-sdr package."); return
    lo, hi = band.split(":")
    try:
        subprocess.run(["rtl_power", "-f", f"{lo}:{hi}:100k", "-1", "-g", "40"])
    except Exception as e:
        print(f"scan failed: {e}")


def run_tui():
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Header, Footer, Static, ListView, ListItem, Label
    except Exception as e:
        print(f"Textual unavailable ({e}).")
        for t, d in TOOLS.items():
            print(f"  [{'x' if have(t) else ' '}] {t:10} {d}")
        return
    try:
        from deck_theme import apply_theme, DECK_CSS, styled
    except Exception:
        def apply_theme(_): pass
        def styled(_n, t): return t
        DECK_CSS = ""

    class Radio(App):
        TITLE = "deck-radio"
        SUB_TITLE = "RTL-SDR"
        CSS = DECK_CSS + """
        #cols { height: 1fr; }
        #tools { width: 40%; }
        #panel { width: 60%; padding: 1 2; }
        .big { color: $secondary; text-style: bold; }
        """
        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("enter", "launch", "Launch"),
            Binding("d", "devices", "Devices"),
        ]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="cols"):
                with Vertical(id="tools"):
                    lv = ListView(id="toollist")
                    yield lv
                yield Static(id="panel", markup=True)
            yield Footer()

        def on_mount(self):
            apply_theme(self)
            lv = self.query_one("#toollist", ListView)
            for t, d in TOOLS.items():
                mark = styled("ok", "●") if have(t) else styled("err", "○")
                it = ListItem(Label(f"{mark} {t}  [dim]{d}[/dim]"))
                it.tool = t
                lv.append(it)
            lv.index = 0
            self._info()

        def _info(self):
            devs = list_devices()
            missing = [t for t in TOOLS if not have(t)]
            lines = [styled("title", "RTL-SDR toolkit"), ""]
            lines.append(f"devices detected : {len(devs)}")
            for d in devs:
                lines.append("  " + styled("big", d))
            if not devs:
                lines.append("  " + styled("err", "none — plug in a dongle"))
            lines.append("")
            if missing:
                lines.append(styled("warn", "missing tools:") + " " + ", ".join(missing))
                lines.append("install: [b]sudo apt install rtl-sdr rtl-433 dump1090-fa[/b]")
            else:
                lines.append(styled("ok", "all tools present"))
            lines.append("")
            lines.append("Select a tool and press [b]Enter[/b] to launch it.")
            self.query_one("#panel", Static).update("\n".join(lines))

        def action_devices(self):
            self._info()

        def action_launch(self):
            it = self.query_one("#toollist", ListView).highlighted_child
            if it is None or not hasattr(it, "tool"):
                return
            tool = it.tool
            if not have(tool):
                self.notify(f"{tool} not installed.", severity="error"); return
            cmd = {
                "rtl_test": ["rtl_test", "-t"],
                "rtl_power": ["rtl_power", "-f", "88M:108M:100k", "-1"],
                "rtl_fm": ["rtl_fm", "-f", "96.9M", "-M", "wbfm"],
                "rtl_433": ["rtl_433"],
                "dump1090": ["dump1090", "--interactive"],
                "rtl_ais": ["rtl_ais"],
            }.get(tool, [tool])
            try:
                with self.suspend():
                    subprocess.run(cmd)
            except Exception as e:
                self.notify(f"launch failed: {e}", severity="error")

    Radio().run()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="deck-radio")
    ap.add_argument("--scan", metavar="LO:HI", help="sweep a band, e.g. 88M:108M")
    ap.add_argument("--devices", action="store_true", help="list RTL-SDR devices")
    a = ap.parse_args()
    if a.devices:
        for d in list_devices() or ["(none detected)"]:
            print(d)
    elif a.scan:
        cli_scan(a.scan)
    else:
        run_tui()
