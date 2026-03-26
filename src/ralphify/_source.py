"""GitHub source parsing and git-based ralph fetching.

Parses ``owner/repo``, ``owner/repo/ralph-name``, and full GitHub URLs
into a normalised form, then clones the repo (shallow) and extracts the
requested ralph directory.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ralphify._frontmatter import RALPH_MARKER
from ralphify._output import SUBPROCESS_TEXT_KWARGS


@dataclass(frozen=True)
class ParsedSource:
    """Normalised representation of a GitHub ralph source."""

    owner_repo: str
    """Owner and repo slug, e.g. ``owner/repo``."""

    repo_url: str
    """Clone URL, e.g. ``https://github.com/owner/repo.git``."""

    subpath: str | None
    """Path segment(s) after ``owner/repo``, or *None* for repo-root."""

    handle: str
    """Canonical short-form, e.g. ``owner/repo/ralph-name``."""

    name: str
    """Derived ralph name (leaf directory or repo name)."""


# ---------------------------------------------------------------------------
# GitHub URL helpers
# ---------------------------------------------------------------------------

_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?(?:/tree/[^/]+(?:/(?P<path>.+))?)?/?$"
)

_SHORTHAND_RE = re.compile(r"^(?P<owner>[^/]+)/(?P<repo>[^/]+)(?:/(?P<rest>.+))?/?$")


def parse_github_source(source: str) -> ParsedSource:
    """Parse a GitHub source string into a :class:`ParsedSource`.

    Accepted formats::

        owner/repo
        owner/repo/ralph-name
        owner/repo/some/path/to/ralph
        https://github.com/owner/repo
        https://github.com/owner/repo/tree/main/path

    Raises ``ValueError`` for unrecognised formats.
    """
    owner: str | None = None
    repo: str | None = None
    rest: str | None = None

    # Try full URL first.
    m = _GITHUB_URL_RE.match(source)
    if m:
        owner, repo, rest = m.group("owner"), m.group("repo"), m.group("path")
    else:
        m = _SHORTHAND_RE.match(source)
        if m:
            owner, repo, rest = m.group("owner"), m.group("repo"), m.group("rest")

    if not owner or not repo:
        raise ValueError(
            f"Cannot parse source '{source}'. "
            "Expected owner/repo, owner/repo/ralph-name, or a GitHub URL."
        )

    # Strip .git suffix — the URL regex handles this via (?:\.git)? in the
    # pattern, but the shorthand regex captures the full repo segment.
    repo = repo.removesuffix(".git")

    owner_repo = f"{owner}/{repo}"
    repo_url = f"https://github.com/{owner}/{repo}.git"
    subpath = rest.strip("/") if rest else None
    subpath = subpath or None  # normalize empty string to None
    name = Path(subpath).name if subpath else repo
    handle = f"{owner_repo}/{subpath}" if subpath else owner_repo

    return ParsedSource(owner_repo=owner_repo, repo_url=repo_url, subpath=subpath, handle=handle, name=name)


# ---------------------------------------------------------------------------
# Git clone + ralph extraction
# ---------------------------------------------------------------------------


def _find_ralphs_in(root: Path) -> list[Path]:
    """Return all directories under *root* that contain a RALPH.md."""
    return sorted(
        p.parent for p in root.rglob(RALPH_MARKER) if p.is_file()
    )


def _shallow_clone(repo_url: str, dest: Path) -> None:
    """Run ``git clone --depth 1`` into *dest*.

    Raises ``RuntimeError`` on failure.
    """
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(dest)],
            capture_output=True,
            **SUBPROCESS_TEXT_KWARGS,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "git is required for 'ralph add'. Install it from https://git-scm.com/"
        ) from None
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr.strip() if exc.stderr else "") or "unknown error"
        raise RuntimeError(f"git clone failed: {stderr}") from None


@dataclass(frozen=True)
class FetchResult:
    """Result of fetching ralph(s) from a source."""

    installed: list[tuple[str, Path]]
    """List of ``(name, dest_path)`` for each installed ralph."""


def _install_single_ralph(src: Path, name: str, ralphs_dir: Path) -> FetchResult:
    """Copy a single ralph from *src* to *ralphs_dir*/*name* and return a FetchResult."""
    dest = ralphs_dir / name
    _copy_ralph(src, dest)
    return FetchResult(installed=[(name, dest)])


def fetch_ralphs(parsed: ParsedSource, ralphs_dir: Path) -> FetchResult:
    """Clone the repo and extract ralph(s) to *ralphs_dir*.

    *ralphs_dir* is the ``.ralphify/ralphs/`` directory.  Each ralph is
    placed in ``ralphs_dir/<name>/``.

    Returns a :class:`FetchResult` describing what was installed.
    Raises ``RuntimeError`` on any failure.
    """
    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "repo"
        _shallow_clone(parsed.repo_url, clone_dir)

        if parsed.subpath is None:
            # owner/repo — check if root is a ralph, else install all.
            return _fetch_repo_ralphs(clone_dir, parsed, ralphs_dir)
        else:
            # owner/repo/ralph-name — search for the ralph.
            return _fetch_named_ralph(clone_dir, parsed, ralphs_dir)


def _fetch_repo_ralphs(
    clone_dir: Path, parsed: ParsedSource, ralphs_dir: Path,
) -> FetchResult:
    """Handle ``owner/repo`` — repo root is a ralph, or install all."""
    root_ralph = clone_dir / RALPH_MARKER
    if root_ralph.is_file():
        return _install_single_ralph(clone_dir, parsed.name, ralphs_dir)

    # Scan for all ralphs in the repo.
    ralph_dirs = _find_ralphs_in(clone_dir)
    if not ralph_dirs:
        raise RuntimeError(
            f"No {RALPH_MARKER} found in {parsed.handle}."
        )

    # Detect duplicate leaf names — installing two ralphs with the same
    # directory name would silently overwrite the first.
    seen: dict[str, list[Path]] = {}
    for rd in ralph_dirs:
        seen.setdefault(rd.name, []).append(rd)
    duplicates = {name: paths for name, paths in seen.items() if len(paths) > 1}
    if duplicates:
        dup_name = next(iter(duplicates))
        paths = "\n".join(
            f"  - {m.relative_to(clone_dir)}/{RALPH_MARKER}" for m in duplicates[dup_name]
        )
        raise RuntimeError(
            f"Found multiple ralphs named '{dup_name}' in {parsed.owner_repo}:\n"
            f"{paths}\n\n"
            f"Use the full path to disambiguate, e.g.:\n"
            f"  ralph add {parsed.owner_repo}/{duplicates[dup_name][0].relative_to(clone_dir)}"
        )

    installed: list[tuple[str, Path]] = []
    for rd in ralph_dirs:
        result = _install_single_ralph(rd, rd.name, ralphs_dir)
        installed.extend(result.installed)
    return FetchResult(installed=installed)


def _fetch_named_ralph(
    clone_dir: Path, parsed: ParsedSource, ralphs_dir: Path,
) -> FetchResult:
    """Handle ``owner/repo/ralph-name`` — search or exact subpath."""
    assert parsed.subpath is not None
    ralph_name = parsed.name

    # First try exact subpath.
    exact = clone_dir / parsed.subpath
    if exact.is_dir() and (exact / RALPH_MARKER).is_file():
        return _install_single_ralph(exact, ralph_name, ralphs_dir)

    # Search by name (leaf segment).
    all_ralphs = _find_ralphs_in(clone_dir)
    matches = [rd for rd in all_ralphs if rd.name == ralph_name]

    if len(matches) == 1:
        return _install_single_ralph(matches[0], ralph_name, ralphs_dir)

    elif len(matches) > 1:
        paths = "\n".join(
            f"  - {m.relative_to(clone_dir)}/{RALPH_MARKER}" for m in matches
        )
        raise RuntimeError(
            f"Found multiple ralphs named '{ralph_name}' in {parsed.owner_repo}:\n"
            f"{paths}\n\n"
            f"Use the full path to disambiguate, e.g.:\n"
            f"  ralph add {parsed.owner_repo}/{matches[0].relative_to(clone_dir)}"
        )

    raise RuntimeError(
        f"No ralph named '{ralph_name}' found in {parsed.handle}."
    )


def _copy_ralph(src: Path, dest: Path) -> None:
    """Copy a ralph directory to *dest*, overwriting if it exists."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git"))
