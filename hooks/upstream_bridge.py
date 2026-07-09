"""Subprocess bridge to upstream llm_wiki_session.py.

Maps Hermes hook kwargs to the upstream's expected JSON payload format,
invokes the bundled llm_wiki_session.py as a subprocess, and returns
context strings for pre_llm_call/on_session_start hooks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPT_PATH = Path(__file__).resolve().parent / "llm_wiki_session.py"
_TIMEOUT = 5  # seconds — matches upstream shell hook timeout


def _build_payload(event_name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Build the upstream-compatible JSON payload from Hermes hook kwargs.

    The upstream's normalize_event() expects these keys:
    - session_id / sessionId
    - hook_event_name / hookEventName / event
    - cwd
    - model
    - tool_name / toolName / tool
    - turn_id / turnId
    """
    payload: dict[str, Any] = {
        "hook_event_name": event_name,
        "session_id": kwargs.get("session_id", ""),
        "cwd": str(kwargs.get("cwd", os.getcwd())),
        "model": kwargs.get("model", ""),
    }

    # Tool-specific fields
    tool_name = kwargs.get("tool_name")
    if tool_name:
        payload["tool_name"] = tool_name

    tool_call_id = kwargs.get("tool_call_id")
    if tool_call_id:
        payload["tool_use_id"] = tool_call_id

    turn_id = kwargs.get("turn_id")
    if turn_id:
        payload["turn_id"] = turn_id

    task_id = kwargs.get("task_id")
    if task_id:
        payload["task_id"] = task_id

    # For pre_llm_call, include user_message for feedback classification
    user_message = kwargs.get("user_message")
    if user_message and event_name in ("UserPromptSubmit", "SessionStart"):
        payload["user_prompt"] = user_message

    # For post_tool_call, include tool result preview
    result = kwargs.get("result")
    if result and event_name == "PostToolUse":
        result_str = str(result)
        if len(result_str) > 1200:
            result_str = result_str[:1200] + "…"
        payload["tool_output"] = result_str

    duration_ms = kwargs.get("duration_ms")
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms

    status = kwargs.get("status")
    if status:
        payload["status"] = status

    # For session boundary events
    platform = kwargs.get("platform")
    if platform:
        payload["platform"] = platform

    reason = kwargs.get("reason")
    if reason:
        payload["reason"] = reason

    completed = kwargs.get("completed")
    if completed is not None:
        payload["completed"] = completed

    interrupted = kwargs.get("interrupted")
    if interrupted is not None:
        payload["interrupted"] = interrupted

    return payload


def invoke(event_name: str, **kwargs: Any) -> str | None:
    """Invoke the upstream session capture script.

    Args:
        event_name: Upstream event name (SessionStart, UserPromptSubmit,
                     PostToolUse, PreCompact, SessionEnd).
        **kwargs: Hermes hook kwargs.

    Returns:
        Context string for pre_llm_call/on_session_start, or None.
    """
    if not _SCRIPT_PATH.exists():
        return None

    try:
        payload = _build_payload(event_name, kwargs)
        stdin_json = json.dumps(payload, ensure_ascii=False, default=str)

        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPT_PATH),
                "hook",
                "--harness",
                "hermes",
                "--if-enabled",
            ],
            input=stdin_json,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            cwd=kwargs.get("cwd", os.getcwd()),
        )

        if result.returncode != 0:
            return None

        stdout = (result.stdout or "").strip()
        if not stdout:
            return None

        # Parse stdout for hookSpecificOutput (SessionStart, UserPromptSubmit)
        try:
            data = json.loads(stdout)
            hook_output = data.get("hookSpecificOutput", {})
            additional_context = hook_output.get("additionalContext", "")
            if additional_context:
                return str(additional_context)
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: return raw stdout as context if it looks like text
        if stdout and not stdout.startswith("{"):
            return stdout

        return None

    except (subprocess.TimeoutExpired, OSError, ValueError, TypeError):
        return None
