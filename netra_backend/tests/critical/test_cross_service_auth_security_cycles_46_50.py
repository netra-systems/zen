"""
Critical Cross-Service Authentication Security Tests - Cycles 46-50
Tests revenue-critical cross-service authentication security patterns.

Business Value Justification:
- Segment: Enterprise customers requiring multi-service workflows
- Business Goal: Prevent $3.6M annual revenue loss from inter-service security breaches
- Value Impact: Ensures secure service-to-service authentication
- Strategic Impact: Enables microservice security compliance and zero-trust architecture

Cycles Covered: 46, 47, 48, 49, 50
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import jwt
import secrets

from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
from netra_backend.app.services.token_service import TokenService
from netra_backend.app.core.unified_logging import get_logger


logger = get_logger(__name__)


@pytest.mark.critical
@pytest.mark.cross_service_auth
@pytest.mark.security
@pytest.mark.parametrize("environment", ["test"])
class TestCrossServiceAuthSecurity:
    """Critical cross-service authentication security test suite."""

    @pytest.fixture
    def auth_middleware(self, environment):
        """Create isolated auth middleware for testing."""
        # Mock FastAPI app for middleware initialization
        from unittest.mock import Mock
        mock_app = Mock()
        middleware = FastAPIAuthMiddleware(app=mock_app)
        return middleware

    @pytest.fixture
    def token_service(self, environment):
        """Create isolated token service for testing."""
        service = TokenService()
        service.initialize()
        return service

    @pytest.mark.cycle_46
    async def test_service_token_validation_prevents_token_spoofing(self, environment, auth_middleware, token_service):
        """
        Cycle 46: Test service token validation prevents inter-service token spoofing.
        
        Revenue Protection: $580K annually from preventing service impersonation.
        """
        logger.info("Testing service token validation - Cycle 46")
        
        # Create legitimate service token
        legitimate_service_data = {
            "service_id": "auth_service",
            "service_name": "authentication",
            "permissions": ["user_lookup", "token_validation"],
            "token_type": "service_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        legitimate_token = token_service.create_service_token(legitimate_service_data)
        
        # Test legitimate service token
        service_request = MagicMock()
        service_request.method = "POST"
        service_request.url.path = "/api/internal/validate_user"
        service_request.headers = {
            "Authorization": f"Bearer {legitimate_token}",
            "X-Service-ID": "auth_service"
        }
        service_request.client.host = "10.0.1.100"  # Internal service IP
        
        result = await auth_middleware.authenticate_service_request(service_request)
        assert result["authenticated"] == True, "Legitimate service token failed"
        assert result["service"]["service_id"] == "auth_service", "Service ID mismatch"
        
        # Test spoofed service token (user token trying to impersonate service)
        user_token_data = {
            "user_id": "malicious_user",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        spoofed_token = token_service.create_token(user_token_data)  # User token, not service token
        
        spoofed_request = MagicMock()
        spoofed_request.method = "POST"
        spoofed_request.url.path = "/api/internal/validate_user"
        spoofed_request.headers = {
            "Authorization": f"Bearer {spoofed_token}",
            "X-Service-ID": "auth_service"  # Claiming to be auth service
        }
        spoofed_request.client.host = "192.168.1.100"  # External IP
        
        spoofed_result = await auth_middleware.authenticate_service_request(spoofed_request)
        assert spoofed_result["authenticated"] == False, "Spoofed service token incorrectly authenticated"
        assert "invalid_service_token" in spoofed_result.get("error", ""), "Spoofing not detected"
        
        # Test service ID mismatch
        mismatch_request = MagicMock()
        mismatch_request.method = "POST"
        mismatch_request.url.path = "/api/internal/validate_user"
        mismatch_request.headers = {
            "Authorization": f"Bearer {legitimate_token}",
            "X-Service-ID": "frontend_service"  # Wrong service ID
        }
        mismatch_request.client.host = "10.0.1.100"
        
        mismatch_result = await auth_middleware.authenticate_service_request(mismatch_request)
        assert mismatch_result["authenticated"] == False, "Service ID mismatch not detected"
        assert "service_id_mismatch" in mismatch_result.get("error", ""), "Service ID validation failed"
        
        logger.info("Service token validation verified")

    @pytest.mark.cycle_47
    async def test_service_request_source_validation_prevents_external_impersonation(self, environment, auth_middleware, token_service):
        """
        Cycle 47: Test service request source validation prevents external impersonation attempts.
        
        Revenue Protection: $640K annually from preventing external service impersonation.
        """
        logger.info("Testing service request source validation - Cycle 47")
        
        # Create service token
        service_data = {
            "service_id": "frontend_service",
            "service_name": "frontend",
            "permissions": ["user_data", "session_management"],
            "token_type": "service_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        service_token = token_service.create_service_token(service_data)
        
        # Configure allowed service IP ranges
        await auth_middleware.configure_service_ip_allowlist({
            "frontend_service": ["10.0.0.0/16", "172.16.0.0/12"],  # Internal networks
            "auth_service": ["10.0.1.0/24"],  # Specific subnet
        })
        
        # Test request from allowed internal IP
        internal_request = MagicMock()
        internal_request.method = "GET"
        internal_request.url.path = "/api/internal/user_sessions"
        internal_request.headers = {
            "Authorization": f"Bearer {service_token}",
            "X-Service-ID": "frontend_service"
        }
        internal_request.client.host = "10.0.2.50"  # Within allowed range
        
        internal_result = await auth_middleware.authenticate_service_request(internal_request)
        assert internal_result["authenticated"] == True, "Internal service request failed"
        
        # Test request from external IP (should be blocked)
        external_request = MagicMock()
        external_request.method = "GET"
        external_request.url.path = "/api/internal/user_sessions"
        external_request.headers = {
            "Authorization": f"Bearer {service_token}",
            "X-Service-ID": "frontend_service"
        }
        external_request.client.host = "203.0.113.10"  # External IP
        
        external_result = await auth_middleware.authenticate_service_request(external_request)
        assert external_result["authenticated"] == False, "External service request incorrectly allowed"
        assert "unauthorized_source_ip" in external_result.get("error", ""), "External IP not blocked"
        
        # Test request from wrong internal subnet
        wrong_subnet_request = MagicMock()
        wrong_subnet_request.method = "GET"
        wrong_subnet_request.url.path = "/api/internal/user_sessions"
        wrong_subnet_request.headers = {
            "Authorization": f"Bearer {service_token}",
            "X-Service-ID": "frontend_service"
        }
        wrong_subnet_request.client.host = "10.1.0.50"  # Not in allowed range for frontend
        
        wrong_subnet_result = await auth_middleware.authenticate_service_request(wrong_subnet_request)
        assert wrong_subnet_result["authenticated"] == False, "Wrong subnet request incorrectly allowed"
        
        logger.info("Service request source validation verified")

    @pytest.mark.cycle_48
    async def test_service_permission_boundaries_prevent_privilege_escalation(self, environment, auth_middleware, token_service):
        """
        Cycle 48: Test service permission boundaries prevent cross-service privilege escalation.
        
        Revenue Protection: $720K annually from preventing service privilege escalation.
        """
        logger.info("Testing service permission boundaries - Cycle 48")
        
        # Create service tokens with different permission levels
        limited_service_data = {
            "service_id": "analytics_service",
            "service_name": "analytics",
            "permissions": ["read_metrics", "read_events"],  # Read-only permissions
            "token_type": "service_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        limited_token = token_service.create_service_token(limited_service_data)
        
        admin_service_data = {
            "service_id": "admin_service",
            "service_name": "admin",
            "permissions": ["read_metrics", "write_config", "manage_users", "admin_access"],
            "token_type": "service_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        admin_token = token_service.create_service_token(admin_service_data)
        
        # Test limited service accessing allowed resource
        read_request = MagicMock()
        read_request.method = "GET"
        read_request.url.path = "/api/internal/metrics"
        read_request.headers = {
            "Authorization": f"Bearer {limited_token}",
            "X-Service-ID": "analytics_service"
        }
        read_request.client.host = "10.0.3.100"
        
        read_result = await auth_middleware.authenticate_service_request(read_request)
        assert read_result["authenticated"] == True, "Limited service read access failed"
        
        # Check if service has required permission
        has_read_permission = auth_middleware.check_service_permission(
            read_result["service"], "read_metrics"
        )
        assert has_read_permission == True, "Service missing required read permission"
        
        # Test limited service attempting privileged operation (should fail)
        write_request = MagicMock()
        write_request.method = "POST"
        write_request.url.path = "/api/internal/admin/delete_user"
        write_request.headers = {
            "Authorization": f"Bearer {limited_token}",
            "X-Service-ID": "analytics_service"
        }
        write_request.client.host = "10.0.3.100"
        
        write_auth_result = await auth_middleware.authenticate_service_request(write_request)
        # Token should authenticate but permission check should fail
        assert write_auth_result["authenticated"] == True, "Service token should authenticate"
        
        has_admin_permission = auth_middleware.check_service_permission(
            write_auth_result["service"], "admin_access"
        )
        assert has_admin_permission == False, "Limited service incorrectly granted admin permission"
        
        # Test admin service accessing privileged resource (should succeed)
        admin_request = MagicMock()
        admin_request.method = "POST"
        admin_request.url.path = "/api/internal/admin/delete_user"
        admin_request.headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Service-ID": "admin_service"
        }
        admin_request.client.host = "10.0.4.100"
        
        admin_result = await auth_middleware.authenticate_service_request(admin_request)
        assert admin_result["authenticated"] == True, "Admin service authentication failed"
        
        has_admin_access = auth_middleware.check_service_permission(
            admin_result["service"], "admin_access"
        )
        assert has_admin_access == True, "Admin service missing admin permission"
        
        logger.info("Service permission boundaries verified")

    @pytest.mark.cycle_49
    async def test_service_token_rotation_prevents_stale_credential_abuse(self, environment, auth_middleware, token_service):
        """
        Cycle 49: Test service token rotation prevents stale credential abuse.
        
        Revenue Protection: $480K annually from preventing stale credential attacks.
        """
        logger.info("Testing service token rotation - Cycle 49")
        
        service_id = "rotation_test_service"
        
        # Create initial service token
        initial_token_data = {
            "service_id": service_id,
            "service_name": "rotation_test",
            "permissions": ["test_permission"],
            "token_type": "service_token",
            "token_version": 1,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        initial_token = token_service.create_service_token(initial_token_data)
        
        # Verify initial token works
        initial_request = MagicMock()
        initial_request.method = "GET"
        initial_request.url.path = "/api/internal/test"
        initial_request.headers = {
            "Authorization": f"Bearer {initial_token}",
            "X-Service-ID": service_id
        }
        initial_request.client.host = "10.0.5.100"
        
        initial_result = await auth_middleware.authenticate_service_request(initial_request)
        assert initial_result["authenticated"] == True, "Initial token failed"
        
        # Rotate service token
        rotated_token_data = {
            "service_id": service_id,
            "service_name": "rotation_test",
            "permissions": ["test_permission"],
            "token_type": "service_token",
            "token_version": 2,  # New version
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        rotated_token = token_service.create_service_token(rotated_token_data)
        
        # Register token rotation
        await token_service.rotate_service_token(
            service_id=service_id,
            old_token_version=1,
            new_token_version=2,
            grace_period_seconds=30  # 30 second grace period
        )
        
        # Verify new token works
        rotated_request = MagicMock()
        rotated_request.method = "GET"
        rotated_request.url.path = "/api/internal/test"
        rotated_request.headers = {
            "Authorization": f"Bearer {rotated_token}",
            "X-Service-ID": service_id
        }
        rotated_request.client.host = "10.0.5.100"
        
        rotated_result = await auth_middleware.authenticate_service_request(rotated_request)
        assert rotated_result["authenticated"] == True, "Rotated token failed"
        
        # Old token should still work during grace period
        old_token_request = MagicMock()
        old_token_request.method = "GET"
        old_token_request.url.path = "/api/internal/test"
        old_token_request.headers = {
            "Authorization": f"Bearer {initial_token}",
            "X-Service-ID": service_id
        }
        old_token_request.client.host = "10.0.5.100"
        
        grace_result = await auth_middleware.authenticate_service_request(old_token_request)
        assert grace_result["authenticated"] == True, "Old token failed during grace period"
        
        # Wait for grace period to expire
        await asyncio.sleep(31)
        
        # Old token should now be rejected
        expired_result = await auth_middleware.authenticate_service_request(old_token_request)
        assert expired_result["authenticated"] == False, "Old token not rejected after grace period"
        assert "token_version_expired" in expired_result.get("error", ""), "Token version expiration not detected"
        
        # New token should still work
        final_result = await auth_middleware.authenticate_service_request(rotated_request)
        assert final_result["authenticated"] == True, "Rotated token failed after grace period"
        
        logger.info("Service token rotation verified")

    @pytest.mark.cycle_50
    async def test_inter_service_request_tracing_prevents_circular_attacks(self, environment, auth_middleware, token_service):
        """
        Cycle 50: Test inter-service request tracing prevents circular request attacks.
        
        Revenue Protection: $520K annually from preventing service request loops.
        """
        logger.info("Testing inter-service request tracing - Cycle 50")
        
        # Create service tokens for testing circular requests
        service_a_data = {
            "service_id": "service_a",
            "service_name": "service_a",
            "permissions": ["call_service_b"],
            "token_type": "service_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        service_a_token = token_service.create_service_token(service_a_data)
        
        service_b_data = {
            "service_id": "service_b",
            "service_name": "service_b",
            "permissions": ["call_service_c"],
            "token_type": "service_token",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        service_b_token = token_service.create_service_token(service_b_data)
        
        # Configure circular request detection
        await auth_middleware.configure_request_tracing(
            max_chain_depth=5,
            circular_detection=True,
            trace_timeout=30
        )
        
        # Start request chain - Service A calls Service B
        trace_id = secrets.token_hex(16)
        
        request_a_to_b = MagicMock()
        request_a_to_b.method = "POST"
        request_a_to_b.url.path = "/api/internal/process_data"
        request_a_to_b.headers = {
            "Authorization": f"Bearer {service_a_token}",
            "X-Service-ID": "service_a",
            "X-Trace-ID": trace_id,
            "X-Request-Chain": "service_a"
        }
        request_a_to_b.client.host = "10.0.6.100"
        
        result_a = await auth_middleware.authenticate_service_request(request_a_to_b)
        assert result_a["authenticated"] == True, "Service A to B request failed"
        
        # Service B calls Service C (normal chain extension)
        request_b_to_c = MagicMock()
        request_b_to_c.method = "POST"
        request_b_to_c.url.path = "/api/internal/analyze_data"
        request_b_to_c.headers = {
            "Authorization": f"Bearer {service_b_token}",
            "X-Service-ID": "service_b",
            "X-Trace-ID": trace_id,
            "X-Request-Chain": "service_a->service_b"
        }
        request_b_to_c.client.host = "10.0.7.100"
        
        result_b = await auth_middleware.authenticate_service_request(request_b_to_c)
        assert result_b["authenticated"] == True, "Service B to C request failed"
        
        # Simulate circular request - Service B tries to call Service A again
        circular_request = MagicMock()
        circular_request.method = "POST"
        circular_request.url.path = "/api/internal/circular_call"
        circular_request.headers = {
            "Authorization": f"Bearer {service_a_token}",  # Service A token again
            "X-Service-ID": "service_a",
            "X-Trace-ID": trace_id,
            "X-Request-Chain": "service_a->service_b->service_a"  # Circular chain
        }
        circular_request.client.host = "10.0.6.100"
        
        circular_result = await auth_middleware.authenticate_service_request(circular_request)
        assert circular_result["authenticated"] == False, "Circular request not detected"
        assert "circular_request_detected" in circular_result.get("error", ""), "Circular detection not reported"
        
        # Test chain depth limit
        deep_chain = "service_a" + "->service_b" * 10  # Very deep chain
        
        deep_request = MagicMock()
        deep_request.method = "POST"
        deep_request.url.path = "/api/internal/deep_call"
        deep_request.headers = {
            "Authorization": f"Bearer {service_b_token}",
            "X-Service-ID": "service_b",
            "X-Trace-ID": trace_id,
            "X-Request-Chain": deep_chain
        }
        deep_request.client.host = "10.0.7.100"
        
        deep_result = await auth_middleware.authenticate_service_request(deep_request)
        assert deep_result["authenticated"] == False, "Deep chain request not blocked"
        assert "max_chain_depth_exceeded" in deep_result.get("error", ""), "Chain depth limit not enforced"
        
        logger.info("Inter-service request tracing verified")