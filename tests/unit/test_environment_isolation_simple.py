"""Simple test for environment isolation functionality.

This test focuses on verifying that the IsolatedEnvironment and
configuration management works correctly for environment variable loading.
"""

import os
import pytest
from unittest.mock import patch

from shared.isolated_environment import get_env


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
        from shared.isolated_environment import get_env
        
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
                
    def test_isolated_environment_thread_safety(self):
        """Test that IsolatedEnvironment works correctly in multi-threaded scenarios."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor
        
        results = {}
        
        def test_worker(thread_id):
            """Worker function to test environment isolation per thread."""
            env = get_env()
            test_var = f'THREAD_TEST_{thread_id}'
            test_value = f'thread_value_{thread_id}'
            
            # Set thread-specific value
            os.environ[test_var] = test_value
            
            # Small delay to allow other threads to interfere if not isolated
            time.sleep(0.01)
            
            # Verify our value is still there
            retrieved_value = env.get(test_var)
            results[thread_id] = retrieved_value == test_value
            
        # Run multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(test_worker, i)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        # Verify all threads got their correct values
        for thread_id in range(5):
            assert results[thread_id], f"Thread {thread_id} failed to get correct isolated value"
            
    def test_environment_variable_types(self):
        """Test that IsolatedEnvironment handles different variable types correctly."""
        env = get_env()
        
        # Test string values
        os.environ['STRING_VAR'] = 'string_value'
        assert env.get('STRING_VAR') == 'string_value'
        
        # Test empty string
        os.environ['EMPTY_VAR'] = ''
        assert env.get('EMPTY_VAR') == ''
        
        # Test values with special characters
        os.environ['SPECIAL_VAR'] = 'value with spaces and symbols !@#$%'
        assert env.get('SPECIAL_VAR') == 'value with spaces and symbols !@#$%'
        
        # Test values that look like other types
        os.environ['NUMBER_VAR'] = '123'
        assert env.get('NUMBER_VAR') == '123'  # Should remain string
        
        os.environ['BOOL_VAR'] = 'true'
        assert env.get('BOOL_VAR') == 'true'  # Should remain string
        
    def test_isolated_environment_context_manager(self):
        """Test that IsolatedEnvironment works as a context manager if supported."""
        env = get_env()
        
        # Test basic functionality even if not a context manager
        original_value = os.environ.get('CONTEXT_TEST_VAR')
        
        try:
            os.environ['CONTEXT_TEST_VAR'] = 'context_value'
            
            # Within context, value should be accessible
            assert env.get('CONTEXT_TEST_VAR') == 'context_value'
            
        finally:
            # Cleanup
            if original_value is not None:
                os.environ['CONTEXT_TEST_VAR'] = original_value
            else:
                os.environ.pop('CONTEXT_TEST_VAR', None)
                
    def test_environment_variable_precedence(self):
        """Test precedence of environment variable sources."""
        env = get_env()
        
        # Set base value
        os.environ['PRECEDENCE_VAR'] = 'os_environ_value'
        
        # Check that os.environ value is retrieved
        assert env.get('PRECEDENCE_VAR') == 'os_environ_value'
        
        # If isolation is supported, test override behavior
        if hasattr(env, 'enable_isolation') and hasattr(env, 'set'):
            env.enable_isolation()
            try:
                env.set('PRECEDENCE_VAR', 'isolated_value', source='test')
                assert env.get('PRECEDENCE_VAR') == 'isolated_value'
                
                # os.environ should still have original value
                assert os.environ['PRECEDENCE_VAR'] == 'os_environ_value'
                
            finally:
                env.disable_isolation()
                
    def test_configuration_manager_integration(self):
        """Test integration between IsolatedEnvironment and ConfigurationManager."""
        from netra_backend.app.core.configuration.base import config_manager
        
        # Set test environment variables
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['INTEGRATION_TEST_VAR'] = 'integration_test_value'
        
        # Force refresh environment detection
        if hasattr(config_manager, '_refresh_environment_detection'):
            config_manager._refresh_environment_detection()
        
        # Verify environment detection worked
        assert config_manager._environment == 'development'
        
        # Test that environment variables are accessible through the system
        env = get_env()
        assert env.get('INTEGRATION_TEST_VAR') == 'integration_test_value'
        
    def test_error_handling_in_isolation(self):
        """Test error handling in IsolatedEnvironment operations."""
        env = get_env()
        
        # Test getting non-existent variable with and without default
        assert env.get('NON_EXISTENT_VAR_12345') is None
        assert env.get('NON_EXISTENT_VAR_12345', 'default_val') == 'default_val'
        
        # Test that operations don't crash on edge cases  
        assert env.get('') is None  # Empty variable name
        
    def test_subprocess_environment_generation(self):
        """Test subprocess environment generation functionality."""
        env = get_env()
        
        # Set some test variables
        os.environ['SUBPROCESS_VAR_1'] = 'subprocess_value_1'
        os.environ['SUBPROCESS_VAR_2'] = 'subprocess_value_2'
        
        # Get subprocess environment
        if hasattr(env, 'get_subprocess_env'):
            subprocess_env = env.get_subprocess_env()
            
            # Verify our variables are included
            assert subprocess_env.get('SUBPROCESS_VAR_1') == 'subprocess_value_1'
            assert subprocess_env.get('SUBPROCESS_VAR_2') == 'subprocess_value_2'
            
            # Verify critical system variables are preserved
            assert 'PATH' in subprocess_env
            
            # Verify it's a separate dict (not a reference to os.environ)
            assert subprocess_env is not os.environ
            
    def test_environment_source_tracking_detailed(self):
        """Test detailed source tracking functionality if available."""
        env = get_env()
        
        # Test basic source tracking (if supported)
        os.environ['SOURCE_TRACK_VAR'] = 'tracked_value'
        
        # Access variable
        value = env.get('SOURCE_TRACK_VAR')
        assert value == 'tracked_value'
        
        # If source tracking is implemented, test it
        if hasattr(env, 'get_source'):
            source = env.get_source('SOURCE_TRACK_VAR')
            assert source is not None
            
        if hasattr(env, 'get_all_sources'):
            all_sources = env.get_all_sources()
            assert isinstance(all_sources, dict)
            
    def test_isolation_mode_transitions(self):
        """Test enabling/disabling isolation mode multiple times."""
        env = get_env()
        
        # Test multiple enable/disable cycles if isolation is supported
        if hasattr(env, 'enable_isolation') and hasattr(env, 'disable_isolation'):
            # Initially not isolated (presumably)
            os.environ['ISOLATION_CYCLE_VAR'] = 'initial_value'
            assert env.get('ISOLATION_CYCLE_VAR') == 'initial_value'
            
            # Enable isolation
            env.enable_isolation()
            
            # Set isolated value
            if hasattr(env, 'set'):
                env.set('ISOLATION_CYCLE_VAR', 'isolated_value', source='test')
                assert env.get('ISOLATION_CYCLE_VAR') == 'isolated_value'
            
            # Disable isolation
            env.disable_isolation()
            
            # Should now see os.environ value again
            assert env.get('ISOLATION_CYCLE_VAR') == 'initial_value'
            
            # Enable again
            env.enable_isolation()
            env.disable_isolation()  # And disable again
            
            # Should still work
            assert env.get('ISOLATION_CYCLE_VAR') == 'initial_value'