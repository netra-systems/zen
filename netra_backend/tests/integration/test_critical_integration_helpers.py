from unittest.mock import Mock, patch, MagicMock

"""Utilities Tests - Split from test_critical_integration.py"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

import jwt
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.websockets import WebSocketState

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState

# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import ( )

# REMOVED_SYNTAX_ERROR: SupervisorAgent as Supervisor)
from netra_backend.app.db.base import Base
from netra_backend.app.db.models_postgres import Run
from netra_backend.app.schemas.agent import AgentStarted
from netra_backend.app.schemas import UserBase
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.run_repository import RunRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.services.websocket.message_handler import UserMessageHandler
from netra_backend.app.websocket_core import WebSocketManager

# REMOVED_SYNTAX_ERROR: class TestSyntaxFix:

    # REMOVED_SYNTAX_ERROR: """Test class for orphaned methods"""

# REMOVED_SYNTAX_ERROR: def _setup_supervisor_with_database(self, db_setup, infra, test_entities):

    # REMOVED_SYNTAX_ERROR: """Setup supervisor agent with database and infrastructure"""

    # Mock: Session state isolation for predictable testing
    # REMOVED_SYNTAX_ERROR: supervisor = Supervisor(db_setup["session"], infra["llm_manager"], infra["websocket_manager"], Mock()  # TODO: Use real service instance)

    # REMOVED_SYNTAX_ERROR: supervisor.thread_id = test_entities["thread"].id

    # REMOVED_SYNTAX_ERROR: supervisor.user_id = test_entities["user_id"]

    # REMOVED_SYNTAX_ERROR: return supervisor

# REMOVED_SYNTAX_ERROR: def _verify_agent_result(self, result):

    # REMOVED_SYNTAX_ERROR: """Verify the agent execution result"""

    # REMOVED_SYNTAX_ERROR: assert result != None

    # REMOVED_SYNTAX_ERROR: assert "optimization" in str(result).lower()

# REMOVED_SYNTAX_ERROR: def _verify_state_persistence(self):

    # REMOVED_SYNTAX_ERROR: """Verify state was saved correctly"""

    # REMOVED_SYNTAX_ERROR: assert self.mock_save_state.called

    # REMOVED_SYNTAX_ERROR: save_calls = self.mock_save_state.call_args_list

    # REMOVED_SYNTAX_ERROR: assert len(save_calls) >= 3  # At least triage, data, and optimization agents

# REMOVED_SYNTAX_ERROR: def _verify_websocket_messages(self, mock_websocket):

    # REMOVED_SYNTAX_ERROR: """Verify WebSocket messages were sent correctly"""

    # REMOVED_SYNTAX_ERROR: assert mock_websocket.send_json.called, "WebSocket should have sent JSON messages"

    # REMOVED_SYNTAX_ERROR: ws_messages = [call.args[0] for call in mock_websocket.send_json.call_args_list]

    # REMOVED_SYNTAX_ERROR: self._verify_agent_lifecycle_messages(ws_messages)

# REMOVED_SYNTAX_ERROR: def _verify_agent_lifecycle_messages(self, ws_messages):

    # REMOVED_SYNTAX_ERROR: """Verify agent lifecycle messages in WebSocket stream"""

    # REMOVED_SYNTAX_ERROR: has_started = any("agent_started" in str(msg) for msg in ws_messages)

    # REMOVED_SYNTAX_ERROR: has_updates = any("sub_agent_update" in str(msg) for msg in ws_messages)

    # REMOVED_SYNTAX_ERROR: has_completed = any("agent_completed" in str(msg) for msg in ws_messages)

    # REMOVED_SYNTAX_ERROR: assert has_started and has_updates and has_completed, "Missing required lifecycle messages"

# REMOVED_SYNTAX_ERROR: def _verify_supervisor_configuration(self, supervisor, test_entities):

    # REMOVED_SYNTAX_ERROR: """Verify supervisor was configured correctly"""

    # REMOVED_SYNTAX_ERROR: assert supervisor.thread_id == test_entities["thread"].id

    # REMOVED_SYNTAX_ERROR: assert supervisor.user_id == test_entities["user_id"]

# REMOVED_SYNTAX_ERROR: def _verify_message_sending(self, mock_websocket):

    # REMOVED_SYNTAX_ERROR: """Verify messages were sent correctly through WebSocket"""

    # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.assert_called()

    # REMOVED_SYNTAX_ERROR: sent_data = mock_websocket.send_json.call_args[0][0]

    # REMOVED_SYNTAX_ERROR: assert sent_data["type"] == "agent_request"

    # REMOVED_SYNTAX_ERROR: assert sent_data["payload"]["query"] == "Test authenticated request"

    # REMOVED_SYNTAX_ERROR: assert mock_websocket.send_json.call_count >= 2

# REMOVED_SYNTAX_ERROR: def _create_state_service(self, session):

    # REMOVED_SYNTAX_ERROR: """Create state persistence service with database session"""

    # REMOVED_SYNTAX_ERROR: state_service = StatePersistenceService()

    # REMOVED_SYNTAX_ERROR: state_service.db_session = session

    # REMOVED_SYNTAX_ERROR: return state_service

# REMOVED_SYNTAX_ERROR: def _get_triage_output(self):

    # REMOVED_SYNTAX_ERROR: """Get triage output for testing"""

    # REMOVED_SYNTAX_ERROR: return { )

    # REMOVED_SYNTAX_ERROR: "category": "optimization",

    # REMOVED_SYNTAX_ERROR: "analysis": "GPU optimization needed",

    # REMOVED_SYNTAX_ERROR: "priority": "high"

    
    # )  # Orphaned closing parenthesis