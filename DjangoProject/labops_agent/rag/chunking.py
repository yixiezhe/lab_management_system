import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass(frozen=True)
class ParsedSection:
    path: str
    text: str


@dataclass(frozen=True)
class ChunkDraft:
    section_path: str
    content: str
    content_hash: str
    char_count: int
    token_estimate: int


class _TextHTMLParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "li", "tr", "br", "section", "article"}
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.current_heading = ""
        self.heading_parts = []
        self.text_parts = []
        self.sections = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self.hidden_depth += 1
        elif not self.hidden_depth and tag in self.HEADING_TAGS:
            self._flush_section()
            self.heading_parts = []
        elif not self.hidden_depth and tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif not self.hidden_depth and tag in self.HEADING_TAGS:
            self.current_heading = _clean("".join(self.heading_parts))
            self.heading_parts = []
        elif not self.hidden_depth and tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.hidden_depth:
            return
        if self.heading_parts is not None and data.strip() and not self.text_parts:
            self.heading_parts.append(data)
        self.text_parts.append(data)

    def _flush_section(self):
        text = _clean("".join(self.text_parts))
        if text:
            self.sections.append(ParsedSection(self.current_heading, text))
        self.text_parts = []

    def finish(self):
        self._flush_section()
        return self.sections


def _clean(text):
    lines = []
    for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[\t \u3000]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _markdown_sections(text):
    sections = []
    headings = []
    buffer = []

    def flush():
        cleaned = _clean("\n".join(buffer))
        if cleaned:
            sections.append(ParsedSection(" > ".join(headings), cleaned))
        buffer.clear()

    for line in str(text).splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            buffer.append(line)
            continue
        flush()
        level = len(match.group(1))
        headings[:] = headings[: level - 1]
        headings.append(_clean(match.group(2)))
    flush()
    return sections


def parse_document(path):
    source = Path(path)
    if source.suffix.lower() not in {".md", ".markdown", ".txt", ".html", ".htm"}:
        raise ValueError("第一版仅支持 Markdown、TXT 和 HTML 文档。")
    if source.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("知识文档不能超过 5 MB。")
    text = source.read_text(encoding="utf-8-sig", errors="strict")
    if source.suffix.lower() in {".html", ".htm"}:
        parser = _TextHTMLParser()
        parser.feed(text)
        sections = parser.finish()
    elif source.suffix.lower() in {".md", ".markdown"}:
        sections = _markdown_sections(text)
    else:
        sections = [ParsedSection("", _clean(text))]
    return [section for section in sections if section.text]


def _split_text(text, target_chars, overlap_chars):
    if len(text) <= target_chars:
        return [text]
    pieces = re.split(r"(?<=[。！？；.!?;])\s*|\n+", text)
    chunks = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(current) + len(piece) + 1 <= target_chars:
            current = f"{current}\n{piece}".strip()
            continue
        if current:
            chunks.append(current)
        tail = current[-overlap_chars:] if current else ""
        current = f"{tail}\n{piece}".strip()
        while len(current) > target_chars * 2:
            chunks.append(current[:target_chars])
            current = current[target_chars - overlap_chars :]
    if current:
        chunks.append(current)
    return chunks


def build_chunks(sections, target_chars=600, overlap_chars=80):
    chunks = []
    for section in sections:
        for content in _split_text(section.text, target_chars, overlap_chars):
            content = _clean(content)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunks.append(
                ChunkDraft(
                    section_path=section.path,
                    content=content,
                    content_hash=digest,
                    char_count=len(content),
                    token_estimate=max(1, round(len(content) / 1.7)),
                )
            )
    return chunks
