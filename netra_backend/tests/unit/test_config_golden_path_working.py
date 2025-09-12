"""
Working Unit Tests for Configuration Golden Path SSOT Classes

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (CRITICAL INFRASTRUCTURE)
- Business Goal: Zero configuration-related system failures and 100% deployment reliability
- Value Impact: Prevents configuration cascade failures that can cause $500K+ revenue loss
- Strategic Impact: Ensures stable golden path user flow from login  ->  AI responses
- Revenue Impact: Eliminates downtime from configuration mismatches across environments

MISSION CRITICAL: These tests validate the configuration SSOT classes that enable:
1. Unified configuration access across all environments (TEST/DEV/STAGING/PROD)
2. Environment-specific configuration loading and validation 
3. Service startup reliability through proper configuration validation
4. Golden path user flow stability (users login  ->  get AI responses)
"""

import pytest
import time
from contextlib import contextmanager

# SSOT imports following absolute import rules
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.config import get_config, reload_config, validate_configuration
from netra_backend.app.schemas.config import AppConfig


class TestConfigurationGoldenPathWorking(SSotBaseTestCase):
    """
    Working test suite for Configuration Golden Path SSOT classes.
    
    Tests the critical configuration components that enable reliable
    configuration across all environments for golden path user flow stability.
    """
    
    def setup_method(self, method):
        """Set up test environment with proper isolation."""
        super().setup_method(method)
        
        # Set test environment
        self.set_env_var('ENVIRONMENT', 'testing')
        self.set_env_var('TESTING', 'true')
    
    # === UNIFIED CONFIGURATION INTERFACE TESTS ===
    
    def test_get_config_returns_valid_app_config(self):
        """
        Test get_config() returns valid AppConfig for golden path user flow.
        
        BVJ: This is the primary configuration access point used throughout
        the system. Failure here breaks the entire golden path user flow.
        """
        # Execute configuration loading
        config = get_config()
        
        # Validate return type and core structure
        assert isinstance(config, AppConfig), "get_config() must return AppConfig instance"
        assert hasattr(config, 'environment'), "Config missing environment attribute"
        assert hasattr(config, 'app_name'), "Config missing app_name attribute"
        assert hasattr(config, 'secret_key'), "Config missing secret_key attribute"
        
        # Validate critical business values
        assert config.app_name == "netra", "App name must be 'netra' for proper service identification"
        assert config.secret_key is not None, "Secret key is required for authentication"
        assert len(config.secret_key) >= 16, "Secret key must be at least 16 characters for security"
        
        print(f"[U+2713] Configuration loaded successfully for environment: {config.environment}")
    
    def test_get_config_caching_behavior(self):
        """
        Test get_config() caching behavior for performance.
        
        BVJ: Caching is critical for runtime performance to prevent
        configuration loading delays during user interactions.
        """
        # First call to populate cache
        config1 = get_config()
        
        # Second call should return cached instance
        config2 = get_config()
        
        # Validate caching works
        assert config1 is config2, "get_config() should return cached instance for performance"
        
        # Measure cache performance
        start_time = time.time()
        for _ in range(100):
            cached_config = get_config()
            assert cached_config is config1, "Cache should remain consistent"
        cache_time = time.time() - start_time
        
        # Cache performance requirement
        assert cache_time < 0.1, "100 cached calls should complete in under 100ms"
        print(f"[U+2713] Configuration caching validated - 100 calls in {cache_time:.3f}s")
    
    def test_reload_config_force_reload(self):
        """
        Test reload_config() with force flag for configuration updates.
        
        BVJ: Force reload capability is critical for deployment scenarios
        where configuration must be updated without service restart.
        """
        # Get initial configuration
        initial_config = get_config()
        initial_id = id(initial_config)
        
        # Force reload configuration
        reload_config(force=True)
        
        # Get new configuration
        new_config = get_config()
        new_id = id(new_config)
        
        # Validate reload behavior
        assert initial_id != new_id, "Force reload should create new config instance"
        assert isinstance(new_config, AppConfig), "Reloaded config should be valid AppConfig"
        assert new_config.app_name == "netra", "Reloaded config should maintain app_name"
        
        print("[U+2713] Force reload configuration validated")
    
    def test_validate_configuration_success_scenarios(self):
        """
        Test validate_configuration() returns success for valid configurations.
        
        BVJ: Configuration validation prevents deployment of invalid
        configurations that could break the golden path user flow.
        """
        # Execute configuration validation
        is_valid, errors = validate_configuration()
        
        # Validate response format
        assert isinstance(is_valid, bool), "Validation should return boolean result"
        assert isinstance(errors, list), "Validation should return list of errors"
        
        # In test environment with proper setup, validation should succeed
        if not is_valid:
            # If validation fails, provide detailed error information
            error_details = "\n".join(str(error) for error in errors)
            pytest.fail(f"Configuration validation failed with errors:\n{error_details}")
        
        print("[U+2713] Configuration validation passed successfully")
    
    # === PERFORMANCE TESTS ===
    
    def test_configuration_loading_performance(self):
        """
        Test configuration loading meets performance requirements.
        
        BVJ: Configuration loading performance is critical for system
        startup time and request latency in production environments.
        """
        # Test initial configuration loading performance
        start_time = time.time()
        config = get_config()
        load_time = time.time() - start_time
        
        # Performance requirement for initial load
        assert load_time < 1.0, "Configuration loading should complete in under 1 second"
        
        # Test cached configuration access performance
        cache_start = time.time()
        for _ in range(100):
            cached_config = get_config()
            assert cached_config is config, "Should return cached instance"
        cache_time = time.time() - cache_start
        
        # Performance requirement for cached access
        assert cache_time < 0.1, "100 cached configuration accesses should complete in under 100ms"
        
        print(f"[U+2713] Configuration performance validated - load: {load_time:.3f}s, cache: {cache_time:.3f}s")
    
    def test_validation_performance(self):
        """
        Test configuration validation meets performance requirements.
        
        BVJ: Validation performance is critical for deployment speed
        and system startup time in production environments.
        """
        # Test validation performance
        start_time = time.time()
        is_valid, errors = validate_configuration()
        validation_time = time.time() - start_time
        
        # Performance requirement for validation
        assert validation_time < 0.5, "Configuration validation should complete in under 500ms"
        
        print(f"[U+2713] Configuration validation performance validated - {validation_time:.3f}s")
    
    # === INTEGRATION TESTS ===
    
    def test_configuration_environment_integration(self):
        """
        Test configuration properly integrates with IsolatedEnvironment.
        
        BVJ: Environment integration is critical for environment variable
        access patterns that support golden path user flow across environments.
        """
        # Test environment variable integration
        with self.temp_env_vars(TEST_CONFIG_VALUE="test_value", CUSTOM_ENV_VAR="custom_value"):
            config = get_config()
            
            # Verify configuration is accessible
            assert isinstance(config, AppConfig), "Config should be accessible with env vars"
            
            # Test environment variable access through isolated environment
            test_value = self.get_env_var("TEST_CONFIG_VALUE")
            assert test_value == "test_value", "Environment variables should be accessible"
            
            custom_value = self.get_env_var("CUSTOM_ENV_VAR")
            assert custom_value == "custom_value", "Custom environment variables should be accessible"
        
        print("[U+2713] Configuration environment integration validated")
    
    # === BUSINESS VALUE VALIDATION ===
    
    def test_golden_path_configuration_requirements(self):
        """
        Test configuration meets golden path user flow requirements.
        
        BVJ: Golden path requirements ensure users can successfully
        login  ->  get AI responses without configuration-related failures.
        """
        config = get_config()
        
        # Golden path requirement: App identification
        assert config.app_name == "netra", "App name required for service identification"
        
        # Golden path requirement: Security configuration
        assert config.secret_key is not None, "Secret key required for authentication"
        assert len(config.secret_key) >= 16, "Secret key must meet minimum length requirement"
        
        # Golden path requirement: Database connectivity (if configured)
        if hasattr(config, 'database_url') and config.database_url:
            assert isinstance(config.database_url, str), "Database URL must be string"
            assert len(config.database_url) > 0, "Database URL must not be empty"
        
        # Golden path requirement: JWT configuration (if configured)
        if hasattr(config, 'jwt_secret_key') and config.jwt_secret_key:
            assert isinstance(config.jwt_secret_key, str), "JWT secret must be string"
            assert len(config.jwt_secret_key) >= 16, "JWT secret must meet minimum length"
        
        # Golden path requirement: Logging configuration
        if hasattr(config, 'log_level') and config.log_level:
            assert config.log_level is not None, "Log level required for system monitoring"
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            assert config.log_level in valid_log_levels, f"Log level must be valid: {valid_log_levels}"
        
        print("[U+2713] Golden path configuration requirements validated")
    
    def test_business_value_metrics_comprehensive(self):
        """
        Test and record comprehensive business value metrics.
        
        BVJ: Business value metrics demonstrate the configuration system's
        contribution to system reliability and golden path user flow stability.
        """
        metrics = {}
        
        # Metric 1: Configuration loading reliability
        load_attempts = 10
        successful_loads = 0
        total_load_time = 0
        
        for _ in range(load_attempts):
            try:
                start_time = time.time()
                config = get_config()
                load_time = time.time() - start_time
                total_load_time += load_time
                
                if isinstance(config, AppConfig) and config.app_name == "netra":
                    successful_loads += 1
            except Exception:
                pass
        
        load_reliability = successful_loads / load_attempts
        avg_load_time = total_load_time / successful_loads if successful_loads > 0 else 0
        
        # Metric 2: Validation reliability
        validation_attempts = 5
        successful_validations = 0
        total_validation_time = 0
        
        for _ in range(validation_attempts):
            try:
                start_time = time.time()
                is_valid, errors = validate_configuration()
                validation_time = time.time() - start_time
                total_validation_time += validation_time
                
                if isinstance(is_valid, bool) and isinstance(errors, list):
                    successful_validations += 1
            except Exception:
                pass
        
        validation_reliability = successful_validations / validation_attempts
        avg_validation_time = total_validation_time / successful_validations if successful_validations > 0 else 0
        
        # Metric 3: Cache effectiveness
        cache_hits = 0
        cache_attempts = 100
        initial_config = get_config()
        
        for _ in range(cache_attempts):
            cached_config = get_config()
            if cached_config is initial_config:
                cache_hits += 1
        
        cache_hit_rate = cache_hits / cache_attempts
        
        # Business value assertions
        assert load_reliability >= 0.95, "Configuration loading should be 95%+ reliable"
        assert validation_reliability >= 0.95, "Configuration validation should be 95%+ reliable"  
        assert cache_hit_rate >= 0.90, "Configuration cache should be 90%+ effective"
        assert avg_load_time < 0.5, "Average load time should be under 500ms"
        assert avg_validation_time < 0.2, "Average validation time should be under 200ms"
        
        # Record metrics for business value reporting
        metrics = {
            'configuration_load_reliability': f"{load_reliability:.1%}",
            'configuration_validation_reliability': f"{validation_reliability:.1%}",
            'configuration_cache_hit_rate': f"{cache_hit_rate:.1%}",
            'avg_configuration_load_time': f"{avg_load_time:.3f}s",
            'avg_validation_time': f"{avg_validation_time:.3f}s"
        }
        
        print(f"[U+2713] Business value metrics validated: {metrics}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])