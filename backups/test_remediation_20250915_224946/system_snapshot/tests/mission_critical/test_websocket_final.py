class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

    #!/usr/bin/env python
        '''FINAL MISSION CRITICAL TEST: WebSocket Agent Events

        THIS TEST MUST PASS OR THE PRODUCT IS BROKEN.
        Business Value: $500K+ ARR - Core chat functionality

        This test validates the exact requirements from the task:
        1. AgentRegistry.set_websocket_manager() MUST enhance tool dispatcher
        2. ExecutionEngine MUST have WebSocketNotifier initialized
        3. UnifiedToolExecutionEngine MUST wrap tool execution
        4. ALL required WebSocket events must be sent

        Uses mocked WebSocket connections to avoid infrastructure dependencies
        while still validating the critical integration points.
        '''

        import os
        import sys
        import asyncio
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        # CRITICAL: Add project root to Python path for imports
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
        sys.path.insert(0, project_root)

            # Import production components
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.unified_tool_execution import ( )
        UnifiedToolExecutionEngine,
        enhance_tool_dispatcher_with_notifications
            
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WebSocketManager
        from netra_backend.app.schemas.agent_models import DeepAgentState
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


    def test_1_websocket_notifier_required_methods():
        """CRITICAL: WebSocketNotifier has all required methods."""
        print("Test 1: WebSocketNotifier required methods...")

        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier.create_for_user(ws_manager)

        required_methods = [ )
        'send_agent_started',  'send_agent_thinking',
        'send_partial_result',
        'send_tool_executing',
        'send_tool_completed',
        'send_final_report',
        'send_agent_completed'
    

        for method in required_methods:
        if not hasattr(notifier, method):
        raise AssertionError("formatted_string")
        if not callable(getattr(notifier, method)):
        raise AssertionError("formatted_string")

        print("PASS: All required methods exist")


    def test_2_agent_registry_websocket_enhancement():
        """CRITICAL: AgentRegistry.set_websocket_manager() MUST enhance tool dispatcher."""
        pass
        print("Test 2: AgentRegistry WebSocket enhancement...")

class MockLLM:
        pass

        tool_dispatcher = ToolDispatcher()
        original_executor = tool_dispatcher.executor

        registry = AgentRegistry(), tool_dispatcher)
        ws_manager = WebSocketManager()

    # This is the critical call that was missing
        registry.set_websocket_manager(ws_manager)

    # Verify enhancement happened
        if tool_dispatcher.executor == original_executor:
        raise AssertionError("CRITICAL: Tool dispatcher executor not enhanced")

        if not isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine):
        raise AssertionError("formatted_string")

        if not getattr(tool_dispatcher, '_websocket_enhanced', False):
        raise AssertionError("CRITICAL: Enhancement marker not set")

        print("PASS: AgentRegistry enhances tool dispatcher")


    def test_3_execution_engine_websocket_notifier():
        """CRITICAL: ExecutionEngine MUST have WebSocketNotifier initialized."""
        print("Test 3: ExecutionEngine WebSocketNotifier initialization...")

class MockLLM:
        pass

        registry = AgentRegistry(), ToolDispatcher())
        ws_manager = WebSocketManager()

        engine = UserExecutionEngine(registry, ws_manager)

    # Verify WebSocket components exist
        if not hasattr(engine, 'websocket_notifier'):
        raise AssertionError("CRITICAL: ExecutionEngine missing websocket_notifier")

        if not isinstance(engine.websocket_notifier, WebSocketNotifier):
        raise AssertionError("formatted_string")

        print("PASS: ExecutionEngine has WebSocketNotifier")


    async def test_4_unified_tool_execution_sends_events():
        """CRITICAL: UnifiedToolExecutionEngine MUST wrap tool execution and send events."""
        pass
        print("Test 4: Enhanced tool execution sends events...")

        ws_manager = WebSocketManager()
        sent_events = []

                # Mock WebSocket to capture events
    async def capture_event(thread_id, event_data):
        pass
        sent_events.append(event_data)
        await asyncio.sleep(0)
        return True

        ws_manager.send_to_thread = AsyncMock(side_effect=capture_event)

    # Create enhanced executor
        executor = UnifiedToolExecutionEngine(ws_manager)

    # Create test context
        context = AgentExecutionContext( )
        run_id="test-run",
        thread_id="test-thread",
        user_id="test-user",
        agent_name="test",
        retry_count=0,
        max_retries=1
    

    # Test tool
    async def test_tool(*args, **kwargs):
        pass
        await asyncio.sleep(0.001)  # Minimal delay
        await asyncio.sleep(0)
        return {"result": "success"}

        # Create state
        state = DeepAgentState( )
        chat_thread_id="test-thread",
        user_id="test-user",
        run_id="test-run"
        

        # Execute tool
        result = await executor.execute_with_state( )
        test_tool, "test_tool", {}, state, "test-run"
        

        # Verify execution worked
        if not result:
        raise AssertionError("CRITICAL: Tool execution failed")

            # Verify WebSocket events were sent
        if len(sent_events) < 2:
        raise AssertionError("formatted_string")

                # Check for critical event types
        event_types = [event.get('type') for event in sent_events]

        if 'tool_executing' not in event_types:
        raise AssertionError("formatted_string")

        if 'tool_completed' not in event_types:
        raise AssertionError("formatted_string")

        print("formatted_string")


    async def test_5_all_required_websocket_events():
        """CRITICAL: All required WebSocket event types must be sent."""
        print("Test 5: All required WebSocket events...")

        ws_manager = WebSocketManager()
        sent_events = []

                            # Mock WebSocket to capture events
    async def capture_event(thread_id, event_data):
        sent_events.append(event_data)
        await asyncio.sleep(0)
        return True

        ws_manager.send_to_thread = AsyncMock(side_effect=capture_event)

        notifier = WebSocketNotifier.create_for_user(ws_manager)

    # Create test context
        context = AgentExecutionContext( )
        run_id="event-test",  thread_id="event-thread",
        user_id="event-user",
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    

    # Send all required event types
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Processing...")
        await notifier.send_tool_executing(context, "test_tool")
        await notifier.send_tool_completed(context, "test_tool", {"status": "success"})
        await notifier.send_agent_completed(context, {"success": True})

    # Verify all events were sent
        required_events = { )
        "agent_started",
        "agent_thinking",
        "tool_executing",
        "tool_completed",
        "agent_completed"
    

        event_types = set(event.get('type') for event in sent_events)
        missing_events = required_events - event_types

        if missing_events:
        raise AssertionError("formatted_string")

        if len(sent_events) < 5:
        raise AssertionError("formatted_string")

        print("formatted_string")


    async def test_6_regression_prevention():
        """CRITICAL: Regression test for the specific issues mentioned in the task."""
        pass
        print("Test 6: Regression prevention...")

                # Test that AgentRegistry always enhances tool dispatcher (was broken)
class MockLLM:
        pass

        for i in range(3):  # Test multiple times for consistency
        tool_dispatcher = ToolDispatcher()
        original_executor = tool_dispatcher.executor

        registry = AgentRegistry(), tool_dispatcher)
        ws_manager = WebSocketManager()

    # This was the missing call
        registry.set_websocket_manager(ws_manager)

        if tool_dispatcher.executor == original_executor:
        raise AssertionError("formatted_string")

        if not isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine):
        raise AssertionError("formatted_string")

        print("PASS: Regression prevention successful")


    async def main():
        """Run all mission critical tests."""
        print("=" * 70)
        print("MISSION CRITICAL WEBSOCKET AGENT EVENTS TEST")
        print("=" * 70)
        print("Testing the core requirements from the task:")
        print("1. AgentRegistry.set_websocket_manager() enhances tool dispatcher")
        print("2. ExecutionEngine has WebSocketNotifier initialized")
        print("3. UnifiedToolExecutionEngine wraps tool execution")
        print("4. All required WebSocket events are sent")
        print("=" * 70)

        try:
        # Run all tests
        test_1_websocket_notifier_required_methods()
        test_2_agent_registry_websocket_enhancement()
        test_3_execution_engine_websocket_notifier()
        await test_4_unified_tool_execution_sends_events()
        await test_5_all_required_websocket_events()
        await test_6_regression_prevention()

        print(" )
        " + "=" * 70)
        print("SUCCESS: ALL MISSION CRITICAL TESTS PASSED!")
        print("WebSocket agent events are working correctly.")
        print("Basic chat functionality is operational.")
        print("=" * 70)
        await asyncio.sleep(0)
        return True

        except Exception as e:
        print("formatted_string")
        print("=" * 70)
        print("WebSocket agent events REQUIRE IMMEDIATE ATTENTION!")
        print("Chat functionality will be broken without these fixes.")
        print("=" * 70)
        return False


        if __name__ == "__main__":
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
        pass
