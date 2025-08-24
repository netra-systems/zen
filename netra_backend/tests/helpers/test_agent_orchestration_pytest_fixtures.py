"""
Pytest fixtures for agent orchestration tests.

Contains pytest fixture definitions for agent service testing.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.tests.test_agent_orchestration_fixtures import (
    AgentOrchestrator,
    MockSupervisorAgent,
)

@pytest.fixture
def mock_supervisor():
    """Create mock supervisor agent."""
    return MockSupervisorAgent()

@pytest.fixture
def mock_thread_service():
    """Create mock thread service."""
    # Mock: Service component isolation for predictable testing behavior
    service = MagicMock(spec=ThreadService)
    # Mock: Generic component isolation for controlled unit testing
    service.get_or_create_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.get_thread_history = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.create_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.delete_thread = AsyncMock()
    return service

@pytest.fixture
def mock_message_handler():
    """Create mock message handler service."""
    # Mock: Service component isolation for predictable testing behavior
    handler = MagicMock(spec=MessageHandlerService)
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_start_agent = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_user_message = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_thread_history = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_stop_agent = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_create_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_switch_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_delete_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    handler.handle_list_threads = AsyncMock()
    return handler

@pytest.fixture
def agent_service(mock_supervisor):
    """Create agent service with mocked dependencies."""
    service = AgentService(mock_supervisor)
    # Mock: Service component isolation for predictable testing behavior
    service.message_handler = MagicMock(spec=MessageHandlerService)
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_thread_history = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_create_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_switch_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_delete_thread = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_list_threads = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_start_agent = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    service.message_handler.handle_user_message = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
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