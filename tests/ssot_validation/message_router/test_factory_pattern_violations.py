"""
Test Factory Pattern Violations - Phase 1 SSOT Violation Detection

CRITICAL TEST PURPOSE: Detect mixed singleton/factory patterns in WebSocket bridge
These tests MUST FAIL initially to prove SSOT violations exist:

1. AgentWebSocketBridge incomplete singleton removal
2. User isolation failures in WebSocket bridge
3. Mixed factory/singleton pattern inconsistencies

Business Value Justification (BVJ):
- Segment: Platform/Internal - SSOT Compliance & User Security
- Business Goal: Eliminate user isolation failures causing cross-user data leakage
- Value Impact: Detect factory pattern violations that create security vulnerabilities
- Strategic Impact: Foundation for $500K+ ARR protection through proper user isolation

EXPECTED RESULT: These tests SHOULD FAIL, proving SSOT violations exist
SUCCESS CRITERIA: Tests fail demonstrating factory pattern violations and user isolation issues

GitHub Issue: #1074 Message Router SSOT Violations - Phase 1 Detection
"""

import pytest
import asyncio
import importlib
import inspect
import threading
import time
from typing import Dict, Any, List, Callable, Set, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class FactoryPatternViolationsTests(SSotAsyncTestCase):
    """
    Phase 1 SSOT Violation Detection: Mixed singleton/factory patterns in WebSocket bridge

    CRITICAL: These tests MUST FAIL to prove SSOT violations exist.
    Success is measured by test failure, not pass.
    """

    def setup_method(self, method):
        """Setup factory pattern violation detection test."""
        super().setup_method(method)
        self.bridge_instances = {}
        self.user_isolation_violations = []
        self.violation_evidence = {}

    async def test_detect_singleton_factory_pattern_mixing(self):
        """
        VIOLATION DETECTION: Mixed singleton/factory patterns in AgentWebSocketBridge

        EXPECTED: FAIL - Mixed patterns should be detected
        PURPOSE: Prove factory pattern violations exist in WebSocket bridge
        """
        # Test for singleton pattern remnants
        singleton_indicators = []

        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Check for singleton pattern indicators
            bridge_class = AgentWebSocketBridge

            # Look for singleton-like class methods or attributes
            class_methods = inspect.getmembers(bridge_class, predicate=inspect.ismethod)
            class_attributes = [attr for attr in dir(bridge_class) if not attr.startswith('__')]

            singleton_patterns = [
                '_instance',
                '_instances',
                'get_instance',
                'getInstance',
                'singleton',
                '_singleton',
                'instance'
            ]

            for pattern in singleton_patterns:
                if pattern in class_attributes:
                    singleton_indicators.append({
                        'pattern': pattern,
                        'location': f"AgentWebSocketBridge.{pattern}",
                        'type': 'class_attribute'
                    })

            # Check for singleton-like methods
            singleton_methods = [
                'get_instance',
                'create_instance',
                'get_or_create',
                'singleton'
            ]

            for method_name, method_obj in class_methods:
                if method_name in singleton_methods:
                    singleton_indicators.append({
                        'pattern': method_name,
                        'location': f"AgentWebSocketBridge.{method_name}",
                        'type': 'class_method'
                    })

            # Check constructor for singleton-like behavior
            init_source = inspect.getsource(bridge_class.__init__)
            singleton_init_patterns = [
                'if not hasattr',
                '_instance =',
                'instance =',
                'singleton'
            ]

            for pattern in singleton_init_patterns:
                if pattern in init_source:
                    singleton_indicators.append({
                        'pattern': pattern,
                        'location': f"AgentWebSocketBridge.__init__",
                        'type': 'constructor_pattern',
                        'source_hint': init_source[:200]  # First 200 chars
                    })

        except (ImportError, AttributeError) as e:
            self.logger.debug(f"AgentWebSocketBridge analysis failed: {e}")

        # Record violation evidence
        self.violation_evidence['singleton_indicators'] = singleton_indicators

        # Log singleton pattern analysis
        self.logger.info(f"SINGLETON PATTERN ANALYSIS: Found {len(singleton_indicators)} singleton indicators:")
        for indicator in singleton_indicators:
            self.logger.info(f"  - {indicator['pattern']} at {indicator['location']} ({indicator['type']})")

        # CRITICAL ASSERTION: This SHOULD FAIL if singleton patterns remain
        assert len(singleton_indicators) == 0, (
            f"SSOT VIOLATION DETECTED: Found {len(singleton_indicators)} singleton pattern indicators in AgentWebSocketBridge. "
            f"Factory pattern migration requires complete singleton removal. "
            f"Detected patterns: {[ind['pattern'] for ind in singleton_indicators]}"
        )

        # If this assertion passes, no singleton patterns exist (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: No singleton pattern remnants detected in AgentWebSocketBridge")

    async def test_detect_user_isolation_failures(self):
        """
        VIOLATION DETECTION: User isolation failures in WebSocket bridge instances

        EXPECTED: FAIL - User isolation failures should be detected
        PURPOSE: Prove user isolation violations exist in factory pattern implementation
        """
        user_contamination_evidence = []

        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Create multiple bridge instances for different "users"
            test_users = ["user_1", "user_2", "user_3"]
            bridge_instances = {}

            for user_id in test_users:
                try:
                    # Try to create user-specific instances
                    bridge = AgentWebSocketBridge()
                    bridge_instances[user_id] = bridge

                    # Set user-specific state (if possible)
                    if hasattr(bridge, 'user_id'):
                        bridge.user_id = user_id
                    if hasattr(bridge, 'user_context'):
                        bridge.user_context = {'user_id': user_id}

                except Exception as e:
                    self.logger.debug(f"Could not create bridge instance for {user_id}: {e}")

            # Test for shared state between instances (isolation violation)
            if len(bridge_instances) >= 2:
                bridge_1 = list(bridge_instances.values())[0]
                bridge_2 = list(bridge_instances.values())[1]

                # Check if instances share the same object identity (singleton behavior)
                if bridge_1 is bridge_2:
                    user_contamination_evidence.append({
                        'violation_type': 'shared_instance',
                        'description': 'Multiple user bridge instances are the same object',
                        'evidence': f"id(bridge_1): {id(bridge_1)}, id(bridge_2): {id(bridge_2)}"
                    })

                # Check for shared state attributes
                shared_attributes = []
                for attr_name in dir(bridge_1):
                    if not attr_name.startswith('__') and hasattr(bridge_2, attr_name):
                        attr_1 = getattr(bridge_1, attr_name)
                        attr_2 = getattr(bridge_2, attr_name)

                        # Check if attributes point to the same object (not just equal values)
                        if attr_1 is attr_2 and not callable(attr_1) and not isinstance(attr_1, (type, type(None))):
                            shared_attributes.append({
                                'attribute': attr_name,
                                'shared_object_id': id(attr_1),
                                'type': type(attr_1).__name__
                            })

                if shared_attributes:
                    user_contamination_evidence.append({
                        'violation_type': 'shared_state',
                        'description': f'Bridge instances share {len(shared_attributes)} state attributes',
                        'evidence': shared_attributes
                    })

                # Test for cross-user state contamination
                try:
                    # Set different state in each instance
                    if hasattr(bridge_1, 'websocket_manager'):
                        # Mock different websocket managers
                        bridge_1.websocket_manager = MagicMock(name="manager_1")
                        bridge_2.websocket_manager = MagicMock(name="manager_2")

                        # Check if setting state on one affects the other
                        if bridge_1.websocket_manager is bridge_2.websocket_manager:
                            user_contamination_evidence.append({
                                'violation_type': 'state_contamination',
                                'description': 'WebSocket manager state shared between user instances',
                                'evidence': 'bridge_1.websocket_manager is bridge_2.websocket_manager'
                            })

                except Exception as e:
                    self.logger.debug(f"Could not test websocket manager isolation: {e}")

        except (ImportError, AttributeError) as e:
            self.logger.debug(f"User isolation testing failed: {e}")

        # Record violation evidence
        self.violation_evidence['user_contamination_evidence'] = user_contamination_evidence

        # Log user isolation violation analysis
        self.logger.info(f"USER ISOLATION ANALYSIS: Found {len(user_contamination_evidence)} isolation violations:")
        for violation in user_contamination_evidence:
            self.logger.info(f"  - {violation['violation_type']}: {violation['description']}")

        # CRITICAL ASSERTION: This SHOULD FAIL if user isolation violations exist
        assert len(user_contamination_evidence) == 0, (
            f"SSOT VIOLATION DETECTED: Found {len(user_contamination_evidence)} user isolation violations in AgentWebSocketBridge. "
            f"Factory pattern requires complete user isolation to prevent cross-user data leakage. "
            f"Violations: {[v['violation_type'] for v in user_contamination_evidence]}"
        )

        # If this assertion passes, user isolation works properly (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: No user isolation violations detected")

    async def test_detect_concurrent_user_factory_conflicts(self):
        """
        VIOLATION DETECTION: Concurrent user factory pattern conflicts

        EXPECTED: FAIL - Factory conflicts under concurrent usage should be detected
        PURPOSE: Prove factory pattern is not thread-safe or user-isolated
        """
        concurrency_violations = []

        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Test concurrent bridge creation/usage
            num_concurrent_users = 5
            num_operations_per_user = 10
            shared_state_detected = False
            race_conditions = []

            async def create_and_use_bridge(user_id: str, operation_id: int):
                """Simulate concurrent bridge usage by different users."""
                try:
                    # Create bridge instance
                    bridge = AgentWebSocketBridge()

                    # Set user-specific identifier
                    bridge_id = f"{user_id}_{operation_id}"

                    # Store in instance tracking
                    instance_key = f"{user_id}_{operation_id}"
                    self.bridge_instances[instance_key] = {
                        'bridge': bridge,
                        'user_id': user_id,
                        'operation_id': operation_id,
                        'creation_time': time.time(),
                        'thread_id': threading.get_ident()
                    }

                    # Simulate some bridge operations
                    await asyncio.sleep(0.01)  # Small delay to increase race condition chances

                    # Check if bridge has user-specific state isolation
                    if hasattr(bridge, 'connections') and bridge.connections is not None:
                        # Check if connections are shared across users (violation)
                        connection_id = id(bridge.connections)

                        # Store connection info for later analysis
                        if not hasattr(self, 'connection_ids'):
                            self.connection_ids = {}

                        if connection_id in self.connection_ids:
                            race_conditions.append({
                                'type': 'shared_connections',
                                'user_1': self.connection_ids[connection_id],
                                'user_2': user_id,
                                'shared_object_id': connection_id
                            })
                        else:
                            self.connection_ids[connection_id] = user_id

                except Exception as e:
                    race_conditions.append({
                        'type': 'creation_exception',
                        'user_id': user_id,
                        'operation_id': operation_id,
                        'error': str(e)
                    })

            # Run concurrent bridge operations
            tasks = []
            for user_num in range(num_concurrent_users):
                user_id = f"concurrent_user_{user_num}"
                for op_num in range(num_operations_per_user):
                    tasks.append(create_and_use_bridge(user_id, op_num))

            # Execute all tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results for concurrency violations
            if len(self.bridge_instances) > 1:
                # Check if instances share identity (singleton behavior under concurrency)
                bridge_objects = [info['bridge'] for info in self.bridge_instances.values()]
                unique_bridge_ids = set(id(bridge) for bridge in bridge_objects)

                expected_unique_bridges = len(self.bridge_instances)
                actual_unique_bridges = len(unique_bridge_ids)

                if actual_unique_bridges < expected_unique_bridges:
                    concurrency_violations.append({
                        'violation_type': 'shared_instances_under_concurrency',
                        'expected_instances': expected_unique_bridges,
                        'actual_unique_instances': actual_unique_bridges,
                        'sharing_ratio': actual_unique_bridges / expected_unique_bridges
                    })

            # Add race condition violations
            concurrency_violations.extend(race_conditions)

        except (ImportError, AttributeError) as e:
            self.logger.debug(f"Concurrency testing failed: {e}")

        # Record violation evidence
        self.violation_evidence['concurrency_violations'] = concurrency_violations

        # Log concurrency violation analysis
        self.logger.info(f"CONCURRENCY ANALYSIS: Found {len(concurrency_violations)} concurrency violations:")
        for violation in concurrency_violations:
            self.logger.info(f"  - {violation.get('violation_type', violation.get('type', 'unknown'))}")

        # CRITICAL ASSERTION: This SHOULD FAIL if concurrency violations exist
        assert len(concurrency_violations) == 0, (
            f"SSOT VIOLATION DETECTED: Found {len(concurrency_violations)} concurrency violations in AgentWebSocketBridge factory pattern. "
            f"Factory pattern must support concurrent user operations without state sharing. "
            f"Violation types: {[v.get('violation_type', v.get('type', 'unknown')) for v in concurrency_violations]}"
        )

        # If this assertion passes, concurrent factory usage works properly (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: No concurrency violations detected in factory pattern")

    async def test_detect_websocket_manager_factory_inconsistencies(self):
        """
        VIOLATION DETECTION: Inconsistent factory patterns between bridge and WebSocket manager

        EXPECTED: FAIL - Factory pattern inconsistencies should be detected
        PURPOSE: Prove inconsistent factory implementations across related components
        """
        factory_inconsistencies = []

        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Analyze AgentWebSocketBridge factory behavior
            bridge_1 = AgentWebSocketBridge()
            bridge_2 = AgentWebSocketBridge()

            # Check if bridges use consistent WebSocket manager creation
            websocket_manager_consistency = []

            if hasattr(bridge_1, 'websocket_manager') and hasattr(bridge_2, 'websocket_manager'):
                # Check if websocket managers are the same instance (singleton) or different (factory)
                manager_1 = bridge_1.websocket_manager
                manager_2 = bridge_2.websocket_manager

                if manager_1 is manager_2:
                    websocket_manager_consistency.append({
                        'issue': 'shared_websocket_manager',
                        'description': 'Different bridge instances share the same WebSocket manager',
                        'manager_id': id(manager_1)
                    })

                # Check for factory method consistency
                if hasattr(bridge_1, 'create_websocket_manager'):
                    try:
                        created_manager_1 = bridge_1.create_websocket_manager()
                        created_manager_2 = bridge_2.create_websocket_manager()

                        if created_manager_1 is created_manager_2:
                            websocket_manager_consistency.append({
                                'issue': 'factory_method_returns_singleton',
                                'description': 'Factory method returns same instance instead of creating new ones',
                                'created_manager_id': id(created_manager_1)
                            })
                    except Exception as e:
                        websocket_manager_consistency.append({
                            'issue': 'factory_method_error',
                            'description': f'Factory method failed: {str(e)}',
                            'error': str(e)
                        })

            factory_inconsistencies.extend(websocket_manager_consistency)

            # Test for dependency injection pattern consistency
            dependency_patterns = []

            # Check if bridge accepts external dependencies (proper factory)
            try:
                # Try creating bridge with mock dependencies
                mock_manager = MagicMock()
                mock_registry = MagicMock()

                # Different ways bridge might accept dependencies
                dependency_test_methods = [
                    lambda: AgentWebSocketBridge(websocket_manager=mock_manager),
                    lambda: AgentWebSocketBridge(registry=mock_registry),
                    lambda: AgentWebSocketBridge(manager=mock_manager, registry=mock_registry)
                ]

                successful_dependency_injections = 0
                for test_method in dependency_test_methods:
                    try:
                        bridge_with_deps = test_method()
                        successful_dependency_injections += 1
                    except TypeError:
                        # Expected if bridge doesn't accept these parameters
                        pass

                if successful_dependency_injections == 0:
                    dependency_patterns.append({
                        'issue': 'no_dependency_injection',
                        'description': 'Bridge does not support dependency injection (rigid factory)',
                        'tested_methods': len(dependency_test_methods)
                    })

            except Exception as e:
                dependency_patterns.append({
                    'issue': 'dependency_injection_test_failed',
                    'description': f'Could not test dependency injection: {str(e)}',
                    'error': str(e)
                })

            factory_inconsistencies.extend(dependency_patterns)

        except (ImportError, AttributeError) as e:
            self.logger.debug(f"Factory inconsistency testing failed: {e}")

        # Record violation evidence
        self.violation_evidence['factory_inconsistencies'] = factory_inconsistencies

        # Log factory inconsistency analysis
        self.logger.info(f"FACTORY INCONSISTENCY ANALYSIS: Found {len(factory_inconsistencies)} inconsistencies:")
        for inconsistency in factory_inconsistencies:
            self.logger.info(f"  - {inconsistency['issue']}: {inconsistency['description']}")

        # CRITICAL ASSERTION: This SHOULD FAIL if factory inconsistencies exist
        assert len(factory_inconsistencies) == 0, (
            f"SSOT VIOLATION DETECTED: Found {len(factory_inconsistencies)} factory pattern inconsistencies. "
            f"Consistent factory patterns required across WebSocket bridge and related components. "
            f"Inconsistencies: {[inc['issue'] for inc in factory_inconsistencies]}"
        )

        # If this assertion passes, factory patterns are consistent (unexpected for Phase 1)
        self.logger.warning("UNEXPECTED: No factory pattern inconsistencies detected")

    def teardown_method(self, method):
        """Teardown and record violation evidence."""
        super().teardown_method(method)

        # Clean up test instances
        self.bridge_instances.clear()
        if hasattr(self, 'connection_ids'):
            self.connection_ids.clear()

        # Log summary of factory pattern violations detected
        if self.violation_evidence:
            self.logger.info("FACTORY PATTERN SSOT VIOLATION EVIDENCE SUMMARY:")
            self.logger.info(f"  - Singleton indicators: {len(self.violation_evidence.get('singleton_indicators', []))}")
            self.logger.info(f"  - User isolation violations: {len(self.violation_evidence.get('user_contamination_evidence', []))}")
            self.logger.info(f"  - Concurrency violations: {len(self.violation_evidence.get('concurrency_violations', []))}")
            self.logger.info(f"  - Factory inconsistencies: {len(self.violation_evidence.get('factory_inconsistencies', []))}")

            # Record detailed evidence for remediation planning
            if hasattr(self, '_test_context') and self._test_context:
                self.record_metric('factory_pattern_violations_detected', True)
                self.record_metric('factory_violation_evidence', self.violation_evidence)