"""Critical test for WebSocket agent event completeness.

THIS IS THE PRIMARY TEST FOR AGENT WEBSOCKET COMMUNICATION.
Business Value: $500K+ ARR protection - Core chat functionality depends on this.

Tests that ALL required agent events are sent through the WebSocket pipeline:
- agent_started: User sees agent is working
- agent_thinking: Real-time reasoning display
- tool_executing: Tool execution visibility
- tool_completed: Tool results display
- partial_result: Streaming responses
- final_report: Complete execution summary
- agent_completed: Execution finished

CRITICAL: If this test fails, the chat UI will appear broken to users.
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
from loguru import logger

# Use the actual production services
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
# BaseExecutionInterface removed - using protocol-based approach
from netra_backend.app.routes.websocket import get_websocket_manager, WebSocketManager
from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


# Required events that MUST be sent for proper UI operation
CRITICAL_EVENTS = {
    "agent_started",      # Must show agent is working
    "agent_thinking",     # Must show reasoning process
    "tool_executing",     # Must show tool usage
    "tool_completed",     # Must show tool results
    "partial_result",     # Must stream responses
    "agent_completed"     # Must show completion
}

# Events that enhance UX but aren't critical
ENHANCED_EVENTS = {
    "final_report",       # Comprehensive summary
    "agent_fallback",     # Error recovery
    "agent_update",       # Status updates
}

# Event order validation
REQUIRED_EVENT_ORDER = [
    "agent_started",      # Must be first
    # ... middle events can vary ...
    "agent_completed"     # Must be last (or final_report)
]


class CriticalEventValidator:
    """Validates that all critical WebSocket events are sent."""
    
    def __init__(self):
        self.events: List[Dict] = []
        self.event_types: Set[str] = set()
        self.event_order: List[str] = []
        self.tool_events: List[Dict] = []
        self.thinking_events: List[Dict] = []
        self.partial_results: List[str] = []
        self.timing: Dict[str, float] = {}
        self.start_time = time.time()
        self.errors: List[str] = []
    
    def record_event(self, event: Dict) -> None:
        """Record a WebSocket event for validation."""
        self.events.append(event)
        event_type = event.get("type", "unknown")
        self.event_types.add(event_type)
        self.event_order.append(event_type)
        self.timing[event_type] = time.time() - self.start_time
        
        # Categorize events
        if event_type == "tool_executing":
            self.tool_events.append(event)
        elif event_type == "tool_completed":
            self.tool_events.append(event)
        elif event_type == "agent_thinking":
            self.thinking_events.append(event)
        elif event_type == "partial_result":
            content = event.get("data", {}).get("content", "")
            self.partial_results.append(content)
    
    def validate_critical_events(self) -> tuple[bool, List[str]]:
        """Validate that all critical events were sent."""
        missing = CRITICAL_EVENTS - self.event_types
        errors = []
        
        if missing:
            errors.append(f"CRITICAL: Missing required events: {missing}")
        
        # Validate event order
        if self.event_order:
            if self.event_order[0] != "agent_started":
                errors.append("CRITICAL: agent_started must be first event")
            
            last_event = self.event_order[-1]
            if last_event not in ["agent_completed", "final_report"]:
                errors.append(f"CRITICAL: Invalid last event: {last_event}")
        else:
            errors.append("CRITICAL: No events received at all!")
        
        # Validate tool event pairing
        tool_starts = [e for e in self.tool_events if e.get("type") == "tool_executing"]
        tool_ends = [e for e in self.tool_events if e.get("type") == "tool_completed"]
        
        if len(tool_starts) != len(tool_ends):
            errors.append(f"Tool events mismatch: {len(tool_starts)} starts, {len(tool_ends)} completions")
        
        return len(errors) == 0, errors
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics for the event flow."""
        metrics = {
            "total_events": len(self.events),
            "unique_event_types": len(self.event_types),
            "thinking_updates": len(self.thinking_events),
            "tool_executions": len([e for e in self.tool_events if e.get("type") == "tool_executing"]),
            "partial_results": len(self.partial_results),
            "total_duration": max(self.timing.values()) if self.timing else 0
        }
        
        # Calculate event latencies
        if "agent_started" in self.timing:
            metrics["time_to_first_event"] = self.timing["agent_started"]
        
        if "agent_thinking" in self.timing:
            metrics["time_to_first_thought"] = self.timing["agent_thinking"]
        
        if "partial_result" in self.timing:
            metrics["time_to_first_result"] = self.timing["partial_result"]
        
        return metrics
    
    def generate_report(self) -> str:
        """Generate a comprehensive validation report."""
        is_valid, errors = self.validate_critical_events()
        metrics = self.get_performance_metrics()
        
        report = [
            "=" * 60,
            "CRITICAL WEBSOCKET EVENT VALIDATION REPORT",
            "=" * 60,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {metrics['total_events']}",
            f"Event Types: {metrics['unique_event_types']}",
            "",
            "Critical Events Status:",
        ]
        
        for event in CRITICAL_EVENTS:
            status = "✅" if event in self.event_types else "❌"
            report.append(f"  {status} {event}")
        
        if errors:
            report.extend(["", "Errors Found:"] + [f"  - {e}" for e in errors])
        
        report.extend([
            "",
            "Performance Metrics:",
            f"  - Thinking Updates: {metrics['thinking_updates']}",
            f"  - Tool Executions: {metrics['tool_executions']}",
            f"  - Partial Results: {metrics['partial_results']}",
            f"  - Total Duration: {metrics['total_duration']:.2f}s",
        ])
        
        if "time_to_first_thought" in metrics:
            report.append(f"  - Time to First Thought: {metrics['time_to_first_thought']:.2f}s")
        
        report.extend(["", "Event Sequence:"])
        for i, event in enumerate(self.event_order[:20]):  # Show first 20
            report.append(f"  {i+1}. {event}")
        
        if len(self.event_order) > 20:
            report.append(f"  ... and {len(self.event_order) - 20} more events")
        
        report.append("=" * 60)
        
        return "\n".join(report)


class TestCriticalWebSocketAgentEvents:
    """Test suite for critical WebSocket agent event flow."""
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create a test WebSocket manager."""
        manager = WebSocketManager()
        return manager
    
    @pytest.fixture
    async def event_validator(self):
        """Create an event validator."""
        return CriticalEventValidator()
    
    @pytest.fixture
    async def mock_websocket_connection(self, websocket_manager, event_validator):
        """Mock WebSocket connection that captures events."""
        connection_id = "test-connection-123"
        
        # Create a mock connection that records events
        async def mock_send(message: str):
            try:
                data = json.loads(message)
                event_validator.record_event(data)
                logger.info(f"WebSocket event sent: {data.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to record event: {e}")
        
        mock_conn = MagicMock()
        mock_conn.send = AsyncMock(side_effect=mock_send)
        
        # Register the connection
        await websocket_manager.connect(connection_id, mock_conn)
        
        yield connection_id, mock_conn
        
        # Cleanup
        await websocket_manager.disconnect(connection_id)
    
    @pytest.fixture
    async def execution_engine_with_websocket(self, websocket_manager):
        """Create a supervisor execution engine with WebSocket support."""
        # Create the execution engine
        execution_engine = SupervisorExecutionEngine()
        
        # Create and attach WebSocket notifier
        notifier = WebSocketNotifier(websocket_manager)
        execution_engine.websocket_notifier = notifier
        
        # Create agent registry with WebSocket support
        registry = AgentRegistry()
        registry.set_websocket_manager(websocket_manager)
        
        # CRITICAL: Enhance tool dispatcher with WebSocket notifications
        if hasattr(registry, 'tool_dispatcher'):
            enhance_tool_dispatcher_with_notifications(
                registry.tool_dispatcher, 
                websocket_manager
            )
        
        execution_engine.agent_registry = registry
        
        return execution_engine
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_critical_agent_lifecycle_events(
        self,
        execution_engine_with_websocket,
        mock_websocket_connection,
        event_validator
    ):
        """Test that ALL critical agent lifecycle events are sent."""
        connection_id, mock_conn = mock_websocket_connection
        engine = execution_engine_with_websocket
        
        # Create a test task that will trigger various events
        test_task = {
            "task": "Analyze the system performance and suggest optimizations",
            "context": {
                "user_id": "test-user",
                "session_id": "test-session",
                "connection_id": connection_id,
                "request_id": "test-request-123"
            },
            "metadata": {
                "priority": "high",
                "timeout": 30
            }
        }
        
        # Mock the LLM to return predictable responses
        with patch.object(engine, '_execute_llm_call', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "content": "I'll analyze the system performance now.",
                "reasoning": "First, I need to check current metrics.",
                "tool_calls": [
                    {
                        "tool": "system_metrics",
                        "arguments": {"type": "performance"}
                    }
                ]
            }
            
            # Mock tool execution
            async def mock_tool_execute(tool_name, args):
                # Simulate tool execution delay
                await asyncio.sleep(0.1)
                return {
                    "status": "success",
                    "result": f"Metrics for {tool_name}: CPU 45%, Memory 60%"
                }
            
            with patch.object(engine.agent_registry.tool_dispatcher, 'execute', new_callable=AsyncMock) as mock_tool:
                mock_tool.side_effect = mock_tool_execute
                
                # Execute the task
                result = await engine.execute(test_task)
                
                # Allow time for async events to complete
                await asyncio.sleep(0.5)
        
        # Validate events
        report = event_validator.generate_report()
        logger.info(f"\n{report}")
        
        is_valid, errors = event_validator.validate_critical_events()
        
        # Assert all critical events were sent
        assert is_valid, f"Critical events validation failed:\n" + "\n".join(errors)
        
        # Verify specific event properties
        assert len(event_validator.thinking_events) > 0, "No thinking events sent"
        assert len(event_validator.tool_events) > 0, "No tool events sent"
        
        # Verify event order
        assert event_validator.event_order[0] == "agent_started", "First event must be agent_started"
        assert event_validator.event_order[-1] in ["agent_completed", "final_report"], \
            "Last event must be agent_completed or final_report"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_tool_execution_websocket_events(
        self,
        websocket_manager,
        event_validator
    ):
        """Test that tool execution sends proper WebSocket notifications."""
        # Create enhanced tool dispatcher
        tool_dispatcher = ToolDispatcher()
        enhance_tool_dispatcher_with_notifications(tool_dispatcher, websocket_manager)
        
        # Create mock connection
        connection_id = "test-tool-conn"
        
        async def mock_send(message: str):
            data = json.loads(message)
            event_validator.record_event(data)
        
        mock_conn = MagicMock()
        mock_conn.send = AsyncMock(side_effect=mock_send)
        await websocket_manager.connect(connection_id, mock_conn)
        
        # Register a test tool
        async def test_tool(input_data: str) -> Dict:
            await asyncio.sleep(0.1)  # Simulate work
            return {"result": f"Processed: {input_data}"}
        
        tool_dispatcher.register_tool("test_tool", test_tool, "Test tool")
        
        # Execute tool with context
        context = {
            "connection_id": connection_id,
            "request_id": "test-request"
        }
        
        result = await tool_dispatcher.execute(
            "test_tool",
            {"input_data": "test data"},
            context
        )
        
        # Allow events to propagate
        await asyncio.sleep(0.2)
        
        # Validate tool events
        tool_events = [e for e in event_validator.events if "tool" in e.get("type", "")]
        assert len(tool_events) >= 2, "Should have tool_executing and tool_completed events"
        
        # Check for proper pairing
        executing_events = [e for e in tool_events if e.get("type") == "tool_executing"]
        completed_events = [e for e in tool_events if e.get("type") == "tool_completed"]
        
        assert len(executing_events) > 0, "No tool_executing events"
        assert len(completed_events) > 0, "No tool_completed events"
        assert len(executing_events) == len(completed_events), "Tool events not properly paired"
        
        # Cleanup
        await websocket_manager.disconnect(connection_id)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_partial_result_streaming(
        self,
        execution_engine_with_websocket,
        mock_websocket_connection,
        event_validator
    ):
        """Test that partial results are streamed during execution."""
        connection_id, _ = mock_websocket_connection
        engine = execution_engine_with_websocket
        
        # Create a task that generates partial results
        test_task = {
            "task": "Generate a detailed analysis report",
            "context": {
                "connection_id": connection_id,
                "request_id": "streaming-test",
                "stream": True  # Enable streaming
            }
        }
        
        # Mock LLM to return content in chunks
        async def mock_llm_streaming(*args, **kwargs):
            chunks = [
                "Starting analysis...",
                "Processing data points...",
                "Generating insights...",
                "Finalizing report..."
            ]
            
            for chunk in chunks:
                # Send partial result
                if hasattr(engine.websocket_notifier, 'send_partial_result'):
                    await engine.websocket_notifier.send_partial_result(
                        connection_id,
                        "streaming-test",
                        chunk
                    )
                await asyncio.sleep(0.1)
            
            return {
                "content": " ".join(chunks),
                "reasoning": "Analysis complete"
            }
        
        with patch.object(engine, '_execute_llm_call', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = mock_llm_streaming
            
            result = await engine.execute(test_task)
            await asyncio.sleep(0.5)
        
        # Validate streaming
        assert len(event_validator.partial_results) > 0, "No partial results streamed"
        assert len(event_validator.partial_results) >= 3, \
            f"Expected at least 3 partial results, got {len(event_validator.partial_results)}"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_error_recovery_websocket_events(
        self,
        execution_engine_with_websocket,
        mock_websocket_connection,
        event_validator
    ):
        """Test that errors still send proper completion events."""
        connection_id, _ = mock_websocket_connection
        engine = execution_engine_with_websocket
        
        test_task = {
            "task": "Execute a failing operation",
            "context": {
                "connection_id": connection_id,
                "request_id": "error-test"
            }
        }
        
        # Mock LLM to raise an error
        with patch.object(engine, '_execute_llm_call', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("Simulated LLM failure")
            
            # Execute should handle the error gracefully
            result = await engine.execute(test_task)
            await asyncio.sleep(0.2)
        
        # Even with errors, we should get proper events
        assert "agent_started" in event_validator.event_types, "Missing agent_started even with error"
        assert any(e in event_validator.event_types for e in ["agent_completed", "agent_fallback"]), \
            "Missing completion event after error"
        
        # Check for error indication
        error_events = [e for e in event_validator.events 
                       if "error" in str(e.get("data", {})).lower() or 
                       e.get("type") == "agent_fallback"]
        assert len(error_events) > 0, "No error indication in events"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_high_throughput_event_delivery(
        self,
        websocket_manager,
        event_validator
    ):
        """Test that WebSocket can handle high-throughput event delivery."""
        connection_id = "throughput-test"
        
        async def mock_send(message: str):
            data = json.loads(message)
            event_validator.record_event(data)
        
        mock_conn = MagicMock()
        mock_conn.send = AsyncMock(side_effect=mock_send)
        await websocket_manager.connect(connection_id, mock_conn)
        
        # Create notifier
        notifier = WebSocketNotifier(websocket_manager)
        
        # Send many events rapidly
        event_count = 100
        start_time = time.time()
        
        for i in range(event_count):
            await notifier.send_agent_thinking(
                connection_id,
                f"request-{i}",
                f"Thinking about item {i}..."
            )
            
            if i % 10 == 0:
                await notifier.send_partial_result(
                    connection_id,
                    f"request-{i}",
                    f"Partial result for batch {i//10}"
                )
        
        duration = time.time() - start_time
        events_per_second = event_count / duration
        
        logger.info(f"Sent {event_count} events in {duration:.2f}s ({events_per_second:.0f} events/s)")
        
        # Validate all events were received
        assert len(event_validator.events) >= event_count, \
            f"Lost events: sent {event_count}, received {len(event_validator.events)}"
        
        # Check throughput
        assert events_per_second > 50, \
            f"Throughput too low: {events_per_second:.0f} events/s (expected >50)"
        
        # Cleanup
        await websocket_manager.disconnect(connection_id)


if __name__ == "__main__":
    # Run with: python -m pytest tests/e2e/test_critical_websocket_agent_events.py -v
    pytest.main([__file__, "-v", "--tb=short"])