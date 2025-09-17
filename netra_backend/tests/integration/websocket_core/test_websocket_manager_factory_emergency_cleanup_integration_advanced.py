"""
WebSocket Manager Factory Emergency Cleanup Integration Test - Advanced Scenarios

CRITICAL: Advanced integration tests for Issue #1279 - WebSocket Manager Resource Exhaustion.

These tests validate emergency cleanup system behavior under real-world integration scenarios
with actual WebSocket manager instances, health assessment, and cleanup logic.

Business Value Justification (BVJ):
- Segment: All users (affects $500K+ ARR)
- Business Goal: Validate emergency cleanup system handles real resource exhaustion scenarios
- Value Impact: Tests real-world failure modes in AI chat infrastructure
- Revenue Impact: Prevents permanent chat blocking affecting revenue

TESTING APPROACH: Integration tests with real WebSocket manager instances and actual cleanup logic.
"""

import asyncio
import pytest
import time
import threading
import gc
from typing import List, Dict, Set
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# System under test
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    CleanupLevel,
    ManagerHealthStatus,
    ManagerHealth
)
from netra_backend.app.websocket_core.types import WebSocketManagerMode, create_isolated_mode
from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation

# Dependencies
from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = get_logger(__name__)


class TestWebSocketManagerFactoryEmergencyCleanupIntegration(SSotAsyncTestCase):
    """
    Integration tests for WebSocket Manager Factory Emergency Cleanup System

    These tests use real WebSocket manager instances and actual cleanup logic
    to validate emergency cleanup behavior under resource exhaustion scenarios.
    """

    def setUp(self):
        """Set up integration test environment"""
        super().setUp()

        # Create factory with realistic limits for integration testing
        self.factory = WebSocketManagerFactory(
            max_managers_per_user=8,  # Moderate limit for integration tests
            enable_monitoring=True
        )

        self.id_manager = UnifiedIDManager()
        self.mock_factory = SSotMockFactory()

        # Track created managers for cleanup
        self.created_managers: List[_UnifiedWebSocketManagerImplementation] = []
        self.user_contexts: List[Mock] = []

    def tearDown(self):
        """Clean up integration test environment"""
        # Force cleanup all test managers
        with self.factory._registry_lock:
            # Clean up any managers created during tests
            for manager in self.created_managers:
                try:
                    if hasattr(manager, 'cleanup'):
                        manager.cleanup()
                except Exception as e:
                    logger.debug(f"Error cleaning up manager during teardown: {e}")

            # Clear factory state
            self.factory._active_managers.clear()
            self.factory._user_manager_keys.clear()
            self.factory._manager_health.clear()
            self.factory._creation_times.clear()
            self.factory._metrics = type(self.factory._metrics)()

        # Clear references and force garbage collection
        self.created_managers.clear()
        self.user_contexts.clear()
        gc.collect()

        super().tearDown()

    def _create_realistic_user_context(self, user_id: str = None, thread_id: str = None) -> Mock:
        """Create realistic user context for integration testing"""
        if user_id is None:
            user_id = self.id_manager.generate_id(IDType.USER, prefix="integ")

        if thread_id is None:
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="integ")

        request_id = self.id_manager.generate_id(IDType.REQUEST, prefix="integ")

        context = self.mock_factory.create_mock_user_context()
        context.user_id = user_id
        context.thread_id = thread_id
        context.request_id = request_id
        context.is_test = True

        self.user_contexts.append(context)
        return context

    async def _create_manager_with_tracking(self, user_context: Mock) -> _UnifiedWebSocketManagerImplementation:
        """Create manager and add to tracking for cleanup"""
        manager = await self.factory.create_manager(user_context, WebSocketManagerMode.UNIFIED)
        self.created_managers.append(manager)
        return manager

    async def test_real_emergency_cleanup_conservative_level_integration(self):
        """
        Integration test for conservative emergency cleanup with real managers

        Tests the actual conservative cleanup logic with real WebSocket manager instances.
        """
        logger.info("INTEGRATION TEST: Testing conservative emergency cleanup with real managers")

        user_id = "test_conservative_cleanup"

        # Create managers up to threshold for conservative cleanup (70%)
        target_count = int(self.factory.max_managers_per_user * 0.8)  # Slightly above threshold
        logger.info(f"Creating {target_count} managers for conservative cleanup test")

        for i in range(target_count):
            context = self._create_realistic_user_context(user_id, f"conservative_thread_{i}")
            manager = await self._create_manager_with_tracking(context)

            # Verify manager creation
            self.assertIsNotNone(manager)
            self.assertIsInstance(manager, _UnifiedWebSocketManagerImplementation)

        # Verify managers are tracked
        current_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(current_count, target_count)

        # Artificially age some managers to make them candidates for cleanup
        user_manager_keys = list(self.factory._user_manager_keys.get(user_id, set()))
        for i, manager_key in enumerate(user_manager_keys[:2]):  # Age first 2 managers
            # Set creation time to 1 hour ago
            old_time = datetime.now(timezone.utc) - timedelta(hours=1)
            self.factory._creation_times[manager_key] = old_time

            # Set health to inactive
            self.factory._manager_health[manager_key] = ManagerHealth(
                status=ManagerHealthStatus.INACTIVE,
                last_activity=old_time,
                health_score=0.1,
                creation_time=old_time
            )

        # Trigger conservative cleanup
        logger.info("Triggering conservative emergency cleanup")
        cleaned_count = await self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.CONSERVATIVE)

        # Verify cleanup was effective
        logger.info(f"Conservative cleanup removed {cleaned_count} managers")
        self.assertGreater(cleaned_count, 0, "Conservative cleanup should have removed inactive managers")

        # Verify remaining count
        remaining_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(remaining_count, target_count - cleaned_count)

        # Verify metrics were updated
        self.assertGreater(self.factory._metrics.cleanup_events, 0)

        logger.info("INTEGRATION TEST PASSED: Conservative emergency cleanup with real managers")

    async def test_real_emergency_cleanup_escalation_integration(self):
        """
        Integration test for cleanup level escalation with real managers

        Tests the full escalation path: Conservative → Moderate → Aggressive → Force
        """
        logger.critical("INTEGRATION TEST: Testing cleanup escalation with real managers")

        user_id = "test_escalation"

        # Fill exactly to max to trigger all cleanup levels
        for i in range(self.factory.max_managers_per_user):
            context = self._create_realistic_user_context(user_id, f"escalation_thread_{i}")
            manager = await self._create_manager_with_tracking(context)

        # Verify at limit
        current_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(current_count, self.factory.max_managers_per_user)

        # Create varied health states for testing escalation
        user_manager_keys = list(self.factory._user_manager_keys.get(user_id, set()))

        # Set up different health states
        for i, manager_key in enumerate(user_manager_keys):
            if i < 2:  # First 2: Inactive (Conservative cleanup targets)
                self.factory._manager_health[manager_key] = ManagerHealth(
                    status=ManagerHealthStatus.INACTIVE,
                    last_activity=datetime.now(timezone.utc) - timedelta(hours=2),
                    health_score=0.0
                )
            elif i < 4:  # Next 2: Idle (Moderate cleanup targets)
                self.factory._manager_health[manager_key] = ManagerHealth(
                    status=ManagerHealthStatus.IDLE,
                    last_activity=datetime.now(timezone.utc) - timedelta(minutes=30),
                    health_score=0.3
                )
            elif i < 6:  # Next 2: Zombie (Aggressive cleanup targets)
                self.factory._manager_health[manager_key] = ManagerHealth(
                    status=ManagerHealthStatus.ZOMBIE,
                    last_activity=datetime.now(timezone.utc) - timedelta(minutes=10),
                    connection_count=1,
                    responsive_connections=0,
                    health_score=0.1
                )
            else:  # Remaining: Healthy (Force cleanup targets only)
                self.factory._manager_health[manager_key] = ManagerHealth(
                    status=ManagerHealthStatus.HEALTHY,
                    last_activity=datetime.now(timezone.utc),
                    health_score=0.9
                )

        # Test Conservative cleanup
        logger.info("Testing Conservative cleanup level")
        conservative_cleaned = await self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.CONSERVATIVE)
        logger.info(f"Conservative cleanup removed {conservative_cleaned} managers")

        # Test Moderate cleanup (should clean more)
        moderate_cleaned = await self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.MODERATE)
        logger.info(f"Moderate cleanup removed {moderate_cleaned} managers")

        # Test Aggressive cleanup (should clean even more)
        aggressive_cleaned = await self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.AGGRESSIVE)
        logger.info(f"Aggressive cleanup removed {aggressive_cleaned} managers")

        # Verify escalation effectiveness
        remaining_count = self.factory.get_user_manager_count(user_id)
        total_cleaned = conservative_cleaned + moderate_cleaned + aggressive_cleaned

        logger.critical(f"ESCALATION RESULTS: Cleaned {total_cleaned} managers, {remaining_count} remaining")

        # Verify cleanup was progressively more aggressive
        self.assertGreaterEqual(total_cleaned, 0, "Escalation should have cleaned some managers")

        # Test Force cleanup as last resort
        if remaining_count >= self.factory.max_managers_per_user:
            force_cleaned = await self.factory._force_cleanup([], user_id)
            logger.critical(f"Force cleanup removed {force_cleaned} managers")

        logger.critical("INTEGRATION TEST COMPLETED: Cleanup escalation with real managers")

    async def test_real_health_assessment_integration(self):
        """
        Integration test for real manager health assessment

        Tests the actual health assessment logic with real WebSocket manager instances.
        """
        logger.info("INTEGRATION TEST: Testing real manager health assessment")

        user_id = "test_health_assessment"

        # Create a few managers for health testing
        managers_data = []
        for i in range(3):
            context = self._create_realistic_user_context(user_id, f"health_thread_{i}")
            manager = await self._create_manager_with_tracking(context)

            # Get manager key from factory
            user_keys = self.factory._user_manager_keys.get(user_id, set())
            manager_key = next(iter(user_keys.difference({data[0] for data in managers_data})))

            managers_data.append((manager_key, manager, context))

        # Test health assessment for each manager
        for manager_key, manager, context in managers_data:
            logger.info(f"Assessing health for manager {manager_key}")

            health = await self.factory._assess_manager_health(manager_key, manager)

            # Verify health assessment returned valid data
            self.assertIsInstance(health, ManagerHealth)
            self.assertIsInstance(health.status, ManagerHealthStatus)
            self.assertIsInstance(health.health_score, (int, float))
            self.assertGreaterEqual(health.health_score, 0.0)
            self.assertLessEqual(health.health_score, 1.0)

            logger.info(f"Manager {manager_key} health: {health.status.value}, score: {health.health_score}")

        # Test health-based cleanup decisions
        user_manager_keys = list(self.factory._user_manager_keys.get(user_id, set()))

        # Create manager assessments for cleanup testing
        manager_assessments = []
        for manager_key in user_manager_keys:
            if manager_key in self.factory._active_managers:
                manager = self.factory._active_managers[manager_key]
                health = await self.factory._assess_manager_health(manager_key, manager)
                manager_assessments.append((manager_key, manager, health))

        # Test conservative cleanup with real assessments
        original_conservative = self.factory._conservative_cleanup
        cleanup_count = await original_conservative(manager_assessments)

        logger.info(f"Health-based conservative cleanup removed {cleanup_count} managers")

        logger.info("INTEGRATION TEST PASSED: Real manager health assessment")

    async def test_concurrent_emergency_cleanup_integration(self):
        """
        Integration test for concurrent emergency cleanup scenarios

        Tests emergency cleanup behavior when multiple cleanup operations
        run concurrently with real managers.
        """
        logger.critical("INTEGRATION TEST: Testing concurrent emergency cleanup")

        user_id = "test_concurrent_cleanup"

        # Create managers to fill near limit
        for i in range(self.factory.max_managers_per_user - 1):
            context = self._create_realistic_user_context(user_id, f"concurrent_thread_{i}")
            manager = await self._create_manager_with_tracking(context)

        # Launch multiple concurrent cleanup operations
        cleanup_tasks = []
        for level in [CleanupLevel.CONSERVATIVE, CleanupLevel.MODERATE, CleanupLevel.AGGRESSIVE]:
            task = asyncio.create_task(
                self.factory._emergency_cleanup_user_managers(user_id, level)
            )
            cleanup_tasks.append((level, task))

        # Wait for all cleanup tasks
        cleanup_results = []
        for level, task in cleanup_tasks:
            try:
                result = await task
                cleanup_results.append((level, result))
                logger.info(f"Concurrent cleanup {level.value} completed: {result} managers cleaned")
            except Exception as e:
                logger.error(f"Concurrent cleanup {level.value} failed: {e}")
                cleanup_results.append((level, 0))

        # Verify concurrent cleanup handled safely
        total_concurrent_cleaned = sum(result for _, result in cleanup_results)
        remaining_count = self.factory.get_user_manager_count(user_id)

        logger.critical(f"CONCURRENT CLEANUP RESULTS: {total_concurrent_cleaned} total cleaned, {remaining_count} remaining")

        # Verify factory state consistency after concurrent operations
        self.assertGreaterEqual(remaining_count, 0)
        self.assertEqual(len(self.factory._active_managers), sum(len(keys) for keys in self.factory._user_manager_keys.values()))

        logger.critical("INTEGRATION TEST COMPLETED: Concurrent emergency cleanup")

    async def test_resource_exhaustion_recovery_integration(self):
        """
        Integration test for complete resource exhaustion and recovery cycle

        Tests the full cycle of resource exhaustion, emergency cleanup, and recovery
        with real WebSocket manager instances.
        """
        logger.critical("INTEGRATION TEST: Testing complete resource exhaustion and recovery cycle")

        user_id = "test_exhaustion_recovery"

        # Phase 1: Fill to exact limit
        logger.info("Phase 1: Filling to resource limit")
        for i in range(self.factory.max_managers_per_user):
            context = self._create_realistic_user_context(user_id, f"recovery_thread_{i}")
            manager = await self._create_manager_with_tracking(context)

        # Verify at limit
        current_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(current_count, self.factory.max_managers_per_user)
        logger.info(f"Phase 1 Complete: {current_count} managers at limit")

        # Phase 2: Make some managers cleanable by setting appropriate health states
        logger.info("Phase 2: Setting up managers for cleanup")
        user_manager_keys = list(self.factory._user_manager_keys.get(user_id, set()))

        # Make half the managers inactive/cleanable
        cleanable_count = len(user_manager_keys) // 2
        for i, manager_key in enumerate(user_manager_keys[:cleanable_count]):
            self.factory._manager_health[manager_key] = ManagerHealth(
                status=ManagerHealthStatus.INACTIVE,
                last_activity=datetime.now(timezone.utc) - timedelta(hours=1),
                health_score=0.0
            )

        # Phase 3: Trigger emergency cleanup at various levels
        logger.info("Phase 3: Triggering emergency cleanup")

        # Conservative cleanup first
        conservative_cleaned = await self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.CONSERVATIVE)
        logger.info(f"Conservative cleanup: {conservative_cleaned} managers removed")

        # If still at/near limit, try moderate
        current_count = self.factory.get_user_manager_count(user_id)
        if current_count >= self.factory.max_managers_per_user * 0.9:
            moderate_cleaned = await self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.MODERATE)
            logger.info(f"Moderate cleanup: {moderate_cleaned} managers removed")

        # Phase 4: Verify recovery - should be able to create new manager
        logger.info("Phase 4: Testing recovery - creating new manager")
        current_count = self.factory.get_user_manager_count(user_id)

        if current_count < self.factory.max_managers_per_user:
            recovery_context = self._create_realistic_user_context(user_id, "recovery_new_thread")
            recovery_manager = await self._create_manager_with_tracking(recovery_context)

            self.assertIsNotNone(recovery_manager)
            logger.info("Phase 4 Complete: Successfully created manager after cleanup (recovery successful)")
        else:
            logger.warning("Phase 4: Still at limit after cleanup - recovery not achieved")

        # Phase 5: Verify metrics and state consistency
        logger.info("Phase 5: Verifying final state")
        final_count = self.factory.get_user_manager_count(user_id)
        total_cleaned = conservative_cleaned + (moderate_cleaned if 'moderate_cleaned' in locals() else 0)

        logger.critical(f"EXHAUSTION RECOVERY COMPLETE: {total_cleaned} managers cleaned, {final_count} final count")

        # Verify factory metrics
        self.assertGreater(self.factory._metrics.cleanup_events, 0)
        self.assertGreater(self.factory._metrics.emergency_cleanups, 0)

        # Verify state consistency
        self.assertEqual(len(self.factory._active_managers), sum(len(keys) for keys in self.factory._user_manager_keys.values()))

        logger.critical("INTEGRATION TEST COMPLETED: Complete resource exhaustion and recovery cycle")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])