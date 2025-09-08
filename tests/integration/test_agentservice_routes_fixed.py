"""
Test to verify that the AgentService route parameter fixes work correctly.

This test verifies that the routes no longer call AgentService methods with incorrect parameters
and that they handle the correct method signatures properly.
"""

import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.routes.agents_execute import router


class TestAgentServiceRouteFixes:
    """Test class to verify that the AgentService route parameter fixes work."""

    @pytest.fixture
    def mock_supervisor(self):
        """Create a mock supervisor for testing."""
        supervisor = Mock(spec=SupervisorAgent)
        supervisor.run = AsyncMock(return_value="test response")
        supervisor.registry = Mock()
        return supervisor

    @pytest.fixture
    def mock_agent_service(self, mock_supervisor):
        """Create a mock AgentService that behaves like the real one."""
        service = Mock(spec=AgentService)
        
        # Mock the correct method signatures
        service.get_agent_status = AsyncMock(return_value={
            "user_id": "test-user",
            "status": "active", 
            "supervisor_available": True,
            "thread_service_available": True,
            "message_handler_available": True,
            "service_ready": True,
            "bridge_integrated": False
        })
        
        service.stop_agent = AsyncMock(return_value=True)
        
        service.start_agent = AsyncMock(return_value={
            "message": "Agent started successfully",
            "status": "success"
        })
        
        return service

    @pytest.fixture
    def app(self):
        """Create FastAPI app with agent routes for testing."""
        app = FastAPI()
        app.include_router(router, prefix="/api/agents")
        return app

    @pytest.fixture  
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_get_agent_status_route_calls_correct_method_signature(self, mock_agent_service, client):
        """Test that the get_agent_status route calls AgentService with correct parameters."""
        
        with patch("netra_backend.app.routes.agents_execute.get_agent_service_optional", return_value=mock_agent_service):
            with patch("netra_backend.app.routes.agents_execute.get_current_user_optional", return_value={"user_id": "test-user"}):
                
                # Make request to status endpoint with agent_id
                response = client.get("/api/agents/status?agent_id=test-agent-123")
                
                # Verify the service was called with correct signature (only user_id)
                mock_agent_service.get_agent_status.assert_called_once_with(user_id="test-user")
                
                # Verify response is successful
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, list)
                assert len(data) == 1
                assert data[0]["agent_id"] == "test-agent-123"
                assert data[0]["status"] == "running"  # mapped from "active"

    def test_stop_agent_route_calls_correct_method_signature(self, mock_agent_service, client):
        """Test that the stop_agent route calls AgentService with correct parameters."""
        
        with patch("netra_backend.app.routes.agents_execute.get_agent_service_optional", return_value=mock_agent_service):
            with patch("netra_backend.app.routes.agents_execute.get_current_user_optional", return_value={"user_id": "test-user"}):
                
                # Make request to stop endpoint
                response = client.post("/api/agents/stop", json={
                    "agent_id": "test-agent-123",
                    "reason": "test stop"
                })
                
                # Verify the service was called with correct signature (only user_id)
                mock_agent_service.stop_agent.assert_called_once_with(user_id="test-user")
                
                # Verify response is successful  
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["agent_id"] == "test-agent-123"
                assert data["action"] == "stop"

    def test_start_agent_route_calls_correct_method_signature(self, mock_agent_service, client):
        """Test that the start_agent route calls AgentService with correct parameters."""
        
        with patch("netra_backend.app.routes.agents_execute.get_agent_service_optional", return_value=mock_agent_service):
            with patch("netra_backend.app.routes.agents_execute.get_current_user_optional", return_value={"user_id": "test-user"}):
                
                # Make request to start endpoint
                response = client.post("/api/agents/start", json={
                    "agent_type": "triage",
                    "message": "test message",
                    "context": {"key": "value"}
                })
                
                # Verify the service was called with correct signature
                # Should be start_agent(request_model, run_id, stream_updates)
                mock_agent_service.start_agent.assert_called_once()
                
                call_args = mock_agent_service.start_agent.call_args
                assert len(call_args.args) == 0  # All keyword arguments
                assert "request_model" in call_args.kwargs
                assert "run_id" in call_args.kwargs  
                assert "stream_updates" in call_args.kwargs
                
                # Verify response is successful
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["action"] == "start"

    def test_cancel_agent_route_uses_stop_agent_fallback(self, mock_agent_service, client):
        """Test that the cancel_agent route uses stop_agent as fallback since cancel_agent doesn't exist."""
        
        with patch("netra_backend.app.routes.agents_execute.get_agent_service_optional", return_value=mock_agent_service):
            with patch("netra_backend.app.routes.agents_execute.get_current_user_optional", return_value={"user_id": "test-user"}):
                
                # Make request to cancel endpoint  
                response = client.post("/api/agents/cancel", json={
                    "agent_id": "test-agent-123",
                    "force": False
                })
                
                # Verify that stop_agent was called instead of cancel_agent
                mock_agent_service.stop_agent.assert_called_once_with(user_id="test-user")
                
                # Verify response mentions it's a cancel via stop
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "canceled successfully (via stop)" in data["message"]

    def test_routes_handle_service_unavailable_gracefully(self, client):
        """Test that routes handle unavailable AgentService gracefully without parameter errors."""
        
        with patch("netra_backend.app.routes.agents_execute.get_agent_service_optional", return_value=None):
            with patch("netra_backend.app.routes.agents_execute.get_current_user_optional", return_value={"user_id": "test-user"}):
                
                # All these requests should succeed with mock responses, no parameter errors
                
                # Status request
                response = client.get("/api/agents/status?agent_id=test-agent-123")
                assert response.status_code == 200
                assert response.json()[0]["status"] == "mock_status"
                
                # Stop request  
                response = client.post("/api/agents/stop", json={
                    "agent_id": "test-agent-123",
                    "reason": "test"
                })
                assert response.status_code == 200
                assert "Mock stop response" in response.json()["message"]
                
                # Start request
                response = client.post("/api/agents/start", json={
                    "agent_type": "triage", 
                    "message": "test"
                })
                assert response.status_code == 200
                assert "Mock start response" in response.json()["message"]
                
                # Cancel request
                response = client.post("/api/agents/cancel", json={
                    "agent_id": "test-agent-123"
                })
                assert response.status_code == 200
                assert "Mock cancel response" in response.json()["message"]

    def test_no_more_parameter_mismatch_errors(self, mock_agent_service, client):
        """
        Integration test to ensure no TypeError exceptions about unexpected keyword arguments.
        
        This test verifies the main fix - no more "unexpected keyword argument" errors.
        """
        
        # Mock service that would previously cause parameter errors
        error_service = Mock(spec=AgentService)
        
        # These should be the methods that are actually called (correct signatures)
        error_service.get_agent_status = AsyncMock(return_value={"user_id": "test", "status": "active"})
        error_service.stop_agent = AsyncMock(return_value=True)
        error_service.start_agent = AsyncMock(return_value={"message": "started"})
        
        with patch("netra_backend.app.routes.agents_execute.get_agent_service_optional", return_value=error_service):
            with patch("netra_backend.app.routes.agents_execute.get_current_user_optional", return_value={"user_id": "test-user"}):
                
                # These calls should NOT raise TypeError about unexpected keyword arguments
                
                response = client.get("/api/agents/status?agent_id=test-agent")
                assert response.status_code == 200
                
                response = client.post("/api/agents/stop", json={"agent_id": "test-agent"})
                assert response.status_code == 200
                
                response = client.post("/api/agents/start", json={"agent_type": "triage", "message": "test"})
                assert response.status_code == 200
                
                # Verify that all service methods were called with correct parameters
                error_service.get_agent_status.assert_called_with(user_id="test-user")
                error_service.stop_agent.assert_called_with(user_id="test-user") 
                error_service.start_agent.assert_called_once()  # Complex call structure, just verify it was called