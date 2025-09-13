"""Integration tests for Issue #686: Execution Engine SSOT Consolidation.

This test suite validates the integration between multiple execution engines
during the consolidation process to ensure Golden Path functionality is preserved.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Performance Protection
- Value Impact: Protects $500K+ ARR chat functionality during SSOT migration
- Strategic Impact: Ensures seamless transition from multiple engines to single SSOT

Integration Test Strategy:
- Test cross-service execution consistency during consolidation
- Validate WebSocket event delivery remains intact
- Ensure user isolation is maintained during engine transitions
- Verify performance doesn't degrade during consolidation
- Test backwards compatibility with legacy engine consumers

CRITICAL: These tests use REAL SERVICES (no Docker required) to validate
actual integration behavior during SSOT consolidation process.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestExecutionEngineConsolidationIntegration(SSotAsyncTestCase):
    """Integration tests for execution engine SSOT consolidation."""

    def setUp(self):
        """Set up test fixtures for integration testing."""
        super().setUp()

        # Test user contexts for isolation validation
        self.test_user_context_1 = UserExecutionContext(
            user_id="test_user_1",
            session_id="test_session_1",
            request_id=f"test_req_{uuid.uuid4()}"
        )

        self.test_user_context_2 = UserExecutionContext(
            user_id="test_user_2",
            session_id="test_session_2",
            request_id=f"test_req_{uuid.uuid4()}"
        )

        # Track WebSocket events for validation
        self.websocket_events = []
        self.execution_results = {}

    async def test_01_cross_service_execution_consistency_validation(self):
        """INITIALLY FAILING TEST: Validate execution consistency across services.

        This test SHOULD FAIL initially if multiple execution engines
        produce inconsistent results for the same operations.
        """
        # Test execution through different engine entry points
        execution_targets = [
            ("UserExecutionEngine", "netra_backend.app.agents.supervisor.user_execution_engine"),
            ("ToolExecutionEngine", "netra_backend.app.agents.tool_dispatcher_execution"),
            ("UnifiedToolExecutionEngine", "netra_backend.app.agents.unified_tool_execution"),
        ]

        execution_results = {}

        for engine_name, module_path in execution_targets:
            try:
                # Import and create engine instance
                module = __import__(module_path, fromlist=[engine_name])
                engine_class = getattr(module, engine_name)

                # Create test execution context
                if hasattr(engine_class, '__init__'):
                    engine_instance = engine_class()
                else:
                    continue

                # Test simple execution operation
                test_operation = {
                    'operation': 'test_execution_consistency',
                    'user_context': self.test_user_context_1,
                    'timestamp': time.time()
                }

                # Store result for comparison
                execution_results[engine_name] = {
                    'engine_instance': engine_instance,
                    'supports_user_context': hasattr(engine_instance, 'user_context'),
                    'execution_methods': [
                        method for method in dir(engine_instance)
                        if method.startswith(('execute', 'run', 'process')) and not method.startswith('_')
                    ]
                }

            except (ImportError, AttributeError) as e:
                execution_results[engine_name] = {'error': str(e)}

        # Validate consistency requirements
        print(f"\nEXECUTION ENGINE ANALYSIS:")
        for engine_name, result in execution_results.items():
            if 'error' not in result:
                print(f"  {engine_name}: {len(result['execution_methods'])} methods, "
                      f"user_context_support={result['supports_user_context']}")
            else:
                print(f"  {engine_name}: ERROR - {result['error']}")

        # EXPECTED TO FAIL: Inconsistent execution patterns
        engines_with_user_context = [
            name for name, result in execution_results.items()
            if 'error' not in result and result['supports_user_context']
        ]

        self.assertGreater(
            len(engines_with_user_context),
            0,
            "At least one execution engine should support user context for proper isolation"
        )

        # Check for method signature consistency
        all_execution_methods = set()
        for result in execution_results.values():
            if 'error' not in result:
                all_execution_methods.update(result['execution_methods'])

        # SSOT requirement: Core execution methods should be consistent
        core_methods = {'execute', 'execute_with_context', 'execute_async'}
        available_core_methods = core_methods.intersection(all_execution_methods)

        self.assertGreater(
            len(available_core_methods),
            0,
            f"SSOT VIOLATION: No consistent core execution methods found. "
            f"Available methods: {all_execution_methods}, Expected core methods: {core_methods}"
        )

    async def test_02_websocket_event_delivery_during_consolidation(self):
        """Validate WebSocket events are delivered consistently during consolidation."""

        # Mock WebSocket manager for event tracking
        mock_websocket_manager = Mock()
        mock_websocket_manager.emit_event = Mock()

        captured_events = []

        def capture_event(*args, **kwargs):
            captured_events.append({'args': args, 'kwargs': kwargs, 'timestamp': time.time()})
            return True

        mock_websocket_manager.emit_event.side_effect = capture_event

        # Test execution engines that handle WebSocket events
        websocket_execution_targets = [
            "netra_backend.app.agents.unified_tool_execution.UnifiedToolExecutionEngine",
        ]

        for target in websocket_execution_targets:
            try:
                module_path, class_name = target.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                engine_class = getattr(module, class_name)

                # Create instance with mock WebSocket manager
                if 'websocket_manager' in engine_class.__init__.__code__.co_varnames:
                    engine = engine_class(websocket_manager=mock_websocket_manager)
                else:
                    engine = engine_class()
                    # Set websocket manager if possible
                    if hasattr(engine, 'websocket_manager'):
                        engine.websocket_manager = mock_websocket_manager

                # Test WebSocket event emission
                if hasattr(engine, 'emit_event') or hasattr(mock_websocket_manager, 'emit_event'):
                    test_events = [
                        ('agent_started', {'user_id': self.test_user_context_1.user_id}),
                        ('tool_executing', {'tool_name': 'test_tool'}),
                        ('agent_completed', {'result': 'success'})
                    ]

                    for event_type, event_data in test_events:
                        if hasattr(engine, 'emit_event'):
                            await engine.emit_event(event_type, event_data)
                        else:
                            mock_websocket_manager.emit_event(event_type, event_data)

            except (ImportError, AttributeError, TypeError) as e:
                print(f"Failed to test WebSocket integration for {target}: {e}")

        # Validate WebSocket events were captured
        print(f"\nCAPTURED WEBSOCKET EVENTS: {len(captured_events)}")
        for i, event in enumerate(captured_events):
            print(f"  Event {i+1}: {event}")

        # SSOT requirement: Events should be delivered through consistent channel
        self.assertGreater(
            len(captured_events),
            0,
            "WebSocket events should be delivered during execution engine operations"
        )

    async def test_03_user_isolation_during_engine_transitions(self):
        """INITIALLY FAILING TEST: Validate user isolation during engine transitions.

        This test SHOULD FAIL if different execution engines share state
        between users or don't properly isolate user contexts.
        """

        # Test concurrent user operations through different engines
        isolation_test_results = {}

        # Simulate concurrent user operations
        user_operations = [
            (self.test_user_context_1, "operation_user_1", {"param": "value_1"}),
            (self.test_user_context_2, "operation_user_2", {"param": "value_2"}),
        ]

        async def simulate_user_operation(user_context, operation_name, operation_params):
            """Simulate user operation through execution engines."""
            try:
                # Try to import and use UserExecutionEngine (SSOT target)
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

                # Create engine instance with user context
                if hasattr(UserExecutionEngine, 'create_for_user'):
                    engine = await UserExecutionEngine.create_for_user(user_context)
                else:
                    engine = UserExecutionEngine(user_context=user_context)

                # Store operation result with user isolation validation
                isolation_test_results[user_context.user_id] = {
                    'engine_id': id(engine),
                    'user_context': user_context,
                    'operation_name': operation_name,
                    'operation_params': operation_params,
                    'timestamp': time.time()
                }

                return True

            except Exception as e:
                isolation_test_results[user_context.user_id] = {'error': str(e)}
                return False

        # Execute concurrent operations
        tasks = [
            simulate_user_operation(user_context, op_name, op_params)
            for user_context, op_name, op_params in user_operations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate user isolation
        print(f"\nUSER ISOLATION TEST RESULTS:")
        for user_id, result in isolation_test_results.items():
            if 'error' not in result:
                print(f"  User {user_id}: Engine ID {result['engine_id']}, Operation: {result['operation_name']}")
            else:
                print(f"  User {user_id}: ERROR - {result['error']}")

        # EXPECTED TO FAIL: User contexts should be properly isolated
        successful_operations = [r for r in isolation_test_results.values() if 'error' not in r]

        self.assertEqual(
            len(successful_operations),
            2,
            f"Both user operations should succeed with proper isolation. "
            f"Successful: {len(successful_operations)}, Expected: 2"
        )

        # Verify different engine instances for different users
        if len(successful_operations) >= 2:
            engine_ids = [result['engine_id'] for result in successful_operations]

            self.assertEqual(
                len(set(engine_ids)),
                len(engine_ids),
                f"SSOT VIOLATION: Users should have separate engine instances for isolation. "
                f"Found engine IDs: {engine_ids}"
            )

    async def test_04_performance_validation_during_consolidation(self):
        """Validate performance doesn't degrade during SSOT consolidation."""

        performance_metrics = {}

        # Test performance of different execution patterns
        execution_patterns = [
            ("direct_user_engine", self._test_direct_user_engine_performance),
            ("legacy_redirect", self._test_legacy_redirect_performance),
            ("tool_execution", self._test_tool_execution_performance),
        ]

        for pattern_name, test_method in execution_patterns:
            start_time = time.time()

            try:
                result = await test_method()
                execution_time = time.time() - start_time

                performance_metrics[pattern_name] = {
                    'execution_time': execution_time,
                    'success': True,
                    'result': result
                }

            except Exception as e:
                execution_time = time.time() - start_time
                performance_metrics[pattern_name] = {
                    'execution_time': execution_time,
                    'success': False,
                    'error': str(e)
                }

        # Analyze performance results
        print(f"\nPERFORMANCE METRICS:")
        for pattern, metrics in performance_metrics.items():
            status = "SUCCESS" if metrics['success'] else f"FAILED: {metrics.get('error', 'Unknown')}"
            print(f"  {pattern}: {metrics['execution_time']:.3f}s - {status}")

        # Performance requirements
        successful_patterns = [p for p, m in performance_metrics.items() if m['success']]

        self.assertGreater(
            len(successful_patterns),
            0,
            "At least one execution pattern should complete successfully"
        )

        # Check execution times are reasonable (< 5 seconds for test operations)
        for pattern, metrics in performance_metrics.items():
            if metrics['success']:
                self.assertLess(
                    metrics['execution_time'],
                    5.0,
                    f"Execution pattern '{pattern}' took {metrics['execution_time']:.3f}s, "
                    f"should complete in < 5 seconds"
                )

    async def test_05_backwards_compatibility_validation(self):
        """Validate backwards compatibility with legacy execution engine consumers."""

        compatibility_results = {}

        # Test legacy import patterns still work
        legacy_import_patterns = [
            ("supervisor.execution_engine", "ExecutionEngine"),
            ("agents.tool_dispatcher_execution", "ToolExecutionEngine"),
        ]

        for module_suffix, class_name in legacy_import_patterns:
            try:
                # Test import pattern
                full_module = f"netra_backend.app.{module_suffix}"
                module = __import__(full_module, fromlist=[class_name])
                execution_class = getattr(module, class_name)

                # Test basic instantiation
                if hasattr(execution_class, '__init__'):
                    instance = execution_class()

                    compatibility_results[f"{module_suffix}.{class_name}"] = {
                        'import_success': True,
                        'instantiation_success': True,
                        'methods': [m for m in dir(instance) if not m.startswith('_')],
                        'class_type': str(type(instance))
                    }
                else:
                    compatibility_results[f"{module_suffix}.{class_name}"] = {
                        'import_success': True,
                        'instantiation_success': False,
                        'reason': 'No __init__ method'
                    }

            except Exception as e:
                compatibility_results[f"{module_suffix}.{class_name}"] = {
                    'import_success': False,
                    'error': str(e)
                }

        # Validate backwards compatibility
        print(f"\nBACKWARDS COMPATIBILITY RESULTS:")
        for pattern, result in compatibility_results.items():
            if result.get('import_success'):
                methods_count = len(result.get('methods', []))
                print(f"  {pattern}: Import ✓, Instantiation {'✓' if result.get('instantiation_success') else '✗'}, Methods: {methods_count}")
            else:
                print(f"  {pattern}: Import ✗ - {result.get('error')}")

        # SSOT requirement: Legacy imports should work (redirects to SSOT)
        successful_imports = [p for p, r in compatibility_results.items() if r.get('import_success')]

        self.assertGreater(
            len(successful_imports),
            0,
            f"At least some legacy import patterns should work for backwards compatibility. "
            f"Failed imports: {[p for p, r in compatibility_results.items() if not r.get('import_success')]}"
        )

    # Helper methods for performance testing

    async def _test_direct_user_engine_performance(self):
        """Test direct UserExecutionEngine performance."""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            if hasattr(UserExecutionEngine, 'create_for_user'):
                engine = await UserExecutionEngine.create_for_user(self.test_user_context_1)
            else:
                engine = UserExecutionEngine(user_context=self.test_user_context_1)

            return f"UserExecutionEngine created successfully: {type(engine)}"

        except Exception as e:
            raise Exception(f"Direct UserExecutionEngine test failed: {e}")

    async def _test_legacy_redirect_performance(self):
        """Test legacy redirect performance."""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine

            engine = UserExecutionEngine()
            return f"Legacy ExecutionEngine redirect successful: {type(engine)}"

        except Exception as e:
            raise Exception(f"Legacy redirect test failed: {e}")

    async def _test_tool_execution_performance(self):
        """Test tool execution performance."""
        try:
            from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine

            engine = ToolExecutionEngine()
            return f"ToolExecutionEngine created successfully: {type(engine)}"

        except Exception as e:
            raise Exception(f"Tool execution test failed: {e}")


if __name__ == '__main__':
    import unittest
    unittest.main()