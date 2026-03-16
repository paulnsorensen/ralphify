"""Tests for ralphify.resolver — the template placeholder resolution engine.

Only named placeholders are supported: {{ kind.name }} → specific content.
"""

from ralphify.resolver import resolve_placeholders


class TestEmptyAvailable:
    def test_returns_prompt_unchanged_when_no_items(self):
        assert resolve_placeholders("Hello world", {}, "contexts") == "Hello world"

    def test_returns_prompt_unchanged_when_available_is_empty(self):
        prompt = "Some prompt text"
        assert resolve_placeholders(prompt, {}, "contexts") == prompt


class TestNamedPlaceholders:
    def test_single_named_replacement(self):
        result = resolve_placeholders(
            "Before {{ contexts.git }} after",
            {"git": "latest commit: abc123"},
            "contexts",
        )
        assert result == "Before latest commit: abc123 after"

    def test_multiple_named_replacements(self):
        result = resolve_placeholders(
            "{{ ctx.a }} and {{ ctx.b }}",
            {"a": "alpha", "b": "beta"},
            "ctx",
        )
        assert result == "alpha and beta"

    def test_unknown_name_resolves_to_empty(self):
        result = resolve_placeholders(
            "{{ contexts.nonexistent }}",
            {"real": "content"},
            "contexts",
        )
        assert result == ""

    def test_whitespace_in_placeholder_is_tolerated(self):
        result = resolve_placeholders(
            "{{  contexts.name  }}",
            {"name": "value"},
            "contexts",
        )
        assert result == "value"

    def test_hyphenated_name(self):
        result = resolve_placeholders(
            "{{ contexts.git-log }}",
            {"git-log": "commits here"},
            "contexts",
        )
        assert result == "commits here"

    def test_underscored_name(self):
        result = resolve_placeholders(
            "{{ contexts.test_status }}",
            {"test_status": "all green"},
            "contexts",
        )
        assert result == "all green"

    def test_named_with_regex_special_chars_in_content(self):
        """Content with backslash sequences must not be interpreted by re.sub."""
        result = resolve_placeholders(
            "{{ contexts.re }}",
            {"re": r"match \d+ and \1 groups"},
            "contexts",
        )
        assert result == r"match \d+ and \1 groups"


class TestUnreferencedItemsExcluded:
    def test_unreferenced_items_not_appended(self):
        """Items not referenced by a named placeholder should be excluded."""
        result = resolve_placeholders(
            "Base prompt.",
            {"style": "Use black formatting."},
            "instructions",
        )
        assert result == "Base prompt."

    def test_only_named_items_included(self):
        result = resolve_placeholders(
            "{{ contexts.used }}",
            {"used": "placed", "unused": "should not appear"},
            "contexts",
        )
        assert "placed" in result
        assert "should not appear" not in result

    def test_multiple_available_only_named_placed(self):
        result = resolve_placeholders(
            "{{ contexts.alpha }}",
            {"alpha": "A", "beta": "B", "gamma": "G"},
            "contexts",
        )
        assert result == "A"
        assert "B" not in result
        assert "G" not in result


class TestKindIsolation:
    def test_different_kind_placeholder_not_replaced(self):
        """Placeholders for a different kind should be left untouched."""
        result = resolve_placeholders(
            "{{ instructions.foo }}",
            {"foo": "bar"},
            "contexts",  # resolving contexts, not instructions
        )
        assert result == "{{ instructions.foo }}"

    def test_kind_with_special_regex_chars(self):
        """Kind names are re.escape'd so dots/brackets don't break patterns."""
        result = resolve_placeholders(
            "{{ my.kind.name }}",
            {"name": "value"},
            "my.kind",
        )
        assert result == "value"
