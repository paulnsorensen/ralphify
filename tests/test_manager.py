"""Tests for the multi-run manager."""

import subprocess
import threading
import time
from unittest.mock import patch

from helpers import MOCK_SUBPROCESS, drain_events, make_config, ok_result

from ralphify._events import EventType, QueueEmitter
from ralphify._run_types import RUN_ID_LENGTH, RunStatus
from ralphify.manager import ManagedRun, RunManager


class TestRunManagerCreateRun:
    def test_create_run_returns_managed_run(self, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path)
        managed = manager.create_run(config)

        assert isinstance(managed, ManagedRun)
        assert managed.config is config
        assert managed.state.status == RunStatus.PENDING
        assert managed.thread is None
        assert isinstance(managed.emitter, QueueEmitter)

    def test_create_run_assigns_unique_ids(self, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path)
        run1 = manager.create_run(config)
        run2 = manager.create_run(config)

        assert run1.state.run_id != run2.state.run_id

    def test_create_run_id_is_12_hex_chars(self, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path)
        managed = manager.create_run(config)

        run_id = managed.state.run_id
        assert len(run_id) == RUN_ID_LENGTH
        assert all(c in "0123456789abcdef" for c in run_id)


class TestRunManagerStartRun:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_start_run_starts_thread(self, mock_run, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path, max_iterations=1)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        manager.start_run(run_id)

        assert managed.thread is not None
        managed.thread.join(timeout=5)
        assert managed.state.status == RunStatus.COMPLETED

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_start_run_thread_is_daemon(self, mock_run, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path, max_iterations=1)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        manager.start_run(run_id)

        assert managed.thread is not None
        assert managed.thread.daemon is True
        managed.thread.join(timeout=5)

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_start_run_emits_events_to_queue(self, mock_run, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path, max_iterations=1)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        manager.start_run(run_id)
        assert managed.thread is not None
        managed.thread.join(timeout=5)

        events = drain_events(managed.emitter)
        types = [e.type for e in events]
        assert EventType.RUN_STARTED in types
        assert EventType.RUN_STOPPED in types


class TestRunManagerStopRun:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_stop_run_stops_running_run(self, mock_run, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path, max_iterations=100, delay=0.1)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        manager.start_run(run_id)
        time.sleep(0.05)

        manager.stop_run(run_id)
        assert managed.thread is not None
        managed.thread.join(timeout=5)

        assert managed.state.status == RunStatus.STOPPED


class TestRunManagerPauseResume:
    @patch(MOCK_SUBPROCESS)
    def test_pause_and_resume(self, mock_run, tmp_path):
        pause_done = threading.Event()
        resume_allowed = threading.Event()
        call_count = 0

        def counting_ok(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                pause_done.set()
                resume_allowed.wait(timeout=5)
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = counting_ok

        manager = RunManager()
        config = make_config(tmp_path, max_iterations=3)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        manager.start_run(run_id)

        pause_done.wait(timeout=5)
        manager.pause_run(run_id)
        assert managed.state.status == RunStatus.PAUSED

        resume_allowed.set()
        time.sleep(0.05)
        manager.resume_run(run_id)

        assert managed.thread is not None
        managed.thread.join(timeout=5)
        assert managed.state.completed == 3


class TestRunManagerListAndGet:
    def test_list_runs_returns_all_runs(self, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path)

        managed1 = manager.create_run(config)
        managed2 = manager.create_run(config)
        managed3 = manager.create_run(config)

        runs = manager.list_runs()
        assert len(runs) == 3
        run_ids = {r.state.run_id for r in runs}
        assert managed1.state.run_id in run_ids
        assert managed2.state.run_id in run_ids
        assert managed3.state.run_id in run_ids

    def test_list_runs_empty(self):
        manager = RunManager()
        assert manager.list_runs() == []

    def test_get_run_returns_correct_run(self, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        result = manager.get_run(run_id)
        assert result is managed

    def test_get_run_returns_none_for_unknown_id(self):
        manager = RunManager()
        assert manager.get_run("nonexistent") is None


class TestRunManagerExtraListeners:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_extra_listeners_receive_events(self, mock_run, tmp_path):
        manager = RunManager()
        config = make_config(tmp_path, max_iterations=1)
        managed = manager.create_run(config)
        run_id = managed.state.run_id

        extra = QueueEmitter()
        managed.add_listener(extra)

        manager.start_run(run_id)
        assert managed.thread is not None
        managed.thread.join(timeout=5)

        primary_events = drain_events(managed.emitter)
        extra_events = drain_events(extra)

        assert len(primary_events) > 0
        assert len(extra_events) == len(primary_events)
