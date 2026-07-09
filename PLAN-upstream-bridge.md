# Plan: Invoke Upstream llm_wiki_session.py as Subprocess from Hermes Hooks

## Context

Our Hermes adapter hooks are mostly no-ops. The upstream nvk/llm-wiki has a
production `llm_wiki_session.py` (~1700 lines) that handles all session capture
logic: event recording, state tracking, digest writing, feedback classification,
rehydration context, and index management. This script is designed to be invoked
as a subprocess — it reads JSON from stdin, writes files to `HUB/.sessions/`, and
optionally outputs JSON to stdout for context injection.

Currently cloned at `/tmp/llm-wiki-upstream` for reference (not committed).

## Hook Mapping

| Hermes Hook | Upstream Event | Return Value |
|---|---|---|
| `pre_llm_call` | `UserPromptSubmit` | string → injected into user message |
| `on_session_start` | `SessionStart` | string → injected into user message |
| `post_tool_call` | `PostToolUse` | None (side-effects only) |
| `on_session_finalize` | `PreCompact` | None (digest writing) |
| `on_session_end` | `SessionEnd` | None (final digest + checkpoint) |

## Upstream Protocol

The upstream script expects:
- **Command**: `python3 llm_wiki_session.py hook --harness codex --if-enabled`
- **stdin**: JSON object with hook metadata (session_id, hook_event_name, cwd, model, tool_name, etc.)
- **stdout**: JSON with `hookSpecificOutput.hookEventName.additionalContext` for SessionStart/UserPromptSubmit; empty for others
- **`--if-enabled`**: exits silently (code 0) if `HUB/.sessions/config.json` has `enabled: false`

The upstream's `normalize_event()` function accepts these payload keys:
- `session_id` / `sessionId` — session identifier
- `hook_event_name` / `hookEventName` / `event` — event name
- `cwd` — working directory
- `model` — model name
- `tool_name` / `toolName` / `tool` — tool name (for PostToolUse)
- `turn_id` / `turnId` — turn identifier
- `transcript_path` / `transcriptPath` — transcript file path

## Hermes Hook Kwargs (from source analysis)

### `pre_llm_call` (turn_context.py:434-446)
```
session_id, task_id, turn_id, user_message, conversation_history,
is_first_turn, model, platform, sender_id
```
Return: `str` or `{"context": str}` → injected into user message

### `on_session_start` (run_agent.py:668-680)
```
session_id (positional), old_session_id, carry_over_context,
platform, model, context_length, conversation_id
```
Return: used by context engine, not injected into prompt directly

### `post_tool_call` (model_tools.py:884-899)
```
tool_name, args, result, task_id, session_id, tool_call_id,
turn_id, api_request_id, duration_ms, status, error_type,
error_message, middleware_trace
```
Return: None (observer hook)

### `on_session_finalize` (test_session_boundary_hooks.py)
```
session_id, platform, reason
```
Return: None

### `on_session_end` (test_session_boundary_hooks.py)
```
session_id, task_id, turn_id, api_request_id, completed,
interrupted, reason, model, platform
```
Return: None

## Implementation Plan

### 1. `hooks/upstream_bridge.py` — Subprocess Bridge Module

New module that:
- Locates the upstream `llm_wiki_session.py` script (bundled with the plugin)
- Builds the upstream-compatible JSON payload from Hermes kwargs
- Invokes the subprocess with correct args
- Parses stdout for context injection (pre_llm_call, on_session_start)
- Handles timeouts, missing script, and errors gracefully
- Provides `invoke(event_name, **kwargs)` → `str | None` interface

Key design:
- Bundle `llm_wiki_session.py` into the plugin's `hooks/` directory
- Use `__file__` to locate the bundled script relative to the bridge module
- 3-second timeout (upstream uses 5s for shell hooks, but we're in-process)
- Return `None` on any failure (the hook must never crash the agent)

### 2. Update `hooks/system_prompt.py` (`pre_llm_call`)

Replace static string with:
```python
def pre_llm_call(**kwargs):
    ctx = upstream_bridge.invoke("UserPromptSubmit", **kwargs)
    if ctx:
        return ctx
    return "Wiki hub at ~/wiki. Session capture active."
```

### 3. Update `hooks/prefetch.py` (`on_session_start`)

Replace checkpoint read with:
```python
def on_session_start(session_id="", **kwargs):
    return upstream_bridge.invoke("SessionStart", session_id=session_id, **kwargs)
```

### 4. Update `hooks/sync_turn.py` (`post_tool_call`)

Replace direct event writing with:
```python
def post_tool_call(session_id="", tool_name="", **kwargs):
    upstream_bridge.invoke("PostToolUse", session_id=session_id, tool_name=tool_name, **kwargs)
```

### 5. Update `hooks/on_session_end.py` (`on_session_end`)

Replace manual digest writing with:
```python
def on_session_end(session_id="", **kwargs):
    upstream_bridge.invoke("SessionEnd", session_id=session_id, **kwargs)
```

### 6. Update `__init__.py`

Replace the `on_session_finalize` lambda with a bridge call:
```python
from hooks.upstream_bridge import invoke as upstream_invoke

ctx.register_hook(
    "on_session_finalize",
    lambda **kw: upstream_invoke("PreCompact", **kw),
)
```

### 7. Bundle the upstream script

Copy `llm_wiki_session.py` from upstream into `hooks/llm_wiki_session.py`.
The bridge will locate it via `Path(__file__).parent / "llm_wiki_session.py"`.

### 8. Update `tests/test_hooks.py`

- Mock `subprocess.run` to verify correct invocation
- Test payload construction for each event type
- Test graceful fallback when script is missing
- Test timeout handling
- Keep existing structural tests (file creation, digest format)

## Files Changed

| File | Change |
|---|---|
| `hooks/llm_wiki_session.py` | NEW — bundled upstream script |
| `hooks/upstream_bridge.py` | NEW — subprocess bridge |
| `hooks/system_prompt.py` | REPLACE — delegate to bridge |
| `hooks/prefetch.py` | REPLACE — delegate to bridge |
| `hooks/sync_turn.py` | REPLACE — delegate to bridge |
| `hooks/on_session_end.py` | REPLACE — delegate to bridge |
| `__init__.py` | MODIFY — on_session_finalize bridge |
| `tests/test_hooks.py` | MODIFY — mock subprocess, test bridge |
| `.gitignore` | ADD — exclude `__pycache__` in hooks/ |

## Risks & Mitigations

1. **Upstream script availability**: The script must be bundled. If missing,
   bridge returns `None` and falls back to current behavior.
2. **Subprocess overhead**: Each hook spawns a process. Mitigated by 3s timeout
   and the script being a simple Python CLI (fast cold start).
3. **Upstream changes**: The script is bundled at a specific version. We track
   the commit in `upstream.lock.json`.
4. **Concurrent hooks**: The upstream uses atomic file writes (temp + rename),
   safe for concurrent access.
