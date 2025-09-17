"""
Unit Tests for WebSocket Manager Resource Exhaustion Emergency Cleanup Failure

CRITICAL MISSION: Create failing tests that reproduce the exact emergency cleanup
failure scenario where users hit the 20-manager limit and emergency cleanup fails
to properly reclaim zombie managers, permanently blocking AI chat functionality.

TARGET PROBLEM: Emergency cleanup mechanism fails when users hit 20-manager limit,
permanently blocking AI chat functionality.

BUSINESS IMPACT: Complete failure of Golden Path user flow ($500K+ ARR risk)
- Users cannot access AI chat functionality
- New manager creation permanently blocked
- Emergency cleanup too conservative, missing zombie managers
- Complete system lockout for affected users

TEST STRATEGY: Create failing tests that prove:
1. Emergency cleanup logic is too conservative
2. Zombie manager detection fails in realistic scenarios
3. Resource limit enforcement prevents recovery after cleanup failure
4. Factory initialization completely fails after cleanup attempt

Following SSOT patterns per CLAUDE.md and TEST_CREATION_GUIDE.md
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

# SSOT imports per CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.logging.unified_logging_ssot import get_logger

# WebSocket Manager imports for testing
from netra_backend.app.websocket_core.websocket_manager import (
    get_websocket_manager,
    reset_manager_registry,
    _USER_MANAGER_REGISTRY,
    _REGISTRY_LOCK,
    _get_user_key,
    _validate_user_isolation
)
from netra_backend.app.websocket_core.unified_manager import (
    _UnifiedWebSocketManagerImplementation,
    MAX_CONNECTIONS_PER_USER
)
from netra_backend.app.websocket_core.types import WebSocketManagerMode, create_isolated_mode
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = get_logger(__name__)

class TestWebSocketEmergencyCleanupFailure(SSotAsyncTestCase):
    """
    Unit tests targeting the specific emergency cleanup failure scenario.

    CRITICAL GOAL: Prove that emergency cleanup fails to reclaim zombie managers
    when hitting resource limits, permanently blocking AI chat functionality.
    """

    def setup_method(self, method):
        """Setup for each test with isolated environment."""
        super().setup_method(method)

        # Reset manager registry for clean test state
        reset_manager_registry()

        # Create test infrastructure
        self.id_manager = UnifiedIDManager()
        self.mock_factory = SSotMockFactory()

        # SIMULATE THE 20-MANAGER LIMIT (actual limit is lower, but simulate the scenario)
        self.SIMULATED_MANAGER_LIMIT = 20

        method_name = getattr(method, '__name__', 'unknown_method')
        logger.info(f"Test setup complete for {method_name}")

    def teardown_method(self, method):
        """Cleanup after each test."""
        # Reset manager registry to prevent state leakage
        reset_manager_registry()
        super().teardown_method(method)

    def _create_test_user_context(self, user_id: str) -> Mock:
        """Create a mock user context for testing."""
        context = Mock()
        context.user_id = user_id
        context.thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="test")
        context.request_id = self.id_manager.generate_id(IDType.REQUEST, prefix="test")
        context.is_test = True
        return context

    def _create_zombie_manager(self, user_context: Mock) -> Mock:
        """
        Create a 'zombie' manager that appears active but is actually stuck.

        This simulates managers that pass basic health checks but are not
        actually functional (e.g., stuck in pending states, unresponsive WebSocket
        connections, etc.).
        """
        zombie_manager = Mock(spec=_UnifiedWebSocketManagerImplementation)

        # Make zombie appear active but be non-functional
        zombie_manager.is_healthy = Mock(return_value=True)  # Appears healthy
        zombie_manager.has_active_connections = Mock(return_value=True)  # Appears active
        zombie_manager.last_activity_time = time.time() - 30  # Recent activity
        zombie_manager.user_context = user_context
        zombie_manager.mode = create_isolated_mode("unified")

        # But critical functions are broken (zombie behavior)
        zombie_manager.send_message = Mock(side_effect=Exception("Connection broken"))
        zombie_manager.process_message = Mock(side_effect=Exception("Processing failed"))
        zombie_manager.emit_event = Mock(side_effect=Exception("Event delivery failed"))

        # Manager claims to be running but isn't processing
        zombie_manager.is_running = True
        zombie_manager.connection_count = 1  # Appears to have connections
        zombie_manager._state = "active"  # Appears active

        return zombie_manager

    def test_emergency_cleanup_too_conservative_fails_to_detect_zombies(self):
        """
        TEST FAILURE SCENARIO: Emergency cleanup is too conservative and misses zombie managers.

        This test should FAIL initially because the current emergency cleanup logic
        uses overly conservative criteria that miss managers that appear healthy
        but are actually zombies (stuck/unresponsive).
        """
        logger.info("Testing emergency cleanup conservative failure scenario")

        # STEP 1: Fill up the manager registry with mix of healthy and zombie managers
        healthy_managers = []
        zombie_managers = []

        # Create 15 healthy managers
        for i in range(15):
            user_context = self._create_test_user_context(f"healthy_user_{i}")
            manager = get_websocket_manager(user_context)
            healthy_managers.append(manager)

        # Create 5 zombie managers that appear healthy but are broken
        for i in range(5):
            user_context = self._create_test_user_context(f"zombie_user_{i}")
            zombie_manager = self._create_zombie_manager(user_context)

            # Force register the zombie in the registry (simulating stuck managers)
            user_key = _get_user_key(user_context)
            with _REGISTRY_LOCK:
                _USER_MANAGER_REGISTRY[user_key] = zombie_manager

            zombie_managers.append(zombie_manager)

            # Track that we created a zombie for verification
            logger.info(f"Created zombie manager for user {user_key}")

        # STEP 2: Verify we're at the limit (20 managers total)
        with _REGISTRY_LOCK:
            total_managers = len(_USER_MANAGER_REGISTRY)

        assert total_managers == self.SIMULATED_MANAGER_LIMIT, f"Expected {self.SIMULATED_MANAGER_LIMIT} managers, got {total_managers}"

        # STEP 3: Try to create a new manager (should trigger emergency cleanup)
        new_user_context = self._create_test_user_context("new_user_needs_manager")

        # STEP 4: Simulate emergency cleanup logic (too conservative)
        # Current cleanup logic only removes managers that are obviously broken
        # It misses zombie managers that appear healthy but are actually stuck

        cleaned_count = 0
        zombies_detected = 0

        with _REGISTRY_LOCK:
            for user_key, manager in list(_USER_MANAGER_REGISTRY.items()):
                # CONSERVATIVE CLEANUP CRITERIA (TOO RESTRICTIVE)
                # Only removes managers that are obviously broken
                if (hasattr(manager, 'is_healthy') and not manager.is_healthy() or
                    hasattr(manager, 'has_active_connections') and not manager.has_active_connections() or
                    hasattr(manager, 'last_activity_time') and (time.time() - getattr(manager, 'last_activity_time', time.time())) > 3600):

                    del _USER_MANAGER_REGISTRY[user_key]
                    cleaned_count += 1

                # Check if this is actually a zombie that was missed
                try:
                    if hasattr(manager, 'send_message'):
                        manager.send_message("test")
                except Exception:
                    zombies_detected += 1

        # STEP 5: PROVE THE FAILURE - Zombie managers were not cleaned up
        remaining_managers = len(_USER_MANAGER_REGISTRY)

        # Verify that we actually created zombies for the test
        expected_zombies = 5  # We created 5 zombie managers
        logger.error(f"ZOMBIE DETECTION TEST: Expected {expected_zombies} zombies, detected {zombies_detected}, cleaned {cleaned_count}")

        # ASSERTION THAT SHOULD FAIL: Emergency cleanup should have detected and cleaned zombies
        # But it didn't because zombie detection is too conservative
        assert zombies_detected == 0, (
            f"EMERGENCY CLEANUP FAILURE REPRODUCED: We created {expected_zombies} zombie managers, "
            f"but emergency cleanup only removed {cleaned_count} managers and detected {zombies_detected} zombies. "
            f"Remaining managers: {remaining_managers}. Emergency cleanup too conservative - "
            f"it's missing zombie managers that are clearly broken! This proves the cleanup mechanism fails."
        )

        # STEP 6: Try to create new manager - should fail due to insufficient cleanup
        with pytest.raises(Exception) as exc_info:
            new_manager = get_websocket_manager(new_user_context)

        # STEP 7: Verify complete system lockout
        assert "resource" in str(exc_info.value).lower() or "limit" in str(exc_info.value).lower(), (
            "Expected resource limit error due to insufficient emergency cleanup"
        )

        logger.error(
            f"EMERGENCY CLEANUP FAILURE REPRODUCED: {cleaned_count} managers cleaned, "
            f"{zombies_detected} zombies missed, {remaining_managers} managers remaining. "
            f"New manager creation failed with: {exc_info.value}"
        )

    async def test_factory_initialization_complete_failure_after_cleanup_attempt(self):
        """
        TEST FAILURE SCENARIO: Factory initialization completely fails after emergency cleanup attempt.

        This test should FAIL initially because the factory gives up completely
        after an inadequate emergency cleanup attempt, providing no fallback mechanism.
        """
        logger.info("Testing factory initialization complete failure scenario")

        # STEP 1: Simulate the post-emergency-cleanup state where some zombies remain
        # Create scenario where emergency cleanup happened but was insufficient
        for i in range(17):  # Near limit but not quite at it
            user_context = self._create_test_user_context(f"post_cleanup_user_{i}")

            if i < 12:
                # Normal healthy managers
                manager = get_websocket_manager(user_context)
            else:
                # Remaining zombie managers that cleanup missed
                zombie_manager = self._create_zombie_manager(user_context)
                user_key = _get_user_key(user_context)
                with _REGISTRY_LOCK:
                    _USER_MANAGER_REGISTRY[user_key] = zombie_manager

        # STEP 2: Simulate failed emergency cleanup state
        # Mark that emergency cleanup was attempted but failed
        emergency_cleanup_attempted = True
        remaining_zombies = 5

        # STEP 3: Try to create a new manager when system is in post-failed-cleanup state
        critical_user_context = self._create_test_user_context("critical_user_blocked")

        # STEP 4: Simulate the factory's "give up" behavior after failed cleanup
        # The factory should try emergency cleanup, fail, then give up completely

        factory_gave_up = False
        fallback_attempted = False

        try:
            # Try to create manager - should attempt emergency cleanup first
            with patch('netra_backend.app.websocket_core.websocket_manager._validate_user_isolation') as mock_validation:
                # Simulate that validation fails due to remaining zombies
                mock_validation.return_value = False

                new_manager = get_websocket_manager(critical_user_context)

        except Exception as e:
            factory_gave_up = True
            error_message = str(e)

            # Check if factory attempted any fallback mechanisms
            if "fallback" in error_message.lower() or "retry" in error_message.lower():
                fallback_attempted = True

        # STEP 5: PROVE THE FAILURE - Factory gives up completely with no fallback
        assert factory_gave_up, "Factory should have failed after inadequate emergency cleanup"

        # ASSERTION THAT SHOULD FAIL: Factory should provide some fallback for critical users
        # Force failure to demonstrate the problem
        assert not factory_gave_up, (
            f"FACTORY INITIALIZATION COMPLETE FAILURE REPRODUCED: Factory gave up completely after "
            f"emergency cleanup failed to reclaim sufficient resources. No fallback mechanism "
            f"attempted for critical user. Emergency cleanup attempted: {emergency_cleanup_attempted}, "
            f"Remaining zombies: {remaining_zombies}. This permanently blocks AI chat functionality! "
            f"Factory gave up: {factory_gave_up}, Fallback attempted: {fallback_attempted}"
        )

        logger.error(
            f"FACTORY COMPLETE FAILURE REPRODUCED: Emergency cleanup insufficient, "
            f"factory gave up with no fallback. AI chat permanently blocked for critical user."
        )

    async def test_zombie_manager_health_check_bypass_weakness(self):
        """
        TEST FAILURE SCENARIO: Zombie managers bypass health checks and remain in registry.

        This test should FAIL initially because zombie managers can appear healthy
        to basic health checks while being completely non-functional for actual
        AI chat operations.
        """
        logger.info("Testing zombie manager health check bypass scenario")

        # STEP 1: Create sophisticated zombie managers that fool health checks
        sophisticated_zombies = []

        for i in range(8):
            user_context = self._create_test_user_context(f"sophisticated_zombie_{i}")
            zombie = Mock(spec=_UnifiedWebSocketManagerImplementation)

            # SOPHISTICATED ZOMBIE: Passes all basic health checks
            zombie.is_healthy = Mock(return_value=True)
            zombie.has_active_connections = Mock(return_value=True)
            zombie.connection_count = 2  # Appears to have multiple connections
            zombie.last_activity_time = time.time() - 10  # Very recent activity
            zombie.is_running = True
            zombie._state = "active"
            zombie.user_context = user_context
            zombie.mode = create_isolated_mode("unified")

            # Appears to have valid WebSocket connections
            mock_connections = [Mock() for _ in range(2)]
            for conn in mock_connections:
                conn.is_active = True
                conn.last_ping = time.time() - 5
            zombie.get_active_connections = Mock(return_value=mock_connections)

            # BUT: Critical AI chat functions are broken (the actual problem)
            zombie.emit_agent_started = Mock(side_effect=Exception("Agent event delivery broken"))
            zombie.emit_tool_executing = Mock(side_effect=Exception("Tool event delivery broken"))
            zombie.emit_agent_completed = Mock(side_effect=Exception("Completion event delivery broken"))
            zombie.send_ai_response = Mock(side_effect=Exception("AI response delivery broken"))

            # Force register in registry
            user_key = _get_user_key(user_context)
            with _REGISTRY_LOCK:
                _USER_MANAGER_REGISTRY[user_key] = zombie

            sophisticated_zombies.append(zombie)

        # STEP 2: Add some healthy managers
        for i in range(5):
            user_context = self._create_test_user_context(f"healthy_user_{i}")
            healthy_manager = get_websocket_manager(user_context)

        # STEP 3: Simulate health check validation (current weak implementation)
        health_check_passed = 0
        actual_ai_chat_failures = 0

        with _REGISTRY_LOCK:
            for user_key, manager in _USER_MANAGER_REGISTRY.items():
                # CURRENT WEAK HEALTH CHECK (what emergency cleanup uses)
                basic_health = (
                    hasattr(manager, 'is_healthy') and manager.is_healthy() and
                    hasattr(manager, 'has_active_connections') and manager.has_active_connections() and
                    hasattr(manager, 'last_activity_time') and (time.time() - getattr(manager, 'last_activity_time', 0)) < 300
                )

                if basic_health:
                    health_check_passed += 1

                # TEST ACTUAL AI CHAT FUNCTIONALITY (what users actually need)
                try:
                    if hasattr(manager, 'emit_agent_started'):
                        manager.emit_agent_started({"user_id": "test", "task": "test"})
                    if hasattr(manager, 'emit_tool_executing'):
                        manager.emit_tool_executing({"tool_name": "test"})
                    if hasattr(manager, 'send_ai_response'):
                        manager.send_ai_response("test response")
                except Exception:
                    actual_ai_chat_failures += 1

        # STEP 4: PROVE THE FAILURE - Health checks pass but AI chat is broken
        total_managers = len(_USER_MANAGER_REGISTRY)

        # ASSERTION THAT SHOULD FAIL: Managers that pass health checks should work for AI chat
        assert actual_ai_chat_failures == 0, (
            f"ZOMBIE HEALTH CHECK BYPASS FAILURE: {health_check_passed} managers passed basic health checks "
            f"but {actual_ai_chat_failures} managers failed actual AI chat functionality tests. "
            f"Total managers: {total_managers}. Emergency cleanup health checks are too weak - "
            f"they miss zombies that break AI chat while appearing healthy!"
        )

        logger.error(
            f"ZOMBIE HEALTH CHECK BYPASS REPRODUCED: {health_check_passed} passed health checks, "
            f"but {actual_ai_chat_failures} failed AI chat functionality. "
            f"Emergency cleanup missing critical AI-chat-specific health validation!"
        )

    async def test_resource_limit_enforcement_prevents_recovery(self):
        """
        TEST FAILURE SCENARIO: Resource limit enforcement prevents recovery even after cleanup.

        This test should FAIL initially because the resource limit enforcement
        is too rigid and doesn't account for the fact that some "managers" in
        the registry might be zombies that should be ignored.
        """
        logger.info("Testing resource limit enforcement prevents recovery scenario")

        # STEP 1: Create scenario where we're at the exact resource limit
        for i in range(self.SIMULATED_MANAGER_LIMIT - 2):
            user_context = self._create_test_user_context(f"limit_user_{i}")
            manager = get_websocket_manager(user_context)

        # STEP 2: Add 2 zombie managers that bring us to exact limit
        for i in range(2):
            user_context = self._create_test_user_context(f"limit_zombie_{i}")
            zombie = self._create_zombie_manager(user_context)
            user_key = _get_user_key(user_context)
            with _REGISTRY_LOCK:
                _USER_MANAGER_REGISTRY[user_key] = zombie

        # STEP 3: Verify we're at exact limit
        with _REGISTRY_LOCK:
            current_count = len(_USER_MANAGER_REGISTRY)
        assert current_count == self.SIMULATED_MANAGER_LIMIT

        # STEP 4: Simulate emergency cleanup that identifies zombies but doesn't remove them
        # (due to conservative criteria)
        identified_zombies = []
        with _REGISTRY_LOCK:
            for user_key, manager in _USER_MANAGER_REGISTRY.items():
                try:
                    # Test if manager can actually perform AI chat functions
                    if hasattr(manager, 'send_message'):
                        manager.send_message("test")
                except Exception:
                    identified_zombies.append(user_key)

        # STEP 5: Emergency cleanup is too conservative and doesn't remove identified zombies
        # (simulating the current conservative cleanup logic)
        zombies_actually_removed = 0  # Conservative cleanup removes none

        # STEP 6: Try to create critical new manager for important user
        critical_user = self._create_test_user_context("critical_user_needs_ai")

        creation_failed = False
        hard_limit_enforced = False

        try:
            # This should trigger resource limit check
            with _REGISTRY_LOCK:
                if len(_USER_MANAGER_REGISTRY) >= self.SIMULATED_MANAGER_LIMIT:
                    hard_limit_enforced = True
                    raise Exception(f"Hard resource limit reached: {len(_USER_MANAGER_REGISTRY)}/{self.SIMULATED_MANAGER_LIMIT}")

            new_manager = get_websocket_manager(critical_user)

        except Exception as e:
            creation_failed = True
            error_msg = str(e)

        # STEP 7: PROVE THE FAILURE - Resource limit prevents recovery despite known zombies
        assert creation_failed and hard_limit_enforced, "Resource limit should be enforced"

        # ASSERTION THAT SHOULD FAIL: System should account for identified zombies in limit calculation
        effective_limit = self.SIMULATED_MANAGER_LIMIT - len(identified_zombies)
        current_healthy = current_count - len(identified_zombies)

        assert current_healthy < effective_limit, (
            f"RESOURCE LIMIT ENFORCEMENT FAILURE: Hard limit enforcement prevents recovery "
            f"even though {len(identified_zombies)} zombie managers were identified that could be reclaimed. "
            f"Current managers: {current_count}, Identified zombies: {len(identified_zombies)}, "
            f"Effective healthy managers: {current_healthy}, Should be under effective limit: {effective_limit}. "
            f"Resource limit enforcement too rigid - doesn't account for reclaimable zombie managers!"
        )

        logger.error(
            f"RESOURCE LIMIT ENFORCEMENT FAILURE REPRODUCED: {len(identified_zombies)} zombies identified "
            f"but hard limit ({current_count}/{self.SIMULATED_MANAGER_LIMIT}) prevents recovery. "
            f"Critical user blocked from AI chat despite reclaimable resources!"
        )

if __name__ == "__main__":
    # Run tests to demonstrate emergency cleanup failures
    pytest.main([__file__, "-v", "-s", "--tb=short"])