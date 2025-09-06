'''Core unit tests for MetricsCollector.

Tests customer usage tracking for accurate billing calculations.
CRITICAL for revenue accuracy - prevents under/overcharging customers.

Business Value: Ensures precise usage metrics collection for billing,
preventing revenue loss and customer disputes.
'''

from pathlib import Path
import sys
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
import pytest

from netra_backend.app.monitoring.metrics_collector import (
    PerformanceMetric,
    MetricsCollector,
    DatabaseMetrics,
    SystemResourceMetrics,
    WebSocketMetrics
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment


class TestMetricsCollectorCore:
    """Core test suite for MetricsCollector billing accuracy."""

    @pytest.fixture
    def collector(self):
        """Create metrics collector with minimal retention."""
        return MetricsCollector(retention_period=300)  # 5 minutes for testing

    @pytest.fixture
    def system_metrics(self):
        """Create sample system resource metrics."""
        return SystemResourceMetrics(
            cpu_percent=45.2,
            memory_percent=67.8,
            memory_available_mb=2048.0,
            disk_io_read_mb=15.3,
            disk_io_write_mb=8.7,
            network_bytes_sent=1024,
            network_bytes_recv=2048,
            active_connections=25
        )

    @pytest.mark.asyncio
    async def test_start_collection_creates_tasks(self, collector):
        """Test that start_collection creates required background tasks."""
        await collector.start_collection()
        
        assert len(collector._collection_tasks) == 5
        assert all(isinstance(task, asyncio.Task) for task in collector._collection_tasks)
        
        await collector.stop_collection()

    @pytest.mark.asyncio
    async def test_stop_collection_cancels_tasks(self, collector):
        """Test that stop_collection properly cancels all tasks."""
        await collector.start_collection()
        
        initial_task_count = len(collector._collection_tasks)
        await collector.stop_collection()
        
        assert collector._shutdown is True
        assert initial_task_count == 5

    def test_record_system_metrics(self, collector, system_metrics):
        """Test recording system metrics to buffer."""
        collector._record_system_metrics(system_metrics)
        
        assert len(collector._metrics_buffer["system_resources"]) == 1
        assert len(collector._metrics_buffer["system.cpu_percent"]) == 1
        assert len(collector._metrics_buffer["system.memory_percent"]) == 1
        assert collector._metrics_buffer["system.cpu_percent"][0].value == 45.2

    def test_record_metric_basic(self, collector):
        """Test basic metric recording functionality."""
        collector._record_metric("test.metric", 123.45, {"source": "test"})
        
        assert len(collector._metrics_buffer["test.metric"]) == 1
        
        metric = collector._metrics_buffer["test.metric"][0]
        assert metric.value == 123.45
        assert metric.tags["source"] == "test"

    def test_cleanup_old_metrics(self, collector):
        """Test cleanup of expired metrics."""
        old_time = datetime.now() - timedelta(seconds=400)  # Older than retention
        new_time = datetime.now()
        
        old_metric = PerformanceMetric("test", 1.0, old_time)
        new_metric = PerformanceMetric("test", 2.0, new_time)
        
        collector._metrics_buffer["test_metric"].extend([old_metric, new_metric])
        collector._remove_expired_metrics()
        
        assert len(collector._metrics_buffer["test_metric"]) == 1
        assert collector._metrics_buffer["test_metric"][0].timestamp == new_time

    def test_metrics_buffer_initialization(self, collector):
        """Test that metrics buffer is properly initialized."""
        assert isinstance(collector._metrics_buffer, defaultdict)
        assert len(collector._metrics_buffer) == 0

    def test_retention_period_setting(self, collector):
        """Test that retention period is properly set."""
        assert collector.retention_period == 300