"""
Enhanced Zombie Manager Detection Failure Test

This test file proves that the current zombie manager detection system is insufficient
and fails to identify managers that appear active but have dead connections.

Business Value:
- Protects system stability from zombie manager accumulation
- Ensures resource cleanup prevents memory leaks
- Validates connection state consistency
- Tests edge cases that lead to "HARD LIMIT" errors

BUG DESCRIPTION:
Zombie managers are WebSocket managers that appear to be active in the system tracking
but actually have no active connections or closed connections. The current detection
logic fails to identify these properly, leading to:
1. Managers counted against user limits but providing no value
2. Resource accumulation over time
3. Users hitting limits prematurely
4. Emergency cleanup failing to free up slots

These tests are designed to FAIL to prove zombie detection is broken.
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
from netra_backend.app.websocket_core.websocket_manager import (
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


class TestZombieManagerDetectionEnhanced(SSotAsyncTestCase):
    """Enhanced tests proving zombie manager detection failures."""

    async def asyncSetUp(self):
        """Set up enhanced zombie detection test environment."""
        self.mock_factory = SSotMockFactory()
        self.test_managers = []
        self.factory = get_websocket_manager_factory()

        # Track original factory state
        self.original_max_managers = self.factory.max_managers_per_user
        self.factory.max_managers_per_user = 20

        # Test user for zombie scenarios
        self.zombie_test_user_id = "zombie_detection_test_user"

    async def asyncTearDown(self):
        """Clean up zombie detection test resources."""
        # Restore original factory configuration
        self.factory.max_managers_per_user = self.original_max_managers

        # Clean up test managers
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

    async def test_closed_connection_zombie_detection_failure(self):
        """
        TEST: Prove detection fails for managers with closed connections.

        This test SHOULD FAIL because managers with closed WebSocket connections
        are not properly identified as zombies during health assessment.

        EXPECTED FAILURE: Managers with closed connections assessed as healthy.
        """
        logger.info("=== TESTING: Closed connection zombie detection failure ===")

        # Create managers with explicitly closed connections
        zombie_managers = []
        for i in range(5):
            user_context = self.mock_factory.create_mock_user_context(
                user_id=self.zombie_test_user_id,
                websocket_connection_id=f"closed_conn_{i}",
                session_id=f"closed_session_{i}"
            )

            manager = get_websocket_manager(user_context=user_context)

            # Simulate WebSocket connections that were closed
            if hasattr(manager, '_connections'):
                # Create mock connections that are closed
                for conn_id in range(2):  # 2 connections per manager
                    mock_connection = MagicMock()
                    mock_connection.closed = True  # Connection is closed
                    mock_connection.close_code = 1000  # Normal closure
                    mock_connection.close_reason = "Client disconnected"
                    mock_connection.is_open = False
                    mock_connection.state = "CLOSED"

                    # Add to manager's connection tracking
                    manager._connections[f"conn_{i}_{conn_id}"] = mock_connection

            zombie_managers.append(manager)
            self.test_managers.append(manager)

        # Assess health of managers with closed connections
        unhealthy_count = 0
        healthy_count = 0

        for i, manager in enumerate(zombie_managers):
            manager_key = f"{self.zombie_test_user_id}:closed_conn_{i}"

            try:
                health = await self.factory._assess_manager_health(manager_key, manager)

                if health in [ManagerHealth.ZOMBIE, ManagerHealth.UNHEALTHY]:
                    unhealthy_count += 1
                else:
                    healthy_count += 1
                    logger.warning(f"Manager {i} with closed connections assessed as: {health.value}")

            except Exception as e:
                logger.error(f"Health assessment failed for manager {i}: {e}")

        # If most managers with closed connections are still considered healthy, detection is broken
        if healthy_count > unhealthy_count:
            self.fail(
                f"BUG CONFIRMED: Zombie detection failed for closed connections!\n"
                f"Managers with closed connections: {len(zombie_managers)}\n"
                f"Correctly identified as unhealthy: {unhealthy_count}\n"
                f"Incorrectly assessed as healthy: {healthy_count}\n"
                f"Detection logic fails to identify managers with closed WebSocket connections."
            )
        else:
            self.fail(
                f"BUG NOT REPRODUCED: Zombie detection worked correctly for closed connections. "
                f"Unhealthy: {unhealthy_count}, Healthy: {healthy_count}"
            )

    async def test_inactive_but_tracked_zombie_detection_failure(self):
        """
        TEST: Prove detection fails for managers that are inactive but still tracked.

        This test SHOULD FAIL because managers that haven't been active for hours
        but still exist in the factory tracking are not identified as zombies.

        EXPECTED FAILURE: Long-inactive managers assessed as healthy/idle.
        """
        logger.info("=== TESTING: Inactive but tracked zombie detection failure ===")

        # Create managers that have been inactive for various time periods
        test_scenarios = [
            {"hours_ago": 0.5, "expected_health": "IDLE"},      # 30 minutes - should be idle
            {"hours_ago": 2, "expected_health": "UNHEALTHY"},   # 2 hours - should be unhealthy
            {"hours_ago": 8, "expected_health": "ZOMBIE"},      # 8 hours - should be zombie
            {"hours_ago": 24, "expected_health": "ZOMBIE"},     # 24 hours - definitely zombie
        ]

        detection_failures = []

        for i, scenario in enumerate(test_scenarios):
            user_context = self.mock_factory.create_mock_user_context(
                user_id=self.zombie_test_user_id,
                websocket_connection_id=f"inactive_conn_{i}",
                session_id=f"inactive_session_{i}"
            )

            manager = get_websocket_manager(user_context=user_context)

            # Set last activity time to hours ago
            hours_ago = scenario["hours_ago"]
            last_activity = time.time() - (hours_ago * 3600)

            if hasattr(manager, '_last_activity_time'):
                manager._last_activity_time = last_activity

            # Clear connections to simulate no current activity
            if hasattr(manager, '_connections'):
                manager._connections.clear()

            # Set other inactive indicators
            if hasattr(manager, '_is_active'):
                manager._is_active = False
            if hasattr(manager, '_connection_count'):
                manager._connection_count = 0

            self.test_managers.append(manager)

            # Assess health
            manager_key = f"{self.zombie_test_user_id}:inactive_conn_{i}"

            try:
                health = await self.factory._assess_manager_health(manager_key, manager)

                expected_unhealthy = scenario["expected_health"] in ["UNHEALTHY", "ZOMBIE"]
                actually_unhealthy = health in [ManagerHealth.UNHEALTHY, ManagerHealth.ZOMBIE]

                if expected_unhealthy and not actually_unhealthy:
                    detection_failures.append({
                        "scenario": scenario,
                        "actual_health": health.value,
                        "hours_inactive": hours_ago
                    })

                logger.info(f"Manager inactive for {hours_ago}h assessed as: {health.value}")

            except Exception as e:
                logger.error(f"Health assessment failed for {hours_ago}h inactive manager: {e}")
                detection_failures.append({
                    "scenario": scenario,
                    "error": str(e),
                    "hours_inactive": hours_ago
                })

        # If we have detection failures, the zombie detection is broken
        if detection_failures:
            failure_details = "\n".join([
                f"  - {f['hours_inactive']}h inactive: {f.get('actual_health', 'ERROR')} (error: {f.get('error', 'none')})"
                for f in detection_failures
            ])

            self.fail(
                f"BUG CONFIRMED: Zombie detection failed for inactive managers!\n"
                f"Detection failures:\n{failure_details}\n"
                f"Long-inactive managers are not being properly identified as zombies."
            )
        else:
            self.fail(
                f"BUG NOT REPRODUCED: Zombie detection worked correctly for all inactive scenarios. "
                f"All managers properly assessed based on inactivity time."
            )

    async def test_resource_leak_zombie_accumulation(self):
        """
        TEST: Prove zombies accumulate over time leading to resource leaks.

        This test SHOULD FAIL because zombie managers accumulate in the system
        and are not cleaned up, eventually leading to resource exhaustion.

        EXPECTED FAILURE: Zombie count grows instead of being cleaned up.
        """
        logger.info("=== TESTING: Resource leak zombie accumulation ===")

        # Simulate a typical user session lifecycle over time
        session_cycles = 5  # Simulate 5 connection cycles
        managers_per_cycle = 4  # 4 managers per cycle
        expected_cleanup_per_cycle = 3  # Should clean up 3 out of 4 each time

        total_created = 0
        accumulated_zombies = []

        for cycle in range(session_cycles):
            logger.info(f"Cycle {cycle + 1}: Creating {managers_per_cycle} managers")

            cycle_managers = []

            # Create managers for this cycle
            for i in range(managers_per_cycle):
                user_context = self.mock_factory.create_mock_user_context(
                    user_id=self.zombie_test_user_id,
                    websocket_connection_id=f"cycle_{cycle}_conn_{i}",
                    session_id=f"cycle_{cycle}_session_{i}"
                )

                manager = get_websocket_manager(user_context=user_context)
                cycle_managers.append(manager)
                self.test_managers.append(manager)
                total_created += 1

            # Simulate most managers becoming zombies after the cycle
            zombie_managers_this_cycle = cycle_managers[:-1]  # All but the last one
            for manager in zombie_managers_this_cycle:
                # Make them zombies
                if hasattr(manager, '_connections'):
                    manager._connections.clear()
                if hasattr(manager, '_is_active'):
                    manager._is_active = False
                if hasattr(manager, '_last_activity_time'):
                    manager._last_activity_time = time.time() - 1800  # 30 minutes ago
                if hasattr(manager, '_connection_count'):
                    manager._connection_count = 0

                accumulated_zombies.append(manager)

            # Try cleanup after each cycle
            try:
                cleaned_count = await self.factory._emergency_cleanup_user_managers(
                    self.zombie_test_user_id,
                    CleanupLevel.MODERATE
                )
                logger.info(f"Cycle {cycle + 1}: Cleaned {cleaned_count} managers")

            except Exception as e:
                logger.error(f"Cleanup failed in cycle {cycle + 1}: {e}")

        # Check final state
        final_manager_count = self.factory.get_user_manager_count(self.zombie_test_user_id)
        expected_active_managers = session_cycles  # Should only have the last manager from each cycle

        if final_manager_count > expected_active_managers * 2:  # Allow some margin
            self.fail(
                f"BUG CONFIRMED: Zombie accumulation causing resource leak!\n"
                f"Total managers created: {total_created}\n"
                f"Expected zombies created: {len(accumulated_zombies)}\n"
                f"Final manager count: {final_manager_count}\n"
                f"Expected final count: ~{expected_active_managers}\n"
                f"Zombies are accumulating instead of being cleaned up properly."
            )
        else:
            self.fail(
                f"BUG NOT REPRODUCED: Zombie cleanup worked effectively. "
                f"Final count: {final_manager_count}, Expected problematic: >{expected_active_managers * 2}"
            )

    async def test_partial_cleanup_zombie_detection_failure(self):
        """
        TEST: Prove that partial cleanup leaves some zombies undetected.

        This test SHOULD FAIL because cleanup processes identify some zombies
        but miss others that should also be cleaned up.

        EXPECTED FAILURE: Inconsistent zombie detection during cleanup.
        """
        logger.info("=== TESTING: Partial cleanup zombie detection failure ===")

        # Create a mix of managers with different zombie characteristics
        manager_types = [
            {"type": "obvious_zombie", "count": 3},     # Obviously should be cleaned
            {"type": "subtle_zombie", "count": 4},      # Harder to detect but still zombies
            {"type": "healthy", "count": 2},            # Should not be cleaned
        ]

        created_managers = {"obvious_zombie": [], "subtle_zombie": [], "healthy": []}

        for manager_type_info in manager_types:
            manager_type = manager_type_info["type"]
            count = manager_type_info["count"]

            for i in range(count):
                user_context = self.mock_factory.create_mock_user_context(
                    user_id=self.zombie_test_user_id,
                    websocket_connection_id=f"{manager_type}_conn_{i}",
                    session_id=f"{manager_type}_session_{i}"
                )

                manager = get_websocket_manager(user_context=user_context)

                if manager_type == "obvious_zombie":
                    # Make obviously zombie
                    if hasattr(manager, '_connections'):
                        manager._connections.clear()
                    if hasattr(manager, '_is_active'):
                        manager._is_active = False
                    if hasattr(manager, '_last_activity_time'):
                        manager._last_activity_time = time.time() - 7200  # 2 hours ago
                    if hasattr(manager, '_connection_count'):
                        manager._connection_count = 0

                elif manager_type == "subtle_zombie":
                    # Make subtly zombie (harder to detect)
                    if hasattr(manager, '_connections'):
                        # Add some closed connections
                        for j in range(2):
                            mock_conn = MagicMock()
                            mock_conn.closed = True
                            mock_conn.is_open = False
                            manager._connections[f"closed_{j}"] = mock_conn

                    if hasattr(manager, '_last_activity_time'):
                        manager._last_activity_time = time.time() - 3600  # 1 hour ago
                    if hasattr(manager, '_is_active'):
                        manager._is_active = True  # Still marked active but no real connections

                elif manager_type == "healthy":
                    # Keep healthy
                    if hasattr(manager, '_last_activity_time'):
                        manager._last_activity_time = time.time() - 60  # 1 minute ago
                    if hasattr(manager, '_is_active'):
                        manager._is_active = True
                    if hasattr(manager, '_connections'):
                        # Add active connection
                        mock_conn = MagicMock()
                        mock_conn.closed = False
                        mock_conn.is_open = True
                        manager._connections["active"] = mock_conn

                created_managers[manager_type].append(manager)
                self.test_managers.append(manager)

        initial_count = self.factory.get_user_manager_count(self.zombie_test_user_id)
        logger.info(f"Created {initial_count} managers: {sum(len(managers) for managers in created_managers.values())}")

        # Perform cleanup
        try:
            cleaned_count = await self.factory._emergency_cleanup_user_managers(
                self.zombie_test_user_id,
                CleanupLevel.AGGRESSIVE
            )

            final_count = self.factory.get_user_manager_count(self.zombie_test_user_id)

            # Analyze cleanup effectiveness
            obvious_zombies = len(created_managers["obvious_zombie"])
            subtle_zombies = len(created_managers["subtle_zombie"])
            healthy_managers = len(created_managers["healthy"])

            total_zombies = obvious_zombies + subtle_zombies
            expected_remaining = healthy_managers  # Only healthy should remain

            logger.info(f"Cleanup results: Initial={initial_count}, Final={final_count}, Cleaned={cleaned_count}")
            logger.info(f"Expected to clean: {total_zombies} zombies, Keep: {healthy_managers} healthy")

            # If cleanup was perfect, we'd have only healthy managers remaining
            if final_count > expected_remaining + 1:  # Allow 1 margin for error
                zombies_remaining = final_count - expected_remaining

                # Check if obvious zombies were cleaned but subtle ones weren't
                if cleaned_count > 0 and cleaned_count < total_zombies:
                    self.fail(
                        f"BUG CONFIRMED: Partial cleanup zombie detection failure!\n"
                        f"Total zombies: {total_zombies} (obvious: {obvious_zombies}, subtle: {subtle_zombies})\n"
                        f"Healthy managers: {healthy_managers}\n"
                        f"Managers cleaned: {cleaned_count}\n"
                        f"Final count: {final_count}\n"
                        f"Zombies remaining: {zombies_remaining}\n"
                        f"Cleanup detected some zombies but missed others, proving inconsistent detection."
                    )
                else:
                    self.fail(
                        f"BUG CONFIRMED: Zombie detection completely failed!\n"
                        f"No zombies cleaned despite {total_zombies} obvious candidates."
                    )
            else:
                self.fail(
                    f"BUG NOT REPRODUCED: Zombie cleanup worked effectively. "
                    f"Final count: {final_count}, Expected problematic: >{expected_remaining + 1}"
                )

        except Exception as e:
            self.fail(f"Cleanup threw unexpected exception: {e}")


class TestZombieDetectionEdgeCases(SSotAsyncTestCase):
    """Test edge cases in zombie detection that reveal failures."""

    async def asyncSetUp(self):
        """Set up zombie detection edge case tests."""
        self.mock_factory = SSotMockFactory()
        self.test_managers = []
        self.factory = get_websocket_manager_factory()

        # Save original state
        self.original_max_managers = self.factory.max_managers_per_user
        self.factory.max_managers_per_user = 20

    async def asyncTearDown(self):
        """Clean up zombie detection edge case tests."""
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

    async def test_connection_state_inconsistency_detection_failure(self):
        """
        TEST: Prove detection fails when connection state is inconsistent.

        This test SHOULD FAIL because managers with inconsistent connection states
        (reporting active but having no real connections) are not detected as zombies.

        EXPECTED FAILURE: Inconsistent state managers assessed as healthy.
        """
        logger.info("=== TESTING: Connection state inconsistency detection failure ===")

        user_id = "inconsistent_state_user"

        # Create managers with various inconsistent states
        inconsistent_scenarios = [
            {
                "name": "active_but_no_connections",
                "is_active": True,
                "connection_count": 0,
                "connections": {},
            },
            {
                "name": "inactive_but_has_connections",
                "is_active": False,
                "connection_count": 3,
                "connections": {"conn1": "mock", "conn2": "mock", "conn3": "mock"},
            },
            {
                "name": "count_mismatch",
                "is_active": True,
                "connection_count": 5,
                "connections": {"conn1": "mock"},  # Only 1 connection but count says 5
            },
        ]

        detection_failures = []

        for i, scenario in enumerate(inconsistent_scenarios):
            user_context = self.mock_factory.create_mock_user_context(
                user_id=user_id,
                websocket_connection_id=f"inconsistent_conn_{i}",
                session_id=f"inconsistent_session_{i}"
            )

            manager = get_websocket_manager(user_context=user_context)

            # Set up inconsistent state
            if hasattr(manager, '_is_active'):
                manager._is_active = scenario["is_active"]
            if hasattr(manager, '_connection_count'):
                manager._connection_count = scenario["connection_count"]
            if hasattr(manager, '_connections'):
                manager._connections = scenario["connections"].copy()

            self.test_managers.append(manager)

            # Assess health
            manager_key = f"{user_id}:inconsistent_conn_{i}"

            try:
                health = await self.factory._assess_manager_health(manager_key, manager)

                # Managers with inconsistent state should be identified as unhealthy
                if health in [ManagerHealth.HEALTHY, ManagerHealth.IDLE]:
                    detection_failures.append({
                        "scenario": scenario["name"],
                        "health": health.value,
                        "details": scenario
                    })

                logger.info(f"Inconsistent manager '{scenario['name']}' assessed as: {health.value}")

            except Exception as e:
                logger.error(f"Health assessment failed for inconsistent manager '{scenario['name']}': {e}")
                detection_failures.append({
                    "scenario": scenario["name"],
                    "error": str(e),
                    "details": scenario
                })

        # If we have detection failures, inconsistent state detection is broken
        if detection_failures:
            failure_details = "\n".join([
                f"  - {f['scenario']}: {f.get('health', 'ERROR')} (error: {f.get('error', 'none')})"
                for f in detection_failures
            ])

            self.fail(
                f"BUG CONFIRMED: Inconsistent connection state detection failed!\n"
                f"Detection failures:\n{failure_details}\n"
                f"Managers with inconsistent states are not being identified as problematic."
            )
        else:
            self.fail(
                f"BUG NOT REPRODUCED: Inconsistent state detection worked correctly. "
                f"All inconsistent managers properly identified as unhealthy."
            )


if __name__ == '__main__':
    # These tests are designed to FAIL to prove zombie detection is broken
    unittest.main(verbosity=2)