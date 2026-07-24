#!/bin/bash
set -e

echo ">>> Verifying FileForge folder structure..."

echo
echo "Root:"
ls

echo
echo "src/fileforge/:"
ls src/fileforge

echo
echo "src/fileforge/converters/:"
ls src/fileforge/converters

echo
echo "cloud-api/app/:"
ls cloud-api/app

echo
echo "Key files:"
for f in README.md ARCHITECTURE.md CHANGELOG.md RELEASE_NOTES.md VERSION pyproject.toml; do
    if [ -f "$f" ]; then
        echo "✓ $f exists"
    else
        echo "✗ $f missing"
    fi
done

echo
echo ">>> Structure check complete."
