"""
Test suite for factory consolidation with performance optimizations.

Business Value Justification:
- Segment: Platform Quality Assurance  
- Business Goal: Stability and Reliability
- Value Impact: Ensures consolidated factory maintains all functionality
- Strategic Impact: Validates performance improvements without regressions
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserWebSocketEmitter,
    get_agent_instance_factory,
    configure_agent_instance_factory
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.factory_performance_config import (
    FactoryPerformanceConfig,
    set_factory_performance_config
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self):
        super().__init__()
        self.executed = False

    async def execute(self, state: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        self.executed = True
        return {"result": "success"}


@pytest.fixture
async def mock_websocket_bridge():
    """Mock WebSocket bridge for testing."""
    bridge = AsyncMock(spec=AgentWebSocketBridge)
    bridge.notify_agent_started = AsyncMock(return_value=True)
    bridge.notify_agent_thinking = AsyncMock(return_value=True)
    bridge.notify_tool_executing = AsyncMock(return_value=True)
    bridge.notify_tool_completed = AsyncMock(return_value=True)
    bridge.notify_agent_completed = AsyncMock(return_value=True)
    await asyncio.sleep(0)
    return bridge


@pytest.fixture
async def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    await asyncio.sleep(0)
    return MagicMock(spec=WebSocketManager)


@pytest.fixture
async def mock_agent_class_registry():
    """Mock agent class registry for testing."""
    # Create a real registry but populate it with test agents
    from netra_backend.app.agents.supervisor.agent_class_registry import create_test_registry
    registry = create_test_registry()

    # Register our mock agent for testing
    registry.register("test_agent", MockAgent, "Test agent for unit testing")
    registry.freeze()

    await asyncio.sleep(0)
    return registry


@pytest.fixture
async def mock_db_session():
    """Mock database session for testing."""
    await asyncio.sleep(0)
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def minimal_performance_config():
    """Minimal performance configuration for testing."""
    config = FactoryPerformanceConfig.minimal()
    set_factory_performance_config(config)
    return config


@pytest.fixture
def balanced_performance_config():
    """Balanced performance configuration for testing."""
    config = FactoryPerformanceConfig.balanced()
    set_factory_performance_config(config)
    return config


@pytest.fixture
def maximum_performance_config():
    """Maximum performance configuration for testing."""
    config = FactoryPerformanceConfig.maximum_performance()
    set_factory_performance_config(config)
    return config


class TestFactoryConsolidation:
    """Test suite for factory consolidation."""

    @pytest.mark.asyncio
    async def test_factory_initialization_with_minimal_config(self, minimal_performance_config):
        """Test factory initialization with minimal configuration."""
        factory = AgentInstanceFactory()

        assert factory._performance_config == minimal_performance_config
        assert factory._emitter_pool is None

    @pytest.mark.asyncio
    async def test_factory_configuration(self, mock_websocket_bridge, mock_agent_class_registry):
        """Test factory configuration with required components."""
        factory = AgentInstanceFactory()

        factory.configure(
            agent_class_registry=mock_agent_class_registry,
            websocket_bridge=mock_websocket_bridge
        )

        assert factory._websocket_bridge == mock_websocket_bridge
        assert factory._agent_class_registry == mock_agent_class_registry

    @pytest.mark.asyncio  
    async def test_user_context_creation(self, mock_websocket_bridge, mock_db_session, balanced_performance_config, mock_agent_class_registry):
        """Test user execution context creation with pooling."""
        factory = AgentInstanceFactory()
        factory.configure(agent_class_registry=mock_agent_class_registry, websocket_bridge=mock_websocket_bridge)

        user_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        context = await factory.create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            db_session=mock_db_session
        )

        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.run_id == run_id
        assert context.db_session == mock_db_session

    @pytest.mark.asyncio
    async def test_websocket_emitter_notifications(self, mock_websocket_bridge):
        """Test WebSocket emitter sends all required notifications."""
        emitter = UserWebSocketEmitter(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            websocket_bridge=mock_websocket_bridge
        )

        # Test all 5 critical WebSocket events
        assert await emitter.notify_agent_started("test_agent") == True
        assert await emitter.notify_agent_thinking("test_agent", "reasoning") == True
        assert await emitter.notify_tool_executing("test_agent", "test_tool") == True
        assert await emitter.notify_tool_completed("test_agent", "test_tool", True) == True
        assert await emitter.notify_agent_completed("test_agent", {"result": "done"}) == True

        # Verify bridge was called
        mock_websocket_bridge.notify_agent_started.assert_called_once()
        mock_websocket_bridge.notify_agent_thinking.assert_called_once()
        mock_websocket_bridge.notify_tool_executing.assert_called_once()
        mock_websocket_bridge.notify_tool_completed.assert_called_once()
        mock_websocket_bridge.notify_agent_completed.assert_called_once()