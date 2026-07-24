"""HTML and Markdown converters.

Converts HTML back to Markdown format for easy editing and portability.
Handles common HTML tags (headings, paragraphs, links, lists, bold/italic).
Also handles Markdown -> text and other markup transformations.
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
    text = re.sub(r'<a\s+href=["\']([\w\W]*?)["\'][^>]*>([\w\W]*?)<\/a>', r"[\2](\1)", text, flags=re.IGNORECASE | re.DOTALL)
    
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


def _markdown_to_text(md: str) -> str:
    """Strip Markdown syntax to plain text."""
    text = md
    
    # Remove code blocks: ```...```
    text = re.sub(r"```[\s\S]*?```", "", text)
    
    # Remove inline code: `code` -> code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    
    # Remove bold: **text** or __text__ -> text
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    
    # Remove italic: *text* or _text_ -> text
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    
    # Remove links: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    
    # Remove headings: # heading -> heading
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    
    # Remove list markers: - item or * item or + item -> item
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    
    # Remove numbered lists: 1. item -> item
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    
    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip() + "\n"


@registry.add("html", "md", description="HTML document -> Markdown")
def html_to_md(source: Path, target: Path, **_) -> Path:
    html = Path(source).read_text(encoding="utf-8")
    markdown = _html_to_markdown(html)
    Path(target).write_text(markdown, encoding="utf-8")
    return Path(target)


@registry.add("md", "txt", description="Markdown -> plain text (strip syntax)")
def md_to_txt(source: Path, target: Path, **_) -> Path:
    md = Path(source).read_text(encoding="utf-8")
    text = _markdown_to_text(md)
    Path(target).write_text(text, encoding="utf-8")
    return Path(target)


@registry.add("markdown", "txt", description="Markdown -> plain text (strip syntax)")
def markdown_to_txt(source: Path, target: Path, **_) -> Path:
    return md_to_txt(source, target)
