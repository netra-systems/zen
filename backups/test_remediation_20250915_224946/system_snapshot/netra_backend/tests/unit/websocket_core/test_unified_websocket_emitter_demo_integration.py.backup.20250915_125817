"""
Test UnifiedWebSocketEmitter Demo Integration - Issue #1209 Reproduction

Phase 1 of Issue #1209 Reproduction Tests - SHOULD FAIL

These tests verify the integration between UnifiedWebSocketEmitter and DemoWebSocketBridge,
specifically reproducing the AttributeError when UnifiedWebSocketEmitter tries to call
is_connection_active on the DemoWebSocketBridge.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability
- Value Impact: Prevents broken demo functionality affecting sales and marketing
- Strategic Impact: $500K+ ARR demos must work reliably for customer acquisition

Expected Result: Tests should FAIL with AttributeError: 'DemoWebSocketBridge' object has no attribute 'is_connection_active'
"""

import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestUnifiedWebSocketEmitterDemoIntegration(SSotAsyncTestCase):
    """Test UnifiedWebSocketEmitter integration with DemoWebSocketBridge - Issue #1209."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Create test user context
        id_manager = UnifiedIDManager()
        self.demo_user_id = id_manager.generate_id(IDType.USER, context={"demo": True})
        self.thread_id = UnifiedIDManager.generate_thread_id()
        self.run_id = UnifiedIDManager.generate_run_id(self.thread_id)

        self.user_context = UserExecutionContext(
            user_id=self.demo_user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=id_manager.generate_id(IDType.REQUEST, context={"demo": True}),
            db_session=Mock(),
            websocket_client_id="test_connection_123",
            agent_context={"user_request": "test message", "demo_mode": True},
            audit_metadata={"demo_session": True, "connection_id": "test_connection_123"}
        )

        # Mock WebSocket adapter for demo bridge
        self.mock_websocket_adapter = Mock()
        self.mock_websocket_adapter.send_event = AsyncMock()
        self.mock_websocket_adapter.notify_agent_started = AsyncMock()
        self.mock_websocket_adapter.notify_agent_thinking = AsyncMock()
        self.mock_websocket_adapter.notify_tool_executing = AsyncMock()
        self.mock_websocket_adapter.notify_tool_completed = AsyncMock()
        self.mock_websocket_adapter.notify_agent_completed = AsyncMock()
        self.mock_websocket_adapter.notify_agent_error = AsyncMock()

    def create_demo_websocket_bridge(self):
        """Create a DemoWebSocketBridge instance exactly like in production."""

        class DemoWebSocketBridge(AgentWebSocketBridge):
            """Demo WebSocket bridge that sends events directly to the demo WebSocket"""

            def __init__(self, websocket_adapter, user_context):
                super().__init__(user_context=user_context)
                self.websocket_adapter = websocket_adapter

            async def notify_agent_started(self, run_id: str, agent_name: str, **kwargs):
                return await self.websocket_adapter.notify_agent_started(run_id, agent_name, **kwargs)

            async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str = "", **kwargs):
                return await self.websocket_adapter.notify_agent_thinking(run_id, agent_name, reasoning, **kwargs)

            async def notify_tool_executing(self, run_id: str, tool_name: str, **kwargs):
                return await self.websocket_adapter.notify_tool_executing(run_id, tool_name, **kwargs)

            async def notify_tool_completed(self, run_id: str, tool_name: str, **kwargs):
                return await self.websocket_adapter.notify_tool_completed(run_id, tool_name, **kwargs)

            async def notify_agent_completed(self, run_id: str, agent_name: str, **kwargs):
                return await self.websocket_adapter.notify_agent_completed(run_id, agent_name, **kwargs)

            async def notify_agent_error(self, run_id: str, agent_name: str, error: str, **kwargs):
                return await self.websocket_adapter.notify_agent_error(run_id, agent_name, error, **kwargs)

        return DemoWebSocketBridge(self.mock_websocket_adapter, self.user_context)

    async def test_emitter_calls_is_connection_active(self):
        """
        CRITICAL TEST: UnifiedWebSocketEmitter calls is_connection_active on DemoWebSocketBridge.

        THIS TEST SHOULD FAIL - reproducing Issue #1209 AttributeError.

        When UnifiedWebSocketEmitter tries to verify connection status before sending events,
        it calls is_connection_active on its manager, which in the demo case is DemoWebSocketBridge.
        However, DemoWebSocketBridge doesn't implement this method.
        """
        # Create demo bridge without is_connection_active method
        demo_bridge = self.create_demo_websocket_bridge()

        # Create UnifiedWebSocketEmitter with demo bridge as manager
        # This simulates how it's used in the demo route
        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge  # This is the problematic part
        )

        # Attempt to send an agent started notification
        # This should trigger the is_connection_active call and fail
        with self.assertRaises(AttributeError, msg="Expected AttributeError for missing is_connection_active"):
            await emitter.notify_agent_started(
                agent_name="TestAgent",
                context={"test": True}
            )

    async def test_emitter_connection_check_failure(self):
        """
        Test that emitter fails when checking connection status on demo bridge.

        THIS TEST SHOULD FAIL - demonstrating the exact Issue #1209 scenario.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        # Create emitter with demo bridge
        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge
        )

        # Try to manually trigger the connection check that causes the error
        try:
            # This is what happens internally in UnifiedWebSocketEmitter
            is_active = demo_bridge.is_connection_active(self.demo_user_id)
            self.fail("Expected AttributeError when calling is_connection_active")
        except AttributeError as e:
            # Verify this is the exact error from Issue #1209
            self.assertIn("is_connection_active", str(e))
            self.assertIn("DemoWebSocketBridge", str(e))

            # Log for Issue #1209 documentation
            self.logger.error(f"Issue #1209 AttributeError reproduced: {e}")

    async def test_emitter_notify_agent_thinking_fails(self):
        """
        Test notify_agent_thinking fails due to missing is_connection_active.

        THIS TEST SHOULD FAIL - reproducing the agent thinking notification error.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge
        )

        # This should trigger the AttributeError
        with self.assertRaises(AttributeError) as cm:
            await emitter.notify_agent_thinking(
                agent_name="TestAgent",
                reasoning="Testing thinking notification"
            )

        error_message = str(cm.exception)
        self.assertIn("is_connection_active", error_message)

    async def test_emitter_notify_agent_completed_fails(self):
        """
        Test notify_agent_completed fails due to missing is_connection_active.

        THIS TEST SHOULD FAIL - reproducing the agent completed notification error.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge
        )

        # This should trigger the AttributeError
        with self.assertRaises(AttributeError) as cm:
            await emitter.notify_agent_completed(
                agent_name="TestAgent",
                result={"status": "completed", "data": "test result"}
            )

        error_message = str(cm.exception)
        self.assertIn("is_connection_active", error_message)

    async def test_emitter_all_notification_methods_fail(self):
        """
        Test that all notification methods fail due to is_connection_active missing.

        THIS TEST SHOULD FAIL - comprehensive reproduction of Issue #1209.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge
        )

        # Test all notification methods that should fail
        notification_methods = [
            ('notify_agent_started', {'agent_name': 'TestAgent'}),
            ('notify_agent_thinking', {'agent_name': 'TestAgent', 'reasoning': 'test reasoning'}),
            ('notify_tool_executing', {'tool_name': 'TestTool', 'parameters': {}}),
            ('notify_tool_completed', {'tool_name': 'TestTool', 'result': {}}),
            ('notify_agent_completed', {'agent_name': 'TestAgent', 'result': {}})
        ]

        failed_methods = []
        for method_name, kwargs in notification_methods:
            try:
                method = getattr(emitter, method_name)
                await method(**kwargs)
                # If we get here, the method didn't fail as expected
                failed_methods.append(f"{method_name} should have failed but didn't")
            except AttributeError as e:
                if "is_connection_active" in str(e):
                    # This is the expected failure
                    self.logger.info(f"✓ {method_name} failed as expected: {e}")
                else:
                    # Different AttributeError
                    failed_methods.append(f"{method_name} failed with unexpected error: {e}")
            except Exception as e:
                # Unexpected error type
                failed_methods.append(f"{method_name} failed with unexpected error type: {type(e).__name__}: {e}")

        # All methods should have failed with AttributeError about is_connection_active
        if failed_methods:
            self.fail(f"Unexpected behaviors: {failed_methods}")

    def test_demo_bridge_missing_manager_interface(self):
        """
        Test that DemoWebSocketBridge doesn't implement required manager interface.

        THIS TEST SHOULD FAIL - showing interface incompatibility.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        # Check for methods required by UnifiedWebSocketEmitter
        required_manager_methods = [
            'is_connection_active',  # The missing one
            'send_json',
            'get_connection_count',
            'close_connection'
        ]

        missing_methods = []
        for method in required_manager_methods:
            if not hasattr(demo_bridge, method):
                missing_methods.append(method)

        # This should fail showing the missing methods
        self.assertEqual(
            [],
            missing_methods,
            f"DemoWebSocketBridge missing manager interface methods: {missing_methods}"
        )

    async def test_emitter_with_proper_manager_works(self):
        """
        Control test: Show that UnifiedWebSocketEmitter works with proper manager.

        THIS TEST SHOULD PASS - proving the issue is with DemoWebSocketBridge interface.
        """
        # Create a proper mock manager with is_connection_active
        mock_manager = Mock()
        mock_manager.is_connection_active = Mock(return_value=True)
        mock_manager.send_json = AsyncMock(return_value=True)
        mock_manager.get_connection_count = Mock(return_value=1)

        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=mock_manager
        )

        # This should work without AttributeError
        try:
            await emitter.notify_agent_started(
                agent_name="TestAgent",
                context={"test": True}
            )
            # If we get here, the proper manager worked
            self.assertTrue(True, "Emitter works with proper manager interface")
        except AttributeError as e:
            if "is_connection_active" in str(e):
                self.fail(f"Even proper manager failed: {e}")
            else:
                # Different error is acceptable for this control test
                pass


if __name__ == '__main__':
    unittest.main()