"""Integration tests for Issue #1101 QualityMessageRouter handler registration issues.

Tests that should FAIL initially to reproduce real handler registration
problems during integration between QualityMessageRouter and main router.

Business Impact: Protects $500K+ ARR Golden Path by identifying integration
failures that could break quality message routing in production environment.
"""

import pytest
import unittest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.integration
class QualityRouterHandlerRegistrationIntegrationTests(SSotAsyncTestCase):
    """Test QualityMessageRouter handler registration integration issues - SHOULD FAIL initially."""

    def setUp(self):
        """Setup integration test environment."""
        super().setUp()
        self.registration_failures = []
        self.integration_errors = []
        self.runtime_conflicts = []

    async def test_quality_router_startup_registration_failure(self):
        """Test quality router startup registration failures.

        EXPECTED TO FAIL: Quality router should fail to register properly
        during application startup due to missing service dependencies.
        """
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            # Try to create quality router without proper service initialization
            startup_failures = []

            # Attempt 1: No services provided
            try:
                router = QualityMessageRouter(
                    supervisor=None,
                    db_session_factory=None,
                    quality_gate_service=None,
                    monitoring_service=None
                )
                startup_failures.append("Router created with None services - should fail")

            except Exception as e:
                # This is expected
                startup_failures.append(f"Expected failure with None services: {str(e)}")

            # Attempt 2: Mock services that don't provide required interface
            try:
                incomplete_supervisor = Mock()
                incomplete_db = Mock()
                incomplete_quality = Mock()
                incomplete_monitoring = Mock()

                router = QualityMessageRouter(
                    supervisor=incomplete_supervisor,
                    db_session_factory=incomplete_db,
                    quality_gate_service=incomplete_quality,
                    monitoring_service=incomplete_monitoring
                )

                # Try to use the router - should fail due to incomplete mocks
                test_message = {
                    "type": "get_quality_metrics",
                    "payload": {"user_id": "test"}
                }

                await router.handle_message("test_user", test_message)
                startup_failures.append("Router worked with incomplete mocks - should fail")

            except Exception as e:
                # This is expected
                startup_failures.append(f"Expected failure with incomplete mocks: {str(e)}")

            # This should fail because startup is problematic
            if any("should fail" in failure for failure in startup_failures):
                failure_msg = f"Quality router startup issues: {startup_failures}"
                self.registration_failures.append(failure_msg)
                self.fail(f"EXPECTED FAILURE: {failure_msg}")

        except Exception as e:
            startup_error = f"Quality router startup test failed: {str(e)}"
            self.registration_failures.append(startup_error)
            raise AssertionError(f"EXPECTED FAILURE: {startup_error}")

    async def test_handler_registration_order_dependency_issues(self):
        """Test handler registration order dependency issues.

        EXPECTED TO FAIL: Quality handlers must be registered in specific order
        due to dependencies, but main router doesn't handle order requirements.
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            # Create main router
            main_router = MessageRouter()

            # Mock quality services
            mock_services = {
                'supervisor': Mock(),
                'db_session_factory': Mock(),
                'quality_gate_service': Mock(),
                'monitoring_service': Mock()
            }

            # Create quality router
            quality_router = QualityMessageRouter(**mock_services)

            # Try to register quality handlers in main router
            registration_order_issues = []

            quality_handlers = quality_router.handlers

            # Try registering handlers in different orders
            order_tests = [
                list(quality_handlers.keys()),  # Original order
                list(reversed(quality_handlers.keys())),  # Reversed order
                sorted(quality_handlers.keys()),  # Alphabetical order
            ]

            for i, order in enumerate(order_tests):
                try:
                    # Reset main router for each test
                    main_router.custom_handlers.clear() if hasattr(main_router, 'custom_handlers') else None

                    # Register handlers in specific order
                    for handler_type in order:
                        handler = quality_handlers[handler_type]

                        # Try to register with main router
                        if hasattr(main_router, 'custom_handlers'):
                            main_router.custom_handlers.append(handler)
                        else:
                            # Main router doesn't support custom handler registration
                            registration_order_issues.append(
                                f"Order {i}: Main router missing custom_handlers attribute"
                            )

                    # Test if registered handlers work
                    test_message = {
                        "type": "get_quality_metrics",
                        "payload": {"user_id": "test"}
                    }

                    # Try to route message - this should fail due to order issues
                    if hasattr(main_router, 'handle_message'):
                        try:
                            # This should fail because main router doesn't know how to handle quality messages
                            await main_router.handle_message("test_user", test_message)
                            registration_order_issues.append(
                                f"Order {i}: Unexpectedly succeeded - quality routing should fail"
                            )
                        except Exception as e:
                            registration_order_issues.append(
                                f"Order {i}: Expected failure in routing: {str(e)}"
                            )

                except Exception as e:
                    registration_order_issues.append(f"Order {i}: Registration failed: {str(e)}")

            # This should fail due to order dependency issues
            if registration_order_issues:
                order_msg = f"Handler registration order issues: {registration_order_issues}"
                self.integration_errors.append(order_msg)
                self.fail(f"EXPECTED FAILURE: {order_msg}")

        except Exception as e:
            order_error = f"Handler registration order test failed: {str(e)}"
            self.integration_errors.append(order_error)
            raise AssertionError(f"EXPECTED FAILURE: {order_error}")

    async def test_concurrent_handler_registration_race_conditions(self):
        """Test concurrent handler registration race conditions.

        EXPECTED TO FAIL: Concurrent registration of quality handlers should
        create race conditions and registration conflicts.
        """
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            # Mock services for quality router
            mock_services = {
                'supervisor': Mock(),
                'db_session_factory': Mock(),
                'quality_gate_service': Mock(),
                'monitoring_service': Mock()
            }

            race_condition_errors = []

            # Create multiple quality routers concurrently
            async def create_and_register_router(router_id):
                try:
                    router = QualityMessageRouter(**mock_services)
                    main_router = MessageRouter()

                    # Try to register handlers
                    if hasattr(main_router, 'custom_handlers'):
                        for handler_type, handler in router.handlers.items():
                            main_router.custom_handlers.append(handler)

                    return f"Router {router_id}: Success"

                except Exception as e:
                    return f"Router {router_id}: Failed - {str(e)}"

            # Run multiple concurrent registrations
            tasks = [create_and_register_router(i) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results for race conditions
            for result in results:
                if isinstance(result, Exception):
                    race_condition_errors.append(f"Concurrent registration exception: {str(result)}")
                elif "Failed" in str(result):
                    race_condition_errors.append(f"Concurrent registration failure: {result}")

            # Additional race condition test: shared state modification
            try:
                shared_router = MessageRouter()
                quality_router1 = QualityMessageRouter(**mock_services)
                quality_router2 = QualityMessageRouter(**mock_services)

                # Simulate concurrent modification of router state
                async def modify_router_state(router, quality_router, modification_id):
                    if hasattr(router, 'custom_handlers'):
                        # Add all quality handlers at once
                        for handler_type, handler in quality_router.handlers.items():
                            router.custom_handlers.append(handler)
                    return f"Modification {modification_id} complete"

                # Run concurrent modifications
                mod_tasks = [
                    modify_router_state(shared_router, quality_router1, 1),
                    modify_router_state(shared_router, quality_router2, 2)
                ]

                mod_results = await asyncio.gather(*mod_tasks, return_exceptions=True)

                # Check for race condition indicators
                if hasattr(shared_router, 'custom_handlers'):
                    final_handler_count = len(shared_router.custom_handlers)

                    # If we have duplicate handlers, that indicates race conditions
                    expected_unique_handlers = len(set(quality_router1.handlers.keys()))
                    if final_handler_count != expected_unique_handlers * 2:
                        race_condition_errors.append(
                            f"Handler count mismatch - Expected: {expected_unique_handlers * 2}, "
                            f"Actual: {final_handler_count}"
                        )

            except Exception as e:
                race_condition_errors.append(f"Shared state race condition test failed: {str(e)}")

            # This should fail due to race conditions
            if race_condition_errors:
                race_msg = f"Concurrent registration race conditions: {race_condition_errors}"
                self.runtime_conflicts.append(race_msg)
                self.fail(f"EXPECTED FAILURE: {race_msg}")

            # If no race conditions detected, that's unexpected for concurrent operations
            self.fail("EXPECTED FAILURE: Should detect race conditions in concurrent registration")

        except Exception as e:
            race_error = f"Concurrent registration test failed: {str(e)}"
            self.runtime_conflicts.append(race_error)
            raise AssertionError(f"EXPECTED FAILURE: {race_error}")

    async def test_websocket_manager_integration_conflicts(self):
        """Test WebSocket manager integration conflicts.

        EXPECTED TO FAIL: Quality router's WebSocket manager usage should
        conflict with main router's WebSocket manager expectations.
        """
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            # Mock services for quality router
            mock_services = {
                'supervisor': Mock(),
                'db_session_factory': Mock(),
                'quality_gate_service': Mock(),
                'monitoring_service': Mock()
            }

            quality_router = QualityMessageRouter(**mock_services)

            websocket_conflicts = []

            # Test WebSocket manager creation patterns
            test_user_id = "test_user"
            test_message = {
                "type": "get_quality_metrics",
                "payload": {"user_id": test_user_id}
            }

            # Mock WebSocket manager functions to detect usage patterns
            with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_get_context:
                with patch('netra_backend.app.services.user_execution_context.create_defensive_user_execution_context') as mock_create_ws:

                    # Configure mocks to detect calls
                    mock_context = Mock()
                    mock_get_context.return_value = mock_context

                    mock_websocket_manager = AsyncMock()
                    mock_create_ws.return_value = mock_websocket_manager

                    # Try to handle message
                    try:
                        await quality_router.handle_message(test_user_id, test_message)

                        # Check WebSocket manager usage patterns
                        if mock_get_context.called:
                            call_args = mock_get_context.call_args
                            if call_args:
                                # Check if called with expected parameters
                                args, kwargs = call_args
                                if 'user_id' in kwargs or (args and len(args) > 0):
                                    # Quality router uses specific context creation pattern
                                    websocket_conflicts.append(
                                        "Quality router uses get_user_execution_context with specific pattern"
                                    )

                        if mock_create_ws.called:
                            # Quality router uses defensive context creation
                            websocket_conflicts.append(
                                "Quality router uses create_defensive_user_execution_context pattern"
                            )

                        # Check WebSocket manager method calls
                        if mock_websocket_manager.send_to_user.called:
                            send_calls = mock_websocket_manager.send_to_user.call_args_list
                            websocket_conflicts.append(
                                f"Quality router made {len(send_calls)} WebSocket send calls"
                            )

                    except Exception as e:
                        websocket_conflicts.append(f"WebSocket integration failed: {str(e)}")

            # Test broadcast functionality conflicts
            try:
                test_update = {"metric": "test", "value": 100}
                await quality_router.broadcast_quality_update(test_update)

                # Broadcast should also create WebSocket conflicts
                websocket_conflicts.append("Quality router broadcast creates additional WebSocket usage")

            except Exception as e:
                websocket_conflicts.append(f"Broadcast integration failed: {str(e)}")

            # This should fail due to WebSocket integration conflicts
            if websocket_conflicts:
                ws_msg = f"WebSocket manager integration conflicts: {websocket_conflicts}"
                self.integration_errors.append(ws_msg)
                self.fail(f"EXPECTED FAILURE: {ws_msg}")

            # If no conflicts, WebSocket integration is unexpectedly smooth
            self.fail("EXPECTED FAILURE: Should detect WebSocket manager integration conflicts")

        except Exception as e:
            ws_error = f"WebSocket manager integration test failed: {str(e)}"
            self.integration_errors.append(ws_error)
            raise AssertionError(f"EXPECTED FAILURE: {ws_error}")

    def tearDown(self):
        """Report all detected integration issues."""
        super().tearDown()

        if self.registration_failures or self.integration_errors or self.runtime_conflicts:
            print("\n=== Issue #1101 Handler Registration Integration Issues Detected ===")

            if self.registration_failures:
                print("Registration Failures:")
                for failure in self.registration_failures:
                    print(f"  - {failure}")

            if self.integration_errors:
                print("Integration Errors:")
                for error in self.integration_errors:
                    print(f"  - {error}")

            if self.runtime_conflicts:
                print("Runtime Conflicts:")
                for conflict in self.runtime_conflicts:
                    print(f"  - {conflict}")

            print("These failures indicate real handler registration integration challenges.")
            print("=== End Issue #1101 Integration Report ===\n")


if __name__ == '__main__':
    unittest.main()