from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import tempfile
import threading
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, RichLog, Button, Select, Label
from textual import work

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage-bench.db")


def init_db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS bench_results(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, device TEXT, label TEXT,
            seq_read REAL, seq_write REAL,
            rnd4k_read REAL, rnd4k_write REAL,
            read_latency_ms REAL, write_latency_ms REAL)""")
    cx.commit()
    cx.close()


def detect_devices():
    devices = []
    try:
        r = subprocess.run(["lsblk", "-dno", "NAME,TRAN,ROTA,SIZE,MODEL"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split("\n"):
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            tran = parts[1] if len(parts) > 1 else ""
            rota = parts[2] if len(parts) > 2 else ""
            size = parts[3] if len(parts) > 3 else ""
            model = " ".join(parts[4:]) if len(parts) > 4 else ""
            if tran in ("sdcard", "mmc"):
                label = f"SD Card ({name}: {size})"
            elif tran == "nvme":
                label = f"NVMe ({name}: {size} {model})"
            elif tran == "usb":
                label = f"USB ({name}: {size} {model})"
            elif rota == "1":
                label = f"HDD ({name}: {size})"
            elif rota == "0" and tran:
                label = f"SSD ({name}: {size} {model})"
            else:
                label = f"{name} ({tran or '?'})"
            dev_path = f"/dev/{name}"
            if os.path.exists(dev_path) and "loop" not in name:
                devices.append((label, dev_path))
    except Exception:
        pass
    # Always add zram if available
    try:
        r = subprocess.run(["swapon", "--show", "--noheadings"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split("\n"):
            if "zram" in line:
                dev = line.split()[0]
                size = line.split()[2] if len(line.split()) > 2 else ""
                devices.append((f"zram swap ({dev}: {size})", dev))
    except Exception:
        pass
    return devices


def bench_dd(dev_path, is_char=False):
    """Quick sequential read/write test using dd."""
    t = tempfile.NamedTemporaryFile(prefix="cyberdeck-bench-", delete=False)
    test_file = t.name
    t.close()
    results = {"seq_read": 0, "seq_write": 0}

    try:
        r = subprocess.run(
            ["dd", f"if={dev_path}", f"of={test_file}", "bs=1M", "count=100",
             "iflag=direct" if not is_char else "",
             "oflag=direct" if not is_char else "",
             "2>&1"],
            capture_output=True, text=True, timeout=30)
        for line in r.stderr.split("\n"):
            if "MB/s" in line or "GB/s" in line:
                m = re.search(r'([\d.]+)\s*(MB|GB)/s', line)
                if m:
                    v = float(m.group(1))
                    if m.group(2) == "GB":
                        v *= 1000
                    results["seq_read"] = v
    except Exception:
        pass

    try:
        with open(test_file, "wb") as f:
            f.write(os.urandom(1024 * 1024 * 100))
        r = subprocess.run(
            ["dd", f"if={test_file}", f"of={dev_path}", "bs=1M", "count=100",
             "oflag=direct" if not is_char else "", "2>&1"],
            capture_output=True, text=True, timeout=30)
        for line in r.stderr.split("\n"):
            if "MB/s" in line or "GB/s" in line:
                m = re.search(r'([\d.]+)\s*(MB|GB)/s', line)
                if m:
                    v = float(m.group(1))
                    if m.group(2) == "GB":
                        v *= 1000
                    results["seq_write"] = v
    except Exception:
        pass

    try:
        os.remove(test_file)
    except Exception:
        pass

    return results


def bench_all(device_path, label):
    results = {"device": device_path, "label": label,
               "seq_read": 0, "seq_write": 0,
               "rnd4k_read": 0, "rnd4k_write": 0,
               "read_latency_ms": 0, "write_latency_ms": 0}

    is_char = device_path.startswith("/dev/zram") or "zram" in device_path

    # Sequential via dd
    dd = bench_dd(device_path, is_char)
    results["seq_read"] = dd["seq_read"]
    results["seq_write"] = dd["seq_write"]

    # Try fio for more detailed results
    t = tempfile.NamedTemporaryFile(prefix="cyberdeck-fio-", suffix=".dat", delete=False)
    test_file = t.name
    t.close()
    try:
        for rw, key in [("read", "rnd4k_read"), ("write", "rnd4k_write")]:
            r = subprocess.run(
                ["fio", "--name=test", f"--filename={test_file}",
                 "--size=64M", f"--rw=rand{to_short(rw)}",
                 "--bs=4k", "--direct=1", "--ioengine=libaio",
                 "--iodepth=16", "--runtime=10", "--time_based",
                 "--output-format=json"],
                capture_output=True, text=True, timeout=20)
            try:
                data = json.loads(r.stdout)
                if "jobs" in data and data["jobs"]:
                    job = data["jobs"][0][rw]
                    results[key] = job.get("iops", 0) * 4 / 1024  # Convert IOPS to MB/s
                    results[f"{rw}_latency_ms"] = job.get("lat_ns", {}).get("mean", 0) / 1e6
            except Exception:
                pass
    except Exception:
        pass

    try:
        os.remove(test_file)
    except Exception:
        pass

    return results


def to_short(s):
    return {"read": "read", "write": "write", "rw": "rw"}.get(s, s)


def save_result(r):
    cx = sqlite3.connect(DB_PATH)
    cx.execute(
        "INSERT INTO bench_results(date, device, label, seq_read, seq_write, "
        "rnd4k_read, rnd4k_write, read_latency_ms, write_latency_ms) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M"), r["device"], r["label"],
         r["seq_read"], r["seq_write"],
         r["rnd4k_read"], r["rnd4k_write"],
         r.get("read_latency_ms", 0), r.get("write_latency_ms", 0)))
    cx.commit()
    cx.close()


def get_history(limit=20):
    cx = sqlite3.connect(DB_PATH)
    rows = cx.execute(
        "SELECT date, label, seq_read, seq_write, rnd4k_read, rnd4k_write "
        "FROM bench_results ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    cx.close()
    return rows


class StorageBenchApp(App):
    TITLE = "Deck-Storage-Bench"
    SUBTITLE = "storage performance benchmark"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    #control-row { height: 5; margin: 0 1; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f5", "refresh_devices", "Refresh Devices"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Storage Benchmark[/bold]  (F5=refresh devices)")
        with Horizontal(id="control-row"):
            yield Select([], prompt="Device", id="device-select")
            yield Button("Benchmark", variant="primary", id="bench-btn")
            yield Button("Benchmark All", id="bench-all-btn")
        yield DataTable(id="results-table")
        yield Static("Select a device and press Benchmark.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self._results_table = self.query_one("#results-table", DataTable)
        self._results_table.cursor_type = "row"
        self._results_table.zebra_stripes = True
        self._results_table.add_columns("Date", "Device", "Seq R", "Seq W", "4K R", "4K W")
        self._refresh_devices()
        self._load_history()

    def _refresh_devices(self):
        devs = detect_devices()
        sel = self.query_one("#device-select", Select)
        sel.set_options([(l, d) for l, d in devs]) if devs else sel.set_options([])

    def _load_history(self):
        self._results_table.clear()
        for row in get_history(20):
            self._results_table.add_row(
                row[0], row[1][:25],
                f"{row[2]:.0f}" if row[2] else "—",
                f"{row[3]:.0f}" if row[3] else "—",
                f"{row[4]:.0f}" if row[4] else "—",
                f"{row[5]:.0f}" if row[5] else "—")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        sel = self.query_one("#device-select", Select)
        if event.button.id == "bench-btn":
            dev = sel.value
            label = dict(sel.options).get(dev, dev)
            if dev:
                self._run_bench(dev, label)
        elif event.button.id == "bench-all-btn":
            self._run_all()

    def action_refresh_devices(self):
        self._refresh_devices()
        self.query_one("#status-bar", Static).update("Devices refreshed.")

    @work(thread=True)
    def _run_bench(self, dev, label):
        status = self.query_one("#status-bar", Static)
        self.call_from_thread(status.update, f"Benchmarking {label}...")
        results = bench_all(dev, label)
        save_result(results)
        self.call_from_thread(self._load_history)

        sr = results.get("seq_read", 0)
        sw = results.get("seq_write", 0)
        r4k = results.get("rnd4k_read", 0)
        rec = ""
        if "NVMe" in label and sr > 300:
            rec = "[green] Excellent — use this for AI models[/green]"
        elif "SD" in label and sr < 30:
            rec = "[yellow] Slow SD — consider NVMe for AI workloads[/yellow]"
        elif "zram" in label:
            rec = "[cyan] zram is compressed RAM — fast but eats RAM[/cyan]"

        self.call_from_thread(
            status.update,
            f"Seq R: {sr:.0f} MB/s | Seq W: {sw:.0f} MB/s | 4K R: {r4k:.0f} MB/s {rec}")

    @work(thread=True)
    def _run_all(self):
        status = self.query_one("#status-bar", Static)
        devs = detect_devices()
        for label, dev in devs:
            self.call_from_thread(status.update, f"Benchmarking {label}...")
            try:
                results = bench_all(dev, label)
                save_result(results)
                self.call_from_thread(self._load_history)
            except Exception as e:
                self.call_from_thread(status.update, f"[red]Error on {label}: {e}[/red]")
        self.call_from_thread(status.update, "All benchmarks complete.")


if __name__ == "__main__":
    app = StorageBenchApp()
    app.run()
