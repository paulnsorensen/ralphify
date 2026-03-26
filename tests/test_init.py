"""Tests for ralphify.__init__ — version fallback and main() entry point."""

from unittest.mock import patch, MagicMock


class TestVersionFallback:
    def test_fallback_to_0_0_0_when_package_not_found(self):
        """When importlib.metadata can't find the package, __version__ falls back to '0.0.0'."""
        import importlib
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
