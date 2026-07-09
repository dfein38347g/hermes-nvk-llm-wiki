"""on_session_end hook — invoke upstream session capture for final digest.

Called when a Hermes session terminates. Delegates to upstream
llm_wiki_session.py which writes the final digest, checkpoint, and
rebuilds all indexes.
"""

from __future__ import annotations

from typing import Any

from hooks.upstream_bridge import invoke as _upstream_invoke


def on_session_end(
    session_id: str = "",
    **kwargs: Any,
) -> None:
    """Save final checkpoint and write session digest.

    Hermes passes: session_id, task_id, turn_id, api_request_id,
    completed, interrupted, reason, model, platform.
    """
    if not session_id:
        return
    _upstream_invoke(
        "SessionEnd",
        session_id=session_id,
        **kwargs,
    )
