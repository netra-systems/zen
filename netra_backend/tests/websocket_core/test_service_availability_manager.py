"""
Unit Tests for ServiceAvailabilityManager - Issue #895 Implementation

Tests the comprehensive service availability detection system that prevents
1011 WebSocket errors by checking service health before connection attempts.

Test Categories:
1. Service Health Checking - Individual service health validation
2. Circuit Breaker Pattern - Failure detection and recovery
3. Service Dependency Mapping - Critical vs optional service classification
4. Graceful Degradation - Connection allowance decision logic
5. Health Reporting - Comprehensive health report generation

Non-Docker Test Approach:
- Uses real service imports but mocks external dependencies
- Focuses on logic validation without requiring Docker infrastructure
- Tests circuit breaker patterns with simulated failures
- Validates health check algorithms and decision making
"""

import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any

# Test framework imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from netra_backend.app.websocket_core.service_availability_manager import (
    ServiceAvailabilityManager,
    ServiceType,
    ServiceStatus,
    ServiceHealthInfo,
    ServiceDependencyMap,
    get_service_availability_manager,
    check_websocket_services_health
)


class TestServiceAvailabilityManager(unittest.TestCase):
    """Test ServiceAvailabilityManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ServiceAvailabilityManager()

    def tearDown(self):
        """Clean up after tests."""
        # Reset global manager instance
        import netra_backend.app.websocket_core.service_availability_manager as sam_module
        sam_module._service_availability_manager = None

    def test_initialization(self):
        """Test ServiceAvailabilityManager initialization."""
        # Verify initial state
        self.assertIsInstance(self.manager.service_health, dict)
        self.assertIsInstance(self.manager.dependency_map, ServiceDependencyMap)

        # Verify all service types are initialized
        for service_type in ServiceType:
            self.assertIn(service_type, self.manager.service_health)
            health_info = self.manager.service_health[service_type]
            self.assertEqual(health_info.status, ServiceStatus.UNKNOWN)
            self.assertEqual(health_info.consecutive_failures, 0)
            self.assertFalse(health_info.circuit_breaker_open)

    def test_service_dependency_mapping(self):
        """Test service dependency classification."""
        # Verify critical services
        critical_services = self.manager.dependency_map.critical_services
        self.assertIn(ServiceType.AUTHENTICATION, critical_services)
        self.assertIn(ServiceType.DATABASE_POSTGRES, critical_services)

        # Verify optional services
        optional_services = self.manager.dependency_map.optional_services
        self.assertIn(ServiceType.AGENT_BRIDGE, optional_services)
        self.assertIn(ServiceType.THREAD_SERVICE, optional_services)
        self.assertIn(ServiceType.DATABASE_REDIS, optional_services)

        # Verify no overlap between critical and optional
        self.assertEqual(len(critical_services.intersection(optional_services)), 0)

    @patch('netra_backend.app.websocket_core.service_availability_manager.get_logger')
    async def test_authentication_service_health_check_success(self, mock_logger):
        """Test successful authentication service health check."""
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
            # Mock successful auth service
            mock_auth_instance = Mock()
            mock_auth_instance.health_check = AsyncMock()
            mock_auth.return_value = mock_auth_instance

            status, error, response_time = await self.manager._check_authentication_service()

            self.assertEqual(status, ServiceStatus.HEALTHY)
            self.assertIsNone(error)
            self.assertIsNotNone(response_time)
            self.assertGreater(response_time, 0)

    @patch('netra_backend.app.websocket_core.service_availability_manager.get_logger')
    async def test_authentication_service_health_check_failure(self, mock_logger):
        """Test authentication service health check failure."""
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
            # Mock auth service that raises exception
            mock_auth.side_effect = Exception("Auth service unavailable")

            status, error, response_time = await self.manager._check_authentication_service()

            self.assertEqual(status, ServiceStatus.FAILED)
            self.assertIn("Auth service unavailable", error)
            self.assertIsNotNone(response_time)

    async def test_agent_bridge_service_health_check_with_app_state(self):
        """Test agent bridge health check with properly initialized app state."""
        # Create mock app with bridge in state
        mock_app = Mock()
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = Mock()
        mock_bridge.notify_agent_completed = Mock()
        mock_bridge.notify_tool_executing = Mock()
        mock_app.state.agent_websocket_bridge = mock_bridge

        manager = ServiceAvailabilityManager(mock_app)
        status, error, response_time = await manager._check_agent_bridge_service()

        self.assertEqual(status, ServiceStatus.HEALTHY)
        self.assertIsNone(error)
        self.assertIsNotNone(response_time)

    async def test_agent_bridge_service_health_check_missing_methods(self):
        """Test agent bridge health check with missing required methods."""
        # Create mock app with incomplete bridge
        mock_app = Mock()
        mock_bridge = Mock()
        # Only provide some methods, missing others
        mock_bridge.notify_agent_started = Mock()
        # Missing notify_agent_completed and notify_tool_executing
        mock_app.state.agent_websocket_bridge = mock_bridge

        manager = ServiceAvailabilityManager(mock_app)
        status, error, response_time = await manager._check_agent_bridge_service()

        self.assertEqual(status, ServiceStatus.DEGRADED)
        self.assertIn("missing methods", error)

    async def test_database_health_checks(self):
        """Test database health check methods."""
        with patch('netra_backend.app.db.database_manager.DatabaseManager') as mock_db_class:
            # Mock successful database manager
            mock_db_instance = Mock()
            mock_db_instance.get_postgres_pool.return_value = Mock()  # Non-None pool
            mock_db_instance.get_redis_client.return_value = Mock()   # Non-None client
            mock_db_class.return_value = mock_db_instance

            # Test PostgreSQL check
            status, error, response_time = await self.manager._check_postgres_database()
            self.assertEqual(status, ServiceStatus.HEALTHY)
            self.assertIsNone(error)

            # Test Redis check
            status, error, response_time = await self.manager._check_redis_database()
            self.assertEqual(status, ServiceStatus.HEALTHY)
            self.assertIsNone(error)

    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern for failing services."""
        service_type = ServiceType.AUTHENTICATION

        # Simulate multiple failures
        for i in range(self.manager._max_consecutive_failures):
            self.manager._update_service_health(
                service_type, ServiceStatus.FAILED, f"Failure {i+1}"
            )

        health_info = self.manager.service_health[service_type]

        # Verify circuit breaker is open
        self.assertTrue(health_info.circuit_breaker_open)
        self.assertIsNotNone(health_info.circuit_breaker_until)
        self.assertEqual(health_info.consecutive_failures, self.manager._max_consecutive_failures)

        # Service should not be available when circuit breaker is open
        self.assertFalse(self.manager.is_service_available(service_type))

    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        service_type = ServiceType.AUTHENTICATION

        # Simulate circuit breaker opening
        for i in range(self.manager._max_consecutive_failures):
            self.manager._update_service_health(
                service_type, ServiceStatus.FAILED, f"Failure {i+1}"
            )

        # Manually set circuit breaker timeout to past
        health_info = self.manager.service_health[service_type]
        health_info.circuit_breaker_until = datetime.now() - timedelta(seconds=1)

        # Service should allow one test attempt
        self.assertTrue(self.manager.is_service_available(service_type))

        # Simulate successful recovery
        self.manager._update_service_health(service_type, ServiceStatus.HEALTHY)

        # Circuit breaker should be closed
        self.assertFalse(health_info.circuit_breaker_open)
        self.assertIsNone(health_info.circuit_breaker_until)

    async def test_critical_services_availability_check(self):
        """Test critical services availability checking."""
        # Set all critical services to healthy
        for service_type in self.manager.dependency_map.critical_services:
            self.manager._update_service_health(service_type, ServiceStatus.HEALTHY)

        # All critical services should be available
        self.assertTrue(self.manager.are_critical_services_available())

        # Fail one critical service
        critical_service = next(iter(self.manager.dependency_map.critical_services))
        self.manager._update_service_health(critical_service, ServiceStatus.FAILED)

        # Should report critical services as unavailable
        self.assertFalse(self.manager.are_critical_services_available())

    async def test_websocket_connection_decision_logic(self):
        """Test WebSocket connection allowance decision logic."""
        # Test with all services healthy
        for service_type in ServiceType:
            self.manager._update_service_health(service_type, ServiceStatus.HEALTHY)

        allow, reason = self.manager.should_allow_websocket_connection()
        self.assertTrue(allow)
        self.assertIsNone(reason)

        # Test with critical service failed
        critical_service = next(iter(self.manager.dependency_map.critical_services))
        self.manager._update_service_health(critical_service, ServiceStatus.FAILED)

        allow, reason = self.manager.should_allow_websocket_connection()
        self.assertFalse(allow)
        self.assertIn("Critical services unavailable", reason)

        # Test with too many degraded services
        for service_type in ServiceType:
            self.manager._update_service_health(service_type, ServiceStatus.DEGRADED)

        allow, reason = self.manager.should_allow_websocket_connection()
        self.assertFalse(allow)
        self.assertIn("Too many degraded services", reason)

    async def test_health_report_generation(self):
        """Test comprehensive health report generation."""
        # Set mixed service states
        auth_service = ServiceType.AUTHENTICATION
        bridge_service = ServiceType.AGENT_BRIDGE

        self.manager._update_service_health(auth_service, ServiceStatus.HEALTHY)
        self.manager._update_service_health(bridge_service, ServiceStatus.DEGRADED, "Bridge issues")

        report = await self.manager.get_health_report()

        # Verify report structure
        self.assertIn("overall_status", report)
        self.assertIn("allow_websocket_connections", report)
        self.assertIn("critical_services", report)
        self.assertIn("optional_services", report)
        self.assertIn("summary", report)

        # Verify critical service details
        auth_info = report["critical_services"][auth_service.value]
        self.assertTrue(auth_info["available"])
        self.assertEqual(auth_info["status"], ServiceStatus.HEALTHY.value)

        # Verify optional service details
        bridge_info = report["optional_services"][bridge_service.value]
        self.assertTrue(bridge_info["available"])  # Degraded but available
        self.assertEqual(bridge_info["status"], ServiceStatus.DEGRADED.value)
        self.assertEqual(bridge_info["error"], "Bridge issues")

    async def test_service_health_summary(self):
        """Test service health summary generation."""
        # Set up mixed service states
        self.manager._update_service_health(ServiceType.AUTHENTICATION, ServiceStatus.HEALTHY)
        self.manager._update_service_health(ServiceType.AGENT_BRIDGE, ServiceStatus.DEGRADED)
        self.manager._update_service_health(ServiceType.THREAD_SERVICE, ServiceStatus.FAILED)
        # Leave others as UNKNOWN

        summary = self.manager._get_health_summary()

        # Should reflect the counts
        self.assertIn("Healthy: 1", summary)
        self.assertIn("Degraded: 1", summary)
        self.assertIn("Failed: 1", summary)
        self.assertIn("Unknown: 4", summary)  # Remaining services

    async def test_get_degraded_and_failed_services(self):
        """Test getting lists of degraded and failed services."""
        # Set up test states
        self.manager._update_service_health(ServiceType.AUTHENTICATION, ServiceStatus.HEALTHY)
        self.manager._update_service_health(ServiceType.AGENT_BRIDGE, ServiceStatus.DEGRADED)
        self.manager._update_service_health(ServiceType.THREAD_SERVICE, ServiceStatus.FAILED)

        degraded = self.manager.get_degraded_services()
        failed = self.manager.get_failed_services()

        self.assertEqual(degraded, [ServiceType.AGENT_BRIDGE])
        self.assertEqual(failed, [ServiceType.THREAD_SERVICE])

    async def test_comprehensive_service_check(self):
        """Test comprehensive service checking."""
        # Mock individual service check methods
        with patch.object(self.manager, '_check_authentication_service',
                         return_value=(ServiceStatus.HEALTHY, None, 10.5)) as mock_auth, \
             patch.object(self.manager, '_check_agent_bridge_service',
                         return_value=(ServiceStatus.DEGRADED, "Bridge issue", 20.3)) as mock_bridge:

            results = await self.manager.check_all_services()

            # Verify all services were checked
            self.assertEqual(len(results), len(ServiceType))

            # Verify auth service result
            auth_health = results[ServiceType.AUTHENTICATION]
            self.assertEqual(auth_health.status, ServiceStatus.HEALTHY)
            self.assertEqual(auth_health.response_time_ms, 10.5)

            # Verify bridge service result
            bridge_health = results[ServiceType.AGENT_BRIDGE]
            self.assertEqual(bridge_health.status, ServiceStatus.DEGRADED)
            self.assertEqual(bridge_health.error_message, "Bridge issue")


class TestServiceAvailabilityManagerGlobal(unittest.TestCase):
    """Test global ServiceAvailabilityManager functions."""

    def tearDown(self):
        """Clean up global state."""
        import netra_backend.app.websocket_core.service_availability_manager as sam_module
        sam_module._service_availability_manager = None

    def test_get_service_availability_manager_singleton(self):
        """Test global manager singleton behavior."""
        manager1 = get_service_availability_manager()
        manager2 = get_service_availability_manager()

        # Should return the same instance
        self.assertIs(manager1, manager2)

    def test_get_service_availability_manager_with_app(self):
        """Test global manager initialization with app."""
        mock_app = Mock()
        manager = get_service_availability_manager(mock_app)

        self.assertIs(manager.app, mock_app)

    async def test_check_websocket_services_health_convenience(self):
        """Test convenience function for health checking."""
        mock_app = Mock()

        # Mock the health report
        with patch.object(ServiceAvailabilityManager, 'get_health_report') as mock_health:
            mock_health.return_value = {"status": "healthy", "test": True}

            result = await check_websocket_services_health(mock_app)

            self.assertEqual(result["status"], "healthy")
            self.assertTrue(result["test"])


class TestServiceAvailabilityIntegration(unittest.TestCase):
    """Integration tests for ServiceAvailabilityManager with WebSocket system."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.manager = ServiceAvailabilityManager()

    async def test_integration_with_websocket_manager_creation(self):
        """Test integration with WebSocket manager creation flow."""
        # This would be tested in a higher-level integration test
        # For now, verify the manager can be created and basic checks work

        # Simulate service availability check for WebSocket creation
        for service_type in [ServiceType.AUTHENTICATION, ServiceType.DATABASE_POSTGRES]:
            self.manager._update_service_health(service_type, ServiceStatus.HEALTHY)

        allow, reason = self.manager.should_allow_websocket_connection()
        self.assertTrue(allow)

        # Simulate failure of critical service
        self.manager._update_service_health(ServiceType.AUTHENTICATION, ServiceStatus.FAILED)

        allow, reason = self.manager.should_allow_websocket_connection()
        self.assertFalse(allow)

    async def test_health_check_endpoint_integration(self):
        """Test health check endpoint integration."""
        # Simulate various service states
        self.manager._update_service_health(ServiceType.AUTHENTICATION, ServiceStatus.HEALTHY)
        self.manager._update_service_health(ServiceType.AGENT_BRIDGE, ServiceStatus.DEGRADED)

        health_report = await self.manager.get_health_report()

        # Verify report can be used in health endpoint
        self.assertIn("overall_status", health_report)
        self.assertIn("allow_websocket_connections", health_report)
        self.assertIn("service_availability", health_report)


if __name__ == '__main__':
    # Run tests with asyncio support
    import pytest
    pytest.main([__file__, "-v"])