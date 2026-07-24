#!/bin/bash

echo ">>> FileForge post-merge checklist"

echo
echo "1) Run tests:"
echo "   pytest -q"
echo
echo "2) Try core CLI commands:"
echo "   fileforge list"
echo "   fileforge convert notes.md notes.html"
echo "   fileforge batch ./images png jpg --recursive --workers 8"
echo
echo "3) Try Cloud API:"
echo "   pip install -e '.[cloud]'"
echo "   cd cloud-api && uvicorn app.main:app --reload"
echo "   curl -s -H 'X-API-Key: demo-lifetime' -F file=@notes.md 'http://127.0.0.1:8000/v1/convert?target=html' -o out.html"
echo
echo "4) Verify README and paths:"
echo "   - src/fileforge/converters/ contains batch, ocr, pdf, tts"
echo "   - No src/fileforge/pro directory"
echo
echo "5) Commit and tag:"
echo "   git add ."
echo "   git commit -m \"Merge pro converters into unified converters namespace\""
echo "   git tag -a v1.1.0 -m \"Merged pro into converters\""
echo "   git push origin main --tags"
echo
echo ">>> Checklist complete."
