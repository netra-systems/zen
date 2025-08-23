"""Utilities Tests - Split from test_critical_integration.py"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import jwt
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.websockets import WebSocketState

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import (

    SupervisorAgent as Supervisor,

)
from netra_backend.app.db.base import Base
from netra_backend.app.db.models_postgres import Run
from netra_backend.app.schemas.Agent import AgentStarted
from netra_backend.app.schemas.registry import UserBase
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.run_repository import RunRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

class TestSyntaxFix:

    """Test class for orphaned methods"""

    def _setup_supervisor_with_database(self, db_setup, infra, test_entities):

        """Setup supervisor agent with database and infrastructure"""

        supervisor = Supervisor(db_setup["session"], infra["llm_manager"], infra["websocket_manager"], Mock())

        supervisor.thread_id = test_entities["thread"].id

        supervisor.user_id = test_entities["user_id"]

        return supervisor

    def _verify_agent_result(self, result):

        """Verify the agent execution result"""

        assert result != None

        assert "optimization" in str(result).lower()

    def _verify_state_persistence(self):

        """Verify state was saved correctly"""

        assert self.mock_save_state.called

        save_calls = self.mock_save_state.call_args_list

        assert len(save_calls) >= 3  # At least triage, data, and optimization agents

    def _verify_websocket_messages(self, mock_websocket):

        """Verify WebSocket messages were sent correctly"""

        assert mock_websocket.send_json.called, "WebSocket should have sent JSON messages"

        ws_messages = [call.args[0] for call in mock_websocket.send_json.call_args_list]

        self._verify_agent_lifecycle_messages(ws_messages)

    def _verify_agent_lifecycle_messages(self, ws_messages):

        """Verify agent lifecycle messages in WebSocket stream"""

        has_started = any("agent_started" in str(msg) for msg in ws_messages)

        has_updates = any("sub_agent_update" in str(msg) for msg in ws_messages)

        has_completed = any("agent_completed" in str(msg) for msg in ws_messages)

        assert has_started and has_updates and has_completed, "Missing required lifecycle messages"

    def _verify_supervisor_configuration(self, supervisor, test_entities):

        """Verify supervisor was configured correctly"""

        assert supervisor.thread_id == test_entities["thread"].id

        assert supervisor.user_id == test_entities["user_id"]

    def _verify_message_sending(self, mock_websocket):

        """Verify messages were sent correctly through WebSocket"""

        mock_websocket.send_json.assert_called()

        sent_data = mock_websocket.send_json.call_args[0][0]

        assert sent_data["type"] == "agent_request"

        assert sent_data["payload"]["query"] == "Test authenticated request"

        assert mock_websocket.send_json.call_count >= 2

    def _create_state_service(self, session):

        """Create state persistence service with database session"""

        state_service = StatePersistenceService()

        state_service.db_session = session

        return state_service

    def _get_triage_output(self):

        """Get triage output for testing"""

        return {

            "category": "optimization",

            "analysis": "GPU optimization needed",

            "priority": "high"

        }
# )  # Orphaned closing parenthesis