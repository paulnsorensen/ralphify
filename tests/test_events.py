"""Tests for the event types and emitter implementations."""

import queue
from datetime import datetime, timezone

from ralphify._events import Event, EventType, FanoutEmitter, NullEmitter, QueueEmitter


class TestEvent:
    def test_to_dict_serialization(self):
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        event = Event(
            type=EventType.RUN_STARTED,
            run_id="abc123",
            data={"max_iterations": 5},
            timestamp=ts,
        )
        result = event.to_dict()

        assert result["type"] == "run_started"
        assert result["run_id"] == "abc123"
        assert result["data"] == {"max_iterations": 5}
        assert result["timestamp"] == "2025-01-15T12:00:00+00:00"

    def test_to_dict_empty_data(self):
        event = Event(type=EventType.RUN_STOPPED, run_id="x")

        result = event.to_dict()

        assert result["data"] == {}
        assert result["type"] == "run_stopped"

    def test_default_data_is_empty_dict(self):
        event = Event(type=EventType.LOG_MESSAGE, run_id="r1")
        assert event.data == {}

    def test_default_timestamp_is_utc(self):
        event = Event(type=EventType.RUN_STARTED, run_id="r1")
        assert event.timestamp.tzinfo == timezone.utc


class TestNullEmitter:
    def test_emit_does_not_raise(self):
        emitter = NullEmitter()
        event = Event(type=EventType.RUN_STARTED, run_id="x")
        emitter.emit(event)  # should not raise


class TestQueueEmitter:
    def test_emit_pushes_to_queue(self):
        emitter = QueueEmitter()
        event = Event(type=EventType.ITERATION_STARTED, run_id="r1", data={"iteration": 1})

        emitter.emit(event)

        assert not emitter.queue.empty()
        assert emitter.queue.get() is event

    def test_multiple_events_queued_in_order(self):
        emitter = QueueEmitter()
        e1 = Event(type=EventType.RUN_STARTED, run_id="r1")
        e2 = Event(type=EventType.ITERATION_STARTED, run_id="r1")
        e3 = Event(type=EventType.RUN_STOPPED, run_id="r1")

        emitter.emit(e1)
        emitter.emit(e2)
        emitter.emit(e3)

        assert emitter.queue.get() is e1
        assert emitter.queue.get() is e2
        assert emitter.queue.get() is e3

    def test_accepts_external_queue(self):
        q: queue.Queue[Event] = queue.Queue()
        emitter = QueueEmitter(q)
        event = Event(type=EventType.RUN_STARTED, run_id="r1")

        emitter.emit(event)

        assert q.get() is event


class TestFanoutEmitter:
    def test_broadcasts_to_all_emitters(self):
        q1 = QueueEmitter()
        q2 = QueueEmitter()
        fanout = FanoutEmitter([q1, q2])
        event = Event(type=EventType.RUN_STARTED, run_id="r1")

        fanout.emit(event)

        assert q1.queue.get() is event
        assert q2.queue.get() is event

    def test_empty_emitters_list(self):
        fanout = FanoutEmitter([])
        event = Event(type=EventType.RUN_STARTED, run_id="r1")
        fanout.emit(event)  # should not raise

    def test_fanout_with_null_emitter(self):
        null = NullEmitter()
        q = QueueEmitter()
        fanout = FanoutEmitter([null, q])
        event = Event(type=EventType.ITERATION_COMPLETED, run_id="r1")

        fanout.emit(event)

        assert q.queue.get() is event
