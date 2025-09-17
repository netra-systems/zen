"""
Issue #889 WebSocket Manager Duplication Unit Tests - REPRODUCTION SUITE

This test suite is designed to FAIL initially and reproduce the exact WebSocket manager
duplication violations observed in GCP logs for demo-user-001. The tests expose
fundamental SSOT violations in WebSocket manager instantiation patterns.

CRITICAL BUSINESS CONTEXT:
- WebSocket manager duplication directly impacts $500K+ ARR chat functionality
- Multiple managers for same user causes message delivery failures and race conditions
- Golden Path user flow depends on reliable WebSocket event delivery
- Staging GCP logs show consistent duplication patterns for demo-user-001

TEST OBJECTIVES (Must FAIL initially):
1. Expose registry key inconsistency in WebSocket manager creation
2. Demonstrate factory pattern bypass allowing direct instantiation
3. Validate enum sharing violations across manager instances
4. Show user context contamination between concurrent sessions

EXPECTED FAILURES:
- test_registry_key_inconsistency: Different keys for same user context
- test_factory_pattern_bypass_prevention: Direct instantiation not blocked
- test_enum_sharing_violation_detection: Shared enum state across instances
- test_user_context_contamination_unit: Cross-user data leakage

Business Value Justification (BVJ):
- Segment: Platform Infrastructure (supports ALL tiers)
- Business Goal: Stability - prevent WebSocket duplication breaking chat
- Value Impact: Protects core AI interaction reliability
- Revenue Impact: Prevents chat failures affecting customer retention
"""

import asyncio
import unittest
import sys
import os
import logging
import weakref
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Add test_framework to path for SSOT imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'test_framework'))

# Import SSOT BaseTestCase - MANDATORY for all tests
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Import core WebSocket components to test duplication patterns
try:
    from netra_backend.app.websocket_core.canonical_import_patterns import (
        WebSocketManager,
        UnifiedWebSocketManager,
        WebSocketManagerFactory,
        get_websocket_manager,
        create_test_user_context,
        create_test_fallback_manager
    )
    from netra_backend.app.websocket_core.types import (
        WebSocketManagerMode,
        WebSocketConnection,
        create_isolated_mode
    )
    from netra_backend.app.websocket_core.unified_manager import (
        _UnifiedWebSocketManagerImplementation
    )
    from netra_backend.app.agents.registry import AgentRegistry, AgentType, AgentStatus
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
    from shared.types.core_types import ensure_user_id, ensure_thread_id
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"WebSocket imports not available: {e}")
    IMPORTS_AVAILABLE = False


@dataclass
class UserContextMock:
    """Mock user context for demo-user-001 testing."""
    user_id: str = "demo-user-001"
    session_id: str = "session-demo-001"
    request_id: str = "req-demo-001"
    thread_id: str = "thread-demo-001"
    is_test: bool = True
    websocket_id: Optional[str] = None
    connection_id: Optional[str] = None

    def __post_init__(self):
        if not self.websocket_id:
            self.websocket_id = f"ws-{self.user_id}-{self.session_id}"
        if not self.connection_id:
            self.connection_id = f"conn-{self.user_id}-{self.session_id}"


class Issue889WebSocketManagerDuplicationUnitTests(SSotBaseTestCase):
    """
    Unit tests to reproduce WebSocket manager duplication for demo-user-001.

    These tests MUST FAIL initially to demonstrate the current violations.
    Success would indicate the issue is already fixed.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Create demo-user-001 context to match GCP log patterns
        self.demo_user_context = UserContextMock(
            user_id="demo-user-001",
            session_id="session-demo-001",
            request_id="req-demo-001-unit"
        )

        # Track manager instances for duplication detection
        self.manager_instances = []
        self.registry_keys_seen = set()

        self.logger.info(f"Setup test: {method.__name__} for demo-user-001")

    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Clear tracked instances
        self.manager_instances.clear()
        self.registry_keys_seen.clear()
        super().teardown_method(method)
        self.logger.info(f"Teardown test: {method.__name__}")

    @unittest.skipUnless(IMPORTS_AVAILABLE, "WebSocket imports not available")
    def test_registry_key_inconsistency_reproduction(self):
        """
        TEST MUST FAIL: Reproduce registry key inconsistency for same user.

        EXPECTED FAILURE: Different registry keys generated for same user context,
        causing multiple manager instances to be created and stored separately.

        This directly reproduces the duplication pattern seen in GCP logs where
        demo-user-001 gets multiple WebSocket managers with different keys.
        """
        self.logger.info("REPRODUCING: Registry key inconsistency for demo-user-001")

        # Create multiple managers for same user context
        manager_keys = []
        managers = []

        for i in range(3):
            try:
                # Attempt to get manager using different patterns
                if i == 0:
                    # Direct factory call
                    manager = get_websocket_manager(user_context=self.demo_user_context)
                elif i == 1:
                    # Legacy factory pattern
                    factory = WebSocketManagerFactory()
                    manager = factory.create_manager(user_context=self.demo_user_context)
                else:
                    # Fallback pattern
                    manager = create_test_fallback_manager(self.demo_user_context)

                managers.append(manager)

                # Extract internal registry key if available
                registry_key = None
                if hasattr(manager, '_registry_key'):
                    registry_key = manager._registry_key
                elif hasattr(manager, 'user_context') and hasattr(manager.user_context, 'user_id'):
                    registry_key = f"ws_manager_{manager.user_context.user_id}"
                else:
                    registry_key = f"unknown_key_{i}"

                manager_keys.append(registry_key)
                self.registry_keys_seen.add(registry_key)

                self.logger.info(f"Manager {i}: key={registry_key}, id={id(manager)}")

            except Exception as e:
                self.logger.error(f"Failed to create manager {i}: {e}")
                manager_keys.append(f"error_{i}")

        # EXPECTED FAILURE: All keys should be identical for same user
        # If this assertion PASSES, the duplication issue is already fixed
        unique_keys = set(manager_keys)

        self.logger.critical(
            f"DUPLICATION CHECK: {len(unique_keys)} unique keys for demo-user-001: {unique_keys}"
        )

        # This assertion SHOULD FAIL - multiple keys indicates duplication
        self.assertEqual(
            len(unique_keys), 1,
            f"DUPLICATION DETECTED: Expected 1 registry key for demo-user-001, got {len(unique_keys)}: {unique_keys}. "
            f"This reproduces the Issue #889 violation."
        )

        # EXPECTED FAILURE: All managers should be the same instance
        unique_managers = {id(m) for m in managers if m is not None}
        self.assertEqual(
            len(unique_managers), 1,
            f"DUPLICATION DETECTED: Expected 1 manager instance for demo-user-001, got {len(unique_managers)}. "
            f"This reproduces the Issue #889 violation."
        )

    @unittest.skipUnless(IMPORTS_AVAILABLE, "WebSocket imports not available")
    def test_factory_pattern_bypass_prevention_failure(self):
        """
        TEST MUST FAIL: Validate factory pattern is not properly enforced.

        EXPECTED FAILURE: Direct instantiation of WebSocket managers should be blocked
        but currently bypasses are possible, leading to duplication.

        This reproduces the pattern where tests and code directly instantiate
        managers instead of using the SSOT factory function.
        """
        self.logger.info("REPRODUCING: Factory pattern bypass for demo-user-001")

        bypass_attempts = []
        successful_bypasses = 0

        # Attempt 1: Direct class instantiation (should be blocked)
        try:
            direct_manager = WebSocketManager(user_context=self.demo_user_context)
            bypass_attempts.append(("direct_instantiation", True, direct_manager))
            successful_bypasses += 1
            self.logger.warning("BYPASS SUCCESS: Direct WebSocketManager() instantiation allowed")
        except Exception as e:
            bypass_attempts.append(("direct_instantiation", False, str(e)))
            self.logger.info(f"Direct instantiation properly blocked: {e}")

        # Attempt 2: Using __new__ directly (should be blocked)
        try:
            new_manager = WebSocketManager.__new__(WebSocketManager)
            bypass_attempts.append(("new_method", True, new_manager))
            successful_bypasses += 1
            self.logger.warning("BYPASS SUCCESS: __new__ method bypass allowed")
        except Exception as e:
            bypass_attempts.append(("new_method", False, str(e)))
            self.logger.info(f"__new__ bypass properly blocked: {e}")

        # Attempt 3: Direct implementation class access (should be controlled)
        try:
            impl_manager = _UnifiedWebSocketManagerImplementation(
                mode=create_isolated_mode("test"),
                user_context=self.demo_user_context
            )
            bypass_attempts.append(("implementation_direct", True, impl_manager))
            successful_bypasses += 1
            self.logger.warning("BYPASS SUCCESS: Direct implementation class access allowed")
        except Exception as e:
            bypass_attempts.append(("implementation_direct", False, str(e)))
            self.logger.info(f"Implementation direct access properly blocked: {e}")

        # EXPECTED FAILURE: At least one bypass should succeed (indicating vulnerability)
        self.logger.critical(f"BYPASS ANALYSIS: {successful_bypasses} successful bypasses out of {len(bypass_attempts)} attempts")

        for attempt_type, success, result in bypass_attempts:
            if success:
                self.logger.error(f"VULNERABILITY: {attempt_type} bypass succeeded: {type(result)}")
            else:
                self.logger.info(f"PROTECTION: {attempt_type} bypass blocked: {result}")

        # This assertion SHOULD FAIL - successful bypasses indicate Issue #889 root cause
        self.assertEqual(
            successful_bypasses, 0,
            f"VULNERABILITY DETECTED: {successful_bypasses} factory pattern bypasses succeeded. "
            f"This allows duplicate manager creation reproducing Issue #889."
        )

    @unittest.skipUnless(IMPORTS_AVAILABLE, "WebSocket imports not available")
    def test_enum_sharing_violation_detection(self):
        """
        TEST MUST FAIL: Detect enum sharing violations across manager instances.

        EXPECTED FAILURE: WebSocket manager instances share enum state or
        configuration objects, causing cross-contamination between users.

        This reproduces the enum sharing pattern that leads to user context
        contamination in concurrent sessions.
        """
        self.logger.info("REPRODUCING: Enum sharing violations for demo-user-001")

        # Create two managers for different contexts but track shared state
        context1 = UserContextMock(
            user_id="demo-user-001",
            session_id="session-demo-001-A"
        )
        context2 = UserContextMock(
            user_id="demo-user-001",
            session_id="session-demo-001-B"
        )

        try:
            manager1 = get_websocket_manager(user_context=context1)
            manager2 = get_websocket_manager(user_context=context2)

            shared_enums = []
            enum_violations = []

            # Check for shared enum objects
            attrs_to_check = ['mode', '_mode', 'connection_state', '_connection_state',
                            'status', '_status', 'user_context', '_user_context']

            for attr in attrs_to_check:
                try:
                    val1 = getattr(manager1, attr, None)
                    val2 = getattr(manager2, attr, None)

                    if val1 is not None and val2 is not None:
                        # Check if same object reference (violation)
                        if val1 is val2:
                            shared_enums.append((attr, val1))
                            self.logger.error(f"VIOLATION: Shared {attr} object between managers: {val1}")

                        # Check for enum contamination patterns
                        if hasattr(val1, '__dict__') and hasattr(val2, '__dict__'):
                            if id(val1.__dict__) == id(val2.__dict__):
                                enum_violations.append((attr, "shared_dict"))
                                self.logger.error(f"VIOLATION: Shared enum dict for {attr}")

                except Exception as e:
                    self.logger.debug(f"Could not check attribute {attr}: {e}")

            # Check for shared registry objects
            if hasattr(manager1, '_registry') and hasattr(manager2, '_registry'):
                if manager1._registry is manager2._registry:
                    shared_enums.append(("_registry", manager1._registry))
                    self.logger.error("VIOLATION: Shared _registry object between managers")

            self.logger.critical(
                f"ENUM SHARING ANALYSIS: {len(shared_enums)} shared objects, "
                f"{len(enum_violations)} enum violations detected"
            )

            # EXPECTED FAILURE: No objects should be shared between manager instances
            self.assertEqual(
                len(shared_enums), 0,
                f"ENUM SHARING VIOLATION: {len(shared_enums)} shared objects detected: {shared_enums}. "
                f"This reproduces cross-user contamination in Issue #889."
            )

            self.assertEqual(
                len(enum_violations), 0,
                f"ENUM STATE VIOLATION: {len(enum_violations)} enum sharing violations: {enum_violations}. "
                f"This reproduces state contamination in Issue #889."
            )

        except Exception as e:
            self.logger.error(f"Failed to test enum sharing: {e}")
            self.fail(f"Could not reproduce enum sharing violations: {e}")

    @unittest.skipUnless(IMPORTS_AVAILABLE, "WebSocket imports not available")
    def test_user_context_contamination_unit_level(self):
        """
        TEST MUST FAIL: Reproduce user context contamination at unit level.

        EXPECTED FAILURE: User contexts leak between concurrent manager instances,
        causing demo-user-001 data to appear in other user sessions.

        This is the core violation that breaks user isolation and causes
        the duplication patterns observed in production logs.
        """
        self.logger.info("REPRODUCING: User context contamination for demo-user-001")

        # Create contexts for different users
        demo_context = UserContextMock(
            user_id="demo-user-001",
            session_id="session-demo-primary",
            request_id="req-demo-primary"
        )
        other_context = UserContextMock(
            user_id="user-other-002",
            session_id="session-other-secondary",
            request_id="req-other-secondary"
        )

        contamination_detected = []
        isolation_failures = []

        try:
            # Create managers with distinct contexts
            demo_manager = get_websocket_manager(user_context=demo_context)
            other_manager = get_websocket_manager(user_context=other_context)

            # Track original context values
            demo_original_user = getattr(demo_manager, 'user_context', {})
            other_original_user = getattr(other_manager, 'user_context', {})

            self.logger.info(f"Demo manager context: {getattr(demo_original_user, 'user_id', 'unknown')}")
            self.logger.info(f"Other manager context: {getattr(other_original_user, 'user_id', 'unknown')}")

            # Simulate concurrent operations that might cause contamination
            operations = [
                ("demo_operation", demo_manager, demo_context),
                ("other_operation", other_manager, other_context),
                ("demo_concurrent", demo_manager, demo_context),
                ("other_concurrent", other_manager, other_context)
            ]

            for op_name, manager, expected_context in operations:
                try:
                    # Check if context is still correct
                    current_context = getattr(manager, 'user_context', None)
                    if current_context:
                        current_user_id = getattr(current_context, 'user_id', 'unknown')
                        expected_user_id = getattr(expected_context, 'user_id', 'unknown')

                        if current_user_id != expected_user_id:
                            contamination_detected.append({
                                'operation': op_name,
                                'expected_user': expected_user_id,
                                'actual_user': current_user_id,
                                'manager_id': id(manager)
                            })
                            self.logger.error(
                                f"CONTAMINATION: {op_name} expected {expected_user_id}, got {current_user_id}"
                            )

                        # Check for cross-reference contamination
                        if expected_user_id == "demo-user-001":
                            if current_user_id == "user-other-002":
                                isolation_failures.append({
                                    'type': 'demo_to_other_leak',
                                    'operation': op_name
                                })
                        elif expected_user_id == "user-other-002":
                            if current_user_id == "demo-user-001":
                                isolation_failures.append({
                                    'type': 'other_to_demo_leak',
                                    'operation': op_name
                                })

                except Exception as e:
                    self.logger.debug(f"Could not check context for {op_name}: {e}")

            self.logger.critical(
                f"CONTAMINATION ANALYSIS: {len(contamination_detected)} contamination events, "
                f"{len(isolation_failures)} isolation failures"
            )

            # EXPECTED FAILURE: No contamination should occur between user contexts
            self.assertEqual(
                len(contamination_detected), 0,
                f"USER CONTEXT CONTAMINATION: {len(contamination_detected)} contamination events detected: {contamination_detected}. "
                f"This reproduces the user isolation violation in Issue #889."
            )

            self.assertEqual(
                len(isolation_failures), 0,
                f"USER ISOLATION FAILURE: {len(isolation_failures)} isolation failures: {isolation_failures}. "
                f"This reproduces cross-user data leakage in Issue #889."
            )

        except Exception as e:
            self.logger.error(f"Failed to test user context contamination: {e}")
            self.fail(f"Could not reproduce user context contamination: {e}")

    def test_demo_user_001_specific_patterns(self):
        """
        TEST MUST FAIL: Reproduce specific patterns observed for demo-user-001 in GCP logs.

        EXPECTED FAILURE: The exact duplication patterns seen in staging logs
        should be reproducible with demo-user-001 context.

        This test validates the specific conditions that trigger duplication
        for this user in the production environment.
        """
        self.logger.info("REPRODUCING: Specific demo-user-001 duplication patterns from GCP logs")

        duplication_patterns = []
        gcp_like_conditions = []

        # Simulate GCP staging conditions for demo-user-001
        staging_contexts = [
            UserContextMock(
                user_id="demo-user-001",
                session_id="session-demo-staging-1",
                request_id="req-staging-1"
            ),
            UserContextMock(
                user_id="demo-user-001",
                session_id="session-demo-staging-1",  # Same session ID
                request_id="req-staging-2"  # Different request
            ),
            UserContextMock(
                user_id="demo-user-001",
                session_id="session-demo-staging-2",
                request_id="req-staging-3"
            )
        ]

        managers_created = []
        for i, context in enumerate(staging_contexts):
            try:
                # Try different creation patterns that might be used in staging
                if i == 0:
                    manager = get_websocket_manager(user_context=context)
                elif i == 1:
                    # Simulate rapid recreation (common in staging)
                    manager = get_websocket_manager(user_context=context)
                else:
                    # Simulate fallback creation
                    manager = create_test_fallback_manager(context)

                managers_created.append({
                    'index': i,
                    'manager_id': id(manager),
                    'context_session': context.session_id,
                    'context_request': context.request_id,
                    'manager_obj': manager
                })

                self.logger.info(f"Created manager {i}: ID={id(manager)}, session={context.session_id}")

            except Exception as e:
                self.logger.error(f"Failed to create staging-like manager {i}: {e}")

        # Analyze for duplication patterns matching GCP logs
        unique_manager_ids = {m['manager_id'] for m in managers_created}
        session_groups = {}

        for manager_info in managers_created:
            session_id = manager_info['context_session']
            if session_id not in session_groups:
                session_groups[session_id] = []
            session_groups[session_id].append(manager_info)

        # Check for same-session duplicates (key violation pattern)
        for session_id, managers_in_session in session_groups.items():
            if len(managers_in_session) > 1:
                manager_ids_in_session = {m['manager_id'] for m in managers_in_session}
                if len(manager_ids_in_session) > 1:
                    duplication_patterns.append({
                        'type': 'same_session_different_managers',
                        'session_id': session_id,
                        'manager_count': len(manager_ids_in_session),
                        'manager_ids': list(manager_ids_in_session)
                    })
                    self.logger.error(
                        f"DUPLICATION PATTERN: Session {session_id} has {len(manager_ids_in_session)} different managers"
                    )

        # Check for demo-user-001 specific violations
        demo_user_managers = [m for m in managers_created if "demo-user-001" in str(m.get('context_session', ''))]
        if len(demo_user_managers) > 0:
            unique_demo_managers = {m['manager_id'] for m in demo_user_managers}
            if len(unique_demo_managers) > 1:
                gcp_like_conditions.append({
                    'type': 'demo_user_multiple_managers',
                    'total_managers': len(unique_demo_managers),
                    'manager_ids': list(unique_demo_managers)
                })
                self.logger.critical(
                    f"GCP PATTERN REPRODUCED: demo-user-001 has {len(unique_demo_managers)} different managers"
                )

        self.logger.critical(
            f"DUPLICATION REPRODUCTION: {len(duplication_patterns)} patterns, "
            f"{len(gcp_like_conditions)} GCP-like conditions reproduced"
        )

        # EXPECTED FAILURE: No duplication patterns should exist for demo-user-001
        self.assertEqual(
            len(duplication_patterns), 0,
            f"DUPLICATION REPRODUCED: {len(duplication_patterns)} patterns match GCP logs: {duplication_patterns}. "
            f"This confirms Issue #889 reproduction."
        )

        self.assertEqual(
            len(gcp_like_conditions), 0,
            f"GCP VIOLATIONS REPRODUCED: {len(gcp_like_conditions)} conditions match staging: {gcp_like_conditions}. "
            f"This confirms Issue #889 reproduction."
        )


if __name__ == '__main__':
    # Configure logging for reproduction visibility
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run tests with detailed output for Issue #889 analysis
    unittest.main(verbosity=2)