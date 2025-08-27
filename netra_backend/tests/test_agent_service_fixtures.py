"""Fixtures for agent service testing.

This module provides pytest fixtures for testing agent services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from netra_backend.tests.test_agent_service_mock_classes import MockOrchestrator, MockAgent


@pytest.fixture
def resilient_orchestrator():
    """Create a resilient orchestrator for testing."""
    orchestrator = MockOrchestrator()
    orchestrator.error_threshold = 3
    orchestrator.recovery_timeout = 5.0
    return orchestrator


@pytest.fixture  
def mock_agent():
    """Create a mock agent for testing."""
    return MockAgent("test_agent_123")


@pytest.fixture
def error_prone_agent():
    """Create an agent that simulates errors."""
    agent = MockAgent("error_agent")
    
    async def failing_process(request):
        agent.error_count += 1
        if agent.error_count < 3:
            raise Exception(f"Simulated error {agent.error_count}")
        return {"status": "success", "result": "recovered"}
    
    agent.process_request = failing_process
    return agent


@pytest.fixture
def orchestrator():
    """Create a standard orchestrator for testing."""
    orchestrator = MockOrchestrator()
    # Don't override metrics - use the complete initialization from MockOrchestrator
    return orchestrator


@pytest.fixture
def circuit_breaker_config():
    """Configuration for circuit breaker testing."""
    return {
        "failure_threshold": 3,
        "timeout": 5.0,
        "recovery_timeout": 10.0,
        "max_retry_attempts": 3
    }


def verify_orchestration_metrics(orchestrator, expected_agents=None, expected_tasks=None):
    """Verify orchestration metrics match expected values."""
    if expected_agents is not None:
        assert orchestrator.metrics["agents_created"] == expected_agents
    if expected_tasks is not None:
        assert orchestrator.metrics["tasks_executed"] == expected_tasks
    return True


@pytest.fixture
def agent_service(mock_supervisor):
    """Create a real agent service for testing with mocked dependencies."""
    from netra_backend.app.services.agent_service import AgentService
    # Create real service with mocked supervisor for integration testing
    service = AgentService(mock_supervisor)
    return service


@pytest.fixture
def mock_agent_service():
    """Create a mock agent service for testing."""
    from netra_backend.app.services.agent_service import AgentService
    # Mock: Agent service isolation for testing without LLM agent execution
    service = MagicMock(spec=AgentService)
    # Mock: Generic component isolation for controlled unit testing
    service.initialize = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.shutdown = AsyncMock()
    # Mock: Async component isolation for testing without real async operations
    service.execute = AsyncMock(return_value={"status": "completed", "result": "test result"})
    return service


@pytest.fixture  
def mock_supervisor():
    """Create a mock supervisor for testing."""
    # Mock: Generic component isolation for controlled unit testing
    supervisor = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    supervisor.run = AsyncMock(return_value={"status": "completed", "result": "supervised result"})
    # Mock: Generic component isolation for controlled unit testing
    supervisor.initialize = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    supervisor.shutdown = AsyncMock()
    return supervisor


@pytest.fixture
def mock_thread_service():
    """Create a mock thread service for testing.""" 
    # Mock: Generic component isolation for controlled unit testing
    thread_service = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    thread_service.get_thread = AsyncMock(return_value={"id": "thread1", "name": "test thread"})
    # Mock: Async component isolation for testing without real async operations
    thread_service.create_thread = AsyncMock(return_value={"id": "thread1", "name": "new thread"})
    return thread_service


@pytest.fixture
def mock_message_handler():
    """Create a mock message handler for testing."""
    # Mock: Generic component isolation for controlled unit testing
    handler = MagicMock()
    # Mock: Async component isolation for testing without real async operations
    handler.handle_message = AsyncMock(return_value={"status": "handled"})
    # Mock: Generic component isolation for controlled unit testing
    handler.send_message = AsyncMock()
    return handler


def create_mock_request_model():
    """Create a mock request model for testing."""
    from netra_backend.app.schemas import RequestModel
    # Mock: Service component isolation for predictable testing behavior
    request = MagicMock(spec=RequestModel)
    request.message = "test message"
    request.user_request = "test message"  # Alias for message
    request.thread_id = "thread123"
    request.user_id = "user123"
    request.run_id = "run123"
    request.id = "request123"
    return request


def create_concurrent_request_models(count: int = 3):
    """Create multiple mock request models for concurrent testing."""
    requests = []
    for i in range(count):
        request = create_mock_request_model()
        request.message = f"test message {i}"
        request.thread_id = f"thread{i}"
        request.user_id = f"user{i}"
        request.run_id = f"run{i}"
        requests.append(request)
    return requests


def create_websocket_message(message_type: str = "chat", content: str = "test"):
    """Create a mock websocket message for testing."""
    return {
        "type": message_type,
        "content": content,
        "timestamp": "2023-01-01T00:00:00Z",
        "user_id": "user123"
    }


def verify_agent_execution_result(result, expected_status: str = "completed"):
    """Verify agent execution result matches expectations."""
    assert result is not None
    # Handle both dict and mock objects
    if hasattr(result, "get"):
        status = result.get("status")
    else:
        status = getattr(result, "status", None)
    assert status == expected_status
    return True