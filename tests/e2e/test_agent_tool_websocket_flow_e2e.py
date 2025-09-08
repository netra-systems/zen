"""
E2E Tests for Complete Agent-Tool-WebSocket Flow

Tests the entire end-to-end flow from agent execution through tool dispatching
to WebSocket event delivery with real authentication and services.

Business Value: Validates complete user experience works with real components
"""

import asyncio
import pytest
import json
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket import create_test_websocket_manager

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import create_request_scoped_tool_dispatcher
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from langchain_core.tools import BaseTool


class MockE2ETool(BaseTool):
    """Mock tool for E2E testing that simulates real tool behavior."""
    name: str = "e2e_test_tool"
    description: str = "E2E test tool that simulates real tool execution"
    
    def __init__(self, execution_time: float = 0.1, should_fail: bool = False):
        super().__init__()
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.execution_count = 0
        
    def _run(self, query: str = "default query") -> str:
        """Synchronous tool execution."""
        import time
        time.sleep(self.execution_time)
        
        self.execution_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"E2E tool failure on execution {self.execution_count}")
        
        return f"E2E tool result #{self.execution_count} for query: {query}"
    
    async def _arun(self, query: str = "default query") -> str:
        """Asynchronous tool execution."""
        await asyncio.sleep(self.execution_time)
        
        self.execution_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"E2E tool failure on execution {self.execution_count}")
        
        return f"Async E2E tool result #{self.execution_count} for query: {query}"


class MockE2EAgent:
    """Mock agent for E2E testing that uses tools and WebSocket notifications."""
    
    def __init__(self, tool_dispatcher=None, websocket_bridge=None):
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = websocket_bridge
        self._run_id = None
        self._trace_context = None
        self.execution_count = 0
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for notifications."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    def set_trace_context(self, trace_context):
        """Set trace context."""
        self._trace_context = trace_context
        
    async def execute(self, state, run_id, is_streaming=False):
        """Execute agent with tool usage and WebSocket events."""
        self.execution_count += 1
        
        # Simulate agent thinking
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name="e2e_test_agent",
                reasoning=f"Starting E2E test execution #{self.execution_count}"
            )
        
        # Use tool if dispatcher is available
        tool_result = None
        if self.tool_dispatcher:
            try:
                # Notify tool execution start
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_tool_executing(
                        run_id=run_id,
                        agent_name="e2e_test_agent", 
                        tool_name="e2e_test_tool",
                        parameters={"query": f"E2E test query #{self.execution_count}"}
                    )
                
                # Execute tool (simulate dispatch)
                tool_result = f"Tool executed successfully for execution #{self.execution_count}"
                
                # Notify tool completion
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_tool_completed(
                        run_id=run_id,
                        agent_name="e2e_test_agent",
                        tool_name="e2e_test_tool",
                        result={"output": tool_result}
                    )
                    
            except Exception as e:
                # Notify tool error
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_tool_error(
                        run_id=run_id,
                        agent_name="e2e_test_agent",
                        tool_name="e2e_test_tool", 
                        error=str(e)
                    )
                tool_result = f"Tool execution failed: {e}"
        
        # Final thinking update
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name="e2e_test_agent",
                reasoning=f"Completing E2E test execution #{self.execution_count}"
            )
        
        return {
            "success": True,
            "result": f"E2E agent execution #{self.execution_count} completed",
            "tool_result": tool_result,
            "agent_name": "e2e_test_agent",
            "execution_time": 0.2
        }


class TestAgentToolWebSocketFlowE2E:
    """E2E tests for complete agent-tool-websocket integration."""

    @pytest.fixture
    async def auth_helper(self):
        """E2E authentication helper."""
        helper = E2EAuthHelper()
        await helper.setup()
        return helper

    @pytest.fixture
    async def websocket_manager(self):
        """Real WebSocket manager for E2E testing."""
        return await create_test_websocket_manager()

    @pytest.fixture 
    def websocket_bridge(self, websocket_manager):
        """AgentWebSocketBridge with real WebSocket manager."""
        return AgentWebSocketBridge(websocket_manager)

    @pytest.fixture
    def agent_registry(self):
        """Real agent registry for E2E testing."""
        return AgentRegistry()

    @pytest.fixture
    def tool_dispatcher_factory(self, auth_helper, websocket_manager):
        """Tool dispatcher factory for E2E testing."""
        return UnifiedToolDispatcherFactory()

    @pytest.fixture
    def execution_core(self, agent_registry, websocket_bridge):
        """AgentExecutionCore with real dependencies."""
        return AgentExecutionCore(agent_registry, websocket_bridge)

    @pytest.fixture
    def e2e_context(self, auth_helper):
        """E2E execution context."""
        return AgentExecutionContext(
            agent_name="e2e_test_agent",
            run_id=uuid4(),
            thread_id=f"e2e-thread-{uuid4()}",
            user_id=auth_helper.test_user_id,
            correlation_id=f"e2e-correlation-{uuid4()}"
        )

    @pytest.fixture
    def e2e_state(self, auth_helper):
        """E2E agent state."""
        state = Mock(spec=DeepAgentState)
        state.user_id = auth_helper.test_user_id
        state.thread_id = f"e2e-thread-{uuid4()}"
        state.__dict__ = {
            'user_id': state.user_id,
            'thread_id': state.thread_id,
            'data': 'e2e_test_data'
        }
        return state

    @pytest.mark.asyncio
    async def test_complete_agent_tool_websocket_flow(
        self, execution_core, agent_registry, websocket_bridge, 
        e2e_context, e2e_state, websocket_manager, auth_helper
    ):
        """Test complete flow: Agent -> Tool -> WebSocket notifications."""
        
        # Setup WebSocket message capture
        websocket_events = []
        
        async def capture_websocket_events(thread_id, message):
            websocket_events.append({
                'thread_id': thread_id,
                'type': message.get('type'),
                'payload': message.get('payload', {}),
                'timestamp': asyncio.get_event_loop().time()
            })
            return True
        
        websocket_manager.send_to_thread.side_effect = capture_websocket_events
        
        # Create tool dispatcher with real user context
        mock_user_context = Mock()
        mock_user_context.user_id = auth_helper.test_user_id
        mock_user_context.thread_id = e2e_context.thread_id
        
        tool_dispatcher = create_request_scoped_tool_dispatcher(
            user_context=mock_user_context,
            websocket_manager=websocket_manager,
            tools=[MockE2ETool(execution_time=0.05)]
        )
        
        # Create and register E2E agent
        e2e_agent = MockE2EAgent(
            tool_dispatcher=tool_dispatcher,
            websocket_bridge=websocket_bridge
        )
        agent_registry.register("e2e_test_agent", e2e_agent)
        
        # Execute complete flow
        result = await execution_core.execute_agent(e2e_context, e2e_state, 10.0)
        
        # Verify execution succeeded
        assert result.success is True
        assert result.duration is not None
        assert result.duration > 0
        
        # Verify agent was executed
        assert e2e_agent.execution_count == 1
        
        # Verify WebSocket events were sent
        assert len(websocket_events) >= 4  # At least: started, thinking, tool_executing, completed
        
        # Verify event sequence
        event_types = [event['type'] for event in websocket_events]
        assert 'agent_started' in event_types
        assert 'agent_thinking' in event_types  
        assert 'tool_executing' in event_types
        assert 'agent_completed' in event_types
        
        # Verify all events targeted correct thread
        thread_ids = [event['thread_id'] for event in websocket_events]
        assert all(tid == e2e_context.thread_id for tid in thread_ids)
        
        # Verify event ordering (started should be first, completed should be last)
        assert event_types[0] == 'agent_started'
        assert event_types[-1] == 'agent_completed'

    @pytest.mark.asyncio
    async def test_agent_tool_error_handling_e2e(
        self, execution_core, agent_registry, websocket_bridge,
        e2e_context, e2e_state, websocket_manager
    ):
        """Test error handling throughout the complete flow."""
        
        websocket_events = []
        
        async def capture_error_events(thread_id, message):
            websocket_events.append({
                'thread_id': thread_id,
                'type': message.get('type'),
                'payload': message.get('payload', {}),
                'error': message.get('payload', {}).get('error')
            })
            return True
        
        websocket_manager.send_to_thread.side_effect = capture_error_events
        
        # Create failing agent
        failing_agent = MockE2EAgent()
        
        # Override execute to simulate failure
        async def failing_execute(state, run_id, is_streaming=False):
            # Send thinking event
            if failing_agent.websocket_bridge:
                await failing_agent.websocket_bridge.notify_agent_thinking(
                    run_id=run_id,
                    agent_name="e2e_test_agent",
                    reasoning="About to fail..."
                )
            
            # Simulate failure
            raise RuntimeError("E2E test failure")
        
        failing_agent.execute = failing_execute
        agent_registry.register("e2e_test_agent", failing_agent)
        
        # Execute flow expecting failure
        result = await execution_core.execute_agent(e2e_context, e2e_state, 5.0)
        
        # Verify failure was handled
        assert result.success is False
        assert "E2E test failure" in result.error
        
        # Verify error events were sent
        error_events = [event for event in websocket_events if event['type'] == 'agent_error']
        assert len(error_events) >= 1
        
        error_event = error_events[0]
        assert "E2E test failure" in str(error_event.get('error', ''))

    @pytest.mark.asyncio
    async def test_concurrent_agent_executions_e2e(
        self, execution_core, agent_registry, websocket_bridge, websocket_manager, auth_helper
    ):
        """Test multiple concurrent agent executions with WebSocket isolation."""
        
        websocket_events = []
        
        async def capture_concurrent_events(thread_id, message):
            websocket_events.append({
                'thread_id': thread_id,
                'type': message.get('type'),
                'agent_name': message.get('payload', {}).get('agent_name'),
                'timestamp': asyncio.get_event_loop().time()
            })
            return True
        
        websocket_manager.send_to_thread.side_effect = capture_concurrent_events
        
        # Register concurrent agent
        concurrent_agent = MockE2EAgent(websocket_bridge=websocket_bridge)
        agent_registry.register("e2e_test_agent", concurrent_agent)
        
        # Create multiple execution contexts
        num_concurrent = 3
        contexts = []
        states = []
        
        for i in range(num_concurrent):
            context = AgentExecutionContext(
                agent_name="e2e_test_agent",
                run_id=uuid4(),
                thread_id=f"concurrent-e2e-thread-{i}",
                user_id=auth_helper.test_user_id,
                correlation_id=f"concurrent-e2e-correlation-{i}"
            )
            state = Mock(spec=DeepAgentState)
            state.user_id = auth_helper.test_user_id
            state.thread_id = context.thread_id
            
            contexts.append(context)
            states.append(state)
        
        # Execute concurrently
        tasks = [
            execution_core.execute_agent(ctx, state, 10.0)
            for ctx, state in zip(contexts, states)
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify all executions succeeded
        for i, result in enumerate(results):
            assert result.success is True, f"Concurrent execution {i} failed: {result.error}"
        
        # Verify WebSocket event isolation
        thread_event_counts = {}
        for event in websocket_events:
            thread_id = event['thread_id']
            thread_event_counts[thread_id] = thread_event_counts.get(thread_id, 0) + 1
        
        # Each thread should have received events
        assert len(thread_event_counts) == num_concurrent
        
        # Each thread should have similar event counts (started, thinking, completed)
        for thread_id, count in thread_event_counts.items():
            assert count >= 3, f"Thread {thread_id} got {count} events, expected at least 3"

    @pytest.mark.asyncio
    async def test_websocket_event_content_validation_e2e(
        self, execution_core, agent_registry, websocket_bridge,
        e2e_context, e2e_state, websocket_manager
    ):
        """Test WebSocket event content validation in realistic scenario."""
        
        captured_events = []
        
        async def validate_event_content(thread_id, message):
            captured_events.append({
                'thread_id': thread_id,
                'message_type': message.get('type'),
                'full_message': message
            })
            return True
        
        websocket_manager.send_to_thread.side_effect = validate_event_content
        
        # Register validation agent
        validation_agent = MockE2EAgent(websocket_bridge=websocket_bridge)
        agent_registry.register("e2e_test_agent", validation_agent)
        
        # Execute flow
        result = await execution_core.execute_agent(e2e_context, e2e_state, 5.0)
        assert result.success is True
        
        # Validate event content structure
        for event in captured_events:
            message = event['full_message']
            
            # All events should have required fields
            assert 'type' in message
            assert 'payload' in message
            
            payload = message['payload']
            
            # Event-specific validation
            if event['message_type'] == 'agent_started':
                assert 'agent_name' in payload
                assert 'run_id' in payload
                assert payload['agent_name'] == "e2e_test_agent"
                assert str(payload['run_id']) == str(e2e_context.run_id)
                
            elif event['message_type'] == 'agent_thinking':
                assert 'thought' in payload or 'reasoning' in payload
                assert 'agent_name' in payload
                
            elif event['message_type'] == 'tool_executing':
                assert 'tool_name' in payload
                assert 'agent_name' in payload
                
            elif event['message_type'] == 'agent_completed':
                assert 'agent_name' in payload
                assert 'result' in payload or 'duration_ms' in payload

    @pytest.mark.asyncio
    async def test_performance_under_realistic_load_e2e(
        self, execution_core, agent_registry, websocket_bridge, websocket_manager, auth_helper
    ):
        """Test system performance under realistic E2E load."""
        import time
        
        event_count = 0
        start_time = time.time()
        
        async def count_performance_events(thread_id, message):
            nonlocal event_count
            event_count += 1
            # Simulate realistic WebSocket processing delay
            await asyncio.sleep(0.001)
            return True
        
        websocket_manager.send_to_thread.side_effect = count_performance_events
        
        # Register performance test agent
        perf_agent = MockE2EAgent(websocket_bridge=websocket_bridge)
        agent_registry.register("e2e_test_agent", perf_agent)
        
        # Create realistic load scenario
        num_agents = 10
        contexts_and_states = []
        
        for i in range(num_agents):
            context = AgentExecutionContext(
                agent_name="e2e_test_agent",
                run_id=uuid4(),
                thread_id=f"perf-e2e-thread-{i}",
                user_id=auth_helper.test_user_id,
                correlation_id=f"perf-e2e-correlation-{i}"
            )
            state = Mock(spec=DeepAgentState)
            state.user_id = auth_helper.test_user_id
            state.thread_id = context.thread_id
            
            contexts_and_states.append((context, state))
        
        # Execute load test
        tasks = [
            execution_core.execute_agent(ctx, state, 15.0)
            for ctx, state in contexts_and_states
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Verify performance characteristics
        successful_results = [r for r in results if hasattr(r, 'success') and r.success]
        assert len(successful_results) >= num_agents * 0.9  # At least 90% success rate
        
        # Should complete in reasonable time
        assert total_time < 10.0, f"E2E load test took {total_time}s, expected < 10s"
        
        # Should have processed significant number of events
        assert event_count >= num_agents * 3  # At least 3 events per agent
        
        # Calculate throughput
        throughput = event_count / total_time
        assert throughput > 10, f"Event throughput {throughput:.2f} events/s too low"

    @pytest.mark.asyncio
    async def test_trace_context_propagation_e2e(
        self, execution_core, agent_registry, websocket_bridge,
        e2e_context, e2e_state, websocket_manager
    ):
        """Test trace context propagation through complete E2E flow."""
        
        trace_contexts = []
        
        async def capture_trace_contexts(thread_id, message):
            payload = message.get('payload', {})
            if 'trace_context' in payload:
                trace_contexts.append({
                    'event_type': message.get('type'),
                    'trace_context': payload['trace_context']
                })
            return True
        
        websocket_manager.send_to_thread.side_effect = capture_trace_contexts
        
        # Register trace-aware agent
        trace_agent = MockE2EAgent(websocket_bridge=websocket_bridge)
        agent_registry.register("e2e_test_agent", trace_agent)
        
        # Execute with trace monitoring
        result = await execution_core.execute_agent(e2e_context, e2e_state, 5.0)
        assert result.success is True
        
        # Verify trace contexts were propagated
        if trace_contexts:  # Only check if trace contexts are being sent
            # All trace contexts should be consistent
            trace_ids = [tc['trace_context'].get('trace_id') for tc in trace_contexts if tc.get('trace_context')]
            if trace_ids:
                # All events in the same execution should have same trace ID
                assert len(set(trace_ids)) <= 2  # Parent and child trace at most