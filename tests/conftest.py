"""Shared pytest fixtures for ralphify tests."""

import pytest

from ralphify.adapters._generic import GenericAdapter


@pytest.fixture(autouse=True)
def _disable_streaming(monkeypatch):
    """Force adapter dispatch to the blocking path in all tests.

    Routing ``select_adapter`` to :class:`GenericAdapter` means
    ``renders_structured`` is False, so :func:`execute_agent` never
    spawns the Popen-based streaming helper.  Both ``_agent`` and
    ``engine`` import ``select_adapter`` directly, so we patch both
    module-level references (each binding is independent once the
    ``from ralphify.adapters import select_adapter`` import resolves).
    Individual tests that need to exercise the streaming path re-patch
    ``select_adapter`` locally.
    """
    for target in (
        "ralphify._agent.select_adapter",
        "ralphify.engine.select_adapter",
    ):
        monkeypatch.setattr(target, lambda cmd: GenericAdapter())
