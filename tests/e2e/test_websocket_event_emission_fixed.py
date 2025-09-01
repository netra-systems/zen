#!/usr/bin/env python
"""
End-to-End Test: WebSocket Event Emission Fixed

This test validates that our WebSocket context propagation fix is working correctly.
It tests the critical path from agent execution to WebSocket event emission.

Business Value: Core chat functionality - users must see real-time agent status.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import core components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


class WebSocketEventCapture:
    """Captures and validates WebSocket events with timing."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.events = []
        self.event_types = set()
        self.start_time = time.time()
        
    async def capture_event(self, message):
        """Capture WebSocket event."""
        if isinstance(message, str):
            data = json.loads(message)
        else:
            data = message
        
        # Add timestamp
        data['_captured_at'] = time.time() - self.start_time
        
        self.events.append(data)
        self.event_types.add(data.get('type', 'unknown'))
        
        logger.info(f"Captured event: {data.get('type', 'unknown')} at {data['_captured_at']:.3f}s")
        
    def validate_critical_events(self):
        """Validate that all critical events were captured."""
        missing = self.REQUIRED_EVENTS - self.event_types
        if missing:
            logger.error(f"Missing critical events: {missing}")
            logger.error(f"Got events: {sorted(self.event_types)}")
            return False, f"Missing events: {missing}"
        
        # Validate event ordering
        event_order = [e.get('type') for e in self.events]
        
        # First event should be agent_started
        if not event_order or event_order[0] != 'agent_started':
            return False, f"First event was {event_order[0] if event_order else 'none'}, not agent_started"
        
        # Should have a completion event
        completion_events = {'agent_completed', 'final_report'}
        if not any(event_type in completion_events for event_type in event_order):
            return False, f"No completion event found in {event_order}"
        
        return True, "All critical events validated"
    
    def get_report(self):
        """Generate validation report."""
        is_valid, message = self.validate_critical_events()
        
        report = [
            f"\nWebSocket Event Validation Report",
            f"{'='*50}",
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total events: {len(self.events)}",
            f"Event types: {sorted(self.event_types)}",
            f"Duration: {self.events[-1]['_captured_at'] if self.events else 0:.3f}s",
            f"Result: {message}",
            f"{'='*50}"
        ]
        
        # Show event timeline
        if self.events:
            report.append("\nEvent Timeline:")
            for event in self.events:
                event_type = event.get('type', 'unknown')
                timestamp = event.get('_captured_at', 0)
                report.append(f"  {timestamp:.3f}s: {event_type}")
        
        return "\n".join(report)


class MockLLMManager:
    """Mock LLM manager for testing."""
    
    async def generate(self, *args, **kwargs):
        """Mock generate method."""
        await asyncio.sleep(0.1)  # Simulate processing
        return {
            "content": "Mock analysis complete",
            "reasoning": "This is a test response",
            "confidence": 0.95,
            "triage_result": "data_request",
            "priority": "high",
            "estimated_complexity": "medium"
        }


@pytest.mark.asyncio
@pytest.mark.critical
async def test_websocket_events_emitted_during_agent_execution():
    """
    Test that WebSocket events are properly emitted during real agent execution.
    
    This validates that our WebSocket context propagation fix is working.
    """
    logger.info("\n" + "="*80)
    logger.info("TESTING: WebSocket Event Emission Fixed")
    logger.info("="*80)
    
    # Setup WebSocket manager and capture
    ws_manager = WebSocketManager()
    event_capture = WebSocketEventCapture()
    
    # Setup mock WebSocket connection
    user_id = "test-user"
    thread_id = "test-thread"
    mock_websocket = MagicMock()
    mock_websocket.send_json = AsyncMock(side_effect=event_capture.capture_event)
    
    # Connect user
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    try:
        # Setup components with real WebSocket integration
        llm_manager = MockLLMManager()
        tool_dispatcher = ToolDispatcher()
        
        # Register a test tool that will trigger tool events
        from langchain_core.tools import tool
        
        @tool
        def test_analysis_tool(query: str) -> dict:
            """Test tool that simulates analysis."""
            return {"analysis": f"Analyzed: {query}", "confidence": 0.9}
        
        # Register the tool through the registry
        tool_dispatcher.registry.register_tool(test_analysis_tool)
        
        # Create agent registry and set WebSocket manager
        # This is the CRITICAL integration point we're testing
        registry = AgentRegistry(llm_manager, tool_dispatcher)
        registry.set_websocket_manager(ws_manager)  # This should enhance tool dispatcher
        
        # Verify tool dispatcher was enhanced
        assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            "Tool dispatcher was not enhanced with WebSocket notifications"
        assert hasattr(tool_dispatcher, '_websocket_enhanced'), \
            "Tool dispatcher enhancement marker missing"
        
        logger.info("✅ Tool dispatcher enhanced with WebSocket notifications")
        
        # Register default agents
        registry.register_default_agents()
        
        # Create execution engine
        execution_engine = ExecutionEngine(registry, ws_manager)
        
        # Create execution context
        context = AgentExecutionContext(
            agent_name="triage",
            run_id=f"test-run-{uuid.uuid4()}",
            thread_id=thread_id,
            user_id=user_id,
            retry_count=0,
            max_retries=1
        )
        
        # Create agent state
        state = DeepAgentState()
        state.user_request = "What is the system performance status?"
        state.chat_thread_id = thread_id
        state.user_id = user_id
        
        logger.info("Starting agent execution...")
        
        # Execute agent - this should emit WebSocket events
        result = await execution_engine.execute_agent(context, state)
        
        # Give events time to propagate
        await asyncio.sleep(0.5)
        
        logger.info(f"Agent execution completed with result: {result is not None}")
        
        # Validate WebSocket events
        is_valid, validation_message = event_capture.validate_critical_events()
        
        # Generate report
        report = event_capture.get_report()
        logger.info(report)
        
        # Assert critical events were emitted
        assert is_valid, f"WebSocket event validation failed: {validation_message}"
        
        # Additional validations
        assert len(event_capture.events) >= 3, \
            f"Expected at least 3 events, got {len(event_capture.events)}"
        
        assert "agent_started" in event_capture.event_types, \
            "agent_started event not emitted - user won't know processing started"
        
        # Check for completion
        completion_events = {"agent_completed", "final_report"}
        has_completion = bool(completion_events & event_capture.event_types)
        assert has_completion, \
            "No completion event emitted - user won't know when processing finished"
        
        # Test that tool events were properly paired if any tools were used
        tool_executing_count = sum(1 for e in event_capture.events if e.get('type') == 'tool_executing')
        tool_completed_count = sum(1 for e in event_capture.events if e.get('type') == 'tool_completed')
        
        if tool_executing_count > 0:
            assert tool_executing_count == tool_completed_count, \
                f"Tool events not paired: {tool_executing_count} starts, {tool_completed_count} completions"
            logger.info(f"✅ Tool events properly paired: {tool_executing_count} pairs")
        
        logger.info("✅ WebSocket event emission test PASSED")
        logger.info("✅ WebSocket context propagation fix is working correctly")
        
    finally:
        # Cleanup
        await ws_manager.disconnect_user(user_id, mock_websocket, thread_id)


@pytest.mark.asyncio  
@pytest.mark.critical
async def test_unified_tool_execution_direct():
    """
    Direct test of the UnifiedToolExecutionEngine WebSocket integration.
    
    This tests the core fix in unified_tool_execution.py.
    """
    logger.info("\n" + "="*50)
    logger.info("TESTING: Enhanced Tool Execution Direct")
    logger.info("="*50)
    
    # Setup
    ws_manager = WebSocketManager()
    event_capture = WebSocketEventCapture()
    
    user_id = "direct-test"
    thread_id = "direct-thread"
    mock_websocket = MagicMock()
    mock_websocket.send_json = AsyncMock(side_effect=event_capture.capture_event)
    
    await ws_manager.connect_user(user_id, mock_websocket, thread_id)
    
    try:
        # Create enhanced executor directly
        enhanced_executor = UnifiedToolExecutionEngine(ws_manager)
        
        # Create test state
        state = DeepAgentState()
        state.chat_thread_id = thread_id
        state.user_id = user_id
        
        # Create test tool
        async def test_direct_tool():
            await asyncio.sleep(0.02)
            return {"result": "direct tool success"}
        
        # Execute tool directly through enhanced executor
        result = await enhanced_executor.execute_with_state(
            test_direct_tool,
            "test_direct_tool", 
            {},
            state,
            thread_id
        )
        
        await asyncio.sleep(0.1)
        
        # Validate tool events were emitted
        assert "tool_executing" in event_capture.event_types, \
            "tool_executing event not emitted by enhanced executor"
        assert "tool_completed" in event_capture.event_types, \
            "tool_completed event not emitted by enhanced executor"
        
        logger.info("✅ Enhanced tool execution direct test PASSED")
        logger.info(f"Events captured: {sorted(event_capture.event_types)}")
        
    finally:
        await ws_manager.disconnect_user(user_id, mock_websocket, thread_id)


@pytest.mark.asyncio
@pytest.mark.critical
async def test_tool_dispatcher_enhancement_integration():
    """
    Test that the tool dispatcher enhancement function works properly.
    
    This tests the integration point in agent_registry.py.
    """
    logger.info("\n" + "="*50)
    logger.info("TESTING: Tool Dispatcher Enhancement Integration")
    logger.info("="*50)
    
    # Create tool dispatcher
    tool_dispatcher = ToolDispatcher()
    original_executor = tool_dispatcher.executor
    
    # Create WebSocket manager
    ws_manager = WebSocketManager()
    
    # Enhance the tool dispatcher
    enhance_tool_dispatcher_with_notifications(tool_dispatcher, ws_manager)
    
    # Validate enhancement
    assert tool_dispatcher.executor != original_executor, \
        "Tool dispatcher executor was not replaced"
    
    assert isinstance(tool_dispatcher.executor, UnifiedToolExecutionEngine), \
        f"Expected UnifiedToolExecutionEngine, got {type(tool_dispatcher.executor)}"
    
    assert hasattr(tool_dispatcher, '_websocket_enhanced'), \
        "Enhancement marker not set"
    
    assert tool_dispatcher._websocket_enhanced is True, \
        "Enhancement marker not True"
    
    assert hasattr(tool_dispatcher, '_original_executor'), \
        "Original executor not preserved"
    
    # Test that enhanced executor has WebSocket manager
    enhanced_executor = tool_dispatcher.executor
    assert enhanced_executor.websocket_manager is ws_manager, \
        "Enhanced executor doesn't have WebSocket manager"
    
    logger.info("✅ Tool dispatcher enhancement integration test PASSED")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])