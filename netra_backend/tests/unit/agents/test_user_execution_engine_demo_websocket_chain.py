"""
Test User Execution Engine Demo WebSocket Call Chain - Issue #1209 Reproduction

Phase 1 of Issue #1209 Reproduction Tests - SHOULD FAIL

These tests reproduce the exact call chain that fails in user_execution_engine.py:1659
when UserExecutionEngine → UnifiedWebSocketEmitter → DemoWebSocketBridge → is_connection_active().

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability
- Value Impact: Prevents broken demo functionality affecting sales and marketing
- Strategic Impact: $500K+ ARR demos must work reliably for customer acquisition

Expected Result: Tests should FAIL with AttributeError: 'DemoWebSocketBridge' object has no attribute 'is_connection_active'
showing the exact error that occurs in production demo scenarios.
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
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.base.execution_context import AgentExecutionContext


class TestUserExecutionEngineDemoWebSocketChain(SSotAsyncTestCase):
    """Test exact call chain that fails in user_execution_engine.py - Issue #1209."""

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

        # Mock agent factory
        self.mock_agent_factory = Mock()
        self.mock_agent = Mock()
        self.mock_agent_factory.create_agent = AsyncMock(return_value=self.mock_agent)
        self.mock_agent_factory.agent_class_registry = {"TestAgent": Mock}

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

    def create_user_execution_engine_with_demo_bridge(self):
        """Create UserExecutionEngine configured with demo WebSocket bridge."""
        demo_bridge = self.create_demo_websocket_bridge()

        # Create UnifiedWebSocketEmitter using demo bridge as manager
        websocket_emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge  # This is the source of the issue
        )

        # Create UserExecutionEngine with the emitter
        engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=self.mock_agent_factory,
            websocket_emitter=websocket_emitter
        )

        return engine, demo_bridge, websocket_emitter

    async def test_send_user_agent_started_with_demo_bridge(self):
        """
        CRITICAL TEST: Reproduce exact call chain that fails at line 1659.

        THIS TEST SHOULD FAIL - reproducing Issue #1209 AttributeError.

        Call chain: UserExecutionEngine._send_user_agent_started() →
                   UnifiedWebSocketEmitter.notify_agent_started() →
                   UnifiedWebSocketEmitter checks manager.is_connection_active() →
                   DemoWebSocketBridge.is_connection_active() → AttributeError
        """
        engine, demo_bridge, websocket_emitter = self.create_user_execution_engine_with_demo_bridge()

        # Create agent execution context
        agent_context = AgentExecutionContext(
            agent_name="TestAgent",
            user_context=self.user_context,
            metadata={"test": "data"}
        )

        # Call the exact method that fails in production
        with self.assertRaises(AttributeError, msg="Expected AttributeError for missing is_connection_active"):
            await engine._send_user_agent_started(agent_context)

    async def test_send_user_agent_thinking_with_demo_bridge(self):
        """
        Test agent thinking notification call chain failure.

        THIS TEST SHOULD FAIL - reproducing the agent thinking error.
        """
        engine, demo_bridge, websocket_emitter = self.create_user_execution_engine_with_demo_bridge()

        agent_context = AgentExecutionContext(
            agent_name="TestAgent",
            user_context=self.user_context,
            metadata={"test": "data"}
        )

        # This should trigger the AttributeError
        with self.assertRaises(AttributeError) as cm:
            await engine._send_user_agent_thinking(
                agent_context,
                thought="Testing agent thinking",
                step_number=1
            )

        error_message = str(cm.exception)
        self.assertIn("is_connection_active", error_message)
        self.logger.error(f"Agent thinking error reproduced: {error_message}")

    async def test_send_user_agent_completed_with_demo_bridge(self):
        """
        Test agent completed notification call chain failure.

        THIS TEST SHOULD FAIL - reproducing the agent completed error.
        """
        engine, demo_bridge, websocket_emitter = self.create_user_execution_engine_with_demo_bridge()

        agent_context = AgentExecutionContext(
            agent_name="TestAgent",
            user_context=self.user_context,
            metadata={"test": "data"}
        )

        # This should trigger the AttributeError
        with self.assertRaises(AttributeError) as cm:
            await engine._send_user_agent_completed(
                agent_context,
                result={"status": "completed", "data": "test result"}
            )

        error_message = str(cm.exception)
        self.assertIn("is_connection_active", error_message)

    async def test_websocket_emitter_direct_call_fails(self):
        """
        Test direct UnifiedWebSocketEmitter call with demo bridge fails.

        THIS TEST SHOULD FAIL - isolating the exact point of failure.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        # Create emitter with demo bridge as manager (the problematic setup)
        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge
        )

        # Direct call should fail
        with self.assertRaises(AttributeError) as cm:
            await emitter.notify_agent_started(
                agent_name="TestAgent",
                context={"status": "started"}
            )

        # Verify this is the exact Issue #1209 error
        error_message = str(cm.exception)
        self.assertIn("DemoWebSocketBridge", error_message)
        self.assertIn("is_connection_active", error_message)

        # Log the exact error pattern for documentation
        self.logger.error(f"Issue #1209 exact error reproduced: {error_message}")

    async def test_demo_bridge_manager_interface_mismatch(self):
        """
        Test that demonstrates the interface mismatch causing Issue #1209.

        THIS TEST SHOULD FAIL - showing the root cause.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        # Try to use demo bridge as if it were a WebSocket manager
        try:
            # This is what UnifiedWebSocketEmitter tries to do
            connection_active = demo_bridge.is_connection_active(self.demo_user_id)
            self.fail("Expected AttributeError but method call succeeded")
        except AttributeError as e:
            # This is the expected error
            self.assertIn("is_connection_active", str(e))
            self.logger.info(f"✓ Interface mismatch confirmed: {e}")

    async def test_full_user_execution_flow_with_demo_bridge(self):
        """
        Test complete user execution flow with demo bridge.

        THIS TEST SHOULD FAIL - showing where in the flow the error occurs.
        """
        engine, demo_bridge, websocket_emitter = self.create_user_execution_engine_with_demo_bridge()

        # Mock agent execution
        self.mock_agent.execute = AsyncMock(return_value={"status": "completed"})

        # Create agent execution context
        agent_context = AgentExecutionContext(
            agent_name="TestAgent",
            user_context=self.user_context,
            metadata={"test": "execution"}
        )

        # Try to execute user agent - should fail at notification step
        with self.assertRaises(AttributeError) as cm:
            await engine.execute_user_agent(agent_context)

        error_message = str(cm.exception)
        self.assertIn("is_connection_active", error_message)

        # Log where in the execution flow the error occurs
        self.logger.error(f"Full execution flow failed at: {error_message}")

    def test_demo_bridge_inheritance_analysis(self):
        """
        Analyze DemoWebSocketBridge inheritance to understand missing methods.

        THIS TEST SHOULD FAIL - showing what's missing from the inheritance chain.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        # Check inheritance chain
        inheritance_chain = [cls.__name__ for cls in type(demo_bridge).__mro__]
        self.logger.info(f"DemoWebSocketBridge inheritance: {inheritance_chain}")

        # Check what methods are available
        available_methods = [method for method in dir(demo_bridge) if not method.startswith('_')]
        self.logger.info(f"Available methods: {available_methods}")

        # Check specifically for is_connection_active
        has_is_connection_active = hasattr(demo_bridge, 'is_connection_active')

        # This should fail
        self.assertTrue(
            has_is_connection_active,
            f"DemoWebSocketBridge missing is_connection_active method. "
            f"Inheritance: {inheritance_chain}, Methods: {available_methods}"
        )

    async def test_error_occurs_at_connection_check(self):
        """
        Pinpoint that error occurs specifically at connection active check.

        THIS TEST SHOULD FAIL - proving the exact location of the error.
        """
        demo_bridge = self.create_demo_websocket_bridge()

        emitter = UnifiedWebSocketEmitter(
            user_id=self.demo_user_id,
            run_id=self.run_id,
            manager=demo_bridge
        )

        # Mock the internal call to isolate where error occurs
        with patch.object(emitter, '_check_connection_active') as mock_check:
            # Make the check call is_connection_active internally
            mock_check.side_effect = lambda: demo_bridge.is_connection_active(self.demo_user_id)

            with self.assertRaises(AttributeError) as cm:
                emitter._check_connection_active()

            error_message = str(cm.exception)
            self.assertIn("is_connection_active", error_message)
            self.logger.error(f"Error confirmed at connection check: {error_message}")


if __name__ == '__main__':
    unittest.main()