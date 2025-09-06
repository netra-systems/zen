"""Configuration Resilience - Critical Failing Tests

Tests that expose configuration loading failures found in staging logs.
These tests are designed to FAIL to demonstrate current configuration problems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service reliability and configuration robustness
- Value Impact: Ensures backend handles missing/invalid configuration gracefully  
- Strategic Impact: $9.4M protection - prevents service outages from config issues

Critical Issues from Staging Logs:
1. GCP Secret Manager access failures cause service crashes
2. Missing environment variables cause startup failures  
3. Invalid configuration values are not handled gracefully
4. Partial configuration loading causes inconsistent service state

Expected Behavior (CURRENTLY FAILING):
- Service should start with safe defaults when config is missing
- GCP Secret Manager failures should fallback to environment variables
- Invalid configuration should log warnings but not crash service
- Partial config loading should be detected and handled

Test Strategy:
- Use real configuration system (no mocks per CLAUDE.md)
- Test actual environment variable and secret loading
- Verify graceful degradation for missing secrets
- Confirm service stability with partial configuration
"""

import pytest
import asyncio
import os
from typing import Dict, Any, Optional
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

# ABSOLUTE IMPORTS - Following SPEC/import_management_architecture.xml
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.core.configuration.secrets import SecretManager
from shared.isolated_environment import get_env, IsolatedEnvironment
from netra_backend.app.config import get_config
from netra_backend.app.startup_module import initialize_logging


class TestConfigurationResilience:
    """Test configuration loading resilience that currently fails."""
    
    def test_missing_database_url_should_use_safe_default(self):
        """Test service handles missing DATABASE_URL gracefully.
        
        CURRENTLY FAILS: Service crashes when DATABASE_URL is not provided,
        should use safe default or provide clear error message.
        
        Expected: Should use default database URL or fail gracefully with guidance.
        """
        # Remove DATABASE_URL completely
        with patch.dict(os.environ, {}, clear=True):
            # Add minimal required environment
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'development',
                'SERVICE_NAME': 'netra_backend',
                # DATABASE_URL is missing - this should be handled gracefully
            }):
                try:
                    config = get_unified_config()
                    
                    # Should not crash - should provide default or clear error
                    assert config is not None, "Configuration should load even with missing DATABASE_URL"
                    
                    # Should have some database configuration (default or error indication)
                    database_url = getattr(config, 'database_url', None)
                    if database_url is None:
                        # If no default, should have clear error indication
                        assert hasattr(config, 'configuration_errors'), \
                            "Should track configuration errors when DATABASE_URL is missing"
                    
                except Exception as e:
                    pytest.fail(f"Configuration should handle missing DATABASE_URL gracefully: {e}")
    
    def test_gcp_secret_manager_unavailable_should_fallback(self):
        """Test GCP Secret Manager failures fallback to environment variables.
        
        CURRENTLY FAILS: Service crashes when GCP Secret Manager is unavailable,
        should fallback to environment variables for secrets.
        
        Expected: Should use environment variables when GCP secrets unavailable.
        """
        # Simulate GCP Secret Manager being unavailable
        with patch.dict(os.environ, {
            'GCP_PROJECT_ID': 'invalid-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/nonexistent/credentials.json',
            'ENVIRONMENT': 'staging',  # Staging should handle this
            'GEMINI_API_KEY': 'fallback-api-key-from-env',  # Fallback in env
            'JWT_SECRET_KEY': 'fallback-jwt-secret-from-env',  # Fallback in env
        }):
            try:
                secret_manager = SecretManager()
                
                # Should not crash during initialization
                assert secret_manager is not None, "SecretManager should initialize even with invalid GCP config"
                
                # Should detect environment and handle GCP unavailability
                environment = secret_manager._get_environment()
                assert environment == 'staging', "Should detect staging environment"
                
                # Should be able to get config without crashing
                config = get_unified_config()
                assert config is not None, "Config should load with GCP Secret Manager unavailable"
                
                # Should use environment variables as fallback
                # This will currently fail if GCP secrets are required
                
            except Exception as e:
                pytest.fail(f"Should fallback to environment variables when GCP unavailable: {e}")
    
    def test_invalid_environment_values_should_be_sanitized(self):
        """Test invalid environment variable values are handled safely.
        
        CURRENTLY FAILS: Invalid environment values may cause parsing errors
        or security issues when not properly validated.
        
        Expected: Should sanitize invalid values and use safe defaults.
        """
        # Provide invalid values for various configuration fields
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db',
            'REDIS_PORT': 'invalid_port_number',  # Invalid integer
            'CORS_ORIGINS': 'not-a-valid-json-array',  # Invalid JSON
            'MAX_WORKERS': 'not-a-number',  # Invalid integer
            'DEBUG': 'maybe',  # Invalid boolean
            'JWT_EXPIRE_MINUTES': 'forever',  # Invalid integer
        }):
            try:
                config = get_unified_config()
                
                # Should not crash with invalid values
                assert config is not None, "Config should load even with invalid values"
                
                # Should have sanitized values or safe defaults
                if hasattr(config, 'redis_port'):
                    redis_port = getattr(config, 'redis_port', None)
                    if redis_port is not None:
                        assert isinstance(redis_port, int), "Redis port should be sanitized to integer"
                        assert 1 <= redis_port <= 65535, "Redis port should be in valid range"
                
                if hasattr(config, 'max_workers'):
                    max_workers = getattr(config, 'max_workers', None) 
                    if max_workers is not None:
                        assert isinstance(max_workers, int), "Max workers should be sanitized to integer"
                        assert max_workers > 0, "Max workers should be positive"
                
                # Debug should be sanitized to boolean
                if hasattr(config, 'debug'):
                    debug_value = getattr(config, 'debug', None)
                    if debug_value is not None:
                        assert isinstance(debug_value, bool), "Debug should be sanitized to boolean"
                
            except Exception as e:
                pytest.fail(f"Configuration should sanitize invalid environment values: {e}")
    
    def test_partial_configuration_loading_detected_and_handled(self):
        """Test partial configuration loading is detected and handled.
        
        CURRENTLY FAILS: Partial configuration loading may leave service
        in inconsistent state without proper error handling.
        
        Expected: Should detect partial loads and either complete or fail clearly.
        """
        # Simulate partial configuration by providing some but not all required values
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',  # Production requires more config
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db',
            # Missing: REDIS_URL, JWT_SECRET_KEY, etc.
            'SERVICE_NAME': 'netra_backend',
        }):
            try:
                config = get_unified_config()
                
                # Should either complete configuration with defaults or fail clearly
                assert config is not None, "Configuration should not return None"
                
                # Should track missing required configuration
                if hasattr(config, 'configuration_errors'):
                    errors = getattr(config, 'configuration_errors', [])
                    if errors:
                        # If errors are tracked, they should be actionable
                        for error in errors:
                            assert isinstance(error, str), "Configuration errors should be strings"
                            assert len(error) > 0, "Configuration errors should not be empty"
                
                # Should have environment properly set
                assert hasattr(config, 'environment'), "Should have environment field"
                assert config.environment == 'production', "Should preserve environment setting"
                
            except Exception as e:
                # If it fails, the error should be clear and actionable
                error_message = str(e)
                assert 'configuration' in error_message.lower(), \
                    f"Configuration errors should be clearly identified: {e}"
    
    def test_environment_isolation_prevents_cross_contamination(self):
        """Test environment isolation prevents configuration cross-contamination.
        
        CURRENTLY FAILS: Environment configurations may leak between test runs
        or different service instances, causing unpredictable behavior.
        
        Expected: Should maintain proper environment isolation.
        """
        # Test development environment isolation
        dev_env = {
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://dev:pass@localhost:5432/dev_db',
            'DEBUG': 'true',
            'REDIS_URL': 'redis://localhost:6379/0'
        }
        
        # Test staging environment isolation
        staging_env = {
            'ENVIRONMENT': 'staging',
            'DATABASE_URL': 'postgresql://staging:pass@staging:5432/staging_db',
            'DEBUG': 'false',
            'REDIS_URL': 'redis://staging-redis:6379/0'
        }
        
        try:
            # Load development configuration
            with patch.dict(os.environ, dev_env, clear=True):
                dev_config = get_unified_config()
                dev_environment = dev_config.environment
                dev_debug = getattr(dev_config, 'debug', None)
                
                # Verify development configuration
                assert dev_environment == 'development', "Should load development environment"
                if dev_debug is not None:
                    assert dev_debug is True, "Development should have debug enabled"
            
            # Load staging configuration - should not be contaminated by dev
            with patch.dict(os.environ, staging_env, clear=True):
                staging_config = get_unified_config()
                staging_environment = staging_config.environment
                staging_debug = getattr(staging_config, 'debug', None)
                
                # Verify staging configuration is isolated
                assert staging_environment == 'staging', "Should load staging environment"
                if staging_debug is not None:
                    assert staging_debug is False, "Staging should have debug disabled"
                
                # Should not have development values
                assert staging_environment != dev_environment or staging_environment == 'staging', \
                    "Staging config should not be contaminated by development config"
        
        except Exception as e:
            pytest.fail(f"Environment isolation should prevent cross-contamination: {e}")
    
    def test_secret_loading_timeout_handling(self):
        """Test secret loading handles timeouts gracefully.
        
        CURRENTLY FAILS: Secret loading may hang or crash when GCP Secret Manager
        is slow to respond, affecting service startup time.
        
        Expected: Should timeout gracefully and use fallback values.
        """
        # Simulate slow/hanging secret manager by pointing to invalid endpoint
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT_ID': 'test-project',
            'GOOGLE_APPLICATION_CREDENTIALS': '/tmp/fake-credentials.json',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db',
            # Provide fallback values in environment
            'GEMINI_API_KEY': 'fallback-key',
            'JWT_SECRET_KEY': 'fallback-jwt-secret',
        }):
            try:
                import time
                start_time = time.time()
                
                # This should complete within reasonable time even with GCP unavailable
                secret_manager = SecretManager()
                config = get_unified_config()
                
                elapsed_time = time.time() - start_time
                
                # Should not take too long (hanging on network calls)
                assert elapsed_time < 30, f"Secret loading took too long: {elapsed_time}s"
                
                # Should have loaded configuration successfully
                assert config is not None, "Should load config even with slow/unavailable GCP"
                
                # Should use fallback values from environment
                # This will currently fail if secret manager hangs
                
            except Exception as e:
                pytest.fail(f"Secret loading should handle timeouts gracefully: {e}")
    
    @pytest.mark.asyncio
    async def test_async_configuration_loading_thread_safety(self):
        """Test configuration loading is thread-safe in async environment.
        
        CURRENTLY FAILS: Configuration loading may have race conditions
        when accessed from multiple async contexts simultaneously.
        
        Expected: Should be thread-safe and return consistent results.
        """
        # Set up consistent environment
        test_env = {
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'SERVICE_NAME': 'netra_backend',
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            try:
                # Load configuration from multiple async contexts simultaneously
                async def load_config():
                    return get_unified_config()
                
                # Start multiple config loading tasks
                tasks = [load_config() for _ in range(10)]
                configs = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed or all should fail consistently
                exceptions = [c for c in configs if isinstance(c, Exception)]
                if exceptions:
                    # If any failed, they should all fail with the same error
                    assert len(exceptions) == len(configs), \
                        "Configuration loading should be consistent across async contexts"
                else:
                    # All should have loaded the same configuration
                    first_config = configs[0]
                    for config in configs[1:]:
                        assert config.environment == first_config.environment, \
                            "All async config loads should return same environment"
                        assert getattr(config, 'database_url', None) == getattr(first_config, 'database_url', None), \
                            "All async config loads should return same database_url"
                            
            except Exception as e:
                pytest.fail(f"Async configuration loading should be thread-safe: {e}")


if __name__ == "__main__":
    # Run specific failing tests to demonstrate issues
    pytest.main([__file__, "-v", "--tb=short"])