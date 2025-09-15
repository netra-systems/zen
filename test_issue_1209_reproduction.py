#!/usr/bin/env python3
"""
Simple test to reproduce Issue #1209 - DemoWebSocketBridge missing is_connection_active method
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import Mock, AsyncMock
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


def test_demo_websocket_bridge_missing_method():
    """Reproduce the exact AttributeError from Issue #1209."""

    print("Reproducing Issue #1209...")

    # Create mock user context
    mock_user_context = Mock(spec=UserExecutionContext)
    mock_user_context.user_id = "demo_user_001"
    mock_user_context.thread_id = "demo_thread_001"
    mock_user_context.run_id = "demo_run_001"
    mock_user_context.request_id = "demo_req_001"
    mock_user_context.websocket_client_id = "demo_conn_001"

    # Create a mock WebSocket adapter (simulates the inner class in demo_websocket.py)
    mock_websocket_adapter = Mock()
    mock_websocket_adapter.send_event = AsyncMock()
    mock_websocket_adapter.notify_agent_started = AsyncMock()
    mock_websocket_adapter.notify_agent_thinking = AsyncMock()
    mock_websocket_adapter.notify_tool_executing = AsyncMock()
    mock_websocket_adapter.notify_tool_completed = AsyncMock()
    mock_websocket_adapter.notify_agent_completed = AsyncMock()
    mock_websocket_adapter.notify_agent_error = AsyncMock()

    # Import and instantiate the problematic DemoWebSocketBridge
    # We need to import it from where it's defined (inside the function)
    from netra_backend.app.routes.demo_websocket import execute_real_agent_workflow
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

    # Create a replica of the DemoWebSocketBridge class that's defined inside execute_real_agent_workflow
    class TestDemoWebSocketBridge(AgentWebSocketBridge):
        """Replica of DemoWebSocketBridge to test the missing method issue"""

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

        # NOTE: is_connection_active method is INTENTIONALLY MISSING to reproduce the issue

    # Create the bridge instance
    bridge = TestDemoWebSocketBridge(mock_websocket_adapter, mock_user_context)

    # Create a UnifiedWebSocketEmitter that will try to call is_connection_active
    emitter = UnifiedWebSocketEmitter(
        manager=bridge,
        user_id=mock_user_context.user_id,
        context=mock_user_context
    )

    # The critical test: Try to call a method that uses is_connection_active
    try:
        # This should fail because the bridge doesn't have is_connection_active
        # The UnifiedWebSocketEmitter calls manager.is_connection_active(user_id)
        result = bridge.is_connection_active(mock_user_context.user_id)
        print(f"UNEXPECTED: Method call succeeded with result: {result}")
        return False
    except AttributeError as e:
        error_msg = str(e)
        if "is_connection_active" in error_msg:
            print(f"ISSUE REPRODUCED: {error_msg}")
            return True
        else:
            print(f"WRONG ERROR: {error_msg}")
            return False
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        return False


if __name__ == "__main__":
    success = test_demo_websocket_bridge_missing_method()
    if success:
        print("\nIssue #1209 successfully reproduced!")
        print("Next step: Add is_connection_active method to DemoWebSocketBridge")
    else:
        print("\nFailed to reproduce the issue")

    sys.exit(0 if success else 1)