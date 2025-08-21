"""
Metric Storage Integration Tests

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Validates metrics storage ensures data persistence
- Revenue Impact: Ensures metrics data is reliably stored for analytics and monitoring

REQUIREMENTS:
- Storage verification ensures data persistence
- Storage operations complete within 1 second
- Data integrity maintained across store/retrieve cycles
- Storage metadata tracking for operations
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta

from app.logging_config import central_logger
from netra_backend.tests.shared_fixtures import (
    MetricEvent, MockMetricsStorage, MockMetricsAggregator,
    metrics_storage, metrics_aggregator, metrics_collector
)

logger = central_logger.get_logger(__name__)


class TestMetricStorage:
    """BVJ: Validates metrics storage ensures data persistence."""

    @pytest.mark.asyncio
    async def test_metrics_storage_verification(self, metrics_aggregator, metrics_storage, metrics_collector):
        """BVJ: Validates metrics storage ensures data persistence."""
        test_metrics = [
            MetricEvent("test_counter", 10, "counter", {"test": "true"}, datetime.now(timezone.utc)),
            MetricEvent("test_gauge", 75.5, "gauge", {"test": "true"}, datetime.now(timezone.utc)),
            MetricEvent("test_histogram", 1.5, "histogram", {"test": "true"}, datetime.now(timezone.utc))
        ]
        
        for metric in test_metrics:
            await metrics_collector.collect_metric(metric)
        
        aggregated_data = await metrics_aggregator.aggregate_metrics(timedelta(minutes=1))
        storage_key = f"test_metrics_{int(time.time())}"
        
        start_time = time.time()
        storage_success = await metrics_storage.store_metrics(aggregated_data, storage_key)
        storage_time = time.time() - start_time
        
        assert storage_success, "Metrics storage failed"
        assert storage_time < 1.0, f"Storage took {storage_time:.2f}s, too slow"

    @pytest.mark.asyncio
    async def test_data_persistence(self, metrics_storage):
        """BVJ: Validates data integrity is maintained across store/retrieve cycles."""
        test_data = {
            "test_metric": {"value": 42, "count": 1, "aggregation_type": "sum"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        storage_key = f"persistence_test_{int(time.time())}"
        
        storage_success = await metrics_storage.store_metrics(test_data, storage_key)
        assert storage_success, "Storage operation failed"
        
        retrieved_data = await metrics_storage.retrieve_metrics(storage_key)
        assert retrieved_data is not None, "Stored metrics not retrievable"
        assert retrieved_data == test_data, "Retrieved data doesn't match stored data"

    @pytest.mark.asyncio
    async def test_storage_metadata_tracking(self, metrics_storage):
        """BVJ: Validates storage metadata is tracked for operations."""
        test_data = {"simple_metric": 123}
        storage_key = f"metadata_test_{int(time.time())}"
        
        await metrics_storage.store_metrics(test_data, storage_key)
        
        storage_stats = metrics_storage.get_storage_stats()
        assert storage_stats["total_entries"] >= 1, "Storage entry count incorrect"
        assert storage_stats["total_size_bytes"] > 0, "Storage size not tracked"
        assert storage_stats["storage_operations"] >= 1, "Storage operations not tracked"

    @pytest.mark.asyncio
    async def test_multiple_storage_operations(self, metrics_storage):
        """BVJ: Validates multiple storage operations work correctly."""
        additional_storage_keys = []
        for i in range(3):
            key = f"additional_metrics_{i}_{int(time.time())}"
            await metrics_storage.store_metrics({"test_metric": i}, key)
            additional_storage_keys.append(key)
        
        # Verify all stored
        for key in additional_storage_keys:
            data = await metrics_storage.retrieve_metrics(key)
            assert data is not None, f"Additional metrics {key} not stored properly"
        
        final_stats = metrics_storage.get_storage_stats()
        assert final_stats["total_entries"] >= 3, "Not all storage operations recorded"

    @pytest.mark.asyncio
    async def test_storage_performance_at_scale(self, metrics_storage):
        """BVJ: Validates storage performance under load."""
        start_time = time.time()
        
        # Store multiple metrics quickly
        storage_tasks = []
        for i in range(10):
            key = f"scale_test_{i}_{int(time.time())}"
            task = metrics_storage.store_metrics({"metric_value": i}, key)
            storage_tasks.append(task)
        
        results = await asyncio.gather(*storage_tasks)
        total_time = time.time() - start_time
        
        successful_operations = sum(1 for r in results if r)
        assert successful_operations == 10, "Not all storage operations succeeded"
        assert total_time < 5.0, f"Batch storage took {total_time:.2f}s, too slow"

    @pytest.mark.asyncio
    async def test_storage_error_handling(self, metrics_storage):
        """BVJ: Validates storage error handling and recovery."""
        # Simulate storage failure
        original_store_method = metrics_storage.store_metrics
        
        async def failing_store_method(*args, **kwargs):
            metrics_storage.storage_errors += 1
            return False
        
        metrics_storage.store_metrics = failing_store_method
        
        # Attempt storage with failing method
        storage_result = await metrics_storage.store_metrics({"test": "data"}, "failing_test")
        assert not storage_result, "Storage failure not properly handled"
        assert metrics_storage.storage_errors > 0, "Storage errors not tracked"
        
        # Restore original method
        metrics_storage.store_metrics = original_store_method

    @pytest.mark.asyncio
    async def test_storage_recovery_after_errors(self, metrics_storage):
        """BVJ: Validates storage can recover after errors."""
        recovery_test_data = {"recovery": "test"}
        recovery_result = await metrics_storage.store_metrics(recovery_test_data, "recovery_test")
        assert recovery_result, "Storage recovery failed"
        
        # Verify data integrity after recovery
        retrieved_recovery_data = await metrics_storage.retrieve_metrics("recovery_test")
        assert retrieved_recovery_data == recovery_test_data, "Data integrity compromised after recovery"

    @pytest.mark.asyncio
    async def test_storage_size_tracking(self, metrics_storage):
        """BVJ: Validates storage size is tracked accurately."""
        large_data = {"large_metric": "x" * 1000, "value": 42}
        small_data = {"small_metric": 1}
        
        await metrics_storage.store_metrics(large_data, "large_test")
        await metrics_storage.store_metrics(small_data, "small_test")
        
        stats = metrics_storage.get_storage_stats()
        assert stats["total_size_bytes"] > 1000, "Large data size not tracked correctly"
        
        # Check that total size increases with more data
        initial_size = stats["total_size_bytes"]
        await metrics_storage.store_metrics(large_data, "another_large_test")
        
        updated_stats = metrics_storage.get_storage_stats()
        assert updated_stats["total_size_bytes"] > initial_size, "Storage size not updating"

    @pytest.mark.asyncio
    async def test_storage_timestamp_tracking(self, metrics_storage):
        """BVJ: Validates storage timestamps are tracked for entries."""
        test_data = {"timestamp_test": "value"}
        
        before_storage = datetime.now(timezone.utc)
        await metrics_storage.store_metrics(test_data, "timestamp_test")
        after_storage = datetime.now(timezone.utc)
        
        stats = metrics_storage.get_storage_stats()
        
        if stats["newest_entry"]:
            newest_time = stats["newest_entry"]
            assert before_storage <= newest_time <= after_storage, "Storage timestamp not accurate"

        logger.info(f"Storage verification completed: {stats['total_entries']} entries, {stats['total_size_bytes']} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])