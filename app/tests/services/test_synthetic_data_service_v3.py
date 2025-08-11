"""
Comprehensive Test Suite for Synthetic Data Generation Service v3
Testing all aspects of synthetic data generation, corpus integration, and ClickHouse ingestion
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, List, Any, Optional

from app.services.synthetic_data_service import (
    SyntheticDataService,
    WorkloadCategory,
    GenerationStatus
)
from app.services.corpus_service import CorpusService, CorpusStatus
from app.ws_manager import manager as ws_manager
from app import schemas

# Mock classes for testing
class GenerationConfig:
    def __init__(self, **kwargs):
        self.num_traces = kwargs.get('num_traces', 1000)
        self.num_logs = kwargs.get('num_logs', kwargs.get('num_traces', 1000))  # Support both names
        self.workload_distribution = kwargs.get('workload_distribution', {})
        self.time_window_hours = kwargs.get('time_window_hours', 24)
        self.domain_focus = kwargs.get('domain_focus', 'general')
        self.error_rate = kwargs.get('error_rate', 0.01)
        self.corpus_id = kwargs.get('corpus_id', None)
        self.batch_size = kwargs.get('batch_size', 100)
        self.__dict__.update(kwargs)

class ValidationResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class IngestionMetrics:
    def __init__(self):
        self.records_processed = 0
        self.backpressure_events = 0
        self.total_records = 0
        self.total_batches = 0
        self.avg_latency_ms = 0
        self.max_latency_ms = 0
        self.min_latency_ms = float('inf')

class ClickHouseService:
    async def query(self, query):
        return []
    async def insert(self, data):
        return True
    async def count_records(self, table):
        return 0


# ==================== Test Suite 1: Corpus Management (10 tests) ====================

# ==================== Fixtures ====================

@pytest.fixture
def corpus_service():
    return CorpusService()

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db

@pytest.fixture
def mock_clickhouse_client():
    client = AsyncMock()
    client.execute = AsyncMock(return_value=None)
    client.query = AsyncMock(return_value=[])
    return client

@pytest.fixture
def generation_service():
    return SyntheticDataService()

@pytest.fixture
def generation_config():
    return GenerationConfig(
        num_traces=1000,
        workload_distribution={
            "simple_chat": 0.3,
            "tool_use": 0.3,
            "rag_pipeline": 0.2,
            "failed_request": 0.2
        },
        time_window_hours=24,
        domain_focus="e-commerce"
    )

@pytest.fixture
def ingestion_service():
    return SyntheticDataService()

@pytest.fixture
def mock_clickhouse():
    client = AsyncMock()
    client.execute = AsyncMock()
    client.query = AsyncMock()
    return client

@pytest.fixture
def ws_service():
    return ws_manager

@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    return ws

@pytest.fixture
def validation_service():
    return SyntheticDataService()

@pytest.fixture
def perf_service():
    return SyntheticDataService()

@pytest.fixture
def recovery_service():
    return SyntheticDataService()

@pytest.fixture
def admin_service():
    return SyntheticDataService()

@pytest.fixture
def full_stack():
    """Setup full stack for integration testing"""
    services = {
        "corpus": CorpusService(),
        "generation": SyntheticDataService(),
        "clickhouse": ClickHouseService(),
        "websocket": ws_manager
    }
    return services

@pytest.fixture
def advanced_service():
    return SyntheticDataService()

class TestCorpusManagement:
    """Test corpus lifecycle management and integration"""

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_corpus_deletion_cascade(self, corpus_service, mock_db, mock_clickhouse_client):
        """Test corpus deletion with ClickHouse table cleanup"""
        corpus_id = str(uuid.uuid4())
        
        with patch('app.services.corpus_service.get_clickhouse_client', return_value=mock_clickhouse_client):
            await corpus_service.delete_corpus(mock_db, corpus_id)
        
        # Should drop ClickHouse table and delete PostgreSQL record
        mock_clickhouse_client.execute.assert_called()
        mock_db.query.assert_called()
        mock_db.delete.assert_called()

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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


# ==================== Test Suite 2: Data Generation Engine (10 tests) ====================

class TestDataGenerationEngine:
    """Test synthetic data generation core functionality"""

    @pytest.mark.asyncio
    async def test_workload_distribution_generation(self, generation_service, generation_config):
        """Test generating data with specified workload distribution"""
        records = await generation_service.generate_synthetic_data(
            generation_config,
            corpus_id="test_corpus"
        )
        
        # Check distribution matches configuration
        workload_counts = {}
        for record in records:
            workload_type = record["workload_type"]
            workload_counts[workload_type] = workload_counts.get(workload_type, 0) + 1
        
        for workload, expected_ratio in generation_config.workload_distribution.items():
            actual_ratio = workload_counts.get(workload, 0) / len(records)
            assert abs(actual_ratio - expected_ratio) < 0.05  # 5% tolerance

    @pytest.mark.asyncio
    async def test_temporal_pattern_generation(self, generation_service):
        """Test generating data with realistic temporal patterns"""
        config = GenerationConfig(
            num_traces=1000,
            time_window_hours=168,  # 1 week
            temporal_pattern="business_hours"
        )
        
        records = await generation_service.generate_with_temporal_patterns(config)
        
        # Verify business hours have higher density
        business_hours_count = sum(
            1 for r in records 
            if 9 <= r["timestamp"].hour <= 17 and r["timestamp"].weekday() < 5
        )
        
        assert business_hours_count > len(records) * 0.6  # Most traffic during business hours

    @pytest.mark.asyncio
    async def test_tool_invocation_patterns(self, generation_service):
        """Test generating realistic tool invocation patterns"""
        patterns = await generation_service.generate_tool_invocations(
            num_invocations=100,
            pattern="sequential_chain"
        )
        
        # Verify sequential pattern
        for i in range(len(patterns) - 1):
            current = patterns[i]
            next_inv = patterns[i + 1]
            # Output of current should be input to next
            assert current["trace_id"] == next_inv["trace_id"]
            assert current["end_time"] <= next_inv["start_time"]

    @pytest.mark.asyncio
    async def test_error_scenario_generation(self, generation_service):
        """Test generating error scenarios and failures"""
        config = GenerationConfig(
            num_traces=100,
            error_rate=0.15,
            error_patterns=["timeout", "rate_limit", "invalid_input"]
        )
        
        records = await generation_service.generate_with_errors(config)
        
        error_count = sum(1 for r in records if r.get("status") == "failed")
        error_rate = error_count / len(records)
        
        assert 0.10 <= error_rate <= 0.20  # Within expected range
        
        # Check error types
        error_types = [r.get("error_type") for r in records if r.get("status") == "failed"]
        assert all(et in config.error_patterns for et in error_types)

    @pytest.mark.asyncio
    async def test_trace_hierarchy_generation(self, generation_service):
        """Test generating valid trace and span hierarchies"""
        traces = await generation_service.generate_trace_hierarchies(
            num_traces=10,
            max_depth=3,
            max_branches=5
        )
        
        for trace in traces:
            # Verify parent-child relationships
            spans = trace["spans"]
            span_map = {s["span_id"]: s for s in spans}
            
            for span in spans:
                if span["parent_span_id"]:
                    parent = span_map.get(span["parent_span_id"])
                    assert parent is not None
                    # Child span must be within parent time bounds
                    assert span["start_time"] >= parent["start_time"]
                    assert span["end_time"] <= parent["end_time"]

    @pytest.mark.asyncio
    async def test_domain_specific_generation(self, generation_service):
        """Test domain-specific data generation"""
        domains = ["e-commerce", "healthcare", "finance"]
        
        for domain in domains:
            config = GenerationConfig(
                num_traces=100,
                domain_focus=domain
            )
            
            records = await generation_service.generate_domain_specific(config)
            
            # Verify domain-specific fields
            if domain == "e-commerce":
                assert all("cart_value" in r["metadata"] for r in records)
            elif domain == "healthcare":
                assert all("patient_id" in r["metadata"] for r in records)
            elif domain == "finance":
                assert all("transaction_amount" in r["metadata"] for r in records)

    @pytest.mark.asyncio
    async def test_statistical_distribution_generation(self, generation_service):
        """Test generating data with specific statistical distributions"""
        distributions = ["normal", "exponential", "uniform", "bimodal"]
        
        for dist in distributions:
            config = GenerationConfig(
                num_traces=1000,
                latency_distribution=dist
            )
            
            records = await generation_service.generate_with_distribution(config)
            latencies = [r["latency_ms"] for r in records]
            
            # Verify distribution characteristics
            if dist == "normal":
                # Should follow bell curve
                mean = sum(latencies) / len(latencies)
                within_std = sum(1 for l in latencies if abs(l - mean) < 100)
                assert within_std > len(latencies) * 0.68  # ~68% within 1 std

    @pytest.mark.asyncio
    async def test_custom_tool_catalog_generation(self, generation_service):
        """Test generation with custom tool catalog"""
        custom_tools = [
            {"name": "custom_api", "latency_ms": [100, 500], "failure_rate": 0.02},
            {"name": "ml_model", "latency_ms": [1000, 5000], "failure_rate": 0.05},
            {"name": "database_query", "latency_ms": [20, 200], "failure_rate": 0.01}
        ]
        
        config = GenerationConfig(
            num_traces=100,
            tool_catalog=custom_tools
        )
        
        records = await generation_service.generate_with_custom_tools(config)
        
        # Verify custom tools are used
        tool_names = set()
        for record in records:
            if "tool_invocations" in record:
                tool_names.update(record["tool_invocations"])
        
        assert all(tool["name"] in tool_names for tool in custom_tools)

    @pytest.mark.asyncio
    async def test_incremental_generation(self, generation_service):
        """Test incremental data generation with checkpoints"""
        config = GenerationConfig(
            num_traces=10000,
            checkpoint_interval=1000
        )
        
        checkpoints = []
        
        async def checkpoint_callback(checkpoint_data):
            checkpoints.append(checkpoint_data)
        
        await generation_service.generate_incremental(
            config,
            checkpoint_callback=checkpoint_callback
        )
        
        assert len(checkpoints) == 10  # 10000 / 1000
        assert all(cp["records_generated"] % 1000 == 0 for cp in checkpoints)

    @pytest.mark.asyncio
    async def test_generation_with_corpus_sampling(self, generation_service):
        """Test generation using corpus content sampling"""
        corpus_content = [
            {"prompt": f"Prompt {i}", "response": f"Response {i}"}
            for i in range(100)
        ]
        
        config = GenerationConfig(
            num_traces=1000,
            corpus_sampling_strategy="weighted_random"
        )
        
        records = await generation_service.generate_from_corpus(
            config,
            corpus_content
        )
        
        # Verify corpus content is used
        prompts_used = set(r["prompt"] for r in records)
        assert len(prompts_used) > 50  # Should use variety of corpus content


# ==================== Test Suite 3: Real-time Ingestion (10 tests) ====================

class TestRealTimeIngestion:
    """Test real-time data ingestion to ClickHouse"""

    @pytest.mark.asyncio
    async def test_batch_ingestion_to_clickhouse(self, ingestion_service, mock_clickhouse):
        """Test batch ingestion of generated data to ClickHouse"""
        records = [{"id": i, "data": f"record_{i}"} for i in range(1000)]
        
        with patch('app.services.synthetic_data_service.get_clickhouse_client', return_value=mock_clickhouse):
            result = await ingestion_service.ingest_batch(
                records,
                table_name="test_table",
                batch_size=100
            )
        
        assert result["records_ingested"] == 1000
        assert result["batches_processed"] == 10
        assert mock_clickhouse.execute.call_count == 10

    @pytest.mark.asyncio
    async def test_streaming_ingestion_with_backpressure(self, ingestion_service):
        """Test streaming ingestion with backpressure handling"""
        async def generate_stream():
            for i in range(10000):
                yield {"id": i, "timestamp": datetime.utcnow()}
                if i % 100 == 0:
                    await asyncio.sleep(0.01)  # Simulate processing time
        
        ingestion_metrics = await ingestion_service.ingest_stream(
            generate_stream(),
            max_buffer_size=500,
            flush_interval_ms=100
        )
        
        assert ingestion_metrics.records_processed == 10000
        assert ingestion_metrics.backpressure_events > 0

    @pytest.mark.asyncio
    async def test_ingestion_error_recovery(self, ingestion_service, mock_clickhouse):
        """Test error recovery during ingestion"""
        # Simulate intermittent failures
        call_count = 0
        
        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
                raise Exception("Connection error")
            return None
        
        mock_clickhouse.execute = mock_execute
        
        records = [{"id": i} for i in range(100)]
        
        with patch('app.services.synthetic_data_service.get_clickhouse_client', return_value=mock_clickhouse):
            result = await ingestion_service.ingest_with_retry(
                records,
                max_retries=3,
                retry_delay_ms=10
            )
        
        assert result["records_ingested"] > 0
        assert result["failed_records"] < len(records)
        assert result["retries_performed"] > 0

    @pytest.mark.asyncio
    async def test_ingestion_deduplication(self, ingestion_service):
        """Test deduplication during ingestion"""
        records_with_duplicates = [
            {"id": 1, "data": "a"},
            {"id": 2, "data": "b"},
            {"id": 1, "data": "a"},  # Duplicate
            {"id": 3, "data": "c"},
            {"id": 2, "data": "b"},  # Duplicate
        ]
        
        result = await ingestion_service.ingest_with_deduplication(
            records_with_duplicates,
            dedup_key="id"
        )
        
        assert result["records_ingested"] == 3
        assert result["duplicates_removed"] == 2

    @pytest.mark.asyncio
    async def test_table_creation_on_demand(self, ingestion_service, mock_clickhouse):
        """Test automatic table creation before ingestion"""
        table_name = f"synthetic_data_{uuid.uuid4().hex}"
        
        mock_clickhouse.query.return_value = []  # Table doesn't exist
        
        with patch('app.services.synthetic_data_service.get_clickhouse_client', return_value=mock_clickhouse):
            await ingestion_service.ensure_table_exists(table_name)
        
        # Should create table
        create_table_calls = [
            call for call in mock_clickhouse.execute.call_args_list
            if "CREATE TABLE" in str(call)
        ]
        assert len(create_table_calls) > 0

    @pytest.mark.asyncio
    async def test_ingestion_metrics_tracking(self, ingestion_service):
        """Test tracking ingestion metrics and performance"""
        start_time = datetime.utcnow()
        
        metrics = IngestionMetrics()
        
        for i in range(100):
            await ingestion_service.track_ingestion(
                metrics,
                batch_size=10,
                latency_ms=50 + i
            )
        
        assert metrics.total_records == 1000
        assert metrics.total_batches == 100
        assert metrics.avg_latency_ms > 0
        assert metrics.max_latency_ms >= 149
        assert metrics.min_latency_ms <= 50

    @pytest.mark.asyncio
    async def test_parallel_batch_ingestion(self, ingestion_service):
        """Test parallel ingestion of multiple batches"""
        batches = [
            [{"id": i + j * 100} for i in range(100)]
            for j in range(10)
        ]
        
        tasks = [
            ingestion_service.ingest_batch(batch, f"table_{i}")
            for i, batch in enumerate(batches)
        ]
        
        results = await asyncio.gather(*tasks)
        
        total_ingested = sum(r["records_ingested"] for r in results)
        assert total_ingested == 1000

    @pytest.mark.asyncio
    async def test_ingestion_with_transformation(self, ingestion_service):
        """Test data transformation during ingestion"""
        def transform_record(record):
            record["timestamp"] = datetime.utcnow().isoformat()
            record["processed"] = True
            return record
        
        records = [{"id": i, "value": i * 10} for i in range(100)]
        
        result = await ingestion_service.ingest_with_transform(
            records,
            transform_fn=transform_record
        )
        
        assert all("timestamp" in r for r in result["transformed_records"])
        assert all(r["processed"] == True for r in result["transformed_records"])

    @pytest.mark.asyncio
    async def test_ingestion_circuit_breaker(self, ingestion_service):
        """Test circuit breaker for ingestion failures"""
        circuit_breaker = ingestion_service.get_circuit_breaker(
            failure_threshold=3,
            timeout_seconds=1
        )
        
        # Simulate failures
        for _ in range(3):
            try:
                await circuit_breaker.call(lambda: Exception("Failed"))
            except Exception:
                pass  # Expected to fail for testing circuit breaker
        
        # Circuit should be open
        assert circuit_breaker.is_open()
        
        # Should reject calls
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await circuit_breaker.call(lambda: "test")

    @pytest.mark.asyncio
    async def test_ingestion_progress_tracking(self, ingestion_service):
        """Test real-time progress tracking during ingestion"""
        progress_updates = []
        
        async def progress_callback(progress):
            progress_updates.append(progress)
        
        records = [{"id": i} for i in range(1000)]
        
        await ingestion_service.ingest_with_progress(
            records,
            batch_size=100,
            progress_callback=progress_callback
        )
        
        assert len(progress_updates) == 10
        assert progress_updates[-1]["percentage"] == 100
        assert all(p["percentage"] <= 100 for p in progress_updates)


# ==================== Test Suite 4: WebSocket Updates (10 tests) ====================

class TestWebSocketUpdates:
    """Test WebSocket real-time updates during generation"""

    @pytest.mark.asyncio
    async def test_websocket_connection_management(self, ws_service, mock_websocket):
        """Test WebSocket connection lifecycle"""
        job_id = str(uuid.uuid4())
        
        # Connect
        await ws_service.connect(mock_websocket, job_id)
        assert job_id in ws_service.active_connections
        
        # Disconnect
        await ws_service.disconnect(job_id)
        assert job_id not in ws_service.active_connections

    @pytest.mark.asyncio
    async def test_generation_progress_broadcast(self, ws_service, mock_websocket):
        """Test broadcasting generation progress to connected clients"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        progress_update = {
            "type": "generation_progress",
            "job_id": job_id,
            "progress_percentage": 50,
            "records_generated": 500,
            "records_ingested": 450
        }
        
        await ws_service.broadcast_to_job(job_id, progress_update)
        
        mock_websocket.send_json.assert_called_with(progress_update)

    @pytest.mark.asyncio
    async def test_batch_completion_notifications(self, ws_service):
        """Test notifications for batch completion"""
        job_id = str(uuid.uuid4())
        
        notifications = []
        
        async def mock_send(data):
            notifications.append(data)
        
        mock_ws = MagicMock()
        mock_ws.send_json = mock_send
        
        await ws_service.connect(mock_ws, job_id)
        
        for batch_num in range(1, 6):
            await ws_service.notify_batch_complete(
                job_id,
                batch_num,
                batch_size=100
            )
        
        assert len(notifications) == 5
        assert all(n["type"] == "batch_complete" for n in notifications)

    @pytest.mark.asyncio
    async def test_error_notification_handling(self, ws_service, mock_websocket):
        """Test error notification through WebSocket"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        error_data = {
            "type": "generation_error",
            "job_id": job_id,
            "error_type": "ClickHouseConnectionError",
            "error_message": "Failed to connect to ClickHouse",
            "recoverable": True,
            "retry_after_seconds": 30
        }
        
        await ws_service.notify_error(job_id, error_data)
        
        mock_websocket.send_json.assert_called_with(error_data)

    @pytest.mark.asyncio
    async def test_websocket_reconnection_handling(self, ws_service):
        """Test WebSocket reconnection and state recovery"""
        job_id = str(uuid.uuid4())
        
        # Initial connection
        ws1 = AsyncMock()
        await ws_service.connect(ws1, job_id)
        
        # Store some state
        ws_service.set_job_state(job_id, {"progress": 50})
        
        # Disconnect
        await ws_service.disconnect(job_id)
        
        # Reconnect with new socket
        ws2 = AsyncMock()
        await ws_service.connect(ws2, job_id)
        
        # Should recover state
        state = ws_service.get_job_state(job_id)
        assert state["progress"] == 50

    @pytest.mark.asyncio
    async def test_multiple_client_subscriptions(self, ws_service):
        """Test multiple clients subscribing to same job"""
        job_id = str(uuid.uuid4())
        
        clients = [AsyncMock() for _ in range(5)]
        
        for client in clients:
            await ws_service.connect(client, job_id)
        
        update = {"type": "progress", "percentage": 75}
        await ws_service.broadcast_to_job(job_id, update)
        
        # All clients should receive update
        for client in clients:
            client.send_json.assert_called_with(update)

    @pytest.mark.asyncio
    async def test_websocket_message_queuing(self, ws_service):
        """Test message queuing for slow clients"""
        job_id = str(uuid.uuid4())
        
        slow_client = AsyncMock()
        slow_client.send_json = AsyncMock(side_effect=lambda x: asyncio.sleep(0.1))
        
        await ws_service.connect(slow_client, job_id)
        
        # Send multiple updates rapidly
        for i in range(10):
            await ws_service.broadcast_to_job(
                job_id,
                {"type": "progress", "percentage": i * 10}
            )
        
        # Should queue messages
        assert ws_service.get_queue_size(job_id) > 0

    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self, ws_service, mock_websocket):
        """Test WebSocket heartbeat/keepalive mechanism"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        # Start heartbeat
        await ws_service.start_heartbeat(job_id, interval_seconds=1)
        
        await asyncio.sleep(2.5)
        
        # Should have sent at least 2 heartbeats
        heartbeat_calls = [
            call for call in mock_websocket.send_json.call_args_list
            if call[0][0].get("type") == "heartbeat"
        ]
        assert len(heartbeat_calls) >= 2

    @pytest.mark.asyncio
    async def test_generation_completion_notification(self, ws_service, mock_websocket):
        """Test generation completion notification"""
        job_id = str(uuid.uuid4())
        
        await ws_service.connect(mock_websocket, job_id)
        
        completion_data = {
            "type": "generation_complete",
            "job_id": job_id,
            "total_records": 10000,
            "duration_seconds": 45.3,
            "destination_table": "synthetic_data_20240110",
            "quality_metrics": {
                "distribution_accuracy": 0.95,
                "temporal_consistency": 0.98
            }
        }
        
        await ws_service.notify_completion(job_id, completion_data)
        
        mock_websocket.send_json.assert_called_with(completion_data)

    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(self, ws_service):
        """Test WebSocket message rate limiting"""
        job_id = str(uuid.uuid4())
        
        mock_ws = AsyncMock()
        await ws_service.connect(mock_ws, job_id)
        
        # Configure rate limit
        ws_service.set_rate_limit(job_id, max_messages_per_second=10)
        
        # Try to send 100 messages rapidly
        start_time = asyncio.get_event_loop().time()
        for i in range(100):
            await ws_service.send_with_rate_limit(
                job_id,
                {"type": "progress", "value": i}
            )
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 9 seconds (100 messages / 10 per second)
        assert (end_time - start_time) >= 9


# ==================== Test Suite 5: Data Quality Validation (10 tests) ====================

class TestDataQualityValidation:
    """Test data quality and validation mechanisms"""

    @pytest.mark.asyncio
    async def test_schema_validation(self, validation_service):
        """Test schema validation of generated records"""
        valid_record = {
            "trace_id": str(uuid.uuid4()),
            "span_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "workload_type": "simple_chat",
            "latency_ms": 150,
            "status": "success"
        }
        
        invalid_record = {
            "trace_id": "invalid-uuid",
            "timestamp": "not-a-timestamp",
            "latency_ms": "not-a-number"
        }
        
        assert validation_service.validate_schema(valid_record) == True
        assert validation_service.validate_schema(invalid_record) == False

    @pytest.mark.asyncio
    async def test_statistical_distribution_validation(self, validation_service):
        """Test validation of statistical distributions"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        validation_result = await validation_service.validate_distribution(
            records,
            expected_distribution="normal",
            tolerance=0.05
        )
        
        assert validation_result.chi_square_p_value > 0.05
        assert validation_result.ks_test_p_value > 0.05
        assert validation_result.distribution_match == True

    @pytest.mark.asyncio
    async def test_referential_integrity_validation(self, validation_service):
        """Test referential integrity in trace hierarchies"""
        traces = await validation_service.generate_trace_hierarchies(num_traces=10)
        
        validation_result = await validation_service.validate_referential_integrity(traces)
        
        assert validation_result.valid_parent_child_relationships == True
        assert validation_result.temporal_ordering_valid == True
        assert validation_result.orphaned_spans == 0

    @pytest.mark.asyncio
    async def test_temporal_consistency_validation(self, validation_service):
        """Test temporal consistency of generated data"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(
                num_traces=1000,
                time_window_hours=24
            )
        )
        
        validation_result = await validation_service.validate_temporal_consistency(records)
        
        assert validation_result.all_within_window == True
        assert validation_result.chronological_order == True
        assert validation_result.no_future_timestamps == True

    @pytest.mark.asyncio
    async def test_data_completeness_validation(self, validation_service):
        """Test data completeness and required fields"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=100)
        )
        
        required_fields = ["trace_id", "span_id", "timestamp", "workload_type"]
        
        validation_result = await validation_service.validate_completeness(
            records,
            required_fields=required_fields
        )
        
        assert validation_result.all_required_fields_present == True
        assert validation_result.null_value_percentage < 0.01

    @pytest.mark.asyncio
    async def test_anomaly_detection_in_generated_data(self, validation_service):
        """Test anomaly detection in generated data"""
        config = GenerationConfig(
            num_traces=1000,
            anomaly_injection_rate=0.05
        )
        
        records = await validation_service.generate_with_anomalies(config)
        
        detected_anomalies = await validation_service.detect_anomalies(records)
        
        # Should detect approximately 5% anomalies
        anomaly_rate = len(detected_anomalies) / len(records)
        assert 0.04 <= anomaly_rate <= 0.06

    @pytest.mark.asyncio
    async def test_correlation_preservation(self, validation_service):
        """Test preservation of correlations in generated data"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        # Test correlation between complexity and latency
        correlation = await validation_service.calculate_correlation(
            records,
            field1="tool_count",
            field2="latency_ms"
        )
        
        assert correlation > 0.5  # Positive correlation expected

    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self, validation_service):
        """Test calculation of quality metrics"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        metrics = await validation_service.calculate_quality_metrics(records)
        
        assert metrics.validation_pass_rate > 0.95
        assert metrics.distribution_divergence < 0.1
        assert metrics.temporal_consistency > 0.98
        assert metrics.corpus_coverage > 0.5

    @pytest.mark.asyncio
    async def test_data_diversity_validation(self, validation_service):
        """Test diversity of generated data"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        diversity_metrics = await validation_service.calculate_diversity(records)
        
        assert diversity_metrics.unique_traces == 1000
        assert diversity_metrics.workload_type_entropy > 1.0
        assert diversity_metrics.tool_usage_variety > 10

    @pytest.mark.asyncio
    async def test_validation_report_generation(self, validation_service):
        """Test comprehensive validation report generation"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        report = await validation_service.generate_validation_report(records)
        
        assert "schema_validation" in report
        assert "statistical_validation" in report
        assert "quality_metrics" in report
        assert report["overall_quality_score"] > 0.9


# ==================== Test Suite 6: Performance and Scalability (10 tests) ====================

class TestPerformanceScalability:
    """Test performance optimization and scalability"""

    @pytest.mark.asyncio
    async def test_high_throughput_generation(self, perf_service):
        """Test high-throughput data generation"""
        start_time = asyncio.get_event_loop().time()
        
        config = GenerationConfig(
            num_traces=10000,
            parallel_workers=10
        )
        
        records = await perf_service.generate_parallel(config)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        throughput = len(records) / duration
        assert throughput > 1000  # Should generate >1000 records/second

    @pytest.mark.asyncio
    async def test_memory_efficient_streaming(self, perf_service):
        """Test memory-efficient streaming generation"""
        memory_usage = []
        
        async def monitor_memory():
            import psutil
            process = psutil.Process()
            while True:
                memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
                await asyncio.sleep(0.1)
        
        monitor_task = asyncio.create_task(monitor_memory())
        
        # Generate large dataset in streaming mode
        stream = perf_service.generate_stream(
            GenerationConfig(num_traces=100000)
        )
        
        count = 0
        async for record in stream:
            count += 1
            if count >= 100000:
                break
        
        monitor_task.cancel()
        
        # Memory should not grow linearly with data size
        max_memory = max(memory_usage)
        assert max_memory < 500  # Should stay under 500MB

    @pytest.mark.asyncio
    async def test_horizontal_scaling(self, perf_service):
        """Test horizontal scaling with multiple workers"""
        worker_counts = [1, 5, 10, 20]
        throughputs = []
        
        for workers in worker_counts:
            config = GenerationConfig(
                num_traces=5000,
                parallel_workers=workers
            )
            
            start = asyncio.get_event_loop().time()
            await perf_service.generate_parallel(config)
            duration = asyncio.get_event_loop().time() - start
            
            throughputs.append(5000 / duration)
        
        # Throughput should increase with workers (with diminishing returns)
        for i in range(1, len(throughputs)):
            assert throughputs[i] > throughputs[i-1]

    @pytest.mark.asyncio
    async def test_batch_size_optimization(self, perf_service):
        """Test optimal batch size determination"""
        batch_sizes = [10, 50, 100, 500, 1000, 5000]
        best_throughput = 0
        optimal_batch_size = 0
        
        for batch_size in batch_sizes:
            config = GenerationConfig(
                num_traces=10000,
                batch_size=batch_size
            )
            
            start = asyncio.get_event_loop().time()
            await perf_service.generate_batched(config)
            duration = asyncio.get_event_loop().time() - start
            
            throughput = 10000 / duration
            if throughput > best_throughput:
                best_throughput = throughput
                optimal_batch_size = batch_size
        
        # Optimal batch size should be in middle range
        assert 100 <= optimal_batch_size <= 1000

    @pytest.mark.asyncio
    async def test_connection_pooling_efficiency(self, perf_service):
        """Test connection pool efficiency"""
        pool_metrics = await perf_service.test_connection_pool(
            pool_size=20,
            concurrent_requests=100,
            duration_seconds=10
        )
        
        assert pool_metrics.pool_utilization > 0.7
        assert pool_metrics.connection_wait_time_avg < 100  # ms
        assert pool_metrics.connection_reuse_rate > 0.9

    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, perf_service):
        """Test corpus cache effectiveness"""
        # First access - cache miss
        start1 = asyncio.get_event_loop().time()
        corpus1 = await perf_service.get_corpus_cached("test_corpus")
        time1 = asyncio.get_event_loop().time() - start1
        
        # Second access - cache hit
        start2 = asyncio.get_event_loop().time()
        corpus2 = await perf_service.get_corpus_cached("test_corpus")
        time2 = asyncio.get_event_loop().time() - start2
        
        assert corpus1 == corpus2
        assert time2 < time1 * 0.1  # Cache hit should be >10x faster

    @pytest.mark.asyncio
    async def test_auto_scaling_behavior(self, perf_service):
        """Test auto-scaling based on load"""
        config = GenerationConfig(
            num_traces=50000,
            enable_auto_scaling=True,
            min_workers=2,
            max_workers=20
        )
        
        scaling_events = []
        
        async def scaling_callback(event):
            scaling_events.append(event)
        
        await perf_service.generate_with_auto_scaling(
            config,
            scaling_callback=scaling_callback
        )
        
        # Should have scaling events
        scale_up_events = [e for e in scaling_events if e["type"] == "scale_up"]
        scale_down_events = [e for e in scaling_events if e["type"] == "scale_down"]
        
        assert len(scale_up_events) > 0
        assert len(scale_down_events) > 0

    @pytest.mark.asyncio
    async def test_resource_limit_handling(self, perf_service):
        """Test behavior at resource limits"""
        config = GenerationConfig(
            num_traces=100000,
            memory_limit_mb=100,
            cpu_limit_percent=50
        )
        
        result = await perf_service.generate_with_limits(config)
        
        assert result["completed"] == True
        assert result["memory_exceeded_count"] == 0
        assert result["cpu_throttle_events"] > 0

    @pytest.mark.asyncio
    async def test_query_optimization(self, perf_service):
        """Test ClickHouse query optimization"""
        # Unoptimized query
        unoptimized_time = await perf_service.benchmark_query(
            "SELECT * FROM corpus WHERE workload_type = 'simple_chat'",
            optimize=False
        )
        
        # Optimized query with projection
        optimized_time = await perf_service.benchmark_query(
            "SELECT prompt, response FROM corpus WHERE workload_type = 'simple_chat'",
            optimize=True
        )
        
        assert optimized_time < unoptimized_time * 0.5

    @pytest.mark.asyncio
    async def test_burst_load_handling(self, perf_service):
        """Test handling of burst loads"""
        # Normal load
        normal_config = GenerationConfig(
            num_traces=1000,
            arrival_pattern="uniform"
        )
        
        # Burst load
        burst_config = GenerationConfig(
            num_traces=1000,
            arrival_pattern="burst",
            burst_factor=10
        )
        
        normal_result = await perf_service.generate_with_pattern(normal_config)
        burst_result = await perf_service.generate_with_pattern(burst_config)
        
        # Should handle burst without failures
        assert burst_result["success_rate"] > 0.95
        assert burst_result["peak_throughput"] > normal_result["avg_throughput"] * 5


# ==================== Test Suite 7: Error Recovery (10 tests) ====================

class TestErrorRecovery:
    """Test error handling and recovery mechanisms"""

    @pytest.mark.asyncio
    async def test_corpus_unavailable_fallback(self, recovery_service):
        """Test fallback when corpus is unavailable"""
        with patch.object(recovery_service, 'get_corpus_content', side_effect=Exception("Corpus not found")):
            config = GenerationConfig(
                num_traces=100,
                use_fallback_corpus=True
            )
            
            records = await recovery_service.generate_with_fallback(config)
            
            assert len(records) == 100
            assert all(r.get("source") == "fallback_corpus" for r in records)

    @pytest.mark.asyncio
    async def test_clickhouse_connection_recovery(self, recovery_service):
        """Test recovery from ClickHouse connection failures"""
        failure_count = 0
        
        async def flaky_connection(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception("Connection failed")
            return AsyncMock()
        
        with patch('app.services.synthetic_data_service.get_clickhouse_client', side_effect=flaky_connection):
            result = await recovery_service.ingest_with_retry(
                [{"id": 1}],
                max_retries=5,
                retry_delay_ms=10
            )
            
            assert result["success"] == True
            assert result["retry_count"] == 3

    @pytest.mark.asyncio
    async def test_generation_checkpoint_recovery(self, recovery_service):
        """Test recovery from generation crashes using checkpoints"""
        # Simulate crash at 50%
        with patch.object(recovery_service, 'generate_batch') as mock_gen:
            mock_gen.side_effect = [
                [{"id": i} for i in range(100)],  # First batch OK
                Exception("Generation crashed"),  # Crash
            ]
            
            config = GenerationConfig(
                num_traces=200,
                checkpoint_interval=100
            )
            
            try:
                await recovery_service.generate_with_checkpoints(config)
            except Exception:
                pass  # Expected to fail for testing recovery
            
            # Resume from checkpoint
            resumed_result = await recovery_service.resume_from_checkpoint(config)
            
            assert resumed_result["resumed_from_record"] == 100
            assert len(resumed_result["records"]) == 200

    @pytest.mark.asyncio
    async def test_websocket_disconnect_recovery(self, recovery_service):
        """Test recovery from WebSocket disconnections"""
        ws_manager = MagicMock()
        disconnect_count = 0
        
        async def flaky_send(job_id, data):
            nonlocal disconnect_count
            disconnect_count += 1
            if disconnect_count == 3:
                raise Exception("WebSocket disconnected")
            return None
        
        ws_manager.broadcast_to_job = flaky_send
        
        # Should continue generation despite WS failures
        result = await recovery_service.generate_with_ws_updates(
            GenerationConfig(num_traces=100),
            ws_manager=ws_manager
        )
        
        assert result["generation_complete"] == True
        assert result["ws_failures"] == 1

    @pytest.mark.asyncio
    async def test_memory_overflow_handling(self, recovery_service):
        """Test handling of memory overflow conditions"""
        config = GenerationConfig(
            num_traces=1000000,  # Very large
            memory_limit_mb=50
        )
        
        result = await recovery_service.generate_with_memory_limit(config)
        
        # Should complete with reduced batch sizes
        assert result["completed"] == True
        assert result["memory_overflow_prevented"] == True
        assert result["batch_size_reduced"] == True

    @pytest.mark.asyncio
    async def test_circuit_breaker_operation(self, recovery_service):
        """Test circuit breaker preventing cascade failures"""
        circuit_breaker = recovery_service.get_circuit_breaker()
        
        # Simulate repeated failures
        for _ in range(5):
            try:
                await circuit_breaker.call(lambda: 1/0)
            except (ZeroDivisionError, Exception):
                pass  # Expected division by zero for testing
        
        # Circuit should open
        assert circuit_breaker.state == "open"
        
        # Wait for timeout
        await asyncio.sleep(circuit_breaker.timeout)
        
        # Should transition to half-open
        assert circuit_breaker.state == "half_open"

    @pytest.mark.asyncio
    async def test_dead_letter_queue_processing(self, recovery_service):
        """Test dead letter queue for failed records"""
        records = [{"id": i, "fail": i % 10 == 0} for i in range(100)]
        
        async def process_with_failures(record):
            if record.get("fail"):
                raise Exception("Processing failed")
            return record
        
        result = await recovery_service.process_with_dlq(
            records,
            process_fn=process_with_failures
        )
        
        assert len(result["processed"]) == 90
        assert len(result["dead_letter_queue"]) == 10

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, recovery_service):
        """Test transaction rollback on failures"""
        async def failing_operation():
            # Start transaction
            tx = await recovery_service.begin_transaction()
            
            # Partial success
            await tx.insert_records([{"id": 1}, {"id": 2}])
            
            # Failure
            raise Exception("Operation failed")
        
        try:
            await failing_operation()
        except Exception:
            pass  # Expected to fail for testing fallback
        
        # Should have rolled back
        result = await recovery_service.query_records()
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_idempotent_generation(self, recovery_service):
        """Test idempotent generation to prevent duplicates"""
        job_id = str(uuid.uuid4())
        config = GenerationConfig(
            num_traces=100,
            job_id=job_id
        )
        
        # First generation
        result1 = await recovery_service.generate_idempotent(config)
        
        # Duplicate request with same job_id
        result2 = await recovery_service.generate_idempotent(config)
        
        # Should return cached result
        assert result2["cached"] == True
        assert result1["records"] == result2["records"]

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, recovery_service):
        """Test graceful degradation under failures"""
        config = GenerationConfig(
            num_traces=1000,
            required_features=["corpus_sampling", "tool_simulation", "clustering"],
            degradation_allowed=True
        )
        
        # Simulate feature failures
        with patch.object(recovery_service, 'enable_clustering', side_effect=Exception("Clustering unavailable")):
            result = await recovery_service.generate_with_degradation(config)
        
        assert result["completed"] == True
        assert "clustering" in result["disabled_features"]
        assert len(result["records"]) == 1000


# ==================== Test Suite 8: Admin Visibility (10 tests) ====================

class TestAdminVisibility:
    """Test admin monitoring and visibility features"""

    @pytest.mark.asyncio
    async def test_generation_job_monitoring(self, admin_service):
        """Test real-time job monitoring for admins"""
        job_id = str(uuid.uuid4())
        
        # Start generation
        generation_task = asyncio.create_task(
            admin_service.generate_monitored(
                GenerationConfig(num_traces=1000),
                job_id=job_id
            )
        )
        
        # Monitor job
        await asyncio.sleep(0.1)
        status = await admin_service.get_job_status(job_id)
        
        assert status["state"] == "running"
        assert "progress_percentage" in status
        assert "estimated_completion" in status
        
        await generation_task

    @pytest.mark.asyncio
    async def test_detailed_metrics_dashboard(self, admin_service):
        """Test detailed metrics dashboard for admins"""
        metrics = await admin_service.get_generation_metrics(
            time_range_hours=24
        )
        
        assert "total_jobs" in metrics
        assert "success_rate" in metrics
        assert "avg_generation_time" in metrics
        assert "records_per_second" in metrics
        assert "resource_utilization" in metrics

    @pytest.mark.asyncio
    async def test_corpus_usage_analytics(self, admin_service):
        """Test corpus usage analytics for admins"""
        analytics = await admin_service.get_corpus_analytics()
        
        assert "most_used_corpora" in analytics
        assert "corpus_coverage" in analytics
        assert "content_distribution" in analytics
        assert "access_patterns" in analytics

    @pytest.mark.asyncio
    async def test_audit_log_generation(self, admin_service):
        """Test audit logging of generation activities"""
        job_id = str(uuid.uuid4())
        
        await admin_service.generate_with_audit(
            GenerationConfig(num_traces=100),
            job_id=job_id,
            user_id="admin_user"
        )
        
        audit_logs = await admin_service.get_audit_logs(job_id=job_id)
        
        assert len(audit_logs) > 0
        assert all("timestamp" in log for log in audit_logs)
        assert all("action" in log for log in audit_logs)
        assert all("user_id" in log for log in audit_logs)

    @pytest.mark.asyncio
    async def test_performance_profiling(self, admin_service):
        """Test performance profiling for optimization"""
        profile = await admin_service.profile_generation(
            GenerationConfig(num_traces=1000)
        )
        
        assert "generation_time_breakdown" in profile
        assert "bottlenecks" in profile
        assert "optimization_suggestions" in profile
        assert profile["generation_time_breakdown"]["total"] > 0

    @pytest.mark.asyncio
    async def test_alert_configuration(self, admin_service):
        """Test alert configuration for admins"""
        alert_config = {
            "slow_generation": {"threshold_seconds": 60},
            "high_error_rate": {"threshold_percentage": 5},
            "resource_exhaustion": {"memory_threshold_mb": 1000}
        }
        
        await admin_service.configure_alerts(alert_config)
        
        # Trigger alert condition
        with patch.object(admin_service, 'send_alert') as mock_alert:
            await admin_service.generate_synthetic_data(
                GenerationConfig(num_traces=10000)  # Will be slow
            )
            
            mock_alert.assert_called()

    @pytest.mark.asyncio
    async def test_job_cancellation_by_admin(self, admin_service):
        """Test admin ability to cancel running jobs"""
        job_id = str(uuid.uuid4())
        
        # Start long-running job
        generation_task = asyncio.create_task(
            admin_service.generate_synthetic_data(
                GenerationConfig(num_traces=100000),
                job_id=job_id
            )
        )
        
        await asyncio.sleep(0.1)
        
        # Admin cancels job
        result = await admin_service.cancel_job(job_id, reason="Testing cancellation")
        
        assert result["cancelled"] == True
        assert result["records_completed"] < 100000
        
        generation_task.cancel()

    @pytest.mark.asyncio
    async def test_resource_usage_tracking(self, admin_service):
        """Test tracking of resource usage during generation"""
        resource_tracker = await admin_service.start_resource_tracking()
        
        await admin_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        usage = await resource_tracker.get_usage_summary()
        
        assert "peak_memory_mb" in usage
        assert "avg_cpu_percent" in usage
        assert "total_io_operations" in usage
        assert "clickhouse_queries" in usage

    @pytest.mark.asyncio
    async def test_admin_diagnostic_tools(self, admin_service):
        """Test diagnostic tools for troubleshooting"""
        diagnostics = await admin_service.run_diagnostics()
        
        assert diagnostics["corpus_connectivity"] == "healthy"
        assert diagnostics["clickhouse_connectivity"] == "healthy"
        assert diagnostics["websocket_status"] == "active"
        assert "worker_pool_status" in diagnostics
        assert "cache_hit_rate" in diagnostics

    @pytest.mark.asyncio
    async def test_batch_job_management(self, admin_service):
        """Test batch job management interface for admins"""
        # Schedule multiple jobs
        job_ids = []
        for i in range(5):
            job_id = await admin_service.schedule_generation(
                GenerationConfig(num_traces=1000),
                scheduled_time=datetime.utcnow() + timedelta(minutes=i)
            )
            job_ids.append(job_id)
        
        # Get batch status
        batch_status = await admin_service.get_batch_status(job_ids)
        
        assert len(batch_status) == 5
        assert all(s["state"] == "scheduled" for s in batch_status)
        
        # Cancel batch
        await admin_service.cancel_batch(job_ids)


# ==================== Test Suite 9: Integration Testing (10 tests) ====================

class TestIntegration:
    """Test end-to-end integration scenarios"""

    @pytest.mark.asyncio
    async def test_complete_generation_workflow(self, full_stack):
        """Test complete workflow from corpus creation to data visualization"""
        # 1. Create corpus
        corpus = await full_stack["corpus"].create_corpus(
            schemas.CorpusCreate(name="integration_test", domain="e-commerce"),
            user_id="test_user"
        )
        
        # 2. Upload content
        await full_stack["corpus"].upload_content(
            corpus.id,
            [{"prompt": f"Q{i}", "response": f"A{i}"} for i in range(100)]
        )
        
        # 3. Generate synthetic data
        job_id = str(uuid.uuid4())
        config = GenerationConfig(
            num_traces=1000,
            corpus_id=corpus.id
        )
        
        records = await full_stack["generation"].generate_synthetic_data(
            config,
            job_id=job_id
        )
        
        # 4. Verify ClickHouse ingestion
        ingested = await full_stack["clickhouse"].query(
            f"SELECT COUNT(*) FROM synthetic_data_{job_id}"
        )
        
        assert ingested[0][0] == 1000

    @pytest.mark.asyncio
    async def test_multi_tenant_generation(self, full_stack):
        """Test multi-tenant data generation isolation"""
        tenant_configs = [
            {"tenant_id": "tenant_1", "domain": "healthcare"},
            {"tenant_id": "tenant_2", "domain": "finance"},
            {"tenant_id": "tenant_3", "domain": "retail"}
        ]
        
        jobs = []
        for config in tenant_configs:
            job = await full_stack["generation"].generate_for_tenant(
                GenerationConfig(num_traces=500),
                tenant_id=config["tenant_id"],
                domain=config["domain"]
            )
            jobs.append(job)
        
        # Verify isolation
        for i, job in enumerate(jobs):
            data = await full_stack["clickhouse"].query(
                f"SELECT DISTINCT tenant_id FROM {job['table_name']}"
            )
            assert len(data) == 1
            assert data[0][0] == tenant_configs[i]["tenant_id"]

    @pytest.mark.asyncio
    async def test_real_time_streaming_pipeline(self, full_stack):
        """Test real-time streaming from generation to UI"""
        job_id = str(uuid.uuid4())
        received_updates = []
        
        # Setup WebSocket listener
        async def ws_listener():
            async for message in full_stack["websocket"].listen(job_id):
                received_updates.append(message)
                if message.get("type") == "generation_complete":
                    break
        
        listener_task = asyncio.create_task(ws_listener())
        
        # Start generation
        await full_stack["generation"].generate_streaming(
            GenerationConfig(num_traces=100),
            job_id=job_id
        )
        
        await listener_task
        
        # Verify updates received
        assert len(received_updates) > 0
        assert any(u["type"] == "generation_progress" for u in received_updates)
        assert received_updates[-1]["type"] == "generation_complete"

    @pytest.mark.asyncio
    async def test_failure_recovery_integration(self, full_stack):
        """Test integrated failure recovery across components"""
        # Simulate ClickHouse failure midway
        original_insert = full_stack["clickhouse"].insert
        call_count = 0
        
        async def failing_insert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if 3 <= call_count <= 5:
                raise Exception("ClickHouse unavailable")
            return await original_insert(*args, **kwargs)
        
        full_stack["clickhouse"].insert = failing_insert
        
        # Should complete with retries
        result = await full_stack["generation"].generate_with_recovery(
            GenerationConfig(num_traces=1000)
        )
        
        assert result["completed"] == True
        assert result["recovery_attempts"] > 0

    @pytest.mark.asyncio
    async def test_cross_component_validation(self, full_stack):
        """Test validation across multiple components"""
        # Generate data
        config = GenerationConfig(num_traces=1000)
        generation_result = await full_stack["generation"].generate_synthetic_data(config)
        
        # Validate in ClickHouse
        ch_validation = await full_stack["clickhouse"].validate_data_quality(
            generation_result["table_name"]
        )
        
        # Cross-check with generation metrics
        assert abs(ch_validation["record_count"] - generation_result["records_generated"]) < 10
        assert ch_validation["schema_valid"] == True

    @pytest.mark.asyncio
    async def test_performance_under_load(self, full_stack):
        """Test system performance under concurrent load"""
        concurrent_jobs = 10
        
        async def run_job(index):
            return await full_stack["generation"].generate_synthetic_data(
                GenerationConfig(num_traces=1000)
            )
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[run_job(i) for i in range(concurrent_jobs)])
        total_time = asyncio.get_event_loop().time() - start_time
        
        # All should complete
        assert all(r["success"] for r in results)
        
        # Performance should scale reasonably
        assert total_time < 60  # Should complete within 1 minute

    @pytest.mark.asyncio
    async def test_data_consistency_verification(self, full_stack):
        """Test data consistency across all storage layers"""
        job_id = str(uuid.uuid4())
        
        # Generate data
        generation_result = await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(num_traces=1000),
            job_id=job_id
        )
        
        # Check PostgreSQL metadata
        pg_metadata = await full_stack["corpus"].get_job_metadata(job_id)
        
        # Check ClickHouse data
        ch_count = await full_stack["clickhouse"].count_records(
            f"synthetic_data_{job_id}"
        )
        
        # Check cache
        cache_count = full_stack["generation"].get_cache_count(job_id)
        
        # All should be consistent
        assert pg_metadata["record_count"] == ch_count == 1000

    @pytest.mark.asyncio
    async def test_monitoring_integration(self, full_stack):
        """Test monitoring and metrics collection integration"""
        # Enable monitoring
        await full_stack["generation"].enable_monitoring()
        
        # Run generation
        await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(num_traces=500)
        )
        
        # Collect metrics
        metrics = await full_stack["generation"].collect_metrics()
        
        assert metrics["generation_count"] > 0
        assert metrics["ingestion_success_rate"] > 0.95
        assert "latency_p99" in metrics

    @pytest.mark.asyncio
    async def test_security_and_access_control(self, full_stack):
        """Test security and access control integration"""
        # Create corpus with restricted access
        restricted_corpus = await full_stack["corpus"].create_corpus(
            schemas.CorpusCreate(name="restricted", access_level="admin_only"),
            user_id="admin"
        )
        
        # Non-admin user attempts generation
        with pytest.raises(Exception):
            await full_stack["generation"].generate_synthetic_data(
                GenerationConfig(corpus_id=restricted_corpus.id),
                user_id="regular_user"
            )
        
        # Admin user succeeds
        result = await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(corpus_id=restricted_corpus.id),
            user_id="admin"
        )
        
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_cleanup_and_retention(self, full_stack):
        """Test data cleanup and retention policies"""
        # Generate data with retention policy
        job_id = str(uuid.uuid4())
        await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(num_traces=1000),
            job_id=job_id,
            retention_days=1
        )
        
        # Verify data exists
        initial_count = await full_stack["clickhouse"].count_records(
            f"synthetic_data_{job_id}"
        )
        assert initial_count == 1000
        
        # Trigger cleanup for expired data
        await full_stack["generation"].cleanup_expired_data()
        
        # Verify cleanup (would need to mock time for actual test)
        # This is a placeholder for the cleanup verification


# ==================== Test Suite 10: Advanced Features (10 tests) ====================

class TestAdvancedFeatures:
    """Test advanced and specialized features"""

    @pytest.mark.asyncio
    async def test_ml_driven_pattern_generation(self, advanced_service):
        """Test ML-driven pattern learning and generation"""
        # Train on production patterns
        training_data = await advanced_service.load_production_patterns()
        model = await advanced_service.train_pattern_model(training_data)
        
        # Generate using learned patterns
        generated = await advanced_service.generate_ml_driven(
            model=model,
            num_traces=1000
        )
        
        # Validate similarity to production
        similarity_score = await advanced_service.calculate_pattern_similarity(
            generated,
            training_data
        )
        
        assert similarity_score > 0.85

    @pytest.mark.asyncio
    async def test_anomaly_injection_strategies(self, advanced_service):
        """Test various anomaly injection strategies"""
        strategies = [
            "random_spike",
            "gradual_degradation",
            "cascading_failure",
            "intermittent_issue"
        ]
        
        for strategy in strategies:
            config = GenerationConfig(
                num_traces=1000,
                anomaly_strategy=strategy,
                anomaly_rate=0.1
            )
            
            records = await advanced_service.generate_with_anomalies(config)
            anomalies = await advanced_service.detect_anomalies(records)
            
            # Should inject appropriate anomalies
            assert len(anomalies) > 0
            assert all(a["strategy"] == strategy for a in anomalies)

    @pytest.mark.asyncio
    async def test_cross_correlation_generation(self, advanced_service):
        """Test generation with cross-correlations between metrics"""
        config = GenerationConfig(
            num_traces=1000,
            correlations=[
                {"field1": "request_size", "field2": "latency", "coefficient": 0.7},
                {"field1": "error_rate", "field2": "throughput", "coefficient": -0.5}
            ]
        )
        
        records = await advanced_service.generate_with_correlations(config)
        
        # Verify correlations
        corr1 = await advanced_service.calculate_correlation(
            records, "request_size", "latency"
        )
        corr2 = await advanced_service.calculate_correlation(
            records, "error_rate", "throughput"
        )
        
        assert 0.6 <= corr1 <= 0.8
        assert -0.6 <= corr2 <= -0.4

    @pytest.mark.asyncio
    async def test_temporal_event_sequences(self, advanced_service):
        """Test generation of complex temporal event sequences"""
        sequence_config = {
            "user_journey": [
                {"event": "login", "duration_ms": [100, 500]},
                {"event": "browse", "duration_ms": [5000, 30000]},
                {"event": "add_to_cart", "duration_ms": [200, 1000]},
                {"event": "checkout", "duration_ms": [2000, 10000]}
            ]
        }
        
        sequences = await advanced_service.generate_event_sequences(
            sequence_config,
            num_sequences=100
        )
        
        # Verify sequence integrity
        for seq in sequences:
            events = seq["events"]
            assert len(events) == 4
            assert events[0]["event"] == "login"
            assert events[-1]["event"] == "checkout"
            
            # Verify temporal ordering
            for i in range(1, len(events)):
                assert events[i]["timestamp"] > events[i-1]["timestamp"]

    @pytest.mark.asyncio
    async def test_geo_distributed_simulation(self, advanced_service):
        """Test geo-distributed workload simulation"""
        geo_config = GenerationConfig(
            num_traces=1000,
            geo_distribution={
                "us-east": 0.4,
                "eu-west": 0.3,
                "ap-south": 0.2,
                "sa-east": 0.1
            },
            latency_by_region={
                "us-east": [10, 50],
                "eu-west": [50, 150],
                "ap-south": [100, 300],
                "sa-east": [150, 400]
            }
        )
        
        records = await advanced_service.generate_geo_distributed(geo_config)
        
        # Verify geo distribution
        region_counts = {}
        for record in records:
            region = record["region"]
            region_counts[region] = region_counts.get(region, 0) + 1
        
        for region, expected_ratio in geo_config.geo_distribution.items():
            actual_ratio = region_counts.get(region, 0) / len(records)
            assert abs(actual_ratio - expected_ratio) < 0.05

    @pytest.mark.asyncio
    async def test_adaptive_generation_feedback(self, advanced_service):
        """Test adaptive generation based on validation feedback"""
        target_metrics = {
            "avg_latency": 100,
            "error_rate": 0.02,
            "throughput": 1000
        }
        
        # Initial generation
        config = GenerationConfig(num_traces=1000)
        records = await advanced_service.generate_adaptive(config, target_metrics)
        
        # Should adapt to meet targets
        actual_metrics = await advanced_service.calculate_metrics(records)
        
        assert abs(actual_metrics["avg_latency"] - 100) < 10
        assert abs(actual_metrics["error_rate"] - 0.02) < 0.005
        assert abs(actual_metrics["throughput"] - 1000) < 50

    @pytest.mark.asyncio
    async def test_multi_model_workload_generation(self, advanced_service):
        """Test generation for multi-model AI workloads"""
        model_config = {
            "models": [
                {"name": "gpt-4", "weight": 0.5, "latency_ms": [500, 2000]},
                {"name": "claude-3", "weight": 0.3, "latency_ms": [400, 1500]},
                {"name": "llama-2", "weight": 0.2, "latency_ms": [100, 500]}
            ],
            "model_switching_pattern": "load_balanced"
        }
        
        records = await advanced_service.generate_multi_model(
            GenerationConfig(num_traces=1000),
            model_config
        )
        
        # Verify model distribution
        model_usage = {}
        for record in records:
            model = record["model_name"]
            model_usage[model] = model_usage.get(model, 0) + 1
        
        for model_cfg in model_config["models"]:
            expected_count = model_cfg["weight"] * 1000
            actual_count = model_usage.get(model_cfg["name"], 0)
            assert abs(actual_count - expected_count) < 50

    @pytest.mark.asyncio
    async def test_compliance_aware_generation(self, advanced_service):
        """Test generation with compliance constraints"""
        compliance_config = {
            "standards": ["HIPAA", "GDPR"],
            "data_residency": "eu-west",
            "pii_handling": "pseudonymized",
            "audit_level": "detailed"
        }
        
        records = await advanced_service.generate_compliant(
            GenerationConfig(num_traces=1000),
            compliance_config
        )
        
        # Verify compliance
        for record in records:
            assert record["data_residency"] == "eu-west"
            assert "pii" not in record or record["pii"]["pseudonymized"] == True
            assert "audit_trail" in record
            assert record["compliance_standards"] == ["HIPAA", "GDPR"]

    @pytest.mark.asyncio
    async def test_cost_optimized_generation(self, advanced_service):
        """Test cost-optimized data generation"""
        cost_constraints = {
            "max_cost_per_1000_records": 0.10,
            "preferred_storage": "compressed",
            "compute_tier": "spot_instances"
        }
        
        result = await advanced_service.generate_cost_optimized(
            GenerationConfig(num_traces=10000),
            cost_constraints
        )
        
        assert result["total_cost"] <= 1.0  # $0.10 per 1000 * 10
        assert result["storage_format"] == "compressed"
        assert result["compute_cost_saved"] > 0

    @pytest.mark.asyncio
    async def test_versioned_corpus_generation(self, advanced_service):
        """Test generation with versioned corpus content"""
        # Create corpus versions
        v1_corpus = await advanced_service.create_corpus_version(
            "base_corpus", version=1
        )
        v2_corpus = await advanced_service.create_corpus_version(
            "base_corpus", version=2, changes={"new_patterns": True}
        )
        
        # Generate with different versions
        v1_data = await advanced_service.generate_from_corpus_version(
            GenerationConfig(num_traces=100),
            corpus_version=1
        )
        
        v2_data = await advanced_service.generate_from_corpus_version(
            GenerationConfig(num_traces=100),
            corpus_version=2
        )
        
        # Should have different characteristics
        v1_patterns = set(r["pattern_id"] for r in v1_data)
        v2_patterns = set(r["pattern_id"] for r in v2_data)
        
        assert v1_patterns != v2_patterns
        assert len(v2_patterns - v1_patterns) > 0  # V2 has new patterns


# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])