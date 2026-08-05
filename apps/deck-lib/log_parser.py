"""Regex log parser — turn deck/Pi log lines into structured events.

Stdlib only, no deps, so it runs anywhere on the deck. Handles the formats you
actually hit on a Pi: journald/syslog, kernel dmesg, Python `logging`, nginx
access logs, bare ISO-timestamped app logs, and deck-serial's UART captures.

Use as a library::

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "deck-lib"))
    from log_parser import parse, summarize, LEVELS

    events = list(parse(open("/var/log/syslog")))
    errs = [e for e in events if e.level in ("ERROR", "CRITICAL")]
    print(summarize(events).top_sources(5))

or from the shell::

    python log_parser.py /var/log/syslog --level WARNING --stats
    python log_parser.py app.log --grep 'timeout|refused' --json
    journalctl -b | python log_parser.py -            # '-' reads stdin

Parsing is best-effort by design: an unrecognised line still becomes an event
(``fmt="raw"``) rather than being dropped, because on a field deck a line you
can't classify is usually the one you needed to see.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

# Severity ordering, low → high. Used by --level (which filters at or above).
LEVELS = ["DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL"]
_LEVEL_RANK = {name: i for i, name in enumerate(LEVELS)}

# Aliases seen in the wild, mapped onto the canonical names above.
_LEVEL_ALIASES = {
    "TRACE": "DEBUG", "DBG": "DEBUG", "FINE": "DEBUG",
    "INFORMATION": "INFO", "INF": "INFO", "I": "INFO",
    "WARN": "WARNING", "WRN": "WARNING", "W": "WARNING",
    "ERR": "ERROR", "ERRO": "ERROR", "E": "ERROR", "FAIL": "ERROR",
    "FATAL": "CRITICAL", "CRIT": "CRITICAL", "EMERG": "CRITICAL",
    "ALERT": "CRITICAL", "PANIC": "CRITICAL",
}

# --- patterns --------------------------------------------------------------
# Ordered most-specific first: the first full-line match wins, so a syslog line
# is never mistaken for the looser "generic" shape. Every pattern uses the same
# named groups (ts / level / source / pid / msg); missing ones are just absent.

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # kernel ring buffer: "[   12.345678] usb 1-1: new high-speed USB device"
    ("dmesg", re.compile(
        r"^\[\s*(?P<uptime>\d+\.\d+)\]\s+"
        r"(?:(?P<source>[\w.\-]+)(?:\s+[\w:\-.]+)?:\s+)?"
        r"(?P<msg>.*)$")),

    # syslog / journald short: "Aug  1 03:14:15 deck sshd[1234]: Accepted ..."
    ("syslog", re.compile(
        r"^(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<host>\S+)\s+"
        r"(?P<source>[\w./\-]+?)(?:\[(?P<pid>\d+)\])?:\s+"
        r"(?P<msg>.*)$")),

    # nginx/apache combined: '1.2.3.4 - - [01/Aug/2026:03:14:15 +0000] "GET /x HTTP/1.1" 404 153'
    ("access", re.compile(
        r"^(?P<client>\d{1,3}(?:\.\d{1,3}){3}|[0-9a-fA-F:]+)\s+\S+\s+\S+\s+"
        r"\[(?P<ts>[^\]]+)\]\s+"
        r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)[^"]*"\s+'
        r"(?P<status>\d{3})\s+(?P<size>\d+|-)"
        r"(?P<msg>.*)$")),

    # Python logging default-ish: "2026-08-01 03:14:15,123 - deck.net - ERROR - boom"
    ("python", re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s*[-|]\s*"
        r"(?P<source>[\w.\-]+)\s*[-|]\s*"
        r"(?P<level>[A-Z]+)\s*[-|]\s*"
        r"(?P<msg>.*)$")),

    # ISO timestamp + bracketed or bare level: "2026-08-01T03:14:15Z [WARN] disk 91%"
    ("iso", re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+\-]\d{2}:?\d{2})?)\s+"
        r"\[?(?P<level>[A-Z]{1,11})\]?\s*"
        r"(?:\[(?P<source>[\w.\-]+)\]\s*)?[:\-]?\s*"
        r"(?P<msg>.*)$")),

    # deck-serial UART capture: "[03:14:15.123] <ttyUSB0> boot: ok"
    ("serial", re.compile(
        r"^\[(?P<ts>\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]\s*"
        r"(?:<(?P<source>[\w/\-]+)>\s*)?"
        r"(?P<msg>.*)$")),

    # last resort: a level word anywhere near the start
    ("generic", re.compile(
        r"^(?P<level>DEBUG|TRACE|INFO|NOTICE|WARN(?:ING)?|ERR(?:OR)?|CRIT(?:ICAL)?|FATAL)\b[:\s\-]*"
        r"(?P<msg>.*)$", re.IGNORECASE)),
]

# Continuation lines (tracebacks, indented detail) belong to the event above.
_CONTINUATION = re.compile(r"^(?:\s+|Traceback |\.\.\.|\t)")
_TRACEBACK_START = re.compile(r"^\s*Traceback \(most recent call last\)")
# A traceback's final line is NOT indented: "ValueError: bad value". Without
# this it would break out and become its own bogus event.
_EXC_TAIL = re.compile(r"^(?:[A-Za-z_][\w.]*)?(?:Error|Exception|Interrupt|Exit|Warning)"
                       r"(?::|$)|^[A-Za-z_][\w.]*Error\b")

# Levels can also hide inside the message of an otherwise level-less format.
# Uppercase-only on purpose — matching case-insensitively would tag any message
# containing the word "info" or "error" in prose.
_INLINE_LEVEL = re.compile(
    r"\b(DEBUG|TRACE|INFO|NOTICE|WARN(?:ING)?|ERR(?:OR)?|CRIT(?:ICAL)?|FATAL|PANIC)\b")

# Formats like syslog carry no level field, and the interesting lines say
# "Failed to start X" rather than "ERROR". A small, deliberately conservative
# set of failure words promotes those to ERROR so they survive `--level ERROR`.
_FAILURE_HINT = re.compile(
    r"\b(fail(?:ed|ure|s)?|fatal|panic|segfault|refused|denied|"
    r"oom-killer|out of memory|cannot open|unable to)\b", re.IGNORECASE)

# (strptime format, how much of the date it actually carries). syslog omits the
# year and deck-serial logs time only; strptime fills the gaps with 1900-01-01,
# which would wreck any sort or timespan, so those get today's date folded in.
_FULL, _NO_YEAR, _TIME_ONLY = "full", "no_year", "time_only"
_TS_FORMATS = [
    ("%Y-%m-%d %H:%M:%S.%f", _FULL),
    ("%Y-%m-%d %H:%M:%S", _FULL),
    ("%Y-%m-%dT%H:%M:%S.%f", _FULL),
    ("%Y-%m-%dT%H:%M:%S", _FULL),
    ("%d/%b/%Y:%H:%M:%S %z", _FULL),
    ("%b %d %H:%M:%S", _NO_YEAR),
    ("%H:%M:%S.%f", _TIME_ONLY),
    ("%H:%M:%S", _TIME_ONLY),
]


def normalize_level(raw: str | None) -> str:
    """Map any spelling of a severity onto a canonical LEVELS name."""
    if not raw:
        return "INFO"
    key = raw.strip().upper()
    if key in _LEVEL_RANK:
        return key
    return _LEVEL_ALIASES.get(key, "INFO")


def parse_timestamp(raw: str | None, now: datetime | None = None) -> datetime | None:
    """Best-effort timestamp parse. Returns None rather than raising.

    Always returns a *naive* datetime (offsets are converted to UTC and the
    tzinfo dropped). A single log can mix offset-aware formats like nginx's
    ``+0000`` with naive ones like syslog's, and comparing the two raises —
    which would blow up sorting and ``summarize()`` on real-world input.

    Year-less and time-only stamps are dated against ``now`` (default: today),
    since strptime would otherwise place them in 1900. Pass ``now`` to keep this
    deterministic in tests, and note the caveat: a log spanning New Year, or one
    read months later, will be dated wrong — the line itself carries no year.
    """
    if not raw:
        return None
    text = raw.strip().replace(",", ".")
    if text.endswith("Z"):
        text = text[:-1]
    today = (now or datetime.now()).date()
    for fmt, kind in _TS_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        if kind == _NO_YEAR:
            dt = dt.replace(year=today.year)
        elif kind == _TIME_ONLY:
            dt = dt.replace(year=today.year, month=today.month, day=today.day)
        return dt
    return None


@dataclass
class LogEvent:
    raw: str
    msg: str
    fmt: str = "raw"                 # which pattern matched
    level: str = "INFO"
    source: str = ""                 # unit / logger / device
    ts: datetime | None = None
    lineno: int = 0
    fields: dict = field(default_factory=dict)   # format-specific extras

    @property
    def rank(self) -> int:
        return _LEVEL_RANK.get(self.level, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = self.ts.isoformat() if self.ts else None
        return d

    def __str__(self) -> str:
        stamp = self.ts.isoformat(sep=" ") if self.ts else "-"
        src = f" {self.source}" if self.source else ""
        return f"{stamp} {self.level:8}{src}: {self.msg}"


def parse_line(line: str, lineno: int = 0) -> LogEvent:
    """Parse one line. Never returns None — unmatched lines come back raw."""
    text = line.rstrip("\n")
    stripped = text.strip()
    if not stripped:
        return LogEvent(raw=text, msg="", fmt="blank", lineno=lineno)

    for name, pattern in _PATTERNS:
        m = pattern.match(stripped)
        if not m:
            continue
        g = m.groupdict()
        msg = (g.get("msg") or "").strip()

        # Formats with no level field: sniff one out of the message text.
        level = g.get("level")
        if not level:
            inline = _INLINE_LEVEL.search(msg[:60])
            if inline:
                level = inline.group(1)
            elif _FAILURE_HINT.search(msg):
                level = "ERROR"

        extras = {k: v for k, v in g.items()
                  if k not in ("ts", "level", "source", "msg") and v is not None}

        # An access-log line's severity is really its status code.
        if name == "access":
            status = int(g.get("status") or 0)
            level = "ERROR" if status >= 500 else "WARNING" if status >= 400 else "INFO"
            msg = f'{g.get("method")} {g.get("path")} -> {status}'

        return LogEvent(
            raw=text, msg=msg, fmt=name,
            level=normalize_level(level),
            source=(g.get("source") or "").strip(),
            ts=parse_timestamp(g.get("ts")),
            lineno=lineno, fields=extras,
        )

    return LogEvent(raw=text, msg=stripped, fmt="raw", lineno=lineno)


def parse(lines, merge_continuations: bool = True):
    """Parse an iterable of lines into LogEvents.

    Indented lines and tracebacks are folded into the preceding event, so a
    Python stack trace stays one ERROR instead of exploding into 30 events.
    """
    current: LogEvent | None = None
    in_traceback = False

    def fold(ev: LogEvent, text: str):
        ev.raw += "\n" + text
        ev.msg += " | " + text.strip()

    for i, line in enumerate(lines, 1):
        text = line.rstrip("\n")
        if merge_continuations and current is not None and text.strip():
            if _CONTINUATION.match(text):
                fold(current, text)
                if _TRACEBACK_START.match(text):
                    in_traceback = True
                continue
            # Unindented exception line closing a traceback — still part of it.
            if in_traceback and _EXC_TAIL.match(text.strip()):
                fold(current, text)
                in_traceback = False
                continue
        in_traceback = False
        ev = parse_line(line, i)
        if ev.fmt == "blank":
            continue
        if current is not None:
            yield current
        current = ev
    if current is not None:
        yield current


# --- summarising -----------------------------------------------------------

@dataclass
class Summary:
    total: int = 0
    levels: Counter = field(default_factory=Counter)
    sources: Counter = field(default_factory=Counter)
    formats: Counter = field(default_factory=Counter)
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    patterns: Counter = field(default_factory=Counter)

    def top_sources(self, n: int = 5) -> list[tuple[str, int]]:
        return self.sources.most_common(n)

    def top_messages(self, n: int = 5) -> list[tuple[str, int]]:
        return self.patterns.most_common(n)

    @property
    def problem_count(self) -> int:
        return sum(c for lvl, c in self.levels.items()
                   if _LEVEL_RANK.get(lvl, 0) >= _LEVEL_RANK["WARNING"])


# Numbers/hex/paths differ per occurrence but the *shape* is what repeats;
# blanking them turns 400 unique lines into "disk <N>% full" x400.
_NOISE = [
    (re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b"), "<mac>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<hex>"),
    (re.compile(r"/[\w./\-]{4,}"), "<path>"),
    (re.compile(r"\b\d+\b"), "<n>"),
]


def fingerprint(msg: str) -> str:
    """Collapse a message to its shape so recurring events group together."""
    out = msg
    for pattern, repl in _NOISE:
        out = pattern.sub(repl, out)
    return out[:120]


def summarize(events) -> Summary:
    s = Summary()
    for e in events:
        s.total += 1
        s.levels[e.level] += 1
        s.formats[e.fmt] += 1
        if e.source:
            s.sources[e.source] += 1
        if e.msg:
            s.patterns[fingerprint(e.msg)] += 1
        if e.ts:
            if s.first_ts is None or e.ts < s.first_ts:
                s.first_ts = e.ts
            if s.last_ts is None or e.ts > s.last_ts:
                s.last_ts = e.ts
    return s


# --- CLI -------------------------------------------------------------------

def _open(path: str):
    if path == "-":
        return sys.stdin
    return open(path, encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="log_parser",
        description="Parse and filter log files with regex (stdlib only).")
    p.add_argument("files", nargs="*", default=["-"],
                   help="log files, or '-' for stdin (default)")
    p.add_argument("--level", choices=LEVELS,
                   help="only show this severity and above")
    p.add_argument("--source", help="only this source/unit (substring)")
    p.add_argument("--grep", help="regex the message must match")
    p.add_argument("--fmt", help="only lines parsed as this format "
                                 "(syslog, dmesg, python, iso, access, serial, raw)")
    p.add_argument("--json", action="store_true", help="emit JSON lines")
    p.add_argument("--stats", action="store_true", help="print a summary instead of lines")
    p.add_argument("--no-merge", action="store_true",
                   help="keep traceback/indented lines as separate events")
    args = p.parse_args(argv)

    grep = re.compile(args.grep, re.IGNORECASE) if args.grep else None
    floor = _LEVEL_RANK[args.level] if args.level else -1

    selected = []
    for path in (args.files or ["-"]):
        try:
            handle = _open(path)
        except OSError as e:
            print(f"log_parser: {e}", file=sys.stderr)
            return 1
        with handle if path != "-" else _NullCtx(handle):
            for ev in parse(handle, merge_continuations=not args.no_merge):
                if ev.rank < floor:
                    continue
                if args.source and args.source.lower() not in ev.source.lower():
                    continue
                if args.fmt and ev.fmt != args.fmt:
                    continue
                if grep and not grep.search(ev.msg):
                    continue
                selected.append(ev)

    if args.stats:
        s = summarize(selected)
        span = "-"
        if s.first_ts and s.last_ts:
            span = f"{s.first_ts.isoformat(sep=' ')} .. {s.last_ts.isoformat(sep=' ')}"
        print(f"events   : {s.total}   ({s.problem_count} at WARNING+)")
        print(f"timespan : {span}")
        print("levels   : " + ", ".join(f"{k}={v}" for k, v in
                                        sorted(s.levels.items(),
                                               key=lambda kv: -_LEVEL_RANK.get(kv[0], 0))))
        print("formats  : " + ", ".join(f"{k}={v}" for k, v in s.formats.most_common()))
        if s.sources:
            print("top sources:")
            for name, n in s.top_sources(5):
                print(f"  {n:6}  {name}")
        if s.patterns:
            print("recurring messages:")
            for shape, n in s.top_messages(5):
                print(f"  {n:6}  {shape}")
        return 0

    for ev in selected:
        print(json.dumps(ev.to_dict(), default=str) if args.json else str(ev))
    return 0


class _NullCtx:
    """Wrap stdin so the `with` above doesn't close it."""
    def __init__(self, obj): self.obj = obj
    def __enter__(self): return self.obj
    def __exit__(self, *a): return False


if __name__ == "__main__":
    sys.exit(main())
