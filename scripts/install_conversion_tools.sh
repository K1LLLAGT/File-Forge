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

echo "[install] Installing proot-distro for LibreOffice/unoconv..."
pkg install -y proot-distro
proot-distro install ubuntu || echo "[install] Ubuntu proot already installed, continuing."
proot-distro login ubuntu -- apt update
proot-distro login ubuntu -- apt install -y libreoffice unoconv

echo "[install] All conversion tools installed."
echo "[install] Note: document conversions (docx/pptx/xlsx -> pdf/html) run"
echo "[install] through the Ubuntu proot layer, not natively in Termux."
