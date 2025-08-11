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
    save_corpus_to_clickhouse,
    generate_content_corpus,
    generate_synthetic_llm_logs,
    generate_synthetic_data_batch,
    parallel_generate_sample,
    generate_log_entry,
    _split_params,
    _run_parallel_generation
)
from app.schemas import (
    ContentGenParams,
    LogGenParams,
    SyntheticDataGenParams,
    ContentCorpus,
    SyntheticLLMLog
)
from app.core.exceptions import NetraException


class TestJobManagement:
    """Test job management functions"""
    
    @pytest.mark.asyncio
    async def test_update_job_status_success(self):
        """Test successful job status update"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status("job123", "running", progress=50, eta=3600)
                
                mock_store.update.assert_called_once_with(
                    "job123", "running", progress=50, eta=3600
                )
                mock_manager.broadcast.assert_called_once_with({
                    "job_id": "job123",
                    "status": "running",
                    "progress": 50,
                    "eta": 3600
                })
    
    @pytest.mark.asyncio
    async def test_update_job_status_with_error(self):
        """Test job status update with error message"""
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                await update_job_status("job456", "failed", error="Connection timeout")
                
                mock_store.update.assert_called_once_with(
                    "job456", "failed", error="Connection timeout"
                )
                mock_manager.broadcast.assert_called_once()


class TestCorpusOperations:
    """Test corpus database operations"""
    
    @pytest.mark.asyncio
    async def test_get_corpus_from_clickhouse_success(self):
        """Test successful corpus retrieval from ClickHouse"""
        mock_db = MagicMock()
        mock_db.execute_query = AsyncMock(return_value=[
            {'workload_type': 'qa', 'prompt': 'What is AI?', 'response': 'AI is...'},
            {'workload_type': 'qa', 'prompt': 'Explain ML', 'response': 'ML is...'},
            {'workload_type': 'generation', 'prompt': 'Write a story', 'response': 'Once upon...'}
        ])
        mock_db.disconnect = MagicMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_db):
            corpus = await get_corpus_from_clickhouse("test_corpus")
            
            assert len(corpus) == 2
            assert len(corpus['qa']) == 2
            assert len(corpus['generation']) == 1
            assert corpus['qa'][0] == ('What is AI?', 'AI is...')
            mock_db.execute_query.assert_called_once()
            mock_db.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_corpus_from_clickhouse_empty(self):
        """Test corpus retrieval with empty result"""
        mock_db = MagicMock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.disconnect = MagicMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_db):
            corpus = await get_corpus_from_clickhouse("empty_corpus")
            
            assert corpus == {}
            mock_db.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_corpus_from_clickhouse_error(self):
        """Test corpus retrieval with database error"""
        mock_db = MagicMock()
        mock_db.execute_query = AsyncMock(side_effect=Exception("Database connection failed"))
        mock_db.disconnect = MagicMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_db):
            with pytest.raises(Exception) as exc_info:
                await get_corpus_from_clickhouse("error_corpus")
            
            assert "Database connection failed" in str(exc_info.value)
            mock_db.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_corpus_to_clickhouse_success(self):
        """Test successful corpus save to ClickHouse"""
        corpus = {
            "qa": [("Q1", "A1"), ("Q2", "A2")],
            "generation": [("Prompt1", "Response1")]
        }
        
        mock_db = MagicMock()
        mock_db.command = AsyncMock()
        mock_db.insert_data = AsyncMock()
        mock_db.disconnect = MagicMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_db):
            with patch('app.services.generation_service.get_content_corpus_schema') as mock_schema:
                mock_schema.return_value = "CREATE TABLE test_corpus ..."
                
                await save_corpus_to_clickhouse(corpus, "test_corpus")
                
                mock_db.command.assert_called_once()
                mock_db.insert_data.assert_called_once()
                mock_db.disconnect.assert_called_once()
                
                # Verify records were created
                insert_call = mock_db.insert_data.call_args
                records = insert_call[0][1]
                assert len(records) == 3
    
    @pytest.mark.asyncio
    async def test_save_corpus_to_clickhouse_with_job_id(self):
        """Test corpus save with job ID (saves to file)"""
        corpus = {"qa": [("Q1", "A1")]}
        job_id = "job789"
        
        mock_db = MagicMock()
        mock_db.command = AsyncMock()
        mock_db.insert_data = AsyncMock()
        mock_db.disconnect = MagicMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_db):
            with patch('app.services.generation_service.get_content_corpus_schema'):
                with patch('builtins.open', create=True) as mock_open:
                    with patch('os.makedirs') as mock_makedirs:
                        await save_corpus_to_clickhouse(corpus, "test_corpus", job_id)
                        
                        mock_makedirs.assert_called_once()
                        mock_open.assert_called_once()
                        mock_db.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_corpus_with_malformed_data(self):
        """Test save corpus with various data formats"""
        corpus = {
            "qa": [
                ("Q1", "A1"),  # Tuple format
                [("Q2", "A2")],  # Nested list with tuple
                ["Q3", "A3"],  # List format
            ],
            "generation": [
                ("Single", "Response")
            ]
        }
        
        mock_db = MagicMock()
        mock_db.command = AsyncMock()
        mock_db.insert_data = AsyncMock()
        mock_db.disconnect = MagicMock()
        
        with patch('app.services.generation_service.ClickHouseDatabase', return_value=mock_db):
            with patch('app.services.generation_service.get_content_corpus_schema'):
                await save_corpus_to_clickhouse(corpus, "test_corpus")
                
                # Should handle all formats without error
                mock_db.insert_data.assert_called_once()
                records = mock_db.insert_data.call_args[0][1]
                assert len(records) == 4


class TestContentGeneration:
    """Test content generation functions"""
    
    @pytest.mark.asyncio
    async def test_generate_content_corpus_basic(self):
        """Test basic content corpus generation"""
        params = ContentGenParams(
            workload_types=["qa"],
            num_samples_per_type=2,
            output_format="json"
        )
        
        with patch('app.services.generation_service._run_parallel_generation') as mock_gen:
            mock_gen.return_value = {
                "qa": [("Q1", "A1"), ("Q2", "A2")]
            }
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
                with patch('app.services.generation_service.save_corpus_to_clickhouse', new_callable=AsyncMock):
                    result = await generate_content_corpus(params, "job123")
                    
                    assert result["status"] == "completed"
                    assert "qa" in result["corpus"]
                    assert len(result["corpus"]["qa"]) == 2
    
    @pytest.mark.asyncio
    async def test_generate_content_corpus_with_custom_table(self):
        """Test content generation with custom table name"""
        params = ContentGenParams(
            workload_types=["generation", "qa"],
            num_samples_per_type=5,
            output_format="json",
            corpus_table_name="custom_corpus"
        )
        
        with patch('app.services.generation_service._run_parallel_generation') as mock_gen:
            mock_gen.return_value = {
                "generation": [("P1", "R1")] * 5,
                "qa": [("Q1", "A1")] * 5
            }
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
                with patch('app.services.generation_service.save_corpus_to_clickhouse', new_callable=AsyncMock) as mock_save:
                    result = await generate_content_corpus(params, "job456")
                    
                    mock_save.assert_called_with(
                        mock_gen.return_value,
                        "custom_corpus",
                        "job456"
                    )
    
    @pytest.mark.asyncio
    async def test_generate_content_corpus_error_handling(self):
        """Test content generation error handling"""
        params = ContentGenParams(
            workload_types=["qa"],
            num_samples_per_type=10
        )
        
        with patch('app.services.generation_service._run_parallel_generation') as mock_gen:
            mock_gen.side_effect = Exception("Generation failed")
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock) as mock_update:
                result = await generate_content_corpus(params, "job789")
                
                assert result["status"] == "failed"
                assert "Generation failed" in result["error"]
                
                # Verify error status was updated
                mock_update.assert_any_call(
                    "job789", "failed", error="Generation failed"
                )


class TestLogGeneration:
    """Test synthetic log generation"""
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_llm_logs_basic(self):
        """Test basic log generation"""
        params = LogGenParams(
            num_logs=100,
            models=["gpt-4", "claude"],
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
            with patch('app.services.generation_service.ingest_records', new_callable=AsyncMock) as mock_ingest:
                result = await generate_synthetic_llm_logs(params, "log_job_1")
                
                assert result["status"] == "completed"
                assert result["total_generated"] == 100
                
                # Verify ingestion was called
                mock_ingest.assert_called_once()
                ingested_data = mock_ingest.call_args[0][0]
                assert len(ingested_data) == 100
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_llm_logs_with_corpus(self):
        """Test log generation with corpus"""
        params = LogGenParams(
            num_logs=50,
            models=["gpt-4"],
            corpus_table_name="test_corpus"
        )
        
        mock_corpus = {
            "qa": [("Question", "Answer")],
            "generation": [("Prompt", "Response")]
        }
        
        with patch('app.services.generation_service.get_corpus_from_clickhouse', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_corpus
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
                with patch('app.services.generation_service.ingest_records', new_callable=AsyncMock):
                    result = await generate_synthetic_llm_logs(params, "log_job_2")
                    
                    assert result["status"] == "completed"
                    mock_get.assert_called_once_with("test_corpus")
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_llm_logs_error(self):
        """Test log generation error handling"""
        params = LogGenParams(num_logs=1000)
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock) as mock_update:
            with patch('app.services.generation_service.ingest_records', new_callable=AsyncMock) as mock_ingest:
                mock_ingest.side_effect = Exception("Ingestion failed")
                
                result = await generate_synthetic_llm_logs(params, "log_job_3")
                
                assert result["status"] == "failed"
                assert "Ingestion failed" in result["error"]
                
                mock_update.assert_any_call(
                    "log_job_3", "failed", error="Ingestion failed"
                )


class TestSyntheticDataGeneration:
    """Test synthetic data batch generation"""
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_data_batch_success(self):
        """Test successful synthetic data batch generation"""
        params = SyntheticDataGenParams(
            schema={
                "name": "string",
                "age": "integer",
                "email": "email"
            },
            num_records=100
        )
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
            result = await generate_synthetic_data_batch(params, "data_job_1")
            
            assert result["status"] == "completed"
            assert len(result["data"]) == 100
            assert all("name" in record for record in result["data"])
            assert all("age" in record for record in result["data"])
            assert all("email" in record for record in result["data"])
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_data_with_constraints(self):
        """Test synthetic data generation with constraints"""
        params = SyntheticDataGenParams(
            schema={
                "id": "uuid",
                "status": {"type": "choice", "values": ["active", "inactive"]},
                "score": {"type": "float", "min": 0, "max": 100}
            },
            num_records=50,
            constraints={"unique": ["id"]}
        )
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
            result = await generate_synthetic_data_batch(params, "data_job_2")
            
            assert result["status"] == "completed"
            assert len(result["data"]) == 50
            
            # Check uniqueness
            ids = [record["id"] for record in result["data"]]
            assert len(ids) == len(set(ids))
            
            # Check constraints
            for record in result["data"]:
                assert record["status"] in ["active", "inactive"]
                assert 0 <= record["score"] <= 100
    
    @pytest.mark.asyncio
    async def test_generate_synthetic_data_error(self):
        """Test synthetic data generation error handling"""
        params = SyntheticDataGenParams(
            schema={"invalid": "unknown_type"},
            num_records=10
        )
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock) as mock_update:
            # Force an error by using invalid schema
            with patch('app.services.generation_service.Faker') as mock_faker:
                mock_faker.side_effect = Exception("Invalid schema")
                
                result = await generate_synthetic_data_batch(params, "data_job_3")
                
                assert result["status"] == "failed"
                mock_update.assert_any_call(
                    "data_job_3", "failed", error=pytest.Any(str)
                )


class TestHelperFunctions:
    """Test helper and utility functions"""
    
    def test_split_params_even_split(self):
        """Test parameter splitting with even distribution"""
        from app.services.generation_service import _split_params
        
        params = ContentGenParams(
            workload_types=["qa", "generation"],
            num_samples_per_type=100
        )
        
        splits = _split_params(params, 4)
        
        assert len(splits) == 4
        # Each worker should get 50 samples (100 total per type / 2 types = 50)
        for split in splits:
            assert split.num_samples_per_type == 25
    
    def test_split_params_uneven_split(self):
        """Test parameter splitting with uneven distribution"""
        from app.services.generation_service import _split_params
        
        params = ContentGenParams(
            workload_types=["qa"],
            num_samples_per_type=17
        )
        
        splits = _split_params(params, 4)
        
        assert len(splits) == 4
        # Should distribute 17 samples across 4 workers: 5, 4, 4, 4
        sample_counts = [s.num_samples_per_type for s in splits]
        assert sum(sample_counts) == 17
        assert max(sample_counts) - min(sample_counts) <= 1
    
    def test_generate_log_entry(self):
        """Test single log entry generation"""
        from app.services.generation_service import generate_log_entry
        
        corpus = {
            "qa": [("Test question?", "Test answer.")],
            "generation": [("Generate text", "Generated response")]
        }
        
        models = ["gpt-4", "claude-3"]
        
        log = generate_log_entry(0, corpus, models)
        
        assert log["model"] in models
        assert log["workload_type"] in ["qa", "generation"]
        assert "prompt" in log
        assert "response" in log
        assert "metrics" in log
        assert log["metrics"]["latency_ms"] > 0
        assert log["metrics"]["tokens_used"] > 0
    
    def test_parallel_generate_sample(self):
        """Test parallel sample generation"""
        from app.services.generation_service import parallel_generate_sample
        
        result = parallel_generate_sample("qa", 0)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)  # prompt
        assert isinstance(result[1], str)  # response
    
    @patch('app.services.generation_service.Pool')
    def test_run_parallel_generation(self, mock_pool_class):
        """Test parallel generation runner"""
        from app.services.generation_service import _run_parallel_generation
        
        mock_pool = MagicMock()
        mock_pool_class.return_value.__enter__.return_value = mock_pool
        mock_pool.map.return_value = [
            ("Q1", "A1"),
            ("Q2", "A2")
        ]
        
        params = ContentGenParams(
            workload_types=["qa"],
            num_samples_per_type=2
        )
        
        result = _run_parallel_generation(params)
        
        assert "qa" in result
        assert len(result["qa"]) == 2
        mock_pool.map.assert_called_once()


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_workload_types(self):
        """Test generation with empty workload types"""
        params = ContentGenParams(
            workload_types=[],
            num_samples_per_type=10
        )
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
            result = await generate_content_corpus(params, "empty_job")
            
            assert result["corpus"] == {}
    
    @pytest.mark.asyncio
    async def test_zero_samples(self):
        """Test generation with zero samples"""
        params = ContentGenParams(
            workload_types=["qa"],
            num_samples_per_type=0
        )
        
        with patch('app.services.generation_service._run_parallel_generation') as mock_gen:
            mock_gen.return_value = {"qa": []}
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
                result = await generate_content_corpus(params, "zero_job")
                
                assert result["corpus"]["qa"] == []
    
    @pytest.mark.asyncio
    async def test_very_large_batch(self):
        """Test generation with very large batch size"""
        params = LogGenParams(
            num_logs=100000,
            models=["gpt-4"]
        )
        
        with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
            with patch('app.services.generation_service.ingest_records', new_callable=AsyncMock) as mock_ingest:
                # Should handle large batches by chunking
                result = await generate_synthetic_llm_logs(params, "large_job")
                
                assert result["status"] == "completed"
                assert result["total_generated"] == 100000
                
                # Verify chunked ingestion
                assert mock_ingest.call_count > 1
    
    @pytest.mark.asyncio
    async def test_concurrent_job_updates(self):
        """Test concurrent job status updates"""
        jobs = ["job1", "job2", "job3"]
        
        with patch('app.services.generation_service.job_store') as mock_store:
            with patch('app.services.generation_service.manager') as mock_manager:
                mock_store.update = AsyncMock()
                mock_manager.broadcast = AsyncMock()
                
                # Simulate concurrent updates
                tasks = [
                    update_job_status(job_id, "running", progress=i*10)
                    for i, job_id in enumerate(jobs)
                ]
                
                await asyncio.gather(*tasks)
                
                assert mock_store.update.call_count == 3
                assert mock_manager.broadcast.call_count == 3


class TestIntegration:
    """Integration tests for generation service"""
    
    @pytest.mark.asyncio
    async def test_full_content_generation_flow(self):
        """Test complete content generation workflow"""
        params = ContentGenParams(
            workload_types=["qa", "generation", "summarization"],
            num_samples_per_type=10,
            output_format="json",
            corpus_table_name="test_full_corpus"
        )
        
        with patch('app.services.generation_service._run_parallel_generation') as mock_gen:
            mock_gen.return_value = {
                "qa": [("Q", "A")] * 10,
                "generation": [("G", "R")] * 10,
                "summarization": [("S", "Sum")] * 10
            }
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock) as mock_update:
                with patch('app.services.generation_service.save_corpus_to_clickhouse', new_callable=AsyncMock) as mock_save:
                    result = await generate_content_corpus(params, "integration_job")
                    
                    # Verify workflow steps
                    assert mock_update.call_count >= 2  # At least running and completed
                    assert mock_save.called
                    assert result["status"] == "completed"
                    assert len(result["corpus"]) == 3
                    assert result["total_samples"] == 30
    
    @pytest.mark.asyncio
    async def test_log_generation_with_corpus_fallback(self):
        """Test log generation with corpus fallback on error"""
        params = LogGenParams(
            num_logs=100,
            corpus_table_name="missing_corpus"
        )
        
        with patch('app.services.generation_service.get_corpus_from_clickhouse', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Corpus not found")
            
            with patch('app.services.generation_service.update_job_status', new_callable=AsyncMock):
                with patch('app.services.generation_service.ingest_records', new_callable=AsyncMock):
                    # Should fall back to default corpus
                    result = await generate_synthetic_llm_logs(params, "fallback_job")
                    
                    assert result["status"] == "completed"
                    assert result["total_generated"] == 100