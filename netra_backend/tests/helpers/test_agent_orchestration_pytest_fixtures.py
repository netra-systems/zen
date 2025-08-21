"""
Pytest fixtures for agent orchestration tests.

Contains pytest fixture definitions for agent service testing.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import AsyncMock, MagicMock

# Add project root to path

from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.tests.helpers.test_agent_orchestration_fixtures import (

# Add project root to path
    MockSupervisorAgent, AgentOrchestrator
)


@pytest.fixture
def mock_supervisor():
    """Create mock supervisor agent."""
    return MockSupervisorAgent()


@pytest.fixture
def mock_thread_service():
    """Create mock thread service."""
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
    handler.handle_start_agent = AsyncMock()
    handler.handle_user_message = AsyncMock()
    handler.handle_thread_history = AsyncMock()
    handler.handle_stop_agent = AsyncMock()
    handler.handle_create_thread = AsyncMock()
    handler.handle_switch_thread = AsyncMock()
    handler.handle_delete_thread = AsyncMock()
    handler.handle_list_threads = AsyncMock()
    return handler


@pytest.fixture
def agent_service(mock_supervisor):
    """Create agent service with mocked dependencies."""
    service = AgentService(mock_supervisor)
    service.message_handler = MagicMock(spec=MessageHandlerService)
    service.message_handler.handle_thread_history = AsyncMock()
    service.message_handler.handle_create_thread = AsyncMock()
    service.message_handler.handle_switch_thread = AsyncMock()
    service.message_handler.handle_delete_thread = AsyncMock()
    service.message_handler.handle_list_threads = AsyncMock()
    service.message_handler.handle_start_agent = AsyncMock()
    service.message_handler.handle_user_message = AsyncMock()
    service.message_handler.handle_stop_agent = AsyncMock()
    return service


@pytest.fixture
def orchestrator():
    """Create agent orchestrator."""
    return AgentOrchestrator()


@pytest.fixture
def resilient_orchestrator():
    """Create orchestrator with error recovery features."""
    orchestrator = AgentOrchestrator()
    orchestrator.error_recovery_enabled = True
    orchestrator.max_retries = 3
    orchestrator.retry_delay = 0.01
    return orchestrator