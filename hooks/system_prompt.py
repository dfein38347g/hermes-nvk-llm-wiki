"""pre_llm_call hook — invoke upstream session capture for context injection.

Called before each LLM call. Delegates to upstream llm_wiki_session.py which
reads recent session digests for the current CWD and returns rehydration context.
Falls back to static wiki awareness string if the upstream is unavailable.
"""

from __future__ import annotations

from typing import Any

from hooks.upstream_bridge import invoke as _upstream_invoke


def pre_llm_call(**kwargs: Any) -> str | None:
    """Inject wiki session context into the current turn.

    Hermes passes: session_id, user_message, conversation_history,
    is_first_turn, model, platform, task_id, turn_id, sender_id.

    Returns a string that Hermes injects into the user message.
    """
    ctx = _upstream_invoke("UserPromptSubmit", **kwargs)
    if ctx:
        return ctx
    return (
        "Wiki hub at ~/wiki.\n"
        "Use the `wiki` skill for knowledge base operations.\n"
        "Session capture active."
    )
