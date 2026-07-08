"""Hermes adapter plugin for nvk/llm-wiki."""

from __future__ import annotations

from pathlib import Path

from cli import register_cli, wiki_command
from hooks.on_session_end import on_session_end as session_end_handler
from hooks.prefetch import prefetch as prefetch_handler
from hooks.sync_turn import sync_turn as sync_turn_handler
from hooks.system_prompt import build_system_prompt_block


def register(ctx):
    """Register the nvk-llm-wiki plugin with Hermes.

    Called by Hermes at plugin load time.
    """
    ctx.register_cli_command(
        name="wiki",
        help="Manage the nvk/llm-wiki plugin and synced skill bundle",
        setup_fn=register_cli,
        handler_fn=wiki_command,
        description="Sync, activate, and inspect the managed nvk/llm-wiki bundle.",
    )

    ctx.register_hook("system_prompt_block", build_system_prompt_block)
    ctx.register_hook("prefetch", prefetch_handler)
    ctx.register_hook("sync_turn", sync_turn_handler)
    from session import write_checkpoint

    ctx.register_hook(
        "on_pre_compress",
        lambda **kw: write_checkpoint(
            Path.home() / "wiki" / ".sessions", {"compacted": True}
        ),
    )
    ctx.register_hook("on_session_end", session_end_handler)
