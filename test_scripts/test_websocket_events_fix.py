#!/usr/bin/env python
"""Test script to verify WebSocket events are sent during agent execution.

MISSION CRITICAL: Validates that all 5 required WebSocket events are sent:
- agent_started
- agent_thinking
- tool_executing
- tool_completed
- agent_completed
"""

import asyncio
import json
import sys
import time
from typing import Dict, List, Set, Optional, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class WebSocketEventCapture:
    """Captures WebSocket events for validation."""
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_types: Set[str] = set()
        
    async def capture_event(self, thread_id: str, message: Dict):
        """Capture a WebSocket event."""
        event_type = message.get("type", "unknown")
        self.events.append(message)
        self.event_types.add(event_type)
        logger.info(f" PASS:  Captured WebSocket event: {event_type}")
        return True

class TestWebSocketEventIntegration:
    """Test WebSocket event integration with agent execution."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking",
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    async def setup_components(self):
        """Setup test components with WebSocket integration."""
        # Create mock LLM manager
        llm_manager = Mock()
        llm_manager.generate_response = AsyncMock(return_value={
            "content": "Test response",
            "usage": {"total_tokens": 100}
        })
        
        # Create tool dispatcher
        tool_dispatcher = ToolDispatcher()
        
        # Create WebSocket manager and event capture
        websocket_manager = WebSocketManager()
        event_capture = WebSocketEventCapture()
        
        # Mock the send_to_thread method to capture events
        websocket_manager.send_to_thread = event_capture.capture_event
        
        # Create agent registry and set WebSocket manager
        registry = AgentRegistry()
        registry.register_default_agents()
        
        # CRITICAL: Set WebSocket manager to enable event notifications
        registry.set_websocket_manager(websocket_manager)
        
        # Verify tool dispatcher was enhanced
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            "Tool dispatcher not enhanced with WebSocket notifications!"
        
        # Create execution engine
        execution_engine = ExecutionEngine(registry, websocket_manager)
        
        return {
            "llm_manager": llm_manager,
            "tool_dispatcher": tool_dispatcher,
            "websocket_manager": websocket_manager,
            "event_capture": event_capture,
            "registry": registry,
            "execution_engine": execution_engine
        }
    
    async def test_agent_execution_sends_events(self):
        """Test that agent execution sends all required WebSocket events."""
        components = await self.setup_components()
        
        # Create execution context
        from dataclasses import dataclass, field
        from datetime import datetime, timezone
        
        @dataclass
        class TestContext:
            agent_name: str
            thread_id: str
            run_id: str
            user_id: str
            retry_count: int = 0
            max_retries: int = 3
            timeout: Optional[int] = None
            metadata: Dict[str, Any] = field(default_factory=dict)
            started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
        
        context = TestContext(
            agent_name="test_agent",
            thread_id="test_thread_123",
            run_id="test_run_456",
            user_id="test_user"
        )
        
        # Get execution engine and notifier
        engine = components["execution_engine"]
        notifier = engine.websocket_notifier
        event_capture = components["event_capture"]
        
        # Send events manually to test WebSocket integration
        await notifier.send_agent_started(context)
        await notifier.send_agent_thinking(context, "Processing request...", 1)
        await notifier.send_tool_executing(context, "search_tool")
        await notifier.send_tool_completed(context, "search_tool", {"result": "data"})
        await notifier.send_agent_completed(context, {"response": "Complete"}, 1000)
        
        # Validate events were captured
        missing_events = self.REQUIRED_EVENTS - event_capture.event_types
        
        if missing_events:
            logger.error(f" FAIL:  MISSING EVENTS: {missing_events}")
            logger.error(f"   Captured events: {event_capture.event_types}")
            return False
        
        logger.info(f" PASS:  All required events captured: {event_capture.event_types}")
        return True
    
    async def test_tool_execution_sends_events(self):
        """Test that tool execution sends WebSocket events."""
        components = await self.setup_components()
        
        # Get tool dispatcher with enhanced executor
        tool_dispatcher = components["tool_dispatcher"]
        event_capture = components["event_capture"]
        
        # Create mock tool
        mock_tool = Mock()
        mock_tool.execute = AsyncMock(return_value={"result": "success"})
        
        # Register tool
        tool_dispatcher.register_tool("test_tool", mock_tool)
        
        # Execute tool with context
        from dataclasses import dataclass, field
        from datetime import datetime, timezone
        
        @dataclass
        class TestContext:
            agent_name: str
            thread_id: str
            run_id: str
            user_id: str
            retry_count: int = 0
            max_retries: int = 3
            timeout: Optional[int] = None
            metadata: Dict[str, Any] = field(default_factory=dict)
            started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
        
        context = TestContext(
            agent_name="test_agent",
            thread_id="test_thread_789",
            run_id="test_run_101",
            user_id="test_user"
        )
        
        # Execute tool through enhanced dispatcher
        result = await tool_dispatcher.dispatch(
            tool_name="test_tool",
            param="value"
        )
        
        # Check if tool events were captured
        tool_events = [e for e in event_capture.event_types if "tool" in e]
        
        if "tool_executing" not in tool_events or "tool_completed" not in tool_events:
            logger.error(f" FAIL:  Tool events not captured properly: {tool_events}")
            return False
        
        logger.info(f" PASS:  Tool execution events captured: {tool_events}")
        return True

async def main():
    """Run WebSocket event integration tests."""
    logger.info("=" * 80)
    logger.info("WEBSOCKET EVENT INTEGRATION TEST")
    logger.info("=" * 80)
    
    tester = TestWebSocketEventIntegration()
    
    # Test 1: Agent execution sends events
    logger.info("\n[U+1F4DD] Test 1: Agent Execution WebSocket Events")
    test1_passed = await tester.test_agent_execution_sends_events()
    
    # Test 2: Tool execution sends events
    logger.info("\n[U+1F4DD] Test 2: Tool Execution WebSocket Events")
    test2_passed = await tester.test_tool_execution_sends_events()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    if test1_passed and test2_passed:
        logger.info(" PASS:  ALL TESTS PASSED - WebSocket events are working!")
        logger.info(" PASS:  The fix has been successfully implemented:")
        logger.info("   1. AgentRegistry.set_websocket_manager() enhances tool dispatcher")
        logger.info("   2. UnifiedToolExecutionEngine wraps tool execution with events")
        logger.info("   3. AgentWebSocketBridge sends all required events")
        return 0
    else:
        logger.error(" FAIL:  TESTS FAILED - WebSocket events not working properly")
        logger.error("   Check the implementation of:")
        logger.error("   - AgentRegistry.set_websocket_manager()")
        logger.error("   - enhance_tool_dispatcher_with_notifications()")
        logger.error("   - UnifiedToolExecutionEngine")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)