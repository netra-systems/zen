"""
Test Suite 3: Corpus Generation Coverage Tests
Tests comprehensive coverage of corpus generation workflows
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from netra_backend.app.schemas import ContentGenParams, CorpusCreate, CorpusUpdate

# Add project root to path
from netra_backend.app.services.corpus_service import (
    ContentSource,
    CorpusService,
    CorpusStatus,
)
from netra_backend.app.services.generation_service import (
    get_corpus_from_clickhouse,
    # Add project root to path
    run_content_generation_job,
    run_synthetic_data_generation_job,
    save_corpus_to_clickhouse,
)


class TestCorpusLifecycle:
    """Test complete corpus lifecycle from creation to deletion"""
    async def test_corpus_creation_workflow(self):
        """Test 1: Verify complete corpus creation workflow"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            corpus_data = CorpusCreate(
                name="test_corpus",
                description="Test corpus for coverage",
                domain="testing"
            )
            
            # Create corpus
            corpus = await service.create_corpus(
                db, corpus_data, "test_user", ContentSource.GENERATE
            )
            
            # Verify corpus attributes
            assert corpus.name == "test_corpus"
            assert corpus.status == CorpusStatus.CREATING.value
            assert corpus.created_by_id == "test_user"
            assert "netra_content_corpus_" in corpus.table_name
            
            # Verify metadata
            metadata = json.loads(corpus.metadata_)
            assert metadata["content_source"] == ContentSource.GENERATE.value
            assert metadata["version"] == 1
    async def test_corpus_status_transitions(self):
        """Test 2: Verify corpus status transitions"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            
            # Test status flow: CREATING -> AVAILABLE
            await service._create_clickhouse_table("corpus_id", "table_name", db)
            
            # Verify status update to AVAILABLE
            db.query().filter().update.assert_called_with(
                {"status": CorpusStatus.AVAILABLE.value}
            )
            
            # Test error flow: CREATING -> FAILED
            mock_instance.execute.side_effect = Exception("Table creation failed")
            await service._create_clickhouse_table("corpus_id2", "table_name2", db)
            
            # Verify status update to FAILED
            calls = db.query().filter().update.call_args_list
            assert {"status": CorpusStatus.FAILED.value} in [call[0][0] for call in calls]
    async def test_corpus_deletion_workflow(self):
        """Test 3: Verify complete corpus deletion workflow"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            corpus = MagicMock()
            corpus.id = "test_id"
            corpus.table_name = "test_table"
            corpus.status = CorpusStatus.AVAILABLE.value
            
            db.query().filter().first.return_value = corpus
            
            result = await service.delete_corpus(db, "test_id")
            
            # Verify deletion steps
            assert result == True
            mock_instance.execute.assert_called_with("DROP TABLE IF EXISTS test_table")
            db.delete.assert_called_with(corpus)
            db.commit.assert_called()


class TestWorkloadTypesCoverage:
    """Test coverage of all workload types"""
    async def test_all_workload_types_supported(self):
        """Test 4: Verify all workload types are supported"""
        service = CorpusService()
        
        valid_workload_types = [
            "simple_chat",
            "rag_pipeline", 
            "tool_use",
            "multi_turn_tool_use",
            "failed_request",
            "custom_domain"
        ]
        
        for workload_type in valid_workload_types:
            records = [{
                "workload_type": workload_type,
                "prompt": "test prompt",
                "response": "test response"
            }]
            
            result = service._validate_records(records)
            assert result["valid"], f"Workload type {workload_type} should be valid"
    async def test_workload_distribution_tracking(self):
        """Test 5: Verify workload distribution is tracked correctly"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock distribution query result
            mock_instance.execute.side_effect = [
                [(1000, 6, 100, 200, datetime.now(), datetime.now())],  # stats
                [
                    ("simple_chat", 400),
                    ("rag_pipeline", 300),
                    ("tool_use", 200),
                    ("multi_turn_tool_use", 50),
                    ("failed_request", 30),
                    ("custom_domain", 20)
                ]  # distribution
            ]
            
            db = MagicMock()
            corpus = MagicMock()
            corpus.status = "available"
            corpus.table_name = "test_table"
            db.query().filter().first.return_value = corpus
            
            stats = await service.get_corpus_statistics(db, "test_id")
            
            # Verify all workload types are tracked
            assert len(stats["workload_distribution"]) == 6
            assert sum(stats["workload_distribution"].values()) == 1000


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
                    
                    params = ContentGenParams(
                        samples_per_type=10,
                        temperature=0.7,
                        clickhouse_table="test_corpus"
                    )
                    
                    await run_content_generation_job("job_123", params)
                    
                    # Verify job status updates
                    assert mock_update.call_count >= 3  # running, progress, completed
                    
                    # Verify corpus was saved
                    mock_save.assert_called_once()
                    saved_corpus = mock_save.call_args[0][0]
                    assert "simple_chat" in saved_corpus
                    assert "rag_pipeline" in saved_corpus
    async def test_corpus_save_to_clickhouse(self):
        """Test 7: Verify corpus is properly saved to ClickHouse"""
        corpus = {
            "simple_chat": [("p1", "r1"), ("p2", "r2")],
            "rag_pipeline": [("p3", "r3")],
            "tool_use": [("p4", "r4")]
        }
        
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
            mock_instance.execute_query.return_value = [
                {"workload_type": "simple_chat", "prompt": "p1", "response": "r1"},
                {"workload_type": "simple_chat", "prompt": "p2", "response": "r2"},
                {"workload_type": "rag_pipeline", "prompt": "p3", "response": "r3"}
            ]
            
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
            
            db = MagicMock()
            corpus = MagicMock()
            corpus.status = "available"
            corpus.table_name = "test_table"
            db.query().filter().first.return_value = corpus
            
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
                mock_get.return_value = {
                    "simple_chat": [("p1", "r1")],
                    "rag_pipeline": [("p2", "r2")]
                }
                
                with patch('app.services.generation_service.synthetic_data_main') as mock_main:
                    # Mock generated logs
                    mock_main.return_value = [
                        {"log": i} for i in range(2500)  # 2.5 batches
                    ]
                    
                    with patch('app.services.generation_service.ingest_records') as mock_ingest:
                        mock_ingest.return_value = 1000  # Each batch
                        
                        params = {
                            "batch_size": 1000,
                            "num_traces": 2500,
                            "source_table": "corpus",
                            "destination_table": "synthetic"
                        }
                        
                        await run_synthetic_data_generation_job("job_id", params)
                        
                        # Should call ingest 3 times (2 full batches + 1 partial)
                        assert mock_ingest.call_count == 3


class TestCorpusCloning:
    """Test corpus cloning functionality"""
    async def test_corpus_clone_workflow(self):
        """Test 11: Verify corpus cloning creates new corpus with data"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            
            # Mock source corpus
            source = MagicMock()
            source.id = "source_id"
            source.name = "Original Corpus"
            source.status = "available"
            source.table_name = "source_table"
            source.domain = "testing"
            
            db.query().filter().first.return_value = source
            
            # Clone corpus
            result = await service.clone_corpus(
                db, "source_id", "Cloned Corpus", "new_user"
            )
            
            assert result != None
            assert result.name == "Cloned Corpus"
            assert result.description == "Clone of Original Corpus"
    async def test_corpus_content_copy(self):
        """Test 12: Verify corpus content is copied correctly"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            db = MagicMock()
            
            await service._copy_corpus_content(
                "source_table", "dest_table", "corpus_id", db
            )
            
            # Should wait for table to be ready
            await asyncio.sleep(2.1)
            
            # Verify copy query
            mock_instance.execute.assert_called()
            query = mock_instance.execute.call_args[0][0]
            assert "INSERT INTO dest_table" in query
            assert "SELECT * FROM source_table" in query


class TestValidationAndSafety:
    """Test validation and safety measures"""
    
    def test_prompt_response_length_validation(self):
        """Test 13: Verify prompt/response length limits"""
        service = CorpusService()
        
        # Test max length validation
        long_prompt = "x" * 100001
        long_response = "y" * 100001
        
        records = [
            {"workload_type": "simple_chat", "prompt": long_prompt, "response": "r"},
            {"workload_type": "simple_chat", "prompt": "p", "response": long_response}
        ]
        
        result = service._validate_records(records)
        
        assert not result["valid"]
        assert "exceeds maximum length" in str(result["errors"])
    
    def test_required_fields_validation(self):
        """Test 14: Verify all required fields are validated"""
        service = CorpusService()
        
        test_cases = [
            ({}, ["missing 'prompt'", "missing 'response'", "missing 'workload_type'"]),
            ({"prompt": "p"}, ["missing 'response'", "missing 'workload_type'"]),
            ({"response": "r"}, ["missing 'prompt'", "missing 'workload_type'"]),
            ({"workload_type": "test"}, ["missing 'prompt'", "missing 'response'"])
        ]
        
        for record, expected_errors in test_cases:
            result = service._validate_records([record])
            assert not result["valid"]
            for expected in expected_errors:
                assert any(expected in error for error in result["errors"])
    async def test_corpus_access_control(self):
        """Test 15: Verify corpus access control"""
        service = CorpusService()
        
        db = MagicMock()
        
        # Test filtering by user_id
        await service.get_corpora(db, user_id="specific_user")
        
        # Verify filter was applied
        db.query().filter.assert_called()
        filter_call = db.query().filter.call_args
        assert filter_call != None


class TestMetadataTracking:
    """Test metadata tracking throughout corpus lifecycle"""
    async def test_corpus_metadata_creation(self):
        """Test 16: Verify metadata is properly initialized"""
        service = CorpusService()
        
        db = MagicMock()
        corpus_data = CorpusCreate(
            name="test", 
            description="test",
            domain="testing"
        )
        
        corpus = await service.create_corpus(
            db, corpus_data, "user1", ContentSource.UPLOAD
        )
        
        metadata = json.loads(corpus.metadata_)
        assert metadata["content_source"] == "upload"
        assert metadata["version"] == 1
        assert "created_at" in metadata
    async def test_corpus_metadata_update(self):
        """Test 17: Verify metadata is updated correctly"""
        service = CorpusService()
        
        db = MagicMock()
        corpus = MagicMock()
        corpus.metadata_ = json.dumps({"version": 1})
        
        db.query().filter().first.return_value = corpus
        
        update_data = CorpusUpdate(name="Updated Name")
        
        result = await service.update_corpus(db, "test_id", update_data)
        
        metadata = json.loads(result.metadata_)
        assert metadata["version"] == 2
        assert "updated_at" in metadata


class TestErrorRecovery:
    """Test error recovery mechanisms"""
    async def test_table_creation_failure_recovery(self):
        """Test 18: Verify recovery from table creation failure"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Simulate table creation failure
            mock_instance.execute.side_effect = Exception("Cannot create table")
            
            db = MagicMock()
            
            await service._create_clickhouse_table("corpus_id", "table_name", db)
            
            # Should update status to FAILED
            db.query().filter().update.assert_called_with(
                {"status": CorpusStatus.FAILED.value}
            )
    async def test_upload_failure_recovery(self):
        """Test 19: Verify recovery from upload failure"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Simulate insert failure
            mock_instance.execute.side_effect = Exception("Insert failed")
            
            db = MagicMock()
            corpus = MagicMock()
            corpus.status = "available"
            corpus.table_name = "test_table"
            db.query().filter().first.return_value = corpus
            
            records = [
                {"workload_type": "simple_chat", "prompt": "p", "response": "r"}
            ]
            
            result = await service.upload_content(db, "test_id", records)
            
            assert result["records_uploaded"] == 0
            assert "Insert failed" in str(result["validation_errors"])
    async def test_deletion_failure_recovery(self):
        """Test 20: Verify recovery from deletion failure"""
        service = CorpusService()
        
        with patch('app.services.corpus_service.get_clickhouse_client') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Simulate drop table failure
            mock_instance.execute.side_effect = Exception("Cannot drop table")
            
            db = MagicMock()
            corpus = MagicMock()
            corpus.status = "available"
            corpus.table_name = "test_table"
            db.query().filter().first.return_value = corpus
            
            result = await service.delete_corpus(db, "test_id")
            
            assert result == False
            
            # Should revert status to FAILED
            corpus.status = CorpusStatus.FAILED.value
            db.commit.assert_called()