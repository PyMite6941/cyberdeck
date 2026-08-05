"""Shared cyberdeck Textual theme + CSS.

Every deck app should look like it came from the same terminal. Import this
and call ``apply_theme(self)`` in ``on_mount`` (or set ``CSS = DECK_CSS``) so
the whole apps/ suite shares one phosphor-on-black palette.

Usage from an app in apps/<app>/<app>.py::

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "deck-lib"))
    from deck_theme import apply_theme, DECK_CSS

    class MyApp(App):
        CSS = DECK_CSS
        def on_mount(self):
            apply_theme(self)

``apply_theme`` is a no-op on Textual builds without the theme API, so apps
stay runnable everywhere.

For colour *inside* a widget's text use ``styled("warn", msg)`` — inline markup
can't reach the CSS classes below (see ``DECK_MARKUP``).
"""

from __future__ import annotations

# Cyberdeck palette — cyan primary, phosphor-green accent, amber warning,
# on a near-black surface. Kept in one place so every app matches.
DECK_COLORS = {
    "primary": "#00e5ff",    # cyan — headers, borders, selection
    "secondary": "#39ff14",  # phosphor green — accents, "installed"
    "accent": "#39ff14",
    "foreground": "#c8f7e2",
    "background": "#080b0c",
    "surface": "#101617",
    "panel": "#0d1314",
    "success": "#39ff14",
    "warning": "#ffb300",     # amber — "update available"
    "error": "#ff453a",
}


def cyberdeck_theme():
    """Return a Textual Theme, or None if this Textual build lacks the API."""
    try:
        from textual.theme import Theme
    except Exception:
        return None
    return Theme(
        name="cyberdeck",
        primary=DECK_COLORS["primary"],
        secondary=DECK_COLORS["secondary"],
        accent=DECK_COLORS["accent"],
        foreground=DECK_COLORS["foreground"],
        background=DECK_COLORS["background"],
        surface=DECK_COLORS["surface"],
        panel=DECK_COLORS["panel"],
        success=DECK_COLORS["success"],
        warning=DECK_COLORS["warning"],
        error=DECK_COLORS["error"],
        dark=True,
    )


def apply_theme(app) -> None:
    """Register and activate the cyberdeck theme. Safe on any Textual build."""
    theme = cyberdeck_theme()
    if theme is None:
        return
    try:
        app.register_theme(theme)
        app.theme = "cyberdeck"
    except Exception:
        # Older Textual: fall back to dark mode, colors come from DECK_CSS.
        try:
            app.dark = True
        except Exception:
            pass


# Shared CSS. Uses design tokens ($primary, $surface, ...) so it tracks the
# theme above, plus literal fallbacks for the status glyphs.
DECK_CSS = """
Screen { background: $background; }
Header { background: $panel; color: $primary; text-style: bold; }
Footer { background: $panel; }
.panel { border: round $primary; background: $surface; padding: 1; margin: 1; }
.title { color: $primary; text-style: bold; }
.muted { color: $foreground 60%; }
.ok      { color: $success; }
.warn    { color: $warning; }
.err     { color: $error; }
ListView { background: $surface; border: round $primary; }
ListView > ListItem.--highlight { background: $primary 25%; }
DataTable { background: $surface; }
DataTable > .datatable--cursor { background: $primary 30%; }
Tabs { background: $panel; }
Tab.-active { color: $primary; text-style: bold; }
"""

# --- inline markup -------------------------------------------------------- #
# CSS classes (.ok/.warn/...) style whole *widgets*; they do NOT apply to inline
# markup spans inside a widget's content — Textual resolves "[warn]x[/warn]"
# against theme/color names, not the stylesheet, so an unknown tag silently
# renders in the default foreground. Inline colouring therefore has to name a
# real colour. `styled()` does that from the one palette above, and works on
# every Textual build (unlike the newer "[$warning]" variable syntax).
# Values are Rich/Textual *style strings*, so they may combine attributes and a
# colour ("bold #39ff14"). Names mirror the CSS classes below on purpose — the
# same intent, reachable from inline text.
DECK_MARKUP = {
    "title": DECK_COLORS["primary"],
    "primary": DECK_COLORS["primary"],
    "ok": DECK_COLORS["success"],
    "warn": DECK_COLORS["warning"],
    "err": DECK_COLORS["error"],
    "muted": "#7f9a92",
    "big": f"bold {DECK_COLORS['secondary']}",   # large readouts (sensor cards)
}


def styled(name: str, text: str) -> str:
    """Wrap ``text`` in deck-palette inline markup. Unknown names pass through."""
    style = DECK_MARKUP.get(name)
    return f"[{style}]{text}[/]" if style else text


# Status glyphs used across deck apps (deck-store, launchers).
GLYPH = {
    "installed": "✓",   # installed & current
    "update": "⟳",      # installed, update available
    "available": "○",   # not installed
    "builtin": "◆",     # ships with the deck (in-repo)
}
