#!/data/data/com.termux/files/usr/bin/bash
#
# install_conversion_tools.sh — installs everything engine.py shells out to.
#
# LibreOffice/unoconv (used only for doc -> pdf/html conversions) are large
# and don't build natively for Termux, so they run inside a proot-distro
# Ubuntu layer instead. Everything else (ffmpeg, ImageMagick, Pandoc,
# unzip, tar, redis) installs natively via pkg.

set -euo pipefail

echo "[install] Updating pkg..."
pkg update -y

echo "[install] Installing core conversion tools..."
pkg install -y ffmpeg imagemagick pandoc unzip tar redis nodejs python

echo "[install] Installing tesseract (OCR binary — not yet wired into a backend"
echo "[install] route, since it'd collide with the ASCII-art png->txt route; see"
echo "[install] WEBAPP.md. Installing it now so that's a quick follow-up later.)"
pkg install -y tesseract

echo "[install] Installing proot-distro for LibreOffice/unoconv..."
pkg install -y proot-distro
proot-distro install ubuntu || echo "[install] Ubuntu proot already installed, continuing."
proot-distro login ubuntu -- apt update
proot-distro login ubuntu -- apt install -y libreoffice unoconv

echo "[install] Installing the src/fileforge package (subtitles, config/data"
echo "[install] formats, markup, encoding, PDF text extraction) as the backend's"
echo "[install] conversion fallback for formats engine.py doesn't handle directly..."
FILEFORGE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
pip install -e "$FILEFORGE_ROOT[yaml,markdown,xml,toml,xlsx,pdf]"

echo "[install] Attempting QR/ASCII-art/SVG/PDF-render extras (qrcode, cairosvg,"
echo "[install] pymupdf). These have native C dependencies — if any fails to"
echo "[install] build on Termux's ARM64 Android, that's fine: the affected"
echo "[install] routes just report as unavailable rather than breaking anything else."
pip install qrcode || echo "[install] qrcode failed to install — txt->png QR codes won't be available."
pip install cairosvg || echo "[install] cairosvg failed to install — svg->png (via the fallback registry) won't be available; engine.py's direct ImageMagick route for svg->png is unaffected."
pip install pymupdf || echo "[install] pymupdf failed to install — pdf->png rendering won't be available."

echo "[install] All conversion tools installed."
echo "[install] Note: document conversions (docx/pptx/xlsx -> pdf/html) run"
echo "[install] through the Ubuntu proot layer, not natively in Termux."
