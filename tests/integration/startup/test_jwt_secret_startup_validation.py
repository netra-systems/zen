"""
Test JWT Secret Startup Validation - Cross-Service JWT Configuration During System Startup

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Startup Security
- Business Goal: Ensure JWT authentication is properly configured during system initialization
- Value Impact: Prevents authentication failures that block all user access during startup
- Strategic Impact: JWT configuration is foundational to platform security and user access

CRITICAL: This test validates JWT configuration consistency during system startup phases.
System startup must properly initialize JWT secrets across all services before accepting user requests.

Test Categories:
- JWT Configuration During Startup Phases
- Cross-Service JWT Secret Validation at Startup
- Startup Failure Detection for JWT Misconfigurations
- Environment-Specific JWT Validation During Init
- Service Discovery and JWT Integration at Startup

Expected Failures (Issue Reproduction):
- Tests should FAIL if JWT_SECRET vs JWT_SECRET_KEY inconsistency exists during startup
- Tests validate that startup properly detects JWT configuration issues
- Tests ensure all services initialize with consistent JWT configuration
"""
import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env
from shared.isolated_environment import get_env
from netra_backend.app.smd import StartupOrchestrator, StartupPhase, DeterministicStartupError
from fastapi import FastAPI


class JWTSecretStartupValidationTests(SSotAsyncTestCase):
    """Test JWT secret validation during system startup phases."""
    
    async def asyncSetUp(self):
        """Set up test environment for startup JWT validation."""
        await super().asyncSetUp()
        self.env = get_env()
        self.app = FastAPI()
        self.startup_orchestrator: Optional[StartupOrchestrator] = None
        
        # Clear JWT variables for clean testing
        self.env.delete("JWT_SECRET", "test_setup")
        self.env.delete("JWT_SECRET_KEY", "test_setup")
        
    async def asyncTearDown(self):
        """Clean up startup test resources."""
        if self.startup_orchestrator:
            try:
                await self.startup_orchestrator.shutdown()
            except Exception:
                pass  # Ignore cleanup errors
        await super().asyncTearDown()
        
    async def test_startup_jwt_secret_key_required_configuration(self):
        """
        Test that system startup requires JWT_SECRET_KEY configuration.
        
        This test should FAIL if startup incorrectly accepts JWT_SECRET
        instead of the standard JWT_SECRET_KEY.
        """
        # Set test environment with ONLY JWT_SECRET (not JWT_SECRET_KEY)
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET", "startup-jwt-secret-should-not-work", "test")
        self.env.delete("JWT_SECRET_KEY", "test")
        
        # Additional required startup configuration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        self.env.set("REDIS_URL", "redis://localhost:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://user:pass@localhost:5432/test", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        # Startup should fail if JWT_SECRET_KEY is not properly configured
        with pytest.raises((DeterministicStartupError, ValueError, KeyError)) as exc_info:
            await self.startup_orchestrator.initialize_system()
            
        error_message = str(exc_info.value)
        
        # Error should specifically mention JWT_SECRET_KEY requirement
        assert any(keyword in error_message for keyword in ["JWT_SECRET_KEY", "jwt", "authentication"]), (
            f"Startup should fail with JWT_SECRET_KEY requirement error, got: {error_message}"
        )
        
    async def test_startup_jwt_configuration_validation_success(self):
        """
        Test that system startup succeeds with proper JWT_SECRET_KEY configuration.
        
        This validates that startup properly recognizes correct JWT configuration.
        """
        # Set proper test environment with JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "startup-test-jwt-secret-key-32-chars", "test")
        
        # Required startup configuration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        self.env.set("REDIS_URL", "redis://localhost:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://user:pass@localhost:5432/test", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        try:
            # Startup should succeed with proper JWT_SECRET_KEY
            await self.startup_orchestrator.initialize_system()
            
            # Validate that JWT configuration was properly loaded
            from netra_backend.app.config import get_config
            config = get_config()
            
            jwt_secret = config.JWT_SECRET_KEY
            assert jwt_secret == "startup-test-jwt-secret-key-32-chars", (
                f"Startup failed to load correct JWT_SECRET_KEY: got '{jwt_secret}'"
            )
            
        except Exception as e:
            pytest.fail(f"Startup should succeed with proper JWT_SECRET_KEY configuration: {e}")
            
    async def test_startup_production_jwt_secret_key_enforcement(self):
        """
        Test that startup enforces strict JWT_SECRET_KEY validation in production.
        
        This test ensures production startup fails without proper JWT configuration.
        """
        # Set production environment without JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "production", "test")
        self.env.delete("JWT_SECRET_KEY", "test")
        self.env.delete("JWT_SECRET", "test")
        
        # Required production configuration
        self.env.set("AUTH_SERVICE_URL", "https://auth.production.com", "test")
        self.env.set("REDIS_URL", "redis://prod-redis:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://prod-user:pass@prod-db:5432/prod", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        # Production startup should fail without JWT_SECRET_KEY
        with pytest.raises((DeterministicStartupError, ValueError)) as exc_info:
            await self.startup_orchestrator.initialize_system()
            
        error_message = str(exc_info.value)
        
        # Error should mention production JWT requirements
        assert any(keyword in error_message.lower() for keyword in ["jwt_secret_key", "production", "required"]), (
            f"Production startup should fail with JWT_SECRET_KEY requirement error, got: {error_message}"
        )
        
    async def test_startup_staging_jwt_secret_key_enforcement(self):
        """
        Test that startup enforces strict JWT_SECRET_KEY validation in staging.
        
        This test ensures staging behaves like production for JWT validation.
        """
        # Set staging environment with only JWT_SECRET (should fail)
        self.env.set("ENVIRONMENT", "staging", "test")
        self.env.set("JWT_SECRET", "staging-jwt-secret-incorrect-var-name", "test")
        self.env.delete("JWT_SECRET_KEY", "test")
        
        # Required staging configuration
        self.env.set("AUTH_SERVICE_URL", "https://auth.staging.com", "test")
        self.env.set("REDIS_URL", "redis://staging-redis:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://staging-user:pass@staging-db:5432/staging", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        # Staging startup should fail with JWT_SECRET instead of JWT_SECRET_KEY
        with pytest.raises((DeterministicStartupError, ValueError)) as exc_info:
            await self.startup_orchestrator.initialize_system()
            
        error_message = str(exc_info.value)
        
        # Error should indicate JWT_SECRET_KEY requirement in staging
        assert "JWT_SECRET_KEY" in error_message or "jwt" in error_message.lower(), (
            f"Staging startup should fail with JWT_SECRET_KEY requirement error, got: {error_message}"
        )


class StartupJWTCrossServiceValidationTests(SSotAsyncTestCase):
    """Test JWT configuration validation across services during startup."""
    
    async def asyncSetUp(self):
        """Set up cross-service startup validation tests."""
        await super().asyncSetUp()
        self.env = get_env()
        self.app = FastAPI()
        self.startup_orchestrator: Optional[StartupOrchestrator] = None
        
        # Clear JWT variables for clean cross-service testing
        self.env.delete("JWT_SECRET", "test_setup")
        self.env.delete("JWT_SECRET_KEY", "test_setup")
        
    async def asyncTearDown(self):
        """Clean up cross-service test resources."""
        if self.startup_orchestrator:
            try:
                await self.startup_orchestrator.shutdown()
            except Exception:
                pass
        await super().asyncTearDown()
        
    async def test_startup_cross_service_jwt_consistency_validation(self):
        """
        Test that startup validates JWT consistency across all services.
        
        This test should FAIL if there are JWT configuration inconsistencies
        between backend, auth service, and other components during startup.
        """
        # Set test environment with proper JWT_SECRET_KEY
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "cross-service-startup-jwt-secret-32", "test")
        
        # Required cross-service configuration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        self.env.set("BACKEND_URL", "http://localhost:8000", "test")
        self.env.set("REDIS_URL", "redis://localhost:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://user:pass@localhost:5432/test", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        try:
            # Startup should succeed with consistent JWT configuration
            await self.startup_orchestrator.initialize_system()
            
            # Validate that all services can access consistent JWT configuration
            from netra_backend.app.config import get_config
            backend_config = get_config()
            
            # Backend should have correct JWT_SECRET_KEY
            backend_jwt_secret = backend_config.JWT_SECRET_KEY
            assert backend_jwt_secret == "cross-service-startup-jwt-secret-32", (
                f"Backend JWT configuration inconsistent during startup: got '{backend_jwt_secret}'"
            )
            
            # Test auth service integration
            from netra_backend.app.auth_integration.auth import AuthService
            auth_service = AuthService()
            assert auth_service is not None, "AuthService failed to initialize during startup"
            
        except Exception as e:
            pytest.fail(f"Cross-service JWT startup validation failed: {e}")
            
    async def test_startup_jwt_variable_name_standardization_validation(self):
        """
        Test that startup validates JWT variable name standardization across services.
        
        This ensures that the migration from JWT_SECRET to JWT_SECRET_KEY is
        properly validated during system initialization.
        """
        # Set test environment with ONLY JWT_SECRET_KEY (standardized)
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET_KEY", "standardized-startup-jwt-secret-key", "test")
        
        # Ensure old JWT_SECRET is not set (test migration completion)
        self.env.delete("JWT_SECRET", "test")
        
        # Required startup configuration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        self.env.set("REDIS_URL", "redis://localhost:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://user:pass@localhost:5432/test", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        try:
            # Startup should succeed with standardized JWT_SECRET_KEY
            await self.startup_orchestrator.initialize_system()
            
            # Validate standardization compliance
            from netra_backend.app.config import get_config
            config = get_config()
            
            # Should use JWT_SECRET_KEY (standardized)
            jwt_secret = config.JWT_SECRET_KEY
            assert jwt_secret == "standardized-startup-jwt-secret-key", (
                f"Startup failed JWT variable standardization: got '{jwt_secret}'"
            )
            
            # Should NOT have JWT_SECRET property (migration complete)
            assert not hasattr(config, 'JWT_SECRET'), (
                "Startup should not expose JWT_SECRET after standardization migration"
            )
            
        except Exception as e:
            pytest.fail(f"JWT variable standardization validation failed during startup: {e}")
            
    async def test_startup_jwt_configuration_error_propagation(self):
        """
        Test that JWT configuration errors are properly propagated during startup.
        
        This validates that startup provides clear error messages for JWT issues.
        """
        # Set test environment with conflicting JWT variables
        self.env.set("ENVIRONMENT", "test", "test")
        self.env.set("JWT_SECRET", "old-jwt-secret-value", "test")
        self.env.set("JWT_SECRET_KEY", "new-jwt-secret-key-value", "test")
        
        # Required startup configuration
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")
        self.env.set("REDIS_URL", "redis://localhost:6379", "test")
        self.env.set("DATABASE_URL", "postgresql://user:pass@localhost:5432/test", "test")
        
        self.startup_orchestrator = StartupOrchestrator(self.app)
        
        try:
            # Startup should succeed using JWT_SECRET_KEY (takes precedence)
            await self.startup_orchestrator.initialize_system()
            
            # Validate that JWT_SECRET_KEY takes precedence
            from netra_backend.app.config import get_config
            config = get_config()
            
            jwt_secret = config.JWT_SECRET_KEY
            assert jwt_secret == "new-jwt-secret-key-value", (
                f"Startup should use JWT_SECRET_KEY when both variables present: got '{jwt_secret}'"
            )
            
        except Exception as e:
            # If startup fails, error should be clear about JWT configuration
            error_message = str(e)
            assert any(keyword in error_message for keyword in ["JWT_SECRET_KEY", "JWT_SECRET", "jwt"]), (
                f"JWT configuration error should be clearly propagated, got: {error_message}"
            )
            pytest.fail(f"Startup failed with JWT configuration conflict: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])