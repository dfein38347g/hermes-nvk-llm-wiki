"""system_prompt_block hook — lightweight wiki context injection."""

from __future__ import annotations

from typing import Any


def build_system_prompt_block(hub_info: dict[str, Any] | None = None) -> str:
    """Return a compact wiki-awareness block for the system prompt.

    Args:
        hub_info: Optional dict with topic_count, topics list, last_session date.
    """
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
