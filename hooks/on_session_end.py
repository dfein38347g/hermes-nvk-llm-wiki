"""on_session_end hook — final checkpoint + markdown digest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from session import append_event, create_digest, write_checkpoint


def on_session_end(
    session_id: str,
    state: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    sessions_dir: str | None = None,
    **kwargs,
) -> None:
    """Save final checkpoint and write session digest.

    Called when a Hermes session terminates.
    """
    session_dir = Path(sessions_dir) / session_id if sessions_dir else Path(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    if events:
        for ev in events:
            append_event(
                session_dir,
                ev.get("event", "unknown"),
                ev.get("payload", {}),
            )

    if state:
        write_checkpoint(session_dir, state)

    if events or state:
        digest = create_digest(session_dir)
        if digest:
            digest_dir = (
                Path(sessions_dir) / "digests"
                if sessions_dir
                else session_dir / "digests"
            )
            digest_dir.mkdir(parents=True, exist_ok=True)
            (digest_dir / f"{session_id}.md").write_text(digest, encoding="utf-8")
