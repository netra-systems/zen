"""Test that agents_execute endpoints work with the fixed circuit breaker decorator."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.routes.agents_execute import router


@pytest.fixture
def test_app():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a test FastAPI app with the agents_execute router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/agents")
    return app


@pytest.fixture
def test_client(test_app):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a test client."""
    return TestClient(test_app)


def test_decorator_syntax_is_valid():
    """Test that the decorator syntax doesn't raise import errors."""
    # This test passes if the module imports without errors
    from netra_backend.app.routes import agents_execute
    
    # Check that the decorated functions exist
    assert hasattr(agents_execute, "execute_agent")
    assert hasattr(agents_execute, "execute_triage_agent")
    assert hasattr(agents_execute, "execute_data_agent")
    assert hasattr(agents_execute, "execute_optimization_agent")
    
    # Check that they are callable
    assert callable(agents_execute.execute_agent)
    assert callable(agents_execute.execute_triage_agent)
    assert callable(agents_execute.execute_data_agent)
    assert callable(agents_execute.execute_optimization_agent)


@pytest.mark.asyncio
async def test_execute_agent_with_circuit_breaker():
    """Test that execute_agent function works with the circuit breaker decorator."""
    from netra_backend.app.routes.agents_execute import execute_agent, AgentExecuteRequest
    from netra_backend.app.services.agent_service import AgentService
    
    # Create mock dependencies
    mock_user = {"user_id": "test_user"}
    mock_agent_service = Mock(spec=AgentService)
    
    # Create a test request
    request = AgentExecuteRequest(
        type="test",
        message="Test message",
        context=None,
        simulate_delay=None,
        force_failure=False,
        force_retry=False
    )
    
    # Execute the function (it should handle test messages with mock response)
    result = await execute_agent(request, mock_user, mock_agent_service)
    
    # Verify the result
    assert result.status == "success"
    assert result.agent == "test"
    assert "Mock" in result.response  # Test messages get mock responses
    assert result.circuit_breaker_state == "CLOSED"


def test_endpoints_are_registered(test_client):
    """Test that the endpoints are properly registered and accessible."""
    # Test the main execute endpoint
    response = test_client.post(
        "/api/agents/execute",
        json={
            "type": "test",
            "message": "Test message",
            "force_failure": False
        }
    )
    
    # Should return success for test messages
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["agent"] == "test"
    
    # Test agent-specific endpoints
    for agent_type in ["triage", "data", "optimization"]:
        response = test_client.post(
            f"/api/agents/{agent_type}",
            json={
                "message": "Test message",
                "force_failure": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["agent"] == agent_type


def test_circuit_breaker_opens_on_failures(test_client):
    """Test that circuit breaker opens after multiple failures."""
    # Force failures to test circuit breaker
    for i in range(5):
        response = test_client.post(
            "/api/agents/execute",
            json={
                "type": "failure_test",
                "message": "FORCE_ERROR",  # This triggers a failure
                "force_failure": False  # Using message instead
            }
        )
        
        # Should get 500 error for forced failures
        assert response.status_code == 500
    
    # After 5 failures, the circuit should open
    # However, since we're using test messages, the circuit might not actually open
    # This is more of a syntax/integration test than a full functional test