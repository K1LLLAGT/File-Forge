"""Text/markup converters: Markdown -> HTML, HTML -> plain text.

The Markdown route uses the ``markdown`` package when available and falls
back to a compact built-in renderer that covers headings, bold/italic,
inline code, links, and paragraphs so the free tier works with zero deps.
"""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

from fileforge.core.registry import registry

_HTML_DOC = "<!doctype html>\n<html>\n<head><meta charset=\"utf-8\"></head>\n<body>\n{body}\n</body>\n</html>\n"


def _mini_markdown(text: str) -> str:
    lines = text.splitlines()
    out, para = [], []

    def flush() -> None:
        if para:
            out.append("<p>" + " ".join(para).strip() + "</p>")
            para.clear()

    for line in lines:
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if not stripped:
            flush()
        elif heading:
            flush()
            level = len(heading.group(1))
            out.append(f"<h{level}>{heading.group(2).strip()}</h{level}>")
        else:
            para.append(stripped)
    flush()
    body = "\n".join(out)
    # inline formatting
    body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", body)
    body = re.sub(r"`(.+?)`", r"<code>\1</code>", body)
    body = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', body)
    return body


@registry.add("md", "html", description="Markdown -> HTML document")
def md_to_html(source: Path, target: Path, **_) -> Path:
    text = Path(source).read_text(encoding="utf-8")
    try:
        import markdown  # optional dependency

        body = markdown.markdown(text, extensions=["extra", "sane_lists"])
    except ImportError:
        body = _mini_markdown(text)
    Path(target).write_text(_HTML_DOC.format(body=body), encoding="utf-8")
    return Path(target)


@registry.add("markdown", "html", description="Markdown -> HTML document")
def markdown_to_html(source: Path, target: Path, **_) -> Path:
    return md_to_html(source, target)


@registry.add("html", "txt", description="HTML -> plain text (tags stripped)")
def html_to_txt(source: Path, target: Path, **_) -> Path:
    raw = Path(source).read_text(encoding="utf-8")
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|h[1-6]|li)>", "\n", raw)
    text = re.sub(r"(?s)<[^>]+>", "", raw)
    text = html_lib.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    Path(target).write_text(text, encoding="utf-8")
    return Path(target)
