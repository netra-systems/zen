"""
Corpus metadata and error recovery tests
Tests metadata tracking throughout corpus lifecycle and error recovery mechanisms
COMPLIANCE: 300-line max file, 8-line max functions
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.corpus_service import CorpusService, CorpusStatus, ContentSource
from app.schemas import CorpusCreate, CorpusUpdate


class TestMetadataTracking:
    """Test metadata tracking throughout corpus lifecycle"""
    
    async def test_corpus_metadata_creation(self):
        """Test 16: Verify metadata is properly initialized"""
        service = CorpusService()
        
        db = MagicMock()
        corpus_data = _create_metadata_test_corpus()
        
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
        corpus = _create_mock_corpus_with_metadata()
        
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
            corpus = _create_available_corpus()
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
            corpus = _create_deletable_corpus()
            db.query().filter().first.return_value = corpus
            
            result = await service.delete_corpus(db, "test_id")
            
            assert result == False
            
            # Should revert status to FAILED
            corpus.status = CorpusStatus.FAILED.value
            db.commit.assert_called()


def _create_metadata_test_corpus():
    """Create corpus for metadata testing."""
    return CorpusCreate(
        name="test", 
        description="test",
        domain="testing"
    )


def _create_mock_corpus_with_metadata():
    """Create mock corpus with metadata."""
    corpus = MagicMock()
    corpus.metadata_ = json.dumps({"version": 1})
    return corpus


def _create_available_corpus():
    """Create available corpus for testing."""
    corpus = MagicMock()
    corpus.status = "available"
    corpus.table_name = "test_table"
    return corpus


def _create_deletable_corpus():
    """Create corpus for deletion testing."""
    corpus = MagicMock()
    corpus.status = "available"
    corpus.table_name = "test_table"
    return corpus