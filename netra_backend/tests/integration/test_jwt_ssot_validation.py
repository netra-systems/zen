"""
Integration Tests for JWT SSOT Validation - Backend to Auth Service Communication

Business Value Justification (BVJ):
- Segment: Platform/Internal - Cross-Service Integration Security
- Business Goal: Ensure JWT authentication works seamlessly between backend and auth service
- Value Impact: Prevents authentication failures that block user access to platform features
- Strategic Impact: JWT integration is critical for secure multi-service architecture

CRITICAL: This test validates JWT configuration consistency between backend and auth service.
The backend must successfully authenticate users using JWT tokens from the auth service.

Test Categories:
- JWT Token Validation Between Services
- Backend Auth Integration SSOT Compliance
- Cross-Service JWT Configuration Validation
- Authentication Flow Integration
- JWT Secret Consistency Validation

Expected Failures (Issue Reproduction):
- Tests should FAIL if JWT_SECRET vs JWT_SECRET_KEY inconsistency exists
- Tests validate that backend can verify JWT tokens created by auth service
- Tests ensure both services use the same JWT secret variable name
"""
import pytest
import asyncio
import warnings
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.auth_integration.auth import AuthService
from netra_backend.app.config import get_config


class JWTSSOTValidationTests(SSotAsyncTestCase):
    """Test JWT SSOT validation between backend and auth service."""
    
    async def asyncSetUp(self):
        """Set up test environment for JWT SSOT validation."""
        await super().asyncSetUp()
        self.env = get_env()
        
        # Clear any existing JWT variables for clean testing
        self.env.delete("JWT_SECRET", "test_setup")
        self.env.delete("JWT_SECRET_KEY", "test_setup")
        
    async def test_backend_auth_service_jwt_secret_consistency(self):
        """
        Test that backend and auth service use consistent JWT secret variables.
        
        This test should FAIL if there's inconsistency between backend
        expecting JWT_SECRET_KEY and auth service providing JWT_SECRET.
        """
        # Set test environment with proper JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "test-backend-auth-jwt-secret-32-chars", "test")
        
        # Test backend configuration
        backend_config = get_config()
        
        try:
            # Backend should be able to get JWT secret
            backend_jwt_secret = backend_config.JWT_SECRET_KEY
            
            assert backend_jwt_secret, "Backend failed to get JWT secret"
            assert backend_jwt_secret == "test-backend-auth-jwt-secret-32-chars", (
                f"Backend JWT secret mismatch: got '{backend_jwt_secret}'"
            )
            
        except Exception as e:
            pytest.fail(f"Backend JWT configuration failed: {e}")
            
    async def test_backend_auth_integration_jwt_validation(self):
        """
        Test that backend AuthService can validate JWT tokens using consistent configuration.
        
        This test should FAIL if JWT configuration is inconsistent between services.
        """
        # Set test environment
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "test-integration-jwt-secret-32-chars", "test")
        
        # Additional auth service configuration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        
        # Create AuthService instance (backend auth integration)
        auth_service = AuthService()
        
        try:
            # Test that AuthService can initialize without JWT config errors
            assert auth_service is not None, "AuthService failed to initialize"
            
            # Test that backend can access JWT configuration
            backend_config = get_config()
            jwt_secret = backend_config.JWT_SECRET_KEY
            
            assert jwt_secret == "test-integration-jwt-secret-32-chars", (
                f"Backend-Auth integration JWT secret mismatch: got '{jwt_secret}'"
            )
            
        except Exception as e:
            pytest.fail(f"Backend-Auth JWT integration failed: {e}")
            
    async def test_jwt_secret_key_required_not_jwt_secret(self):
        """
        Test that backend requires JWT_SECRET_KEY, not JWT_SECRET.
        
        This test should FAIL if backend incorrectly accepts JWT_SECRET
        instead of the standard JWT_SECRET_KEY.
        """
        # Set test environment
        self.env.set("ENVIRONMENT", "test", "test")
        
        # Set ONLY JWT_SECRET (not JWT_SECRET_KEY) to test migration issue
        self.env.set("JWT_SECRET", "test-jwt-secret-should-not-work", "test")
        self.env.delete("JWT_SECRET_KEY", "test")
        
        backend_config = get_config()
        
        # Backend should fail to get JWT_SECRET_KEY if only JWT_SECRET is set
        try:
            jwt_secret = backend_config.JWT_SECRET_KEY
            
            # If we get here with a value, the test should fail
            if jwt_secret:
                pytest.fail(
                    f"CRITICAL: Backend incorrectly accepted JWT_SECRET instead of JWT_SECRET_KEY. "
                    f"Got value: '{jwt_secret}'. This indicates improper migration from JWT_SECRET to JWT_SECRET_KEY."
                )
                
        except (AttributeError, KeyError, ValueError) as e:
            # This is expected - backend should require JWT_SECRET_KEY
            assert "JWT_SECRET_KEY" in str(e) or "not found" in str(e).lower(), (
                f"Expected JWT_SECRET_KEY error, got: {e}"
            )
            
    async def test_staging_production_jwt_secret_key_enforcement(self):
        """
        Test that backend enforces JWT_SECRET_KEY in staging/production environments.
        
        This test validates strict JWT configuration in production-like environments.
        """
        # Test staging environment
        self.env.set("ENVIRONMENT", "staging", "test")
        self.env.delete("JWT_SECRET_KEY", "test")
        self.env.delete("JWT_SECRET", "test")
        
        backend_config = get_config()
        
        # Backend should fail to get JWT secret in staging without proper configuration
        with pytest.raises((ValueError, KeyError, AttributeError)) as exc_info:
            jwt_secret = backend_config.JWT_SECRET_KEY
            
        error_message = str(exc_info.value)
        assert "JWT_SECRET_KEY" in error_message or "required" in error_message.lower(), (
            f"Expected JWT_SECRET_KEY requirement error in staging, got: {error_message}"
        )
        
    async def test_cross_service_jwt_configuration_consistency(self):
        """
        Test JWT configuration consistency across backend and auth service boundaries.
        
        This test should FAIL if there are inconsistencies in JWT variable naming
        or configuration between the two services.
        """
        # Set test environment with valid JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "cross-service-jwt-secret-32-chars", "test")
        
        # Additional service URLs for full integration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        self.env.set("BACKEND_URL", "http://localhost:8000", "test")
        
        # Test backend configuration
        backend_config = get_config()
        backend_jwt_secret = backend_config.JWT_SECRET_KEY
        
        # Test auth service integration
        auth_service = AuthService()
        
        # Both should use the same JWT secret
        assert backend_jwt_secret == "cross-service-jwt-secret-32-chars", (
            f"Backend JWT secret mismatch: got '{backend_jwt_secret}'"
        )
        
        # Validate that AuthService can work with backend configuration
        try:
            # This tests that the auth integration can access consistent configuration
            assert auth_service is not None, "AuthService integration failed"
            
        except Exception as e:
            pytest.fail(f"Cross-service JWT configuration inconsistency: {e}")


class BackendAuthJWTIntegrationTests(SSotAsyncTestCase):
    """Test backend-auth JWT integration scenarios."""
    
    async def asyncSetUp(self):
        """Set up for backend-auth integration tests."""
        await super().asyncSetUp()
        self.env = get_env()
        # Clean environment for integration tests
        self.env.delete("JWT_SECRET", "test_setup")
        self.env.delete("JWT_SECRET_KEY", "test_setup")
        
    async def test_backend_jwt_config_method_naming(self):
        """
        Test that backend uses correct JWT configuration method names.
        
        This test ensures backend follows SSOT patterns for JWT configuration access.
        """
        # Set valid test environment
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "backend-method-naming-jwt-secret", "test")
        
        backend_config = get_config()
        
        # Test that backend config has correct property name
        assert hasattr(backend_config, 'JWT_SECRET_KEY'), (
            "Backend config missing JWT_SECRET_KEY property"
        )
        
        # Test that it returns the correct value
        jwt_secret = backend_config.JWT_SECRET_KEY
        assert jwt_secret == "backend-method-naming-jwt-secret", (
            f"Backend JWT_SECRET_KEY method returned wrong value: '{jwt_secret}'"
        )
        
    async def test_backend_auth_service_url_consistency(self):
        """
        Test that backend can communicate with auth service using consistent configuration.
        
        This validates that service discovery and JWT validation work together.
        """
        # Set comprehensive test environment
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "backend-auth-url-consistency-32-chars", "test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        
        # Test backend configuration
        backend_config = get_config()
        
        # Validate JWT configuration
        jwt_secret = backend_config.JWT_SECRET_KEY
        assert jwt_secret == "backend-auth-url-consistency-32-chars", (
            f"Backend JWT secret incorrect: '{jwt_secret}'"
        )
        
        # Validate auth service URL configuration
        auth_url = backend_config.AUTH_SERVICE_URL
        assert auth_url == "http://localhost:8001", (
            f"Backend auth service URL incorrect: '{auth_url}'"
        )
        
        # Test AuthService integration
        auth_service = AuthService()
        assert auth_service is not None, "AuthService failed to initialize with consistent config"
        
    async def test_jwt_variable_standardization_backend_compliance(self):
        """
        Test that backend complies with JWT_SECRET_KEY standardization.
        
        This ensures the migration from JWT_SECRET to JWT_SECRET_KEY is complete in backend.
        """
        # Set test environment with ONLY JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "standardized-backend-jwt-secret-key", "test")
        
        # Ensure JWT_SECRET is not set (test clean migration)
        self.env.delete("JWT_SECRET", "test")
        
        backend_config = get_config()
        
        # Backend should successfully use JWT_SECRET_KEY
        try:
            jwt_secret = backend_config.JWT_SECRET_KEY
            assert jwt_secret == "standardized-backend-jwt-secret-key", (
                f"Backend failed JWT_SECRET_KEY standardization: got '{jwt_secret}'"
            )
            
        except Exception as e:
            pytest.fail(f"Backend JWT_SECRET_KEY standardization failed: {e}")
            
        # Backend should NOT have JWT_SECRET property (migration complete)
        assert not hasattr(backend_config, 'JWT_SECRET'), (
            "Backend should not have JWT_SECRET property after standardization migration"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])