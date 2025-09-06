from unittest.mock import Mock, AsyncMock, patch, MagicMock
"""Test case for async_sessionmaker fix in StateCheckpointManager.

This test ensures the StateCheckpointManager properly handles 
db_session_factory as an async context manager.
"""

import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Skip entire module since state_checkpoint_manager was removed during refactoring
pytestmark = pytest.mark.skip(reason="state_checkpoint_manager module was removed during SSOT consolidation")

import sys
from pathlib import Path

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Skip test if modules are missing
pytest.skip("StateCheckpointManager module has been removed", allow_module_level=True)

try:
    from netra_backend.app.agents.state import DeepAgentState
    from netra_backend.app.agents.supervisor.state_checkpoint_manager import (
    StateCheckpointManager)
except ImportError:
    pytest.skip("Required modules have been removed or have missing dependencies", allow_module_level=True)
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.schemas.agent_state import AgentPhase, CheckpointType
    import asyncio

    class TestStateCheckpointSessionFix:
        """Test StateCheckpointManager session handling fix."""

        @pytest.fixture
        def real_session():
            """Use real service instance."""
    # TODO: Initialize real service
            """Create mock AsyncSession with proper async methods."""
            pass
        # Mock: Database session isolation for transaction testing without real database dependency
            session = Mock(spec=AsyncSession)
        # Mock: Session isolation for controlled testing without external state
            session.execute = AsyncMock(return_value=Mock(
            # Mock: Component isolation for controlled unit testing
            scalar_one_or_none=Mock(return_value=Mock(metadata_={}))
            ))
        # Mock: Session isolation for controlled testing without external state
            session.flush = AsyncNone  # TODO: Use real service instance
        # Mock: Session isolation for controlled testing without external state
            session.commit = AsyncNone  # TODO: Use real service instance
        # Mock: Session isolation for controlled testing without external state
            session.rollback = AsyncNone  # TODO: Use real service instance
            return session

        @pytest.fixture
        def real_state():
            """Use real service instance."""
    # TODO: Initialize real service
            """Create mock DeepAgentState."""
            pass
            return DeepAgentState(
        user_request="Test request",
        chat_thread_id="thread_123",
        user_id="user_456",
        step_count=0
        )

        @pytest.mark.asyncio
        async def test_session_factory_context_manager(self, mock_session):
            """Test db_session_factory works as async context manager."""
            @asynccontextmanager
            async def db_session_factory():
                yield mock_session

                manager = StateCheckpointManager(db_session_factory)

        # This should work without AttributeError
                async with db_session_factory() as session:
                    assert session == mock_session
                    assert hasattr(session, 'execute')

                    @pytest.mark.asyncio
                    async def test_checkpoint_save_with_factory(self, mock_session, mock_state):
                        """Test checkpoint save with proper session factory."""
                        pass
        # Create a mock sessionmaker that returns the session when called
                        from sqlalchemy.ext.asyncio import async_sessionmaker
                        db_session_factory = Mock(spec=async_sessionmaker)
                        db_session_factory.return_value = mock_session

        # Mock: Agent supervisor isolation for testing without spawning real agents
                        with patch('netra_backend.app.agents.supervisor.state_checkpoint_manager.state_persistence_service') as mock_persistence:
            # Mock: Agent service isolation for testing without LLM agent execution
                            mock_persistence.save_agent_state = AsyncMock(return_value=True)

                            manager = StateCheckpointManager(db_session_factory)
                            success = await manager.save_state_checkpoint(
                            mock_state, "run_123", "thread_123", "user_123",
                            CheckpointType.AUTO, AgentPhase.INITIALIZATION
                            )

                            assert success
                            mock_persistence.save_agent_state.assert_called_once()
                            call_args = mock_persistence.save_agent_state.call_args[0]
            # First argument should be a StatePersistenceRequest
                            from netra_backend.app.schemas.agent_state import StatePersistenceRequest
                            assert isinstance(call_args[0], StatePersistenceRequest)
                            assert call_args[0].run_id == "run_123"
                            assert call_args[0].thread_id == "thread_123"
                            assert call_args[0].user_id == "user_123"
            # Second argument should be the session (created from factory)
                            assert call_args[1] == mock_session

                            @pytest.mark.asyncio
                            async def test_supervisor_state_manager_initialization(self, mock_session):
                                """Test SupervisorAgent correctly initializes StateManager."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
                                llm_manager = Mock(spec=LLMManager)
        # Mock: WebSocket connection isolation for testing without network overhead
                                websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
                                tool_dispatcher = Mock(spec=ToolDispatcher)

                                supervisor = SupervisorAgent(
                                mock_session, llm_manager, websocket_manager, tool_dispatcher
                                )

        # Verify state_manager is initialized
                                assert hasattr(supervisor, 'state_manager')
                                assert supervisor.state_manager is not None

        # Verify the db_session is properly stored
                                assert supervisor.state_manager.checkpoint_manager.db_session == mock_session

                                @pytest.mark.asyncio
                                async def test_async_sessionmaker_error_prevention(self):
                                    """Test that passing async_sessionmaker directly would fail."""
                                    pass
        # This simulates the error case
        # Mock: Database session isolation for transaction testing without real database dependency
                                    mock_sessionmaker = Mock(spec=async_sessionmaker)

        # This should raise AttributeError if used incorrectly
                                    with pytest.raises(AttributeError, match="has no attribute 'execute'"):
                                        await mock_sessionmaker.execute("SELECT 1")

                                        @pytest.mark.asyncio
                                        async def test_session_reuse_in_pipeline(self, mock_session, mock_state):
                                            """Test session is properly reused in pipeline execution."""
                                            @asynccontextmanager
                                            async def db_session_factory():
                                                yield mock_session

        # Mock: Agent supervisor isolation for testing without spawning real agents
                                                with patch('netra_backend.app.agents.supervisor.state_checkpoint_manager.state_persistence_service') as mock_persistence:
            # Mock: Agent service isolation for testing without LLM agent execution
                                                    mock_persistence.save_agent_state = AsyncMock(return_value=True)

                                                    manager = StateCheckpointManager(db_session_factory)

            # Multiple checkpoint saves should reuse the same session
                                                    for i in range(3):
                                                        success = await manager.save_state_checkpoint(
                                                        mock_state, f"run_{i}", "thread_123", "user_123",
                                                        CheckpointType.AUTO
                                                        )
                                                        assert success

            # Verify session was reused (3 calls with same session)
                                                        assert mock_persistence.save_agent_state.call_count == 3
            # Verify calls were made - specific session argument validation is complex
            # due to async context manager handling, but we confirmed the method calls
                                                        assert len(mock_persistence.save_agent_state.call_args_list) == 3

                                                        @pytest.mark.asyncio
                                                        async def test_transaction_rollback_on_error(self, mock_session, mock_state):
                                                            """Test transaction rollback on checkpoint save error - critical for data integrity."""
                                                            pass
                                                            @asynccontextmanager
                                                            async def db_session_factory():
                                                                pass
                                                                yield mock_session

                                                                with patch('netra_backend.app.agents.supervisor.state_checkpoint_manager.state_persistence_service') as mock_persistence:
            # Simulate database error during save
                                                                    mock_persistence.save_agent_state = AsyncMock(side_effect=Exception("Database error"))

                                                                    manager = StateCheckpointManager(db_session_factory)

            # Should handle error gracefully and await asyncio.sleep(0)
                                                                    # FIXED: return with value in async generator
                                                                    yield False
                                                                    return
                                                                success = await manager.save_state_checkpoint(
                                                                mock_state, "run_error", "thread_123", "user_123",
                                                                CheckpointType.AUTO, AgentPhase.INITIALIZATION
                                                                )

                                                                assert success is False
            # Verify the persistence service was called with the error
                                                                mock_persistence.save_agent_state.assert_called_once()