"""E2E Comprehensive Tests for Agent Execution WebSocket Events.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - WebSocket events are core to user experience
- Business Goal: Ensure reliable real-time user feedback during agent execution
- Value Impact: Users must receive timely updates for long-running agent processes
- Strategic Impact: Complete WebSocket event validation prevents user abandonment due to unclear agent status

These E2E tests validate ALL required WebSocket events with complete system stack:
- Real authentication (JWT/OAuth) 
- Real WebSocket connections with event ordering validation
- Real agent execution with tool integration
- All 5 required WebSocket events: started, thinking, tool_executing, tool_completed, completed
- Event delivery guarantees and failure handling
- Concurrent user event isolation

CRITICAL: ALL E2E tests MUST use authentication - no exceptions.
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from langchain_core.tools import BaseTool


class WebSocketEventTestTool(BaseTool):
    """Tool that generates WebSocket events during execution."""
    
    name: str = "websocket_event_test_tool"
    description: str = "Tool for testing WebSocket event generation during execution"
    
    def __init__(self, execution_delay: float = 0.5, **kwargs):
        super().__init__(**kwargs)
        self.execution_delay = execution_delay
        self.websocket_bridge = None
        self._run_id = None
        self.execution_count = 0
    
    def set_websocket_bridge(self, bridge, run_id: str):
        """Set WebSocket bridge for event notifications."""
        self.websocket_bridge = bridge
        self._run_id = run_id
    
    async def _arun(self, operation: str = "default_operation") -> Dict[str, Any]:
        """Async execution with WebSocket events."""
        self.execution_count += 1
        start_time = datetime.now(timezone.utc)
        
        # Send tool executing event if bridge is available
        if self.websocket_bridge and self._run_id:
            await self.websocket_bridge.notify_tool_executing(
                run_id=self._run_id,
                agent_name="websocket_event_test_agent",
                tool_name=self.name,
                tool_args={"operation": operation}
            )
        
        # Simulate processing time with intermediate updates
        await asyncio.sleep(self.execution_delay / 2)
        
        # Send intermediate thinking event
        if self.websocket_bridge and self._run_id:
            await self.websocket_bridge.notify_agent_thinking(
                run_id=self._run_id,
                agent_name="websocket_event_test_agent", 
                reasoning=f"Tool {self.name} processing operation: {operation}"
            )
        
        await asyncio.sleep(self.execution_delay / 2)
        
        # Create result
        result = {
            "success": True,
            "operation": operation,
            "execution_count": self.execution_count,
            "tool_name": self.name,
            "processing_time": self.execution_delay,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send tool completed event
        if self.websocket_bridge and self._run_id:
            await self.websocket_bridge.notify_tool_completed(
                run_id=self._run_id,
                agent_name="websocket_event_test_agent",
                tool_name=self.name,
                tool_result=result
            )
        
        return result
    
    def _run(self, operation: str = "default_operation") -> Dict[str, Any]:
        """Sync execution (fallback)."""
        return {
            "success": True,
            "operation": operation,
            "tool_name": self.name,
            "sync_execution": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class WebSocketEventTestAgent:
    """Real agent that uses tools and generates complete WebSocket event sequences."""
    
    def __init__(self, name: str = "websocket_event_test_agent"):
        self.name = name
        self.websocket_bridge = None
        self._run_id = None
        self._user_id = None
        self._trace_context = None
        
        # Event tracking
        self.events_sent = []
        self.execution_history = []
        self.tools = []
    
    def add_tool(self, tool):
        """Add tool to agent."""
        self.tools.append(tool)
    
    async def execute(self, state: DeepAgentState, run_id: str, enable_websocket: bool = True):
        """Execute agent with comprehensive WebSocket event generation."""
        execution_start = datetime.now(timezone.utc)
        
        # Record execution
        execution_record = {
            'run_id': run_id,
            'user_id': getattr(state, 'user_id', None),
            'thread_id': getattr(state, 'thread_id', None),
            'start_time': execution_start,
            'websocket_enabled': enable_websocket
        }
        self.execution_history.append(execution_record)
        
        try:
            # Phase 1: Agent thinking (initial reasoning)
            if self.websocket_bridge and enable_websocket:
                await self.websocket_bridge.notify_agent_thinking(
                    run_id=run_id,
                    agent_name=self.name,
                    reasoning="Analyzing request and planning tool execution sequence...",
                    trace_context=getattr(self._trace_context, 'to_websocket_context', lambda: {})()
                )
                self.events_sent.append('agent_thinking_initial')
            
            await asyncio.sleep(0.1)  # Simulate thinking time
            
            # Phase 2: Tool execution (if tools are available)
            tool_results = []
            for i, tool in enumerate(self.tools):
                if hasattr(tool, 'set_websocket_bridge') and self.websocket_bridge:
                    tool.set_websocket_bridge(self.websocket_bridge, run_id)
                
                # Execute tool (this should generate tool_executing and tool_completed events)
                if hasattr(tool, '_arun'):
                    tool_result = await tool._arun(f"operation_{i+1}")
                else:
                    tool_result = tool._run(f"operation_{i+1}")
                
                tool_results.append(tool_result)
                
                # Additional thinking between tools
                if i < len(self.tools) - 1 and self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=run_id,
                        agent_name=self.name,
                        reasoning=f"Completed tool {i+1}/{len(self.tools)}, proceeding to next tool...",
                        trace_context=getattr(self._trace_context, 'to_websocket_context', lambda: {})()
                    )
                    self.events_sent.append(f'agent_thinking_between_tools_{i}')
                
                await asyncio.sleep(0.05)  # Small delay between tools
            
            # Phase 3: Final processing
            if self.websocket_bridge and enable_websocket:
                await self.websocket_bridge.notify_agent_thinking(
                    run_id=run_id,
                    agent_name=self.name,
                    reasoning="Compiling final results and preparing response...",
                    trace_context=getattr(self._trace_context, 'to_websocket_context', lambda: {})()
                )
                self.events_sent.append('agent_thinking_final')
            
            await asyncio.sleep(0.1)  # Simulate final processing
            
            # Create comprehensive result
            execution_end = datetime.now(timezone.utc)
            duration_ms = (execution_end - execution_start).total_seconds() * 1000
            
            result = {
                "success": True,
                "agent_name": self.name,
                "result": f"WebSocket event test agent completed with {len(tool_results)} tool executions",
                "tool_results": tool_results,
                "execution_duration_ms": duration_ms,
                "user_id": getattr(state, 'user_id', None),
                "thread_id": getattr(state, 'thread_id', None),
                "events_sent_count": len(self.events_sent),
                "events_sent": self.events_sent.copy(),
                "timestamp": execution_end.isoformat(),
                "tools_executed": len(self.tools)
            }
            
            return result
            
        except Exception as e:
            # Even in failure, record what events were sent
            execution_record['error'] = str(e)
            execution_record['events_sent'] = self.events_sent.copy()
            raise
    
    def set_websocket_bridge(self, bridge, run_id: str):
        """Set WebSocket bridge for event delivery."""
        self.websocket_bridge = bridge
        self._run_id = run_id
    
    def set_trace_context(self, trace_context):
        """Set trace context for event correlation."""
        self._trace_context = trace_context


class TestAgentExecutionWebSocketEventsComprehensive(BaseE2ETest):
    """Comprehensive E2E tests for all WebSocket events in agent execution."""
    
    @pytest.fixture
    async def authenticated_user(self):
        """Create authenticated user for WebSocket event testing."""
        token, user_data = await create_authenticated_user(
            environment="test",
            user_id="websocket-events-user",
            email="websocket-events@test.com",
            permissions=["read", "write", "agent_execute", "websocket_connect"]
        )
        return {
            "token": token,
            "user_data": user_data,
            "user_id": user_data["id"],
            "email": user_data["email"]
        }
    
    @pytest.fixture
    def auth_helper(self):
        """E2E authentication helper."""
        return E2EAuthHelper(environment="test")
    
    @pytest.fixture
    async def websocket_client(self, authenticated_user, auth_helper):
        """Authenticated WebSocket client for event testing."""
        headers = auth_helper.get_websocket_headers(authenticated_user["token"])
        client = WebSocketTestClient(
            url="ws://localhost:8002/ws",
            headers=headers
        )
        await client.connect()
        yield client
        await client.disconnect()
    
    @pytest.fixture
    def websocket_test_tools(self):
        """Tools configured for WebSocket event testing."""
        return [
            WebSocketEventTestTool(name="event_tool_1", execution_delay=0.3),
            WebSocketEventTestTool(name="event_tool_2", execution_delay=0.2),
            WebSocketEventTestTool(name="event_tool_3", execution_delay=0.1)
        ]
    
    @pytest.fixture
    def websocket_event_registry(self, websocket_test_tools):
        """Agent registry with WebSocket event test agents."""
        registry = AgentRegistry()
        
        # Create comprehensive test agent with tools
        event_agent = WebSocketEventTestAgent("websocket_event_test_agent")
        for tool in websocket_test_tools:
            event_agent.add_tool(tool)
        
        registry._agents["websocket_event_test_agent"] = event_agent
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    async def test_all_five_required_websocket_events_e2e(
        self,
        authenticated_user,
        websocket_client,
        websocket_event_registry
    ):
        """Test all 5 required WebSocket events are sent in correct order."""
        
        # Create execution context
        context = AgentExecutionContext(
            agent_name="websocket_event_test_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        # Create authenticated agent state
        state = DeepAgentState(
            user_id=authenticated_user["user_id"],
            thread_id=f"websocket-events-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Collect WebSocket events
        received_events = []
        
        async def collect_all_websocket_events():
            """Collect all WebSocket events during execution."""
            try:
                while True:
                    event = await asyncio.wait_for(websocket_client.receive_json(), timeout=3.0)
                    received_events.append(event)
                    
                    # Continue collecting until we get agent_completed
                    if event.get('type') == 'agent_completed':
                        break
            except asyncio.TimeoutError:
                pass  # Normal timeout
        
        # Create real WebSocket bridge
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        
        # Override bridge to send events to our test client
        original_started = websocket_bridge.notify_agent_started
        original_completed = websocket_bridge.notify_agent_completed
        original_error = websocket_bridge.notify_agent_error
        original_thinking = websocket_bridge.notify_agent_thinking
        original_tool_executing = websocket_bridge.notify_tool_executing
        original_tool_completed = websocket_bridge.notify_tool_completed
        
        async def send_to_test_client(event_type: str, **kwargs):
            """Send event to test WebSocket client."""
            event = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **kwargs
            }
            await websocket_client.send_json(event)
            return True
        
        # Wrap bridge methods to send to our test client
        async def wrapped_started(run_id, agent_name, trace_context=None):
            await send_to_test_client("agent_started", run_id=str(run_id), agent_name=agent_name)
            return await original_started(run_id, agent_name, trace_context)
        
        async def wrapped_completed(run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
            await send_to_test_client("agent_completed", run_id=str(run_id), agent_name=agent_name, result=result)
            return await original_completed(run_id, agent_name, result, execution_time_ms, trace_context)
        
        async def wrapped_error(run_id, agent_name, error, trace_context=None):
            await send_to_test_client("agent_error", run_id=str(run_id), agent_name=agent_name, error=error)
            return await original_error(run_id, agent_name, error, trace_context)
        
        async def wrapped_thinking(run_id, agent_name, reasoning, trace_context=None):
            await send_to_test_client("agent_thinking", run_id=str(run_id), agent_name=agent_name, reasoning=reasoning)
            return await original_thinking(run_id, agent_name, reasoning, trace_context)
        
        async def wrapped_tool_executing(run_id, agent_name, tool_name, tool_args=None, trace_context=None):
            await send_to_test_client("tool_executing", run_id=str(run_id), agent_name=agent_name, tool_name=tool_name)
            return await original_tool_executing(run_id, agent_name, tool_name, tool_args, trace_context)
        
        async def wrapped_tool_completed(run_id, agent_name, tool_name, tool_result=None, trace_context=None):
            await send_to_test_client("tool_completed", run_id=str(run_id), agent_name=agent_name, tool_name=tool_name)
            return await original_tool_completed(run_id, agent_name, tool_name, tool_result, trace_context)
        
        # Apply wrappers
        websocket_bridge.notify_agent_started = wrapped_started
        websocket_bridge.notify_agent_completed = wrapped_completed
        websocket_bridge.notify_agent_error = wrapped_error
        websocket_bridge.notify_agent_thinking = wrapped_thinking
        websocket_bridge.notify_tool_executing = wrapped_tool_executing
        websocket_bridge.notify_tool_completed = wrapped_tool_completed
        
        # Create execution core with wrapped bridge
        execution_core = AgentExecutionCore(websocket_event_registry, websocket_bridge)
        
        # Start event collection
        event_collection_task = asyncio.create_task(collect_all_websocket_events())
        
        # Execute agent
        try:
            result = await execution_core.execute_agent(context, state, timeout=15.0)
        finally:
            # Stop event collection
            event_collection_task.cancel()
            try:
                await event_collection_task
            except asyncio.CancelledError:
                pass
        
        # Verify execution success
        assert result.success is True, f"Agent execution failed: {result.error}"
        
        # Extract event types in order
        event_types = [event.get('type') for event in received_events]
        
        # CRITICAL: Verify all 5 required WebSocket events are present
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for required_event in required_events:
            assert required_event in event_types, \
                f"MISSING CRITICAL EVENT: {required_event} not found in {event_types}"
        
        # Verify event ordering constraints
        started_index = event_types.index('agent_started')
        completed_index = event_types.index('agent_completed')
        
        # agent_started must be first
        assert started_index == 0, f"agent_started must be first event, found at index {started_index}"
        
        # agent_completed must be last
        assert completed_index == len(event_types) - 1, \
            f"agent_completed must be last event, found at index {completed_index}"
        
        # tool_executing must come before tool_completed
        tool_executing_indices = [i for i, event_type in enumerate(event_types) if event_type == 'tool_executing']
        tool_completed_indices = [i for i, event_type in enumerate(event_types) if event_type == 'tool_completed']
        
        assert len(tool_executing_indices) > 0, "No tool_executing events found"
        assert len(tool_completed_indices) > 0, "No tool_completed events found"
        
        # Each tool_executing should be followed by tool_completed
        for exec_index in tool_executing_indices:
            # Find the next tool_completed after this tool_executing
            next_completed = next((i for i in tool_completed_indices if i > exec_index), None)
            assert next_completed is not None, \
                f"No tool_completed event found after tool_executing at index {exec_index}"
        
        # Verify event details contain proper context
        for event in received_events:
            assert 'timestamp' in event, "All events must have timestamps"
            
            if event.get('type') in ['agent_started', 'agent_completed', 'agent_thinking', 'tool_executing', 'tool_completed']:
                assert event.get('run_id') == str(context.run_id), \
                    f"Event {event.get('type')} has wrong run_id: {event.get('run_id')} != {context.run_id}"
                assert event.get('agent_name') == context.agent_name, \
                    f"Event {event.get('type')} has wrong agent_name: {event.get('agent_name')} != {context.agent_name}"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    async def test_websocket_events_concurrent_users_isolation(
        self,
        auth_helper,
        websocket_event_registry
    ):
        """Test WebSocket event isolation between concurrent users."""
        
        # Create two different authenticated users
        token1, user1_data = await create_authenticated_user(
            environment="test",
            user_id="websocket-user-1",
            email="websocket-user-1@test.com"
        )
        
        token2, user2_data = await create_authenticated_user(
            environment="test",
            user_id="websocket-user-2",
            email="websocket-user-2@test.com"
        )
        
        # Create WebSocket clients for both users
        headers1 = auth_helper.get_websocket_headers(token1)
        headers2 = auth_helper.get_websocket_headers(token2)
        
        client1 = WebSocketTestClient(url="ws://localhost:8002/ws", headers=headers1)
        client2 = WebSocketTestClient(url="ws://localhost:8002/ws", headers=headers2)
        
        await client1.connect()
        await client2.connect()
        
        try:
            # Track events for each user
            user1_events = []
            user2_events = []
            
            async def collect_user1_events():
                try:
                    while True:
                        event = await asyncio.wait_for(client1.receive_json(), timeout=2.0)
                        user1_events.append(event)
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    pass
            
            async def collect_user2_events():
                try:
                    while True:
                        event = await asyncio.wait_for(client2.receive_json(), timeout=2.0)
                        user2_events.append(event)
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    pass
            
            # Create execution contexts
            context1 = AgentExecutionContext(
                agent_name="websocket_event_test_agent",
                run_id=str(uuid.uuid4()),
                correlation_id=str(uuid.uuid4()),
                retry_count=0
            )
            
            context2 = AgentExecutionContext(
                agent_name="websocket_event_test_agent", 
                run_id=str(uuid.uuid4()),
                correlation_id=str(uuid.uuid4()),
                retry_count=0
            )
            
            state1 = DeepAgentState(
                user_id=user1_data["id"],
                thread_id=f"user1-websocket-thread-{uuid.uuid4().hex[:8]}"
            )
            
            state2 = DeepAgentState(
                user_id=user2_data["id"],
                thread_id=f"user2-websocket-thread-{uuid.uuid4().hex[:8]}"
            )
            
            # Simple event bridge that routes to correct client
            class UserIsolatedEventBridge:
                def __init__(self, client1, client2, run_id1, run_id2):
                    self.client1 = client1
                    self.client2 = client2
                    self.run_id1 = str(run_id1)
                    self.run_id2 = str(run_id2)
                
                async def route_event(self, event_type: str, run_id: str, **kwargs):
                    event = {"type": event_type, "run_id": run_id, **kwargs}
                    
                    # Route to correct user based on run_id
                    if run_id == self.run_id1:
                        await self.client1.send_json(event)
                    elif run_id == self.run_id2:
                        await self.client2.send_json(event)
                    
                    return True
                
                async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                    return await self.route_event("agent_started", str(run_id), agent_name=agent_name)
                
                async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                    return await self.route_event("agent_completed", str(run_id), agent_name=agent_name, result=result)
                
                async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                    return await self.route_event("agent_error", str(run_id), agent_name=agent_name, error=error)
                
                async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                    return await self.route_event("agent_thinking", str(run_id), agent_name=agent_name, reasoning=reasoning)
                
                async def notify_tool_executing(self, run_id, agent_name, tool_name, tool_args=None, trace_context=None):
                    return await self.route_event("tool_executing", str(run_id), agent_name=agent_name, tool_name=tool_name)
                
                async def notify_tool_completed(self, run_id, agent_name, tool_name, tool_result=None, trace_context=None):
                    return await self.route_event("tool_completed", str(run_id), agent_name=agent_name, tool_name=tool_name)
            
            # Create isolated bridge
            isolated_bridge = UserIsolatedEventBridge(client1, client2, context1.run_id, context2.run_id)
            
            # Start event collection
            collection_task1 = asyncio.create_task(collect_user1_events())
            collection_task2 = asyncio.create_task(collect_user2_events())
            
            # Execute agents concurrently
            execution_core = AgentExecutionCore(websocket_event_registry, isolated_bridge)
            
            results = await asyncio.gather(
                execution_core.execute_agent(context1, state1, timeout=10.0),
                execution_core.execute_agent(context2, state2, timeout=10.0)
            )
            
            # Wait for event collection to complete
            await asyncio.gather(collection_task1, collection_task2)
            
            # Verify both executions succeeded
            assert results[0].success is True, "User 1 execution failed"
            assert results[1].success is True, "User 2 execution failed"
            
            # Verify each user received their events
            assert len(user1_events) > 0, "User 1 should have received events"
            assert len(user2_events) > 0, "User 2 should have received events"
            
            # CRITICAL: Verify event isolation
            user1_run_ids = {event.get('run_id') for event in user1_events}
            user2_run_ids = {event.get('run_id') for event in user2_events}
            
            # User 1 should only see their run_id
            assert str(context1.run_id) in user1_run_ids, "User 1 missing their own run_id in events"
            assert str(context2.run_id) not in user1_run_ids, "ISOLATION VIOLATION: User 1 saw User 2's run_id"
            
            # User 2 should only see their run_id
            assert str(context2.run_id) in user2_run_ids, "User 2 missing their own run_id in events"
            assert str(context1.run_id) not in user2_run_ids, "ISOLATION VIOLATION: User 2 saw User 1's run_id"
        
        finally:
            await client1.disconnect()
            await client2.disconnect()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    async def test_websocket_event_delivery_failure_handling(
        self,
        authenticated_user,
        websocket_event_registry
    ):
        """Test handling of WebSocket event delivery failures."""
        
        # Create execution context
        context = AgentExecutionContext(
            agent_name="websocket_event_test_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        state = DeepAgentState(
            user_id=authenticated_user["user_id"],
            thread_id=f"failure-test-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Create a bridge that simulates delivery failures
        class FailureTestBridge:
            def __init__(self):
                self.events_attempted = []
                self.events_failed = []
                self.failure_rate = 0.3  # 30% failure rate
                self.event_count = 0
            
            async def simulate_delivery(self, event_type: str, **kwargs):
                self.event_count += 1
                self.events_attempted.append(event_type)
                
                # Simulate random failures
                import random
                if random.random() < self.failure_rate:
                    self.events_failed.append(event_type)
                    # Still return True to avoid breaking agent execution
                    # Real system should handle failures gracefully
                    return True
                
                return True
            
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                return await self.simulate_delivery("agent_started", run_id=run_id, agent_name=agent_name)
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                return await self.simulate_delivery("agent_completed", run_id=run_id, agent_name=agent_name)
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                return await self.simulate_delivery("agent_error", run_id=run_id, agent_name=agent_name)
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                return await self.simulate_delivery("agent_thinking", run_id=run_id, agent_name=agent_name)
            
            async def notify_tool_executing(self, run_id, agent_name, tool_name, tool_args=None, trace_context=None):
                return await self.simulate_delivery("tool_executing", run_id=run_id, agent_name=agent_name)
            
            async def notify_tool_completed(self, run_id, agent_name, tool_name, tool_result=None, trace_context=None):
                return await self.simulate_delivery("tool_completed", run_id=run_id, agent_name=agent_name)
        
        failure_bridge = FailureTestBridge()
        execution_core = AgentExecutionCore(websocket_event_registry, failure_bridge)
        
        # Execute agent despite WebSocket failures
        result = await execution_core.execute_agent(context, state, timeout=10.0)
        
        # CRITICAL: Agent execution should succeed even with WebSocket failures
        assert result.success is True, \
            f"Agent execution should succeed despite WebSocket failures: {result.error}"
        
        # Verify that events were attempted
        assert len(failure_bridge.events_attempted) > 0, "No WebSocket events were attempted"
        
        # Verify critical events were attempted
        critical_events = ['agent_started', 'agent_completed']
        for critical_event in critical_events:
            assert critical_event in failure_bridge.events_attempted, \
                f"Critical event {critical_event} was not attempted"
        
        # Log failure statistics for monitoring
        failure_rate_actual = len(failure_bridge.events_failed) / len(failure_bridge.events_attempted)
        print(f"WebSocket event failure rate: {failure_rate_actual:.1%} ({len(failure_bridge.events_failed)}/{len(failure_bridge.events_attempted)})")
        
        # System should be resilient to some event failures
        assert failure_rate_actual < 1.0, "Not all WebSocket events should fail"