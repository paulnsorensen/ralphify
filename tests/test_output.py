from ralphify._output import collect_output, format_duration


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


class TestFormatDuration:
    def test_seconds(self):
        assert format_duration(5.3) == "5.3s"
        assert format_duration(0.1) == "0.1s"
        assert format_duration(59.9) == "59.9s"

    def test_minutes(self):
        assert format_duration(60) == "1m 0s"
        assert format_duration(90.5) == "1m 30s"
        assert format_duration(3599) == "59m 59s"

    def test_zero(self):
        assert format_duration(0.0) == "0.0s"

    def test_boundary_at_60(self):
        assert format_duration(59.94) == "59.9s"
        assert format_duration(59.95) == "1m 0s"  # rounds to 60.0, so use minute format
        assert format_duration(60) == "1m 0s"
        assert format_duration(60.4) == "1m 0s"

    def test_hours(self):
        assert format_duration(3600) == "1h 0m"
        assert format_duration(5400) == "1h 30m"

    def test_multi_day(self):
        assert format_duration(90000) == "25h 0m"
