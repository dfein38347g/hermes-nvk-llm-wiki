# tests/test_adaptation.py
from runtime import _adapt_router_markdown, _adapt_command_markdown


def test_adapt_router_replaces_reference_paths():
    md = "See skills/wiki-manager/references/indexing.md for details."
    result = _adapt_router_markdown(md)
    assert result == "See .hub/skills/wiki-manager/references/indexing.md for details."


def test_adapt_router_replaces_slash_commands():
    md = "Use `Skill: wiki:research` for investigations."
    result = _adapt_router_markdown(md)
    assert "Skill: wiki:" not in result
    assert ".hub/commands/research.md" in result


def test_adapt_command_replaces_refs():
    md = "See `references/indexing.md` for details."
    result = _adapt_command_markdown(md)
    assert "../wiki/.hub/skills/wiki-manager/references/" in result


def test_adapt_command_replaces_slash_commands():
    md = "Use `/wiki:research` to start."
    result = _adapt_command_markdown(md)
    assert "/wiki-research" in result or "/wiki-" in result
