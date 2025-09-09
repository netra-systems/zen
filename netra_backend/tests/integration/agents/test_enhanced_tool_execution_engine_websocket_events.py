"""Integration tests for Enhanced Tool Execution Engine WebSocket events.

These tests validate the complete integration between the UnifiedToolExecutionEngine
and the WebSocket system, ensuring real tool execution generates proper events
for the chat experience.

Business Value: Free/Early/Mid/Enterprise - Chat Experience
Real-time tool execution feedback is essential for substantive AI chat interactions.

Test Coverage:
- Real tool execution with WebSocket event generation
- AgentWebSocketBridge adapter functionality
- Tool dispatcher enhancement with WebSocket notifications
- Multi-agent tool execution event coordination
- WebSocket event ordering and timing validation
- Real tool registry integration with events
"""

import asyncio
import json
import pytest
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications,
    EnhancedToolExecutionEngine
)
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from langchain_core.tools import BaseTool


class IntegrationWebSocketEventTracker:
    """Comprehensive WebSocket event tracker for integration testing."""
    
    def __init__(self):
        self.all_events = []
        self.events_by_agent = defaultdict(list)
        self.events_by_user = defaultdict(list)
        self.events_by_tool = defaultdict(list)
        self.event_sequences = defaultdict(list)  # Track event sequences per run_id
        self.timing_data = {}
        
    def record_event(self, event_type: str, run_id: str, agent_name: str, data: Dict[str, Any]):
        """Record a WebSocket event with full context."""
        timestamp = time.time()
        
        event_record = {
            "event_type": event_type,
            "run_id": run_id,
            "agent_name": agent_name,
            "data": data.copy(),
            "timestamp": timestamp,
            "event_id": str(uuid.uuid4())
        }
        
        # Store in all collections
        self.all_events.append(event_record)
        self.events_by_agent[agent_name].append(event_record)
        
        user_id = data.get("user_id")
        if user_id:
            self.events_by_user[user_id].append(event_record)
            
        tool_name = data.get("tool_name")
        if tool_name:
            self.events_by_tool[tool_name].append(event_record)
            
        # Track sequence for run_id
        self.event_sequences[run_id].append(event_record)
        
        # Track timing
        if run_id not in self.timing_data:
            self.timing_data[run_id] = {"first_event": timestamp}
        self.timing_data[run_id]["last_event"] = timestamp
        
    def get_complete_tool_sequence(self, tool_name: str, run_id: str = None) -> List[Dict[str, Any]]:
        """Get complete event sequence for a tool execution."""
        if run_id:
            # Get events for specific run
            events = [e for e in self.event_sequences[run_id] if e["data"].get("tool_name") == tool_name]
        else:
            # Get all events for tool
            events = self.events_by_tool[tool_name]
            
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        return events
        
    def validate_tool_execution_flow(self, tool_name: str, run_id: str = None) -> Dict[str, Any]:
        """Validate complete tool execution event flow."""
        sequence = self.get_complete_tool_sequence(tool_name, run_id)
        
        validation = {
            "valid": True,
            "issues": [],
            "event_count": len(sequence),
            "has_executing": False,
            "has_completed": False,
            "has_proper_ordering": True,
            "execution_duration_ms": None,
            "event_types": [e["event_type"] for e in sequence]
        }
        
        if not sequence:
            validation["valid"] = False
            validation["issues"].append("No events found for tool execution")
            return validation
            
        # Check for required events
        event_types = set(validation["event_types"])
        
        if "tool_executing" in event_types:
            validation["has_executing"] = True
        else:
            validation["valid"] = False
            validation["issues"].append("Missing tool_executing event")
            
        if "tool_completed" in event_types:
            validation["has_completed"] = True
        else:
            validation["valid"] = False
            validation["issues"].append("Missing tool_completed event")
            
        # Check event ordering
        if validation["has_executing"] and validation["has_completed"]:
            executing_events = [e for e in sequence if e["event_type"] == "tool_executing"]
            completed_events = [e for e in sequence if e["event_type"] == "tool_completed"]
            
            if executing_events and completed_events:
                first_executing = min(executing_events, key=lambda x: x["timestamp"])
                last_completed = max(completed_events, key=lambda x: x["timestamp"])
                
                if first_executing["timestamp"] >= last_completed["timestamp"]:
                    validation["valid"] = False
                    validation["has_proper_ordering"] = False
                    validation["issues"].append("tool_executing should come before tool_completed")
                    
                # Calculate execution duration
                validation["execution_duration_ms"] = (
                    last_completed["timestamp"] - first_executing["timestamp"]
                ) * 1000
                
        return validation
        
    def get_agent_event_timeline(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get chronological event timeline for an agent."""
        events = self.events_by_agent[agent_name]
        events.sort(key=lambda x: x["timestamp"])
        return events
        
    def analyze_multi_agent_coordination(self) -> Dict[str, Any]:
        """Analyze coordination between multiple agents."""
        analysis = {
            "total_agents": len(self.events_by_agent),
            "agent_names": list(self.events_by_agent.keys()),
            "event_overlap": False,
            "concurrent_executions": 0,
            "coordination_issues": []
        }
        
        # Check for concurrent tool executions
        all_executing_events = [e for e in self.all_events if e["event_type"] == "tool_executing"]
        all_completed_events = [e for e in self.all_events if e["event_type"] == "tool_completed"]
        
        # Simple concurrent execution detection
        for executing_event in all_executing_events:
            concurrent_count = 0
            for other_executing in all_executing_events:
                if (other_executing["event_id"] != executing_event["event_id"] and
                    abs(other_executing["timestamp"] - executing_event["timestamp"]) < 0.1):  # Within 100ms
                    concurrent_count += 1
                    
            if concurrent_count > 0:
                analysis["event_overlap"] = True
                analysis["concurrent_executions"] = max(analysis["concurrent_executions"], concurrent_count + 1)
                
        return analysis
        
    def clear_events(self):
        """Clear all tracked events."""
        self.all_events.clear()
        self.events_by_agent.clear()
        self.events_by_user.clear()
        self.events_by_tool.clear()
        self.event_sequences.clear()
        self.timing_data.clear()


class MockIntegratedWebSocketManager:
    """Mock WebSocket manager that integrates with the event tracker."""
    
    def __init__(self, event_tracker: IntegrationWebSocketEventTracker):
        self.event_tracker = event_tracker
        self.connection_active = True
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send event and record in tracker."""
        if not self.connection_active:
            return False
            
        run_id = data.get("run_id", "unknown")
        agent_name = data.get("agent_name", "unknown")
        
        self.event_tracker.record_event(event_type, run_id, agent_name, data)
        return True


class ComprehensiveAnalyticsTool(BaseTool):
    """Comprehensive analytics tool for testing complete workflows."""
    
    name = "comprehensive_analytics"
    description = "Performs comprehensive data analytics with multiple phases"
    
    def __init__(self, phases: int = 3, phase_duration_ms: int = 10):
        super().__init__()
        self.phases = phases
        self.phase_duration_ms = phase_duration_ms
        self.execution_count = 0
        self.last_context = None
        self.phase_results = []
        
    def _run(self, dataset: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(dataset, **kwargs))
        
    async def _arun(self, dataset: str, **kwargs) -> str:
        """Multi-phase asynchronous execution."""
        self.execution_count += 1
        self.last_context = kwargs.get('context')
        self.phase_results.clear()
        
        # Execute multiple phases
        for phase in range(self.phases):
            await asyncio.sleep(self.phase_duration_ms / 1000)
            
            phase_result = f"Phase {phase + 1}: Analyzed {dataset} segment {phase + 1}/{self.phases}"
            self.phase_results.append(phase_result)
            
        final_result = {
            "dataset": dataset,
            "phases_completed": self.phases,
            "total_execution": self.execution_count,
            "results": self.phase_results
        }
        
        return json.dumps(final_result)


class DataVisualizationTool(BaseTool):
    """Data visualization tool for testing multi-tool workflows."""
    
    name = "data_visualization"
    description = "Creates visualizations from analytics data"
    
    def __init__(self, chart_types: List[str] = None):
        super().__init__()
        self.chart_types = chart_types or ["bar", "line", "scatter"]
        self.execution_count = 0
        self.created_charts = []
        
    def _run(self, data_source: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(data_source, **kwargs))
        
    async def _arun(self, data_source: str, **kwargs) -> str:
        """Asynchronous chart generation."""
        self.execution_count += 1
        self.created_charts.clear()
        
        # Generate charts
        for chart_type in self.chart_types:
            await asyncio.sleep(0.005)  # 5ms per chart
            chart_info = f"{chart_type}_chart_{self.execution_count}_{chart_type}"
            self.created_charts.append(chart_info)
            
        result = {
            "data_source": data_source,
            "charts_created": self.created_charts,
            "chart_count": len(self.created_charts)
        }
        
        return json.dumps(result)


class TestEnhancedToolExecutionEngineWebSocketEvents(SSotAsyncTestCase):
    """Integration tests for Enhanced Tool Execution Engine WebSocket events."""
    
    def setUp(self):
        """Set up comprehensive integration test environment."""
        super().setUp()
        
        # Create event tracking system
        self.event_tracker = IntegrationWebSocketEventTracker()
        self.websocket_manager = MockIntegratedWebSocketManager(self.event_tracker)
        
        # Create user contexts
        self.user1_context = UserExecutionContext(
            user_id="integration_user_001",
            run_id=f"integration_run_{int(time.time() * 1000)}",
            thread_id="integration_thread_001",
            session_id="integration_session_001"
        )
        
        self.user2_context = UserExecutionContext(
            user_id="integration_user_002",
            run_id=f"integration_run_{int(time.time() * 1000) + 1}",
            thread_id="integration_thread_002",
            session_id="integration_session_002"
        )
        
        # Create agent contexts
        self.analytics_agent_context = AgentExecutionContext(
            agent_name="AnalyticsAgent",
            run_id=self.user1_context.run_id,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id
        )
        
        self.visualization_agent_context = AgentExecutionContext(
            agent_name="VisualizationAgent",
            run_id=self.user2_context.run_id,
            thread_id=self.user2_context.thread_id,
            user_id=self.user2_context.user_id
        )
        
        # Create comprehensive test tools
        self.analytics_tool = ComprehensiveAnalyticsTool(phases=3, phase_duration_ms=20)
        self.visualization_tool = DataVisualizationTool(["bar", "line", "scatter", "heatmap"])
        
        # Create tool registry
        self.tool_registry = UniversalRegistry[BaseTool]("IntegrationToolRegistry")
        self.tool_registry.register("analytics", self.analytics_tool)
        self.tool_registry.register("visualization", self.visualization_tool)
        
    async def tearDown(self):
        """Clean up after integration tests."""
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user1_context.user_id)
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user2_context.user_id)
        
        await super().tearDown()
        
    # ===================== COMPREHENSIVE INTEGRATION TESTS =====================
        
    async def test_complete_tool_execution_websocket_integration(self):
        """Test complete integration of tool execution with WebSocket events."""
        # Create enhanced tool execution engine
        execution_engine = UnifiedToolExecutionEngine(
            websocket_bridge=self.websocket_manager
        )
        
        # Execute comprehensive analytics tool
        tool_input = ToolInput(
            tool_name="comprehensive_analytics",
            parameters={"dataset": "quarterly_sales_data"},
            request_id=self.user1_context.run_id
        )
        
        self.event_tracker.clear_events()
        
        result = await execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.analytics_tool,
            kwargs={"context": self.analytics_agent_context, "dataset": "quarterly_sales_data"}
        )
        
        # Verify tool execution succeeded
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        self.assertIsNotNone(result.payload.result)
        
        # Validate WebSocket event flow
        validation = self.event_tracker.validate_tool_execution_flow(
            "comprehensive_analytics", self.user1_context.run_id
        )
        
        self.assertTrue(validation["valid"], f"Event flow issues: {validation['issues']}")
        self.assertTrue(validation["has_executing"])
        self.assertTrue(validation["has_completed"])
        self.assertTrue(validation["has_proper_ordering"])
        self.assertIsNotNone(validation["execution_duration_ms"])
        self.assertGreater(validation["execution_duration_ms"], 0)
        
        # Verify event content
        sequence = self.event_tracker.get_complete_tool_sequence("comprehensive_analytics", self.user1_context.run_id)
        
        executing_event = next(e for e in sequence if e["event_type"] == "tool_executing")
        self.assertEqual(executing_event["agent_name"], "AnalyticsAgent")
        self.assertEqual(executing_event["data"]["user_id"], self.user1_context.user_id)
        self.assertIn("parameters", executing_event["data"])
        
        completed_event = next(e for e in sequence if e["event_type"] == "tool_completed")
        self.assertEqual(completed_event["data"]["status"], "success")
        self.assertIn("result", completed_event["data"])
        
    async def test_tool_dispatcher_websocket_enhancement_integration(self):
        """Test integration of tool dispatcher WebSocket enhancement."""
        # Create tool dispatcher
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, self.visualization_tool]
        )
        
        # Enhance with WebSocket notifications (should already be enhanced)
        enhanced_dispatcher = await enhance_tool_dispatcher_with_notifications(
            tool_dispatcher=dispatcher,
            websocket_manager=self.websocket_manager,
            enable_notifications=True
        )
        
        self.event_tracker.clear_events()
        
        # Execute tool through enhanced dispatcher
        result = await enhanced_dispatcher.execute_tool(
            "comprehensive_analytics",
            {"dataset": "integration_test_data"}
        )
        
        self.assertTrue(result.success)
        
        # Validate enhancement worked
        validation = self.event_tracker.validate_tool_execution_flow("comprehensive_analytics")
        self.assertTrue(validation["valid"])
        self.assertGreater(validation["event_count"], 0)
        
        await dispatcher.cleanup()
        
    async def test_multi_agent_tool_execution_coordination(self):
        """Test WebSocket event coordination across multiple agents."""
        # Create dispatchers for different agents
        analytics_dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool]
        )
        
        visualization_dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user2_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.visualization_tool]
        )
        
        self.event_tracker.clear_events()
        
        # Execute tools concurrently from different agents
        analytics_task = analytics_dispatcher.execute_tool(
            "comprehensive_analytics",
            {"dataset": "multi_agent_analytics_data"}
        )
        
        visualization_task = visualization_dispatcher.execute_tool(
            "data_visualization",
            {"data_source": "multi_agent_visualization_source"}
        )
        
        results = await asyncio.gather(analytics_task, visualization_task, return_exceptions=True)
        
        # Verify both executions succeeded
        self.assertTrue(all(r.success for r in results if not isinstance(r, Exception)))
        
        # Analyze multi-agent coordination
        coordination_analysis = self.event_tracker.analyze_multi_agent_coordination()
        
        self.assertEqual(coordination_analysis["total_agents"], 2)
        self.assertIn("AnalyticsAgent", coordination_analysis["agent_names"])
        self.assertIn("VisualizationAgent", coordination_analysis["agent_names"])
        
        # Verify each agent has its own event timeline
        analytics_timeline = self.event_tracker.get_agent_event_timeline("AnalyticsAgent")
        visualization_timeline = self.event_tracker.get_agent_event_timeline("VisualizationAgent")
        
        self.assertGreater(len(analytics_timeline), 0)
        self.assertGreater(len(visualization_timeline), 0)
        
        # Verify events are properly isolated by agent
        for event in analytics_timeline:
            self.assertEqual(event["agent_name"], "AnalyticsAgent")
            
        for event in visualization_timeline:
            self.assertEqual(event["agent_name"], "VisualizationAgent")
            
        await analytics_dispatcher.cleanup()
        await visualization_dispatcher.cleanup()
        
    async def test_tool_registry_integration_with_websocket_events(self):
        """Test integration between tool registry and WebSocket events."""
        # Create dispatcher with tool registry
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager
        )
        
        # Populate dispatcher with tools from registry
        await dispatcher._populate_tools_from_registry(self.tool_registry)
        
        # Verify tools were registered
        self.assertTrue(dispatcher.has_tool("analytics"))
        self.assertTrue(dispatcher.has_tool("visualization"))
        
        self.event_tracker.clear_events()
        
        # Execute tools from registry
        analytics_result = await dispatcher.execute_tool("analytics", {"dataset": "registry_test_data"})
        visualization_result = await dispatcher.execute_tool("visualization", {"data_source": "registry_viz_data"})
        
        self.assertTrue(analytics_result.success)
        self.assertTrue(visualization_result.success)
        
        # Verify WebSocket events were generated for registry tools
        analytics_validation = self.event_tracker.validate_tool_execution_flow("comprehensive_analytics")
        visualization_validation = self.event_tracker.validate_tool_execution_flow("data_visualization")
        
        self.assertTrue(analytics_validation["valid"])
        self.assertTrue(visualization_validation["valid"])
        
        await dispatcher.cleanup()
        
    # ===================== EVENT TIMING AND ORDERING TESTS =====================
        
    async def test_websocket_event_timing_accuracy(self):
        """Test accuracy of WebSocket event timing."""
        execution_engine = UnifiedToolExecutionEngine(
            websocket_bridge=self.websocket_manager
        )
        
        self.event_tracker.clear_events()
        
        # Record start time
        start_time = time.time()
        
        # Execute tool with known duration
        tool_input = ToolInput(
            tool_name="comprehensive_analytics",
            parameters={"dataset": "timing_test_data"},
            request_id=self.user1_context.run_id
        )
        
        result = await execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.analytics_tool,
            kwargs={"context": self.analytics_agent_context, "dataset": "timing_test_data"}
        )
        
        end_time = time.time()
        actual_duration_ms = (end_time - start_time) * 1000
        
        self.assertTrue(result.status == ToolStatus.SUCCESS)
        
        # Validate event timing
        validation = self.event_tracker.validate_tool_execution_flow(
            "comprehensive_analytics", self.user1_context.run_id
        )
        
        event_duration_ms = validation["execution_duration_ms"]
        self.assertIsNotNone(event_duration_ms)
        
        # Event duration should be reasonably close to actual duration
        timing_tolerance = 100  # 100ms tolerance
        self.assertLess(
            abs(event_duration_ms - actual_duration_ms),
            timing_tolerance,
            f"Event timing ({event_duration_ms}ms) differs too much from actual ({actual_duration_ms}ms)"
        )
        
    async def test_concurrent_tool_execution_event_ordering(self):
        """Test WebSocket event ordering during concurrent tool executions."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool, self.visualization_tool]
        )
        
        self.event_tracker.clear_events()
        
        # Execute multiple tools with slight delays to test ordering
        tasks = []
        
        for i in range(3):
            # Alternate between tools
            if i % 2 == 0:
                task = dispatcher.execute_tool("comprehensive_analytics", {"dataset": f"concurrent_data_{i}"})
            else:
                task = dispatcher.execute_tool("data_visualization", {"data_source": f"concurrent_viz_{i}"})
            
            tasks.append(task)
            await asyncio.sleep(0.01)  # Small delay between starts
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        self.assertTrue(all(r.success for r in results if not isinstance(r, Exception)))
        
        # Analyze event ordering
        all_events = sorted(self.event_tracker.all_events, key=lambda x: x["timestamp"])
        
        # Verify events are in chronological order
        for i in range(1, len(all_events)):
            self.assertGreaterEqual(
                all_events[i]["timestamp"],
                all_events[i-1]["timestamp"],
                "Events should be in chronological order"
            )
            
        # Verify each tool execution has proper event sequence
        for tool_name in ["comprehensive_analytics", "data_visualization"]:
            tool_events = [e for e in all_events if e["data"].get("tool_name") == tool_name]
            
            if tool_events:
                # Group by run_id
                events_by_run = defaultdict(list)
                for event in tool_events:
                    events_by_run[event["run_id"]].append(event)
                    
                # Verify each run has proper sequence
                for run_events in events_by_run.values():
                    run_events.sort(key=lambda x: x["timestamp"])
                    event_types = [e["event_type"] for e in run_events]
                    
                    # Should have executing before completed
                    if "tool_executing" in event_types and "tool_completed" in event_types:
                        executing_index = event_types.index("tool_executing")
                        completed_index = event_types.index("tool_completed")
                        self.assertLess(executing_index, completed_index)
                        
        await dispatcher.cleanup()
        
    async def test_websocket_event_data_completeness(self):
        """Test completeness of WebSocket event data."""
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user1_context,
            websocket_bridge=self.websocket_manager,
            tools=[self.analytics_tool]
        )
        
        self.event_tracker.clear_events()
        
        # Execute tool with comprehensive parameters
        result = await dispatcher.execute_tool(
            "comprehensive_analytics",
            {
                "dataset": "completeness_test_data",
                "options": {"detailed": True, "format": "json"},
                "filters": ["category_a", "category_b"]
            }
        )
        
        self.assertTrue(result.success)
        
        # Analyze event data completeness
        sequence = self.event_tracker.get_complete_tool_sequence("comprehensive_analytics", self.user1_context.run_id)
        
        for event in sequence:
            # Verify all events have required fields
            self.assertIn("event_type", event)
            self.assertIn("run_id", event)
            self.assertIn("agent_name", event)
            self.assertIn("data", event)
            self.assertIn("timestamp", event)
            
            # Verify data completeness
            event_data = event["data"]
            self.assertIn("tool_name", event_data)
            self.assertIn("user_id", event_data)
            self.assertIn("thread_id", event_data)
            
            if event["event_type"] == "tool_executing":
                self.assertIn("parameters", event_data)
                # Verify parameters are preserved
                parameters = event_data["parameters"]
                self.assertIn("summary", parameters)  # Should be summarized for WebSocket
                
            elif event["event_type"] == "tool_completed":
                self.assertIn("status", event_data)
                if event_data["status"] == "success":
                    self.assertIn("result", event_data)
                    
        await dispatcher.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])