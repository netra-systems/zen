#!/usr/bin/env python
"""MISSION CRITICAL: Enhanced Tool Execution WebSocket Events Test Suite

Business Value: $500K+ ARR - Ensures tool execution events reach users in real-time
This test suite validates that EnhancedToolExecutionEngine properly sends WebSocket
events during tool execution, which is critical for user experience during AI processing.

CRITICAL: Tool execution events are the most visible part of agent processing to users.
If these fail, users see "blank screen" during the most important part of the workflow.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import enhanced tool execution components
from netra_backend.app.agents.enhanced_tool_execution import (
    EnhancedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.schemas.tool import ToolInput, ToolResult


# ============================================================================
# MOCK CLASSES FOR ENHANCED TOOL EXECUTION TESTING
# ============================================================================

class MockWebSocketManager:
    """Mock WebSocket manager optimized for tool execution testing."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.tool_events: List[Dict] = []
        self.connections: Dict[str, Any] = {}
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message and simulate successful delivery."""
        event_data = {
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        }
        
        self.messages.append(event_data)
        
        # Track tool-specific events separately
        if event_data['event_type'] in ['tool_executing', 'tool_completed']:
            self.tool_events.append(event_data)
        
        return True
    
    def get_tool_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get tool-specific events for a thread."""
        return [event for event in self.tool_events if event['thread_id'] == thread_id]
    
    def get_tool_event_pairs(self, thread_id: str) -> List[tuple]:
        """Get tool event pairs (executing, completed) for validation."""
        events = self.get_tool_events_for_thread(thread_id)
        pairs = []
        executing_events = {}
        
        for event in events:
            tool_name = event['message'].get('payload', {}).get('tool_name', 'unknown')
            
            if event['event_type'] == 'tool_executing':
                executing_events[tool_name] = event
            elif event['event_type'] == 'tool_completed' and tool_name in executing_events:
                pairs.append((executing_events[tool_name], event))
                del executing_events[tool_name]
        
        return pairs
    
    def clear_messages(self):
        """Clear all recorded messages."""
        self.messages.clear()
        self.tool_events.clear()


class MockTool:
    """Mock tool for testing enhanced tool execution."""
    
    def __init__(self, name: str, should_fail: bool = False, execution_time: float = 0.01):
        self.name = name
        self.should_fail = should_fail
        self.execution_time = execution_time
        self.call_count = 0
    
    async def execute(self, **kwargs) -> Any:
        """Mock tool execution."""
        self.call_count += 1
        await asyncio.sleep(self.execution_time)
        
        if self.should_fail:
            raise Exception(f"Tool {self.name} failed intentionally")
        
        return f"Result from {self.name} (call #{self.call_count})"


class MockToolInput:
    """Mock ToolInput for testing."""
    
    def __init__(self, tool_name: str, parameters: Dict = None):
        self.tool_name = tool_name
        self.parameters = parameters or {}


class MockToolResult:
    """Mock ToolResult for testing."""
    
    def __init__(self, result: Any, success: bool = True):
        self.result = result
        self.success = success


# ============================================================================
# UNIT TESTS - Enhanced Tool Execution Engine
# ============================================================================

class TestEnhancedToolExecutionEngineUnit:
    """Unit tests for EnhancedToolExecutionEngine WebSocket events."""
    
    @pytest.fixture(autouse=True)
    def setup_enhanced_tool_mocks(self):
        """Setup mocks for enhanced tool execution testing."""
        self.mock_ws_manager = MockWebSocketManager()
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhanced_tool_execution_engine_creation(self):
        """Test that EnhancedToolExecutionEngine creates properly with WebSocket manager."""
        
        # Create enhanced executor
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Verify initialization
        assert executor.websocket_manager is self.mock_ws_manager, \
            "WebSocket manager should be stored"
        assert executor.websocket_notifier is not None, \
            "WebSocket notifier should be created"
        assert isinstance(executor.websocket_notifier, WebSocketNotifier), \
            "Should have WebSocketNotifier instance"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhanced_tool_execution_sends_events(self):
        """Test that enhanced tool execution sends WebSocket events."""
        
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Create test context and tool
        context = AgentExecutionContext(
            run_id="test-enhanced-tool",
            thread_id="enhanced-test-thread",
            user_id="enhanced-test-user",
            agent_name="test_agent",
            retry_count=0,
            max_retries=1
        )
        
        mock_tool = MockTool("test_enhanced_tool", should_fail=False, execution_time=0.05)
        tool_input = MockToolInput("test_enhanced_tool", {"param1": "value1"})
        
        # Mock the parent execute method to return a proper result
        with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input', 
                         return_value=MockToolResult("success")) as mock_parent_execute:
            
            # Execute tool with enhanced notifications
            result = await executor.execute_tool_with_input(
                tool_input, mock_tool, {'context': context}
            )
            
            # Verify parent method was called
            mock_parent_execute.assert_called_once()
            
            # Verify WebSocket events were sent
            tool_events = self.mock_ws_manager.get_tool_events_for_thread("enhanced-test-thread")
            assert len(tool_events) == 2, f"Expected 2 tool events, got {len(tool_events)}"
            
            # Verify event types and order
            event_types = [event['event_type'] for event in tool_events]
            assert event_types == ['tool_executing', 'tool_completed'], \
                f"Expected [tool_executing, tool_completed], got {event_types}"
            
            # Verify event content
            executing_event = tool_events[0]
            completed_event = tool_events[1]
            
            assert executing_event['message']['payload']['tool_name'] == 'test_enhanced_tool', \
                "Executing event should have correct tool name"
            assert completed_event['message']['payload']['status'] == 'success', \
                "Completed event should indicate success"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhanced_tool_execution_error_handling(self):
        """Test that enhanced tool execution handles errors and still sends events."""
        
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Create test context
        context = AgentExecutionContext(
            run_id="test-error-tool",
            thread_id="error-test-thread",
            user_id="error-test-user",
            agent_name="error_agent",
            retry_count=0,
            max_retries=1
        )
        
        mock_tool = MockTool("error_tool", should_fail=True)
        tool_input = MockToolInput("error_tool")
        
        # Mock parent execute method to raise an exception
        with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input',
                         side_effect=Exception("Tool execution failed")) as mock_parent_execute:
            
            # Execute tool and expect exception
            with pytest.raises(Exception, match="Tool execution failed"):
                await executor.execute_tool_with_input(
                    tool_input, mock_tool, {'context': context}
                )
            
            # Verify WebSocket events were still sent
            tool_events = self.mock_ws_manager.get_tool_events_for_thread("error-test-thread")
            assert len(tool_events) == 2, f"Expected 2 tool events even with error, got {len(tool_events)}"
            
            # Verify event types
            event_types = [event['event_type'] for event in tool_events]
            assert event_types == ['tool_executing', 'tool_completed'], \
                f"Expected [tool_executing, tool_completed] even with error, got {event_types}"
            
            # Verify error event content
            completed_event = tool_events[1]
            assert completed_event['message']['payload']['status'] == 'error', \
                "Completed event should indicate error"
            assert 'error' in completed_event['message']['payload'], \
                "Error event should contain error information"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_dispatcher_enhancement_function(self):
        """Test the enhance_tool_dispatcher_with_notifications function."""
        
        # Create a regular tool dispatcher
        dispatcher = ToolDispatcher()
        original_executor = dispatcher.executor
        
        # Verify initial state
        assert not hasattr(dispatcher, '_websocket_enhanced'), \
            "Dispatcher should not be enhanced initially"
        
        # Enhance it
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        
        # Verify enhancement
        assert hasattr(dispatcher, '_websocket_enhanced'), \
            "Dispatcher should have enhancement marker"
        assert dispatcher._websocket_enhanced is True, \
            "Enhancement marker should be True"
        assert dispatcher.executor != original_executor, \
            "Executor should be replaced"
        assert isinstance(dispatcher.executor, EnhancedToolExecutionEngine), \
            "Executor should be EnhancedToolExecutionEngine"
        assert dispatcher.executor.websocket_manager is self.mock_ws_manager, \
            "Enhanced executor should have WebSocket manager"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_double_enhancement_protection(self):
        """Test that double enhancement is handled gracefully."""
        
        dispatcher = ToolDispatcher()
        
        # First enhancement
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        first_executor = dispatcher.executor
        
        # Second enhancement attempt
        enhance_tool_dispatcher_with_notifications(dispatcher, self.mock_ws_manager)
        second_executor = dispatcher.executor
        
        # Should be the same executor (no double enhancement)
        assert first_executor is second_executor, \
            "Double enhancement should not create new executor"
        assert dispatcher._websocket_enhanced is True, \
            "Enhancement marker should remain True"


# ============================================================================
# INTEGRATION TESTS - Tool Dispatcher Integration
# ============================================================================

class TestEnhancedToolDispatcherIntegration:
    """Integration tests for enhanced tool dispatcher with WebSocket events."""
    
    @pytest.fixture(autouse=True)
    def setup_tool_integration_mocks(self):
        """Setup mocks for tool dispatcher integration testing."""
        self.mock_ws_manager = MockWebSocketManager()
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_agent_registry_tool_dispatcher_enhancement(self):
        """Test that AgentRegistry enhances tool dispatcher with WebSocket events."""
        
        # Create components
        class MockLLM:
            pass
        
        mock_llm = MockLLM()
        tool_dispatcher = ToolDispatcher()
        
        # Create registry and set WebSocket manager
        registry = AgentRegistry(mock_llm, tool_dispatcher)
        original_executor = tool_dispatcher.executor
        
        # Set WebSocket manager (this should trigger enhancement)
        registry.set_websocket_manager(self.mock_ws_manager)
        
        # Verify enhancement occurred
        assert tool_dispatcher.executor != original_executor, \
            "AgentRegistry should enhance tool dispatcher executor"
        assert isinstance(tool_dispatcher.executor, EnhancedToolExecutionEngine), \
            "Tool dispatcher should have enhanced executor"
        assert hasattr(tool_dispatcher, '_websocket_enhanced'), \
            "Tool dispatcher should be marked as enhanced"
        assert tool_dispatcher.executor.websocket_manager is self.mock_ws_manager, \
            "Enhanced executor should have WebSocket manager"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhanced_tool_dispatcher_execution_with_state(self):
        """Test enhanced tool execution with state using execute_with_state method."""
        
        # Create enhanced executor
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Create test parameters
        mock_tool = MockTool("state_tool")
        tool_name = "state_tool"
        parameters = {"param1": "value1"}
        mock_state = {"state_key": "state_value"}
        run_id = "test-state-run"
        
        # Mock the parent execute_with_state method
        expected_result = "state execution result"
        with patch.object(executor.__class__.__bases__[0], 'execute_with_state',
                         return_value=expected_result) as mock_parent_execute:
            
            # Execute with state
            result = await executor.execute_with_state(
                mock_tool, tool_name, parameters, mock_state, run_id
            )
            
            # Verify parent method was called
            mock_parent_execute.assert_called_once_with(
                mock_tool, tool_name, parameters, mock_state, run_id
            )
            
            # Verify result
            assert result == expected_result, "Should return parent execution result"
            
            # Verify WebSocket events were sent
            # Note: execute_with_state creates its own context, so we need to check for events
            all_events = self.mock_ws_manager.messages
            tool_events = [e for e in all_events if e['event_type'] in ['tool_executing', 'tool_completed']]
            
            assert len(tool_events) >= 2, f"Expected at least 2 tool events, got {len(tool_events)}"
            
            # Verify event sequence
            executing_events = [e for e in tool_events if e['event_type'] == 'tool_executing']
            completed_events = [e for e in tool_events if e['event_type'] == 'tool_completed']
            
            assert len(executing_events) > 0, "Should have at least one tool_executing event"
            assert len(completed_events) > 0, "Should have at least one tool_completed event"


# ============================================================================
# PERFORMANCE TESTS - Tool Execution Under Load
# ============================================================================

class TestEnhancedToolExecutionPerformance:
    """Performance tests for enhanced tool execution WebSocket events."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_mocks(self):
        """Setup mocks for performance testing."""
        self.mock_ws_manager = MockWebSocketManager()
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_tool_execution_performance(self):
        """Test WebSocket events with concurrent tool execution."""
        
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        concurrent_tools = 20
        
        async def execute_single_tool(tool_id: int):
            """Execute a single tool with WebSocket events."""
            context = AgentExecutionContext(
                run_id=f"perf-tool-{tool_id}",
                thread_id=f"perf-thread-{tool_id}",
                user_id=f"perf-user-{tool_id}",
                agent_name="performance_agent",
                retry_count=0,
                max_retries=1
            )
            
            mock_tool = MockTool(f"perf_tool_{tool_id}", execution_time=0.01)
            tool_input = MockToolInput(f"perf_tool_{tool_id}")
            
            # Mock parent execution
            with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input',
                             return_value=MockToolResult(f"result_{tool_id}")):
                
                return await executor.execute_tool_with_input(
                    tool_input, mock_tool, {'context': context}
                )
        
        # Execute all tools concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[execute_single_tool(i) for i in range(concurrent_tools)],
            return_exceptions=True
        )
        duration = time.time() - start_time
        
        # Verify all tools executed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_tools, \
            f"Expected {concurrent_tools} successful executions, got {len(successful_results)}"
        
        # Verify WebSocket events were sent for all tools
        total_tool_events = len(self.mock_ws_manager.tool_events)
        expected_events = concurrent_tools * 2  # Each tool sends 2 events
        assert total_tool_events == expected_events, \
            f"Expected {expected_events} tool events, got {total_tool_events}"
        
        # Verify performance
        tools_per_second = concurrent_tools / duration
        assert tools_per_second > 50, \
            f"Tool execution too slow: {tools_per_second:.0f} tools/s (expected >50)"
        
        logger.info(f"Concurrent tool performance: {tools_per_second:.0f} tools/s in {duration:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_event_throughput_validation(self):
        """Test WebSocket event throughput during rapid tool execution."""
        
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Create single context for rapid execution
        context = AgentExecutionContext(
            run_id="throughput-test",
            thread_id="throughput-thread",
            user_id="throughput-user",
            agent_name="throughput_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Execute many tools rapidly
        rapid_executions = 100
        start_time = time.time()
        
        with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input',
                         return_value=MockToolResult("rapid_result")):
            
            for i in range(rapid_executions):
                mock_tool = MockTool(f"rapid_tool_{i}", execution_time=0.001)
                tool_input = MockToolInput(f"rapid_tool_{i}")
                
                await executor.execute_tool_with_input(
                    tool_input, mock_tool, {'context': context}
                )
        
        duration = time.time() - start_time
        events_per_second = (rapid_executions * 2) / duration  # 2 events per execution
        
        # Verify high throughput
        assert events_per_second > 200, \
            f"WebSocket event throughput too low: {events_per_second:.0f} events/s (expected >200)"
        
        # Verify all events were captured
        thread_events = self.mock_ws_manager.get_tool_events_for_thread("throughput-thread")
        assert len(thread_events) == rapid_executions * 2, \
            f"Expected {rapid_executions * 2} events, got {len(thread_events)}"
        
        logger.info(f"Event throughput: {events_per_second:.0f} events/s for {rapid_executions} executions")


# ============================================================================
# ERROR HANDLING TESTS - Tool Execution Failures
# ============================================================================

class TestEnhancedToolExecutionErrorHandling:
    """Error handling tests for enhanced tool execution WebSocket events."""
    
    @pytest.fixture(autouse=True)
    def setup_error_handling_mocks(self):
        """Setup mocks for error handling testing."""
        self.mock_ws_manager = MockWebSocketManager()
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_execution_error_events(self):
        """Test that tool execution errors still produce proper WebSocket events."""
        
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        # Create error scenarios
        error_scenarios = [
            ("timeout_tool", Exception("Tool execution timeout")),
            ("memory_tool", MemoryError("Out of memory during tool execution")),
            ("network_tool", ConnectionError("Network error in tool")),
            ("validation_tool", ValueError("Invalid tool parameters"))
        ]
        
        for tool_name, error in error_scenarios:
            context = AgentExecutionContext(
                run_id=f"error-test-{tool_name}",
                thread_id=f"error-thread-{tool_name}",
                user_id=f"error-user-{tool_name}",
                agent_name="error_agent",
                retry_count=0,
                max_retries=1
            )
            
            mock_tool = MockTool(tool_name, should_fail=True)
            tool_input = MockToolInput(tool_name)
            
            # Mock parent to raise the specific error
            with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input',
                             side_effect=error):
                
                # Execute and expect error
                with pytest.raises(type(error)):
                    await executor.execute_tool_with_input(
                        tool_input, mock_tool, {'context': context}
                    )
                
                # Verify WebSocket events were sent despite error
                thread_events = self.mock_ws_manager.get_tool_events_for_thread(f"error-thread-{tool_name}")
                assert len(thread_events) == 2, \
                    f"Expected 2 events for {tool_name} error, got {len(thread_events)}"
                
                # Verify event content
                executing_event = thread_events[0]
                completed_event = thread_events[1]
                
                assert executing_event['event_type'] == 'tool_executing', \
                    f"First event should be tool_executing for {tool_name}"
                assert completed_event['event_type'] == 'tool_completed', \
                    f"Second event should be tool_completed for {tool_name}"
                assert completed_event['message']['payload']['status'] == 'error', \
                    f"Completed event should indicate error for {tool_name}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_manager_failure_resilience(self):
        """Test that tool execution continues even if WebSocket manager fails."""
        
        # Create executor with failing WebSocket manager
        class FailingWebSocketManager:
            async def send_to_thread(self, thread_id, message):
                raise ConnectionError("WebSocket connection lost")
        
        failing_ws_manager = FailingWebSocketManager()
        executor = EnhancedToolExecutionEngine(failing_ws_manager)
        
        context = AgentExecutionContext(
            run_id="websocket-failure-test",
            thread_id="websocket-failure-thread",
            user_id="websocket-failure-user",
            agent_name="resilient_agent",
            retry_count=0,
            max_retries=1
        )
        
        mock_tool = MockTool("resilient_tool")
        tool_input = MockToolInput("resilient_tool")
        expected_result = MockToolResult("resilient_result")
        
        # Mock parent execution to succeed
        with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input',
                         return_value=expected_result):
            
            # Tool execution should succeed despite WebSocket failure
            result = await executor.execute_tool_with_input(
                tool_input, mock_tool, {'context': context}
            )
            
            # Verify tool execution succeeded
            assert result == expected_result, \
                "Tool execution should succeed even if WebSocket events fail"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_missing_context_handling(self):
        """Test tool execution when context is missing from kwargs."""
        
        executor = EnhancedToolExecutionEngine(self.mock_ws_manager)
        
        mock_tool = MockTool("no_context_tool")
        tool_input = MockToolInput("no_context_tool")
        expected_result = MockToolResult("no_context_result")
        
        # Mock parent execution
        with patch.object(executor.__class__.__bases__[0], 'execute_tool_with_input',
                         return_value=expected_result):
            
            # Execute without context in kwargs
            result = await executor.execute_tool_with_input(
                tool_input, mock_tool, {}  # No context provided
            )
            
            # Should still work
            assert result == expected_result, \
                "Tool execution should work without context"
            
            # No WebSocket events should be sent (no context to send to)
            assert len(self.mock_ws_manager.messages) == 0, \
                "No WebSocket events should be sent without context"


# ============================================================================
# VALIDATION RUNNER
# ============================================================================

def run_enhanced_tool_execution_websocket_validation():
    """Run comprehensive validation of enhanced tool execution WebSocket events."""
    
    logger.info("\n" + "=" * 80)
    logger.info("ENHANCED TOOL EXECUTION WEBSOCKET EVENTS - COMPREHENSIVE VALIDATION")
    logger.info("=" * 80)
    
    # Run the tests
    test_results = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "-m", "critical"  # Only run critical tests
    ])
    
    if test_results == 0:
        logger.info("\n✅ ALL ENHANCED TOOL EXECUTION WEBSOCKET TESTS PASSED")
        logger.info("Tool execution WebSocket events are working correctly ($500K+ ARR protected)")
    else:
        logger.error("\n❌ ENHANCED TOOL EXECUTION WEBSOCKET TESTS FAILED")
        logger.error("CRITICAL: Tool execution WebSocket events are broken!")
    
    return test_results


if __name__ == "__main__":
    # Run comprehensive validation
    exit_code = run_enhanced_tool_execution_websocket_validation()
    sys.exit(exit_code)