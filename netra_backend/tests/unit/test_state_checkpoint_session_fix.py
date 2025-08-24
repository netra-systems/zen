"""Test case for async_sessionmaker fix in StateCheckpointManager.

This test ensures the StateCheckpointManager properly handles 
db_session_factory as an async context manager.
"""

import sys
from pathlib import Path

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor.state_checkpoint_manager import (
    StateCheckpointManager,
)
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.agent_state import AgentPhase, CheckpointType

class TestStateCheckpointSessionFix:
    """Test StateCheckpointManager session handling fix."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession with proper async methods."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=Mock(metadata_={}))
        ))
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_state(self):
        """Create mock DeepAgentState."""
        return DeepAgentState(
            user_request="Test request",
            chat_thread_id="thread_123",
            user_id="user_456",
            step_count=0
        )
    
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
    
    async def test_checkpoint_save_with_factory(self, mock_session, mock_state):
        """Test checkpoint save with proper session factory."""
        @asynccontextmanager
        async def db_session_factory():
            yield mock_session
        
        with patch('app.agents.supervisor.state_checkpoint_manager.state_persistence_service') as mock_persistence:
            mock_persistence.save_agent_state = AsyncMock(return_value=True)
            
            manager = StateCheckpointManager(db_session_factory)
            success = await manager.save_state_checkpoint(
                mock_state, "run_123", "thread_123", "user_123",
                CheckpointType.AUTO, AgentPhase.INITIALIZATION
            )
            
            assert success
            mock_persistence.save_agent_state.assert_called_once()
            call_args = mock_persistence.save_agent_state.call_args[0]
            assert call_args[0] == "run_123"  # run_id
            assert call_args[1] == "thread_123"  # thread_id
            assert call_args[2] == "user_123"  # user_id
            assert isinstance(call_args[3], DeepAgentState)  # state
            assert call_args[4] == mock_session  # session
    
    async def test_supervisor_state_manager_initialization(self, mock_session):
        """Test SupervisorAgent correctly initializes StateManager."""
        llm_manager = Mock(spec=LLMManager)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(
            mock_session, llm_manager, websocket_manager, tool_dispatcher
        )
        
        # Verify state_manager is initialized
        assert hasattr(supervisor, 'state_manager')
        assert supervisor.state_manager is not None
        
        # Verify the db_session_factory works
        factory = supervisor.state_manager.checkpoint_manager.db_session_factory
        async with factory() as session:
            assert session == mock_session
    
    async def test_async_sessionmaker_error_prevention(self):
        """Test that passing async_sessionmaker directly would fail."""
        # This simulates the error case
        mock_sessionmaker = Mock(spec=async_sessionmaker)
        
        # This should raise AttributeError if used incorrectly
        with pytest.raises(AttributeError, match="has no attribute 'execute'"):
            await mock_sessionmaker.execute("SELECT 1")
    
    async def test_session_reuse_in_pipeline(self, mock_session, mock_state):
        """Test session is properly reused in pipeline execution."""
        @asynccontextmanager
        async def db_session_factory():
            yield mock_session
        
        with patch('app.agents.supervisor.state_checkpoint_manager.state_persistence_service') as mock_persistence:
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
            for call in mock_persistence.save_agent_state.call_args_list:
                assert call[0][4] == mock_session  # session argument