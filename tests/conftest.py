"""Shared pytest fixtures for ralphify tests."""

import pytest

from ralphify.adapters import ADAPTERS


@pytest.fixture(autouse=True)
def _disable_streaming(monkeypatch):
    """Force the blocking path on every registered adapter.

    Tests that explicitly need the Popen streaming path re-enable it
    on the specific adapter they exercise.
    """
    for adapter in ADAPTERS:
        monkeypatch.setattr(adapter, "renders_structured", False)
