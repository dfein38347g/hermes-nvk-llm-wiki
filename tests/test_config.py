from runtime import (
    _ensure_managed_skills_external_dir,
    _builtin_llm_wiki_disabled,
)


def test_ensure_external_dir_adds_entry(tmp_path):
    config = {"skills": {"external_dirs": []}}
    changed = _ensure_managed_skills_external_dir(
        config, str(tmp_path / "managed-skills")
    )
    assert changed is True
    assert str(tmp_path / "managed-skills") in config["skills"]["external_dirs"]


def test_ensure_external_dir_no_duplicate(tmp_path):
    entry = str(tmp_path / "managed-skills")
    config = {"skills": {"external_dirs": [entry]}}
    changed = _ensure_managed_skills_external_dir(config, entry)
    assert changed is False


def test_builtin_disabled_detection():
    config = {"skills": {"disabled": ["llm-wiki"]}}
    assert _builtin_llm_wiki_disabled(config) is True


def test_builtin_not_disabled():
    config = {"skills": {"disabled": []}}
    assert _builtin_llm_wiki_disabled(config) is False
