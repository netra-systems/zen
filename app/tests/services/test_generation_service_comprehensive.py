"""
Comprehensive tests for Generation Service

Covers all methods, error handling, and edge cases.
"""

import pytest
import json
import uuid
import os
import time
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from collections import defaultdict

from app.services.generation_service import (
    update_job_status,
    get_corpus_from_clickhouse,
    save_corpus_to_clickhouse
)
from app.schemas import (
    ContentGenParams,
    LogGenParams,
    SyntheticDataGenParams
)
from app.core.exceptions_base import NetraException


@pytest.fixture
def mock_job_store():
    """Mock job store fixture"""
    store = MagicMock()
    store.get = AsyncMock()
    store.create = AsyncMock()
    store.update = AsyncMock()
    store.list = AsyncMock()
    return store


@pytest.fixture
def mock_clickhouse():
    """Mock ClickHouse client fixture"""
    client = MagicMock()
    client.execute_query = AsyncMock()
    client.insert_data = AsyncMock()
    client.create_table = AsyncMock()
    client.command = AsyncMock()
    client.insert = AsyncMock()
    return client


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager fixture"""
    manager = MagicMock()
    manager.broadcast = AsyncMock()
    manager.send_to_connection = AsyncMock()
    return manager


@pytest.fixture
def sample_corpus():
    """Sample corpus data fixture"""
    return {
        "qa": [
            ("What is AI?", "AI is artificial intelligence."),
            ("How does ML work?", "ML works by learning patterns from data.")
        ],
        "generation": [
            ("Write a poem", "Roses are red, violets are blue..."),
            ("Generate text", "This is generated text.")
        ],
        "summarization": [
            ("Long text here...", "Summary: Brief version"),
            ("Another long text...", "Summary: Short form")
        ]
    }


class TestJobStatusManagement:
    """Test job status update functionality"""
    
    @pytest.mark.asyncio
    async def test_update_job_status_running(self):
        """Test updating job status to running"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status("job123", "running", progress=50)
                
                mock_store.update.assert_called_once()
                # Check positional arguments
                assert mock_store.update.call_args[0][0] == "job123"  # job_id
                assert mock_store.update.call_args[0][1] == "running"  # status
                # Check keyword arguments
                assert mock_store.update.call_args[1]["progress"] == 50
                
                mock_manager.broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_job_status_completed(self):
        """Test updating job status to completed"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status(
                    "job456", 
                    "completed", 
                    progress=100,
                    result={"data": "test"}
                )
                
                mock_store.update.assert_called_once()
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
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status(
                    "job789",
                    "failed",
                    error="Test error message"
                )
                
                mock_store.update.assert_called_once()
                # Check positional arguments
                assert mock_store.update.call_args[0][0] == "job789"  # job_id
                assert mock_store.update.call_args[0][1] == "failed"  # status
                # Check keyword arguments
                assert mock_store.update.call_args[1]["error"] == "Test error message"
    
    @pytest.mark.asyncio
    async def test_update_job_status_with_metadata(self):
        """Test updating job status with additional metadata"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status(
                    "job_meta",
                    "running",
                    progress=75,
                    estimated_time_remaining=30,
                    processed_items=750,
                    total_items=1000
                )
                
                mock_store.update.assert_called_once()
                # Check positional arguments
                assert mock_store.update.call_args[0][0] == "job_meta"  # job_id
                assert mock_store.update.call_args[0][1] == "running"  # status
                # Check keyword arguments
                assert mock_store.update.call_args[1]["progress"] == 75
                assert mock_store.update.call_args[1]["estimated_time_remaining"] == 30
                assert mock_store.update.call_args[1]["processed_items"] == 750
                assert mock_store.update.call_args[1]["total_items"] == 1000


class TestClickHouseOperations:
    """Test ClickHouse corpus operations"""
    
    @pytest.mark.asyncio
    async def test_get_corpus_from_clickhouse(self, mock_clickhouse):
        """Test retrieving corpus from ClickHouse"""
        mock_clickhouse.execute_query.return_value = [
            {"workload_type": "qa", "prompt": "Q1", "response": "A1"},
            {"workload_type": "qa", "prompt": "Q2", "response": "A2"},
            {"workload_type": "generation", "prompt": "G1", "response": "R1"}
        ]
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_clickhouse):
            with patch('app.services.generation_service.ClickHouseQueryInterceptor', return_value=mock_clickhouse):
                result = await get_corpus_from_clickhouse("test_corpus")
                
                assert "qa" in result
                assert "generation" in result
                assert len(result["qa"]) == 2
                assert len(result["generation"]) == 1
                assert result["qa"][0] == ("Q1", "A1")
    
    @pytest.mark.asyncio
    async def test_get_corpus_empty_table(self, mock_clickhouse):
        """Test retrieving corpus from empty table"""
        mock_clickhouse.execute_query.return_value = []
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_clickhouse):
            with patch('app.services.generation_service.ClickHouseQueryInterceptor', return_value=mock_clickhouse):
                result = await get_corpus_from_clickhouse("empty_corpus")
                
                assert result == {}
    
    @pytest.mark.asyncio
    async def test_save_corpus_to_clickhouse(self, mock_clickhouse, sample_corpus):
        """Test saving corpus to ClickHouse"""
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_clickhouse):
            with patch('app.services.generation_service.ClickHouseQueryInterceptor', return_value=mock_clickhouse):
                await save_corpus_to_clickhouse(sample_corpus, "new_corpus", "job123")
                
                # Verify table creation
                mock_clickhouse.command.assert_called()
                
                # Verify data insertion
                mock_clickhouse.insert_data.assert_called()
                inserted_data = mock_clickhouse.insert_data.call_args[0][1]
                
                # Check data format - insert_data receives list of lists (values only)
                assert len(inserted_data) == 6  # 2 qa + 2 generation + 2 summarization
                # Each row should be a list of values (not a dict)
                assert all(isinstance(row, list) for row in inserted_data)
                # Each row should have the expected number of fields
                assert all(len(row) > 0 for row in inserted_data)
    
    @pytest.mark.asyncio
    async def test_save_corpus_with_error(self, mock_clickhouse, sample_corpus):
        """Test corpus save error handling"""
        mock_clickhouse.command.side_effect = Exception("Database error")
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_clickhouse):
            with patch('app.services.generation_service.ClickHouseQueryInterceptor', return_value=mock_clickhouse):
                with pytest.raises(Exception) as exc:
                    await save_corpus_to_clickhouse(sample_corpus, "error_corpus", "job_error")
                
                assert "Database error" in str(exc.value)


# Note: The following test classes are commented out as they test functions
# that don't exist in the current implementation of generation_service.py

# class TestContentGeneration:
#     """Test content generation functions"""
#     # Tests for generate_content_corpus which doesn't exist
#     pass

# class TestLogGeneration:
#     """Test synthetic log generation"""
#     # Tests for generate_synthetic_llm_logs which doesn't exist
#     pass

# class TestSyntheticDataGeneration:
#     """Test synthetic data batch generation"""
#     # Tests for generate_synthetic_data_batch which doesn't exist
#     pass

# class TestHelperFunctions:
#     """Test helper and utility functions"""
#     # Tests for _split_params, generate_log_entry, parallel_generate_sample, _run_parallel_generation
#     # which don't exist
#     pass

# class TestEdgeCases:
#     """Test edge cases and boundary conditions"""
#     # Tests for functions that don't exist
#     pass

# class TestIntegration:
#     """Integration tests for generation service"""
#     # Tests for functions that don't exist
#     pass


class TestExistingFunctions:
    """Test the actual functions that exist in generation_service"""
    
    @pytest.mark.asyncio
    async def test_update_job_status_broadcasts_update(self):
        """Test that job status updates are broadcast via WebSocket"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status("test_job", "running", progress=25)
                
                # Verify broadcast was called with correct message
                broadcast_call = mock_manager.broadcast.call_args[0][0]
                assert broadcast_call["job_id"] == "test_job"
                assert broadcast_call["status"] == "running"
                assert broadcast_call["progress"] == 25
    
    @pytest.mark.asyncio
    async def test_corpus_operations_integration(self, mock_clickhouse):
        """Test corpus save and retrieve integration"""
        test_corpus = {
            "qa": [("Question?", "Answer.")],
            "generation": [("Generate", "Response")]
        }
        
        # Setup mock to return saved data
        mock_clickhouse.execute_query.return_value = [
            {"workload_type": "qa", "prompt": "Question?", "response": "Answer."},
            {"workload_type": "generation", "prompt": "Generate", "response": "Response"}
        ]
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_clickhouse):
            with patch('app.services.generation_service.ClickHouseQueryInterceptor', return_value=mock_clickhouse):
                # Save corpus
                await save_corpus_to_clickhouse(test_corpus, "integration_corpus", "int_job")
                
                # Retrieve corpus
                retrieved = await get_corpus_from_clickhouse("integration_corpus")
                
                # Verify round trip
                assert retrieved["qa"][0] == test_corpus["qa"][0]
                assert retrieved["generation"][0] == test_corpus["generation"][0]