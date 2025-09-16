"""
User-Friendly Error Message Tests.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: User Experience
- Value Impact: Provides actionable error messages to users
- Strategic/Revenue Impact: Reduces support tickets and improves user satisfaction
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.error_propagation_fixtures import (
    error_correlation_context,
    real_http_client,
    real_websocket_client,
    service_orchestrator,
    test_user,
)

@pytest.mark.asyncio
@pytest.mark.e2e
class TestUserFriendlyMessages:
    """Test user-friendly error message generation."""
    
    @pytest.mark.resilience
    async def test_authentication_error_messages(self, service_orchestrator, real_websocket_client:
                                                error_correlation_context):
        """Test user-friendly authentication error messages."""
        # Use invalid credentials
        invalid_token = "invalid_token_123"
        
        connection_result = await real_websocket_client.connect(invalid_token)
        
        if not connection_result.success:
            error_message = connection_result.error.lower()
            
            # Should be user-friendly, not technical
            assert "authentication failed" in error_message or \
                   "invalid credentials" in error_message or \
                   "please log in again" in error_message
                   
            # Should not contain technical details
            assert "jwt" not in error_message
            assert "token" not in error_message or "invalid token" in error_message
            assert "500" not in error_message
            
    @pytest.mark.resilience
    async def test_permission_error_messages(self, service_orchestrator, real_http_client:
                                           error_correlation_context):
        """Test user-friendly permission error messages."""
        # Attempt unauthorized operation
        response = await real_http_client.request(
            "DELETE",
            "/api/admin/delete_all_data",
            headers={"Authorization": "Bearer limited_token"}
        )
        
        if not response.success:
            error_message = str(response.error).lower()
            
            # Should explain what user can't do
            assert "permission" in error_message or \
                   "not authorized" in error_message or \
                   "access denied" in error_message
                   
            # Should suggest next steps
            assert "contact administrator" in error_message or \
                   "insufficient privileges" in error_message
                   
    @pytest.mark.resilience
    async def test_validation_error_messages(self, service_orchestrator, real_http_client:
                                           error_correlation_context):
        """Test user-friendly validation error messages."""
        # Send invalid data
        response = await real_http_client.request(
            "POST",
            "/api/user/create",
            json={
                "email": "invalid-email",
                "password": "123",  # Too short
                "age": -5  # Invalid age
            }
        )
        
        if not response.success:
            error_message = str(response.error).lower()
            
            # Should explain specific validation issues
            assert "email" in error_message or "invalid format" in error_message
            assert "password" in error_message or "too short" in error_message
            
            # Should not contain technical validation details
            assert "regex" not in error_message
            assert "schema" not in error_message
            
    @pytest.mark.resilience
    async def test_rate_limit_error_messages(self, service_orchestrator, real_http_client:
                                           error_correlation_context):
        """Test user-friendly rate limit error messages."""
        # Send rapid requests to trigger rate limit
        tasks = []
        for i in range(20):
            task = real_http_client.request(
                "GET",
                "/api/rate_limited_endpoint",
                headers={"X-User-ID": error_correlation_context.user_id}
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for rate limit messages
        rate_limited = [r for r in results if hasattr(r, 'success') and not r.success]
        
        for result in rate_limited:
            if "rate" in str(result.error).lower():
                error_message = str(result.error).lower()
                
                # Should explain rate limit clearly
                assert "too many requests" in error_message or \
                       "rate limit exceeded" in error_message
                       
                # Should suggest when to retry
                assert "try again" in error_message or \
                       "wait" in error_message
                       
    @pytest.mark.resilience
    async def test_service_unavailable_messages(self, service_orchestrator, real_http_client:
                                              error_correlation_context):
        """Test user-friendly service unavailable messages."""
        # Try to connect to unavailable service
        unavailable_client = RealHTTPClient("http://localhost:9999")
        
        try:
            response = await unavailable_client.request("GET", "/api/test")
            
            if not response.success:
                error_message = str(response.error).lower()
                
                # Should be user-friendly
                assert "service unavailable" in error_message or \
                       "temporarily unavailable" in error_message or \
                       "connection failed" in error_message
                       
                # Should suggest action
                assert "try again later" in error_message or \
                       "please retry" in error_message or \
                       "check connection" in error_message
                       
        finally:
            await unavailable_client.close()
            
    @pytest.mark.resilience
    async def test_timeout_error_messages(self, service_orchestrator, real_http_client:
                                        error_correlation_context):
        """Test user-friendly timeout error messages."""
        # Request with very short timeout
        response = await real_http_client.request(
            "GET",
            "/api/slow_operation",
            timeout=0.1
        )
        
        if not response.success:
            error_message = str(response.error).lower()
            
            # Should explain timeout clearly
            assert "timeout" in error_message or \
                   "took too long" in error_message or \
                   "request timed out" in error_message
                   
            # Should suggest action
            assert "try again" in error_message or \
                   "check connection" in error_message
                   
            # Should not contain technical details
            assert "socket" not in error_message
            assert "tcp" not in error_message
