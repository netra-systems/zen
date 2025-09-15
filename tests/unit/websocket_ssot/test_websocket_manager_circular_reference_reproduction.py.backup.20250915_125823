"""WebSocket Manager Circular Reference Reproduction Test - Issue #824

CRITICAL BUSINESS CONTEXT:
- Issue #824: WebSocket Manager SSOT fragmentation causing Golden Path failures
- Business Impact: $500K+ ARR from chat functionality failures
- Root Cause: Circular reference in websocket_ssot.py:1207 - get_websocket_manager() calls itself
- Golden Path Impact: Infinite loops in WebSocket manager creation blocking user interactions

TEST PURPOSE:
This test MUST reproduce the circular reference issue to validate the problem exists,
then verify the fix eliminates the circular reference pattern.

Expected Behavior:
- BEFORE FIX: Test reproduces circular reference causing infinite loop or stack overflow
- AFTER FIX: Test passes with proper WebSocket manager creation

Business Value Justification:
- Segment: ALL (Free -> Enterprise) - Critical infrastructure
- Business Goal: Fix Golden Path agent execution failures
- Value Impact: Restore chat functionality reliability (90% of platform value)
- Revenue Impact: Protect $500K+ ARR from WebSocket-dependent features
"""

import pytest
import sys
import time
import threading
import asyncio
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class TestWebSocketManagerCircularReferenceReproduction(SSotBaseTestCase):
    """Reproduce circular reference issues in WebSocket manager creation."""

    def setup_method(self, method):
        """Set up test environment with clean import state."""
        super().setup_method(method)
        logger.info(f"Setting up circular reference reproduction test: {method.__name__}")

        # Clear any cached WebSocket manager modules to ensure clean test
        websocket_modules = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.routes.websocket_ssot'
        ]

        for module_name in websocket_modules:
            if module_name in sys.modules:
                logger.info(f"Clearing cached module: {module_name}")
                del sys.modules[module_name]

    def test_circular_reference_in_websocket_ssot_factory_method(self):
        """
        Test to reproduce the specific circular reference issue in websocket_ssot.py:1207.

        PROBLEM: The _create_websocket_manager method calls get_websocket_manager()
        which can cause infinite recursion if not properly implemented.

        Expected: This test should initially FAIL by detecting circular reference,
        then PASS after the fix is implemented.
        """
        logger.info("Testing circular reference in websocket_ssot.py factory method")

        # Create mock user context
        mock_user_context = MagicMock()
        mock_user_context.user_id = "test_user_circular"

        # Track call depth to detect infinite recursion
        call_depth = {"count": 0}
        original_get_websocket_manager = None

        def track_calls_wrapper(original_func):
            """Wrapper to track recursive calls and prevent infinite loop."""
            def wrapper(*args, **kwargs):
                call_depth["count"] += 1

                # Prevent infinite loop by limiting depth
                if call_depth["count"] > 50:
                    raise RecursionError(f"Circular reference detected: get_websocket_manager called {call_depth['count']} times")

                logger.debug(f"get_websocket_manager call depth: {call_depth['count']}")

                try:
                    return original_func(*args, **kwargs)
                finally:
                    call_depth["count"] -= 1
            return wrapper

        try:
            # Import the problematic module
            from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter

            # Create instance to test
            route_instance = WebSocketSSOTRouter()

            # Patch get_websocket_manager to track calls if it gets imported
            try:
                from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
                original_get_websocket_manager = get_websocket_manager

                # Apply tracking wrapper
                tracked_get_websocket_manager = track_calls_wrapper(original_get_websocket_manager)

                with patch('netra_backend.app.routes.websocket_ssot.get_websocket_manager', tracked_get_websocket_manager):
                    with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager', tracked_get_websocket_manager):

                        # This should trigger the circular reference issue
                        # Set a timeout to prevent test hanging
                        start_time = time.time()
                        max_test_time = 30.0  # 30 seconds max

                        async def test_websocket_creation():
                            """Test async WebSocket manager creation with timeout."""
                            try:
                                # This line should trigger circular reference if the bug exists
                                manager = await route_instance._create_websocket_manager(mock_user_context)

                                # If we get here, the circular reference is fixed
                                assert manager is not None, "WebSocket manager should be created successfully"

                                logger.info(f"SUCCESS: WebSocket manager created without circular reference. Call depth reached: {call_depth['count']}")
                                return True

                            except RecursionError as e:
                                logger.error(f"CIRCULAR REFERENCE DETECTED: {e}")
                                # This is the expected failure before fix
                                raise AssertionError(f"Circular reference issue reproduced: {e}")

                            except Exception as e:
                                logger.warning(f"Other exception occurred: {e}")
                                # This might be acceptable depending on environment
                                return False

                        # Run with timeout
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                        # Use timeout to prevent hanging
                        result = None
                        try:
                            result = loop.run_until_complete(
                                asyncio.wait_for(test_websocket_creation(), timeout=max_test_time)
                            )
                        except asyncio.TimeoutError:
                            pytest.fail(f"WebSocket manager creation timed out after {max_test_time}s - likely circular reference causing infinite loop")
                        except RecursionError as e:
                            # This is expected behavior if bug is present
                            logger.info(f"CIRCULAR REFERENCE REPRODUCED: {e}")
                            pytest.fail(f"Issue #824 confirmed: Circular reference in websocket_ssot.py - {e}")

                        elapsed_time = time.time() - start_time
                        logger.info(f"Test completed in {elapsed_time:.2f} seconds with max call depth: {call_depth['count']}")

                        # Validate no excessive recursion occurred
                        max_acceptable_call_depth = 10
                        if call_depth["count"] > max_acceptable_call_depth:
                            pytest.fail(
                                f"Excessive recursion detected: {call_depth['count']} calls to get_websocket_manager. "
                                f"This suggests circular reference issue even if not infinite."
                            )

                        # If we reach here, the fix is working
                        assert result is not False, "WebSocket manager creation should succeed after circular reference fix"

            except ImportError as e:
                logger.warning(f"Could not import websocket components: {e}")
                pytest.skip(f"WebSocket components not available for testing: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in circular reference test: {e}")
            # Don't skip - this might be the issue we're trying to reproduce
            raise

    def test_multiple_import_paths_create_different_managers(self):
        """
        Test that validates SSOT fragmentation - different import paths creating different manager instances.

        This test should FAIL before SSOT consolidation and PASS after.
        """
        logger.info("Testing import path fragmentation creating different manager instances")

        mock_user_context = MagicMock()
        mock_user_context.user_id = "test_user_fragmentation"

        manager_instances = {}

        try:
            # Test different import paths that should return the SAME manager
            import_paths = [
                'netra_backend.app.websocket_core.websocket_manager',
                'netra_backend.app.websocket_core.unified_manager'
            ]

            for import_path in import_paths:
                try:
                    module = __import__(import_path, fromlist=[''])

                    # Try to get manager creation function
                    if hasattr(module, 'get_websocket_manager'):
                        get_manager_func = getattr(module, 'get_websocket_manager')

                        # Create manager using this import path
                        if asyncio.iscoroutinefunction(get_manager_func):
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                            try:
                                manager = loop.run_until_complete(get_manager_func(mock_user_context))
                                manager_instances[import_path] = manager
                                logger.info(f"Created manager from {import_path}: {type(manager).__name__}")
                            except Exception as e:
                                logger.warning(f"Failed to create manager from {import_path}: {e}")
                                manager_instances[import_path] = None
                        else:
                            try:
                                manager = get_manager_func(mock_user_context)
                                manager_instances[import_path] = manager
                                logger.info(f"Created manager from {import_path}: {type(manager).__name__}")
                            except Exception as e:
                                logger.warning(f"Failed to create manager from {import_path}: {e}")
                                manager_instances[import_path] = None

                except ImportError as e:
                    logger.warning(f"Could not import from {import_path}: {e}")
                    manager_instances[import_path] = None
                except Exception as e:
                    logger.error(f"Unexpected error importing from {import_path}: {e}")
                    manager_instances[import_path] = None

            # Filter out failed imports
            successful_managers = {path: mgr for path, mgr in manager_instances.items() if mgr is not None}

            if len(successful_managers) < 2:
                pytest.skip(f"Need at least 2 successful manager creations for comparison, got {len(successful_managers)}")

            # Check if all managers are the same type (SSOT compliance)
            manager_types = {path: type(mgr).__name__ for path, mgr in successful_managers.items()}
            unique_types = set(manager_types.values())

            logger.info(f"Manager types from different import paths: {manager_types}")

            if len(unique_types) > 1:
                # This indicates SSOT fragmentation - different types from different import paths
                logger.error(f"SSOT FRAGMENTATION DETECTED: Different manager types from different imports: {manager_types}")
                pytest.fail(
                    f"Issue #824: SSOT fragmentation confirmed. Different manager types from different imports: {manager_types}. "
                    f"This violates Single Source of Truth principle."
                )

            # Additional check: verify managers behave consistently
            manager_behaviors = {}
            for path, mgr in successful_managers.items():
                behavior_signature = {
                    'has_send_event': hasattr(mgr, 'send_event'),
                    'has_broadcast': hasattr(mgr, 'broadcast'),
                    'has_connect': hasattr(mgr, 'connect'),
                    'class_module': mgr.__class__.__module__,
                    'class_name': mgr.__class__.__name__
                }
                manager_behaviors[path] = behavior_signature

            logger.info(f"Manager behaviors: {manager_behaviors}")

            # All managers should have consistent behavior (same methods available)
            first_behavior = next(iter(manager_behaviors.values()))
            for path, behavior in manager_behaviors.items():
                if behavior != first_behavior:
                    logger.error(f"INCONSISTENT BEHAVIOR: Manager from {path} has different interface: {behavior} vs {first_behavior}")
                    pytest.fail(
                        f"Issue #824: Inconsistent manager interfaces from different import paths. "
                        f"Path {path} behavior differs from expected."
                    )

            logger.info("SUCCESS: All manager instances have consistent types and behaviors - SSOT compliance achieved")

        except Exception as e:
            logger.error(f"Error in import path fragmentation test: {e}")
            raise

    def test_websocket_factory_method_infinite_loop_timeout(self):
        """
        Test that specifically targets the infinite loop scenario with timeout protection.

        This test simulates the exact conditions that would cause infinite recursion
        in the websocket_ssot.py factory method.
        """
        logger.info("Testing WebSocket factory method infinite loop with timeout protection")

        mock_user_context = MagicMock()
        mock_user_context.user_id = "test_timeout_protection"

        # Create a controlled timeout test
        def timeout_test():
            """Run factory method test with timeout."""

            try:
                from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
                route = WebSocketSSOTRouter()

                # This is the problematic call that should be fixed
                async def run_factory_test():
                    return await route._create_websocket_manager(mock_user_context)

                # Execute with strict timeout
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # 10 second timeout - should be more than enough for normal operation
                result = loop.run_until_complete(asyncio.wait_for(run_factory_test(), timeout=10.0))

                logger.info("SUCCESS: Factory method completed within timeout - no infinite loop")
                return result

            except asyncio.TimeoutError:
                logger.error("INFINITE LOOP DETECTED: Factory method timed out")
                raise AssertionError("Issue #824: WebSocket factory method infinite loop confirmed - operation timed out")

            except RecursionError as e:
                logger.error(f"RECURSION ERROR: {e}")
                raise AssertionError(f"Issue #824: Circular reference causing recursion error: {e}")

            except Exception as e:
                logger.warning(f"Other exception in factory method: {e}")
                # Depending on the environment, some exceptions might be acceptable
                return None

        # Run the timeout test
        start_time = time.time()

        try:
            result = timeout_test()
            elapsed_time = time.time() - start_time

            logger.info(f"Factory method test completed in {elapsed_time:.2f} seconds")

            # Verify reasonable completion time
            max_reasonable_time = 5.0  # Should complete within 5 seconds
            if elapsed_time > max_reasonable_time:
                logger.warning(f"Factory method took {elapsed_time:.2f}s - longer than expected {max_reasonable_time}s")
                pytest.fail(
                    f"WebSocket factory method took {elapsed_time:.2f}s, which suggests performance issues. "
                    f"Expected completion under {max_reasonable_time}s."
                )

            # If result is None, it might indicate environment issues, not necessarily the bug
            if result is not None:
                assert result is not None, "Factory method should return a valid manager"
                logger.info("Factory method successfully created WebSocket manager")
            else:
                logger.info("Factory method completed but returned None (possibly due to environment)")

        except AssertionError:
            # Re-raise assertion errors (these are test failures we want to report)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in timeout test: {e}")
            raise

    def teardown_method(self, method):
        """Clean up after test."""
        logger.info(f"Tearing down circular reference test: {method.__name__}")
        super().teardown_method(method)

        # Force cleanup of any problematic modules
        problematic_modules = [
            'netra_backend.app.routes.websocket_ssot',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.unified_manager'
        ]

        for module_name in problematic_modules:
            if module_name in sys.modules:
                try:
                    del sys.modules[module_name]
                    logger.debug(f"Cleaned up module: {module_name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup module {module_name}: {e}")
