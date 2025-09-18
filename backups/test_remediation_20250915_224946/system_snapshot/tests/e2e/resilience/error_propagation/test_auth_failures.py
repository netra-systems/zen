"""
Auth Service Failure Propagation Tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Authentication Reliability
- Value Impact: Validates auth error handling across all services
- Strategic/Revenue Impact: Prevents auth failures from cascading
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.error_propagation_fixtures import (
    ErrorCorrelationContext,
    error_correlation_context,
    real_http_client,
    real_websocket_client,
    service_orchestrator,
    test_user,
)

@pytest.mark.asyncio
@pytest.mark.e2e
class AuthServiceFailuresTests:
    """Test auth service failure propagation."""
    
    @pytest.mark.resilience
    @pytest.mark.auth
    async def test_invalid_token_propagation(self, service_orchestrator, real_websocket_client:
                                           error_correlation_context):
        """Test invalid token error propagates correctly."""
        # Use invalid token
        invalid_token = "invalid_token_123"
        
        # Attempt connection with invalid token
        connection_result = await real_websocket_client.connect(invalid_token)
        
        # Should fail with proper error
        assert not connection_result.success
        assert "authentication" in connection_result.error.lower()
        assert real_websocket_client.state == ConnectionState.DISCONNECTED
        
    @pytest.mark.resilience
    @pytest.mark.auth
    async def test_expired_token_handling(self, service_orchestrator, real_websocket_client:
                                        error_correlation_context):
        """Test expired token error handling."""
        # Create expired token
        expired_token = "expired_token_456"
        
        # Attempt operation with expired token
        connection_result = await real_websocket_client.connect(expired_token)
        
        # Should handle gracefully
        assert not connection_result.success
        assert "expired" in connection_result.error.lower() or "invalid" in connection_result.error.lower()
        
    @pytest.mark.resilience
    @pytest.mark.auth
    async def test_auth_service_unavailable(self, service_orchestrator, real_http_client:
                                          error_correlation_context):
        """Test auth service unavailability handling."""
        # Simulate auth service down by using wrong endpoint
        wrong_auth_url = "http://localhost:9999/auth"
        
        # Attempt to get token
        response = await real_http_client.request(
            "POST", 
            f"{wrong_auth_url}/token",
            json={"username": "test", "password": "test"}
        )
        
        # Should handle connection error gracefully
        assert not response.success
        assert response.error is not None
        
    @pytest.mark.resilience
    @pytest.mark.auth
    async def test_token_validation_failure(self, service_orchestrator, real_websocket_client:
                                          error_correlation_context):
        """Test token validation failure handling."""
        # Use malformed token
        malformed_token = "not.a.valid.jwt.token"
        
        # Attempt connection
        connection_result = await real_websocket_client.connect(malformed_token)
        
        # Should reject gracefully
        assert not connection_result.success
        assert connection_result.error is not None
        
    @pytest.mark.resilience
    @pytest.mark.auth
    async def test_permission_denied_propagation(self, service_orchestrator, real_websocket_client:
                                                error_correlation_context):
        """Test permission denied error propagation."""
        # Create token with limited permissions (simulated)
        limited_token = "limited_permissions_token"
        
        # Connect and attempt privileged operation
        connection_result = await real_websocket_client.connect(limited_token)
        
        if connection_result.success:
            # Attempt privileged operation
            message_result = await real_websocket_client.send_message({
                "type": "admin_command",
                "command": "delete_all_data"
            })
            
            # Should be denied
            assert not message_result.success or "permission" in str(message_result.response).lower()
            
    @pytest.mark.resilience
    @pytest.mark.auth
    async def test_concurrent_auth_failures(self, service_orchestrator, real_websocket_client:
                                          error_correlation_context):
        """Test handling of concurrent auth failures."""
        invalid_tokens = [f"invalid_token_{i}" for i in range(5)]
        
        # Attempt concurrent connections
        tasks = []
        for token in invalid_tokens:
            task = real_websocket_client.connect(token)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should fail gracefully
        for result in results:
            if hasattr(result, 'success'):
                assert not result.success
            # Exceptions are also acceptable for invalid auth
