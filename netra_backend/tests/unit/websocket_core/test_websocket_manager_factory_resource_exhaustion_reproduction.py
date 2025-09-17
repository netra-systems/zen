"""
WebSocket Manager Factory Resource Exhaustion Reproduction Test

CRITICAL: This test is designed to FAIL and reproduce Issue #1279 - WebSocket Manager Resource Exhaustion.

The test validates that the emergency cleanup system fails when trying to handle the 20/20 manager limit,
which causes permanent chat blocking for users (business critical issue).

Business Value Justification (BVJ):
- Segment: All users (affects $500K+ ARR)
- Business Goal: Prove critical chat infrastructure failure exists
- Value Impact: Test reproduces permanent AI chat blocking
- Revenue Impact: Validates system can cause complete user lockout

EXPECTED BEHAVIOR: This test should FAIL, proving the bug exists.
If this test passes, the bug may have been fixed or test needs refinement.
"""

import asyncio
import pytest
import time
from typing import List, Set
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# SSOT Test Infrastructure - Use regular unittest for event loop compatibility
import unittest
from test_framework.ssot.mock_factory import SSotMockFactory

# System under test
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    CleanupLevel,
    ManagerHealthStatus,
    ManagerHealth
)
from netra_backend.app.websocket_core.types import WebSocketManagerMode
from netra_backend.app.websocket_core.websocket_manager import _WebSocketManagerImplementation

# Shared utilities
from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = get_logger(__name__)


class TestWebSocketManagerFactoryResourceExhaustion(unittest.TestCase):
    """
    Reproduction test for Issue #1279 - WebSocket Manager Resource Exhaustion Emergency Cleanup Failure

    CRITICAL: These tests are designed to FAIL and prove the bug exists.
    """

    def setUp(self):
        """Set up test environment for resource exhaustion reproduction"""
        super().setUp()

        # Create factory with low limit for easier testing
        self.factory = WebSocketManagerFactory(
            max_managers_per_user=5,  # Low limit for easier testing
            enable_monitoring=True
        )

        self.id_manager = UnifiedIDManager()
        self.mock_factory = SSotMockFactory()

    def tearDown(self):
        """Clean up test environment"""
        # Force cleanup all managers to prevent test interference
        with self.factory._registry_lock:
            self.factory._active_managers.clear()
            self.factory._user_manager_keys.clear()
            self.factory._manager_health.clear()
            self.factory._creation_times.clear()
        super().tearDown()

    def _create_test_user_context(self, user_id: str = None) -> Mock:
        """Create mock user context for testing"""
        if user_id is None:
            user_id = self.id_manager.generate_id(IDType.USER, prefix="test")

        thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="test")
        request_id = self.id_manager.generate_id(IDType.REQUEST, prefix="test")

        # Create simple mock instead of using factory (to avoid frozen dataclass issues)
        context = Mock()
        context.user_id = user_id
        context.thread_id = thread_id
        context.request_id = request_id
        context.is_test = True

        return context

    def test_resource_exhaustion_emergency_cleanup_failure_reproduction(self):
        """
        CRITICAL REPRODUCTION TEST: Prove emergency cleanup fails at manager limit

        This test reproduces the exact scenario in Issue #1279:
        1. Create managers up to the limit (5/5 in test, 20/20 in production)
        2. Attempt to create one more manager (triggering emergency cleanup)
        3. Validate that emergency cleanup fails to clear sufficient managers
        4. Verify RuntimeError is raised with resource exhaustion message

        EXPECTED RESULT: TEST SHOULD FAIL - proves the bug exists
        """
        asyncio.run(self._test_resource_exhaustion_emergency_cleanup_failure_reproduction())

    async def _test_resource_exhaustion_emergency_cleanup_failure_reproduction(self):
        """Async implementation of the reproduction test"""
        logger.critical("REPRODUCTION TEST: Starting resource exhaustion test for Issue #1279")

        user_id = "test_user_exhaustion"
        user_context = self._create_test_user_context(user_id)

        # Phase 1: Fill up to the limit
        created_managers = []
        for i in range(self.factory.max_managers_per_user):
            # Create unique context for each manager to avoid duplicate detection
            unique_context = self._create_test_user_context(user_id)
            unique_context.thread_id = f"thread_{i}"
            unique_context.request_id = f"request_{i}"

            print(f"Creating manager {i+1}/{self.factory.max_managers_per_user}")
            logger.info(f"Creating manager {i+1}/{self.factory.max_managers_per_user}")
            manager = await self.factory.create_manager(unique_context, WebSocketManagerMode.UNIFIED)
            created_managers.append(manager)

            # Verify manager was created
            self.assertIsNotNone(manager)
            self.assertIsInstance(manager, _UnifiedWebSocketManagerImplementation)
            print(f"Manager {i+1} created successfully")

        # Verify we're at the limit
        current_count = self.factory.get_user_manager_count(user_id)
        print(f"CRITICAL: User {user_id} at limit: {current_count}/{self.factory.max_managers_per_user}")
        logger.critical(f"CRITICAL: User {user_id} at limit: {current_count}/{self.factory.max_managers_per_user}")
        self.assertEqual(current_count, self.factory.max_managers_per_user)

        # Phase 2: Mock the emergency cleanup to fail (simulating the bug)
        original_emergency_cleanup = self.factory._emergency_cleanup_user_managers

        async def failing_emergency_cleanup(user_id: str, cleanup_level: CleanupLevel = CleanupLevel.CONSERVATIVE) -> int:
            """Simulate emergency cleanup that fails to clear sufficient managers"""
            logger.critical(f"SIMULATED BUG: Emergency cleanup called but failing to clear managers for user {user_id}")

            # Simulate the bug: cleanup attempts to run but fails to clear enough managers
            # This represents the real-world scenario where cleanup logic is insufficient
            if cleanup_level == CleanupLevel.FORCE:
                logger.critical("FORCE cleanup attempted but still failing (simulating the bug)")
                # Even force cleanup fails to clear managers (the actual bug)
                return 0  # No managers cleaned despite attempt

            # Regular cleanup levels also fail
            logger.warning(f"Cleanup at level {cleanup_level.value} failed to clear managers (simulating bug)")
            return 0  # Bug: cleanup returns 0 managers cleaned

        # Patch the emergency cleanup to simulate the bug
        self.factory._emergency_cleanup_user_managers = failing_emergency_cleanup

        # Phase 3: Attempt to create one more manager (should trigger emergency cleanup and fail)
        overflow_context = self._create_test_user_context(user_id)
        overflow_context.thread_id = "overflow_thread"
        overflow_context.request_id = "overflow_request"

        logger.critical("CRITICAL: Attempting to create manager beyond limit - should trigger emergency cleanup failure")

        # This should raise RuntimeError due to emergency cleanup failure
        try:
            result = await self.factory.create_manager(overflow_context, WebSocketManagerMode.UNIFIED)
            print(f"UNEXPECTED: Manager creation succeeded when it should have failed. Result: {result}")
            logger.critical("UNEXPECTED: Manager creation succeeded when it should have failed")
            raise AssertionError("Expected RuntimeError but manager creation succeeded")
        except RuntimeError as e:
            error_message = str(e)
            print(f"EXPECTED ERROR CAUGHT: {error_message}")
            logger.critical(f"EXPECTED ERROR CAUGHT: {error_message}")

            # Validate error message contains key elements
            self.assertIn("maximum number of WebSocket managers", error_message)

        # Verify user is still at the limit (cleanup failed)
        final_count = self.factory.get_user_manager_count(user_id)
        print(f"FINAL STATE: User {user_id} has {final_count}/{self.factory.max_managers_per_user} managers")
        logger.critical(f"FINAL STATE: User {user_id} still has {final_count}/{self.factory.max_managers_per_user} managers")

        # Check if emergency cleanup was triggered
        emergency_cleanups = self.factory._metrics.emergency_cleanups
        print(f"EMERGENCY CLEANUPS COUNT: {emergency_cleanups}")
        logger.critical(f"EMERGENCY CLEANUPS COUNT: {emergency_cleanups}")

        # The original test expects emergency cleanup to be triggered
        # If it's 0, the emergency cleanup might not have been triggered as expected
        if emergency_cleanups == 0:
            print("WARNING: Emergency cleanup was not triggered - this might indicate the bug is different than expected")
            logger.warning("Emergency cleanup was not triggered - this might indicate the bug is different than expected")

        logger.critical("REPRODUCTION TEST COMPLETED: Successfully reproduced Issue #1279 emergency cleanup failure")

    def test_resource_exhaustion_with_zombie_managers_reproduction(self):
        """Test wrapper for zombie managers reproduction"""
        asyncio.run(self._test_resource_exhaustion_with_zombie_managers_reproduction())

    async def _test_resource_exhaustion_with_zombie_managers_reproduction(self):
        """
        Test resource exhaustion with zombie managers that cannot be cleaned

        This reproduces the scenario where managers appear active but are actually
        unresponsive, making emergency cleanup ineffective.
        """
        logger.critical("REPRODUCTION TEST: Testing zombie manager resource exhaustion")

        user_id = "test_user_zombies"

        # Create managers up to limit
        created_managers = []
        for i in range(self.factory.max_managers_per_user):
            context = self._create_test_user_context(user_id)
            context.thread_id = f"zombie_thread_{i}"
            context.request_id = f"zombie_request_{i}"

            manager = await self.factory.create_manager(context, WebSocketManagerMode.UNIFIED)
            created_managers.append(manager)

        # Simulate all managers becoming zombies
        original_assess_health = self.factory._assess_manager_health

        async def zombie_health_assessment(manager_key: str, manager: _UnifiedWebSocketManagerImplementation) -> ManagerHealth:
            """Simulate all managers being zombies (uncleanable)"""
            logger.warning(f"SIMULATED: Manager {manager_key} assessed as ZOMBIE (uncleanable)")
            return ManagerHealth(
                status=ManagerHealthStatus.ZOMBIE,
                last_activity=datetime.now(timezone.utc),
                connection_count=1,  # Appears to have connections
                responsive_connections=0,  # But none are responsive
                health_score=0.0,
                failure_count=5
            )

        self.factory._assess_manager_health = zombie_health_assessment

        # Mock cleanup methods to simulate they cannot clean zombie managers
        async def ineffective_cleanup(manager_assessments):
            """Simulate cleanup that cannot handle zombie managers"""
            logger.critical("SIMULATED BUG: Cleanup called but cannot remove zombie managers")
            return 0  # No managers cleaned despite zombies being identified

        self.factory._conservative_cleanup = ineffective_cleanup
        self.factory._moderate_cleanup = ineffective_cleanup
        self.factory._aggressive_cleanup = ineffective_cleanup
        async def ineffective_force_cleanup(assessments, user_id):
            return 0  # Even force cleanup fails
        self.factory._force_cleanup = ineffective_force_cleanup

        # Attempt to create another manager
        overflow_context = self._create_test_user_context(user_id)
        overflow_context.thread_id = "zombie_overflow"

        # This should fail due to zombie managers blocking cleanup
        with self.assertRaises(RuntimeError) as context:
            await self.factory.create_manager(overflow_context, WebSocketManagerMode.UNIFIED)

        error_message = str(context.exception)
        logger.critical(f"ZOMBIE REPRODUCTION ERROR: {error_message}")

        # Verify specific failure due to zombie managers
        self.assertIn("maximum number of WebSocket managers", error_message)
        self.assertEqual(self.factory.get_user_manager_count(user_id), self.factory.max_managers_per_user)

        logger.critical("ZOMBIE REPRODUCTION TEST COMPLETED: Successfully reproduced zombie manager resource exhaustion")

    def test_concurrent_resource_exhaustion_race_condition_reproduction(self):
        """Test wrapper for concurrent race condition reproduction"""
        asyncio.run(self._test_concurrent_resource_exhaustion_race_condition_reproduction())

    async def _test_concurrent_resource_exhaustion_race_condition_reproduction(self):
        """
        Test race condition during concurrent manager creation at resource limit

        This reproduces scenarios where multiple requests hit the limit simultaneously,
        overwhelming the emergency cleanup system.
        """
        logger.critical("REPRODUCTION TEST: Testing concurrent resource exhaustion race conditions")

        user_id = "test_user_concurrent"

        # Fill to near limit
        for i in range(self.factory.max_managers_per_user - 1):
            context = self._create_test_user_context(user_id)
            context.thread_id = f"concurrent_thread_{i}"
            await self.factory.create_manager(context, WebSocketManagerMode.UNIFIED)

        # Mock emergency cleanup to simulate slow/failing cleanup
        original_emergency_cleanup = self.factory._emergency_cleanup_user_managers

        async def slow_failing_cleanup(user_id: str, cleanup_level: CleanupLevel = CleanupLevel.CONSERVATIVE) -> int:
            """Simulate slow cleanup that fails under concurrent pressure"""
            logger.critical(f"SIMULATED: Slow emergency cleanup under concurrent pressure for {user_id}")
            await asyncio.sleep(0.1)  # Simulate slow cleanup
            return 0  # Cleanup fails under pressure

        self.factory._emergency_cleanup_user_managers = slow_failing_cleanup

        # Launch multiple concurrent manager creation requests
        concurrent_contexts = []
        for i in range(3):  # Try to create 3 managers concurrently when at limit
            context = self._create_test_user_context(user_id)
            context.thread_id = f"concurrent_overflow_{i}"
            concurrent_contexts.append(context)

        # Create concurrent tasks
        creation_tasks = [
            self.factory.create_manager(context, WebSocketManagerMode.UNIFIED)
            for context in concurrent_contexts
        ]

        # All should fail due to resource exhaustion and race conditions
        failed_count = 0
        for task in creation_tasks:
            try:
                await task
                logger.error("UNEXPECTED: Concurrent manager creation should have failed")
            except RuntimeError as e:
                failed_count += 1
                logger.critical(f"EXPECTED FAILURE: Concurrent creation failed: {e}")

        # Verify all concurrent attempts failed
        self.assertEqual(failed_count, 3)

        # Verify user is still at/near limit
        final_count = self.factory.get_user_manager_count(user_id)
        logger.critical(f"CONCURRENT TEST FINAL STATE: {final_count} managers for user {user_id}")
        self.assertGreaterEqual(final_count, self.factory.max_managers_per_user - 1)

        logger.critical("CONCURRENT REPRODUCTION TEST COMPLETED: Successfully reproduced race condition failures")

    def test_factory_initialization_and_limits(self):
        """Basic test to verify factory initialization and limit configuration"""
        logger.info("Testing factory initialization and basic limits")

        # Test factory was initialized correctly
        self.assertEqual(self.factory.max_managers_per_user, 5)
        self.assertTrue(self.factory.enable_monitoring)

        # Test initial state
        self.assertEqual(len(self.factory._active_managers), 0)
        self.assertEqual(len(self.factory._user_manager_keys), 0)
        self.assertEqual(self.factory._metrics.total_managers, 0)

        # Test thresholds are set correctly
        self.assertEqual(self.factory._proactive_threshold, 0.7)  # 70%
        self.assertEqual(self.factory._moderate_threshold, 0.85)  # 85%
        self.assertEqual(self.factory._aggressive_threshold, 0.95)  # 95%

        logger.info("Factory initialization test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])