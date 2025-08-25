"""Simple test for environment isolation functionality.

This test focuses on verifying that the IsolatedEnvironment and
configuration management works correctly for environment variable loading.
"""

import os
import pytest
from unittest.mock import patch

from netra_backend.app.core.isolated_environment import get_env


class TestEnvironmentIsolation:
    """Test environment isolation functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Store original environment
        self.original_env = os.environ.copy()
        
        # Clear test-specific variables that might interfere
        test_vars = ['TEST_VAR_1', 'TEST_VAR_2', 'NETRA_TEST_VAR', 'TESTING']
        for var in test_vars:
            os.environ.pop(var, None)
            
        yield
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_isolated_environment_basic_access(self):
        """Test basic environment variable access through IsolatedEnvironment."""
        # Set test environment variable
        os.environ['TEST_VAR_1'] = 'test_value_1'
        
        # Get environment through isolated access
        env = get_env()
        
        # Verify access works
        assert env.get('TEST_VAR_1') == 'test_value_1'
        assert env.get('NON_EXISTENT_VAR') is None
        assert env.get('NON_EXISTENT_VAR', 'default') == 'default'

    def test_isolated_environment_overrides(self):
        """Test that environment variables can be overridden."""
        # Set initial value
        os.environ['TEST_VAR_2'] = 'initial_value'
        
        # Verify initial value
        env = get_env()
        assert env.get('TEST_VAR_2') == 'initial_value'
        
        # Override value
        os.environ['TEST_VAR_2'] = 'overridden_value'
        
        # Verify override works (may need fresh env instance)
        env_fresh = get_env()
        assert env_fresh.get('TEST_VAR_2') == 'overridden_value'

    def test_environment_source_tracking(self):
        """Test that IsolatedEnvironment can track variable sources."""
        # Set a variable
        os.environ['NETRA_TEST_VAR'] = 'tracked_value'
        
        # Get environment
        env = get_env()
        
        # Access the variable
        value = env.get('NETRA_TEST_VAR')
        assert value == 'tracked_value'
        
        # Basic functionality test - we're not testing full source tracking here
        # just that the basic environment access works
        
    def test_configuration_environment_detection(self):
        """Test that configuration properly detects environment from IsolatedEnvironment."""
        # Set development environment
        os.environ['ENVIRONMENT'] = 'development'
        
        # Import and test configuration manager
        from netra_backend.app.core.configuration.base import config_manager
        
        # Force refresh to pick up our environment setting
        config_manager._environment = config_manager._detect_environment()
        
        # Verify environment detection works
        assert config_manager._environment == 'development'
        
        # Test with staging
        os.environ['ENVIRONMENT'] = 'staging' 
        config_manager._environment = config_manager._detect_environment()
        assert config_manager._environment == 'staging'

    def test_environment_variable_isolation_in_config(self):
        """Test that configuration loads environment variables correctly through IsolatedEnvironment."""
        # Set test configuration values
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['DATABASE_URL'] = 'postgresql://test@localhost/test_db'
        os.environ['REDIS_URL'] = 'redis://test:6379/1'
        
        from netra_backend.app.core.configuration.base import config_manager
        
        # Clear any cached configuration to force reload
        config_manager._config_cache = None  
        config_manager.get_config.cache_clear()
        
        # Clear database manager caches as well
        if hasattr(config_manager, '_database_manager'):
            config_manager._database_manager._redis_url_cache = None
            config_manager._database_manager._postgres_url_cache = None
        
        # Load fresh configuration
        config = config_manager.get_config()
        
        # Verify configuration loaded our test values
        assert config.environment == 'development'
        assert config.database_url == 'postgresql://test@localhost/test_db'
        assert config.redis_url == 'redis://test:6379/1'