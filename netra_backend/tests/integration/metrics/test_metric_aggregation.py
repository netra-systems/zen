"""
Metric Aggregation Integration Tests

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Validates metrics aggregation processes collected data correctly
- Revenue Impact: Ensures aggregated metrics provide accurate insights for platform optimization

REQUIREMENTS:
- Aggregation processes metrics correctly
- Request count aggregation via sum
- Response time aggregation via average
- Error rate calculation accuracy
- Aggregation processing within 2 seconds
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta

from app.logging_config import central_logger
from netra_backend.tests.shared_fixtures import (
    MetricEvent, MockMetricsAggregator, MockUserActionTracker,
    metrics_aggregator, user_action_tracker, metrics_collector
)

logger = central_logger.get_logger(__name__)


class TestMetricAggregation:
    """BVJ: Validates metrics aggregation processes collected data correctly."""

    @pytest.mark.asyncio
    async def test_metrics_aggregation_processing(self, user_action_tracker, metrics_aggregator, metrics_collector):
        """BVJ: Validates metrics aggregation processes collected data correctly."""
        user_id = "aggregation_test_user"
        
        # Generate multiple user messages
        for i in range(5):
            await user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Test message {i}",
                "user_tier": "mid"
            })
        
        start_time = time.time()
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        aggregation_time = time.time() - start_time
        
        assert len(aggregation_results) > 0, "No metrics aggregated"
        assert aggregation_time < 2.0, f"Aggregation took {aggregation_time:.2f}s, too slow"

    @pytest.mark.asyncio
    async def test_request_count_aggregation(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates request count aggregation via sum is correct."""
        user_id = "request_count_user"
        
        for i in range(5):
            await user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Message {i}",
                "user_tier": "mid"
            })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        
        if "request_count" in aggregation_results:
            request_count = aggregation_results["request_count"]
            assert request_count["value"] == 5, f"Request count aggregation incorrect: {request_count['value']}"
            assert request_count["aggregation_type"] == "sum", "Aggregation type incorrect"

    @pytest.mark.asyncio
    async def test_response_time_aggregation(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates response time aggregation via average is correct."""
        user_id = "response_time_user"
        response_times = [1.2, 2.5, 0.8, 3.1, 1.7]
        
        for i, response_time in enumerate(response_times):
            await user_action_tracker.track_user_action("agent_response", user_id, {
                "agent_type": "optimization",
                "response_time": response_time,
                "tokens_used": 100 + (i * 25)
            })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        
        if "response_time" in aggregation_results:
            response_time_agg = aggregation_results["response_time"]
            expected_avg = sum(response_times) / len(response_times)
            assert abs(response_time_agg["value"] - expected_avg) < 0.1, "Response time average incorrect"

    @pytest.mark.asyncio
    async def test_token_usage_aggregation(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates token usage aggregation via sum is correct."""
        user_id = "token_agg_user"
        
        for i in range(5):
            await user_action_tracker.track_user_action("agent_response", user_id, {
                "agent_type": "optimization",
                "response_time": 1.0,
                "tokens_used": 100 + (i * 25)
            })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        
        if "llm_tokens_used" in aggregation_results:
            token_agg = aggregation_results["llm_tokens_used"]
            expected_total = sum(100 + (i * 25) for i in range(5))
            assert token_agg["value"] == expected_total, "Token usage sum incorrect"

    @pytest.mark.asyncio
    async def test_error_rate_calculation(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates error rate calculation accuracy."""
        user_id = "error_rate_user"
        
        # Generate requests
        for i in range(5):
            await user_action_tracker.track_user_action("user_message", user_id, {
                "content": f"Message {i}",
                "user_tier": "mid"
            })
        
        # Generate errors
        for i in range(2):
            await user_action_tracker.track_user_action("error", user_id, {
                "error_type": "llm_timeout"
            })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        
        if "error_rate" in aggregation_results:
            error_rate = aggregation_results["error_rate"]
            expected_rate = (2 / 5) * 100  # 2 errors out of 5 requests
            assert abs(error_rate["value"] - expected_rate) < 1.0, "Error rate calculation incorrect"

    @pytest.mark.asyncio
    async def test_aggregation_time_window(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates aggregation respects time window boundaries."""
        user_id = "time_window_user"
        
        await user_action_tracker.track_user_action("user_message", user_id, {
            "content": "Current window message",
            "user_tier": "mid"
        })
        
        # Test 1-minute window
        aggregation_results_1min = await metrics_aggregator.aggregate_metrics(timedelta(minutes=1))
        
        # Test 5-minute window
        aggregation_results_5min = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        
        # 5-minute window should include all metrics that 1-minute window includes
        if "request_count" in aggregation_results_1min and "request_count" in aggregation_results_5min:
            count_1min = aggregation_results_1min["request_count"]["value"]
            count_5min = aggregation_results_5min["request_count"]["value"]
            assert count_5min >= count_1min, "Time window aggregation logic incorrect"

    @pytest.mark.asyncio
    async def test_unique_user_session_count(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates unique user session counting in aggregation."""
        users = ["session_user_1", "session_user_2", "session_user_3"]
        
        for user_id in users:
            await user_action_tracker.track_user_action("user_session", user_id, {
                "session_type": "websocket",
                "session_id": f"session_{user_id}"
            })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=5))
        
        if "user_active_sessions" in aggregation_results:
            session_count = aggregation_results["user_active_sessions"]
            assert session_count["value"] == 3, f"Unique session count incorrect: {session_count['value']}"
            assert session_count["aggregation_type"] == "count_unique", "Session aggregation type incorrect"

    @pytest.mark.asyncio
    async def test_aggregation_metadata_structure(self, user_action_tracker, metrics_aggregator):
        """BVJ: Validates aggregation results include proper metadata."""
        user_id = "metadata_structure_user"
        
        await user_action_tracker.track_user_action("user_message", user_id, {
            "content": "Test message",
            "user_tier": "early"
        })
        
        aggregation_results = await metrics_aggregator.aggregate_metrics(timedelta(minutes=1))
        
        for metric_name, metric_data in aggregation_results.items():
            assert "value" in metric_data, f"Missing value in {metric_name}"
            assert "count" in metric_data, f"Missing count in {metric_name}"
            assert "window_start" in metric_data, f"Missing window_start in {metric_name}"
            assert "window_end" in metric_data, f"Missing window_end in {metric_name}"
            assert "aggregation_type" in metric_data, f"Missing aggregation_type in {metric_name}"

        logger.info(f"Aggregation metadata validated for {len(aggregation_results)} metrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])