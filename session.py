"""Session state machine — event logging, checkpointing, digest, rehydration.

Provides a standalone session management layer for wiki research/thesis
sessions with append-only event logging, checkpoint snapshots, ephemeral
state files, markdown digest generation, and full rehydration.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "SESSION_EVENTS_FILE",
    "SESSION_CHECKPOINT_FILE",
    "SESSION_STATE_FILE",
    "append_event",
    "read_events",
    "write_checkpoint",
    "read_checkpoint",
    "write_state",
    "read_state",
    "create_digest",
    "rehydrate",
]

SESSION_EVENTS_FILE = ".session-events.jsonl"
SESSION_CHECKPOINT_FILE = ".session-checkpoint.json"
SESSION_STATE_FILE = ".research-session.json"


def _session_dir(path: str | Path) -> Path:
    return Path(path)


def _events_path(path: str | Path) -> Path:
    return _session_dir(path) / SESSION_EVENTS_FILE


def _checkpoint_path(path: str | Path) -> Path:
    return _session_dir(path) / SESSION_CHECKPOINT_FILE


def _state_path(path: str | Path) -> Path:
    return _session_dir(path) / SESSION_STATE_FILE


def append_event(
    session_dir: str | Path,
    event_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Append a single JSON event line to .session-events.jsonl.

    Returns the event dict (with auto-generated timestamp).
    """
    p = _session_dir(session_dir)
    p.mkdir(parents=True, exist_ok=True)
    event = {
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    path = _events_path(session_dir)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
    return event


def read_events(session_dir: str | Path) -> list[dict[str, Any]]:
    """Read all events from .session-events.jsonl. Corrupt lines are skipped."""
    p = _events_path(session_dir)
    if not p.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def write_checkpoint(
    session_dir: str | Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Write .session-checkpoint.json with the given summary dict."""
    p = _session_dir(session_dir)
    p.mkdir(parents=True, exist_ok=True)
    (_checkpoint_path(session_dir)).write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def read_checkpoint(session_dir: str | Path) -> dict[str, Any] | None:
    """Read .session-checkpoint.json, or None if missing or corrupt."""
    p = _checkpoint_path(session_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_state(
    session_dir: str | Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Write ephemeral session state to .research-session.json."""
    p = _session_dir(session_dir)
    p.mkdir(parents=True, exist_ok=True)
    (_state_path(session_dir)).write_text(
        json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return state


def read_state(session_dir: str | Path) -> dict[str, Any] | None:
    """Read .research-session.json, or None if missing or corrupt."""
    p = _state_path(session_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def create_digest(session_dir: str | Path) -> str:
    """Generate a markdown digest from events and checkpoint."""
    events = read_events(session_dir)
    if not events:
        return ""

    lines: list[str] = []
    lines.append("## Session Digest")
    lines.append("")

    cp = read_checkpoint(session_dir)
    if cp:
        lines.append("### Checkpoint")
        lines.append("")
        for k, v in cp.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines.append(f"### Events ({len(events)} total)")
    lines.append("")
    for ev in events:
        ts = ev.get("timestamp", "")
        etype = ev.get("event_type", "?")
        data = ev.get("data", {})
        data_str = ", ".join(f"{k}={v}" for k, v in data.items()) if data else ""
        line = f"- `{ts}` **{etype}**"
        if data_str:
            line += f" — {data_str}"
        lines.append(line)

    return "\n".join(lines) + "\n"


def rehydrate(session_dir: str | Path) -> dict[str, Any]:
    """Rehydrate full session context from events, checkpoint, and state.

    Returns a dict with keys: events, checkpoint, state, digest, event_count.
    """
    events = read_events(session_dir)
    cp = read_checkpoint(session_dir)
    st = read_state(session_dir)
    digest = create_digest(session_dir)

    return {
        "events": events,
        "checkpoint": cp,
        "state": st,
        "digest": digest,
        "event_count": len(events),
    }
