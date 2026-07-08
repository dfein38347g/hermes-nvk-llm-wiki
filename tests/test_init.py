"""Tests for __init__.py — Hermes plugin registration."""

from runtime import ALL_COMMANDS


def test_register_called_with_ctx():
    """Verify __init__.py's register() shape is correct."""
    import __init__ as plugin

    assert hasattr(plugin, "register"), "register() entry point missing"
    assert callable(plugin.register)


class FakeCtx:
    """Minimal Hermes ctx mock for registration testing."""

    def __init__(self):
        self.registered_cli = None
        self.registered_hooks = []

    def register_cli_command(self, name, help, setup_fn, handler_fn, description):
        self.registered_cli = {
            "name": name,
            "help": help,
            "setup_fn": setup_fn,
            "handler_fn": handler_fn,
            "description": description,
        }

    def register_hook(self, event, handler):
        self.registered_hooks.append({"event": event, "handler": handler})


def test_register_registers_cli_command():
    import __init__ as plugin

    ctx = FakeCtx()
    plugin.register(ctx)
    assert ctx.registered_cli is not None
    assert ctx.registered_cli["name"] == "wiki"


def test_register_registers_hooks():
    import __init__ as plugin

    ctx = FakeCtx()
    plugin.register(ctx)
    hook_events = {h["event"] for h in ctx.registered_hooks}
    assert "pre_llm_call" in hook_events
    assert "on_session_start" in hook_events
    assert "post_tool_call" in hook_events
    assert "on_session_finalize" in hook_events
    assert "on_session_end" in hook_events
