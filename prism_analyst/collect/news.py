"""News/RSS collector using lightweight XML parsing."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from ..config import settings
from ..models import SourceItem, SourceType
from ..workspace import workspace


_RSS_TEMPLATES = [
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
]


def _parse_rss(xml_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            entries.append({
                "title": title,
                "link": link,
                "summary": description,
                "published": pub_date,
            })
    except ET.ParseError:
        pass
    return entries[:15]


def collect_news(company_name: str, domain: str | None = None) -> list[SourceItem]:
    sources: list[SourceItem] = []
    query = company_name
    if domain:
        query = f"{company_name} OR {domain}"

    for template in _RSS_TEMPLATES:
        url = template.format(query=query.replace(" ", "+"))
        cache_key = workspace.cache_key("news", url)
        cached = workspace.get_cache(cache_key)

        if cached:
            entries = cached
        else:
            try:
                with httpx.Client(
                    timeout=settings.http_timeout,
                    follow_redirects=True,
                    headers={"User-Agent": settings.user_agent},
                ) as client:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        continue
                    entries = _parse_rss(resp.text)
                    workspace.set_cache(cache_key, entries)
            except (httpx.HTTPError, Exception):
                continue

        for item in entries:
            content = f"{item['title']}\n{item['summary']}"
            sources.append(
                SourceItem(
                    source_type=SourceType.NEWS,
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    content=content,
                    excerpt=content[:500],
                    metadata={"published": item.get("published", "")},
                )
            )

    return sources
