"""post_tool_call hook — append event to session log after each tool call.

Called after each tool call. Records minimal redacted metadata — not
full transcripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from session import append_event


def post_tool_call(
    session_id: str = "",
    tool_name: str = "",
    tool_call_id: str = "",
    result: str = "",
    duration_ms: int = 0,
    **kwargs: Any,
) -> None:
    """Record a session event after each tool call.

    Hermes passes: tool_name, args, session_id, task_id, tool_call_id,
    result, duration_ms.
    """
    if not session_id:
        return
    sessions_dir = kwargs.get("sessions_dir")
    session_dir = Path(sessions_dir) / session_id if sessions_dir else Path(session_id)
    append_event(
        session_dir,
        "post_tool_call",
        {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "duration_ms": duration_ms,
        },
    )
