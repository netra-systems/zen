"""Core Tests - Split from test_critical_integration.py"""

import pytest
import pytest_asyncio
import asyncio
import json
import jwt
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.services.agent_service import AgentService
from app.services.websocket.message_handler import BaseMessageHandler
from app.services.state_persistence import StatePersistenceService
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.run_repository import RunRepository
from app.ws_manager import WebSocketManager
from app.schemas.registry import (
from app.schemas.Agent import AgentStarted
from starlette.websockets import WebSocketState
from app.schemas.registry import UserBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile
import os
from app.db.models_postgres import Run
import time

    def setup_real_database(self):
        """Setup a real in-memory SQLite database for integration testing"""
        async def _setup():
            # Create temporary database
            db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            db_url = f"sqlite+aiosqlite:///{db_file.name}"
            
            # Create engine and session
            engine = create_async_engine(db_url, echo=False)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Create tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Create session
            session = async_session()
            
            return {
                "session": session,
                "engine": engine,
                "db_file": db_file.name
            }
        return _setup

    def setup_integration_infrastructure(self):
        """Setup integrated infrastructure for testing"""
        # Real WebSocket Manager
        websocket_manager = WebSocketManager()
        
        # Mock LLM Manager with realistic responses
        llm_manager = Mock()
        llm_manager.call_llm = AsyncMock(side_effect=self._mock_llm_response)
        llm_manager.ask_llm = AsyncMock(side_effect=self._mock_ask_llm_response)
        
        # Real state persistence service
        state_service = StatePersistenceService()
        
        return {
            "websocket_manager": websocket_manager,
            "llm_manager": llm_manager,
            "state_service": state_service
        }

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
