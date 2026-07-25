# Build FileForge.exe with PyInstaller (Windows 11).
#
#   ./windows/build_windows.ps1
#
# Produces windows/dist/FileForge.exe. Run windows/setup_windows.ps1 first to
# create the .venv and install PyInstaller + the FileForge engine.
$ErrorActionPreference = 'Stop'

$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Win  = Join-Path $Repo 'windows'
Write-Host "==> Building FileForge.exe"
Write-Host "    repo:    $Repo"

# Prefer the project venv if present.
$Venv = Join-Path $Repo '.venv'
$Activate = Join-Path $Venv 'Scripts/Activate.ps1'
if (Test-Path $Activate) {
    Write-Host "==> Activating $Activate"
    . $Activate
}

# Ensure the engine + PyInstaller are importable.
python -c "import fileforge" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "==> Installing FileForge engine (editable)"
    python -m pip install --quiet -e "$Repo[images,pdf]"
}
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "==> Installing PyInstaller"
    python -m pip install --quiet pyinstaller
}

# Build from the windows/ dir so the spec's relative paths resolve.
Push-Location $Win
try {
    Write-Host "==> Running PyInstaller"
    pyinstaller --noconfirm --clean fileforge.spec
} finally {
    Pop-Location
}

$Exe = Join-Path $Win 'dist/FileForge.exe'
if (Test-Path $Exe) {
    Write-Host "==> Built: $Exe"
} else {
    Write-Error "Build finished but $Exe was not found."
    exit 1
}
