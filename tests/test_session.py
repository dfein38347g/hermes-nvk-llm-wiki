"""Tests for the session state machine (session.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from session import (
    append_event,
    read_events,
    write_checkpoint,
    read_checkpoint,
    create_digest,
    rehydrate,
    write_state,
    read_state,
    SESSION_EVENTS_FILE,
    SESSION_CHECKPOINT_FILE,
    SESSION_STATE_FILE,
)


# ── append_event / read_events ────────────────────────────────────


def test_append_event_creates_file(tmp_path):
    ev = append_event(tmp_path, "session_start", {"topic": "robotics"})
    assert (tmp_path / SESSION_EVENTS_FILE).exists()
    assert ev["event_type"] == "session_start"
    assert ev["data"]["topic"] == "robotics"
    assert "timestamp" in ev


def test_append_event_increments_event_count(tmp_path):
    append_event(tmp_path, "a", {"n": 1})
    append_event(tmp_path, "b", {"n": 2})
    lines = (
        (tmp_path / SESSION_EVENTS_FILE)
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    assert len(lines) == 2


def test_read_events_empty_dir(tmp_path):
    assert read_events(tmp_path) == []


def test_read_events_no_file(tmp_path):
    assert read_events(tmp_path / "nonexistent") == []


def test_read_events_returns_all(tmp_path):
    append_event(tmp_path, "e1", {"v": 1})
    append_event(tmp_path, "e2", {"v": 2})
    events = read_events(tmp_path)
    assert len(events) == 2
    assert events[0]["data"]["v"] == 1
    assert events[1]["data"]["v"] == 2


def test_read_events_skips_corrupt_lines(tmp_path):
    f = tmp_path / SESSION_EVENTS_FILE
    f.write_text(
        '{"event_type":"good","data":{},"timestamp":"2025-01-01T00:00:00"}\n'
        "not-json\n"
        '{"event_type":"also-good","data":{},"timestamp":"2025-01-01T00:00:01"}\n',
        encoding="utf-8",
    )
    events = read_events(tmp_path)
    assert len(events) == 2
    assert events[0]["event_type"] == "good"
    assert events[1]["event_type"] == "also-good"


# ── write_checkpoint / read_checkpoint ────────────────────────────


def test_write_checkpoint_creates_file(tmp_path):
    cp = write_checkpoint(tmp_path, {"status": "completed", "events": 10})
    assert (tmp_path / SESSION_CHECKPOINT_FILE).exists()
    assert cp["status"] == "completed"


def test_read_checkpoint_no_file(tmp_path):
    assert read_checkpoint(tmp_path) is None


def test_read_checkpoint_no_file_nonexistent_dir(tmp_path):
    assert read_checkpoint(tmp_path / "nonexistent") is None


def test_read_checkpoint_returns_content(tmp_path):
    write_checkpoint(tmp_path, {"status": "in_progress", "events": 5})
    cp = read_checkpoint(tmp_path)
    assert cp is not None
    assert cp["status"] == "in_progress"
    assert cp["events"] == 5


def test_read_checkpoint_corrupt_file(tmp_path):
    (tmp_path / SESSION_CHECKPOINT_FILE).write_text("not-json\n", encoding="utf-8")
    assert read_checkpoint(tmp_path) is None


# ── write_state / read_state ──────────────────────────────────────


def test_write_state_creates_file(tmp_path):
    st = write_state(tmp_path, {"status": "in_progress", "plan": "research"})
    assert (tmp_path / SESSION_STATE_FILE).exists()
    assert st["status"] == "in_progress"


def test_read_state_no_file(tmp_path):
    assert read_state(tmp_path) is None


def test_read_state_no_file_nonexistent_dir(tmp_path):
    assert read_state(tmp_path / "nonexistent") is None


def test_read_state_returns_content(tmp_path):
    write_state(tmp_path, {"status": "completed"})
    st = read_state(tmp_path)
    assert st is not None
    assert st["status"] == "completed"


def test_read_state_corrupt_file(tmp_path):
    (tmp_path / SESSION_STATE_FILE).write_text("broken", encoding="utf-8")
    assert read_state(tmp_path) is None


# ── create_digest ─────────────────────────────────────────────────


def test_create_digest_no_events(tmp_path):
    digest = create_digest(tmp_path)
    assert digest == ""


def test_create_digest_empty_events(tmp_path):
    (tmp_path / SESSION_EVENTS_FILE).write_text("", encoding="utf-8")
    assert create_digest(tmp_path) == ""


def test_create_digest_has_headers(tmp_path):
    append_event(tmp_path, "session_start", {"topic": "robotics"})
    append_event(tmp_path, "finding", {"text": "Found X"})
    digest = create_digest(tmp_path)
    assert "## Session Digest" in digest
    assert "robotics" in digest
    assert "Found X" in digest
    assert "session_start" in digest
    assert "finding" in digest


def test_create_digest_includes_checkpoint(tmp_path):
    write_checkpoint(tmp_path, {"status": "completed", "events": 2})
    append_event(tmp_path, "session_start", {})
    append_event(tmp_path, "finding", {"text": "discovery"})
    digest = create_digest(tmp_path)
    assert "completed" in digest
    assert "discovery" in digest


def test_create_digest_no_checkpoint_still_works(tmp_path):
    append_event(tmp_path, "finding", {"text": "something"})
    digest = create_digest(tmp_path)
    assert "something" in digest
    assert "Session Digest" in digest


# ── rehydrate ─────────────────────────────────────────────────────


def test_rehydrate_empty_dir(tmp_path):
    state = rehydrate(tmp_path)
    assert state["events"] == []
    assert state["checkpoint"] is None
    assert state["state"] is None
    assert state["digest"] == ""
    assert "event_count" in state


def test_rehydrate_no_checkpoint(tmp_path):
    append_event(tmp_path, "finding", {"text": "X"})
    state = rehydrate(tmp_path)
    assert len(state["events"]) == 1
    assert state["checkpoint"] is None
    assert state["event_count"] == 1
    assert "X" in state["digest"]


def test_rehydrate_full(tmp_path):
    write_state(tmp_path, {"status": "in_progress", "plan": "test"})
    write_checkpoint(tmp_path, {"status": "in_progress", "events": 2})
    append_event(tmp_path, "session_start", {"topic": "X"})
    append_event(tmp_path, "finding", {"text": "found Y"})
    state = rehydrate(tmp_path)
    assert state["event_count"] == 2
    assert state["checkpoint"]["status"] == "in_progress"
    assert state["state"]["plan"] == "test"
    assert "found Y" in state["digest"]


def test_rehydrate_nonexistent_dir(tmp_path):
    state = rehydrate(tmp_path / "nonexistent")
    assert state["events"] == []
    assert state["checkpoint"] is None
    assert state["state"] is None
    assert state["digest"] == ""
    assert state["event_count"] == 0


# ── timestamp format ──────────────────────────────────────────────


def test_append_event_iso_timestamp(tmp_path):
    ev = append_event(tmp_path, "test", {})
    assert "T" in ev["timestamp"], "expected ISO-8601 timestamp"
