"""
Fixed tests for Generation Service

Tests only the functions that actually exist with proper mocking.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.generation_service import update_job_status


class TestJobStatusManagement:
    """Test job status update functionality"""
    
    @pytest.mark.asyncio
    async def test_update_job_status_running(self):
        """Test updating job status to running"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast_to_job = AsyncMock()
                
                await update_job_status("job123", "running", progress=50)
                
                # Check positional arguments
                assert mock_store.update.call_args[0][0] == "job123"  # job_id
                assert mock_store.update.call_args[0][1] == "running"  # status
                # Check keyword arguments
                assert mock_store.update.call_args[1]["progress"] == 50
                
                mock_manager.broadcast_to_job.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_job_status_completed(self):
        """Test updating job status to completed"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast_to_job = AsyncMock()
                
                await update_job_status(
                    "job456", 
                    "completed", 
                    progress=100,
                    result={"data": "test"}
                )
                
                # Check positional arguments
                assert mock_store.update.call_args[0][0] == "job456"  # job_id
                assert mock_store.update.call_args[0][1] == "completed"  # status
                # Check keyword arguments
                assert mock_store.update.call_args[1]["progress"] == 100
                assert mock_store.update.call_args[1]["result"] == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_update_job_status_failed(self):
        """Test updating job status to failed"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast_to_job = AsyncMock()
                
                await update_job_status(
                    "job789",
                    "failed",
                    error="Test error message"
                )
                
                # Check positional arguments
                assert mock_store.update.call_args[0][0] == "job789"  # job_id
                assert mock_store.update.call_args[0][1] == "failed"  # status
                # Check keyword arguments
                assert mock_store.update.call_args[1]["error"] == "Test error message"
    
    @pytest.mark.asyncio
    async def test_update_job_status_broadcasts_update(self):
        """Test that job status updates are broadcast via WebSocket"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast_to_job = AsyncMock()
                
                await update_job_status("test_job", "running", progress=25)
                
                # Verify broadcast_to_job was called with correct message
                broadcast_call = mock_manager.broadcast_to_job.call_args[0][1]
                assert broadcast_call["job_id"] == "test_job"
                assert broadcast_call["status"] == "running"
                assert broadcast_call["progress"] == 25


class TestClickHouseOperationsMocked:
    """Test ClickHouse operations with full mocking"""
    
    @pytest.mark.asyncio
    async def test_get_corpus_from_clickhouse_mocked(self):
        """Test retrieving corpus with mocked ClickHouse"""
        from app.services.generation_service import get_corpus_from_clickhouse
        
        mock_db = MagicMock()
        mock_db.execute_query = AsyncMock(return_value=[
            {"workload_type": "qa", "prompt": "Q1", "response": "A1"},
            {"workload_type": "qa", "prompt": "Q2", "response": "A2"},
            {"workload_type": "generation", "prompt": "G1", "response": "R1"}
        ])
        mock_db.disconnect = AsyncMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_ch_class:
            with patch('app.services.generation_service.ClickHouseQueryInterceptor') as mock_interceptor:
                mock_interceptor.return_value = mock_db
                
                result = await get_corpus_from_clickhouse("test_corpus")
                
                assert "qa" in result
                assert "generation" in result
                assert len(result["qa"]) == 2
                assert len(result["generation"]) == 1
    
    @pytest.mark.asyncio
    async def test_save_corpus_to_clickhouse_mocked(self):
        """Test saving corpus with mocked ClickHouse"""
        from app.services.generation_service import save_corpus_to_clickhouse
        
        sample_corpus = {
            "qa": [("Q1", "A1"), ("Q2", "A2")],
            "generation": [("G1", "R1")]
        }
        
        mock_db = MagicMock()
        mock_db.command = AsyncMock()
        mock_db.create_table = AsyncMock()
        mock_db.insert_data = AsyncMock()
        mock_db.disconnect = AsyncMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_ch_class:
            with patch('app.services.generation_service.ClickHouseQueryInterceptor') as mock_interceptor:
                mock_interceptor.return_value = mock_db
                
                await save_corpus_to_clickhouse(sample_corpus, "new_corpus", "job123")
                
                # Verify table creation command was attempted
                mock_db.command.assert_called_once()
                # Note: insert_data is called directly on the db object in the actual code