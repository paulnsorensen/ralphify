"""Auto-detect project type from manifest files.

Used during ``ralph init`` to report the detected language ecosystem.
Checks for common manifest files (package.json, pyproject.toml, etc.)
and returns a short label like "python" or "node".
"""

from pathlib import Path


def detect_project(path: Path = Path(".")) -> str:
    """Detect project type based on manifest files."""
    markers = {
        "package.json": "node",
        "pyproject.toml": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
    }
    for filename, project_type in markers.items():
        if (path / filename).exists():
            return project_type
    return "generic"
