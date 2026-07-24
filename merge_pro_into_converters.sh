#!/bin/bash
set -e

echo ">>> Merging src/fileforge/pro into src/fileforge/converters..."

# 1. Move only .py files, ignore __pycache__
if [ -d src/fileforge/pro ]; then
    find src/fileforge/pro -maxdepth 1 -type f -name "*.py" -exec mv {} src/fileforge/converters/ \;
    rm -r src/fileforge/pro
    echo "✓ Moved pro .py modules into converters/ and removed src/fileforge/pro"
else
    echo "✓ src/fileforge/pro already removed"
fi

# 2. Update all imports
echo ">>> Updating import paths..."
grep -rl "fileforge.pro" src cloud-api 2>/dev/null | xargs sed -i 's/fileforge\.pro/fileforge\.converters/g' || true
echo "✓ Updated all fileforge.pro imports (if any)"

# 3. Patch converter registry
REG=\"src/fileforge/converters/__init__.py\"
echo ">>> Ensuring registry includes former pro converters..."

for mod in batch ocr pdf tts; do
    ClassName=\"$(echo ${mod} | awk '{print toupper(substr($0,1,1)) substr($0,2)}')Converter\"
    if ! grep -q "from .${mod} import" \"\$REG\"; then
        sed -i \"/from \\.markup/a from .${mod} import ${ClassName}\" \"\$REG\"
    fi
done

for mod in batch ocr pdf tts; do
    ClassName=\"$(echo ${mod} | awk '{print toupper(substr($0,1,1)) substr($0,2)}')Converter\"
    if ! grep -q "\"${mod}\":" \"\$REG\"; then
        sed -i \"/\\\"markup\\\": MarkupConverter/a\\    \\\"${mod}\\\": ${ClassName},\" \"\$REG\"
    fi
done

echo "✓ Registry updated"

# 4. Update README “What’s in the box”
echo ">>> Updating README.md section..."

# Remove old pro row if present
sed -i '/src\/fileforge\/pro/d' README.md

# Ensure converters row is updated
sed -i 's|\\`src/fileforge/converters/\\`.*|\\`src/fileforge/converters/\\`  | All converters (free + former Pro) | data, config, encoding, markup, batch, ocr, pdf, tts ||' README.md || true

echo "✓ README updated"

echo ""
echo ">>> Merge complete!"
echo "Run: pytest -q"
echo "Then: git add ., git commit, git push."
