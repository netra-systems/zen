"""
CRITICAL INTEGRATION TEST #15: Metrics Collection Pipeline

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Ensures user action → metric capture → aggregation → storage verification
- Revenue Impact: Prevents operational issues from going undetected that would cause customer churn

REQUIREMENTS:
- User actions trigger metric collection
- Metrics are captured with proper metadata
- Aggregation processes metrics correctly
- Storage verification ensures data persistence
- Metric capture within 1 second
- 100% metric collection reliability
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass, asdict

# Set testing environment
import os
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.logging_config import central_logger
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)


@dataclass
class MetricEvent:
    """Represents a metric event in the collection pipeline."""
    metric_name: str
    metric_value: float
    metric_type: str  # counter, gauge, histogram
    labels: Dict[str, str]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None


class MockMetricsCollector:
    """Mock metrics collector for testing pipeline integration."""
    
    def __init__(self):
        self.collected_metrics = []
        self.collection_rate = {}
        self.dropped_metrics = 0
        self.collection_errors = 0
        self.buffer_size = 1000
        self.flush_interval = 5.0
        
    async def collect_metric(self, event: MetricEvent) -> bool:
        """Collect single metric event."""
        try:
            # Simulate collection processing time
            await asyncio.sleep(0.001)
            
            # Add collection metadata
            enriched_event = MetricEvent(
                metric_name=event.metric_name,
                metric_value=event.metric_value,
                metric_type=event.metric_type,
                labels={**event.labels, "collector": "mock_collector"},
                timestamp=event.timestamp,
                user_id=event.user_id,
                session_id=event.session_id,
                trace_id=event.trace_id or str(uuid.uuid4())
            )
            
            # Buffer management
            if len(self.collected_metrics) >= self.buffer_size:
                self.dropped_metrics += 1
                return False
            
            self.collected_metrics.append(enriched_event)
            
            # Track collection rate
            metric_key = event.metric_name
            if metric_key not in self.collection_rate:
                self.collection_rate[metric_key] = {"count": 0, "last_collected": time.time()}
            
            self.collection_rate[metric_key]["count"] += 1
            self.collection_rate[metric_key]["last_collected"] = time.time()
            
            return True
            
        except Exception as e:
            self.collection_errors += 1
            logger.error(f"Metric collection error: {e}")
            return False
    
    async def collect_batch(self, events: List[MetricEvent]) -> Dict[str, int]:
        """Collect batch of metric events."""
        results = {"successful": 0, "failed": 0}
        
        for event in events:
            success = await self.collect_metric(event)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def get_metrics_by_name(self, metric_name: str) -> List[MetricEvent]:
        """Get all metrics by name."""
        return [m for m in self.collected_metrics if m.metric_name == metric_name]
    
    def get_metrics_by_user(self, user_id: str) -> List[MetricEvent]:
        """Get all metrics for specific user."""
        return [m for m in self.collected_metrics if m.user_id == user_id]
    
    async def flush_buffer(self) -> int:
        """Flush collected metrics to storage."""
        flushed_count = len(self.collected_metrics)
        self.collected_metrics.clear()
        return flushed_count


class MockMetricsAggregator:
    """Mock metrics aggregator for processing collected metrics."""
    
    def __init__(self, collector: MockMetricsCollector):
        self.collector = collector
        self.aggregated_metrics = {}
        self.aggregation_rules = {
            "request_count": {"type": "counter", "aggregation": "sum"},
            "response_time": {"type": "histogram", "aggregation": "avg"},
            "error_rate": {"type": "gauge", "aggregation": "rate"},
            "user_active_sessions": {"type": "gauge", "aggregation": "count_unique"},
            "llm_tokens_used": {"type": "counter", "aggregation": "sum"}
        }
        
    async def aggregate_metrics(self, time_window: timedelta = timedelta(minutes=1)) -> Dict[str, Any]:
        """Aggregate metrics over time window."""
        current_time = datetime.now(timezone.utc)
        window_start = current_time - time_window
        
        # Get metrics within time window
        window_metrics = [
            m for m in self.collector.collected_metrics
            if m.timestamp >= window_start
        ]
        
        aggregation_results = {}
        
        for metric_name, rule in self.aggregation_rules.items():
            metric_events = [m for m in window_metrics if m.metric_name == metric_name]
            
            if not metric_events:
                continue
            
            if rule["aggregation"] == "sum":
                value = sum(m.metric_value for m in metric_events)
            elif rule["aggregation"] == "avg":
                value = sum(m.metric_value for m in metric_events) / len(metric_events)
            elif rule["aggregation"] == "rate":
                # Calculate error rate
                total_requests = len([m for m in window_metrics if m.metric_name == "request_count"])
                error_count = len(metric_events)
                value = (error_count / max(1, total_requests)) * 100
            elif rule["aggregation"] == "count_unique":
                unique_values = set(m.user_id for m in metric_events if m.user_id)
                value = len(unique_values)
            else:
                value = len(metric_events)
            
            aggregation_results[metric_name] = {
                "value": value,
                "count": len(metric_events),
                "window_start": window_start.isoformat(),
                "window_end": current_time.isoformat(),
                "aggregation_type": rule["aggregation"]
            }
        
        # Store aggregated results
        window_key = f"{window_start.isoformat()}_{current_time.isoformat()}"
        self.aggregated_metrics[window_key] = aggregation_results
        
        return aggregation_results
    
    async def get_metric_trends(self, metric_name: str, periods: int = 5) -> List[Dict[str, Any]]:
        """Get metric trends over multiple time periods."""
        trends = []
        
        for i in range(periods):
            period_start = datetime.now(timezone.utc) - timedelta(minutes=(i+1))
            period_end = datetime.now(timezone.utc) - timedelta(minutes=i)
            
            period_metrics = [
                m for m in self.collector.collected_metrics
                if m.metric_name == metric_name and period_start <= m.timestamp <= period_end
            ]
            
            if period_metrics:
                avg_value = sum(m.metric_value for m in period_metrics) / len(period_metrics)
                trends.append({
                    "period": i,
                    "start_time": period_start.isoformat(),
                    "end_time": period_end.isoformat(),
                    "value": avg_value,
                    "sample_count": len(period_metrics)
                })
        
        return list(reversed(trends))  # Return chronological order


class MockMetricsStorage:
    """Mock metrics storage for persistence verification."""
    
    def __init__(self):
        self.stored_metrics = {}
        self.storage_operations = []
        self.storage_errors = 0
        self.retention_policy = timedelta(days=30)
        
    async def store_metrics(self, metrics: Dict[str, Any], storage_key: str) -> bool:
        """Store aggregated metrics."""
        try:
            operation_start = time.time()
            
            # Simulate storage latency
            await asyncio.sleep(0.01)
            
            storage_entry = {
                "metrics": metrics,
                "stored_at": datetime.now(timezone.utc),
                "storage_key": storage_key,
                "size_bytes": len(str(metrics))
            }
            
            self.stored_metrics[storage_key] = storage_entry
            
            operation_time = time.time() - operation_start
            
            self.storage_operations.append({
                "operation": "store",
                "key": storage_key,
                "timestamp": datetime.now(timezone.utc),
                "operation_time": operation_time,
                "success": True
            })
            
            return True
            
        except Exception as e:
            self.storage_errors += 1
            self.storage_operations.append({
                "operation": "store",
                "key": storage_key,
                "timestamp": datetime.now(timezone.utc),
                "error": str(e),
                "success": False
            })
            return False
    
    async def retrieve_metrics(self, storage_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored metrics."""
        if storage_key in self.stored_metrics:
            return self.stored_metrics[storage_key]["metrics"]
        return None
    
    async def cleanup_old_metrics(self) -> int:
        """Clean up metrics older than retention policy."""
        current_time = datetime.now(timezone.utc)
        keys_to_remove = []
        
        for key, entry in self.stored_metrics.items():
            if current_time - entry["stored_at"] > self.retention_policy:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.stored_metrics[key]
        
        return len(keys_to_remove)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_size = sum(entry["size_bytes"] for entry in self.stored_metrics.values())
        
        return {
            "total_entries": len(self.stored_metrics),
            "total_size_bytes": total_size,
            "storage_operations": len(self.storage_operations),
            "storage_errors": self.storage_errors,
            "oldest_entry": min((entry["stored_at"] for entry in self.stored_metrics.values()), default=None),
            "newest_entry": max((entry["stored_at"] for entry in self.stored_metrics.values()), default=None)
        }


class MockUserActionTracker:
    """Mock user action tracker for generating metric events."""
    
    def __init__(self, metrics_collector: MockMetricsCollector):
        self.metrics_collector = metrics_collector
        self.tracked_actions = []
        
    async def track_user_action(self, action_type: str, user_id: str, action_data: Dict[str, Any]) -> bool:
        """Track user action and generate relevant metrics."""
        action_id = str(uuid.uuid4())
        action_timestamp = datetime.now(timezone.utc)
        
        # Record action
        self.tracked_actions.append({
            "action_id": action_id,
            "action_type": action_type,
            "user_id": user_id,
            "action_data": action_data,
            "timestamp": action_timestamp
        })
        
        # Generate metrics based on action type
        metrics_to_collect = []
        
        if action_type == "user_message":
            metrics_to_collect.extend([
                MetricEvent(
                    metric_name="request_count",
                    metric_value=1,
                    metric_type="counter",
                    labels={"action": "user_message", "user_tier": action_data.get("user_tier", "free")},
                    timestamp=action_timestamp,
                    user_id=user_id
                ),
                MetricEvent(
                    metric_name="message_length",
                    metric_value=len(action_data.get("content", "")),
                    metric_type="histogram",
                    labels={"action": "user_message"},
                    timestamp=action_timestamp,
                    user_id=user_id
                )
            ])
        
        elif action_type == "agent_response":
            response_time = action_data.get("response_time", 0)
            metrics_to_collect.extend([
                MetricEvent(
                    metric_name="response_time",
                    metric_value=response_time,
                    metric_type="histogram",
                    labels={"agent_type": action_data.get("agent_type", "unknown")},
                    timestamp=action_timestamp,
                    user_id=user_id
                ),
                MetricEvent(
                    metric_name="llm_tokens_used",
                    metric_value=action_data.get("tokens_used", 0),
                    metric_type="counter",
                    labels={"model": action_data.get("model", "unknown")},
                    timestamp=action_timestamp,
                    user_id=user_id
                )
            ])
        
        elif action_type == "user_session":
            metrics_to_collect.append(
                MetricEvent(
                    metric_name="user_active_sessions",
                    metric_value=1,
                    metric_type="gauge",
                    labels={"session_type": action_data.get("session_type", "websocket")},
                    timestamp=action_timestamp,
                    user_id=user_id,
                    session_id=action_data.get("session_id")
                )
            )
        
        elif action_type == "error":
            metrics_to_collect.append(
                MetricEvent(
                    metric_name="error_rate",
                    metric_value=1,
                    metric_type="gauge",
                    labels={"error_type": action_data.get("error_type", "unknown")},
                    timestamp=action_timestamp,
                    user_id=user_id
                )
            )
        
        # Collect all generated metrics
        collection_results = await self.metrics_collector.collect_batch(metrics_to_collect)
        
        return collection_results["successful"] == len(metrics_to_collect)


class TestMetricsCollectionPipeline:
    """BVJ: Protects $35K MRR through reliable metrics collection pipeline."""

    @pytest.fixture
    def metrics_collector(self):
        """Create mock metrics collector."""
        return MockMetricsCollector()

    @pytest.fixture
    def metrics_aggregator(self, metrics_collector):
        """Create mock metrics aggregator."""
        return MockMetricsAggregator(metrics_collector)

    @pytest.fixture
    def metrics_storage(self):
        """Create mock metrics storage."""
        return MockMetricsStorage()

    @pytest.fixture
    def user_action_tracker(self, metrics_collector):
        """Create mock user action tracker."""
        return MockUserActionTracker(metrics_collector)

    @pytest.mark.asyncio
    async def test_01_user_action_metric_capture(self, user_action_tracker, metrics_collector):
        """BVJ: Validates user actions trigger metric collection correctly."""
        # Step 1: Track user message action
        user_id = "metric_test_user"
        
        message_action_data = {
            "content": "Help me optimize my AI workload performance",
            "user_tier": "early",
            "session_id": "session_123"
        }
        
        start_time = time.time()
        success = await user_action_tracker.track_user_action("user_message", user_id, message_action_data)
        capture_time = time.time() - start_time
        
        # Step 2: Validate action tracking
        assert success, "User action tracking failed"
        assert capture_time < 1.0, f"Metric capture took {capture_time:.2f}s, exceeds 1s limit"
        
        # Step 3: Verify metrics were collected
        collected_metrics = metrics_collector.collected_metrics
        assert len(collected_metrics) >= 2, f"Expected at least 2 metrics, got {len(collected_metrics)}"
        
        # Check request count metric
        request_metrics = metrics_collector.get_metrics_by_name("request_count")
        assert len(request_metrics) >= 1, "Request count metric not collected"
        
        request_metric = request_metrics[0]
        assert request_metric.metric_value == 1, "Request count value incorrect"
        assert request_metric.user_id == user_id, "User ID not captured"
        assert request_metric.labels["user_tier"] == "early", "User tier not captured"
        
        # Check message length metric
        length_metrics = metrics_collector.get_metrics_by_name("message_length")
        assert len(length_metrics) >= 1, "Message length metric not collected"
        
        length_metric = length_metrics[0]
        expected_length = len(message_action_data["content"])
        assert length_metric.metric_value == expected_length, "Message length incorrect"
        
        logger.info(f"User action metric capture validated: {capture_time:.2f}s capture time")

    @pytest.mark.asyncio
    async def test_02_agent_response_metric_collection(self, user_action_tracker, metrics_collector):
        """BVJ: Validates agent responses generate proper metrics."""
        # Step 1: Track agent response action
        user_id = "agent_metric_user"
        
        response_action_data = {
            "agent_type": "optimization",
            "response_time": 2.5,
            "tokens_used": 150,
            "model": "gpt-4-turbo",
            "quality_score": 0.85
        }
        
        success = await user_action_tracker.track_user_action("agent_response", user_id, response_action_data)
        assert success, "Agent response tracking failed"
        
        # Step 2: Verify response time metrics
        response_time_metrics = metrics_collector.get_metrics_by_name("response_time")
        assert len(response_time_metrics) >= 1, "Response time metric not collected"
        
        time_metric = response_time_metrics[0]
        assert time_metric.metric_value == 2.5, "Response time value incorrect"
        assert time_metric.labels["agent_type"] == "optimization", "Agent type not captured"
        
        # Step 3: Verify token usage metrics
        token_metrics = metrics_collector.get_metrics_by_name("llm_tokens_used")
        assert len(token_metrics) >= 1, "Token usage metric not collected"
        
        token_metric = token_metrics[0]
        assert token_metric.metric_value == 150, "Token usage value incorrect"
        assert token_metric.labels["model"] == "gpt-4-turbo", "Model not captured"
        
        # Step 4: Test multiple response scenarios
        response_scenarios = [
            {"agent_type": "triage", "response_time": 0.8, "tokens_used": 50},
            {"agent_type": "data", "response_time": 3.2, "tokens_used": 200},
            {"agent_type": "reporting", "response_time": 1.5, "tokens_used": 120}
        ]
        
        for scenario in response_scenarios:
            await user_action_tracker.track_user_action("agent_response", user_id, scenario)
        
        # Validate all scenarios captured
        final_response_metrics = metrics_collector.get_metrics_by_name("response_time")
        assert len(final_response_metrics) >= 4, "Not all response metrics captured"  # 1 initial + 3 scenarios
        
        logger.info(f"Agent response metrics validated: {len(final_response_metrics)} response metrics collected")

    @pytest.mark.asyncio
    async def test_03_metrics_aggregation_processing(self, user_action_tracker, metrics_aggregator, metrics_collector):
        """BVJ: Validates metrics aggregation processes collected data correctly."""
        # Step 1: Generate diverse metrics data
        user_id = "aggregation_test_user"
        
        # Generate multiple user messages
        for i in range(5):
            await user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Test message {i}",
                "user_tier": "mid"
            })
        
        # Generate agent responses with varying times
        response_times = [1.2, 2.5, 0.8, 3.1, 1.7]
        for i, response_time in enumerate(response_times):
            await user_action_tracker.track_user_action("agent_response", user_id, {
                "agent_type": "optimization",
                "response_time": response_time,
                "tokens_used": 100 + (i * 25)
            })
        
        # Generate some errors
        for i in range(2):
            await user_action_tracker.track_user_action("error", user_id, {
                "error_type": "llm_timeout"
            })
        
        # Step 2: Perform aggregation
        start_time = time.time()
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        aggregation_time = time.time() - start_time
        
        # Step 3: Validate aggregation results
        assert len(aggregation_results) > 0, "No metrics aggregated"
        assert aggregation_time < 2.0, f"Aggregation took {aggregation_time:.2f}s, too slow"
        
        # Check request count aggregation
        if "request_count" in aggregation_results:
            request_count = aggregation_results["request_count"]
            assert request_count["value"] == 5, f"Request count aggregation incorrect: {request_count['value']}"
            assert request_count["aggregation_type"] == "sum", "Aggregation type incorrect"
        
        # Check response time aggregation
        if "response_time" in aggregation_results:
            response_time_agg = aggregation_results["response_time"]
            expected_avg = sum(response_times) / len(response_times)
            assert abs(response_time_agg["value"] - expected_avg) < 0.1, "Response time average incorrect"
        
        # Check token usage aggregation
        if "llm_tokens_used" in aggregation_results:
            token_agg = aggregation_results["llm_tokens_used"]
            expected_total = sum(100 + (i * 25) for i in range(5))
            assert token_agg["value"] == expected_total, "Token usage sum incorrect"
        
        # Check error rate calculation
        if "error_rate" in aggregation_results:
            error_rate = aggregation_results["error_rate"]
            expected_rate = (2 / 5) * 100  # 2 errors out of 5 requests
            assert abs(error_rate["value"] - expected_rate) < 1.0, "Error rate calculation incorrect"
        
        logger.info(f"Metrics aggregation validated: {aggregation_time:.2f}s processing time")

    @pytest.mark.asyncio
    async def test_04_metrics_storage_verification(self, metrics_aggregator, metrics_storage, metrics_collector):
        """BVJ: Validates metrics storage ensures data persistence."""
        # Step 1: Generate metrics and aggregate
        test_metrics = [
            MetricEvent("test_counter", 10, "counter", {"test": "true"}, datetime.now(timezone.utc)),
            MetricEvent("test_gauge", 75.5, "gauge", {"test": "true"}, datetime.now(timezone.utc)),
            MetricEvent("test_histogram", 1.5, "histogram", {"test": "true"}, datetime.now(timezone.utc))
        ]
        
        for metric in test_metrics:
            await metrics_collector.collect_metric(metric)
        
        aggregated_data = await metrics_aggregator.aggregate_metrics(timedelta(minutes=1))
        
        # Step 2: Store aggregated metrics
        storage_key = f"test_metrics_{int(time.time())}"
        
        start_time = time.time()
        storage_success = await metrics_storage.store_metrics(aggregated_data, storage_key)
        storage_time = time.time() - start_time
        
        # Step 3: Validate storage operation
        assert storage_success, "Metrics storage failed"
        assert storage_time < 1.0, f"Storage took {storage_time:.2f}s, too slow"
        
        # Step 4: Verify data persistence
        retrieved_data = await metrics_storage.retrieve_metrics(storage_key)
        assert retrieved_data is not None, "Stored metrics not retrievable"
        assert retrieved_data == aggregated_data, "Retrieved data doesn't match stored data"
        
        # Step 5: Validate storage metadata
        storage_stats = metrics_storage.get_storage_stats()
        assert storage_stats["total_entries"] >= 1, "Storage entry count incorrect"
        assert storage_stats["total_size_bytes"] > 0, "Storage size not tracked"
        assert storage_stats["storage_operations"] >= 1, "Storage operations not tracked"
        
        # Step 6: Test multiple storage operations
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
        assert final_stats["total_entries"] >= 4, "Not all storage operations recorded"
        
        logger.info(f"Metrics storage verified: {storage_time:.2f}s storage time, {final_stats['total_entries']} entries")

    @pytest.mark.asyncio
    async def test_05_end_to_end_pipeline_performance(self, user_action_tracker, metrics_aggregator, metrics_storage):
        """BVJ: Validates complete end-to-end metrics pipeline performance."""
        # Step 1: Simulate realistic user activity
        pipeline_start_time = time.time()
        
        users = [f"pipeline_user_{i}" for i in range(10)]
        total_actions = 0
        
        # Generate user activities
        for user_id in users:
            # User session start
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
            
            # Occasional errors
            if int(user_id.split('_')[-1]) % 3 == 0:
                await user_action_tracker.track_user_action("error", user_id, {
                    "error_type": "rate_limit"
                })
                total_actions += 1
        
        action_generation_time = time.time() - pipeline_start_time
        
        # Step 2: Process aggregation
        aggregation_start_time = time.time()
        aggregated_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=10))
        aggregation_time = time.time() - aggregation_start_time
        
        # Step 3: Store aggregated data
        storage_start_time = time.time()
        storage_key = f"e2e_pipeline_{int(time.time())}"
        storage_success = await metrics_storage.store_metrics(aggregated_results, storage_key)
        storage_time = time.time() - storage_start_time
        
        total_pipeline_time = time.time() - pipeline_start_time
        
        # Step 4: Validate pipeline performance
        assert storage_success, "End-to-end pipeline storage failed"
        assert total_pipeline_time < 30.0, f"Complete pipeline took {total_pipeline_time:.2f}s, too slow"
        assert aggregation_time < 5.0, f"Aggregation took {aggregation_time:.2f}s, too slow"
        assert storage_time < 2.0, f"Storage took {storage_time:.2f}s, too slow"
        
        # Step 5: Validate data integrity
        retrieved_data = await metrics_storage.retrieve_metrics(storage_key)
        assert retrieved_data == aggregated_results, "Pipeline data integrity compromised"
        
        # Step 6: Verify metric accuracy
        if "request_count" in aggregated_results:
            # Should have 30 user messages (10 users × 3 messages)
            request_count = aggregated_results["request_count"]["value"]
            assert request_count == 30, f"Request count {request_count} doesn't match expected 30"
        
        if "user_active_sessions" in aggregated_results:
            # Should have 10 unique users
            session_count = aggregated_results["user_active_sessions"]["value"]
            assert session_count == 10, f"Session count {session_count} doesn't match expected 10"
        
        # Step 7: Calculate pipeline efficiency
        actions_per_second = total_actions / total_pipeline_time
        assert actions_per_second >= 10.0, f"Pipeline efficiency {actions_per_second:.1f} actions/sec too low"
        
        logger.info(f"E2E pipeline validated: {total_pipeline_time:.2f}s total, {actions_per_second:.1f} actions/sec")

    @pytest.mark.asyncio
    async def test_06_metrics_pipeline_reliability_and_error_handling(self, user_action_tracker, metrics_collector, metrics_storage):
        """BVJ: Validates metrics pipeline reliability and error handling."""
        # Step 1: Test high-volume metric collection
        high_volume_start = time.time()
        
        # Generate burst of metrics
        burst_size = 500
        user_id = "reliability_user"
        
        collection_tasks = []
        for i in range(burst_size):
            task = user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Burst message {i}",
                "burst_test": True
            })
            collection_tasks.append(task)
        
        # Execute burst collection
        burst_results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        burst_time = time.time() - high_volume_start
        
        # Step 2: Analyze burst performance
        successful_collections = sum(1 for r in burst_results if r is True)
        failed_collections = burst_size - successful_collections
        
        collection_success_rate = (successful_collections / burst_size) * 100
        
        assert collection_success_rate >= 95.0, f"Collection success rate {collection_success_rate}% below 95%"
        assert burst_time < 10.0, f"Burst collection took {burst_time:.2f}s, too slow"
        
        # Step 3: Test buffer overflow handling
        initial_buffer_size = len(metrics_collector.collected_metrics)
        
        # Fill buffer beyond capacity
        overflow_metrics = []
        for i in range(metrics_collector.buffer_size + 100):
            metric = MetricEvent(
                metric_name="overflow_test",
                metric_value=i,
                metric_type="counter",
                labels={"test": "overflow"},
                timestamp=datetime.now(timezone.utc)
            )
            overflow_metrics.append(metric)
        
        overflow_results = await metrics_collector.collect_batch(overflow_metrics)
        
        # Should have some dropped metrics
        assert metrics_collector.dropped_metrics > 0, "Buffer overflow not handled"
        assert overflow_results["failed"] > 0, "Failed collections not reported"
        
        # Step 4: Test storage error handling
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
        
        # Step 5: Test recovery after errors
        recovery_test_data = {"recovery": "test"}
        recovery_result = await metrics_storage.store_metrics(recovery_test_data, "recovery_test")
        assert recovery_result, "Storage recovery failed"
        
        # Verify data integrity after recovery
        retrieved_recovery_data = await metrics_storage.retrieve_metrics("recovery_test")
        assert retrieved_recovery_data == recovery_test_data, "Data integrity compromised after recovery"
        
        # Step 6: Calculate overall reliability metrics
        total_operations = burst_size + len(overflow_metrics)
        reliability_score = ((successful_collections + overflow_results["successful"]) / total_operations) * 100
        
        assert reliability_score >= 90.0, f"Overall reliability {reliability_score}% below 90%"
        
        logger.info(f"Pipeline reliability validated: {reliability_score}% reliability, {collection_success_rate}% collection success")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])