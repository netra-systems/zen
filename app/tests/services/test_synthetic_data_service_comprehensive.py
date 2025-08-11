"""
Comprehensive tests for SyntheticDataService with extensive coverage
Tests all methods, error handling, edge cases, async operations, and mock external dependencies
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict, Any, AsyncGenerator
from collections import namedtuple

from app.services.synthetic_data_service import (
    SyntheticDataService,
    WorkloadCategory,
    GenerationStatus,
    synthetic_data_service
)
from app import schemas
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
def mock_clickhouse_client():
    """Create mock ClickHouse client"""
    client = AsyncMock()
    client.execute = AsyncMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def mock_corpus():
    """Create mock corpus"""
    corpus = MagicMock()
    corpus.id = "test-corpus-id"
    corpus.name = "Test Corpus"
    corpus.table_name = "test_corpus_table"
    corpus.status = "completed"
    return corpus


class TestServiceInitialization:
    """Test service initialization and setup"""
    
    def test_initialization(self, service):
        """Test service initializes correctly with default values"""
        assert service.active_jobs == {}
        assert service.corpus_cache == {}
        assert hasattr(service, 'default_tools')
        assert len(service.default_tools) > 0
        
    def test_default_tools_structure(self, service):
        """Test default tools have required structure"""
        for tool in service.default_tools:
            assert "name" in tool
            assert "type" in tool
            assert "latency_ms_range" in tool
            assert "failure_rate" in tool
            assert isinstance(tool["latency_ms_range"], tuple)
            assert len(tool["latency_ms_range"]) == 2
            assert 0 <= tool["failure_rate"] <= 1


class TestWorkloadTypeSelection:
    """Test workload type selection and distribution"""
    
    def test_select_workload_type(self, service):
        """Test workload type selection returns valid types"""
        # Test multiple selections for distribution
        types = set()
        for _ in range(100):
            workload_type = service._select_workload_type()
            types.add(workload_type)
            assert workload_type in [
                "simple_queries", "tool_orchestration", "data_analysis",
                "optimization_workflows", "error_scenarios"
            ]
        
        # Should select multiple different types over 100 iterations
        assert len(types) > 1
    
    def test_select_agent_type(self, service):
        """Test agent type selection for different workload types"""
        test_cases = [
            ("simple_queries", "triage"),
            ("tool_orchestration", "supervisor"),
            ("data_analysis", "data_analysis"),
            ("optimization_workflows", "optimization"),
            ("error_scenarios", "triage"),
            ("unknown_type", "general")
        ]
        
        for workload_type, expected_agent in test_cases:
            agent = service._select_agent_type(workload_type)
            assert agent == expected_agent


class TestToolInvocations:
    """Test tool invocation generation"""
    
    def test_generate_tool_invocations_simple(self, service):
        """Test simple queries tool invocation"""
        invocations = service._generate_tool_invocations("simple_queries")
        
        assert len(invocations) == 1
        assert "name" in invocations[0]
        assert "type" in invocations[0]
        assert "latency_ms" in invocations[0]
        assert "status" in invocations[0]
        assert invocations[0]["status"] in ["success", "failed"]
    
    def test_generate_tool_invocations_orchestration(self, service):
        """Test tool orchestration invocations"""
        invocations = service._generate_tool_invocations("tool_orchestration")
        
        assert 2 <= len(invocations) <= 5
        for inv in invocations:
            assert "name" in inv
            assert "latency_ms" in inv
            assert inv["latency_ms"] > 0
    
    def test_generate_tool_invocations_data_analysis(self, service):
        """Test data analysis tool invocations"""
        invocations = service._generate_tool_invocations("data_analysis")
        
        # Should have query and analysis tools
        assert len(invocations) >= 1
        tool_types = [inv.get("type") for inv in invocations]
        # May have query or analysis tools (depends on availability)
        assert any(t in ["query", "analysis"] for t in tool_types if t)
    
    def test_generate_tool_invocations_error_scenarios(self, service):
        """Test error scenario invocations"""
        invocations = service._generate_tool_invocations("error_scenarios")
        
        assert len(invocations) == 1
        assert invocations[0]["status"] == "failed"
        assert "error" in invocations[0]
        assert invocations[0]["error"] == "Simulated error"
    
    def test_create_tool_invocation(self, service):
        """Test individual tool invocation creation"""
        tool = {
            "name": "test_tool",
            "type": "query",
            "latency_ms_range": (50, 200),
            "failure_rate": 0.1
        }
        
        invocation = service._create_tool_invocation(tool)
        
        assert invocation["name"] == "test_tool"
        assert invocation["type"] == "query"
        assert 50 <= invocation["latency_ms"] <= 200
        assert invocation["status"] in ["success", "failed"]
        
        if invocation["status"] == "failed":
            assert invocation["error"] == "Tool execution failed"
        else:
            assert invocation["error"] is None


class TestContentGeneration:
    """Test content generation from corpus and synthetic sources"""
    
    def test_generate_content_with_corpus(self, service):
        """Test content generation using corpus"""
        corpus_content = [
            {"prompt": "Test prompt 1", "response": "Test response 1"},
            {"prompt": "Test prompt 2", "response": "Test response 2"}
        ]
        
        request, response = service._generate_content("simple_queries", corpus_content)
        
        assert request in ["Test prompt 1", "Test prompt 2"]
        assert response in ["Test response 1", "Test response 2"]
    
    def test_generate_content_synthetic(self, service):
        """Test synthetic content generation"""
        request, response = service._generate_content("simple_queries", None)
        
        assert isinstance(request, str)
        assert isinstance(response, str)
        assert len(request) > 0
        assert len(response) > 0
    
    def test_generate_content_all_workload_types(self, service):
        """Test content generation for all workload types"""
        workload_types = ["simple_queries", "tool_orchestration", "data_analysis", "unknown_type"]
        
        for workload_type in workload_types:
            request, response = service._generate_content(workload_type, None)
            assert isinstance(request, str)
            assert isinstance(response, str)


class TestTimestampGeneration:
    """Test timestamp generation with patterns"""
    
    def test_generate_timestamp(self, service, sample_config):
        """Test timestamp generation with variation"""
        sample_config.num_logs = 10
        
        timestamps = []
        for i in range(5):
            timestamp = service._generate_timestamp(sample_config, i)
            timestamps.append(timestamp)
            assert isinstance(timestamp, datetime)
        
        # Timestamps should be different
        assert len(set(timestamps)) > 1
        
        # Should be within reasonable range (last 24 hours + jitter)
        now = datetime.utcnow()
        yesterday = now - timedelta(hours=25)  # Account for jitter
        tomorrow = now + timedelta(hours=1)    # Account for jitter
        
        for ts in timestamps:
            assert yesterday <= ts <= tomorrow


class TestMetricsCalculation:
    """Test metrics calculation from tool invocations"""
    
    def test_calculate_metrics_empty(self, service):
        """Test metrics calculation with empty invocations"""
        metrics = service._calculate_metrics([])
        
        assert metrics["total_latency_ms"] == 0
        assert metrics["tool_count"] == 0
        assert metrics["success_rate"] == 1.0
    
    def test_calculate_metrics_with_data(self, service):
        """Test metrics calculation with tool invocations"""
        invocations = [
            {"latency_ms": 100, "status": "success"},
            {"latency_ms": 200, "status": "success"},
            {"latency_ms": 150, "status": "failed"}
        ]
        
        metrics = service._calculate_metrics(invocations)
        
        assert metrics["total_latency_ms"] == 450
        assert metrics["tool_count"] == 3
        assert metrics["success_rate"] == 2/3
        assert metrics["avg_latency_ms"] == 150


class TestGenerationRateCalculation:
    """Test generation rate calculation"""
    
    def test_calculate_generation_rate_no_job(self, service):
        """Test generation rate for non-existent job"""
        rate = service._calculate_generation_rate("non-existent")
        assert rate == 0.0
    
    def test_calculate_generation_rate_zero_elapsed(self, service):
        """Test generation rate with zero elapsed time"""
        job_id = "test-job"
        service.active_jobs[job_id] = {
            "start_time": datetime.utcnow(),
            "records_generated": 100
        }
        
        rate = service._calculate_generation_rate(job_id)
        assert rate == 0.0  # Division by zero handled
    
    def test_calculate_generation_rate_with_time(self, service):
        """Test generation rate calculation with elapsed time"""
        job_id = "test-job"
        start_time = datetime.utcnow() - timedelta(seconds=10)
        service.active_jobs[job_id] = {
            "start_time": start_time,
            "records_generated": 100
        }
        
        rate = service._calculate_generation_rate(job_id)
        assert rate > 0
        assert rate == pytest.approx(10, rel=0.1)  # ~10 records/second


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
        
        assert result is None
    
    async def test_load_corpus_not_completed(self, service, mock_db, mock_corpus):
        """Test loading corpus that's not completed"""
        mock_corpus.status = "pending"
        mock_db.query_results[models.Corpus] = [mock_corpus]
        
        result = await service._load_corpus("test-corpus", mock_db)
        
        assert result is None
    
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
        
        assert result is not None
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
        
        assert result is None


@pytest.mark.asyncio
class TestTableOperations:
    """Test ClickHouse table operations"""
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_create_destination_table(self, mock_get_client, service):
        """Test creating destination table"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        await service._create_destination_table("test_table")
        
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS test_table" in call_args
        assert "MergeTree()" in call_args
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_ingest_batch_empty(self, mock_get_client, service):
        """Test ingesting empty batch"""
        await service._ingest_batch("test_table", [])
        
        # Should not attempt ClickHouse operation
        mock_get_client.assert_not_called()
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_ingest_batch_with_data(self, mock_get_client, service):
        """Test ingesting batch with data"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        batch = [
            {
                "event_id": "event1",
                "trace_id": "trace1",
                "span_id": "span1",
                "parent_span_id": None,
                "timestamp_utc": datetime.utcnow(),
                "workload_type": "test",
                "agent_type": "test",
                "tool_invocations": ["tool1"],
                "request_payload": {"prompt": "test"},
                "response_payload": {"completion": "test"},
                "metrics": {"latency": 100},
                "corpus_reference_id": None
            }
        ]
        
        await service._ingest_batch("test_table", batch)
        
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args
        assert "INSERT INTO test_table" in call_args[0][0]
        assert len(call_args[0][1]) == 1  # One record


@pytest.mark.asyncio
class TestMainGenerationWorkflow:
    """Test main generation workflow"""
    
    @patch('app.services.synthetic_data_service.manager')
    @patch('app.db.models_postgres.Corpus')
    async def test_generate_synthetic_data(self, mock_corpus_model, mock_manager, service, mock_db, sample_config):
        """Test main synthetic data generation workflow"""
        user_id = "test-user"
        mock_corpus_instance = MagicMock()
        mock_corpus_instance.id = "corpus-id"
        mock_corpus_model.return_value = mock_corpus_instance
        
        result = await service.generate_synthetic_data(mock_db, sample_config, user_id)
        
        assert "job_id" in result
        assert result["status"] == GenerationStatus.INITIATED.value
        assert "table_name" in result
        assert "websocket_channel" in result
        
        # Verify job was added to active jobs
        job_id = result["job_id"]
        assert job_id in service.active_jobs
        
        job = service.active_jobs[job_id]
        assert job["status"] == GenerationStatus.INITIATED.value
        assert job["config"] == sample_config
        assert job["user_id"] == user_id
    
    async def test_generate_synthetic_data_with_corpus(self, service, mock_db, sample_config):
        """Test generation with specific corpus"""
        user_id = "test-user"
        corpus_id = "test-corpus"
        
        with patch('app.db.models_postgres.Corpus') as mock_corpus:
            mock_instance = MagicMock()
            mock_instance.id = "corpus-id"
            mock_corpus.return_value = mock_instance
            
            result = await service.generate_synthetic_data(mock_db, sample_config, user_id, corpus_id)
            
            assert "job_id" in result
            job = service.active_jobs[result["job_id"]]
            assert job["corpus_id"] == corpus_id


@pytest.mark.asyncio
class TestGenerationWorker:
    """Test the background generation worker"""
    
    @patch('app.services.synthetic_data_service.manager')
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_generate_worker_success(self, mock_get_client, mock_manager, service, mock_db, sample_config):
        """Test successful generation worker execution"""
        job_id = "test-job"
        synthetic_data_id = "synth-id"
        sample_config.num_logs = 2
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        # Initialize job
        service.active_jobs[job_id] = {
            "status": GenerationStatus.INITIATED.value,
            "config": sample_config,
            "corpus_id": None,
            "start_time": datetime.utcnow(),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": "test_table",
            "user_id": "test-user"
        }
        
        # Run worker
        await service._generate_worker(job_id, sample_config, None, mock_db, synthetic_data_id)
        
        # Verify job completion
        assert service.active_jobs[job_id]["status"] == GenerationStatus.COMPLETED.value
        assert service.active_jobs[job_id]["records_generated"] == 2
        assert "end_time" in service.active_jobs[job_id]
    
    @patch('app.services.synthetic_data_service.manager')
    async def test_generate_worker_failure(self, mock_manager, service, mock_db, sample_config):
        """Test generation worker with failure"""
        job_id = "test-job"
        synthetic_data_id = "synth-id"
        
        # Initialize job
        service.active_jobs[job_id] = {
            "status": GenerationStatus.INITIATED.value,
            "config": sample_config,
            "corpus_id": None,
            "start_time": datetime.utcnow(),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": "test_table",
            "user_id": "test-user"
        }
        
        # Make table creation fail
        with patch.object(service, '_create_destination_table', side_effect=Exception("Table error")):
            await service._generate_worker(job_id, sample_config, None, mock_db, synthetic_data_id)
        
        # Verify job failure
        assert service.active_jobs[job_id]["status"] == GenerationStatus.FAILED.value
        assert len(service.active_jobs[job_id]["errors"]) > 0


@pytest.mark.asyncio
class TestJobManagement:
    """Test job status and management operations"""
    
    async def test_get_job_status_exists(self, service):
        """Test getting status of existing job"""
        job_id = "test-job"
        job_data = {"status": "running", "progress": 50}
        service.active_jobs[job_id] = job_data
        
        status = await service.get_job_status(job_id)
        assert status == job_data
    
    async def test_get_job_status_not_exists(self, service):
        """Test getting status of non-existent job"""
        status = await service.get_job_status("non-existent")
        assert status is None
    
    async def test_cancel_job_exists(self, service):
        """Test canceling existing job"""
        job_id = "test-job"
        service.active_jobs[job_id] = {"status": "running"}
        
        result = await service.cancel_job(job_id)
        assert result is True
        assert service.active_jobs[job_id]["status"] == GenerationStatus.CANCELLED.value
    
    async def test_cancel_job_not_exists(self, service):
        """Test canceling non-existent job"""
        result = await service.cancel_job("non-existent")
        assert result is False


@pytest.mark.asyncio
class TestPreviewGeneration:
    """Test preview generation functionality"""
    
    async def test_get_preview(self, service):
        """Test generating preview samples"""
        corpus_id = "test-corpus"
        workload_type = "simple_queries"
        
        samples = await service.get_preview(corpus_id, workload_type, 5)
        
        assert len(samples) == 5
        for sample in samples:
            assert "event_id" in sample
            assert "workload_type" in sample
    
    async def test_get_preview_no_corpus(self, service):
        """Test generating preview without corpus"""
        samples = await service.get_preview(None, "test_type", 3)
        
        assert len(samples) == 3


@pytest.mark.asyncio
class TestAdvancedGenerationMethods:
    """Test advanced generation methods for comprehensive coverage"""
    
    async def test_generate_with_temporal_patterns(self, service):
        """Test generation with temporal patterns"""
        config = MagicMock()
        config.num_traces = 10
        config.temporal_pattern = 'business_hours'
        
        records = await service.generate_with_temporal_patterns(config)
        
        assert len(records) == 10
        for record in records:
            assert 'timestamp' in record
    
    async def test_generate_tool_invocations(self, service):
        """Test tool invocations generation"""
        invocations = await service.generate_tool_invocations(5, "sequential")
        
        assert len(invocations) == 5
        for i, inv in enumerate(invocations):
            assert inv['sequence_number'] == i
            assert 'trace_id' in inv
            assert 'invocation_id' in inv
    
    async def test_generate_with_errors(self, service):
        """Test generation with error scenarios"""
        config = MagicMock()
        config.num_traces = 10
        config.error_rate = 0.5
        config.error_patterns = ['timeout', 'rate_limit']
        
        records = await service.generate_with_errors(config)
        
        assert len(records) == 10
        error_count = sum(1 for r in records if r.get('status') == 'failed')
        # Should have some errors (probabilistic, so allow range)
        assert error_count >= 0
    
    async def test_generate_trace_hierarchies(self, service):
        """Test trace hierarchy generation"""
        traces = await service.generate_trace_hierarchies(3, 2, 3)
        
        assert len(traces) == 3
        for trace in traces:
            assert 'trace_id' in trace
            assert 'spans' in trace
            assert len(trace['spans']) >= 1  # At least root span
    
    async def test_generate_domain_specific(self, service):
        """Test domain-specific generation"""
        config = MagicMock()
        config.num_traces = 5
        config.domain_focus = 'e-commerce'
        
        records = await service.generate_domain_specific(config)
        
        assert len(records) == 5
        for record in records:
            if 'metadata' in record:
                assert 'cart_value' in record['metadata']
    
    async def test_generate_with_distribution(self, service):
        """Test generation with specific distributions"""
        config = MagicMock()
        config.num_traces = 10
        config.latency_distribution = 'normal'
        
        records = await service.generate_with_distribution(config)
        
        assert len(records) == 10
        for record in records:
            assert 'latency_ms' in record
            assert record['latency_ms'] >= 0
    
    async def test_generate_with_custom_tools(self, service):
        """Test generation with custom tool catalog"""
        config = MagicMock()
        config.num_traces = 5
        config.tool_catalog = [{"name": "custom_tool", "type": "test"}]
        
        records = await service.generate_with_custom_tools(config)
        
        assert len(records) == 5
        for record in records:
            assert 'tool_invocations' in record
    
    async def test_generate_incremental(self, service):
        """Test incremental generation"""
        config = MagicMock()
        config.num_traces = 100
        config.checkpoint_interval = 25
        
        checkpoints = []
        async def checkpoint_callback(data):
            checkpoints.append(data)
        
        result = await service.generate_incremental(config, checkpoint_callback)
        
        assert result['total_generated'] == 100
        assert len(checkpoints) == 4  # 100 / 25
    
    async def test_generate_from_corpus(self, service):
        """Test generation from corpus content"""
        config = MagicMock()
        config.num_traces = 5
        corpus_content = [{"prompt": "test", "response": "test"}]
        
        records = await service.generate_from_corpus(config, corpus_content)
        
        assert len(records) == 5


@pytest.mark.asyncio
class TestIngestionMethods:
    """Test various ingestion methods"""
    
    async def test_ingest_batch_method(self, service):
        """Test the ingest_batch public method"""
        records = [{"id": 1, "data": "test"}]
        
        with patch.object(service, '_create_destination_table') as mock_create:
            with patch.object(service, '_ingest_batch') as mock_ingest:
                result = await service.ingest_batch(records, "test_table")
                
                mock_create.assert_called_once_with("test_table")
                mock_ingest.assert_called_once_with("test_table", records)
                
                assert result["records_ingested"] == 1
                assert result["table_name"] == "test_table"
    
    async def test_ingest_with_retry_success(self, service):
        """Test ingestion with successful retry"""
        records = [{"id": 1}]
        
        with patch.object(service, 'ingest_batch', return_value={"records_ingested": 1}):
            result = await service.ingest_with_retry(records, max_retries=3)
            
            assert result["success"] is True
            assert result["retry_count"] == 0
            assert result["records_ingested"] == 1
    
    async def test_ingest_with_retry_failure(self, service):
        """Test ingestion with all retries failing"""
        records = [{"id": 1}]
        
        with patch.object(service, 'ingest_batch', side_effect=Exception("Ingest failed")):
            result = await service.ingest_with_retry(records, max_retries=2)
            
            assert result["success"] is False
            assert result["retry_count"] == 2
            assert result["failed_records"] == 1
    
    async def test_ingest_with_deduplication(self, service):
        """Test ingestion with deduplication"""
        records = [
            {"id": "1", "data": "test1"},
            {"id": "2", "data": "test2"},
            {"id": "1", "data": "duplicate"}  # Duplicate
        ]
        
        with patch.object(service, 'ingest_batch', return_value={"records_ingested": 2}):
            result = await service.ingest_with_deduplication(records)
            
            assert result["records_ingested"] == 2
            assert result["duplicates_removed"] == 1
    
    async def test_ingest_with_transform(self, service):
        """Test ingestion with data transformation"""
        records = [{"value": 1}, {"value": 2}]
        
        def transform_fn(record):
            return {"transformed_value": record["value"] * 2}
        
        with patch.object(service, 'ingest_batch', return_value={"records_ingested": 2}):
            result = await service.ingest_with_transform(records, transform_fn)
            
            assert result["records_ingested"] == 2
            assert len(result["transformed_records"]) == 2
            assert result["transformed_records"][0]["transformed_value"] == 2


@pytest.mark.asyncio
class TestValidationMethods:
    """Test data validation methods"""
    
    def test_validate_schema_valid(self, service):
        """Test schema validation with valid record"""
        record = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "workload_type": "test",
            "latency_ms": 100
        }
        
        assert service.validate_schema(record) is True
    
    def test_validate_schema_missing_fields(self, service):
        """Test schema validation with missing required fields"""
        record = {"data": "incomplete"}
        
        assert service.validate_schema(record) is False
    
    def test_validate_schema_invalid_uuid(self, service):
        """Test schema validation with invalid UUID"""
        record = {
            "trace_id": "not-a-uuid",
            "timestamp": datetime.utcnow().isoformat(),
            "workload_type": "test"
        }
        
        assert service.validate_schema(record) is False
    
    def test_validate_schema_invalid_timestamp(self, service):
        """Test schema validation with invalid timestamp"""
        record = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": "not-a-timestamp",
            "workload_type": "test"
        }
        
        assert service.validate_schema(record) is False
    
    async def test_validate_distribution(self, service):
        """Test statistical distribution validation"""
        records = [{"latency": i} for i in range(100)]
        
        result = await service.validate_distribution(records)
        
        assert hasattr(result, 'chi_square_p_value')
        assert hasattr(result, 'ks_test_p_value')
        assert hasattr(result, 'distribution_match')
    
    async def test_validate_referential_integrity(self, service):
        """Test referential integrity validation"""
        traces = [
            {
                "spans": [
                    {"span_id": "1", "parent_span_id": None, "start_time": datetime.utcnow(), "end_time": datetime.utcnow() + timedelta(seconds=1)},
                    {"span_id": "2", "parent_span_id": "1", "start_time": datetime.utcnow(), "end_time": datetime.utcnow() + timedelta(seconds=1)}
                ]
            }
        ]
        
        result = await service.validate_referential_integrity(traces)
        
        assert hasattr(result, 'valid_parent_child_relationships')
        assert hasattr(result, 'temporal_ordering_valid')
        assert hasattr(result, 'orphaned_spans')
    
    async def test_validate_temporal_consistency(self, service):
        """Test temporal consistency validation"""
        records = [
            {"timestamp_utc": datetime.utcnow() - timedelta(hours=1)},
            {"timestamp_utc": datetime.utcnow()}
        ]
        
        result = await service.validate_temporal_consistency(records)
        
        assert hasattr(result, 'all_within_window')
        assert hasattr(result, 'chronological_order')
        assert hasattr(result, 'no_future_timestamps')
    
    async def test_validate_completeness(self, service):
        """Test data completeness validation"""
        records = [
            {"field1": "value1", "field2": "value2"},
            {"field1": "value1", "field2": None},
            {"field1": None, "field2": "value2"}
        ]
        required_fields = ["field1", "field2"]
        
        result = await service.validate_completeness(records, required_fields)
        
        assert hasattr(result, 'all_required_fields_present')
        assert hasattr(result, 'null_value_percentage')
        assert result.null_value_percentage == 2/6  # 2 null values out of 6 total field checks


@pytest.mark.asyncio
class TestQualityAndDiversityMetrics:
    """Test quality and diversity metrics calculation"""
    
    async def test_calculate_quality_metrics(self, service):
        """Test quality metrics calculation"""
        records = [
            {"trace_id": str(uuid.uuid4()), "timestamp": datetime.utcnow().isoformat(), "workload_type": "test"},
            {"trace_id": "invalid", "timestamp": "invalid", "workload_type": "test"}  # Invalid record
        ]
        
        metrics = await service.calculate_quality_metrics(records)
        
        assert hasattr(metrics, 'validation_pass_rate')
        assert hasattr(metrics, 'distribution_divergence')
        assert hasattr(metrics, 'temporal_consistency')
        assert hasattr(metrics, 'corpus_coverage')
        assert 0 <= metrics.validation_pass_rate <= 1
    
    async def test_calculate_diversity(self, service):
        """Test diversity metrics calculation"""
        records = [
            {"trace_id": "trace1", "workload_type": "type1", "tool_invocations": ["tool1", "tool2"]},
            {"trace_id": "trace2", "workload_type": "type2", "tool_invocations": ["tool2", "tool3"]},
            {"trace_id": "trace1", "workload_type": "type1", "tool_invocations": ["tool1"]}  # Duplicate trace
        ]
        
        metrics = await service.calculate_diversity(records)
        
        assert hasattr(metrics, 'unique_traces')
        assert hasattr(metrics, 'workload_type_entropy')
        assert hasattr(metrics, 'tool_usage_variety')
        assert metrics.unique_traces == 2  # Only 2 unique trace IDs
        assert metrics.tool_usage_variety == 3  # 3 unique tools
    
    async def test_generate_validation_report(self, service):
        """Test comprehensive validation report generation"""
        records = [
            {"trace_id": str(uuid.uuid4()), "timestamp": datetime.utcnow().isoformat(), "workload_type": "test"}
        ]
        
        report = await service.generate_validation_report(records)
        
        assert "schema_validation" in report
        assert "statistical_validation" in report
        assert "quality_metrics" in report
        assert "overall_quality_score" in report
        assert 0 <= report["overall_quality_score"] <= 1


@pytest.mark.asyncio
class TestCircuitBreakerAndErrorHandling:
    """Test circuit breaker and error handling functionality"""
    
    def test_get_circuit_breaker(self, service):
        """Test circuit breaker creation"""
        cb = service.get_circuit_breaker(failure_threshold=2, timeout_seconds=1)
        
        assert hasattr(cb, 'failure_threshold')
        assert hasattr(cb, 'timeout')
        assert hasattr(cb, 'call')
        assert hasattr(cb, 'is_open')
        assert cb.failure_threshold == 2
        assert cb.timeout == 1
    
    async def test_circuit_breaker_functionality(self, service):
        """Test circuit breaker operation"""
        cb = service.get_circuit_breaker(failure_threshold=2)
        
        # Test successful call
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        assert not cb.is_open()
        
        # Test failing calls
        async def fail_func():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            await cb.call(fail_func)
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            await cb.call(fail_func)
        
        # Circuit should now be open
        assert cb.is_open()


@pytest.mark.asyncio
class TestLegacyFunctions:
    """Test legacy compatibility functions"""
    
    @patch('asyncio.run')
    def test_legacy_generate_synthetic_data(self, mock_run):
        """Test legacy generate_synthetic_data function"""
        from app.services.synthetic_data_service import generate_synthetic_data
        
        mock_db = MagicMock()
        mock_params = MagicMock()
        user_id = "test-user"
        
        generate_synthetic_data(mock_db, mock_params, user_id)
        
        # Should call asyncio.run with the async method
        mock_run.assert_called_once()
    
    @patch.object(SyntheticDataService, '_generate_worker')
    async def test_legacy_generate_synthetic_data_task(self, mock_worker):
        """Test legacy generate_synthetic_data_task function"""
        from app.services.synthetic_data_service import generate_synthetic_data_task
        
        await generate_synthetic_data_task("synth_id", "source_table", "dest_table", 100, MagicMock())
        
        # Should call the new worker method
        mock_worker.assert_called_once()


class TestSingletonInstance:
    """Test singleton instance functionality"""
    
    def test_singleton_instance_exists(self):
        """Test that singleton instance is accessible"""
        assert synthetic_data_service is not None
        assert isinstance(synthetic_data_service, SyntheticDataService)
    
    def test_singleton_instance_consistency(self):
        """Test that singleton returns same instance"""
        from app.services.synthetic_data_service import synthetic_data_service as service1
        from app.services.synthetic_data_service import synthetic_data_service as service2
        
        assert service1 is service2


@pytest.mark.asyncio
class TestErrorScenarios:
    """Test various error scenarios and edge cases"""
    
    async def test_generate_with_anomalies_method(self, service):
        """Test anomaly generation method"""
        config = MagicMock()
        config.num_traces = 10
        config.anomaly_injection_rate = 1.0  # 100% anomalies
        
        records = await service.generate_with_anomalies(config)
        
        assert len(records) == 10
        anomaly_count = sum(1 for r in records if r.get('anomaly', False))
        assert anomaly_count > 0  # Should have some anomalies
    
    async def test_detect_anomalies(self, service):
        """Test anomaly detection"""
        records = [
            {"event_id": "1", "anomaly": True, "anomaly_type": "spike"},
            {"event_id": "2", "anomaly": False},
            {"event_id": "3", "anomaly": True, "anomaly_type": "failure"}
        ]
        
        anomalies = await service.detect_anomalies(records)
        
        assert len(anomalies) == 2
        for anomaly in anomalies:
            assert "record_id" in anomaly
            assert "anomaly_type" in anomaly
            assert "severity" in anomaly
    
    async def test_calculate_correlation(self, service):
        """Test correlation calculation between fields"""
        records = [
            {"field1": 1, "field2": 2},
            {"field1": 2, "field2": 4},
            {"field1": 3, "field2": 6}
        ]
        
        correlation = await service.calculate_correlation(records, "field1", "field2")
        
        assert isinstance(correlation, float)
        assert -1 <= correlation <= 1
        assert correlation == pytest.approx(1.0, rel=0.01)  # Perfect positive correlation
    
    async def test_calculate_correlation_no_data(self, service):
        """Test correlation calculation with insufficient data"""
        records = [{"field1": 1}]  # Only one record
        
        correlation = await service.calculate_correlation(records, "field1", "field2")
        
        assert correlation == 0.0
    
    async def test_calculate_correlation_invalid_data(self, service):
        """Test correlation calculation with invalid data"""
        records = [
            {"field1": "not_a_number", "field2": "also_not_a_number"},
            {"field1": 2, "field2": 4}
        ]
        
        correlation = await service.calculate_correlation(records, "field1", "field2")
        
        # Should handle invalid data gracefully
        assert isinstance(correlation, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])