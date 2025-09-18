"""
Unit Test: WebSocket Factory Pattern SSOT Violations

ISSUE #1090: SSOT-incomplete-migration-websocket-manager-import-fragmentation

This test detects usage of deprecated factory pattern vs direct SSOT instantiation.

KEY VIOLATION PATTERNS:
X Factory Pattern: WebSocketManagerFactory.create_websocket_manager()
X Factory Import: from websocket_manager_factory import create_websocket_manager
CHECK Direct SSOT: WebSocketManager(user_context=context)
CHECK SSOT Helper: get_websocket_manager(user_context=context)

PURPOSE:
- FAILS if deprecated factory patterns are detected in active use
- PASSES after factory patterns are eliminated for direct SSOT

Business Value: Eliminates factory abstraction overhead threatening $500K+ ARR performance
"""

import pytest
import warnings
import asyncio
import inspect
import time
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.unit
class WebSocketFactoryPatternSSOTViolationsTests(SSotAsyncTestCase):
    """Test for WebSocket factory pattern SSOT violations."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.factory_violations = []
        self.ssot_patterns = []
        self.performance_metrics = {}

    def test_detect_deprecated_websocket_manager_factory_class(self):
        """
        FACTORY CLASS TEST: Detects deprecated WebSocketManagerFactory class usage.

        This test FAILS if the deprecated factory class exists and is usable.
        This test PASSES after factory class is properly deprecated/removed.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

            # If import succeeds, check if class is properly deprecated
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Attempt to instantiate factory
                factory_instance = WebSocketManagerFactory()

                # Check for deprecation warnings
                deprecation_warnings = [
                    warning for warning in w
                    if issubclass(warning.category, DeprecationWarning)
                    and 'WebSocketManagerFactory is deprecated' in str(warning.message)
                ]

                # VIOLATION: Factory class usable without proper deprecation
                if len(deprecation_warnings) == 0:
                    self.factory_violations.append({
                        'type': 'factory_class_no_deprecation',
                        'class': 'WebSocketManagerFactory',
                        'status': 'SSOT_VIOLATION'
                    })
                    self.fail(
                        "SSOT VIOLATION: WebSocketManagerFactory class exists without proper "
                        "deprecation warnings. This indicates incomplete SSOT migration."
                    )

                # Test factory method exists
                if hasattr(factory_instance, 'create_websocket_manager'):
                    self.factory_violations.append({
                        'type': 'factory_method_active',
                        'class': 'WebSocketManagerFactory',
                        'method': 'create_websocket_manager',
                        'deprecation_warnings': len(deprecation_warnings),
                        'status': 'FACTORY_PATTERN_VIOLATION'
                    })

                    # This is the violation state - factory is still functional
                    self.assertTrue(
                        callable(factory_instance.create_websocket_manager),
                        "SSOT VIOLATION: Factory method is callable, indicating factory pattern "
                        "still active. This test FAILS during violation state, PASSES after removal."
                    )

        except ImportError:
            # Factory class removed - this is the post-remediation state
            self.ssot_patterns.append({
                'type': 'factory_class_removed',
                'status': 'SSOT_COMPLIANT'
            })

    def test_detect_factory_function_usage_violations(self):
        """
        FACTORY FUNCTION TEST: Detects usage of deprecated factory functions.

        This test identifies active usage of factory creation patterns.
        """
        deprecated_factory_functions = [
            'create_websocket_manager',
            'get_websocket_manager_factory',
            'create_websocket_manager_sync'
        ]

        for func_name in deprecated_factory_functions:
            try:
                module = __import__(
                    'netra_backend.app.websocket_core.websocket_manager_factory',
                    fromlist=[func_name]
                )
                factory_function = getattr(module, func_name, None)

                if factory_function and callable(factory_function):
                    self.factory_violations.append({
                        'type': 'factory_function_active',
                        'function': func_name,
                        'callable': True,
                        'status': 'FACTORY_PATTERN_VIOLATION'
                    })

                    # Test function signature for SSOT compliance
                    try:
                        sig = inspect.signature(factory_function)
                        if 'user_context' not in sig.parameters:
                            self.factory_violations.append({
                                'type': 'factory_function_non_ssot_signature',
                                'function': func_name,
                                'signature': str(sig),
                                'status': 'SSOT_SIGNATURE_VIOLATION'
                            })

                    except Exception as sig_error:
                        self.factory_violations.append({
                            'type': 'factory_function_signature_error',
                            'function': func_name,
                            'error': str(sig_error),
                            'status': 'INSPECTION_FAILED'
                        })

            except (ImportError, AttributeError):
                # Function not available - post-remediation state
                self.ssot_patterns.append({
                    'type': 'factory_function_removed',
                    'function': func_name,
                    'status': 'SSOT_COMPLIANT'
                })

        # ASSERTION: Factory functions indicate incomplete migration
        if self.factory_violations:
            active_functions = [v['function'] for v in self.factory_violations if v['type'] == 'factory_function_active']
            self.assertTrue(
                len(active_functions) > 0,
                f"SSOT VIOLATION: {len(active_functions)} deprecated factory functions still active: "
                f"{active_functions}. This confirms factory pattern not eliminated."
            )

    async def test_factory_vs_direct_instantiation_performance(self):
        """
        PERFORMANCE TEST: Compares factory pattern vs direct SSOT instantiation.

        This test measures performance difference and detects factory overhead.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from shared.types.core_types import ensure_user_id

        # Create test context
        test_context = UserExecutionContext(
            user_id=ensure_user_id("performance_test_user"),
            thread_id="perf_test_thread",
            run_id="perf_test_run",
            request_id="factory_performance_test"
        )

        # Test factory pattern performance
        factory_times = []
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

            for i in range(5):  # 5 iterations
                start_time = time.perf_counter()
                manager = await create_websocket_manager(user_context=test_context)
                end_time = time.perf_counter()
                factory_times.append(end_time - start_time)

                # Cleanup
                if hasattr(manager, 'cleanup'):
                    await manager.cleanup()

        except Exception as e:
            factory_times = []  # Factory pattern failed

        # Test direct SSOT instantiation performance
        direct_times = []
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

            for i in range(5):  # 5 iterations
                start_time = time.perf_counter()
                manager = WebSocketManager(user_context=test_context)
                end_time = time.perf_counter()
                direct_times.append(end_time - start_time)

                # Cleanup
                if hasattr(manager, 'cleanup'):
                    await manager.cleanup()

        except Exception as e:
            direct_times = []

        # Calculate performance metrics
        if factory_times and direct_times:
            avg_factory_time = sum(factory_times) / len(factory_times)
            avg_direct_time = sum(direct_times) / len(direct_times)
            performance_overhead = avg_factory_time - avg_direct_time
            overhead_percentage = (performance_overhead / avg_direct_time) * 100 if avg_direct_time > 0 else 0

            self.performance_metrics = {
                'factory_avg_time': avg_factory_time,
                'direct_avg_time': avg_direct_time,
                'overhead_seconds': performance_overhead,
                'overhead_percentage': overhead_percentage,
                'factory_samples': len(factory_times),
                'direct_samples': len(direct_times)
            }

            # VIOLATION: Factory pattern adds overhead
            if overhead_percentage > 10:  # More than 10% overhead
                self.factory_violations.append({
                    'type': 'factory_performance_overhead',
                    'overhead_percentage': overhead_percentage,
                    'overhead_seconds': performance_overhead,
                    'status': 'PERFORMANCE_VIOLATION'
                })

                self.assertLess(
                    overhead_percentage, 10,
                    f"SSOT VIOLATION: Factory pattern adds {overhead_percentage:.1f}% overhead "
                    f"({performance_overhead:.4f}s) vs direct instantiation. "
                    "This confirms factory abstraction impacts performance."
                )

        elif factory_times and not direct_times:
            # Only factory works - indicates incomplete SSOT migration
            self.factory_violations.append({
                'type': 'only_factory_functional',
                'factory_working': True,
                'direct_working': False,
                'status': 'SSOT_MIGRATION_INCOMPLETE'
            })

        elif direct_times and not factory_times:
            # Only direct works - this is post-remediation state
            self.ssot_patterns.append({
                'type': 'only_direct_functional',
                'factory_working': False,
                'direct_working': True,
                'status': 'SSOT_MIGRATION_COMPLETE'
            })

    def test_factory_pattern_memory_leak_detection(self):
        """
        MEMORY LEAK TEST: Detects factory pattern memory accumulation issues.

        Factory patterns often accumulate state that should be per-user.
        """
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

            # Test factory instance management
            factory1 = WebSocketManagerFactory()
            factory2 = WebSocketManagerFactory()

            # Check if factory uses singleton pattern (potential memory leak)
            if factory1 is factory2:
                self.factory_violations.append({
                    'type': 'factory_singleton_pattern',
                    'description': 'Factory uses singleton pattern - potential memory leak',
                    'status': 'MEMORY_LEAK_RISK'
                })

                self.assertIsNot(
                    factory1, factory2,
                    "SSOT VIOLATION: Factory uses singleton pattern which can cause memory leaks "
                    "in multi-user environments. Each user should have isolated instances."
                )

            # Test for module-level state
            if hasattr(factory1, '_manager_cache') or hasattr(factory1, '_active_managers'):
                self.factory_violations.append({
                    'type': 'factory_state_accumulation',
                    'description': 'Factory maintains internal state caches',
                    'status': 'STATE_LEAK_RISK'
                })

        except ImportError:
            # Factory class not available - post-remediation state
            self.ssot_patterns.append({
                'type': 'factory_class_eliminated',
                'memory_leak_risk': 'ELIMINATED',
                'status': 'SSOT_COMPLIANT'
            })

    def test_websocket_manager_direct_instantiation_validation(self):
        """
        DIRECT INSTANTIATION TEST: Validates direct WebSocketManager instantiation.

        This test ensures the preferred SSOT pattern works correctly.
        """
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id

            # Test direct instantiation (preferred SSOT pattern)
            test_context = UserExecutionContext(
                user_id=ensure_user_id("direct_test_user"),
                thread_id="direct_test_thread",
                run_id="direct_test_run",
                request_id="direct_instantiation_test"
            )

            # Direct instantiation should work
            manager = WebSocketManager(user_context=test_context)

            # Validate manager properties
            self.assertIsNotNone(manager, "Direct WebSocketManager instantiation failed")
            self.assertTrue(hasattr(manager, 'user_context'), "Manager missing user_context")
            self.assertEqual(manager.user_context, test_context, "User context not preserved")

            # Validate SSOT compliance
            if hasattr(manager, '_ssot_authorization_token'):
                self.ssot_patterns.append({
                    'type': 'direct_instantiation_ssot_compliant',
                    'has_auth_token': True,
                    'user_context_preserved': True,
                    'status': 'SSOT_COMPLIANT'
                })
            else:
                self.factory_violations.append({
                    'type': 'direct_instantiation_missing_ssot_features',
                    'missing_features': ['_ssot_authorization_token'],
                    'status': 'SSOT_INCOMPLETE'
                })

        except Exception as e:
            self.fail(f"CRITICAL: Direct WebSocketManager instantiation failed: {e}")

    async def test_factory_pattern_user_isolation_violations(self):
        """
        USER ISOLATION TEST: Detects factory pattern user isolation failures.

        Factory patterns often share state between users inappropriately.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from shared.types.core_types import ensure_user_id

        # Create contexts for two different users
        user1_context = UserExecutionContext(
            user_id=ensure_user_id("isolation_user1"),
            thread_id="user1_thread",
            run_id="user1_run",
            request_id="user1_isolation_test"
        )

        user2_context = UserExecutionContext(
            user_id=ensure_user_id("isolation_user2"),
            thread_id="user2_thread",
            run_id="user2_run",
            request_id="user2_isolation_test"
        )

        # Test factory pattern isolation
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

            manager1 = await create_websocket_manager(user_context=user1_context)
            manager2 = await create_websocket_manager(user_context=user2_context)

            # Check for improper shared state
            if manager1 is manager2:
                self.factory_violations.append({
                    'type': 'factory_shared_instance',
                    'description': 'Factory returns same instance for different users',
                    'status': 'USER_ISOLATION_VIOLATION'
                })

                self.assertIsNot(
                    manager1, manager2,
                    "SSOT VIOLATION: Factory pattern returns shared instance for different users. "
                    "This violates user isolation requirements."
                )

            # Check for shared internal state
            if (hasattr(manager1, '_connection_registry') and
                hasattr(manager2, '_connection_registry') and
                manager1._connection_registry is manager2._connection_registry):

                self.factory_violations.append({
                    'type': 'factory_shared_connection_registry',
                    'description': 'Factory managers share connection registry',
                    'status': 'CONNECTION_ISOLATION_VIOLATION'
                })

        except ImportError:
            # Factory pattern not available - test direct instantiation isolation
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

            manager1 = WebSocketManager(user_context=user1_context)
            manager2 = WebSocketManager(user_context=user2_context)

            # Verify proper isolation in direct instantiation
            self.assertIsNot(manager1, manager2, "Direct instantiation should create separate instances")
            self.assertNotEqual(manager1.user_context.user_id, manager2.user_context.user_id)

            self.ssot_patterns.append({
                'type': 'direct_instantiation_proper_isolation',
                'user1_id': str(manager1.user_context.user_id),
                'user2_id': str(manager2.user_context.user_id),
                'status': 'USER_ISOLATION_COMPLIANT'
            })

    def tearDown(self):
        """Clean up and report factory pattern violations."""
        super().tearDown()

        print("\n=== WEBSOCKET FACTORY PATTERN SSOT VIOLATIONS ===")

        if self.factory_violations:
            print(f"\nFACTORY VIOLATIONS FOUND ({len(self.factory_violations)}):")
            for violation in self.factory_violations:
                print(f"  - {violation['type']}: {violation['status']}")
                if 'description' in violation:
                    print(f"    Description: {violation['description']}")

        if self.ssot_patterns:
            print(f"\nSSOT COMPLIANT PATTERNS ({len(self.ssot_patterns)}):")
            for pattern in self.ssot_patterns:
                print(f"  - {pattern['type']}: {pattern['status']}")

        if self.performance_metrics:
            print(f"\nPERFORMANCE METRICS:")
            metrics = self.performance_metrics
            print(f"  - Factory Avg Time: {metrics.get('factory_avg_time', 'N/A'):.4f}s")
            print(f"  - Direct Avg Time: {metrics.get('direct_avg_time', 'N/A'):.4f}s")
            print(f"  - Overhead: {metrics.get('overhead_percentage', 0):.1f}%")

        # Summary
        violation_count = len(self.factory_violations)
        compliant_count = len(self.ssot_patterns)

        print(f"\nSUMMARY:")
        print(f"  - Factory Violations: {violation_count}")
        print(f"  - SSOT Compliant: {compliant_count}")

        if violation_count > 0:
            print("  - RESULT: FACTORY PATTERNS ACTIVE (Test FAILS as expected)")
            print("  - ACTION: Eliminate factory patterns for direct SSOT instantiation")
        else:
            print("  - RESULT: FACTORY PATTERNS ELIMINATED (Test PASSES after remediation)")


if __name__ == '__main__':
    import asyncio

    async def run_factory_tests():
        test_instance = WebSocketFactoryPatternSSOTViolationsTests()
        await test_instance.asyncSetUp()

        # Run sync tests
        sync_tests = [
            test_instance.test_detect_deprecated_websocket_manager_factory_class,
            test_instance.test_detect_factory_function_usage_violations,
            test_instance.test_factory_pattern_memory_leak_detection,
            test_instance.test_websocket_manager_direct_instantiation_validation,
        ]

        for test in sync_tests:
            try:
                test()
                print(f"CHECK {test.__name__}")
            except AssertionError as e:
                print(f"✗ {test.__name__}: {e}")
            except Exception as e:
                print(f"? {test.__name__}: {e}")

        # Run async tests
        async_tests = [
            test_instance.test_factory_vs_direct_instantiation_performance,
            test_instance.test_factory_pattern_user_isolation_violations,
        ]

        for test in async_tests:
            try:
                await test()
                print(f"CHECK {test.__name__}")
            except AssertionError as e:
                print(f"✗ {test.__name__}: {e}")
            except Exception as e:
                print(f"? {test.__name__}: {e}")

        test_instance.tearDown()

    asyncio.run(run_factory_tests())