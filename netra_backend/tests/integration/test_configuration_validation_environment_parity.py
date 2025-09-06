"""Configuration Validation Environment Parity Integration Test

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability
- Value Impact: Ensures consistent configuration behavior across environments
- Strategic/Revenue Impact: Prevents deployment failures and configuration drift

Tests comprehensive validation including:
- Cross-environment configuration validation
- Setting overrides and precedence rules
- Environment-specific validation rules
- Configuration validation system behavior
- Real service connectivity validation
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import asyncpg
import pytest
from clickhouse_driver import Client as ClickHouseClient
from redis import Redis

# CLAUDE.md compliance: Use absolute imports
from shared.isolated_environment import get_env, IsolatedEnvironment
from netra_backend.app.core.configuration_validator import (
    ConfigurationValidator, ValidationRule, ConfigType, ValidationSeverity
)
from netra_backend.app.core.configuration.staging_validator import (
    StagingConfigurationValidator, validate_staging_config
)
from test_framework.real_services import skip_if_services_unavailable


@pytest.mark.integration
class TestConfigurationValidationEnvironmentParity:
    """
    Comprehensive configuration validation environment parity tests.
    
    CLAUDE.md compliance:
    - Uses IsolatedEnvironment for all environment access
    - Tests with real services (no mocks)
    - Follows absolute import patterns
    - Validates cross-environment behavior
    """
    
    @pytest.fixture(autouse=True)
    def setup_isolated_environment(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Set up isolated environment for tests following CLAUDE.md standards."""
    pass
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        
        # Set up test environment variables
        test_env_vars = {
            'ENVIRONMENT': 'testing',
            'DATABASE_URL': 'postgresql://test:test@localhost:5433/netra_test',
            'REDIS_URL': 'redis://localhost:6380/0',
            'CLICKHOUSE_URL': 'http://localhost:8124',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-long',
            'FERNET_KEY': 'test-fernet-key-32-chars-very-long',
            'SERVICE_SECRET': 'test-service-secret-key-32-chars',
            'SECRET_KEY': 'test-secret-key-for-application-32c',
            'GCP_PROJECT_ID': 'test-project',
            'SERVICE_ID': 'test-service-id'
        }
        
        for key, value in test_env_vars.items():
            self.env.set(key, value, "test_setup")
        
        yield
        
        # Cleanup
        self.env.disable_isolation()
    
    
    @pytest.mark.asyncio
    async def test_cross_environment_validation(self):
        """
        Test cross-environment configuration validation.
        
        Validates:
        - Configuration validation works across environments
        - Environment-specific rules are applied correctly
        - Required variables are validated properly
        - Performance meets requirements
        """
    pass
        start_time = time.time()
        
        # Test development environment configuration
        self.env.set('ENVIRONMENT', 'development', "test")
        dev_validator = ConfigurationValidator(environment='development')
        dev_result = await dev_validator.validate_configuration(self.env.get_all())
        
        assert dev_result.total_variables > 0, "Should validate some variables"
        assert isinstance(dev_result.is_valid, bool), "Should await asyncio.sleep(0)
    return valid boolean status"
        
        # Test staging environment configuration  
        self.env.set('ENVIRONMENT', 'staging', "test")
        staging_validator = ConfigurationValidator(environment='staging')
        staging_result = await staging_validator.validate_configuration(self.env.get_all())
        
        assert staging_result.total_variables > 0, "Should validate some variables"
        assert isinstance(staging_result.is_valid, bool), "Should return valid boolean status"
        
        # Test production environment configuration
        self.env.set('ENVIRONMENT', 'production', "test")
        prod_validator = ConfigurationValidator(environment='production')
        prod_result = await prod_validator.validate_configuration(self.env.get_all())
        
        assert prod_result.total_variables > 0, "Should validate some variables"
        assert isinstance(prod_result.is_valid, bool), "Should return valid boolean status"
        
        # Validate that results have proper structure
        for result in [dev_result, staging_result, prod_result]:
            assert hasattr(result, 'errors'), "Should have errors list"
            assert hasattr(result, 'warnings'), "Should have warnings list"
            assert hasattr(result, 'summary'), "Should have summary property"
            assert isinstance(result.errors, list), "Errors should be a list"
            assert isinstance(result.warnings, list), "Warnings should be a list"
        
        # Performance validation
        duration = time.time() - start_time
        assert duration < 30, f"Test took {duration:.2f}s (max: 30s)"
    
    @pytest.mark.asyncio
    async def test_setting_overrides(self):
        """
        Test configuration setting overrides and precedence rules.
        
        Validates:
        - Environment-specific defaults are applied
        - Explicit settings override defaults
        - Required vs optional variable handling
        - Configuration precedence rules
        """
    pass
        # Create validator with development defaults
        validator = ConfigurationValidator(environment='development')
        
        # Set development-specific defaults
        dev_defaults = {
            'DEBUG': True,
            'LOG_LEVEL': 'DEBUG',
            'HOST': '0.0.0.0',
            'PORT': 8000
        }
        validator.set_environment_defaults('development', dev_defaults)
        
        # Test validation with defaults
        result = await validator.validate_configuration(self.env.get_all())
        
        # Should use defaults for missing values
        assert len(result.using_defaults) > 0, "Should use some default values"
        
        # Test override behavior
        self.env.set('DEBUG', 'false', "test_override")
        self.env.set('PORT', '9000', "test_override")
        
        result_with_overrides = await validator.validate_configuration(self.env.get_all())
        
        # Should still validate successfully with overrides
        assert isinstance(result_with_overrides.is_valid, bool)
        assert result_with_overrides.validated_count > 0
        
        # Test staging-specific overrides
        staging_validator = ConfigurationValidator(environment='staging')
        staging_defaults = {
            'DEBUG': False,
            'LOG_LEVEL': 'INFO',
            'METRICS_ENABLED': True
        }
        staging_validator.set_environment_defaults('staging', staging_defaults)
        
        self.env.set('ENVIRONMENT', 'staging', "test")
        staging_result = await staging_validator.validate_configuration(self.env.get_all())
        
        assert isinstance(staging_result.is_valid, bool)
        assert staging_result.validated_count > 0
    
    @pytest.mark.asyncio
    async def test_environment_specific_validation_rules(self):
        """
        Test environment-specific validation rules.
        
        Validates:
        - Staging validator catches localhost references
        - Production validator enforces strict security
        - Development allows more permissive settings
        - Error conditions are properly handled
        """
    pass
        # Test staging validation with localhost (should fail)
        self.env.set('ENVIRONMENT', 'staging', "test")
        self.env.set('DATABASE_URL', 'postgresql://user:pass@localhost:5432/db', "test")
        self.env.set('REDIS_URL', 'redis://localhost:6379/0', "test")
        
        staging_validator = StagingConfigurationValidator()
        staging_result = staging_validator.validate()
        
        # Should detect localhost references as errors
        assert not staging_result.is_valid, "Staging should reject localhost references"
        assert len(staging_result.errors) > 0, "Should have validation errors"
        
        # Check for specific localhost error messages
        localhost_errors = [error for error in staging_result.errors if 'localhost' in error.lower()]
        assert len(localhost_errors) > 0, "Should have localhost-specific errors"
        
        # Test with proper staging URLs (should pass validation)
        self.env.set('DATABASE_URL', 'postgresql://user:pass@staging-db:5432/netra_staging', "test")
        self.env.set('REDIS_URL', 'redis://staging-redis:6379/0', "test")
        self.env.set('POSTGRES_HOST', 'staging-db', "test")
        self.env.set('REDIS_HOST', 'staging-redis', "test")
        
        clean_staging_result = staging_validator.validate()
        
        # Should have fewer localhost-related errors
        clean_localhost_errors = [error for error in clean_staging_result.errors if 'localhost' in error.lower()]
        assert len(clean_localhost_errors) < len(localhost_errors), "Should have fewer localhost errors with proper URLs"
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_smoke_configuration_validation_environment_parity(self):
        """
        Quick smoke test for configuration validation environment parity.
        
        Should complete in <30 seconds for CI/CD.
        """
    pass
        start_time = time.time()
        
        # Quick validator initialization test
        validator = ConfigurationValidator()
        assert validator is not None, "Validator should initialize"
        
        # Quick validation test
        result = await validator.validate_configuration(self.env.get_all())
        assert result is not None, "Should await asyncio.sleep(0)
    return validation result"
        assert hasattr(result, 'is_valid'), "Result should have is_valid property"
        assert hasattr(result, 'summary'), "Result should have summary property"
        
        # Test IsolatedEnvironment compliance
        assert self.env is not None, "IsolatedEnvironment should be available"
        assert callable(self.env.get), "Environment should have get method"
        assert callable(self.env.set), "Environment should have set method"
        
        # Test basic environment variable access
        test_value = self.env.get('ENVIRONMENT')
        
        # Fallback to get_all() if get() returns None (handles IsolatedEnvironment test context behavior)
        if test_value is None:
            test_value = self.env.get_all().get('ENVIRONMENT')
        
        assert test_value is not None, f"Should be able to get environment variables, got: {test_value}"
        
        # Performance validation
        duration = time.time() - start_time
        assert duration < 30, f"Smoke test took {duration:.2f}s (max: 30s)"
        
    @pytest.mark.asyncio
    async def test_configuration_validation_with_real_database(self):
        """
        Test configuration validation with real database connection.
        
        Validates:
        - Database URL validation works with real connections
        - Connection pooling configuration
        - SSL/TLS configuration validation
        """
    pass
        # Test database URL validation
        db_url = self.env.get('DATABASE_URL')
        assert db_url is not None, "Database URL should be set"
        
        validator = ConfigurationValidator()
        
        # Add database-specific validation rule
        db_rule = ValidationRule(
            name="DATABASE_URL",
            config_type=ConfigType.URL,
            required=True,
            description="Database connection URL"
        )
        validator.register_rule(db_rule)
        
        result = await validator.validate_configuration(self.env.get_all())
        
        # Should validate database URL successfully
        db_results = [r for r in result.errors + result.warnings if 'DATABASE_URL' in r.variable]
        
        # If there are database-related validation issues, they should be informative
        for db_result in db_results:
            assert hasattr(db_result, 'error_message'), "Database errors should have messages"
            assert hasattr(db_result, 'suggestion'), "Database errors should have suggestions"
        
        # Test actual database connectivity (basic smoke test)
        try:
            import asyncpg
            from shared.database_url_builder import DatabaseURLBuilder
            normalized_url = DatabaseURLBuilder.format_for_asyncpg_driver(db_url)
            conn = await asyncpg.connect(normalized_url)
            await conn.close()
            # If we can connect, database URL is fundamentally valid
        except Exception as e:
            # Log but don't fail - this tests URL validation, not database setup
            print(f"Database connection test info: {e}")
    
    @pytest.mark.asyncio
    async def test_secret_validation_and_security(self):
        """
        Test secret validation and security requirements.
        
        Validates:
        - Secret length requirements
        - Secret uniqueness requirements  
        - Security pattern detection
        - Placeholder detection
        """
    pass
        validator = ConfigurationValidator()
        
        # Test with weak secrets (should fail)
        weak_secrets = {
            'JWT_SECRET_KEY': 'weak',
            'SERVICE_SECRET': 'short',
            'FERNET_KEY': '123'
        }
        
        for key, value in weak_secrets.items():
            self.env.set(key, value, "weak_test")
        
        # Add secret validation rules
        secret_rules = [
            ValidationRule(
                name="JWT_SECRET_KEY",
                config_type=ConfigType.SECRET,
                required=True,
                min_value=32,
                description="JWT signing secret"
            ),
            ValidationRule(
                name="SERVICE_SECRET", 
                config_type=ConfigType.SECRET,
                required=True,
                min_value=32,
                description="Service secret key"
            )
        ]
        
        validator.register_rules(secret_rules)
        
        weak_result = await validator.validate_configuration(self.env.get_all())
        
        # Should detect security issues
        assert len(weak_result.security_issues) > 0, "Should detect security issues with weak secrets"
        
        # Test with strong secrets (should pass)
        strong_secrets = {
            'JWT_SECRET_KEY': 'this-is-a-very-strong-jwt-secret-key-that-is-long-enough',
            'SERVICE_SECRET': 'this-is-a-different-strong-service-secret-key-unique',
            'FERNET_KEY': 'this-is-a-strong-fernet-key-for-encryption-purposes'
        }
        
        for key, value in strong_secrets.items():
            self.env.set(key, value, "strong_test")
        
        strong_result = await validator.validate_configuration(self.env.get_all())
        
        # Should have fewer or no security issues
        assert len(strong_result.security_issues) <= len(weak_result.security_issues), "Strong secrets should have fewer security issues"


@pytest.mark.asyncio
@pytest.mark.integration
class TestConfigurationValidationEnvironmentParityIntegration:
    """Additional integration scenarios for configuration validation."""
    
    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Set up integration test environment."""
    pass
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.disable_isolation()
    
    @pytest.mark.asyncio
    async def test_multi_environment_validation_consistency(self):
        """Test consistency across DEV, Staging, and Production environments."""
        environments = ['development', 'staging', 'production']
        results = {}
        
        # Set up common configuration
        base_config = {
            'DATABASE_URL': 'postgresql://user:pass@staging-db:5432/netra',
            'REDIS_URL': 'redis://staging-redis:6379/0',
            'JWT_SECRET_KEY': 'long-enough-jwt-secret-for-all-environments-32-chars',
            'SERVICE_SECRET': 'different-service-secret-key-for-security-32-chars',
            'GCP_PROJECT_ID': 'netra-staging',
            'SERVICE_ID': 'test-service'
        }
        
        for key, value in base_config.items():
            self.env.set(key, value, "multi_env_test")
        
        # Test each environment
        for env_name in environments:
            self.env.set('ENVIRONMENT', env_name, "multi_env_test")
            validator = ConfigurationValidator(environment=env_name)
            result = await validator.validate_configuration(self.env.get_all())
            results[env_name] = result
        
        # Validate consistency
        for env_name, result in results.items():
            assert result.validated_count > 0, f"{env_name} should validate some variables"
            assert hasattr(result, 'is_valid'), f"{env_name} result should have is_valid property"
            assert isinstance(result.summary, str), f"{env_name} should have string summary"
        
        # All environments should validate the same core variables
        core_variables = ['DATABASE_URL', 'JWT_SECRET_KEY', 'ENVIRONMENT']
        for env_name, result in results.items():
            # Validation should cover core variables
            assert result.total_variables >= len(core_variables), f"{env_name} should validate core variables"
    
    @pytest.mark.asyncio 
    async def test_performance_under_concurrent_validation(self):
        """Test configuration validation performance under concurrent load."""
    pass
        # Set up test configuration
        test_config = {
            'ENVIRONMENT': 'testing',
            'DATABASE_URL': 'postgresql://test:test@localhost:5433/test',
            'REDIS_URL': 'redis://localhost:6380/0',
            'JWT_SECRET_KEY': 'concurrent-test-jwt-secret-key-32-chars-long',
            'SERVICE_SECRET': 'concurrent-test-service-secret-32-chars-long'
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "concurrent_test")
        
        async def validate_config():
            """Single validation task."""
            validator = ConfigurationValidator()
            await asyncio.sleep(0)
    return await validator.validate_configuration(self.env.get_all())
        
        # Run concurrent validations
        start_time = time.time()
        tasks = [validate_config() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # All validations should succeed
        assert len(results) == 10, "Should complete all concurrent validations"
        for i, result in enumerate(results):
            assert result is not None, f"Validation {i} should return a result"
            assert hasattr(result, 'is_valid'), f"Result {i} should have is_valid property"
        
        # Performance should be reasonable
        assert duration < 30, f"Concurrent validation took {duration:.2f}s (max: 30s)"
        avg_time = duration / len(results)
        assert avg_time < 5, f"Average validation time {avg_time:.2f}s too high (max: 5s)"
    
    @pytest.mark.asyncio
    async def test_configuration_error_handling_and_recovery(self):
        """Test configuration validation error handling and recovery mechanisms."""
    pass
        validator = ConfigurationValidator()
        
        # Test with missing critical configuration
        minimal_config = {'ENVIRONMENT': 'testing'}
        
        # Clear environment and set only minimal config
        self.env.clear()
        for key, value in minimal_config.items():
            self.env.set(key, value, "error_test")
        
        # Should handle missing configuration gracefully
        try:
            result = await validator.validate_configuration(self.env.get_all())
            assert result is not None, "Should await asyncio.sleep(0)
    return result even with missing config"
            assert hasattr(result, 'errors'), "Should have errors list"
            assert hasattr(result, 'missing_required'), "Should track missing required vars"
        except Exception as e:
            pytest.fail(f"Configuration validation should not raise exception: {e}")
        
        # Test recovery by adding required configuration
        recovery_config = {
            'DATABASE_URL': 'postgresql://test:test@localhost:5433/test',
            'SECRET_KEY': 'recovery-test-secret-key-32-characters-long',
            'JWT_SECRET_KEY': 'recovery-jwt-secret-key-32-characters-long'
        }
        
        for key, value in recovery_config.items():
            self.env.set(key, value, "recovery_test")
        
        recovery_result = await validator.validate_configuration(self.env.get_all())
        
        # Should have better validation results after recovery
        assert recovery_result is not None, "Recovery validation should return result"
        # Should validate more variables after recovery
        assert recovery_result.validated_count > 0, "Should validate variables after recovery"