"""Fixtures Tests - Split from test_critical_integration.py"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
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
from netra_backend.app.ws_manager import WebSocketManager

@pytest.fixture

def setup_real_database():

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

@pytest.fixture

def setup_integration_infrastructure():

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
