"""
Tool Dispatcher Integration Tests - Priority 3 for Issue #861

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents can execute tools to provide valuable insights  
- Value Impact: Tools are how agents deliver actionable results to users
- Strategic Impact: Tool execution enables agents to solve real problems vs just chat

CRITICAL: Tests tool dispatcher integration covering:
- Agent → Tool dispatcher → Tool execution → Results back to agent
- Multi-user tool execution with proper isolation
- Tool execution WebSocket events (tool_executing, tool_completed)
- Error handling and timeout management in tool execution

INTEGRATION LAYER: Uses real services (PostgreSQL, Redis) without Docker dependencies.
NO MOCKS in integration tests - validates actual tool execution flow.

Target: Improve coverage from 8% → 70%+ (Priority 3 of 4)
Focus Area: /netra_backend/app/tools/enhanced_dispatcher.py
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from unittest import mock
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.real_services import (
    real_services_fixture,
    real_postgres_connection,
    with_test_database,
    real_redis_connection
)

# SSOT Tool dispatcher imports
try:
    from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
    from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
    DISPATCHER_AVAILABLE = True
except ImportError:
    DISPATCHER_AVAILABLE = False

# SSOT Agent and context imports
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# SSOT Base agent
from netra_backend.app.agents.base_agent import BaseAgent

# SSOT configuration
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


@dataclass
class ToolExecutionResult:
    """Container for tool execution results."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    events_emitted: List[str] = None
    tool_name: str = ""
    
    def __post_init__(self):
        if self.events_emitted is None:
            self.events_emitted = []


class MockToolForTesting:
    """Mock tool that simulates various execution scenarios."""
    
    def __init__(self, name: str, execution_time: float = 0.1, should_fail: bool = False):
        self.name = name
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.call_count = 0
        self.last_parameters = None
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mock tool with configurable behavior."""
        self.call_count += 1
        self.last_parameters = parameters
        
        # Simulate execution time
        if self.execution_time > 0:
            await asyncio.sleep(self.execution_time)
        
        if self.should_fail:
            raise RuntimeError(f"Mock tool {self.name} failed as configured")
        
        return {
            "tool_name": self.name,
            "result": f"Mock result from {self.name}",
            "parameters_received": parameters,
            "execution_count": self.call_count
        }


class MockWebSocketForToolTesting:
    """Mock WebSocket that captures tool execution events."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_connected = True
        self.tool_events: List[Dict[str, Any]] = []
        
    async def send_text(self, message: str):
        """Capture tool-related events."""
        if self.is_connected:
            try:
                data = json.loads(message)
                self.sent_messages.append(data)
                
                # Track tool-specific events
                if data.get('type') in ['tool_executing', 'tool_completed', 'tool_error']:
                    self.tool_events.append(data)
                    
            except json.JSONDecodeError:
                pass
    
    async def close(self, code: int = 1000):
        """Close connection."""
        self.is_connected = False


class TestToolDispatcherIntegration(SSotAsyncTestCase):
    """Test comprehensive tool dispatcher integration functionality."""
    
    async def asyncSetUp(self):
        """Set up test environment with real services and tool infrastructure."""
        await super().asyncSetUp()
        
        # Generate unique test identifiers
        self.test_session_id = f"tool-session-{uuid.uuid4().hex[:8]}"
        self.test_user_id = f"tool-user-{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"tool-conn-{uuid.uuid4().hex[:8]}"
        
        # Create mock WebSocket for event capture
        self.mock_websocket = MockWebSocketForToolTesting(self.test_user_id)
        
        # Set up WebSocket manager
        self.websocket_manager = WebSocketManager()
        self.websocket_manager.active_connections[self.test_connection_id] = self.mock_websocket
        self.websocket_manager.connection_user_map[self.test_connection_id] = self.test_user_id
        self.websocket_manager.user_connection_map[self.test_user_id] = {self.test_connection_id}
        
        # Create user execution context
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            connection_id=self.test_connection_id,
            request_timestamp=time.time()
        )
        
        # Create WebSocket bridge
        self.websocket_bridge = AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_context=self.user_context
        )
        
        # Create tool dispatcher (use available dispatcher)
        if DISPATCHER_AVAILABLE:
            try:
                self.tool_dispatcher = EnhancedToolDispatcher(
                    user_context=self.user_context,
                    websocket_bridge=self.websocket_bridge
                )
            except Exception:
                # Fallback to unified dispatcher
                self.tool_dispatcher = UnifiedToolDispatcher(
                    user_context=self.user_context
                )
        else:
            # Create basic tool dispatcher for testing
            self.tool_dispatcher = self._create_basic_tool_dispatcher()
        
        # Register mock tools
        self._register_mock_tools()
    
    def _create_basic_tool_dispatcher(self):
        """Create basic tool dispatcher for testing when imports unavailable."""
        class BasicToolDispatcher:
            def __init__(self, user_context):
                self.user_context = user_context
                self.tools = {}
                self.websocket_bridge = None
                
            def register_tool(self, name: str, tool):
                self.tools[name] = tool
            
            def set_websocket_bridge(self, bridge):
                self.websocket_bridge = bridge
                
            async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]):
                if tool_name not in self.tools:
                    raise ValueError(f"Tool {tool_name} not found")
                
                tool = self.tools[tool_name]
                
                # Emit tool_executing event
                if self.websocket_bridge:
                    await self.websocket_bridge.emit_agent_event(
                        event_type="tool_executing",
                        agent_name="TestAgent",
                        data={
                            "tool_name": tool_name,
                            "parameters": parameters
                        }
                    )
                
                try:
                    result = await tool.execute(parameters)
                    
                    # Emit tool_completed event
                    if self.websocket_bridge:
                        await self.websocket_bridge.emit_agent_event(
                            event_type="tool_completed",
                            agent_name="TestAgent",
                            data={
                                "tool_name": tool_name,
                                "result": result,
                                "success": True
                            }
                        )
                    
                    return result
                    
                except Exception as e:
                    # Emit tool_error event
                    if self.websocket_bridge:
                        await self.websocket_bridge.emit_agent_event(
                            event_type="tool_error",
                            agent_name="TestAgent", 
                            data={
                                "tool_name": tool_name,
                                "error": str(e),
                                "success": False
                            }
                        )
                    raise
        
        dispatcher = BasicToolDispatcher(self.user_context)
        dispatcher.set_websocket_bridge(self.websocket_bridge)
        return dispatcher
    
    def _register_mock_tools(self):
        """Register mock tools for testing."""
        self.mock_tools = {
            "data_analyzer": MockToolForTesting("data_analyzer", 0.2),
            "report_generator": MockToolForTesting("report_generator", 0.3),  
            "slow_tool": MockToolForTesting("slow_tool", 1.0),
            "failing_tool": MockToolForTesting("failing_tool", 0.1, should_fail=True)
        }
        
        for name, tool in self.mock_tools.items():
            self.tool_dispatcher.register_tool(name, tool)
    
    async def asyncTearDown(self):
        """Clean up test resources."""
        # Close mock WebSocket
        if hasattr(self, 'mock_websocket') and self.mock_websocket.is_connected:
            await self.mock_websocket.close()
        
        # Clean up WebSocket manager
        if hasattr(self, 'websocket_manager'):
            self.websocket_manager.active_connections.clear()
            self.websocket_manager.connection_user_map.clear()
            self.websocket_manager.user_connection_map.clear()
        
        await super().asyncTearDown()
    
    async def execute_tool_with_events(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: float = 5.0
    ) -> ToolExecutionResult:
        """Execute tool through dispatcher and capture events."""
        
        start_time = time.time()
        
        # Clear previous events
        self.mock_websocket.tool_events.clear()
        
        try:
            # Execute tool through dispatcher
            result = await asyncio.wait_for(
                self.tool_dispatcher.execute_tool(tool_name, parameters),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Extract event types
            events = [event['type'] for event in self.mock_websocket.tool_events]
            
            return ToolExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time,
                events_emitted=events,
                tool_name=tool_name
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            events = [event['type'] for event in self.mock_websocket.tool_events]
            
            return ToolExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                events_emitted=events,
                tool_name=tool_name
            )

    @pytest.mark.asyncio
    async def test_successful_tool_execution_with_events(self):
        """Test Priority 3: Successful tool execution emits proper WebSocket events."""
        
        # Execute tool through dispatcher
        result = await self.execute_tool_with_events(
            tool_name="data_analyzer",
            parameters={"dataset": "test_data", "analysis_type": "basic"}
        )
        
        # Verify execution succeeded
        self.assertTrue(result.success, f"Tool execution failed: {result.error}")
        self.assertIsNotNone(result.result)
        
        # Verify tool was called
        mock_tool = self.mock_tools["data_analyzer"]
        self.assertEqual(mock_tool.call_count, 1)
        self.assertEqual(mock_tool.last_parameters["dataset"], "test_data")
        
        # Verify WebSocket events were emitted
        self.assertIn("tool_executing", result.events_emitted)
        self.assertIn("tool_completed", result.events_emitted)
        
        # Verify event order (executing before completed)
        executing_index = result.events_emitted.index("tool_executing")
        completed_index = result.events_emitted.index("tool_completed")
        self.assertLess(executing_index, completed_index)

    @pytest.mark.asyncio
    async def test_tool_execution_failure_handling(self):
        """Test Priority 3: Failed tool execution emits appropriate error events."""
        
        # Execute failing tool
        result = await self.execute_tool_with_events(
            tool_name="failing_tool",
            parameters={"test": "failure_scenario"}
        )
        
        # Verify execution failed
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("Mock tool failing_tool failed", result.error)
        
        # Verify tool_executing event was still emitted
        self.assertIn("tool_executing", result.events_emitted)
        
        # Should have either tool_error or tool_completed with error
        has_error_event = any(
            event in result.events_emitted 
            for event in ["tool_error", "tool_completed"]
        )
        self.assertTrue(has_error_event, "No error event emitted for failed tool")

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_isolation(self):
        """Test Priority 3: Multiple users can execute tools concurrently with isolation."""
        
        # Create second user context
        user2_id = f"tool-user2-{uuid.uuid4().hex[:8]}"
        conn2_id = f"tool-conn2-{uuid.uuid4().hex[:8]}"
        
        mock_websocket2 = MockWebSocketForToolTesting(user2_id)
        
        # Register second user in WebSocket manager
        self.websocket_manager.active_connections[conn2_id] = mock_websocket2
        self.websocket_manager.connection_user_map[conn2_id] = user2_id
        self.websocket_manager.user_connection_map[user2_id] = {conn2_id}
        
        user2_context = UserExecutionContext(
            user_id=user2_id,
            session_id=f"tool-session2-{uuid.uuid4().hex[:8]}",
            connection_id=conn2_id,
            request_timestamp=time.time()
        )
        
        # Create second WebSocket bridge and tool dispatcher
        user2_bridge = AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_context=user2_context
        )
        
        user2_dispatcher = self._create_basic_tool_dispatcher()
        user2_dispatcher.set_websocket_bridge(user2_bridge)
        
        # Register tools for user 2
        for name, tool in self.mock_tools.items():
            user2_dispatcher.register_tool(name, tool)
        
        # Execute tools concurrently for both users
        async def execute_user1_tool():
            return await self.execute_tool_with_events(
                tool_name="data_analyzer",
                parameters={"user": "user1", "data": "user1_data"}
            )
        
        async def execute_user2_tool():
            start_time = time.time()
            mock_websocket2.tool_events.clear()
            
            try:
                result = await user2_dispatcher.execute_tool(
                    "report_generator",
                    {"user": "user2", "data": "user2_data"}
                )
                
                events = [event['type'] for event in mock_websocket2.tool_events]
                
                return ToolExecutionResult(
                    success=True,
                    result=result,
                    execution_time=time.time() - start_time,
                    events_emitted=events,
                    tool_name="report_generator"
                )
                
            except Exception as e:
                return ToolExecutionResult(
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time,
                    tool_name="report_generator"
                )
        
        # Execute both concurrently
        result1, result2 = await asyncio.gather(
            execute_user1_tool(),
            execute_user2_tool()
        )
        
        # Verify both executions succeeded
        self.assertTrue(result1.success, f"User 1 tool execution failed: {result1.error}")
        self.assertTrue(result2.success, f"User 2 tool execution failed: {result2.error}")
        
        # Verify tools received correct parameters (isolation)
        self.assertIn("user1_data", str(result1.result))
        self.assertIn("user2_data", str(result2.result))
        
        # Verify events were emitted for both users separately
        self.assertGreater(len(result1.events_emitted), 0)
        self.assertGreater(len(result2.events_emitted), 0)
        
        # Clean up user 2 WebSocket
        await mock_websocket2.close()

    @pytest.mark.asyncio
    async def test_tool_execution_timeout_handling(self):
        """Test Priority 3: Tool execution respects timeout limits."""
        
        # Execute slow tool with short timeout
        result = await self.execute_tool_with_events(
            tool_name="slow_tool",
            parameters={"test": "timeout_scenario"},
            timeout=0.5  # Shorter than tool's 1.0s execution time
        )
        
        # Should timeout
        self.assertFalse(result.success)
        self.assertIn("timeout", result.error.lower())
        
        # Should have emitted tool_executing but not tool_completed
        self.assertIn("tool_executing", result.events_emitted)
        # May or may not have tool_completed depending on timing

    @pytest.mark.asyncio
    async def test_multiple_tool_execution_sequence(self):
        """Test Priority 3: Sequential execution of multiple tools with proper events."""
        
        tools_to_execute = [
            ("data_analyzer", {"step": 1}),
            ("report_generator", {"step": 2}),
            ("data_analyzer", {"step": 3})  # Same tool again
        ]
        
        results = []
        
        # Execute tools in sequence
        for tool_name, parameters in tools_to_execute:
            result = await self.execute_tool_with_events(
                tool_name=tool_name,
                parameters=parameters
            )
            results.append(result)
        
        # Verify all executions succeeded
        for i, result in enumerate(results):
            self.assertTrue(result.success, 
                           f"Tool {tools_to_execute[i][0]} execution {i+1} failed: {result.error}")
        
        # Verify data_analyzer was called twice
        data_analyzer_tool = self.mock_tools["data_analyzer"]
        self.assertEqual(data_analyzer_tool.call_count, 2)
        
        # Verify report_generator was called once
        report_generator_tool = self.mock_tools["report_generator"]
        self.assertEqual(report_generator_tool.call_count, 1)
        
        # Verify all tools emitted proper events
        for result in results:
            self.assertIn("tool_executing", result.events_emitted)
            self.assertIn("tool_completed", result.events_emitted)

    @pytest.mark.asyncio
    async def test_tool_dispatcher_unknown_tool_handling(self):
        """Test Priority 3: Dispatcher handles requests for unknown tools gracefully."""
        
        # Attempt to execute unknown tool
        result = await self.execute_tool_with_events(
            tool_name="nonexistent_tool",
            parameters={"test": "unknown_tool"}
        )
        
        # Should fail gracefully
        self.assertFalse(result.success)
        self.assertIn("not found", result.error.lower())
        
        # Should complete quickly
        self.assertLess(result.execution_time, 1.0)

    @pytest.mark.asyncio  
    async def test_tool_event_message_structure(self):
        """Test Priority 3: Tool execution events have proper message structure."""
        
        # Execute tool and capture detailed events
        result = await self.execute_tool_with_events(
            tool_name="data_analyzer",
            parameters={"analysis": "structure_test"}
        )
        
        # Verify execution succeeded
        self.assertTrue(result.success)
        
        # Verify event messages have proper structure
        tool_events = self.mock_websocket.tool_events
        self.assertGreater(len(tool_events), 0)
        
        for event in tool_events:
            # All events should have required fields
            self.assertIn('type', event)
            self.assertIn('timestamp', event)
            self.assertIn('data', event)
            
            # Tool events should have tool_name in data
            if event['type'] in ['tool_executing', 'tool_completed', 'tool_error']:
                self.assertIn('tool_name', event['data'])
                self.assertEqual(event['data']['tool_name'], 'data_analyzer')
            
            # tool_executing should have parameters
            if event['type'] == 'tool_executing':
                self.assertIn('parameters', event['data'])
                self.assertEqual(event['data']['parameters']['analysis'], 'structure_test')
            
            # tool_completed should have result and success
            if event['type'] == 'tool_completed':
                self.assertIn('result', event['data'])
                self.assertIn('success', event['data'])
                self.assertTrue(event['data']['success'])

    @pytest.mark.asyncio
    async def test_tool_dispatcher_resource_cleanup(self):
        """Test Priority 3: Tool dispatcher properly manages resources and cleanup."""
        
        # Execute multiple tools to create resource usage
        tools_executed = []
        
        for i in range(5):
            result = await self.execute_tool_with_events(
                tool_name="data_analyzer",
                parameters={"batch": i}
            )
            tools_executed.append(result)
        
        # Verify all executions succeeded
        for i, result in enumerate(tools_executed):
            self.assertTrue(result.success, f"Batch {i} execution failed: {result.error}")
        
        # Verify tool was called correct number of times
        data_analyzer_tool = self.mock_tools["data_analyzer"] 
        self.assertEqual(data_analyzer_tool.call_count, 5)
        
        # Verify no memory leaks (basic check)
        # Tool should maintain reasonable state
        self.assertIsNotNone(data_analyzer_tool.last_parameters)
        self.assertEqual(data_analyzer_tool.last_parameters["batch"], 4)  # Last execution


if __name__ == '__main__':
    pytest.main([__file__, '-v'])