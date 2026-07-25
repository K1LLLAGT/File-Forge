# FileForge 2.0 — Windows 11 setup.
# Installs the FileForge engine (editable) plus the discovery/suggestion CLIs.
# Run from an elevated or normal PowerShell:  ./setup/setup_windows.ps1
$ErrorActionPreference = 'Stop'

$Here = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "==> FileForge 2.0 setup (Windows 11)"
Write-Host "    repo root: $Here"

# Locate a Python launcher.
$Python = $null
foreach ($cand in @('py', 'python', 'python3')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $Python = $cand; break }
}
if (-not $Python) {
    Write-Error "Python 3.9+ not found. Install it from https://python.org and re-run."
    exit 1
}
Write-Host "==> Python launcher: $Python"

# Create / activate a virtual environment unless opted out.
if ($env:FILEFORGE_NO_VENV -ne '1') {
    $Venv = Join-Path $Here '.venv'
    if (-not (Test-Path $Venv)) {
        Write-Host "==> Creating virtualenv at $Venv"
        & $Python -m venv $Venv
    }
    $Activate = Join-Path $Venv 'Scripts/Activate.ps1'
    Write-Host "==> Activating $Activate"
    . $Activate
    $Python = 'python'
}

Write-Host "==> Upgrading pip"
& $Python -m pip install --quiet --upgrade pip

$Extras = $env:FILEFORGE_EXTRAS
if ($Extras) {
    Write-Host "==> Installing FileForge with extras: [$Extras]"
    & $Python -m pip install --quiet -e "$Here[$Extras]"
} else {
    Write-Host "==> Installing FileForge (core)"
    & $Python -m pip install --quiet -e "$Here"
}

Write-Host "==> Verifying console entry points"
foreach ($cmd in @('fileforge', 'fileforge-discover', 'fileforge-suggest', 'fileforge-cli')) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Host "    ok: $cmd"
    } else {
        Write-Host "    warn: $cmd not on PATH (activate the venv first)"
    }
}

Write-Host "==> Done. Try:"
Write-Host "    fileforge list"
Write-Host "    fileforge-discover"
Write-Host "    fileforge-suggest ."
Write-Host "    fileforge-cli --dir . --discover"
