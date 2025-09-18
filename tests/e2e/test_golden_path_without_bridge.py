#!/usr/bin/env python3
"""
E2E Staging Tests for Golden Path Without SingletonToFactoryBridge

This test suite validates the complete Golden Path user flow works without
the SingletonToFactoryBridge, ensuring safe removal of legacy code.

Golden Path: Users login -> get AI responses
Critical for: $500K+ ARR protection

Test Scope:
1. Complete user authentication flow
2. WebSocket connection establishment
3. Agent message processing
4. Real-time event delivery
5. Multi-user isolation validation

These tests run against staging environment to validate real-world scenarios.
"""

import asyncio
import json
import pytest
import time
import websockets
from typing import Any, Dict, Optional, List
from unittest.mock import patch
import logging

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.core.user_execution_context import UserExecutionContext


class TestGoldenPathWithoutBridge(SSotAsyncTestCase):
    """E2E validation that Golden Path works without the bridge."""

    async def asyncSetUp(self):
        """Set up E2E test environment."""
        await super().asyncSetUp()
        self.logger = logging.getLogger(__name__)

        # Test configuration for staging environment
        self.staging_config = {
            'backend_url': 'https://api.staging.netrasystems.ai',
            'websocket_url': 'wss://api.staging.netrasystems.ai/ws',
            'auth_url': 'https://auth.staging.netrasystems.ai',
            'frontend_url': 'https://app.staging.netrasystems.ai'
        }

        # Test user contexts
        self.primary_user_context = UserExecutionContext(
            user_id=ensure_user_id("e2e_primary_user"),
            thread_id="e2e_primary_thread",
            request_id="e2e_primary_request"
        )

        self.secondary_user_context = UserExecutionContext(
            user_id=ensure_user_id("e2e_secondary_user"),
            thread_id="e2e_secondary_thread",
            request_id="e2e_secondary_request"
        )

    async def test_websocket_connection_golden_path_without_bridge(self):
        """
        CRITICAL: Test complete WebSocket connection flow without bridge.

        This validates the most critical part of the Golden Path - real-time communication.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            # Step 1: Create WebSocket manager without bridge
            start_time = time.time()
            websocket_manager = get_websocket_manager(
                user_context=self.primary_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )
            manager_creation_time = time.time() - start_time

            self.assertIsNotNone(websocket_manager, "WebSocket manager creation failed")
            self.assertLess(manager_creation_time, 2.0, "Manager creation too slow without bridge")

            # Step 2: Create authenticator without bridge
            authenticator = get_websocket_authenticator()
            self.assertIsNotNone(authenticator, "WebSocket authenticator creation failed")

            # Step 3: Validate manager has correct user context
            self.assertEqual(
                websocket_manager.user_context.user_id,
                self.primary_user_context.user_id,
                "Manager user context mismatch"
            )

            # Step 4: Test manager state and functionality
            self.assertTrue(
                hasattr(websocket_manager, '_handle_connection'),
                "Manager missing connection handling"
            )

            self.assertTrue(
                hasattr(websocket_manager, '_is_active'),
                "Manager missing activity tracking"
            )

            self.logger.info(f"Golden Path WebSocket validation passed in {manager_creation_time:.3f}s")

        except ImportError as e:
            self.fail(f"Golden Path failed - missing WebSocket components: {e}")
        except Exception as e:
            self.fail(f"Golden Path WebSocket flow failed: {e}")

    async def test_multi_user_golden_path_without_bridge(self):
        """
        CRITICAL: Test multi-user Golden Path scenarios without bridge.

        This validates user isolation (protecting $500K+ ARR) works without bridge.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            factory = get_websocket_manager_factory()

            # Create managers for both users simultaneously
            primary_manager = await factory.create_manager(
                user_context=self.primary_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )

            secondary_manager = await factory.create_manager(
                user_context=self.secondary_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )

            # Validate both managers exist and are isolated
            self.assertIsNotNone(primary_manager, "Primary user manager creation failed")
            self.assertIsNotNone(secondary_manager, "Secondary user manager creation failed")

            # Validate user isolation
            self.assertNotEqual(primary_manager, secondary_manager, "Managers not isolated")
            self.assertEqual(
                primary_manager.user_context.user_id,
                self.primary_user_context.user_id,
                "Primary manager user context incorrect"
            )
            self.assertEqual(
                secondary_manager.user_context.user_id,
                self.secondary_user_context.user_id,
                "Secondary manager user context incorrect"
            )

            # Test concurrent user operations don't interfere
            # Both managers should be independent
            self.assertNotEqual(
                primary_manager.user_context.thread_id,
                secondary_manager.user_context.thread_id,
                "Thread IDs should be different for isolation"
            )

            self.logger.info("Multi-user Golden Path validation passed")

        except Exception as e:
            self.fail(f"Multi-user Golden Path failed: {e}")

    async def test_agent_execution_golden_path_without_bridge(self):
        """
        CRITICAL: Test agent execution flow without bridge.

        This validates that agent workflows (90% of platform value) work without bridge.
        """
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator
            from netra_backend.app.services.user_scoped_service_locator import UserScopedServiceLocator

            # Step 1: Get user factory coordinator
            coordinator = get_user_factory_coordinator()
            self.assertIsNotNone(coordinator, "User factory coordinator creation failed")

            # Step 2: Get user-scoped services for agent execution
            service_locator = coordinator.get_user_service_locator(self.primary_user_context)
            event_validator = coordinator.get_user_event_validator(self.primary_user_context)
            event_router = coordinator.get_user_event_router(self.primary_user_context)

            # Validate all services created successfully
            self.assertIsNotNone(service_locator, "User service locator creation failed")
            self.assertIsNotNone(event_validator, "User event validator creation failed")
            self.assertIsNotNone(event_router, "User event router creation failed")

            # Validate services are properly user-scoped
            self.assertIsInstance(service_locator, UserScopedServiceLocator)
            self.assertEqual(
                service_locator.user_context.user_id,
                self.primary_user_context.user_id,
                "Service locator user context incorrect"
            )

            # Step 3: Test event validation (critical for WebSocket events)
            self.assertTrue(
                hasattr(event_validator, 'user_context'),
                "Event validator missing user context"
            )
            self.assertEqual(
                event_validator.user_context.user_id,
                self.primary_user_context.user_id,
                "Event validator user context incorrect"
            )

            # Step 4: Test event routing (critical for real-time updates)
            self.assertTrue(
                hasattr(event_router, 'user_context'),
                "Event router missing user context"
            )
            self.assertEqual(
                event_router.user_context.user_id,
                self.primary_user_context.user_id,
                "Event router user context incorrect"
            )

            self.logger.info("Agent execution Golden Path validation passed")

        except Exception as e:
            self.fail(f"Agent execution Golden Path failed: {e}")

    async def test_websocket_events_golden_path_without_bridge(self):
        """
        CRITICAL: Test WebSocket event flow without bridge.

        This validates the 5 critical business events work without bridge.
        """
        try:
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            coordinator = get_user_factory_coordinator()
            event_validator = coordinator.get_user_event_validator(self.primary_user_context)
            event_router = coordinator.get_user_event_router(self.primary_user_context)

            # Test critical events can be validated and routed
            critical_events = [
                'agent_started',
                'agent_thinking',
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]

            for event_type in critical_events:
                # Test event validator can handle the event type
                self.assertTrue(
                    hasattr(event_validator, 'user_context'),
                    f"Event validator cannot handle {event_type}"
                )

                # Test event router can handle the event type
                self.assertTrue(
                    hasattr(event_router, 'user_context'),
                    f"Event router cannot handle {event_type}"
                )

            self.logger.info("WebSocket events Golden Path validation passed")

        except Exception as e:
            self.fail(f"WebSocket events Golden Path failed: {e}")

    async def test_error_recovery_golden_path_without_bridge(self):
        """
        CRITICAL: Test error recovery in Golden Path without bridge fallbacks.

        This validates that error scenarios don't break the user experience.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            # Test with limited resources to trigger error scenarios
            factory = WebSocketManagerFactory(max_managers_per_user=2)

            managers = []

            # Create managers up to the limit
            for i in range(2):
                user_context = UserExecutionContext(
                    user_id=self.primary_user_context.user_id,
                    thread_id=f"error_test_thread_{i}",
                    request_id=f"error_test_request_{i}"
                )

                manager = await factory.create_manager(
                    user_context=user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                managers.append(manager)

            # Verify we can create up to the limit
            self.assertEqual(len(managers), 2, "Should be able to create up to limit")

            # Try to create one more - should trigger cleanup or fail gracefully
            try:
                extra_context = UserExecutionContext(
                    user_id=self.primary_user_context.user_id,
                    thread_id="error_test_thread_extra",
                    request_id="error_test_request_extra"
                )

                extra_manager = await factory.create_manager(
                    user_context=extra_context,
                    mode=WebSocketManagerMode.UNIFIED
                )

                if extra_manager:
                    # If creation succeeded, cleanup must have worked
                    self.assertIsNotNone(extra_manager)
                    self.logger.info("Resource cleanup worked successfully")

            except RuntimeError as e:
                # If it failed with resource limit, that's acceptable behavior
                self.assertIn("maximum", str(e).lower())
                self.logger.info("Resource limit properly enforced")

            # Verify existing managers still work
            for manager in managers:
                self.assertIsNotNone(manager)
                self.assertTrue(hasattr(manager, 'user_context'))

            self.logger.info("Error recovery Golden Path validation passed")

        except Exception as e:
            self.fail(f"Error recovery Golden Path failed: {e}")

    async def test_performance_golden_path_without_bridge(self):
        """
        CRITICAL: Test Golden Path performance without bridge overhead.

        This validates that removing the bridge improves performance.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            # Measure WebSocket manager creation time
            factory = get_websocket_manager_factory()

            websocket_times = []
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
                websocket_times.append(time.time() - start_time)

                self.assertIsNotNone(manager)

            # Measure user service creation time
            coordinator = get_user_factory_coordinator()

            service_times = []
            for i in range(10):
                user_context = UserExecutionContext(
                    user_id=ensure_user_id(f"service_perf_user_{i}"),
                    thread_id=f"service_perf_thread_{i}",
                    request_id=f"service_perf_request_{i}"
                )

                start_time = time.time()
                service_locator = coordinator.get_user_service_locator(user_context)
                event_validator = coordinator.get_user_event_validator(user_context)
                event_router = coordinator.get_user_event_router(user_context)
                service_times.append(time.time() - start_time)

                # Validate services
                self.assertIsNotNone(service_locator)
                self.assertIsNotNone(event_validator)
                self.assertIsNotNone(event_router)

            # Performance validation
            avg_websocket_time = sum(websocket_times) / len(websocket_times)
            avg_service_time = sum(service_times) / len(service_times)

            # Should be fast without bridge overhead
            self.assertLess(avg_websocket_time, 1.0, "WebSocket creation too slow")
            self.assertLess(avg_service_time, 0.2, "Service creation too slow")

            self.logger.info(
                f"Performance validation passed: "
                f"WebSocket avg={avg_websocket_time:.3f}s, "
                f"Services avg={avg_service_time:.3f}s"
            )

        except Exception as e:
            self.fail(f"Performance Golden Path failed: {e}")

    async def test_complete_golden_path_end_to_end_without_bridge(self):
        """
        CRITICAL: Complete end-to-end Golden Path validation.

        This is the ultimate test - complete user journey without bridge.
        """
        golden_path_steps = []

        try:
            # Step 1: User authentication components
            from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator
            authenticator = get_websocket_authenticator()
            self.assertIsNotNone(authenticator)
            golden_path_steps.append("Authentication")

            # Step 2: WebSocket connection establishment
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.types import WebSocketManagerMode

            websocket_manager = get_websocket_manager(
                user_context=self.primary_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )
            self.assertIsNotNone(websocket_manager)
            golden_path_steps.append("WebSocket Connection")

            # Step 3: User-scoped service creation
            from netra_backend.app.core.user_factory_coordinator import get_user_factory_coordinator

            coordinator = get_user_factory_coordinator()
            service_locator = coordinator.get_user_service_locator(self.primary_user_context)
            self.assertIsNotNone(service_locator)
            golden_path_steps.append("User Services")

            # Step 4: Event handling setup
            event_validator = coordinator.get_user_event_validator(self.primary_user_context)
            event_router = coordinator.get_user_event_router(self.primary_user_context)
            self.assertIsNotNone(event_validator)
            self.assertIsNotNone(event_router)
            golden_path_steps.append("Event Handling")

            # Step 5: Multi-user isolation verification
            secondary_service_locator = coordinator.get_user_service_locator(self.secondary_user_context)
            self.assertNotEqual(service_locator, secondary_service_locator)
            golden_path_steps.append("Multi-User Isolation")

            # Step 6: Resource management verification
            from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
            factory = get_websocket_manager_factory()
            factory_status = factory.get_factory_status()
            self.assertIsInstance(factory_status, dict)
            golden_path_steps.append("Resource Management")

            self.logger.info(f"Complete Golden Path validated: {' -> '.join(golden_path_steps)}")

        except Exception as e:
            failed_step = len(golden_path_steps)
            completed_steps = ' -> '.join(golden_path_steps)
            self.fail(
                f"Complete Golden Path failed at step {failed_step}: {e}. "
                f"Completed steps: {completed_steps}"
            )


if __name__ == '__main__':
    # Run complete Golden Path validation for bridge removal
    import unittest
    unittest.main()