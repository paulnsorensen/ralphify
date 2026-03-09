import os
from unittest.mock import patch

from typer.testing import CliRunner

from ralphify.cli import app, CONFIG_FILENAME, RALPH_TOML_TEMPLATE, PROMPT_TEMPLATE

runner = CliRunner()


class TestInit:
    def test_creates_config_and_prompt(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / CONFIG_FILENAME).exists()
        assert (tmp_path / "PROMPT.md").exists()
        assert (tmp_path / CONFIG_FILENAME).read_text() == RALPH_TOML_TEMPLATE
        assert (tmp_path / "PROMPT.md").read_text() == PROMPT_TEMPLATE

    def test_refuses_overwrite_without_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text("existing")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
        assert (tmp_path / CONFIG_FILENAME).read_text() == "existing"

    def test_force_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text("old")
        (tmp_path / "PROMPT.md").write_text("old")
        result = runner.invoke(app, ["init", "--force"])
        assert result.exit_code == 0
        assert (tmp_path / CONFIG_FILENAME).read_text() == RALPH_TOML_TEMPLATE
        assert (tmp_path / "PROMPT.md").read_text() == PROMPT_TEMPLATE

    def test_skips_prompt_if_exists_without_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "PROMPT.md").write_text("my custom prompt")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "PROMPT.md").read_text() == "my custom prompt"


class TestRun:
    def test_errors_without_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_errors_with_missing_prompt(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("ralphify.cli.subprocess.run")
    def test_runs_n_iterations(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "PROMPT.md").write_text("test prompt")

        result = runner.invoke(app, ["run", "-n", "3"])
        assert result.exit_code == 0
        assert mock_run.call_count == 3
        # Verify the prompt was piped as stdin
        for call in mock_run.call_args_list:
            assert call.kwargs["input"] == "test prompt"
            assert call.kwargs["text"] is True

    @patch("ralphify.cli.subprocess.run")
    def test_reads_prompt_each_iteration(self, mock_run, tmp_path, monkeypatch):
        """Prompt file is re-read each iteration so edits take effect."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        prompt_path = tmp_path / "PROMPT.md"
        prompt_path.write_text("v1")

        call_count = 0

        def update_prompt(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                prompt_path.write_text("v2")

        mock_run.side_effect = update_prompt

        result = runner.invoke(app, ["run", "-n", "2"])
        assert result.exit_code == 0
        # First call gets "v1", second call gets "v2"
        assert mock_run.call_args_list[0].kwargs["input"] == "v1"
        assert mock_run.call_args_list[1].kwargs["input"] == "v2"

    @patch("ralphify.cli.subprocess.run")
    def test_custom_command_and_args(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = '[agent]\ncommand = "myagent"\nargs = ["--fast"]\nprompt = "PROMPT.md"\n'
        (tmp_path / CONFIG_FILENAME).write_text(config)
        (tmp_path / "PROMPT.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["myagent", "--fast"], input="go", text=True
        )
