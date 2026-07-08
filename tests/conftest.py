"""Shared fixtures for hermes-nvk-llm-wiki tests."""

from pathlib import Path
import pytest

PLUGIN_DIR = Path(__file__).resolve().parent.parent
FIXTURES = PLUGIN_DIR / "tests" / "fixtures"


@pytest.fixture
def plugin_dir() -> Path:
    return PLUGIN_DIR


@pytest.fixture
def tmp_workdir(tmp_path: Path) -> Path:
    """A clean temp directory for sync/bundle tests."""
    return tmp_path


@pytest.fixture
def upstream_lock() -> dict:
    import json

    return json.loads((PLUGIN_DIR / "upstream.lock.json").read_text(encoding="utf-8"))
