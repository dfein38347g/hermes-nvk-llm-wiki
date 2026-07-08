"""pre_llm_call hook — lightweight wiki context injection.

Called before each LLM call. Returns a context string that Hermes injects
into the user message (not the system prompt, to preserve prompt cache).
"""

from __future__ import annotations

from typing import Any


def pre_llm_call(**kwargs: Any) -> str | None:
    """Inject wiki hub awareness into the current turn.

    Hermes passes: session_id, user_message, conversation_history,
    is_first_turn, model, platform.
    """
    hub_info = kwargs.get("hub_info")
    if hub_info:
        tc = hub_info.get("topic_count", 0)
        topics = hub_info.get("topics", [])
        last = hub_info.get("last_session", "never")
        topic_list = ", ".join(topics[:5])
        return (
            f"Wiki hub at ~/wiki with {tc} topic wikis: {topic_list}.\n"
            f"Last session: {last}.\n"
            f"Session capture active — digests under .sessions/."
        )
    return (
        "Wiki hub at ~/wiki.\n"
        "Use the `wiki` skill for knowledge base operations.\n"
        "Session capture active."
    )
