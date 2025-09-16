"""
Unit Tests for JWT Configuration Validation - JWT_SECRET to JWT_SECRET_KEY Migration

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Security & Configuration
- Business Goal: Ensure JWT configuration consistency across services
- Value Impact: Prevents authentication failures due to config mismatches
- Strategic Impact: JWT secrets are fundamental to platform security - inconsistent
  naming between JWT_SECRET and JWT_SECRET_KEY causes deployment failures

CRITICAL: This test reproduces the JWT_SECRET vs JWT_SECRET_KEY inconsistency
that causes authentication failures when services expect different variable names.

Test Categories:
- JWT Secret Key Loading & Validation
- Environment Variable Name Consistency
- Configuration Method Naming Validation
- Cross-Service Configuration Compatibility
- Error Handling for Missing/Invalid JWT Secrets

Expected Failures (Issue Reproduction):
- Tests should FAIL initially to demonstrate the JWT_SECRET vs JWT_SECRET_KEY issue
- Tests validate that auth service expects JWT_SECRET_KEY but may receive JWT_SECRET
- Tests ensure proper error messages when configuration is inconsistent
"""
import pytest
import warnings
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from auth_service.auth_core.config import AuthConfig, get_config
from auth_service.auth_core.auth_environment import get_auth_env


class JWTConfigValidationTests(SSotBaseTestCase):
    """Test JWT configuration validation and consistency."""
    
    def setUp(self):
        """Set up test environment with clean state."""
        super().setUp()
        self.env = get_env()
        # Clear any existing JWT variables to test clean state
        self.env.delete("JWT_SECRET", "test_setup")
        self.env.delete("JWT_SECRET_KEY", "test_setup")
        
    def test_jwt_secret_key_required_in_production(self):
        """
        Test that JWT_SECRET_KEY is required in production environment.
        
        This test should FAIL if the system incorrectly accepts JWT_SECRET
        instead of JWT_SECRET_KEY in production.
        """
        # Set production environment
        self.env.set("ENVIRONMENT", "production", "test")
        
        # Set ONLY JWT_SECRET (not JWT_SECRET_KEY) to test migration issue
        self.env.set("JWT_SECRET", "production-jwt-secret-32-characters-minimum", "test")
        
        # Attempt to get JWT secret - should fail if expecting JWT_SECRET_KEY
        config = AuthConfig()
        
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be explicitly set"):
            # This should fail because system expects JWT_SECRET_KEY, not JWT_SECRET
            config.get_jwt_secret()
            
    def test_jwt_secret_vs_jwt_secret_key_inconsistency(self):
        """
        Test that demonstrates JWT_SECRET vs JWT_SECRET_KEY inconsistency.
        
        This test should FAIL to demonstrate the configuration naming issue.
        """
        # Set staging environment (strict like production)
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Set BOTH variables with different values to show the conflict
        self.env.set("JWT_SECRET", "jwt-secret-value-32-characters-long", "test")
        self.env.set("JWT_SECRET_KEY", "jwt-secret-key-value-32-characters", "test")
        
        # Get config instances
        config = AuthConfig()
        auth_env = get_auth_env()
        
        # Test that they use consistent variable names
        try:
            config_secret = config.get_jwt_secret()
            auth_env_secret = auth_env.get_jwt_secret_key()
            
            # These should be the same value if using consistent variable names
            assert config_secret == auth_env_secret, (
                f"JWT secret mismatch: AuthConfig='{config_secret}' vs "
                f"AuthEnvironment='{auth_env_secret}'. This indicates JWT_SECRET vs "
                f"JWT_SECRET_KEY inconsistency."
            )
        except Exception as e:
            pytest.fail(f"JWT configuration method inconsistency: {e}")
            
    def test_jwt_config_method_naming_consistency(self):
        """
        Test that all JWT-related methods use consistent naming patterns.
        
        This test should FAIL if method names are inconsistent between
        AuthConfig and AuthEnvironment.
        """
        # Set valid test environment
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters", "test")
        
        config = AuthConfig()
        auth_env = get_auth_env()
        
        # Test method existence and naming consistency
        assert hasattr(config, 'get_jwt_secret'), "AuthConfig missing get_jwt_secret method"
        assert hasattr(auth_env, 'get_jwt_secret_key'), "AuthEnvironment missing get_jwt_secret_key method"
        
        # Test that both methods work without errors
        try:
            config_secret = config.get_jwt_secret()
            auth_env_secret = auth_env.get_jwt_secret_key()
            
            # Both should return valid secrets
            assert config_secret, "AuthConfig.get_jwt_secret() returned empty value"
            assert auth_env_secret, "AuthEnvironment.get_jwt_secret_key() returned empty value"
            
            # They should be the same value (both reading JWT_SECRET_KEY)
            assert config_secret == auth_env_secret, (
                f"Method naming inconsistency: get_jwt_secret()='{config_secret}' vs "
                f"get_jwt_secret_key()='{auth_env_secret}'"
            )
            
        except Exception as e:
            pytest.fail(f"JWT method naming inconsistency error: {e}")
            
    def test_missing_jwt_secret_key_error_handling(self):
        """
        Test proper error handling when JWT_SECRET_KEY is missing.
        
        This test validates that clear error messages are provided for
        missing JWT configuration.
        """
        # Set production environment where JWT_SECRET_KEY is required
        self.env.set("ENVIRONMENT", "production", "test")
        
        # Ensure no JWT variables are set
        self.env.delete("JWT_SECRET", "test")
        self.env.delete("JWT_SECRET_KEY", "test")
        
        config = AuthConfig()
        
        # Test that appropriate error is raised for missing JWT_SECRET_KEY
        with pytest.raises(ValueError) as exc_info:
            config.get_jwt_secret()
            
        error_message = str(exc_info.value)
        
        # Validate error message mentions JWT_SECRET_KEY specifically
        assert "JWT_SECRET_KEY" in error_message, (
            f"Error message should mention JWT_SECRET_KEY specifically, got: {error_message}"
        )
        assert "production" in error_message.lower(), (
            f"Error message should mention production environment, got: {error_message}"
        )
        
    def test_development_environment_jwt_flexibility(self):
        """
        Test that development environment allows JWT flexibility.
        
        This test ensures development/test environments are more permissive
        while production/staging remain strict.
        """
        # Set development environment
        self.env.set("ENVIRONMENT", "development", "test")
        
        # Test with minimal JWT secret (should be allowed in dev)
        self.env.set("JWT_SECRET_KEY", "dev-secret", "test")
        
        config = AuthConfig()
        
        try:
            secret = config.get_jwt_secret()
            assert secret == "dev-secret", f"Expected 'dev-secret', got '{secret}'"
        except Exception as e:
            pytest.fail(f"Development environment should allow flexible JWT config: {e}")
            
    def test_staging_environment_strict_jwt_validation(self):
        """
        Test that staging environment enforces strict JWT validation.
        
        This test ensures staging behaves like production for JWT secrets.
        """
        # Set staging environment
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Test that JWT_SECRET_KEY is required (not JWT_SECRET)
        self.env.delete("JWT_SECRET_KEY", "test")
        self.env.set("JWT_SECRET", "staging-jwt-secret-32-characters-long", "test")
        
        config = AuthConfig()
        
        # Should fail because staging should require JWT_SECRET_KEY
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be explicitly set"):
            config.get_jwt_secret()


class JWTCrossServiceValidationTests(SSotBaseTestCase):
    """Test JWT configuration consistency across service boundaries."""
    
    def setUp(self):
        """Set up test environment for cross-service validation."""
        super().setUp()
        self.env = get_env()
        # Clean slate for cross-service tests
        self.env.delete("JWT_SECRET", "test_setup")
        self.env.delete("JWT_SECRET_KEY", "test_setup")
        
    def test_auth_config_to_auth_environment_consistency(self):
        """
        Test that AuthConfig and AuthEnvironment use same JWT variable.
        
        This test should FAIL if there's inconsistency in variable names
        between AuthConfig.get_jwt_secret() and AuthEnvironment.get_jwt_secret_key().
        """
        # Set test environment with valid JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters", "test")
        
        # Create instances
        config = AuthConfig()
        auth_env = get_auth_env()
        
        # Both should read from the same environment variable
        config_secret = config.get_jwt_secret()
        auth_env_secret = auth_env.get_jwt_secret_key()
        
        # Critical assertion: Both should return the same value
        assert config_secret == auth_env_secret, (
            f"CRITICAL: JWT configuration inconsistency detected!\n"
            f"AuthConfig.get_jwt_secret() = '{config_secret}'\n"
            f"AuthEnvironment.get_jwt_secret_key() = '{auth_env_secret}'\n"
            f"This indicates JWT_SECRET vs JWT_SECRET_KEY variable naming inconsistency."
        )
        
    def test_jwt_variable_name_standardization(self):
        """
        Test that all components use JWT_SECRET_KEY as the standard variable name.
        
        This test ensures migration from JWT_SECRET to JWT_SECRET_KEY is complete.
        """
        # Set test environment
        self.env.set("ENVIRONMENT", "test", "test")
        
        # Set ONLY JWT_SECRET_KEY (the new standard)
        self.env.set("JWT_SECRET_KEY", "standardized-jwt-secret-key-32-chars", "test")
        
        # Ensure old JWT_SECRET is not set
        self.env.delete("JWT_SECRET", "test")
        
        # Test that all config methods work with JWT_SECRET_KEY only
        config = AuthConfig()
        auth_env = get_auth_env()
        
        try:
            # Both should successfully read from JWT_SECRET_KEY
            config_secret = config.get_jwt_secret()
            auth_env_secret = auth_env.get_jwt_secret_key()
            
            expected_value = "standardized-jwt-secret-key-32-chars"
            
            assert config_secret == expected_value, (
                f"AuthConfig should read from JWT_SECRET_KEY, got: {config_secret}"
            )
            assert auth_env_secret == expected_value, (
                f"AuthEnvironment should read from JWT_SECRET_KEY, got: {auth_env_secret}"
            )
            
        except Exception as e:
            pytest.fail(f"JWT_SECRET_KEY standardization failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])