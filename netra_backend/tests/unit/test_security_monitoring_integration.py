"""
Unit tests for security monitoring integration.

Business Value: Platform/Internal - Security & Risk Reduction
Ensures security monitoring works correctly across system components.
"""
import pytest
from datetime import datetime, timezone
from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
try:
    from netra_backend.app.core.security_monitoring import SecurityMonitoringManager, detect_mock_token, log_security_event, check_and_alert_mock_token, get_security_metrics, SecurityEventType, SecurityEventSeverity
except ImportError:
    pytest.skip('Required modules have been removed or have missing dependencies', allow_module_level=True)

class SecurityMonitoringTests:
    """Test security monitoring functionality."""

    def test_mock_token_detection(self):
        """Test mock token detection patterns."""
        mock_tokens = ['mock_test_token_123', 'test_token_abc', 'fake_bearer_xyz', 'dummy_auth_token', 'dev_user_token_999', 'local_admin_token']
        for token in mock_tokens:
            assert detect_mock_token(token) is True, f'Should detect {token} as mock'
        valid_tokens = ['Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9', 'valid_production_token_xyz', 'prod_user_session_123', 'authenticated_bearer_token']
        for token in valid_tokens:
            assert detect_mock_token(token) is False, f'Should not detect {token} as mock'

    def test_security_event_logging(self):
        """Test security event logging with different severities."""
        monitor = SecurityMonitoringManager()
        event_details = {'message': 'Test security event', 'context': 'unit_test', 'user_id': 'test_user'}
        monitor.log_security_event(SecurityEventType.AUTHENTICATION_FAILURE, event_details, SecurityEventSeverity.HIGH)
        metrics = monitor.get_security_metrics()
        assert metrics['total_events'] >= 1
        assert metrics['events_by_type']['authentication_failure'] >= 1
        assert metrics['events_by_severity']['high'] >= 1

    def test_mock_token_alerting(self):
        """Test mock token alerting functionality."""
        monitor = SecurityMonitoringManager()
        mock_detected = monitor.check_and_alert_mock_token('mock_admin_token', 'unit_test')
        assert mock_detected is True
        metrics = monitor.get_security_metrics()
        assert metrics['mock_token_detections'] >= 1
        assert metrics['total_events'] >= 1

    def test_security_metrics_collection(self):
        """Test security metrics collection and formatting."""
        monitor = SecurityMonitoringManager()
        test_events = [(SecurityEventType.MOCK_TOKEN_DETECTED, {'context': 'test1'}, SecurityEventSeverity.CRITICAL), (SecurityEventType.AUTHENTICATION_FAILURE, {'context': 'test2'}, SecurityEventSeverity.HIGH), (SecurityEventType.RATE_LIMIT_EXCEEDED, {'context': 'test3'}, SecurityEventSeverity.MEDIUM)]
        for event_type, details, severity in test_events:
            monitor.log_security_event(event_type, details, severity)
        metrics = monitor.get_security_metrics()
        required_keys = ['total_events', 'events_by_type', 'events_by_severity', 'mock_token_detections', 'timestamp', 'alerting_enabled']
        for key in required_keys:
            assert key in metrics, f'Missing required metric key: {key}'
        assert isinstance(metrics['total_events'], int)
        assert isinstance(metrics['events_by_type'], dict)
        assert isinstance(metrics['events_by_severity'], dict)
        assert isinstance(metrics['alerting_enabled'], bool)

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test security monitoring health check."""
        monitor = SecurityMonitoringManager()
        health = await monitor.health_check()
        assert 'status' in health
        assert health['status'] in ['healthy', 'unhealthy']
        assert 'timestamp' in health
        if health['status'] == 'healthy':
            assert 'total_events_processed' in health
            assert 'alerting_enabled' in health
            assert isinstance(health['total_events_processed'], int)

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        monitor = SecurityMonitoringManager()
        event_type = SecurityEventType.AUTHENTICATION_FAILURE
        for i in range(20):
            monitor.log_security_event(event_type, {'message': f'Test event {i}', 'context': 'rate_limit_test'}, SecurityEventSeverity.MEDIUM)
        metrics = monitor.get_security_metrics()
        assert metrics['total_events'] > 0

    def test_convenience_functions(self):
        """Test convenience functions for easy integration."""
        assert detect_mock_token('mock_token_123') is True
        assert detect_mock_token('valid_token') is False
        initial_metrics = get_security_metrics()
        initial_count = initial_metrics.get('total_events', 0)
        log_security_event('test_event', {'test': 'data'}, 'low')
        updated_metrics = get_security_metrics()
        assert updated_metrics['total_events'] > initial_count
        result = check_and_alert_mock_token('mock_test_token', 'convenience_test')
        assert result is True

class SecurityMonitoringIntegrationTests:
    """Test security monitoring integration with system components."""

    def test_websocket_auth_integration(self):
        """Test that websocket auth properly integrates with security monitoring."""
        try:
            from netra_backend.app.websocket_core.auth import get_websocket_authenticator
            from netra_backend.app.core.security_monitoring import get_security_metrics
            authenticator = get_websocket_authenticator()
            assert authenticator is not None
            metrics = get_security_metrics()
            assert isinstance(metrics, dict)
        except ImportError as e:
            pytest.fail(f'Security monitoring integration import failed: {e}')

    def test_metrics_api_integration(self):
        """Test that metrics API properly integrates with security monitoring."""
        try:
            from netra_backend.app.routes.metrics_api import get_security_metrics_endpoint
            assert callable(get_security_metrics_endpoint)
        except ImportError as e:
            pytest.fail(f'Metrics API integration import failed: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')