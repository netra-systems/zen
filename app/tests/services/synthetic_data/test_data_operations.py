"""
Tests for data generation, batch operations, and corpus loading
"""

import pytest
import asyncio
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.synthetic_data_service import (
    SyntheticDataService,
    GenerationStatus
)
from app.db import models_postgres as models


class MockSession:
    """Mock database session"""
    def __init__(self):
        self.query_results = {}
        self.added_objects = []
        self.committed = False
        self.refresh_called = False
    
    def query(self, model):
        return MockQuery(self.query_results.get(model, []))
    
    def add(self, obj):
        self.added_objects.append(obj)
    
    def commit(self):
        self.committed = True
    
    def refresh(self, obj):
        self.refresh_called = True


class MockQuery:
    """Mock database query"""
    def __init__(self, results):
        self.results = results
        self.filters = []
    
    def filter(self, *args):
        self.filters.extend(args)
        return self
    
    def first(self):
        return self.results[0] if self.results else None
    
    def all(self):
        return self.results
    
    def update(self, values):
        return len(self.results)


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MockSession()


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


@pytest.fixture
def sample_config():
    """Create sample LogGenParams"""
    config = MagicMock()
    config.num_logs = 100
    config.corpus_id = None
    return config


@pytest.fixture
def mock_corpus():
    """Create mock corpus"""
    corpus = MagicMock()
    corpus.id = "test-corpus-id"
    corpus.name = "Test Corpus"
    corpus.table_name = "test_corpus_table"
    corpus.status = "completed"
    return corpus


@pytest.mark.asyncio
class TestSingleRecordGeneration:
    """Test single record generation"""
    
    async def test_generate_single_record(self, service, sample_config):
        """Test generating a single record"""
        record = await service._generate_single_record(sample_config, None, 0)
        
        # Verify required fields
        required_fields = [
            "event_id", "trace_id", "span_id", "timestamp_utc",
            "workload_type", "agent_type", "tool_invocations",
            "request_payload", "response_payload", "metrics"
        ]
        
        for field in required_fields:
            assert field in record
        
        # Verify field types
        assert isinstance(record["event_id"], str)
        assert isinstance(record["trace_id"], str)
        assert isinstance(record["span_id"], str)
        assert isinstance(record["timestamp_utc"], datetime)
        assert isinstance(record["tool_invocations"], list)
        assert isinstance(record["request_payload"], dict)
        assert isinstance(record["response_payload"], dict)
        assert isinstance(record["metrics"], dict)
    
    async def test_generate_single_record_with_corpus(self, service, sample_config):
        """Test generating record with corpus content"""
        corpus_content = [{"prompt": "Test", "response": "Response"}]
        
        record = await service._generate_single_record(sample_config, corpus_content, 0)
        
        assert "request_payload" in record
        assert "response_payload" in record


@pytest.mark.asyncio
class TestBatchGeneration:
    """Test batch generation functionality"""
    
    async def test_generate_batches(self, service, sample_config):
        """Test batch generation async generator"""
        sample_config.num_logs = 5
        
        batches = []
        async for batch_num, batch in service._generate_batches(sample_config, None, 2, 5):
            batches.append((batch_num, batch))
        
        # Should have 3 batches: [2, 2, 1]
        assert len(batches) == 3
        assert batches[0][0] == 0  # First batch number
        assert len(batches[0][1]) == 2  # First batch size
        assert len(batches[1][1]) == 2  # Second batch size
        assert len(batches[2][1]) == 1  # Third batch size
    
    async def test_generate_batch(self, service, sample_config):
        """Test generate_batch method"""
        batch = await service.generate_batch(sample_config, 3)
        
        assert len(batch) == 3
        for record in batch:
            assert "event_id" in record
            assert "trace_id" in record


@pytest.mark.asyncio
class TestCorpusLoading:
    """Test corpus loading and caching"""
    
    async def test_load_corpus_cached(self, service, mock_db):
        """Test loading corpus from cache"""
        corpus_id = "test-corpus"
        cached_data = [{"prompt": "cached", "response": "data"}]
        service.corpus_cache[corpus_id] = cached_data
        
        result = await service._load_corpus(corpus_id, mock_db)
        
        assert result == cached_data
    
    async def test_load_corpus_not_found(self, service, mock_db):
        """Test loading non-existent corpus"""
        mock_db.query_results[models.Corpus] = []
        
        result = await service._load_corpus("non-existent", mock_db)
        
        assert result == None
    
    async def test_load_corpus_not_completed(self, service, mock_db, mock_corpus):
        """Test loading corpus that's not completed"""
        mock_corpus.status = "pending"
        mock_db.query_results[models.Corpus] = [mock_corpus]
        
        result = await service._load_corpus("test-corpus", mock_db)
        
        assert result == None
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_load_corpus_success(self, mock_get_client, service, mock_db, mock_corpus):
        """Test successful corpus loading"""
        mock_db.query_results[models.Corpus] = [mock_corpus]
        
        mock_client = AsyncMock()
        mock_client.execute.return_value = [
            ("type1", "prompt1", "response1", "{}"),
            ("type2", "prompt2", "response2", "{}")
        ]
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        result = await service._load_corpus("test-corpus", mock_db)
        
        assert result != None
        assert len(result) == 2
        assert result[0]["prompt"] == "prompt1"
        assert result[0]["response"] == "response1"
        
        # Check caching
        assert service.corpus_cache["test-corpus"] == result
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_load_corpus_clickhouse_error(self, mock_get_client, service, mock_db, mock_corpus):
        """Test corpus loading with ClickHouse error"""
        mock_db.query_results[models.Corpus] = [mock_corpus]
        mock_get_client.side_effect = Exception("ClickHouse error")
        
        result = await service._load_corpus("test-corpus", mock_db)
        
        assert result == None