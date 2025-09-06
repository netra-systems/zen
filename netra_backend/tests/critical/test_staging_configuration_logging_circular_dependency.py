from shared.isolated_environment import get_env
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment
"""
Critical test suite for staging configuration and logging circular dependency.

This test reproduces the circular dependency error seen in staging:
- Loguru handler emission error at `/usr/local/lib/python3.11/site-packages/loguru/_handler.py:133`
- Configuration loading error at `/app/netra_backend/app/core/configuration/base.py:182`

The issue is that UnifiedConfigManager imports central_logger, but UnifiedLogger
tries to load config during initialization, creating a circular dependency.
"""

import pytest
import sys
import threading
from typing import Dict, Any


class TestConfigurationLoggingCircularDependency:
    """Test suite for configuration and logging circular dependency issues."""
    
    def test_config_imports_logger_but_logger_loads_config_fails(self):
        """
        FAILING TEST: Reproduces circular dependency between config and logger.
        
        This test demonstrates the exact circular dependency issue seen in staging:
        1. UnifiedConfigManager imports central_logger during module load
        2. When logger is accessed, it tries to load config via _load_config()
        3. This creates infinite recursion or import failures
        """
        # Clear any cached imports to simulate fresh startup
        modules_to_clear = [
            m for m in sys.modules.keys() 
            if m.startswith('netra_backend.app.core.configuration') or 
               m.startswith('netra_backend.app.logging_config') or
               m.startswith('netra_backend.app.core.unified_logging')
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # This should fail with circular import or recursion error
        with pytest.raises((ImportError, RecursionError, AttributeError)) as exc_info:
            # Try to import config manager - this imports logger
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            
            # Create instance - this should trigger the circular dependency
            manager = UnifiedConfigManager()
            
            # Try to get config - this should trigger logger initialization
            # which tries to load config again
            config = manager.get_config()
            
        # We expect this to fail with circular dependency error
        assert "circular" in str(exc_info.value).lower() or "recursion" in str(exc_info.value).lower()
    
    def test_logger_initialization_during_config_load_fails(self):
        """
        FAILING TEST: Reproduces logger initialization failure during config load.
        
        This simulates the exact scenario where configuration loading is triggered
        but logger initialization fails because config isn't available yet.
        """
        # Mock the scenario where config is being loaded but logger needs config
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.unified_logging.UnifiedLogger._load_config') as mock_load_config:
            # Make _load_config try to import configuration which isn't ready
            mock_load_config.side_effect = ImportError("Configuration not ready during logger init")
            
            from netra_backend.app.core.unified_logging import UnifiedLogger
            
            logger = UnifiedLogger()
            
            # This should fail because config loading fails during logger setup
            with pytest.raises((ImportError, ConfigurationError)) as exc_info:
                logger._setup_logging()
            
            assert "Configuration not ready" in str(exc_info.value)
    
    def test_recursive_config_loading_with_logging_fails(self):
        """
        FAILING TEST: Reproduces recursive config loading when logger emits logs.
        
        This test simulates the scenario where:
        1. Config starts loading
        2. Logger tries to emit a log during config load
        3. Logger tries to load config for its configuration
        4. Creates recursive loop
        """
        # Track recursive calls
        call_count = {'config_load': 0, 'logger_setup': 0}
        
        def mock_config_load():
            call_count['config_load'] += 1
            if call_count['config_load'] > 1:
                # Second call means recursion detected
                raise RecursionError("Configuration loading called recursively")
            # Simulate logger being called during config load
            from netra_backend.app.core.unified_logging import central_logger
            central_logger.info("Loading configuration...")  # This triggers recursion
            # Mock: Generic component isolation for controlled unit testing
            return None  # TODO: Use real service instance
        
        def mock_logger_setup(self):
            call_count['logger_setup'] += 1
            if call_count['logger_setup'] > 1:
                raise RecursionError("Logger setup called recursively")
            # Try to load config during logger setup
            self._load_config()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.core.configuration.base.UnifiedConfigManager._load_complete_configuration', side_effect=mock_config_load):
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.core.unified_logging.UnifiedLogger._setup_logging', side_effect=mock_logger_setup):
                from netra_backend.app.core.configuration.base import UnifiedConfigManager
                
                manager = UnifiedConfigManager()
                
                # This should fail with recursion error
                with pytest.raises(RecursionError) as exc_info:
                    config = manager.get_config()
                
                assert "recursively" in str(exc_info.value)
    
    def test_loguru_handler_emission_error_during_config_fails(self):
        """
        FAILING TEST: Reproduces Loguru handler emission error during config initialization.
        
        This simulates the exact error from staging:
        `/usr/local/lib/python3.11/site-packages/loguru/_handler.py:133`
        """
        # Mock loguru handler to simulate emission failure during config load
        # Mock: Component isolation for testing without external dependencies
        with patch('loguru.logger') as mock_loguru:
            # Setup mock to fail when trying to emit log during config initialization
            mock_loguru.info.side_effect = RuntimeError("Handler emission failed during config initialization")
            mock_loguru.error.side_effect = RuntimeError("Handler emission failed during config initialization")
            
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            
            manager = UnifiedConfigManager()
            
            # This should fail when config tries to log during initialization
            with pytest.raises(RuntimeError) as exc_info:
                # Force logger to be used during config loading
                with patch.object(manager, '_logger') as mock_logger:
                    mock_logger.info.side_effect = mock_loguru.info.side_effect
                    config = manager.get_config()
            
            assert "Handler emission failed" in str(exc_info.value)


class TestConfigurationBootstrapWithoutLogger:
    """Test configuration bootstrap scenarios without working logger."""
    
    def test_config_initialization_without_logger_available_fails(self):
        """
        FAILING TEST: Config initialization fails when logger module is not available.
        
        This simulates staging scenario where logger import fails during config init.
        """
        # Mock the import to fail for logging modules
        original_import = __builtins__['__import__']
        
        def mock_import(name, *args, **kwargs):
            if 'logging_config' in name or 'unified_logging' in name:
                raise ImportError(f"No module named '{name}' - logging not available")
            return original_import(name, *args, **kwargs)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('builtins.__import__', side_effect=mock_import):
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            
            # This should fail because logger import fails
            with pytest.raises(ImportError) as exc_info:
                manager = UnifiedConfigManager()
                manager._initialize_core_components()
            
            assert "logging not available" in str(exc_info.value)
    
    def test_config_error_handling_without_logger_fails(self):
        """
        FAILING TEST: Configuration error handling fails when logger is not working.
        
        This tests the scenario where configuration validation fails but
        error logging also fails, creating a cascading failure.
        """
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        
        manager = UnifiedConfigManager()
        
        # Mock logger to fail when trying to log errors
        with patch.object(manager, '_logger') as mock_logger:
            mock_logger.error.side_effect = RuntimeError("Logger not available for error reporting")
            
            # Mock config loading to fail
            with patch.object(manager, '_create_base_config', side_effect=ValueError("Config creation failed")):
                # This should fail because both config creation and error logging fail
                with pytest.raises(RuntimeError) as exc_info:
                    config = manager.get_config()
                
                # Should fail on the logging error, not the original config error
                assert "Logger not available" in str(exc_info.value)
    
    def test_fallback_config_loading_with_broken_logger_fails(self):
        """
        FAILING TEST: Fallback configuration loading fails when logger is broken.
        
        This tests the scenario where logger falls back to environment variables
        but the fallback mechanism itself fails.
        """
        from netra_backend.app.core.unified_logging import UnifiedLogger
        
        logger = UnifiedLogger()
        
        # Mock the fallback config loading to fail
        with patch.object(logger, '_get_fallback_log_level', side_effect=Exception("Fallback config unavailable")):
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.core.unified_logging.os.environ.get', return_value=None):
                # This should fail when trying to get fallback configuration
                with pytest.raises(Exception) as exc_info:
                    config = logger._load_config()
                
                assert "Fallback config unavailable" in str(exc_info.value)


class TestStagingSpecificCircularDependencyScenarios:
    """Test staging-specific circular dependency scenarios."""
    
    def test_singleton_initialization_race_condition_fails(self):
        """
        FAILING TEST: Singleton initialization with threading creates race condition.
        
        This reproduces the scenario where multiple threads try to initialize
        the singleton configuration manager simultaneously, creating circular dependencies.
        """
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        
        # Reset singleton state
        UnifiedConfigManager._instance = None
        
        exceptions = []
        
        def create_manager():
            try:
                manager = UnifiedConfigManager()
                config = manager.get_config()
            except Exception as e:
                exceptions.append(e)
        
        # Create multiple threads that try to initialize simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_manager)
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # At least one thread should fail due to race condition
        assert len(exceptions) > 0, "Expected at least one thread to fail due to race condition"
        
        # Check that we got circular dependency or threading-related errors
        error_messages = [str(e) for e in exceptions]
        has_expected_error = any(
            "circular" in msg.lower() or 
            "recursion" in msg.lower() or 
            "lock" in msg.lower() or
            "thread" in msg.lower()
            for msg in error_messages
        )
        
        assert has_expected_error, f"Expected circular dependency or threading error, got: {error_messages}"
    
    def test_config_loading_flag_not_preventing_recursion_fails(self):
        """
        FAILING TEST: Configuration loading flag doesn't prevent recursion properly.
        
        The current code has a _loading flag but it may not prevent all recursive scenarios.
        """
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        
        manager = UnifiedConfigManager()
        manager._loading = True  # Set flag as if loading is in progress
        
        # Even with loading flag set, recursive call should fail
        with pytest.raises((RecursionError, RuntimeError)) as exc_info:
            # This should detect that loading is already in progress and fail
            config = manager._load_complete_configuration()
        
        assert "already loading" in str(exc_info.value) or "recursion" in str(exc_info.value).lower()
    
    def test_logger_config_cache_invalidation_during_init_fails(self):
        """
        FAILING TEST: Logger config cache gets invalidated during initialization.
        
        This tests the scenario where logger's config cache is cleared
        while configuration is still being loaded.
        """
        from netra_backend.app.core.unified_logging import UnifiedLogger
        
        logger = UnifiedLogger()
        
        # Set cache as if config was loaded
        logger._config_loaded = True
        logger._config = {'log_level': 'INFO'}
        
        def mock_load_config():
            # Simulate config being cleared during load
            logger._config = None
            logger._config_loaded = False
            raise RuntimeError("Config cache invalidated during initialization")
        
        with patch.object(logger, '_load_config', side_effect=mock_load_config):
            # This should fail when cache is invalidated during setup
            with pytest.raises(RuntimeError) as exc_info:
                logger._setup_logging()
            
            assert "Config cache invalidated" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
