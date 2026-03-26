---
title: Contributing to Ralphify
description: Set up a ralphify development environment, run tests, understand the architecture, and submit pull requests.
keywords: ralphify contributing, development setup, pull requests, open source, contributor guide
---

# Contributing

Ralphify is open source (MIT) and welcomes contributions. This page covers everything you need to set up a development environment, run tests, and submit changes.

For architecture details and codebase orientation, see the [Codebase Map](codebase-map.md).

## Development setup

Clone the repository and install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/computerlovetech/ralphify.git
cd ralphify
uv sync
```

This installs all runtime and dev dependencies (pytest, mkdocs, mkdocs-material) into a local virtual environment.

Verify the setup by running the CLI from source:

```bash
uv run ralph --version
```

## Running tests

The test suite uses pytest with one test file per source module:

```bash
uv run pytest           # Run all tests
uv run pytest -x        # Stop on first failure
uv run pytest -v        # Verbose output
```

Tests use temporary directories and have no external dependencies — no API keys, no network access, no Docker.

When adding a new feature, add tests in the corresponding file. If you're adding a new module, create a matching `test_<module>.py` file.

## Working on documentation

The docs site uses [MkDocs](https://www.mkdocs.org/) with the [Material](https://squidfunk.github.io/mkdocs-material/) theme.

### Local preview

```bash
uv run mkdocs serve
```

This starts a local server at `http://127.0.0.1:8000` with live reload — edits to docs files appear instantly in the browser.

### Build check

```bash
uv run mkdocs build --strict
```

The `--strict` flag treats warnings as errors. The CI pipeline uses this flag, so make sure your changes build cleanly before submitting.

## Working on the website

The deployed site combines a static **landing page** (`website/`) and the **MkDocs docs** (`docs/`). The `docs.yml` GitHub Actions workflow builds both and deploys them together to GitHub Pages.

### Local preview

Use the [justfile](https://github.com/casey/just) for common build tasks:

```bash
just docs-preview         # MkDocs dev server at http://127.0.0.1:8000
just website-build        # Build the full combined site to _site/
just website-preview      # Build + serve at http://127.0.0.1:8080
```

## Submitting changes

1. **Fork and branch** — create a feature branch from `main`:

    ```bash
    git checkout -b my-feature
    ```

2. **Make your changes** — keep commits focused and atomic.

3. **Run tests** — make sure all tests pass:

    ```bash
    uv run pytest
    ```

4. **Check the docs** — if you changed anything in `docs/` or `mkdocs.yml`:

    ```bash
    uv run mkdocs build --strict
    ```

5. **Open a pull request** against `main` with a clear description of what you changed and why.

### Commit messages

The project uses descriptive commit messages that explain the user benefit:

```text
docs: explain X for users who want to Y
feat: add X so users can Y
fix: resolve X that caused Y
```

Look at `git log --oneline` for examples of the style.

## Dependencies

Ralphify is minimal by design:

- **Runtime:** `typer` (CLI framework), `rich` (terminal formatting), and `pyyaml` (YAML frontmatter parsing)
- **Dev:** `pytest`, `mkdocs`, `mkdocs-material`

Think carefully before adding a new dependency. If it can be done with the standard library, prefer that.

## Release process

Releases are published to PyPI automatically when a GitHub release is created:

1. Update the version in `pyproject.toml`
2. Create a GitHub release with a tag matching the version (e.g. `v0.2.0`)
3. The `publish.yml` workflow runs tests, builds the package, verifies the version matches the tag, and publishes to PyPI

Docs deploy automatically to GitHub Pages on every push to `main` that changes files in `docs/` or `mkdocs.yml`.
