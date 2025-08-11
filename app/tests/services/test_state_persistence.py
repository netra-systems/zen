import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.state_persistence_service import StatePersistenceService
from datetime import datetime

@pytest.mark.asyncio
class TestStatePersistence:
    
    async def test_save_agent_state(self):
        """Test saving agent state to database"""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        
        persistence_service = StatePersistenceService(mock_db)
        
        state_data = {
            "agent_id": "supervisor",
            "thread_id": "thread-123",
            "state": {
                "current_step": "data_analysis",
                "sub_agents_active": ["triage", "data"],
                "context": {"user_query": "Analyze performance"}
            },
            "timestamp": datetime.now().isoformat()
        }
        
        result = await persistence_service.save_state(state_data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result == True
    
    async def test_restore_agent_state(self):
        """Test restoring agent state from database"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        
        saved_state = {
            "agent_id": "supervisor",
            "thread_id": "thread-123",
            "state": json.dumps({
                "current_step": "optimization",
                "recommendations": ["cache", "batch_processing"]
            }),
            "timestamp": datetime.now()
        }
        
        mock_result.scalar_one_or_none.return_value = saved_state
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        persistence_service = StatePersistenceService(mock_db)
        
        restored_state = await persistence_service.restore_state("thread-123", "supervisor")
        
        assert restored_state != None
        assert restored_state["agent_id"] == "supervisor"
        assert "current_step" in json.loads(restored_state["state"])
    
    async def test_cleanup_old_states(self):
        """Test cleanup of old state records"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        
        persistence_service = StatePersistenceService(mock_db)
        
        result = await persistence_service.cleanup_old_states(days_to_keep=7)
        
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result == True
    
    async def test_state_versioning(self):
        """Test state versioning for rollback capability"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        
        versions = [
            {"version": 1, "state": json.dumps({"step": "init"})},
            {"version": 2, "state": json.dumps({"step": "processing"})},
            {"version": 3, "state": json.dumps({"step": "complete"})}
        ]
        
        mock_result.scalars.return_value.all.return_value = versions
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        persistence_service = StatePersistenceService(mock_db)
        
        history = await persistence_service.get_state_history("thread-123")
        
        assert len(history) == 3
        assert history[-1]["version"] == 3
    
    async def test_concurrent_state_updates(self):
        """Test handling concurrent state updates"""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        
        persistence_service = StatePersistenceService(mock_db)
        
        import asyncio
        
        async def update_state(step_name):
            state_data = {
                "agent_id": "supervisor",
                "thread_id": "thread-123",
                "state": {"current_step": step_name},
                "timestamp": datetime.now().isoformat()
            }
            return await persistence_service.save_state(state_data)
        
        results = await asyncio.gather(
            update_state("step1"),
            update_state("step2"),
            update_state("step3")
        )
        
        assert all(results)
        assert mock_db.add.call_count == 3
        assert mock_db.commit.call_count == 3