"""Manual/paste content ingestion."""

from __future__ import annotations

from pathlib import Path

from ..models import SourceItem, SourceType


def ingest_text(text: str, title: str = "Manual note") -> SourceItem:
    return SourceItem(
        source_type=SourceType.MANUAL,
        title=title,
        content=text,
        excerpt=text[:500],
    )


def ingest_file(path: Path) -> SourceItem:
    text = path.read_text(encoding="utf-8")
    return SourceItem(
        source_type=SourceType.MANUAL,
        title=path.name,
        content=text,
        excerpt=text[:500],
        metadata={"file": str(path)},
    )


def collect_manual(notes_dir: Path | None = None) -> list[SourceItem]:
    if notes_dir is None or not notes_dir.exists():
        return []
    sources: list[SourceItem] = []
    for f in sorted(notes_dir.iterdir()):
        if f.is_file() and f.suffix in (".txt", ".md", ".json"):
            sources.append(ingest_file(f))
    return sources
