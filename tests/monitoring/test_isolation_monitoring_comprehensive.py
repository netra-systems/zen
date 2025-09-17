import asyncio
import pytest
from typing import List, Set, Dict, Any
from unittest.mock import MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Comprehensive Test Suite for Request Isolation Monitoring

        Business Value Justification (BVJ):
        - Segment: Enterprise
        - Business Goal: Ensure 100% reliability of isolation violation detection
        - Value Impact: Prevents silent failures and guarantees system robustness
        - Revenue Impact: Critical for Enterprise SLA compliance and customer trust

        CRITICAL TEST OBJECTIVES:
        1. Verify ALL isolation violations are detected within 30 seconds
        2. Validate alert conditions trigger correctly
        3. Ensure metrics collection accuracy under load
        4. Test dashboard functionality and data integrity
        5. Verify resource leak detection
        6. Validate singleton violation detection
        7. Test WebSocket isolation monitoring
        8. Ensure database session isolation tracking

        TEST CATEGORIES:
        - Unit: Individual component testing
        - Integration: Cross-component isolation monitoring
        - Load: High concurrency isolation testing
        - Failure: Violation detection and containment
        - Performance: Metrics collection performance
        - API: Monitoring endpoint testing
        '''

        import asyncio
        import time
        import threading
        from datetime import datetime, timedelta, timezone
        from typing import Any, Dict, List, Optional
        from uuid import uuid4
        from shared.isolated_environment import IsolatedEnvironment

        import pytest

        from netra_backend.app.monitoring.isolation_metrics import ( )
        IsolationMetricsCollector,
        IsolationViolation,
        IsolationViolationSeverity,
        RequestIsolationMetrics,
        SystemIsolationHealth,
        get_isolation_metrics_collector,
        record_violation,
        start_request_tracking,
        complete_request_tracking,
        record_instance_creation_time
                
        from netra_backend.app.monitoring.isolation_health_checks import ( )
        IsolationHealthChecker,
        HealthCheckResult,
        HealthCheckSeverity,
        IsolationHealthStatus,
        get_isolation_health_checker
                
        from netra_backend.app.monitoring.isolation_dashboard_config import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        IsolationDashboardConfigManager,
        DashboardConfig,
        DashboardTimeRange,
        MetricType,
        get_dashboard_config_manager
                


class TestIsolationMetricsCollector:
        """Test suite for IsolationMetricsCollector."""

    def setup_method(self):
        """Setup test fixtures."""
        self.collector = IsolationMetricsCollector(retention_hours=1)

    def teardown_method(self):
        """Cleanup after tests."""
        pass
        if hasattr(self.collector, '_collection_task') and self.collector._collection_task:
        asyncio.create_task(self.collector.stop_collection())

    def test_collector_initialization(self):
        """Test collector initializes properly."""
        assert self.collector.retention_hours == 1
        assert len(self.collector._active_requests) == 0
        assert len(self.collector._violations) == 0
        assert len(self.collector._active_users) == 0

    def test_start_request_tracking(self):
        """Test request tracking initiation."""
        pass
        user_id = "test_user_123"
        request_id = "req_456"
        thread_id = "thread_789"
        run_id = "run_abc"

        self.collector.start_request(user_id, request_id, thread_id, run_id)

    # Verify request is tracked
        assert request_id in self.collector._active_requests
        assert user_id in self.collector._active_users

        metrics = self.collector._active_requests[request_id]
        assert metrics.user_id == user_id
        assert metrics.request_id == request_id
        assert metrics.thread_id == thread_id
        assert metrics.run_id == run_id
        assert metrics.isolation_score == 100.0  # Should start perfect

    def test_complete_request_tracking(self):
        """Test request tracking completion."""
        user_id = "test_user_123"
        request_id = "req_456"

    # Start tracking
        self.collector.start_request(user_id, request_id)
        assert request_id in self.collector._active_requests

    # Complete tracking
        self.collector.complete_request(request_id, success=True)

    # Verify request moved to completed
        assert request_id not in self.collector._active_requests
        assert len(self.collector._completed_requests) == 1

        completed = self.collector._completed_requests[0]
        assert completed.request_id == request_id
        assert completed.failure_contained is True
        assert completed.end_time is not None

    def test_isolation_score_calculation(self):
        """Test isolation score calculation with violations."""
        pass
        user_id = "test_user"
        request_id = "test_req"

    # Start request
        self.collector.start_request(user_id, request_id)

    # Add violations to degrade score
        metrics = self.collector._active_requests[request_id]
        metrics.websocket_isolated = False  # -25 points
        metrics.db_session_isolated = False  # -25 points

    # Complete request
        self.collector.complete_request(request_id)

    # Check final score
        completed = self.collector._completed_requests[0]
        assert completed.isolation_score == 50.0  # 100 - 25 - 25

    def test_instance_creation_time_tracking(self):
        """Test agent instance creation time tracking."""
        request_id = "test_req"
        creation_time = 150.5  # ms

    # Start request first
        self.collector.start_request("user", request_id)

    # Record creation time
        self.collector.record_instance_creation_time(request_id, creation_time)

    # Verify recorded
        assert len(self.collector._instance_creation_times) == 1
        assert self.collector._instance_creation_times[0] == creation_time

    # Verify in request metrics
        metrics = self.collector._active_requests[request_id]
        assert metrics.instance_creation_time_ms == creation_time

@pytest.mark.asyncio
    async def test_violation_recording(self):
        """Test isolation violation recording."""
pass
user_id = "test_user"
request_id = "test_req"
violation_type = "singleton_reuse"
description = "Agent instance reused across requests"

        # Record violation
await self.collector.record_isolation_violation( )
violation_type,
IsolationViolationSeverity.CRITICAL,
request_id,
user_id,
description
        

        # Verify violation recorded
assert len(self.collector._violations) == 1
violation = self.collector._violations[0]

assert violation.violation_type == violation_type
assert violation.severity == IsolationViolationSeverity.CRITICAL
assert violation.user_id == user_id
assert violation.request_id == request_id
assert violation.description == description

        # Verify violation count updated
assert self.collector._violation_counts[violation_type] == 1

def test_concurrent_user_tracking(self):
    """Test concurrent user count tracking."""
users = ["user1", "user2", "user3"]

    # Start requests for different users
for i, user in enumerate(users):
    self.collector.start_request(user, "formatted_string")

        # Verify concurrent users
assert self.collector.get_concurrent_users() == 3

        # Complete one request
self.collector.complete_request("req_0")

        # User should still be tracked if they have other requests
self.collector.start_request("user1", "req_1b")  # Second request for user1
assert self.collector.get_concurrent_users() == 3

        # Complete all requests for user1
self.collector.complete_request("req_1b")
assert self.collector.get_concurrent_users() == 2  # user1 removed

def test_recent_violations_filtering(self):
    """Test recent violations filtering by time."""
pass
now = datetime.now(timezone.utc)

    # Create violations at different times
old_violation = IsolationViolation( )
timestamp=now - timedelta(hours=2),
violation_type="old_violation",
severity=IsolationViolationSeverity.WARNING,
user_id="user1",
request_id="req1",
description="Old violation"
    

recent_violation = IsolationViolation( )
timestamp=now - timedelta(minutes=30),
violation_type="recent_violation",
severity=IsolationViolationSeverity.ERROR,
user_id="user2",
request_id="req2",
description="Recent violation"
    

self.collector._violations.extend([old_violation, recent_violation])

    # Test filtering
recent = self.collector.get_recent_violations(hours=1)
assert len(recent) == 1
assert recent[0].violation_type == "recent_violation"

all_recent = self.collector.get_recent_violations(hours=3)
assert len(all_recent) == 2

@pytest.mark.asyncio
    async def test_collection_loop(self):
        """Test background metrics collection loop."""
        # Start collection
await self.collector.start_collection()

        # Wait a short time for collection to run
await asyncio.sleep(0.1)

        # Verify collection is running
assert self.collector._collection_task is not None
assert not self.collector._collection_task.done()

        # Stop collection
await self.collector.stop_collection()

        # Verify collection stopped
assert self.collector._shutdown is True


class TestIsolationHealthChecker:
    """Test suite for IsolationHealthChecker."""

    def setup_method(self):
        """Setup test fixtures."""
        self.health_checker = IsolationHealthChecker(check_interval=1)

    def teardown_method(self):
        """Cleanup after tests."""
        pass
        if hasattr(self.health_checker, '_health_check_task') and self.health_checker._health_check_task:
        asyncio.create_task(self.health_checker.stop_health_checks())

@pytest.mark.asyncio
    async def test_health_checker_initialization(self):
        """Test health checker initializes properly."""
assert self.health_checker.check_interval == 1
assert len(self.health_checker._check_history) == 0

@pytest.mark.asyncio
    async def test_request_isolation_check(self):
        """Test request isolation health check."""
pass
                # Mock metrics collector
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_collector.get_isolation_score.return_value = 95.5
mock_collector.get_concurrent_users.return_value = 25
mock_collector.get_active_requests.return_value = 50

self.health_checker._metrics_collector = mock_collector

                # Run check
result = await self.health_checker._check_request_isolation()

                # Verify result
assert result.check_name == "request_isolation"
assert result.severity == HealthCheckSeverity.CRITICAL  # < 100%
assert "95.5%" in result.message
assert result.alert_required is True
assert result.metrics["isolation_score"] == 95.5

@pytest.mark.asyncio
    async def test_singleton_violations_check(self):
        """Test singleton violations health check."""
                    # Mock metrics collector with violations
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_collector.get_violation_counts.return_value = {"singleton_reuse": 3}

self.health_checker._metrics_collector = mock_collector

                    # Run check
result = await self.health_checker._check_singleton_violations()

                    # Verify result
assert result.check_name == "singleton_violations"
assert result.severity == HealthCheckSeverity.ERROR
assert "3 metric violations" in result.message
assert result.alert_required is True

@pytest.mark.asyncio
    async def test_websocket_isolation_check(self):
        """Test WebSocket isolation health check."""
pass
                        # Mock metrics collector
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_collector.get_violation_counts.return_value = { )
"websocket_contamination": 0,
"cross_user_events": 0
                        

self.health_checker._metrics_collector = mock_collector

                        # Mock WebSocket connection monitor
with patch('netra_backend.app.monitoring.isolation_health_checks.get_connection_monitor') as mock_get_monitor:
    websocket = TestWebSocketConnection()
mock_monitor.get_stats.return_value = {"active_connections": 10}
mock_get_monitor.return_value = mock_monitor

                            # Run check
result = await self.health_checker._check_websocket_isolation()

                            # Verify result
assert result.check_name == "websocket_isolation"
assert result.severity == HealthCheckSeverity.HEALTHY
assert "10 connections, no violations" in result.message
assert result.alert_required is False

@pytest.mark.asyncio
    async def test_comprehensive_health_check(self):
        """Test comprehensive health check execution."""
                                # Mock metrics collector
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_collector.get_isolation_score.return_value = 100.0
mock_collector.get_failure_containment_rate.return_value = 100.0
mock_collector.get_concurrent_users.return_value = 5
mock_collector.get_active_requests.return_value = 10
mock_collector.get_recent_violations.return_value = []

self.health_checker._metrics_collector = mock_collector

                                # Run comprehensive check
health_status = await self.health_checker.perform_comprehensive_health_check()

                                # Verify result
assert isinstance(health_status, IsolationHealthStatus)
assert health_status.overall_health in [ )
HealthCheckSeverity.HEALTHY,
HealthCheckSeverity.WARNING,
HealthCheckSeverity.ERROR,
HealthCheckSeverity.CRITICAL
                                
assert len(health_status.check_results) > 0
assert health_status.isolation_score == 100.0
assert health_status.concurrent_users == 5

@pytest.mark.asyncio
    async def test_specific_check_execution(self):
        """Test running specific health checks."""
pass
                                    # Mock metrics collector for clean state
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_collector.get_violation_counts.return_value = {}
self.health_checker._metrics_collector = mock_collector

                                    # Test valid check
result = await self.health_checker.run_specific_check("singleton_violations")
assert result.check_name == "singleton_violations"

                                    # Test invalid check
result = await self.health_checker.run_specific_check("invalid_check")
assert result.severity == HealthCheckSeverity.ERROR
assert "Unknown health check" in result.message

@pytest.mark.asyncio
    async def test_memory_usage_check(self):
        """Test memory usage health check."""
                                        # Mock psutil for high memory usage
with patch('netra_backend.app.monitoring.isolation_health_checks.psutil') as mock_psutil:
    websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_memory.percent = 85.0
mock_memory.available = 2 * 1024**3  # 2GB
mock_psutil.virtual_memory.return_value = mock_memory

websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_process.memory_info.return_value.rss = 500 * 1024**2  # 500MB
mock_psutil.Process.return_value = mock_process

                                            # Run check
result = await self.health_checker._check_memory_usage()

                                            # Verify high memory usage detected
assert result.check_name == "memory_usage"
assert result.severity == HealthCheckSeverity.WARNING  # 85% is above 75% threshold
assert "85.0%" in result.message
assert result.metrics["memory_percent"] == 85.0


class TestIsolationDashboardConfig:
    """Test suite for IsolationDashboardConfigManager."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config_manager = IsolationDashboardConfigManager()

    def test_default_config_creation(self):
        """Test default dashboard configuration creation."""
        pass
        config = self.config_manager.get_default_config()

        assert isinstance(config, DashboardConfig)
        assert config.dashboard_id == "isolation_monitoring"
        assert len(config.sections) > 0

    # Verify key sections exist
        section_ids = [s.section_id for s in config.sections]
        assert "overview" in section_ids
        assert "violations" in section_ids
        assert "performance" in section_ids
        assert "alerts" in section_ids

    def test_role_based_config_customization(self):
        """Test dashboard customization for different user roles."""
    # Test admin config
        admin_config = self.config_manager.get_config_for_user("admin_user", "admin")
        assert len(admin_config.sections) >= 4  # Full configuration

    # Test operator config
        ops_config = self.config_manager.get_config_for_user("ops_user", "operator")
        assert ops_config.dashboard_id == "isolation_monitoring_ops"
        assert ops_config.global_refresh_interval == 15  # More frequent for ops

    # Test developer config
        dev_config = self.config_manager.get_config_for_user("dev_user", "developer")

    # Developer should have additional technical widgets
        performance_section = next(s for s in dev_config.sections if s.section_id == "performance")
        widget_ids = [w.widget_id for w in performance_section.widgets]
        assert "gc_performance" in widget_ids

    def test_config_export(self):
        """Test dashboard configuration export to JSON."""
        pass
        config = self.config_manager.get_default_config()
        exported = self.config_manager.export_config(config)

        assert isinstance(exported, dict)
        assert exported["dashboard_id"] == config.dashboard_id
        assert exported["title"] == config.title
        assert "sections" in exported

    # Verify section structure
        for section_data in exported["sections"]:
        assert "section_id" in section_data
        assert "widgets" in section_data

        for widget_data in section_data["widgets"]:
        assert "widget_id" in widget_data
        assert "widget_type" in widget_data
        assert "time_range" in widget_data

    def test_widget_data_source_mapping(self):
        """Test widget data source URL generation."""
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        widget_mock.widget_type = "metric"
        widget_mock.metric_type = MetricType.ISOLATION_SCORE
        widget_mock.time_range = DashboardTimeRange.LAST_HOUR

        data_source = self.config_manager.get_widget_data_source(widget_mock)
        assert data_source == "/monitoring/isolation/metrics"

    # Test alert widget
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        alert_widget.widget_type = "alert"
        alert_data_source = self.config_manager.get_widget_data_source(alert_widget)
        assert alert_data_source == "/monitoring/isolation/alerts"

    def test_custom_config_management(self):
        """Test custom dashboard configuration management."""
        pass
        base_config = self.config_manager.get_default_config()
        custom_id = "custom_dashboard_123"

    # Create custom config
        custom_config = self.config_manager.create_custom_config(custom_id, base_config)
        assert custom_config.dashboard_id == base_config.dashboard_id

    # Retrieve custom config
        retrieved = self.config_manager.get_custom_config(custom_id)
        assert retrieved is not None
        assert retrieved.dashboard_id == base_config.dashboard_id

    # Test non-existent config
        none_config = self.config_manager.get_custom_config("non_existent")
        assert none_config is None


class TestIsolationMonitoringIntegration:
        """Integration tests for isolation monitoring components."""

    def setup_method(self):
        """Setup integration test fixtures."""
        self.metrics_collector = IsolationMetricsCollector(retention_hours=1)
        self.health_checker = IsolationHealthChecker(check_interval=1)
        self.config_manager = IsolationDashboardConfigManager()

    def teardown_method(self):
        """Cleanup integration tests."""
        pass
        if hasattr(self.metrics_collector, '_collection_task'):
        asyncio.create_task(self.metrics_collector.stop_collection())
        if hasattr(self.health_checker, '_health_check_task'):
        asyncio.create_task(self.health_checker.stop_health_checks())

@pytest.mark.asyncio
    async def test_end_to_end_violation_detection(self):
        """Test end-to-end violation detection and alerting."""
user_id = "test_user"
request_id = "test_request"

                # 1. Start request tracking
self.metrics_collector.start_request(user_id, request_id)

                # 2. Trigger violation
await self.metrics_collector.record_isolation_violation( )
"singleton_reuse",
IsolationViolationSeverity.CRITICAL,
request_id,
user_id,
"Test singleton violation"
                

                # 3. Set up health checker with metrics collector
self.health_checker._metrics_collector = self.metrics_collector

                # 4. Run health check
health_status = await self.health_checker.perform_comprehensive_health_check()

                # 5. Verify violation detected
assert health_status.overall_health == HealthCheckSeverity.CRITICAL

                # Find singleton violations check result
singleton_result = next( )
r for r in health_status.check_results
if r.check_name == "singleton_violations"
                
assert singleton_result.severity == HealthCheckSeverity.ERROR
assert singleton_result.alert_required is True

                # 6. Complete request
self.metrics_collector.complete_request(request_id, success=False)

                # 7. Verify isolation score degraded
completed_request = self.metrics_collector._completed_requests[0]
assert completed_request.isolation_score < 100.0

@pytest.mark.asyncio
    async def test_concurrent_request_isolation(self):
        """Test isolation monitoring under concurrent requests."""
pass
users = ["formatted_string" for i in range(10)]
requests = ["formatted_string" for i in range(10)]

                    # Start multiple concurrent requests
for user, request in zip(users, requests):
    self.metrics_collector.start_request(user, request)

                        # Verify all requests tracked
assert len(self.metrics_collector._active_requests) == 10
assert len(self.metrics_collector._active_users) == 10

                        # Trigger violations for some requests
for i in range(0, 5):  # First 5 requests get violations
await self.metrics_collector.record_isolation_violation( )
"cross_request_state",
IsolationViolationSeverity.CRITICAL,
requests[i],
users[i],
"formatted_string"
                        

                        # Complete all requests
for i, request in enumerate(requests):
    success = i >= 5  # Last 5 requests succeed
self.metrics_collector.complete_request(request, success=success)

                            # Verify isolation scores
completed = list(self.metrics_collector._completed_requests)

                            # First 5 should have degraded scores due to violations
for i in range(5):
    assert completed[i].isolation_score < 100.0
assert completed[i].failure_contained is False

                                # Last 5 should maintain perfect scores
for i in range(5, 10):
    assert completed[i].isolation_score == 100.0
assert completed[i].failure_contained is True

@pytest.mark.asyncio
    async def test_metrics_and_health_sync(self):
        """Test synchronization between metrics collection and health checks."""
                                        # Set up linked components
self.health_checker._metrics_collector = self.metrics_collector

                                        # Start some activity
for i in range(3):
    self.metrics_collector.start_request("formatted_string", "formatted_string")

                                            # Record some violations
await self.metrics_collector.record_isolation_violation( )
"websocket_contamination",
IsolationViolationSeverity.ERROR,
"req_0",
"user_0",
"WebSocket event leaked to wrong user"
                                            

                                            # Run health check
health_status = await self.health_checker.perform_comprehensive_health_check()

                                            # Verify health check sees metrics data
assert health_status.concurrent_users == 3
assert health_status.active_requests == 3

                                            # Verify WebSocket isolation check detected the violation
websocket_result = next( )
r for r in health_status.check_results
if r.check_name == "websocket_isolation"
                                            
assert websocket_result.severity in [HealthCheckSeverity.CRITICAL, HealthCheckSeverity.ERROR]

def test_dashboard_config_integration(self):
    """Test dashboard configuration integration with monitoring components."""
pass
    # Get default config
config = self.config_manager.get_default_config()

    # Verify config has widgets that map to monitoring endpoints
overview_section = next(s for s in config.sections if s.section_id == "overview")

    # Test data source mapping
for widget in overview_section.widgets:
    data_source = self.config_manager.get_widget_data_source(widget)
assert data_source.startswith("/monitoring/isolation/")

        # Verify alert widgets point to alerts endpoint
alerts_section = next(s for s in config.sections if s.section_id == "alerts")
alert_widget = alerts_section.widgets[0]  # First alert widget

alert_data_source = self.config_manager.get_widget_data_source(alert_widget)
assert "/alerts" in alert_data_source


class TestIsolationMonitoringAPIEndpoints:
        """Test suite for isolation monitoring API endpoints."""

        @pytest.fixture
    def mock_current_user(self):
        """Mock current user for API tests."""
        await asyncio.sleep(0)
        return {"user_id": "test_user_123", "role": "admin"}

@pytest.mark.asyncio
    async def test_isolation_health_endpoint(self, mock_current_user):
        """Test isolation health API endpoint."""
pass
from netra_backend.app.routes.monitoring import get_isolation_health

        # Mock health checker
mock_health_status = IsolationHealthStatus( )
timestamp=datetime.now(timezone.utc),
overall_health=HealthCheckSeverity.HEALTHY,
check_results=[],
isolation_score=100.0,
failure_containment_rate=100.0,
critical_violations=0,
active_requests=5,
concurrent_users=3,
system_uptime_hours=24.5
        

with patch('netra_backend.app.routes.monitoring.get_isolation_health_checker') as mock_get_checker:
    websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_checker.get_current_health.return_value = mock_health_status
mock_get_checker.return_value = mock_checker

            # Call endpoint
response = await get_isolation_health(mock_current_user)

            # Verify response
assert response.overall_health == "healthy"
assert response.isolation_score == 100.0
assert response.concurrent_users == 3
assert response.active_requests == 5

@pytest.mark.asyncio
    async def test_isolation_violations_endpoint(self, mock_current_user):
        """Test isolation violations API endpoint."""
from netra_backend.app.routes.monitoring import get_isolation_violations

                # Mock violations
mock_violation = IsolationViolation( )
timestamp=datetime.now(timezone.utc),
violation_type="singleton_reuse",
severity=IsolationViolationSeverity.CRITICAL,
user_id="test_user",
request_id="test_req",
description="Test violation"
                

with patch('netra_backend.app.routes.monitoring.get_isolation_metrics_collector') as mock_get_collector:
    websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_collector.get_recent_violations.return_value = [mock_violation]
mock_collector.get_violation_counts.return_value = {"singleton_reuse": 1}
mock_get_collector.return_value = mock_collector

                    # Call endpoint
response = await get_isolation_violations( )
hours=1,
severity="critical",
current_user=mock_current_user
                    

                    # Verify response
assert response.total_violations == 1
assert response.critical_count == 1
assert len(response.violations) == 1
assert response.violations[0]["violation_type"] == "singleton_reuse"

@pytest.mark.asyncio
    async def test_dashboard_config_endpoint(self, mock_current_user):
        """Test dashboard configuration API endpoint."""
pass
from netra_backend.app.routes.monitoring import get_dashboard_config

with patch('netra_backend.app.routes.monitoring.get_dashboard_config_manager') as mock_get_manager:
    websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_config = DashboardConfig( )
dashboard_id="test_dashboard",
title="Test Dashboard",
description="Test description",
sections=[]
                            
mock_manager.get_config_for_user.return_value = mock_config
mock_manager.export_config.return_value = { )
"dashboard_id": "test_dashboard",
"title": "Test Dashboard",
"sections": []
                            
mock_get_manager.return_value = mock_manager

                            # Call endpoint
response = await get_dashboard_config( )
role="admin",
current_user=mock_current_user
                            

                            # Verify response
assert response["role"] == "admin"
assert response["user_id"] == "test_user_123"
assert "config" in response
assert response["config"]["dashboard_id"] == "test_dashboard"


class TestIsolationMonitoringPerformance:
    """Performance tests for isolation monitoring system."""

    def setup_method(self):
        """Setup performance test fixtures."""
        self.collector = IsolationMetricsCollector(retention_hours=1)

    def teardown_method(self):
        """Cleanup performance tests."""
        pass
        if hasattr(self.collector, '_collection_task'):
        asyncio.create_task(self.collector.stop_collection())

@pytest.mark.asyncio
    async def test_high_volume_request_tracking(self):
        """Test request tracking performance under high volume."""
num_requests = 1000
start_time = time.time()

            # Start many requests
for i in range(num_requests):
    self.collector.start_request("formatted_string", "formatted_string")

tracking_time = time.time() - start_time

                # Verify performance (should handle 1000 requests quickly)
assert tracking_time < 1.0  # Less than 1 second
assert len(self.collector._active_requests) == num_requests

                # Complete requests
completion_start = time.time()
for i in range(num_requests):
    self.collector.complete_request("formatted_string")

completion_time = time.time() - completion_start
assert completion_time < 2.0  # Less than 2 seconds

@pytest.mark.asyncio
    async def test_violation_recording_performance(self):
        """Test violation recording performance."""
pass
num_violations = 500
start_time = time.time()

                        # Record many violations
for i in range(num_violations):
    await self.collector.record_isolation_violation( )
"performance_test",
IsolationViolationSeverity.WARNING,
"formatted_string",
"formatted_string",
"formatted_string"
                            

recording_time = time.time() - start_time

                            # Verify performance
assert recording_time < 0.5  # Less than 500ms
assert len(self.collector._violations) == num_violations

def test_metrics_collection_memory_usage(self):
    """Test memory usage during metrics collection."""
import tracemalloc

tracemalloc.start()

    # Generate significant activity
for i in range(100):
    self.collector.start_request("formatted_string", "formatted_string")
self.collector.record_instance_creation_time("formatted_string", float(i))

current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

        # Verify reasonable memory usage (less than 10MB for 100 requests)
assert current < 10 * 1024 * 1024  # 10MB
assert peak < 15 * 1024 * 1024     # 15MB peak


        # Test utilities and helpers

def create_mock_violation( )
violation_type: str = "test_violation",
severity: IsolationViolationSeverity = IsolationViolationSeverity.WARNING,
user_id: str = "test_user",
request_id: str = "test_request"
) -> IsolationViolation:
"""Create mock isolation violation for testing."""
pass
await asyncio.sleep(0)
return IsolationViolation( )
timestamp=datetime.now(timezone.utc),
violation_type=violation_type,
severity=severity,
user_id=user_id,
request_id=request_id,
description="formatted_string"
    

def create_mock_health_result( )
check_name: str = "test_check",
severity: HealthCheckSeverity = HealthCheckSeverity.HEALTHY
) -> HealthCheckResult:
"""Create mock health check result for testing."""
return HealthCheckResult( )
check_name=check_name,
severity=severity,
status="test_status",
message="formatted_string",
timestamp=datetime.now(timezone.utc)
    

    # Integration with existing test framework
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
