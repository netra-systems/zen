"""Simple test for environment isolation functionality.

This test focuses on verifying that the IsolatedEnvironment and
configuration management works correctly for environment variable loading.
"""

import os
import pytest

from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestEnvironmentIsolation:
    """Test environment isolation functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Store original environment
        self.original_env = get_env().get_all()
        
        # Clear test-specific variables that might interfere
        test_vars = ['TEST_VAR_1', 'TEST_VAR_2', 'NETRA_TEST_VAR', 'TESTING']
        for var in test_vars:
            os.environ.pop(var, None)
            
        yield
        
        # Restore original environment - only clear if in isolation mode
        env = get_env()
        if env.is_isolation_enabled():
            env.clear()
        
        # Restore original environment variables
        env.update(self.original_env, "test")

    def test_isolated_environment_basic_access(self):
        """Test basic environment variable access through IsolatedEnvironment."""
        # Set test environment variable
        get_env().set('TEST_VAR_1', 'test_value_1', "test")
        
        # Get environment through isolated access
        env = get_env()
        
        # Verify access works
        assert get_env().get('TEST_VAR_1') == 'test_value_1'
        assert get_env().get('NON_EXISTENT_VAR') is None
        assert get_env().get('NON_EXISTENT_VAR', 'default') == 'default'

    def test_isolated_environment_overrides(self):
        """Test that environment variables can be overridden."""
        # Set initial value
        get_env().set('TEST_VAR_2', 'initial_value', "test")
        
        # Verify initial value
        env = get_env()
        assert get_env().get('TEST_VAR_2') == 'initial_value'
        
        # Override value
        get_env().set('TEST_VAR_2', 'overridden_value', "test")
        
        # Verify override works (may need fresh env instance)
        env_fresh = get_env()
        assert env_fresh.get('TEST_VAR_2') == 'overridden_value'

    def test_environment_source_tracking(self):
        """Test that IsolatedEnvironment can track variable sources."""
        # Set a variable
        get_env().set('NETRA_TEST_VAR', 'tracked_value', "test")
        
        # Get environment
        env = get_env()
        
        # Access the variable
        value = get_env().get('NETRA_TEST_VAR')
        assert value == 'tracked_value'
        
        # Basic functionality test - we're not testing full source tracking here
        # just that the basic environment access works
        
    def test_configuration_environment_detection(self):
        """Test that configuration properly detects environment from IsolatedEnvironment."""
        # Import and test configuration manager
        from netra_backend.app.core.configuration.base import config_manager
        
        # Force refresh to pick up current environment setting
        config_manager._environment = config_manager._get_environment()
        
        # In pytest context, should detect testing environment
        assert config_manager._environment == 'testing'
        
        # Test that config manager can access environment variables through IsolatedEnvironment
        env = get_env()
        env.set('TEST_CONFIG_VAR', 'test_value_config', "test")
        
        # Verify that the environment variable is accessible
        assert env.get('TEST_CONFIG_VAR') == 'test_value_config'
        
        # Test the core functionality: that the configuration system uses IsolatedEnvironment
        # by verifying it can detect environment changes when we modify isolated variables
        original_env = env.get('ENVIRONMENT')
        
        # Set a different environment temporarily
        env.set('ENVIRONMENT', 'custom_test_env', "test")
        
        # The get() method should return our custom value
        assert env.get('ENVIRONMENT') == 'custom_test_env'
        
        # Restore original environment
        if original_env:
            env.set('ENVIRONMENT', original_env, "test")
        else:
            env.delete('ENVIRONMENT', "test")

    def test_environment_variable_isolation_in_config(self):
        """Test that environment variables are properly isolated and accessible through IsolatedEnvironment."""
        # Use IsolatedEnvironment to properly isolate test settings
        from shared.isolated_environment import get_env
        
        # Store original values to restore later
        original_env_val = get_env().get('ENVIRONMENT')
        original_database_url = get_env().get('DATABASE_URL')
        original_redis_url = get_env().get('REDIS_URL')
        
        env = get_env()
        
        # Enable isolation mode to prevent conflicts with global test setup
        get_env().enable_isolation()
        
        try:
            # Set test configuration values through IsolatedEnvironment
            get_env().set('ENVIRONMENT', 'development', source='test')
            get_env().set('DATABASE_URL', 'postgresql://test@localhost/test_db', source='test')
            get_env().set('REDIS_URL', 'redis://test:6379/1', source='test')
            
            # Also clear conflicting environment variables that might interfere
            get_env().set('NETRA_ENV', '', source='test_clear')  # Clear the e2e test override
            
            # Verify the isolated environment has our values
            assert get_env().get('ENVIRONMENT') == 'development'
            assert get_env().get('DATABASE_URL') == 'postgresql://test@localhost/test_db'
            assert get_env().get('REDIS_URL') == 'redis://test:6379/1'
            assert get_env().get('NETRA_ENV') == ''  # Cleared value
            
            # When in isolation mode, isolated variables take precedence
            # So we should see our isolated values, not the original os.environ values
            assert get_env().get('ENVIRONMENT') == 'development'  # Isolated value
            assert get_env().get('DATABASE_URL') == 'postgresql://test@localhost/test_db'  # Isolated value
            assert get_env().get('REDIS_URL') == 'redis://test:6379/1'  # Isolated value
                
            # Test that the basic config manager can access IsolatedEnvironment variables
            from netra_backend.app.core.configuration.base import config_manager
            
            # Test that our isolated environment variables are accessible
            assert get_env().get('ENVIRONMENT') == 'development'
            assert get_env().get('DATABASE_URL') == 'postgresql://test@localhost/test_db'
            
            # In pytest context, the config manager will detect testing environment
            # but our isolated variables should still be accessible through get_env()
            config_manager._environment = None
            detected_env = config_manager._get_environment()
            
            # Config manager should detect testing (because of pytest context)
            # but IsolatedEnvironment should still have our isolated values
            assert detected_env == 'testing'  # pytest context takes priority
            
            # But our isolated variables should still be accessible
            assert get_env().get('ENVIRONMENT') == 'development'  # Isolated value
            
            # Test subprocess environment generation includes our values
            subprocess_env = get_env().get_subprocess_env()
            assert subprocess_env.get('ENVIRONMENT') == 'development'
            assert subprocess_env.get('DATABASE_URL') == 'postgresql://test@localhost/test_db'
            assert subprocess_env.get('REDIS_URL') == 'redis://test:6379/1'
            
            # Verify critical system variables are still present in subprocess env
            assert 'PATH' in subprocess_env
            
        finally:
            # Clean up isolation mode
            get_env().disable_isolation()
            
            # Restore original values if they existed
            if original_env_val is not None:
                get_env().set('ENVIRONMENT', original_env_val, "test")
            else:
                get_env().delete('ENVIRONMENT', "test")
                
            if original_database_url is not None:
                get_env().set('DATABASE_URL', original_database_url, "test")
            else:
                get_env().delete('DATABASE_URL', "test")
                
            if original_redis_url is not None:
                get_env().set('REDIS_URL', original_redis_url, "test")  
            else:
                get_env().delete('REDIS_URL', "test")
                
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
            retrieved_value = get_env().get(test_var)
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
        get_env().set('STRING_VAR', 'string_value', "test")
        assert get_env().get('STRING_VAR') == 'string_value'
        
        # Test empty string
        get_env().set('EMPTY_VAR', '', "test")
        assert get_env().get('EMPTY_VAR') == ''
        
        # Test values with special characters
        get_env().set('SPECIAL_VAR', 'value with spaces and symbols !@#$%', "test")
        assert get_env().get('SPECIAL_VAR') == 'value with spaces and symbols !@#$%'
        
        # Test values that look like other types
        get_env().set('NUMBER_VAR', '123', "test")
        assert get_env().get('NUMBER_VAR') == '123'  # Should remain string
        
        get_env().set('BOOL_VAR', 'true', "test")
        assert get_env().get('BOOL_VAR') == 'true'  # Should remain string
        
    def test_isolated_environment_context_manager(self):
        """Test that IsolatedEnvironment works as a context manager if supported."""
        env = get_env()
        
        # Test basic functionality even if not a context manager
        original_value = get_env().get('CONTEXT_TEST_VAR')
        
        try:
            get_env().set('CONTEXT_TEST_VAR', 'context_value', "test")
            
            # Within context, value should be accessible
            assert get_env().get('CONTEXT_TEST_VAR') == 'context_value'
            
        finally:
            # Cleanup
            if original_value is not None:
                get_env().set('CONTEXT_TEST_VAR', original_value, "test")
            else:
                get_env().delete('CONTEXT_TEST_VAR', "test")
                
    def test_environment_variable_precedence(self):
        """Test precedence of environment variable sources."""
        env = get_env()
        
        # Set base value
        get_env().set('PRECEDENCE_VAR', 'os_environ_value', "test")
        
        # Check that os.environ value is retrieved
        assert get_env().get('PRECEDENCE_VAR') == 'os_environ_value'
        
        # If isolation is supported, test override behavior
        if hasattr(env, 'enable_isolation') and hasattr(env, 'set'):
            get_env().enable_isolation()
            try:
                get_env().set('PRECEDENCE_VAR', 'isolated_value', source='test')
                assert get_env().get('PRECEDENCE_VAR') == 'isolated_value'
                
                # os.environ should still have original value
                assert os.environ['PRECEDENCE_VAR'] == 'os_environ_value'
                
            finally:
                get_env().disable_isolation()
                
    def test_configuration_manager_integration(self):
        """Test integration between IsolatedEnvironment and ConfigurationManager."""
        from netra_backend.app.core.configuration.base import config_manager
        
        # Set test environment variables
        get_env().set('INTEGRATION_TEST_VAR', 'integration_test_value', "test")
        
        # Force refresh environment detection by clearing cache
        config_manager._environment = None
        detected_env = config_manager._get_environment()
        
        # In pytest context, should detect testing environment
        assert detected_env == 'testing'
        
        # Test that environment variables are accessible through the system
        env = get_env()
        assert get_env().get('INTEGRATION_TEST_VAR') == 'integration_test_value'
        
    def test_error_handling_in_isolation(self):
        """Test error handling in IsolatedEnvironment operations."""
        env = get_env()
        
        # Test getting non-existent variable with and without default
        assert get_env().get('NON_EXISTENT_VAR_12345') is None
        assert get_env().get('NON_EXISTENT_VAR_12345', 'default_val') == 'default_val'
        
        # Test that operations don't crash on edge cases  
        assert get_env().get('') is None  # Empty variable name
        
    def test_subprocess_environment_generation(self):
        """Test subprocess environment generation functionality."""
        env = get_env()
        
        # Set some test variables
        get_env().set('SUBPROCESS_VAR_1', 'subprocess_value_1', "test")
        get_env().set('SUBPROCESS_VAR_2', 'subprocess_value_2', "test")
        
        # Get subprocess environment
        if hasattr(env, 'get_subprocess_env'):
            subprocess_env = get_env().get_subprocess_env()
            
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
        get_env().set('SOURCE_TRACK_VAR', 'tracked_value', "test")
        
        # Access variable
        value = get_env().get('SOURCE_TRACK_VAR')
        assert value == 'tracked_value'
        
        # If source tracking is implemented, test it
        if hasattr(env, 'get_source'):
            source = get_env().get_source('SOURCE_TRACK_VAR')
            assert source is not None
            
        if hasattr(env, 'get_all_sources'):
            all_sources = get_env().get_all_sources()
            assert isinstance(all_sources, dict)
            
    def test_isolation_mode_transitions(self):
        """Test enabling/disabling isolation mode multiple times."""
        env = get_env()
        
        # Test multiple enable/disable cycles if isolation is supported
        if hasattr(env, 'enable_isolation') and hasattr(env, 'disable_isolation'):
            # Initially not isolated (presumably)
            get_env().set('ISOLATION_CYCLE_VAR', 'initial_value', "test")
            assert get_env().get('ISOLATION_CYCLE_VAR') == 'initial_value'
            
            # Enable isolation
            get_env().enable_isolation()
            
            # Set isolated value
            if hasattr(env, 'set'):
                get_env().set('ISOLATION_CYCLE_VAR', 'isolated_value', source='test')
                assert get_env().get('ISOLATION_CYCLE_VAR') == 'isolated_value'
            
            # Disable isolation - by default this syncs isolated vars to os.environ
            get_env().disable_isolation()
            
            # Should now see the isolated value that was synced to os.environ
            assert get_env().get('ISOLATION_CYCLE_VAR') == 'isolated_value'
            
            # Test restore_original=True option
            get_env().set('ISOLATION_CYCLE_VAR_2', 'initial_value_2', "test")
            get_env().enable_isolation()
            get_env().set('ISOLATION_CYCLE_VAR_2', 'isolated_value_2', source='test')
            
            # Disable with restore_original=True
            get_env().disable_isolation(restore_original=True)
            
            # Should now see original os.environ value
            assert get_env().get('ISOLATION_CYCLE_VAR_2') == 'initial_value_2'
