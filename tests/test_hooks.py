"""Tests for hook modules (hooks/system_prompt, hooks/prefetch, etc.)."""

from __future__ import annotations

from pathlib import Path

from hooks.system_prompt import pre_llm_call
from hooks.on_session_end import on_session_end


# ── pre_llm_call (was system_prompt_block) ─────────────────────────


def test_system_prompt_block_returns_string():
    result = pre_llm_call(hub_info={"topic_count": 3, "topics": ["test"]})
    assert isinstance(result, str)
    assert "Wiki hub" in result


def test_system_prompt_block_mentions_topic_count():
    result = pre_llm_call(hub_info={"topic_count": 3, "topics": ["a", "b", "c"]})
    assert "3" in result


def test_system_prompt_block_no_args():
    result = pre_llm_call()
    assert isinstance(result, str)
    assert "Wiki hub" in result


def test_system_prompt_block_omits_topic_count_when_missing():
    result = pre_llm_call(hub_info={"topics": ["a"]})
    assert "0" in result


# ── on_session_start (was prefetch) ────────────────────────────────


def test_prefetch_returns_none_for_no_session_id():
    from hooks.prefetch import on_session_start

    assert on_session_start() is None


def test_prefetch_returns_none_when_session_id_is_none():
    from hooks.prefetch import on_session_start

    assert on_session_start(session_id=None) is None


# ── post_tool_call (was sync_turn) ─────────────────────────────────


def test_sync_turn_appends_event(tmp_path):
    from hooks.sync_turn import post_tool_call

    sess_dir = tmp_path / ".sessions"
    session_id = "sess-st-1"

    post_tool_call(
        session_id=session_id,
        tool_name="terminal",
        tool_call_id="call-1",
        result='{"output": "hello"}',
        duration_ms=42,
        sessions_dir=str(sess_dir),
    )

    session_dir = sess_dir / session_id
    events_file = session_dir / ".session-events.jsonl"
    assert events_file.exists()
    content = events_file.read_text(encoding="utf-8")
    assert "post_tool_call" in content
    assert "terminal" in content
    assert "call-1" in content
    assert '"duration_ms": 42' in content


def test_sync_turn_empty_turn_data(tmp_path):
    from hooks.sync_turn import post_tool_call

    sess_dir = tmp_path / ".sessions"
    session_id = "sess-st-2"

    post_tool_call(
        session_id=session_id,
        sessions_dir=str(sess_dir),
    )

    session_dir = sess_dir / session_id
    events_file = session_dir / ".session-events.jsonl"
    assert events_file.exists()
    content = events_file.read_text(encoding="utf-8")
    assert "tool_name" in content
    assert "duration_ms" in content


# ── on_session_end ─────────────────────────────────────────────────


def test_on_session_end_writes_digest(tmp_path):
    sess_dir = tmp_path / ".sessions"
    events = [
        {"event": "sync_turn", "timestamp": "2026-01-01T00:00:00Z", "payload": {}}
    ]
    on_session_end(
        session_id="sess-hooks-1",
        events=events,
        sessions_dir=str(sess_dir),
    )
    digest_dir = sess_dir / "digests"
    assert any(digest_dir.rglob("*.md"))


def test_on_session_end_writes_checkpoint(tmp_path):
    sess_dir = tmp_path / ".sessions"
    state = {"summary": "test session", "events": 5}

    on_session_end(
        session_id="sess-hooks-2",
        state=state,
        sessions_dir=str(sess_dir),
    )

    session_dir = sess_dir / "sess-hooks-2"
    checkpoint = session_dir / ".session-checkpoint.json"
    assert checkpoint.exists()
    import json

    cp = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert cp["summary"] == "test session"


def test_on_session_end_writes_both(tmp_path):
    sess_dir = tmp_path / ".sessions"
    events = [
        {
            "event": "finding",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {"text": "X"},
        }
    ]
    state = {"status": "completed"}

    on_session_end(
        session_id="sess-hooks-3",
        events=events,
        state=state,
        sessions_dir=str(sess_dir),
    )

    session_dir = sess_dir / "sess-hooks-3"
    assert (session_dir / ".session-checkpoint.json").exists()
    assert (session_dir / ".session-events.jsonl").exists()

    digest_dir = sess_dir / "digests"
    assert any(digest_dir.rglob("*.md"))


def test_on_session_end_no_events_no_state(tmp_path):
    sess_dir = tmp_path / ".sessions"
    on_session_end(
        session_id="sess-hooks-4",
        sessions_dir=str(sess_dir),
    )
    session_dir = sess_dir / "sess-hooks-4"
    assert not (session_dir / ".session-events.jsonl").exists()
    assert not (session_dir / ".session-checkpoint.json").exists()
    digest_dir = sess_dir / "digests"
    assert not digest_dir.exists()
