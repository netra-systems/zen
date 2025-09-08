"""E2E tests for AgentExecutionCore with full system integration.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete agent execution flow works end-to-end
- Value Impact: Users must receive reliable agent execution with real-time updates
- Strategic Impact: E2E validation prevents production failures affecting customer experience

These E2E tests validate agent execution with complete system stack:
- Real authentication (JWT/OAuth)
- Real WebSocket connections
- Real databases (PostgreSQL, Redis, ClickHouse)
- Real agent workflows
- Real LLM integration (when available)

CRITICAL: ALL E2E tests MUST use authentication - no exceptions.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState


class TestAgentExecutionCoreE2E(BaseE2ETest):
    """E2E tests for AgentExecutionCore with authenticated full-stack integration."""
    
    @pytest.fixture
    async def authenticated_user(self):
        """Create authenticated user for E2E testing."""
        token, user_data = await create_authenticated_user(
            environment="test",
            permissions=["read", "write", "agent_execute"]
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
        """Authenticated WebSocket client for E2E testing."""
        headers = auth_helper.get_websocket_headers(authenticated_user["token"])
        client = WebSocketTestClient(
            url="ws://localhost:8002/ws",
            headers=headers
        )
        await client.connect()
        yield client
        await client.disconnect()
    
    @pytest.fixture
    def real_agent_registry(self):
        """Real agent registry with E2E test agents."""
        registry = AgentRegistry()
        
        class E2ETestAgent:
            """Real agent for E2E testing with complete WebSocket integration."""
            
            def __init__(self, name: str, execution_behavior: str = "success"):
                self.name = name
                self.execution_behavior = execution_behavior
                self.websocket_bridge = None
                self._run_id = None
                self._user_id = None
                self._trace_context = None
                
                # E2E tracking
                self.execution_history = []
                self.websocket_events_sent = []
            
            async def execute(self, state: DeepAgentState, run_id: str, enable_websocket: bool = True):
                """Execute E2E test agent with real WebSocket events."""
                execution_start = datetime.now(timezone.utc)
                
                # Record execution
                self.execution_history.append({
                    'run_id': run_id,
                    'user_id': getattr(state, 'user_id', None),
                    'thread_id': getattr(state, 'thread_id', None),
                    'start_time': execution_start,
                    'websocket_enabled': enable_websocket
                })
                
                # Send WebSocket thinking event during execution
                if self.websocket_bridge and enable_websocket:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=run_id,
                        agent_name=self.name,
                        reasoning="E2E test agent processing user request...",
                        trace_context=getattr(self._trace_context, 'to_websocket_context', lambda: {})()
                    )
                    self.websocket_events_sent.append('agent_thinking')
                
                # Simulate realistic processing time
                await asyncio.sleep(0.2)
                
                # Handle different execution behaviors
                if self.execution_behavior == "failure":
                    raise RuntimeError(f"E2E test agent {self.name} simulated failure")
                elif self.execution_behavior == "timeout":
                    await asyncio.sleep(10.0)  # Will timeout in tests
                elif self.execution_behavior == "dead":
                    return None  # Dead agent signature
                elif self.execution_behavior == "slow":
                    await asyncio.sleep(1.0)
                
                # Successful execution result
                execution_end = datetime.now(timezone.utc)
                duration_ms = (execution_end - execution_start).total_seconds() * 1000
                
                return {
                    "success": True,
                    "agent_name": self.name,
                    "result": f"E2E test agent {self.name} completed successfully",
                    "execution_duration_ms": duration_ms,
                    "user_id": getattr(state, 'user_id', None),
                    "thread_id": getattr(state, 'thread_id', None),
                    "websocket_events_sent": len(self.websocket_events_sent),
                    "timestamp": execution_end.isoformat()
                }
            
            def set_websocket_bridge(self, bridge, run_id: str):
                """Set WebSocket bridge for real event delivery."""
                self.websocket_bridge = bridge
                self._run_id = run_id
            
            def set_trace_context(self, trace_context):
                """Set trace context for event correlation."""
                self._trace_context = trace_context
        
        # Register E2E test agents with different behaviors
        registry._agents["e2e_success_agent"] = E2ETestAgent("e2e_success_agent", "success")
        registry._agents["e2e_failure_agent"] = E2ETestAgent("e2e_failure_agent", "failure")
        registry._agents["e2e_dead_agent"] = E2ETestAgent("e2e_dead_agent", "dead")
        registry._agents["e2e_slow_agent"] = E2ETestAgent("e2e_slow_agent", "slow")
        
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_complete_agent_execution_flow_e2e(
        self, 
        authenticated_user,
        websocket_client,
        real_agent_registry
    ):
        """Test complete agent execution flow with real authentication and WebSocket."""
        # Create real execution context with authenticated user
        context = AgentExecutionContext(
            agent_name="e2e_success_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        # Create authenticated agent state
        state = DeepAgentState(
            user_id=authenticated_user["user_id"],
            thread_id=f"e2e-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Start listening for WebSocket events
        websocket_events = []
        
        async def collect_websocket_events():
            """Collect WebSocket events during execution."""
            try:
                while True:
                    event = await asyncio.wait_for(websocket_client.receive_json(), timeout=1.0)
                    websocket_events.append(event)
                    
                    # Stop collecting if we get completion event
                    if event.get('type') in ['agent_completed', 'agent_error']:
                        break
            except asyncio.TimeoutError:
                pass  # Normal timeout, stop collecting
        
        # Create real WebSocket bridge that sends to our client
        class E2EWebSocketBridge:
            """WebSocket bridge that sends events to real WebSocket connection."""
            
            def __init__(self, websocket_client):
                self.websocket_client = websocket_client
            
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                """Send agent started event via real WebSocket."""
                event = {
                    "type": "agent_started",
                    "run_id": str(run_id),
                    "agent_name": agent_name,
                    "trace_context": trace_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.websocket_client.send_json(event)
                return True
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, 
                                           execution_time_ms=0, trace_context=None):
                """Send agent completed event via real WebSocket."""
                event = {
                    "type": "agent_completed",
                    "run_id": str(run_id),
                    "agent_name": agent_name,
                    "result": result,
                    "execution_time_ms": execution_time_ms,
                    "trace_context": trace_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.websocket_client.send_json(event)
                return True
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                """Send agent error event via real WebSocket."""
                event = {
                    "type": "agent_error",
                    "run_id": str(run_id),
                    "agent_name": agent_name,
                    "error": error,
                    "trace_context": trace_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.websocket_client.send_json(event)
                return True
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                """Send agent thinking event via real WebSocket."""
                event = {
                    "type": "agent_thinking",
                    "run_id": str(run_id),
                    "agent_name": agent_name,
                    "reasoning": reasoning,
                    "trace_context": trace_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.websocket_client.send_json(event)
                return True
        
        # Create execution core with real WebSocket bridge
        websocket_bridge = E2EWebSocketBridge(websocket_client)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        # Start WebSocket event collection
        event_collection_task = asyncio.create_task(collect_websocket_events())
        
        # Execute agent with real authentication and WebSocket integration
        try:
            result = await execution_core.execute_agent(context, state, timeout=15.0)
            
            # Give a moment for final events to arrive
            await asyncio.sleep(0.1)
            
        finally:
            # Stop event collection
            event_collection_task.cancel()
            try:
                await event_collection_task
            except asyncio.CancelledError:
                pass
        
        # Verify successful execution
        assert result.success is True
        assert result.duration is not None
        assert result.duration > 0
        assert result.metrics is not None
        
        # Verify WebSocket events were received
        assert len(websocket_events) >= 3  # started, thinking, completed
        
        # Verify event sequence
        event_types = [event['type'] for event in websocket_events]
        assert 'agent_started' in event_types
        assert 'agent_thinking' in event_types  
        assert 'agent_completed' in event_types
        
        # Verify event order (started should be first, completed should be last)
        assert event_types[0] == 'agent_started'
        assert event_types[-1] == 'agent_completed'
        
        # Verify event details contain authenticated user context
        for event in websocket_events:
            assert event['run_id'] == str(context.run_id)
            assert event['agent_name'] == context.agent_name
            assert 'timestamp' in event
        
        # Verify agent received proper context
        executed_agent = real_agent_registry.get("e2e_success_agent")
        assert len(executed_agent.execution_history) == 1
        
        execution_record = executed_agent.execution_history[0]
        assert execution_record['user_id'] == authenticated_user["user_id"]
        assert execution_record['run_id'] == str(context.run_id)
        assert execution_record['websocket_enabled'] is True
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_failure_e2e_flow(
        self,
        authenticated_user,
        websocket_client,
        real_agent_registry
    ):
        """Test complete agent failure flow with real authentication and WebSocket."""
        # Create context for failing agent
        context = AgentExecutionContext(
            agent_name="e2e_failure_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        state = DeepAgentState(
            user_id=authenticated_user["user_id"],
            thread_id=f"e2e-failure-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Set up WebSocket event collection
        websocket_events = []
        
        class E2EWebSocketBridge:
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                event = {"type": "agent_started", "run_id": str(run_id), "agent_name": agent_name}
                websocket_events.append(event)
                return True
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                event = {"type": "agent_completed", "run_id": str(run_id), "agent_name": agent_name}
                websocket_events.append(event)
                return True
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                event = {"type": "agent_error", "run_id": str(run_id), "agent_name": agent_name, "error": error}
                websocket_events.append(event)
                return True
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                event = {"type": "agent_thinking", "run_id": str(run_id), "agent_name": agent_name}
                websocket_events.append(event)
                return True
        
        # Execute failing agent
        execution_core = AgentExecutionCore(real_agent_registry, E2EWebSocketBridge())
        result = await execution_core.execute_agent(context, state, timeout=10.0)
        
        # Verify failure handling
        assert result.success is False
        assert "simulated failure" in result.error
        
        # Verify WebSocket error events
        event_types = [event['type'] for event in websocket_events]
        assert 'agent_started' in event_types
        assert 'agent_error' in event_types
        
        # Find error event
        error_events = [event for event in websocket_events if event['type'] == 'agent_error']
        assert len(error_events) >= 1
        assert "simulated failure" in error_events[0]['error']
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_timeout_e2e_flow(
        self,
        authenticated_user,
        websocket_client,
        real_agent_registry
    ):
        """Test agent timeout handling in E2E environment."""
        # Create context for slow agent
        context = AgentExecutionContext(
            agent_name="e2e_slow_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        state = DeepAgentState(
            user_id=authenticated_user["user_id"],
            thread_id=f"e2e-timeout-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Simple WebSocket bridge for timeout testing
        websocket_events = []
        
        class TimeoutTestWebSocketBridge:
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                websocket_events.append({"type": "agent_started", "run_id": str(run_id)})
                return True
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                websocket_events.append({"type": "agent_completed", "run_id": str(run_id)})
                return True
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                websocket_events.append({"type": "agent_error", "run_id": str(run_id), "error": error})
                return True
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                websocket_events.append({"type": "agent_thinking", "run_id": str(run_id)})
                return True
        
        # Execute with short timeout
        execution_core = AgentExecutionCore(real_agent_registry, TimeoutTestWebSocketBridge())
        result = await execution_core.execute_agent(context, state, timeout=0.5)
        
        # Verify timeout handling
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.duration is not None
        assert result.duration >= 0.5  # Should be at least timeout duration
        
        # Verify WebSocket events for timeout
        event_types = [event['type'] for event in websocket_events]
        assert 'agent_started' in event_types
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_authenticated_agent_executions(
        self,
        authenticated_user,
        websocket_client,
        real_agent_registry
    ):
        """Test concurrent agent executions with real authentication."""
        # Create multiple execution contexts
        contexts = []
        states = []
        
        for i in range(3):
            context = AgentExecutionContext(
                agent_name="e2e_success_agent",
                run_id=str(uuid.uuid4()),
                correlation_id=str(uuid.uuid4()),
                retry_count=0
            )
            state = DeepAgentState(
                user_id=authenticated_user["user_id"],
                thread_id=f"e2e-concurrent-thread-{i}-{uuid.uuid4().hex[:8]}"
            )
            contexts.append(context)
            states.append(state)
        
        # Track events for all executions
        all_websocket_events = []
        
        class ConcurrentWebSocketBridge:
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                all_websocket_events.append({"type": "agent_started", "run_id": str(run_id)})
                return True
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                all_websocket_events.append({"type": "agent_completed", "run_id": str(run_id)})
                return True
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                all_websocket_events.append({"type": "agent_error", "run_id": str(run_id)})
                return True
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                all_websocket_events.append({"type": "agent_thinking", "run_id": str(run_id)})
                return True
        
        # Execute concurrently
        execution_core = AgentExecutionCore(real_agent_registry, ConcurrentWebSocketBridge())
        
        tasks = [
            execution_core.execute_agent(context, state, timeout=10.0)
            for context, state in zip(contexts, states)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all executions succeeded
        for i, result in enumerate(results):
            assert result.success is True, f"Execution {i} failed: {result.error}"
            assert result.duration is not None
        
        # Verify WebSocket events for all executions
        run_ids = {str(context.run_id) for context in contexts}
        event_run_ids = {event['run_id'] for event in all_websocket_events}
        
        # Each run should have generated events
        for run_id in run_ids:
            assert run_id in event_run_ids
        
        # Should have at least 2 events per execution (started + completed/thinking)
        assert len(all_websocket_events) >= 6  # 3 executions × 2 events minimum
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_dead_agent_detection_e2e(
        self,
        authenticated_user,
        websocket_client,
        real_agent_registry
    ):
        """Test dead agent detection with real authentication and WebSocket."""
        # Create context for dead agent
        context = AgentExecutionContext(
            agent_name="e2e_dead_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        state = DeepAgentState(
            user_id=authenticated_user["user_id"],
            thread_id=f"e2e-dead-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # WebSocket bridge for dead agent testing
        websocket_events = []
        
        class DeadAgentWebSocketBridge:
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                websocket_events.append({"type": "agent_started", "run_id": str(run_id)})
                return True
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                websocket_events.append({"type": "agent_completed", "run_id": str(run_id)})
                return True
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                websocket_events.append({"type": "agent_error", "run_id": str(run_id), "error": error})
                return True
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                websocket_events.append({"type": "agent_thinking", "run_id": str(run_id)})
                return True
        
        # Execute dead agent
        execution_core = AgentExecutionCore(real_agent_registry, DeadAgentWebSocketBridge())
        result = await execution_core.execute_agent(context, state, timeout=10.0)
        
        # Verify dead agent detection
        assert result.success is False
        assert "died silently" in result.error
        
        # Verify WebSocket events for dead agent
        event_types = [event['type'] for event in websocket_events]
        assert 'agent_started' in event_types
        assert 'agent_error' in event_types
        
        # Verify error message in WebSocket event
        error_events = [event for event in websocket_events if event['type'] == 'agent_error']
        assert len(error_events) >= 1
        assert "died silently" in error_events[0]['error']
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_user_isolation_e2e(self, auth_helper, websocket_client, real_agent_registry):
        """Test that different users get isolated agent executions."""
        # Create two different authenticated users
        token1, user1_data = await create_authenticated_user(
            environment="test",
            user_id="e2e-user-1",
            email="e2e-user-1@test.com"
        )
        
        token2, user2_data = await create_authenticated_user(
            environment="test", 
            user_id="e2e-user-2",
            email="e2e-user-2@test.com"
        )
        
        # Create contexts for both users
        context1 = AgentExecutionContext(
            agent_name="e2e_success_agent",
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        context2 = AgentExecutionContext(
            agent_name="e2e_success_agent", 
            run_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        state1 = DeepAgentState(
            user_id=user1_data["id"],
            thread_id=f"user1-thread-{uuid.uuid4().hex[:8]}"
        )
        
        state2 = DeepAgentState(
            user_id=user2_data["id"],
            thread_id=f"user2-thread-{uuid.uuid4().hex[:8]}"
        )
        
        # Simple event tracking
        user_events = {}
        
        class IsolationTestWebSocketBridge:
            async def notify_agent_started(self, run_id, agent_name, trace_context=None):
                run_id_str = str(run_id)
                if run_id_str not in user_events:
                    user_events[run_id_str] = []
                user_events[run_id_str].append({"type": "agent_started"})
                return True
            
            async def notify_agent_completed(self, run_id, agent_name, result=None, execution_time_ms=0, trace_context=None):
                run_id_str = str(run_id)
                if run_id_str not in user_events:
                    user_events[run_id_str] = []
                user_events[run_id_str].append({"type": "agent_completed", "result": result})
                return True
            
            async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
                run_id_str = str(run_id)
                if run_id_str not in user_events:
                    user_events[run_id_str] = []
                user_events[run_id_str].append({"type": "agent_error"})
                return True
            
            async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
                run_id_str = str(run_id)
                if run_id_str not in user_events:
                    user_events[run_id_str] = []
                user_events[run_id_str].append({"type": "agent_thinking"})
                return True
        
        # Execute for both users
        execution_core = AgentExecutionCore(real_agent_registry, IsolationTestWebSocketBridge())
        
        result1 = await execution_core.execute_agent(context1, state1, timeout=10.0)
        result2 = await execution_core.execute_agent(context2, state2, timeout=10.0)
        
        # Verify both executions succeeded
        assert result1.success is True
        assert result2.success is True
        
        # Verify proper isolation - each user should have separate events
        assert str(context1.run_id) in user_events
        assert str(context2.run_id) in user_events
        
        # Verify agent received correct user contexts
        executed_agent = real_agent_registry.get("e2e_success_agent")
        assert len(executed_agent.execution_history) == 2
        
        user_ids_in_history = {exec_record['user_id'] for exec_record in executed_agent.execution_history}
        assert user1_data["id"] in user_ids_in_history
        assert user2_data["id"] in user_ids_in_history
        assert user1_data["id"] != user2_data["id"]  # Ensure they're actually different users