"""prefetch hook — load checkpoint and inject rehydration context."""

from __future__ import annotations

from pathlib import Path

from session import read_checkpoint, rehydrate


def prefetch(session_id: str | None = None, **kwargs) -> str | dict | None:
    """Load session checkpoint and return rehydration context if resuming.

    Called before each LLM call. Returns context string or dict if a checkpoint
    exists, or None for a fresh session.
    """
    if not session_id:
        return None
    sessions_dir = kwargs.get("sessions_dir")
    session_dir = Path(sessions_dir) / session_id if sessions_dir else Path(session_id)
    checkpoint = read_checkpoint(session_dir)
    if not checkpoint:
        return None
    return rehydrate(session_dir)
