"""
Integration Tests for Messages API Authentication Flow - Issue #1234 Reproduction

Tests the complete authentication flow for the messages API with real auth service,
targeting the 403 authentication errors that correlate with commit f1c251c9c JWT SSOT changes.

Business Value: Platform/Critical - Chat Functionality Protection
Validates the complete auth flow for $500K+ ARR chat functionality protection.

Following CLAUDE.md guidelines:
- Use REAL auth services (no mocks in integration tests)
- Tests designed to FAIL initially to reproduce 403 errors 
- Target the specific `/api/chat/messages` endpoint
- Use SSOT patterns from test_framework/ssot/
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
from datetime import datetime, timezone

# SSOT Base Test Case per CLAUDE.md requirements  
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# FastAPI testing utilities
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Target auth integration components
from netra_backend.app.auth_integration.auth import auth_client, get_current_user, BackendAuthIntegration
from netra_backend.app.main import app


class MessagesAPIAuthFlowIntegrationTests(SSotAsyncTestCase):
    """
    Integration tests for messages API authentication flow - Issue #1234 reproduction.
    
    These tests use REAL auth services and are designed to reproduce the 403
    authentication errors introduced in commit f1c251c9c JWT SSOT changes.
    """
    
    def setup_method(self, method):
        """Setup test environment for messages API auth integration testing."""
        super().setup_method(method)
        
        # Set up integration test environment
        self._env.set("JWT_SECRET_KEY", "test-jwt-secret-32-chars-long-for-integration", "integration_test")
        self._env.set("AUTH_SERVICE_URL", "http://localhost:8001", "integration_test") 
        self._env.set("ENVIRONMENT", "test", "integration_test")
        self._env.set("DATABASE_URL", "sqlite:///:memory:", "integration_test")
        
        # Initialize auth integration for testing
        self.auth_integration = BackendAuthIntegration()
        
        # Create test client
        self.client = TestClient(app)
    
    async def _get_test_jwt_token(self) -> str:
        """
        Get a valid JWT token for testing using real auth service.
        
        This simulates the normal user authentication flow.
        """
        try:
            # Use real auth client to create a test token
            test_user_id = "test_user_issue_1234"
            test_email = "test_issue_1234@example.com"
            
            # Create access token via real auth service
            token_result = await auth_client.create_access_token(
                user_id=test_user_id,
                email=test_email
            )
            
            if token_result and "access_token" in token_result:
                return token_result["access_token"]
            else:
                raise Exception(f"Failed to create test token: {token_result}")
                
        except Exception as e:
            pytest.skip(f"Cannot create test token - auth service may be unavailable: {e}")
    
    async def _get_invalid_jwt_token(self) -> str:
        """Get an invalid JWT token for testing failure cases."""
        return "invalid.jwt.token.for.testing.403.errors"
    
    @pytest.mark.asyncio
    async def test_messages_list_with_valid_auth_should_succeed(self):
        """
        Test that messages list endpoint works with valid authentication.
        
        This establishes the baseline for successful authentication.
        """
        # Arrange
        valid_token = await self._get_test_jwt_token()
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Act
        response = self.client.get("/api/chat/messages", headers=headers)
        
        # Assert - Should succeed with 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        response_data = response.json()
        assert "messages" in response_data
        assert "total_count" in response_data
        assert "page" in response_data
        
        # Record successful auth flow
        self._metrics.record_custom("valid_auth_success", True)
    
    @pytest.mark.asyncio
    async def test_messages_list_with_invalid_auth_expects_401_not_403(self):
        """
        Test that messages list endpoint returns 401 (not 403) for invalid auth.
        
        This is the KEY test for Issue #1234 - we expect 401 for invalid tokens,
        but if there's a bug, we might get 403 instead.
        """
        # Arrange
        invalid_token = await self._get_invalid_jwt_token()
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        # Act
        response = self.client.get("/api/chat/messages", headers=headers)
        
        # Assert - Should be 401 Unauthorized, NOT 403 Forbidden
        assert response.status_code == 401, f"Expected 401 (Unauthorized), got {response.status_code}: {response.text}"
        
        response_data = response.json()
        assert "detail" in response_data
        # Should indicate authentication failure, not authorization failure
        assert "Invalid" in response_data["detail"] or "expired" in response_data["detail"]
        
        # Record the error type for Issue #1234 analysis
        self._metrics.record_custom("invalid_auth_status_code", response.status_code)
        self._metrics.record_custom("invalid_auth_detail", response_data.get("detail", ""))
    
    @pytest.mark.asyncio
    async def test_messages_create_with_invalid_auth_expects_401_not_403(self):
        """
        Test that messages create endpoint returns 401 (not 403) for invalid auth.
        
        This tests the POST endpoint which might have different auth behavior.
        """
        # Arrange
        invalid_token = await self._get_invalid_jwt_token()
        headers = {"Authorization": f"Bearer {invalid_token}"}
        message_data = {
            "content": "Test message for Issue #1234",
            "thread_id": "test_thread_123",
            "message_type": "user"
        }
        
        # Act
        response = self.client.post("/api/chat/messages", headers=headers, json=message_data)
        
        # Assert - Should be 401 Unauthorized, NOT 403 Forbidden
        assert response.status_code == 401, f"Expected 401 (Unauthorized), got {response.status_code}: {response.text}"
        
        # Record the error for Issue #1234 tracking
        self._metrics.record_custom("create_invalid_auth_status_code", response.status_code)
    
    @pytest.mark.asyncio 
    async def test_messages_stream_with_invalid_auth_expects_401_not_403(self):
        """
        Test that messages stream endpoint returns 401 (not 403) for invalid auth.
        
        The streaming endpoint is critical for investor demos and may have
        different authentication handling.
        """
        # Arrange
        invalid_token = await self._get_invalid_jwt_token()
        headers = {"Authorization": f"Bearer {invalid_token}"}
        stream_data = {
            "content": "Stream test for Issue #1234",
            "thread_id": "test_thread_stream",
            "message_type": "user"
        }
        
        # Act
        response = self.client.post("/api/chat/messages/stream", headers=headers, json=stream_data)
        
        # Assert - Should be 401 Unauthorized, NOT 403 Forbidden
        assert response.status_code == 401, f"Expected 401 (Unauthorized), got {response.status_code}: {response.text}"
        
        # Record streaming auth failure
        self._metrics.record_custom("stream_invalid_auth_status_code", response.status_code)
    
    @pytest.mark.asyncio
    async def test_messages_auth_with_no_bearer_token_expects_401(self):
        """
        Test messages endpoint with no Authorization header.
        
        This tests the case where no auth is provided at all.
        """
        # Arrange - No Authorization header
        headers = {}
        
        # Act
        response = self.client.get("/api/chat/messages", headers=headers)
        
        # Assert - Should be 401 or 422 (validation error)
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}: {response.text}"
        
        self._metrics.record_custom("no_auth_status_code", response.status_code)
    
    @pytest.mark.asyncio
    async def test_messages_auth_with_malformed_bearer_token_expects_401(self):
        """
        Test messages endpoint with malformed Bearer token.
        
        This tests edge cases in token parsing that could cause 403 errors.
        """
        # Arrange - Malformed Authorization headers
        malformed_headers = [
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "Bearer "},  # Empty token
            {"Authorization": "Bearer invalid"},  # Invalid token format
            {"Authorization": "Basic dGVzdA=="},  # Wrong auth scheme
            {"Authorization": "Bearer token.with.only.two.parts"},  # Invalid JWT structure
        ]
        
        for case_num, headers in enumerate(malformed_headers):
            # Act
            response = self.client.get("/api/chat/messages", headers=headers)
            
            # Assert - Should be 401, not 403
            assert response.status_code == 401, f"Case {case_num}: Expected 401, got {response.status_code}: {response.text}"
    
    @pytest.mark.asyncio
    async def test_auth_service_delegation_timing_reproduction(self):
        """
        Test auth service delegation timing to reproduce Issue #1234.
        
        This test focuses on the timing correlation with commit f1c251c9c
        which changed JWT SSOT patterns.
        """
        # Arrange
        test_token = await self._get_test_jwt_token()
        
        # Time the auth validation process
        start_time = datetime.now(timezone.utc)
        
        # Use the auth integration directly to test delegation
        auth_result = await self.auth_integration.validate_request_token(f"Bearer {test_token}")
        
        end_time = datetime.now(timezone.utc)
        validation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Assert successful validation
        assert auth_result.valid, f"Auth validation should succeed: {auth_result.error}"
        assert auth_result.user_id is not None, "User ID should be present in auth result"
        
        # Record timing metrics for Issue #1234 analysis
        self._metrics.record_custom("auth_validation_time_ms", validation_time_ms)
        self._metrics.record_custom("auth_delegation_success", True)
        
        # Log timing for debugging
        self.logger.info(f"Auth validation took {validation_time_ms:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_auth_failure_reproduction(self):
        """
        Test auth failures under circuit breaker conditions.
        
        This simulates conditions where circuit breaker might cause
        incorrect 403 responses instead of 401.
        """
        # This test would need the circuit breaker to be in a testable state
        # For now, we'll test with invalid tokens to simulate service failures
        
        invalid_token = "deliberately.invalid.token.to.trigger.circuit.breaker"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        # Make multiple rapid requests to potentially trigger circuit breaker
        responses = []
        for i in range(5):
            response = self.client.get("/api/chat/messages", headers=headers)
            responses.append(response)
            
            # Each should be 401, not 403, even under load
            assert response.status_code == 401, f"Request {i}: Expected 401, got {response.status_code}"
        
        # Record circuit breaker behavior
        self._metrics.record_custom("circuit_breaker_requests", len(responses))
        self._metrics.record_custom("all_returned_401", all(r.status_code == 401 for r in responses))
    
    @pytest.mark.asyncio
    async def test_auth_service_connectivity_issue_reproduction(self):
        """
        Test behavior when auth service is unreachable.
        
        This tests how the system behaves when the auth service dependency fails,
        which could be related to the Issue #1234 403 errors.
        """
        # Temporarily set an unreachable auth service URL
        original_auth_url = self._env.get("AUTH_SERVICE_URL")
        self._env.set("AUTH_SERVICE_URL", "http://nonexistent-auth-service:9999", "test_unreachable")
        
        try:
            # Create new auth client with unreachable service
            unreachable_headers = {"Authorization": "Bearer any.token.will.fail"}
            
            # Act - This should fail but with correct error code
            response = self.client.get("/api/chat/messages", headers=unreachable_headers)
            
            # Assert - Could be 401 (auth failure) or 503 (service unavailable)
            # But should NOT be 403 (forbidden)
            assert response.status_code in [401, 503], f"Expected 401 or 503, got {response.status_code}: {response.text}"
            
            self._metrics.record_custom("unreachable_auth_service_status", response.status_code)
            
        finally:
            # Restore original auth service URL
            self._env.set("AUTH_SERVICE_URL", original_auth_url, "test_restore")
    
    def teardown_method(self, method):
        """Clean up after each test."""
        # Record completion of Issue #1234 reproduction test
        self._metrics.record_custom("issue_1234_test_completed", True)
        self._metrics.record_custom("commit_correlation", "f1c251c9c")
        
        super().teardown_method(method)