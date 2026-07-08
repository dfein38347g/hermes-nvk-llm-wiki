"""sync_turn hook — append event to session log after each assistant turn."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from session import append_event


def sync_turn(
    session_id: str,
    turn_data: dict[str, Any] | None = None,
    **kwargs,
) -> None:
    """Record a session event after each assistant turn.

    Stores minimal redacted metadata — not full transcripts.
    """
    payload = {
        "files_touched": turn_data.get("files", []) if turn_data else [],
        "tool_count": turn_data.get("tool_count", 0) if turn_data else 0,
    }
    sessions_dir = kwargs.get("sessions_dir")
    session_dir = Path(sessions_dir) / session_id if sessions_dir else Path(session_id)
    append_event(session_dir, "sync_turn", payload)
