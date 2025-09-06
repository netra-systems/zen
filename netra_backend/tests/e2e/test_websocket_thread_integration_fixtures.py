from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Fixtures Tests - Split from test_websocket_thread_integration.py"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.websocket_core import get_websocket_manager as get_unified_manager
manager = get_unified_manager()

from netra_backend.app.schemas.websocket_message_types import WebSocketMessage
from netra_backend.app.services.agent_service import AgentService

from netra_backend.app.services.thread_service import ThreadService

def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    # Mock: Generic component isolation for controlled unit testing
    manager_mock = manager_mock_instance  # Initialize appropriate service
    # Mock: Generic component isolation for controlled unit testing
    manager_mock.send_message = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    manager_mock.broadcast_to_thread = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    manager_mock.connect_user_to_thread = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    manager_mock.disconnect_user_from_thread = AsyncMock()  # TODO: Use real service instance
    
    # Mock: Component isolation for testing without external dependencies
    with patch('app.ws_manager.manager', manager_mock):
        yield manager_mock

def mock_thread_service():
    """Mock thread service for testing."""
    # Mock: Component isolation for controlled unit testing
    service = Mock(spec = ThreadService)
    # Mock: Generic component isolation for controlled unit testing
    service.create_thread = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    service.switch_thread = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    service.delete_thread = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    service.create_run = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    service.get_or_create_thread = AsyncMock()  # TODO: Use real service instance
    return service
#   # Orphaned closing parenthesis