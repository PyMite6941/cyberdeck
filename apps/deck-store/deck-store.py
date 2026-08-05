#!/usr/bin/env python3
"""deck-store — browse and install deck apps (CLI + Textual TUI).

    deck-store                 launch the TUI (default)
    deck-store list            list apps + install status
    deck-store search <query>  filter by name/tag/category
    deck-store info <id>       show details + loaded commit + update status
    deck-store install <id>    install a vendored app (clone + private venv)
    deck-store upgrade <id>    fast-forward + wipe caches (use --all for all)
    deck-store refresh         check every vendored app for updates
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

# UTF-8 output so the status glyphs render on any console (Windows cp1252 too).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deck-lib"))

from store.registry import Registry, App           # noqa: E402
from store import appstate as st                     # noqa: E402
from store import actions                            # noqa: E402

try:
    from deck_theme import GLYPH, styled
except Exception:                                     # pragma: no cover
    GLYPH = {"installed": "OK", "update": "UP", "available": "--", "builtin": "**"}

    def styled(_name, text):                          # noqa: D103
        return text

STATE_LABEL = {
    st.INSTALLED: ("installed", "ok"),
    st.UPDATE: ("update available", "warn"),
    st.AVAILABLE: ("not installed", "muted"),
    st.BUILTIN: ("built-in", "ok"),
}


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #

def _glyph(state: str) -> str:
    return {
        st.INSTALLED: GLYPH["installed"], st.UPDATE: GLYPH["update"],
        st.AVAILABLE: GLYPH["available"], st.BUILTIN: GLYPH["builtin"],
    }.get(state, "?")


def cli_list(reg: Registry, state: st.StateStore, apps: list[App] | None = None):
    apps = apps if apps is not None else reg.apps
    print(f"{'':2} {'ID':22} {'STATUS':18} {'COMMIT':10} SUMMARY")
    for a in apps:
        s = state.status(a)
        label = STATE_LABEL.get(s.state, ("?", ""))[0]
        commit = s.local or ("—" if a.is_vendored else "")
        print(f"{_glyph(s.state):2} {a.id:22} {label:18} {commit:10} {a.summary}")


def cli_info(reg: Registry, state: st.StateStore, app_id: str):
    a = reg.get(app_id)
    if not a:
        print(f"No such app: {app_id}")
        return 1
    s = state.status(a)
    print(f"{a.name}  ({a.id})")
    print(f"  {a.summary}")
    print(f"  category   : {a.category}")
    print(f"  tags       : {', '.join(a.tags)}")
    print(f"  interfaces : {', '.join(a.interfaces)}")
    print(f"  status     : {_glyph(s.state)} {STATE_LABEL.get(s.state, ('?',''))[0]}")
    if a.is_vendored:
        print(f"  source     : {a.repo_url} ({a.branch})")
        print(f"  loaded     : {s.local or '(not installed)'}")
        if s.remote:
            print(f"  remote     : {s.remote}" + (f"  ({s.behind} behind)" if s.behind else "  (up to date)"))
        else:
            print("  remote     : (run 'deck-store refresh' to check)")
    if a.requires_pkg:
        print(f"  needs pkgs : {', '.join(a.requires_pkg)}")
    return 0


def cli_refresh(reg: Registry, state: st.StateStore):
    vend = [a for a in reg.apps if a.is_vendored]
    print(f"Checking {len(vend)} vendored app(s) for updates ...")
    updates = []
    for a in vend:
        s = state.refresh(a)
        if s.update_available:
            updates.append((a, s))
        tag = f"{s.behind} behind" if s.update_available else "up to date" if s.local else "not installed"
        print(f"  {_glyph(s.state):2} {a.id:22} {tag}")
    if updates:
        print(f"\n{len(updates)} update(s) available:")
        for a, s in updates:
            print(f"  {a.id}: {s.local} -> {s.remote} ({s.behind} commits)")
        print("Run 'deck-store upgrade <id>' or 'deck-store upgrade --all'.")
    else:
        print("\nEverything up to date.")


def run_cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="deck-store", description="Browse and install deck apps.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list")
    sp = sub.add_parser("search"); sp.add_argument("query", nargs="*")
    sp = sub.add_parser("info"); sp.add_argument("id")
    sp = sub.add_parser("install"); sp.add_argument("id")
    sp = sub.add_parser("uninstall"); sp.add_argument("id"); sp.add_argument("--yes", action="store_true")
    sp = sub.add_parser("upgrade"); sp.add_argument("id", nargs="?"); sp.add_argument("--all", action="store_true")
    sub.add_parser("refresh")
    sub.add_parser("tui")
    args = p.parse_args(argv)

    reg = Registry.load()
    state = st.StateStore()

    if args.cmd in (None, "tui"):
        return run_tui(reg, state)
    if args.cmd == "list":
        cli_list(reg, state); return 0
    if args.cmd == "search":
        cli_list(reg, state, reg.search(" ".join(args.query))); return 0
    if args.cmd == "info":
        return cli_info(reg, state, args.id)
    if args.cmd == "refresh":
        cli_refresh(reg, state); return 0
    if args.cmd == "install":
        a = reg.get(args.id)
        if not a:
            print(f"No such app: {args.id}"); return 1
        return 0 if actions.install(a) else 1
    if args.cmd == "uninstall":
        a = reg.get(args.id)
        if not a:
            print(f"No such app: {args.id}"); return 1
        # Deletes everything under src/ — for grimoire that's the whole tome.
        if not args.yes:
            print(f"This deletes {st.src_dir(a)} and everything in it "
                  f"(data the app keeps there is NOT recoverable).")
            if input("Continue? [y/N] ").strip().lower() != "y":
                print("Cancelled."); return 1
        return 0 if actions.uninstall(a) else 1
    if args.cmd == "upgrade":
        if args.all:
            ok = True
            for a in [x for x in reg.apps if x.is_vendored]:
                state.refresh(a)
                if state.status(a).update_available:
                    ok = actions.upgrade(a, state) and ok
            return 0 if ok else 1
        if not args.id:
            print("Usage: deck-store upgrade <id> | --all"); return 1
        a = reg.get(args.id)
        if not a:
            print(f"No such app: {args.id}"); return 1
        return 0 if actions.upgrade(a, state) else 1
    return 0


# --------------------------------------------------------------------------- #
#  TUI
# --------------------------------------------------------------------------- #

def build_store_app(reg: Registry, state: st.StateStore):
    """Build the Textual app instance. Returns None if Textual isn't installed.

    Split out from ``run_tui`` so the TUI can be driven headlessly in tests
    (``async with app.run_test()``) without launching a real terminal.
    """
    try:
        from textual import work
        from textual.app import App as TextualApp, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal, Vertical
        from textual.widgets import (
            Header, Footer, Static, ListView, ListItem, Label, Input, Tabs, Tab,
        )
    except Exception as e:
        print(f"Textual not available ({e}); falling back to list.\n")
        return None

    try:
        from deck_theme import apply_theme, DECK_CSS
    except Exception:
        def apply_theme(_app):  # noqa
            pass
        DECK_CSS = ""

    UPDATES = "Updates"

    def _tab_id(category: str) -> str:
        """Textual widget ids allow only [A-Za-z0-9_-], so slugify the name."""
        return "cat-" + "".join(c if c.isalnum() or c in "_-" else "-" for c in category)

    class AppItem(ListItem):
        def __init__(self, app: App, status: st.Status):
            glyph = styled(STATE_LABEL.get(status.state, ("", "muted"))[1],
                           _glyph(status.state))
            commit = f" [dim]{status.local}[/dim]" if status.local else ""
            super().__init__(Label(f"{glyph} {app.name}{commit}"))
            self.app_id = app.id

    class Store(TextualApp):
        TITLE = "deck-store"
        SUB_TITLE = "app store"
        CSS = DECK_CSS + """
        #body { height: 1fr; }
        #left { width: 42%; }
        #detail { width: 58%; padding: 1 2; }
        #search { margin: 0 1; }
        #statusbar { height: 1; background: $panel; color: $primary; padding: 0 1; }
        ListView { height: 1fr; }
        """
        BINDINGS = [
            Binding("enter", "primary", "Install/Run"),
            Binding("u", "upgrade", "Upgrade"),
            Binding("r", "refresh", "Check updates"),
            Binding("x", "uninstall", "Uninstall"),
            Binding("slash", "search", "Search"),
            Binding("escape", "unfocus", "Back to list", show=False),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(self, reg: Registry, state: st.StateStore):
            super().__init__()
            self.reg = reg
            self.state = state
            self.category = "All"
            self.query = ""
            self.has_updates = False
            self.busy = False          # a clone/pip/fetch job is running
            self._widgets_ready = False        # widgets exist (on_mount has run)
            self._confirm_uninstall = None     # app id awaiting a second `x`
            self.selected_id = None            # authoritative selection

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            self.tabs = Tabs(*self._tab_objects(), id="tabs")
            yield self.tabs
            with Horizontal(id="body"):
                with Vertical(id="left"):
                    yield Input(placeholder="search…", id="search")
                    yield ListView(id="applist")
                yield Static(id="detail", markup=True)
            yield Static("", id="statusbar")
            yield Footer()

        # -- tab helpers --
        def _categories(self) -> list[str]:
            cats = ["All"] + list(self.reg.categories)
            if self.has_updates:
                cats.insert(1, UPDATES)
            return cats

        def _tab_objects(self):
            return [Tab(c, id=_tab_id(c)) for c in self._categories()]

        def _sync_updates_tab(self):
            """Add/remove the Updates tab in place.

            Rebuilding the whole Tabs bar would reset the active tab and drop
            the user back to "All" after every refresh, so only the one
            conditional tab is inserted or removed.
            """
            tid = _tab_id(UPDATES)
            exists = bool(self.tabs.query(f"#{tid}"))
            if self.has_updates and not exists:
                self.tabs.add_tab(Tab(UPDATES, id=tid), after=_tab_id("All"))
            elif exists and not self.has_updates:
                if self.category == UPDATES:
                    self.tabs.active = _tab_id("All")
                self.tabs.remove_tab(tid)

        # -- lifecycle --
        def on_mount(self):
            apply_theme(self)
            self.applist = self.query_one("#applist", ListView)
            self.detail = self.query_one("#detail", Static)
            self.statusbar = self.query_one("#statusbar", Static)
            self._widgets_ready = True
            self._reload_list()
            self._update_statusbar()

        # -- data -> widgets --
        def _visible_apps(self) -> list[App]:
            if self.category == UPDATES:
                return [a for a in self.reg.apps
                        if a.is_vendored and self.state.status(a).update_available]
            return self.reg.search(self.query, self.category)

        def _reload_list(self, keep: str | None = None):
            """Rebuild the list, re-selecting ``keep`` (or the current app)."""
            keep = keep or self.selected_id
            visible = self._visible_apps()
            ids = [a.id for a in visible]
            target = keep if keep in ids else (ids[0] if ids else None)

            self.applist.clear()
            for a in visible:
                self.applist.append(AppItem(a, self.state.status(a)))

            # clear()/append() only *schedule* the un/mounts, so the ListView is
            # still empty right now and an index set here would be dropped. The
            # selection is therefore tracked on the app (authoritative and
            # available immediately, so an action fired right after a filter
            # can't act on a stale widget) and the highlight bar catches up on
            # the next refresh.
            self.selected_id = target
            self._show_detail(self.reg.get(target) if target else None)
            self.call_after_refresh(self._restore_selection, ids, target)

        def _restore_selection(self, ids: list[str], target: str | None):
            if target in ids:
                self.applist.index = ids.index(target)

        def _selected_id(self) -> str | None:
            return self.selected_id

        def _selected_app(self) -> App | None:
            return self.reg.get(self.selected_id) if self.selected_id else None

        def _update_statusbar(self, note: str = ""):
            n_up = sum(1 for a in self.reg.apps
                       if a.is_vendored and self.state.status(a).update_available)
            n_inst = sum(1 for a in self.reg.apps if self.state.status(a).installed)
            msg = f"{n_inst}/{len(self.reg.apps)} installed"
            if n_up:
                msg += "   " + styled(
                    "warn", f"{GLYPH['update']} {n_up} update(s) available — see Updates tab")
            if note:
                msg += "   " + styled("muted", note)
            self.statusbar.update(msg)

        def _show_detail(self, app: App | None):
            if app is None:
                self.detail.update("")
                return
            s = self.state.status(app)
            label, color = STATE_LABEL.get(s.state, ("?", "muted"))
            lines = [
                f"{styled('title', app.name)}  [dim]({app.id})[/dim]",
                "",
                app.summary,
                "",
                f"status     : {styled(color, f'{_glyph(s.state)} {label}')}",
                f"category   : {app.category}",
                f"tags       : {', '.join(app.tags)}",
                f"interfaces : {', '.join(app.interfaces)}",
            ]
            if app.is_vendored:
                lines.append(f"source     : {app.repo_url}")
                lines.append(f"loaded     : {s.local or '(not installed)'}")
                if s.remote:
                    tail = f"{s.behind} behind" if s.behind else "up to date"
                    lines.append(f"remote     : {s.remote}  ({tail})")
                else:
                    lines.append("remote     : press [b]r[/b] to check for updates")
            if app.requires_pkg:
                lines.append(f"needs pkgs : {', '.join(app.requires_pkg)}")
            lines.append("")
            if s.state == st.AVAILABLE:
                lines.append("[b]Enter[/b] to install." if app.is_vendored
                             else "Built-in app — missing from this deck.")
            elif s.state == st.UPDATE:
                lines.append("[b]u[/b] to upgrade (wipes caches).   [b]Enter[/b] to run.")
            else:
                lines.append("[b]Enter[/b] to run.")
            self.detail.update("\n".join(lines))

        # -- events --
        def on_tabs_tab_activated(self, event: Tabs.TabActivated):
            # Tabs activates its first tab while mounting, before on_mount has
            # bound the widget handles — ignore that one.
            tid = event.tab.id or ""
            self.category = tid[len("cat-"):] if tid.startswith("cat-") else "All"
            if self._widgets_ready:
                self._reload_list()

        def on_list_view_highlighted(self, event: ListView.Highlighted):
            app_id = getattr(self.applist.highlighted_child, "app_id", None)
            if app_id is None or app_id == self.selected_id:
                return          # transient None while the list is rebuilding
            # Moving off an app cancels its pending uninstall confirmation, so a
            # stray second `x` can never delete a different app than the prompt.
            self._confirm_uninstall = None
            self.selected_id = app_id
            self._show_detail(self._selected_app())

        def on_input_changed(self, event: Input.Changed):
            self.query = event.value
            if self._widgets_ready:
                self._reload_list()

        # -- background jobs ------------------------------------------------ #
        # git clone / fetch and pip install take seconds to minutes. Run them on
        # a worker thread and marshal every UI touch back through the app thread,
        # so the store stays responsive instead of freezing mid-install.

        def _job_log(self, msg: str):
            self.call_from_thread(self._update_statusbar, msg)

        def _job_done(self, app_id: str, msg: str):
            self.busy = False
            self.has_updates = any(
                a.is_vendored and self.state.status(a).update_available for a in self.reg.apps
            )
            self._sync_updates_tab()
            self._reload_list(keep=app_id)
            self._update_statusbar()
            self.notify(msg, timeout=3)

        def _start_job(self, label: str) -> bool:
            if self.busy:
                self.notify("Another job is still running.", severity="warning")
                return False
            self.busy = True
            self._update_statusbar(label)
            return True

        @work(thread=True, exclusive=True, group="store-job")
        def _do_install(self, app: App):
            ok = actions.install(app, log=self._job_log)
            self.call_from_thread(
                self._job_done, app.id,
                f"{app.name} installed." if ok else f"{app.name}: install failed.")

        @work(thread=True, exclusive=True, group="store-job")
        def _do_upgrade(self, app: App):
            ok = actions.upgrade(app, self.state, log=self._job_log)
            self.call_from_thread(
                self._job_done, app.id,
                f"{app.name} upgraded." if ok else f"{app.name}: upgrade failed.")

        @work(thread=True, exclusive=True, group="store-job")
        def _do_uninstall(self, app: App):
            ok = actions.uninstall(app, log=self._job_log)
            self.call_from_thread(
                self._job_done, app.id,
                f"{app.name} uninstalled." if ok else f"{app.name}: uninstall failed.")

        @work(thread=True, exclusive=True, group="store-job")
        def _do_refresh(self, keep: str | None):
            vendored = [a for a in self.reg.apps if a.is_vendored]
            for a in vendored:
                self._job_log(f"checking {a.id} …")
                self.state.refresh(a)
            n = sum(1 for a in vendored if self.state.status(a).update_available)
            self.call_from_thread(
                self._job_done, keep,
                f"{n} update(s) available." if n else "Everything up to date.")

        # -- actions --
        def action_search(self):
            self.query_one("#search", Input).focus()

        def action_unfocus(self):
            self.applist.focus()

        def action_refresh(self):
            if self._start_job("checking remotes …"):
                self._do_refresh(self._selected_id())

        def action_primary(self):
            app = self._selected_app()
            if app is None:
                return
            if self.state.status(app).state == st.AVAILABLE and app.is_vendored:
                if self._start_job(f"installing {app.id} …"):
                    self._do_install(app)
            else:
                self._launch(app)

        def action_upgrade(self):
            app = self._selected_app()
            if app is None or not self.state.status(app).update_available:
                self.notify("No update for this app.", timeout=2)
                return
            if self._start_job(f"upgrading {app.id} …"):
                self._do_upgrade(app)

        def action_uninstall(self):
            """Delete a vendored app's clone. Needs a second `x` to confirm.

            src/ holds whatever the app stores there — grimoire keeps its whole
            tome and corpora in it — so this never fires on a single keypress.
            """
            app = self._selected_app()
            if app is None or not app.is_vendored or not st.is_cloned(app):
                self._confirm_uninstall = None
                self.notify("Nothing to uninstall for this app.", timeout=2)
                return
            if self._confirm_uninstall != app.id:
                self._confirm_uninstall = app.id
                self.notify(
                    f"Delete {app.name}'s src/ and everything in it? "
                    f"Press x again to confirm.", severity="warning", timeout=6)
                return
            self._confirm_uninstall = None
            if self._start_job(f"uninstalling {app.id} …"):
                self._do_uninstall(app)

        def _launch(self, app: App):
            run = os.path.join(st.app_dir(app), "run.sh")
            if not os.path.exists(run):
                self.notify("No run.sh for this app.", severity="error")
                return
            bash = shutil.which("bash")
            if not bash:
                self.notify("bash not found — can't launch.", severity="error")
                return
            try:
                with self.suspend():
                    subprocess.run([bash, run])
            except Exception as e:
                self.notify(f"Launch failed: {e}", severity="error")

    return Store(reg, state)


def run_tui(reg: Registry, state: st.StateStore) -> int:
    app = build_store_app(reg, state)
    if app is None:                      # Textual missing — CLI fallback
        cli_list(reg, state)
        return 0
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(run_cli(sys.argv[1:]))
