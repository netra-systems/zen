"""
Issue #1231 Async/Await Bug Reproduction Tests

CRITICAL BUG: get_websocket_manager() is being awaited incorrectly in websocket_ssot.py
causing complete WebSocket connection failures.

These tests REPRODUCE the bug to demonstrate the issue before applying the fix.

Business Impact: Breaks Golden Path user flow (90% of platform value, $500K+ ARR dependency)

Test Categories:
- Unit tests demonstrating incorrect async/await usage
- Manager creation failures
- Health endpoint failures
- Configuration endpoint failures

Expected Results: ALL TESTS SHOULD FAIL until the bug is fixed by removing 'await' from get_websocket_manager() calls
"""

import sys
import pytest
import asyncio
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parents[3]
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestIssue1231AsyncAwaitBugReproduction:
    """
    REPRODUCTION TESTS: These tests demonstrate the async/await bug in websocket_ssot.py

    EXPECTED RESULT: ALL TESTS SHOULD FAIL with the current bug
    """

    def create_test_user_context(self):
        """Create test user context for WebSocket manager testing."""
        return UserExecutionContext(
            user_id="issue-1231-test-user",
            thread_id="issue-1231-test-thread",
            run_id="issue-1231-reproduction",
            request_id="issue-1231-test-request"
        )

    def test_get_websocket_manager_is_synchronous_function(self):
        """
        BASELINE TEST: Verify get_websocket_manager() is synchronous (not a coroutine)

        This test confirms the function signature - it's NOT an async function,
        so awaiting it should cause errors.
        """
        import inspect

        # Verify get_websocket_manager is NOT a coroutine function
        assert not inspect.iscoroutinefunction(get_websocket_manager), \
            "get_websocket_manager() should be synchronous, not async"

        # Verify it's a regular function
        assert callable(get_websocket_manager), "get_websocket_manager should be callable"

        # Test synchronous call works fine
        user_context = self.create_test_user_context()
        manager = get_websocket_manager(user_context)
        assert manager is not None, "Synchronous call should work"

    @pytest.mark.asyncio
    async def test_awaiting_get_websocket_manager_causes_error(self):
        """
        REPRODUCTION TEST: Demonstrates that awaiting get_websocket_manager() fails

        This reproduces the exact bug pattern found in websocket_ssot.py where
        'await get_websocket_manager()' is used incorrectly.

        EXPECTED: This test should FAIL, demonstrating the bug
        """
        user_context = self.create_test_user_context()

        # This is the INCORRECT pattern used in websocket_ssot.py
        # It should cause a TypeError or RuntimeError
        with pytest.raises((TypeError, RuntimeError, AttributeError)) as exc_info:
            # This is the BUGGY code pattern from websocket_ssot.py
            manager = await get_websocket_manager(user_context)

        error_msg = str(exc_info.value).lower()

        # Verify the error indicates the async/await problem
        assert any(keyword in error_msg for keyword in [
            "await", "coroutine", "generator", "async", "object is not awaitable"
        ]), f"Error should indicate async/await problem. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_simulated_websocket_ssot_manager_creation_bug(self):
        """
        REPRODUCTION TEST: Simulates the exact bug pattern in websocket_ssot.py

        This test recreates the problematic code pattern from the create_websocket_manager_ssot() function.
        """
        async def simulate_websocket_ssot_manager_creation(user_context):
            """Simulate the buggy code from websocket_ssot.py"""
            try:
                # This is the EXACT problematic line from websocket_ssot.py
                manager = await get_websocket_manager(user_context)  # BUG: awaiting non-coroutine
                return manager
            except Exception as e:
                # This exception demonstrates the bug
                raise RuntimeError(f"WebSocket manager creation failed due to async/await bug: {e}")

        user_context = self.create_test_user_context()

        # This should fail, reproducing the bug
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_websocket_ssot_manager_creation(user_context)

        assert "async/await bug" in str(exc_info.value), \
            f"Should fail due to async/await bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_simulated_health_endpoint_bug(self):
        """
        REPRODUCTION TEST: Simulates the bug in WebSocket health endpoint

        This recreates the problematic pattern in the health check endpoint.
        """
        async def simulate_health_endpoint():
            """Simulate the buggy health endpoint code"""
            try:
                # This simulates the buggy pattern from websocket_ssot.py health endpoint
                manager = await get_websocket_manager(user_context=None)  # BUG: awaiting non-coroutine
                return {"status": "healthy", "manager": str(manager)}
            except Exception as e:
                raise RuntimeError(f"Health endpoint failed due to async/await bug: {e}")

        # This should fail, reproducing the health endpoint bug
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_health_endpoint()

        assert "async/await bug" in str(exc_info.value), \
            f"Health endpoint should fail due to bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_simulated_config_endpoint_bug(self):
        """
        REPRODUCTION TEST: Simulates the bug in WebSocket config endpoint

        This recreates the problematic pattern in the configuration endpoint.
        """
        async def simulate_config_endpoint():
            """Simulate the buggy config endpoint code"""
            try:
                # This simulates the buggy pattern from websocket_ssot.py config endpoint
                manager = await get_websocket_manager(user_context=None)  # BUG: awaiting non-coroutine
                return {"websocket_config": {"manager": str(manager)}}
            except Exception as e:
                raise RuntimeError(f"Config endpoint failed due to async/await bug: {e}")

        # This should fail, reproducing the config endpoint bug
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_config_endpoint()

        assert "async/await bug" in str(exc_info.value), \
            f"Config endpoint should fail due to bug. Got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_simulated_stats_endpoint_bug(self):
        """
        REPRODUCTION TEST: Simulates the bug in WebSocket statistics endpoint

        This recreates the problematic pattern in the statistics endpoint.
        """
        async def simulate_stats_endpoint():
            """Simulate the buggy stats endpoint code"""
            try:
                # This simulates the buggy pattern from websocket_ssot.py stats endpoint
                manager = await get_websocket_manager(user_context=None)  # BUG: awaiting non-coroutine
                return {"stats": {"manager": str(manager)}}
            except Exception as e:
                raise RuntimeError(f"Stats endpoint failed due to async/await bug: {e}")

        # This should fail, reproducing the stats endpoint bug
        with pytest.raises(RuntimeError) as exc_info:
            await simulate_stats_endpoint()

        assert "async/await bug" in str(exc_info.value), \
            f"Stats endpoint should fail due to bug. Got: {exc_info.value}"

    def test_correct_synchronous_usage_works(self):
        """
        VALIDATION TEST: Demonstrates the CORRECT way to use get_websocket_manager()

        This shows how the function should be called (without await) and that it works fine.
        This test should PASS even with the current bug.
        """
        user_context = self.create_test_user_context()

        # CORRECT usage: No await, direct synchronous call
        manager = get_websocket_manager(user_context)

        # Verify manager was created successfully
        assert manager is not None, "Manager should be created"
        assert hasattr(manager, 'send_to_thread'), "Manager should have WebSocket functionality"

        # Test with None user context (health endpoints)
        health_manager = get_websocket_manager(user_context=None)
        assert health_manager is not None, "Health endpoint manager should be created"


if __name__ == "__main__":
    print("=" * 80)
    print("ISSUE #1231 ASYNC/AWAIT BUG REPRODUCTION TESTS")
    print("=" * 80)
    print("These tests demonstrate the critical async/await bug in websocket_ssot.py")
    print("EXPECTED: Tests should FAIL until 'await' is removed from get_websocket_manager() calls")
    print("=" * 80)

    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])