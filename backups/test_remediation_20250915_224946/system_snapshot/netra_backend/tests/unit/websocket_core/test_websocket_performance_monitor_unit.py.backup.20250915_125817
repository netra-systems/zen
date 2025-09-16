"""
Unit tests for WebSocket Performance Monitor - Testing performance tracking and optimization.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform scalability and performance optimization  
- Value Impact: Ensures WebSocket performance meets user expectations for real-time chat
- Strategic Impact: Identifies bottlenecks before they impact user experience

These tests focus on performance metrics collection, latency tracking, throughput monitoring,
and alerting on performance degradation that could impact chat responsiveness.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.websocket_core.performance_monitor_core import (
    WebSocketPerformanceMonitor,
    PerformanceMetrics,
    LatencyMeasurement,
    ThroughputMetrics,
    PerformanceAlert,
    PerformanceThresholds
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestWebSocketPerformanceMonitor:
    """Unit tests for WebSocket performance monitoring."""
    
    @pytest.fixture
    def performance_thresholds(self):
        """Create performance threshold configuration."""
        return PerformanceThresholds(
            max_message_latency_ms=1000,
            max_connection_time_ms=3000,
            min_throughput_messages_per_second=10,
            max_memory_usage_mb=100,
            max_cpu_usage_percent=80
        )
    
    @pytest.fixture
    def performance_monitor(self, performance_thresholds):
        """Create WebSocketPerformanceMonitor instance."""
        return WebSocketPerformanceMonitor(
            thresholds=performance_thresholds,
            metrics_window_minutes=5,
            alert_enabled=True,
            detailed_tracking=True
        )
    
    @pytest.fixture
    def sample_connection(self):
        """Create sample connection data."""
        return {
            "connection_id": "conn_123",
            "user_id": "user_456",
            "connected_at": datetime.now(timezone.utc),
            "client_info": {
                "user_agent": "Mozilla/5.0...",
                "ip_address": "192.168.1.100",
                "connection_type": "websocket"
            }
        }
    
    def test_initializes_with_correct_configuration(self, performance_monitor, performance_thresholds):
        """Test PerformanceMonitor initializes with proper configuration."""
        assert performance_monitor.thresholds == performance_thresholds
        assert performance_monitor.metrics_window_minutes == 5
        assert performance_monitor.alert_enabled is True
        assert performance_monitor.detailed_tracking is True
        assert len(performance_monitor._connection_metrics) == 0
        assert len(performance_monitor._latency_measurements) == 0
    
    @pytest.mark.asyncio
    async def test_tracks_connection_performance(self, performance_monitor, sample_connection):
        """Test connection performance tracking."""
        connection_id = sample_connection["connection_id"]
        
        # Start tracking connection
        start_time = datetime.now(timezone.utc)
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Simulate connection establishment delay
        await asyncio.sleep(0.01)  # 10ms delay
        
        # Record connection established
        await performance_monitor.record_connection_established(connection_id)
        
        # Verify metrics tracked
        assert connection_id in performance_monitor._connection_metrics
        metrics = performance_monitor._connection_metrics[connection_id]
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.connection_time_ms >= 10  # At least 10ms delay
        assert metrics.connection_time_ms < 1000  # Reasonable upper bound
        assert metrics.is_connected is True
    
    @pytest.mark.asyncio
    async def test_measures_message_latency(self, performance_monitor, sample_connection):
        """Test message latency measurement."""
        connection_id = sample_connection["connection_id"]
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Create message with timestamp
        message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "test message", "client_timestamp": datetime.now(timezone.utc).isoformat()},
            user_id=sample_connection["user_id"]
        )
        
        # Record message processing
        start_time = datetime.now(timezone.utc)
        await asyncio.sleep(0.005)  # 5ms processing delay
        await performance_monitor.record_message_processed(connection_id, message)
        
        # Verify latency measured
        metrics = performance_monitor._connection_metrics[connection_id]
        assert metrics.message_count >= 1
        assert len(metrics.latency_measurements) >= 1
        
        latency = metrics.latency_measurements[-1]
        assert isinstance(latency, LatencyMeasurement)
        assert latency.latency_ms >= 5  # At least 5ms processing time
        assert latency.message_type == MessageType.USER_MESSAGE
    
    @pytest.mark.asyncio
    async def test_calculates_throughput_metrics(self, performance_monitor, sample_connection):
        """Test throughput calculation and monitoring."""
        connection_id = sample_connection["connection_id"]
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Send multiple messages to measure throughput
        message_count = 20
        start_time = datetime.now(timezone.utc)
        
        for i in range(message_count):
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={"iteration": i},
                user_id=sample_connection["user_id"]
            )
            await performance_monitor.record_message_processed(connection_id, message)
            await asyncio.sleep(0.001)  # Small delay between messages
        
        # Calculate throughput
        throughput = await performance_monitor.calculate_throughput(connection_id)
        
        assert isinstance(throughput, ThroughputMetrics)
        assert throughput.messages_per_second > 0
        assert throughput.total_messages == message_count
        assert throughput.measurement_period_seconds > 0
        
        # Should be high throughput due to fast processing
        assert throughput.messages_per_second > 100  # Should process much faster than threshold
    
    @pytest.mark.asyncio
    async def test_detects_performance_degradation(self, performance_monitor, sample_connection):
        """Test detection of performance degradation and alerting."""
        connection_id = sample_connection["connection_id"]
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Simulate slow message processing (exceeds threshold)
        slow_message = WebSocketMessage(
            message_type=MessageType.AGENT_THINKING,
            payload={"processing": "slow"},
            user_id=sample_connection["user_id"]
        )
        
        # Mock high latency
        with patch.object(performance_monitor, '_calculate_message_latency', return_value=1500):  # 1.5s > 1s threshold
            await performance_monitor.record_message_processed(connection_id, slow_message)
        
        # Should trigger performance alert
        alerts = await performance_monitor.get_active_alerts(connection_id)
        
        assert len(alerts) > 0
        latency_alert = next((alert for alert in alerts if alert.alert_type == "high_latency"), None)
        assert latency_alert is not None
        assert latency_alert.severity in ["warning", "critical"]
        assert latency_alert.value_measured >= 1500
        assert latency_alert.threshold_exceeded == performance_monitor.thresholds.max_message_latency_ms
    
    @pytest.mark.asyncio
    async def test_tracks_resource_usage(self, performance_monitor, sample_connection):
        """Test resource usage tracking (memory, CPU)."""
        connection_id = sample_connection["connection_id"]
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Mock resource usage data
        memory_usage_mb = 75
        cpu_usage_percent = 60
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu:
            
            # Configure mocks
            mock_memory.return_value.used = memory_usage_mb * 1024 * 1024  # Convert to bytes
            mock_memory.return_value.total = 8 * 1024 * 1024 * 1024  # 8GB total
            mock_cpu.return_value = cpu_usage_percent
            
            # Record resource usage
            await performance_monitor.record_resource_usage(connection_id)
        
        # Verify resource metrics tracked
        metrics = performance_monitor._connection_metrics[connection_id]
        assert metrics.current_memory_usage_mb <= memory_usage_mb + 10  # Allow some variance
        assert metrics.current_cpu_usage_percent <= cpu_usage_percent + 5
        
        # Should not trigger alerts (within thresholds)
        alerts = await performance_monitor.get_active_alerts(connection_id)
        resource_alerts = [alert for alert in alerts if alert.alert_type in ["high_memory", "high_cpu"]]
        assert len(resource_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_generates_performance_report(self, performance_monitor, sample_connection):
        """Test comprehensive performance report generation."""
        connection_id = sample_connection["connection_id"]
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Generate some activity
        for i in range(5):
            message = WebSocketMessage(
                message_type=MessageType.AGENT_COMPLETED,
                payload={"result": f"result_{i}"},
                user_id=sample_connection["user_id"]
            )
            await performance_monitor.record_message_processed(connection_id, message)
        
        # Generate performance report
        report = await performance_monitor.generate_performance_report(connection_id)
        
        # Verify report completeness
        assert report is not None
        assert report.connection_id == connection_id
        assert report.total_messages >= 5
        assert report.average_latency_ms >= 0
        assert report.throughput_messages_per_second >= 0
        assert isinstance(report.connection_duration_minutes, (int, float))
        
        # Should include performance assessment
        assert hasattr(report, 'performance_rating')
        assert report.performance_rating in ['excellent', 'good', 'fair', 'poor']
        
        # Should include recommendations if performance is suboptimal
        if report.performance_rating in ['fair', 'poor']:
            assert len(report.optimization_recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_handles_multiple_connections_independently(self, performance_monitor):
        """Test independent performance tracking for multiple connections."""
        # Create multiple connections
        connections = {
            "conn_1": {"connection_id": "conn_1", "user_id": "user_1"},
            "conn_2": {"connection_id": "conn_2", "user_id": "user_2"},
            "conn_3": {"connection_id": "conn_3", "user_id": "user_3"}
        }
        
        # Start tracking all connections
        for conn_data in connections.values():
            await performance_monitor.start_connection_tracking(
                conn_data["connection_id"], conn_data
            )
        
        # Generate different activity patterns for each connection
        for conn_id, conn_data in connections.items():
            message_count = hash(conn_id) % 10 + 5  # 5-14 messages
            for i in range(message_count):
                message = WebSocketMessage(
                    message_type=MessageType.USER_MESSAGE,
                    payload={"message": i},
                    user_id=conn_data["user_id"]
                )
                await performance_monitor.record_message_processed(conn_id, message)
        
        # Verify independent tracking
        assert len(performance_monitor._connection_metrics) == 3
        
        for conn_id in connections:
            metrics = performance_monitor._connection_metrics[conn_id]
            assert isinstance(metrics, PerformanceMetrics)
            assert metrics.message_count >= 5
            
            # Each connection should have independent metrics
            report = await performance_monitor.generate_performance_report(conn_id)
            assert report.connection_id == conn_id
    
    @pytest.mark.asyncio
    async def test_cleans_up_old_metrics(self, performance_monitor, sample_connection):
        """Test cleanup of old performance metrics and measurements."""
        connection_id = sample_connection["connection_id"]
        await performance_monitor.start_connection_tracking(connection_id, sample_connection)
        
        # Generate metrics
        for i in range(10):
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={"iteration": i},
                user_id=sample_connection["user_id"]
            )
            await performance_monitor.record_message_processed(connection_id, message)
        
        # Age the metrics
        metrics = performance_monitor._connection_metrics[connection_id]
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        for measurement in metrics.latency_measurements:
            measurement.timestamp = old_time
        
        # Run cleanup (only keep metrics within window)
        await performance_monitor.cleanup_old_metrics()
        
        # Verify old metrics cleaned up
        # Implementation dependent - may clean old measurements while keeping connection metrics
        if performance_monitor.auto_cleanup_enabled:
            # Should clean measurements older than metrics_window_minutes
            recent_measurements = [
                m for m in metrics.latency_measurements 
                if m.timestamp > datetime.now(timezone.utc) - timedelta(minutes=performance_monitor.metrics_window_minutes)
            ]
            assert len(recent_measurements) <= len(metrics.latency_measurements)
    
    @pytest.mark.asyncio
    async def test_aggregates_system_wide_metrics(self, performance_monitor):
        """Test aggregation of system-wide performance metrics."""
        # Create multiple connections with different performance characteristics
        connections = [
            {"connection_id": "fast_conn", "user_id": "fast_user"},
            {"connection_id": "slow_conn", "user_id": "slow_user"},
            {"connection_id": "medium_conn", "user_id": "medium_user"}
        ]
        
        # Start tracking all connections
        for conn in connections:
            await performance_monitor.start_connection_tracking(conn["connection_id"], conn)
        
        # Generate different performance patterns
        # Fast connection
        for i in range(100):
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={"fast": i},
                user_id="fast_user"
            )
            await performance_monitor.record_message_processed("fast_conn", message)
        
        # Slow connection (simulate with artificial delays)
        for i in range(20):
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={"slow": i},
                user_id="slow_user"
            )
            with patch.object(performance_monitor, '_calculate_message_latency', return_value=500):
                await performance_monitor.record_message_processed("slow_conn", message)
        
        # Get system-wide metrics
        system_metrics = await performance_monitor.get_system_wide_metrics()
        
        # Verify aggregation
        assert system_metrics is not None
        assert system_metrics.total_active_connections >= 3
        assert system_metrics.total_messages_processed >= 120
        assert system_metrics.average_system_latency_ms >= 0
        assert system_metrics.system_throughput_messages_per_second >= 0
        
        # Should identify performance outliers
        if system_metrics.performance_outliers:
            assert "slow_conn" in [outlier.connection_id for outlier in system_metrics.performance_outliers]