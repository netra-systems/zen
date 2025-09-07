from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Fixtures Tests - Split from test_unified_message_flow.py"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import tracemalloc
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.websocket_helpers import decode_token_payload
from starlette.websockets import WebSocketDisconnect

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.schemas.core_enums import AgentStatus, WebSocketMessageType
# Removed WebSocket mock import - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

from netra_backend.tests.integration.jwt_token_helpers import JWTTestHelper
from test_framework.fixtures.message_flow import MessageFlowTracker

def flow_tracker():
    """Create message flow tracker."""
    return MessageFlowTracker()

def jwt_helper():
    """Create JWT test helper."""
    return JWTTestHelper()

def mock_websocket():
    """Create mock WebSocket connection."""
    return MockWebSocket()

def mock_db_session():
    """Create mock database session."""
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.execute = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.commit = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_session.rollback = AsyncMock()  # TODO: Use real service instance
    return mock_session

def mock_security_service():
    """Create mock security service."""
    # Mock: Generic component isolation for controlled unit testing
    service = AsyncMock()  # TODO: Use real service instance
    # Mock: Async component isolation for testing without real async operations
    service.decode_access_token = AsyncMock(return_value = {"user_id": "test_user_123"})
    # Mock: Async component isolation for testing without real async operations
    service.get_user_by_id = AsyncMock(return_value = Mock(id = "test_user_123", is_active = True))
    return service

def mock_agent_service():
    """Create mock agent service."""
    # Mock: Generic component isolation for controlled unit testing
    service = AsyncMock()  # TODO: Use real service instance 
    # Mock: Generic component isolation for controlled unit testing
    service.handle_websocket_message = AsyncMock()  # TODO: Use real service instance
    return service
