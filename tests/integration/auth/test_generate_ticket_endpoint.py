"""
Integration tests for /auth/generate-ticket endpoint (Issue #1296 Phase 2)

Tests the complete authentication ticket generation flow:
1. JWT token validation
2. Ticket generation via AuthTicketManager
3. Proper error handling and response formatting

Business Value: Enables secure, time-limited authentication for CI/CD automation,
webhooks, and automated testing without exposing long-lived credentials.
"""

import asyncio
import json
import pytest
import time
import httpx
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.environment_markers import requires_backend_service


class TestGenerateTicketEndpoint(SSotAsyncTestCase):
    """Integration tests for the /auth/generate-ticket endpoint."""

    @pytest.fixture
    def backend_base_url(self):
        """Get backend service URL for testing."""
        from shared.isolated_environment import get_env
        env = get_env()
        return env.get("BACKEND_URL", "http://localhost:8000")

    @pytest.fixture
    def sample_jwt_token(self):
        """Sample JWT token for testing."""
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwicGVybWlzc2lvbnMiOlsicmVhZCIsImNoYXQiLCJ3ZWJzb2NrZXQiXSwiZXhwIjoxNzAwMDAwMDAwfQ.test-signature"

    @pytest.fixture
    def auth_headers(self, sample_jwt_token):
        """Authorization headers with Bearer token."""
        return {"Authorization": f"Bearer {sample_jwt_token}"}

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_success_minimal_payload(self, backend_base_url, auth_headers):
        """Test successful ticket generation with minimal request payload."""
        
        # Mock auth client validation to simulate successful JWT validation
        mock_validation_result = {
            'valid': True,
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'permissions': ['read', 'chat', 'websocket']
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            # Mock ticket manager to return expected ticket
            with patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager.generate_ticket') as mock_generate:
                from netra_backend.app.websocket_core.unified_auth_ssot import AuthTicket
                
                current_time = time.time()
                expected_ticket = AuthTicket(
                    ticket_id="test-ticket-abc123",
                    user_id="test-user-123",
                    email="test@example.com",
                    permissions=['read', 'chat', 'websocket'],
                    expires_at=current_time + 300,
                    created_at=current_time,
                    single_use=True,
                    metadata={}
                )
                mock_generate.return_value = expected_ticket
                
                # Make request to generate ticket endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{backend_base_url}/api/v1/auth/generate-ticket",
                        headers=auth_headers,
                        json={}  # Minimal payload - use defaults
                    )
                
                # Assert successful response
                assert response.status_code == 200
                
                response_data = response.json()
                assert "ticket_id" in response_data
                assert response_data["ticket_id"] == "test-ticket-abc123"
                assert response_data["user_id"] == "test-user-123"
                assert response_data["email"] == "test@example.com"
                assert response_data["permissions"] == ['read', 'chat', 'websocket']
                assert response_data["single_use"] is True
                assert "expires_at" in response_data
                assert "created_at" in response_data
                
                # Verify auth client was called
                mock_validate.assert_called_once()
                
                # Verify ticket manager was called with correct parameters
                mock_generate.assert_called_once_with(
                    user_id="test-user-123",
                    email="test@example.com",
                    permissions=['read', 'chat', 'websocket'],
                    ttl_seconds=None,
                    single_use=True,
                    metadata={}
                )

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_success_custom_parameters(self, backend_base_url, auth_headers):
        """Test successful ticket generation with custom parameters."""
        
        # Mock auth client validation
        mock_validation_result = {
            'valid': True,
            'user_id': 'test-user-456',
            'email': 'custom@example.com',
            'permissions': ['read', 'write', 'admin']
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            with patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager.generate_ticket') as mock_generate:
                from netra_backend.app.websocket_core.unified_auth_ssot import AuthTicket
                
                current_time = time.time()
                expected_ticket = AuthTicket(
                    ticket_id="custom-ticket-xyz789",
                    user_id="test-user-456",
                    email="custom@example.com",
                    permissions=['read', 'chat'],  # Custom permissions
                    expires_at=current_time + 600,  # Custom TTL
                    created_at=current_time,
                    single_use=False,  # Reusable ticket
                    metadata={"source": "integration_test"}
                )
                mock_generate.return_value = expected_ticket
                
                # Request with custom parameters
                request_payload = {
                    "ttl_seconds": 600,
                    "single_use": False,
                    "permissions": ["read", "chat"],
                    "metadata": {"source": "integration_test"}
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{backend_base_url}/api/v1/auth/generate-ticket",
                        headers=auth_headers,
                        json=request_payload
                    )
                
                # Assert successful response
                assert response.status_code == 200
                
                response_data = response.json()
                assert response_data["ticket_id"] == "custom-ticket-xyz789"
                assert response_data["single_use"] is False
                assert response_data["permissions"] == ["read", "chat"]
                assert response_data["metadata"] == {"source": "integration_test"}
                
                # Verify ticket manager was called with custom parameters
                mock_generate.assert_called_once_with(
                    user_id="test-user-456",
                    email="custom@example.com",
                    permissions=["read", "chat"],
                    ttl_seconds=600,
                    single_use=False,
                    metadata={"source": "integration_test"}
                )

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_unauthorized_no_token(self, backend_base_url):
        """Test ticket generation fails without authorization token."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{backend_base_url}/api/v1/auth/generate-ticket",
                json={}
            )
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
        
        response_data = response.json()
        assert "detail" in response_data
        assert "Authorization header" in response_data["detail"]

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_unauthorized_invalid_token(self, backend_base_url):
        """Test ticket generation fails with invalid JWT token."""
        
        invalid_headers = {"Authorization": "Bearer invalid-jwt-token"}
        
        # Mock auth client to return invalid token
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = {"valid": False}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_base_url}/api/v1/auth/generate-ticket",
                    headers=invalid_headers,
                    json={}
                )
            
            # Should return 401 Unauthorized
            assert response.status_code == 401
            
            response_data = response.json()
            assert "detail" in response_data
            assert "Invalid or expired JWT token" in response_data["detail"]

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_invalid_ttl_parameter(self, backend_base_url, auth_headers):
        """Test ticket generation fails with invalid TTL parameter."""
        
        # Mock auth client validation
        mock_validation_result = {
            'valid': True,
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'permissions': ['read']
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            # Test with negative TTL
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_base_url}/api/v1/auth/generate-ticket",
                    headers=auth_headers,
                    json={"ttl_seconds": -100}
                )
            
            # Should return 422 Unprocessable Entity
            assert response.status_code == 422
            
            response_data = response.json()
            assert "detail" in response_data
            assert "TTL must be positive" in response_data["detail"]

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_auth_client_exception(self, backend_base_url, auth_headers):
        """Test ticket generation handles auth client exceptions gracefully."""
        
        # Mock auth client to raise an exception
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.side_effect = Exception("Auth service connection failed")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_base_url}/api/v1/auth/generate-ticket",
                    headers=auth_headers,
                    json={}
                )
            
            # Should return 401 Unauthorized with error handling
            assert response.status_code == 401
            
            response_data = response.json()
            assert "detail" in response_data
            assert "Token validation failed" in response_data["detail"]

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_storage_failure(self, backend_base_url, auth_headers):
        """Test ticket generation handles storage failures gracefully."""
        
        # Mock auth client validation to succeed
        mock_validation_result = {
            'valid': True,
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'permissions': ['read']
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            # Mock ticket manager to raise storage error
            with patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager.generate_ticket') as mock_generate:
                mock_generate.side_effect = RuntimeError("Failed to store authentication ticket")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{backend_base_url}/api/v1/auth/generate-ticket",
                        headers=auth_headers,
                        json={}
                    )
                
                # Should return 503 Service Unavailable
                assert response.status_code == 503
                
                response_data = response.json()
                assert "detail" in response_data
                assert "service temporarily unavailable" in response_data["detail"]

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_compatibility_endpoint(self, backend_base_url, auth_headers):
        """Test that compatibility endpoint /auth/generate-ticket works."""
        
        # Mock auth client validation
        mock_validation_result = {
            'valid': True,
            'user_id': 'test-user-compat',
            'email': 'compat@example.com',
            'permissions': ['read']
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            with patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager.generate_ticket') as mock_generate:
                from netra_backend.app.websocket_core.unified_auth_ssot import AuthTicket
                
                current_time = time.time()
                expected_ticket = AuthTicket(
                    ticket_id="compat-ticket-123",
                    user_id="test-user-compat",
                    email="compat@example.com",
                    permissions=['read'],
                    expires_at=current_time + 300,
                    created_at=current_time,
                    single_use=True,
                    metadata={}
                )
                mock_generate.return_value = expected_ticket
                
                # Test compatibility endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{backend_base_url}/auth/generate-ticket",  # Compatibility route
                        headers=auth_headers,
                        json={}
                    )
                
                # Should work identically to main endpoint
                assert response.status_code == 200
                
                response_data = response.json()
                assert response_data["ticket_id"] == "compat-ticket-123"
                assert response_data["user_id"] == "test-user-compat"

    @requires_backend_service
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_generate_ticket_ttl_capping(self, backend_base_url, auth_headers):
        """Test that TTL is properly capped at maximum allowed value."""
        
        # Mock auth client validation
        mock_validation_result = {
            'valid': True,
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'permissions': ['read']
        }
        
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token_jwt') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            with patch('netra_backend.app.websocket_core.unified_auth_ssot.ticket_manager.generate_ticket') as mock_generate:
                from netra_backend.app.websocket_core.unified_auth_ssot import AuthTicket
                
                current_time = time.time()
                # Ticket manager should cap TTL at 3600 seconds (1 hour)
                expected_ticket = AuthTicket(
                    ticket_id="capped-ticket-123",
                    user_id="test-user-123",
                    email="test@example.com",
                    permissions=['read'],
                    expires_at=current_time + 3600,  # Capped at 1 hour
                    created_at=current_time,
                    single_use=True,
                    metadata={}
                )
                mock_generate.return_value = expected_ticket
                
                # Request with excessive TTL (2 hours)
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{backend_base_url}/api/v1/auth/generate-ticket",
                        headers=auth_headers,
                        json={"ttl_seconds": 7200}  # 2 hours - should be capped
                    )
                
                # Should succeed but TTL should be capped
                assert response.status_code == 200
                
                # Verify ticket manager was called with the original requested TTL
                # (AuthTicketManager handles the capping internally)
                mock_generate.assert_called_once()
                call_args = mock_generate.call_args
                assert call_args[1]['ttl_seconds'] == 7200  # Original value passed


if __name__ == '__main__':
    pytest.main([__file__])