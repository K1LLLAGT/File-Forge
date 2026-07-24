#!/bin/bash
set -e

echo ">>> FileForge cleanup starting..."

# Remove Python cache directories
echo ">>> Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true

# Remove stray .pyc files
echo ">>> Removing .pyc files..."
find . -type f -name "*.pyc" -delete

# Remove build artifacts
echo ">>> Removing build/dist artifacts..."
rm -rf build/ dist/ *.egg-info 2>/dev/null || true

# Remove old release bundles except latest
echo ">>> Removing old release bundles..."
find . -maxdepth 1 -type f -name "FileForge-v*.zip" ! -name "FileForge-v1.0.0-full.zip" -delete

# Remove leftover pro directory if any
echo ">>> Removing orphaned pro directory..."
rm -rf src/fileforge/pro 2>/dev/null || true

# Remove temporary editor files
echo ">>> Removing temp files..."
find . -type f -name "*~" -delete
find . -type f -name "*.tmp" -delete
find . -type f -name ".DS_Store" -delete

# Remove Termux swap files
find . -type f -name "*.swp" -delete

# Remove stray logs
find . -type f -name "*.log" -delete

echo ">>> Cleanup complete!"
echo ">>> Recommended next step: git add -A && git commit"
