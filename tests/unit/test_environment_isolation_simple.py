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
        """Test that environment variables are properly isolated and accessible through IsolatedEnvironment."""
        # Use IsolatedEnvironment to properly isolate test settings
        from netra_backend.app.core.isolated_environment import get_env
        
        # Store original values to restore later
        original_env_val = os.environ.get('ENVIRONMENT')
        original_database_url = os.environ.get('DATABASE_URL')
        original_redis_url = os.environ.get('REDIS_URL')
        
        env = get_env()
        
        # Enable isolation mode to prevent conflicts with global test setup
        env.enable_isolation()
        
        try:
            # Set test configuration values through IsolatedEnvironment
            env.set('ENVIRONMENT', 'development', source='test')
            env.set('DATABASE_URL', 'postgresql://test@localhost/test_db', source='test')
            env.set('REDIS_URL', 'redis://test:6379/1', source='test')
            
            # Also clear conflicting environment variables that might interfere
            env.set('NETRA_ENV', '', source='test_clear')  # Clear the e2e test override
            
            # Verify the isolated environment has our values
            assert env.get('ENVIRONMENT') == 'development'
            assert env.get('DATABASE_URL') == 'postgresql://test@localhost/test_db'
            assert env.get('REDIS_URL') == 'redis://test:6379/1'
            assert env.get('NETRA_ENV') == ''  # Cleared value
            
            # Verify isolation works - os.environ should be unchanged
            if original_env_val is not None:
                assert os.environ.get('ENVIRONMENT') == original_env_val
            if original_database_url is not None:
                assert os.environ.get('DATABASE_URL') == original_database_url  
            if original_redis_url is not None:
                assert os.environ.get('REDIS_URL') == original_redis_url
                
            # Test that the basic config manager can use IsolatedEnvironment for environment detection
            from netra_backend.app.core.configuration.base import config_manager
            
            # Force refresh of environment detection to pick up our isolated values
            config_manager._refresh_environment_detection()
            
            # The environment should now be detected from our isolated environment
            assert config_manager._environment == 'development'
            
            # Test subprocess environment generation includes our values
            subprocess_env = env.get_subprocess_env()
            assert subprocess_env.get('ENVIRONMENT') == 'development'
            assert subprocess_env.get('DATABASE_URL') == 'postgresql://test@localhost/test_db'
            assert subprocess_env.get('REDIS_URL') == 'redis://test:6379/1'
            
            # Verify critical system variables are still present in subprocess env
            assert 'PATH' in subprocess_env
            
        finally:
            # Clean up isolation mode
            env.disable_isolation()
            
            # Restore original values if they existed
            if original_env_val is not None:
                os.environ['ENVIRONMENT'] = original_env_val
            else:
                os.environ.pop('ENVIRONMENT', None)
                
            if original_database_url is not None:
                os.environ['DATABASE_URL'] = original_database_url
            else:
                os.environ.pop('DATABASE_URL', None)
                
            if original_redis_url is not None:
                os.environ['REDIS_URL'] = original_redis_url  
            else:
                os.environ.pop('REDIS_URL', None)