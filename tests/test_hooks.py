"""Tests for hook modules (hooks/system_prompt, hooks/prefetch, etc.)."""

from __future__ import annotations

from pathlib import Path

from hooks.system_prompt import build_system_prompt_block
from hooks.on_session_end import on_session_end


# ── system_prompt_block ────────────────────────────────────────────


def test_system_prompt_block_returns_string():
    result = build_system_prompt_block({"topic_count": 3, "topics": ["test"]})
    assert isinstance(result, str)
    assert "Wiki hub" in result


def test_system_prompt_block_mentions_topic_count():
    result = build_system_prompt_block({"topic_count": 3, "topics": ["a", "b", "c"]})
    assert "3" in result


def test_system_prompt_block_no_args():
    result = build_system_prompt_block()
    assert isinstance(result, str)
    assert "Wiki hub" in result


def test_system_prompt_block_omits_topic_count_when_missing():
    result = build_system_prompt_block({"topics": ["a"]})
    assert "0" in result


# ── prefetch ───────────────────────────────────────────────────────


def test_prefetch_returns_none_for_no_session_id():
    from hooks.prefetch import prefetch

    assert prefetch() is None


def test_prefetch_returns_none_when_session_id_is_none():
    from hooks.prefetch import prefetch

    assert prefetch(session_id=None) is None


# ── sync_turn ──────────────────────────────────────────────────────


def test_sync_turn_appends_event(tmp_path):
    from hooks.sync_turn import sync_turn

    sess_dir = tmp_path / ".sessions"
    session_id = "sess-st-1"
    turn_data = {"files": ["a.py", "b.py"], "tool_count": 3}

    sync_turn(
        session_id=session_id,
        turn_data=turn_data,
        sessions_dir=str(sess_dir),
    )

    session_dir = sess_dir / session_id
    events_file = session_dir / ".session-events.jsonl"
    assert events_file.exists()
    content = events_file.read_text(encoding="utf-8")
    assert "sync_turn" in content
    assert "a.py" in content
    assert "b.py" in content
    assert '"tool_count": 3' in content


def test_sync_turn_empty_turn_data(tmp_path):
    from hooks.sync_turn import sync_turn

    sess_dir = tmp_path / ".sessions"
    session_id = "sess-st-2"

    sync_turn(
        session_id=session_id,
        turn_data=None,
        sessions_dir=str(sess_dir),
    )

    session_dir = sess_dir / session_id
    events_file = session_dir / ".session-events.jsonl"
    assert events_file.exists()
    content = events_file.read_text(encoding="utf-8")
    assert "files_touched" in content
    assert "tool_count" in content


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
