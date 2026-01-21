"""
Input Validation and Sanitization Module

Provides utilities for validating and sanitizing user inputs to prevent:
- Command injection
- Path traversal
- SQL injection
- XSS attacks
- Invalid data types
"""

import re
import os
from pathlib import Path
from typing import Optional, List, Union
import unicodedata


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """Utility class for validating and sanitizing inputs."""

    # Regex patterns for common validations
    CHANNEL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\s]{1,100}$')
    VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]{1,255}$')
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )

    # Dangerous characters for command injection
    SHELL_DANGEROUS_CHARS = ['&', '|', ';', '$', '`', '\n', '(', ')', '<', '>', '\\', '!']

    @staticmethod
    def sanitize_channel_name(name: str) -> str:
        """
        Sanitize channel name to prevent injection attacks.

        Args:
            name: Raw channel name input

        Returns:
            Sanitized channel name

        Raises:
            ValidationError: If name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValidationError("Channel name must be a non-empty string")

        # Remove leading/trailing whitespace
        name = name.strip()

        # Check length
        if len(name) < 1 or len(name) > 100:
            raise ValidationError("Channel name must be between 1 and 100 characters")

        # Check for valid characters
        if not InputValidator.CHANNEL_NAME_PATTERN.match(name):
            raise ValidationError(
                "Channel name can only contain letters, numbers, spaces, hyphens, and underscores"
            )

        return name

    @staticmethod
    def sanitize_filename(filename: str, allow_path: bool = False) -> str:
        """
        Sanitize filename to prevent path traversal and command injection.

        Args:
            filename: Raw filename input
            allow_path: If True, allow directory separators

        Returns:
            Sanitized filename

        Raises:
            ValidationError: If filename is invalid
        """
        if not filename or not isinstance(filename, str):
            raise ValidationError("Filename must be a non-empty string")

        # Remove null bytes
        filename = filename.replace('\0', '')

        # Normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename)

        if not allow_path:
            # Remove any path separators to prevent directory traversal
            filename = os.path.basename(filename)

            # Check for path traversal attempts
            if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
                raise ValidationError("Filename contains path traversal attempt")

        # Remove dangerous characters
        for char in InputValidator.SHELL_DANGEROUS_CHARS:
            if char in filename:
                raise ValidationError(f"Filename contains dangerous character: {char}")

        # Check length
        if len(filename) > 255:
            raise ValidationError("Filename too long (max 255 characters)")

        # Ensure not empty after sanitization
        if not filename or filename in ('.', '..'):
            raise ValidationError("Invalid filename")

        return filename

    @staticmethod
    def sanitize_path(path: str, base_dir: Optional[str] = None) -> str:
        """
        Sanitize file path to prevent directory traversal.

        Args:
            path: Raw path input
            base_dir: Base directory to restrict access to

        Returns:
            Sanitized absolute path

        Raises:
            ValidationError: If path is invalid or outside base_dir
        """
        if not path or not isinstance(path, str):
            raise ValidationError("Path must be a non-empty string")

        # Resolve to absolute path
        try:
            abs_path = os.path.abspath(path)
        except Exception as e:
            raise ValidationError(f"Invalid path: {e}")

        # If base_dir specified, ensure path is within it
        if base_dir:
            base_dir = os.path.abspath(base_dir)
            # Use os.path.commonpath to check if path is under base_dir
            try:
                common = os.path.commonpath([abs_path, base_dir])
                if common != base_dir:
                    raise ValidationError(f"Path outside allowed directory: {path}")
            except ValueError:
                raise ValidationError(f"Path outside allowed directory: {path}")

        return abs_path

    @staticmethod
    def validate_video_id(video_id: str) -> str:
        """
        Validate YouTube video ID format.

        Args:
            video_id: Raw video ID input

        Returns:
            Validated video ID

        Raises:
            ValidationError: If video ID is invalid
        """
        if not video_id or not isinstance(video_id, str):
            raise ValidationError("Video ID must be a non-empty string")

        if not InputValidator.VIDEO_ID_PATTERN.match(video_id):
            raise ValidationError("Invalid YouTube video ID format")

        return video_id

    @staticmethod
    def validate_url(url: str, allowed_domains: Optional[List[str]] = None) -> str:
        """
        Validate URL format and optionally check domain whitelist.

        Args:
            url: Raw URL input
            allowed_domains: Optional list of allowed domains

        Returns:
            Validated URL

        Raises:
            ValidationError: If URL is invalid or not in allowed domains
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string")

        # Basic URL format validation
        if not InputValidator.URL_PATTERN.match(url):
            raise ValidationError("Invalid URL format")

        # Check allowed domains if specified
        if allowed_domains:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]

            if not any(domain == allowed or domain.endswith('.' + allowed)
                      for allowed in allowed_domains):
                raise ValidationError(
                    f"URL domain not in allowed list: {domain}"
                )

        return url

    @staticmethod
    def validate_integer(value: Union[str, int], min_val: Optional[int] = None,
                        max_val: Optional[int] = None) -> int:
        """
        Validate and convert integer value.

        Args:
            value: Raw integer input
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Validated integer

        Raises:
            ValidationError: If value is not a valid integer or out of range
        """
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid integer value: {value}")

        if min_val is not None and int_val < min_val:
            raise ValidationError(f"Value {int_val} below minimum {min_val}")

        if max_val is not None and int_val > max_val:
            raise ValidationError(f"Value {int_val} above maximum {max_val}")

        return int_val

    @staticmethod
    def validate_float(value: Union[str, float], min_val: Optional[float] = None,
                      max_val: Optional[float] = None) -> float:
        """
        Validate and convert float value.

        Args:
            value: Raw float input
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Validated float

        Raises:
            ValidationError: If value is not a valid float or out of range
        """
        try:
            float_val = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid float value: {value}")

        if min_val is not None and float_val < min_val:
            raise ValidationError(f"Value {float_val} below minimum {min_val}")

        if max_val is not None and float_val > max_val:
            raise ValidationError(f"Value {float_val} above maximum {max_val}")

        return float_val

    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """
        Sanitize input for SQL queries (use parameterized queries instead when possible).

        Args:
            text: Raw text input

        Returns:
            Sanitized text

        Note:
            This is a defense-in-depth measure. Always use parameterized queries.
        """
        if not isinstance(text, str):
            text = str(text)

        # Remove null bytes
        text = text.replace('\0', '')

        # Escape single quotes for SQL
        text = text.replace("'", "''")

        return text

    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Sanitize HTML to prevent XSS attacks.

        Args:
            text: Raw HTML input

        Returns:
            Sanitized HTML
        """
        if not isinstance(text, str):
            text = str(text)

        # Basic HTML entity encoding
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
        }

        for char, entity in replacements.items():
            text = text.replace(char, entity)

        return text

    @staticmethod
    def validate_enum(value: str, allowed_values: List[str],
                     case_sensitive: bool = False) -> str:
        """
        Validate that value is in allowed list.

        Args:
            value: Raw value input
            allowed_values: List of allowed values
            case_sensitive: Whether comparison is case-sensitive

        Returns:
            Validated value

        Raises:
            ValidationError: If value not in allowed list
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        check_value = value if case_sensitive else value.lower()
        check_list = allowed_values if case_sensitive else [v.lower() for v in allowed_values]

        if check_value not in check_list:
            raise ValidationError(
                f"Value '{value}' not in allowed list: {', '.join(allowed_values)}"
            )

        return value

    @staticmethod
    def validate_channel_id(channel_id: Union[str, int]) -> int:
        """
        Validate channel ID.

        Args:
            channel_id: Raw channel ID input

        Returns:
            Validated channel ID as integer

        Raises:
            ValidationError: If channel ID is invalid
        """
        return InputValidator.validate_integer(channel_id, min_val=1)

    @staticmethod
    def sanitize_search_query(query: str, max_length: int = 500) -> str:
        """
        Sanitize search query.

        Args:
            query: Raw search query
            max_length: Maximum query length

        Returns:
            Sanitized query

        Raises:
            ValidationError: If query is invalid
        """
        if not query or not isinstance(query, str):
            raise ValidationError("Search query must be a non-empty string")

        query = query.strip()

        if len(query) > max_length:
            raise ValidationError(f"Search query too long (max {max_length} characters)")

        if len(query) < 1:
            raise ValidationError("Search query cannot be empty")

        return query

    @staticmethod
    def safe_ffmpeg_arg(arg: str) -> str:
        """
        Sanitize argument for FFmpeg command to prevent command injection.

        Args:
            arg: Raw FFmpeg argument

        Returns:
            Sanitized argument

        Raises:
            ValidationError: If argument contains dangerous characters
        """
        if not isinstance(arg, str):
            arg = str(arg)

        # Check for shell dangerous characters
        for char in InputValidator.SHELL_DANGEROUS_CHARS:
            if char in arg:
                raise ValidationError(
                    f"FFmpeg argument contains dangerous character: {char}"
                )

        return arg


# Convenience functions
def sanitize_channel_name(name: str) -> str:
    """Sanitize channel name."""
    return InputValidator.sanitize_channel_name(name)


def sanitize_filename(filename: str, allow_path: bool = False) -> str:
    """Sanitize filename."""
    return InputValidator.sanitize_filename(filename, allow_path)


def validate_channel_id(channel_id: Union[str, int]) -> int:
    """Validate channel ID."""
    return InputValidator.validate_channel_id(channel_id)


def safe_ffmpeg_arg(arg: str) -> str:
    """Sanitize FFmpeg argument."""
    return InputValidator.safe_ffmpeg_arg(arg)


if __name__ == '__main__':
    # Test input validator
    print("Input Validator Test")
    print("=" * 50)

    # Test channel name
    try:
        name = InputValidator.sanitize_channel_name("My Channel 123")
        print(f"[OK] Valid channel name: {name}")
    except ValidationError as e:
        print(f"[FAIL] Invalid channel name: {e}")

    # Test filename
    try:
        filename = InputValidator.sanitize_filename("../../../etc/passwd")
        print(f"[OK] Valid filename: {filename}")
    except ValidationError as e:
        print(f"[FAIL] Invalid filename (expected): {e}")

    # Test video ID
    try:
        vid_id = InputValidator.validate_video_id("dQw4w9WgXcQ")
        print(f"[OK] Valid video ID: {vid_id}")
    except ValidationError as e:
        print(f"[FAIL] Invalid video ID: {e}")

    # Test URL
    try:
        url = InputValidator.validate_url("https://example.com/path")
        print(f"[OK] Valid URL: {url}")
    except ValidationError as e:
        print(f"[FAIL] Invalid URL: {e}")

    # Test FFmpeg arg
    try:
        arg = InputValidator.safe_ffmpeg_arg("video.mp4")
        print(f"[OK] Safe FFmpeg arg: {arg}")
    except ValidationError as e:
        print(f"[FAIL] Unsafe FFmpeg arg: {e}")

    try:
        arg = InputValidator.safe_ffmpeg_arg("video.mp4; rm -rf /")
        print(f"[OK] Safe FFmpeg arg: {arg}")
    except ValidationError as e:
        print(f"[FAIL] Unsafe FFmpeg arg (expected): {e}")

    print("\nValidation tests completed!")
