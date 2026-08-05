#!/usr/bin/env python3
"""deck-sensors — live Pi HAT / SoC sensor monitor.

Reads the SoC temperature and memory via deck-lib/pi_sensors, plus any I2C
environment sensors that are present (BME280 / SHT31 style, best-effort). Logs
readings to a local SQLite history. Degrades gracefully off-Pi: missing sensors
just read "n/a".

    ./run.sh            live TUI
    ./run.sh --once     print one reading (CLI) and exit
    ./run.sh --log DB   append readings to a SQLite file while running
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deck-lib"))

try:
    import pi_sensors
except Exception:  # pragma: no cover
    pi_sensors = None


def read_i2c_env() -> dict:
    """Best-effort read of a temp/humidity/pressure I2C sensor. n/a if absent."""
    out = {"humidity": None, "pressure": None, "ext_temp": None}
    try:
        import board  # type: ignore
        import adafruit_bme280.basic as bme280  # type: ignore
        i2c = board.I2C()
        s = bme280.Adafruit_BME280_I2C(i2c)
        out["ext_temp"] = round(s.temperature, 1)
        out["humidity"] = round(s.relative_humidity, 1)
        out["pressure"] = round(s.pressure, 1)
    except Exception:
        pass
    return out


def read_all() -> dict:
    temp = pi_sensors.get_cpu_temp() if pi_sensors else 0.0
    mem = pi_sensors.get_memory() if pi_sensors else {}
    up = pi_sensors.get_uptime() if pi_sensors else "n/a"
    env = read_i2c_env()
    return {
        "ts": time.time(),
        "cpu_temp": temp,
        "mem_used": mem.get("mem_used"),
        "mem_total": mem.get("mem_total"),
        "uptime": up,
        **env,
    }


def _fmt(v, unit=""):
    return f"{v}{unit}" if v is not None else "n/a"


def log_row(db: str, r: dict):
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE IF NOT EXISTS readings
        (ts REAL, cpu_temp REAL, ext_temp REAL, humidity REAL, pressure REAL,
         mem_used INTEGER, mem_total INTEGER)""")
    con.execute("INSERT INTO readings VALUES (?,?,?,?,?,?,?)",
                (r["ts"], r["cpu_temp"], r["ext_temp"], r["humidity"],
                 r["pressure"], r["mem_used"], r["mem_total"]))
    con.commit(); con.close()


def cli_once():
    r = read_all()
    print(f"CPU temp : {_fmt(round(r['cpu_temp'],1),'°C')}")
    print(f"Ext temp : {_fmt(r['ext_temp'],'°C')}")
    print(f"Humidity : {_fmt(r['humidity'],'%')}")
    print(f"Pressure : {_fmt(r['pressure'],' hPa')}")
    print(f"Memory   : {_fmt(r['mem_used'],'M')} / {_fmt(r['mem_total'],'M')}")
    print(f"Uptime   : {r['uptime']}")


def run_tui(db: str | None):
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Grid
        from textual.widgets import Header, Footer, Static
        from textual import work
    except Exception as e:
        print(f"Textual unavailable ({e}); one-shot reading:\n")
        cli_once(); return
    try:
        from deck_theme import apply_theme, DECK_CSS, styled
    except Exception:
        def apply_theme(_): pass
        def styled(_n, t): return t
        DECK_CSS = ""

    class Card(Static):
        pass

    class Sensors(App):
        TITLE = "deck-sensors"
        SUB_TITLE = "environment & SoC"
        CSS = DECK_CSS + """
        Grid { grid-size: 2 3; grid-gutter: 1; padding: 1; }
        Card { border: round $primary; background: $surface; padding: 1; height: 5; }
        .big { color: $secondary; text-style: bold; }
        """
        BINDINGS = [Binding("q", "quit", "Quit"), Binding("r", "refresh", "Refresh")]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Grid():
                for cid in ("cpu", "ext", "hum", "press", "mem", "up"):
                    yield Card(id=cid)
            yield Footer()

        def on_mount(self):
            apply_theme(self)
            self._tick()
            self.set_interval(2, self._tick)

        @work(thread=True, exclusive=True)
        def _tick(self):
            r = read_all()
            if db:
                try: log_row(db, r)
                except Exception: pass
            self.call_from_thread(self._apply, r)

        def action_refresh(self):
            self._tick()

        def _apply(self, r):
            self.query_one("#cpu", Card).update(f"CPU Temp\n" + styled("big", f"{_fmt(round(r['cpu_temp'],1),'°C')}"))
            self.query_one("#ext", Card).update(f"Ext Temp\n" + styled("big", f"{_fmt(r['ext_temp'],'°C')}"))
            self.query_one("#hum", Card).update(f"Humidity\n" + styled("big", f"{_fmt(r['humidity'],'%')}"))
            self.query_one("#press", Card).update(f"Pressure\n" + styled("big", f"{_fmt(r['pressure'],' hPa')}"))
            self.query_one("#mem", Card).update(f"Memory\n" + styled("big", f"{_fmt(r['mem_used'],'M')}/{_fmt(r['mem_total'],'M')}"))
            self.query_one("#up", Card).update(f"Uptime\n" + styled("big", f"{r['uptime']}"))

    Sensors().run()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="deck-sensors")
    ap.add_argument("--once", action="store_true", help="print one reading and exit")
    ap.add_argument("--log", metavar="DB", help="append readings to a SQLite file")
    a = ap.parse_args()
    if a.once:
        cli_once()
    else:
        run_tui(a.log)
