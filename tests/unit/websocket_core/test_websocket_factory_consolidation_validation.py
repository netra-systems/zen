"""
Test WebSocket Factory Pattern Consolidation Validation (Issue #1055)

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure Protection
- Business Goal: Protect $500K+ ARR by eliminating WebSocket factory fragmentation
- Value Impact: Ensures consistent WebSocket Manager instantiation across user contexts
- Revenue Impact: Prevents race conditions in multi-user WebSocket creation

CRITICAL PURPOSE: These tests INITIALLY FAIL to demonstrate factory pattern fragmentation,
then PASS after SSOT factory consolidation to validate the fix.

TEST STRATEGY: Detect mixed singleton/factory patterns that cause WebSocket Manager
instantiation inconsistencies and potential race conditions.
"""

import pytest
import asyncio
import threading
import time
import concurrent.futures
from typing import Dict, List, Any, Set, Type, Optional
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from shared.types.core_types import UserID, ensure_user_id


@dataclass
class FactoryPatternAnalysis:
    """Analysis results for factory pattern implementation."""
    pattern_type: str  # "singleton", "factory", "mixed", "adapter"
    instance_consistency: bool
    user_isolation: bool
    thread_safety: bool
    creation_method: str
    detected_issues: List[str]


class WebSocketFactoryConsolidationValidationTests(BaseIntegrationTest):
    """Test WebSocket factory pattern consolidation for SSOT validation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory_analysis_results = {}
        self.created_instances = []

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_mixed_singleton_factory_pattern_detection(self):
        """
        FAIL-FIRST TEST: Detect mixed singleton/factory patterns.

        This test identifies WebSocket Manager implementations that mix
        singleton and factory patterns, which can cause race conditions
        and inconsistent instance creation.
        """
        # Test different instantiation patterns
        patterns_to_test = [
            ("unified_manager_singleton", self._test_unified_manager_singleton_pattern),
            ("factory_pattern", self._test_factory_pattern_creation),
            ("adapter_singleton", self._test_adapter_singleton_pattern),
            ("mixed_pattern", self._test_mixed_instantiation_pattern)
        ]

        detected_patterns = {}
        pattern_inconsistencies = []

        for pattern_name, test_func in patterns_to_test:
            try:
                analysis = test_func()
                detected_patterns[pattern_name] = analysis

                # Check for pattern inconsistencies
                if analysis.pattern_type == "mixed":
                    pattern_inconsistencies.append(pattern_name)

                print(f"PATTERN ANALYSIS - {pattern_name}: {analysis.pattern_type}")
                if analysis.detected_issues:
                    print(f"  Issues: {analysis.detected_issues}")

            except Exception as e:
                print(f"Pattern {pattern_name} not available: {e}")

        # ASSERTION: Mixed patterns indicate SSOT violation
        if pattern_inconsistencies:
            pytest.fail(
                f"SSOT VIOLATION: Mixed singleton/factory patterns detected: "
                f"{pattern_inconsistencies}. This indicates inconsistent instantiation "
                f"patterns that can cause race conditions and user isolation failures. "
                f"All patterns should be consolidated to a single SSOT approach."
            )

        # Check for multiple active patterns (also a violation)
        active_patterns = [name for name, analysis in detected_patterns.items()
                          if analysis and not analysis.detected_issues]

        if len(active_patterns) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Multiple WebSocket Manager instantiation patterns active: "
                f"{active_patterns}. After SSOT consolidation, only one pattern should be available."
            )

        # SUCCESS: Only one consistent pattern should remain
        assert len(active_patterns) <= 1, (
            f"Expected at most 1 active instantiation pattern after SSOT consolidation, "
            f"found {len(active_patterns)}: {active_patterns}"
        )

    def _test_unified_manager_singleton_pattern(self) -> FactoryPatternAnalysis:
        """Test unified manager singleton pattern."""
        try:
            # Test singleton behavior
            from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager

            instance1 = UnifiedWebSocketManager()
            instance2 = UnifiedWebSocketManager()

            # Analyze singleton characteristics
            is_singleton = id(instance1) == id(instance2)
            issues = []

            if is_singleton:
                issues.append("Singleton pattern detected - may cause user isolation issues")

            return FactoryPatternAnalysis(
                pattern_type="singleton" if is_singleton else "factory",
                instance_consistency=True,
                user_isolation=not is_singleton,
                thread_safety=True,  # Assume true, would need deeper testing
                creation_method="direct_instantiation",
                detected_issues=issues
            )

        except ImportError:
            return FactoryPatternAnalysis(
                pattern_type="unavailable",
                instance_consistency=False,
                user_isolation=False,
                thread_safety=False,
                creation_method="none",
                detected_issues=["UnifiedWebSocketManager not available"]
            )

    def _test_factory_pattern_creation(self) -> FactoryPatternAnalysis:
        """Test factory pattern creation."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

            factory = WebSocketManagerFactory()

            # Create instances with different contexts
            user1_context = self._create_test_user_context("user1")
            user2_context = self._create_test_user_context("user2")

            instance1 = factory.create_websocket_manager(user_context=user1_context)
            instance2 = factory.create_websocket_manager(user_context=user2_context)
            instance3 = factory.create_websocket_manager(user_context=user1_context)  # Same user

            # Analyze factory behavior
            different_users_isolated = id(instance1) != id(instance2)
            same_user_consistent = id(instance1) == id(instance3)  # May or may not be true

            issues = []
            if not different_users_isolated:
                issues.append("Factory not providing user isolation")

            return FactoryPatternAnalysis(
                pattern_type="factory",
                instance_consistency=True,
                user_isolation=different_users_isolated,
                thread_safety=True,  # Would need concurrent testing
                creation_method="factory_method",
                detected_issues=issues
            )

        except ImportError:
            return FactoryPatternAnalysis(
                pattern_type="unavailable",
                instance_consistency=False,
                user_isolation=False,
                thread_safety=False,
                creation_method="none",
                detected_issues=["WebSocketManagerFactory not available"]
            )

    def _test_adapter_singleton_pattern(self) -> FactoryPatternAnalysis:
        """Test adapter singleton pattern."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

            # Create adapters with mock managers
            mock_manager1 = MagicMock()
            mock_manager2 = MagicMock()

            adapter1 = WebSocketManagerAdapter(mock_manager1)
            adapter2 = WebSocketManagerAdapter(mock_manager2)

            # Adapters should be different instances
            different_instances = id(adapter1) != id(adapter2)

            issues = []
            if not different_instances:
                issues.append("Adapter pattern showing singleton behavior")

            return FactoryPatternAnalysis(
                pattern_type="adapter",
                instance_consistency=True,
                user_isolation=different_instances,
                thread_safety=True,
                creation_method="adapter_pattern",
                detected_issues=issues
            )

        except ImportError:
            return FactoryPatternAnalysis(
                pattern_type="unavailable",
                instance_consistency=False,
                user_isolation=False,
                thread_safety=False,
                creation_method="none",
                detected_issues=["WebSocketManagerAdapter not available"]
            )

    def _test_mixed_instantiation_pattern(self) -> FactoryPatternAnalysis:
        """Test for mixed instantiation patterns."""
        creation_methods = []
        issues = []

        try:
            # Try direct instantiation
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            instance1 = WebSocketManager()
            creation_methods.append("direct")
        except ImportError:
            pass

        try:
            # Try factory creation
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            user_context = self._create_test_user_context("test_user")
            instance2 = create_websocket_manager(user_context=user_context)
            creation_methods.append("factory_function")
        except ImportError:
            pass

        try:
            # Try unified manager
            from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
            instance3 = UnifiedWebSocketManager()
            creation_methods.append("unified")
        except ImportError:
            pass

        # Mixed patterns indicate fragmentation
        if len(creation_methods) > 1:
            issues.append(f"Multiple creation methods available: {creation_methods}")

        return FactoryPatternAnalysis(
            pattern_type="mixed" if len(creation_methods) > 1 else "single",
            instance_consistency=len(creation_methods) <= 1,
            user_isolation=False,  # Can't determine with mixed patterns
            thread_safety=False,  # Can't guarantee with mixed patterns
            creation_method=",".join(creation_methods) if creation_methods else "none",
            detected_issues=issues
        )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_concurrent_websocket_manager_creation_race_conditions(self):
        """
        FAIL-FIRST TEST: Detect race conditions in concurrent WebSocket Manager creation.

        This test simulates concurrent creation of WebSocket Manager instances
        to detect race conditions that occur with fragmented factory patterns.
        """
        # Test concurrent creation with multiple users
        num_threads = 8
        num_users = 5
        creation_results = []
        creation_errors = []
        result_lock = threading.Lock()

        def create_websocket_manager_concurrently(user_id: str, thread_id: int) -> None:
            """Create WebSocket Manager in concurrent thread."""
            try:
                start_time = time.time()

                # Try different creation methods
                creation_attempts = []

                # Method 1: Direct instantiation (if available)
                try:
                    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                    instance1 = WebSocketManager()
                    creation_attempts.append(("direct", instance1, time.time() - start_time))
                except ImportError:
                    pass

                # Method 2: Factory pattern (if available)
                try:
                    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                    user_context = self._create_test_user_context(user_id)
                    instance2 = create_websocket_manager(user_context=user_context)
                    creation_attempts.append(("factory", instance2, time.time() - start_time))
                except ImportError:
                    pass

                # Method 3: Unified manager (if available)
                try:
                    from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
                    instance3 = UnifiedWebSocketManager()
                    creation_attempts.append(("unified", instance3, time.time() - start_time))
                except ImportError:
                    pass

                with result_lock:
                    for method, instance, duration in creation_attempts:
                        creation_results.append({
                            'user_id': user_id,
                            'thread_id': thread_id,
                            'method': method,
                            'instance_id': id(instance),
                            'instance_type': type(instance).__name__,
                            'duration': duration,
                            'success': True
                        })

            except Exception as e:
                with result_lock:
                    creation_errors.append({
                        'user_id': user_id,
                        'thread_id': thread_id,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })

        # Execute concurrent creation
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for thread_id in range(num_threads):
                for user_num in range(num_users):
                    user_id = f"user_{user_num}"
                    future = executor.submit(create_websocket_manager_concurrently, user_id, thread_id)
                    futures.append(future)

            # Wait for all futures to complete
            concurrent.futures.wait(futures, timeout=30)

        # Analyze results for race conditions
        methods_used = set(result['method'] for result in creation_results)
        user_instances = {}

        # Group results by user to check isolation
        for result in creation_results:
            user_id = result['user_id']
            if user_id not in user_instances:
                user_instances[user_id] = []
            user_instances[user_id].append(result)

        # Check for race condition indicators
        race_condition_indicators = []

        # Multiple creation methods indicate fragmentation
        if len(methods_used) > 1:
            race_condition_indicators.append(f"Multiple creation methods used concurrently: {methods_used}")

        # Check for inconsistent instance creation per user
        for user_id, instances in user_instances.items():
            instance_ids = set(instance['instance_id'] for instance in instances)
            methods = set(instance['method'] for instance in instances)

            if len(methods) > 1:
                race_condition_indicators.append(f"User {user_id} created via multiple methods: {methods}")

            # If singleton pattern, all instances should be the same
            # If factory pattern, instances might be different (depends on implementation)

        # ASSERTION: Race condition indicators suggest SSOT violation
        if race_condition_indicators:
            pytest.fail(
                f"SSOT VIOLATION: Race condition indicators detected in concurrent WebSocket Manager creation: "
                f"{race_condition_indicators}. "
                f"Total successes: {len(creation_results)}, Errors: {len(creation_errors)}. "
                f"This suggests fragmented factory patterns causing concurrent creation issues."
            )

        # SUCCESS: Consistent creation pattern with no race conditions
        assert len(methods_used) <= 1, (
            f"Expected at most 1 creation method after SSOT consolidation, "
            f"found {len(methods_used)}: {methods_used}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_user_context_isolation_consistency(self):
        """
        FAIL-FIRST TEST: Validate consistent user context isolation across factory patterns.

        This test ensures that all WebSocket Manager factory patterns provide
        consistent user context isolation behavior.
        """
        test_users = [ensure_user_id(f"user_{i}") for i in range(3)]
        isolation_results = {}

        # Test isolation across different factory patterns
        factory_patterns = [
            ("direct_instantiation", self._test_direct_instantiation_isolation),
            ("factory_pattern", self._test_factory_pattern_isolation),
            ("unified_manager", self._test_unified_manager_isolation)
        ]

        for pattern_name, test_func in factory_patterns:
            try:
                isolation_results[pattern_name] = test_func(test_users)
                print(f"ISOLATION TEST - {pattern_name}: {isolation_results[pattern_name]}")
            except Exception as e:
                isolation_results[pattern_name] = {
                    'error': str(e),
                    'isolated': False,
                    'consistent': False
                }

        # Analyze isolation consistency
        working_patterns = {name: result for name, result in isolation_results.items()
                           if 'error' not in result}

        if len(working_patterns) > 1:
            # Check for inconsistent isolation behavior
            isolation_behaviors = set()
            for pattern, result in working_patterns.items():
                isolation_behaviors.add(result.get('isolated', False))

            # ASSERTION: Inconsistent isolation indicates SSOT violation
            if len(isolation_behaviors) > 1:
                pytest.fail(
                    f"SSOT VIOLATION: Inconsistent user isolation behavior across WebSocket Manager factory patterns. "
                    f"Pattern results: {working_patterns}. "
                    f"This inconsistency can cause user data leakage and security issues."
                )

        # SUCCESS: Consistent isolation behavior (or only one pattern exists)
        if working_patterns:
            for pattern, result in working_patterns.items():
                assert result.get('isolated', False), (
                    f"Factory pattern {pattern} should provide user isolation"
                )
                assert result.get('consistent', False), (
                    f"Factory pattern {pattern} should be consistent"
                )

    def _test_direct_instantiation_isolation(self, test_users: List[UserID]) -> Dict[str, Any]:
        """Test isolation for direct instantiation pattern."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

            instances = []
            for user_id in test_users:
                # Direct instantiation doesn't typically take user context
                instance = WebSocketManager()
                instances.append(instance)

            # Check if instances are isolated
            instance_ids = [id(instance) for instance in instances]
            isolated = len(set(instance_ids)) == len(instances)

            return {
                'isolated': isolated,
                'consistent': True,
                'method': 'direct_instantiation',
                'instance_count': len(instances),
                'unique_instances': len(set(instance_ids))
            }

        except ImportError:
            raise Exception("Direct instantiation not available")

    def _test_factory_pattern_isolation(self, test_users: List[UserID]) -> Dict[str, Any]:
        """Test isolation for factory pattern."""
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

            instances = []
            for user_id in test_users:
                user_context = self._create_test_user_context(str(user_id))
                instance = create_websocket_manager(user_context=user_context)
                instances.append(instance)

            # Check isolation
            instance_ids = [id(instance) for instance in instances]
            isolated = len(set(instance_ids)) == len(instances)

            return {
                'isolated': isolated,
                'consistent': True,
                'method': 'factory_pattern',
                'instance_count': len(instances),
                'unique_instances': len(set(instance_ids))
            }

        except ImportError:
            raise Exception("Factory pattern not available")

    def _test_unified_manager_isolation(self, test_users: List[UserID]) -> Dict[str, Any]:
        """Test isolation for unified manager pattern."""
        try:
            from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager

            instances = []
            for user_id in test_users:
                instance = UnifiedWebSocketManager()
                instances.append(instance)

            # Check isolation (unified manager might be singleton)
            instance_ids = [id(instance) for instance in instances]
            isolated = len(set(instance_ids)) == len(instances)

            return {
                'isolated': isolated,
                'consistent': True,
                'method': 'unified_manager',
                'instance_count': len(instances),
                'unique_instances': len(set(instance_ids)),
                'note': 'Unified manager may use singleton pattern'
            }

        except ImportError:
            raise Exception("Unified manager not available")

    def _create_test_user_context(self, user_id: str) -> Any:
        """Create a test user context object."""
        try:
            from netra_backend.app.core.user_context.factory import UserExecutionContextFactory
            return UserExecutionContextFactory.create_test_context(user_id=user_id)
        except ImportError:
            # Fallback to mock context
            return type('MockUserContext', (), {
                'user_id': ensure_user_id(user_id),
                'session_id': f"session_{user_id}",
                'is_test': True
            })()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_lifecycle_consistency(self):
        """
        FAIL-FIRST TEST: Validate consistent lifecycle management across factory patterns.

        This test ensures that WebSocket Manager instances created through different
        factory patterns have consistent lifecycle behavior (creation, cleanup, etc.).
        """
        lifecycle_patterns = {}

        # Test lifecycle for different patterns
        patterns_to_test = [
            ("direct", self._test_direct_lifecycle),
            ("factory", self._test_factory_lifecycle),
            ("unified", self._test_unified_lifecycle)
        ]

        for pattern_name, test_func in patterns_to_test:
            try:
                lifecycle_result = test_func()
                lifecycle_patterns[pattern_name] = lifecycle_result
            except Exception as e:
                lifecycle_patterns[pattern_name] = {
                    'error': str(e),
                    'lifecycle_consistent': False
                }

        # Analyze lifecycle consistency
        working_patterns = {name: result for name, result in lifecycle_patterns.items()
                           if 'error' not in result}

        if len(working_patterns) > 1:
            # Check for inconsistent lifecycle behavior
            lifecycle_behaviors = set()
            for pattern, result in working_patterns.items():
                behavior_signature = f"{result.get('supports_cleanup', False)}_{result.get('supports_context', False)}"
                lifecycle_behaviors.add(behavior_signature)

            # ASSERTION: Inconsistent lifecycle indicates fragmentation
            if len(lifecycle_behaviors) > 1:
                pytest.fail(
                    f"SSOT VIOLATION: Inconsistent WebSocket Manager lifecycle behavior across patterns. "
                    f"Pattern results: {working_patterns}. "
                    f"Different lifecycle behaviors detected: {lifecycle_behaviors}. "
                    f"This inconsistency can cause resource leaks and cleanup issues."
                )

        # SUCCESS: Consistent lifecycle behavior
        print(f"WebSocket Manager lifecycle analysis: {working_patterns}")

    def _test_direct_lifecycle(self) -> Dict[str, Any]:
        """Test lifecycle for direct instantiation."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

        instance = WebSocketManager()

        # Test lifecycle methods
        supports_cleanup = hasattr(instance, 'cleanup') or hasattr(instance, 'close')
        supports_context = hasattr(instance, 'set_context') or hasattr(instance, 'user_context')

        return {
            'supports_cleanup': supports_cleanup,
            'supports_context': supports_context,
            'lifecycle_consistent': True,
            'pattern': 'direct'
        }

    def _test_factory_lifecycle(self) -> Dict[str, Any]:
        """Test lifecycle for factory pattern."""
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

        user_context = self._create_test_user_context("test_user")
        instance = create_websocket_manager(user_context=user_context)

        supports_cleanup = hasattr(instance, 'cleanup') or hasattr(instance, 'close')
        supports_context = hasattr(instance, 'set_context') or hasattr(instance, 'user_context')

        return {
            'supports_cleanup': supports_cleanup,
            'supports_context': supports_context,
            'lifecycle_consistent': True,
            'pattern': 'factory'
        }

    def _test_unified_lifecycle(self) -> Dict[str, Any]:
        """Test lifecycle for unified manager."""
        from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager

        instance = UnifiedWebSocketManager()

        supports_cleanup = hasattr(instance, 'cleanup') or hasattr(instance, 'close')
        supports_context = hasattr(instance, 'set_context') or hasattr(instance, 'user_context')

        return {
            'supports_cleanup': supports_cleanup,
            'supports_context': supports_context,
            'lifecycle_consistent': True,
            'pattern': 'unified'
        }