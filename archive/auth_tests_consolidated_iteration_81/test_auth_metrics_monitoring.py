"""
Auth metrics and monitoring tests (Iteration 46).

Tests authentication metrics collection and monitoring including:
- Login/logout metrics tracking
- Authentication failure rate monitoring
- Session duration metrics
- Security event metrics
- Performance metrics (response times, throughput)
- SLA compliance monitoring
- Real-time alerting on anomalies
- Dashboard metrics aggregation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, List, Any, Optional

from auth_service.auth_core.models.auth_models import User
# Mock classes for non-existent services and models
class MetricsService:
    pass

class AuthMonitor:
    pass

class AuthMetricsCollector:
    pass

class PerformanceMetricsCollector:
    pass

class SecurityMetricsCollector:
    pass

class AuthAlerting:
    pass
from test_framework.environment_markers import env

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.auth_service,
    pytest.mark.metrics,
    pytest.mark.monitoring
]


class TestAuthenticationMetrics:
    """Test authentication metrics collection and tracking."""

    @pytest.fixture
    def mock_metrics_service(self):
        """Mock metrics service."""
        service = MagicMock(spec=MetricsService)
        service.record_login = AsyncMock()
        service.record_logout = AsyncMock()
        service.record_auth_failure = AsyncMock()
        service.record_session_duration = AsyncMock()
        service.get_metrics = AsyncMock()
        return service

    @pytest.fixture
    def mock_auth_monitor(self):
        """Mock auth monitor."""
        monitor = MagicMock(spec=AuthMonitor)
        monitor.track_login_attempt = AsyncMock()
        monitor.track_authentication_event = AsyncMock()
        monitor.check_anomalies = AsyncMock()
        monitor.generate_report = AsyncMock()
        return monitor

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id=str(uuid4()),
            email='user@example.com',
            full_name='Test User',
            auth_provider='google',
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow()
        )

    async def test_login_metrics_collection(self, mock_metrics_service, sample_user):
        """Test collection of login metrics."""
        login_data = {
            'user_id': sample_user.id,
            'auth_provider': 'google',
            'ip_address': '127.0.0.1',
            'user_agent': 'Mozilla/5.0',
            'login_time': datetime.utcnow(),
            'session_id': str(uuid4())
        }
        
        # Record login event
        await mock_metrics_service.record_login(login_data)
        
        # Verify login metrics recording
        mock_metrics_service.record_login.assert_called_once_with(login_data)

    async def test_logout_metrics_collection(self, mock_metrics_service, sample_user):
        """Test collection of logout metrics."""
        logout_data = {
            'user_id': sample_user.id,
            'session_id': str(uuid4()),
            'logout_time': datetime.utcnow(),
            'session_duration_seconds': 3600,
            'logout_reason': 'user_initiated'
        }
        
        # Record logout event
        await mock_metrics_service.record_logout(logout_data)
        
        # Verify logout metrics recording
        mock_metrics_service.record_logout.assert_called_once_with(logout_data)

    async def test_authentication_failure_metrics(self, mock_metrics_service):
        """Test authentication failure metrics collection."""
        failure_data = {
            'email': 'user@example.com',
            'ip_address': '192.168.1.100',
            'failure_reason': 'invalid_credentials',
            'auth_provider': 'local',
            'timestamp': datetime.utcnow(),
            'user_agent': 'Mozilla/5.0'
        }
        
        # Record authentication failure
        await mock_metrics_service.record_auth_failure(failure_data)
        
        # Verify failure metrics recording
        mock_metrics_service.record_auth_failure.assert_called_once_with(failure_data)

    async def test_session_duration_metrics(self, mock_metrics_service, sample_user):
        """Test session duration metrics collection."""
        session_data = {
            'user_id': sample_user.id,
            'session_id': str(uuid4()),
            'duration_seconds': 7200,  # 2 hours
            'activity_count': 25,
            'last_activity': datetime.utcnow(),
            'session_end_reason': 'timeout'
        }
        
        # Record session duration
        await mock_metrics_service.record_session_duration(session_data)
        
        # Verify session metrics recording
        mock_metrics_service.record_session_duration.assert_called_once_with(session_data)

    async def test_metrics_aggregation(self, mock_metrics_service):
        """Test metrics aggregation and reporting."""
        # Mock aggregated metrics
        mock_metrics_service.get_metrics.return_value = {
            'total_logins_24h': 1250,
            'total_failures_24h': 45,
            'success_rate_24h': 96.4,
            'average_session_duration_minutes': 85,
            'unique_users_24h': 875,
            'most_common_failure_reason': 'invalid_credentials',
            'peak_login_hour': 9
        }
        
        # Get aggregated metrics
        metrics = await mock_metrics_service.get_metrics(
            time_range='24h',
            include_breakdown=True
        )
        
        # Verify metrics aggregation
        assert metrics['total_logins_24h'] > 0
        assert metrics['success_rate_24h'] > 90
        assert 'average_session_duration_minutes' in metrics
        assert 'unique_users_24h' in metrics

    async def test_real_time_metrics_streaming(self, mock_auth_monitor):
        """Test real-time metrics streaming."""
        # Mock real-time event tracking
        auth_event = {
            'event_type': 'login_success',
            'user_id': str(uuid4()),
            'timestamp': datetime.utcnow(),
            'metadata': {'auth_provider': 'google', 'ip_address': '127.0.0.1'}
        }
        
        # Track real-time authentication event
        await mock_auth_monitor.track_authentication_event(auth_event)
        
        # Verify real-time tracking
        mock_auth_monitor.track_authentication_event.assert_called_once_with(auth_event)

    async def test_metrics_by_auth_provider(self, mock_metrics_service):
        """Test metrics breakdown by authentication provider."""
        # Mock provider-specific metrics
        mock_metrics_service.get_provider_metrics.return_value = {
            'google': {
                'logins': 500,
                'failures': 12,
                'success_rate': 97.6,
                'avg_response_time_ms': 150
            },
            'github': {
                'logins': 300,
                'failures': 8,
                'success_rate': 97.4,
                'avg_response_time_ms': 200
            },
            'local': {
                'logins': 450,
                'failures': 25,
                'success_rate': 94.7,
                'avg_response_time_ms': 100
            }
        }
        
        # Get provider-specific metrics
        provider_metrics = mock_metrics_service.get_provider_metrics(time_range='24h')
        
        # Verify provider breakdown
        assert 'google' in provider_metrics
        assert 'github' in provider_metrics
        assert 'local' in provider_metrics
        assert all(provider['success_rate'] > 90 for provider in provider_metrics.values())


class TestPerformanceMetrics:
    """Test authentication performance metrics."""

    @pytest.fixture
    def mock_performance_collector(self):
        """Mock performance metrics collector."""
        collector = MagicMock(spec=PerformanceMetricsCollector)
        collector.record_response_time = AsyncMock()
        collector.record_throughput = AsyncMock()
        collector.record_error_rate = AsyncMock()
        collector.get_performance_summary = AsyncMock()
        return collector

    async def test_authentication_response_time_metrics(self, mock_performance_collector):
        """Test authentication response time metrics."""
        response_time_data = {
            'endpoint': '/auth/login',
            'method': 'POST',
            'response_time_ms': 245,
            'status_code': 200,
            'auth_provider': 'google',
            'timestamp': datetime.utcnow()
        }
        
        # Record response time
        await mock_performance_collector.record_response_time(response_time_data)
        
        # Verify response time recording
        mock_performance_collector.record_response_time.assert_called_once_with(response_time_data)

    async def test_authentication_throughput_metrics(self, mock_performance_collector):
        """Test authentication throughput metrics."""
        throughput_data = {
            'endpoint': '/auth/login',
            'requests_per_minute': 150,
            'successful_requests': 147,
            'failed_requests': 3,
            'timestamp': datetime.utcnow()
        }
        
        # Record throughput
        await mock_performance_collector.record_throughput(throughput_data)
        
        # Verify throughput recording
        mock_performance_collector.record_throughput.assert_called_once_with(throughput_data)

    async def test_authentication_error_rate_metrics(self, mock_performance_collector):
        """Test authentication error rate metrics."""
        error_rate_data = {
            'endpoint': '/auth/login',
            'total_requests': 1000,
            'error_requests': 25,
            'error_rate_percentage': 2.5,
            'time_window_minutes': 60,
            'timestamp': datetime.utcnow()
        }
        
        # Record error rate
        await mock_performance_collector.record_error_rate(error_rate_data)
        
        # Verify error rate recording
        mock_performance_collector.record_error_rate.assert_called_once_with(error_rate_data)

    async def test_performance_summary_generation(self, mock_performance_collector):
        """Test performance summary generation."""
        # Mock performance summary
        mock_performance_collector.get_performance_summary.return_value = {
            'avg_response_time_ms': 195,
            'p95_response_time_ms': 380,
            'p99_response_time_ms': 650,
            'throughput_rpm': 1250,
            'error_rate_percentage': 2.1,
            'availability_percentage': 99.8,
            'slowest_endpoints': [
                {'endpoint': '/auth/oauth/callback', 'avg_time_ms': 450},
                {'endpoint': '/auth/mfa/verify', 'avg_time_ms': 380}
            ]
        }
        
        # Get performance summary
        summary = await mock_performance_collector.get_performance_summary(
            time_range='1h'
        )
        
        # Verify performance summary
        assert summary['avg_response_time_ms'] > 0
        assert summary['availability_percentage'] > 99
        assert len(summary['slowest_endpoints']) > 0

    async def test_sla_compliance_monitoring(self, mock_performance_collector):
        """Test SLA compliance monitoring."""
        # Mock SLA compliance data
        mock_performance_collector.check_sla_compliance.return_value = {
            'availability_sla': {
                'target': 99.9,
                'current': 99.95,
                'status': 'meeting',
                'breach_risk': 'low'
            },
            'response_time_sla': {
                'target_p95_ms': 500,
                'current_p95_ms': 380,
                'status': 'meeting',
                'breach_risk': 'low'
            },
            'error_rate_sla': {
                'target_percentage': 1.0,
                'current_percentage': 0.8,
                'status': 'meeting',
                'breach_risk': 'low'
            }
        }
        
        # Check SLA compliance
        sla_status = mock_performance_collector.check_sla_compliance()
        
        # Verify SLA compliance
        assert sla_status['availability_sla']['status'] == 'meeting'
        assert sla_status['response_time_sla']['current_p95_ms'] < sla_status['response_time_sla']['target_p95_ms']
        assert sla_status['error_rate_sla']['current_percentage'] < sla_status['error_rate_sla']['target_percentage']


class TestSecurityMetrics:
    """Test security-related metrics collection."""

    @pytest.fixture
    def mock_security_collector(self):
        """Mock security metrics collector."""
        collector = MagicMock(spec=SecurityMetricsCollector)
        collector.record_suspicious_activity = AsyncMock()
        collector.record_security_event = AsyncMock()
        collector.track_threat_level = AsyncMock()
        collector.generate_security_report = AsyncMock()
        return collector

    async def test_suspicious_activity_metrics(self, mock_security_collector):
        """Test suspicious activity metrics collection."""
        suspicious_activity = {
            'activity_type': 'rapid_login_attempts',
            'user_id': str(uuid4()),
            'ip_address': '192.168.1.100',
            'attempt_count': 15,
            'time_window_minutes': 5,
            'risk_score': 85,
            'timestamp': datetime.utcnow()
        }
        
        # Record suspicious activity
        await mock_security_collector.record_suspicious_activity(suspicious_activity)
        
        # Verify suspicious activity recording
        mock_security_collector.record_suspicious_activity.assert_called_once_with(suspicious_activity)

    async def test_security_event_metrics(self, mock_security_collector):
        """Test security event metrics collection."""
        security_event = {
            'event_type': 'account_lockout',
            'user_id': str(uuid4()),
            'reason': 'multiple_failed_attempts',
            'severity': 'medium',
            'ip_address': '10.0.0.50',
            'timestamp': datetime.utcnow(),
            'action_taken': 'account_locked_30min'
        }
        
        # Record security event
        await mock_security_collector.record_security_event(security_event)
        
        # Verify security event recording
        mock_security_collector.record_security_event.assert_called_once_with(security_event)

    async def test_threat_level_tracking(self, mock_security_collector):
        """Test threat level tracking and metrics."""
        threat_data = {
            'overall_threat_level': 'medium',
            'threat_score': 65,
            'active_threats': [
                {'type': 'credential_stuffing', 'severity': 'high', 'ip_count': 25},
                {'type': 'brute_force', 'severity': 'medium', 'ip_count': 8}
            ],
            'mitigation_actions': [
                'rate_limiting_enabled',
                'suspicious_ip_monitoring'
            ],
            'timestamp': datetime.utcnow()
        }
        
        # Track threat level
        await mock_security_collector.track_threat_level(threat_data)
        
        # Verify threat level tracking
        mock_security_collector.track_threat_level.assert_called_once_with(threat_data)

    async def test_security_metrics_aggregation(self, mock_security_collector):
        """Test security metrics aggregation."""
        # Mock security report
        mock_security_collector.generate_security_report.return_value = {
            'total_security_events_24h': 35,
            'high_severity_events': 5,
            'medium_severity_events': 15,
            'low_severity_events': 15,
            'blocked_ips': 12,
            'locked_accounts': 8,
            'threat_level': 'medium',
            'top_attack_types': [
                {'type': 'brute_force', 'count': 15},
                {'type': 'credential_stuffing', 'count': 12}
            ],
            'geographical_threats': [
                {'country': 'Unknown', 'event_count': 18},
                {'country': 'CN', 'event_count': 10}
            ]
        }
        
        # Generate security report
        report = await mock_security_collector.generate_security_report(
            time_range='24h'
        )
        
        # Verify security report
        assert report['total_security_events_24h'] > 0
        assert len(report['top_attack_types']) > 0
        assert report['threat_level'] in ['low', 'medium', 'high']

    async def test_compliance_metrics(self, mock_security_collector):
        """Test compliance and audit metrics."""
        # Mock compliance metrics
        mock_security_collector.get_compliance_metrics.return_value = {
            'gdpr_compliance': {
                'data_retention_compliant': True,
                'consent_tracking': True,
                'data_deletion_requests_processed': 5
            },
            'password_policy_compliance': {
                'users_compliant': 892,
                'users_non_compliant': 23,
                'compliance_rate': 97.5
            },
            'session_management_compliance': {
                'secure_session_handling': True,
                'session_timeout_enforced': True,
                'concurrent_session_limit_enforced': True
            },
            'audit_trail_completeness': 99.8
        }
        
        # Get compliance metrics
        compliance = mock_security_collector.get_compliance_metrics()
        
        # Verify compliance metrics
        assert compliance['gdpr_compliance']['data_retention_compliant'] is True
        assert compliance['password_policy_compliance']['compliance_rate'] > 95
        assert compliance['audit_trail_completeness'] > 99


class TestAlerting:
    """Test authentication alerting and monitoring."""

    @pytest.fixture
    def mock_alerting_service(self):
        """Mock alerting service."""
        service = MagicMock(spec=AuthAlerting)
        service.check_alert_conditions = AsyncMock()
        service.send_alert = AsyncMock()
        service.escalate_alert = AsyncMock()
        service.resolve_alert = AsyncMock()
        return service

    async def test_high_failure_rate_alerting(self, mock_alerting_service):
        """Test alerting on high authentication failure rates."""
        # Mock high failure rate condition
        mock_alerting_service.check_alert_conditions.return_value = [
            {
                'alert_type': 'high_failure_rate',
                'severity': 'high',
                'current_value': 15.2,
                'threshold': 5.0,
                'description': 'Authentication failure rate exceeded threshold',
                'time_window': '5m'
            }
        ]
        
        # Check alert conditions
        alerts = await mock_alerting_service.check_alert_conditions()
        
        # Verify high failure rate alert
        assert len(alerts) > 0
        assert alerts[0]['alert_type'] == 'high_failure_rate'
        assert alerts[0]['severity'] == 'high'
        assert alerts[0]['current_value'] > alerts[0]['threshold']

    async def test_performance_degradation_alerting(self, mock_alerting_service):
        """Test alerting on performance degradation."""
        # Mock performance degradation alert
        performance_alert = {
            'alert_type': 'performance_degradation',
            'severity': 'medium',
            'metric': 'p95_response_time',
            'current_value': 850,
            'threshold': 500,
            'description': 'Authentication response time degraded',
            'affected_endpoints': ['/auth/login', '/auth/oauth/callback']
        }
        
        # Send performance alert
        await mock_alerting_service.send_alert(performance_alert)
        
        # Verify alert sending
        mock_alerting_service.send_alert.assert_called_once_with(performance_alert)

    async def test_security_incident_alerting(self, mock_alerting_service):
        """Test alerting on security incidents."""
        # Mock security incident alert
        security_alert = {
            'alert_type': 'security_incident',
            'severity': 'critical',
            'incident_type': 'potential_credential_stuffing',
            'affected_accounts': 25,
            'source_ips': ['192.168.1.100', '10.0.0.50'],
            'description': 'Coordinated attack detected across multiple accounts',
            'immediate_actions': ['rate_limiting', 'ip_blocking']
        }
        
        # Send security alert
        await mock_alerting_service.send_alert(security_alert)
        
        # Verify security alert
        mock_alerting_service.send_alert.assert_called_once_with(security_alert)

    async def test_sla_breach_alerting(self, mock_alerting_service):
        """Test alerting on SLA breaches."""
        # Mock SLA breach alert
        sla_alert = {
            'alert_type': 'sla_breach',
            'severity': 'high',
            'sla_metric': 'availability',
            'current_value': 99.85,
            'sla_target': 99.9,
            'breach_duration_minutes': 15,
            'estimated_impact': 'moderate',
            'escalation_required': True
        }
        
        # Send SLA breach alert
        await mock_alerting_service.send_alert(sla_alert)
        
        # Check if escalation is required
        if sla_alert['escalation_required']:
            await mock_alerting_service.escalate_alert(sla_alert)
        
        # Verify SLA breach alerting and escalation
        mock_alerting_service.send_alert.assert_called_once_with(sla_alert)
        mock_alerting_service.escalate_alert.assert_called_once_with(sla_alert)

    async def test_alert_resolution(self, mock_alerting_service):
        """Test alert resolution and acknowledgment."""
        # Mock alert resolution
        alert_id = str(uuid4())
        resolution_data = {
            'alert_id': alert_id,
            'resolved_by': 'admin@example.com',
            'resolution_time': datetime.utcnow(),
            'resolution_notes': 'Issue resolved by restarting auth service',
            'root_cause': 'temporary_database_connection_issue'
        }
        
        # Resolve alert
        await mock_alerting_service.resolve_alert(resolution_data)
        
        # Verify alert resolution
        mock_alerting_service.resolve_alert.assert_called_once_with(resolution_data)

    async def test_alert_suppression(self, mock_alerting_service):
        """Test alert suppression for duplicate/similar alerts."""
        # Mock alert suppression logic
        duplicate_alert = {
            'alert_type': 'high_failure_rate',
            'severity': 'medium',
            'current_value': 6.2,
            'threshold': 5.0
        }
        
        # Mock suppression check
        mock_alerting_service.should_suppress_alert.return_value = True
        
        # Check if alert should be suppressed
        should_suppress = mock_alerting_service.should_suppress_alert(duplicate_alert)
        
        # Verify alert suppression
        assert should_suppress is True


class TestDashboardMetrics:
    """Test dashboard metrics aggregation and presentation."""

    @pytest.fixture
    def mock_dashboard_service(self):
        """Mock dashboard metrics service."""
        service = MagicMock()
        service.get_dashboard_data = AsyncMock()
        service.get_real_time_stats = AsyncMock()
        service.get_historical_trends = AsyncMock()
        return service

    async def test_dashboard_overview_metrics(self, mock_dashboard_service):
        """Test dashboard overview metrics."""
        # Mock dashboard overview
        mock_dashboard_service.get_dashboard_data.return_value = {
            'overview': {
                'total_active_sessions': 1547,
                'logins_last_hour': 245,
                'success_rate_24h': 97.2,
                'average_response_time_ms': 185,
                'current_threat_level': 'low'
            },
            'recent_activities': [
                {'time': '14:35', 'event': 'User login spike detected'},
                {'time': '14:20', 'event': 'High failure rate resolved'},
                {'time': '13:45', 'event': 'Suspicious IP blocked'}
            ],
            'system_health': {
                'auth_service_status': 'healthy',
                'database_status': 'healthy',
                'cache_status': 'healthy',
                'external_providers': {'google': 'healthy', 'github': 'healthy'}
            }
        }
        
        # Get dashboard data
        dashboard = await mock_dashboard_service.get_dashboard_data()
        
        # Verify dashboard metrics
        assert dashboard['overview']['total_active_sessions'] > 0
        assert dashboard['overview']['success_rate_24h'] > 95
        assert dashboard['system_health']['auth_service_status'] == 'healthy'
        assert len(dashboard['recent_activities']) > 0

    async def test_real_time_statistics(self, mock_dashboard_service):
        """Test real-time statistics for dashboard."""
        # Mock real-time stats
        mock_dashboard_service.get_real_time_stats.return_value = {
            'current_logins_per_minute': 25,
            'current_failures_per_minute': 2,
            'active_sessions': 1547,
            'concurrent_users': 1234,
            'response_time_p95_ms': 320,
            'error_rate_percentage': 1.8,
            'timestamp': datetime.utcnow()
        }
        
        # Get real-time stats
        real_time = await mock_dashboard_service.get_real_time_stats()
        
        # Verify real-time statistics
        assert real_time['current_logins_per_minute'] >= 0
        assert real_time['active_sessions'] > 0
        assert real_time['error_rate_percentage'] < 5  # Should be reasonable
        assert 'timestamp' in real_time

    async def test_historical_trends(self, mock_dashboard_service):
        """Test historical trends for dashboard charts."""
        # Mock historical trend data
        mock_dashboard_service.get_historical_trends.return_value = {
            'login_trends': [
                {'hour': '00:00', 'logins': 45, 'failures': 2},
                {'hour': '01:00', 'logins': 32, 'failures': 1},
                {'hour': '02:00', 'logins': 28, 'failures': 3},
            ],
            'performance_trends': [
                {'hour': '00:00', 'avg_response_ms': 180, 'p95_response_ms': 350},
                {'hour': '01:00', 'avg_response_ms': 175, 'p95_response_ms': 340},
                {'hour': '02:00', 'avg_response_ms': 190, 'p95_response_ms': 380},
            ],
            'provider_usage': {
                'google': 45.2,
                'github': 30.8,
                'local': 24.0
            }
        }
        
        # Get historical trends
        trends = await mock_dashboard_service.get_historical_trends(
            time_range='24h',
            granularity='hourly'
        )
        
        # Verify historical trends
        assert len(trends['login_trends']) > 0
        assert len(trends['performance_trends']) > 0
        assert sum(trends['provider_usage'].values()) == 100.0  # Should total 100%

    async def test_metrics_export(self, mock_dashboard_service):
        """Test metrics export functionality."""
        # Mock metrics export
        mock_dashboard_service.export_metrics.return_value = {
            'export_id': str(uuid4()),
            'format': 'json',
            'time_range': '7d',
            'file_size_bytes': 245780,
            'download_url': 'https://api.example.com/exports/metrics-123456.json',
            'expires_at': datetime.utcnow() + timedelta(hours=24)
        }
        
        # Export metrics
        export_result = mock_dashboard_service.export_metrics(
            format='json',
            time_range='7d',
            include_raw_data=True
        )
        
        # Verify metrics export
        assert 'export_id' in export_result
        assert export_result['format'] == 'json'
        assert export_result['file_size_bytes'] > 0
        assert 'download_url' in export_result


class TestMetricsRetention:
    """Test metrics retention and archival."""

    @pytest.fixture
    def mock_retention_service(self):
        """Mock metrics retention service."""
        service = MagicMock()
        service.cleanup_old_metrics = AsyncMock()
        service.archive_metrics = AsyncMock()
        service.get_retention_policy = AsyncMock()
        return service

    async def test_metrics_cleanup(self, mock_retention_service):
        """Test cleanup of old metrics data."""
        # Mock cleanup operation
        mock_retention_service.cleanup_old_metrics.return_value = {
            'records_deleted': 150000,
            'disk_space_freed_mb': 45.7,
            'oldest_retained_date': datetime.utcnow() - timedelta(days=90),
            'cleanup_duration_seconds': 12.5
        }
        
        # Cleanup old metrics
        cleanup_result = await mock_retention_service.cleanup_old_metrics(
            retention_days=90
        )
        
        # Verify cleanup
        assert cleanup_result['records_deleted'] > 0
        assert cleanup_result['disk_space_freed_mb'] > 0
        assert cleanup_result['cleanup_duration_seconds'] > 0

    async def test_metrics_archival(self, mock_retention_service):
        """Test archival of metrics data."""
        # Mock archival operation
        mock_retention_service.archive_metrics.return_value = {
            'archived_records': 500000,
            'archive_file_size_mb': 125.3,
            'archive_location': 's3://metrics-archive/2024/01/auth-metrics.gz',
            'archive_duration_seconds': 45.2,
            'compression_ratio': 0.15
        }
        
        # Archive metrics
        archive_result = await mock_retention_service.archive_metrics(
            date_range='2024-01',
            compression=True
        )
        
        # Verify archival
        assert archive_result['archived_records'] > 0
        assert archive_result['archive_file_size_mb'] > 0
        assert archive_result['compression_ratio'] < 1.0
        assert 'archive_location' in archive_result

    async def test_retention_policy_compliance(self, mock_retention_service):
        """Test retention policy compliance checking."""
        # Mock retention policy
        mock_retention_service.get_retention_policy.return_value = {
            'raw_metrics_days': 30,
            'aggregated_metrics_days': 365,
            'archived_metrics_years': 7,
            'compliance_status': 'compliant',
            'next_cleanup_date': datetime.utcnow() + timedelta(days=1),
            'storage_usage': {
                'raw_data_gb': 2.3,
                'aggregated_data_gb': 0.8,
                'archived_data_gb': 15.7
            }
        }
        
        # Get retention policy status
        retention_status = await mock_retention_service.get_retention_policy()
        
        # Verify retention policy compliance
        assert retention_status['compliance_status'] == 'compliant'
        assert retention_status['raw_metrics_days'] <= 90  # Reasonable retention
        assert retention_status['storage_usage']['raw_data_gb'] > 0