#!/bin/bash
set -e

REG="src/fileforge/converters/__init__.py"

echo ">>> Updating converter registry in $REG..."

for mod in data config encoding markup batch ocr pdf tts; do
    ClassName="$(echo ${mod} | awk '{print toupper(substr($0,1,1)) substr($0,2)}')Converter"
    if ! grep -q "from .${mod} import" "$REG"; then
        sed -i "/__all__/i from .${mod} import ${ClassName}" "$REG"
    fi
done

for mod in data config encoding markup batch ocr pdf tts; do
    ClassName="$(echo ${mod} | awk '{print toupper(substr($0,1,1)) substr($0,2)}')Converter"
    if ! grep -q "\"${mod}\":" "$REG"; then
        sed -i "/AVAILABLE = {/a\    \"${mod}\": ${ClassName}," "$REG"
    fi
done

echo "✓ Registry now includes: data, config, encoding, markup, batch, ocr, pdf, tts"
