"""
Metric Collection Integration Tests

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Validates user actions trigger metric collection correctly
- Revenue Impact: Ensures metrics are captured with proper metadata within 1 second

REQUIREMENTS:
- User actions trigger metric collection
- Metrics are captured with proper metadata
- Metric capture within 1 second
- 100% metric collection reliability
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
import time
from datetime import datetime, timezone

import pytest

# Add project root to path
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.shared_fixtures import (
    # Add project root to path
    MetricEvent,
    MockMetricsCollector,
    MockUserActionTracker,
    metrics_collector,
    user_action_tracker,
)

logger = central_logger.get_logger(__name__)


class TestMetricCollection:
    """BVJ: Validates user actions trigger metric collection correctly."""

    @pytest.mark.asyncio
    async def test_user_action_metric_capture(self, user_action_tracker, metrics_collector):
        """BVJ: Validates user actions trigger metric collection correctly."""
        user_id = "metric_test_user"
        message_action_data = {
            "content": "Help me optimize my AI workload performance",
            "user_tier": "early",
            "session_id": "session_123"
        }
        
        start_time = time.time()
        success = await user_action_tracker.track_user_action("user_message", user_id, message_action_data)
        capture_time = time.time() - start_time
        
        assert success, "User action tracking failed"
        assert capture_time < 1.0, f"Metric capture took {capture_time:.2f}s, exceeds 1s limit"

    @pytest.mark.asyncio
    async def test_metric_metadata_capture(self, user_action_tracker, metrics_collector):
        """BVJ: Validates metrics are captured with proper metadata."""
        user_id = "metadata_test_user"
        message_action_data = {
            "content": "Test message for metadata validation",
            "user_tier": "early"
        }
        
        await user_action_tracker.track_user_action("user_message", user_id, message_action_data)
        
        request_metrics = metrics_collector.get_metrics_by_name("request_count")
        assert len(request_metrics) >= 1, "Request count metric not collected"
        
        request_metric = request_metrics[0]
        assert request_metric.metric_value == 1, "Request count value incorrect"
        assert request_metric.user_id == user_id, "User ID not captured"
        assert request_metric.labels["user_tier"] == "early", "User tier not captured"

    @pytest.mark.asyncio
    async def test_message_length_metric(self, user_action_tracker, metrics_collector):
        """BVJ: Validates message length metrics are calculated correctly."""
        user_id = "length_test_user"
        test_content = "This is a test message for length validation"
        message_action_data = {"content": test_content, "user_tier": "mid"}
        
        await user_action_tracker.track_user_action("user_message", user_id, message_action_data)
        
        length_metrics = metrics_collector.get_metrics_by_name("message_length")
        assert len(length_metrics) >= 1, "Message length metric not collected"
        
        length_metric = length_metrics[0]
        expected_length = len(test_content)
        assert length_metric.metric_value == expected_length, "Message length incorrect"

    @pytest.mark.asyncio
    async def test_agent_response_metrics(self, user_action_tracker, metrics_collector):
        """BVJ: Validates agent responses generate proper metrics."""
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

    @pytest.mark.asyncio
    async def test_response_time_metric_capture(self, user_action_tracker, metrics_collector):
        """BVJ: Validates response time metrics are captured correctly."""
        user_id = "response_time_user"
        response_action_data = {"agent_type": "optimization", "response_time": 2.5, "tokens_used": 150}
        
        await user_action_tracker.track_user_action("agent_response", user_id, response_action_data)
        
        response_time_metrics = metrics_collector.get_metrics_by_name("response_time")
        assert len(response_time_metrics) >= 1, "Response time metric not collected"
        
        time_metric = response_time_metrics[0]
        assert time_metric.metric_value == 2.5, "Response time value incorrect"
        assert time_metric.labels["agent_type"] == "optimization", "Agent type not captured"

    @pytest.mark.asyncio
    async def test_token_usage_metric_capture(self, user_action_tracker, metrics_collector):
        """BVJ: Validates token usage metrics are captured correctly."""
        user_id = "token_test_user"
        response_action_data = {"tokens_used": 150, "model": "gpt-4-turbo"}
        
        await user_action_tracker.track_user_action("agent_response", user_id, response_action_data)
        
        token_metrics = metrics_collector.get_metrics_by_name("llm_tokens_used")
        assert len(token_metrics) >= 1, "Token usage metric not collected"
        
        token_metric = token_metrics[0]
        assert token_metric.metric_value == 150, "Token usage value incorrect"
        assert token_metric.labels["model"] == "gpt-4-turbo", "Model not captured"

    @pytest.mark.asyncio
    async def test_multiple_response_scenarios(self, user_action_tracker, metrics_collector):
        """BVJ: Validates multiple agent response scenarios are captured."""
        user_id = "multi_scenario_user"
        response_scenarios = [
            {"agent_type": "triage", "response_time": 0.8, "tokens_used": 50},
            {"agent_type": "data", "response_time": 3.2, "tokens_used": 200},
            {"agent_type": "reporting", "response_time": 1.5, "tokens_used": 120}
        ]
        
        for scenario in response_scenarios:
            await user_action_tracker.track_user_action("agent_response", user_id, scenario)
        
        final_response_metrics = metrics_collector.get_metrics_by_name("response_time")
        assert len(final_response_metrics) >= 3, "Not all response metrics captured"
        logger.info(f"Multiple response scenarios validated: {len(final_response_metrics)} metrics collected")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])