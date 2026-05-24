"""Tests for ralphify.__init__ — version fallback and main() entry point."""

import builtins

import pytest

from unittest.mock import patch, MagicMock


class TestVersionFallback:
    def test_fallback_to_0_0_0_when_package_not_found(self):
        """When importlib.metadata can't find the package, __version__ falls back to '0.0.0'."""
        import sys
        from importlib.metadata import PackageNotFoundError

        with patch(
            "importlib.metadata.version", side_effect=PackageNotFoundError("ralphify")
        ):
            # Remove cached module so re-import executes module-level code
            saved = sys.modules.pop("ralphify")
            try:
                import ralphify

                assert ralphify.__version__ == "0.0.0"
            finally:
                # Restore the original module to avoid polluting other tests
                sys.modules["ralphify"] = saved

    def test_version_is_set_from_metadata(self):
        """Normal case: __version__ is a non-empty string from installed metadata."""
        import ralphify

        assert isinstance(ralphify.__version__, str)
        assert len(ralphify.__version__) > 0


class TestMain:
    def test_main_calls_app(self):
        """main() imports and calls the typer app."""
        mock_app = MagicMock()
        with patch("ralphify.cli.app", mock_app):
            from ralphify import main

            main()

        mock_app.assert_called_once()

    def test_main_is_callable(self):
        """main() is a callable function suitable as a console_scripts entry point."""
        from ralphify import main

        assert callable(main)

    def test_main_raises_actionable_error_without_cli_extra(self):
        """When rich/typer are absent, importing the CLI fails and main() exits
        with a message pointing at the [cli] extra."""
        import sys
        from ralphify import main

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "ralphify.cli" or name.startswith("typer") or name == "rich":
                raise ImportError(f"No module named {name!r}")
            return real_import(name, *args, **kwargs)

        # Drop any cached CLI module so the import is re-attempted.
        saved = {
            k: sys.modules.pop(k) for k in list(sys.modules) if k == "ralphify.cli"
        }
        try:
            with patch.object(builtins, "__import__", side_effect=fake_import):
                with pytest.raises(SystemExit, match=r"ralphify\[cli\]"):
                    main()
        finally:
            sys.modules.update(saved)
