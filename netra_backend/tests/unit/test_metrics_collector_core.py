"""Core unit tests for MetricsCollector.

Tests customer usage tracking for accurate billing calculations.
CRITICAL for revenue accuracy - prevents under/overcharging customers.

Business Value: Ensures precise usage metrics collection for billing,
preventing revenue loss and customer disputes.
"""

from netra_backend.app.monitoring.performance_monitor import PerformanceMonitor as PerformanceMetric
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.monitoring.metrics_collector import (

    DatabaseMetrics,

    MetricsCollector,

    PerformanceMetric,

    SystemResourceMetrics,

    WebSocketMetrics,

)

class TestMetricsCollectorCore:

    """Core test suite for MetricsCollector billing accuracy."""
    
    @pytest.fixture

    def collector(self):

        """Create metrics collector with minimal retention."""

        return MetricsCollector(retention_period=300)  # 5 minutes for testing
    
    @pytest.fixture

    def sample_metric(self):

        """Create sample performance metric."""

        return PerformanceMetric(

            name="test.metric", value=42.5, timestamp=datetime.now(),

            tags={"component": "test"}, unit="ms"

        )
    
    @pytest.fixture

    def system_metrics(self):

        """Create sample system resource metrics."""

        return SystemResourceMetrics(

            cpu_percent=45.2, memory_percent=67.8, memory_available_mb=2048.0,

            disk_io_read_mb=15.3, disk_io_write_mb=8.7, network_bytes_sent=1024,

            network_bytes_recv=2048, active_connections=25

        )
    
    async def test_start_collection_creates_tasks(self, collector):

        """Test that start_collection creates required background tasks."""

        await collector.start_collection()
        
        assert len(collector._collection_tasks) == 5

        assert all(isinstance(task, asyncio.Task) for task in collector._collection_tasks)
        
        await collector.stop_collection()
    
    async def test_stop_collection_cancels_tasks(self, collector):

        """Test that stop_collection properly cancels all tasks."""

        await collector.start_collection()

        initial_task_count = len(collector._collection_tasks)
        
        await collector.stop_collection()
        
        assert collector._shutdown is True

        assert initial_task_count == 5
    
    @patch('app.monitoring.metrics_collector.psutil')

    def test_gather_system_metrics_success(self, mock_psutil, collector):

        """Test successful system metrics gathering."""

        self._setup_mock_psutil_success(mock_psutil)
        
        metrics = collector._gather_system_metrics()
        
        assert isinstance(metrics, SystemResourceMetrics)

        assert metrics.cpu_percent == 25.5

        assert metrics.memory_percent == 60.0

        assert metrics.active_connections == 10
    
    @patch('app.monitoring.metrics_collector.psutil')

    def test_gather_system_metrics_with_none_values(self, mock_psutil, collector):

        """Test system metrics gathering with None disk/network counters."""

        self._setup_mock_psutil_none_values(mock_psutil)
        
        metrics = collector._gather_system_metrics()
        
        assert metrics.disk_io_read_mb == 0

        assert metrics.disk_io_write_mb == 0

        assert metrics.network_bytes_sent == 0

        assert metrics.network_bytes_recv == 0
    
    def test_record_system_metrics(self, collector, system_metrics):

        """Test recording system metrics to buffer."""

        collector._record_system_metrics(system_metrics)
        
        assert len(collector._metrics_buffer["system_resources"]) == 1

        assert len(collector._metrics_buffer["system.cpu_percent"]) == 1

        assert len(collector._metrics_buffer["system.memory_percent"]) == 1

        assert collector._metrics_buffer["system.cpu_percent"][0].value == 45.2
    
    @patch('app.monitoring.metrics_collector.get_pool_status')

    @patch('app.monitoring.metrics_collector.performance_manager')

    def test_gather_database_metrics_success(self, mock_perf_manager, mock_pool_status, collector):

        """Test successful database metrics gathering."""

        self._setup_mock_database_data(mock_pool_status, mock_perf_manager)
        
        metrics = collector._gather_database_metrics()
        
        assert isinstance(metrics, DatabaseMetrics)

        assert metrics.active_connections == 8

        assert metrics.pool_size == 18

        assert metrics.total_queries == 1000

        assert metrics.cache_hit_rate == 0.85
    
    def test_record_database_metrics(self, collector):

        """Test recording database metrics to buffer."""

        db_metrics = self._create_test_database_metrics()
        
        collector._record_database_metrics(db_metrics)
        
        assert len(collector._metrics_buffer["database_metrics"]) == 1

        assert len(collector._metrics_buffer["database.active_connections"]) == 1

        assert collector._metrics_buffer["database.cache_hit_ratio"][0].value == 0.92
    
    @patch('app.monitoring.metrics_collector.get_connection_manager')

    async def test_gather_websocket_metrics_success(self, mock_get_manager, collector):

        """Test successful WebSocket metrics gathering."""

        mock_manager = self._create_mock_websocket_manager()

        mock_get_manager.return_value = mock_manager
        
        metrics = await collector._gather_websocket_metrics()
        
        assert isinstance(metrics, WebSocketMetrics)

        assert metrics.active_connections == 25

        assert metrics.total_connections == 150
    
    def test_record_websocket_metrics(self, collector):

        """Test recording WebSocket metrics to buffer."""

        websocket_metrics = self._create_test_websocket_metrics()
        
        collector._record_websocket_metrics(websocket_metrics)
        
        assert len(collector._metrics_buffer["websocket_metrics"]) == 1

        assert len(collector._metrics_buffer["websocket.active_connections"]) == 1

        efficiency_metric = collector._metrics_buffer["websocket.connection_efficiency"][0]

        assert efficiency_metric.value == 0.15  # 15/100
    
    @patch('app.monitoring.metrics_collector.gc')

    def test_gather_memory_metrics(self, mock_gc, collector):

        """Test gathering Python memory metrics."""

        mock_gc.get_count.return_value = (100, 10, 2)
        
        collector._gather_and_record_memory_metrics()
        
        assert len(collector._metrics_buffer["memory.gc_generation_0"]) == 1

        assert len(collector._metrics_buffer["memory.gc_generation_1"]) == 1

        assert len(collector._metrics_buffer["memory.gc_generation_2"]) == 1

        assert collector._metrics_buffer["memory.gc_generation_0"][0].value == 100
    
    @patch('app.monitoring.metrics_collector.time.time')

    @patch('app.monitoring.metrics_collector.gc.collect')

    def test_periodic_gc_triggered(self, mock_collect, mock_time, collector):

        """Test periodic garbage collection is triggered."""

        mock_time.return_value = 300.0  # Trigger GC condition

        mock_collect.return_value = 42

        collector._collection_interval = 10
        
        collector._perform_periodic_gc()
        
        mock_collect.assert_called_once()

        assert len(collector._metrics_buffer["memory.gc_collected"]) == 1
    
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
    
    # Helper methods (each ≤8 lines)

    def _setup_mock_psutil_success(self, mock_psutil):

        """Helper to setup successful psutil mock."""

        mock_psutil.cpu_percent.return_value = 25.5

        mock_psutil.virtual_memory.return_value = Mock(percent=60.0, available=4096 * 1024 * 1024)

        mock_psutil.disk_io_counters.return_value = Mock(read_bytes=1024 * 1024, write_bytes=512 * 1024)

        mock_psutil.net_io_counters.return_value = Mock(bytes_sent=2048, bytes_recv=4096)

        mock_psutil.net_connections.return_value = [Mock()] * 10
    
    def _setup_mock_psutil_none_values(self, mock_psutil):

        """Helper to setup psutil mock with None values."""

        mock_psutil.cpu_percent.return_value = 15.0

        mock_psutil.virtual_memory.return_value = Mock(percent=30.0, available=8192 * 1024 * 1024)

        mock_psutil.disk_io_counters.return_value = None

        mock_psutil.net_io_counters.return_value = None

        mock_psutil.net_connections.return_value = []
    
    def _setup_mock_database_data(self, mock_pool_status, mock_perf_manager):

        """Helper to setup database mock data."""

        mock_pool_status.return_value = {

            "sync": {"total": 5, "size": 10, "overflow": 2},

            "async": {"total": 3, "size": 8, "overflow": 1}

        }

        mock_perf_manager.get_performance_stats.return_value = {

            "query_optimizer": {"total_queries": 1000, "slow_queries": 15},

            "cache_stats": {"total_hits": 850, "size": 1000}

        }
    
    def _create_test_database_metrics(self):

        """Helper to create test database metrics."""

        return DatabaseMetrics(

            active_connections=10, pool_size=20, pool_overflow=2,

            total_queries=500, avg_query_time=25.5, slow_queries=5,

            cache_hit_rate=0.92

        )
    
    def _create_mock_websocket_manager(self):

        """Helper to create mock WebSocket manager."""

        mock_manager = Mock()

        mock_manager.get_stats = AsyncMock(return_value={

            "active_connections": 25, "total_connections": 150

        })

        return mock_manager
    
    def _create_test_websocket_metrics(self):

        """Helper to create test WebSocket metrics."""

        return WebSocketMetrics(

            active_connections=15, total_connections=100, messages_sent=500,

            messages_received=450, failed_sends=2, avg_message_size=256.5,

            batch_efficiency=0.95

        )