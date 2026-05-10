"""Filesystem workspace and cache management."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import settings


def _slug(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace(".", "-")
        .replace(",", "")
        .replace("'", "")
        .strip("-")
    )


class Workspace:
    def __init__(self, base: Path | None = None) -> None:
        self.base = base or settings.workspace_dir
        self.output = settings.output_dir
        self.base.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)

    # ---- account dirs ----

    def account_dir(self, slug: str) -> Path:
        d = self.base / "accounts" / slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    def run_dir(self, slug: str, run_id: str | None = None) -> Path:
        if run_id is None:
            run_id = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        d = self.account_dir(slug) / "runs" / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def latest_run_dir(self, slug: str) -> Path | None:
        runs = self.account_dir(slug) / "runs"
        if not runs.exists():
            return None
        dirs = sorted(runs.iterdir())
        return dirs[-1] if dirs else None

    def previous_run_dir(self, slug: str) -> Path | None:
        runs = self.account_dir(slug) / "runs"
        if not runs.exists():
            return None
        dirs = sorted(runs.iterdir())
        return dirs[-2] if len(dirs) >= 2 else None

    # ---- output dirs ----

    def output_account_dir(self, slug: str) -> Path:
        d = self.output / "accounts" / slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- JSON read/write ----

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read_text(self, path: Path) -> str | None:
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    # ---- cache ----

    def cache_dir(self) -> Path:
        d = self.base / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def cache_key(self, *parts: str) -> str:
        raw = ":".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def cache_path(self, key: str) -> Path:
        return self.cache_dir() / f"{key}.json"

    def get_cache(self, key: str) -> Any:
        path = self.cache_path(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
        if datetime.utcnow() - cached_at > timedelta(days=settings.cache_ttl_days):
            return None
        return data.get("value")

    def set_cache(self, key: str, value: Any) -> None:
        path = self.cache_path(key)
        payload = {
            "_cached_at": datetime.utcnow().isoformat(),
            "value": value,
        }
        self.write_json(path, payload)


workspace = Workspace()
