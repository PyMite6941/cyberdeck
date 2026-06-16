# inject-to-sd.ps1 — turn a freshly flashed Raspberry Pi OS SD card into the
# cyberdeck bootable image. Run on Windows AFTER flashing with Raspberry Pi
# Imager (use Imager's settings for hostname/user/Wi-Fi/SSH).
#
# Usage:  .\inject-to-sd.ps1            # auto-detect the boot partition
#         .\inject-to-sd.ps1 -Drive E   # or name it explicitly
#
# What it does to the SD card (boot partition only — FAT32, Windows-writable):
#   \cyberdeck\        <- copy of the whole os/ folder
#   \firstrun.sh       <- first-boot hook script (LF endings enforced)
#   \cmdline.txt       <- appends the systemd.run hook (backup saved first)
# On first boot the Pi stages the files, wires the installer service, removes
# the hook, reboots, then installs everything (incl. FreeCAD) once online.
param([string]$Drive = "")

$ErrorActionPreference = "Stop"
$osDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# ── locate the boot partition ──
if ($Drive -eq "") {
    $candidates = Get-Volume | Where-Object {
        $_.DriveLetter -and $_.FileSystem -eq "FAT32" -and
        (Test-Path "$($_.DriveLetter):\cmdline.txt") -and
        (Test-Path "$($_.DriveLetter):\config.txt")
    }
    if (-not $candidates) {
        Write-Error "No Raspberry Pi boot partition found. Flash the SD with Raspberry Pi Imager first, or pass -Drive X."
    }
    $Drive = ($candidates | Select-Object -First 1).DriveLetter
}
$root = "${Drive}:"
if (-not (Test-Path "$root\cmdline.txt")) {
    Write-Error "$root does not look like a Pi boot partition (no cmdline.txt)."
}
Write-Host "Boot partition: $root (label: $((Get-Volume -DriveLetter $Drive).FileSystemLabel))"

# ── helper: write text as UTF-8, no BOM, LF endings (FAT32 + Linux safe) ──
function Write-Lf([string]$Path, [string]$Text) {
    $Text = $Text -replace "`r`n", "`n" -replace "`r", "`n"
    [IO.File]::WriteAllBytes($Path, [Text.Encoding]::UTF8.GetBytes($Text))
}

# ── 1. copy the OS payload ──
Write-Host "Copying os/ -> $root\cyberdeck\ ..."
robocopy $osDir "$root\cyberdeck" /E /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Error "robocopy failed (code $LASTEXITCODE)" }

# Normalise line endings on everything bash will read.
Get-ChildItem "$root\cyberdeck" -Recurse -Include *.sh, *.service, *.conf, *.txt |
    ForEach-Object { Write-Lf $_.FullName (Get-Content $_.FullName -Raw) }

# ── 2. install the firstrun hook ──
if (Test-Path "$root\firstrun.sh") {
    # Raspberry Pi Imager customisation already owns the hook. Chain our
    # script into Imager's firstrun.sh, just before its self-cleanup line.
    $imager = (Get-Content "$root\firstrun.sh" -Raw) -replace "`r`n", "`n"
    if ($imager -match "cyberdeck") {
        Write-Host "firstrun.sh already chains cyberdeck - left untouched."
    } else {
        $call = "bash /boot/cyberdeck/image/firstrun.sh || bash /boot/firmware/cyberdeck/image/firstrun.sh || true`n"
        $lines = $imager -split "`n"
        $idx = [array]::FindIndex($lines, [Predicate[string]]{ param($l) $l -match '^\s*rm\s+-f\s+.*firstrun' })
        if ($idx -lt 0) { $idx = [array]::FindLastIndex($lines, [Predicate[string]]{ param($l) $l -match '^\s*exit\s+0' }) }
        if ($idx -lt 0) { Write-Error "Couldn't find a safe place to chain into Imager's firstrun.sh" }
        $merged = ($lines[0..($idx-1)] + $call.TrimEnd() + $lines[$idx..($lines.Count-1)]) -join "`n"
        Write-Lf "$root\firstrun.sh" $merged
        Write-Host "Chained cyberdeck install into Imager's firstrun.sh."
    }
} else {
    # No Imager customisation: install our own hook script + cmdline entry.
    Write-Lf "$root\firstrun.sh" (Get-Content "$osDir\image\firstrun.sh" -Raw)
    $cmdline = ((Get-Content "$root\cmdline.txt" -Raw) -replace "`r?`n", " ").Trim()
    if ($cmdline -notmatch "systemd\.run=") {
        Copy-Item "$root\cmdline.txt" "$root\cmdline.txt.bak" -Force
        $cmdline += " systemd.run=/boot/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"
        Write-Lf "$root\cmdline.txt" "$cmdline`n"
        Write-Host "cmdline.txt hooked (backup: cmdline.txt.bak)"
    }
}

Write-Host ""
Write-Host "Done. Safely eject the card, boot the Pi, and wait:"
Write-Host "  boot 1: stages files + hooks installer, auto-reboots (fast)"
Write-Host "  boot 2: installs packages incl. FreeCAD (~10-30 min on Wi-Fi)"
Write-Host "Check progress on the Pi:  journalctl -fu cyberdeck-firstboot"
