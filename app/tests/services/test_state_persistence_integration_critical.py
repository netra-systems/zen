"""Critical State Persistence Integration Tests

Tests for state persistence service with Redis and PostgreSQL.
Focuses on async session usage and datetime serialization issues.
"""

import pytest
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.services.state_persistence_service import state_persistence_service
from app.agents.state import DeepAgentState, AgentMetadata, OptimizationsResult
from app.db.models_postgres import Run, Reference


class TestStatePersistenceCritical:
    """Test state persistence with actual service patterns"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock AsyncSession with proper interface"""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        session.add = Mock()
        return session
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        client = Mock()
        client.set = AsyncMock()
        client.get = AsyncMock()
        return client
    async def test_sessionmaker_error_reproduction(self):
        """Reproduce async_sessionmaker.execute() error"""
        sessionmaker = Mock(spec=async_sessionmaker)
        with pytest.raises(AttributeError) as exc_info:
            sessionmaker.execute("SELECT 1")
        assert "Mock object has no attribute 'execute'" in str(exc_info.value)
    async def test_correct_session_pattern(self, mock_db_session):
        """Test correct async session usage"""
        # Correct: get session instance then call execute
        result = await mock_db_session.execute(select(Run))
        await mock_db_session.commit()
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
    async def test_save_state_with_datetime(self, mock_db_session, mock_redis_client):
        """Test state save with datetime serialization"""
        state = DeepAgentState(
            user_request="Test",
            metadata=AgentMetadata(created_at=datetime.now(), last_updated=datetime.now())
        )
        
        # Mock Run query result
        mock_run = Mock(spec=Run)
        mock_run.metadata_ = {}
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(state_persistence_service, 'redis_manager') as mock_redis_mgr:
            mock_redis_mgr.get_client = AsyncMock(return_value=mock_redis_client)
            
            result = await state_persistence_service.save_agent_state(
                "test_run", "test_thread", "test_user", state, mock_db_session
            )
            
            assert result is True
            mock_redis_client.set.assert_called()
            mock_db_session.flush.assert_called_once()
    async def test_load_state_fallback(self, mock_db_session, mock_redis_client):
        """Test loading state from PostgreSQL when Redis misses"""
        # Redis returns None
        mock_redis_client.get.return_value = None
        
        # PostgreSQL has the data
        mock_run = Mock(spec=Run)
        mock_run.metadata_ = {"state": {"user_request": "Test"}}
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(state_persistence_service, 'redis_manager') as mock_redis_mgr:
            mock_redis_mgr.get_client = AsyncMock(return_value=mock_redis_client)
            
            result = await state_persistence_service.load_agent_state("test_run", mock_db_session)
            
            assert result is not None
            assert result.user_request == "Test"
            mock_redis_client.set.assert_called()  # Re-caches in Redis
    async def test_datetime_serialization(self):
        """Test JSON serialization handles datetime fields"""
        state = DeepAgentState(
            user_request="Test",
            metadata=AgentMetadata(
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
        )
        
        # Should serialize to dict without error
        serialized = state.model_dump()
        json_str = json.dumps(serialized, default=str)
        assert json_str
        
        # Should deserialize back to dict
        deserialized = json.loads(json_str)
        assert deserialized["user_request"] == "Test"
    async def test_save_sub_agent_result(self, mock_db_session, mock_redis_client):
        """Test saving individual sub-agent results"""
        result_data = {"status": "completed", "data": [1, 2, 3]}
        
        with patch.object(state_persistence_service, 'redis_manager') as mock_redis_mgr:
            mock_redis_mgr.get_client = AsyncMock(return_value=mock_redis_client)
            
            success = await state_persistence_service.save_sub_agent_result(
                "test_run", "triage_agent", result_data, mock_db_session
            )
            
            assert success is True
            mock_redis_client.set.assert_called()
            mock_db_session.add.assert_called()
            mock_db_session.flush.assert_called()
    async def test_get_sub_agent_result_fallback(self, mock_db_session, mock_redis_client):
        """Test sub-agent result retrieval with fallback"""
        # Redis miss
        mock_redis_client.get.return_value = None
        
        # PostgreSQL hit
        mock_ref = Mock(spec=Reference)
        mock_ref.value = json.dumps({"data": "test"})
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_ref
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(state_persistence_service, 'redis_manager') as mock_redis_mgr:
            mock_redis_mgr.get_client = AsyncMock(return_value=mock_redis_client)
            
            result = await state_persistence_service.get_sub_agent_result(
                "test_run", "triage_agent", mock_db_session
            )
            
            assert result == {"data": "test"}
            mock_db_session.execute.assert_called_once()
    async def test_transaction_rollback_on_error(self, mock_db_session, mock_redis_client):
        """Test transaction rollback when save fails"""
        mock_db_session.flush.side_effect = Exception("DB Error")
        
        with patch.object(state_persistence_service, 'redis_manager') as mock_redis_mgr:
            mock_redis_mgr.get_client = AsyncMock(return_value=mock_redis_client)
            
            result = await state_persistence_service.save_sub_agent_result(
                "test_run", "agent", {"data": "test"}, mock_db_session
            )
            
            assert result is False
            mock_db_session.rollback.assert_called_once()
    async def test_get_thread_context(self, mock_redis_client):
        """Test thread context retrieval from Redis"""
        context = {"current_run_id": "test", "user_id": "user123"}
        mock_redis_client.get.return_value = json.dumps(context)
        
        with patch.object(state_persistence_service, 'redis_manager') as mock_redis_mgr:
            mock_redis_mgr.get_client = AsyncMock(return_value=mock_redis_client)
            
            result = await state_persistence_service.get_thread_context("thread123")
            
            assert result == context
            mock_redis_client.get.assert_called_with("thread_context:thread123")
    async def test_list_thread_runs(self, mock_db_session):
        """Test listing runs for a thread"""
        mock_runs = [Mock(spec=Run) for _ in range(3)]
        for i, run in enumerate(mock_runs):
            run.id = f"run_{i}"
            run.status = "completed"
            run.created_at = datetime.now()
            run.completed_at = datetime.now()
            run.metadata_ = {"state": {}} if i == 0 else None
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_runs
        mock_db_session.execute.return_value = mock_result
        
        runs = await state_persistence_service.list_thread_runs("thread123", mock_db_session)
        
        assert len(runs) == 3
        assert runs[0]["has_state"] is True
        assert runs[1]["has_state"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])