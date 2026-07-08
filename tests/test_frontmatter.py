# tests/test_frontmatter.py
from pathlib import Path
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Import will fail until runtime.py exists
from runtime import load_upstream_metadata, _strip_frontmatter


def test_load_upstream_metadata_returns_dict(plugin_dir):
    meta = load_upstream_metadata(str(plugin_dir / "upstream.lock.json"))
    assert isinstance(meta, dict)
    assert "repo" in meta
    assert "version" in meta
    assert "source_paths" in meta


def test_strip_frontmatter_parses_yaml():
    md = """---
name: test-skill
description: "A test"
---

# Body
"""
    meta, body = _strip_frontmatter(md)
    assert meta["name"] == "test-skill"
    assert meta["description"] == "A test"
    assert "# Body" in body


def test_strip_frontmatter_no_frontmatter():
    md = "# Just a heading\n\nSome text"
    meta, body = _strip_frontmatter(md)
    assert meta == {}
    assert body == md


def test_strip_frontmatter_empty_frontmatter():
    md = """---
---

# Body after empty frontmatter"""
    meta, body = _strip_frontmatter(md)
    assert meta == {}
    assert "# Body after empty frontmatter" in body
