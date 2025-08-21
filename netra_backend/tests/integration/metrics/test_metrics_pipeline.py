"""
End-to-End Metrics Pipeline Integration Tests

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Validates complete end-to-end metrics pipeline performance
- Revenue Impact: Ensures pipeline efficiency supports high-volume operations

REQUIREMENTS:
- Complete pipeline performance validation
- High-volume metric collection reliability
- Buffer overflow handling
- Pipeline efficiency metrics
- End-to-end processing within 30 seconds
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta

# Add project root to path

from netra_backend.app.logging_config import central_logger
from netra_backend.tests.shared_fixtures import (

# Add project root to path
    MetricEvent, MockUserActionTracker, MockMetricsAggregator, MockMetricsStorage,
    user_action_tracker, metrics_aggregator, metrics_storage, metrics_collector
)

logger = central_logger.get_logger(__name__)


class TestMetricsPipeline:
    """BVJ: Validates complete end-to-end metrics pipeline performance."""

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_performance(self, user_action_tracker, metrics_aggregator, metrics_storage):
        """BVJ: Validates complete end-to-end metrics pipeline performance."""
        pipeline_start_time = time.time()
        
        users = [f"pipeline_user_{i}" for i in range(10)]
        total_actions = 0
        
        # Generate user activities
        for user_id in users:
            await user_action_tracker.track_user_action("user_session", user_id, {
                "session_type": "websocket",
                "session_id": f"session_{user_id}"
            })
            total_actions += 1
            
            # Multiple user messages
            for msg_idx in range(3):
                await user_action_tracker.track_user_action("user_message", user_id, {
                    "content": f"User {user_id} message {msg_idx}",
                    "user_tier": "early" if int(user_id.split('_')[-1]) % 2 == 0 else "mid"
                })
                total_actions += 1
                
                # Corresponding agent responses
                await user_action_tracker.track_user_action("agent_response", user_id, {
                    "agent_type": "optimization",
                    "response_time": 1.0 + (msg_idx * 0.5),
                    "tokens_used": 100 + (msg_idx * 50),
                    "model": "gpt-4-turbo"
                })
                total_actions += 1
        
        action_generation_time = time.time() - pipeline_start_time
        
        aggregation_start_time = time.time()
        aggregated_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=10))
        aggregation_time = time.time() - aggregation_start_time
        
        storage_start_time = time.time()
        storage_key = f"e2e_pipeline_{int(time.time())}"
        storage_success = await metrics_storage.store_metrics(aggregated_results, storage_key)
        storage_time = time.time() - storage_start_time
        
        total_pipeline_time = time.time() - pipeline_start_time
        
        assert storage_success, "End-to-end pipeline storage failed"
        assert total_pipeline_time < 30.0, f"Complete pipeline took {total_pipeline_time:.2f}s, too slow"

    @pytest.mark.asyncio
    async def test_pipeline_data_integrity(self, user_action_tracker, metrics_aggregator, metrics_storage):
        """BVJ: Validates pipeline maintains data integrity end-to-end."""
        user_id = "data_integrity_user"
        
        # Generate specific metrics
        await user_action_tracker.track_user_action("user_message", user_id, {
            "content": "Test message",
            "user_tier": "mid"
        })
        
        aggregated_data = await metrics_aggregator.aggregate_metrics(timedelta(minutes=1))
        storage_key = f"integrity_test_{int(time.time())}"
        await metrics_storage.store_metrics(aggregated_data, storage_key)
        
        retrieved_data = await metrics_storage.retrieve_metrics(storage_key)
        assert retrieved_data == aggregated_data, "Pipeline data integrity compromised"

    @pytest.mark.asyncio
    async def test_pipeline_metric_accuracy(self, user_action_tracker, metrics_aggregator, metrics_storage):
        """BVJ: Validates pipeline produces accurate metric counts."""
        users = [f"accuracy_user_{i}" for i in range(5)]
        
        for user_id in users:
            await user_action_tracker.track_user_action("user_session", user_id, {
                "session_type": "websocket",
                "session_id": f"session_{user_id}"
            })
            
            # Each user sends 2 messages
            for i in range(2):
                await user_action_tracker.track_user_action("user_message", user_id, {
                    "content": f"Message {i}",
                    "user_tier": "early"
                })
        
        aggregated_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        storage_key = f"accuracy_test_{int(time.time())}"
        await metrics_storage.store_metrics(aggregated_results, storage_key)
        
        if "request_count" in aggregated_results:
            request_count = aggregated_results["request_count"]["value"]
            assert request_count == 10, f"Request count {request_count} doesn't match expected 10"
        
        if "user_active_sessions" in aggregated_results:
            session_count = aggregated_results["user_active_sessions"]["value"]
            assert session_count == 5, f"Session count {session_count} doesn't match expected 5"

    @pytest.mark.asyncio
    async def test_pipeline_efficiency_metrics(self, user_action_tracker, metrics_aggregator, metrics_storage):
        """BVJ: Validates pipeline efficiency meets performance requirements."""
        pipeline_start_time = time.time()
        total_actions = 50
        
        user_id = "efficiency_user"
        for i in range(total_actions):
            await user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Efficiency test message {i}",
                "user_tier": "mid"
            })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        storage_key = f"efficiency_test_{int(time.time())}"
        await metrics_storage.store_metrics(aggregation_results, storage_key)
        
        total_pipeline_time = time.time() - pipeline_start_time
        actions_per_second = total_actions / total_pipeline_time
        
        assert actions_per_second >= 10.0, f"Pipeline efficiency {actions_per_second:.1f} actions/sec too low"
        logger.info(f"Pipeline efficiency validated: {actions_per_second:.1f} actions/sec")

    @pytest.mark.asyncio
    async def test_high_volume_pipeline_reliability(self, user_action_tracker, metrics_collector, metrics_storage):
        """BVJ: Validates pipeline reliability under high-volume conditions."""
        high_volume_start = time.time()
        burst_size = 100
        user_id = "reliability_user"
        
        collection_tasks = []
        for i in range(burst_size):
            task = user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Burst message {i}",
                "burst_test": True
            })
            collection_tasks.append(task)
        
        burst_results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        burst_time = time.time() - high_volume_start
        
        successful_collections = sum(1 for r in burst_results if r is True)
        collection_success_rate = (successful_collections / burst_size) * 100
        
        assert collection_success_rate >= 95.0, f"Collection success rate {collection_success_rate}% below 95%"
        assert burst_time < 10.0, f"Burst collection took {burst_time:.2f}s, too slow"

    @pytest.mark.asyncio
    async def test_buffer_overflow_handling(self, metrics_collector):
        """BVJ: Validates pipeline handles buffer overflow gracefully."""
        initial_buffer_size = len(metrics_collector.collected_metrics)
        
        # Fill buffer beyond capacity
        overflow_metrics = []
        for i in range(metrics_collector.buffer_size + 50):
            metric = MetricEvent(
                metric_name="overflow_test",
                metric_value=i,
                metric_type="counter",
                labels={"test": "overflow"},
                timestamp=datetime.now(timezone.utc)
            )
            overflow_metrics.append(metric)
        
        overflow_results = await metrics_collector.collect_batch(overflow_metrics)
        
        assert metrics_collector.dropped_metrics > 0, "Buffer overflow not handled"
        assert overflow_results["failed"] > 0, "Failed collections not reported"

    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, user_action_tracker, metrics_storage):
        """BVJ: Validates pipeline recovers from component failures."""
        user_id = "error_recovery_user"
        
        # Generate normal activity
        await user_action_tracker.track_user_action("user_message", user_id, {
            "content": "Pre-error message",
            "user_tier": "early"
        })
        
        # Simulate temporary storage failure
        original_store_method = metrics_storage.store_metrics
        
        async def failing_store_method(*args, **kwargs):
            metrics_storage.storage_errors += 1
            return False
        
        metrics_storage.store_metrics = failing_store_method
        
        # Attempt operation during failure
        storage_result = await metrics_storage.store_metrics({"test": "data"}, "failing_test")
        assert not storage_result, "Storage failure not properly handled"
        
        # Restore functionality
        metrics_storage.store_metrics = original_store_method
        
        # Verify recovery
        recovery_test_data = {"recovery": "test"}
        recovery_result = await metrics_storage.store_metrics(recovery_test_data, "recovery_test")
        assert recovery_result, "Pipeline recovery failed"

    @pytest.mark.asyncio
    async def test_concurrent_pipeline_operations(self, user_action_tracker, metrics_aggregator, metrics_storage):
        """BVJ: Validates pipeline handles concurrent operations correctly."""
        concurrent_users = [f"concurrent_user_{i}" for i in range(5)]
        
        # Generate concurrent user activities
        concurrent_tasks = []
        for user_id in concurrent_users:
            task = user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Concurrent message from {user_id}",
                "user_tier": "mid"
            })
            concurrent_tasks.append(task)
        
        # Execute all activities concurrently
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        successful_concurrent = sum(1 for r in concurrent_results if r)
        
        assert successful_concurrent == len(concurrent_users), "Concurrent operations failed"
        
        # Verify aggregation handles concurrent data
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=1))
        
        if "request_count" in aggregation_results:
            request_count = aggregation_results["request_count"]["value"]
            assert request_count >= len(concurrent_users), "Concurrent data not aggregated correctly"

        logger.info(f"Concurrent pipeline operations validated: {successful_concurrent} successful operations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])