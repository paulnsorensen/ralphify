"""Discover and resolve named ralphs from ``.ralphify/ralphs/<name>/RALPH.md``.

Ralphs are reusable task-focused prompt files that users can switch between
(e.g. ``improve-docs``, ``refactor``, ``add-tests``).  They follow the same
``.ralphify/<kind>/<name>/MARKER.md`` convention as other primitives.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from ralphify._discovery import PrimitiveEntry, discover_primitives
from ralphify._frontmatter import RALPH_MARKER


class RalphSource(NamedTuple):
    """Resolved ralph source: the file to read and optional ralph name.

    Returned by :func:`resolve_ralph_source` so call sites can access
    fields by name instead of unpacking a positional tuple.
    """

    file_path: str
    """Path to the ralph markdown file (e.g. ``RALPH.md`` or ``.ralphify/ralphs/docs/RALPH.md``)."""

    ralph_name: str | None
    """The ralph's directory name if a named ralph was resolved, ``None`` for file paths."""


@dataclass
class Ralph:
    """A named ralph discovered from ``.ralphify/ralphs/<name>/RALPH.md``.

    Named ralphs let users keep multiple task-focused prompts (e.g.
    ``docs``, ``refactor``, ``add-tests``) and switch between them with
    ``ralph run <name>`` instead of editing the root ``RALPH.md``.

    The *content* is the body text below the YAML frontmatter — this is the
    full prompt that gets piped to the agent.  Context placeholders
    (``{{ contexts.name }}``) resolve the same way as in a root ``RALPH.md``.
    """

    name: str
    path: Path
    description: str = ""
    enabled: bool = True
    content: str = ""
    checks: list[str] | None = None
    contexts: list[str] | None = None


def _ralph_from_entry(prim: PrimitiveEntry) -> Ralph:
    """Convert a :class:`PrimitiveEntry` to a :class:`Ralph`."""
    return Ralph(
        name=prim.path.name,
        path=prim.path,
        description=prim.frontmatter.get("description", ""),
        enabled=prim.frontmatter.get("enabled", True),
        content=prim.body,
        checks=prim.frontmatter.get("checks"),
        contexts=prim.frontmatter.get("contexts"),
    )


def discover_ralphs(root: Path = Path(".")) -> list[Ralph]:
    """Scan ``.ralphify/ralphs/`` for subdirectories containing ``RALPH.md``.

    Returns all discovered ralphs (both enabled and disabled) sorted
    alphabetically by name.
    """
    return [_ralph_from_entry(prim) for prim in discover_primitives(root, "ralphs", RALPH_MARKER)]


def resolve_ralph_name(name: str, root: Path = Path(".")) -> Ralph:
    """Look up a named ralph by its directory name and return the ``Ralph``.

    Called by the CLI when the user passes a positional ralph name
    (``ralph run docs``) or when ``ralph.toml``'s ``ralph`` field contains
    a name.  The match is exact — ``name`` must equal one of the directory
    names under ``.ralphify/ralphs/``.

    Raises ``ValueError`` with a message listing available ralphs if no
    match is found.  The CLI catches this and prints a user-friendly error.
    """
    ralphs = discover_ralphs(root)
    for r in ralphs:
        if r.name == name:
            return r
    available = [r.name for r in ralphs]
    msg = f"Ralph '{name}' not found."
    if available:
        msg += f" Available: {', '.join(available)}"
    raise ValueError(msg)


def is_ralph_name(value: str) -> bool:
    """Return ``True`` if *value* looks like a ralph name rather than a file path.

    A ralph name is a bare identifier (e.g. ``"docs"``) with no ``/`` path
    separators and no ``.`` file extension.  This heuristic lets
    ``ralph.toml``'s ``ralph`` field accept either a name (``"docs"``) or a
    file path (``"RALPH.md"``, ``"ralphs/custom.md"``) and route to the
    correct resolution logic in :func:`resolve_ralph_source`.
    """
    return "/" not in value and "." not in value


def _ralph_to_source(ralph: Ralph) -> RalphSource:
    """Convert a resolved :class:`Ralph` to a :class:`RalphSource`."""
    return RalphSource(str(ralph.path / RALPH_MARKER), ralph.name)


def resolve_ralph_source(
    *,
    ralph_arg: str | None,
    toml_ralph: str,
) -> RalphSource:
    """Resolve the CLI positional argument into a ralph file path and optional name.

    *ralph_arg* is the positional argument from ``ralph run <name>``
    (a named ralph identifier, or ``None`` when omitted).

    *toml_ralph* is the ``agent.ralph`` value from ``ralph.toml``
    (either a ralph name like ``"docs"`` or a file path like ``"RALPH.md"``).

    Resolution:

    1. CLI argument present → look up as a named ralph
    2. toml value looks like a file path → use it directly
    3. toml value looks like a name → try named lookup, fall back to file path

    Raises ``ValueError`` if a CLI-provided ralph name lookup fails.
    """
    # Case 1: CLI argument takes precedence — always resolve as a named ralph
    if ralph_arg is not None:
        return _ralph_to_source(resolve_ralph_name(ralph_arg))

    # Case 2: toml value is a file path (contains "/" or ".")
    if not is_ralph_name(toml_ralph):
        return RalphSource(toml_ralph, None)

    # Case 3: toml value looks like a ralph name — try lookup, fall back to path
    try:
        return _ralph_to_source(resolve_ralph_name(toml_ralph))
    except ValueError:
        return RalphSource(toml_ralph, None)
