# FileForge Architecture Overview

## Converters
- data: JSON, CSV, TSV, YAML, XML
- config: INI, TOML, YAML normalization
- encoding: UTF-8, UTF-16, Latin-1 transforms
- markup: HTML, XML, Markdown

## Cloud API
- FastAPI service exposing unified converter interface
- Metering hooks for Enterprise licensing

## CLI
- Unified command registry
- Pipeline chaining
- Format autodetection
