# Medium 02 — `returncode=None` on timeout: document the semantic change

**Original finding:** M4
**Severity:** Medium — external-API behavior change with no CHANGELOG note
**Files:** `src/ralphify/_agent.py`, `CHANGELOG.md`, possibly `docs/contributing/codebase-map.md`

## Problem

`_run_agent_blocking` now forces `returncode=None` on timeout:

```python
# src/ralphify/_agent.py ~443
return AgentResult(
    returncode=None if timed_out else returncode,
    elapsed=time.monotonic() - start,
    log_file=log_file,
    timed_out=timed_out,
    ...
)
```

Previously the blocking path used `proc.communicate()` which set `proc.returncode` to the actual exit code of the killed process (typically `-9` for SIGKILL or `-15` for SIGTERM). The new code overwrites that to `None` whenever `timed_out is True`.

The streaming path (`_run_agent_streaming`) also made the same change: `returncode=None if stream.timed_out else proc.returncode`.

### Why this was done

Consistency with `ProcessResult`'s documented contract: the base class docstring already says returncode is "`int` or `None` when the process timed out." The old blocking path was inconsistent with its own base class; this change makes them agree.

### Why it might matter

- **Internal callers are fine.** `engine._run_agent_phase` checks `timed_out` first, so it never dereferences `returncode` on the timeout path. `ProcessResult.success` uses `returncode == 0 and not timed_out` — works with `None`.
- **External subscribers may break.** `IterationEndedData.returncode` is emitted to any caller that subscribes to `EventType.ITERATION_ENDED` via the Python API. A custom emitter that previously logged `-9` on timeout now sees `None` and must handle it.
- **The change is not in the CHANGELOG.** The big CHANGELOG paragraph mentions the deadlock fix and the peek feature but not the `returncode` semantic change.

## Why it matters

This is not a bug — it's a behavior change that wasn't documented. Downstream consumers (people with Python-API integrations) could be surprised. The fix is small: either document the change, or revert to preserve backward compat.

## Fix direction

Pick **one** of the following.

### Option A — Document the change (preferred)

Add a note to the CHANGELOG's Unreleased section:

```markdown
### Changed

- `AgentResult.returncode` and `IterationEndedData.returncode` now consistently return `None` when the agent times out (previously the blocking path returned the kill signal's exit code, e.g. `-9`). The streaming path already behaved this way; this change aligns both paths with the documented `ProcessResult` contract. **API consumers:** if you emit metrics or logs keyed on `returncode` for timeouts, check `timed_out` first.
```

This is the minimum effort fix. The semantic is cleaner; just say so.

### Option B — Revert to preserve the exit code

Change:

```python
return AgentResult(
    returncode=returncode,  # keep the kill signal exit code
    ...
    timed_out=timed_out,
)
```

For both `_run_agent_blocking` and `_run_agent_streaming`. Update the `ProcessResult` docstring to say "returncode is always set; check `timed_out` to distinguish a normal zero-exit from a killed process."

This preserves backward compat but is slightly less clean — `returncode=-9, timed_out=True` is redundant information and consumers have to check both.

### Recommendation

Go with **Option A**. The new contract is cleaner, the blocking-vs-streaming inconsistency on `main` was a latent bug waiting to bite someone, and a single CHANGELOG bullet is all that's needed. Just make sure the bullet is written clearly enough that API consumers notice it.

## Done when

- [ ] CHANGELOG Unreleased section has a `### Changed` entry documenting the `returncode` semantic (or Option B is implemented and documented in the docstring).
- [ ] If Option A: `docs/contributing/codebase-map.md` — check whether the "AgentResult" / "IterationEndedData" references need updating. Usually no, but verify.
- [ ] If Option B: both paths preserve `proc.returncode` on timeout; `ProcessResult` docstring reflects the contract; `IterationEndedData` type hint is unchanged.
- [ ] No code changes if Option A is chosen beyond the CHANGELOG.
- [ ] New test (Option A): `tests/test_agent.py::test_returncode_is_none_on_blocking_timeout` — run an agent with a short timeout, assert `AgentResult.returncode is None and timed_out is True`.
- [ ] New test (Option B): same test but assert `returncode == expected_kill_signal`.
- [ ] `uv run pytest`, lint, format, ty check all pass.
- [ ] `uv run mkdocs build --strict` passes (CHANGELOG is built into the docs site).

## Context

- `AgentResult` is a dataclass in `src/ralphify/_agent.py`. It extends (or delegates to) `ProcessResult` from `_output.py`.
- `ProcessResult.success` is defined in `_output.py`; check its exact implementation before choosing Option B — if it already treats `None` returncode as "not success," Option B has no practical advantage.
- `IterationEndedData` is a TypedDict in `_events.py`. Its `returncode` field is typed as `int | None`.
- Consumers: this is the `engine.py` event emission path and any Python-API caller using `run_with_emitter` or equivalent. Grep for `IterationEndedData` and `EventType.ITERATION_ENDED` to find subscribers in the test suite.
- **Scope:** this is a 20-line task at most. Do not expand into a larger refactor of `ProcessResult`.
