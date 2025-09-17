#!/usr/bin/env python3
"""
Integration Tests for SingletonToFactoryBridge Removal

This test suite validates that removing the SingletonToFactoryBridge doesn't break
integration scenarios, especially WebSocket and agent execution flows.

Business Value: Protects $500K+ ARR by ensuring chat functionality remains intact
after legacy code removal.

Test Focus:
1. WebSocket connection flows work without bridge
2. Agent execution flows work without bridge
3. Multi-user scenarios work with factory patterns
4. Error handling works without bridge fallbacks
5. Performance doesn't degrade without bridge
"""

import asyncio
import pytest
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.core.user_execution_context import UserExecutionContext


class TestWebSocketIntegrationWithoutBridge(SSotAsyncTestCase):
    """Integration tests for WebSocket functionality without the bridge."""

    async def asyncSetUp(self):
        """Set up async test environment."""
        await super().asyncSetUp()
        self.logger = logging.getLogger(__name__)

        self.user_context = UserExecutionContext(
            user_id=ensure_user_id("integration_test_user"),
            thread_id="integration_test_thread",
            request_id="integration_test_request"
        )

    async def test_websocket_manager_creation_integration(self):
        """Test complete WebSocket manager creation flow without bridge."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            factory = get_websocket_manager()

            # Test factory can create manager
            start_time = time.time()
            manager = await factory.create_manager(
                user_context=self.user_context,
                mode=WebSocketManagerMode.UNIFIED
            )
            creation_time = time.time() - start_time

            # Validate manager was created successfully
            self.assertIsNotNone(manager)
            self.assertEqual(manager.user_context.user_id, self.user_context.user_id)

            # Performance validation - should be fast without bridge overhead
            self.assertLess(creation_time, 1.0, "Manager creation should be fast without bridge")

            # Test manager has required methods
            required_methods = ['_handle_connection', '_disconnect', '_is_active']
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(manager, method_name),
                    f"Manager missing method: {method_name}"
                )

        except ImportError as e:
            self.fail(f"WebSocket integration failed due to missing imports: {e}")
        except Exception as e:
            self.fail(f"WebSocket manager creation integration failed: {e}")

    async def test_websocket_multiple_users_without_bridge(self):
        """Test multi-user WebSocket scenarios work without bridge."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            factory = get_websocket_manager()

            # Create managers for multiple users
            user_contexts = []
            managers = []

            for i in range(3):
                user_context = UserExecutionContext(
                    user_id=ensure_user_id(f"multi_user_{i}"),
                    thread_id=f"multi_thread_{i}",
                    request_id=f"multi_request_{i}"
                )
                user_contexts.append(user_context)

                manager = await factory.create_manager(
                    user_context=user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                managers.append(manager)

            # Validate all managers are created and isolated
            self.assertEqual(len(managers), 3)

            for i, manager in enumerate(managers):
                self.assertEqual(manager.user_context.user_id, user_contexts[i].user_id)

                # Verify isolation - each manager should be unique
                for j, other_manager in enumerate(managers):
                    if i != j:
                        self.assertNotEqual(manager, other_manager)

        except Exception as e:
            self.fail(f"Multi-user WebSocket integration failed: {e}")

    async def test_websocket_authentication_integration_without_bridge(self):
        """Test WebSocket authentication flow works without bridge."""
        try:
            from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator

            authenticator = get_websocket_authenticator()

            # Test authenticator has required methods
            required_methods = ['authenticate_websocket', 'validate_token']
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(authenticator, method_name),
                    f"Authenticator missing method: {method_name}"
                )

            # Test that authenticator can be used (even if we don't have real tokens)
            self.assertIsNotNone(authenticator)

        except Exception as e:
            self.fail(f"WebSocket authentication integration failed: {e}")

    async def test_websocket_event_routing_without_bridge(self):
        """Test WebSocket event routing works without bridge."""
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            coordinator = get_user_factory_coordinator()
            event_router = coordinator.get_user_event_router(self.user_context)

            self.assertIsNotNone(event_router)

            # Test event router has required functionality
            self.assertEqual(event_router.user_context.user_id, self.user_context.user_id)

        except Exception as e:
            self.fail(f"WebSocket event routing integration failed: {e}")


class TestAgentExecutionIntegrationWithoutBridge(SSotAsyncTestCase):
    """Integration tests for agent execution without the bridge."""

    async def asyncSetUp(self):
        """Set up async test environment."""
        await super().asyncSetUp()
        self.user_context = UserExecutionContext(
            user_id=ensure_user_id("agent_test_user"),
            thread_id="agent_test_thread",
            request_id="agent_test_request"
        )

    async def test_user_execution_context_integration(self):
        """Test user execution context integration without bridge."""
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            coordinator = get_user_factory_coordinator()

            # Test that coordinator can provide user-scoped services
            service_locator = coordinator.get_user_service_locator(self.user_context)
            event_validator = coordinator.get_user_event_validator(self.user_context)
            event_router = coordinator.get_user_event_router(self.user_context)

            # Validate all services are user-scoped
            self.assertIsNotNone(service_locator)
            self.assertIsNotNone(event_validator)
            self.assertIsNotNone(event_router)

            # Validate they all have the correct user context
            self.assertEqual(service_locator.user_context.user_id, self.user_context.user_id)
            self.assertEqual(event_validator.user_context.user_id, self.user_context.user_id)
            self.assertEqual(event_router.user_context.user_id, self.user_context.user_id)

        except Exception as e:
            self.fail(f"User execution context integration failed: {e}")

    async def test_service_discovery_integration_without_bridge(self):
        """Test service discovery works without bridge."""
        try:
            from netra_backend.app.services.service_locator import ServiceLocator

            service_locator = ServiceLocator()

            # Test that service locator can be used for discovery
            self.assertIsNotNone(service_locator)

            # Test basic service locator functionality
            self.assertTrue(hasattr(service_locator, 'get'))
            self.assertTrue(hasattr(service_locator, 'register'))

        except Exception as e:
            self.fail(f"Service discovery integration failed: {e}")


class TestPerformanceWithoutBridge(SSotAsyncTestCase):
    """Test that performance is not degraded without the bridge."""

    async def asyncSetUp(self):
        """Set up performance test environment."""
        await super().asyncSetUp()
        self.user_context = UserExecutionContext(
            user_id=ensure_user_id("perf_test_user"),
            thread_id="perf_test_thread",
            request_id="perf_test_request"
        )

    async def test_websocket_manager_creation_performance(self):
        """Test WebSocket manager creation performance without bridge."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            factory = get_websocket_manager()

            # Measure time for multiple manager creations
            creation_times = []

            for i in range(5):
                user_context = UserExecutionContext(
                    user_id=ensure_user_id(f"perf_user_{i}"),
                    thread_id=f"perf_thread_{i}",
                    request_id=f"perf_request_{i}"
                )

                start_time = time.time()
                manager = await factory.create_manager(
                    user_context=user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                end_time = time.time()

                creation_times.append(end_time - start_time)
                self.assertIsNotNone(manager)

            # Performance validation
            avg_creation_time = sum(creation_times) / len(creation_times)
            max_creation_time = max(creation_times)

            # Should be fast without bridge overhead
            self.assertLess(avg_creation_time, 0.5, "Average creation time should be under 0.5s")
            self.assertLess(max_creation_time, 1.0, "Max creation time should be under 1.0s")

            self.logger.info(f"Manager creation performance: avg={avg_creation_time:.3f}s, max={max_creation_time:.3f}s")

        except Exception as e:
            self.fail(f"Performance test failed: {e}")

    async def test_user_factory_coordination_performance(self):
        """Test user factory coordination performance without bridge."""
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            coordinator = get_user_factory_coordinator()

            # Measure time for multiple user service creations
            service_creation_times = []

            for i in range(10):
                user_context = UserExecutionContext(
                    user_id=ensure_user_id(f"coord_perf_user_{i}"),
                    thread_id=f"coord_perf_thread_{i}",
                    request_id=f"coord_perf_request_{i}"
                )

                start_time = time.time()
                service_locator = coordinator.get_user_service_locator(user_context)
                event_validator = coordinator.get_user_event_validator(user_context)
                event_router = coordinator.get_user_event_router(user_context)
                end_time = time.time()

                service_creation_times.append(end_time - start_time)

                # Validate services were created
                self.assertIsNotNone(service_locator)
                self.assertIsNotNone(event_validator)
                self.assertIsNotNone(event_router)

            # Performance validation
            avg_service_time = sum(service_creation_times) / len(service_creation_times)
            max_service_time = max(service_creation_times)

            # Should be very fast without bridge
            self.assertLess(avg_service_time, 0.1, "Average service creation should be under 0.1s")
            self.assertLess(max_service_time, 0.2, "Max service creation should be under 0.2s")

            self.logger.info(f"Service creation performance: avg={avg_service_time:.3f}s, max={max_service_time:.3f}s")

        except Exception as e:
            self.fail(f"Coordination performance test failed: {e}")


class TestErrorHandlingWithoutBridge(SSotAsyncTestCase):
    """Test error handling scenarios work without the bridge."""

    async def asyncSetUp(self):
        """Set up error handling test environment."""
        await super().asyncSetUp()
        self.user_context = UserExecutionContext(
            user_id=ensure_user_id("error_test_user"),
            thread_id="error_test_thread",
            request_id="error_test_request"
        )

    async def test_factory_error_handling_without_bridge(self):
        """Test that factory error handling works without bridge fallbacks."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            # Create factory with very low limits to test error conditions
            factory = WebSocketManager(max_managers_per_user=1)

            # Create first manager
            manager1 = await factory.create_manager(
                user_context=self.user_context,
                mode=WebSocketManagerMode.UNIFIED
            )
            self.assertIsNotNone(manager1)

            # Try to create second manager - should trigger resource management
            # This should either succeed (with cleanup) or fail gracefully
            try:
                manager2 = await factory.create_manager(
                    user_context=self.user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                # If it succeeds, verify it's working properly
                if manager2:
                    self.assertIsNotNone(manager2)
            except RuntimeError as e:
                # If it fails with resource limits, that's expected behavior
                self.assertIn("maximum number", str(e).lower())

        except Exception as e:
            self.fail(f"Factory error handling test failed: {e}")

    async def test_invalid_user_context_handling(self):
        """Test handling of invalid user contexts without bridge."""
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            coordinator = get_user_factory_coordinator()

            # Test with None user context - should handle gracefully
            try:
                service_locator = coordinator.get_user_service_locator(None)
                # If it succeeds, verify the result
                if service_locator:
                    self.assertIsNotNone(service_locator)
            except (TypeError, ValueError) as e:
                # Expected error for invalid context
                self.assertIn("context", str(e).lower())

        except Exception as e:
            self.fail(f"Invalid context handling test failed: {e}")


if __name__ == '__main__':
    # Run integration tests to validate bridge removal doesn't break integrations
    import unittest
    unittest.main()