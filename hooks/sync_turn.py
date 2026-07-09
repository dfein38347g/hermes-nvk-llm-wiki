"""post_tool_call hook — invoke upstream session capture after each tool call.

Called after each tool call. Delegates to upstream llm_wiki_session.py which
records the event, updates session state (event count, tool count, git state),
and manages indexes.
"""

from __future__ import annotations

from typing import Any

from hooks.upstream_bridge import invoke as _upstream_invoke


def post_tool_call(
    session_id: str = "",
    tool_name: str = "",
    **kwargs: Any,
) -> None:
    """Record a session event after each tool call.

    Hermes passes: tool_name, args, session_id, task_id, tool_call_id,
    result, duration_ms, status, error_type, error_message, turn_id,
    api_request_id, middleware_trace.
    """
    if not session_id:
        return
    _upstream_invoke(
        "PostToolUse",
        session_id=session_id,
        tool_name=tool_name,
        **kwargs,
    )
