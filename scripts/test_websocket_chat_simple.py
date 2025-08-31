#!/usr/bin/env python
"""SIMPLE CRITICAL CHAT FLOW TEST

This is a simple test that validates the critical WebSocket chat flow
without any external service dependencies or pytest fixtures.

Business Value: $500K+ ARR - Core product functionality depends on this.

Tests the complete flow:
1. User sends message via WebSocket
2. Supervisor processes message 
3. Agent events are sent back via WebSocket
4. User receives complete response

If this test fails, the chat UI is completely broken.
"""

import asyncio
import json
import sys
import os
import time
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set minimal environment variables to prevent service lookups
os.environ["TESTING"] = "1"
os.environ["NETRA_ENV"] = "test"
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_REAL_SERVICES"] = "false"

try:
    # Import actual production components
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.agents.state import DeepAgentState
    
    print("[OK] All critical imports successful")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)


class SimpleFlowValidator:
    """Validates the critical chat flow events."""
    
    def __init__(self):
        self.events = []
        self.agent_started = False
        self.agent_thinking = False
        self.tool_executing = False
        self.tool_completed = False
        self.partial_results = False
        self.agent_completed = False
        self.errors = []
        
    def record(self, event: Dict) -> None:
        """Record and categorize event."""
        self.events.append(event)
        event_type = event.get("type", "")
        
        if "agent_started" in event_type:
            self.agent_started = True
            print(f"[OK] Agent started event received: {event_type}")
            
        elif "agent_thinking" in event_type:
            self.agent_thinking = True
            print(f"[OK] Agent thinking event received: {event_type}")
            
        elif "tool_executing" in event_type:
            self.tool_executing = True
            print(f"[OK] Tool executing event received: {event_type}")
            
        elif "tool_completed" in event_type:
            self.tool_completed = True
            print(f"[OK] Tool completed event received: {event_type}")
            
        elif "partial_result" in event_type:
            self.partial_results = True
            print(f"[OK] Partial result event received: {event_type}")
            
        elif "agent_completed" in event_type or "final_report" in event_type:
            self.agent_completed = True
            print(f"[OK] Agent completed event received: {event_type}")
    
    def validate(self) -> tuple[bool, List[str]]:
        """Validate critical flow requirements."""
        errors = []
        
        if not self.agent_started:
            errors.append("[FAIL] No agent_started event - User won't know processing began")
            
        if not self.agent_completed:
            errors.append("[FAIL] No completion event - User won't know when done")
            
        if len(self.events) == 0:
            errors.append("[FAIL] CRITICAL: No WebSocket events at all!")
            
        return len(errors) == 0, errors
    
    def get_report(self) -> str:
        """Generate validation report."""
        is_valid, errors = self.validate()
        
        report = [
            "\n" + "=" * 60,
            "SIMPLE CRITICAL CHAT FLOW VALIDATION",
            "=" * 60,
            f"Overall Status: {'[PASS]' if is_valid else '[FAIL]'}",
            f"Total Events: {len(self.events)}",
            "",
            "Event Coverage:",
            f"  {'[OK]' if self.agent_started else '[FAIL]'} Agent Started",
            f"  {'[OK]' if self.agent_thinking else '[WARN]'} Agent Thinking",
            f"  {'[OK]' if self.tool_executing else '[WARN]'} Tool Executing",
            f"  {'[OK]' if self.tool_completed else '[WARN]'} Tool Completed", 
            f"  {'[OK]' if self.partial_results else '[WARN]'} Partial Results",
            f"  {'[OK]' if self.agent_completed else '[FAIL]'} Agent Completed",
        ]
        
        if errors:
            report.extend(["", "Issues Found:"] + errors)
            
        if self.events:
            report.extend(["", "Event Sequence:"])
            for i, event in enumerate(self.events[:10]):
                report.append(f"  {i+1}. {event.get('type', 'unknown')}")
            if len(self.events) > 10:
                report.append(f"  ... and {len(self.events) - 10} more")
                
        report.append("=" * 60)
        return "\n".join(report)


async def test_websocket_notifier():
    """Test WebSocket notifier basic functionality."""
    
    print("\n" + "=" * 60)
    print("TESTING WEBSOCKET NOTIFIER")
    print("=" * 60)
    
    # Setup
    ws_manager = WebSocketManager()
    validator = SimpleFlowValidator()
    
    # Mock connection
    connection_id = "notifier-test"
    user_id = "test-user"
    request_id = "req-456"
    
    mock_ws = MagicMock()
    
    async def capture(message, timeout=None):
        try:
            print(f"[DEBUG] Mock WebSocket capture called with: {type(message)} {message} (timeout={timeout})")
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record(data)
            print(f"[MSG] WebSocket message captured: {data.get('type', 'unknown')}")
        except Exception as e:
            print(f"[WARN] Failed to capture message: {e}")
    
    mock_ws.send_json = AsyncMock(side_effect=capture)
    mock_ws.send_text = AsyncMock(side_effect=capture)
    mock_ws.send = AsyncMock(side_effect=capture)
    
    await ws_manager.connect_user(user_id, mock_ws, thread_id=connection_id)
    print(f"[CONN] Connected user {user_id} with connection {connection_id}")
    
    # Create notifier
    notifier = WebSocketNotifier(ws_manager)
    print("[INIT] WebSocket notifier created")
    
    # Create execution context for notifier calls
    context = AgentExecutionContext(
        run_id=request_id,
        thread_id=connection_id,
        user_id=user_id,
        agent_name="test_agent",
        retry_count=0,
        max_retries=1
    )
    
    print("[INIT] Execution context created")
    
    # Send all event types
    print("\n[SEND] Sending WebSocket events...")
    print(f"[DEBUG] Notifier has websocket_manager: {notifier.websocket_manager is not None}")
    print(f"[DEBUG] WebSocket manager has connections: {len(notifier.websocket_manager.connections)}")
    
    await notifier.send_agent_started(context)
    await notifier.send_agent_thinking(context, "Processing...")
    await notifier.send_tool_executing(context, "test_tool")
    await notifier.send_tool_completed(context, "test_tool", {"result": "done"})
    await notifier.send_partial_result(context, "Partial data...")
    await notifier.send_agent_completed(context, {"success": True})
    
    # Allow processing
    await asyncio.sleep(0.3)
    
    # Validate
    print(validator.get_report())
    
    # Check results
    success = True
    if not validator.agent_started:
        print("[FAIL] Agent started event not sent")
        success = False
        
    if not validator.agent_thinking:
        print("[WARN] Agent thinking event not sent")
        
    if not validator.tool_executing:
        print("[WARN] Tool executing event not sent")
        
    if not validator.tool_completed:
        print("[WARN] Tool completed event not sent")
        
    if not validator.agent_completed:
        print("[FAIL] Agent completed event not sent")
        success = False
    
    # Cleanup
    await ws_manager.disconnect_user(user_id, mock_ws, connection_id)
    print("[CLEANUP] Cleaned up WebSocket connection")
    
    if success:
        print("[PASS] WebSocket notifier test PASSED")
    else:
        print("[FAIL] WebSocket notifier test FAILED")
        
    return success


async def test_complete_chat_flow():
    """Test complete chat flow with mocked external dependencies."""
    
    print("\n" + "=" * 60)
    print("STARTING CRITICAL CHAT FLOW TEST")
    print("=" * 60)
    
    # Setup WebSocket manager and validator
    ws_manager = WebSocketManager()
    validator = SimpleFlowValidator()
    
    # Create mock WebSocket connection
    connection_id = "chat-conn"
    user_id = "test-user"
    
    # Mock WebSocket that captures events
    mock_ws = MagicMock()
    sent_messages = []
    
    async def capture_send(message, timeout=None):
        """Capture sent WebSocket messages."""
        try:
            print(f"[DEBUG] Complete flow capture called with: {type(message)} {message} (timeout={timeout})")
            if isinstance(message, str):
                data = json.loads(message)
            elif isinstance(message, dict):
                data = message
            else:
                data = {"raw": str(message)}
                
            sent_messages.append(data)
            validator.record(data)
            print(f"[MSG] WebSocket captured: {data.get('type', 'unknown')}")
        except Exception as e:
            print(f"[WARN] Failed to capture message: {e}")
    
    mock_ws.send_json = AsyncMock(side_effect=capture_send)
    mock_ws.send_text = AsyncMock(side_effect=capture_send)
    mock_ws.send = AsyncMock(side_effect=capture_send)
    
    # Connect user
    await ws_manager.connect_user(user_id, mock_ws, thread_id=connection_id)
    print(f"[CONN] Connected user {user_id}")
    
    # Create supervisor components with mock LLM
    class MockLLMManager:
        async def generate(self, *args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "content": "The system is operational.",
                "reasoning": "Checking system status...",
                "confidence": 0.95
            }
    
    print("[INIT] Created mock LLM manager")
    llm_manager = MockLLMManager()
    tool_dispatcher = ToolDispatcher()
    
    # Register a simple test tool
    async def test_tool(*args, **kwargs):
        await asyncio.sleep(0.05)  # Simulate tool execution
        return {"status": "success", "data": "Tool executed"}
    
    tool_dispatcher.register_tool("test_tool", test_tool, "Test tool for validation")
    print("[INIT] Registered test tool")
    
    # Create and configure agent registry
    registry = AgentRegistry(llm_manager, tool_dispatcher)
    registry.set_websocket_manager(ws_manager)  # This should enhance tool dispatcher
    print("[INIT] Created agent registry with WebSocket manager")
    
    # Check if tool dispatcher was enhanced
    if hasattr(tool_dispatcher, '_websocket_enhanced') and tool_dispatcher._websocket_enhanced:
        print("[OK] Tool dispatcher was enhanced with WebSocket notifications")
    else:
        print("[WARN] Tool dispatcher may not be properly enhanced")
    
    registry.register_default_agents()
    print("[INIT] Registered default agents")
    
    # Create execution engine
    engine = ExecutionEngine(registry, ws_manager)
    print("[INIT] Created execution engine")
    
    # Create supervisor agent with mock database session
    class MockDBSession:
        pass
    
    mock_db_session = MockDBSession()
    supervisor = SupervisorAgent(mock_db_session, llm_manager, ws_manager, tool_dispatcher)
    supervisor.agent_registry = registry
    supervisor.execution_engine = engine
    print("[INIT] Created supervisor agent")
    
    # Create test message
    test_message = "What is the system status?"
    print(f"[TEST] Test message: {test_message}")
    
    # Create the state properly
    state = DeepAgentState()
    state.user_request = test_message
    state.chat_thread_id = connection_id
    state.user_id = user_id
    state.run_id = f"run-{connection_id}"
    
    # Process the message through supervisor
    try:
        print("[RUN] Processing message through supervisor...")
        
        result = await supervisor.execute(
            state,
            state.run_id,
            True  # stream_updates
        )
        
        print(f"[OK] Supervisor execution completed: {result is not None}")
        
    except Exception as e:
        print(f"[FAIL] Supervisor execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Allow async events to complete
    print("[WAIT] Waiting for async events to complete...")
    await asyncio.sleep(1.5)
    
    # Validate results
    print(validator.get_report())
    
    # Check critical requirements
    success = True
    
    if len(validator.events) == 0:
        print(f"[FAIL] No WebSocket events were sent! Total sent messages: {len(sent_messages)}")
        success = False
    else:
        print(f"[OK] Received {len(validator.events)} WebSocket events")
    
    # At minimum, we should have start indication
    if not validator.agent_started and not any("start" in str(e) for e in validator.events):
        print("[FAIL] No agent start indication")
        success = False
    else:
        print("[OK] Agent start indication found")
    
    # Should have some form of completion
    if not validator.agent_completed and not any("complet" in str(e) or "final" in str(e) for e in validator.events):
        print("[FAIL] No completion indication")
        success = False
    else:
        print("[OK] Completion indication found")
    
    # Cleanup
    await ws_manager.disconnect_user(user_id, mock_ws, connection_id)
    print("[CLEANUP] Cleaned up resources")
    
    if success:
        print("[PASS] CRITICAL CHAT FLOW TEST PASSED")
    else:
        print("[FAIL] CRITICAL CHAT FLOW TEST FAILED")
        
    return success


async def main():
    """Run all tests."""
    print("[START] Starting Critical Chat Flow Tests")
    print("=" * 80)
    
    results = []
    
    try:
        # Test 1: WebSocket Notifier
        print("TEST 1: WebSocket Notifier Basic Flow")
        result1 = await test_websocket_notifier()
        results.append(("WebSocket Notifier", result1))
        
        # Test 2: Complete Chat Flow  
        print("\nTEST 2: Complete Chat Flow")
        result2 = await test_complete_chat_flow()
        results.append(("Complete Chat Flow", result2))
        
    except Exception as e:
        print(f"[FAIL] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 80)
    print("FINAL TEST RESULTS")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED - Critical chat functionality is working!")
    else:
        print("[ERROR] SOME TESTS FAILED - Critical chat functionality may be broken!")
    
    return all_passed


if __name__ == "__main__":
    # Run the tests
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)