"""Fixtures for agent service testing.

This module provides pytest fixtures for testing agent services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
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
    orchestrator.metrics = {
        "agents_created": 0,
        "tasks_executed": 0,
        "errors_handled": 0,
        "total_execution_time": 0.0
    }
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