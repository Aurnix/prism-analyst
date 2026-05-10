"""Tests for workspace and cache."""

import json
from pathlib import Path

from prism_analyst.workspace import Workspace


def test_workspace_account_dir(tmp_path: Path):
    ws = Workspace(base=tmp_path / ".prism")
    d = ws.account_dir("test-co")
    assert d.exists()
    assert "test-co" in str(d)


def test_workspace_cache_roundtrip(tmp_path: Path):
    ws = Workspace(base=tmp_path / ".prism")
    key = ws.cache_key("test", "data")
    ws.set_cache(key, {"hello": "world"})
    result = ws.get_cache(key)
    assert result == {"hello": "world"}


def test_workspace_cache_miss(tmp_path: Path):
    ws = Workspace(base=tmp_path / ".prism")
    result = ws.get_cache("nonexistent")
    assert result is None


def test_workspace_json_roundtrip(tmp_path: Path):
    ws = Workspace(base=tmp_path / ".prism")
    path = tmp_path / "test.json"
    ws.write_json(path, {"key": "value"})
    result = ws.read_json(path)
    assert result == {"key": "value"}


def test_workspace_text_roundtrip(tmp_path: Path):
    ws = Workspace(base=tmp_path / ".prism")
    path = tmp_path / "test.md"
    ws.write_text(path, "# Hello")
    result = ws.read_text(path)
    assert result == "# Hello"
