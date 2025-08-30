"""PRIMARY TEST: End-to-end WebSocket chat functionality.

CRITICAL: This is THE PRIMARY TEST for basic chat functionality.
If this test fails, users cannot use the chat interface properly.

Business Value: $500K+ ARR protection - Core product functionality.
"""

import asyncio
import json
import time
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger

# Test WebSocket event flow without complex imports
from netra_backend.app.routes.websocket import WebSocketManager


class ChatEventValidator:
    """Validates chat WebSocket events are sent correctly."""
    
    def __init__(self):
        self.events = []
        self.event_types = set()
        self.has_started = False
        self.has_thinking = False
        self.has_tools = False
        self.has_results = False
        self.has_completed = False
    
    def record_event(self, event: Dict) -> None:
        """Record and categorize an event."""
        self.events.append(event)
        event_type = event.get("type", "")
        self.event_types.add(event_type)
        
        # Track critical event categories
        if "started" in event_type:
            self.has_started = True
        if "thinking" in event_type:
            self.has_thinking = True
        if "tool" in event_type:
            self.has_tools = True
        if "result" in event_type or "response" in event_type:
            self.has_results = True
        if "completed" in event_type or "final" in event_type:
            self.has_completed = True
    
    def validate_basic_flow(self) -> tuple[bool, List[str]]:
        """Validate basic chat flow requirements."""
        errors = []
        
        if not self.has_started:
            errors.append("No start event - user won't know agent is working")
        
        if not self.has_results:
            errors.append("No results sent - user won't see any response")
        
        if not self.has_completed:
            errors.append("No completion event - user won't know when done")
        
        if len(self.events) == 0:
            errors.append("No WebSocket events at all - chat is completely broken")
        
        return len(errors) == 0, errors
    
    def get_summary(self) -> str:
        """Get a summary of events received."""
        return f"""
WebSocket Chat Event Summary:
- Total Events: {len(self.events)}
- Event Types: {', '.join(self.event_types) if self.event_types else 'NONE'}
- Has Start: {'✅' if self.has_started else '❌'}
- Has Thinking: {'✅' if self.has_thinking else '❌'}
- Has Tools: {'✅' if self.has_tools else '❌'}
- Has Results: {'✅' if self.has_results else '❌'}
- Has Completion: {'✅' if self.has_completed else '❌'}
"""


class TestPrimaryChatWebSocketFlow:
    """Test the primary chat WebSocket flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_basic_chat_message_flow(self):
        """Test that a basic chat message triggers proper WebSocket events."""
        # Create WebSocket manager
        manager = WebSocketManager()
        validator = ChatEventValidator()
        
        # Mock WebSocket connection
        connection_id = "test-chat-123"
        
        async def capture_event(message: str):
            try:
                data = json.loads(message)
                validator.record_event(data)
                logger.info(f"Captured event: {data.get('type', 'unknown')}")
            except:
                pass
        
        mock_conn = MagicMock()
        mock_conn.send = AsyncMock(side_effect=capture_event)
        
        # Connect
        await manager.connect(connection_id, mock_conn)
        
        # Test sending various WebSocket events that should happen during chat
        from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
        notifier = WebSocketNotifier(manager)
        
        request_id = "test-request-123"
        
        # Simulate a chat flow
        await notifier.send_agent_started(connection_id, request_id, "supervisor")
        await asyncio.sleep(0.01)
        
        await notifier.send_agent_thinking(connection_id, request_id, "Analyzing your request...")
        await asyncio.sleep(0.01)
        
        await notifier.send_tool_executing(connection_id, request_id, "search_knowledge", {})
        await asyncio.sleep(0.01)
        
        await notifier.send_tool_completed(connection_id, request_id, "search_knowledge", {"found": "data"})
        await asyncio.sleep(0.01)
        
        await notifier.send_partial_result(connection_id, request_id, "Here's what I found...")
        await asyncio.sleep(0.01)
        
        await notifier.send_agent_completed(connection_id, request_id, {"success": True})
        
        # Allow events to process
        await asyncio.sleep(0.1)
        
        # Validate
        is_valid, errors = validator.validate_basic_flow()
        
        logger.info(validator.get_summary())
        
        if not is_valid:
            logger.error(f"Validation errors: {errors}")
        
        assert is_valid, f"Basic chat flow validation failed: {errors}"
        assert len(validator.events) >= 6, f"Expected at least 6 events, got {len(validator.events)}"
        
        # Cleanup
        await manager.disconnect(connection_id)
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    @pytest.mark.timeout(30)
    async def test_real_supervisor_websocket_integration(self):
        """Test that the supervisor agent actually sends WebSocket events."""
        # Import the real supervisor components
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.llm.llm_manager import LLMManager
        
        # Setup
        manager = WebSocketManager()
        validator = ChatEventValidator()
        connection_id = "supervisor-test"
        
        async def capture_event(message: str):
            try:
                data = json.loads(message)
                validator.record_event(data)
            except:
                pass
        
        mock_conn = MagicMock()
        mock_conn.send = AsyncMock(side_effect=capture_event)
        await manager.connect(connection_id, mock_conn)
        
        # Create supervisor components
        llm_manager = LLMManager()
        tool_dispatcher = ToolDispatcher()
        
        # Create registry and set WebSocket manager
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        registry.set_websocket_manager(manager)  # This should now enhance tool dispatcher!
        
        # Create execution engine
        engine = ExecutionEngine(registry, manager)
        
        # Create execution context
        context = AgentExecutionContext(
            agent_name="test_agent",
            request_id="test-req-456",
            connection_id=connection_id,
            start_time=time.time(),
            retry_count=0,
            max_retries=1
        )
        
        # Create state
        state = DeepAgentState()
        state.user_prompt = "Test message"
        
        # Mock the agent execution to avoid LLM calls
        async def mock_execute(ctx, st):
            # Simulate some work
            await asyncio.sleep(0.1)
            st.final_answer = "Test response"
            return MagicMock(success=True, agent_name="test", execution_time=0.1)
        
        with patch.object(engine.agent_core, 'execute_agent', new=mock_execute):
            # Execute
            result = await engine.execute_agent(context, state)
        
        # Allow events to process
        await asyncio.sleep(0.2)
        
        # Validate
        logger.info(validator.get_summary())
        
        # Should have at least start and thinking events from execution engine
        assert validator.has_started, "Supervisor didn't send start event"
        assert validator.has_thinking, "Supervisor didn't send thinking events"
        assert len(validator.events) > 0, "No WebSocket events sent by supervisor"
        
        # Cleanup
        await manager.disconnect(connection_id)
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_tool_execution_websocket_events(self):
        """Test that tool execution sends proper WebSocket events."""
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.enhanced_tool_execution import (
            enhance_tool_dispatcher_with_notifications
        )
        
        # Setup
        manager = WebSocketManager()
        validator = ChatEventValidator()
        connection_id = "tool-test"
        
        async def capture_event(message: str):
            try:
                data = json.loads(message)
                validator.record_event(data)
                if "tool" in data.get("type", ""):
                    logger.info(f"Tool event: {data}")
            except:
                pass
        
        mock_conn = MagicMock()
        mock_conn.send = AsyncMock(side_effect=capture_event)
        await manager.connect(connection_id, mock_conn)
        
        # Create and enhance tool dispatcher
        dispatcher = ToolDispatcher()
        enhance_tool_dispatcher_with_notifications(dispatcher, manager)
        
        # Register a test tool
        async def test_tool(data: str) -> Dict:
            await asyncio.sleep(0.05)
            return {"result": f"Processed: {data}"}
        
        dispatcher.register_tool("test_tool", test_tool, "Test tool")
        
        # Execute tool with context
        context = {
            "connection_id": connection_id,
            "request_id": "tool-req-789"
        }
        
        result = await dispatcher.execute("test_tool", {"data": "test"}, context)
        
        # Allow events to process
        await asyncio.sleep(0.1)
        
        # Validate
        logger.info(validator.get_summary())
        
        assert validator.has_tools, "Tool execution didn't send WebSocket events"
        
        # Check for both executing and completed
        tool_events = [e for e in validator.events if "tool" in e.get("type", "")]
        assert len(tool_events) >= 2, f"Expected executing and completed events, got {len(tool_events)}"
        
        # Cleanup
        await manager.disconnect(connection_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-k", "test_basic_chat_message_flow"])