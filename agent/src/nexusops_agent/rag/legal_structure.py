from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


SectionType = Literal[
    "PREAMBLE",
    "ARTICLE",
    "ARTICLE_INTRO",
    "CLAUSE",
    "CLAUSE_INTRO",
    "POINT",
    "APPENDIX",
]


@dataclass(frozen=True)
class SourcePage:
    page_or_part: int
    text: str


class StructuralChunk(BaseModel):
    section_type: SectionType
    article: str | None = None
    article_title: str | None = None
    clause: str | None = None
    point: str | None = None
    part: str | None = None
    chapter: str | None = None
    section: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    page_from: int
    page_to: int
    source_text: str
    content: str
    warnings: list[str] = Field(default_factory=list)


@dataclass
class _Node:
    kind: Literal["PREAMBLE", "ARTICLE", "CLAUSE", "POINT"]
    label: str | None
    title: str | None
    heading: str | None
    part: str | None
    chapter: str | None
    section: str | None
    article: "_Node | None" = None
    clause: "_Node | None" = None
    lines: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    children: list["_Node"] = field(default_factory=list)

    def append(self, line: str, page: int) -> None:
        self.lines.append(line)
        self.pages.append(page)


PART_RE = re.compile(r"^\s*(PHẦN\s+(?:THỨ\s+)?[A-ZÀ-Ỹ0-9IVXLCDM]+)\s*[.:]?\s*(.*)$", re.IGNORECASE)
CHAPTER_RE = re.compile(r"^\s*(CHƯƠNG\s+[A-ZÀ-Ỹ0-9IVXLCDM]+)\s*[.:]?\s*(.*)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^\s*(MỤC\s+\d+[A-ZÀ-Ỹ]?)\s*[.:]?\s*(.*)$", re.IGNORECASE)
ARTICLE_RE = re.compile(r"^\s*(Điều\s+\d+[A-Za-zÀ-ỹĐđ]?)\s*[.:]?\s*(.*)$", re.IGNORECASE)
CLAUSE_RE = re.compile(r"^\s*(\d{1,3})[.](?:\s+(.*))?$")
POINT_RE = re.compile(r"^\s*([A-Za-zÀ-ỹĐđ])\s*[)]\s*(.*)$")
APPENDIX_RE = re.compile(r"^\s*(PHỤ\s+LỤC(?:\s+[A-ZÀ-Ỹ0-9IVXLCDM]+)?)\b\s*(.*)$", re.IGNORECASE)


def _clean_lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]
    compact: list[str] = []
    for line in lines:
        if line or (compact and compact[-1]):
            compact.append(line)
    while compact and not compact[-1]:
        compact.pop()
    return compact


def _heading(label: str, title: str) -> str:
    return f"{label}. {title}".rstrip(". ") if title else label


class LegalStructureParser:
    """Stateful Vietnamese legal parser that preserves atomic clauses and points."""

    def parse_pages(self, pages: list[SourcePage]) -> list[StructuralChunk]:
        roots: list[_Node] = []
        preamble = _Node("PREAMBLE", None, None, None, None, None, None)
        roots.append(preamble)
        active: _Node = preamble
        article: _Node | None = None
        clause: _Node | None = None
        part: str | None = None
        chapter: str | None = None
        section: str | None = None
        appendix_mode = False

        for page in sorted(pages, key=lambda item: item.page_or_part):
            for line in _clean_lines(page.text):
                if not line:
                    if active.lines and active.lines[-1]:
                        active.append("", page.page_or_part)
                    continue

                match = APPENDIX_RE.match(line)
                if match:
                    appendix_mode = True
                    article = None
                    clause = None
                    appendix = _Node(
                        "ARTICLE", match.group(1), match.group(2).strip() or None, line,
                        part, chapter, section,
                    )
                    roots.append(appendix)
                    active = appendix
                    continue

                match = PART_RE.match(line)
                if match and not appendix_mode:
                    part = _heading(match.group(1), match.group(2).strip())
                    chapter = None
                    section = None
                    continue

                match = CHAPTER_RE.match(line)
                if match and not appendix_mode:
                    chapter = _heading(match.group(1), match.group(2).strip())
                    section = None
                    continue

                match = SECTION_RE.match(line)
                if match and not appendix_mode:
                    section = _heading(match.group(1), match.group(2).strip())
                    continue

                match = ARTICLE_RE.match(line)
                if match and not appendix_mode:
                    article = _Node(
                        "ARTICLE", match.group(1), match.group(2).strip() or None, line,
                        part, chapter, section,
                    )
                    roots.append(article)
                    clause = None
                    active = article
                    continue

                match = CLAUSE_RE.match(line)
                if match and article is not None and not appendix_mode:
                    clause = _Node(
                        "CLAUSE", match.group(1), None, f"{match.group(1)}.",
                        part, chapter, section, article=article,
                    )
                    clause.append(line, page.page_or_part)
                    article.children.append(clause)
                    active = clause
                    continue

                match = POINT_RE.match(line)
                if match and article is not None and not appendix_mode:
                    point = _Node(
                        "POINT", match.group(1).casefold(), None, f"{match.group(1).casefold()})",
                        part, chapter, section, article=article, clause=clause,
                    )
                    point.append(line, page.page_or_part)
                    (clause or article).children.append(point)
                    active = point
                    continue

                active.append(line, page.page_or_part)

        return self._flatten(roots)

    def _flatten(self, roots: list[_Node]) -> list[StructuralChunk]:
        chunks: list[StructuralChunk] = []
        for node in roots:
            if node.kind == "PREAMBLE":
                self._append_chunk(chunks, node, "PREAMBLE")
                continue
            if node.label and node.label.upper().startswith("PHỤ LỤC"):
                self._append_chunk(chunks, node, "APPENDIX", include_descendants=True)
                continue
            if not node.children:
                self._append_chunk(chunks, node, "ARTICLE")
                continue
            self._append_chunk(chunks, node, "ARTICLE_INTRO")
            for child in node.children:
                if child.kind == "POINT":
                    self._append_chunk(chunks, child, "POINT")
                    continue
                if not child.children:
                    self._append_chunk(chunks, child, "CLAUSE")
                    continue
                self._append_chunk(chunks, child, "CLAUSE_INTRO")
                for point in child.children:
                    self._append_chunk(chunks, point, "POINT")
        return chunks

    def _append_chunk(
        self,
        output: list[StructuralChunk],
        node: _Node,
        section_type: SectionType,
        *,
        include_descendants: bool = False,
    ) -> None:
        nodes = [node]
        if include_descendants:
            cursor = 0
            while cursor < len(nodes):
                nodes.extend(nodes[cursor].children)
                cursor += 1
        source_lines = [line for item in nodes for line in item.lines]
        pages = [page for item in nodes for page in item.pages]
        source_text = "\n".join(source_lines).strip()
        if not source_text:
            return

        is_appendix = section_type == "APPENDIX"
        article = None if is_appendix else node if node.kind == "ARTICLE" else node.article
        clause = node if node.kind == "CLAUSE" else node.clause
        structural_headings = [value for value in [node.part, node.chapter, node.section] if value]
        heading_path = list(structural_headings)
        if is_appendix and node.heading:
            heading_path.append(node.heading)
        if article and article.heading:
            heading_path.append(article.heading)
        if clause:
            heading_path.append(f"Khoản {clause.label}")
        if node.kind == "POINT":
            heading_path.append(f"Điểm {node.label}")

        content_context = list(structural_headings)
        if is_appendix and node.heading:
            content_context.append(node.heading)
        if article and article.heading:
            content_context.append(article.heading)
        if node.kind == "POINT" and clause:
            clause_intro = "\n".join(clause.lines).strip()
            if clause_intro:
                content_context.append(clause_intro)
        elif node.kind == "POINT" and article:
            article_intro = "\n".join(article.lines).strip()
            if article_intro:
                content_context.append(article_intro)
        content_parts = [*content_context, source_text]
        warnings = ["OVERSIZED_ATOMIC_UNIT"] if len(source_text) > 6000 else []
        output.append(
            StructuralChunk(
                section_type=section_type,
                article=article.label if article else None,
                article_title=article.title if article else None,
                clause=clause.label if clause else None,
                point=node.label if node.kind == "POINT" else None,
                part=node.part,
                chapter=node.chapter,
                section=node.section,
                heading_path=heading_path,
                page_from=min(pages),
                page_to=max(pages),
                source_text=source_text,
                content="\n".join(content_parts),
                warnings=warnings,
            )
        )
