"""Tests for ralphify.resolver — the template placeholder resolution engine.

Tests the three placement strategies directly:
1. Named: {{ kind.name }} → specific content
2. Bulk: {{ kind }} → all remaining content (alphabetically)
3. Implicit: no placeholders → append all at end
"""

from ralphify.resolver import resolve_placeholders


class TestEmptyAvailable:
    def test_returns_prompt_unchanged_when_no_items(self):
        assert resolve_placeholders("Hello world", {}, "contexts") == "Hello world"

    def test_returns_prompt_unchanged_when_available_is_empty(self):
        prompt = "{{ contexts }}"
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


class TestBulkPlaceholder:
    def test_single_item_bulk(self):
        result = resolve_placeholders(
            "Start\n{{ contexts }}\nEnd",
            {"git": "log data"},
            "contexts",
        )
        assert result == "Start\nlog data\nEnd"

    def test_multiple_items_alphabetical_order(self):
        result = resolve_placeholders(
            "{{ contexts }}",
            {"zebra": "Z", "alpha": "A", "middle": "M"},
            "contexts",
        )
        assert result == "A\n\nM\n\nZ"

    def test_bulk_with_backslash_sequences(self):
        """Bulk replacement must use lambda to avoid re.sub backslash interpretation."""
        result = resolve_placeholders(
            "{{ contexts }}",
            {"regex": r"Use \d+ for digits and \1 for groups"},
            "contexts",
        )
        assert result == r"Use \d+ for digits and \1 for groups"

    def test_multiple_bulk_placeholders(self):
        result = resolve_placeholders(
            "First: {{ contexts }}\nSecond: {{ contexts }}",
            {"a": "content"},
            "contexts",
        )
        assert "First: content" in result
        assert "Second: content" in result


class TestNamedExcludesFromBulk:
    def test_named_items_excluded_from_bulk(self):
        result = resolve_placeholders(
            "Specific: {{ contexts.alpha }}\nRest: {{ contexts }}",
            {"alpha": "A", "beta": "B", "gamma": "G"},
            "contexts",
        )
        assert "Specific: A" in result
        assert result.count("A") == 1  # alpha only appears once
        assert "B" in result
        assert "G" in result

    def test_all_named_leaves_bulk_empty(self):
        result = resolve_placeholders(
            "{{ contexts.a }} {{ contexts.b }}\n{{ contexts }}",
            {"a": "A", "b": "B"},
            "contexts",
        )
        assert "A" in result
        assert "B" in result
        # Bulk should be empty since all items were placed by name
        assert result.count("A") == 1
        assert result.count("B") == 1


class TestImplicitAppend:
    def test_appends_when_no_placeholders(self):
        result = resolve_placeholders(
            "Base prompt.",
            {"style": "Use black formatting."},
            "instructions",
        )
        assert result == "Base prompt.\n\nUse black formatting."

    def test_appends_multiple_alphabetically(self):
        result = resolve_placeholders(
            "Base.",
            {"beta": "B", "alpha": "A"},
            "instructions",
        )
        assert result == "Base.\n\nA\n\nB"

    def test_no_append_when_named_placeholder_exists(self):
        """When named placeholders are used (but no bulk), remaining items are NOT appended."""
        result = resolve_placeholders(
            "{{ instructions.used }}",
            {"used": "placed", "unused": "should not appear"},
            "instructions",
        )
        assert "placed" in result
        assert "should not appear" not in result


class TestKindIsolation:
    def test_different_kind_placeholder_not_replaced(self):
        """Placeholders for a different kind should be left untouched."""
        result = resolve_placeholders(
            "{{ instructions.foo }}",
            {"foo": "bar"},
            "contexts",  # resolving contexts, not instructions
        )
        assert result == "{{ instructions.foo }}\n\nbar"

    def test_kind_with_special_regex_chars(self):
        """Kind names are re.escape'd so dots/brackets don't break patterns."""
        result = resolve_placeholders(
            "{{ my.kind.name }}",
            {"name": "value"},
            "my.kind",
        )
        assert result == "value"
