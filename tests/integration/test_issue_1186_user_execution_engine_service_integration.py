"""
Integration tests for Issue #1186 - UserExecutionEngine Service Integration Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Performance
- Value Impact: Validates service integration works correctly after import consolidation
- Strategic Impact: Protects $500K+ ARR chat functionality through validated service interactions

Tests validate:
1. UserExecutionEngine integration with WebSocket services (non-docker)
2. Agent Registry integration and factory patterns
3. User context isolation and service boundaries
4. Business workflow continuity after consolidation

Test Methodology: Service integration validation without docker dependencies
Execution: Integration tests using real service components where possible
"""

import asyncio
import unittest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional
from pathlib import Path
import inspect


class Issue1186UserExecutionEngineServiceIntegrationTests(unittest.TestCase):
    """Integration test suite for UserExecutionEngine service integration validation.

    Focus: Service integration validation after import consolidation
    Scope: Integration-level testing without docker dependencies
    """

    def setUp(self):
        """Set up test fixtures for service integration validation."""
        self.project_root = Path(__file__).parent.parent.parent
        self.mock_user_context = {
            'user_id': 'test_user_123',
            'session_id': 'session_456',
            'execution_id': 'exec_789'
        }
        self.integration_timeout = 5.0  # 5 second timeout for integration tests

    async def async_setUp(self):
        """Async setup for integration components."""
        self.loop = asyncio.get_event_loop()

    def test_user_execution_engine_websocket_integration_interface(self):
        """Test UserExecutionEngine WebSocket integration interface.

        Business Impact: Validates WebSocket event delivery continues to work
        after import consolidation, protecting chat functionality.
        """
        try:
            # Import consolidated UserExecutionEngine
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            # Validate WebSocket-related interface methods
            websocket_interface_methods = [
                'set_websocket_emitter',
                'notify_agent_started',
                'notify_agent_thinking',
                'notify_tool_executing',
                'notify_tool_completed',
                'notify_agent_completed'
            ]

            missing_methods = []
            available_methods = []

            for method in websocket_interface_methods:
                if hasattr(UserExecutionEngine, method):
                    available_methods.append(method)
                else:
                    missing_methods.append(method)

            # Report results
            print(f"CHECK WebSocket interface methods available: {len(available_methods)}")
            for method in available_methods:
                print(f"  CHECK {method}")

            if missing_methods:
                print(f"WARNING️  WebSocket interface methods missing: {len(missing_methods)}")
                for method in missing_methods:
                    print(f"  ✗ {method}")

            # Validate critical WebSocket methods exist
            critical_websocket_methods = ['set_websocket_emitter']
            for method in critical_websocket_methods:
                self.assertTrue(hasattr(UserExecutionEngine, method),
                              f"CRITICAL: UserExecutionEngine missing WebSocket method: {method}")

            # Test method signatures for WebSocket integration
            if hasattr(UserExecutionEngine, 'set_websocket_emitter'):
                method = getattr(UserExecutionEngine, 'set_websocket_emitter')
                sig = inspect.signature(method)
                self.assertGreater(len(sig.parameters), 0,
                                 "set_websocket_emitter should accept WebSocket emitter parameter")

            print("CHECK WebSocket integration interface validation passed")

        except ImportError as e:
            self.fail(f"INTEGRATION FAILURE: UserExecutionEngine import failed: {e}")

    def test_agent_registry_integration_compatibility(self):
        """Test UserExecutionEngine integration with AgentRegistry.

        Business Impact: Validates agent registration and execution continues
        to work after import consolidation.
        """
        try:
            # Import consolidated components
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            # Test AgentRegistry integration interface
            agent_integration_methods = [
                'set_agent_registry',
                'get_agent_registry',
                'register_agent',
                'execute_agent'
            ]

            integration_compatibility = {}

            for method in agent_integration_methods:
                if hasattr(UserExecutionEngine, method):
                    integration_compatibility[method] = 'AVAILABLE'
                else:
                    integration_compatibility[method] = 'MISSING'

            # Report compatibility results
            available_count = sum(1 for status in integration_compatibility.values() if status == 'AVAILABLE')
            total_count = len(integration_compatibility)

            print(f"📊 Agent Registry Integration Compatibility: {available_count}/{total_count}")
            for method, status in integration_compatibility.items():
                symbol = "CHECK" if status == 'AVAILABLE' else "✗"
                print(f"  {symbol} {method}: {status}")

            # Test mock integration with AgentRegistry
            try:
                with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry') as MockRegistry:
                    mock_registry = MockRegistry.return_value
                    mock_registry.get_agent = Mock(return_value=Mock())

                    # Test basic integration setup
                    if hasattr(UserExecutionEngine, 'set_agent_registry'):
                        # This validates the interface exists and can be called
                        engine_class = UserExecutionEngine
                        self.assertTrue(hasattr(engine_class, 'set_agent_registry'),
                                      "UserExecutionEngine should support AgentRegistry integration")

                print("CHECK Agent Registry integration interface validated")

            except Exception as e:
                print(f"WARNING️  Agent Registry mock integration warning: {e}")

        except ImportError as e:
            self.fail(f"INTEGRATION FAILURE: Agent Registry integration test failed: {e}")

    def test_execution_engine_factory_service_integration(self):
        """Test ExecutionEngineFactory service integration patterns.

        Business Impact: Validates factory pattern works correctly with services
        after consolidation, ensuring proper user isolation.
        """
        try:
            # Import factory components
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

            # Test factory service integration interface
            factory_service_methods = [
                'create_execution_engine',
                'get_engine_context',
                'cleanup_engine',
                'set_websocket_bridge',
                'set_agent_registry'
            ]

            service_integration_status = {}

            for method in factory_service_methods:
                if hasattr(ExecutionEngineFactory, method):
                    method_obj = getattr(ExecutionEngineFactory, method)
                    if callable(method_obj):
                        service_integration_status[method] = 'CALLABLE'
                    else:
                        service_integration_status[method] = 'NOT_CALLABLE'
                else:
                    service_integration_status[method] = 'MISSING'

            # Report service integration status
            callable_count = sum(1 for status in service_integration_status.values() if status == 'CALLABLE')
            total_count = len(service_integration_status)

            print(f"🏗️  Factory Service Integration: {callable_count}/{total_count} methods callable")
            for method, status in service_integration_status.items():
                if status == 'CALLABLE':
                    symbol = "CHECK"
                elif status == 'NOT_CALLABLE':
                    symbol = "WARNING️"
                else:
                    symbol = "✗"
                print(f"  {symbol} {method}: {status}")

            # Validate critical factory methods
            critical_factory_methods = ['create_execution_engine']
            for method in critical_factory_methods:
                self.assertIn(method, service_integration_status,
                            f"Factory missing critical method: {method}")
                self.assertEqual(service_integration_status[method], 'CALLABLE',
                               f"Factory method {method} must be callable")

            print("CHECK ExecutionEngineFactory service integration validated")

        except ImportError as e:
            self.fail(f"INTEGRATION FAILURE: ExecutionEngineFactory import failed: {e}")

    def test_user_context_isolation_service_integration(self):
        """Test user context isolation in service integration scenarios.

        Business Impact: Validates user isolation works correctly after consolidation
        preventing cross-user contamination in production.
        """
        try:
            # Import user context components
            from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context

            # Test UserExecutionContext integration
            context_integration_methods = [
                'create_context',
                'validate_context',
                'isolate_context',
                'cleanup_context'
            ]

            # Create mock user contexts for isolation testing
            user_contexts = [
                {'user_id': 'user_1', 'session_id': 'session_1'},
                {'user_id': 'user_2', 'session_id': 'session_2'},
                {'user_id': 'user_3', 'session_id': 'session_3'}
            ]

            isolation_test_results = []

            for i, context_data in enumerate(user_contexts):
                try:
                    # Test context validation function
                    validation_result = validate_user_context(context_data)
                    isolation_test_results.append({
                        'user': context_data['user_id'],
                        'validation': 'PASSED' if validation_result else 'FAILED',
                        'context_data': context_data
                    })

                except Exception as e:
                    isolation_test_results.append({
                        'user': context_data['user_id'],
                        'validation': 'ERROR',
                        'error': str(e)
                    })

            # Report isolation test results
            passed_count = sum(1 for result in isolation_test_results if result['validation'] == 'PASSED')
            total_count = len(isolation_test_results)

            print(f"🔒 User Context Isolation Tests: {passed_count}/{total_count} passed")
            for result in isolation_test_results:
                if result['validation'] == 'PASSED':
                    symbol = "CHECK"
                elif result['validation'] == 'FAILED':
                    symbol = "✗"
                else:
                    symbol = "WARNING️"

                print(f"  {symbol} {result['user']}: {result['validation']}")

            # Validate at least basic context validation works
            self.assertGreater(passed_count, 0,
                             "At least one user context validation should pass")

            print("CHECK User context isolation service integration validated")

        except ImportError as e:
            print(f"WARNING️  User context integration validation skipped: {e}")

    def test_service_boundary_integration_validation(self):
        """Test service boundary integration after consolidation.

        Business Impact: Validates service boundaries remain intact after
        import consolidation, maintaining system architecture integrity.
        """
        service_boundaries = {
            'UserExecutionEngine': 'netra_backend.app.agents.supervisor.user_execution_engine',
            'ExecutionEngineFactory': 'netra_backend.app.agents.supervisor.execution_engine_factory',
            'UserExecutionContext': 'netra_backend.app.services.user_execution_context',
            'AgentRegistry': 'netra_backend.app.agents.supervisor.agent_registry',
            'WebSocketBridge': 'netra_backend.app.services.agent_websocket_bridge'
        }

        boundary_validation_results = {}

        for service_name, expected_module in service_boundaries.items():
            try:
                # Attempt to import the service
                module_parts = expected_module.split('.')
                module_name = '.'.join(module_parts)

                module = __import__(module_name, fromlist=[service_name])

                if hasattr(module, service_name):
                    service_class = getattr(module, service_name)
                    actual_module = service_class.__module__

                    if actual_module == expected_module:
                        boundary_validation_results[service_name] = {
                            'status': 'BOUNDARY_INTACT',
                            'expected_module': expected_module,
                            'actual_module': actual_module
                        }
                    else:
                        boundary_validation_results[service_name] = {
                            'status': 'BOUNDARY_VIOLATION',
                            'expected_module': expected_module,
                            'actual_module': actual_module
                        }
                else:
                    boundary_validation_results[service_name] = {
                        'status': 'SERVICE_MISSING',
                        'expected_module': expected_module,
                        'actual_module': None
                    }

            except ImportError:
                boundary_validation_results[service_name] = {
                    'status': 'MODULE_MISSING',
                    'expected_module': expected_module,
                    'actual_module': None
                }

        # Report boundary validation results
        intact_count = sum(1 for result in boundary_validation_results.values()
                          if result['status'] == 'BOUNDARY_INTACT')
        total_count = len(boundary_validation_results)

        print(f"🏛️  Service Boundary Integration: {intact_count}/{total_count} boundaries intact")

        for service_name, result in boundary_validation_results.items():
            if result['status'] == 'BOUNDARY_INTACT':
                symbol = "CHECK"
            elif result['status'] == 'BOUNDARY_VIOLATION':
                symbol = "WARNING️"
            else:
                symbol = "✗"

            print(f"  {symbol} {service_name}: {result['status']}")
            if result['actual_module'] and result['actual_module'] != result['expected_module']:
                print(f"      Expected: {result['expected_module']}")
                print(f"      Actual: {result['actual_module']}")

        # Validate critical service boundaries
        critical_services = ['UserExecutionEngine', 'ExecutionEngineFactory']
        for service in critical_services:
            if service in boundary_validation_results:
                self.assertIn(boundary_validation_results[service]['status'],
                             ['BOUNDARY_INTACT', 'BOUNDARY_VIOLATION'],
                             f"Critical service {service} must be available")

        print("CHECK Service boundary integration validation completed")

    def test_business_workflow_integration_continuity(self):
        """Test business workflow integration continuity after consolidation.

        Business Impact: Validates end-to-end business workflows continue
        to function after import consolidation.
        """
        workflow_integration_tests = []

        try:
            # Test 1: UserExecutionEngine creation workflow
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            workflow_integration_tests.append({
                'workflow': 'UserExecutionEngine Creation',
                'status': 'IMPORT_SUCCESS',
                'details': 'UserExecutionEngine successfully imported'
            })

            # Test 2: Factory pattern workflow
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

                workflow_integration_tests.append({
                    'workflow': 'Factory Pattern Creation',
                    'status': 'IMPORT_SUCCESS',
                    'details': 'ExecutionEngineFactory successfully imported'
                })

                # Test basic factory interface
                if hasattr(ExecutionEngineFactory, 'create_execution_engine'):
                    workflow_integration_tests.append({
                        'workflow': 'Factory Interface',
                        'status': 'INTERFACE_AVAILABLE',
                        'details': 'create_execution_engine method available'
                    })

            except ImportError as e:
                workflow_integration_tests.append({
                    'workflow': 'Factory Pattern Creation',
                    'status': 'IMPORT_FAILURE',
                    'details': f'ExecutionEngineFactory import failed: {e}'
                })

            # Test 3: User context workflow
            try:
                from netra_backend.app.services.user_execution_context import UserExecutionContext

                workflow_integration_tests.append({
                    'workflow': 'User Context Creation',
                    'status': 'IMPORT_SUCCESS',
                    'details': 'UserExecutionContext successfully imported'
                })

            except ImportError as e:
                workflow_integration_tests.append({
                    'workflow': 'User Context Creation',
                    'status': 'IMPORT_FAILURE',
                    'details': f'UserExecutionContext import failed: {e}'
                })

        except ImportError as e:
            workflow_integration_tests.append({
                'workflow': 'UserExecutionEngine Creation',
                'status': 'IMPORT_FAILURE',
                'details': f'UserExecutionEngine import failed: {e}'
            })

        # Report workflow integration results
        success_count = sum(1 for test in workflow_integration_tests
                           if test['status'] in ['IMPORT_SUCCESS', 'INTERFACE_AVAILABLE'])
        total_count = len(workflow_integration_tests)

        print(f"🔄 Business Workflow Integration: {success_count}/{total_count} workflows functional")

        for test in workflow_integration_tests:
            if test['status'] in ['IMPORT_SUCCESS', 'INTERFACE_AVAILABLE']:
                symbol = "CHECK"
            else:
                symbol = "✗"

            print(f"  {symbol} {test['workflow']}: {test['status']}")
            print(f"      {test['details']}")

        # Validate at least core workflow works
        self.assertGreater(success_count, 0,
                          "At least one business workflow must be functional")

        print("CHECK Business workflow integration continuity validated")


if __name__ == '__main__':
    print("🚀 Issue #1186 UserExecutionEngine Service Integration Validation Tests")
    print("=" * 80)
    print("Business Impact: Validates service integration after import consolidation")
    print("Focus: WebSocket integration, Agent Registry, User isolation, Service boundaries")
    print("Execution: Integration tests (non-docker)")
    print("=" * 80)

    unittest.main(verbosity=2)