from __future__ import annotations

import os
import subprocess


def sys_read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return ""


def get_cpu_temp() -> float:
    try:
        r = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=2)
        return float(r.stdout.split("=")[1].split("'")[0])
    except Exception:
        pass
    raw = sys_read("/sys/class/thermal/thermal_zone0/temp")
    if raw:
        try:
            return float(raw) / 1000
        except ValueError:
            pass
    return 0.0


def get_memory() -> dict:
    d = {"mem_total": 0, "mem_used": 0, "mem_avail": 0, "swap_total": 0, "swap_used": 0}
    raw = sys_read("/proc/meminfo")
    if not raw:
        return d
    m = {}
    for line in raw.split("\n"):
        parts = line.split(":")
        if len(parts) == 2:
            m[parts[0].strip()] = int(parts[1].strip().split()[0])
    d["mem_total"] = m.get("MemTotal", 0) // 1024
    d["mem_avail"] = m.get("MemAvailable", 0) // 1024
    d["mem_used"] = d["mem_total"] - d["mem_avail"]
    d["swap_total"] = m.get("SwapTotal", 0) // 1024
    d["swap_used"] = (m.get("SwapTotal", 0) - m.get("SwapFree", 0)) // 1024
    return d


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
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        parts.append(f"{m}m")
        return " ".join(parts)
    except Exception:
        return "n/a"
