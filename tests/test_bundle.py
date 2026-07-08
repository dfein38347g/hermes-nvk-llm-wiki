"""Tests for root skill generation and bundle sync."""

import json
from pathlib import Path
from runtime import sync_managed_skill_bundle, _generate_root_skill

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_generate_root_skill_has_frontmatter():
    meta = {"version": "0.15.0", "commit": "abc123"}
    vendor_md = '---\ndescription: "Wiki router"\n---\n\n# wiki\n\nRouter content.'
    skill = _generate_root_skill(vendor_md, meta)
    assert "name: wiki" in skill
    assert "nvk/llm-wiki" in skill
    assert ".hub/commands/" in skill


def test_sync_bundle_creates_root(tmp_workdir):
    vendor = FIXTURES / "golden-vendor"
    out = tmp_workdir / "managed-skills"
    meta = {"version": "0.15.0", "commit": "abc123"}
    commands = {"research"}
    result = sync_managed_skill_bundle(
        vendor_dir=str(vendor),
        output_dir=str(out),
        commands=commands,
        meta=meta,
    )
    assert (out / "research" / "wiki" / "SKILL.md").exists()
    assert (
        out
        / "research"
        / "wiki"
        / ".hub"
        / "skills"
        / "wiki-manager"
        / "references"
        / "README.md"
    ).exists()
    assert result["version"] == "0.15.0"


def test_sync_bundle_creates_alias_skills(tmp_workdir):
    vendor = FIXTURES / "golden-vendor"
    out = tmp_workdir / "managed-skills"
    meta = {"version": "0.15.0", "commit": "abc123"}
    commands = {"research"}
    sync_managed_skill_bundle(
        vendor_dir=str(vendor),
        output_dir=str(out),
        commands=commands,
        meta=meta,
    )
    alias_dir = out / "research" / "wiki-research"
    assert alias_dir.exists()
    assert (alias_dir / "SKILL.md").exists()


def test_sync_bundle_writes_nvk_upstream_json(tmp_workdir):
    vendor = FIXTURES / "golden-vendor"
    out = tmp_workdir / "managed-skills"
    meta = {"version": "0.15.0", "commit": "abc123"}
    commands = {"research"}
    sync_managed_skill_bundle(
        vendor_dir=str(vendor),
        output_dir=str(out),
        commands=commands,
        meta=meta,
    )
    meta_file = out / "research" / "wiki" / ".nvk-upstream.json"
    assert meta_file.exists()
    data = json.loads(meta_file.read_text(encoding="utf-8"))
    assert data["version"] == "0.15.0"
