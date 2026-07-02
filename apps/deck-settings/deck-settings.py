from __future__ import annotations

import os, subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Static, Button
)
from textual import work


# ── Helpers ──────────────────────────────────────────────────────────────

def sys_read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return ""


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), -1


def hsize(b):
    for u in ("", "K", "M", "G", "T"):
        if abs(b) < 1024:
            return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}P"


def fmt_temp(celsius_str):
    try:
        t = float(celsius_str)
        if t > 100:
            t /= 1000
        return f"{t:.1f}°C"
    except:
        return celsius_str


# ── Screens ──────────────────────────────────────────────────────────────

class NavScreen(Screen):
    """Main navigation menu."""
    def compose(self):
        yield Header(show_clock=True)
        with Vertical(id="nav-container"):
            yield Static("[bold cyan]Deck Settings[/bold cyan]", id="nav-title")
            yield Static("Navigate with number keys or click", id="nav-subtitle")
            yield Button("1  —  Network & WiFi", id="btn-network", variant="default")
            yield Button("2  —  Storage", id="btn-storage", variant="default")
            yield Button("3  —  Apps", id="btn-apps", variant="default")
            yield Button("4  —  System", id="btn-system", variant="default")
            yield Button("5  —  Security", id="btn-security", variant="default")
            yield Button("6  —  About", id="btn-about", variant="default")
            yield Static("", classes="spacer")
            yield Button("Q  —  Quit", id="btn-quit", variant="error")
        yield Footer()

    CSS = """
    #nav-container {
        align: center middle;
        padding: 2 4;
    }
    #nav-title {
        text-style: bold;
        content-align: center middle;
        height: 3;
    }
    #nav-subtitle {
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
    }
    Button {
        width: 40;
        margin: 0 0 1 0;
    }
    .spacer { height: 1; }
    """

    def on_button_pressed(self, event: Button.Pressed):
        btn = event.button.id
        screens = {
            "btn-network": "network", "btn-storage": "storage",
            "btn-apps": "apps", "btn-system": "system",
            "btn-security": "security", "btn-about": "about",
        }
        if btn == "btn-quit":
            self.app.exit()
        elif btn in screens:
            self.app.push_screen(screens[btn])

    def on_mount(self):
        self._bind_number_keys()

    def _bind_number_keys(self):
        self.app.bind("1", action_screen="push_screen('network')")
        self.app.bind("2", action_screen="push_screen('storage')")
        self.app.bind("3", action_screen="push_screen('apps')")
        self.app.bind("4", action_screen="push_screen('system')")
        self.app.bind("5", action_screen="push_screen('security')")
        self.app.bind("6", action_screen="push_screen('about')")
        self.app.bind("q", action_screen="quit")


class NetworkScreen(Screen):
    def compose(self):
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]Network & WiFi[/bold cyan]", classes="section-title")
            with Horizontal():
                yield Button("Scan WiFi", id="wifi-scan", variant="primary")
                yield Button("Current Status", id="wifi-status", variant="default")
                yield Button("Back", id="back", variant="default")
            yield Static(id="wifi-output", classes="output-box")
        yield Footer()

    CSS = """
    .section-title { text-style: bold; padding: 1 1; }
    Button { margin: 1 1; min-width: 18; }
    .output-box { border: solid $primary; margin: 1; padding: 1; height: 80%; overflow-y: auto; }
    """

    def on_button_pressed(self, event: Button.Pressed):
        btn = event.button.id
        if btn == "back":
            self.app.pop_screen()
        elif btn == "wifi-scan":
            self._do_scan()
        elif btn == "wifi-status":
            self._do_status()

    @work(thread=True, exclusive=True)
    def _do_scan(self):
        out = self.query_one("#wifi-output", Static)
        out.update("Scanning...")
        so, se, rc = run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"])
        if rc != 0:
            self.call_from_thread(out.update, f"[red]nmcli error:[/red]\n{se}")
            return
        lines = so.split("\n") if so else ["(no networks found)"]
        result = f"[bold]WiFi Networks[/bold] ({len([l for l in lines if l])} found)\n\n"
        for line in lines:
            if not line.strip():
                continue
            parts = line.split(":")
            ssid = parts[0] if len(parts) > 0 else "?"
            signal = parts[1] if len(parts) > 1 else "?"
            sec = parts[2] if len(parts) > 2 else "?"
            try:
                bars = min(int(signal) // 20 + 1, 5) if signal.isdigit() else 0
            except:
                bars = 0
            result += f"  {'█' * bars}{'░' * (5 - bars)}  {ssid:<30}  {sec}\n"
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _do_status(self):
        out = self.query_one("#wifi-output", Static)
        so, se, rc = run(["nmcli", "-t", "dev", "status"])
        conn = ""
        so2, se2, rc2 = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"])
        if rc2 == 0:
            for line in so2.split("\n"):
                if "wifi" in line.lower() or "ethernet" in line.lower():
                    conn += f"  {line.replace(':', '  │  ')}\n"
        ip_r = run(["hostname", "-I"])
        ip = ip_r[0] if ip_r[2] == 0 else "?"
        result = f"[bold]Connection Status[/bold]\n\n{conn}\n[bold]IP:[/bold] {ip}\n"
        self.call_from_thread(out.update, result)


class StorageScreen(Screen):
    def compose(self):
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]Storage[/bold cyan]", classes="section-title")
            with Horizontal():
                yield Button("Disk Usage", id="disk-usage", variant="primary")
                yield Button("ZRAM Status", id="zram-status", variant="default")
                yield Button("Mount Points", id="mounts", variant="default")
                yield Button("Back", id="back", variant="default")
            yield Static(id="storage-output", classes="output-box")
        yield Footer()

    CSS = NetworkScreen.CSS

    def on_button_pressed(self, event: Button.Pressed):
        btn = event.button.id
        if btn == "back":
            self.app.pop_screen()
        elif btn == "disk-usage":
            self._disk_usage()
        elif btn == "zram-status":
            self._zram_status()
        elif btn == "mounts":
            self._mounts()

    @work(thread=True)
    def _disk_usage(self):
        out = self.query_one("#storage-output", Static)
        so, se, rc = run(["df", "-h"])
        result = f"[bold]Disk Usage[/bold]\n\n{so}" if rc == 0 else f"[red]{se}[/red]"
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _zram_status(self):
        out = self.query_one("#storage-output", Static)
        result = "[bold]ZRAM Status[/bold]\n\n"
        if os.path.exists("/proc/swaps"):
            sw, sw_e, sw_rc = run(["cat", "/proc/swaps"])
            result += sw if sw_rc == 0 else "n/a"
        zram_devs = list(Path("/sys/class/block").glob("zram*"))
        if zram_devs:
            for dev in zram_devs:
                name = dev.name
                size = sys_read(dev / "disksize")
                comp = sys_read(dev / "comp_algorithm")
                mm = sys_read(dev / "mm_stat")
                result += f"\n[bold]{name}[/bold]  size={hsize(int(size)) if size.isdigit() else size}  algo={comp}\n"
                if mm:
                    parts = mm.split()
                    if len(parts) >= 3:
                        orig, compr, total = parts[0], parts[1], parts[2]
                        ratio = (float(orig) / float(compr)) if int(compr) > 0 else 0
                        result += f"  orig={hsize(int(orig))}  comp={hsize(int(compr))}  ratio={ratio:.1f}x  total={hsize(int(total))}\n"
        else:
            result += "  (no zram devices)"
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _mounts(self):
        out = self.query_one("#storage-output", Static)
        so, se, rc = run(["findmnt", "-D", "-T"])
        result = f"[bold]Mount Points[/bold]\n\n{so}" if rc == 0 else f"[red]{se}[/red]"
        self.call_from_thread(out.update, result)


class AppsScreen(Screen):
    def compose(self):
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]Apps[/bold cyan]", classes="section-title")
            with Horizontal():
                yield Button("List Installed", id="list-apps", variant="primary")
                yield Button("Refresh", id="refresh-apps", variant="default")
                yield Button("Back", id="back", variant="default")
            yield Static(id="apps-output", classes="output-box")
        yield Footer()

    CSS = NetworkScreen.CSS

    def on_button_pressed(self, event: Button.Pressed):
        btn = event.button.id
        if btn == "back":
            self.app.pop_screen()
        elif btn in ("list-apps", "refresh-apps"):
            self._list_apps()

    @work(thread=True)
    def _list_apps(self):
        out = self.query_one("#apps-output", Static)
        result = "[bold]Installed Apps[/bold]\n\n"
        apps_dir = os.environ.get("DECK_APPS_DIR", os.path.expanduser("~/apps"))
        if Path(apps_dir).exists():
            for entry in sorted(Path(apps_dir).iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    run_sh = entry / "run.sh"
                    has_launcher = "✅" if run_sh.exists() else " "
                    result += f"  {has_launcher} {entry.name}\n"
        else:
            result += "  (no apps directory found)\n"
        # Also list apps installed in the project apps/ dir
        result += "\n[bold]Project Apps[/bold]\n\n"
        project_apps = Path(__file__).parent.parent
        if project_apps.exists():
            for entry in sorted(project_apps.iterdir()):
                if entry.is_dir() and not entry.name.startswith(".") and entry.name != "__pycache__":
                    run_sh = entry / "run.sh"
                    has_launcher = "✅" if run_sh.exists() else " "
                    result += f"  {has_launcher} {entry.name}\n"
        self.call_from_thread(out.update, result)


class SystemScreen(Screen):
    def compose(self):
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]System Settings[/bold cyan]", classes="section-title")
            with Horizontal():
                yield Button("Hostname", id="sys-hostname", variant="primary")
                yield Button("CPU Governor", id="sys-governor", variant="default")
                yield Button("Display Mode", id="sys-display", variant="default")
                yield Button("Uptime & Temp", id="sys-info", variant="default")
                yield Button("Back", id="back", variant="default")
            yield Static(id="system-output", classes="output-box")
        yield Footer()

    CSS = """
    .section-title { text-style: bold; padding: 1 1; }
    Button { margin: 1 1; min-width: 14; }
    .output-box { border: solid $primary; margin: 1; padding: 1; height: 70%; overflow-y: auto; }
    .gov-btn { min-width: 12; }
    """

    def on_button_pressed(self, event: Button.Pressed):
        btn = event.button.id
        if btn == "back":
            self.app.pop_screen()
        elif btn == "sys-hostname":
            self._show_hostname()
        elif btn == "sys-governor":
            self._show_governor()
        elif btn == "sys-display":
            self._do_display_mode()
        elif btn == "sys-info":
            self._show_info()

    def _show_hostname(self):
        out = self.query_one("#system-output", Static)
        hn = sys_read("/etc/hostname") or "?"
        so, se, rc = run(["hostnamectl"])
        result = f"[bold]Hostname:[/bold] {hn}\n\n"
        if rc == 0:
            result += so
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _show_governor(self):
        out = self.query_one("#system-output", Static)
        result = "[bold]CPU Governor[/bold]\n\n"
        govs = {}
        for cpu_dir in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
            try:
                gov = (cpu_dir / "cpufreq" / "scaling_governor").read_text().strip()
                min_f = (cpu_dir / "cpufreq" / "scaling_min_freq").read_text().strip()
                max_f = (cpu_dir / "cpufreq" / "scaling_max_freq").read_text().strip()
                cur_f = (cpu_dir / "cpufreq" / "scaling_cur_freq").read_text().strip()
                govs[cpu_dir.name] = (gov, min_f, max_f, cur_f)
            except Exception:
                continue
        if not govs:
            result += "  (no cpufreq info available)"
        else:
            for cpu, (g, mn, mx, cur) in sorted(govs.items()):
                result += f"  {cpu}: governor={g}  freq={int(cur)//1000}MHz  (min={int(mn)//1000}MHz  max={int(mx)//1000}MHz)\n"
        result += "\n[bold]Press a key to set governor:[/bold]\n"
        result += "  [P]erformance  [O]ndemand  [S]powersave  [C]onservative"
        self.call_from_thread(out.update, result)

    def on_key(self, event):
        out = self.query_one("#system-output", Static)
        current = str(out.renderable or "")
        if "CPU Governor" not in current:
            return
        gov_map = {"p": "performance", "o": "ondemand", "s": "powersave", "c": "conservative"}
        if event.key in gov_map:
            target = gov_map[event.key]
            for cpu_dir in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
                try:
                    (cpu_dir / "cpufreq" / "scaling_governor").write_text(target)
                except Exception:
                    pass
            self._show_governor()

    @work(thread=True)
    def _do_display_mode(self):
        out = self.query_one("#system-output", Static)
        check = run(["which", "deck-mode"])
        if check[2] != 0:
            self.call_from_thread(out.update, "[yellow]deck-mode not installed (run setup-extras.sh)[/yellow]")
            return
        result = "[bold]Display Mode[/bold]\n\n"
        result += "  Press a key:\n"
        result += "  [W]ork (normal)   [S]tealth (dimmed)   [B]right (max)\n"
        result += "  Or run directly: deck-mode stealth|work|bright\n\n"
        so, se, rc = run(["deck-mode", "show"])
        if rc == 0:
            result += so
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _show_info(self):
        out = self.query_one("#system-output", Static)
        up = sys_read("/proc/uptime")
        temp = sys_read("/sys/class/thermal/thermal_zone0/temp")
        load = sys_read("/proc/loadavg")
        result = "[bold]System Info[/bold]\n\n"
        if up:
            try:
                secs = int(float(up.split()[0]))
                d, r = divmod(secs, 86400)
                hh, mm = divmod(r, 3600)
                mm //= 60
                result += f"  Uptime: {d}d {hh}h {mm}m\n"
            except:
                pass
        if temp:
            result += f"  Temperature: {fmt_temp(temp)}\n"
        if load:
            result += f"  Load: {load.split()[0]} {load.split()[1]} {load.split()[2]}\n"
        so, se, rc = run(["uname", "-a"])
        if rc == 0:
            result += f"\n  Kernel: {so}"
        self.call_from_thread(out.update, result)


class SecurityScreen(Screen):
    def compose(self):
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]Security[/bold cyan]", classes="section-title")
            with Horizontal():
                yield Button("Vault Status", id="sec-vault", variant="primary")
                yield Button("Open Vault", id="sec-vault-open", variant="default")
                yield Button("Close Vault", id="sec-vault-close", variant="default")
            with Horizontal():
                yield Button("Fingerprint", id="sec-bio", variant="default")
                yield Button("SSH Status", id="sec-ssh", variant="default")
                yield Button("Firewall", id="sec-firewall", variant="default")
                yield Button("Back", id="back", variant="default")
            yield Static(id="security-output", classes="output-box")
        yield Footer()

    CSS = """
    .section-title { text-style: bold; padding: 1 1; }
    Button { margin: 0 1; min-width: 14; }
    .output-box { border: solid $primary; margin: 1; padding: 1; height: 60%; overflow-y: auto; }
    """

    def on_button_pressed(self, event: Button.Pressed):
        btn = event.button.id
        if btn == "back":
            self.app.pop_screen()
        elif btn == "sec-vault":
            self._vault_status()
        elif btn == "sec-vault-open":
            self._vault_open()
        elif btn == "sec-vault-close":
            self._vault_close()
        elif btn == "sec-bio":
            self._biometric()
        elif btn == "sec-ssh":
            self._ssh_status()
        elif btn == "sec-firewall":
            self._firewall()

    @work(thread=True)
    def _vault_status(self):
        out = self.query_one("#security-output", Static)
        result = "[bold]Deck Vault[/bold]\n\n"
        vault_img = os.environ.get("VAULT_IMG", os.path.expanduser("~/Vault.img"))
        if Path(vault_img).exists():
            size = Path(vault_img).stat().st_size
            result += f"  Vault: {hsize(size)} at {vault_img}\n"
            so, se, rc = run(["cryptsetup", "status", "deckvault"])
            if rc == 0:
                first_line = so.split("\n")[0] if so else ""
                result += f"  Status: [green]OPEN[/green]\n  {first_line}"
            else:
                result += "  Status: [yellow]CLOSED[/yellow]\n"
        else:
            result += "  [yellow]No vault found. Create one: deck-vault init[/yellow]\n"
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _vault_open(self):
        out = self.query_one("#security-output", Static)
        rc = subprocess.run(["deck-vault", "open"], capture_output=True, text=True)
        if rc.returncode == 0:
            self.call_from_thread(out.update, "[green]Vault unlocked![/green]")
        else:
            self.call_from_thread(out.update, f"[red]Failed: {rc.stderr.strip()}[/red]")

    @work(thread=True)
    def _vault_close(self):
        out = self.query_one("#security-output", Static)
        rc = subprocess.run(["deck-vault", "close"], capture_output=True, text=True)
        if rc.returncode == 0:
            self.call_from_thread(out.update, "[green]Vault locked.[/green]")
        else:
            self.call_from_thread(out.update, f"[red]Failed: {rc.stderr.strip()}[/red]")

    @work(thread=True)
    def _biometric(self):
        out = self.query_one("#security-output", Static)
        check = run(["which", "deck-biometric"])
        if check[2] != 0:
            self.call_from_thread(out.update, "[yellow]deck-biometric not installed (run setup-upgrades.sh)[/yellow]")
            return
        so, se, rc = run(["deck-biometric", "status"])
        result = "[bold]Fingerprint Scanner[/bold]\n\n"
        result += so if rc == 0 else f"[red]{se}[/red]"
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _ssh_status(self):
        out = self.query_one("#security-output", Static)
        result = "[bold]SSH[/bold]\n\n"
        so, se, rc = run(["systemctl", "is-active", "ssh"])
        result += f"  Service: {'[green]active[/green]' if so == 'active' else '[yellow]' + so + '[/yellow]'}\n"
        so2, se2, rc2 = run(["sshd", "-T"], timeout=3)
        if rc2 == 0:
            for line in so2.split("\n"):
                if "passwordauthentication" in line:
                    val = line.split()[-1]
                    result += f"  PasswordAuth: {'[red]yes[/red]' if val == 'yes' else '[green]no[/green]'}\n"
                if "permitrootlogin" in line:
                    val = line.split()[-1]
                    result += f"  RootLogin: {'[red]' + val + '[/red]' if val != 'no' and val != 'prohibit-password' else '[green]' + val + '[/green]'}\n"
                if "port" in line and len(line.split()) == 2:
                    result += f"  Port: {line.split()[-1]}\n"
        self.call_from_thread(out.update, result)

    @work(thread=True)
    def _firewall(self):
        out = self.query_one("#security-output", Static)
        result = "[bold]Firewall (UFW)[/bold]\n\n"
        so, se, rc = run(["ufw", "status", "verbose"])
        result += so if rc == 0 else f"[yellow]UFW not installed or not running[/yellow]\n{se}"
        self.call_from_thread(out.update, result)


class AboutScreen(Screen):
    CSS = """
    .section-title { text-style: bold; padding: 1 1; }
    .output-box { border: solid $primary; margin: 1; padding: 1; height: 80%; overflow-y: auto; }
    Button { margin: 1; min-width: 14; }
    """

    def compose(self):
        yield Header(show_clock=True)
        with ScrollableContainer():
            yield Static("[bold cyan]About This Deck[/bold cyan]", classes="section-title")
            with Horizontal():
                yield Button("Refresh", id="about-refresh", variant="primary")
                yield Button("Back", id="back", variant="default")
            yield Static(id="about-output", classes="output-box")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "about-refresh":
            self._gather_info()
        elif event.button.id == "back":
            self.app.pop_screen()

    @work(thread=True)
    def _gather_info(self):
        out = self.query_one("#about-output", Static)
        result = ""
        so, se, rc = run(["cat", "/proc/device-tree/model"], timeout=2)
        if rc == 0:
            result += f"[bold]Model:[/bold] {so.strip()}\n"
        result += f"[bold]Hostname:[/bold] {sys_read('/etc/hostname') or '?'}\n"
        so2, se2, rc2 = run(["uname", "-r"])
        if rc2 == 0:
            result += f"[bold]Kernel:[/bold] {so2}\n"
        so3, se3, rc3 = run(["cat", "/etc/os-release"])
        if rc3 == 0:
            for line in so3.split("\n"):
                if line.startswith("PRETTY_NAME="):
                    val = line.split("=", 1)[1].strip("\"")
                    result += f"[bold]OS:[/bold] {val}\n"
        so4, se4, rc4 = run(["free", "-h"])
        if rc4 == 0:
            mem_line = so4.split("\n")[1] if so4 else ""
            parts = mem_line.split()
            if len(parts) >= 3:
                result += f"[bold]Memory:[/bold] {parts[1]} total\n"
        so5, se5, rc5 = run(["df", "-h", "/"])
        if rc5 == 0:
            disk_line = so5.split("\n")[1] if so5 else ""
            parts = disk_line.split()
            if len(parts) >= 4:
                result += f"[bold]Disk:[/bold] {parts[1]} total  ({parts[4]} used)\n"
        temp = sys_read("/sys/class/thermal/thermal_zone0/temp")
        if temp:
            result += f"[bold]Temp:[/bold] {fmt_temp(temp)}\n"
        so6, se6, rc6 = run(["uptime", "-p"])
        if rc6 == 0:
            result += f"[bold]Uptime:[/bold] {so6}\n"
        result += f"\n[bold]Cyberdeck OS Layer[/bold]\n"
        result += f"  os/ version: see CHANGELOG.md\n"
        result += f"  apps: {len([p for p in Path(__file__).parent.parent.iterdir() if p.is_dir() and not p.name.startswith('.')])} installed\n"
        self.call_from_thread(out.update, result)


# ── Main App ─────────────────────────────────────────────────────────────

class DeckSettings(App):
    TITLE = "Deck Settings"
    SUBTITLE = "system configuration"

    SCREENS = {
        "nav": NavScreen(),
        "network": NetworkScreen(),
        "storage": StorageScreen(),
        "apps": AppsScreen(),
        "system": SystemScreen(),
        "security": SecurityScreen(),
        "about": AboutScreen(),
    }

    BINDINGS = [
        Binding("escape", "pop_screen", "Back", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("h", "pop_screen", "Home", show=True),
    ]

    def on_mount(self):
        self.push_screen("nav")


if __name__ == "__main__":
    app = DeckSettings()
    app.run()
