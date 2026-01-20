"""
Unit tests for config_manager module
"""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import ConfigManager, ConfigurationError


class TestConfigManager:
    """Test configuration manager."""

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2

    def test_get_default_values(self):
        """Test getting values with defaults."""
        config = ConfigManager()
        value = config.get('NONEXISTENT_KEY', default='default_value')
        assert value == 'default_value'

    def test_get_required_missing_raises_error(self):
        """Test that required missing keys raise error."""
        config = ConfigManager()
        with pytest.raises(ConfigurationError):
            config.get('DEFINITELY_DOES_NOT_EXIST_KEY', required=True)

    def test_get_int(self):
        """Test integer conversion."""
        config = ConfigManager()
        config.set('TEST_INT', '42')
        value = config.get_int('TEST_INT')
        assert value == 42
        assert isinstance(value, int)

    def test_get_bool(self):
        """Test boolean conversion."""
        config = ConfigManager()

        # Test string representations
        config.set('TEST_BOOL_TRUE', 'true')
        assert config.get_bool('TEST_BOOL_TRUE') is True

        config.set('TEST_BOOL_FALSE', 'false')
        assert config.get_bool('TEST_BOOL_FALSE') is False

        config.set('TEST_BOOL_ONE', '1')
        assert config.get_bool('TEST_BOOL_ONE') is True

    def test_get_float(self):
        """Test float conversion."""
        config = ConfigManager()
        config.set('TEST_FLOAT', '3.14')
        value = config.get_float('TEST_FLOAT')
        assert abs(value - 3.14) < 0.01
        assert isinstance(value, float)

    def test_get_list_from_json(self):
        """Test list parsing from JSON."""
        config = ConfigManager()
        config.set('TEST_LIST', '["a", "b", "c"]')
        value = config.get_list('TEST_LIST')
        assert value == ["a", "b", "c"]

    def test_get_list_from_csv(self):
        """Test list parsing from comma-separated values."""
        config = ConfigManager()
        config.set('TEST_CSV', 'a, b, c')
        value = config.get_list('TEST_CSV')
        assert value == ["a", "b", "c"]

    def test_has_key(self):
        """Test key existence check."""
        config = ConfigManager()
        config.set('EXISTS', 'value')
        assert config.has('EXISTS') is True
        assert config.has('DOES_NOT_EXIST') is False

    def test_database_path_default(self):
        """Test default database path."""
        config = ConfigManager()
        path = config.get_database_path()
        assert path == 'channels.db'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
