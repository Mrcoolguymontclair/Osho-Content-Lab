"""
Unit tests for input_validator module
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from input_validator import InputValidator, ValidationError


class TestInputValidator:
    """Test input validation."""

    def test_sanitize_channel_name_valid(self):
        """Test valid channel names."""
        assert InputValidator.sanitize_channel_name("My Channel") == "My Channel"
        assert InputValidator.sanitize_channel_name("Channel_123") == "Channel_123"
        assert InputValidator.sanitize_channel_name("Test-Channel") == "Test-Channel"

    def test_sanitize_channel_name_invalid(self):
        """Test invalid channel names raise errors."""
        with pytest.raises(ValidationError):
            InputValidator.sanitize_channel_name("")

        with pytest.raises(ValidationError):
            InputValidator.sanitize_channel_name("a" * 101)  # Too long

        with pytest.raises(ValidationError):
            InputValidator.sanitize_channel_name("Bad@Channel")  # Invalid char

    def test_sanitize_filename_prevents_path_traversal(self):
        """Test that path traversal is prevented."""
        with pytest.raises(ValidationError):
            InputValidator.sanitize_filename("../../../etc/passwd")

        with pytest.raises(ValidationError):
            InputValidator.sanitize_filename("..\\windows\\system32")

    def test_sanitize_filename_valid(self):
        """Test valid filenames."""
        assert InputValidator.sanitize_filename("video.mp4") == "video.mp4"
        assert InputValidator.sanitize_filename("my_file-123.txt") == "my_file-123.txt"

    def test_safe_ffmpeg_arg_rejects_dangerous_chars(self):
        """Test that dangerous characters are rejected."""
        dangerous_inputs = [
            "file.mp4; rm -rf /",
            "file.mp4 && echo hack",
            "file.mp4 | cat /etc/passwd",
            "file.mp4 $(whoami)",
            "file.mp4 `ls`",
        ]

        for dangerous in dangerous_inputs:
            with pytest.raises(ValidationError):
                InputValidator.safe_ffmpeg_arg(dangerous)

    def test_safe_ffmpeg_arg_accepts_safe_input(self):
        """Test that safe inputs are accepted."""
        safe_inputs = [
            "video.mp4",
            "output_file.avi",
            "my-video_123.mkv",
        ]

        for safe in safe_inputs:
            result = InputValidator.safe_ffmpeg_arg(safe)
            assert result == safe

    def test_validate_video_id(self):
        """Test YouTube video ID validation."""
        # Valid video ID
        assert InputValidator.validate_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

        # Invalid video IDs
        with pytest.raises(ValidationError):
            InputValidator.validate_video_id("invalid")

        with pytest.raises(ValidationError):
            InputValidator.validate_video_id("too-short")

    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs
        assert InputValidator.validate_url("https://example.com")
        assert InputValidator.validate_url("http://test.org/path")

        # Invalid URLs
        with pytest.raises(ValidationError):
            InputValidator.validate_url("not-a-url")

        with pytest.raises(ValidationError):
            InputValidator.validate_url("ftp://unsupported.com")

    def test_validate_integer(self):
        """Test integer validation."""
        assert InputValidator.validate_integer("42") == 42
        assert InputValidator.validate_integer(42) == 42

        # With range
        assert InputValidator.validate_integer(5, min_val=0, max_val=10) == 5

        with pytest.raises(ValidationError):
            InputValidator.validate_integer("not a number")

        with pytest.raises(ValidationError):
            InputValidator.validate_integer(15, min_val=0, max_val=10)

    def test_validate_channel_id(self):
        """Test channel ID validation."""
        assert InputValidator.validate_channel_id(1) == 1
        assert InputValidator.validate_channel_id("5") == 5

        with pytest.raises(ValidationError):
            InputValidator.validate_channel_id(0)  # Must be >= 1

        with pytest.raises(ValidationError):
            InputValidator.validate_channel_id(-1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
