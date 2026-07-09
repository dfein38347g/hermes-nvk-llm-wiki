"""Tests for hook modules — subprocess-based upstream bridge."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from hooks.system_prompt import pre_llm_call
from hooks.prefetch import on_session_start
from hooks.sync_turn import post_tool_call
from hooks.on_session_end import on_session_end
from hooks.upstream_bridge import _build_payload, invoke, _SCRIPT_PATH, _TIMEOUT


# ── Helpers ─────────────────────────────────────────────────────────


def _mock_run(stdout_text: str = "", returncode: int = 0, exc: Exception | None = None):
    """Return a mock subprocess.run result."""
    mock_result = MagicMock()
    mock_result.returncode = returncode
    mock_result.stdout = stdout_text
    mock_result.stderr = ""
    return mock_result


def _mock_run_from_json(stdout_obj: Any, returncode: int = 0):
    return _mock_run(
        stdout_text=json.dumps(stdout_obj, ensure_ascii=False), returncode=returncode
    )


def _mock_script_path() -> Mock:
    mock_script = Mock(spec=Path)
    mock_script.exists.return_value = True
    mock_script.__str__ = Mock(return_value="/fake/script.py")
    return mock_script


# ── pre_llm_call (system_prompt) ───────────────────────────────────


def test_system_prompt_block_returns_string():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="", returncode=0)
        result = pre_llm_call(session_id="s1")
        assert isinstance(result, str)
        assert result is not None
        assert "Wiki hub" in result


def test_system_prompt_block_returns_upstream_context():
    ctx = "Recent session: compiled 3 articles"
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run_from_json(
            {
                "hookSpecificOutput": {"additionalContext": ctx},
            }
        )
        result = pre_llm_call(session_id="s1")
        assert result == ctx


def test_system_prompt_block_falls_back_to_static():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="", returncode=0)
        result = pre_llm_call()
        assert result is not None
        assert "Wiki hub" in result
        assert "wiki" in result.lower()


def test_system_prompt_block_mentions_topic_count():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="", returncode=0)
        result = pre_llm_call(hub_info={"topic_count": 3, "topics": ["a", "b", "c"]})
        assert result is not None
        assert "Wiki hub" in result


def test_system_prompt_block_no_args():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="", returncode=0)
        result = pre_llm_call()
        assert isinstance(result, str)
        assert result is not None
        assert "Wiki hub" in result


def test_system_prompt_block_omits_topic_count_when_missing():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="", returncode=0)
        result = pre_llm_call(hub_info={"topics": ["a"]})
        assert result is not None
        assert "Wiki hub" in result


def test_system_prompt_block_upstream_error_falls_back():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="", returncode=1)
        result = pre_llm_call(session_id="s1")
        assert result is not None
        assert "Wiki hub" in result


def test_system_prompt_block_upstream_timeout_falls_back():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)
        result = pre_llm_call(session_id="s1")
        assert result is not None
        assert "Wiki hub" in result


# ── on_session_start (prefetch) ────────────────────────────────────


def test_prefetch_returns_none_for_no_session_id():
    assert on_session_start() is None


def test_prefetch_returns_none_when_session_id_is_none():
    assert on_session_start(session_id="") is None


def test_prefetch_returns_none_for_empty_string():
    assert on_session_start(session_id="") is None


def test_prefetch_delegates_to_upstream():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run_from_json(
            {
                "hookSpecificOutput": {"additionalContext": "rehydration text"},
            }
        )
        result = on_session_start(session_id="sess-1")
        assert result == "rehydration text"
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0][2] == "hook"


def test_prefetch_passes_session_start_event():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        on_session_start(session_id="sess-1")
        call_input = mock_run.call_args[1]["input"]
        payload = json.loads(call_input)
        assert payload["hook_event_name"] == "SessionStart"
        assert payload["session_id"] == "sess-1"


# ── post_tool_call (sync_turn) ─────────────────────────────────────


def test_sync_turn_delegates_to_upstream():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        post_tool_call(
            session_id="sess-st-1",
            tool_name="terminal",
            tool_call_id="call-1",
            result='{"output": "hello"}',
            duration_ms=42,
        )
        mock_run.assert_called_once()
        call_input = mock_run.call_args[1]["input"]
        payload = json.loads(call_input)
        assert payload["hook_event_name"] == "PostToolUse"
        assert payload["tool_name"] == "terminal"
        assert payload["tool_use_id"] == "call-1"
        assert payload["duration_ms"] == 42
        assert payload["session_id"] == "sess-st-1"


def test_sync_turn_empty_turn_data():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        post_tool_call(session_id="sess-st-2")
        call_input = mock_run.call_args[1]["input"]
        payload = json.loads(call_input)
        assert payload["hook_event_name"] == "PostToolUse"
        assert payload["session_id"] == "sess-st-2"


def test_sync_turn_skips_without_session_id():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        post_tool_call(session_id="", tool_name="terminal")
        mock_run.assert_not_called()


def test_sync_turn_truncates_long_result():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        long_result = "x" * 2000
        post_tool_call(session_id="s1", tool_name="bash", result=long_result)
        call_input = mock_run.call_args[1]["input"]
        payload = json.loads(call_input)
        assert len(payload["tool_output"]) <= 1203


# ── on_session_end ─────────────────────────────────────────────────


def test_on_session_end_delegates_to_upstream():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        on_session_end(session_id="sess-hooks-1", completed=True, reason="user_done")
        mock_run.assert_called_once()
        call_input = mock_run.call_args[1]["input"]
        payload = json.loads(call_input)
        assert payload["hook_event_name"] == "SessionEnd"
        assert payload["session_id"] == "sess-hooks-1"
        assert payload["completed"] is True
        assert payload["reason"] == "user_done"


def test_on_session_end_writes_digest():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        on_session_end(session_id="sess-hooks-1")
        mock_run.assert_called_once()


def test_on_session_end_writes_checkpoint():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        on_session_end(session_id="sess-hooks-2", state={"summary": "test session"})
        mock_run.assert_called_once()


def test_on_session_end_writes_both():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(stdout_text="")
        on_session_end(
            session_id="sess-hooks-3",
            events=[{"event": "finding", "payload": {}}],
            state={"status": "completed"},
        )
        mock_run.assert_called_once()


def test_on_session_end_no_events_no_state():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        on_session_end(session_id="sess-hooks-4")
        mock_run.assert_called_once()


def test_on_session_end_skips_without_session_id():
    with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
        on_session_end(session_id="")
        mock_run.assert_not_called()


# ── _build_payload ─────────────────────────────────────────────────


def test_build_payload_session_start():
    payload = _build_payload("SessionStart", {"session_id": "s1", "model": "claude-3"})
    assert payload["hook_event_name"] == "SessionStart"
    assert payload["session_id"] == "s1"
    assert payload["model"] == "claude-3"
    assert payload["cwd"]


def test_build_payload_user_prompt_submit():
    payload = _build_payload(
        "UserPromptSubmit",
        {
            "session_id": "s1",
            "user_message": "hello",
        },
    )
    assert payload["hook_event_name"] == "UserPromptSubmit"
    assert payload["user_prompt"] == "hello"


def test_build_payload_post_tool_use():
    payload = _build_payload(
        "PostToolUse",
        {
            "session_id": "s1",
            "tool_name": "terminal",
            "tool_call_id": "call-1",
            "result": "ok",
            "duration_ms": 100,
            "turn_id": "turn-1",
        },
    )
    assert payload["hook_event_name"] == "PostToolUse"
    assert payload["tool_name"] == "terminal"
    assert payload["tool_use_id"] == "call-1"
    assert payload["tool_output"] == "ok"
    assert payload["duration_ms"] == 100
    assert payload["turn_id"] == "turn-1"


def test_build_payload_session_end():
    payload = _build_payload(
        "SessionEnd",
        {
            "session_id": "s1",
            "completed": True,
            "reason": "user_done",
            "platform": "hermes",
        },
    )
    assert payload["hook_event_name"] == "SessionEnd"
    assert payload["completed"] is True
    assert payload["reason"] == "user_done"
    assert payload["platform"] == "hermes"


def test_build_payload_truncates_long_result():
    payload = _build_payload(
        "PostToolUse",
        {
            "session_id": "s1",
            "tool_name": "bash",
            "result": "x" * 2000,
        },
    )
    assert len(payload["tool_output"]) <= 1203


def test_build_payload_omits_optional_fields():
    payload = _build_payload("SessionStart", {"session_id": "s1"})
    assert "tool_name" not in payload
    assert "tool_use_id" not in payload
    assert "user_prompt" not in payload
    assert "tool_output" not in payload


# ── invoke bridge ──────────────────────────────────────────────────


def test_invoke_returns_none_when_script_missing():
    with patch.object(Path, "exists", return_value=False):
        result = invoke("SessionStart", session_id="s1")
        assert result is None


def test_invoke_returns_context_from_stdout_json():
    ctx = "session context here"
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run_from_json(
                {
                    "hookSpecificOutput": {"additionalContext": ctx},
                }
            )
            result = invoke("SessionStart", session_id="s1")
            assert result == ctx


def test_invoke_returns_raw_text_stdout():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(stdout_text="plain text output")
            result = invoke("SessionStart", session_id="s1")
            assert result == "plain text output"


def test_invoke_returns_none_on_non_zero_exit():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(stdout_text="error", returncode=1)
            result = invoke("SessionStart", session_id="s1")
            assert result is None


def test_invoke_returns_none_on_empty_stdout():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(stdout_text="", returncode=0)
            result = invoke("SessionStart", session_id="s1")
            assert result is None


def test_invoke_returns_none_on_timeout():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)
            result = invoke("SessionStart", session_id="s1")
            assert result is None


def test_invoke_returns_none_on_os_error():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("permission denied")
            result = invoke("SessionStart", session_id="s1")
            assert result is None


def test_invoke_returns_none_on_invalid_json():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(stdout_text="{invalid json", returncode=0)
            result = invoke("SessionStart", session_id="s1")
            assert result is None


def test_invoke_passes_correct_args():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(stdout_text="")
            invoke("SessionStart", session_id="s1")
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == sys.executable
            assert cmd[2] == "hook"
            assert "--harness" in cmd
            assert "hermes" in cmd
            assert "--if-enabled" in cmd
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["text"] is True
            assert call_args[1]["timeout"] == _TIMEOUT


def test_invoke_returns_none_when_json_has_no_additional_context():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run_from_json(
                {
                    "hookSpecificOutput": {},
                }
            )
            result = invoke("SessionStart", session_id="s1")
            assert result is None


def test_invoke_returns_none_when_json_no_hook_specific_output():
    mock_script = _mock_script_path()
    with patch("hooks.upstream_bridge._SCRIPT_PATH", mock_script):
        with patch("hooks.upstream_bridge.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run_from_json({"status": "ok"})
            result = invoke("SessionStart", session_id="s1")
            assert result is None
