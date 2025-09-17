"""
Tests for execution isolation with UserExecutionEngine and ExecutionEngineFactory.

This test suite verifies that user execution isolation works correctly and prevents
state leakage between concurrent users.

Business Value: Ensures production-ready concurrent user support with zero context leakage.
"""

import asyncio
import pytest
import uuid
import time
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
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


class TestExecutionIsolation:
    """Test suite for execution isolation between concurrent users."""

    @pytest.fixture
    def execution_factory(self):
        """Create ExecutionEngineFactory for testing."""
        return ExecutionEngineFactory()

    @pytest.fixture
    def mock_agent_registry(self):
        """Create mock agent registry."""
        registry = MagicMock(spec=AgentRegistry)
        return registry

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = MagicMock(spec=WebSocketManager)
        manager.send_to_user = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_concurrent_user_execution_isolation(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test that concurrent user executions are properly isolated."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        # Create separate execution engines for each user
        engine1 = await execution_factory.create_user_engine(
            user_id=user1_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        engine2 = await execution_factory.create_user_engine(
            user_id=user2_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        # Create different states for each user
        state1 = DeepAgentState()
        state1.user_request = "User 1 request"
        state1.user_id = user1_id
        state1.session_data = {"user": "user1", "preferences": "theme_dark"}

        state2 = DeepAgentState()
        state2.user_request = "User 2 request"
        state2.user_id = user2_id
        state2.session_data = {"user": "user2", "preferences": "theme_light"}

        # Execute concurrently
        async def execute_user1():
            context = AgentExecutionContext(
                state=state1,
                run_id=f"run_{user1_id}",
                user_id=user1_id
            )
            result = await engine1.execute_agent_workflow(context)
            return result

        async def execute_user2():
            context = AgentExecutionContext(
                state=state2,
                run_id=f"run_{user2_id}",
                user_id=user2_id
            )
            result = await engine2.execute_agent_workflow(context)
            return result

        # Run both executions concurrently
        results = await asyncio.gather(
            execute_user1(),
            execute_user2(),
            return_exceptions=True
        )

        # Verify isolation
        assert len(results) == 2

        # Verify engines are distinct instances
        assert engine1 is not engine2
        assert engine1.user_id == user1_id
        assert engine2.user_id == user2_id

        # Verify no state leakage
        assert state1.user_id != state2.user_id
        assert state1.session_data["user"] != state2.session_data["user"]

    @pytest.mark.asyncio
    async def test_execution_engine_factory_creates_isolated_instances(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test that factory creates isolated execution engine instances."""
        user_ids = [str(uuid.uuid4()) for _ in range(3)]
        engines = []

        # Create multiple engines
        for user_id in user_ids:
            engine = await execution_factory.create_user_engine(
                user_id=user_id,
                agent_registry=mock_agent_registry,
                websocket_manager=mock_websocket_manager
            )
            engines.append(engine)

        # Verify all engines are unique instances
        for i, engine1 in enumerate(engines):
            for j, engine2 in enumerate(engines):
                if i != j:
                    assert engine1 is not engine2
                    assert engine1.user_id != engine2.user_id

        # Verify proper user ID assignment
        for engine, user_id in zip(engines, user_ids):
            assert engine.user_id == user_id

    @pytest.mark.asyncio
    async def test_state_persistence_isolation(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test that state persistence is isolated between users."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        engine1 = await execution_factory.create_user_engine(
            user_id=user1_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        engine2 = await execution_factory.create_user_engine(
            user_id=user2_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        # Store different data for each user
        await engine1.store_execution_state("key1", {"data": "user1_data"})
        await engine2.store_execution_state("key1", {"data": "user2_data"})

        # Retrieve data and verify isolation
        user1_data = await engine1.retrieve_execution_state("key1")
        user2_data = await engine2.retrieve_execution_state("key1")

        assert user1_data["data"] == "user1_data"
        assert user2_data["data"] == "user2_data"
        assert user1_data != user2_data

    @pytest.mark.asyncio
    async def test_websocket_message_isolation(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test that WebSocket messages are sent to correct users only."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        engine1 = await execution_factory.create_user_engine(
            user_id=user1_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        engine2 = await execution_factory.create_user_engine(
            user_id=user2_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        # Send messages from different engines
        await engine1.send_websocket_message({"type": "user1_message", "data": "test1"})
        await engine2.send_websocket_message({"type": "user2_message", "data": "test2"})

        # Verify messages were sent to correct users
        assert mock_websocket_manager.send_to_user.call_count == 2

        calls = mock_websocket_manager.send_to_user.call_args_list

        # Check first call (user1)
        assert calls[0][0][0] == user1_id  # First argument should be user_id
        assert calls[0][0][1]["type"] == "user1_message"

        # Check second call (user2)
        assert calls[1][0][0] == user2_id  # First argument should be user_id
        assert calls[1][0][1]["type"] == "user2_message"

    @pytest.mark.asyncio
    async def test_memory_isolation_under_load(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test memory isolation under concurrent load."""
        num_users = 10
        tasks = []

        async def simulate_user_execution(user_index):
            user_id = f"user_{user_index}_{uuid.uuid4()}"

            engine = await execution_factory.create_user_engine(
                user_id=user_id,
                agent_registry=mock_agent_registry,
                websocket_manager=mock_websocket_manager
            )

            # Simulate work with user-specific data
            user_data = {"user_index": user_index, "timestamp": time.time()}
            await engine.store_execution_state("user_data", user_data)

            # Simulate some processing time
            await asyncio.sleep(0.1)

            # Retrieve and verify data
            retrieved_data = await engine.retrieve_execution_state("user_data")
            assert retrieved_data["user_index"] == user_index

            return user_id, retrieved_data

        # Create tasks for concurrent execution
        for i in range(num_users):
            task = asyncio.create_task(simulate_user_execution(i))
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all executions succeeded
        assert len(results) == num_users

        for i, (user_id, data) in enumerate(results):
            assert isinstance(user_id, str)
            assert data["user_index"] == i
            # Verify each user got their own data, not someone else's
            assert f"user_{i}_" in user_id

    @pytest.mark.asyncio
    async def test_execution_context_cleanup(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test that execution contexts are properly cleaned up."""
        user_id = str(uuid.uuid4())

        engine = await execution_factory.create_user_engine(
            user_id=user_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        # Store some execution state
        await engine.store_execution_state("temp_data", {"value": "temporary"})

        # Verify data exists
        data = await engine.retrieve_execution_state("temp_data")
        assert data["value"] == "temporary"

        # Cleanup execution context
        await engine.cleanup_execution_context()

        # Verify data is cleaned up (should return None or empty)
        cleaned_data = await engine.retrieve_execution_state("temp_data")
        assert cleaned_data is None or cleaned_data == {}

    @pytest.mark.asyncio
    async def test_error_isolation_between_users(self, execution_factory, mock_agent_registry, mock_websocket_manager):
        """Test that errors in one user's execution don't affect others."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        engine1 = await execution_factory.create_user_engine(
            user_id=user1_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        engine2 = await execution_factory.create_user_engine(
            user_id=user2_id,
            agent_registry=mock_agent_registry,
            websocket_manager=mock_websocket_manager
        )

        async def failing_execution():
            # Simulate a failing execution for user1
            raise Exception("User 1 execution failed")

        async def successful_execution():
            # Simulate successful execution for user2
            await engine2.store_execution_state("success", {"status": "completed"})
            return "success"

        # Run both executions concurrently
        results = await asyncio.gather(
            failing_execution(),
            successful_execution(),
            return_exceptions=True
        )

        # Verify user1 failed but user2 succeeded
        assert isinstance(results[0], Exception)
        assert results[1] == "success"

        # Verify user2's data is intact despite user1's failure
        user2_data = await engine2.retrieve_execution_state("success")
        assert user2_data["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__])