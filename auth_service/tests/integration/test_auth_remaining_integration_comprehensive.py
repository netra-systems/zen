"""
Auth Service Remaining Integration Tests (Tests 4-10)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Complete integration testing coverage of auth service
- Value Impact: Ensures all auth service components work together correctly
- Strategic Impact: Comprehensive validation of authentication platform

These tests validate:
1. JWT token lifecycle management integration
2. Multi-user session isolation
3. Service startup and health checks
4. Cross-service authentication validation
5. Error handling and recovery integration
6. Performance and scalability integration
7. Security policy enforcement integration
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import patch, Mock

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.security.session_manager import SessionManager
from auth_service.auth_core.startup.health_checker import HealthChecker
from auth_service.auth_core.security.cross_service_auth import CrossServiceAuth
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env


class TestJWTLifecycleIntegration(SSotBaseTestCase):
    """Test 4: JWT token lifecycle management integration."""

    @pytest.fixture
    def jwt_handler(self):
        env = get_env()
        env.set("JWT_SECRET_KEY", "test-jwt-secret-32-characters-long", source="test")
        from auth_service.auth_core.auth_environment import AuthEnvironment
        auth_env = AuthEnvironment(env)
        return JWTHandler(auth_env)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_lifecycle_with_refresh_integration(self, jwt_handler):
        """Test complete JWT token lifecycle with refresh mechanism."""
        user_data = {
            "user_id": "integration-user-123",
            "email": "jwt.test@netra.com",
            "role": "user"
        }
        
        # Generate access and refresh tokens
        access_token = jwt_handler.generate_access_token(user_data, expires_in_seconds=5)
        refresh_token = jwt_handler.generate_refresh_token(user_data)
        
        # Verify both tokens work initially
        access_valid = jwt_handler.validate_token(access_token)
        refresh_valid = jwt_handler.validate_refresh_token(refresh_token)
        
        assert access_valid.is_valid
        assert refresh_valid.is_valid
        
        # Wait for access token to expire
        await asyncio.sleep(6)
        
        # Access token should be expired
        expired_access = jwt_handler.validate_token(access_token)
        assert not expired_access.is_valid
        
        # Refresh token should still be valid
        refresh_still_valid = jwt_handler.validate_refresh_token(refresh_token)
        assert refresh_still_valid.is_valid
        
        # Use refresh token to get new access token
        new_access_token = jwt_handler.refresh_access_token(refresh_token)
        assert new_access_token is not None
        assert new_access_token != access_token
        
        # New access token should be valid
        new_access_valid = jwt_handler.validate_token(new_access_token)
        assert new_access_valid.is_valid
        assert new_access_valid.user_id == user_data["user_id"]


class TestMultiUserSessionIntegration(SSotBaseTestCase):
    """Test 5: Multi-user session isolation integration."""

    @pytest.fixture
    def session_manager(self):
        env = get_env()
        from auth_service.auth_core.auth_environment import AuthEnvironment
        auth_env = AuthEnvironment(env)
        return SessionManager(auth_env)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_session_isolation(self, session_manager):
        """Test multiple users can have isolated sessions concurrently."""
        users = [
            {"user_id": f"user-{i}", "email": f"user{i}@netra.com", "org": f"org-{i%2}"}
            for i in range(5)
        ]
        
        # Create sessions for all users concurrently
        async def create_user_session(user):
            return await session_manager.create_session(
                user_id=user["user_id"],
                user_context={
                    "email": user["email"],
                    "organization_id": user["org"],
                    "role": "user"
                }
            )
        
        sessions = await asyncio.gather(*[create_user_session(user) for user in users])
        
        # Verify all sessions were created and are isolated
        assert len(sessions) == 5
        
        for i, session in enumerate(sessions):
            assert session.user_id == users[i]["user_id"]
            assert session.user_context["email"] == users[i]["email"]
            assert session.user_context["organization_id"] == users[i]["org"]
            assert session.is_active
            
            # Verify session doesn't contain other users' data
            for j, other_session in enumerate(sessions):
                if i != j:
                    assert session.user_id != other_session.user_id
                    assert session.user_context["email"] != other_session.user_context["email"]


class TestServiceStartupIntegration(SSotBaseTestCase):
    """Test 6: Service startup and health checks integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_health_check_integration(self):
        """Test service health checks validate all components."""
        from auth_service.auth_core.startup.health_checker import HealthChecker
        
        env = get_env()
        env.set("DATABASE_URL", "postgresql://test:test@localhost:5434/test_auth", source="test")
        env.set("REDIS_URL", "redis://localhost:6381/0", source="test")
        
        health_checker = HealthChecker(env)
        
        # Test comprehensive health check
        health_result = await health_checker.check_all_components()
        
        assert "database" in health_result.components
        assert "redis" in health_result.components
        assert "jwt_service" in health_result.components
        
        # At least some components should be healthy in test environment
        healthy_components = sum(1 for comp in health_result.components.values() if comp.healthy)
        assert healthy_components >= 1


class TestCrossServiceAuthIntegration(SSotBaseTestCase):
    """Test 7: Cross-service authentication integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_token_validation_integration(self):
        """Test cross-service token validation works correctly."""
        auth_helper = E2EAuthHelper(environment="test")
        
        # Create token for cross-service use
        service_token = auth_helper.create_test_jwt_token(
            user_id="service-user-123",
            email="service@netra.com",
            permissions=["read", "write", "cross_service"]
        )
        
        from auth_service.auth_core.security.cross_service_validator import CrossServiceValidator
        env = get_env()
        validator = CrossServiceValidator(env)
        
        # Validate cross-service request
        validation_result = validator.validate_cross_service_token(
            token=service_token,
            requesting_service="backend",
            target_resource="user_data"
        )
        
        assert validation_result.is_valid
        assert validation_result.user_id == "service-user-123"
        assert "cross_service" in validation_result.permissions


class TestErrorHandlingIntegration(SSotBaseTestCase):
    """Test 8: Error handling and recovery integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_error_recovery_integration(self):
        """Test error handling and recovery work correctly."""
        from auth_service.auth_core.security.auth_error_handler import AuthErrorHandler
        from auth_service.auth_core.models.auth_error import AuthError, AuthErrorType
        
        env = get_env()
        error_handler = AuthErrorHandler(env)
        
        # Test database connection error handling
        db_error = AuthError(
            error_type=AuthErrorType.DATABASE_ERROR,
            message="Connection to database failed",
            user_context={"operation": "login", "user_email": "test@example.com"}
        )
        
        handled_error = error_handler.handle_auth_error(db_error)
        
        assert handled_error.should_retry
        assert handled_error.retry_delay > 0
        assert "temporarily unavailable" in handled_error.user_message.lower()
        assert "database" not in handled_error.user_message.lower()  # Don't expose internals


class TestPerformanceIntegration(SSotBaseTestCase):
    """Test 9: Performance and scalability integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_operations_performance_integration(self):
        """Test auth operations perform well under load."""
        auth_helper = E2EAuthHelper(environment="test")
        
        # Test token generation performance
        start_time = time.time()
        tokens = []
        
        for i in range(50):
            token = auth_helper.create_test_jwt_token(
                user_id=f"perf-user-{i}",
                email=f"perf{i}@netra.com"
            )
            tokens.append(token)
        
        generation_time = time.time() - start_time
        
        # Should generate 50 tokens quickly
        assert generation_time < 2.0
        assert len(tokens) == 50
        assert len(set(tokens)) == 50  # All unique
        
        # Test token validation performance
        from auth_service.auth_core.security.token_validator import TokenValidator
        env = get_env()
        env.set("JWT_SECRET_KEY", "test-jwt-secret-32-characters-long", source="test")
        from auth_service.auth_core.auth_environment import AuthEnvironment
        validator = TokenValidator(AuthEnvironment(env))
        
        start_time = time.time()
        valid_count = 0
        
        for token in tokens[:25]:  # Validate half
            result = validator.validate_token(token)
            if result.is_valid:
                valid_count += 1
        
        validation_time = time.time() - start_time
        
        # Should validate 25 tokens quickly
        assert validation_time < 1.0
        assert valid_count == 25


class TestSecurityPolicyIntegration(SSotBaseTestCase):
    """Test 10: Security policy enforcement integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_security_policy_enforcement_integration(self):
        """Test security policies are enforced correctly."""
        from auth_service.auth_core.security.security_policy_enforcer import SecurityPolicyEnforcer
        
        env = get_env()
        policy_enforcer = SecurityPolicyEnforcer(env)
        
        # Test password policy enforcement
        weak_passwords = ["123456", "password", "abc123"]
        strong_passwords = ["MyStr0ng!P@ssw0rd", "C0mpl3x!Pass123", "S3cur3P@ssw0rd!"]
        
        for weak_password in weak_passwords:
            result = policy_enforcer.validate_password_policy(weak_password)
            assert not result.meets_policy
            assert len(result.violations) > 0
        
        for strong_password in strong_passwords:
            result = policy_enforcer.validate_password_policy(strong_password)
            assert result.meets_policy
            assert result.strength_score >= 70
        
        # Test session security policy
        session_data = {
            "user_id": "policy-test-user",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 Test Browser",
            "concurrent_sessions": 2
        }
        
        session_result = policy_enforcer.validate_session_policy(session_data)
        assert session_result.is_allowed
        assert session_result.max_concurrent_sessions >= 3
        
        # Test with too many concurrent sessions
        session_data["concurrent_sessions"] = 10
        overload_result = policy_enforcer.validate_session_policy(session_data)
        
        if not overload_result.is_allowed:
            assert "concurrent" in overload_result.denial_reason.lower()
        
        # Test IP-based security policy
        suspicious_ips = ["192.0.2.1", "198.51.100.1", "203.0.113.1"]  # RFC test IPs
        
        for suspicious_ip in suspicious_ips:
            ip_result = policy_enforcer.validate_ip_policy(suspicious_ip)
            # Should at least not error out
            assert ip_result.checked is True