"""Unit tests for UnifiedToolExecutionEngine WebSocket notification system.

These tests validate the enhanced tool execution engine's WebSocket notification
capabilities which are critical for delivering real-time chat value to users.

Business Value: Free/Early/Mid/Enterprise - User Experience
Ensures users receive real-time tool execution updates for substantive chat interactions.

Test Coverage:
- WebSocket notification emission during tool execution
- Tool execution state tracking and metrics
- AgentWebSocketBridge adapter integration
- Error handling with proper notification fallbacks
- Tool execution context propagation
- Progress updates for long-running tools
"""

import asyncio
import inspect
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications,
    EnhancedToolExecutionEngine,  # Backward compatibility alias
)
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus, SimpleToolPayload
from netra_backend.app.core.tool_models import UnifiedTool, ToolExecutionResult
from langchain_core.tools import BaseTool


class MockAgentWebSocketBridge:
    """Mock WebSocket bridge for testing notifications."""
    
    def __init__(self):
        self.tool_executing_calls = []
        self.tool_completed_calls = []
        self.progress_update_calls = []
        self.should_return_success = True
        
    async def notify_tool_executing(
        self, 
        run_id: str, 
        agent_name: str, 
        tool_name: str, 
        parameters: Dict[str, Any] = None
    ) -> bool:
        """Mock tool executing notification."""
        call_record = {
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.tool_executing_calls.append(call_record)
        return self.should_return_success
        
    async def notify_tool_completed(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        result: Dict[str, Any] = None,
        execution_time_ms: float = None
    ) -> bool:
        """Mock tool completed notification."""
        call_record = {
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.tool_completed_calls.append(call_record)
        return self.should_return_success
        
    async def notify_progress_update(
        self,
        run_id: str,
        agent_name: str,
        progress: Dict[str, Any]
    ) -> bool:
        """Mock progress update notification."""
        call_record = {
            "run_id": run_id,
            "agent_name": agent_name,
            "progress": progress,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.progress_update_calls.append(call_record)
        return self.should_return_success
        
    def clear_calls(self):
        """Clear all recorded calls."""
        self.tool_executing_calls.clear()
        self.tool_completed_calls.clear()
        self.progress_update_calls.clear()


class MockDataProcessingTool(BaseTool):
    """Mock tool that simulates data processing with delays."""
    
    name: str = "data_processor"
    description: str = "Processes datasets and generates insights"
    
    def __init__(self, processing_delay: float = 0.001, should_fail: bool = False):
        super().__init__()
        self.processing_delay = processing_delay
        self.should_fail = should_fail
        self.execution_count = 0
        self.last_context = None
        
    def _run(self, dataset: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(dataset, **kwargs))
        
    async def _arun(self, dataset: str, **kwargs) -> str:
        """Asynchronous execution with context handling."""
        self.execution_count += 1
        
        # Store context if provided
        if 'context' in kwargs:
            self.last_context = kwargs['context']
            
        # Simulate processing delay
        if self.processing_delay > 0:
            await asyncio.sleep(self.processing_delay)
            
        if self.should_fail:
            raise ValueError(f"Processing failed for dataset: {dataset}")
            
        return f"Processed dataset: {dataset} with {len(dataset)} records"


class MockLongRunningTool(BaseTool):
    """Mock tool that simulates long-running operations."""
    
    name: str = "long_runner"
    description: str = "Simulates long-running operations with progress updates"
    
    def __init__(self, total_steps: int = 5, step_delay: float = 0.001):
        super().__init__()
        self.total_steps = total_steps
        self.step_delay = step_delay
        self.execution_count = 0
        
    def _run(self, operation: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(operation, **kwargs))
        
    async def _arun(self, operation: str, **kwargs) -> str:
        """Asynchronous execution with progress simulation."""
        self.execution_count += 1
        
        # Simulate long-running operation with steps
        for step in range(self.total_steps):
            await asyncio.sleep(self.step_delay)
            progress = ((step + 1) / self.total_steps) * 100
            # In real scenarios, progress updates would be handled by the execution engine
            
        return f"Long running operation '{operation}' completed in {self.total_steps} steps"


class TestUnifiedToolExecutionEngineWebSocketNotifications(SSotAsyncTestCase):
    """Unit tests for UnifiedToolExecutionEngine WebSocket notification system."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create test contexts
        self.user_context = UserExecutionContext(
            user_id="test_user_websocket",
            run_id=f"run_{int(time.time() * 1000)}",
            thread_id="thread_websocket_test",
            session_id="session_websocket_test"
        )
        
        self.agent_context = AgentExecutionContext(
            agent_name="TestAgent",
            run_id=self.user_context.run_id,
            thread_id=self.user_context.thread_id,
            user_id=self.user_context.user_id,
            retry_count=0,
            max_retries=3
        )
        
        # Mock WebSocket bridge
        self.websocket_bridge = MockAgentWebSocketBridge()
        
        # Mock tools
        self.data_tool = MockDataProcessingTool()
        self.long_running_tool = MockLongRunningTool()
        self.failing_tool = MockDataProcessingTool(should_fail=True)
        
        # Create execution engine with WebSocket bridge
        self.execution_engine = UnifiedToolExecutionEngine(
            websocket_bridge=self.websocket_bridge
        )
        
    async def tearDown(self):
        """Clean up after tests."""
        await super().tearDown()
        
    # ===================== WEBSOCKET NOTIFICATION TESTS =====================
    
    async def test_tool_execution_emits_websocket_events(self):
        """Test that tool execution emits both executing and completed WebSocket events."""
        # Create tool input
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "customer_data.csv", "operation": "analyze"},
            request_id=self.user_context.run_id
        )
        
        # Execute tool with context
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.data_tool,
            kwargs={"context": self.agent_context, "dataset": "customer_data.csv", "operation": "analyze"}
        )
        
        # Verify successful execution
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertIsNotNone(result.payload.result)
        
        # Verify WebSocket events were emitted
        self.assertEqual(len(self.websocket_bridge.tool_executing_calls), 1)
        self.assertEqual(len(self.websocket_bridge.tool_completed_calls), 1)
        
        # Verify tool_executing event details
        executing_call = self.websocket_bridge.tool_executing_calls[0]
        self.assertEqual(executing_call["tool_name"], "data_processor")
        self.assertEqual(executing_call["run_id"], self.agent_context.run_id)
        self.assertEqual(executing_call["agent_name"], "TestAgent")
        self.assertIsNotNone(executing_call["parameters"])
        
        # Verify tool_completed event details
        completed_call = self.websocket_bridge.tool_completed_calls[0]
        self.assertEqual(completed_call["tool_name"], "data_processor")
        self.assertEqual(completed_call["run_id"], self.agent_context.run_id)
        self.assertEqual(completed_call["result"]["status"], "success")
        self.assertIsNotNone(completed_call["execution_time_ms"])
        
    async def test_websocket_events_on_tool_failure(self):
        """Test WebSocket events are emitted even when tool execution fails."""
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "corrupted_data.csv"},
            request_id=self.user_context.run_id
        )
        
        # Execute failing tool
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.failing_tool,
            kwargs={"context": self.agent_context, "dataset": "corrupted_data.csv"}
        )
        
        # Verify execution failure is handled
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIsNotNone(result.message)
        
        # Verify WebSocket events were still emitted
        self.assertEqual(len(self.websocket_bridge.tool_executing_calls), 1)
        self.assertEqual(len(self.websocket_bridge.tool_completed_calls), 1)
        
        # Verify error details in completed event
        completed_call = self.websocket_bridge.tool_completed_calls[0]
        self.assertEqual(completed_call["result"]["status"], "error")
        self.assertIn("error", completed_call["result"])
        self.assertIn("Processing failed", completed_call["result"]["error"])
        
    async def test_websocket_bridge_failure_handling(self):
        """Test handling when WebSocket bridge fails to deliver notifications."""
        # Configure bridge to fail
        self.websocket_bridge.should_return_success = False
        
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "test_data.csv"},
            request_id=self.user_context.run_id
        )
        
        # Tool execution should still succeed despite WebSocket failure
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.data_tool,
            kwargs={"context": self.agent_context, "dataset": "test_data.csv"}
        )
        
        # Verify tool execution succeeded
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        
        # Verify WebSocket notifications were attempted
        self.assertEqual(len(self.websocket_bridge.tool_executing_calls), 1)
        self.assertEqual(len(self.websocket_bridge.tool_completed_calls), 1)
        
    async def test_websocket_events_without_bridge(self):
        """Test tool execution works without WebSocket bridge (graceful degradation)."""
        # Create engine without WebSocket bridge
        engine_no_websocket = UnifiedToolExecutionEngine(websocket_bridge=None)
        
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "offline_data.csv"},
            request_id=self.user_context.run_id
        )
        
        # Execution should work without WebSocket notifications
        result = await engine_no_websocket.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.data_tool,
            kwargs={"context": self.agent_context, "dataset": "offline_data.csv"}
        )
        
        # Verify successful execution
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertIsNotNone(result.payload.result)
        
    # ===================== CONTEXT HANDLING TESTS =====================
        
    async def test_context_propagation_to_tools(self):
        """Test that execution context is properly propagated to tools."""
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "context_test.csv"},
            request_id=self.user_context.run_id
        )
        
        # Execute tool with context
        await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.data_tool,
            kwargs={"context": self.agent_context, "dataset": "context_test.csv"}
        )
        
        # Verify context was received by tool
        self.assertIsNotNone(self.data_tool.last_context)
        self.assertEqual(self.data_tool.last_context.user_id, self.agent_context.user_id)
        self.assertEqual(self.data_tool.last_context.run_id, self.agent_context.run_id)
        
    async def test_missing_context_error_handling(self):
        """Test error handling when execution context is missing."""
        # Mock the _send_tool_executing method to test missing context error
        original_method = self.execution_engine._send_tool_executing
        
        with patch.object(self.execution_engine, '_send_tool_executing', side_effect=ValueError("Missing execution context")):
            tool_input = ToolInput(
                tool_name="data_processor",
                parameters={"dataset": "no_context.csv"},
                request_id=self.user_context.run_id
            )
            
            # Execution should handle the missing context error
            result = await self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=self.data_tool,
                kwargs={"dataset": "no_context.csv"}  # No context provided
            )
            
            # Should get an error result
            self.assertEqual(result.status, ToolStatus.ERROR)
            
    # ===================== METRICS AND MONITORING TESTS =====================
        
    async def test_execution_metrics_tracking(self):
        """Test that execution metrics are properly tracked."""
        initial_metrics = self.execution_engine.get_execution_metrics()
        
        # Execute successful tool
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "metrics_test.csv"},
            request_id=self.user_context.run_id
        )
        
        await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.data_tool,
            kwargs={"context": self.agent_context, "dataset": "metrics_test.csv"}
        )
        
        # Check metrics were updated
        updated_metrics = self.execution_engine.get_execution_metrics()
        self.assertEqual(updated_metrics['total_executions'], initial_metrics['total_executions'] + 1)
        self.assertEqual(updated_metrics['successful_executions'], initial_metrics['successful_executions'] + 1)
        self.assertGreater(updated_metrics['total_duration_ms'], initial_metrics['total_duration_ms'])
        
    async def test_failed_execution_metrics(self):
        """Test metrics tracking for failed executions."""
        initial_metrics = self.execution_engine.get_execution_metrics()
        
        # Execute failing tool
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "bad_data.csv"},
            request_id=self.user_context.run_id
        )
        
        await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.failing_tool,
            kwargs={"context": self.agent_context, "dataset": "bad_data.csv"}
        )
        
        # Check failure metrics
        updated_metrics = self.execution_engine.get_execution_metrics()
        self.assertEqual(updated_metrics['failed_executions'], initial_metrics['failed_executions'] + 1)
        
    # ===================== PROGRESS UPDATE TESTS =====================
        
    async def test_progress_updates_for_long_running_tools(self):
        """Test progress update notifications for long-running tools."""
        # Send progress updates manually (simulating long-running tool behavior)
        await self.execution_engine.send_progress_update(
            context=self.agent_context,
            tool_name="long_runner",
            progress_percentage=25.0,
            status_message="Processing step 1 of 4"
        )
        
        await self.execution_engine.send_progress_update(
            context=self.agent_context,
            tool_name="long_runner",
            progress_percentage=75.0,
            status_message="Processing step 3 of 4"
        )
        
        # Verify progress updates were sent
        self.assertEqual(len(self.websocket_bridge.progress_update_calls), 2)
        
        # Verify progress update details
        first_update = self.websocket_bridge.progress_update_calls[0]
        self.assertEqual(first_update["progress"]["percentage"], 25.0)
        self.assertEqual(first_update["progress"]["message"], "Processing step 1 of 4")
        
        second_update = self.websocket_bridge.progress_update_calls[1]
        self.assertEqual(second_update["progress"]["percentage"], 75.0)
        self.assertIn("estimated_remaining_ms", second_update["progress"])
        
    # ===================== TOOL DISPATCHER ENHANCEMENT TEST =====================
        
    async def test_tool_dispatcher_enhancement(self):
        """Test the enhance_tool_dispatcher_with_notifications function."""
        # Create mock tool dispatcher
        mock_dispatcher = MagicMock()
        mock_dispatcher._websocket_enhanced = False
        mock_dispatcher.executor = MagicMock()
        
        # Mock WebSocket manager
        mock_websocket_manager = MagicMock()
        
        # Enhance the dispatcher
        enhanced_dispatcher = await enhance_tool_dispatcher_with_notifications(
            tool_dispatcher=mock_dispatcher,
            websocket_manager=mock_websocket_manager,
            enable_notifications=True
        )
        
        # Verify enhancement
        self.assertTrue(enhanced_dispatcher._websocket_enhanced)
        self.assertIsInstance(enhanced_dispatcher.executor, UnifiedToolExecutionEngine)
        
    async def test_backward_compatibility_alias(self):
        """Test that EnhancedToolExecutionEngine alias works correctly."""
        # Verify alias is set correctly
        self.assertIs(EnhancedToolExecutionEngine, UnifiedToolExecutionEngine)
        
        # Create instance via alias
        engine_via_alias = EnhancedToolExecutionEngine(
            websocket_bridge=self.websocket_bridge
        )
        
        # Verify it's the same class
        self.assertIsInstance(engine_via_alias, UnifiedToolExecutionEngine)
        
        # Verify functionality works the same
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters={"dataset": "alias_test.csv"},
            request_id=self.user_context.run_id
        )
        
        result = await engine_via_alias.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.data_tool,
            kwargs={"context": self.agent_context, "dataset": "alias_test.csv"}
        )
        
        self.assertEqual(result.status, ToolStatus.SUCCESS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])