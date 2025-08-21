"""
Real-time Ingestion Test Suite for Synthetic Data Service
Testing real-time data ingestion to ClickHouse
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.tests.test_synthetic_data_service_basic import IngestionMetrics

# Add project root to path


@pytest.fixture
def ingestion_service():
    return SyntheticDataService()


@pytest.fixture
def mock_clickhouse():
    client = AsyncMock()
    client.execute = AsyncMock()
    client.query = AsyncMock()
    return client


# ==================== Test Suite: Real-time Ingestion ====================

class TestRealTimeIngestion:
    """Test real-time data ingestion to ClickHouse"""
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
    async def test_streaming_ingestion_with_backpressure(self, ingestion_service):
        """Test streaming ingestion with backpressure handling"""
        async def generate_stream():
            for i in range(10000):
                yield {"id": i, "timestamp": datetime.now(UTC)}
                if i % 100 == 0:
                    await asyncio.sleep(0.01)  # Simulate processing time
        
        ingestion_metrics = await ingestion_service.ingest_stream(
            generate_stream(),
            max_buffer_size=500,
            flush_interval_ms=100
        )
        
        assert ingestion_metrics.records_processed == 10000
        assert ingestion_metrics.backpressure_events > 0
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
    async def test_ingestion_metrics_tracking(self, ingestion_service):
        """Test tracking ingestion metrics and performance"""
        start_time = datetime.now(UTC)
        
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
    async def test_ingestion_with_transformation(self, ingestion_service):
        """Test data transformation during ingestion"""
        def transform_record(record):
            record["timestamp"] = datetime.now(UTC).isoformat()
            record["processed"] = True
            return record
        
        records = [{"id": i, "value": i * 10} for i in range(100)]
        
        result = await ingestion_service.ingest_with_transform(
            records,
            transform_fn=transform_record
        )
        
        assert all("timestamp" in r for r in result["transformed_records"])
        assert all(r["processed"] == True for r in result["transformed_records"])
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


# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])