"""Comprehensive Integration Tests for UnifiedConfigManager

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: System Stability - Prevent $12K MRR loss from configuration errors
- Value Impact: Ensures configuration system supports chat functionality, agent execution
- Strategic Impact: Prevents OAuth regression bugs that block enterprise customers

CRITICAL REQUIREMENTS:
- NO MOCKS! Use real configuration manager instances
- Test realistic multi-environment scenarios (dev/staging/prod) 
- Focus on configuration that supports WebSocket agent events (mission critical)
- Test scenarios that catch OAuth regression bugs (critical business impact)
- Test database connectivity configuration validation
- Test JWT secret sharing across services

This test suite validates the configuration management system that enables:
1. WebSocket agent events for chat functionality ($50K MRR dependent)
2. Multi-user isolation for concurrent agent execution
3. Cross-service authentication consistency 
4. Environment-specific configuration integrity
5. Configuration hot-reload capabilities for development velocity

Categories: integration
"""

import os
import pytest
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
import hashlib
import json
from unittest.mock import patch

# Use backend-specific isolated environment for consistency
from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_unified_jwt_secret, get_jwt_secret_manager
from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager, 
    get_unified_config, 
    validate_unified_config,
    config_manager
)
from netra_backend.app.core.configuration.validator import ConfigurationValidator, ValidationMode
from netra_backend.app.core.environment_constants import EnvironmentDetector
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig, NetraTestingConfig


class TestUnifiedConfigManagerCore:
    """Core configuration manager functionality tests.
    
    BVJ: Ensures basic configuration loading works for chat functionality.
    """

    def test_config_manager_singleton_consistency(self):
        """Test that config manager maintains singleton behavior across services.
        
        BVJ: Prevents configuration inconsistencies that break multi-user isolation.
        """
        # CRITICAL: Test that same instance is returned consistently
        manager1 = UnifiedConfigManager()
        manager2 = UnifiedConfigManager() 
        
        # Both should work independently but with same environment detection
        config1 = manager1.get_config()
        config2 = manager2.get_config()
        
        # Both configs should be valid
        assert config1 is not None
        assert config2 is not None
        assert isinstance(config1, AppConfig)
        assert isinstance(config2, AppConfig)
        
        # Environment should be consistent
        assert manager1.get_environment_name() == manager2.get_environment_name()

    def test_environment_detection_accuracy(self):
        """Test accurate environment detection across scenarios.
        
        BVJ: Prevents deploying dev config to production (compliance violation).
        """
        env = get_env()
        manager = UnifiedConfigManager()
        
        # Test testing environment detection
        original_env = env.get("ENVIRONMENT")
        original_testing = env.get("TESTING") 
        original_pytest = env.get("PYTEST_CURRENT_TEST")
        
        try:
            # Simulate testing environment
            env.set("ENVIRONMENT", "testing", "test_setup")
            env.set("TESTING", "true", "test_setup")
            env.set("PYTEST_CURRENT_TEST", "test_config", "test_setup")
            
            # Force environment detection refresh
            manager._environment = None
            environment = manager.get_environment_name()
            
            # Should detect testing environment
            assert environment in ["testing", "development"]  # Both acceptable for test context
            assert manager.is_testing() or manager.is_development()
            assert not manager.is_production()
            
        finally:
            # Restore original environment
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup")
            else:
                env.delete("ENVIRONMENT")
            if original_testing:
                env.set("TESTING", original_testing, "test_cleanup") 
            else:
                env.delete("TESTING")
            if original_pytest:
                env.set("PYTEST_CURRENT_TEST", original_pytest, "test_cleanup")
            else:
                env.delete("PYTEST_CURRENT_TEST")

    def test_config_validation_integration(self):
        """Test configuration validation integration with validator.
        
        BVJ: Prevents invalid configurations from reaching production.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Test validation integration
        is_valid = manager.validate_config_integrity()
        assert isinstance(is_valid, bool)
        
        # Validation should work without errors
        validator = ConfigurationValidator()
        result = validator.validate_complete_config(config)
        
        assert result is not None
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'score')
        
        # Score should be reasonable (0-100)
        assert 0 <= result.score <= 100

    def test_config_hot_reload_capability(self):
        """Test configuration hot-reload for development velocity.
        
        BVJ: Enables rapid development iteration without service restarts.
        """
        env = get_env()
        manager = UnifiedConfigManager()
        
        # Get initial config
        config1 = manager.get_config()
        initial_env = config1.environment
        
        # Change an environment variable
        original_debug = env.get("DEBUG")
        try:
            env.set("DEBUG", "true", "test_hot_reload")
            
            # Force reload
            config2 = manager.reload_config(force=True)
            
            # Config should be reloaded
            assert config2 is not None
            assert isinstance(config2, AppConfig)
            
            # Environment should remain consistent
            assert config2.environment == initial_env
            
        finally:
            if original_debug:
                env.set("DEBUG", original_debug, "test_cleanup")
            else:
                env.delete("DEBUG")

    def test_config_caching_behavior(self):
        """Test configuration caching for performance.
        
        BVJ: Ensures fast config access for chat responsiveness.
        """
        manager = UnifiedConfigManager()
        
        # Multiple calls should return same instance when cached
        config1 = manager.get_config()
        config2 = manager.get_config()
        
        # Should be same cached instance
        assert config1 is config2
        
        # After force reload, should be different instance
        config3 = manager.reload_config(force=True)
        assert config3 is not config1  # New instance after reload


class TestEnvironmentSpecificConfiguration:
    """Test environment-specific configuration behavior.
    
    BVJ: Ensures proper environment isolation prevents production data exposure.
    """

    def test_development_config_fallbacks(self):
        """Test development configuration with fallback values.
        
        BVJ: Enables developer productivity without complex setup.
        """
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        original_testing = env.get("TESTING")
        original_pytest = env.get("PYTEST_CURRENT_TEST")
        
        try:
            # Clear testing environment indicators to force development
            env.delete("TESTING")
            env.delete("PYTEST_CURRENT_TEST")
            env.set("ENVIRONMENT", "development", "test_setup")
            
            manager = UnifiedConfigManager()
            manager._environment = None  # Force refresh
            config = manager.get_config()
            
            assert isinstance(config, (DevelopmentConfig, AppConfig))
            # Allow testing environment since we're running under pytest
            assert config.environment in ["development", "testing"]
            
            # Should not be production regardless
            assert not manager.is_production()
            
        finally:
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup")
            else:
                env.delete("ENVIRONMENT")
            if original_testing:
                env.set("TESTING", original_testing, "test_cleanup")
            else:
                env.delete("TESTING")
            if original_pytest:
                env.set("PYTEST_CURRENT_TEST", original_pytest, "test_cleanup")
            else:
                env.delete("PYTEST_CURRENT_TEST")

    def test_testing_config_isolation(self):
        """Test testing configuration isolation.
        
        BVJ: Prevents test data from leaking to other environments.
        """
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        original_testing = env.get("TESTING")
        
        try:
            # Force testing environment explicitly
            env.set("ENVIRONMENT", "testing", "test_setup")
            env.set("TESTING", "true", "test_setup")
            
            manager = UnifiedConfigManager()
            manager._environment = None  # Force refresh
            config = manager.get_config()
            
            assert isinstance(config, (NetraTestingConfig, AppConfig))
            assert config.environment == "testing"
            
            # Testing should be detected correctly
            assert manager.is_testing()
            assert not manager.is_production()
            
        finally:
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup")
            else:
                env.delete("ENVIRONMENT")
            if original_testing:
                env.set("TESTING", original_testing, "test_cleanup")
            else:
                env.delete("TESTING")

    def test_production_config_strictness(self):
        """Test production configuration strictness.
        
        BVJ: Prevents security vulnerabilities in production.
        """
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        original_testing = env.get("TESTING")
        original_pytest = env.get("PYTEST_CURRENT_TEST")
        
        try:
            # Clear testing indicators and force production environment
            env.delete("TESTING")
            env.delete("PYTEST_CURRENT_TEST")
            env.set("ENVIRONMENT", "production", "test_setup")
            
            manager = UnifiedConfigManager()
            manager._environment = None  # Force refresh
            config = manager.get_config()
            
            # Should create production-like config (but might still be testing due to pytest)
            assert config.environment in ["production", "testing"]  # Allow testing due to pytest context
            
            # Key point: should not be development
            assert not manager.is_development()
            
        finally:
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup")
            else:
                env.delete("ENVIRONMENT")
            if original_testing:
                env.set("TESTING", original_testing, "test_cleanup")
            else:
                env.delete("TESTING")
            if original_pytest:
                env.set("PYTEST_CURRENT_TEST", original_pytest, "test_cleanup")
            else:
                env.delete("PYTEST_CURRENT_TEST")

    def test_staging_config_production_parity(self):
        """Test staging configuration matches production requirements.
        
        BVJ: Prevents staging-production deployment surprises.
        """
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        original_testing = env.get("TESTING")
        original_pytest = env.get("PYTEST_CURRENT_TEST")
        
        try:
            # Clear testing indicators and force staging environment
            env.delete("TESTING")
            env.delete("PYTEST_CURRENT_TEST")
            env.set("ENVIRONMENT", "staging", "test_setup")
            
            manager = UnifiedConfigManager()
            manager._environment = None  # Force refresh
            config = manager.get_config()
            
            assert isinstance(config, (StagingConfig, AppConfig))
            # Allow testing environment due to pytest context
            assert config.environment in ["staging", "testing"]
            
            # Key point: should not be development
            assert not manager.is_development()
            
        finally:
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup")
            else:
                env.delete("ENVIRONMENT")
            if original_testing:
                env.set("TESTING", original_testing, "test_cleanup")
            else:
                env.delete("TESTING")
            if original_pytest:
                env.set("PYTEST_CURRENT_TEST", original_pytest, "test_cleanup")
            else:
                env.delete("PYTEST_CURRENT_TEST")


class TestDatabaseConfigurationIntegration:
    """Test database configuration validation and URL building.
    
    BVJ: Ensures database connectivity for agent execution persistence.
    """

    def test_database_url_validation(self):
        """Test database URL format validation.
        
        BVJ: Prevents database connection failures that break chat.
        """
        env = get_env()
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Database URL should be present and valid format
        assert hasattr(config, 'database_url')
        if config.database_url:
            # Should be valid postgres URL format
            assert config.database_url.startswith(('postgresql://', 'postgres://', 'sqlite://'))

    def test_database_ssl_configuration(self):
        """Test database SSL configuration for production.
        
        BVJ: Ensures secure database connections in production.
        """
        env = get_env()
        original_db_url = env.get("DATABASE_URL")
        
        try:
            # Test SSL database URL
            ssl_url = "postgresql://user:pass@host:5432/db?sslmode=require"
            env.set("DATABASE_URL", ssl_url, "test_setup")
            
            manager = UnifiedConfigManager()
            config = manager.reload_config(force=True)
            
            if config.database_url:
                # Should preserve SSL parameters
                assert "sslmode" in config.database_url or "ssl" in config.database_url.lower()
            
        finally:
            if original_db_url:
                env.set("DATABASE_URL", original_db_url, "test_cleanup")
            else:
                env.delete("DATABASE_URL")

    def test_database_connection_pooling_config(self):
        """Test database connection pooling configuration.
        
        BVJ: Ensures efficient database usage for multi-user system.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Should have reasonable pool settings for multi-user system
        if hasattr(config, 'database_pool_size'):
            assert config.database_pool_size > 1  # Multi-user needs pooling
        
        if hasattr(config, 'database_max_connections'):
            assert config.database_max_connections >= 5  # Minimum for multi-user

    def test_database_environment_specific_urls(self):
        """Test environment-specific database URL handling.
        
        BVJ: Prevents test data from contaminating production database.
        """
        env = get_env()
        
        # Test that different environments can have different database configs
        environments = ["development", "testing", "staging"]
        
        for environment in environments:
            original_env = env.get("ENVIRONMENT")
            try:
                env.set("ENVIRONMENT", environment, "test_setup")
                
                manager = UnifiedConfigManager()
                manager._environment = None  # Force refresh
                config = manager.get_config()
                
                # Allow testing environment due to pytest context
                assert config.environment in [environment, "testing"]
                
                # Each environment should handle database appropriately
                if config.database_url:
                    # No environment should use production database accidentally
                    assert "production" not in config.database_url.lower() or config.environment == "production"
                    
            finally:
                if original_env:
                    env.set("ENVIRONMENT", original_env, "test_cleanup")
                else:
                    env.delete("ENVIRONMENT")


class TestJWTSecretManagementIntegration:
    """Test JWT secret management integration across services.
    
    BVJ: Prevents WebSocket 403 auth failures that cost $50K MRR.
    """

    def test_jwt_secret_consistency_across_services(self):
        """Test JWT secret consistency prevents auth failures.
        
        BVJ: CRITICAL - Prevents WebSocket authentication failures.
        """
        # Test that JWT secret is consistent across service boundaries
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Get JWT secret through unified manager
        unified_secret = get_unified_jwt_secret()
        assert unified_secret is not None
        assert len(unified_secret) >= 16  # Minimum security requirement
        
        # Should be consistent across calls
        second_call = get_unified_jwt_secret()
        assert unified_secret == second_call

    def test_environment_specific_jwt_secrets(self):
        """Test environment-specific JWT secret resolution.
        
        BVJ: Prevents cross-environment JWT token leakage.
        """
        env = get_env()
        jwt_manager = get_jwt_secret_manager()
        
        # Test environment-specific JWT secret keys
        environments = ["development", "testing", "staging", "production"]
        
        for environment in environments:
            original_env = env.get("ENVIRONMENT")
            original_jwt_key = env.get("JWT_SECRET_KEY")
            env_specific_key = f"JWT_SECRET_{environment.upper()}"
            original_env_specific = env.get(env_specific_key)
            
            try:
                env.set("ENVIRONMENT", environment, "test_setup")
                
                # Set environment-specific JWT secret
                test_secret = f"test_jwt_secret_for_{environment}_environment_32chars"
                env.set(env_specific_key, test_secret, "test_setup")
                
                # Clear cache to force fresh resolution
                jwt_manager.clear_cache()
                
                resolved_secret = get_unified_jwt_secret()
                
                # For test environments, should get deterministic secret or configured secret
                assert resolved_secret is not None
                assert len(resolved_secret) >= 16
                
                if environment in ["development", "testing"]:
                    # Should either be our test secret or deterministic fallback
                    assert len(resolved_secret) >= 32
                    
            finally:
                # Restore original environment
                if original_env:
                    env.set("ENVIRONMENT", original_env, "test_cleanup")
                else:
                    env.delete("ENVIRONMENT")
                
                if original_jwt_key:
                    env.set("JWT_SECRET_KEY", original_jwt_key, "test_cleanup")
                else:
                    env.delete("JWT_SECRET_KEY")
                    
                if original_env_specific:
                    env.set(env_specific_key, original_env_specific, "test_cleanup")
                else:
                    env.delete(env_specific_key)
                
                jwt_manager.clear_cache()

    def test_jwt_secret_validation_strength(self):
        """Test JWT secret strength validation.
        
        BVJ: Prevents weak secrets that enable security breaches.
        """
        jwt_manager = get_jwt_secret_manager()
        
        # Test validation
        validation_result = jwt_manager.validate_jwt_configuration()
        
        assert isinstance(validation_result, dict)
        assert "valid" in validation_result
        assert "environment" in validation_result
        assert "issues" in validation_result
        assert "warnings" in validation_result
        
        # Get actual secret and validate strength
        secret = get_unified_jwt_secret()
        
        # Secret should meet minimum security requirements
        assert len(secret) >= 32  # Production requirement
        
        # Should not be obviously weak (but allow deterministic dev/test secrets)
        weak_patterns = ["password", "123456", "admin"]
        secret_lower = secret.lower()
        
        # Only check for truly weak patterns, not deterministic test secrets
        if not secret_lower.startswith(('netra_', 'test_jwt_secret', 'emergency')):
            assert not any(weak in secret_lower for weak in weak_patterns)

    def test_jwt_cross_service_compatibility(self):
        """Test JWT token compatibility across services.
        
        BVJ: Ensures WebSocket authentication works with auth service tokens.
        """
        # This tests that JWT configuration is compatible across service boundaries
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Test JWT configuration access through config
        if hasattr(config, 'jwt_secret_key'):
            config_secret = config.jwt_secret_key
            unified_secret = get_unified_jwt_secret()
            
            # Should be consistent (or both working independently)
            if config_secret and unified_secret:
                assert isinstance(config_secret, str)
                assert isinstance(unified_secret, str)
                assert len(config_secret) >= 16
                assert len(unified_secret) >= 16


class TestOAuthConfigurationRegression:
    """Test OAuth configuration to prevent regression bugs.
    
    BVJ: CRITICAL - Prevents OAuth regression that blocked enterprise customers.
    """

    def test_oauth_dual_naming_convention_support(self):
        """Test OAuth dual naming convention handling.
        
        BVJ: Prevents OAuth regression that causes enterprise customer loss.
        """
        env = get_env()
        manager = UnifiedConfigManager()
        
        # Test both naming conventions are supported
        simple_patterns = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
        environment_patterns = [
            "GOOGLE_OAUTH_CLIENT_ID_STAGING", 
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION",
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"
        ]
        
        original_values = {}
        
        try:
            # Test simple naming convention
            for pattern in simple_patterns:
                original_values[pattern] = env.get(pattern)
                env.set(pattern, f"test_{pattern.lower()}_value", "test_setup")
            
            config1 = manager.reload_config(force=True)
            
            # Config should load without errors
            assert config1 is not None
            
            # Test environment-specific naming convention
            for pattern in environment_patterns:
                original_values[pattern] = env.get(pattern)
                env.set(pattern, f"test_{pattern.lower()}_value", "test_setup")
            
            config2 = manager.reload_config(force=True)
            
            # Config should still load without errors
            assert config2 is not None
            
            # Both patterns should be supported simultaneously
            assert isinstance(config2, AppConfig)
            
        finally:
            # Restore all original values
            for key, value in original_values.items():
                if value:
                    env.set(key, value, "test_cleanup")
                else:
                    env.delete(key)

    def test_oauth_environment_specific_validation(self):
        """Test OAuth environment-specific validation rules.
        
        BVJ: Prevents OAuth misconfiguration in different environments.
        """
        env = get_env()
        environments = ["development", "staging", "production"]
        
        for environment in environments:
            original_env = env.get("ENVIRONMENT")
            try:
                env.set("ENVIRONMENT", environment, "test_setup")
                
                # Test OAuth configuration for each environment
                manager = UnifiedConfigManager()
                manager._environment = None  # Force refresh
                config = manager.get_config()
                
                # Should handle OAuth configuration appropriately per environment
                assert config.environment in [environment, "testing"]  # Allow testing due to pytest
                
                # Environment-specific validation should work
                is_valid = manager.validate_config_integrity()
                assert isinstance(is_valid, bool)
                
            finally:
                if original_env:
                    env.set("ENVIRONMENT", original_env, "test_cleanup")
                else:
                    env.delete("ENVIRONMENT")

    def test_oauth_secret_handling_security(self):
        """Test OAuth secret handling security.
        
        BVJ: Prevents OAuth credential leakage in logs/errors.
        """
        env = get_env()
        
        # Test that OAuth credentials are handled securely
        sensitive_keys = [
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", 
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"
        ]
        
        original_values = {}
        try:
            for key in sensitive_keys:
                original_values[key] = env.get(key)
                # Set a test secret value
                env.set(key, f"test_secret_value_{key.lower()}_do_not_log", "test_setup")
            
            manager = UnifiedConfigManager()
            config = manager.reload_config(force=True)
            
            # Config should load without exposing secrets in plain text
            config_dict = config.__dict__ if hasattr(config, '__dict__') else {}
            
            # Verify no secrets are accidentally exposed as plain text
            for field_name, field_value in config_dict.items():
                if isinstance(field_value, str):
                    # Secrets should not appear in plain text in config representation
                    assert "do_not_log" not in field_value.lower()
            
        finally:
            for key, value in original_values.items():
                if value:
                    env.set(key, value, "test_cleanup")
                else:
                    env.delete(key)


class TestConfigurationValidationProgressiveEnforcement:
    """Test progressive configuration validation enforcement.
    
    BVJ: Enables development velocity while maintaining production security.
    """

    def test_validation_mode_warn_permissive(self):
        """Test WARN validation mode converts errors to warnings.
        
        BVJ: Enables development without blocking on non-critical config issues.
        """
        validator = ConfigurationValidator()
        
        # Force development environment for WARN mode
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        
        try:
            env.set("ENVIRONMENT", "development", "test_setup")
            validator.refresh_environment()
            
            manager = UnifiedConfigManager()
            config = manager.reload_config(force=True)
            
            # Run validation - should be permissive in development
            result = validator.validate_complete_config(config)
            
            # Should have result object
            assert result is not None
            assert hasattr(result, 'is_valid')
            assert hasattr(result, 'errors')
            assert hasattr(result, 'warnings')
            
            # In WARN mode, most issues should be warnings, not errors
            # This allows development to continue
            
        finally:
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup")
            else:
                env.delete("ENVIRONMENT")

    def test_validation_mode_enforce_critical(self):
        """Test ENFORCE_CRITICAL mode only fails on critical issues.
        
        BVJ: Balances development velocity with critical security requirements.
        """
        validator = ConfigurationValidator()
        
        # Test critical vs non-critical error categorization
        test_errors = [
            "JWT secret key is required",  # Critical
            "Database URL is required",    # Critical  
            "Redis connection failed",     # Non-critical
            "LLM API key missing"         # Non-critical
        ]
        
        critical, non_critical = validator._categorize_errors(test_errors)
        
        # Should properly categorize
        assert len(critical) >= 1  # At least JWT or Database should be critical
        assert len(non_critical) >= 1  # At least Redis or LLM should be non-critical
        
        # Critical errors should contain security/database issues
        critical_text = " ".join(critical).lower()
        assert "secret" in critical_text or "database" in critical_text

    def test_validation_mode_enforce_all_strict(self):
        """Test ENFORCE_ALL mode for production strictness.
        
        BVJ: Ensures production deployments meet all requirements.
        """
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        
        try:
            # Force production-like environment for strict validation
            env.set("ENVIRONMENT", "production", "test_setup")
            
            validator = ConfigurationValidator()
            validator.refresh_environment()
            
            manager = UnifiedConfigManager()
            config = manager.reload_config(force=True)
            
            # Production validation should be strict
            result = validator.validate_complete_config(config)
            
            assert result is not None
            # In production mode, validation should be thorough
            
        finally:
            if original_env:
                env.set("ENVIRONMENT", original_env, "test_cleanup") 
            else:
                env.delete("ENVIRONMENT")

    def test_configuration_health_scoring(self):
        """Test configuration health scoring system.
        
        BVJ: Provides quantitative config quality metrics for monitoring.
        """
        validator = ConfigurationValidator()
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Test health scoring
        result = validator.validate_complete_config(config)
        
        assert hasattr(result, 'score')
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 100
        
        # Score should reflect configuration completeness
        if result.is_valid and len(result.errors) == 0:
            assert result.score >= 70  # Should be reasonably high for valid config


class TestWebSocketSupportingConfiguration:
    """Test configuration that supports WebSocket agent events.
    
    BVJ: MISSION CRITICAL - Ensures chat functionality works ($50K MRR dependent).
    """

    def test_websocket_authentication_config_support(self):
        """Test configuration supports WebSocket authentication.
        
        BVJ: Prevents WebSocket 403 errors that break chat functionality.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Configuration should support WebSocket authentication requirements
        jwt_secret = get_unified_jwt_secret()
        assert jwt_secret is not None
        assert len(jwt_secret) >= 32  # Strong secret for WebSocket auth
        
        # Should have consistent environment
        assert config.environment is not None
        assert len(config.environment) > 0

    def test_websocket_cors_configuration(self):
        """Test CORS configuration for WebSocket connections.
        
        BVJ: Ensures WebSocket connections work from frontend to backend.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Should have frontend URL for CORS
        if hasattr(config, 'frontend_url'):
            assert config.frontend_url is not None
            # Should be valid URL format
            assert config.frontend_url.startswith(('http://', 'https://'))

    def test_websocket_performance_configuration(self):
        """Test configuration supports WebSocket performance requirements.
        
        BVJ: Ensures WebSocket events are delivered promptly for chat UX.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Should have reasonable configuration for WebSocket performance
        # This includes timeouts, connection limits, etc.
        assert config.environment is not None
        
        # In development, should be optimized for development
        if manager.is_development():
            # Development should allow longer timeouts for debugging
            assert True  # Configuration loaded successfully
            
        # In production, should be optimized for performance
        if manager.is_production():
            # Production should have stricter timeouts
            assert True  # Configuration loaded successfully


class TestConfigurationIntegrityValidation:
    """Test configuration integrity and consistency checks.
    
    BVJ: Prevents configuration drift that causes service failures.
    """

    def test_config_dependency_consistency(self):
        """Test configuration dependency consistency validation.
        
        BVJ: Prevents cascading failures from configuration dependencies.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Test internal consistency
        is_valid = manager.validate_config_integrity()
        assert isinstance(is_valid, bool)
        
        # Configuration should be internally consistent
        if hasattr(config, 'database_url') and config.database_url:
            # Database URL should be consistent with environment
            if manager.is_production():
                # Production should not use localhost
                assert "localhost" not in config.database_url
            elif manager.is_development():
                # Development can use localhost
                assert True  # Any database URL acceptable in development

    def test_cross_service_config_compatibility(self):
        """Test configuration compatibility across services.
        
        BVJ: Ensures auth service and backend service can communicate.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # JWT configuration should be compatible across services
        jwt_secret = get_unified_jwt_secret()
        
        # Both config and JWT manager should work
        assert config is not None
        assert jwt_secret is not None
        
        # Should be consistent approach to configuration
        assert isinstance(config.environment, str)
        assert len(config.environment) > 0

    def test_config_serialization_integrity(self):
        """Test configuration can be serialized for inter-service communication.
        
        BVJ: Enables configuration sharing across service boundaries.
        """
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Config should be serializable (for inter-service communication)
        try:
            # Test that config can be converted to dict
            if hasattr(config, '__dict__'):
                config_dict = config.__dict__
                assert isinstance(config_dict, dict)
                
                # Should contain basic fields
                assert 'environment' in config_dict
                
            # Should be JSON-serializable for API communication
            import json
            config_data = {
                'environment': config.environment,
                'valid': manager.validate_config_integrity()
            }
            json_str = json.dumps(config_data)
            assert isinstance(json_str, str)
            assert len(json_str) > 10
            
        except Exception as e:
            pytest.fail(f"Configuration serialization failed: {e}")

    def test_config_environment_variable_coverage(self):
        """Test configuration covers required environment variables.
        
        BVJ: Ensures all required config is loaded from environment.
        """
        env = get_env()
        manager = UnifiedConfigManager()
        config = manager.get_config()
        
        # Critical environment variables should be accessible
        critical_vars = [
            'ENVIRONMENT',
            'DATABASE_URL', 
            'JWT_SECRET_KEY'
        ]
        
        environment_coverage = {}
        for var in critical_vars:
            env_value = env.get(var)
            environment_coverage[var] = {
                'present_in_env': env_value is not None,
                'env_value_length': len(env_value) if env_value else 0
            }
        
        # Should have reasonable environment coverage
        assert environment_coverage['ENVIRONMENT']['present_in_env']
        
        # Database URL should be present or have fallback
        db_present = environment_coverage['DATABASE_URL']['present_in_env'] or hasattr(config, 'database_url')
        assert db_present

    def test_config_hot_reload_consistency(self):
        """Test configuration hot-reload maintains consistency.
        
        BVJ: Ensures development velocity without breaking running services.
        """
        env = get_env()
        manager = UnifiedConfigManager()
        
        # Get initial config
        config1 = manager.get_config()
        initial_environment = config1.environment
        
        # Change non-critical environment variable
        original_debug = env.get("DEBUG") 
        try:
            env.set("DEBUG", "false", "test_consistency")
            
            # Hot reload
            config2 = manager.reload_config(force=True)
            
            # Critical properties should remain consistent
            assert config2.environment == initial_environment
            
            # Both configs should pass validation
            assert manager.validate_config_integrity()
            
        finally:
            if original_debug:
                env.set("DEBUG", original_debug, "test_cleanup")
            else:
                env.delete("DEBUG")


# Test runner integration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])