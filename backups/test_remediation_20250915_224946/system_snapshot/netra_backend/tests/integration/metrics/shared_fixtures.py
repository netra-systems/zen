from shared.isolated_environment import get_env
"""
env = get_env()
Shared fixtures and utilities for metrics integration tests.

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Provides reusable test infrastructure for metrics validation
- Revenue Impact: Ensures consistent testing of metrics pipeline components
"""

import asyncio

# Set testing environment
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

env.set("TESTING", "1", "test")
env.set("ENVIRONMENT", "testing", "test")
env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")

from netra_backend.app.logging_config import central_logger
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

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
            await asyncio.sleep(0.001)
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
            
            if len(self.collected_metrics) >= self.buffer_size:
                self.dropped_metrics += 1
                return False
            
            self.collected_metrics.append(enriched_event)
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
        
        window_key = f"{window_start.isoformat()}_{current_time.isoformat()}"
        self.aggregated_metrics[window_key] = aggregation_results
        return aggregation_results

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
        
        self.tracked_actions.append({
            "action_id": action_id,
            "action_type": action_type,
            "user_id": user_id,
            "action_data": action_data,
            "timestamp": action_timestamp
        })
        
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
        
        collection_results = await self.metrics_collector.collect_batch(metrics_to_collect)
        return collection_results["successful"] == len(metrics_to_collect)

@pytest.fixture
def metrics_collector():
    """Create mock metrics collector."""
    return MockMetricsCollector()

@pytest.fixture
def metrics_aggregator(metrics_collector):
    """Create mock metrics aggregator."""
    return MockMetricsAggregator(metrics_collector)

@pytest.fixture
def metrics_storage():
    """Create mock metrics storage."""
    return MockMetricsStorage()

@pytest.fixture
def user_action_tracker(metrics_collector):
    """Create mock user action tracker."""
    return MockUserActionTracker(metrics_collector)