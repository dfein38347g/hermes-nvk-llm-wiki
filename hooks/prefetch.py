"""on_session_start hook — invoke upstream session capture for rehydration.

Called when a Hermes session starts. Delegates to upstream llm_wiki_session.py
which reads recent session digests and outputs rehydration context.
"""

from __future__ import annotations

from typing import Any

from hooks.upstream_bridge import invoke as _upstream_invoke


def on_session_start(session_id: str = "", **kwargs: Any) -> str | None:
    """Load session checkpoint on session start for resume context.

    Hermes passes: session_id, old_session_id, carry_over_context,
    platform, model, context_length, conversation_id.

    Returns rehydration context string if available, or None.
    """
    if not session_id:
        return None
    return _upstream_invoke("SessionStart", session_id=session_id, **kwargs)
