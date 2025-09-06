from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Fixtures Tests - Split from test_critical_integration.py"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
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

from netra_backend.app.agents.supervisor_consolidated import (

SupervisorAgent as Supervisor)
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

@pytest.fixture
def setup_real_database():
    """Use real service instance."""
    # TODO: Initialize real service
    return None

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
            
        await asyncio.sleep(0)
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
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager = Mock()  # Initialize appropriate service

    # Mock: LLM service isolation for fast testing without API calls or rate limits
    llm_manager.call_llm = AsyncMock(side_effect=lambda *args, **kwargs: {"content": "test response"})

    # Mock: LLM service isolation for fast testing without API calls or rate limits
    llm_manager.ask_llm = AsyncMock(side_effect=lambda *args, **kwargs: "test response")
        
    # Real state persistence service
    state_service = StatePersistenceService()
        
    return {
        "websocket_manager": websocket_manager,
        "llm_manager": llm_manager,
        "state_service": state_service
    }
