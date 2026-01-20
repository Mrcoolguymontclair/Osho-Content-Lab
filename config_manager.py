"""
Centralized Configuration Manager for Osho Content Lab

Handles all configuration loading from environment variables, secrets files,
and provides a clean interface for accessing configuration throughout the application.

Security features:
- Environment variables take precedence over files
- Proper error handling for missing configuration
- No hardcoded paths
- Support for multiple configuration sources
"""

import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path
import json


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class ConfigManager:
    """
    Centralized configuration manager.

    Priority order (highest to lowest):
    1. Environment variables
    2. .streamlit/secrets.toml file
    3. .env file
    4. Default values
    """

    _instance = None
    _config_cache: Dict[str, Any] = {}
    _initialized = False

    def __new__(cls):
        """Singleton pattern to ensure single configuration instance."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize configuration manager."""
        if not self._initialized:
            self._load_configuration()
            ConfigManager._initialized = True

    def _load_configuration(self):
        """Load configuration from all available sources."""
        # Try to load from .env file if it exists
        self._load_env_file()

        # Try to load from secrets.toml if it exists
        self._load_secrets_toml()

        # Environment variables will be checked at access time (highest priority)

    def _load_env_file(self):
        """Load configuration from .env file if it exists."""
        env_file = Path('.env')
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key not in self._config_cache:
                                self._config_cache[key] = value
            except Exception as e:
                print(f"Warning: Failed to load .env file: {e}", file=sys.stderr)

    def _load_secrets_toml(self):
        """Load configuration from secrets.toml file if it exists."""
        secrets_path = Path('.streamlit/secrets.toml')
        if secrets_path.exists():
            try:
                import toml
                secrets = toml.load(secrets_path)
                # Flatten nested structure
                self._flatten_dict(secrets, self._config_cache)
            except ImportError:
                print("Warning: toml package not installed, skipping secrets.toml", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to load secrets.toml: {e}", file=sys.stderr)

    def _flatten_dict(self, nested_dict: Dict, target_dict: Dict, prefix: str = ''):
        """Flatten nested dictionary into single-level keys."""
        for key, value in nested_dict.items():
            new_key = f"{prefix}_{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_dict(value, target_dict, new_key)
            else:
                if new_key not in target_dict:
                    target_dict[new_key] = value

    def get(self, key: str, default: Optional[Any] = None, required: bool = False) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (e.g., 'GROQ_API_KEY', 'PEXELS_API_KEY')
            default: Default value if key not found
            required: If True, raise ConfigurationError if key not found

        Returns:
            Configuration value

        Raises:
            ConfigurationError: If required=True and key not found
        """
        # Check environment variables first (highest priority)
        value = os.environ.get(key)

        # Check cache (from files)
        if value is None:
            value = self._config_cache.get(key)

        # Check default
        if value is None:
            value = default

        # Raise error if required and not found
        if value is None and required:
            raise ConfigurationError(
                f"Required configuration '{key}' not found. "
                f"Set it as an environment variable or in .streamlit/secrets.toml or .env file."
            )

        return value

    def get_int(self, key: str, default: Optional[int] = None, required: bool = False) -> int:
        """Get configuration value as integer."""
        value = self.get(key, default, required)
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            if required:
                raise ConfigurationError(f"Configuration '{key}' must be an integer, got: {value}")
            return default

    def get_bool(self, key: str, default: Optional[bool] = None, required: bool = False) -> bool:
        """Get configuration value as boolean."""
        value = self.get(key, default, required)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        # Handle string representations
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def get_float(self, key: str, default: Optional[float] = None, required: bool = False) -> float:
        """Get configuration value as float."""
        value = self.get(key, default, required)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            if required:
                raise ConfigurationError(f"Configuration '{key}' must be a float, got: {value}")
            return default

    def get_list(self, key: str, default: Optional[list] = None, required: bool = False) -> list:
        """
        Get configuration value as list.
        Supports JSON array strings or comma-separated values.
        """
        value = self.get(key, default, required)
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try JSON first
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Try comma-separated
            return [item.strip() for item in value.split(',') if item.strip()]
        return default

    def set(self, key: str, value: Any):
        """Set configuration value (for runtime configuration)."""
        self._config_cache[key] = value

    def has(self, key: str) -> bool:
        """Check if configuration key exists."""
        return os.environ.get(key) is not None or key in self._config_cache

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration (excluding sensitive env vars)."""
        config = dict(self._config_cache)
        # Add non-sensitive env vars
        for key in ['PATH', 'HOME', 'USER', 'PWD']:
            if key in os.environ:
                config[key] = os.environ[key]
        return config

    # Convenience methods for common configuration

    def get_groq_api_key(self) -> str:
        """Get Groq API key."""
        return self.get('GROQ_API_KEY', required=True)

    def get_pexels_api_key(self) -> str:
        """Get Pexels API key."""
        return self.get('PEXELS_API_KEY', required=True)

    def get_youtube_client_secrets_file(self) -> str:
        """Get YouTube OAuth client secrets file path."""
        return self.get('YOUTUBE_CLIENT_SECRETS_FILE', default='client_secrets.json')

    def get_database_path(self) -> str:
        """Get database file path."""
        return self.get('DATABASE_PATH', default='channels.db')

    def get_tokens_directory(self) -> str:
        """Get tokens directory path."""
        return self.get('TOKENS_DIR', default='tokens')

    def get_music_directory(self) -> str:
        """Get music directory path."""
        return self.get('MUSIC_DIR', default='music')

    def get_log_level(self) -> str:
        """Get logging level."""
        return self.get('LOG_LEVEL', default='INFO')

    def get_max_log_size(self) -> int:
        """Get maximum log file size in bytes."""
        return self.get_int('MAX_LOG_SIZE', default=10485760)  # 10MB default

    def get_log_backup_count(self) -> int:
        """Get number of log backup files to keep."""
        return self.get_int('LOG_BACKUP_COUNT', default=5)

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_bool('DEBUG', default=False)

    def get_ffmpeg_path(self) -> str:
        """Get FFmpeg executable path."""
        return self.get('FFMPEG_PATH', default='ffmpeg')

    def get_ffprobe_path(self) -> str:
        """Get FFprobe executable path."""
        return self.get('FFPROBE_PATH', default='ffprobe')


# Global singleton instance
_config = None


def get_config() -> ConfigManager:
    """
    Get the global configuration manager instance.

    Returns:
        ConfigManager singleton instance
    """
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config


# Convenience functions for backward compatibility
def get(key: str, default: Optional[Any] = None, required: bool = False) -> Any:
    """Get configuration value."""
    return get_config().get(key, default, required)


def get_groq_api_key() -> str:
    """Get Groq API key."""
    return get_config().get_groq_api_key()


def get_pexels_api_key() -> str:
    """Get Pexels API key."""
    return get_config().get_pexels_api_key()


if __name__ == '__main__':
    # Test configuration manager
    config = get_config()

    print("Configuration Manager Test")
    print("=" * 50)

    # Test basic get
    print(f"Debug mode: {config.is_debug_mode()}")
    print(f"Log level: {config.get_log_level()}")
    print(f"Database path: {config.get_database_path()}")
    print(f"FFmpeg path: {config.get_ffmpeg_path()}")

    # Test required key (will fail if not set)
    try:
        groq_key = config.get_groq_api_key()
        print(f"Groq API key: {'*' * 8}{groq_key[-4:] if len(groq_key) > 4 else ''}")
    except ConfigurationError as e:
        print(f"Missing required config: {e}")

    print("\nConfiguration loaded successfully!")
