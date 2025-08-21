"""
Shared test fixtures and utilities for agent service testing.

MODULE PURPOSE:
Common test fixtures and helper utilities for agent service tests.
Provides reusable pytest fixtures and data builders to eliminate duplication.

CONTAINS:
- Pytest fixtures for agent service components
- Helper functions for test setup and verification
- Test data builders
- Common assertion helpers

COMPLIANCE:
- All functions ≤8 lines
- Module ≤300 lines
- No duplication across test files
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Add project root to path

from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app import schemas

from netra_backend.tests.services.test_agent_service_mock_classes import (
    AgentState,
    MockSupervisorAgent,
    AgentOrchestrator
)


@pytest.fixture
def mock_supervisor():
    """Create mock supervisor agent."""
    return MockSupervisorAgent()


@pytest.fixture
def mock_thread_service():
    """Create mock thread service with all required methods."""
    service = MagicMock(spec=ThreadService)
    service.get_or_create_thread = AsyncMock()
    service.get_thread_history = AsyncMock()
    service.create_thread = AsyncMock()
    service.delete_thread = AsyncMock()
    return service


@pytest.fixture
def mock_message_handler():
    """Create mock message handler service."""
    handler = MagicMock(spec=MessageHandlerService)
    _setup_message_handler_methods(handler)
    return handler


def _setup_message_handler_methods(handler):
    """Setup all message handler async methods."""
    handler.handle_start_agent = AsyncMock()
    handler.handle_user_message = AsyncMock()
    handler.handle_thread_history = AsyncMock()
    handler.handle_stop_agent = AsyncMock()
    handler.handle_create_thread = AsyncMock()
    handler.handle_switch_thread = AsyncMock()
    handler.handle_delete_thread = AsyncMock()
    handler.handle_list_threads = AsyncMock()


@pytest.fixture
def agent_service(mock_supervisor):
    """Create agent service with fully mocked dependencies."""
    service = AgentService(mock_supervisor)
    service.message_handler = MagicMock(spec=MessageHandlerService)
    _setup_message_handler_methods(service.message_handler)
    return service


@pytest.fixture
def orchestrator():
    """Create agent orchestrator for lifecycle testing."""
    return AgentOrchestrator()


@pytest.fixture
def resilient_orchestrator():
    """Create orchestrator with error recovery features."""
    orchestrator = AgentOrchestrator()
    orchestrator.error_recovery_enabled = True
    orchestrator.max_retries = 3
    orchestrator.retry_delay = 0.01
    return orchestrator


def create_mock_request_model(user_request: str = "Test request", thread_id: str = "test_thread", user_id: str = "test_user"):
    """Create mock request model with default values."""
    request_model = MagicMock()
    request_model.user_request = user_request
    request_model.id = thread_id
    request_model.user_id = user_id
    return request_model


def create_concurrent_request_models(count: int):
    """Create multiple request models for concurrent testing."""
    return [create_mock_request_model(f"Concurrent request {i}") for i in range(count)]


def create_websocket_message(message_type: str, payload: Dict[str, Any]):
    """Create WebSocket message with type and payload."""
    return {"type": message_type, "payload": payload}


def verify_agent_execution_result(result: Dict[str, Any], expected_status: str = "completed"):
    """Verify agent execution result has expected structure."""
    assert result["status"] == expected_status


def verify_orchestration_metrics(metrics: Dict[str, Any], expected_executions: int):
    """Verify orchestration metrics have expected values."""
    assert metrics["total_executions"] == expected_executions
    assert "success_rate" in metrics
    assert metrics["success_rate"] >= 0