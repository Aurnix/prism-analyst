"""Job posting collector."""

from __future__ import annotations

from ..config import settings
from ..models import SourceItem, SourceType
from ..workspace import workspace
from .website import fetch_page, _extract_text


_CAREERS_PATHS = [
    "/careers",
    "/jobs",
    "/careers/",
    "/jobs/",
    "/about/careers",
    "/company/careers",
    "/join",
    "/join-us",
    "/work-with-us",
]


def collect_jobs(domain: str) -> list[SourceItem]:
    sources: list[SourceItem] = []

    for path in _CAREERS_PATHS:
        url = f"https://{domain}{path}"
        cache_key = workspace.cache_key("jobs", url)
        cached = workspace.get_cache(cache_key)

        if cached:
            text = cached
        else:
            html, _ = fetch_page(url)
            if not html or len(html) < 200:
                continue
            text = _extract_text(html)
            if len(text) < 100:
                continue
            workspace.set_cache(cache_key, text)

        sources.append(
            SourceItem(
                source_type=SourceType.JOBS,
                url=url,
                title=f"Careers page — {domain}",
                content=text,
                excerpt=text[:500],
            )
        )
        break  # stop after first successful careers page

    return sources
