"""HTML to Markdown converter.

Converts HTML back to Markdown format for easy editing and portability.
Handles common HTML tags (headings, paragraphs, links, lists, bold/italic).
"""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

from fileforge.core.registry import registry


def _html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown (best-effort, handles common tags)."""
    text = html
    
    # Remove doctype, html, head, body tags
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\/?html[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<head[^>]*>.*?<\/head>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<\/?body[^>]*>", "", text, flags=re.IGNORECASE)
    
    # Headings: <h1>text</h1> -> # text
    for level in range(1, 7):
        pattern = f"<h{level}[^>]*>(.*?)<\/h{level}>"
        replacement = f"{'#' * level} \\1\n"
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.DOTALL)
    
    # Paragraphs: <p>text</p> -> text\n\n
    text = re.sub(r"<p[^>]*>(.*?)<\/p>", r"\1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Line breaks: <br> -> \n
    text = re.sub(r"<br\s*\/?>", "\n", text, flags=re.IGNORECASE)
    
    # Links: <a href="url">text</a> -> [text](url)
    text = re.sub(r'<a\s+href=["\'](.*?)["\'][^>]*>(.*?)<\/a>', r"[\2](\1)", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Bold: <strong>text</strong> or <b>text</b> -> **text**
    text = re.sub(r"<strong[^>]*>(.*?)<\/strong>", r"**\1**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<b[^>]*>(.*?)<\/b>", r"**\1**", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Italic: <em>text</em> or <i>text</i> -> *text*
    text = re.sub(r"<em[^>]*>(.*?)<\/em>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<i[^>]*>(.*?)<\/i>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Code: <code>text</code> -> `text`
    text = re.sub(r"<code[^>]*>(.*?)<\/code>", r"`\1`", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Preformatted: <pre>text</pre> -> ```\ntext\n```
    text = re.sub(r"<pre[^>]*>(.*?)<\/pre>", r"```\n\1\n```", text, flags=re.IGNORECASE | re.DOTALL)
    
    # List items: <li>text</li> -> - text
    text = re.sub(r"<li[^>]*>(.*?)<\/li>", r"- \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    # Clean up whitespace: collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Decode HTML entities
    text = html_lib.unescape(text)
    
    # Final trim
    return text.strip() + "\n"


@registry.add("html", "md", description="HTML document -> Markdown")
def html_to_md(source: Path, target: Path, **_) -> Path:
    html = Path(source).read_text(encoding="utf-8")
    markdown = _html_to_markdown(html)
    Path(target).write_text(markdown, encoding="utf-8")
    return Path(target)
