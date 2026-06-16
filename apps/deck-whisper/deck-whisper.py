from __future__ import annotations

import json
import os
import queue
import sqlite3
import sys
import threading
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, RichLog, Select
from textual import work

REC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripts.db")

AUDIO_QUEUE = queue.Queue()


def search_transcripts(query, limit=20):
    cx = sqlite3.connect(DB_PATH)
    rows = cx.execute(
        "SELECT id, title, duration, date FROM transcripts "
        "WHERE text LIKE ? ORDER BY date DESC LIMIT ?",
        (f"%{query}%", limit)).fetchall()
    cx.close()
    return [{"id": r[0], "title": r[1], "duration": r[2], "date": r[3]} for r in rows]


def get_transcript(tid):
    cx = sqlite3.connect(DB_PATH)
    r = cx.execute("SELECT title, text, date FROM transcripts WHERE id=?", (tid,)).fetchone()
    cx.close()
    return r


def init_db():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("""
        CREATE TABLE IF NOT EXISTS transcripts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, duration REAL, date TEXT, text TEXT)""")
    cx.commit()
    cx.close()


class RecordWorker:
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self, duration=30):
        self._running = True
        self._thread = threading.Thread(target=self._record, args=(duration,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _record(self, duration):
        import pyaudio
        import wave
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * duration)):
            if not self._running:
                break
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        timestamp = int(time.time())
        path = os.path.join(REC_DIR, f"recording_{timestamp}.wav")
        wf = wave.open(path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        AUDIO_QUEUE.put(path)


class TranscribeWorker:
    @staticmethod
    def transcribe(path):
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny-int8", device="cpu", cpu_threads=4, num_workers=1)
            segments, info = model.transcribe(path, beam_size=1)
            text = " ".join(s.text for s in segments)
            duration = info.duration if hasattr(info, 'duration') else 0
            return text, duration
        except Exception as e:
            return f"[transcription error: {e}]", 0


class DetailScreen(Screen):
    def __init__(self, tid: int, title: str):
        super().__init__()
        self.tid = tid
        self.doc_title = title

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="detail-content", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        r = get_transcript(self.tid)
        log = self.query_one("#detail-content", RichLog)
        if r:
            log.write(f"[bold cyan]{r[0]}[/bold cyan]")
            log.write(f"[dim]{r[2]}[/dim]\n")
            log.write(r[1])
        else:
            log.write("[red]Not found[/red]")


class WhisperApp(App):
    TITLE = "Deck-Whisper"
    SUBTITLE = "offline voice recorder & transcriber"
    CSS = """
    #toolbar { height: 3; margin: 1; }
    #search-row { height: 5; margin: 0 1; }
    #results-box { height: 1fr; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; }
    #status-bar { height: 3; background: $surface; padding: 0 1; }
    """
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+r", "toggle_record", "Record"),
        Binding("escape", "focus_search", "Search"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("[bold]Deck-Whisper — Offline Voice Recorder[/bold]", id="toolbar")
        with Horizontal(id="search-row"):
            yield Input(placeholder="Search transcripts...", id="search-input")
            yield Button("Search", variant="primary", id="search-btn")
            yield Button("Record (30s)", variant="warning", id="record-btn")
        yield DataTable(id="results-table")
        yield Static("Ready. Press Record to capture audio.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        os.makedirs(REC_DIR, exist_ok=True)
        init_db()
        self._status = self.query_one("#status-bar", Static)
        self._record_btn = self.query_one("#record-btn", Button)
        table = self.query_one("#results-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("ID", "Title", "Duration", "Date")
        self._refresh_list()
        self.query_one("#search-input", Input).focus()

    def _refresh_list(self, query=""):
        table = self.query_one("#results-table", DataTable)
        table.clear()
        for r in search_transcripts(query):
            dur = f"{r['duration']:.1f}s" if r['duration'] else "?"
            table.add_row(str(r['id']), r['title'][:60], dur, r['date'])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._refresh_list(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            q = self.query_one("#search-input", Input).value
            self._refresh_list(q)
        elif event.button.id == "record-btn":
            self._do_record()

    @work(thread=True)
    def _do_record(self):
        self.call_from_thread(setattr, self._record_btn, "label", "Recording...")
        self.call_from_thread(self._status.update, "Recording for 30 seconds...")

        rec = RecordWorker()
        rec.start(30)
        try:
            path = AUDIO_QUEUE.get(timeout=35)
        except queue.Empty:
            self.call_from_thread(self._status.update, "[red]Recording timed out[/red]")
            self.call_from_thread(setattr, self._record_btn, "label", "Record (30s)")
            return
        self.call_from_thread(setattr, self._record_btn, "label", "Record (30s)")
        self.call_from_thread(self._status.update, "Transcribing...")

        text, duration = TranscribeWorker.transcribe(path)
        title = text[:80].strip() if text.strip() else f"Recording {os.path.basename(path)}"

        cx = sqlite3.connect(DB_PATH)
        cx.execute(
            "INSERT INTO transcripts(title, duration, date, text) VALUES(?,?,?,?)",
            (title, duration, time.strftime("%Y-%m-%d %H:%M"), text))
        cx.commit()
        cx.close()
        self.call_from_thread(self._status.update, f"Transcribed: {title}")
        self.call_from_thread(self._refresh_list)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row = self.query_one("#results-table", DataTable).get_row(event.row_key)
        if row:
            self.push_screen(DetailScreen(int(row[0]), row[1]))


if __name__ == "__main__":
    app = WhisperApp()
    app.run()
