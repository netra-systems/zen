"""Critical State Persistence Integration Tests

Tests for the state persistence service issues seen in production,
particularly the async_sessionmaker.execute() error.
"""

import pytest
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, JSON, select

from app.services.state_persistence_service import state_persistence_service
from app.agents.state import DeepAgentState, AgentMetadata, OptimizationsResult
from app.agents.triage_sub_agent.models import TriageResult


class TestStatePersistenceCritical:
    """Test state persistence issues from production"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Create proper mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_sessionmaker(self, mock_db_session):
        """Create mock sessionmaker that returns sessions correctly"""
        sessionmaker = Mock(spec=async_sessionmaker)
        
        # This is the correct pattern - sessionmaker() returns a session
        sessionmaker.return_value = mock_db_session
        
        # Context manager support
        async def async_context_manager():
            return mock_db_session
        
        sessionmaker.__aenter__ = async_context_manager
        sessionmaker.__aexit__ = AsyncMock()
        
        return sessionmaker
    
    @pytest.mark.asyncio
    async def test_sessionmaker_execute_error_reproduction(self):
        """Reproduce the exact error from production"""
        # Create sessionmaker incorrectly used in production
        sessionmaker = Mock(spec=async_sessionmaker)
        
        # This is the ERROR from production - calling execute on sessionmaker
        with pytest.raises(AttributeError) as exc_info:
            await sessionmaker.execute("SELECT 1")
        
        assert "'async_sessionmaker' object has no attribute 'execute'" in str(exc_info.value)
    
    @pytest.mark.asyncio  
    async def test_correct_session_usage_pattern(self, mock_sessionmaker, mock_db_session):
        """Test the correct pattern for using async sessions"""
        # Correct pattern 1: Create session from sessionmaker
        session = mock_sessionmaker()
        result = await session.execute("SELECT 1")
        await session.commit()
        await session.close()
        
        # Verify calls
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_agent_state_with_datetime(self, mock_db_session):
        """Test saving agent state with datetime serialization"""
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4()) 
        user_id = str(uuid.uuid4())
        
        # Create state with datetime fields
        state = DeepAgentState(
            user_request="Test request",
            metadata=AgentMetadata(
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
        )
        
        # Mock the AgentState model
        with patch("app.services.state_persistence_service.AgentState") as MockAgentState:
            mock_state_obj = Mock()
            MockAgentState.return_value = mock_state_obj
            
            # Test save with proper datetime handling
            await state_persistence_service.save_agent_state(
                run_id, thread_id, user_id, state, mock_db_session
            )
            
            # Verify the state was created with proper JSON serialization
            MockAgentState.assert_called_once()
            call_args = MockAgentState.call_args
            
            # Check that state_data was serialized (should be JSON string)
            assert call_args.kwargs["run_id"] == run_id
            assert call_args.kwargs["thread_id"] == thread_id
            
            # Verify session methods called correctly
            mock_db_session.add.assert_called_once_with(mock_state_obj)
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_agent_state_error_handling(self, mock_db_session):
        """Test load_agent_state with the session error from production"""
        run_id = str(uuid.uuid4())
        
        # Setup mock to return no results
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Test load
        result = await state_persistence_service.load_agent_state(run_id, mock_db_session)
        
        # Should handle missing state gracefully
        assert result is None
        
        # Verify execute was called with proper query
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_datetime_json_serialization_in_state(self):
        """Test JSON serialization of datetime in agent state"""
        from app.services.state_persistence_service import DateTimeEncoder
        
        # Create complex state with nested datetime
        state = DeepAgentState(
            user_request="Test",
            metadata=AgentMetadata(
                created_at=datetime.now(),
                last_updated=datetime.now(),
                custom_fields={"timestamp": str(datetime.now())}
            ),
            optimizations_result=OptimizationsResult(
                optimization_type="test",
                metadata=AgentMetadata(created_at=datetime.now())
            )
        )
        
        # Should serialize without error using custom encoder
        serialized = json.dumps(state.model_dump(), cls=DateTimeEncoder)
        assert serialized
        
        # Should be able to deserialize
        deserialized = json.loads(serialized)
        assert deserialized["user_request"] == "Test"
    
    @pytest.mark.asyncio
    async def test_state_with_all_agent_results(self, mock_db_session):
        """Test state persistence with all agent result types populated"""
        # Create fully populated state
        state = DeepAgentState(
            user_request="Complex request",
            triage_result=TriageResult(
                category="Optimization",
                confidence_score=0.95
            ),
            data_result={"metrics": ["cpu", "memory"], "values": [0.8, 0.6]},
            optimizations_result=OptimizationsResult(
                optimization_type="performance",
                recommendations=["Use GPU", "Increase batch size"],
                cost_savings=5000.0
            )
        )
        
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Mock AgentState model
        with patch("app.services.state_persistence_service.AgentState") as MockAgentState:
            mock_state_obj = Mock()
            MockAgentState.return_value = mock_state_obj
            
            # Save state
            await state_persistence_service.save_agent_state(
                run_id, thread_id, user_id, state, mock_db_session
            )
            
            # Verify complex state was handled
            MockAgentState.assert_called_once()
            call_kwargs = MockAgentState.call_args.kwargs
            
            # Parse the state_data to verify structure
            state_data = json.loads(call_kwargs["state_data"])
            assert state_data["user_request"] == "Complex request"
            assert "triage_result" in state_data
            assert "optimizations_result" in state_data
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self, mock_db_session):
        """Test concurrent state updates don't cause conflicts"""
        import asyncio
        
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Create multiple states
        states = [
            DeepAgentState(user_request=f"Request {i}")
            for i in range(5)
        ]
        
        # Mock AgentState
        with patch("app.services.state_persistence_service.AgentState") as MockAgentState:
            MockAgentState.return_value = Mock()
            
            # Save states concurrently
            tasks = [
                state_persistence_service.save_agent_state(
                    f"{run_id}_{i}", thread_id, user_id, state, mock_db_session
                )
                for i, state in enumerate(states)
            ]
            
            await asyncio.gather(*tasks)
            
            # Verify all saves completed
            assert MockAgentState.call_count == 5
            assert mock_db_session.commit.call_count == 5
    
    @pytest.mark.asyncio
    async def test_state_recovery_after_error(self, mock_db_session):
        """Test state recovery after save error"""
        state = DeepAgentState(user_request="Test")
        run_id = str(uuid.uuid4())
        
        # First save fails
        mock_db_session.commit.side_effect = [
            Exception("Database error"),
            None  # Second attempt succeeds
        ]
        
        # First attempt should fail
        with pytest.raises(Exception):
            await state_persistence_service.save_agent_state(
                run_id, "thread", "user", state, mock_db_session
            )
        
        # Reset for retry
        mock_db_session.rollback.assert_called_once()
        
        # Second attempt should succeed
        mock_db_session.commit.side_effect = None
        await state_persistence_service.save_agent_state(
            run_id, "thread", "user", state, mock_db_session
        )
    
    @pytest.mark.asyncio
    async def test_thread_context_operations(self, mock_db_session):
        """Test thread context save and load operations"""
        thread_id = str(uuid.uuid4())
        context = {
            "current_run_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "conversation_history": ["msg1", "msg2"],
            "metadata": {"key": "value"}
        }
        
        # Mock ThreadContext model
        with patch("app.services.state_persistence_service.ThreadContext") as MockThreadContext:
            # Test save
            mock_context_obj = Mock()
            MockThreadContext.return_value = mock_context_obj
            
            await state_persistence_service.save_thread_context(
                thread_id, context, mock_db_session
            )
            
            MockThreadContext.assert_called_once()
            mock_db_session.add.assert_called_with(mock_context_obj)
            mock_db_session.commit.assert_called()
            
            # Test load
            mock_result = Mock()
            mock_loaded_context = Mock()
            mock_loaded_context.context_data = json.dumps(context)
            mock_result.scalars.return_value.first.return_value = mock_loaded_context
            mock_db_session.execute.return_value = mock_result
            
            loaded = await state_persistence_service.get_thread_context(
                thread_id, mock_db_session
            )
            
            assert loaded == context


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])