from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent


def test_plugin_yaml_exists():
    assert (PLUGIN_DIR / "plugin.yaml").exists()


def test_plugin_yaml_contains_name():
    content = (PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8")
    assert "nvk-llm-wiki" in content


def test_plugin_yaml_contains_hooks():
    content = (PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8")
    assert "hooks:" in content
