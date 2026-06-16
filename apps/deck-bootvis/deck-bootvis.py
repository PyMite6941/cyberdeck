from __future__ import annotations

import os
import sqlite3
import subprocess
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, RichLog, Button, TabbedContent, TabPane
from textual import work

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bootvis.db")


def init_db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS boots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, total_kernel REAL, total_initrd REAL,
            total_userspace REAL, total REAL)""")
    cx.execute("""
        CREATE TABLE IF NOT EXISTS services(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boot_id INTEGER, name TEXT, time REAL,
            FOREIGN KEY(boot_id) REFERENCES boots(id))""")
    cx.commit()
    cx.close()


def get_systemd_analyze():
    try:
        r = subprocess.run(["systemd-analyze"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return None


def get_blame():
    try:
        r = subprocess.run(["systemd-analyze", "blame"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().split("\n")
    except Exception:
        return []


def get_critical_chain():
    try:
        r = subprocess.run(["systemd-analyze", "critical-chain"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().split("\n")
    except Exception:
        return []


def parse_blame(lines):
    services = []
    for line in lines:
        line = line.strip()
        if not line or " ms" not in line and "min" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                t = parts[0]
                if "min" in t:
                    m, s = t.split("min")
                    t_sec = float(m.strip()) * 60 + float(s.replace("s", "").strip())
                else:
                    t_sec = float(t.replace("ms", "").strip()) / 1000
                name = parts[1]
                services.append((name, t_sec))
            except Exception:
                continue
    return services


def save_boot_record(services, total, kernel, initrd, userspace):
    cx = sqlite3.connect(DB_PATH)
    cx.execute(
        "INSERT INTO boots(date, total_kernel, total_initrd, total_userspace, total) "
        "VALUES(?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M"), kernel, initrd, userspace, total))
    bid = cx.lastrowid
    for name, t in services:
        cx.execute("INSERT INTO services(boot_id, name, time) VALUES(?,?,?)", (bid, name, t))
    cx.commit()
    cx.close()
    return bid


def get_history(limit=10):
    cx = sqlite3.connect(DB_PATH)
    rows = cx.execute(
        "SELECT id, date, total, total_kernel, total_userspace "
        "FROM boots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    cx.close()
    return rows


def get_service_avgs():
    cx = sqlite3.connect(DB_PATH)
    rows = cx.execute(
        "SELECT name, AVG(time), COUNT(*) FROM services "
        "GROUP BY name ORDER BY AVG(time) DESC LIMIT 20").fetchall()
    cx.close()
    return rows


class BootvisApp(App):
    TITLE = "Deck-BootVis"
    SUBTITLE = "boot time profiler"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f5", "refresh", "Measure Boot"),
        Binding("h", "toggle_history", "History"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]BootVis — Boot Time Profiler[/bold]  (F5=measure  H=history)")
        with Horizontal(id="toolbar"):
            yield Button("Measure Boot", variant="primary", id="measure-btn")
            yield Button("History", id="history-btn")
            yield Button("Suggestions", id="suggest-btn")
        yield TabbedContent(
            TabPane("Services (by time)", DataTable(id="blame-table")),
            TabPane("History", DataTable(id="history-table")),
            TabPane("Suggestions", RichLog(id="suggest-log", highlight=True, markup=True)),
        )
        yield Static("Boot time: --", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._blame_table = self.query_one("#blame-table", DataTable)
        self._history_table = self.query_one("#history-table", DataTable)
        self._suggest_log = self.query_one("#suggest-log", RichLog)
        self._blame_table.cursor_type = "row"
        self._blame_table.zebra_stripes = True
        self._blame_table.add_columns("Service", "Time (sec)")
        self._history_table.add_columns("Date", "Total", "Kernel", "Userspace")
        self._show_saved()

    def _show_saved(self):
        rows = get_service_avgs()
        self._blame_table.clear()
        for name, avg, cnt in rows:
            color = "red" if avg > 2 else ("yellow" if avg > 0.5 else "green")
            self._blame_table.add_row(f"[{color}]{name}[/]", f"{avg:.3f}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "measure-btn":
            self._measure()
        elif event.button.id == "history-btn":
            self._show_history()
        elif event.button.id == "suggest-btn":
            self._show_suggestions()

    @work(thread=True)
    def _measure(self):
        status = self.query_one("#status-bar", Static)
        self.call_from_thread(status.update, "[yellow]Measuring boot times...[/yellow]")

        blame_lines = get_blame()
        analyze = get_systemd_analyze()
        services = parse_blame(blame_lines)

        total = 0
        kernel_t = initrd_t = userspace_t = 0
        if analyze:
            for line in analyze.split("\n"):
                line = line.strip()
                if "Kernel" in line:
                    try:
                        kernel_t = float(line.split(":")[1].strip().replace("s", ""))
                    except Exception:
                        pass
                elif "Initrd" in line:
                    try:
                        initrd_t = float(line.split(":")[1].strip().replace("s", ""))
                    except Exception:
                        pass
                elif "Userspace" in line:
                    try:
                        userspace_t = float(line.split(":")[1].strip().replace("s", ""))
                    except Exception:
                        pass
            if "=" in analyze:
                try:
                    total = float(analyze.split("=")[1].strip().split()[0].replace("s", ""))
                except Exception:
                    total = kernel_t + userspace_t
            else:
                total = kernel_t + userspace_t

        save_boot_record(services, total, kernel_t, initrd_t, userspace_t)

        self.call_from_thread(self._blame_table.clear)
        for name, t in services[:30]:
            color = "red" if t > 2 else ("yellow" if t > 0.5 else "green")
            self.call_from_thread(
                self._blame_table.add_row, f"[{color}]{name}[/]", f"{t:.3f}")

        slow = sum(1 for _, t in services if t > 2)
        self.call_from_thread(
            status.update,
            f"Total: {total:.1f}s | {len(services)} services ({slow} >2s slow)")

    def _show_history(self):
        rows = get_history(10)
        self._history_table.clear()
        for rid, date, total, kernel, userspace in rows:
            self._history_table.add_row(date, f"{total:.1f}s", f"{kernel:.1f}s", f"{userspace:.1f}s")

    def _show_suggestions(self):
        log = self._suggest_log
        log.clear()
        rows = get_service_avgs()
        log.write("[bold cyan]Boot Optimization Suggestions[/bold cyan]\n")

        if not rows:
            log.write("Run 'Measure Boot' first to collect data.")
            return

        total = 0
        for _, avg, _ in rows:
            total += avg

        log.write(f"\n[bold]Top time consumers (avg):[/bold]")
        for name, avg, cnt in rows[:10]:
            pct = (avg / max(total, 0.01)) * 100
            log.write(f"  {name}: {avg:.3f}s ({pct:.0f}%) measured {cnt}x")

        log.write(f"\n[bold yellow]Suggestions:[/bold yellow]")
        for name, avg, cnt in rows:
            if avg > 2:
                log.write(f"  [red]▶ {name}: {avg:.2f}s[/red]")
                if "NetworkManager" in name or "wpa_supplicant" in name or "dhcpcd" in name:
                    log.write(f"     [dim]Consider: sudo systemctl mask {name}[/dim]")
                    log.write(f"     [dim]  If you don't need auto-network at boot[/dim]")
                elif "cups" in name:
                    log.write(f"     [dim]Consider: sudo systemctl disable cups[/dim]")
                    log.write(f"     [dim]  Already disabled by setup-ai.sh[/dim]")
                elif "plymouth" in name:
                    log.write(f"     [dim]Consider: sudo systemctl mask plymouth-start[/dim]")
                    log.write(f"     [dim]  Removes splash screen delay[/dim]")
                elif "dev-" in name or "systemd-udev" in name:
                    log.write(f"     [dim]This is hardware probing — expected on first boot[/dim]")
                else:
                    log.write(f"     [dim]Investigate with: systemctl status {name}[/dim]")

        log.write(f"\n[bold green]Quick wins:[/bold green]")
        log.write("  • Set CPU governor: [green]P[/green] key for performance")
        log.write("  • Drop to console: [green]deck-lite[/green] (saves ~2s in display init)")
        log.write("  • Already optimized: zram replaces swapfile, boot.d scripts are async")


if __name__ == "__main__":
    app = BootvisApp()
    app.run()
