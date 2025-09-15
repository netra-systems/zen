"""Unit tests for monitoring interface and ChatEventMonitor component auditing.

Business Value: Validates that monitoring integration works correctly while
maintaining component independence, ensuring reliable silent failure detection.

Test Coverage:
- MonitorableComponent interface compliance
- ChatEventMonitor component registration and auditing  
- Independent operation (components work without monitors)
- Integration operation (monitors can audit components)
- Error handling and graceful degradation
"""
import pytest
import asyncio
import time
from typing import Dict, Any, List
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment
from shared.monitoring.interfaces import MonitorableComponent, ComponentMonitor, HealthStatus, MonitoringMetrics
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor

class MockMonitorableComponent(MonitorableComponent):
    """Mock component implementing MonitorableComponent for testing."""

    def __init__(self, component_id: str='test_component'):
        self.component_id = component_id
        self.healthy = True
        self.state = 'running'
        self.error_message = None
        self.observers: List[ComponentMonitor] = []
        self.metrics = {'total_operations': 100, 'successful_operations': 95, 'failed_operations': 5, 'success_rate': 0.95, 'uptime_seconds': 3600}
        self.health_check_count = 0
        self.metrics_request_count = 0

    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        self.health_check_count += 1
        return {'healthy': self.healthy, 'state': self.state, 'timestamp': time.time(), 'error_message': self.error_message, 'component_id': self.component_id, 'health_check_count': self.health_check_count}

    async def get_metrics(self) -> Dict[str, Any]:
        """Get operational metrics."""
        self.metrics_request_count += 1
        return {**self.metrics, 'metrics_request_count': self.metrics_request_count, 'timestamp': time.time()}

    def register_monitor_observer(self, observer: ComponentMonitor) -> None:
        """Register monitor observer."""
        if observer not in self.observers:
            self.observers.append(observer)

    def remove_monitor_observer(self, observer: ComponentMonitor) -> None:
        """Remove monitor observer."""
        if observer in self.observers:
            self.observers.remove(observer)

    async def simulate_health_change(self, healthy: bool, state: str, error: str=None):
        """Simulate a health change for testing."""
        self.healthy = healthy
        self.state = state
        self.error_message = error
        health_data = {'healthy': healthy, 'state': state, 'error_message': error, 'timestamp': time.time()}
        for observer in self.observers:
            try:
                await observer.on_component_health_change(self.component_id, health_data)
            except Exception:
                pass

class TestMonitoringInterfaces:
    """Test monitoring interface abstractions."""

    def test_health_status_creation(self):
        """Test HealthStatus helper class."""
        healthy = HealthStatus.healthy_status('running')
        assert healthy.healthy is True
        assert healthy.state == 'running'
        assert healthy.error_message is None
        assert isinstance(healthy.timestamp, float)
        unhealthy = HealthStatus.unhealthy_status('failed', 'Service crashed')
        assert unhealthy.healthy is False
        assert unhealthy.state == 'failed'
        assert unhealthy.error_message == 'Service crashed'
        health_dict = healthy.to_dict()
        assert health_dict['healthy'] is True
        assert health_dict['state'] == 'running'
        assert 'timestamp' in health_dict

    def test_monitoring_metrics(self):
        """Test MonitoringMetrics helper class."""
        metrics = MonitoringMetrics()
        metrics.increment_counter('requests')
        metrics.increment_counter('requests', 5)
        assert metrics.get_counter('requests') == 6
        assert metrics.get_counter('nonexistent') == 0
        metrics.set_gauge('cpu_usage', 75.5)
        assert metrics.get_gauge('cpu_usage') == 75.5
        assert metrics.get_gauge('nonexistent') == 0.0
        metrics.record_timer('response_time', 1.5)
        metrics.record_timer('response_time', 2.0)
        metrics.record_timer('response_time', 1.0)
        stats = metrics.get_timer_stats('response_time')
        assert stats['count'] == 3
        assert stats['avg'] == 1.5
        assert stats['min'] == 1.0
        assert stats['max'] == 2.0
        metrics_dict = metrics.to_dict()
        assert 'counters' in metrics_dict
        assert 'gauges' in metrics_dict
        assert 'timers' in metrics_dict
        assert 'timestamps' in metrics_dict

class TestMockComponent:
    """Test our mock component implementation."""

    @pytest.mark.asyncio
    async def test_mock_component_basic_functionality(self):
        """Test mock component implements interface correctly."""
        component = MockMonitorableComponent('test_comp')
        health = await component.get_health_status()
        assert health['healthy'] is True
        assert health['state'] == 'running'
        assert health['component_id'] == 'test_comp'
        assert health['health_check_count'] == 1
        metrics = await component.get_metrics()
        assert metrics['total_operations'] == 100
        assert metrics['success_rate'] == 0.95
        assert metrics['metrics_request_count'] == 1
        mock_observer = MagicNone
        component.register_monitor_observer(mock_observer)
        assert mock_observer in component.observers
        component.remove_monitor_observer(mock_observer)
        assert mock_observer not in component.observers

    @pytest.mark.asyncio
    async def test_mock_component_health_changes(self):
        """Test mock component can simulate health changes."""
        component = MockMonitorableComponent('test_comp')
        observer = AsyncNone
        component.register_monitor_observer(observer)
        await component.simulate_health_change(False, 'failed', 'Test error')
        health = await component.get_health_status()
        assert health['healthy'] is False
        assert health['state'] == 'failed'
        assert health['error_message'] == 'Test error'
        observer.on_component_health_change.assert_called_once()
        call_args = observer.on_component_health_change.call_args
        assert call_args[0][0] == 'test_comp'
        assert call_args[0][1]['healthy'] is False

class TestChatEventMonitorComponentAuditing:
    """Test ChatEventMonitor's new component auditing capabilities."""

    def test_monitor_implements_component_monitor_interface(self):
        """Test ChatEventMonitor properly implements ComponentMonitor interface."""
        monitor = ChatEventMonitor()
        assert isinstance(monitor, ComponentMonitor)
        assert hasattr(monitor, 'monitored_components')
        assert hasattr(monitor, 'component_health_history')
        assert hasattr(monitor, 'bridge_audit_metrics')
        assert isinstance(monitor.monitored_components, dict)
        assert len(monitor.monitored_components) == 0

    @pytest.mark.asyncio
    async def test_component_registration_success(self):
        """Test successful component registration for monitoring."""
        monitor = ChatEventMonitor()
        component = MockMonitorableComponent('bridge_1')
        await monitor.register_component_for_monitoring('bridge_1', component)
        assert 'bridge_1' in monitor.monitored_components
        assert monitor.monitored_components['bridge_1'] is component
        assert monitor in component.observers
        assert len(monitor.component_health_history['bridge_1']) > 0

    @pytest.mark.asyncio
    async def test_component_registration_with_failure(self):
        """Test component registration handles failures gracefully."""
        monitor = ChatEventMonitor()
        failing_component = MagicMock(spec=MonitorableComponent)
        failing_component.register_monitor_observer.side_effect = Exception('Registration failed')
        failing_component.get_health_status = AsyncMock(return_value={'healthy': True})
        failing_component.get_metrics = AsyncMock(return_value={})
        await monitor.register_component_for_monitoring('failing_comp', failing_component)
        assert 'failing_comp' not in monitor.monitored_components

    @pytest.mark.asyncio
    async def test_bridge_health_audit_comprehensive(self):
        """Test comprehensive bridge health audit functionality."""
        monitor = ChatEventMonitor()
        component = MockMonitorableComponent('test_bridge')
        await monitor.register_component_for_monitoring('test_bridge', component)
        audit_result = await monitor.audit_bridge_health('test_bridge')
        assert audit_result['bridge_id'] == 'test_bridge'
        assert 'audit_timestamp' in audit_result
        assert 'internal_health' in audit_result
        assert 'internal_metrics' in audit_result
        assert 'event_monitor_validation' in audit_result
        assert 'integration_health' in audit_result
        assert 'overall_assessment' in audit_result
        internal_health = audit_result['internal_health']
        assert internal_health['healthy'] is True
        assert internal_health['state'] == 'running'
        assert internal_health['component_id'] == 'test_bridge'
        internal_metrics = audit_result['internal_metrics']
        assert internal_metrics['total_operations'] == 100
        assert internal_metrics['success_rate'] == 0.95
        overall = audit_result['overall_assessment']
        assert 'overall_score' in overall
        assert 'overall_status' in overall
        assert 'component_scores' in overall
        assert overall['overall_score'] > 0

    @pytest.mark.asyncio
    async def test_audit_unregistered_component(self):
        """Test audit of unregistered component returns appropriate response."""
        monitor = ChatEventMonitor()
        result = await monitor.audit_bridge_health('nonexistent')
        assert result['status'] == 'not_monitored'
        assert result['bridge_id'] == 'nonexistent'
        assert 'message' in result

    @pytest.mark.asyncio
    async def test_health_change_notification_handling(self):
        """Test monitor properly handles health change notifications."""
        monitor = ChatEventMonitor()
        component = MockMonitorableComponent('notifying_comp')
        await monitor.register_component_for_monitoring('notifying_comp', component)
        await component.simulate_health_change(False, 'degraded', 'Performance issues')
        history = monitor.component_health_history['notifying_comp']
        health_notifications = [h for h in history if h.get('notification_type') == 'health_change']
        assert len(health_notifications) > 0
        latest_notification = health_notifications[-1]
        assert latest_notification['component_id'] == 'notifying_comp'
        assert latest_notification['health_data']['healthy'] is False
        assert latest_notification['health_data']['state'] == 'degraded'

    @pytest.mark.asyncio
    async def test_component_removal_from_monitoring(self):
        """Test component can be removed from monitoring."""
        monitor = ChatEventMonitor()
        component = MockMonitorableComponent('removable_comp')
        await monitor.register_component_for_monitoring('removable_comp', component)
        assert 'removable_comp' in monitor.monitored_components
        assert monitor in component.observers
        await monitor.remove_component_from_monitoring('removable_comp')
        assert 'removable_comp' not in monitor.monitored_components
        assert monitor not in component.observers
        assert 'removable_comp' in monitor.component_health_history

    def test_component_audit_summary(self):
        """Test comprehensive audit summary generation."""
        monitor = ChatEventMonitor()
        summary = monitor.get_component_audit_summary()
        assert summary['total_monitored_components'] == 0
        assert summary['overall_system_health'] == 'no_monitored_components'
        assert summary['healthy_component_ratio'] == '0/0'

    @pytest.mark.asyncio
    async def test_component_audit_summary_with_components(self):
        """Test audit summary with registered components."""
        monitor = ChatEventMonitor()
        comp1 = MockMonitorableComponent('comp1')
        comp2 = MockMonitorableComponent('comp2')
        await monitor.register_component_for_monitoring('comp1', comp1)
        await monitor.register_component_for_monitoring('comp2', comp2)
        await comp2.simulate_health_change(False, 'failed', 'Test failure')
        summary = monitor.get_component_audit_summary()
        assert summary['total_monitored_components'] == 2
        assert 'comp1' in summary['components']
        assert 'comp2' in summary['components']
        assert summary['overall_system_health'] in ['warning', 'critical']
        assert '1/' in summary['healthy_component_ratio'] or '2/' in summary['healthy_component_ratio']

class TestMonitorIndependence:
    """Test that monitor works independently without registered components."""

    def test_monitor_starts_without_components(self):
        """Test monitor initializes and works without any components."""
        monitor = ChatEventMonitor()
        assert len(monitor.monitored_components) == 0
        assert monitor.get_component_audit_summary() is not None
        assert hasattr(monitor, 'event_counts')
        assert hasattr(monitor, 'silent_failures')

    @pytest.mark.asyncio
    async def test_monitor_health_check_without_components(self):
        """Test monitor health check works without registered components."""
        monitor = ChatEventMonitor()
        health_report = await monitor.check_health()
        assert 'status' in health_report
        assert 'healthy' in health_report
        assert 'issues' in health_report
        assert 'metrics' in health_report

    @pytest.mark.asyncio
    async def test_audit_methods_handle_empty_state(self):
        """Test audit methods work correctly when no components registered."""
        monitor = ChatEventMonitor()
        result = await monitor.audit_bridge_health('nonexistent')
        assert result['status'] == 'not_monitored'
        summary = monitor.get_component_audit_summary()
        assert summary['total_monitored_components'] == 0
        await monitor.on_component_health_change('unknown', {'healthy': True})

class TestComponentIndependence:
    """Test that components work independently without monitors."""

    @pytest.mark.asyncio
    async def test_component_works_without_monitors(self):
        """Test component functions normally without any registered monitors."""
        component = MockMonitorableComponent('independent_comp')
        health = await component.get_health_status()
        assert health['healthy'] is True
        metrics = await component.get_metrics()
        assert metrics['total_operations'] == 100
        await component.simulate_health_change(False, 'degraded', 'Test')
        health_after = await component.get_health_status()
        assert health_after['healthy'] is False

    def test_component_observer_management_handles_empty_state(self):
        """Test component observer management works with no observers."""
        component = MockMonitorableComponent('independent_comp')
        assert len(component.observers) == 0
        mock_observer = MagicNone
        component.remove_monitor_observer(mock_observer)
        assert len(component.observers) == 0

class TestIntegrationScenarios:
    """Test integration scenarios demonstrating both independence and cooperation."""

    @pytest.mark.asyncio
    async def test_full_integration_scenario(self):
        """Test complete integration scenario from registration to audit."""
        monitor = ChatEventMonitor()
        bridge = MockMonitorableComponent('main_bridge')
        initial_health = await bridge.get_health_status()
        assert initial_health['healthy'] is True
        initial_monitor_health = await monitor.check_health()
        assert 'status' in initial_monitor_health
        await monitor.register_component_for_monitoring('main_bridge', bridge)
        assert 'main_bridge' in monitor.monitored_components
        assert monitor in bridge.observers
        audit_result = await monitor.audit_bridge_health('main_bridge')
        assert audit_result['bridge_id'] == 'main_bridge'
        assert audit_result['overall_assessment']['overall_status'] == 'healthy'
        await bridge.simulate_health_change(False, 'critical', 'System failure')
        history = monitor.component_health_history['main_bridge']
        health_changes = [h for h in history if h.get('notification_type') == 'health_change']
        assert len(health_changes) > 0
        latest_change = health_changes[-1]
        assert latest_change['health_data']['healthy'] is False
        assert latest_change['health_data']['state'] == 'critical'
        current_health = await bridge.get_health_status()
        assert current_health['state'] == 'critical'
        new_audit = await monitor.audit_bridge_health('main_bridge')
        assert new_audit['internal_health']['healthy'] is False
        assert new_audit['overall_assessment']['overall_status'] in ['critical', 'failed']

    @pytest.mark.asyncio
    async def test_integration_failure_graceful_degradation(self):
        """Test system gracefully degrades when integration fails."""
        monitor = ChatEventMonitor()
        failing_component = MagicMock(spec=MonitorableComponent)
        failing_component.register_monitor_observer = MagicNone
        failing_component.get_health_status = AsyncMock(side_effect=Exception('Health check failed'))
        failing_component.get_metrics = AsyncMock(side_effect=Exception('Metrics failed'))
        await monitor.register_component_for_monitoring('failing_bridge', failing_component)
        assert 'failing_bridge' in monitor.monitored_components
        audit_result = await monitor.audit_bridge_health('failing_bridge')
        assert audit_result['status'] == 'audit_failed'
        assert 'error' in audit_result
        monitor_health = await monitor.check_health()
        assert 'status' in monitor_health

    @pytest.mark.asyncio
    async def test_multiple_components_independent_failures(self):
        """Test multiple components where some fail independently."""
        monitor = ChatEventMonitor()
        good_component = MockMonitorableComponent('good_bridge')
        bad_component = MockMonitorableComponent('bad_bridge')
        await monitor.register_component_for_monitoring('good_bridge', good_component)
        await monitor.register_component_for_monitoring('bad_bridge', bad_component)
        await bad_component.simulate_health_change(False, 'failed', 'Simulated failure')
        good_audit = await monitor.audit_bridge_health('good_bridge')
        bad_audit = await monitor.audit_bridge_health('bad_bridge')
        assert good_audit['overall_assessment']['overall_status'] == 'healthy'
        assert bad_audit['internal_health']['healthy'] is False
        assert bad_audit['overall_assessment']['overall_status'] in ['critical', 'failed']
        summary = monitor.get_component_audit_summary()
        assert summary['total_monitored_components'] == 2
        assert summary['overall_system_health'] in ['warning', 'critical']
        assert '1/2' in summary['healthy_component_ratio']
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')