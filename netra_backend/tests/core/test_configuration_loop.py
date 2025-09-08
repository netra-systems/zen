import pytest
from unittest.mock import Mock, patch, MagicMock

"""Test to reproduce and fix configuration loop issue."""
import unittest
import logging
from netra_backend.app.core.configuration.base import UnifiedConfigManager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager


class TestConfigurationLoop(unittest.TestCase):
    """Test cases for configuration loop issue."""
    
    def setUp(self):
        """Set up test environment."""
        self.log_calls = []
        
        # Store the original method properly
        self.original_log_info = logging.Logger.info
        
        # Create a closure to capture log calls
        test_instance = self
        
        def mock_log_info(logger_self, message, *args, **kwargs):
            if "All configuration caches cleared" in str(message):
                test_instance.log_calls.append(message)
            return test_instance.original_log_info(logger_self, message, *args, **kwargs)
        
        logging.Logger.info == mock_log_info
        
    def tearDown(self):
        """Clean up after tests."""
        logging.Logger.info = self.original_log_info
    
    def test_configuration_not_cleared_in_development(self):
        """Test that configuration is not repeatedly cleared in development mode."""
        # Create mock environment that simulates development
        mock_env = MagicMock(spec = IsolatedEnvironment)
        mock_env.get.side_effect = lambda key, default = None: {
            'ENVIRONMENT': 'development',
            'TEST_MODE': 'false',
            'TESTING': None,
            'PYTEST_CURRENT_TEST': None,
}.get(key, default)
        
        with patch('netra_backend.app.core.configuration.base.get_env', return_value = mock_env):
            # Create configuration manager
            config_manager = UnifiedConfigManager()
            
            # Clear the log calls
            self.log_calls.clear()
            
            # Call get_config multiple times
            for i in range(5):
                _ = config_manager.get_config()
            
            # In development mode, caches should NOT be cleared repeatedly
            # The log message should appear at most once (during initialization)
            self.assertLessEqual(
                len(self.log_calls), 
                1,
                f"Configuration caches were cleared {len(self.log_calls)} times in development mode. "
                f"Expected at most 1 time. This indicates a configuration loop.",
)
    
    def test_configuration_cleared_only_in_test_context(self):
        """Test that configuration is cleared only when actually in test context."""
        # Simulate test environment
        mock_test_env = MagicMock(spec = IsolatedEnvironment)
        mock_test_env.get.side_effect = lambda key, default = None: {
            'ENVIRONMENT': 'test',
            'TEST_MODE': 'true',
            'TESTING': 'true',
            'PYTEST_CURRENT_TEST': None,
}.get(key, default)
        
        with patch('netra_backend.app.core.configuration.base.get_env', return_value = mock_test_env):
            config_manager = UnifiedConfigManager()
            self.log_calls.clear()
            
            # In test mode, clearing is expected
            for i in range(3):
                _ = config_manager.get_config()
            
            # In test context, we expect clearing on each call
            self.assertGreaterEqual(
                len(self.log_calls),
                3,
                "Configuration should be cleared on each call in test context",
)
    
    def test_no_loop_with_caching_enabled(self):
        """Test that configuration caching prevents loops in production."""
        # Simulate production environment
        mock_prod_env = MagicMock(spec = IsolatedEnvironment)
        mock_prod_env.get.side_effect = lambda key, default = None: {
            'ENVIRONMENT': 'production',
            'TEST_MODE': None,
            'TESTING': None,
            'PYTEST_CURRENT_TEST': None,
}.get(key, default)
        
        with patch('netra_backend.app.core.configuration.base.get_env', return_value = mock_prod_env):
            config_manager = UnifiedConfigManager()
            self.log_calls.clear()
            
            # Call get_config multiple times
            configs = []
            for i in range(10):
                configs.append(config_manager.get_config())
            
            # All configs should be the same cached instance
            for i in range(1, len(configs)):
                self.assertIs(
                    configs[i], 
                    configs[0],
                    "Configuration should be cached and return the same instance",
)
            
            # No cache clearing should occur
            self.assertEqual(
                len(self.log_calls),
                0,
                f"Configuration caches were cleared {len(self.log_calls)} times in production mode. "
                f"Expected 0 times.",
)


if __name__ == '__main__':
    unittest.main()