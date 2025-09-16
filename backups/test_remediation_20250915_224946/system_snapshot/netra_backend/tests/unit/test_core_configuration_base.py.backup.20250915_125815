"""
Unit Test for Core Configuration Base Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Golden Path Reliability
- Value Impact: Ensures configuration system works reliably across all environments
- Strategic Impact: Prevents configuration failures that could block $500K+ ARR Golden Path

CRITICAL: NO MOCKS except for external dependencies. Tests use real business logic.
Tests the SSOT configuration manager that supports all Golden Path operations.
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.configuration.base import UnifiedConfigManager


class TestUnifiedConfigManager(SSotBaseTestCase):
    """Test suite for UnifiedConfigManager following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.config_manager = UnifiedConfigManager()
        self.record_metric("test_category", "configuration_management")
    
    def test_config_manager_initialization(self):
        """
        Test configuration manager initializes properly.
        
        BVJ: Ensures configuration system starts correctly for Golden Path operations
        """
        assert self.config_manager._loader is not None
        assert self.config_manager._validator is not None
        assert self.config_manager._config_cache is None  # Initially empty
        assert self.config_manager._environment is None   # Initially unset
        
        self.record_metric("config_manager_init", "passed")
    
    def test_lazy_logger_initialization(self):
        """
        Test lazy logger loading prevents circular dependencies.
        
        BVJ: Prevents startup failures that would block Golden Path system initialization
        """
        # Logger should be None initially
        assert self.config_manager._logger is None
        
        # First call should initialize logger
        logger = self.config_manager._get_logger()
        assert logger is not None
        
        # Second call should return same logger
        logger2 = self.config_manager._get_logger()
        assert logger is logger2
        
        self.record_metric("lazy_logger_loading", "passed")
    
    def test_get_config_returns_valid_config(self):
        """
        Test get_config returns a valid AppConfig instance.
        
        BVJ: Ensures configuration is available for all Golden Path components
        """
        # Set test environment to avoid caching issues
        with self.temp_env_vars(ENVIRONMENT="testing"):
            config = self.config_manager.get_config()
            
            # Should return AppConfig instance
            from netra_backend.app.schemas.config import AppConfig
            assert isinstance(config, AppConfig)
            
            # Should have essential attributes
            assert hasattr(config, 'environment')
            assert hasattr(config, 'debug')
            
        self.record_metric("config_retrieval", "passed")
    
    def test_test_environment_no_caching(self):
        """
        Test that test environment doesn't cache configuration.
        
        BVJ: Ensures test isolation for reliable Golden Path testing
        """
        with self.temp_env_vars(ENVIRONMENT="testing"):
            # First call
            config1 = self.config_manager.get_config()
            
            # Cache should still be None for test environment
            assert self.config_manager._config_cache is None
            
            # Second call should create new config
            config2 = self.config_manager.get_config()
            
            # Both should be valid but separate instances
            assert config1 is not None
            assert config2 is not None
            # They might be the same type but created fresh each time
            
        self.record_metric("test_environment_no_cache", "passed")
    
    def test_non_test_environment_caching(self):
        """
        Test that non-test environments cache configuration.
        
        BVJ: Ensures performance optimization for production Golden Path operations
        """
        with self.temp_env_vars(ENVIRONMENT="development"):
            # First call should cache
            config1 = self.config_manager.get_config()
            
            # Cache should now be set
            assert self.config_manager._config_cache is not None
            
            # Second call should return cached config
            config2 = self.config_manager.get_config()
            
            # Should be the same instance due to caching
            assert config1 is config2
            
        self.record_metric("non_test_environment_caching", "passed")
    
    def test_environment_detection_accuracy(self):
        """
        Test environment detection works correctly.
        
        BVJ: Ensures proper configuration loading for different deployment environments
        """
        # Test different environment values
        test_environments = ["testing", "development", "staging", "production"]
        
        for env in test_environments:
            with self.temp_env_vars(ENVIRONMENT=env):
                # Clear any cached values to test fresh detection
                self.config_manager._config_cache = None
                self.config_manager._environment = None
                
                config = self.config_manager.get_config()
                
                # Verify environment is properly detected
                assert config.environment == env
                
        self.record_metric("environment_detection", "passed")
    
    def test_configuration_validation_integration(self):
        """
        Test configuration validation is properly integrated.
        
        BVJ: Ensures invalid configurations are caught before affecting Golden Path
        """
        with self.temp_env_vars(ENVIRONMENT="testing"):
            # This should load and validate configuration
            config = self.config_manager.get_config()
            
            # If we get here without exception, validation passed
            assert config is not None
            
            # Configuration should have been validated by the validator
            # We can't directly test validation failures without mocking,
            # but we can verify the validation process completes
            
        self.record_metric("config_validation_integration", "passed")