"""Fixtures Tests - Split from test_unified_message_flow.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone

# Add project root to path

from netra_backend.tests.unified.jwt_token_helpers import JWTTestHelper
from netra_backend.app.schemas.core_enums import WebSocketMessageType, AgentStatus
from logging_config import central_logger
from netra_backend.tests.services.test_ws_connection_mocks import MockWebSocket
import asyncio
from routes.utils.websocket_helpers import decode_token_payload
from starlette.websockets import WebSocketDisconnect
import tracemalloc
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent

# Add project root to path

def flow_tracker():
    """Create message flow tracker."""
    return MessageFlowTracker()

def mock_websocket():
    """Create mock WebSocket connection."""
    return MockWebSocket()

def mock_db_session():
    """Create mock database session."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session

def mock_security_service():
    """Create mock security service."""
    service = AsyncMock()
    service.decode_access_token = AsyncMock(return_value={"user_id": "test_user_123"})
    service.get_user_by_id = AsyncMock(return_value=Mock(id="test_user_123", is_active=True))
    return service

def mock_agent_service():
    """Create mock agent service."""
    service = AsyncMock() 
    service.handle_websocket_message = AsyncMock()
    return service
# )  # Orphaned closing parenthesis