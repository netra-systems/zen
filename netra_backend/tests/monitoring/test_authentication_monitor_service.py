"""
Unit Tests for AuthenticationMonitorService

Tests the SSOT authentication monitoring service functionality without requiring
Docker or external services. These tests validate the core monitoring logic,
metrics tracking, health status calculation, and circuit breaker functionality.

Following SSOT testing patterns from test_framework/ssot/base_test_case.py
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.monitoring.authentication_monitor_service import (
    AuthenticationMonitorService,
    AuthenticationStatus,
    AuthenticationMetrics,
    AuthenticationHealthStatus,
    get_authentication_monitor_service,
    record_auth_attempt,
    get_auth_health_status
)


class TestAuthenticationMonitorService(SSotBaseTestCase):
    """Unit tests for AuthenticationMonitorService SSOT implementation."""
    
    def setUp(self):
        """Set up test environment for each test."""
        super().setUp()
        
        # Reset global instance to ensure test isolation
        import netra_backend.app.monitoring.authentication_monitor_service as service_module
        service_module._authentication_monitor_service = None
        
        # Create fresh service instance for each test
        self.mock_websocket_manager = Mock()
        self.service = AuthenticationMonitorService(self.mock_websocket_manager)
    
    def test_service_initialization(self):
        """Test authentication monitor service initialization."""
        # Verify service is properly initialized
        self.assertIsInstance(self.service.metrics, AuthenticationMetrics)
        self.assertEqual(self.service.metrics.total_attempts, 0)
        self.assertEqual(self.service.metrics.successful_authentications, 0)
        self.assertEqual(self.service.metrics.failed_authentications, 0)
        self.assertEqual(self.service.websocket_manager, self.mock_websocket_manager)
        
        # Verify circuit breaker settings
        self.assertTrue(self.service.circuit_breaker_enabled)
        self.assertFalse(self.service.circuit_breaker_open)
        self.assertEqual(self.service.circuit_breaker_threshold, 50.0)
    
    async def test_record_successful_authentication(self):
        """Test recording successful authentication attempts."""
        # Record successful authentication
        await self.service.record_authentication_attempt(
            success=True,
            response_time_ms=150.0,
            user_id="test-user-123"
        )
        
        # Verify metrics updated correctly
        self.assertEqual(self.service.metrics.total_attempts, 1)
        self.assertEqual(self.service.metrics.successful_authentications, 1)
        self.assertEqual(self.service.metrics.failed_authentications, 0)
        self.assertEqual(self.service.metrics.average_response_time_ms, 150.0)
        self.assertIsNotNone(self.service.metrics.last_success_timestamp)
        self.assertIsNone(self.service.metrics.last_failure_timestamp)
        
        # Verify success rate calculation
        self.assertEqual(self.service.metrics.success_rate, 100.0)
        self.assertEqual(self.service.metrics.failure_rate, 0.0)
    
    async def test_record_failed_authentication(self):
        """Test recording failed authentication attempts."""
        # Record failed authentication
        await self.service.record_authentication_attempt(
            success=False,
            response_time_ms=500.0,
            user_id="test-user-456",
            error_details="Invalid token"
        )
        
        # Verify metrics updated correctly
        self.assertEqual(self.service.metrics.total_attempts, 1)
        self.assertEqual(self.service.metrics.successful_authentications, 0)
        self.assertEqual(self.service.metrics.failed_authentications, 1)
        self.assertEqual(self.service.metrics.average_response_time_ms, 500.0)
        self.assertIsNone(self.service.metrics.last_success_timestamp)
        self.assertIsNotNone(self.service.metrics.last_failure_timestamp)
        
        # Verify success rate calculation
        self.assertEqual(self.service.metrics.success_rate, 0.0)
        self.assertEqual(self.service.metrics.failure_rate, 100.0)
    
    async def test_authentication_timeout_tracking(self):
        """Test tracking of authentication timeouts."""
        # Record timeout failure
        await self.service.record_authentication_attempt(
            success=False,
            response_time_ms=5000.0,
            user_id="test-user-timeout",
            error_details="Authentication timeout occurred"
        )
        
        # Verify timeout was tracked
        self.assertEqual(self.service.metrics.authentication_timeouts, 1)
        self.assertEqual(self.service.metrics.failed_authentications, 1)
    
    async def test_response_time_averaging(self):
        """Test response time averaging with multiple attempts."""
        # Record multiple attempts with different response times
        response_times = [100.0, 200.0, 300.0, 400.0]
        for i, rt in enumerate(response_times):
            await self.service.record_authentication_attempt(
                success=True,
                response_time_ms=rt,
                user_id=f"test-user-{i}"
            )
        
        # Verify average calculation
        expected_average = sum(response_times) / len(response_times)
        self.assertEqual(self.service.metrics.average_response_time_ms, expected_average)
        self.assertEqual(len(self.service.response_times), 4)
    
    async def test_response_time_buffer_limit(self):
        """Test response time buffer doesn't exceed maximum size."""
        # Record more attempts than buffer size (100)
        for i in range(150):
            await self.service.record_authentication_attempt(
                success=True,
                response_time_ms=float(i),
                user_id=f"test-user-{i}"
            )
        
        # Verify buffer doesn't exceed max size
        self.assertEqual(len(self.service.response_times), self.service.max_response_times)
        self.assertEqual(len(self.service.response_times), 100)
        
        # Verify oldest entries were removed (should start from 50, not 0)
        self.assertEqual(self.service.response_times[0], 50.0)
        self.assertEqual(self.service.response_times[-1], 149.0)
    
    async def test_circuit_breaker_trip_on_high_failure_rate(self):
        """Test circuit breaker trips when failure rate exceeds threshold."""
        # Record multiple failures to exceed threshold (50%)
        for i in range(6):  # 6 failures out of 10 = 60% failure rate
            await self.service.record_authentication_attempt(
                success=False,
                response_time_ms=1000.0,
                user_id=f"test-user-fail-{i}"
            )
        
        # Record some successes to get above minimum sample size
        for i in range(4):
            await self.service.record_authentication_attempt(
                success=True,
                response_time_ms=200.0,
                user_id=f"test-user-success-{i}"
            )
        
        # Verify circuit breaker tripped
        self.assertTrue(self.service.circuit_breaker_open)
        self.assertGreater(self.service.metrics.circuit_breaker_trips, 0)
        self.assertIsNotNone(self.service.circuit_breaker_last_trip)
    
    async def test_circuit_breaker_reset_after_timeout(self):
        """Test circuit breaker resets after timeout period."""
        # Trip the circuit breaker
        await self.service.record_circuit_breaker_trip("Test trip")
        self.assertTrue(self.service.circuit_breaker_open)
        
        # Simulate timeout period passing
        past_time = datetime.now(timezone.utc) - timedelta(seconds=65)  # 65 seconds ago
        self.service.circuit_breaker_last_trip = past_time
        
        # Check circuit breaker - should reset
        state = await self.service._check_circuit_breaker()
        self.assertFalse(self.service.circuit_breaker_open)
    
    async def test_get_health_status_healthy(self):
        """Test health status calculation for healthy state."""
        # Record mostly successful authentications
        for i in range(20):
            await self.service.record_authentication_attempt(
                success=True,
                response_time_ms=200.0,
                user_id=f"test-user-{i}"
            )
        
        # Record minimal failures (< 5%)
        await self.service.record_authentication_attempt(
            success=False,
            response_time_ms=300.0,
            user_id="test-user-fail"
        )
        
        # Get health status
        health_status = await self.service.get_health_status()
        
        # Verify healthy status
        self.assertEqual(health_status.status, AuthenticationStatus.HEALTHY)
        self.assertEqual(health_status.metrics.total_attempts, 21)
        self.assertEqual(health_status.metrics.successful_authentications, 20)
        self.assertEqual(health_status.metrics.failed_authentications, 1)
        self.assertLess(health_status.metrics.failure_rate, 5.0)
        self.assertTrue(health_status.monitoring_enabled)
    
    async def test_get_health_status_degraded(self):
        """Test health status calculation for degraded state."""
        # Record 30% failure rate (degraded)
        for i in range(7):
            await self.service.record_authentication_attempt(
                success=True,
                response_time_ms=200.0,
                user_id=f"test-user-success-{i}"
            )
        
        for i in range(3):
            await self.service.record_authentication_attempt(
                success=False,
                response_time_ms=1000.0,
                user_id=f"test-user-fail-{i}"
            )
        
        # Get health status
        health_status = await self.service.get_health_status()
        
        # Verify degraded status
        self.assertEqual(health_status.status, AuthenticationStatus.DEGRADED)
        self.assertGreaterEqual(health_status.metrics.failure_rate, 20.0)
        self.assertLess(health_status.metrics.failure_rate, 50.0)
    
    async def test_get_health_status_critical(self):
        """Test health status calculation for critical state."""
        # Record 60% failure rate (critical)
        for i in range(4):
            await self.service.record_authentication_attempt(
                success=True,
                response_time_ms=200.0,
                user_id=f"test-user-success-{i}"
            )
        
        for i in range(6):
            await self.service.record_authentication_attempt(
                success=False,
                response_time_ms=1000.0,
                user_id=f"test-user-fail-{i}"
            )
        
        # Get health status
        health_status = await self.service.get_health_status()
        
        # Verify critical status
        self.assertEqual(health_status.status, AuthenticationStatus.CRITICAL)
        self.assertGreaterEqual(health_status.metrics.failure_rate, 50.0)
    
    async def test_get_health_status_circuit_breaker_open(self):
        """Test health status is critical when circuit breaker is open."""
        # Trip circuit breaker
        await self.service.record_circuit_breaker_trip("High failure rate")
        
        # Get health status
        health_status = await self.service.get_health_status()
        
        # Verify critical status due to circuit breaker
        self.assertEqual(health_status.status, AuthenticationStatus.CRITICAL)
        self.assertTrue(self.service.circuit_breaker_open)
    
    @patch('netra_backend.app.monitoring.authentication_monitor_service.AuthenticationConnectionMonitor')
    async def test_ensure_auth_connection_health_success(self, mock_monitor_class):
        """Test successful connection health check."""
        # Mock the connection monitor
        mock_monitor = AsyncMock()
        mock_monitor_class.return_value = mock_monitor
        
        # Create service with mock
        service = AuthenticationMonitorService(self.mock_websocket_manager)
        
        # Test connection health check
        result = await service.ensure_auth_connection_health("test-user-123")
        
        # Verify success
        self.assertTrue(result)
        mock_monitor.ensure_auth_connection_health.assert_called_once_with("test-user-123")
    
    @patch('netra_backend.app.monitoring.authentication_monitor_service.AuthenticationConnectionMonitor')
    async def test_ensure_auth_connection_health_failure(self, mock_monitor_class):
        """Test failed connection health check."""
        # Mock the connection monitor to raise exception
        mock_monitor = AsyncMock()
        mock_monitor.ensure_auth_connection_health.side_effect = Exception("Connection unhealthy")
        mock_monitor_class.return_value = mock_monitor
        
        # Create service with mock
        service = AuthenticationMonitorService(self.mock_websocket_manager)
        
        # Test connection health check
        result = await service.ensure_auth_connection_health("test-user-123")
        
        # Verify failure recorded
        self.assertFalse(result)
        self.assertEqual(service.metrics.failed_authentications, 1)
        self.assertIn("Connection health check failed", service.metrics.to_dict()["last_failure_timestamp"] is not None)
    
    def test_get_authentication_stats(self):
        """Test authentication statistics retrieval."""
        # Get stats
        stats = self.service.get_authentication_stats()
        
        # Verify stats structure
        self.assertIn("service_info", stats)
        self.assertIn("metrics", stats)
        self.assertIn("circuit_breaker", stats)
        self.assertIn("health_status", stats)
        self.assertIn("response_time_analysis", stats)
        
        # Verify service info
        service_info = stats["service_info"]
        self.assertEqual(service_info["name"], "AuthenticationMonitorService")
        self.assertTrue(service_info["ssot_compliant"])
        self.assertTrue(service_info["monitoring_enabled"])
    
    def test_authentication_metrics_to_dict(self):
        """Test authentication metrics serialization."""
        # Create metrics with data
        metrics = AuthenticationMetrics(
            total_attempts=10,
            successful_authentications=8,
            failed_authentications=2,
            authentication_timeouts=1,
            average_response_time_ms=250.5
        )
        
        # Convert to dict
        metrics_dict = metrics.to_dict()
        
        # Verify structure and values
        self.assertEqual(metrics_dict["total_attempts"], 10)
        self.assertEqual(metrics_dict["successful_authentications"], 8)
        self.assertEqual(metrics_dict["failed_authentications"], 2)
        self.assertEqual(metrics_dict["authentication_timeouts"], 1)
        self.assertEqual(metrics_dict["average_response_time_ms"], 250.5)
        self.assertEqual(metrics_dict["success_rate_percent"], 80.0)
        self.assertEqual(metrics_dict["failure_rate_percent"], 20.0)
        self.assertIn("uptime_seconds", metrics_dict)
    
    def test_authentication_health_status_to_dict(self):
        """Test authentication health status serialization."""
        # Create health status
        metrics = AuthenticationMetrics(total_attempts=5, successful_authentications=4, failed_authentications=1)
        health_status = AuthenticationHealthStatus(
            status=AuthenticationStatus.HEALTHY,
            metrics=metrics,
            active_connections=10,
            unhealthy_connections=1,
            errors=["Test error"],
            warnings=["Test warning"]
        )
        
        # Convert to dict
        status_dict = health_status.to_dict()
        
        # Verify structure
        self.assertEqual(status_dict["status"], "healthy")
        self.assertEqual(status_dict["active_connections"], 10)
        self.assertEqual(status_dict["unhealthy_connections"], 1)
        self.assertEqual(status_dict["errors"], ["Test error"])
        self.assertEqual(status_dict["warnings"], ["Test warning"])
        self.assertIn("metrics", status_dict)
        self.assertIn("timestamp", status_dict)


class TestAuthenticationMonitorServiceGlobalFunctions(SSotBaseTestCase):
    """Test global SSOT functions for authentication monitoring."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Reset global instance for test isolation
        import netra_backend.app.monitoring.authentication_monitor_service as service_module
        service_module._authentication_monitor_service = None
    
    def test_get_authentication_monitor_service_singleton(self):
        """Test global authentication monitor service is singleton."""
        # Get service twice
        service1 = get_authentication_monitor_service()
        service2 = get_authentication_monitor_service()
        
        # Verify same instance
        self.assertIs(service1, service2)
        self.assertIsInstance(service1, AuthenticationMonitorService)
    
    async def test_record_auth_attempt_convenience_function(self):
        """Test convenience function for recording auth attempts."""
        # Use convenience function
        await record_auth_attempt(
            success=True,
            response_time_ms=123.4,
            user_id="test-user"
        )
        
        # Verify it was recorded
        service = get_authentication_monitor_service()
        self.assertEqual(service.metrics.total_attempts, 1)
        self.assertEqual(service.metrics.successful_authentications, 1)
        self.assertEqual(service.metrics.average_response_time_ms, 123.4)
    
    async def test_get_auth_health_status_convenience_function(self):
        """Test convenience function for getting health status."""
        # Record some data first
        await record_auth_attempt(success=True, response_time_ms=200.0)
        
        # Use convenience function
        health_status = await get_auth_health_status()
        
        # Verify structure
        self.assertIsInstance(health_status, AuthenticationHealthStatus)
        self.assertEqual(health_status.metrics.total_attempts, 1)
        self.assertTrue(health_status.monitoring_enabled)


if __name__ == "__main__":
    pytest.main([__file__])