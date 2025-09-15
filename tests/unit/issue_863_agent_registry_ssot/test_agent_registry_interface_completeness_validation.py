"""
Test AgentRegistry Interface Completeness Validation (Issue #863)

This test module validates the completeness of AgentRegistry interface
implementations to identify and reproduce the 25% interface gap issue.

Business Value: Protects $500K+ ARR by ensuring complete interface
implementation across all AgentRegistry versions, preventing AttributeError
exceptions and ensuring Golden Path user flow functionality.

Test Category: Unit (no Docker required)
Purpose: Failing tests to demonstrate interface completeness gaps
"""

import asyncio
import inspect
import importlib
from typing import Dict, Any, Optional, List, Set, Callable
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentRegistryInterfaceCompletenessValidation(SSotAsyncTestCase):
    """
    Test interface completeness between AgentRegistry implementations.

    These tests are DESIGNED TO FAIL initially to demonstrate the 25%
    interface gap that prevents proper SSOT compliance and blocks Golden Path.
    """

    def setup_method(self, method):
        """Setup test environment for interface validation."""
        # Registry implementations to validate
        self.registry_implementations = {
            'basic': "netra_backend.app.agents.registry",
            'supervisor': "netra_backend.app.agents.supervisor.agent_registry",
            'universal': "netra_backend.app.core.registry.universal_registry"
        }

        # Expected interface methods for complete SSOT compliance
        self.expected_interface_methods = {
            # Core registration methods
            'register_agent',
            'unregister_agent',
            'get_agent_info',
            'get_agent_instance',
            'update_agent_status',
            'increment_execution_count',
            'increment_error_count',

            # Agent discovery methods
            'get_agents_by_type',
            'get_agents_by_status',
            'get_all_agents',
            'get_available_agents',
            'list_available_agents',
            'find_agent_by_name',

            # WebSocket integration methods
            'set_websocket_manager',
            'set_websocket_bridge',
            'get_websocket_manager',

            # User isolation methods
            'create_user_session',
            'cleanup_user_session',
            'get_user_session',
            'create_agent_for_user',
            'get_user_agent',
            'remove_user_agent',

            # Registry management methods
            'cleanup_inactive_agents',
            'get_registry_stats',
            'get_registry_health',
            'reset_all_agents',
            'diagnose_websocket_wiring',

            # Factory pattern methods
            'create_tool_dispatcher_for_user',
            'register_default_agents',
            'register_agent_safely',

            # Legacy compatibility methods
            'register',
            'get',
            'has',
            'list_keys',
            'remove',

            # Async variants
            'get_async',
            'register_agent_async',
            'cleanup_async'
        }

        # Critical methods that MUST exist for Golden Path
        self.golden_path_critical_methods = {
            'list_available_agents',
            'get_agent',
            'set_websocket_manager',
            'create_agent_for_user',
            'get_user_session'
        }

    def test_interface_completeness_gap_validation(self):
        """
        TEST DESIGNED TO FAIL: Validate interface completeness across registries.

        This test identifies the 25% interface gap by comparing expected vs actual
        method implementations across all AgentRegistry variants.
        """
        implementation_gaps = {}
        total_expected_methods = len(self.expected_interface_methods)

        try:
            for impl_name, module_path in self.registry_implementations.items():
                try:
                    module = importlib.import_module(module_path)
                    registry_class = getattr(module, 'AgentRegistry', None)

                    if registry_class is None:
                        implementation_gaps[impl_name] = {
                            'error': 'AgentRegistry class not found',
                            'missing_methods': list(self.expected_interface_methods),
                            'completeness_percentage': 0.0
                        }
                        continue

                    # Get all methods in the implementation
                    actual_methods = set()
                    for attr_name in dir(registry_class):
                        attr = getattr(registry_class, attr_name)
                        if callable(attr) and not attr_name.startswith('_'):
                            actual_methods.add(attr_name)

                    # Identify missing methods
                    missing_methods = self.expected_interface_methods - actual_methods
                    implemented_methods = self.expected_interface_methods - missing_methods

                    # Calculate completeness percentage
                    completeness_percentage = (len(implemented_methods) / total_expected_methods) * 100

                    # Identify critical missing methods
                    critical_missing = self.golden_path_critical_methods & missing_methods

                    implementation_gaps[impl_name] = {
                        'missing_methods': list(missing_methods),
                        'implemented_methods': list(implemented_methods),
                        'completeness_percentage': completeness_percentage,
                        'critical_missing': list(critical_missing),
                        'total_methods_count': len(actual_methods),
                        'expected_methods_count': total_expected_methods
                    }

                    logger.info(f"{impl_name} registry completeness: {completeness_percentage:.1f}% "
                              f"({len(implemented_methods)}/{total_expected_methods} methods)")

                except Exception as e:
                    implementation_gaps[impl_name] = {
                        'error': f"Failed to analyze implementation: {e}",
                        'missing_methods': list(self.expected_interface_methods),
                        'completeness_percentage': 0.0
                    }

            # Analyze overall interface gaps
            gap_analysis = self._analyze_interface_gaps(implementation_gaps)

            # FAILURE CONDITION: Interface gaps > 10% indicate SSOT violation
            critical_failures = []
            for impl_name, gap_info in implementation_gaps.items():
                if gap_info.get('completeness_percentage', 0) < 75.0:  # Less than 75% = critical
                    critical_failures.append(
                        f"{impl_name}: {gap_info.get('completeness_percentage', 0):.1f}% complete "
                        f"(missing {len(gap_info.get('missing_methods', []))} methods)"
                    )

                # Check for critical Golden Path method gaps
                critical_missing = gap_info.get('critical_missing', [])
                if critical_missing:
                    critical_failures.append(
                        f"{impl_name}: Missing critical Golden Path methods: {critical_missing}"
                    )

            if critical_failures:
                failure_summary = "; ".join(critical_failures)
                self.fail(
                    f"CRITICAL INTERFACE COMPLETENESS FAILURE: Multiple registry implementations "
                    f"have significant interface gaps (target: >90% completeness). "
                    f"This reproduces the 25% interface gap issue blocking SSOT compliance and "
                    f"Golden Path functionality. Gaps prevent consistent agent operations and "
                    f"WebSocket integration. Critical failures: {failure_summary}. "
                    f"Overall analysis: {gap_analysis}"
                )

        except Exception as e:
            self.fail(f"Unexpected error during interface completeness validation: {e}")

        # If all implementations have >90% completeness, that's the goal state
        logger.info("Interface completeness is satisfactory across all registry implementations")

    def test_method_signature_consistency_gaps(self):
        """
        TEST DESIGNED TO FAIL: Validate method signature consistency.

        This test identifies signature mismatches for methods that exist in
        multiple implementations but have incompatible signatures.
        """
        try:
            signature_inconsistencies = {}

            # Load all registry implementations
            implementations = {}
            for impl_name, module_path in self.registry_implementations.items():
                try:
                    module = importlib.import_module(module_path)
                    registry_class = getattr(module, 'AgentRegistry', None)
                    if registry_class:
                        implementations[impl_name] = registry_class
                except Exception as e:
                    logger.warning(f"Could not load {impl_name} implementation: {e}")

            if len(implementations) < 2:
                self.fail("Need at least 2 implementations to compare signatures")

            # Find common methods across implementations
            common_methods = None
            for impl_name, registry_class in implementations.items():
                methods = set(name for name in dir(registry_class)
                             if callable(getattr(registry_class, name)) and not name.startswith('_'))
                if common_methods is None:
                    common_methods = methods
                else:
                    common_methods &= methods

            logger.info(f"Found {len(common_methods)} common methods to analyze")

            # Analyze signature consistency for common methods
            for method_name in common_methods:
                signatures = {}
                async_patterns = {}

                for impl_name, registry_class in implementations.items():
                    try:
                        method = getattr(registry_class, method_name)
                        signatures[impl_name] = inspect.signature(method)
                        async_patterns[impl_name] = asyncio.iscoroutinefunction(method)
                    except Exception as e:
                        logger.warning(f"Could not get signature for {impl_name}.{method_name}: {e}")
                        continue

                # Check for signature inconsistencies
                if len(set(str(sig) for sig in signatures.values())) > 1:
                    signature_inconsistencies[method_name] = {
                        'signatures': {impl: str(sig) for impl, sig in signatures.items()},
                        'async_patterns': async_patterns
                    }

                # Check for async/sync inconsistencies
                if len(set(async_patterns.values())) > 1:
                    if method_name not in signature_inconsistencies:
                        signature_inconsistencies[method_name] = {
                            'signatures': {impl: str(sig) for impl, sig in signatures.items()},
                            'async_patterns': async_patterns
                        }
                    else:
                        signature_inconsistencies[method_name]['async_patterns'] = async_patterns

            # FAILURE CONDITION: Signature inconsistencies prevent SSOT compliance
            if signature_inconsistencies:
                inconsistency_details = []
                for method_name, details in signature_inconsistencies.items():
                    sig_info = []
                    for impl, signature in details['signatures'].items():
                        async_info = 'async' if details['async_patterns'].get(impl, False) else 'sync'
                        sig_info.append(f"{impl}: {signature} ({async_info})")

                    inconsistency_details.append(f"{method_name}: {'; '.join(sig_info)}")

                self.fail(
                    f"CRITICAL SIGNATURE CONSISTENCY FAILURE: {len(signature_inconsistencies)} "
                    f"methods have inconsistent signatures across implementations. "
                    f"This prevents SSOT compliance and causes runtime errors when code "
                    f"written for one implementation is used with another. "
                    f"Signature inconsistencies: {'; '.join(inconsistency_details)}"
                )

        except Exception as e:
            self.fail(f"Unexpected error during signature consistency validation: {e}")

        # If signatures are consistent, that's the goal state
        logger.info("Method signatures are consistent across implementations")

    def test_golden_path_critical_methods_availability(self):
        """
        TEST DESIGNED TO FAIL: Validate critical Golden Path methods exist.

        This test specifically validates that all methods required for the
        Golden Path user flow are available and functional.
        """
        try:
            critical_method_failures = {}

            for impl_name, module_path in self.registry_implementations.items():
                try:
                    module = importlib.import_module(module_path)
                    registry_class = getattr(module, 'AgentRegistry', None)

                    if registry_class is None:
                        critical_method_failures[impl_name] = {
                            'error': 'AgentRegistry class not found',
                            'missing_critical_methods': list(self.golden_path_critical_methods)
                        }
                        continue

                    # Test instantiation
                    try:
                        instance = registry_class()
                        missing_critical = []
                        method_test_results = {}

                        # Test each critical method
                        for method_name in self.golden_path_critical_methods:
                            if not hasattr(instance, method_name):
                                missing_critical.append(method_name)
                                method_test_results[method_name] = {'exists': False, 'callable': False}
                            else:
                                method = getattr(instance, method_name)
                                is_callable = callable(method)
                                method_test_results[method_name] = {
                                    'exists': True,
                                    'callable': is_callable,
                                    'is_async': asyncio.iscoroutinefunction(method) if is_callable else None
                                }

                                # Try to call method with safe parameters to test functionality
                                if is_callable and method_name == 'list_available_agents':
                                    try:
                                        if asyncio.iscoroutinefunction(method):
                                            # For async methods, just check they don't immediately fail
                                            result = method()
                                            if asyncio.iscoroutine(result):
                                                result.close()  # Clean up coroutine
                                                method_test_results[method_name]['test_call'] = 'async_callable'
                                        else:
                                            # For sync methods, try to call
                                            result = method()
                                            method_test_results[method_name]['test_call'] = 'success'
                                            method_test_results[method_name]['result_type'] = type(result).__name__
                                    except Exception as e:
                                        method_test_results[method_name]['test_call'] = f'error: {e}'

                        if missing_critical:
                            critical_method_failures[impl_name] = {
                                'missing_critical_methods': missing_critical,
                                'method_test_results': method_test_results
                            }
                        else:
                            # All critical methods exist - store results for verification
                            critical_method_failures[impl_name] = {
                                'missing_critical_methods': [],
                                'method_test_results': method_test_results
                            }

                    except Exception as e:
                        critical_method_failures[impl_name] = {
                            'error': f"Failed to instantiate registry: {e}",
                            'missing_critical_methods': list(self.golden_path_critical_methods)
                        }

                except Exception as e:
                    critical_method_failures[impl_name] = {
                        'error': f"Failed to load implementation: {e}",
                        'missing_critical_methods': list(self.golden_path_critical_methods)
                    }

            # FAILURE CONDITION: Missing critical methods block Golden Path
            golden_path_blocking_failures = []
            for impl_name, failure_info in critical_method_failures.items():
                missing_methods = failure_info.get('missing_critical_methods', [])
                if missing_methods:
                    golden_path_blocking_failures.append(
                        f"{impl_name}: Missing critical methods {missing_methods}"
                    )

                # Check for method test failures
                test_results = failure_info.get('method_test_results', {})
                failed_tests = [name for name, result in test_results.items()
                              if result.get('test_call', '').startswith('error:')]
                if failed_tests:
                    golden_path_blocking_failures.append(
                        f"{impl_name}: Method test failures {failed_tests}"
                    )

            if golden_path_blocking_failures:
                failure_summary = "; ".join(golden_path_blocking_failures)
                self.fail(
                    f"CRITICAL GOLDEN PATH METHOD FAILURE: Critical methods required for "
                    f"Golden Path user flow are missing or non-functional. "
                    f"This directly blocks the $500K+ ARR chat functionality and prevents "
                    f"users from getting AI responses. Golden Path blocking failures: {failure_summary}"
                )

        except Exception as e:
            self.fail(f"Unexpected error during Golden Path critical method validation: {e}")

        # If all critical methods are available, that's the goal state
        logger.info("All Golden Path critical methods are available and functional")

    def test_websocket_integration_interface_gaps(self):
        """
        TEST DESIGNED TO FAIL: Validate WebSocket integration interface completeness.

        This test identifies gaps in WebSocket-related methods that prevent
        real-time agent events in the Golden Path.
        """
        websocket_interface_methods = {
            'set_websocket_manager',
            'set_websocket_bridge',
            'get_websocket_manager',
            'diagnose_websocket_wiring',
            '_notify_agent_event',
            'get_factory_integration_status'
        }

        try:
            websocket_integration_gaps = {}

            for impl_name, module_path in self.registry_implementations.items():
                try:
                    module = importlib.import_module(module_path)
                    registry_class = getattr(module, 'AgentRegistry', None)

                    if registry_class is None:
                        websocket_integration_gaps[impl_name] = {
                            'error': 'AgentRegistry class not found',
                            'missing_websocket_methods': list(websocket_interface_methods)
                        }
                        continue

                    # Check WebSocket method availability
                    missing_websocket_methods = []
                    available_websocket_methods = []

                    for method_name in websocket_interface_methods:
                        if hasattr(registry_class, method_name):
                            available_websocket_methods.append(method_name)
                        else:
                            missing_websocket_methods.append(method_name)

                    websocket_completeness = (len(available_websocket_methods) / len(websocket_interface_methods)) * 100

                    # Test WebSocket integration functionality
                    integration_test_results = {}
                    if len(available_websocket_methods) > 0:
                        try:
                            instance = registry_class()
                            mock_websocket_manager = Mock()

                            # Test set_websocket_manager
                            if hasattr(instance, 'set_websocket_manager'):
                                try:
                                    method = getattr(instance, 'set_websocket_manager')
                                    if asyncio.iscoroutinefunction(method):
                                        # Test async version
                                        try:
                                            coro = method(mock_websocket_manager)
                                            coro.close()  # Clean up coroutine
                                            integration_test_results['set_websocket_manager'] = 'async_compatible'
                                        except Exception as e:
                                            integration_test_results['set_websocket_manager'] = f'async_error: {e}'
                                    else:
                                        # Test sync version
                                        method(mock_websocket_manager)
                                        integration_test_results['set_websocket_manager'] = 'sync_success'
                                except Exception as e:
                                    integration_test_results['set_websocket_manager'] = f'call_error: {e}'

                            # Test diagnose_websocket_wiring if available
                            if hasattr(instance, 'diagnose_websocket_wiring'):
                                try:
                                    result = instance.diagnose_websocket_wiring()
                                    integration_test_results['diagnose_websocket_wiring'] = f'success: {type(result).__name__}'
                                except Exception as e:
                                    integration_test_results['diagnose_websocket_wiring'] = f'error: {e}'

                        except Exception as e:
                            integration_test_results['instantiation'] = f'error: {e}'

                    websocket_integration_gaps[impl_name] = {
                        'missing_websocket_methods': missing_websocket_methods,
                        'available_websocket_methods': available_websocket_methods,
                        'websocket_completeness_percentage': websocket_completeness,
                        'integration_test_results': integration_test_results
                    }

                except Exception as e:
                    websocket_integration_gaps[impl_name] = {
                        'error': f"Failed to analyze WebSocket integration: {e}",
                        'missing_websocket_methods': list(websocket_interface_methods),
                        'websocket_completeness_percentage': 0.0
                    }

            # FAILURE CONDITION: WebSocket integration gaps prevent real-time events
            websocket_blocking_failures = []
            for impl_name, gap_info in websocket_integration_gaps.items():
                completeness = gap_info.get('websocket_completeness_percentage', 0)
                if completeness < 70.0:  # Less than 70% WebSocket interface completeness
                    missing_methods = gap_info.get('missing_websocket_methods', [])
                    websocket_blocking_failures.append(
                        f"{impl_name}: {completeness:.1f}% WebSocket completeness (missing: {missing_methods})"
                    )

                # Check for critical WebSocket method failures
                test_results = gap_info.get('integration_test_results', {})
                failed_integrations = [method for method, result in test_results.items()
                                     if 'error' in str(result)]
                if failed_integrations:
                    websocket_blocking_failures.append(
                        f"{impl_name}: WebSocket integration failures: {failed_integrations}"
                    )

            if websocket_blocking_failures:
                failure_summary = "; ".join(websocket_blocking_failures)
                self.fail(
                    f"CRITICAL WEBSOCKET INTEGRATION FAILURE: WebSocket interface gaps prevent "
                    f"real-time agent events that deliver the Golden Path chat experience. "
                    f"This blocks the real-time progress updates and completion notifications "
                    f"that users expect for $500K+ ARR functionality. "
                    f"WebSocket integration failures: {failure_summary}"
                )

        except Exception as e:
            self.fail(f"Unexpected error during WebSocket integration validation: {e}")

        # If WebSocket integration is complete, that's the goal state
        logger.info("WebSocket integration interfaces are complete across implementations")

    def test_user_isolation_interface_gaps(self):
        """
        TEST DESIGNED TO FAIL: Validate user isolation interface completeness.

        This test identifies gaps in user isolation methods that prevent
        secure multi-user agent execution.
        """
        user_isolation_methods = {
            'create_user_session',
            'cleanup_user_session',
            'get_user_session',
            'create_agent_for_user',
            'get_user_agent',
            'remove_user_agent',
            'reset_user_agents',
            'monitor_all_users',
            'emergency_cleanup_all'
        }

        try:
            user_isolation_gaps = {}

            for impl_name, module_path in self.registry_implementations.items():
                try:
                    module = importlib.import_module(module_path)
                    registry_class = getattr(module, 'AgentRegistry', None)

                    if registry_class is None:
                        user_isolation_gaps[impl_name] = {
                            'error': 'AgentRegistry class not found',
                            'missing_isolation_methods': list(user_isolation_methods)
                        }
                        continue

                    # Check user isolation method availability
                    missing_isolation_methods = []
                    available_isolation_methods = []

                    for method_name in user_isolation_methods:
                        if hasattr(registry_class, method_name):
                            available_isolation_methods.append(method_name)
                        else:
                            missing_isolation_methods.append(method_name)

                    isolation_completeness = (len(available_isolation_methods) / len(user_isolation_methods)) * 100

                    user_isolation_gaps[impl_name] = {
                        'missing_isolation_methods': missing_isolation_methods,
                        'available_isolation_methods': available_isolation_methods,
                        'isolation_completeness_percentage': isolation_completeness
                    }

                except Exception as e:
                    user_isolation_gaps[impl_name] = {
                        'error': f"Failed to analyze user isolation: {e}",
                        'missing_isolation_methods': list(user_isolation_methods),
                        'isolation_completeness_percentage': 0.0
                    }

            # FAILURE CONDITION: User isolation gaps create security vulnerabilities
            isolation_blocking_failures = []
            for impl_name, gap_info in user_isolation_gaps.items():
                completeness = gap_info.get('isolation_completeness_percentage', 0)
                if completeness < 80.0:  # Less than 80% user isolation completeness
                    missing_methods = gap_info.get('missing_isolation_methods', [])
                    isolation_blocking_failures.append(
                        f"{impl_name}: {completeness:.1f}% isolation completeness (missing: {missing_methods})"
                    )

            if isolation_blocking_failures:
                failure_summary = "; ".join(isolation_blocking_failures)
                self.fail(
                    f"CRITICAL USER ISOLATION FAILURE: User isolation interface gaps create "
                    f"security vulnerabilities and prevent proper multi-user agent execution. "
                    f"This can cause user data contamination and privacy violations, "
                    f"blocking enterprise deployment of the $500K+ ARR platform. "
                    f"User isolation failures: {failure_summary}"
                )

        except Exception as e:
            self.fail(f"Unexpected error during user isolation validation: {e}")

        # If user isolation is complete, that's the goal state
        logger.info("User isolation interfaces are complete across implementations")

    def _analyze_interface_gaps(self, implementation_gaps: Dict[str, Any]) -> str:
        """Analyze interface gaps and provide summary."""
        total_implementations = len(implementation_gaps)
        implementations_with_gaps = sum(1 for gap_info in implementation_gaps.values()
                                       if gap_info.get('completeness_percentage', 100) < 90)

        avg_completeness = sum(gap_info.get('completeness_percentage', 0)
                              for gap_info in implementation_gaps.values()) / max(total_implementations, 1)

        most_incomplete = min(implementation_gaps.items(),
                             key=lambda x: x[1].get('completeness_percentage', 0))

        return (f"Average completeness: {avg_completeness:.1f}%, "
               f"Implementations with gaps: {implementations_with_gaps}/{total_implementations}, "
               f"Least complete: {most_incomplete[0]} at {most_incomplete[1].get('completeness_percentage', 0):.1f}%")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "-s", "--tb=short"])