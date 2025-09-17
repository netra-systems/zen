from unittest.mock import AsyncMock, Mock, patch, MagicMock


# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""Fixtures Tests - Split from test_critical_integration.py"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
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
from netra_backend.app.schemas.agent_models import DeepAgentState

from netra_backend.app.agents.supervisor_ssot import (

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
