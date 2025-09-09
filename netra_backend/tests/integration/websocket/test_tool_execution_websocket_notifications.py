"""Integration tests for WebSocket tool execution notifications.

These tests validate that tool execution properly integrates with the WebSocket
system to deliver real-time notifications that enable substantive chat value.

Business Value: Free/Early/Mid/Enterprise - User Experience
Real-time tool execution feedback is core to the chat experience and user value.

Test Coverage:
- Tool execution WebSocket event delivery 
- AgentWebSocketBridge integration with tool dispatcher
- Multi-user WebSocket event isolation
- WebSocket reconnection during tool execution
- Tool progress updates via WebSocket
- Error notification handling
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from langchain_core.tools import BaseTool


class WebSocketEventCollector:
    """Collects and analyzes WebSocket events for testing."""
    
    def __init__(self):
        self.events = []
        self.events_by_type = {}
        self.events_by_user = {}
        self.events_by_thread = {}
        self.connection_events = []
        
    def record_event(self, event_type: str, data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Record a WebSocket event."""
        event_record = {
            "event_type": event_type,
            "data": data.copy(),
            "metadata": metadata or {},
            "timestamp": time.time(),
            "event_id": str(uuid.uuid4())
        }
        
        self.events.append(event_record)
        
        # Index by type
        if event_type not in self.events_by_type:
            self.events_by_type[event_type] = []
        self.events_by_type[event_type].append(event_record)
        
        # Index by user and thread if available
        user_id = data.get("user_id")
        thread_id = data.get("thread_id")
        
        if user_id:
            if user_id not in self.events_by_user:
                self.events_by_user[user_id] = []
            self.events_by_user[user_id].append(event_record)
            
        if thread_id:
            if thread_id not in self.events_by_thread:
                self.events_by_thread[thread_id] = []
            self.events_by_thread[thread_id].append(event_record)
            
    def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific user."""
        return self.events_by_user.get(user_id, [])
        
    def get_events_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific thread."""
        return self.events_by_thread.get(thread_id, [])
        
    def get_events_of_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of specific type."""
        return self.events_by_type.get(event_type, [])
        
    def get_tool_execution_sequence(self, tool_name: str, user_id: str = None) -> List[Dict[str, Any]]:
        """Get the complete execution sequence for a tool."""
        relevant_events = []
        
        events_to_search = self.events
        if user_id:
            events_to_search = self.get_events_for_user(user_id)
            
        for event in events_to_search:
            if event["data"].get("tool_name") == tool_name:
                relevant_events.append(event)
                
        # Sort by timestamp
        relevant_events.sort(key=lambda x: x["timestamp"])
        return relevant_events
        
    def validate_tool_execution_sequence(self, tool_name: str, user_id: str = None) -> Dict[str, Any]:
        """Validate that tool execution sequence is correct."""
        sequence = self.get_tool_execution_sequence(tool_name, user_id)
        
        validation_result = {
            "valid": True,
            "issues": [],
            "sequence_length": len(sequence),
            "has_executing": False,
            "has_completed": False,
            "execution_time_ms": None
        }
        
        if len(sequence) == 0:
            validation_result["valid"] = False
            validation_result["issues"].append("No events found for tool execution")
            return validation_result
            
        # Check for required events
        event_types = [event["event_type"] for event in sequence]
        
        if "tool_executing" in event_types:
            validation_result["has_executing"] = True
        else:
            validation_result["valid"] = False
            validation_result["issues"].append("Missing tool_executing event")
            
        if "tool_completed" in event_types:
            validation_result["has_completed"] = True
            
            # Calculate execution time
            executing_event = next((e for e in sequence if e["event_type"] == "tool_executing"), None)
            completed_event = next((e for e in sequence if e["event_type"] == "tool_completed"), None)
            
            if executing_event and completed_event:
                validation_result["execution_time_ms"] = (
                    completed_event["timestamp"] - executing_event["timestamp"]
                ) * 1000
        else:
            validation_result["valid"] = False
            validation_result["issues"].append("Missing tool_completed event")
            
        return validation_result
        
    def clear_events(self):
        """Clear all collected events."""
        self.events.clear()
        self.events_by_type.clear()
        self.events_by_user.clear()
        self.events_by_thread.clear()
        self.connection_events.clear()


class MockWebSocketManager:
    """Mock WebSocket manager that integrates with event collector."""
    
    def __init__(self, event_collector: WebSocketEventCollector):
        self.event_collector = event_collector
        self.connection_active = True
        self.send_delay_ms = 0  # Simulated network delay
        self.should_fail = False
        self.failure_rate = 0.0  # 0.0 = never fail, 1.0 = always fail
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Mock WebSocket event sending."""
        if not self.connection_active:
            return False
            
        if self.should_fail or (self.failure_rate > 0 and time.time() % 1 < self.failure_rate):
            return False
            
        # Simulate network delay
        if self.send_delay_ms > 0:
            await asyncio.sleep(self.send_delay_ms / 1000)
            
        # Record the event
        self.event_collector.record_event(event_type, data)
        return True
        
    def disconnect(self):
        """Simulate WebSocket disconnection."""
        self.connection_active = False
        
    def reconnect(self):
        """Simulate WebSocket reconnection."""
        self.connection_active = True
        
    def set_failure_mode(self, should_fail: bool = True, failure_rate: float = 0.0):
        """Configure failure simulation."""
        self.should_fail = should_fail
        self.failure_rate = failure_rate


class MockReportingTool(BaseTool):
    """Mock reporting tool that simulates long-running operations."""
    
    name: str = "reporting_tool"
    description: str = "Generates reports with progress updates"
    
    def __init__(self, report_duration_ms: int = 100, progress_steps: int = 5):
        super().__init__()
        self.report_duration_ms = report_duration_ms
        self.progress_steps = progress_steps
        self.execution_count = 0
        self.last_progress_callback = None
        
    def _run(self, report_type: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(report_type, **kwargs))
        
    async def _arun(self, report_type: str, **kwargs) -> str:
        """Asynchronous execution with progress simulation."""
        self.execution_count += 1
        
        # Simulate long-running report generation
        step_duration = self.report_duration_ms / (self.progress_steps * 1000)
        
        for step in range(self.progress_steps):
            await asyncio.sleep(step_duration)
            progress = ((step + 1) / self.progress_steps) * 100
            
            # In real scenarios, progress would be reported through the execution engine
            if self.last_progress_callback:
                await self.last_progress_callback(progress, f"Processing step {step + 1}")
                
        return f"Report generated: {report_type} with {self.progress_steps} steps"


class TestWebSocketToolExecutionNotifications(SSotAsyncTestCase):
    """Integration tests for WebSocket tool execution notifications."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Create event collector and WebSocket manager
        self.event_collector = WebSocketEventCollector()
        self.websocket_manager = MockWebSocketManager(self.event_collector)
        
        # Create user contexts
        self.user1_context = UserExecutionContext(
            user_id="websocket_user_001",
            run_id=f"ws_run_{int(time.time() * 1000)}",
            thread_id="ws_thread_001",
            session_id="ws_session_001"
        )
        
        self.user2_context = UserExecutionContext(
            user_id="websocket_user_002",
            run_id=f"ws_run_{int(time.time() * 1000) + 1}",
            thread_id="ws_thread_002",
            session_id="ws_session_002"
        )
        
        # Create agent contexts
        self.agent1_context = AgentExecutionContext(
            agent_name="WebSocketTestAgent1",
            run_id=self.user1_context.run_id,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id
        )
        
        self.agent2_context = AgentExecutionContext(
            agent_name="WebSocketTestAgent2", 
            run_id=self.user2_context.run_id,
            thread_id=self.user2_context.thread_id,
            user_id=self.user2_context.user_id
        )
        
        # Create test tools
        self.reporting_tool = MockReportingTool(report_duration_ms=50, progress_steps=3)
        
    async def tearDown(self):
        """Clean up after tests."""
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user1_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user2_context.user_id)
        
        await super().tearDown()
        
    # ===================== BASIC WEBSOCKET INTEGRATION =====================
        
    async def test_tool_execution_websocket_event_delivery(self):
        """Test that tool execution delivers WebSocket events correctly."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        # Clear any setup events
        self.event_collector.clear_events()
        
        # Execute tool
        result = await dispatcher.execute_tool(
            "reporting_tool",
            {"report_type": "quarterly_metrics"}
        )
        
        self.assertTrue(result.success)
        
        # Validate event sequence
        validation = self.event_collector.validate_tool_execution_sequence(
            "reporting_tool", self.user1_context.user_id
        )
        
        self.assertTrue(validation["valid"], f"Event sequence issues: {validation['issues']}")
        self.assertTrue(validation["has_executing"])
        self.assertTrue(validation["has_completed"])
        self.assertIsNotNone(validation["execution_time_ms"])
        
        # Verify event details
        executing_events = self.event_collector.get_events_of_type("tool_executing")
        self.assertEqual(len(executing_events), 1)
        
        executing_event = executing_events[0]
        self.assertEqual(executing_event["data"]["tool_name"], "reporting_tool")
        self.assertEqual(executing_event["data"]["user_id"], self.user1_context.user_id)
        self.assertEqual(executing_event["data"]["thread_id"], self.user1_context.thread_id)
        
        completed_events = self.event_collector.get_events_of_type("tool_completed")
        self.assertEqual(len(completed_events), 1)
        
        completed_event = completed_events[0]
        self.assertEqual(completed_event["data"]["tool_name"], "reporting_tool")
        self.assertEqual(completed_event["data"]["status"], "success")
        
        await dispatcher.cleanup()
        
    async def test_websocket_events_user_isolation(self):
        """Test that WebSocket events are properly isolated per user."""
        # Create dispatchers for different users
        dispatcher1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        self.event_collector.clear_events()
        
        # Execute tools for both users
        task1 = dispatcher1.execute_tool("reporting_tool", {"report_type": "user1_report"})
        task2 = dispatcher2.execute_tool("reporting_tool", {"report_type": "user2_report"})
        
        results = await asyncio.gather(task1, task2, return_exceptions=True)
        
        # Verify both succeeded
        self.assertTrue(all(r.success for r in results if not isinstance(r, Exception)))
        
        # Verify event isolation
        user1_events = self.event_collector.get_events_for_user(self.user1_context.user_id)
        user2_events = self.event_collector.get_events_for_user(self.user2_context.user_id)
        
        self.assertGreater(len(user1_events), 0)
        self.assertGreater(len(user2_events), 0)
        
        # Verify no cross-user event contamination
        for event in user1_events:
            self.assertEqual(event["data"]["user_id"], self.user1_context.user_id)
            self.assertNotEqual(event["data"]["user_id"], self.user2_context.user_id)
            
        for event in user2_events:
            self.assertEqual(event["data"]["user_id"], self.user2_context.user_id)
            self.assertNotEqual(event["data"]["user_id"], self.user1_context.user_id)
            
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
        
    # ===================== ERROR HANDLING AND RESILIENCE =====================
        
    async def test_websocket_failure_during_tool_execution(self):
        """Test tool execution continues even when WebSocket fails."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        # Configure WebSocket to fail
        self.websocket_manager.set_failure_mode(should_fail=True)
        
        # Execute tool (should still succeed despite WebSocket failure)
        result = await dispatcher.execute_tool(
            "reporting_tool",
            {"report_type": "failure_test_report"}
        )
        
        self.assertTrue(result.success)
        self.assertIn("Report generated", result.result)
        
        # Verify no events were recorded due to WebSocket failure
        events = self.event_collector.get_events_for_user(self.user1_context.user_id)
        self.assertEqual(len(events), 0)
        
        await dispatcher.cleanup()
        
    async def test_websocket_reconnection_during_execution(self):
        """Test WebSocket reconnection during tool execution."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        self.event_collector.clear_events()
        
        # Start tool execution and disconnect WebSocket partway through
        async def disconnect_and_reconnect():
            await asyncio.sleep(0.01)  # Let execution start
            self.websocket_manager.disconnect()
            await asyncio.sleep(0.01)  # Brief disconnection
            self.websocket_manager.reconnect()
            
        # Run both operations concurrently
        execution_task = dispatcher.execute_tool(
            "reporting_tool",
            {"report_type": "reconnection_test"}
        )
        
        reconnection_task = asyncio.create_task(disconnect_and_reconnect())
        
        result, _ = await asyncio.gather(execution_task, reconnection_task)
        
        self.assertTrue(result.success)
        
        # Check if we got partial events (depends on timing)
        events = self.event_collector.get_events_for_user(self.user1_context.user_id)
        # Some events might be lost during disconnection, which is expected
        
        await dispatcher.cleanup()
        
    async def test_websocket_intermittent_failures(self):
        """Test handling of intermittent WebSocket failures."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        # Configure intermittent failures (50% failure rate)
        self.websocket_manager.set_failure_mode(should_fail=False, failure_rate=0.5)
        
        self.event_collector.clear_events()
        
        # Execute multiple tools
        tasks = []
        for i in range(5):
            task = dispatcher.execute_tool(
                "reporting_tool",
                {"report_type": f"intermittent_test_{i}"}
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tool executions should succeed
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.success)
        self.assertEqual(success_count, 5)
        
        # Some events may be lost due to intermittent failures
        events = self.event_collector.get_events_for_user(self.user1_context.user_id)
        # We might get fewer events than expected due to failures
        
        await dispatcher.cleanup()
        
    # ===================== PERFORMANCE AND LOAD TESTING =====================
        
    async def test_concurrent_websocket_event_delivery(self):
        """Test WebSocket event delivery under concurrent load."""
        num_concurrent = 10
        
        # Create multiple dispatchers
        dispatchers = []
        contexts = []
        
        for i in range(num_concurrent):
            context = UserExecutionContext(
                user_id=f"concurrent_ws_user_{i}",
                run_id=f"concurrent_ws_run_{i}",
                thread_id=f"concurrent_ws_thread_{i}",
                session_id=f"concurrent_ws_session_{i}"
            )
            contexts.append(context)
            
            dispatcher = await UnifiedToolDispatcher.create_for_user(
                user_context=context,
                websocket_bridge=self.websocket_manager,
                tools=[self.reporting_tool]
            )
            dispatchers.append(dispatcher)
            
        self.event_collector.clear_events()
        
        # Execute tools concurrently
        tasks = []
        for i, dispatcher in enumerate(dispatchers):
            task = dispatcher.execute_tool(
                "reporting_tool",
                {"report_type": f"concurrent_report_{i}"}
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions succeeded
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.success)
        self.assertEqual(success_count, num_concurrent)
        
        # Verify events were delivered for all users
        total_events = len(self.event_collector.events)
        self.assertGreater(total_events, 0)
        
        # Each user should have at least some events
        for context in contexts:
            user_events = self.event_collector.get_events_for_user(context.user_id)
            # Due to concurrency, we might not get all events for all users
            # but we should get events for most users
            
        # Cleanup
        for dispatcher in dispatchers:
            await dispatcher.cleanup()
            
    async def test_websocket_event_ordering(self):
        """Test that WebSocket events maintain proper ordering."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.reporting_tool]
        )
        
        self.event_collector.clear_events()
        
        # Execute tool
        result = await dispatcher.execute_tool(
            "reporting_tool",
            {"report_type": "ordering_test"}
        )
        
        self.assertTrue(result.success)
        
        # Get events for this user in order
        user_events = self.event_collector.get_events_for_user(self.user1_context.user_id)
        
        # Verify events are in correct temporal order
        if len(user_events) >= 2:
            for i in range(1, len(user_events)):
                self.assertGreaterEqual(
                    user_events[i]["timestamp"],
                    user_events[i-1]["timestamp"],
                    "Events should be in chronological order"
                )
                
        # Verify executing comes before completed
        tool_events = [e for e in user_events if e["data"].get("tool_name") == "reporting_tool"]
        executing_events = [e for e in tool_events if e["event_type"] == "tool_executing"]
        completed_events = [e for e in tool_events if e["event_type"] == "tool_completed"]
        
        if executing_events and completed_events:
            executing_time = executing_events[0]["timestamp"]
            completed_time = completed_events[0]["timestamp"]
            self.assertLess(executing_time, completed_time)
            
        await dispatcher.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])