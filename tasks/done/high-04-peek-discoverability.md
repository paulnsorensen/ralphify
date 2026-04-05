# High 04 — Peek discoverability

**Original finding:** H5
**Severity:** High — feature is on by default but invisible to first-time users
**Files:** `src/ralphify/cli.py`, `src/ralphify/_console_emitter.py`

## Problem

Live peek is on by default in any interactive terminal. First-time users running `ralph run my-ralph` will see their terminal suddenly flood with the agent's stdout/stderr and have no idea:

1. That this is the new peek feature (not a bug).
2. That they can press `p` to silence it.
3. That `p` exists at all.

Concrete discoverability gaps:

### 1. `ralph run --help` doesn't mention `p`

`src/ralphify/cli.py` around lines 517-525 defines the `run` command with a docstring used by Typer's `--help`. The docstring covers Ctrl+C semantics but never mentions the `p` keybinding.

### 2. No startup banner

`ConsoleEmitter._on_run_started` prints a "Running:" header but no hint about the peek feature. The user goes from a quiet header directly into a flood of agent output.

### 3. Only the docs page mentions it

`docs/cli.md` has a new "Peeking at live agent output" section and `docs/quick-reference.md` has a one-line keybinding entry. Both are discoverable only if the user already knows to go look for them.

## Why it matters

- **Surprise is bad onboarding.** A user's first ralphify run should not feel like a CLI is broken or misbehaving. If they can't instantly find the off-switch, they'll reach for Ctrl+C and assume the tool is buggy.
- **Discoverability of keybindings is a CLI tool's responsibility.** The project already documents Ctrl+C semantics in `--help`; `p` deserves equal billing since it's the only other in-run keybinding.
- **Cost of the fix is trivial** (two or three strings).

## Fix direction

Three small changes:

### 1. Update the `run` command docstring in `cli.py`

Add a line mentioning `p`:

```python
@app.command()
def run(...):
    """Run a ralph in a loop.

    ...existing text...

    Keybindings (in an interactive terminal):
      p         Toggle live peek of agent output (on by default)
      Ctrl+C    Finish the current iteration gracefully, then stop
      Ctrl+C ×2 Force-kill the agent and exit immediately
    """
```

Typer renders triple-quoted docstrings verbatim in `--help`, so be mindful of indentation and line length.

### 2. Print a startup hint from `ConsoleEmitter._on_run_started`

Right after the "Running:" header, when `self._peek_enabled is True` (peek is on at run start), print a one-line hint:

```python
if self._peek_enabled:
    self._console.print("[dim]peek on — press p to toggle[/]")
```

Keep it dim so it doesn't compete with the header visually. Only print it when peek is actually on and the user can actually use the `p` key (i.e. the keypress listener is active — stdin is a TTY). Reuse the existing `_interactive_default_peek` logic or expose it.

### 3. (Optional) Hint when the user silences peek

When `toggle_peek` flips from on → off, the current banner is `[dim]peek off[/]`. Consider `[dim]peek off — press p to resume[/]` for symmetry. Pure polish; skip if the banner gets too long.

## Done when

- [ ] `ralph run --help` output includes a `p` keybinding line alongside the Ctrl+C documentation. Verify by running `uv run ralph run --help | grep -i peek`.
- [ ] When peek is enabled at run start (interactive TTY default), a one-line hint appears under the "Running:" header pointing at `p`. Verify manually or via a test.
- [ ] Hint does NOT appear when peek is off at start (non-TTY, CI, piped).
- [ ] New test `tests/test_console_emitter.py::test_startup_hint_shown_when_peek_on_by_default` — construct a `ConsoleEmitter` with peek forced on, emit a `RUN_STARTED` event, assert the hint string appears in captured console output.
- [ ] New test `tests/test_console_emitter.py::test_no_startup_hint_when_peek_off` — construct with peek forced off, assert the hint is absent.
- [ ] Update `docs/cli.md` Peeking section to match the hint wording if it changed. No new docs page needed.
- [ ] `uv run pytest`, lint, format, ty check all pass.
- [ ] `uv run mkdocs build --strict` passes (required for any docs change per CLAUDE.md).

## Context

- `cli.py` run command docstring is Typer-rendered. Typer preserves whitespace but collapses blank lines in some cases; preview with `uv run ralph run --help` before committing.
- `ConsoleEmitter._on_run_started` is in `src/ralphify/_console_emitter.py`. It's already the right place to print startup info.
- `_interactive_default_peek` at `_console_emitter.py:105` is the authoritative check for "is peek usable?" — call it from the hint guard rather than re-implementing the check.
- **Scope discipline:** do NOT add a keypress-listener-level confirmation dialog, tutorial mode, or config file for peek defaults. The fix is three lines of content plus tests. Adding peek to a config file is a separate feature request.
- This task is independent of every other task in the list and can be done standalone in any order.
