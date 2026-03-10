from ralphify._output import MAX_OUTPUT_LEN, collect_output, truncate_output


class TestCollectOutput:
    def test_both_strings(self):
        assert collect_output("out\n", "err\n") == "out\nerr\n"

    def test_stdout_only(self):
        assert collect_output("out\n", "") == "out\n"

    def test_stderr_only(self):
        assert collect_output("", "err\n") == "err\n"

    def test_both_none(self):
        assert collect_output(None, None) == ""

    def test_stdout_none(self):
        assert collect_output(None, "err\n") == "err\n"

    def test_stderr_none(self):
        assert collect_output("out\n", None) == "out\n"

    def test_both_empty(self):
        assert collect_output("", "") == ""

    def test_bytes_stdout(self):
        assert collect_output(b"out\n", None) == "out\n"

    def test_bytes_stderr(self):
        assert collect_output(None, b"err\n") == "err\n"

    def test_bytes_both(self):
        assert collect_output(b"out\n", b"err\n") == "out\nerr\n"

    def test_mixed_str_and_bytes(self):
        assert collect_output("out\n", b"err\n") == "out\nerr\n"

    def test_bytes_with_replacement(self):
        result = collect_output(b"hello\xff\n", None)
        assert "hello" in result
        assert "\ufffd" in result  # replacement character


class TestTruncateOutput:
    def test_short_text_unchanged(self):
        assert truncate_output("hello") == "hello"

    def test_empty_string(self):
        assert truncate_output("") == ""

    def test_exact_limit_unchanged(self):
        text = "x" * MAX_OUTPUT_LEN
        assert truncate_output(text) == text

    def test_over_limit_truncated(self):
        text = "x" * (MAX_OUTPUT_LEN + 100)
        result = truncate_output(text)
        assert len(result) < len(text)
        assert result.endswith("... (truncated)")

    def test_custom_max_len(self):
        result = truncate_output("hello world", max_len=5)
        assert result == "hello\n... (truncated)"
