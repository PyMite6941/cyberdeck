from __future__ import annotations

import os
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, DataTable
)
from textual import work


def sys_read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return ""


def get_cpu_temp() -> str:
    t = sys_read("/sys/class/thermal/thermal_zone0/temp")
    if t:
        try:
            return f"{float(t) / 1000:.1f}'C"
        except ValueError:
            pass
    return "n/a"


def get_mem() -> dict:
    d = {"mem_used": "n/a", "mem_total": "n/a", "swap_used": "n/a", "swap_total": "n/a"}
    raw = sys_read("/proc/meminfo")
    if not raw:
        return d
    m = {}
    for line in raw.split("\n"):
        parts = line.split(":")
        if len(parts) == 2:
            m[parts[0].strip()] = parts[1].strip().split()[0]
    try:
        total = int(m.get("MemTotal", 0))
        avail = int(m.get("MemAvailable", 0))
        d["mem_total"] = f"{total // 1024}G" if total > 1024 * 1024 else f"{total // 1024}M"
        d["mem_used"] = f"{(total - avail) // 1024}G" if total > 1024 * 1024 else f"{(total - avail) // 1024}M"
    except ValueError:
        pass
    try:
        s_total = int(m.get("SwapTotal", 0))
        s_free = int(m.get("SwapFree", 0))
        d["swap_total"] = f"{s_total // 1024}M"
        d["swap_used"] = f"{(s_total - s_free) // 1024}M"
    except ValueError:
        pass
    return d


def get_disk() -> str:
    try:
        s = os.statvfs("/")
        total = s.f_frsize * s.f_blocks
        free = s.f_frsize * s.f_bfree
        used = total - free
        pct = used / total * 100 if total else 0
        def hsize(b):
            for u in ("", "K", "M", "G", "T"):
                if abs(b) < 1024:
                    return f"{b:.0f}{u}"
                b /= 1024
            return f"{b:.0f}P"
        return f"{hsize(used)} / {hsize(total)} ({pct:.0f}%)"
    except Exception:
        return "n/a"


def get_uptime() -> str:
    raw = sys_read("/proc/uptime")
    if not raw:
        return "n/a"
    try:
        secs = int(float(raw.split()[0]))
        d, r = divmod(secs, 86400)
        h, m = divmod(r, 3600)
        m //= 60
        parts = []
        if d:
            parts.append(f"{d}d")
        if h:
            parts.append(f"{h}h")
        parts.append(f"{m}m")
        return " ".join(parts)
    except Exception:
        return "n/a"


def get_load() -> str:
    raw = sys_read("/proc/loadavg")
    if raw:
        parts = raw.split()
        return f"{parts[0]} {parts[1]} {parts[2]}"
    return "n/a"


def get_network() -> str:
    for iface in ("wlan0", "eth0"):
        op = sys_read(f"/sys/class/net/{iface}/operstate")
        if op == "up":
            addr = sys_read(f"/sys/class/net/{iface}/address")
            return f"{iface} ({addr[:17]})" if addr else iface
    return "disconnected"


def get_top_processes(n: int = 5) -> list[tuple[str, str, str]]:
    results = []
    try:
        entries = []
        for pid_str in os.listdir("/proc"):
            if not pid_str.isdigit():
                continue
            try:
                pid = int(pid_str)
                stat = sys_read(f"/proc/{pid}/stat")
                if not stat:
                    continue
                fields = stat.split(")")
                if len(fields) < 2:
                    continue
                comm = fields[0].split("(")[-1] if "(" in fields[0] else "?"
                after = fields[1].split()
                if len(after) < 18:
                    continue
                utime = int(after[11])
                stime = int(after[12])
                total_ticks = utime + stime
                entries.append((total_ticks, pid, comm[:40]))
            except (ValueError, OSError):
                continue
        entries.sort(key=lambda x: -x[0])
        for _, pid, comm in entries[:n]:
            results.append((str(pid), "?", comm))
    except Exception:
        pass
    return results


class DashboardApp(App):
    TITLE = "Deck Dashboard"
    SUBTITLE = "system monitor"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("t", "toggle_dark", "Dark Mode"),
    ]
    CSS = """
    Screen { overflow: auto; }
    .stat-box {
        border: solid $primary; height: 5; margin: 1; padding: 1;
    }
    .stat-label { text-style: bold; color: $text; }
    .stat-value { text-style: bold; color: $accent; }
    DataTable { height: 10; margin: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]System Status[/bold cyan]", id="title")
            with Horizontal():
                with Vertical(id="col-left"):
                    yield Static(id="cpu-temp", classes="stat-box")
                    yield Static(id="memory", classes="stat-box")
                    yield Static(id="disk", classes="stat-box")
                with Vertical(id="col-right"):
                    yield Static(id="uptime", classes="stat-box")
                    yield Static(id="load", classes="stat-box")
                    yield Static(id="network", classes="stat-box")
            yield Static("[bold cyan]Top Processes[/bold cyan]", id="proc-title")
            yield DataTable(id="proc-table")
        yield Footer()

    def on_mount(self) -> None:
        self._cpu_temp = self.query_one("#cpu-temp", Static)
        self._memory = self.query_one("#memory", Static)
        self._disk = self.query_one("#disk", Static)
        self._uptime = self.query_one("#uptime", Static)
        self._load = self.query_one("#load", Static)
        self._network = self.query_one("#network", Static)
        self._proc_table = self.query_one("#proc-table", DataTable)
        self._proc_table.add_columns("PID", "CPU%", "Command")
        self._start_refresh()

    @work(thread=True, interval=2)
    def _start_refresh(self):
        self._update_all()

    def _update_all(self):
        temp = get_cpu_temp()
        mem = get_mem()
        disk = get_disk()
        up = get_uptime()
        load = get_load()
        net = get_network()
        procs = get_top_processes()
        self.call_from_thread(self._apply_ui, temp, mem, disk, up, load, net, procs)

    def _apply_ui(self, temp, mem, disk, up, load, net, procs):
        self._cpu_temp.update(f"[bold]CPU Temp[/bold]\n{temp}")
        self._memory.update(
            f"[bold]Memory[/bold]\n{mem['mem_used']} / {mem['mem_total']}  "
            f"Swap: {mem['swap_used']} / {mem['swap_total']}")
        self._disk.update(f"[bold]Disk[/bold]\n{disk}")
        self._uptime.update(f"[bold]Uptime[/bold]\n{up}")
        self._load.update(f"[bold]Load[/bold]\n{load}")
        self._network.update(f"[bold]Network[/bold]\n{net}")
        self._proc_table.clear()
        for pid, cpu, cmd in procs:
            self._proc_table.add_row(pid, cpu, cmd)


if __name__ == "__main__":
    app = DashboardApp()
    app.run()
