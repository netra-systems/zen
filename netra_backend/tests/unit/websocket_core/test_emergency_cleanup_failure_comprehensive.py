"""
Emergency Cleanup Failure Bug Proof - Comprehensive Unit Tests

This test file proves the existence of the WebSocket Manager Emergency Cleanup Failure bug.
These tests are designed to FAIL to demonstrate that the emergency cleanup system is not
working correctly when users hit the MAX_CONNECTIONS_PER_USER limit.

Business Value:
- Protects $500K+ ARR dependent on reliable WebSocket chat functionality
- Validates emergency cleanup mechanisms that prevent resource exhaustion
- Ensures Golden Path user flow continues when cleanup fails
- Tests core failure patterns that impact business operations

BUG DESCRIPTION:
The WebSocket Manager emergency cleanup system fails to properly remove closed/zombie
connections when users hit the 20-manager limit, leading to:
1. Users being permanently blocked from new connections
2. "HARD LIMIT: User still over limit after cleanup (20/20)" errors
3. Resource exhaustion that cascades to other users
4. System degradation affecting the Golden Path user experience
"""

import unittest
import asyncio
import time
import secrets
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Set, Optional

# Use SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# WebSocket manager imports
from netra_backend.app.websocket_core.canonical_import_patterns import (
    get_websocket_manager,
    UnifiedWebSocketManager
)
from netra_backend.app.websocket_core.types import WebSocketManagerMode
from netra_backend.app.websocket_core.websocket_manager_factory import (
    get_websocket_manager_factory,
    CleanupLevel,
    ManagerHealth
)
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestEmergencyCleanupFailureComprehensive(SSotAsyncTestCase):
    """Comprehensive tests proving emergency cleanup failure bug exists."""

    async def asyncSetUp(self):
        """Set up comprehensive test environment for bug reproduction."""
        self.mock_factory = SSotMockFactory()
        self.test_managers = []
        self.factory = get_websocket_manager_factory()

        # Track original factory state
        self.original_max_managers = self.factory.max_managers_per_user

        # Configure factory for testing (use 20 like the bug report)
        self.factory.max_managers_per_user = 20
        self.factory._aggressive_threshold = 0.8  # 16/20
        self.factory._moderate_threshold = 0.6    # 12/20
        self.factory._proactive_threshold = 0.7   # 14/20

        # Test user context for bug reproduction
        self.test_user_context = self.mock_factory.create_mock_user_context(
            user_id="10594514182745168115",  # Similar to bug report user ID
            websocket_connection_id="test_emergency_cleanup_conn",
            is_premium=True
        )

    async def asyncTearDown(self):
        """Clean up test resources and restore factory state."""
        # Restore original factory configuration
        self.factory.max_managers_per_user = self.original_max_managers

        # Attempt to clean up test managers
        for manager in self.test_managers:
            try:
                if hasattr(manager, 'cleanup_all_connections'):
                    await manager.cleanup_all_connections()
            except Exception as e:
                logger.debug(f"Test manager cleanup error: {e}")

        # Clear factory state
        if hasattr(self.factory, '_active_managers'):
            self.factory._active_managers.clear()
        if hasattr(self.factory, '_user_manager_keys'):
            self.factory._user_manager_keys.clear()

    async def test_emergency_cleanup_failure_hard_limit_error(self):
        """
        TEST: Reproduce the exact "HARD LIMIT: User still over limit after cleanup (20/20)" error.

        This test SHOULD FAIL because emergency cleanup is not properly removing zombie managers
        when users hit the MAX_CONNECTIONS_PER_USER limit.

        EXPECTED FAILURE: RuntimeError with "HARD LIMIT" message indicating cleanup failed.
        """
        logger.info("=== TESTING: Emergency cleanup failure hard limit error ===")

        user_id = self.test_user_context.user_id

        # Phase 1: Create exactly 20 managers (at the limit)
        logger.info(f"Phase 1: Creating 20 managers for user {user_id}")
        created_managers = []

        for i in range(20):
            try:
                # Create unique user context for each manager
                user_context = self.mock_factory.create_mock_user_context(
                    user_id=user_id,
                    websocket_connection_id=f"conn_{i}",
                    session_id=f"session_{i}"
                )

                manager = get_websocket_manager(
                    user_context=user_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                created_managers.append(manager)
                self.test_managers.append(manager)

            except Exception as e:
                self.fail(f"Failed to create manager {i} during setup: {e}")

        # Verify we're at the limit
        current_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(current_count, 20, f"Should have exactly 20 managers, got {current_count}")

        # Phase 2: Simulate some managers becoming "zombies" (closed connections but still tracked)
        logger.info("Phase 2: Simulating zombie managers")
        zombie_count = 8  # Make 8 managers into zombies

        for i in range(zombie_count):
            manager = created_managers[i]

            # Mock the manager as having zombie characteristics
            if hasattr(manager, '_connections'):
                # Clear connections to simulate they were closed
                manager._connections = {}
            if hasattr(manager, '_is_active'):
                manager._is_active = False
            if hasattr(manager, '_last_activity_time'):
                manager._last_activity_time = time.time() - 3600  # 1 hour ago
            if hasattr(manager, '_connection_count'):
                manager._connection_count = 0

        logger.info(f"Created {zombie_count} zombie managers out of 20 total")

        # Phase 3: Try to create one more manager - this should trigger emergency cleanup
        logger.info("Phase 3: Attempting to create 21st manager (should trigger emergency cleanup)")

        # This should trigger the emergency cleanup and should succeed if cleanup works
        # But it will FAIL because emergency cleanup is broken
        try:
            extra_user_context = self.mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id="conn_21",
                session_id="session_21"
            )

            # This call should trigger emergency cleanup
            extra_manager = get_websocket_manager(
                user_context=extra_user_context,
                mode=WebSocketManagerMode.UNIFIED
            )
            self.test_managers.append(extra_manager)

            # If we get here, the bug is NOT present (emergency cleanup worked)
            final_count = self.factory.get_user_manager_count(user_id)
            logger.info(f"SUCCESS: Emergency cleanup worked! Final count: {final_count}")

            # This test expects failure, so if we succeeded, the bug might be fixed
            self.fail(
                f"BUG NOT REPRODUCED: Emergency cleanup appeared to work correctly. "
                f"Final manager count: {final_count}. "
                f"Expected: RuntimeError with 'HARD LIMIT' message. "
                f"This could mean the bug is fixed or the test conditions are insufficient."
            )

        except RuntimeError as e:
            error_message = str(e)
            logger.error(f"EXPECTED FAILURE: {error_message}")

            # Verify this is the exact bug we're looking for
            if "HARD LIMIT" in error_message and "still over limit after cleanup" in error_message:
                logger.info("✅ BUG CONFIRMED: Emergency cleanup failure reproduced successfully!")

                # Extract details for bug analysis
                if "20/20" in error_message or "(20)" in error_message:
                    self.assertTrue(True, "Bug reproduced exactly as described in issue")

                    # Fail the test to prove the bug exists
                    self.fail(
                        f"BUG CONFIRMED: Emergency cleanup failure reproduced!\n"
                        f"Error: {error_message}\n"
                        f"Analysis: Emergency cleanup ran but failed to remove {zombie_count} zombie managers.\n"
                        f"Impact: User {user_id} is now permanently blocked from creating new connections.\n"
                        f"This proves the WebSocket Manager Emergency Cleanup Failure bug exists."
                    )
                else:
                    self.fail(f"Unexpected error format: {error_message}")
            else:
                self.fail(f"Different error than expected: {error_message}")

        except Exception as e:
            self.fail(f"Unexpected exception type: {type(e).__name__}: {e}")

    async def test_zombie_manager_detection_failure(self):
        """
        TEST: Prove that zombie manager detection is insufficient.

        This test SHOULD FAIL because the current zombie detection logic
        doesn't properly identify managers with closed connections.

        EXPECTED FAILURE: Zombie managers are not detected and removed.
        """
        logger.info("=== TESTING: Zombie manager detection failure ===")

        user_id = self.test_user_context.user_id

        # Create 10 managers
        for i in range(10):
            user_context = self.mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id=f"zombie_test_conn_{i}",
                session_id=f"zombie_session_{i}"
            )

            manager = get_websocket_manager(user_context=user_context)
            self.test_managers.append(manager)

        initial_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(initial_count, 10)

        # Make 6 managers into obvious zombies
        zombie_managers = self.test_managers[:6]
        for manager in zombie_managers:
            # Clear all connections
            if hasattr(manager, '_connections'):
                manager._connections.clear()
            # Mark as inactive
            if hasattr(manager, '_is_active'):
                manager._is_active = False
            # Set old activity time
            if hasattr(manager, '_last_activity_time'):
                manager._last_activity_time = time.time() - 7200  # 2 hours ago
            # Zero connection count
            if hasattr(manager, '_connection_count'):
                manager._connection_count = 0

        # Try emergency cleanup - should detect and remove zombies
        try:
            cleaned_count = await self.factory._emergency_cleanup_user_managers(
                user_id,
                CleanupLevel.AGGRESSIVE
            )

            final_count = self.factory.get_user_manager_count(user_id)

            # If cleanup worked correctly, we should have removed the 6 zombies
            expected_remaining = initial_count - 6  # Should be 4

            if final_count <= expected_remaining:
                # Cleanup worked - this means the bug might be fixed
                self.fail(
                    f"BUG NOT REPRODUCED: Zombie detection appeared to work correctly. "
                    f"Initial: {initial_count}, Final: {final_count}, Cleaned: {cleaned_count}. "
                    f"Expected zombie detection to fail but it succeeded."
                )
            else:
                # Cleanup failed to remove zombies - this proves the bug
                zombies_remaining = final_count - (initial_count - 6)
                self.fail(
                    f"BUG CONFIRMED: Zombie manager detection failed!\n"
                    f"Initial managers: {initial_count}\n"
                    f"Zombie managers created: 6\n"
                    f"Managers cleaned: {cleaned_count}\n"
                    f"Final manager count: {final_count}\n"
                    f"Zombies remaining: {zombies_remaining}\n"
                    f"This proves zombie detection is insufficient."
                )

        except Exception as e:
            self.fail(f"Emergency cleanup threw unexpected exception: {e}")

    async def test_progressive_cleanup_failure_escalation(self):
        """
        TEST: Prove that progressive cleanup levels fail to reduce manager count effectively.

        This test SHOULD FAIL because each cleanup level (CONSERVATIVE -> MODERATE -> AGGRESSIVE -> FORCE)
        fails to properly remove inactive/zombie managers.

        EXPECTED FAILURE: All cleanup levels fail to achieve required reduction.
        """
        logger.info("=== TESTING: Progressive cleanup failure escalation ===")

        user_id = self.test_user_context.user_id

        # Create 18 managers (near the 20 limit)
        initial_manager_count = 18
        for i in range(initial_manager_count):
            user_context = self.mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id=f"escalation_conn_{i}",
                session_id=f"escalation_session_{i}"
            )

            manager = get_websocket_manager(user_context=user_context)

            # Make most managers zombie-like (12 out of 18)
            if i < 12:
                if hasattr(manager, '_connections'):
                    manager._connections.clear()
                if hasattr(manager, '_is_active'):
                    manager._is_active = False
                if hasattr(manager, '_last_activity_time'):
                    manager._last_activity_time = time.time() - 1800  # 30 minutes ago
                if hasattr(manager, '_connection_count'):
                    manager._connection_count = 0

            self.test_managers.append(manager)

        current_count = self.factory.get_user_manager_count(user_id)
        self.assertEqual(current_count, initial_manager_count)

        # Test each cleanup level - they should all fail to clean effectively
        cleanup_results = {}

        for cleanup_level in [CleanupLevel.CONSERVATIVE, CleanupLevel.MODERATE, CleanupLevel.AGGRESSIVE, CleanupLevel.FORCE]:
            logger.info(f"Testing cleanup level: {cleanup_level.value}")

            pre_cleanup_count = self.factory.get_user_manager_count(user_id)

            try:
                cleaned_count = await self.factory._emergency_cleanup_user_managers(
                    user_id,
                    cleanup_level
                )

                post_cleanup_count = self.factory.get_user_manager_count(user_id)

                cleanup_results[cleanup_level.value] = {
                    'pre_count': pre_cleanup_count,
                    'post_count': post_cleanup_count,
                    'cleaned_count': cleaned_count,
                    'effectiveness': cleaned_count / max(pre_cleanup_count, 1) * 100
                }

                logger.info(f"{cleanup_level.value}: {pre_cleanup_count} -> {post_cleanup_count} (cleaned: {cleaned_count})")

            except Exception as e:
                cleanup_results[cleanup_level.value] = {
                    'error': str(e),
                    'effectiveness': 0
                }
                logger.error(f"{cleanup_level.value} failed: {e}")

        # Analyze results - if any level was highly effective, the bug might be fixed
        highly_effective_levels = [
            level for level, result in cleanup_results.items()
            if 'effectiveness' in result and result['effectiveness'] > 50  # More than 50% cleanup
        ]

        if highly_effective_levels:
            self.fail(
                f"BUG NOT REPRODUCED: Some cleanup levels were effective: {highly_effective_levels}. "
                f"Expected all levels to fail. Results: {cleanup_results}"
            )

        # If we get here, all cleanup levels were ineffective - proving the bug
        final_count = self.factory.get_user_manager_count(user_id)
        zombie_count = 12  # We created 12 zombies

        if final_count > initial_manager_count - zombie_count + 2:  # Allow some margin
            self.fail(
                f"BUG CONFIRMED: Progressive cleanup failure!\n"
                f"Initial managers: {initial_manager_count} (12 zombies)\n"
                f"Final managers: {final_count}\n"
                f"Cleanup results: {cleanup_results}\n"
                f"All cleanup levels failed to effectively remove zombie managers.\n"
                f"This proves the emergency cleanup system is fundamentally broken."
            )
        else:
            self.fail(
                f"BUG NOT REPRODUCED: Cleanup was more effective than expected. "
                f"Final count: {final_count}, Expected: >{initial_manager_count - zombie_count + 2}"
            )

    async def test_manager_health_assessment_failure(self):
        """
        TEST: Prove that manager health assessment fails to identify unhealthy managers.

        This test SHOULD FAIL because the health assessment logic doesn't properly
        identify managers that should be cleaned up.

        EXPECTED FAILURE: Unhealthy managers are assessed as healthy.
        """
        logger.info("=== TESTING: Manager health assessment failure ===")

        # Create a manager and make it obviously unhealthy
        user_context = self.mock_factory.create_mock_user_context(
            user_id="health_test_user",
            websocket_connection_id="health_test_conn"
        )

        manager = get_websocket_manager(user_context=user_context)
        self.test_managers.append(manager)

        # Make manager obviously unhealthy
        if hasattr(manager, '_connections'):
            manager._connections.clear()  # No connections
        if hasattr(manager, '_is_active'):
            manager._is_active = False  # Inactive
        if hasattr(manager, '_last_activity_time'):
            manager._last_activity_time = time.time() - 14400  # 4 hours ago
        if hasattr(manager, '_connection_count'):
            manager._connection_count = 0  # Zero connections

        # Assess health
        manager_key = f"health_test_user:health_test_conn"
        try:
            health = await self.factory._assess_manager_health(manager_key, manager)

            # Health should be UNHEALTHY or ZOMBIE based on the conditions
            if health in [ManagerHealth.HEALTHY, ManagerHealth.IDLE]:
                self.fail(
                    f"BUG CONFIRMED: Health assessment failure!\n"
                    f"Manager with no connections, inactive for 4 hours, assessed as: {health.value}\n"
                    f"Expected: UNHEALTHY or ZOMBIE\n"
                    f"This proves the health assessment logic is insufficient."
                )
            else:
                # Health assessment worked correctly
                self.fail(
                    f"BUG NOT REPRODUCED: Health assessment worked correctly. "
                    f"Manager assessed as: {health.value} (expected UNHEALTHY/ZOMBIE)"
                )

        except Exception as e:
            self.fail(f"Health assessment threw unexpected exception: {e}")


class TestEmergencyCleanupEdgeCases(SSotAsyncTestCase):
    """Test edge cases that expose emergency cleanup failures."""

    async def asyncSetUp(self):
        """Set up edge case test environment."""
        self.mock_factory = SSotMockFactory()
        self.test_managers = []
        self.factory = get_websocket_manager_factory()

        # Save original state
        self.original_max_managers = self.factory.max_managers_per_user
        self.factory.max_managers_per_user = 20

    async def asyncTearDown(self):
        """Clean up edge case test resources."""
        self.factory.max_managers_per_user = self.original_max_managers

        for manager in self.test_managers:
            try:
                if hasattr(manager, 'cleanup_all_connections'):
                    await manager.cleanup_all_connections()
            except Exception:
                pass

        if hasattr(self.factory, '_active_managers'):
            self.factory._active_managers.clear()
        if hasattr(self.factory, '_user_manager_keys'):
            self.factory._user_manager_keys.clear()

    async def test_rapid_connection_creation_overwhelms_cleanup(self):
        """
        TEST: Prove that rapid connection creation can overwhelm emergency cleanup.

        This test SHOULD FAIL because cleanup can't keep up with rapid manager creation,
        leading to the hard limit error.

        EXPECTED FAILURE: RuntimeError indicating cleanup overwhelmed.
        """
        logger.info("=== TESTING: Rapid connection creation overwhelming cleanup ===")

        user_id = "rapid_test_user"

        # Rapidly create managers to simulate high-frequency reconnection scenario
        try:
            for i in range(25):  # Try to create more than the 20 limit
                user_context = self.mock_factory.create_mock_user_context(
                    user_id=user_id,
                    websocket_connection_id=f"rapid_conn_{i}",
                    session_id=f"rapid_session_{i}"
                )

                manager = get_websocket_manager(user_context=user_context)
                self.test_managers.append(manager)

                # Simulate some managers becoming inactive quickly
                if i % 3 == 0 and hasattr(manager, '_is_active'):
                    manager._is_active = False
                    if hasattr(manager, '_connections'):
                        manager._connections.clear()

            # If we get here without error, the bug might not be present
            final_count = self.factory.get_user_manager_count(user_id)
            self.fail(
                f"BUG NOT REPRODUCED: Rapid creation succeeded without hitting hard limit. "
                f"Final count: {final_count}. Expected: RuntimeError with hard limit message."
            )

        except RuntimeError as e:
            if "HARD LIMIT" in str(e):
                self.fail(
                    f"BUG CONFIRMED: Rapid connection creation overwhelmed cleanup!\n"
                    f"Error: {str(e)}\n"
                    f"This proves emergency cleanup cannot handle high-frequency scenarios."
                )
            else:
                self.fail(f"Unexpected RuntimeError: {e}")

        except Exception as e:
            self.fail(f"Unexpected exception: {type(e).__name__}: {e}")


if __name__ == '__main__':
    # These tests are designed to FAIL to prove the bug exists
    unittest.main(verbosity=2)