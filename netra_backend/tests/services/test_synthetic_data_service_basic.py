"""
Basic Test Suite for Synthetic Data Generation Service
Testing corpus management and basic functionality
"""

import pytest
import asyncio
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.corpus_service import CorpusStatus
from netra_backend.app import schemas
from netra_backend.tests.test_synthetic_data_service_fixtures import *


# ==================== Test Suite: Corpus Management ====================

class TestCorpusManagement:
    """Test corpus lifecycle management and integration"""
    async def test_corpus_creation_with_clickhouse_table(self, corpus_service, mock_db, mock_clickhouse_client):
        """Test creating corpus with corresponding ClickHouse table"""
        corpus_data = schemas.CorpusCreate(
            name="test_corpus",
            description="Test corpus for unit tests",
            domain="e-commerce"
        )
        
        with patch('app.services.corpus_service.get_clickhouse_client', return_value=mock_clickhouse_client):
            result = await corpus_service.create_corpus(
                mock_db, corpus_data, "user123"
            )
        
        assert result.name == "test_corpus"
        assert result.status == CorpusStatus.CREATING.value
        assert "netra_content_corpus_" in result.table_name
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    async def test_corpus_status_transitions(self, corpus_service):
        """Test corpus status lifecycle transitions"""
        valid_transitions = {
            CorpusStatus.CREATING: [CorpusStatus.AVAILABLE, CorpusStatus.FAILED],
            CorpusStatus.AVAILABLE: [CorpusStatus.UPDATING, CorpusStatus.DELETING],
            CorpusStatus.UPDATING: [CorpusStatus.AVAILABLE, CorpusStatus.FAILED],
            CorpusStatus.FAILED: [CorpusStatus.CREATING, CorpusStatus.DELETING],
            CorpusStatus.DELETING: []
        }
        
        for from_status, to_statuses in valid_transitions.items():
            for to_status in to_statuses:
                assert corpus_service.is_valid_transition(from_status, to_status)
    async def test_corpus_content_upload_batch(self, corpus_service, mock_clickhouse_client):
        """Test batch upload of corpus content"""
        corpus_id = str(uuid.uuid4())
        records = [
            {
                "workload_type": "simple_chat",
                "prompt": f"Test prompt {i}",
                "response": f"Test response {i}",
                "metadata": {"index": i}
            }
            for i in range(100)
        ]
        
        with patch('app.services.corpus_service.get_clickhouse_client', return_value=mock_clickhouse_client):
            result = await corpus_service.upload_corpus_content(
                corpus_id, records, batch_size=50
            )
        
        assert result["records_uploaded"] == 100
        assert result["batches_processed"] == 2
        assert mock_clickhouse_client.execute.call_count == 2
    async def test_corpus_validation(self, corpus_service):
        """Test corpus content validation"""
        valid_record = {
            "workload_type": "tool_use",
            "prompt": "Valid prompt",
            "response": "Valid response",
            "metadata": {"tool": "calculator"}
        }
        
        invalid_record = {
            "workload_type": "invalid_type",
            "prompt": "",  # Empty prompt
            "response": "Response without prompt"
        }
        
        assert corpus_service.validate_corpus_record(valid_record) == True
        assert corpus_service.validate_corpus_record(invalid_record) == False
    async def test_corpus_availability_check(self, corpus_service, mock_clickhouse_client):
        """Test checking corpus availability in ClickHouse"""
        corpus_id = str(uuid.uuid4())
        table_name = f"netra_content_corpus_{corpus_id.replace('-', '_')}"
        
        mock_clickhouse_client.query.return_value = [(table_name, 1000)]
        
        with patch('app.services.corpus_service.get_clickhouse_client', return_value=mock_clickhouse_client):
            is_available, record_count = await corpus_service.check_corpus_availability(
                corpus_id
            )
        
        assert is_available == True
        assert record_count == 1000
    async def test_corpus_fallback_to_default(self, corpus_service):
        """Test fallback to default corpus when primary unavailable"""
        with patch('app.services.corpus_service.get_default_corpus') as mock_default:
            mock_default.return_value = {"default": "corpus"}
            
            result = await corpus_service.get_corpus_content(
                "non_existent_corpus",
                use_fallback=True
            )
            
            assert result == {"default": "corpus"}
            mock_default.assert_called_once()
    async def test_corpus_caching_mechanism(self, corpus_service):
        """Test corpus content caching for performance"""
        corpus_id = str(uuid.uuid4())
        
        # First call should fetch from database
        with patch.object(corpus_service, '_fetch_corpus_content') as mock_fetch:
            mock_fetch.return_value = [{"test": "data"}]
            result1 = await corpus_service.get_corpus_content_cached(corpus_id)
            assert mock_fetch.call_count == 1
        
        # Second call should use cache
        result2 = await corpus_service.get_corpus_content_cached(corpus_id)
        assert result1 == result2
        assert corpus_id in corpus_service.content_buffer
    async def test_corpus_deletion_cascade(self, corpus_service, mock_db, mock_clickhouse_client):
        """Test corpus deletion with ClickHouse table cleanup"""
        corpus_id = str(uuid.uuid4())
        
        with patch('app.services.corpus_service.get_clickhouse_client', return_value=mock_clickhouse_client):
            await corpus_service.delete_corpus(mock_db, corpus_id)
        
        # Should drop ClickHouse table and delete PostgreSQL record
        mock_clickhouse_client.execute.assert_called()
        mock_db.query.assert_called()
        mock_db.delete.assert_called()
    async def test_corpus_metadata_tracking(self, corpus_service):
        """Test corpus metadata and versioning"""
        metadata = corpus_service.create_corpus_metadata(
            source="upload",
            version=2,
            domain="healthcare",
            custom_fields={"compliance": "HIPAA"}
        )
        
        assert metadata["source"] == "upload"
        assert metadata["version"] == 2
        assert metadata["domain"] == "healthcare"
        assert metadata["custom_fields"]["compliance"] == "HIPAA"
        assert "created_at" in metadata
    async def test_corpus_concurrent_access(self, corpus_service):
        """Test concurrent corpus access handling"""
        corpus_id = str(uuid.uuid4())
        
        async def access_corpus():
            return await corpus_service.get_corpus_content(corpus_id)
        
        # Simulate concurrent access
        tasks = [access_corpus() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle concurrent access without errors
        assert all(not isinstance(r, Exception) for r in results)


# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])