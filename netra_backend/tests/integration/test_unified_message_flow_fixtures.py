"""Fixtures Tests - Split from test_unified_message_flow.py"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
import tracemalloc
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, Mock, patch

import pytest
from logging_config import central_logger
from app.routes.utils.websocket_helpers import decode_token_payload
from starlette.websockets import WebSocketDisconnect

from app.agents.supervisor_consolidated import SupervisorAgent
from app.schemas.core_enums import AgentStatus, WebSocketMessageType
from .test_ws_connection_mocks import MockWebSocket

# Add project root to path
from tests.jwt_token_helpers import JWTTestHelper

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