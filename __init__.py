"""Hermes adapter plugin for nvk/llm-wiki."""

from __future__ import annotations

import sys
from pathlib import Path

_plugin_dir = Path(__file__).resolve().parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from cli import register_cli, wiki_command
from hooks.on_session_end import on_session_end as session_end_handler
from hooks.prefetch import on_session_start as on_session_start_handler
from hooks.sync_turn import post_tool_call as post_tool_call_handler
from hooks.system_prompt import pre_llm_call as pre_llm_call_handler
from session import write_checkpoint


def register(ctx):
    """Register the nvk-llm-wiki plugin with Hermes.

    Called by Hermes at plugin load time.
    """
    ctx.register_cli_command(
        name="wiki",
        help="Manage the nvk-llm-wiki plugin and synced skill bundle",
        setup_fn=register_cli,
        handler_fn=wiki_command,
        description="Sync, activate, and inspect the managed nvk-llm-wiki bundle.",
    )

    ctx.register_hook("pre_llm_call", pre_llm_call_handler)
    ctx.register_hook("on_session_start", on_session_start_handler)
    ctx.register_hook("post_tool_call", post_tool_call_handler)
    ctx.register_hook(
        "on_session_finalize",
        lambda **kw: write_checkpoint(
            Path.home() / "wiki" / ".sessions", {"compacted": True}
        ),
    )
    ctx.register_hook("on_session_end", session_end_handler)
