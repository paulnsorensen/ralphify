"""Tests for ralphify._frontmatter — YAML frontmatter parsing and serialization."""

import pytest

from ralphify._frontmatter import (
    RALPH_MARKER,
    _extract_frontmatter_block,
    parse_frontmatter,
    serialize_frontmatter,
)


class TestRalphMarker:
    def test_marker_value(self):
        assert RALPH_MARKER == "RALPH.md"


class TestExtractFrontmatterBlock:
    def test_valid_frontmatter(self):
        text = "---\nagent: claude\n---\nHello"
        fm, body = _extract_frontmatter_block(text)
        assert fm == "agent: claude"
        assert body == "Hello"

    def test_no_frontmatter(self):
        text = "Just a body"
        fm, body = _extract_frontmatter_block(text)
        assert fm == ""
        assert body == "Just a body"

    def test_no_closing_delimiter(self):
        text = "---\nagent: claude\nNo closing"
        fm, body = _extract_frontmatter_block(text)
        assert fm == ""
        assert body == text

    def test_empty_string(self):
        fm, body = _extract_frontmatter_block("")
        assert fm == ""
        assert body == ""

    def test_only_delimiters(self):
        text = "---\n---"
        fm, body = _extract_frontmatter_block(text)
        assert fm == ""
        assert body == ""

    def test_multiline_frontmatter(self):
        text = "---\nagent: claude\ncommands:\n  - name: test\n    run: pytest\n---\nPrompt here"
        fm, body = _extract_frontmatter_block(text)
        assert "agent: claude" in fm
        assert "commands:" in fm
        assert body == "Prompt here"

    def test_body_stripped(self):
        text = "---\nagent: claude\n---\n\n  Hello  \n\n"
        _, body = _extract_frontmatter_block(text)
        assert body == "Hello"

    def test_indented_opening_delimiter_not_treated_as_frontmatter(self):
        """Leading whitespace before the opening '---' means no frontmatter —
        consistent with the closing delimiter which also requires column 0."""
        text = "  ---\nagent: claude\n---\nBody"
        fm, body = _extract_frontmatter_block(text)
        assert fm == ""
        assert body == text

    def test_indented_triple_dash_not_treated_as_closing_delimiter(self):
        """An indented '---' inside a YAML block scalar must not be mistaken
        for the closing frontmatter delimiter.  Only unindented '---' at
        column 0 should close the frontmatter block."""
        text = "---\nagent: claude\nnotes: |\n  first\n  ---\n  third\n---\nBody"
        fm, body = _extract_frontmatter_block(text)
        assert "notes:" in fm
        assert "---" in fm  # the indented --- is part of frontmatter
        assert body == "Body"


class TestParseFrontmatter:
    def test_basic_parsing(self):
        text = "---\nagent: claude\n---\nDo the thing"
        fm, body = parse_frontmatter(text)
        assert fm == {"agent": "claude"}
        assert body == "Do the thing"

    def test_no_frontmatter(self):
        text = "Just a prompt"
        fm, body = parse_frontmatter(text)
        assert fm == {}
        assert body == "Just a prompt"

    def test_commands_list(self):
        text = "---\nagent: claude\ncommands:\n  - name: tests\n    run: pytest\n---\nPrompt"
        fm, _ = parse_frontmatter(text)
        assert fm["commands"] == [{"name": "tests", "run": "pytest"}]

    def test_args_list(self):
        text = "---\nagent: claude\nargs:\n  - dir\n  - focus\n---\nPrompt"
        fm, _ = parse_frontmatter(text)
        assert fm["args"] == ["dir", "focus"]

    def test_html_comments_stripped_from_body(self):
        text = "---\nagent: claude\n---\nBefore <!-- hidden --> after"
        _, body = parse_frontmatter(text)
        assert body == "Before  after"

    def test_multiline_html_comment_stripped(self):
        text = "---\nagent: claude\n---\nBefore <!--\nmultiline\ncomment\n--> after"
        _, body = parse_frontmatter(text)
        assert body == "Before  after"

    def test_invalid_yaml_raises_value_error(self):
        text = "---\n: invalid: yaml: [unclosed\n---\nBody"
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_frontmatter(text)

    def test_empty_frontmatter_returns_empty_dict(self):
        text = "---\n---\nBody"
        fm, body = parse_frontmatter(text)
        assert fm == {}
        assert body == "Body"

    def test_yaml_comment_only_frontmatter_returns_empty_dict(self):
        text = "---\n# just a YAML comment\n---\nBody"
        fm, body = parse_frontmatter(text)
        assert fm == {}
        assert body == "Body"

    def test_block_scalar_with_triple_dash_parsed_correctly(self):
        """A YAML block scalar containing '---' must not break frontmatter parsing."""
        text = "---\nagent: claude\nnotes: |\n  first\n  ---\n  third\n---\nBody"
        fm, body = parse_frontmatter(text)
        assert fm["agent"] == "claude"
        assert "---" in fm["notes"]
        assert body == "Body"

    def test_non_dict_frontmatter_raises_value_error(self):
        text = "---\n- item1\n- item2\n---\nBody"
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            parse_frontmatter(text)

    def test_scalar_frontmatter_raises_value_error(self):
        text = "---\njust a string\n---\nBody"
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            parse_frontmatter(text)


class TestSerializeFrontmatter:
    def test_roundtrip(self):
        original_fm = {"agent": "claude"}
        original_body = "Do the thing"
        serialized = serialize_frontmatter(original_fm, original_body)
        fm, body = parse_frontmatter(serialized)
        assert fm == original_fm
        assert body == original_body

    def test_empty_frontmatter(self):
        result = serialize_frontmatter({}, "Just a body")
        assert result == "Just a body"
        assert "---" not in result

    def test_includes_delimiters(self):
        result = serialize_frontmatter({"agent": "claude"}, "Prompt")
        assert result.startswith("---\n")
        assert "\n---\n" in result

    def test_body_preserved(self):
        result = serialize_frontmatter({"agent": "claude"}, "My prompt text")
        assert result.endswith("My prompt text")
