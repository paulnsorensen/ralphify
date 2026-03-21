"""Tests for ralphify.resolver — the template placeholder resolution engine."""

from ralphify.resolver import resolve_args, resolve_commands, resolve_placeholders


class TestEmptyAvailable:
    def test_returns_prompt_unchanged_when_no_items(self):
        assert resolve_placeholders("Hello world", {}, "commands") == "Hello world"


class TestNamedPlaceholders:
    def test_single_named_replacement(self):
        result = resolve_placeholders(
            "Before {{ commands.tests }} after",
            {"tests": "all passed"},
            "commands",
        )
        assert result == "Before all passed after"

    def test_multiple_named_replacements(self):
        result = resolve_placeholders(
            "{{ commands.a }} and {{ commands.b }}",
            {"a": "alpha", "b": "beta"},
            "commands",
        )
        assert result == "alpha and beta"

    def test_unknown_name_resolves_to_empty(self):
        result = resolve_placeholders(
            "{{ commands.nonexistent }}",
            {"real": "content"},
            "commands",
        )
        assert result == ""

    def test_whitespace_in_placeholder_is_tolerated(self):
        result = resolve_placeholders(
            "{{  commands.name  }}",
            {"name": "value"},
            "commands",
        )
        assert result == "value"

    def test_hyphenated_name(self):
        result = resolve_placeholders(
            "{{ commands.git-log }}",
            {"git-log": "commits here"},
            "commands",
        )
        assert result == "commits here"

    def test_underscored_name(self):
        result = resolve_placeholders(
            "{{ commands.test_status }}",
            {"test_status": "all green"},
            "commands",
        )
        assert result == "all green"

    def test_named_with_regex_special_chars_in_content(self):
        result = resolve_placeholders(
            "{{ commands.re }}",
            {"re": r"match \d+ and \1 groups"},
            "commands",
        )
        assert result == r"match \d+ and \1 groups"


class TestUnreferencedItemsExcluded:
    def test_unreferenced_items_not_appended(self):
        result = resolve_placeholders(
            "Base prompt.",
            {"style": "Use black formatting."},
            "commands",
        )
        assert result == "Base prompt."

    def test_only_named_items_included(self):
        result = resolve_placeholders(
            "{{ commands.used }}",
            {"used": "placed", "unused": "should not appear"},
            "commands",
        )
        assert "placed" in result
        assert "should not appear" not in result


class TestKindIsolation:
    def test_different_kind_placeholder_not_replaced(self):
        result = resolve_placeholders(
            "{{ args.foo }}",
            {"foo": "bar"},
            "commands",
        )
        assert result == "{{ args.foo }}"


class TestResolveCommands:
    def test_single_command(self):
        result = resolve_commands("Tests:\n{{ commands.tests }}", {"tests": "5 passed"})
        assert result == "Tests:\n5 passed"

    def test_multiple_commands(self):
        result = resolve_commands(
            "{{ commands.tests }}\n{{ commands.lint }}",
            {"tests": "ok", "lint": "clean"},
        )
        assert result == "ok\nclean"

    def test_empty_commands_clears_placeholders(self):
        result = resolve_commands("Before {{ commands.tests }} after", {})
        assert result == "Before  after"

    def test_unknown_command_resolves_to_empty(self):
        result = resolve_commands(
            "{{ commands.known }} {{ commands.unknown }}",
            {"known": "value"},
        )
        assert result == "value "

    def test_does_not_touch_arg_placeholders(self):
        result = resolve_commands(
            "{{ commands.tests }} and {{ args.dir }}",
            {"tests": "ok"},
        )
        assert result == "ok and {{ args.dir }}"


class TestResolveArgs:
    def test_single_arg(self):
        result = resolve_args("Research {{ args.dir }}", {"dir": "./my-project"})
        assert result == "Research ./my-project"

    def test_multiple_args(self):
        result = resolve_args(
            "{{ args.dir }} focus: {{ args.focus }}",
            {"dir": "./src", "focus": "performance"},
        )
        assert result == "./src focus: performance"

    def test_empty_args_clears_placeholders(self):
        result = resolve_args("Before {{ args.dir }} after", {})
        assert result == "Before  after"

    def test_unknown_arg_resolves_to_empty(self):
        result = resolve_args(
            "{{ args.known }} {{ args.unknown }}",
            {"known": "value"},
        )
        assert result == "value "

    def test_does_not_touch_command_placeholders(self):
        result = resolve_args(
            "{{ args.dir }} and {{ commands.tests }}",
            {"dir": "./src"},
        )
        assert result == "./src and {{ commands.tests }}"

    def test_whitespace_tolerant(self):
        result = resolve_args("{{  args.dir  }}", {"dir": "."})
        assert result == "."

    def test_hyphenated_arg_name(self):
        result = resolve_args("{{ args.my-dir }}", {"my-dir": "/tmp"})
        assert result == "/tmp"
