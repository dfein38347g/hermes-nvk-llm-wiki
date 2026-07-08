"""Integration tests for end-to-end bundle sync, doctor, and content quality."""

import json
from pathlib import Path

import pytest

from runtime import (
    ALL_COMMANDS,
    _generate_alias_skill,
    _generate_root_skill,
    run_doctor,
    sync_managed_skill_bundle,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# ── Full sync cycle ─────────────────────────────────────────────


def test_full_sync_cycle(tmp_workdir):
    """Sync all 24 commands and verify the complete bundle structure."""
    vendor = FIXTURES / "golden-vendor"
    out = tmp_workdir / "managed-skills"
    meta = {"version": "0.15.0", "commit": "abc123def456"}

    result = sync_managed_skill_bundle(
        vendor_dir=str(vendor),
        output_dir=str(out),
        commands=ALL_COMMANDS,
        meta=meta,
    )

    # Root skill
    root = out / "research" / "wiki"
    assert root.exists()
    assert (root / "SKILL.md").exists()
    assert (root / ".nvk-upstream.json").exists()
    assert result["version"] == "0.15.0"

    # All 24 alias skills
    for cmd in sorted(ALL_COMMANDS):
        alias_dir = out / "research" / f"wiki-{cmd}"
        assert alias_dir.exists(), f"Missing alias dir: {alias_dir}"
        assert (alias_dir / "SKILL.md").exists(), f"Missing SKILL.md for {cmd}"


def test_all_alias_skills_have_correct_frontmatter(tmp_workdir):
    """Every generated alias skill has the expected frontmatter fields."""
    vendor = FIXTURES / "golden-vendor"
    out = tmp_workdir / "managed-skills"
    meta = {"version": "0.15.0", "commit": "abc123"}

    sync_managed_skill_bundle(
        vendor_dir=str(vendor),
        output_dir=str(out),
        commands=ALL_COMMANDS,
        meta=meta,
    )

    for cmd in sorted(ALL_COMMANDS):
        skill_md = out / "research" / f"wiki-{cmd}" / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{cmd} SKILL.md missing frontmatter"
        assert f"name: wiki-{cmd}" in text, f"{cmd} SKILL.md missing name"
        assert "This skill is managed" in text, f"{cmd} missing managed marker"


# ── Doctor tests ────────────────────────────────────────────────


def test_doctor_healthy_after_full_sync(tmp_workdir, upstream_lock):
    """Run doctor after a full sync — should report healthy."""
    vendor = FIXTURES / "golden-vendor"
    managed_root = tmp_workdir / "managed-skills"
    meta = {"version": "0.15.0", "commit": "abc123"}

    sync_managed_skill_bundle(
        vendor_dir=str(vendor),
        output_dir=str(managed_root),
        commands=ALL_COMMANDS,
        meta=meta,
    )

    lock_path = tmp_workdir / "upstream.lock.json"
    lock_path.write_text(json.dumps(upstream_lock) + "\n", encoding="utf-8")

    skill_root = managed_root / "research" / "wiki"
    config = {
        "skills": {
            "external_dirs": [str(managed_root)],
            "disabled": ["llm-wiki"],
        }
    }

    result = run_doctor(
        lock_path=str(lock_path),
        vendor_dir=str(vendor),
        skill_root=str(skill_root),
        config=config,
    )

    assert result["healthy"] is True, (
        f"Doctor not healthy: {[c for c in result['checks'] if not c['ok']]}"
    )


def test_doctor_unhealthy_when_missing_sync(tmp_path):
    """Doctor returns healthy=False before sync has run."""
    result = run_doctor(
        lock_path=str(tmp_path / "upstream.lock.json"),
        vendor_dir=str(tmp_path / "vendor"),
        skill_root=str(tmp_path / "managed-skills" / "research" / "wiki"),
        config={},
    )
    assert result["healthy"] is False


# ── Anti-fictional-tools checks ─────────────────────────────────


def test_no_fictional_tools_in_any_alias_skill():
    """No generated alias skill contains defuddle_parse or summarize_extract."""
    meta = {"version": "0.15.0", "commit": "abc123"}

    for cmd in sorted(ALL_COMMANDS):
        vendor_md = f'---\ndescription: "{cmd}"\n---\n\n# {cmd}\n\nBody.'
        skill = _generate_alias_skill(cmd, vendor_md, meta)
        assert "defuddle_parse" not in skill, f"{cmd} contains defuddle_parse"
        assert "summarize_extract" not in skill, f"{cmd} contains summarize_extract"


def test_no_fictional_tools_in_root_skill():
    """Root wiki skill does not contain fictional tool references."""
    meta = {"version": "0.15.0", "commit": "abc123"}
    vendor_md = '---\ndescription: "Wiki router"\n---\n\n# wiki\n\nRouter content.'
    skill = _generate_root_skill(vendor_md, meta)
    assert "defuddle_parse" not in skill
    assert "summarize_extract" not in skill
