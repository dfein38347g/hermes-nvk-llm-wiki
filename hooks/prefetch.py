"""on_session_start hook — load checkpoint and inject rehydration context.

Called when a Hermes session starts. Returns rehydration context if a
checkpoint exists from a prior session, or None for a fresh session.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from session import read_checkpoint, rehydrate


def on_session_start(session_id: str = "", **kwargs: Any) -> dict | None:
    """Load session checkpoint on session start for resume context.

    Hermes passes: session_id.
    """
    if not session_id:
        return None
    sessions_dir = kwargs.get("sessions_dir")
    session_dir = Path(sessions_dir) / session_id if sessions_dir else Path(session_id)
    checkpoint = read_checkpoint(session_dir)
    if not checkpoint:
        return None
    return rehydrate(session_dir)
