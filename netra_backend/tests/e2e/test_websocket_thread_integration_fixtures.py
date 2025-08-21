"""Fixtures Tests - Split from test_websocket_thread_integration.py"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession
from ws_manager import manager
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.schemas.websocket_message_types import WebSocketMessage

def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    manager_mock = Mock()
    manager_mock.send_message = AsyncMock()
    manager_mock.broadcast_to_thread = AsyncMock()
    manager_mock.connect_user_to_thread = AsyncMock()
    manager_mock.disconnect_user_from_thread = AsyncMock()
    
    with patch('app.ws_manager.manager', manager_mock):
        yield manager_mock

def mock_thread_service():
    """Mock thread service for testing."""
    service = Mock(spec=ThreadService)
    service.create_thread = AsyncMock()
    service.switch_thread = AsyncMock()
    service.delete_thread = AsyncMock()
    service.create_run = AsyncMock()
    service.get_or_create_thread = AsyncMock()
    return service
# )  # Orphaned closing parenthesis