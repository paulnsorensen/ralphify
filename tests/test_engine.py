"""Tests for the extracted run engine."""

import subprocess
import threading
import time
from unittest.mock import patch

from conftest import MOCK_SUBPROCESS, drain_events, fail_result, make_config, make_state, ok_result

from ralphify._events import EventType, NullEmitter, QueueEmitter
from ralphify._run_types import RunConfig, RunStatus
from ralphify._discovery import merge_by_name
from ralphify.engine import _resolve_ralph_dir, run_loop


class TestRunLoop:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_single_iteration(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        assert state.completed == 1
        assert state.failed == 0
        assert state.status == RunStatus.COMPLETED
        assert mock_run.call_count == 1

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_multiple_iterations(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=3)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.completed == 3
        assert mock_run.call_count == 3

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_failed_iterations_counted(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=2)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.completed == 0
        assert state.failed == 2

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_stop_on_error(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=5, stop_on_error=True)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert mock_run.call_count == 1
        assert state.failed == 1

    @patch(MOCK_SUBPROCESS)
    def test_timeout_counted(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=5)
        config = make_config(tmp_path, max_iterations=1, timeout=5)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.timed_out == 1
        assert state.failed == 1

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_prompt_text_overrides_file(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1, prompt_text="ad-hoc")
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert mock_run.call_args.kwargs["input"] == "ad-hoc"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_log_dir_creates_files(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="output\n", stderr=""
        )
        log_dir = tmp_path / "logs"
        config = make_config(tmp_path, max_iterations=2, log_dir=str(log_dir))
        state = make_state()

        run_loop(config, state, NullEmitter())

        log_files = sorted(log_dir.iterdir())
        assert len(log_files) == 2
        assert log_files[0].name.startswith("001_")
        assert log_files[1].name.startswith("002_")


class TestRunLoopEvents:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_events_emitted_in_order(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)

        types = [e.type for e in events]
        assert types[0] == EventType.RUN_STARTED
        assert EventType.ITERATION_STARTED in types
        assert EventType.PROMPT_ASSEMBLED in types
        assert EventType.ITERATION_COMPLETED in types
        assert types[-1] == EventType.RUN_STOPPED

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_failure_event_emitted(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)

        types = [e.type for e in events]
        assert EventType.ITERATION_FAILED in types

    @patch(MOCK_SUBPROCESS)
    def test_timeout_event_emitted(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=5)
        config = make_config(tmp_path, max_iterations=1, timeout=5)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)

        types = [e.type for e in events]
        assert EventType.ITERATION_TIMED_OUT in types

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_all_events_have_run_id(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        for event in drain_events(q):
            assert event.run_id == "test-run-001"


class TestRunStateControls:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_stop_request(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=100)
        state = make_state()

        # Request stop before starting (will stop at first iteration boundary)
        def stop_after_first(*args, **kwargs):
            state.request_stop()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = stop_after_first

        run_loop(config, state, NullEmitter())

        assert mock_run.call_count == 1
        assert state.status == RunStatus.STOPPED

    @patch(MOCK_SUBPROCESS)
    def test_keyboard_interrupt_sets_stopped(self, mock_run, tmp_path):
        """Ctrl+C should set status to STOPPED, not COMPLETED."""
        mock_run.side_effect = KeyboardInterrupt
        config = make_config(tmp_path, max_iterations=5)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        assert state.status == RunStatus.STOPPED

        events = drain_events(q)

        stop_event = [e for e in events if e.type == EventType.RUN_STOPPED][0]
        assert stop_event.data["reason"] == "user_requested"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_pause_and_resume(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=3)
        state = make_state()

        call_count = 0

        def track_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Pause after first iteration, resume shortly after
                state.request_pause()

                def resume_later():
                    time.sleep(0.1)
                    state.request_resume()

                threading.Thread(target=resume_later, daemon=True).start()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = track_calls

        run_loop(config, state, NullEmitter())

        assert state.completed == 3
        assert state.status == RunStatus.COMPLETED

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_reload_rediscovers_primitives(self, mock_run, tmp_path):
        (tmp_path / "RALPH.md").write_text("test prompt")
        config = make_config(tmp_path, max_iterations=2)
        state = make_state()
        q = QueueEmitter()

        call_count = 0

        def request_reload_on_first(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                state.request_reload()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = request_reload_on_first

        run_loop(config, state, q)

        events = drain_events(q)

        types = [e.type for e in events]
        assert EventType.PRIMITIVES_RELOADED in types

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_stop_while_paused(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=100)
        state = make_state()

        def pause_then_stop(*args, **kwargs):
            state.request_pause()

            def stop_later():
                time.sleep(0.1)
                state.request_stop()

            threading.Thread(target=stop_later, daemon=True).start()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = pause_then_stop

        run_loop(config, state, NullEmitter())

        assert state.status == RunStatus.STOPPED
        assert mock_run.call_count == 1


class TestPromptLocalPrimitives:
    """Tests for prompt-scoped primitive discovery and merge logic."""

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_prompt_local_contexts_merged(self, mock_run, tmp_path):
        """Both declared global and local contexts are discovered."""
        # Global context
        gc = tmp_path / ".ralphify" / "contexts" / "global-info"
        gc.mkdir(parents=True)
        (gc / "CONTEXT.md").write_text("---\n---\nGlobal info.")

        # Named prompt — declares global-info as a dependency
        ralph_dir = tmp_path / ".ralphify" / "ralphs" / "ui"
        ralph_dir.mkdir(parents=True)
        (ralph_dir / "RALPH.md").write_text("---\ncontexts: [global-info]\n---\n{{ contexts.global-info }}\n\nBuild the UI.\n\n{{ contexts.focus }}")

        # Local context
        lc = ralph_dir / "contexts" / "focus"
        lc.mkdir(parents=True)
        (lc / "CONTEXT.md").write_text("---\n---\nFocus on components.")

        config = make_config(
            tmp_path,
            ralph_file=str(ralph_dir / "RALPH.md"),
            ralph_name="ui",
            global_contexts=["global-info"],
            max_iterations=1,
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert "Global info." in call_input
        assert "Focus on components." in call_input

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_prompt_local_overrides_global(self, mock_run, tmp_path):
        """A prompt-local primitive with the same name replaces the global one."""
        # Global context
        gc = tmp_path / ".ralphify" / "contexts" / "info"
        gc.mkdir(parents=True)
        (gc / "CONTEXT.md").write_text("---\n---\nGlobal info.")

        # Named prompt — declares info as dependency, but local overrides it
        ralph_dir = tmp_path / ".ralphify" / "ralphs" / "ui"
        ralph_dir.mkdir(parents=True)
        (ralph_dir / "RALPH.md").write_text("---\ncontexts: [info]\n---\n{{ contexts.info }}\n\nBuild the UI.")

        # Local context with SAME name
        lc = ralph_dir / "contexts" / "info"
        lc.mkdir(parents=True)
        (lc / "CONTEXT.md").write_text("---\n---\nLocal info.")

        config = make_config(
            tmp_path,
            ralph_file=str(ralph_dir / "RALPH.md"),
            ralph_name="ui",
            global_contexts=["info"],
            max_iterations=1,
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert "Local info." in call_input
        assert "Global info." not in call_input

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_adhoc_prompt_gets_no_globals(self, mock_run, tmp_path):
        """Ad-hoc prompt text gets no global primitives (no frontmatter = no declarations)."""
        # Global context exists but should NOT be included
        gc = tmp_path / ".ralphify" / "contexts" / "info"
        gc.mkdir(parents=True)
        (gc / "CONTEXT.md").write_text("---\n---\nGlobal info.")

        config = make_config(
            tmp_path,
            prompt_text="ad-hoc prompt",
            ralph_name=None,
            max_iterations=1,
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert call_input == "ad-hoc prompt"
        assert "Global info." not in call_input

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_disabled_local_suppresses_global(self, mock_run, tmp_path):
        """A disabled local primitive with the same name hides the declared global."""
        # Global context (enabled)
        gc = tmp_path / ".ralphify" / "contexts" / "info"
        gc.mkdir(parents=True)
        (gc / "CONTEXT.md").write_text("---\n---\nGlobal info.")

        # Named prompt — declares info, but local disables it
        ralph_dir = tmp_path / ".ralphify" / "ralphs" / "ui"
        ralph_dir.mkdir(parents=True)
        (ralph_dir / "RALPH.md").write_text("---\ncontexts: [info]\n---\nBuild the UI.")

        # Local context: same name, disabled
        lc = ralph_dir / "contexts" / "info"
        lc.mkdir(parents=True)
        (lc / "CONTEXT.md").write_text("---\nenabled: false\n---\nLocal info.")

        config = make_config(
            tmp_path,
            ralph_file=str(ralph_dir / "RALPH.md"),
            ralph_name="ui",
            global_contexts=["info"],
            max_iterations=1,
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert "Global info." not in call_input
        assert "Local info." not in call_input

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_reload_rediscovers_local(self, mock_run, tmp_path):
        """Reload should re-discover prompt-local primitives."""
        # Named prompt
        ralph_dir = tmp_path / ".ralphify" / "ralphs" / "ui"
        ralph_dir.mkdir(parents=True)
        (ralph_dir / "RALPH.md").write_text("---\n---\nBuild the UI.\n\n{{ contexts.new-focus }}")

        config = make_config(
            tmp_path,
            ralph_file=str(ralph_dir / "RALPH.md"),
            ralph_name="ui",
            max_iterations=2,
        )
        state = make_state()
        q = QueueEmitter()

        call_count = 0

        def add_local_on_first(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Add a local context and request reload
                lc = ralph_dir / "contexts" / "new-focus"
                lc.mkdir(parents=True)
                (lc / "CONTEXT.md").write_text("---\n---\nNew focus.")
                state.request_reload()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = add_local_on_first

        run_loop(config, state, q)

        events = drain_events(q)

        types = [e.type for e in events]
        assert EventType.PRIMITIVES_RELOADED in types

        # Second call should include the new context
        second_call_input = mock_run.call_args.kwargs["input"]
        assert "New focus." in second_call_input


class TestMergeByName:
    """Unit tests for merge_by_name helper."""

    def test_local_wins_on_name_conflict(self):
        from ralphify.contexts import Context
        from pathlib import Path

        global_list = [
            Context(name="info", path=Path("/g/info"), static_content="Global."),
            Context(name="other", path=Path("/g/other"), static_content="Other."),
        ]
        local_list = [
            Context(name="info", path=Path("/l/info"), static_content="Local."),
        ]
        merged = merge_by_name(global_list, local_list)
        assert len(merged) == 2
        by_name = {p.name: p for p in merged}
        assert by_name["info"].static_content == "Local."
        assert by_name["other"].static_content == "Other."

    def test_sorted_by_name(self):
        from ralphify.contexts import Context
        from pathlib import Path

        global_list = [
            Context(name="zebra", path=Path("/g/z"), static_content="Z."),
        ]
        local_list = [
            Context(name="alpha", path=Path("/l/a"), static_content="A."),
        ]
        merged = merge_by_name(global_list, local_list)
        assert [p.name for p in merged] == ["alpha", "zebra"]

    def test_empty_lists(self):
        assert merge_by_name([], []) == []


class TestResolveRalphDir:
    """Unit tests for _resolve_ralph_dir helper."""

    def test_named_ralph_returns_parent(self):
        from pathlib import Path
        config = RunConfig(
            command="echo", args=[],
            ralph_file="/project/.ralphify/ralphs/ui/RALPH.md",
            ralph_name="ui",
        )
        result = _resolve_ralph_dir(config)
        assert result == Path("/project/.ralphify/ralphs/ui")

    def test_adhoc_text_returns_none(self):
        config = RunConfig(
            command="echo", args=[],
            ralph_file="RALPH.md",
            prompt_text="ad-hoc",
            ralph_name="ui",
        )
        assert _resolve_ralph_dir(config) is None

    def test_no_ralph_name_returns_none(self):
        config = RunConfig(
            command="echo", args=[],
            ralph_file="RALPH.md",
        )
        assert _resolve_ralph_dir(config) is None


class TestRalphNameEnv:
    """Tests that ralph_name flows to context and check subprocesses."""

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_ralph_name_passed_to_context_scripts(self, mock_run, tmp_path):
        """When ralph_name is set, context scripts receive RALPH_NAME env var."""
        # Create a context with a command
        ctx_dir = tmp_path / ".ralphify" / "contexts" / "test-ctx"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "CONTEXT.md").write_text("---\ncommand: echo hi\n---\n")

        config = make_config(
            tmp_path, ralph_name="docs", max_iterations=1,
            global_contexts=["test-ctx"],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        # Find the context subprocess call (first call before the agent call)
        context_call = mock_run.call_args_list[0]
        assert context_call.kwargs["env"]["RALPH_NAME"] == "docs"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_ralph_name_passed_to_check_scripts(self, mock_run, tmp_path):
        """When ralph_name is set, check scripts receive RALPH_NAME env var."""
        # Create a check with a command
        check_dir = tmp_path / ".ralphify" / "checks" / "test-chk"
        check_dir.mkdir(parents=True)
        (check_dir / "CHECK.md").write_text("---\ncommand: echo ok\n---\n")

        config = make_config(
            tmp_path, ralph_name="docs", max_iterations=1,
            global_checks=["test-chk"],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        # The check call is after the agent call
        check_call = mock_run.call_args_list[-1]
        assert check_call.kwargs["env"]["RALPH_NAME"] == "docs"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_no_ralph_name_no_env(self, mock_run, tmp_path):
        """When ralph_name is None, no custom env is passed."""
        ctx_dir = tmp_path / ".ralphify" / "contexts" / "test-ctx"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "CONTEXT.md").write_text("---\ncommand: echo hi\n---\n")

        config = make_config(
            tmp_path, ralph_name=None, max_iterations=1,
            global_contexts=["test-ctx"],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        context_call = mock_run.call_args_list[0]
        assert context_call.kwargs["env"] is None
