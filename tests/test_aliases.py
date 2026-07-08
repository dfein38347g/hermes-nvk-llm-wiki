# tests/test_aliases.py
from pathlib import Path
import pytest

from runtime import _generate_alias_skill, ALL_COMMANDS


def test_generate_alias_skill_has_frontmatter():
    meta = {"version": "0.15.0", "commit": "abc123"}
    vendor_md = '---\nargument-hint: "topic"\ndescription: "Deep research with parallel agents"\n---\n\n# research\n\nResearch workflow details.'
    skill = _generate_alias_skill("research", vendor_md, meta)
    assert "---\n" in skill
    assert "name: wiki-research" in skill
    assert "description:" in skill
    assert "nvk/llm-wiki research" in skill


def test_generate_alias_skill_includes_meta():
    meta = {"version": "0.15.0", "commit": "abc123"}
    vendor_md = '---\ndescription: "Test command"\n---\n\n# test\n\nBody.'
    skill = _generate_alias_skill("test", vendor_md, meta)
    assert "0.15.0" in skill
    assert "abc123" in skill


def test_all_24_commands_have_entries():
    """ALL_COMMANDS must contain exactly the 24 upstream commands."""
    expected = {
        "archive",
        "assess",
        "audit",
        "collect",
        "compile",
        "dataset",
        "diff",
        "feedback",
        "ingest",
        "ingest-collection",
        "init",
        "inventory",
        "librarian",
        "lint",
        "ll",
        "output",
        "plan",
        "project",
        "query",
        "refresh",
        "research",
        "retract",
        "session",
        "thesis",
    }
    assert ALL_COMMANDS == expected, f"Missing: {expected - set(ALL_COMMANDS)}"


def test_generate_alias_skill_no_fictional_tools():
    meta = {"version": "0.15.0", "commit": "abc123"}
    vendor_md = '---\ndescription: "Ingest"\n---\n\n# ingest\n\nBody.'
    skill = _generate_alias_skill("ingest", vendor_md, meta)
    assert "defuddle_parse" not in skill
    assert "summarize_extract" not in skill
