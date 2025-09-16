"""
Test WebSocket Monitoring Implementation

This test module validates the comprehensive WebSocket monitoring system,
including metrics collection, dashboard functionality, and factory integration.

BUSINESS VALUE:
- Ensure monitoring accurately tracks event delivery
- Validate per-user metric isolation
- Confirm dashboard provides real-time insights
- Test factory integration doesn't impact performance
"""
import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.monitoring.websocket_metrics import WebSocketMetricsCollector, get_websocket_metrics_collector, reset_metrics_collector, record_websocket_event, record_websocket_connection, record_websocket_queue, record_factory_event, get_user_websocket_metrics, get_all_websocket_metrics, export_metrics_prometheus
from netra_backend.app.monitoring.websocket_dashboard import WebSocketDashboard, get_websocket_dashboard, DashboardView

class TestWebSocketMetrics:
    """Test WebSocket metrics collection."""

    def setup_method(self):
        """Reset metrics collector before each test."""
        reset_metrics_collector()
        self.collector = get_websocket_metrics_collector()

    def test_event_metrics_recording(self):
        """Test that events are properly recorded with metrics."""
        user_id = 'test_user_123'
        for i in range(5):
            record_websocket_event(user_id=user_id, event_type='agent_started', latency_ms=10.5 + i, success=True)
        for i in range(2):
            record_websocket_event(user_id=user_id, event_type='agent_completed', latency_ms=100.0, success=False)
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['user_id'] == user_id
        assert metrics['events']['sent'] == 5
        assert metrics['events']['failed'] == 2
        assert metrics['events']['success_rate'] == pytest.approx(71.43, 0.01)
        assert metrics['events']['by_type']['agent_started'] == 5
        assert metrics['events']['failures_by_type']['agent_completed'] == 2
        percentiles = metrics['events']['latency_percentiles']
        assert percentiles['p50'] > 0
        assert percentiles['p99'] > percentiles['p50']

    def test_connection_pool_metrics(self):
        """Test connection pool metrics tracking."""
        user_id = 'test_user_456'
        record_websocket_connection(user_id, 'created')
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['connections']['active'] == 1
        assert metrics['connections']['total_created'] == 1
        assert metrics['connections']['health'] == 'healthy'
        record_websocket_connection(user_id, 'closed', lifetime_seconds=120.5)
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['connections']['active'] == 0
        assert metrics['connections']['total_closed'] == 1
        for _ in range(3):
            record_websocket_connection(user_id, 'error')
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['connections']['errors'] == 3
        assert metrics['connections']['health'] == 'degraded'

    def test_queue_metrics(self):
        """Test queue operation metrics."""
        user_id = 'test_user_789'
        for i in range(10):
            record_websocket_queue(user_id, 'enqueue', queue_size=i + 1)
        for i in range(5):
            record_websocket_queue(user_id, 'dequeue', processing_time_ms=5.0 + i)
        record_websocket_queue(user_id, 'backpressure')
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['queues']['current_size'] == 5
        assert metrics['queues']['max_size'] == 10
        assert metrics['queues']['total_processed'] == 5
        assert metrics['queues']['backpressure_events'] == 1

    def test_factory_metrics(self):
        """Test factory lifecycle metrics."""
        for _ in range(3):
            record_factory_event('created')
        record_factory_event('destroyed')
        all_metrics = get_all_websocket_metrics()
        factory_metrics = all_metrics['system']['factory_metrics']['factories']
        assert factory_metrics['created'] == 3
        assert factory_metrics['destroyed'] == 1
        assert factory_metrics['active'] == 2

    def test_isolation_violation_tracking(self):
        """Test that isolation violations are tracked as critical."""
        record_factory_event('isolation_violation')
        all_metrics = get_all_websocket_metrics()
        isolation_metrics = all_metrics['system']['factory_metrics']['isolation']
        assert isolation_metrics['violations'] == 1

    def test_multi_user_isolation(self):
        """Test that metrics are properly isolated between users."""
        user1 = 'user_alpha'
        user2 = 'user_beta'
        record_websocket_event(user1, 'agent_started', 10.0, True)
        record_websocket_event(user2, 'agent_started', 20.0, True)
        record_websocket_event(user1, 'agent_completed', 15.0, False)
        metrics1 = get_user_websocket_metrics(user1)
        assert metrics1['events']['sent'] == 1
        assert metrics1['events']['failed'] == 1
        metrics2 = get_user_websocket_metrics(user2)
        assert metrics2['events']['sent'] == 1
        assert metrics2['events']['failed'] == 0
        assert metrics1['user_id'] != metrics2['user_id']

    def test_prometheus_export(self):
        """Test Prometheus metrics export format."""
        record_websocket_event('user1', 'test', 10.0, True)
        record_factory_event('created')
        prometheus_output = export_metrics_prometheus()
        assert '# HELP websocket_uptime_hours' in prometheus_output
        assert '# TYPE websocket_uptime_hours gauge' in prometheus_output
        assert 'websocket_uptime_hours' in prometheus_output
        assert 'websocket_total_users' in prometheus_output
        assert 'websocket_factories_active' in prometheus_output

    def test_metrics_cleanup(self):
        """Test that user metrics can be cleaned up."""
        user_id = 'cleanup_user'
        record_websocket_event(user_id, 'test', 10.0, True)
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['events']['sent'] == 1
        self.collector.clear_user_metrics(user_id)
        metrics = get_user_websocket_metrics(user_id)
        assert metrics['events']['sent'] == 0

class TestWebSocketDashboard:
    """Test WebSocket dashboard functionality."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard instance."""
        return get_websocket_dashboard()

    @pytest.mark.asyncio
    async def test_dashboard_system_health_widget(self, dashboard):
        """Test system health widget generation."""
        record_websocket_event('user1', 'test', 10.0, True)
        record_factory_event('created')
        widget = dashboard.get_system_health_widget()
        assert widget.id == 'system_health'
        assert widget.type == 'metric'
        assert 'status' in widget.data
        assert 'uptime_hours' in widget.data
        assert 'total_users' in widget.data
        assert widget.data['total_users'] >= 1

    @pytest.mark.asyncio
    async def test_dashboard_event_rate_widget(self, dashboard):
        """Test event rate chart widget."""
        for i in range(10):
            record_websocket_event(f'user{i}', 'test', 10.0, True)
        widget = dashboard.get_event_rate_widget()
        assert widget.id == 'event_rate'
        assert widget.type == 'chart'
        assert widget.data['chart_type'] == 'line'
        assert 'series' in widget.data
        assert len(widget.data['series']) == 2

    @pytest.mark.asyncio
    async def test_dashboard_success_rate_widget(self, dashboard):
        """Test success rate chart widget."""
        record_websocket_event('user1', 'test', 10.0, True)
        record_websocket_event('user1', 'test', 10.0, False)
        record_websocket_event('user2', 'test', 10.0, True)
        widget = dashboard.get_success_rate_widget()
        assert widget.id == 'success_rate'
        assert widget.type == 'chart'
        assert widget.data['chart_type'] == 'bar'
        assert 'system_average' in widget.data

    @pytest.mark.asyncio
    async def test_dashboard_active_users_widget(self, dashboard):
        """Test active users table widget."""
        for i in range(3):
            user_id = f'user_{i}'
            record_websocket_event(user_id, 'test', 10.0, True)
            record_websocket_connection(user_id, 'created')
        widget = dashboard.get_active_users_widget()
        assert widget.id == 'active_users'
        assert widget.type == 'table'
        assert 'columns' in widget.data
        assert 'rows' in widget.data
        assert len(widget.data['rows']) >= 3

    @pytest.mark.asyncio
    async def test_dashboard_latency_widget(self, dashboard):
        """Test latency distribution widget."""
        latencies = [5.0, 10.0, 50.0, 100.0, 500.0]
        for latency in latencies:
            record_websocket_event('user1', 'test', latency, True)
        widget = dashboard.get_latency_distribution_widget()
        assert widget.id == 'latency_distribution'
        assert widget.type == 'chart'
        assert 'percentiles' in widget.data
        assert 'p50' in widget.data['percentiles']
        assert 'p99' in widget.data['percentiles']

    @pytest.mark.asyncio
    async def test_dashboard_data_views(self, dashboard):
        """Test different dashboard views."""
        data = await dashboard.get_dashboard_data(DashboardView.OVERVIEW)
        assert data['view'] == 'overview'
        assert len(data['widgets']) > 0
        data = await dashboard.get_dashboard_data(DashboardView.CONNECTIONS)
        assert data['view'] == 'connections'
        data = await dashboard.get_dashboard_data(DashboardView.EVENTS)
        assert data['view'] == 'events'

class TestMonitoringIntegration:
    """Test integration with WebSocket factories."""

    @pytest.mark.asyncio
    async def test_factory_monitoring_integration(self):
        """Test that factory properly integrates with monitoring."""
        from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, UserWebSocketContext
        factory = WebSocketBridgeFactory()
        user_context = UserWebSocketContext(user_id='integration_test_user', thread_id='thread_123', connection_id='conn_456')
        emitter = await factory.get_or_create_user_emitter(user_id=user_context.user_id, thread_id=user_context.thread_id, session_id='session_789')
        all_metrics = get_all_websocket_metrics()
        factory_metrics = all_metrics['system']['factory_metrics']['factories']
        assert factory_metrics['created'] > 0
        await emitter.notify_agent_started('TestAgent', 'run_123')
        await asyncio.sleep(0.1)
        user_metrics = get_user_websocket_metrics(user_context.user_id)
        assert user_context.user_id in str(user_metrics)
        await emitter.cleanup()
        all_metrics = get_all_websocket_metrics()
        factory_metrics = all_metrics['system']['factory_metrics']['factories']
        assert factory_metrics['destroyed'] > 0

    @pytest.mark.asyncio
    async def test_monitoring_performance_impact(self):
        """Test that monitoring doesn't significantly impact performance."""
        import time
        reset_metrics_collector()
        start_time = time.time()
        for i in range(1000):
            record_websocket_event(f'user_{i % 10}', 'test', 10.0, True)
        monitoring_time = time.time() - start_time
        assert monitoring_time < 0.1
        all_metrics = get_all_websocket_metrics()
        assert all_metrics['system']['total_events'] == 1000
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')