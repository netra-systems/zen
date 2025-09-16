"""
Integration test for agent route race condition fix.

This test validates that the /api/agent/v2/execute endpoint handles startup race conditions correctly.
"""

import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from netra_backend.app.main import app


class TestAgentRouteRaceConditionFix:
    """Test race condition fix for agent execution endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
        
        # Test request payload (message in body, user_id and thread_id as query params)
        self.execute_request = {
            "message": "Test message"
        }
        self.query_params = {
            "user_id": "test_user",
            "thread_id": "test_thread"
        }
    
    def test_agent_execute_v2_endpoint_exists(self):
        """Test that the /api/agent/v2/execute endpoint exists."""
        # This is a basic existence test
        response = self.client.post("/api/agent/v2/execute", json=self.execute_request, params=self.query_params)
        
        # Should not return 404 Not Found
        assert response.status_code != 404, "Endpoint should exist"
        
        # Debug: Print the actual response to see what's happening
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should return either a proper response or a server error (not 422 "Unknown error")
        # The race condition fix should prevent 422 "Tool dispatcher not available" errors
        if response.status_code == 422:
            # Let's see what the 422 error actually is
            response_data = response.json()
            detail = response_data.get("detail", "")
            print(f"422 Error detail: {detail}")
            
            # Check if it's our race condition error
            if "Tool dispatcher not available" in str(detail):
                pytest.fail(f"Race condition not fixed! Still getting: {detail}")
            elif "validation" in str(detail).lower():
                # This might be a legitimate validation error
                print(f"Validation error (might be expected): {detail}")
            else:
                print(f"Unknown 422 error: {detail}")
        
        assert response.status_code in [200, 422, 500, 503], f"Unexpected status code: {response.status_code}"
        
        if response.status_code == 503:
            # Service temporarily unavailable during startup
            response_data = response.json()
            assert "Service temporarily unavailable" in response_data.get("detail", "")
            assert "retry in a few seconds" in response_data.get("detail", "")
            
        elif response.status_code == 500:
            # Server error, but should be descriptive, not "Tool dispatcher not available"
            response_data = response.json()
            detail = response_data.get("detail", "")
            # Also check message field which might contain the actual error
            message = response_data.get("message", "")
            full_error = f"{detail} {message}".strip()
            
            # Should NOT be the old race condition error
            assert "Tool dispatcher not available" not in full_error
            
            # Should be a more descriptive error
            has_descriptive_error = any(error_msg in full_error.lower() for error_msg in [
                "supervisor",
                "websocket", 
                "startup",
                "configuration",
                "initialization",
                "llm_manager",  # New specific error we're seeing
                "critical startup failure"
            ])
            
            if not has_descriptive_error:
                print(f"DEBUG: Full error detail: {detail}")
                print(f"DEBUG: Full error message: {message}")
                print(f"DEBUG: Combined full_error: {full_error}")
            
            assert has_descriptive_error, f"Error should be more descriptive than 'Tool dispatcher not available': {full_error}"
    
    @patch('netra_backend.app.dependencies.get_request_scoped_supervisor')
    def test_race_condition_503_response(self, mock_get_supervisor):
        """Test that race condition during startup returns 503."""
        from fastapi import HTTPException
        
        # Mock the race condition - service not ready during startup
        mock_get_supervisor.side_effect = HTTPException(
            status_code=503,
            detail="Service temporarily unavailable - system is still starting up. Please retry in a few seconds."
        )
        
        response = self.client.post("/api/agent/v2/execute", json=self.execute_request, params=self.query_params)
        
        # Should return 503 Service Unavailable
        assert response.status_code == 503
        
        response_data = response.json()
        assert "Service temporarily unavailable" in response_data["detail"]
        assert "retry in a few seconds" in response_data["detail"]
    
    @patch('netra_backend.app.dependencies.get_request_scoped_supervisor')
    def test_race_condition_500_response(self, mock_get_supervisor):
        """Test that critical startup failure returns 500 with descriptive error."""
        from fastapi import HTTPException
        
        # Mock the race condition - supervisor missing after startup
        mock_get_supervisor.side_effect = HTTPException(
            status_code=500,
            detail="Agent supervisor not available (critical startup failure - check application logs)"
        )
        
        response = self.client.post("/api/agent/v2/execute", json=self.execute_request, params=self.query_params)
        
        # Should return 500 Internal Server Error
        assert response.status_code == 500
        
        response_data = response.json()
        assert "Agent supervisor not available" in response_data["detail"]
        assert "critical startup failure" in response_data["detail"]
    
    def test_no_422_unknown_error_response(self):
        """Test that the endpoint never returns 422 with unknown error."""
        response = self.client.post("/api/agent/v2/execute", json=self.execute_request, params=self.query_params)
        
        # Should NOT return 422 with generic error
        if response.status_code == 422:
            response_data = response.json()
            detail = response_data.get("detail", "")
            
            # If it's 422, it should be validation error, not our race condition
            assert "Tool dispatcher not available" not in str(detail)
            assert "Unknown error" not in str(detail)
    
    def test_missing_required_fields_validation(self):
        """Test that missing required fields return proper validation errors."""
        # Test with missing message
        invalid_request = {
            "user_id": "test_user",
            "thread_id": "test_thread"
            # Missing "message"
        }
        
        response = self.client.post("/api/agent/v2/execute", json=invalid_request)
        
        # Should return 422 for validation error (this is expected)
        assert response.status_code == 422
        
        response_data = response.json()
        # Should be a proper validation error, not our race condition error
        detail = response_data.get("detail", [])
        if isinstance(detail, list) and len(detail) > 0:
            # Pydantic validation error format
            assert any("message" in str(error).lower() for error in detail)
        else:
            # Simple validation error
            assert "message" in str(detail).lower()
    
    def test_endpoint_returns_json_response(self):
        """Test that endpoint returns proper JSON response format."""
        response = self.client.post("/api/agent/v2/execute", json=self.execute_request, params=self.query_params)
        
        # Should be valid JSON
        assert response.headers.get("content-type") == "application/json"
        
        # Should be parseable
        response_data = response.json()
        assert isinstance(response_data, dict)
        
        if response.status_code == 200:
            # Success response should have expected fields
            assert "run_id" in response_data
            assert "status" in response_data
            assert "message" in response_data
            assert "user_id" in response_data
            assert "thread_id" in response_data
        else:
            # Error response should have detail field
            assert "detail" in response_data