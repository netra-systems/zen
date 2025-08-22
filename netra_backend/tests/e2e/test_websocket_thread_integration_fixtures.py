"""Fixtures Tests - Split from test_websocket_thread_integration.py"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from ws_manager import manager

from netra_backend.app.schemas.websocket_message_types import WebSocketMessage
from netra_backend.app.services.agent_service import AgentService

# Add project root to path
from netra_backend.app.services.thread_service import ThreadService

# Add project root to path

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