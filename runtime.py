"""Runtime helpers for the nvk/llm-wiki Hermes adapter."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List


def load_upstream_metadata(lock_path: str | Path) -> Dict[str, Any]:
    """Read upstream.lock.json and return parsed dict."""
    return json.loads(Path(lock_path).read_text(encoding="utf-8"))


def _strip_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    """Separate YAML frontmatter (---delimited) from markdown body."""
    if not markdown.startswith("---"):
        return {}, markdown

    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return {}, markdown

    _, frontmatter_block, body = parts
    metadata: dict[str, str] = {}
    for line in frontmatter_block.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, body.lstrip()


def _adapt_router_markdown(markdown: str) -> str:
    """Adapt Claude Code router SKILL.md paths to Hermes managed-skill layout."""
    markdown = markdown.replace("skills/wiki-manager/", ".hub/skills/wiki-manager/")
    markdown = markdown.replace("`references/", "`.hub/skills/wiki-manager/references/")
    markdown = markdown.replace("(references/", "(.hub/skills/wiki-manager/references/")
    markdown = markdown.replace(
        "explicit `/wiki:*` command", "explicit routed wiki command"
    )

    def _rewrite_route(match: re.Match[str]) -> str:
        command = match.group(1)
        return f"Read `.hub/commands/{command}.md` and follow that command protocol"

    markdown = re.sub(r"`Skill: wiki:([a-z-]+)`", _rewrite_route, markdown)
    markdown = re.sub(
        r"`/wiki:([a-z-]+)([^`]*)`", lambda m: f"`{m.group(1)}{m.group(2)}`", markdown
    )
    markdown = re.sub(r"`/wiki ([^`]*)`", lambda m: f"`{m.group(1)}`", markdown)
    markdown = re.sub(
        r"Routing to `([a-z-]+)`\.",
        lambda m: (
            f"Routing to the `{m.group(1)}` protocol in `.hub/commands/{m.group(1)}.md`."
        ),
        markdown,
    )
    return markdown


def _adapt_command_markdown(markdown: str) -> str:
    """Adapt Claude Code command markdown to Hermes alias-skill references."""
    markdown = markdown.replace(
        "skills/wiki-manager/", "../wiki/.hub/skills/wiki-manager/"
    )
    markdown = markdown.replace(
        "`references/", "`../wiki/.hub/skills/wiki-manager/references/"
    )
    markdown = markdown.replace(
        "(references/", "(../wiki/.hub/skills/wiki-manager/references/"
    )
    markdown = re.sub(r"/wiki:([a-z-]+)", lambda m: f"/wiki-{m.group(1)}", markdown)
    markdown = re.sub(
        r"`Skill: wiki:([a-z-]+)`", lambda m: f"`/wiki-{m.group(1)}`", markdown
    )
    return markdown


MANAGED_SKILL_MARKER = "This skill is managed by the `nvk-llm-wiki` Hermes plugin."

ALL_COMMANDS = {
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


def _alias_skill_wrapper(*, command: str, meta: Dict[str, Any]) -> str:
    return (
        "## When to Use\n\n"
        f"Use `wiki-{command}` when the user already intends to run the upstream `{command}` workflow.\n"
        "Use the root `wiki` skill instead for generic routing, init, or hub-level operations.\n\n"
        "## Procedure\n\n"
        "1. Treat the user's text as arguments for the upstream command.\n"
        "2. Follow the vendored upstream command markdown exactly.\n\n"
        "## Verification\n\n"
        f"- Locked upstream: nvk/llm-wiki@{meta['version']} ({meta['commit'][:12]}).\n"
    )


def _generate_alias_skill(command: str, vendor_md: str, meta: Dict[str, Any]) -> str:
    """Generate a complete Hermes SKILL.md for one upstream command alias."""
    frontmatter, body = _strip_frontmatter(vendor_md)
    adapted_body = _adapt_command_markdown(body)
    description = frontmatter.get(
        "description", f"Hermes-native wrapper for the upstream {command} wiki command"
    )

    return (
        "---\n"
        f"name: wiki-{command}\n"
        f'description: "{description}"\n'
        f"version: {meta['version']}\n"
        "author: nvk via Hermes adapter\n"
        "license: MIT\n"
        "metadata:\n"
        "  hermes:\n"
        "    tags: [wiki, research, knowledge-base, nvk]\n"
        "    category: research\n"
        "---\n\n"
        f"# nvk/llm-wiki {command}\n\n"
        f"{MANAGED_SKILL_MARKER}\n\n"
        f"{_alias_skill_wrapper(command=command, meta=meta)}"
        f"The adapted upstream command content follows.\n\n"
        f"{adapted_body}"
    )


def _generate_root_skill(vendor_md: str, meta: Dict[str, Any]) -> str:
    """Generate the root wiki router SKILL.md from upstream wiki command."""
    adapted_md = _adapt_router_markdown(vendor_md)

    return (
        "---\n"
        "name: wiki\n"
        'description: "nvk/llm-wiki router skill managed by the Hermes nvk-llm-wiki plugin"\n'
        f"version: {meta['version']}\n"
        "author: nvk via Hermes adapter\n"
        "license: MIT\n"
        "metadata:\n"
        "  hermes:\n"
        "    tags: [wiki, knowledge-base, research, markdown, obsidian]\n"
        "    category: research\n"
        "---\n\n"
        "# nvk/llm-wiki\n\n"
        f"{MANAGED_SKILL_MARKER}\n\n"
        "## When to Use\n\n"
        "Use `wiki` for routing, init, status, and general nvk/llm-wiki workflows.\n\n"
        "## Procedure\n\n"
        "1. Resolve the target wiki or hub context first.\n"
        "2. Follow the adapted upstream protocol.\n\n"
        "Use `.hub/commands/*.md` and `.hub/skills/wiki-manager/**` as the authoritative\n"
        "upstream protocol files.\n\n"
        "The adapted upstream router content follows.\n\n"
        f"{adapted_md}"
    )


def _copy_tree(src: Path, dst: Path) -> None:
    """Recursively copy files from src to dst."""
    if not src.exists():
        return
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, target)


def sync_managed_skill_bundle(
    vendor_dir: str | Path,
    output_dir: str | Path,
    commands: set[str] | None = None,
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generate complete managed-skill bundle from vendored upstream files."""
    vendor = Path(vendor_dir)
    out = Path(output_dir)
    if commands is None:
        commands = ALL_COMMANDS
    if meta is None:
        meta = {"version": "0.0.0", "commit": "unknown"}

    # Root skill dir
    skill_root = out / "research" / "wiki"
    if skill_root.exists():
        shutil.rmtree(skill_root)
    skill_root.mkdir(parents=True, exist_ok=True)

    # Copy .hub/ assets
    commands_src = vendor / "commands"
    if commands_src.exists():
        _copy_tree(commands_src, skill_root / ".hub" / "commands")

    # Copy reference files
    refs_src = vendor / "references"
    if refs_src.exists():
        _copy_tree(
            refs_src, skill_root / ".hub" / "skills" / "wiki-manager" / "references"
        )

    # Generate root SKILL.md
    wiki_cmd_path = vendor / "commands" / "wiki.md"
    if wiki_cmd_path.exists():
        vendor_md = wiki_cmd_path.read_text(encoding="utf-8")
    else:
        vendor_md = '---\ndescription: "Wiki router"\n---\n\nRouter content.'
    (skill_root / "SKILL.md").write_text(
        _generate_root_skill(vendor_md, meta), encoding="utf-8"
    )

    # Write .nvk-upstream.json
    (skill_root / ".nvk-upstream.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )

    # Generate alias skills
    for command in sorted(commands):
        cmd_path = vendor / "commands" / f"{command}.md"
        if cmd_path.exists():
            vendor_md = cmd_path.read_text(encoding="utf-8")
        else:
            vendor_md = f'---\ndescription: "{command}"\n---\n\n# {command}\n\nVendored content.'
        alias_skill = _generate_alias_skill(command, vendor_md, meta)
        alias_root = out / "research" / f"wiki-{command}"
        alias_root.mkdir(parents=True, exist_ok=True)
        (alias_root / "SKILL.md").write_text(alias_skill, encoding="utf-8")

    return {
        "skill_root": str(skill_root),
        "version": meta["version"],
        "commit": meta["commit"],
    }


def _ensure_managed_skills_external_dir(
    config: Dict[str, Any], managed_root: str
) -> bool:
    """Add managed_root to skills.external_dirs if not present. Returns True if changed."""
    skills_cfg = config.setdefault("skills", {})
    external_dirs = skills_cfg.setdefault("external_dirs", [])
    if isinstance(external_dirs, str):
        external_dirs = [external_dirs]
        skills_cfg["external_dirs"] = external_dirs
    if not isinstance(external_dirs, list):
        external_dirs = []
        skills_cfg["external_dirs"] = external_dirs
    if managed_root in external_dirs:
        return False
    external_dirs.append(managed_root)
    return True


def _is_external_dir_registered(config: Dict[str, Any], managed_root: str) -> bool:
    """Read-only check: is managed_root in skills.external_dirs?"""
    external_dirs = config.get("skills", {}).get("external_dirs", [])
    if isinstance(external_dirs, str):
        external_dirs = [external_dirs]
    if not isinstance(external_dirs, list):
        return False
    return managed_root in external_dirs


def _builtin_llm_wiki_disabled(config: Dict[str, Any]) -> bool:
    """Check if Hermes built-in llm-wiki skill is disabled in config."""
    disabled = config.get("skills", {}).get("disabled", [])
    return isinstance(disabled, list) and "llm-wiki" in disabled


def _check(name: str, ok: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def run_doctor(
    lock_path: str | Path,
    vendor_dir: str | Path,
    skill_root: str | Path,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Run integrity checks on the managed skill bundle."""
    checks: List[Dict[str, Any]] = []
    lock_p = Path(lock_path)
    vendor_p = Path(vendor_dir)
    skill_p = Path(skill_root)

    # Check lock file
    checks.append(_check("upstream lock", lock_p.exists(), str(lock_p)))

    # Check vendor files
    vendor_ok = vendor_p.exists() and any(vendor_p.iterdir())
    checks.append(_check("vendor directory", vendor_ok, str(vendor_p)))

    # Check skill root
    checks.append(_check("skill root", skill_p.exists(), str(skill_p)))
    checks.append(
        _check("skill file", (skill_p / "SKILL.md").exists(), str(skill_p / "SKILL.md"))
    )

    # Check all alias skills
    for cmd in sorted(ALL_COMMANDS):
        alias_skill = skill_p.parent / f"wiki-{cmd}" / "SKILL.md"
        checks.append(_check(f"alias-{cmd}", alias_skill.exists(), str(alias_skill)))

    # Check config
    ext_registered = _is_external_dir_registered(config, str(skill_p.parent.parent))
    checks.append(
        _check(
            "external dir",
            ext_registered,
            "registered" if ext_registered else "not registered",
        )
    )
    checks.append(
        _check(
            "built-in disabled",
            _builtin_llm_wiki_disabled(config),
            "disabled" if _builtin_llm_wiki_disabled(config) else "enabled",
        )
    )

    healthy = all(check["ok"] for check in checks)
    return {"healthy": healthy, "checks": checks}


def get_status(
    lock_path: str | Path,
    skill_root: str | Path,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Return current plugin status as a dict."""
    lock_p = Path(lock_path)
    meta = {}
    if lock_p.exists():
        meta = json.loads(lock_p.read_text(encoding="utf-8"))

    skill_p = Path(skill_root)
    return {
        "upstream_repo": meta.get("repo", "unknown"),
        "upstream_version": meta.get("version", "unknown"),
        "upstream_commit": meta.get("commit", "unknown"),
        "skill_installed": (skill_p / "SKILL.md").exists(),
        "skill_root": str(skill_p),
        "external_dir_registered": _is_external_dir_registered(
            config, str(skill_p.parent.parent)
        ),
        "builtin_llm_wiki_disabled": _builtin_llm_wiki_disabled(config),
    }


def activate_plugin(
    config_path: str | Path,
    managed_root: str | Path,
) -> Dict[str, Any]:
    """Activate the plugin by ensuring config has external dirs set up."""
    config: Dict[str, Any] = {"skills": {"external_dirs": [], "disabled": []}}
    if Path(config_path).exists():
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    managed_root_s = str(Path(managed_root))
    changed = _ensure_managed_skills_external_dir(config, managed_root_s)
    disabled = config.setdefault("skills", {}).setdefault("disabled", [])
    if "llm-wiki" not in disabled:
        disabled.append("llm-wiki")
        changed = True
    Path(config_path).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return {
        "success": True,
        "config_updated": changed,
        "external_dir": managed_root_s,
    }
