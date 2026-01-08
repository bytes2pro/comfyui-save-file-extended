"""Tests for utility functions."""

from datetime import datetime

import pytest

from src.comfyui_save_file_extended.utils import (
    process_date_variables,
    sanitize_filename,
)


class TestProcessDateVariables:
    """Test process_date_variables function."""

    def test_no_date_pattern(self):
        """Test that text without date patterns is returned unchanged."""
        text = "simple_filename"
        assert process_date_variables(text) == text

    def test_empty_string(self):
        """Test that empty string is returned unchanged."""
        assert process_date_variables("") == ""

    def test_none_input(self):
        """Test that None is handled gracefully."""
        assert process_date_variables(None) is None

    def test_basic_date_format(self):
        """Test basic yyyy-MM-dd format."""
        test_date = datetime(2024, 1, 15, 14, 30, 45)
        result = process_date_variables("%date:yyyy-MM-dd%", now=test_date)
        assert result == "2024-01-15"

    def test_date_time_format(self):
        """Test date with time format."""
        test_date = datetime(2024, 1, 15, 14, 30, 45)
        result = process_date_variables("%date:yyyyMMdd_HHmmss%", now=test_date)
        assert result == "20240115_143045"

    def test_year_only(self):
        """Test year only format."""
        test_date = datetime(2024, 1, 15)
        result = process_date_variables("%date:yyyy%", now=test_date)
        assert result == "2024"

    def test_two_digit_year(self):
        """Test two-digit year format."""
        test_date = datetime(2024, 1, 15)
        result = process_date_variables("%date:yy%", now=test_date)
        assert result == "24"

    def test_month_formats(self):
        """Test various month formats."""
        test_date = datetime(2024, 1, 15)

        # Full month name
        result = process_date_variables("%date:MMMM%", now=test_date)
        assert result == "January"

        # Abbreviated month name
        result = process_date_variables("%date:MMM%", now=test_date)
        assert result == "Jan"

        # Two-digit month
        result = process_date_variables("%date:MM%", now=test_date)
        assert result == "01"

        # Single digit month (no leading zero)
        result = process_date_variables("%date:M%", now=test_date)
        assert result == "1"

    def test_day_formats(self):
        """Test various day formats."""
        test_date = datetime(2024, 1, 5)

        # Two-digit day
        result = process_date_variables("%date:dd%", now=test_date)
        assert result == "05"

        # Single digit day (no leading zero)
        result = process_date_variables("%date:d%", now=test_date)
        assert result == "5"

    def test_weekday_formats(self):
        """Test weekday formats."""
        test_date = datetime(2024, 1, 15)  # Monday

        # Full weekday name
        result = process_date_variables("%date:EEEE%", now=test_date)
        assert result == "Monday"

        # Abbreviated weekday name
        result = process_date_variables("%date:EEE%", now=test_date)
        assert result == "Mon"

    def test_hour_formats(self):
        """Test hour formats."""
        test_date = datetime(2024, 1, 15, 14, 30, 45)

        # 24-hour format
        result = process_date_variables("%date:HH%", now=test_date)
        assert result == "14"

        # 12-hour format
        result = process_date_variables("%date:hh%", now=test_date)
        assert result == "02"

    def test_minute_second_formats(self):
        """Test minute and second formats."""
        test_date = datetime(2024, 1, 15, 14, 30, 45)

        result = process_date_variables("%date:mm%", now=test_date)
        assert result == "30"

        result = process_date_variables("%date:ss%", now=test_date)
        assert result == "45"

    def test_am_pm_marker(self):
        """Test AM/PM marker."""
        # PM time
        test_date = datetime(2024, 1, 15, 14, 30, 45)
        result = process_date_variables("%date:a%", now=test_date)
        assert result.upper() == "PM"

        # AM time
        test_date = datetime(2024, 1, 15, 9, 30, 45)
        result = process_date_variables("%date:a%", now=test_date)
        assert result.upper() == "AM"

    def test_embedded_in_text(self):
        """Test date pattern embedded in text."""
        test_date = datetime(2024, 1, 15)
        result = process_date_variables("file_%date:yyyy%_test", now=test_date)
        assert result == "file_2024_test"

    def test_prefix_with_date(self):
        """Test typical filename prefix with date."""
        test_date = datetime(2024, 1, 15)
        result = process_date_variables("ComfyUI_%date:yyyy-MM-dd%", now=test_date)
        assert result == "ComfyUI_2024-01-15"

    def test_multiple_date_patterns(self):
        """Test multiple date patterns in same string."""
        test_date = datetime(2024, 1, 15, 14, 30)
        result = process_date_variables(
            "%date:yyyy-MM-dd%/images/%date:HH-mm%",
            now=test_date
        )
        assert result == "2024-01-15/images/14-30"

    def test_complex_format(self):
        """Test complex format with multiple components."""
        test_date = datetime(2024, 1, 15, 14, 30, 45)
        result = process_date_variables(
            "%date:yyyy-MM-dd_HH-mm-ss%",
            now=test_date
        )
        assert result == "2024-01-15_14-30-45"

    def test_preserves_other_percent_signs(self):
        """Test that other % patterns are preserved."""
        test_date = datetime(2024, 1, 15)
        result = process_date_variables(
            "%date:yyyy%_%batch_num%",
            now=test_date
        )
        assert result == "2024_%batch_num%"

    def test_slash_in_path(self):
        """Test date pattern in path with slashes."""
        test_date = datetime(2024, 1, 15)
        result = process_date_variables(
            "outputs/%date:yyyy%/%date:MM%/%date:dd%",
            now=test_date
        )
        assert result == "outputs/2024/01/15"


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_normal_filename(self):
        """Test normal filename is unchanged."""
        assert sanitize_filename("test.png") == "test.png"

    def test_path_traversal_unix(self):
        """Test Unix path traversal is sanitized."""
        result = sanitize_filename("../../../etc/passwd")
        assert result == "passwd"
        assert ".." not in result
        assert "/" not in result

    def test_path_traversal_windows(self):
        """Test Windows path traversal is sanitized."""
        result = sanitize_filename("..\\windows\\system32")
        assert result == "system32"
        assert ".." not in result
        assert "\\" not in result

    def test_empty_string(self):
        """Test empty string returns None."""
        assert sanitize_filename("") is None

    def test_dot_only(self):
        """Test single dot returns None."""
        assert sanitize_filename(".") is None

    def test_double_dot(self):
        """Test double dot returns None."""
        assert sanitize_filename("..") is None

    def test_whitespace_only(self):
        """Test whitespace-only string returns None."""
        assert sanitize_filename("   ") is None

    def test_null_bytes_removed(self):
        """Test null bytes are removed."""
        result = sanitize_filename("test\x00file.png")
        assert "\x00" not in result
        assert result == "testfile.png"
