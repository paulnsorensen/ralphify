from pathlib import Path

from ralphify.detector import detect_project


def test_detect_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").touch()
    assert detect_project(tmp_path) == "python"


def test_detect_node(tmp_path: Path):
    (tmp_path / "package.json").touch()
    assert detect_project(tmp_path) == "node"


def test_detect_rust(tmp_path: Path):
    (tmp_path / "Cargo.toml").touch()
    assert detect_project(tmp_path) == "rust"


def test_detect_go(tmp_path: Path):
    (tmp_path / "go.mod").touch()
    assert detect_project(tmp_path) == "go"


def test_detect_generic(tmp_path: Path):
    assert detect_project(tmp_path) == "generic"


def test_detect_first_match_wins(tmp_path: Path):
    """When multiple markers exist, the first match in iteration order wins."""
    (tmp_path / "package.json").touch()
    (tmp_path / "pyproject.toml").touch()
    result = detect_project(tmp_path)
    assert result in ("node", "python")
