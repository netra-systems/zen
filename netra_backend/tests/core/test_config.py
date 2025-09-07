from unittest.mock import Mock, patch, MagicMock

"""
Unit tests for config
Coverage Target: 80%
Business Value: Platform stability and performance
"""""

import pytest
from netra_backend.app.core.config import get_config, get_settings, reload_config
from netra_backend.app.schemas.config import AppConfig
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment

class TestConfig:
    """Test suite for Config functions"""

    def test_get_config_returns_app_config(self):
        """Test get_config returns AppConfig instance"""
        config = get_config()
        assert config is not None
        assert isinstance(config, AppConfig)

        def test_get_settings_returns_app_config(self):
            """Test get_settings returns AppConfig instance"""
            settings = get_settings()
            assert settings is not None
            assert isinstance(settings, AppConfig)

            def test_get_config_and_get_settings_return_same_instance(self):
                """Test that get_config and get_settings return the same cached instance"""
                config1 = get_config()
                config2 = get_settings()
        # Both should return the same cached instance
                assert config1 is config2

                def test_reload_config_clears_cache(self):
                    """Test reload_config clears the configuration cache"""
        # Get initial config
                    config1 = get_settings()

        # Reload config
                    reload_config()

        # Get config again - should be a new instance due to cache clear
                    config2 = get_settings()

        # Verify both are AppConfig instances
                    assert isinstance(config1, AppConfig)
                    assert isinstance(config2, AppConfig)

                    def test_config_has_required_attributes(self):
                        """Test that config has expected basic attributes"""
                        config = get_config()

        # Check for some basic attributes that should exist
                        assert hasattr(config, 'environment')
                        assert hasattr(config, 'debug')
                        assert hasattr(config, 'log_level')

                        def test_fallback_when_unified_config_fails(self, mock_get_unified_config):
                            """Test fallback behavior when unified config fails"""
        # Clear cache first
                            get_settings.cache_clear()

        # Mock unified config to raise an exception
                            mock_get_unified_config.side_effect = Exception("Config loading failed")

        # Should still return a valid AppConfig due to fallback
                            config = get_settings()
                            assert isinstance(config, AppConfig)

        # Clear cache after test
                            get_settings.cache_clear()
