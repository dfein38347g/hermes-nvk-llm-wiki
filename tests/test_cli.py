"""Tests for the Hermes CLI interface (cli.py)."""

import json
from pathlib import Path
from typing import Any

import pytest

from runtime import ALL_COMMANDS


def _lock_data(tmp_path: Path, **overrides: Any) -> Path:
    """Write a minimal upstream.lock.json in tmp_path."""
    data = {
        "repo": "https://github.com/nvk/llm-wiki",
        "version": "0.15.0",
        "commit": "abc123def456",
    }
    data.update(overrides)
    p = tmp_path / "upstream.lock.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _vendor_dir(tmp_path: Path) -> Path:
    """Create a minimal vendor dir with a wiki.md command file."""
    vendor = tmp_path / "vendor"
    (vendor / "commands").mkdir(parents=True)
    (vendor / "commands" / "wiki.md").write_text(
        "---\ndescription: Wiki\n---\n\nContent.\n"
    )
    (vendor / "commands" / "compile.md").write_text(
        "---\ndescription: Compile\n---\n\nContent.\n"
    )
    return vendor


def _config_file(tmp_path: Path, **overrides: Any) -> Path:
    data = {"skills": {"external_dirs": [], "disabled": []}}
    data.update(overrides)
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# -- Parser structure ------------------------------------------------


def test_parser_builds():
    from cli import build_parser

    parser = build_parser()
    assert parser is not None


def test_parser_has_sync():
    from cli import build_parser

    args = build_parser().parse_args(["sync", "--vendor", "x", "--output", "y"])
    assert args.command == "sync"


def test_parser_has_doctor():
    from cli import build_parser

    args = build_parser().parse_args(
        [
            "doctor",
            "--lock",
            "lock.json",
            "--vendor",
            "vendor",
            "--skill-root",
            "skills",
            "--config",
            "config.json",
        ]
    )
    assert args.command == "doctor"


def test_parser_has_status():
    from cli import build_parser

    args = build_parser().parse_args(
        [
            "status",
            "--lock",
            "lock.json",
            "--skill-root",
            "skills",
            "--config",
            "config.json",
        ]
    )
    assert args.command == "status"


def test_parser_has_activate():
    from cli import build_parser

    args = build_parser().parse_args(
        ["activate", "--config", "config.json", "--managed-root", "root"]
    )
    assert args.command == "activate"


def test_parser_has_wiki():
    from cli import build_parser

    args = build_parser().parse_args(["wiki", "compile"])
    assert args.command == "wiki"
    assert args.wiki_action == "compile"


def test_parser_wiki_accepts_all_commands():
    from cli import build_parser

    for cmd in sorted(ALL_COMMANDS):
        args = build_parser().parse_args(["wiki", cmd])
        assert args.wiki_action == cmd, f"wiki-{cmd} parsing failed"
        assert args.command == "wiki"


def test_parser_wiki_rejects_invalid_command():
    from cli import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(["wiki", "invalid-command"])


# -- main() integration ----------------------------------------------


def test_main_no_command(capsys):
    from cli import main

    code = main([])
    assert code == 1


def test_main_wiki_no_action(capsys):
    from cli import main

    code = main(["wiki"])
    assert code == 1


def test_main_wiki_routes_command(capsys):
    from cli import main

    code = main(["wiki", "compile", "--some-arg"])
    assert code == 0
    out = capsys.readouterr().out
    assert "wiki-compile" in out
    assert "--some-arg" in out


def test_main_wiki_compile_no_extra_args(capsys):
    from cli import main

    code = main(["wiki", "compile"])
    assert code == 0
    out = capsys.readouterr().out
    assert "wiki-compile" in out


def test_main_sync_creates_bundle(tmp_path, capsys):
    from cli import main

    vendor = _vendor_dir(tmp_path)
    out = tmp_path / "out"
    lock = _lock_data(tmp_path)

    code = main(
        ["sync", "--vendor", str(vendor), "--output", str(out), "--lock", str(lock)]
    )
    assert code == 0
    assert (out / "research" / "wiki" / "SKILL.md").exists()

    parsed = json.loads(capsys.readouterr().out)
    assert parsed["version"] == "0.15.0"


def test_main_doctor_reports_unhealthy(tmp_path, capsys):
    from cli import main

    cfg = _config_file(tmp_path)
    code = main(
        [
            "doctor",
            "--lock",
            str(tmp_path / "nonexistent.json"),
            "--vendor",
            str(tmp_path / "nonexistent"),
            "--skill-root",
            str(tmp_path / "nonexistent"),
            "--config",
            str(cfg),
        ]
    )
    assert code == 1
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["healthy"] is False
    assert len(parsed["checks"]) > 0


def test_main_status_returns_dict(tmp_path, capsys):
    from cli import main

    cfg = _config_file(tmp_path)
    lock = _lock_data(tmp_path)

    code = main(
        [
            "status",
            "--lock",
            str(lock),
            "--skill-root",
            str(tmp_path / "skills"),
            "--config",
            str(cfg),
        ]
    )
    assert code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["upstream_version"] == "0.15.0"
    assert parsed["skill_installed"] is False


def test_main_activate_updates_config(tmp_path, capsys):
    from cli import main

    cfg = _config_file(tmp_path)
    managed = tmp_path / "managed"

    code = main(["activate", "--config", str(cfg), "--managed-root", str(managed)])
    assert code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["success"] is True
    assert parsed["config_updated"] is True

    config = json.loads(cfg.read_text(encoding="utf-8"))
    assert str(managed) in config["skills"]["external_dirs"]


def test_main_activate_idempotent(tmp_path, capsys):
    from cli import main

    managed = tmp_path / "managed"
    cfg = _config_file(
        tmp_path,
        skills={"external_dirs": [str(managed)], "disabled": ["llm-wiki"]},
    )

    code = main(["activate", "--config", str(cfg), "--managed-root", str(managed)])
    assert code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["config_updated"] is False
