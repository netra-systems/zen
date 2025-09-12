"""
Metrics Integration Tests Package

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core observability functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from monitoring blind spots
- Value Impact: Comprehensive metrics pipeline testing ensuring reliability
- Revenue Impact: Prevents operational issues from going undetected

This package contains focused integration tests for:
- Metric Collection: User action -> metric capture validation
- Metric Aggregation: Processing and summarizing collected metrics
- Metric Storage: Persistence and retrieval verification
- Metrics Pipeline: End-to-end performance and reliability testing

All tests maintain  <= 8 lines per test function and  <= 300 lines per module.
"""

from netra_backend.tests.integration.metrics.shared_fixtures import (
    MetricEvent,
    MockMetricsAggregator,
    MockMetricsCollector,
    MockMetricsStorage,
    MockUserActionTracker,
    metrics_aggregator,
    metrics_collector,
    metrics_storage,
    user_action_tracker,
)

__all__ = [
    "MetricEvent",
    "MockMetricsCollector",
    "MockMetricsAggregator", 
    "MockMetricsStorage",
    "MockUserActionTracker",
    "metrics_collector",
    "metrics_aggregator",
    "metrics_storage", 
    "user_action_tracker"
]