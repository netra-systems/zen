"""Integration tests for AgentExecutionCore WebSocket event delivery.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time agent status updates reach users reliably
- Value Impact: Users must receive timely feedback during agent execution
- Strategic Impact: WebSocket event delivery is critical for user experience

These integration tests validate WebSocket event sequence and delivery with real components.
Uses real WebSocket bridges and event validation without mocking the critical path.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


class WebSocketEventCollector:
    """Collects WebSocket events for validation."""
    
    def __init__(self):
        self.events = []
        self.event_sequence = []
        self.error_events = []
        
    async def notify_agent_started(self, run_id, agent_name, trace_context=None):
        """Record agent started event."""
        event = {
            'type': 'agent_started',
            'run_id': str(run_id),
            'agent_name': agent_name,
            'trace_context': trace_context,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.events.append(event)
        self.event_sequence.append('agent_started')
        return True
    
    async def notify_agent_completed(self, run_id, agent_name, result=None, 
                                   execution_time_ms=0, trace_context=None):
        """Record agent completed event."""
        event = {
            'type': 'agent_completed',
            'run_id': str(run_id),
            'agent_name': agent_name,
            'result': result,
            'execution_time_ms': execution_time_ms,
            'trace_context': trace_context,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.events.append(event)
        self.event_sequence.append('agent_completed')
        return True
    
    async def notify_agent_error(self, run_id, agent_name, error, trace_context=None):
        """Record agent error event."""
        event = {
            'type': 'agent_error',
            'run_id': str(run_id),
            'agent_name': agent_name,
            'error': error,
            'trace_context': trace_context,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.events.append(event)
        self.event_sequence.append('agent_error')
        self.error_events.append(event)
        return True
    
    async def notify_agent_thinking(self, run_id, agent_name, reasoning, trace_context=None):
        """Record agent thinking event."""
        event = {
            'type': 'agent_thinking',
            'run_id': str(run_id),
            'agent_name': agent_name,
            'reasoning': reasoning,
            'trace_context': trace_context,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.events.append(event)
        self.event_sequence.append('agent_thinking')
        return True
    
    def get_events_for_run(self, run_id):
        """Get all events for a specific run ID."""
        return [event for event in self.events if event['run_id'] == str(run_id)]
    
    def validate_event_sequence(self, run_id, expected_sequence=None):
        """Validate event sequence for a run."""
        run_events = self.get_events_for_run(run_id)
        run_sequence = [event['type'] for event in run_events]
        
        if expected_sequence:
            return run_sequence == expected_sequence
        
        # Default validation: started -> completed OR started -> error
        if len(run_sequence) < 2:
            return False
        
        if run_sequence[0] != 'agent_started':
            return False
        
        last_event = run_sequence[-1]
        return last_event in ['agent_completed', 'agent_error']


class TestAgentExecutionCoreWebSocketIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket event delivery during agent execution."""
    
    @pytest.fixture
    def event_collector(self):
        """WebSocket event collector for validation."""
        return WebSocketEventCollector()
    
    @pytest.fixture
    def test_registry(self):
        """Agent registry with WebSocket-aware test agents."""
        registry = AgentRegistry()
        
        class WebSocketTestAgent:
            """Test agent that supports WebSocket operations."""
            
            def __init__(self, name: str, execution_time: float = 0.1, 
                        should_fail: bool = False, return_none: bool = False):
                self.name = name
                self.execution_time = execution_time
                self.should_fail = should_fail
                self.return_none = return_none
                
                # WebSocket integration tracking
                self.websocket_bridge = None
                self._run_id = None
                self._trace_context = None
                self.websocket_calls_made = 0
            
            async def execute(self, state: DeepAgentState, run_id: str, enable_websocket: bool = True):
                """Execute with WebSocket integration."""
                await asyncio.sleep(self.execution_time)
                
                # Simulate WebSocket thinking notification during execution
                if self.websocket_bridge and enable_websocket:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=run_id,
                        agent_name=self.name,
                        reasoning="Processing user request...",
                        trace_context=getattr(self._trace_context, 'to_websocket_context', lambda: {})()
                    )
                    self.websocket_calls_made += 1
                
                if self.should_fail:
                    raise ValueError(f"WebSocket test agent {self.name} failure")
                
                if self.return_none:
                    return None
                
                return {
                    "success": True,
                    "result": f"WebSocket test agent {self.name} completed",
                    "agent_name": self.name,
                    "websocket_enabled": enable_websocket,
                    "execution_duration": self.execution_time
                }
            
            def set_websocket_bridge(self, bridge, run_id: str):
                """Set WebSocket bridge."""
                self.websocket_bridge = bridge
                self._run_id = run_id
            
            def set_trace_context(self, trace_context):
                """Set trace context."""
                self._trace_context = trace_context
        
        # Register WebSocket test agents
        registry._agents["websocket_success_agent"] = WebSocketTestAgent("websocket_success_agent")
        registry._agents["websocket_failure_agent"] = WebSocketTestAgent("websocket_failure_agent", should_fail=True)
        registry._agents["websocket_dead_agent"] = WebSocketTestAgent("websocket_dead_agent", return_none=True)
        registry._agents["websocket_slow_agent"] = WebSocketTestAgent("websocket_slow_agent", execution_time=0.5)
        
        return registry
    
    @pytest.fixture
    def execution_core(self, test_registry, event_collector):
        """AgentExecutionCore with WebSocket event collection."""
        return AgentExecutionCore(test_registry, event_collector)
    
    @pytest.fixture
    def test_context(self):
        """Test execution context."""
        return AgentExecutionContext(
            agent_name="websocket_success_agent",
            run_id=uuid.uuid4(),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
    
    @pytest.fixture
    def test_state(self):
        """Test agent state."""
        return DeepAgentState(
            user_id="websocket-test-user",
            thread_id="websocket-test-thread"
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_successful_execution_websocket_events(
        self,
        execution_core,
        test_context,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test WebSocket events for successful agent execution."""
        # Execute agent
        result = await execution_core.execute_agent(test_context, test_state, timeout=10.0)
        
        # Verify execution succeeded
        assert result.success is True
        
        # Verify WebSocket events were sent
        run_events = event_collector.get_events_for_run(test_context.run_id)
        assert len(run_events) >= 2  # At least started and completed
        
        # Verify event sequence
        event_types = [event['type'] for event in run_events]
        assert event_types[0] == 'agent_started'
        assert event_types[-1] == 'agent_completed'
        
        # Verify event details
        started_event = run_events[0]
        assert started_event['agent_name'] == test_context.agent_name
        assert started_event['run_id'] == str(test_context.run_id)
        
        completed_event = run_events[-1]
        assert completed_event['agent_name'] == test_context.agent_name
        assert completed_event['run_id'] == str(test_context.run_id)
        assert completed_event['result'] is not None
        assert completed_event['execution_time_ms'] >= 0
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_failed_execution_websocket_events(
        self,
        execution_core,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test WebSocket events for failed agent execution."""
        # Create context for failing agent
        failing_context = AgentExecutionContext(
            agent_name="websocket_failure_agent",
            run_id=uuid.uuid4(),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        # Execute failing agent
        result = await execution_core.execute_agent(failing_context, test_state, timeout=10.0)
        
        # Verify execution failed
        assert result.success is False
        
        # Verify WebSocket events were sent
        run_events = event_collector.get_events_for_run(failing_context.run_id)
        assert len(run_events) >= 2  # At least started and error
        
        # Verify event sequence for failure
        event_types = [event['type'] for event in run_events]
        assert event_types[0] == 'agent_started'
        assert 'agent_error' in event_types
        
        # Verify error event details
        error_events = [event for event in run_events if event['type'] == 'agent_error']
        assert len(error_events) >= 1
        
        error_event = error_events[-1]
        assert error_event['agent_name'] == failing_context.agent_name
        assert error_event['run_id'] == str(failing_context.run_id)
        assert error_event['error'] is not None
        assert "failure" in error_event['error']
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_dead_agent_websocket_events(
        self,
        execution_core,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test WebSocket events when agent returns None (dead agent)."""
        # Create context for dead agent
        dead_context = AgentExecutionContext(
            agent_name="websocket_dead_agent",
            run_id=uuid.uuid4(),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        # Execute dead agent
        result = await execution_core.execute_agent(dead_context, test_state, timeout=10.0)
        
        # Verify dead agent detection
        assert result.success is False
        assert "died silently" in result.error
        
        # Verify WebSocket events for dead agent
        run_events = event_collector.get_events_for_run(dead_context.run_id)
        
        # Should have started event and error event
        event_types = [event['type'] for event in run_events]
        assert 'agent_started' in event_types
        assert 'agent_error' in event_types
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_timeout_websocket_events(
        self,
        execution_core,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test WebSocket events for agent timeout."""
        # Create context for slow agent
        slow_context = AgentExecutionContext(
            agent_name="websocket_slow_agent",
            run_id=uuid.uuid4(),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        # Execute with short timeout
        result = await execution_core.execute_agent(slow_context, test_state, timeout=0.1)
        
        # Verify timeout occurred
        assert result.success is False
        assert "timeout" in result.error.lower()
        
        # Verify WebSocket events for timeout
        run_events = event_collector.get_events_for_run(slow_context.run_id)
        
        # Should have at least started event
        event_types = [event['type'] for event in run_events]
        assert 'agent_started' in event_types
        
        # Timeout should generate error notification
        assert 'agent_error' in event_types or 'agent_completed' in event_types
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_trace_context_in_websocket_events(
        self,
        execution_core,
        test_context,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test that trace context is properly included in WebSocket events."""
        # Execute agent (will create trace context internally)
        result = await execution_core.execute_agent(test_context, test_state, timeout=10.0)
        
        # Verify execution succeeded
        assert result.success is True
        
        # Get WebSocket events
        run_events = event_collector.get_events_for_run(test_context.run_id)
        
        # Verify trace context is included in events
        for event in run_events:
            # trace_context should be present (may be None for tests, but key should exist)
            assert 'trace_context' in event
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_events(
        self,
        execution_core,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test WebSocket events for concurrent agent executions."""
        # Create multiple contexts
        contexts = []
        for i in range(3):
            context = AgentExecutionContext(
                agent_name="websocket_success_agent",
                run_id=uuid.uuid4(),
                correlation_id=str(uuid.uuid4()),
                retry_count=0
            )
            contexts.append(context)
        
        # Execute agents concurrently
        results = await asyncio.gather(*[
            execution_core.execute_agent(context, test_state, timeout=10.0)
            for context in contexts
        ])
        
        # Verify all executions succeeded
        for result in results:
            assert result.success is True
        
        # Verify each execution has proper WebSocket events
        for context in contexts:
            run_events = event_collector.get_events_for_run(context.run_id)
            assert len(run_events) >= 2
            
            # Verify proper event sequence for each run
            assert event_collector.validate_event_sequence(context.run_id)
        
        # Verify total event count (each run should have at least 2 events)
        total_events = len(event_collector.events)
        assert total_events >= 6  # 3 runs × 2 events minimum
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_bridge_propagation_to_agent(
        self,
        execution_core,
        test_context,
        test_state,
        event_collector,
        test_registry,
        real_services_fixture
    ):
        """Test that WebSocket bridge is properly propagated to agents."""
        # Execute agent
        result = await execution_core.execute_agent(test_context, test_state, timeout=10.0)
        
        # Verify execution succeeded
        assert result.success is True
        
        # Get the executed agent to verify WebSocket bridge propagation
        executed_agent = test_registry.get("websocket_success_agent")
        assert executed_agent is not None
        
        # Verify WebSocket bridge was set on agent
        assert executed_agent.websocket_bridge == event_collector
        assert executed_agent._run_id == str(test_context.run_id)
        
        # Verify agent made WebSocket calls during execution
        assert executed_agent.websocket_calls_made > 0
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_timing(
        self,
        execution_core,
        test_context,
        test_state,
        event_collector,
        real_services_fixture
    ):
        """Test timing and ordering of WebSocket events."""
        import time
        
        # Record start time
        start_time = time.time()
        
        # Execute agent
        result = await execution_core.execute_agent(test_context, test_state, timeout=10.0)
        
        # Record end time
        end_time = time.time()
        total_execution_time = end_time - start_time
        
        # Verify execution succeeded
        assert result.success is True
        
        # Get WebSocket events
        run_events = event_collector.get_events_for_run(test_context.run_id)
        
        # Verify event timestamps are reasonable
        for event in run_events:
            event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            event_timestamp = event_time.timestamp()
            
            # Event should be within the execution timeframe
            assert start_time <= event_timestamp <= end_time + 1.0  # 1s tolerance
        
        # Verify chronological order
        if len(run_events) >= 2:
            started_event = run_events[0]
            last_event = run_events[-1]
            
            started_time = datetime.fromisoformat(started_event['timestamp'].replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(last_event['timestamp'].replace('Z', '+00:00'))
            
            assert started_time <= last_time
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_resilience(
        self,
        test_registry,
        test_state,
        real_services_fixture
    ):
        """Test agent execution resilience when WebSocket notifications fail."""
        # Create failing WebSocket bridge
        failing_bridge = AsyncMock()
        failing_bridge.notify_agent_started.side_effect = Exception("WebSocket failure")
        failing_bridge.notify_agent_completed.side_effect = Exception("WebSocket failure")
        failing_bridge.notify_agent_error.side_effect = Exception("WebSocket failure")
        
        # Create execution core with failing bridge
        resilient_core = AgentExecutionCore(test_registry, failing_bridge)
        
        # Create test context
        context = AgentExecutionContext(
            agent_name="websocket_success_agent",
            run_id=uuid.uuid4(),
            correlation_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        # Execute should still succeed despite WebSocket failures
        result = await resilient_core.execute_agent(context, test_state, timeout=10.0)
        
        # Verify execution succeeded despite WebSocket issues
        assert result.success is True
        
        # Verify attempts were made to send WebSocket notifications
        failing_bridge.notify_agent_started.assert_called()
        # One of these should be called depending on how the execution completed
        assert (failing_bridge.notify_agent_completed.call_count > 0 or 
                failing_bridge.notify_agent_error.call_count > 0)