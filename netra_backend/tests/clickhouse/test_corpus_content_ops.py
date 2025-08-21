"""
Corpus content operations tests
Tests content generation workflows and batch processing capabilities
COMPLIANCE: 450-line max file, 25-line max functions
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from netra_backend.app.services.generation_service import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    run_content_generation_job,
    run_synthetic_data_generation_job,
    save_corpus_to_clickhouse,
    get_corpus_from_clickhouse
)
from netra_backend.app.services.corpus_service import CorpusService
from schemas import ContentGenParams


class TestContentGeneration:
    """Test content generation workflows"""
    
    async def test_content_generation_job_flow(self):
        """Test 6: Verify content generation job workflow"""
        with patch('app.services.generation_service.update_job_status') as mock_update:
            with patch('app.services.generation_service.save_corpus_to_clickhouse') as mock_save:
                with patch('app.services.generation_service.run_generation_in_pool') as mock_pool:
                    # Mock generation results
                    mock_pool.return_value = iter([
                        {"type": "simple_chat", "data": ("prompt1", "response1")},
                        {"type": "rag_pipeline", "data": ("prompt2", "response2")}
                    ])
                    
                    params = _create_content_gen_params()
                    
                    await run_content_generation_job("job_123", params)
                    
                    # Verify job status updates
                    assert mock_update.call_count >= 3  # running, progress, completed
                    
                    # Verify corpus was saved
                    _assert_corpus_saved_correctly(mock_save)

    async def test_corpus_save_to_clickhouse(self):
        """Test 7: Verify corpus is properly saved to ClickHouse"""
        corpus = _create_test_corpus()
        
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_db:
            mock_instance = AsyncMock()
            mock_db.return_value = mock_instance
            
            await save_corpus_to_clickhouse(corpus, "test_table", "job_id")
            
            # Verify table creation
            mock_instance.command.assert_called_once()
            
            # Verify data insertion
            mock_instance.insert_data.assert_called_once()
            insert_call = mock_instance.insert_data.call_args
            
            # Should insert 4 total records
            assert len(insert_call[0][1]) == 4

    async def test_corpus_load_from_clickhouse(self):
        """Test 8: Verify corpus is properly loaded from ClickHouse"""
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_db:
            mock_instance = AsyncMock()
            mock_db.return_value = mock_instance
            
            # Mock query results
            mock_instance.execute_query.return_value = _create_query_results()
            
            corpus = await get_corpus_from_clickhouse("test_table")
            
            # Verify corpus structure
            assert len(corpus["simple_chat"]) == 2
            assert len(corpus["rag_pipeline"]) == 1
            assert corpus["simple_chat"][0] == ("p1", "r1")


class TestBatchProcessing:
    """Test batch processing capabilities"""
    
    async def test_batch_content_upload(self):
        """Test 9: Verify batch content upload with buffering"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db, corpus = _setup_batch_test_mocks()
            
            batch_id = "batch_001"
            
            # Upload batch 1 (not final)
            result1 = await service.upload_content(
                db, "test_id",
                [{"workload_type": "simple_chat", "prompt": "p1", "response": "r1"}],
                batch_id=batch_id,
                is_final_batch=False
            )
            
            assert result1["status"] == "buffering"
            assert result1["records_buffered"] == 1
            
            # Upload batch 2 (final)
            result2 = await service.upload_content(
                db, "test_id",
                [{"workload_type": "simple_chat", "prompt": "p2", "response": "r2"}],
                batch_id=batch_id,
                is_final_batch=True
            )
            
            # Should process all buffered records
            assert result2["records_uploaded"] == 2

    async def test_synthetic_data_batch_ingestion(self):
        """Test 10: Verify synthetic data batch ingestion"""
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_db:
            mock_instance = AsyncMock()
            mock_db.return_value = mock_instance
            
            with patch('app.services.generation_service.get_corpus_from_clickhouse') as mock_get:
                mock_get.return_value = _create_source_corpus()
                
                with patch('app.services.generation_service.synthetic_data_main') as mock_main:
                    # Mock generated logs
                    mock_main.return_value = [
                        {"log": i} for i in range(2500)  # 2.5 batches
                    ]
                    
                    with patch('app.services.generation_service.ingest_records') as mock_ingest:
                        mock_ingest.return_value = 1000  # Each batch
                        
                        params = _create_synthetic_data_params()
                        
                        await run_synthetic_data_generation_job("job_id", params)
                        
                        # Should call ingest 3 times (2 full batches + 1 partial)
                        assert mock_ingest.call_count == 3


def _create_content_gen_params():
    """Create content generation parameters."""
    return ContentGenParams(
        samples_per_type=10,
        temperature=0.7,
        clickhouse_table="test_corpus"
    )


def _assert_corpus_saved_correctly(mock_save):
    """Assert corpus was saved correctly."""
    mock_save.assert_called_once()
    saved_corpus = mock_save.call_args[0][0]
    assert "simple_chat" in saved_corpus
    assert "rag_pipeline" in saved_corpus


def _create_test_corpus():
    """Create test corpus for saving."""
    return {
        "simple_chat": [("p1", "r1"), ("p2", "r2")],
        "rag_pipeline": [("p3", "r3")],
        "tool_use": [("p4", "r4")]
    }


def _create_query_results():
    """Create mock query results."""
    return [
        {"workload_type": "simple_chat", "prompt": "p1", "response": "r1"},
        {"workload_type": "simple_chat", "prompt": "p2", "response": "r2"},
        {"workload_type": "rag_pipeline", "prompt": "p3", "response": "r3"}
    ]


def _setup_batch_test_mocks():
    """Setup mocks for batch testing."""
    from unittest.mock import MagicMock
    
    db = MagicMock()
    corpus = MagicMock()
    corpus.status = "available"
    corpus.table_name = "test_table"
    db.query().filter().first.return_value = corpus
    
    return db, corpus


def _create_source_corpus():
    """Create source corpus for synthetic data."""
    return {
        "simple_chat": [("p1", "r1")],
        "rag_pipeline": [("p2", "r2")]
    }


def _create_synthetic_data_params():
    """Create synthetic data generation parameters."""
    return {
        "batch_size": 1000,
        "num_traces": 2500,
        "source_table": "corpus",
        "destination_table": "synthetic"
    }