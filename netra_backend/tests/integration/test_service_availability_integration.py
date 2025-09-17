"""
Integration Tests for ServiceAvailabilityManager - Issue #895

Tests the integration of ServiceAvailabilityManager with the WebSocket system,
including health endpoint functionality and service dependency resolution.

Focus:
- Non-Docker integration testing
- Health endpoint response validation
- Service availability manager integration with WebSocket routes
- Graceful degradation testing
"""

import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Test framework imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from netra_backend.app.websocket_core.service_availability_manager import (
    ServiceAvailabilityManager,
    ServiceType,
    ServiceStatus,
    get_service_availability_manager
)


class TestServiceAvailabilityIntegration(unittest.TestCase):
    """Integration tests for ServiceAvailabilityManager with WebSocket system."""

    def setUp(self):
        """Set up integration test fixtures."""
        # Reset global manager state
        import netra_backend.app.websocket_core.service_availability_manager as sam_module
        sam_module._service_availability_manager = None

    def tearDown(self):
        """Clean up after tests."""
        # Reset global manager state
        import netra_backend.app.websocket_core.service_availability_manager as sam_module
        sam_module._service_availability_manager = None

    async def test_health_endpoint_integration(self):
        """Test health endpoint integration with service availability manager."""
        from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter

        # Create router for testing
        router_instance = WebSocketSSOTRouter()

        # Mock the service manager to return predictable results
        mock_manager = Mock(spec=ServiceAvailabilityManager)
        mock_health_report = {
            "overall_status": "healthy",
            "allow_websocket_connections": True,
            "denial_reason": None,
            "critical_services": {
                "authentication": {
                    "available": True,
                    "status": "healthy",
                    "last_check": "2025-09-17T10:00:00",
                    "error": None,
                    "response_time_ms": 15.2,
                    "circuit_breaker_open": False
                }
            },
            "optional_services": {
                "agent_bridge": {
                    "available": True,
                    "status": "healthy",
                    "last_check": "2025-09-17T10:00:00",
                    "error": None,
                    "response_time_ms": 8.5,
                    "circuit_breaker_open": False
                }
            },
            "summary": {
                "total_services": 7,
                "critical_services_count": 2,
                "optional_services_count": 5,
                "degraded_services": [],
                "failed_services": [],
                "health_summary": "Healthy: 7, Degraded: 0, Failed: 0, Unknown: 0"
            },
            "last_check": "2025-09-17T10:00:00"
        }

        mock_manager.get_health_report = AsyncMock(return_value=mock_health_report)
        mock_manager.should_allow_websocket_connection = Mock(return_value=(True, None))

        with patch('netra_backend.app.websocket_core.service_availability_manager.get_service_availability_manager',
                   return_value=mock_manager):
            with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager',
                       return_value=Mock()):

                # Call the health check endpoint
                result = await router_instance.websocket_health_check()

                # Verify response structure
                self.assertIsInstance(result, dict)
                self.assertIn("status", result)
                self.assertIn("service_availability", result)

                # Verify service availability section
                service_avail = result["service_availability"]
                self.assertTrue(service_avail["allow_websocket_connections"])
                self.assertEqual(service_avail["overall_service_status"], "healthy")
                self.assertIn("critical_services", service_avail)
                self.assertIn("optional_services", service_avail)

    async def test_websocket_manager_service_availability_integration(self):
        """Test WebSocket manager creation with service availability checks."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager_async

        # Mock a healthy service environment
        mock_app = Mock()
        mock_user_context = Mock()
        mock_user_context.user_id = "test_user_123"

        # Mock all the service availability components
        with patch('netra_backend.app.websocket_core.service_availability_manager.ServiceAvailabilityManager') as mock_sam_class:
            mock_sam_instance = Mock()
            mock_sam_class.return_value = mock_sam_instance

            # Mock healthy service report
            mock_health_report = {
                "overall_status": "healthy",
                "summary": {"health_summary": "All services healthy"}
            }
            mock_sam_instance.get_health_report = AsyncMock(return_value=mock_health_report)
            mock_sam_instance.should_allow_websocket_connection = Mock(return_value=(True, None))

            with patch('netra_backend.app.websocket_core.service_availability_manager.get_service_availability_manager',
                       return_value=mock_sam_instance), \
                 patch('netra_backend.app.websocket_core.websocket_manager.check_websocket_service_available',
                       return_value=True), \
                 patch('netra_backend.app.websocket_core.websocket_manager.get_config') as mock_config, \
                 patch('netra_backend.app.websocket_core.websocket_manager._UnifiedWebSocketManagerImplementation') as mock_ws_impl:

                mock_config.return_value = Mock()
                mock_ws_impl.return_value = Mock()

                # Should succeed with healthy services
                try:
                    manager = await get_websocket_manager_async(
                        user_context=mock_user_context,
                        app=mock_app
                    )
                    # If we get here, the service availability check passed
                    self.assertIsNotNone(manager)
                except Exception as e:
                    # Should not raise exception with healthy services
                    self.fail(f"WebSocket manager creation failed with healthy services: {e}")

    async def test_websocket_manager_service_unavailable_scenario(self):
        """Test WebSocket manager creation when critical services are unavailable."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager_async

        mock_app = Mock()
        mock_user_context = Mock()
        mock_user_context.user_id = "test_user_123"

        # Mock unhealthy service environment
        with patch('netra_backend.app.websocket_core.service_availability_manager.ServiceAvailabilityManager') as mock_sam_class:
            mock_sam_instance = Mock()
            mock_sam_class.return_value = mock_sam_instance

            # Mock unhealthy service report
            mock_health_report = {
                "overall_status": "degraded",
                "summary": {
                    "health_summary": "Critical services failed",
                    "failed_services": ["authentication"],
                    "degraded_services": []
                }
            }
            mock_sam_instance.get_health_report = AsyncMock(return_value=mock_health_report)
            mock_sam_instance.should_allow_websocket_connection = Mock(
                return_value=(False, "Critical services unavailable: authentication")
            )

            with patch('netra_backend.app.websocket_core.service_availability_manager.get_service_availability_manager',
                       return_value=mock_sam_instance), \
                 patch('netra_backend.app.websocket_core.websocket_manager.get_config') as mock_config:

                mock_config_instance = Mock()
                mock_config_instance.allow_degraded_websocket = False
                mock_config.return_value = mock_config_instance

                # Should raise RuntimeError when critical services are unavailable
                with self.assertRaises(RuntimeError) as context:
                    await get_websocket_manager_async(
                        user_context=mock_user_context,
                        app=mock_app
                    )

                self.assertIn("WebSocket connection denied", str(context.exception))

    async def test_service_availability_circuit_breaker_integration(self):
        """Test circuit breaker integration with real service checks."""
        manager = ServiceAvailabilityManager()

        # Simulate multiple authentication service failures
        for i in range(manager._max_consecutive_failures):
            manager._update_service_health(
                ServiceType.AUTHENTICATION,
                ServiceStatus.FAILED,
                f"Connection timeout {i+1}"
            )

        # Circuit breaker should be open
        auth_health = manager.service_health[ServiceType.AUTHENTICATION]
        self.assertTrue(auth_health.circuit_breaker_open)

        # Service should not be available
        self.assertFalse(manager.is_service_available(ServiceType.AUTHENTICATION))

        # WebSocket connections should be denied
        allow, reason = manager.should_allow_websocket_connection()
        self.assertFalse(allow)
        self.assertIn("Critical services unavailable", reason)

    async def test_degraded_service_graceful_handling(self):
        """Test graceful handling of degraded but functional services."""
        manager = ServiceAvailabilityManager()

        # Set critical services as healthy
        manager._update_service_health(ServiceType.AUTHENTICATION, ServiceStatus.HEALTHY)
        manager._update_service_health(ServiceType.DATABASE_POSTGRES, ServiceStatus.HEALTHY)

        # Set optional services as degraded
        manager._update_service_health(ServiceType.AGENT_BRIDGE, ServiceStatus.DEGRADED, "Bridge issues")
        manager._update_service_health(ServiceType.DATABASE_REDIS, ServiceStatus.DEGRADED, "Redis slow")

        # Should still allow connections with degraded optional services
        allow, reason = manager.should_allow_websocket_connection()
        self.assertTrue(allow)
        self.assertIsNone(reason)

        # Health report should reflect degraded state
        health_report = await manager.get_health_report()
        self.assertEqual(health_report["overall_status"], "healthy")  # Critical services healthy
        self.assertTrue(health_report["allow_websocket_connections"])

        degraded = health_report["summary"]["degraded_services"]
        self.assertIn("agent_bridge", degraded)
        self.assertIn("database_redis", degraded)

    async def test_real_service_import_health_checks(self):
        """Test health checks with real service imports (no mocking)."""
        manager = ServiceAvailabilityManager()

        # Test authentication service import
        try:
            status, error, response_time = await manager._check_authentication_service()
            # Should either succeed or fail gracefully
            self.assertIn(status, [ServiceStatus.HEALTHY, ServiceStatus.FAILED, ServiceStatus.DEGRADED])
            if status == ServiceStatus.FAILED:
                self.assertIsNotNone(error)
            self.assertIsNotNone(response_time)
        except Exception as e:
            self.fail(f"Authentication service health check raised unexpected exception: {e}")

        # Test thread service import
        try:
            status, error, response_time = await manager._check_thread_service()
            # Should either succeed or fail gracefully
            self.assertIn(status, [ServiceStatus.HEALTHY, ServiceStatus.FAILED])
            self.assertIsNotNone(response_time)
        except Exception as e:
            self.fail(f"Thread service health check raised unexpected exception: {e}")

        # Test agent supervisor import
        try:
            status, error, response_time = await manager._check_agent_supervisor()
            # Should either succeed or fail gracefully
            self.assertIn(status, [ServiceStatus.HEALTHY, ServiceStatus.FAILED])
            self.assertIsNotNone(response_time)
        except Exception as e:
            self.fail(f"Agent supervisor health check raised unexpected exception: {e}")


if __name__ == '__main__':
    # Run tests with asyncio support
    import pytest
    pytest.main([__file__, "-v"])