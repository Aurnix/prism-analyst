"""Website content collector."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
import tldextract
from bs4 import BeautifulSoup

from ..config import settings
from ..models import SourceItem, SourceType
from ..workspace import workspace


def normalize_domain(input_str: str) -> str:
    input_str = input_str.strip().lower()
    if not input_str.startswith(("http://", "https://")):
        if "/" in input_str or "." in input_str:
            input_str = "https://" + input_str
        else:
            return input_str
    ext = tldextract.extract(input_str)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    parsed = urlparse(input_str)
    return parsed.netloc or input_str


def resolve_url(domain: str) -> str:
    return f"https://{domain}"


def _extract_text(html: str, max_len: int = 8000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)[:max_len]


def _extract_meta(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    meta: dict[str, str] = {}
    title_tag = soup.find("title")
    if title_tag:
        meta["title"] = title_tag.get_text(strip=True)
    for tag in soup.find_all("meta"):
        name = tag.get("name", "") or tag.get("property", "")
        content = tag.get("content", "")
        if name and content:
            meta[str(name).lower()] = str(content)[:500]
    return meta


def _find_subpages(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    keywords = ["about", "product", "pricing", "blog", "careers", "jobs", "team", "customers", "case-stud"]
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).lower()
        for kw in keywords:
            if kw in href:
                full = urljoin(base_url, str(a["href"]))
                if full not in found:
                    found.append(full)
                break
    return found[:10]


def fetch_page(url: str) -> tuple[str, int]:
    cache_key = workspace.cache_key("page", url)
    cached = workspace.get_cache(cache_key)
    if cached:
        return cached, 0

    try:
        with httpx.Client(
            timeout=settings.http_timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
            workspace.set_cache(cache_key, html)
            return html, 1
    except (httpx.HTTPError, httpx.InvalidURL):
        return "", 0


def collect_website(domain: str) -> list[SourceItem]:
    sources: list[SourceItem] = []
    base_url = resolve_url(domain)

    html, _ = fetch_page(base_url)
    if not html:
        return sources

    meta = _extract_meta(html)
    text = _extract_text(html)

    sources.append(
        SourceItem(
            source_type=SourceType.WEBSITE,
            url=base_url,
            title=meta.get("title", domain),
            content=text,
            excerpt=text[:500],
            metadata=meta,
        )
    )

    subpages = _find_subpages(html, base_url)
    for page_url in subpages[:5]:
        page_html, _ = fetch_page(page_url)
        if not page_html:
            continue
        page_meta = _extract_meta(page_html)
        page_text = _extract_text(page_html)
        if len(page_text) < 50:
            continue
        sources.append(
            SourceItem(
                source_type=SourceType.WEBSITE,
                url=page_url,
                title=page_meta.get("title", page_url),
                content=page_text,
                excerpt=page_text[:500],
                metadata=page_meta,
            )
        )

    return sources
