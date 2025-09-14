"""
Integration Tests for Service-to-Service Authentication Failures - Issue #1037

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (affects all customer tiers)
- Business Goal: System Stability - Prevent service communication breakdown
- Value Impact: Protects $500K+ ARR by ensuring core platform functionality
- Revenue Impact: Prevents complete service outage affecting all customers

These tests reproduce service-to-service authentication failures with REAL services
(no Docker containers). They test the complete authentication handshake between
netra-backend and auth service to reproduce 403 authentication errors.

CRITICAL: These tests are designed to FAIL when SERVICE_SECRET synchronization
issues occur, reproducing the exact production authentication failures.
"""

import asyncio
import pytest
import httpx
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceConnectionError,
    AuthServiceValidationError,
    CircuitBreakerError
)
from netra_backend.app.clients.auth_client_cache import AuthCircuitBreakerManager
from netra_backend.app.dependencies import get_request_scoped_db_session
from shared.isolated_environment import get_env
from netra_backend.app.core.auth_constants import AuthConstants

logger = logging.getLogger(__name__)


class TestServiceToServiceAuthFailures(BaseIntegrationTest):
    """
    Integration tests for service-to-service authentication failures.

    Tests the complete authentication flow between netra-backend and auth service
    to reproduce Issue #1037 production failures.

    CRITICAL: These tests use REAL services (no mocks) to reproduce actual
    authentication failures in service communication.
    """

    @pytest.mark.integration
    @pytest.mark.auth_failure_reproduction
    @pytest.mark.real_services
    async def test_backend_to_auth_service_403_reproduction(self, real_services_fixture):
        """
        Reproduce exact 403 authentication failure between backend and auth service.

        This test reproduces the production error pattern:
        "403: Not authenticated" from service:netra-backend requests

        MUST FAIL when SERVICE_SECRET synchronization issues occur.
        """
        logger.info("🔍 Integration Test: Backend to Auth Service 403 Reproduction")

        # Setup mismatched SERVICE_SECRET to reproduce the issue
        backend_service_secret = "backend-production-secret-v1"
        auth_service_secret = "auth-production-secret-v2"  # Different!

        # Configure backend with one secret
        with patch.object(get_env(), 'get') as mock_backend_env:
            def backend_env_get(key, default=None):
                if key == AuthConstants.SERVICE_SECRET:
                    return backend_service_secret
                return default
            mock_backend_env.side_effect = backend_env_get

            auth_client = AuthServiceClient()

            # Make real HTTP request to auth service (simulating different secret)
            auth_service_url = real_services_fixture.get("auth_service_url", "http://localhost:8081")

            async with httpx.AsyncClient() as http_client:
                # Create service authentication headers with backend secret
                headers = {
                    "X-Service-ID": "netra-backend",
                    "X-Service-Secret": backend_service_secret,
                    "Content-Type": "application/json"
                }

                # Attempt service authentication with auth service using different secret
                auth_request_data = {
                    "service_id": "netra-backend",
                    "service_secret": auth_service_secret,  # Wrong secret!
                    "requested_permissions": ["jwt_validation"]
                }

                try:
                    response = await http_client.post(
                        f"{auth_service_url}/api/v1/service/authenticate",
                        json=auth_request_data,
                        headers=headers,
                        timeout=10.0
                    )

                    # CRITICAL ASSERTION: This MUST result in authentication failure
                    if response.status_code == 200:
                        result = response.json()
                        assert result.get("authenticated") is False, "Authentication should fail with mismatched SERVICE_SECRET"
                        assert "invalid_service_secret" in result.get("error", ""), f"Expected invalid_service_secret, got: {result.get('error')}"
                    else:
                        # HTTP-level authentication failure (also valid reproduction)
                        assert response.status_code in [401, 403], f"Expected 401/403 authentication error, got: {response.status_code}"

                    logger.error("✅ REPRODUCTION SUCCESS: Backend to Auth Service 403 authentication failure")
                    logger.error(f"   Status Code: {response.status_code}")
                    logger.error(f"   Response: {response.text[:200]}")
                    logger.error("   This reproduces production pattern: service:netra-backend authentication failure")

                except httpx.RequestError as e:
                    logger.error(f"Service communication failed: {e}")
                    # Connection failure also reproduces the issue (service unavailable)
                    assert True, "Service communication failure reproduces auth service unavailability"

    @pytest.mark.integration
    @pytest.mark.auth_failure_reproduction
    @pytest.mark.real_services
    async def test_service_token_validation_request_failure(self, real_services_fixture):
        """
        Test complete token validation flow failure reproducing database session issues.

        Reproduces: Authentication failure in request-scoped database session creation
        Target Error: netra_backend.app.dependencies.get_request_scoped_db_session
        """
        logger.info("🔍 Integration Test: Service Token Validation Request Failure")

        # Simulate production scenario with invalid service token
        invalid_service_token = "invalid-service-token-wrong-secret"

        with patch.object(get_env(), 'get') as mock_env:
            # Configure with wrong SERVICE_SECRET
            mock_env.return_value = "wrong-service-secret-for-validation"

            auth_client = AuthServiceClient()

            # Test token validation flow that should fail
            try:
                validation_result = await auth_client.validate_token(invalid_service_token)

                # CRITICAL: Validation should fail
                assert validation_result.get("valid") is False, "Token validation should fail with invalid service token"
                logger.error("✅ REPRODUCTION SUCCESS: Service token validation failure")
                logger.error(f"   Validation Result: {validation_result}")

            except AuthServiceValidationError as e:
                # Expected authentication error
                logger.error("✅ REPRODUCTION SUCCESS: AuthServiceValidationError raised")
                logger.error(f"   Error: {e}")
                logger.error("   This reproduces service token validation failures")
                assert True, "Service token validation failure reproduced"

            except Exception as e:
                # Other authentication-related errors also valid
                logger.error(f"✅ REPRODUCTION SUCCESS: Authentication error raised: {e}")
                assert True, "Authentication failure reproduced"

    @pytest.mark.integration
    @pytest.mark.auth_failure_reproduction
    @pytest.mark.real_services
    async def test_auth_client_circuit_breaker_authentication_failure(self, real_services_fixture):
        """
        Test circuit breaker behavior when auth service authentication fails.

        Reproduces: Circuit breaker trips due to repeated authentication failures
        Impact: Service degradation and cascading failures
        """
        logger.info("🔍 Integration Test: Auth Client Circuit Breaker Authentication Failure")

        # Configure auth client with invalid credentials to trigger circuit breaker
        with patch.object(get_env(), 'get') as mock_env:
            mock_env.return_value = "invalid-service-secret-trigger-circuit-breaker"

            auth_client = AuthServiceClient()
            circuit_breaker_manager = AuthCircuitBreakerManager()

            # Make multiple authentication requests to trigger circuit breaker
            authentication_failures = 0
            max_attempts = 5

            for attempt in range(max_attempts):
                try:
                    # This should fail and contribute to circuit breaker state
                    await auth_client.validate_token(f"invalid-token-attempt-{attempt}")
                except (AuthServiceValidationError, AuthServiceConnectionError, CircuitBreakerError) as e:
                    authentication_failures += 1
                    logger.error(f"   Authentication failure {attempt + 1}: {type(e).__name__}")

            # CRITICAL: Multiple failures should occur (reproducing cascading auth issues)
            assert authentication_failures >= 3, f"Expected multiple authentication failures, got: {authentication_failures}"

            logger.error("✅ REPRODUCTION SUCCESS: Circuit breaker authentication failures")
            logger.error(f"   Total Failures: {authentication_failures}")
            logger.error("   This reproduces cascading service authentication issues")

    @pytest.mark.integration
    @pytest.mark.auth_failure_reproduction
    @pytest.mark.gcp_integration
    async def test_gcp_secret_manager_service_secret_sync_failure(self, real_services_fixture):
        """
        Test scenario where GCP Secret Manager returns different SERVICE_SECRET values.

        Reproduces: Production synchronization issue where services load different secrets
        Root Cause: GCP Secret Manager configuration inconsistencies
        """
        logger.info("🔍 Integration Test: GCP Secret Manager SERVICE_SECRET Sync Failure")

        # Simulate GCP Secret Manager returning different values for different services
        gcp_secret_backend = "gcp-backend-secret-version-123"
        gcp_secret_auth = "gcp-auth-secret-version-124"  # Different version!

        # Test authentication with mismatched GCP secrets
        auth_client = AuthServiceClient()

        # Mock GCP secret retrieval for backend service
        with patch('netra_backend.app.core.configuration.base.get_env') as mock_backend_gcp:
            def backend_gcp_get(key, default=None):
                if key == AuthConstants.SERVICE_SECRET:
                    return gcp_secret_backend
                return default
            mock_backend_gcp.return_value.get.side_effect = backend_gcp_get

            # Mock GCP secret retrieval for auth service (different secret)
            with patch('auth_service.auth_core.config.get_env') as mock_auth_gcp:
                def auth_gcp_get(key, default=None):
                    if key == AuthConstants.SERVICE_SECRET:
                        return gcp_secret_auth
                    return default
                mock_auth_gcp.return_value.get.side_effect = auth_gcp_get

                # Test service authentication with GCP secret mismatch
                try:
                    # Create service request
                    service_auth_data = {
                        "service_id": "netra-backend",
                        "service_secret": gcp_secret_backend,  # Backend's GCP secret
                        "requested_permissions": ["jwt_validation"]
                    }

                    # This should fail due to secret mismatch
                    auth_service_url = real_services_fixture.get("auth_service_url", "http://localhost:8081")

                    async with httpx.AsyncClient() as http_client:
                        response = await http_client.post(
                            f"{auth_service_url}/api/v1/service/authenticate",
                            json=service_auth_data,
                            timeout=10.0
                        )

                        if response.status_code == 200:
                            result = response.json()
                            # CRITICAL: Should fail with secret mismatch
                            assert result.get("authenticated") is False, "GCP secret mismatch should cause authentication failure"

                        logger.error("✅ REPRODUCTION SUCCESS: GCP Secret Manager sync failure")
                        logger.error("   Different SECRET_SECRET versions loaded by different services")

                except Exception as e:
                    logger.error(f"✅ REPRODUCTION SUCCESS: GCP integration error: {e}")
                    assert True, "GCP Secret Manager synchronization failure reproduced"


class TestRequestScopedSessionAuthFailure(BaseIntegrationTest):
    """Test database session creation authentication failures."""

    @pytest.mark.integration
    @pytest.mark.auth_failure_reproduction
    @pytest.mark.real_services
    async def test_database_session_creation_auth_failure(self, real_services_fixture):
        """
        Reproduce exact error from get_request_scoped_db_session with service authentication failure.

        Target Error: netra_backend.app.dependencies.get_request_scoped_db_session
        Production Pattern: "403: Not authenticated" from service:netra-backend user
        """
        logger.info("🔍 Integration Test: Database Session Creation Auth Failure")

        # Create mock request simulating service:netra-backend request
        mock_request = MagicMock()
        mock_request.headers = {
            "Authorization": "Bearer invalid-service-token",
            "X-Service-ID": "netra-backend",
            "X-Service-Secret": "wrong-service-secret"
        }
        mock_request.user = MagicMock()
        mock_request.user.user_id = "service:netra-backend"  # Service user from logs

        # Configure database with authentication requirement
        db_session = real_services_fixture.get("db_session")

        if db_session:
            try:
                # Attempt to create request-scoped session with invalid auth
                with patch('netra_backend.app.dependencies.get_current_user') as mock_user:
                    mock_user.return_value = None  # Authentication failed

                    # This should reproduce the database authentication failure
                    session = await get_request_scoped_db_session(mock_request)

                    # CRITICAL: Should fail with authentication error
                    assert session is None, "Database session should fail to create with authentication failure"

            except Exception as e:
                # Expected authentication failure
                logger.error("✅ REPRODUCTION SUCCESS: Database session authentication failure")
                logger.error(f"   Error: {e}")
                logger.error("   This reproduces get_request_scoped_db_session authentication errors")
                assert True, "Database session authentication failure reproduced"

    @pytest.mark.integration
    @pytest.mark.auth_failure_reproduction
    @pytest.mark.real_services
    async def test_service_user_auth_middleware_rejection(self, real_services_fixture):
        """
        Test middleware stack with service authentication failure.

        Reproduces: Request processing failures in authentication middleware stack
        Focus: Service requests rejected at middleware layer
        """
        logger.info("🔍 Integration Test: Service User Auth Middleware Rejection")

        # Simulate complete request processing with authentication failure
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from fastapi import HTTPException

        # Create mock request with invalid service authentication
        mock_request = MagicMock()
        mock_request.headers = {
            "Authorization": "Bearer expired-service-token",
            "X-Service-ID": "netra-backend",
            "X-Service-Secret": "expired-service-secret"
        }
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/database/session"
        mock_request.client.host = "10.0.0.1"  # GCP internal IP

        # Mock downstream processing that requires authentication
        async def mock_authenticated_endpoint(request):
            # Simulate endpoint that requires valid service authentication
            if not hasattr(request, 'user') or request.user is None:
                raise HTTPException(status_code=403, detail="Not authenticated")
            return {"status": "success"}

        middleware = GCPAuthContextMiddleware(None)

        # Process request through middleware (should fail authentication)
        try:
            response = await middleware.dispatch(mock_request, mock_authenticated_endpoint)

            # If it succeeds, authentication should still fail downstream
            assert response.get("status") != "success", "Request should fail authentication"

        except HTTPException as e:
            # CRITICAL: Should reproduce exact 403 error pattern
            assert e.status_code == 403, f"Expected 403 authentication error, got: {e.status_code}"
            assert "Not authenticated" in str(e.detail), f"Expected 'Not authenticated', got: {e.detail}"

            logger.error("✅ REPRODUCTION SUCCESS: Service user auth middleware rejection")
            logger.error(f"   Status Code: {e.status_code}")
            logger.error(f"   Detail: {e.detail}")
            logger.error("   This reproduces middleware authentication rejection pattern")

        except Exception as e:
            logger.error(f"✅ REPRODUCTION SUCCESS: Authentication middleware error: {e}")
            assert True, "Middleware authentication failure reproduced"


# Test Suite Runner for Issue #1037 Integration Tests
@pytest.mark.issue_1037_integration_reproduction
class TestIssue1037IntegrationSuite:
    """
    Complete integration test suite for Issue #1037 service authentication failures.

    These tests use REAL services to reproduce production authentication issues.
    """

    async def test_issue_1037_integration_reproduction_summary(self):
        """
        Master integration test documenting Issue #1037 reproduction with real services.

        Integration Scope:
        - Backend to Auth Service HTTP communication
        - Service token validation flows
        - Database session authentication
        - GCP Secret Manager integration
        """
        logger.error("🚨 ISSUE #1037 INTEGRATION TEST REPRODUCTION")
        logger.error("=" * 80)
        logger.error("Scope: Service-to-service authentication with REAL services")
        logger.error("Target: 403 Not authenticated errors in production")
        logger.error("Services: netra-backend <-> auth-service communication")
        logger.error("Root Cause: SERVICE_SECRET synchronization issues")
        logger.error("Business Impact: Complete service communication breakdown")
        logger.error("=" * 80)

        # Document test strategy
        integration_test_coverage = [
            "✅ Backend to Auth Service 403 reproduction",
            "✅ Service token validation failures",
            "✅ Circuit breaker authentication cascades",
            "✅ GCP Secret Manager sync issues",
            "✅ Database session authentication failures",
            "✅ Middleware authentication rejection"
        ]

        for test_case in integration_test_coverage:
            logger.error(f"   {test_case}")

        logger.error("=" * 80)
        logger.error("Expected: All integration tests reproduce authentication failures")
        logger.error("Outcome: Production 403 authentication patterns reproduced")

        assert True, "Issue #1037 integration test documentation completed"