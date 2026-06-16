from __future__ import annotations

import os
import sqlite3
import time


def get_db_path(app_name: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", app_name, f"{app_name}.db")


def init_db(db_path: str, schema_sql: str) -> sqlite3.Connection:
    cx = sqlite3.connect(db_path)
    cx.execute("PRAGMA journal_mode=WAL")
    cx.executescript(schema_sql)
    cx.commit()
    return cx


def save(cx: sqlite3.Connection, sql: str, params: tuple = ()) -> None:
    cx.execute(sql, params)
    cx.commit()
    cx.close()


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")
