"""Tests for utility functions."""

from datetime import datetime

import pytest

from src.comfyui_save_file_extended.utils import (
    process_date_variables,
    process_node_field_tokens,
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


class TestProcessNodeFieldTokens:
    """Test process_node_field_tokens function."""

    def test_no_token(self):
        """Test that text without tokens is returned unchanged."""
        text = "simple_filename"
        prompt = {"1": {"class_type": "Empty Latent Image", "inputs": {"width": 512}}}
        assert process_node_field_tokens(text, prompt) == text

    def test_empty_string(self):
        """Test that empty string is returned unchanged."""
        assert process_node_field_tokens("", {}) == ""

    def test_none_text(self):
        """Test that None text is handled gracefully."""
        assert process_node_field_tokens(None, {}) is None

    def test_none_prompt(self):
        """Test that None prompt returns text unchanged."""
        text = "%Empty Latent Image.width%"
        assert process_node_field_tokens(text, None) == text

    def test_empty_prompt(self):
        """Test that empty prompt returns text unchanged."""
        text = "%Empty Latent Image.width%"
        assert process_node_field_tokens(text, {}) == text

    def test_basic_token_replacement(self):
        """Test basic node field token replacement."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512, "height": 768, "batch_size": 1}
            }
        }
        result = process_node_field_tokens("%Empty Latent Image.width%", prompt)
        assert result == "512"

    def test_multiple_tokens(self):
        """Test multiple token replacements."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512, "height": 768}
            }
        }
        result = process_node_field_tokens(
            "size_%Empty Latent Image.width%x%Empty Latent Image.height%",
            prompt
        )
        assert result == "size_512x768"

    def test_embedded_in_text(self):
        """Test token embedded in text."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 1024}
            }
        }
        result = process_node_field_tokens(
            "ComfyUI_%Empty Latent Image.width%_output",
            prompt
        )
        assert result == "ComfyUI_1024_output"

    def test_node_not_found(self):
        """Test that unmatched node name returns original token."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512}
            }
        }
        result = process_node_field_tokens("%NonExistent Node.width%", prompt)
        assert result == "%NonExistent Node.width%"

    def test_field_not_found(self):
        """Test that unmatched field name returns original token."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512}
            }
        }
        result = process_node_field_tokens("%Empty Latent Image.nonexistent%", prompt)
        assert result == "%Empty Latent Image.nonexistent%"

    def test_different_node_types(self):
        """Test with various node types."""
        prompt = {
            "1": {
                "class_type": "KSampler",
                "inputs": {"seed": 12345, "steps": 20, "cfg": 7.5}
            },
            "2": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512, "height": 512}
            }
        }
        result = process_node_field_tokens(
            "seed_%KSampler.seed%_steps_%KSampler.steps%",
            prompt
        )
        assert result == "seed_12345_steps_20"

    def test_float_value(self):
        """Test float value conversion."""
        prompt = {
            "1": {
                "class_type": "KSampler",
                "inputs": {"cfg": 7.5}
            }
        }
        result = process_node_field_tokens("%KSampler.cfg%", prompt)
        assert result == "7.5"

    def test_string_value(self):
        """Test string value."""
        prompt = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model_v1.safetensors"}
            }
        }
        result = process_node_field_tokens(
            "%CheckpointLoaderSimple.ckpt_name%",
            prompt
        )
        assert result == "model_v1.safetensors"

    def test_linked_input_preserved(self):
        """Test that linked inputs (list/tuple) preserve original token."""
        prompt = {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["2", 0],  # Linked to another node
                    "seed": 12345
                }
            }
        }
        # Linked inputs should return original token
        result = process_node_field_tokens("%KSampler.model%", prompt)
        assert result == "%KSampler.model%"

        # But regular inputs should work
        result = process_node_field_tokens("%KSampler.seed%", prompt)
        assert result == "12345"

    def test_preserves_date_tokens(self):
        """Test that date tokens are preserved (not matching node.field pattern)."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512}
            }
        }
        result = process_node_field_tokens(
            "%date:yyyy-MM-dd%_%Empty Latent Image.width%",
            prompt
        )
        # date token preserved, node field token replaced
        assert result == "%date:yyyy-MM-dd%_512"

    def test_preserves_batch_num_token(self):
        """Test that %batch_num% is preserved."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512}
            }
        }
        result = process_node_field_tokens(
            "%Empty Latent Image.width%_%batch_num%",
            prompt
        )
        assert result == "512_%batch_num%"

    def test_multiple_nodes_same_type(self):
        """Test with multiple nodes of the same type (first match wins)."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512}
            },
            "2": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 1024}
            }
        }
        # First node found wins (dict order)
        result = process_node_field_tokens("%Empty Latent Image.width%", prompt)
        # The result depends on dict iteration order (Python 3.7+ preserves insertion order)
        assert result in ["512", "1024"]

    def test_combined_with_date_variables(self):
        """Test combining node tokens with date variables (integration test)."""
        prompt = {
            "1": {
                "class_type": "Empty Latent Image",
                "inputs": {"width": 512, "height": 768}
            }
        }
        test_date = datetime(2024, 1, 15)

        # Process date first, then node tokens
        text = "%date:yyyy-MM-dd%_%Empty Latent Image.width%x%Empty Latent Image.height%"
        result = process_date_variables(text, now=test_date)
        result = process_node_field_tokens(result, prompt)
        assert result == "2024-01-15_512x768"
