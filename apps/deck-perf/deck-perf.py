from __future__ import annotations

import os
import subprocess
import time
import threading
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, DataTable, Button, TabbedContent, TabPane
from textual.widgets import ProgressBar
from textual.reactive import reactive
from textual import work


def get_cpu_freqs():
    freqs = {}
    for i in range(8):
        try:
            p = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq"
            with open(p) as f:
                freqs[i] = int(f.read().strip()) // 1000
        except Exception:
            pass
    return freqs


def get_temp():
    try:
        r = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=2)
        return float(r.stdout.split("=")[1].split("'")[0])
    except Exception:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000
        except Exception:
            return 0.0


def get_throttled():
    try:
        r = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2)
        val = r.stdout.strip().split("=")[1]
        return int(val, 16)
    except Exception:
        return 0


def get_governor():
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") as f:
            return f.read().strip()
    except Exception:
        return "n/a"


def set_governor(gov):
    for i in range(8):
        try:
            p = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"
            if os.access(p, os.W_OK):
                with open(p, "w") as f:
                    f.write(gov)
        except Exception:
            pass


def get_mem_info():
    try:
        r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=2)
        lines = r.stdout.strip().split("\n")
        mem = lines[1].split()
        swap = lines[2].split()
        return {
            "total": int(mem[1]), "used": int(mem[2]), "avail": int(mem[6]),
            "swap_total": int(swap[1]), "swap_used": int(swap[2]),
        }
    except Exception:
        return {"total": 0, "used": 0, "avail": 0, "swap_total": 0, "swap_used": 0}


def get_throttle_flags(val):
    flags = []
    if val & 1: flags.append("UNDER-VOLTAGE")
    if val & 2: flags.append("FREQ-CAPPED")
    if val & 4: flags.append("THROTTLED")
    if val & 8: flags.append("SOFT-TEMP")
    if val & 0x10000: flags.append("HAD-UV")
    if val & 0x20000: flags.append("HAD-FREQ-CAP")
    if val & 0x40000: flags.append("HAD-THROTTLE")
    return flags


THROTTLE_COLORS = {
    "UNDER-VOLTAGE": "red",
    "FREQ-CAPPED": "yellow",
    "THROTTLED": "red",
    "SOFT-TEMP": "yellow",
    "HAD-UV": "dim",
    "HAD-FREQ-CAP": "dim",
    "HAD-THROTTLE": "dim",
}


class PerfApp(App):
    TITLE = "Deck-Perf"
    SUBTITLE = "system performance tuner"
    CSS = """
    #gauges { height: 7; margin: 1; }
    #info-grid { height: auto; margin: 0 1; }
    #temp-row { height: 3; }
    .card { border: solid $primary; padding: 1; margin: 0 1; }
    .card-title { text-style: bold; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    ProgressBar { width: 1fr; }
    Grid { grid-size: 4 2; grid-gutter: 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("p", "set_gov('performance')", "Performance"),
        Binding("o", "set_gov('ondemand')", "Ondemand"),
        Binding("s", "set_gov('powersave')", "Powersave"),
        Binding("space", "toggle_pause", "Pause"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]System Performance Monitor[/bold]  (P=perf O=ondemand S=powersave SPACE=pause)")
        with Grid(id="gauges"):
            for i in range(4):
                yield Static(f"CPU{i}: --- MHz", id=f"cpu{i}")
            for i in range(4, 8):
                yield Static(f"CPU{i}: --- MHz", id=f"cpu{i}")
        with Horizontal(id="temp-row"):
            yield Static("Temp: --°C", id="temp-val")
            yield Static("Throttle: --", id="throttle-val")
            yield Static("Governor: --", id="gov-val")
        with Horizontal(id="info-grid"):
            yield Static("Mem: --/-- MB", id="mem-val")
            yield Static("Swap: --/-- MB", id="swap-val")
            yield Static("Load: --", id="load-val")
            yield Static("Uptime: --", id="uptime-val")
        yield Static("Monitoring...", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._pause_event = threading.Event()
        self._cpu_widgets = [self.query_one(f"#cpu{i}", Static) for i in range(8)]
        self._temp_val = self.query_one("#temp-val", Static)
        self._throttle_val = self.query_one("#throttle-val", Static)
        self._gov_val = self.query_one("#gov-val", Static)
        self._mem_val = self.query_one("#mem-val", Static)
        self._swap_val = self.query_one("#swap-val", Static)
        self._load_val = self.query_one("#load-val", Static)
        self._uptime_val = self.query_one("#uptime-val", Static)
        self._status_bar = self.query_one("#status-bar", Static)
        self._start_monitor()

    @work(thread=True, interval=2)
    def _start_monitor(self):
        if self._pause_event.is_set():
            return
        self._update_once()

    def _update_once(self):
        temp = get_temp()
        freqs = get_cpu_freqs()
        gov = get_governor()
        thr = get_throttled()
        mem = self._read_mem()
        try:
            load = os.getloadavg()
            load_str = f"{load[0]:.1f} {load[1]:.1f} {load[2]:.1f}"
        except Exception:
            load_str = "n/a"
        try:
            with open("/proc/uptime") as f:
                secs = int(float(f.read().split()[0]))
                d, r = divmod(secs, 86400)
                h, m = divmod(r, 3600)
                m //= 60
                parts = []
                if d: parts.append(f"{d}d")
                if h: parts.append(f"{h}h")
                parts.append(f"{m}m")
                up = " ".join(parts)
        except Exception:
            up = "n/a"

        self.call_from_thread(self._update_ui, temp, freqs, gov, thr, mem, load_str, up)

    def _read_mem(self):
        try:
            with open("/proc/meminfo") as f:
                raw = f.read()
            m = {}
            for line in raw.split("\n"):
                parts = line.split(":")
                if len(parts) == 2:
                    m[parts[0].strip()] = int(parts[1].strip().split()[0])
            return {
                "total": m.get("MemTotal", 0) // 1024,
                "used": (m.get("MemTotal", 0) - m.get("MemAvailable", 0)) // 1024,
                "avail": m.get("MemAvailable", 0) // 1024,
                "swap_total": m.get("SwapTotal", 0) // 1024,
                "swap_used": (m.get("SwapTotal", 0) - m.get("SwapFree", 0)) // 1024,
            }
        except Exception:
            return {"total": 0, "used": 0, "avail": 0, "swap_total": 0, "swap_used": 0}

    def _update_ui(self, temp, freqs, gov, thr, mem, load_str, up):
        for i in range(8):
            f = freqs.get(i, 0)
            color = "green" if f > 1400 else ("yellow" if f > 600 else "dim")
            self._cpu_widgets[i].update(f"CPU{i}: [{color}]{f} MHz[/]")

        tc = "red" if temp >= 75 else ("yellow" if temp >= 65 else "green")
        self._temp_val.update(f"Temp: [{tc}]{temp:.1f}°C[/]")

        flags = get_throttle_flags(thr)
        if flags:
            parts = []
            for f in flags:
                c = THROTTLE_COLORS.get(f, "red")
                parts.append(f"[{c}]{f}[/]")
            self._throttle_val.update(f"Throttle: {' '.join(parts)}")
        else:
            self._throttle_val.update("Throttle: [green]OK[/]")

        gc = "green" if gov == "performance" else ("yellow" if gov == "ondemand" else "dim")
        self._gov_val.update(f"Governor: [{gc}]{gov}[/] (P=perf O=ondemand S=save)")

        pct = (mem["used"] / max(mem["total"], 1)) * 100
        mc = "red" if pct > 85 else ("yellow" if pct > 70 else "green")
        self._mem_val.update(f"Mem: [{mc}]{mem['used']}[/]/{mem['total']} MB")
        sp = (mem["swap_used"] / max(mem["swap_total"], 1)) * 100
        sc = "red" if sp > 50 else "green"
        self._swap_val.update(f"Swap: [{sc}]{mem['swap_used']}[/]/{mem['swap_total']} MB")
        self._load_val.update(f"Load: {load_str}")
        self._uptime_val.update(f"Up: {up}")

    def action_set_gov(self, gov):
        set_governor(gov)
        self._gov_val.update(f"Governor: {gov} (set)")
        self._status_bar.update(f"Governor set to {gov}")

    def action_toggle_pause(self):
        if self._pause_event.is_set():
            self._pause_event.clear()
            self._status_bar.update("Monitoring...")
        else:
            self._pause_event.set()
            self._status_bar.update("[yellow]Paused[/yellow]")


if __name__ == "__main__":
    app = PerfApp()
    app.run()
