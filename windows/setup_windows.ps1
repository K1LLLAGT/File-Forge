# Set up a Windows dev environment for building FileForge.exe.
#
#   ./windows/setup_windows.ps1
#
# Creates a .venv at the repo root, installs the FileForge engine with the
# image/PDF extras, and installs PyInstaller. After this, run
# ./windows/build_windows.ps1 to produce the exe.
$ErrorActionPreference = 'Stop'

$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "==> FileForge Windows build setup"
Write-Host "    repo: $Repo"

$Python = $null
foreach ($cand in @('py', 'python', 'python3')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $Python = $cand; break }
}
if (-not $Python) {
    Write-Error "Python 3.9+ not found. Install it from https://python.org and re-run."
    exit 1
}
Write-Host "==> Python launcher: $Python"

$Venv = Join-Path $Repo '.venv'
if (-not (Test-Path $Venv)) {
    Write-Host "==> Creating virtualenv at $Venv"
    & $Python -m venv $Venv
}
. (Join-Path $Venv 'Scripts/Activate.ps1')

Write-Host "==> Upgrading pip"
python -m pip install --quiet --upgrade pip

Write-Host "==> Installing FileForge engine (editable, with images+pdf extras)"
python -m pip install --quiet -e "$Repo[images,pdf]"

Write-Host "==> Installing PyInstaller"
python -m pip install --quiet pyinstaller

Write-Host "==> Done. Next:"
Write-Host "    ./windows/build_windows.ps1      # produce windows/dist/FileForge.exe"
Write-Host "    python windows/fileforge_app.py  # or run from source"
