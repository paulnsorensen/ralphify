"""Canned fixtures used by the TUI dev harness.

Two flavours of fixture live here:

1. **Peek-panel scenarios** (``ALL_SCENARIOS``): lists of parsed Claude
   stream-json dicts.  The snapshot harness feeds them through a real
   ``_IterationPanel`` so they exercise the live activity feed.

2. **Event-sequence scenarios** (``EVENT_SCENARIOS``): lists of
   ``(EventType, dict)`` tuples.  The snapshot harness drives the
   emitter through these events and captures whatever ends up on the
   recording console — used for iterating on iteration result lines,
   run summaries, error logs, etc.

Add new scenarios to either dict and rerun
``./scripts/tui_dev/run.sh snapshot``.
"""

from __future__ import annotations

from typing import Any

from ralphify._events import EventType

# ── Shared event builders ─────────────────────────────────────────────

MODEL = "claude-opus-4-6"


def system_init(model: str = MODEL) -> dict[str, Any]:
    return {"type": "system", "subtype": "init", "model": model}


def assistant_tool_use(
    name: str,
    tool_input: dict[str, Any],
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "content": [{"type": "tool_use", "name": name, "input": tool_input}],
    }
    if input_tokens or output_tokens or cache_read:
        msg["usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
        }
    return {"type": "assistant", "message": msg}


def assistant_text(text: str, **usage: int) -> dict[str, Any]:
    msg: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if usage:
        msg["usage"] = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read", 0),
        }
    return {"type": "assistant", "message": msg}


def assistant_thinking() -> dict[str, Any]:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "thinking", "thinking": "..."}]},
    }


def rate_limit(
    status: str = "approaching", resets_at: str = "2026-04-11T10:00Z"
) -> dict[str, Any]:
    return {
        "type": "rate_limit_event",
        "rate_limit_info": {"status": status, "resetsAt": resets_at},
    }


def result(text: str) -> dict[str, Any]:
    return {"type": "result", "result": text}


# ── Scenarios ──────────────────────────────────────────────────────────

# Each scenario is a list of (label, events_up_to_this_point) tuples.
# A single scenario runs multiple snapshots to show peek evolution over time.


def scenario_empty() -> list[dict[str, Any]]:
    """Peek just toggled on — panel exists, but zero scroll lines yet.

    Hits the ``_peek_message`` branch in ``_IterationPanel.__rich_console__``.
    """
    return [system_init()]


def scenario_single_tool() -> list[dict[str, Any]]:
    """One tool call — the most common first moment after peek turns on."""
    return [
        system_init(),
        assistant_tool_use(
            "Read",
            {"file_path": "/Users/kasper/Code/ralphify/src/ralphify/cli.py"},
            input_tokens=2_450,
            output_tokens=180,
            cache_read=15_000,
        ),
    ]


def scenario_mixed_activity() -> list[dict[str, Any]]:
    """Realistic mid-iteration state: thinking, several tools, text preview."""
    return [
        system_init(),
        assistant_thinking(),
        assistant_tool_use(
            "Read",
            {
                "file_path": "/Users/kasper/Code/ralphify/src/ralphify/_console_emitter.py"
            },
            input_tokens=3_200,
            output_tokens=210,
            cache_read=18_000,
        ),
        assistant_tool_use(
            "Grep",
            {"pattern": "_IterationPanel"},
            input_tokens=3_400,
            output_tokens=250,
            cache_read=18_000,
        ),
        assistant_text(
            "Looking at the iteration panel — I see three distinct layout sections that could be tightened.",
            input_tokens=3_600,
            output_tokens=420,
            cache_read=18_000,
        ),
        assistant_tool_use(
            "Edit",
            {
                "file_path": "/Users/kasper/Code/ralphify/src/ralphify/_console_emitter.py"
            },
            input_tokens=3_900,
            output_tokens=520,
            cache_read=18_000,
        ),
        assistant_tool_use(
            "Bash",
            {"command": "uv run pytest tests/test_console_emitter.py -x"},
            input_tokens=4_100,
            output_tokens=560,
            cache_read=18_000,
        ),
    ]


def scenario_scroll_buffer_full() -> list[dict[str, Any]]:
    """17 tool calls — exceeds _MAX_VISIBLE_SCROLL (10) so oldest scroll off."""
    events: list[dict[str, Any]] = [system_init()]
    files = [
        "cli.py",
        "engine.py",
        "manager.py",
        "_frontmatter.py",
        "_run_types.py",
        "_resolver.py",
        "_agent.py",
        "_runner.py",
        "_events.py",
        "_console_emitter.py",
        "_output.py",
        "_brand.py",
        "_keypress.py",
        "__init__.py",
        "__main__.py",
        "py.typed",
    ]
    tokens = 1_000
    for i, name in enumerate(files):
        tokens += 250
        events.append(
            assistant_tool_use(
                "Read",
                {"file_path": f"/Users/kasper/Code/ralphify/src/ralphify/{name}"},
                input_tokens=tokens,
                output_tokens=i * 40,
                cache_read=20_000,
            )
        )
    events.append(
        assistant_tool_use(
            "Grep",
            {"pattern": "PEEK_TOGGLE_KEY"},
            input_tokens=tokens + 300,
            output_tokens=len(files) * 40 + 80,
            cache_read=20_000,
        )
    )
    return events


def scenario_heavy_tokens() -> list[dict[str, Any]]:
    """Long-running iteration with 1M+ token context."""
    return [
        system_init(),
        assistant_tool_use(
            "Read",
            {
                "file_path": "/Users/kasper/Code/ralphify/docs/contributing/codebase-map.md"
            },
            input_tokens=850_000,
            output_tokens=12_500,
            cache_read=820_000,
        ),
        assistant_tool_use(
            "Grep",
            {"pattern": "class _IterationPanel"},
            input_tokens=1_050_000,
            output_tokens=14_800,
            cache_read=1_020_000,
        ),
        assistant_text(
            "I have enough context now — drafting the refactor plan.",
            input_tokens=1_120_000,
            output_tokens=18_400,
            cache_read=1_080_000,
        ),
    ]


def scenario_rate_limit() -> list[dict[str, Any]]:
    """Rate-limit event during an otherwise normal iteration."""
    return [
        system_init(),
        assistant_tool_use(
            "Bash",
            {"command": "uv run pytest tests/ -x"},
            input_tokens=4_500,
            output_tokens=320,
            cache_read=18_000,
        ),
        rate_limit(status="approaching", resets_at="2026-04-11T10:30Z"),
        assistant_text(
            "Rate limit warning received — continuing cautiously.",
            input_tokens=4_600,
            output_tokens=380,
            cache_read=18_000,
        ),
    ]


def scenario_tool_error() -> list[dict[str, Any]]:
    """Tool returned an error — exercises the red tool_result branch."""
    return [
        system_init(),
        assistant_tool_use(
            "Bash",
            {"command": "uv run pytest tests/test_peek.py"},
            input_tokens=3_100,
            output_tokens=220,
            cache_read=15_000,
        ),
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "is_error": True,
                        "content": "ERROR: file or directory not found: tests/test_peek.py",
                    }
                ]
            },
        },
        assistant_text(
            "That file doesn't exist — let me list the tests directory instead.",
            input_tokens=3_250,
            output_tokens=290,
            cache_read=15_000,
        ),
    ]


ALL_SCENARIOS: dict[str, list[dict[str, Any]]] = {
    "01_empty": scenario_empty(),
    "02_single_tool": scenario_single_tool(),
    "03_mixed_activity": scenario_mixed_activity(),
    "04_scroll_buffer_full": scenario_scroll_buffer_full(),
    "05_heavy_tokens": scenario_heavy_tokens(),
    "06_rate_limit": scenario_rate_limit(),
    "07_tool_error": scenario_tool_error(),
    # 09_peek_off reuses 03's event sequence — the snapshot harness
    # toggles peek off after applying it so the panel renders the
    # "peek off" placeholder *with* the underlying buffer intact.
    "09_peek_off": scenario_mixed_activity(),
}


# ── Event-sequence scenarios ──────────────────────────────────────────
#
# These don't touch the peek panel — they drive arbitrary event types
# through the emitter and capture whatever it prints to the console.
# Use them when iterating on terminal output that *isn't* the live peek
# region: iteration result lines, run summaries, error logs, markdown
# results, etc.


def _run_started(ralph_name: str, **overrides: Any) -> tuple[EventType, dict[str, Any]]:
    data: dict[str, Any] = {
        "ralph_name": ralph_name,
        "agent": "claude --output-format stream-json",
        "commands": 2,
        "max_iterations": None,
        "timeout": 600.0,
        "delay": 0.0,
    }
    data.update(overrides)
    return EventType.RUN_STARTED, data


def events_iteration_success() -> list[tuple[EventType, dict[str, Any]]]:
    """Happy path: a single iteration completes with a markdown result."""
    return [
        _run_started("demo / 10_iteration_success"),
        (EventType.ITERATION_STARTED, {"iteration": 1}),
        (
            EventType.ITERATION_COMPLETED,
            {
                "iteration": 1,
                "detail": "completed (1m 24s)",
                "log_file": None,
                "result_text": (
                    "## Summary\n\n"
                    "- Implemented the new feature\n"
                    "- Added 4 tests\n"
                    "- All tests pass\n"
                ),
            },
        ),
        (
            EventType.RUN_STOPPED,
            {
                "reason": "completed",
                "total": 1,
                "completed": 1,
                "failed": 0,
                "timed_out_count": 0,
            },
        ),
    ]


def events_iteration_failed() -> list[tuple[EventType, dict[str, Any]]]:
    """An iteration fails with an exit code and a log file path."""
    return [
        _run_started("demo / 11_iteration_failed"),
        (EventType.ITERATION_STARTED, {"iteration": 1}),
        (
            EventType.ITERATION_FAILED,
            {
                "iteration": 1,
                "detail": "failed with exit code 2 (43s)",
                "log_file": "/Users/kasper/Code/ralphify/logs/run-001.log",
                "result_text": None,
            },
        ),
        (
            EventType.RUN_STOPPED,
            {
                "reason": "completed",
                "total": 1,
                "completed": 0,
                "failed": 1,
                "timed_out_count": 0,
            },
        ),
    ]


def events_iteration_timeout() -> list[tuple[EventType, dict[str, Any]]]:
    """An iteration times out — exercises the yellow timeout branch."""
    return [
        _run_started("demo / 12_iteration_timeout", timeout=120.0),
        (EventType.ITERATION_STARTED, {"iteration": 1}),
        (
            EventType.ITERATION_TIMED_OUT,
            {
                "iteration": 1,
                "detail": "timed out after 2m 0s",
                "log_file": None,
                "result_text": None,
            },
        ),
        (
            EventType.RUN_STOPPED,
            {
                "reason": "completed",
                "total": 1,
                "completed": 0,
                "failed": 1,
                "timed_out_count": 1,
            },
        ),
    ]


def events_run_summary_mixed() -> list[tuple[EventType, dict[str, Any]]]:
    """A multi-iteration run with mixed success/failure/timeout outcomes."""
    return [
        _run_started("demo / 13_run_summary_mixed", max_iterations=4),
        (EventType.ITERATION_STARTED, {"iteration": 1}),
        (
            EventType.ITERATION_COMPLETED,
            {
                "iteration": 1,
                "detail": "completed (52s)",
                "log_file": None,
                "result_text": None,
            },
        ),
        (EventType.ITERATION_STARTED, {"iteration": 2}),
        (
            EventType.ITERATION_COMPLETED,
            {
                "iteration": 2,
                "detail": "completed (1m 7s)",
                "log_file": None,
                "result_text": None,
            },
        ),
        (EventType.ITERATION_STARTED, {"iteration": 3}),
        (
            EventType.ITERATION_FAILED,
            {
                "iteration": 3,
                "detail": "failed with exit code 1 (38s)",
                "log_file": None,
                "result_text": None,
            },
        ),
        (EventType.ITERATION_STARTED, {"iteration": 4}),
        (
            EventType.ITERATION_TIMED_OUT,
            {
                "iteration": 4,
                "detail": "timed out after 2m 0s",
                "log_file": None,
                "result_text": None,
            },
        ),
        (
            EventType.RUN_STOPPED,
            {
                "reason": "completed",
                "total": 4,
                "completed": 2,
                "failed": 2,
                "timed_out_count": 1,
            },
        ),
    ]


def events_log_error() -> list[tuple[EventType, dict[str, Any]]]:
    """An error log message with a traceback — exercises the red branch."""
    return [
        _run_started("demo / 14_log_error"),
        (
            EventType.LOG_MESSAGE,
            {
                "message": "Run crashed: KeyError('agent')",
                "level": "error",
                "traceback": (
                    "Traceback (most recent call last):\n"
                    '  File "/src/ralphify/engine.py", line 142, in run_loop\n'
                    "    agent = config['agent']\n"
                    "KeyError: 'agent'"
                ),
            },
        ),
    ]


EVENT_SCENARIOS: dict[str, list[tuple[EventType, dict[str, Any]]]] = {
    "10_iteration_success": events_iteration_success(),
    "11_iteration_failed": events_iteration_failed(),
    "12_iteration_timeout": events_iteration_timeout(),
    "13_run_summary_mixed": events_run_summary_mixed(),
    "14_log_error": events_log_error(),
}
