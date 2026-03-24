"""Tests for GitHub source parsing and ralph fetching."""

from __future__ import annotations

import pytest

from ralphify._frontmatter import RALPH_MARKER
from ralphify._source import (
    FetchResult,
    ParsedSource,
    _find_ralphs_in,
    _fetch_named_ralph,
    _fetch_repo_ralphs,
    parse_github_source,
)


# ── parse_github_source ─────────────────────────────────────────────


class TestParseGithubSource:
    def test_owner_repo(self):
        p = parse_github_source("acme/tools")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath is None
        assert p.handle == "acme/tools"
        assert p.name == "tools"

    def test_owner_repo_with_ralph_name(self):
        p = parse_github_source("acme/tools/linter")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath == "linter"
        assert p.handle == "acme/tools/linter"
        assert p.name == "linter"

    def test_owner_repo_with_deep_path(self):
        p = parse_github_source("acme/tools/some/nested/ralph")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath == "some/nested/ralph"
        assert p.handle == "acme/tools/some/nested/ralph"
        assert p.name == "ralph"

    def test_full_github_url(self):
        p = parse_github_source("https://github.com/acme/tools")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath is None
        assert p.name == "tools"

    def test_full_github_url_with_git_suffix(self):
        p = parse_github_source("https://github.com/acme/tools.git")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath is None

    def test_full_github_url_with_tree_path(self):
        p = parse_github_source("https://github.com/acme/tools/tree/main/my-ralph")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath == "my-ralph"
        assert p.name == "my-ralph"

    def test_full_github_url_trailing_slash(self):
        p = parse_github_source("https://github.com/acme/tools/")
        assert p.repo_url == "https://github.com/acme/tools.git"
        assert p.subpath is None

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_github_source("just-one-segment")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_github_source("")


# ── _find_ralphs_in ─────────────────────────────────────────────────


class TestFindRalphsIn:
    def test_finds_nested_ralphs(self, tmp_path):
        (tmp_path / "a" / "b").mkdir(parents=True)
        (tmp_path / "a" / "b" / RALPH_MARKER).write_text("prompt")
        (tmp_path / "c").mkdir()
        (tmp_path / "c" / RALPH_MARKER).write_text("prompt")
        result = _find_ralphs_in(tmp_path)
        names = [p.name for p in result]
        assert sorted(names) == ["b", "c"]

    def test_returns_empty_when_none(self, tmp_path):
        (tmp_path / "a").mkdir()
        assert _find_ralphs_in(tmp_path) == []

    def test_includes_root_if_ralph(self, tmp_path):
        (tmp_path / RALPH_MARKER).write_text("prompt")
        result = _find_ralphs_in(tmp_path)
        assert tmp_path in result


# ── _fetch_repo_ralphs (no git, uses pre-built directories) ─────────


class TestFetchRepoRalphs:
    def test_root_is_ralph(self, tmp_path):
        clone_dir = tmp_path / "repo"
        clone_dir.mkdir()
        (clone_dir / RALPH_MARKER).write_text("prompt")

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath=None, handle="a/b", name="b",
        )
        result = _fetch_repo_ralphs(clone_dir, parsed, dest_dir)
        assert len(result.installed) == 1
        assert result.installed[0][0] == "b"
        assert (dest_dir / "b" / RALPH_MARKER).is_file()

    def test_repo_with_multiple_ralphs(self, tmp_path):
        clone_dir = tmp_path / "repo"
        for name in ("alpha", "beta"):
            d = clone_dir / "ralphs" / name
            d.mkdir(parents=True)
            (d / RALPH_MARKER).write_text("prompt")

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath=None, handle="a/b", name="b",
        )
        result = _fetch_repo_ralphs(clone_dir, parsed, dest_dir)
        assert len(result.installed) == 2
        names = sorted(n for n, _ in result.installed)
        assert names == ["alpha", "beta"]

    def test_no_ralphs_raises(self, tmp_path):
        clone_dir = tmp_path / "repo"
        clone_dir.mkdir()
        (clone_dir / "README.md").write_text("hello")

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath=None, handle="a/b", name="b",
        )
        with pytest.raises(RuntimeError, match="No RALPH.md found"):
            _fetch_repo_ralphs(clone_dir, parsed, dest_dir)


# ── _fetch_named_ralph ──────────────────────────────────────────────


class TestFetchNamedRalph:
    def test_exact_subpath_match(self, tmp_path):
        clone_dir = tmp_path / "repo"
        d = clone_dir / "cookbooks" / "lint"
        d.mkdir(parents=True)
        (d / RALPH_MARKER).write_text("prompt")

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath="cookbooks/lint", handle="a/b/cookbooks/lint", name="lint",
        )
        result = _fetch_named_ralph(clone_dir, parsed, dest_dir)
        assert result.installed[0][0] == "lint"
        assert (dest_dir / "lint" / RALPH_MARKER).is_file()

    def test_search_by_name(self, tmp_path):
        clone_dir = tmp_path / "repo"
        d = clone_dir / "deep" / "nested" / "lint"
        d.mkdir(parents=True)
        (d / RALPH_MARKER).write_text("prompt")

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        # subpath is just "lint" — not the full path
        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath="lint", handle="a/b/lint", name="lint",
        )
        result = _fetch_named_ralph(clone_dir, parsed, dest_dir)
        assert result.installed[0][0] == "lint"

    def test_ambiguous_raises_with_paths(self, tmp_path):
        clone_dir = tmp_path / "repo"
        for path in ("a/lint", "b/lint"):
            d = clone_dir / path
            d.mkdir(parents=True)
            (d / RALPH_MARKER).write_text("prompt")

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        parsed = ParsedSource(
            repo_url="https://github.com/x/y.git",
            subpath="lint", handle="x/y/lint", name="lint",
        )
        with pytest.raises(RuntimeError, match="Found multiple ralphs named 'lint'"):
            _fetch_named_ralph(clone_dir, parsed, dest_dir)

    def test_not_found_raises(self, tmp_path):
        clone_dir = tmp_path / "repo"
        clone_dir.mkdir()

        dest_dir = tmp_path / "installed"
        dest_dir.mkdir()

        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath="nope", handle="a/b/nope", name="nope",
        )
        with pytest.raises(RuntimeError, match="No ralph named 'nope'"):
            _fetch_named_ralph(clone_dir, parsed, dest_dir)

    def test_overwrites_existing(self, tmp_path):
        clone_dir = tmp_path / "repo"
        d = clone_dir / "lint"
        d.mkdir(parents=True)
        (d / RALPH_MARKER).write_text("new prompt")

        dest_dir = tmp_path / "installed"
        old = dest_dir / "lint"
        old.mkdir(parents=True)
        (old / RALPH_MARKER).write_text("old prompt")

        parsed = ParsedSource(
            repo_url="https://github.com/a/b.git",
            subpath="lint", handle="a/b/lint", name="lint",
        )
        _fetch_named_ralph(clone_dir, parsed, dest_dir)
        assert (dest_dir / "lint" / RALPH_MARKER).read_text() == "new prompt"
