"""GitHub activity collector."""

from __future__ import annotations

import httpx

from ..config import settings
from ..models import SourceItem, SourceType
from ..workspace import workspace


def _guess_org(domain: str) -> str:
    return domain.split(".")[0]


def collect_github(domain: str, org_name: str | None = None) -> list[SourceItem]:
    org = org_name or _guess_org(domain)
    sources: list[SourceItem] = []

    cache_key = workspace.cache_key("github_repos", org)
    cached = workspace.get_cache(cache_key)

    if cached:
        repos = cached
    else:
        url = f"https://api.github.com/orgs/{org}/repos?sort=updated&per_page=10"
        try:
            with httpx.Client(
                timeout=settings.http_timeout,
                headers={"User-Agent": settings.user_agent},
            ) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return sources
                repos = resp.json()
                workspace.set_cache(cache_key, repos)
        except (httpx.HTTPError, ValueError):
            return sources

    for repo in repos[:10]:
        name = repo.get("name", "")
        desc = repo.get("description", "") or ""
        lang = repo.get("language", "") or ""
        stars = repo.get("stargazers_count", 0)
        updated = repo.get("updated_at", "")
        html_url = repo.get("html_url", "")
        topics = repo.get("topics", [])

        content = f"Repository: {name}\nDescription: {desc}\nLanguage: {lang}\nStars: {stars}\nTopics: {', '.join(topics)}\nLast updated: {updated}"
        sources.append(
            SourceItem(
                source_type=SourceType.GITHUB,
                url=html_url,
                title=f"GitHub: {org}/{name}",
                content=content,
                excerpt=content[:500],
                metadata={
                    "stars": stars,
                    "language": lang,
                    "updated_at": updated,
                    "topics": topics,
                },
            )
        )

    return sources
