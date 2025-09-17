"""
Integration Tests for Authentication Flow Validation

Tests the authentication monitoring integration with real services (non-docker).
Validates that authentication monitoring correctly tracks the authentication flow
and integrates with the WebSocket authentication infrastructure.

Following SSOT testing patterns and using real services where possible.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.monitoring.authentication_monitor_service import (
    AuthenticationMonitorService,
    AuthenticationStatus,
    get_authentication_monitor_service
)
from netra_backend.app.websocket_core.auth_health_provider import (
    AuthHealthProvider,
    get_auth_health_provider
)


class TestAuthFlowValidationIntegration(SSotAsyncTestCase):
    """Integration tests for authentication flow validation with monitoring."""
    
    async def setUp(self):
        """Set up integration test environment."""
        await super().setUp()
        
        # Reset global instances for test isolation
        import netra_backend.app.monitoring.authentication_monitor_service as monitor_module
        monitor_module._authentication_monitor_service = None
        
        import netra_backend.app.websocket_core.auth_health_provider as health_module
        health_module._auth_health_provider = None
        
        # Create mock WebSocket manager for testing
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.get_active_connection_count = Mock(return_value=5)
        self.mock_websocket_manager.is_connection_active = Mock(return_value=True)
        
        # Initialize services
        self.monitor_service = get_authentication_monitor_service(self.mock_websocket_manager)
        self.health_provider = get_auth_health_provider(self.mock_websocket_manager)
    
    async def test_authentication_flow_success_tracking(self):
        """Test successful authentication flow is properly tracked."""
        # Simulate successful authentication flow
        user_id = "test-user-123"
        response_time = 150.0
        
        # Record authentication attempt
        await self.monitor_service.record_authentication_attempt(
            success=True,
            response_time_ms=response_time,
            user_id=user_id
        )
        
        # Verify monitoring captured the success
        stats = self.monitor_service.get_authentication_stats()
        metrics = stats["metrics"]
        
        self.assertEqual(metrics["total_attempts"], 1)
        self.assertEqual(metrics["successful_authentications"], 1)
        self.assertEqual(metrics["failed_authentications"], 0)
        self.assertEqual(metrics["success_rate_percent"], 100.0)
        self.assertEqual(metrics["average_response_time_ms"], response_time)
        
        # Verify health status reflects success
        health_status = await self.health_provider.get_authentication_health_status()
        self.assertEqual(health_status["overall_status"], "healthy")
        self.assertEqual(health_status["metrics"]["total_attempts"], 1)
    
    async def test_authentication_flow_failure_tracking(self):
        """Test failed authentication flow is properly tracked."""
        # Simulate failed authentication flow
        user_id = "test-user-456"
        response_time = 500.0
        error_details = "Invalid token signature"
        
        # Record authentication failure
        await self.monitor_service.record_authentication_attempt(
            success=False,
            response_time_ms=response_time,
            user_id=user_id,
            error_details=error_details
        )
        
        # Verify monitoring captured the failure
        stats = self.monitor_service.get_authentication_stats()
        metrics = stats["metrics"]
        
        self.assertEqual(metrics["total_attempts"], 1)
        self.assertEqual(metrics["successful_authentications"], 0)
        self.assertEqual(metrics["failed_authentications"], 1)
        self.assertEqual(metrics["success_rate_percent"], 0.0)
        self.assertEqual(metrics["failure_rate_percent"], 100.0)
        
        # Verify health status reflects degraded state
        health_status = await self.health_provider.get_authentication_health_status()
        # Single failure should show as degraded, not critical (need multiple for critical)
        self.assertIn(health_status["overall_status"], ["degraded", "critical"])
    
    async def test_authentication_timeout_flow_tracking(self):
        """Test authentication timeout flow is properly tracked."""
        # Simulate authentication timeout
        user_id = "test-user-timeout"
        response_time = 5000.0  # 5 second timeout
        error_details = "Authentication request timeout after 5 seconds"
        
        # Record authentication timeout
        await self.monitor_service.record_authentication_attempt(
            success=False,
            response_time_ms=response_time,
            user_id=user_id,
            error_details=error_details
        )
        
        # Verify timeout was specifically tracked
        stats = self.monitor_service.get_authentication_stats()
        metrics = stats["metrics"]
        
        self.assertEqual(metrics["authentication_timeouts"], 1)
        self.assertEqual(metrics["failed_authentications"], 1)
        self.assertEqual(metrics["average_response_time_ms"], response_time)
        
        # Verify health status includes timeout information
        health_status = await self.health_provider.get_authentication_health_status()
        self.assertGreater(health_status["metrics"]["authentication_timeouts"], 0)
    
    async def test_websocket_connection_health_integration(self):
        """Test WebSocket connection health integration with monitoring."""
        # Mock connection monitor for WebSocket integration
        with patch('netra_backend.app.websocket_core.unified_emitter.AuthenticationConnectionMonitor') as mock_monitor_class:
            mock_monitor = AsyncMock()
            mock_monitor.get_monitoring_stats.return_value = {
                "unhealthy_connections_detected": 2,
                "health_checks_performed": 10,
                "recovery_attempts": 1
            }
            mock_monitor_class.return_value = mock_monitor
            
            # Create new service with mocked connection monitor
            service = AuthenticationMonitorService(self.mock_websocket_manager)
            
            # Test connection health check
            result = await service.ensure_auth_connection_health("test-user")
            self.assertTrue(result)
            
            # Verify connection monitor was called
            mock_monitor.ensure_auth_connection_health.assert_called_once_with("test-user")
    
    async def test_circuit_breaker_integration_flow(self):
        """Test circuit breaker integration in authentication flow."""
        # Simulate high failure rate to trip circuit breaker
        for i in range(6):  # Create enough failures
            await self.monitor_service.record_authentication_attempt(
                success=False,
                response_time_ms=1000.0,
                user_id=f"test-user-fail-{i}",
                error_details="Service unavailable"
            )
        
        # Add minimum successful attempts to meet sample size threshold
        for i in range(4):
            await self.monitor_service.record_authentication_attempt(
                success=True,
                response_time_ms=200.0,
                user_id=f"test-user-success-{i}"
            )
        
        # Verify circuit breaker status
        health_status = await self.health_provider.get_authentication_health_status()
        circuit_breaker_status = await self.health_provider.check_authentication_circuit_breaker()
        
        # Circuit breaker should be open due to high failure rate
        self.assertTrue(circuit_breaker_status["circuit_breaker_status"]["is_open"])
        self.assertEqual(health_status["overall_status"], "critical")
        
        # Verify golden path impact assessment
        golden_path = health_status["golden_path_assessment"]
        self.assertEqual(golden_path["impact_level"], "critical")
        self.assertTrue(golden_path["golden_path_blocked"])
        self.assertTrue(golden_path["chat_functionality_impacted"])
    
    async def test_health_provider_caching_behavior(self):
        """Test health provider caching behavior for performance."""
        # Get health status twice quickly
        start_time = datetime.now(timezone.utc)
        health_status_1 = await self.health_provider.get_authentication_health_status()
        health_status_2 = await self.health_provider.get_authentication_health_status()
        
        # Verify caching worked (timestamps should be the same)
        self.assertEqual(
            health_status_1["health_check_timestamp"],
            health_status_2["health_check_timestamp"]
        )
        
        # Verify cache duration
        self.assertIsNotNone(self.health_provider.last_health_check)
        self.assertIsNotNone(self.health_provider.cached_health_status)
    
    async def test_health_provider_cache_expiration(self):
        """Test health provider cache expiration."""
        # Get initial health status
        health_status_1 = await self.health_provider.get_authentication_health_status()
        
        # Manually expire cache
        past_time = datetime.now(timezone.utc) - timezone.utc.localize(datetime.fromtimestamp(0)).replace(tzinfo=None).replace(tzinfo=timezone.utc) + datetime.now(timezone.utc)
        # Simulate cache expiration by setting last check to past
        import datetime as dt
        self.health_provider.last_health_check = datetime.now(timezone.utc) - dt.timedelta(seconds=20)
        
        # Record new data
        await self.monitor_service.record_authentication_attempt(
            success=True,
            response_time_ms=100.0,
            user_id="cache-test-user"
        )
        
        # Get health status again - should be fresh
        health_status_2 = await self.health_provider.get_authentication_health_status()
        
        # Verify cache was refreshed (different timestamps)
        self.assertNotEqual(
            health_status_1["health_check_timestamp"],
            health_status_2["health_check_timestamp"]
        )
        
        # Verify new data is included
        self.assertGreater(
            health_status_2["metrics"]["total_attempts"],
            health_status_1["metrics"]["total_attempts"]
        )
    
    async def test_websocket_authentication_health_integration(self):
        """Test WebSocket-specific authentication health integration."""
        # Set up connection data
        self.mock_websocket_manager.get_active_connection_count.return_value = 8
        
        # Record some authentication data
        await self.monitor_service.record_authentication_attempt(
            success=True,
            response_time_ms=200.0,
            user_id="websocket-user-1"
        )
        
        # Get WebSocket authentication health
        ws_health = await self.health_provider.get_websocket_authentication_health()
        
        # Verify WebSocket-specific data
        self.assertIn("websocket_authentication", ws_health)
        ws_auth = ws_health["websocket_authentication"]
        
        self.assertEqual(ws_auth["active_connections"], 8)
        self.assertEqual(ws_auth["status"], "healthy")
        self.assertTrue(ws_auth["monitoring_enabled"])
        
        # Verify golden path assessment
        self.assertIn("golden_path_impact", ws_health)
        golden_path = ws_health["golden_path_impact"]
        self.assertEqual(golden_path["impact_level"], "none")
        self.assertFalse(golden_path["golden_path_blocked"])
    
    async def test_authentication_metrics_endpoint_integration(self):
        """Test authentication metrics for health endpoint integration."""
        # Record various authentication attempts
        auth_attempts = [
            (True, 150.0, "user-1"),
            (True, 200.0, "user-2"),
            (False, 500.0, "user-3"),
            (True, 175.0, "user-4"),
            (False, 750.0, "user-5")
        ]
        
        for success, response_time, user_id in auth_attempts:
            await self.monitor_service.record_authentication_attempt(
                success=success,
                response_time_ms=response_time,
                user_id=user_id,
                error_details="Test error" if not success else None
            )
        
        # Get authentication metrics
        metrics = await self.health_provider.get_authentication_metrics()
        
        # Verify metrics structure and values
        self.assertIn("authentication_metrics", metrics)
        auth_metrics = metrics["authentication_metrics"]
        
        self.assertEqual(auth_metrics["total_attempts"], 5)
        self.assertEqual(auth_metrics["successful_authentications"], 3)
        self.assertEqual(auth_metrics["failed_authentications"], 2)
        self.assertEqual(auth_metrics["success_rate_percent"], 60.0)
        
        # Verify average response time calculation
        expected_avg = (150.0 + 200.0 + 500.0 + 175.0 + 750.0) / 5
        self.assertEqual(auth_metrics["average_response_time_ms"], expected_avg)
        
        # Verify circuit breaker status included
        self.assertIn("circuit_breaker", metrics)
        self.assertTrue(metrics["monitoring_enabled"])
    
    async def test_golden_path_impact_assessment_integration(self):
        """Test golden path impact assessment integration."""
        # Simulate various failure scenarios
        test_scenarios = [
            # Scenario 1: Healthy state
            {"successes": 9, "failures": 1, "expected_impact": "none"},
            # Scenario 2: Degraded state  
            {"successes": 7, "failures": 3, "expected_impact": "minor"},
            # Scenario 3: Critical state
            {"successes": 2, "failures": 8, "expected_impact": "critical"}
        ]
        
        for scenario_idx, scenario in enumerate(test_scenarios):
            # Reset service for clean test
            import netra_backend.app.monitoring.authentication_monitor_service as monitor_module
            monitor_module._authentication_monitor_service = None
            
            import netra_backend.app.websocket_core.auth_health_provider as health_module  
            health_module._auth_health_provider = None
            
            monitor_service = get_authentication_monitor_service(self.mock_websocket_manager)
            health_provider = get_auth_health_provider(self.mock_websocket_manager)
            
            # Record scenario data
            for i in range(scenario["successes"]):
                await monitor_service.record_authentication_attempt(
                    success=True,
                    response_time_ms=200.0,
                    user_id=f"scenario-{scenario_idx}-success-{i}"
                )
            
            for i in range(scenario["failures"]):
                await monitor_service.record_authentication_attempt(
                    success=False,
                    response_time_ms=1000.0,
                    user_id=f"scenario-{scenario_idx}-fail-{i}",
                    error_details="Test failure"
                )
            
            # Get health status
            health_status = await health_provider.get_authentication_health_status()
            golden_path = health_status["golden_path_assessment"]
            
            # Verify impact level matches expectation
            if scenario["expected_impact"] == "none":
                self.assertIn(golden_path["impact_level"], ["none", "minor"])
                self.assertFalse(golden_path["chat_functionality_impacted"])
            elif scenario["expected_impact"] == "minor":
                self.assertIn(golden_path["impact_level"], ["minor", "major"])
            elif scenario["expected_impact"] == "critical":
                self.assertEqual(golden_path["impact_level"], "critical")
                self.assertTrue(golden_path["chat_functionality_impacted"])
    
    async def test_error_handling_in_integration_flow(self):
        """Test error handling in authentication monitoring integration."""
        # Test with invalid WebSocket manager
        invalid_manager = None
        
        # Should not crash when creating service with None manager
        service = AuthenticationMonitorService(invalid_manager)
        self.assertIsNone(service.connection_monitor)
        
        # Should still be able to record authentication attempts
        await service.record_authentication_attempt(
            success=True,
            response_time_ms=200.0,
            user_id="error-test-user"
        )
        
        # Should still be able to get health status
        health_status = await service.get_health_status()
        self.assertIsInstance(health_status.status, AuthenticationStatus)
        
        # Test health provider with error conditions
        health_provider = AuthHealthProvider(invalid_manager)
        
        # Should handle errors gracefully
        health_response = await health_provider.get_authentication_health_status()
        self.assertIn("overall_status", health_response)
        
        # Should not crash on metrics retrieval
        metrics = await health_provider.get_authentication_metrics()
        self.assertIn("authentication_metrics", metrics)


if __name__ == "__main__":
    pytest.main([__file__])