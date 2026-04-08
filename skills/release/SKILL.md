---
name: release
description: Run the full ralphify release process — analyze changes, update docs, bump version, commit, push, create GitHub release, verify CI, and generate social content. Use when cutting a new release. Optional arg "patch", "minor", or "major" to skip the version bump prompt.
---

# Ralphify Release Skill

You are running the ralphify release process. Follow each phase in order. Stop and ask the user if anything is unclear or if a decision is needed.

## Phase 1: Pre-flight checks

1. **Clean working tree** — run `git status`. If there are uncommitted changes, stop and ask the user whether to stash, commit, or abort.
2. **On main branch** — confirm we're on `main`. If not, ask the user.
3. **Up to date with remote** — run `git fetch origin main && git log HEAD..origin/main --oneline`. If behind, warn the user.

## Phase 2: Analyze changes since last release

1. Find the latest version tag: `git tag --sort=-v:refname | head -5` (tags are `vX.Y.Z`).
2. Read the current version from `pyproject.toml` (line 3, `version = "X.Y.Z"`).
3. Get the full diff and commit log since that tag:
   - `git log <tag>..HEAD --oneline`
   - `git diff <tag>..HEAD --stat`
   - Read changed files as needed to understand the substance of each change.
4. Categorize changes into: **Added**, **Fixed**, **Changed**, **Improved**, **Breaking changes**. Only include categories that have entries.
5. Present a summary to the user: what changed, and your proposed version bump (patch/minor/major) with reasoning.

## Phase 3: Version bump

- If the user passed "patch", "minor", or "major" as an argument to this skill, use that.
- Otherwise, propose a bump level based on the changes and **ask the user to confirm** before proceeding.
- Bump the version in `pyproject.toml` (the single source of truth — `importlib.metadata` picks it up at runtime).

## Phase 4: Update docs (selectively)

Not every release needs doc updates everywhere. Use judgment:

### Changelog (`CHANGELOG.md`)
- **Always update.** Add a new section at the top (below the header), following the existing format:
  ```
  ## X.Y.Z — YYYY-MM-DD

  ### Category

  - **Bold summary** — explanation of what changed and why it matters to users.
  ```
- Keep entries user-focused. Implementation details don't belong here.
- Add a `---` separator after the new section.

### README.md
- **Only update if** the release changes the quickstart, install instructions, core concepts, or the high-level pitch. Most patch releases won't touch this.

### MkDocs docs (`docs/`)
- **Only update if** a user-facing feature was added or changed (new CLI flags, new frontmatter fields, changed behavior).
- Check: `docs/quick-reference.md`, `docs/cli.md`, `docs/how-it-works.md`, and `docs/cookbook.md` for relevance.

### New-ralph skill (`src/ralphify/skills/new-ralph/SKILL.md`)
- **Only update if** new frontmatter fields or ralph structure changes were introduced.

### Codebase map (`docs/contributing/codebase-map.md`)
- **Only update if** new modules were added or module responsibilities changed.

For each doc surface, state whether you're updating it and why (or why not). Don't make changes just to make changes.

## Phase 5: Build verification

Run locally before pushing:

```bash
uv run ruff check .           # Lint must pass
uv run ruff format --check .  # Format must pass
uv run ty check               # Type check must pass
uv run pytest                 # All tests must pass
uv run mkdocs build --strict  # Zero warnings
```

If either fails, fix the issue before continuing.

## Phase 6: Commit, tag, and push

1. Stage all changes: `git add -A` (but check `git diff --cached` to make sure nothing unexpected is staged).
2. Commit with message: `release: vX.Y.Z` followed by a blank line and a concise summary of the release.
3. Create an annotated tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`.
4. Push with tags: `git push origin main --follow-tags`.

## Phase 7: Verify CI pipeline

1. Watch the publish workflow: `gh run list --workflow=publish.yml --limit=3`.
2. If a run is in progress, check its status: `gh run watch <run-id>`.
3. If the run fails, investigate and report to the user. Do not retry automatically.

## Phase 8: Social content

Generate two pieces of social content for the user to review and post:

### Tweet (< 280 chars)
- Lead with the most impactful change, not "we released vX.Y.Z"
- Include the PyPI link: `pypi.org/project/ralphify/`
- Keep it punchy — one key thing, not a feature list
- No emojis unless the user requests them

### ray.so snippet
- Generate a short code/terminal snippet (3-8 lines) that showcases the most important change
- Provide the raw text the user can paste into ray.so
- Suggest settings: theme "candy", language "shell", padding 32, dark mode

Present both to the user for review. These are suggestions — the user decides whether and what to post.

## Important notes

- The publish workflow (`publish.yml`) triggers on tag push (`v*`) and verifies the git tag matches `pyproject.toml` version. CI automatically creates the GitHub Release from `CHANGELOG.md`. The tag format is `vX.Y.Z`.
- Never force-push or rewrite history on main.
- If anything goes wrong mid-release, stop and discuss with the user rather than trying to recover automatically.
