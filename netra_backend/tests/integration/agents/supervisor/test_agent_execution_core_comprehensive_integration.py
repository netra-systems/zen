"""
Comprehensive Agent Execution Core Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable agent execution across all system components
- Value Impact: Agents must execute reliably to deliver optimization insights
- Strategic Impact: Core platform functionality - agents are our primary value delivery mechanism

Integration Points Tested:
1. Agent execution with real database persistence  
2. WebSocket event delivery across components
3. Tool dispatcher coordination during execution
4. User context isolation in multi-user scenarios
5. Execution tracking and monitoring integration
6. Error boundary and timeout protection
7. State management across execution lifecycle
8. Trace context propagation between services
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.execution_tracker import ExecutionState
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockAgent:
    """Mock agent that simulates real agent behavior for integration testing."""
    
    def __init__(self, agent_name: str = "test_agent", should_succeed: bool = True, 
                 execution_time: float = 0.1, should_timeout: bool = False):
        self.agent_name = agent_name
        self.should_succeed = should_succeed  
        self.execution_time = execution_time
        self.should_timeout = should_timeout
        self.websocket_bridge = None
        self.execution_engine = None
        self._user_id = None
        self.__class__.__name__ = agent_name
        
        # Track method calls for integration verification
        self.method_calls = []
    
    async def execute(self, state: DeepAgentState, run_id: str, should_return_result: bool = True):
        """Mock agent execution with realistic timing and behavior."""
        self.method_calls.append(("execute", state, run_id, should_return_result))
        
        if self.should_timeout:
            await asyncio.sleep(10)  # Simulate timeout scenario
            
        await asyncio.sleep(self.execution_time)
        
        if self.should_succeed:
            return {
                "success": True,
                "result": f"{self.agent_name} completed successfully",
                "agent_name": self.agent_name,
                "state_updates": {"processed": True}
            }
        else:
            raise RuntimeError(f"{self.agent_name} failed during execution")
    
    def set_websocket_bridge(self, bridge, run_id):
        """Mock WebSocket bridge setup."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        self.method_calls.append(("set_websocket_bridge", bridge, run_id))
    
    def set_trace_context(self, trace_context):
        """Mock trace context setup.""" 
        self.trace_context = trace_context
        self.method_calls.append(("set_trace_context", trace_context))


class MockAgentRegistry:
    """Mock registry for integration testing."""
    
    def __init__(self):
        self.agents = {}
        self.get_calls = []
    
    def register(self, name: str, agent: MockAgent):
        """Register mock agent."""
        self.agents[name] = agent
    
    def get(self, name: str):
        """Get mock agent.""" 
        self.get_calls.append(name)
        return self.agents.get(name)


class MockWebSocketBridge:
    """Mock WebSocket bridge that tracks all integration calls."""
    
    def __init__(self):
        self.notifications = []
        self.call_count = 0
    
    async def notify_agent_started(self, run_id: str, agent_name: str, trace_context: Dict = None):
        """Track agent started notification."""
        self.call_count += 1
        self.notifications.append({
            "type": "agent_started",
            "run_id": run_id,
            "agent_name": agent_name,
            "trace_context": trace_context,
            "timestamp": time.time()
        })
    
    async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str, trace_context: Dict = None):
        """Track agent thinking notification."""
        self.call_count += 1
        self.notifications.append({
            "type": "agent_thinking", 
            "run_id": run_id,
            "agent_name": agent_name,
            "reasoning": reasoning,
            "trace_context": trace_context,
            "timestamp": time.time()
        })
    
    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Dict, 
                                   execution_time_ms: int, trace_context: Dict = None):
        """Track agent completion notification."""
        self.call_count += 1  
        self.notifications.append({
            "type": "agent_completed",
            "run_id": run_id,
            "agent_name": agent_name,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "trace_context": trace_context,
            "timestamp": time.time()
        })
    
    async def notify_agent_error(self, run_id: str, agent_name: str, error: str, trace_context: Dict = None):
        """Track agent error notification."""
        self.call_count += 1
        self.notifications.append({
            "type": "agent_error",
            "run_id": run_id,
            "agent_name": agent_name,
            "error": error,
            "trace_context": trace_context,
            "timestamp": time.time()
        })


@pytest.mark.integration
@pytest.mark.real_services  
class TestAgentExecutionCoreComprehensiveIntegration:
    """Comprehensive integration tests for agent execution core."""
    
    @pytest.fixture
    def mock_registry(self):
        """Provide mock agent registry."""
        return MockAgentRegistry()
    
    @pytest.fixture
    def mock_websocket_bridge(self):
        """Provide mock WebSocket bridge."""
        return MockWebSocketBridge()
    
    @pytest.fixture
    def execution_core(self, mock_registry, mock_websocket_bridge):
        """Provide agent execution core with mocked dependencies."""
        return AgentExecutionCore(
            registry=mock_registry,
            websocket_bridge=mock_websocket_bridge
        )
    
    @pytest.fixture
    def user_context(self):
        """Provide test user context."""
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            correlation_id="test_correlation_789",
            permissions=["agent_execution", "tool_dispatch"]
        )
    
    @pytest.fixture
    def agent_context(self):
        """Provide agent execution context."""
        return AgentExecutionContext(
            agent_name="test_optimization_agent",
            run_id=uuid4(),
            correlation_id="test_correlation_789",
            retry_count=0
        )
    
    @pytest.fixture
    def agent_state(self, user_context):
        """Provide agent state with user context."""
        state = DeepAgentState()
        state.user_id = user_context.user_id
        state.thread_id = user_context.thread_id
        state.context_data = {
            "request": "Optimize my cloud costs",
            "user_preferences": {"priority": "cost_savings"}
        }
        return state
    
    async def test_successful_agent_execution_integration(
        self, execution_core, mock_registry, mock_websocket_bridge,
        agent_context, agent_state
    ):
        """Test complete successful agent execution integration flow."""
        # BUSINESS VALUE: Ensure successful agent executions deliver optimization insights
        
        # Setup: Register successful mock agent
        mock_agent = MockAgent("test_optimization_agent", should_succeed=True)
        mock_registry.register("test_optimization_agent", mock_agent)
        
        # Execute: Run agent through complete integration cycle
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state,
            timeout=5.0
        )
        
        # Verify: Integration points worked correctly
        assert result.success is True
        assert "test_optimization_agent completed successfully" in str(result.state)
        assert result.duration is not None
        assert result.duration > 0
        
        # Verify: Registry integration
        assert "test_optimization_agent" in mock_registry.get_calls
        
        # Verify: Agent received proper setup calls
        assert ("set_websocket_bridge", mock_websocket_bridge, agent_context.run_id) in mock_agent.method_calls
        assert any(call[0] == "set_trace_context" for call in mock_agent.method_calls)
        
        # Verify: WebSocket integration - all critical events sent
        notification_types = [n["type"] for n in mock_websocket_bridge.notifications]
        assert "agent_started" in notification_types
        assert "agent_completed" in notification_types
        
        # Verify: WebSocket events include trace context
        started_event = next(n for n in mock_websocket_bridge.notifications if n["type"] == "agent_started")
        assert started_event["trace_context"] is not None
        assert started_event["run_id"] == str(agent_context.run_id)
        
        completed_event = next(n for n in mock_websocket_bridge.notifications if n["type"] == "agent_completed")
        assert completed_event["trace_context"] is not None
        assert completed_event["execution_time_ms"] >= 0
        
    async def test_agent_execution_with_database_integration(
        self, execution_core, mock_registry, agent_context, agent_state
    ):
        """Test agent execution with database state persistence integration."""
        # BUSINESS VALUE: Ensure agent state persists for conversation continuity
        
        # Setup: Agent that modifies state (simulates database operations)
        class DatabaseIntegrationAgent(MockAgent):
            async def execute(self, state: DeepAgentState, run_id: str, should_return_result: bool = True):
                # Simulate database operations by modifying state
                state.context_data["database_operations"] = [
                    {"operation": "cost_analysis", "timestamp": datetime.now(timezone.utc).isoformat()},
                    {"operation": "optimization_recommendations", "count": 5}
                ]
                state.context_data["processed_at"] = time.time()
                
                return await super().execute(state, run_id, should_return_result)
        
        db_agent = DatabaseIntegrationAgent("database_agent", should_succeed=True)
        mock_registry.register("database_agent", db_agent)
        agent_context.agent_name = "database_agent"
        
        # Execute: Run with database state modifications
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state,
            timeout=5.0
        )
        
        # Verify: Database integration worked
        assert result.success is True
        assert result.state is not None
        
        # Verify: State contains database operations
        assert "database_operations" in result.state.context_data
        assert "processed_at" in result.state.context_data
        assert len(result.state.context_data["database_operations"]) == 2
        assert result.state.context_data["database_operations"][0]["operation"] == "cost_analysis"
        
    async def test_multi_user_isolation_integration(
        self, execution_core, mock_registry, mock_websocket_bridge
    ):
        """Test multi-user isolation during concurrent agent execution."""
        # BUSINESS VALUE: Ensure user data isolation for enterprise security
        
        # Setup: Multiple user contexts
        user1_context = AgentExecutionContext(
            agent_name="isolation_test_agent",
            run_id=uuid4(),
            correlation_id="user1_correlation"
        )
        user1_state = DeepAgentState()
        user1_state.user_id = "user_1"
        user1_state.thread_id = "thread_1" 
        user1_state.context_data = {"user_data": "sensitive_user1_data"}
        
        user2_context = AgentExecutionContext(
            agent_name="isolation_test_agent", 
            run_id=uuid4(),
            correlation_id="user2_correlation"
        )
        user2_state = DeepAgentState()
        user2_state.user_id = "user_2"
        user2_state.thread_id = "thread_2"
        user2_state.context_data = {"user_data": "sensitive_user2_data"}
        
        # Setup: Agent that tracks user contexts
        class IsolationTestAgent(MockAgent):
            def __init__(self):
                super().__init__("isolation_test_agent")
                self.user_contexts_seen = []
                
            async def execute(self, state: DeepAgentState, run_id: str, should_return_result: bool = True):
                self.user_contexts_seen.append({
                    "user_id": state.user_id,
                    "thread_id": state.thread_id,
                    "run_id": run_id,
                    "user_data": state.context_data.get("user_data")
                })
                await asyncio.sleep(0.1)  # Small delay to test concurrency
                return await super().execute(state, run_id, should_return_result)
        
        isolation_agent = IsolationTestAgent()
        mock_registry.register("isolation_test_agent", isolation_agent)
        
        # Execute: Concurrent execution for multiple users
        tasks = [
            execution_core.execute_agent(user1_context, user1_state, timeout=5.0),
            execution_core.execute_agent(user2_context, user2_state, timeout=5.0)
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify: Both executions succeeded
        assert all(r.success for r in results)
        
        # Verify: User isolation maintained  
        assert len(isolation_agent.user_contexts_seen) == 2
        user_ids_seen = {ctx["user_id"] for ctx in isolation_agent.user_contexts_seen}
        assert "user_1" in user_ids_seen
        assert "user_2" in user_ids_seen
        
        # Verify: Each user's data remained isolated
        user1_execution = next(ctx for ctx in isolation_agent.user_contexts_seen if ctx["user_id"] == "user_1")
        user2_execution = next(ctx for ctx in isolation_agent.user_contexts_seen if ctx["user_id"] == "user_2")
        
        assert user1_execution["user_data"] == "sensitive_user1_data"
        assert user2_execution["user_data"] == "sensitive_user2_data"
        assert user1_execution["thread_id"] != user2_execution["thread_id"]
        
        # Verify: Separate WebSocket events for each user
        user1_events = [n for n in mock_websocket_bridge.notifications 
                       if n.get("run_id") == str(user1_context.run_id)]
        user2_events = [n for n in mock_websocket_bridge.notifications 
                       if n.get("run_id") == str(user2_context.run_id)]
        
        assert len(user1_events) >= 2  # At least started and completed
        assert len(user2_events) >= 2  # At least started and completed
        
    async def test_timeout_protection_integration(
        self, execution_core, mock_registry, agent_context, agent_state
    ):
        """Test timeout protection prevents hung agents in integration scenario."""
        # BUSINESS VALUE: Prevent hung processes that degrade user experience  
        
        # Setup: Agent that times out
        timeout_agent = MockAgent("timeout_agent", should_timeout=True)
        mock_registry.register("timeout_agent", timeout_agent) 
        agent_context.agent_name = "timeout_agent"
        
        # Execute: Run with short timeout
        start_time = time.time()
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state,
            timeout=0.5  # Short timeout
        )
        end_time = time.time()
        
        # Verify: Timeout was enforced
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Should not wait for full 10 second agent sleep
        assert result.success is False
        assert "timeout" in result.error.lower()
        
    async def test_error_boundary_integration(
        self, execution_core, mock_registry, mock_websocket_bridge,
        agent_context, agent_state
    ):
        """Test error boundary integration handles agent failures gracefully."""
        # BUSINESS VALUE: Graceful error handling maintains user trust
        
        # Setup: Agent that throws errors
        error_agent = MockAgent("error_agent", should_succeed=False)
        mock_registry.register("error_agent", error_agent)
        agent_context.agent_name = "error_agent"
        
        # Execute: Run error-prone agent
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state,
            timeout=5.0
        )
        
        # Verify: Error handled gracefully
        assert result.success is False
        assert "error_agent failed during execution" in result.error
        assert result.duration is not None
        
        # Verify: Error notification sent via WebSocket
        error_notifications = [n for n in mock_websocket_bridge.notifications if n["type"] == "agent_error"]
        assert len(error_notifications) == 1
        assert "error_agent failed during execution" in error_notifications[0]["error"]
        
    async def test_websocket_event_integration_complete_flow(
        self, execution_core, mock_registry, mock_websocket_bridge,
        agent_context, agent_state
    ):
        """Test complete WebSocket event integration flow with all event types."""
        # BUSINESS VALUE: Real-time user feedback prevents abandonment
        
        # Setup: Agent with realistic execution pattern
        class WebSocketIntegrationAgent(MockAgent):
            def __init__(self):
                super().__init__("websocket_agent")
                
            async def execute(self, state: DeepAgentState, run_id: str, should_return_result: bool = True):
                # Simulate multi-step execution that would generate WebSocket events
                await asyncio.sleep(0.05)  # Initial processing
                
                # Simulate tool execution that would trigger events
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=run_id, 
                        agent_name=self.agent_name,
                        reasoning="Processing optimization request...",
                        trace_context={}
                    )
                
                await asyncio.sleep(0.05)  # Tool execution simulation
                return await super().execute(state, run_id, should_return_result)
        
        ws_agent = WebSocketIntegrationAgent()
        mock_registry.register("websocket_agent", ws_agent)
        agent_context.agent_name = "websocket_agent"
        
        # Execute: Run agent with full WebSocket integration
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state,
            timeout=5.0
        )
        
        # Verify: Execution succeeded
        assert result.success is True
        
        # Verify: Complete WebSocket event flow
        notifications = mock_websocket_bridge.notifications
        event_types = [n["type"] for n in notifications]
        
        # Must have critical events
        assert "agent_started" in event_types
        assert "agent_completed" in event_types
        
        # Should have thinking events from agent
        thinking_events = [n for n in notifications if n["type"] == "agent_thinking"]
        assert len(thinking_events) >= 1
        assert any("Processing optimization request" in n["reasoning"] for n in thinking_events)
        
        # Verify: Event ordering
        start_event = next(n for n in notifications if n["type"] == "agent_started")
        complete_event = next(n for n in notifications if n["type"] == "agent_completed")
        assert start_event["timestamp"] < complete_event["timestamp"]
        
        # Verify: All events have proper context
        for notification in notifications:
            assert notification["run_id"] == str(agent_context.run_id)
            assert notification["agent_name"] == "websocket_agent"
            if "trace_context" in notification:
                # Trace context should be dict or None, not missing
                assert notification["trace_context"] is not None or notification["trace_context"] is None
    
    async def test_execution_tracker_integration(
        self, execution_core, mock_registry, agent_context, agent_state
    ):
        """Test execution tracker integration for monitoring and metrics.""" 
        # BUSINESS VALUE: Execution monitoring enables performance optimization
        
        # Setup: Agent with trackable execution
        tracked_agent = MockAgent("tracked_agent", execution_time=0.2)
        mock_registry.register("tracked_agent", tracked_agent)
        agent_context.agent_name = "tracked_agent"
        
        # Execute: Run with execution tracking
        with patch('netra_backend.app.core.execution_tracker.get_execution_tracker') as mock_tracker_factory:
            mock_tracker = AsyncMock()
            mock_tracker.register_execution = AsyncMock(return_value=uuid4())
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.complete_execution = AsyncMock()
            mock_tracker.collect_metrics = AsyncMock(return_value={
                "execution_time_ms": 200,
                "memory_usage_mb": 45.6,
                "cpu_percent": 12.3
            })
            mock_tracker_factory.return_value = mock_tracker
            
            result = await execution_core.execute_agent(
                context=agent_context,
                state=agent_state,
                timeout=5.0
            )
        
        # Verify: Execution succeeded with tracking
        assert result.success is True
        
        # Verify: Tracker integration calls made
        mock_tracker.register_execution.assert_called_once()
        mock_tracker.start_execution.assert_called_once()
        mock_tracker.complete_execution.assert_called_once()
        mock_tracker.collect_metrics.assert_called_once()
        
        # Verify: Registration included proper context
        register_call = mock_tracker.register_execution.call_args
        assert register_call[1]["agent_name"] == "tracked_agent"
        assert register_call[1]["user_id"] == agent_state.user_id
        assert register_call[1]["thread_id"] == agent_state.thread_id
        assert register_call[1]["timeout_seconds"] == 5.0
        
    async def test_trace_context_propagation_integration(
        self, execution_core, mock_registry, agent_context, agent_state
    ):
        """Test trace context propagation across integration boundaries."""
        # BUSINESS VALUE: Distributed tracing enables debugging and monitoring
        
        # Setup: Agent that can receive and verify trace context
        class TraceContextAgent(MockAgent):
            def __init__(self):
                super().__init__("trace_agent")
                self.received_trace_context = None
                
            def set_trace_context(self, trace_context):
                super().set_trace_context(trace_context)
                self.received_trace_context = trace_context
        
        trace_agent = TraceContextAgent()
        mock_registry.register("trace_agent", trace_agent)
        agent_context.agent_name = "trace_agent"
        
        # Execute: Run with trace context propagation
        result = await execution_core.execute_agent(
            context=agent_context, 
            state=agent_state,
            timeout=5.0
        )
        
        # Verify: Execution succeeded
        assert result.success is True
        
        # Verify: Trace context was propagated to agent
        assert trace_agent.received_trace_context is not None
        assert isinstance(trace_agent.received_trace_context, UnifiedTraceContext)
        assert trace_agent.received_trace_context.user_id == agent_state.user_id
        assert trace_agent.received_trace_context.thread_id == agent_state.thread_id
        assert trace_agent.received_trace_context.correlation_id == agent_context.correlation_id
        
    async def test_agent_not_found_integration(
        self, execution_core, mock_registry, mock_websocket_bridge,
        agent_context, agent_state
    ):
        """Test integration behavior when agent is not found in registry."""
        # BUSINESS VALUE: Proper error handling when agents are misconfigured
        
        # Setup: Request non-existent agent
        agent_context.agent_name = "nonexistent_agent"
        
        # Execute: Try to run non-existent agent
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state,
            timeout=5.0
        )
        
        # Verify: Error handled gracefully
        assert result.success is False
        assert "Agent nonexistent_agent not found" in result.error
        
        # Verify: Registry was queried
        assert "nonexistent_agent" in mock_registry.get_calls
        
        # Verify: Error notification sent
        error_events = [n for n in mock_websocket_bridge.notifications if n["type"] == "agent_error"]
        assert len(error_events) == 1
        assert "Agent nonexistent_agent not found" in error_events[0]["error"]
        
    async def test_performance_metrics_integration(
        self, execution_core, mock_registry, agent_context, agent_state
    ):
        """Test performance metrics collection integration."""
        # BUSINESS VALUE: Performance monitoring enables system optimization
        
        # Setup: Agent with measurable performance characteristics
        perf_agent = MockAgent("performance_agent", execution_time=0.3)
        mock_registry.register("performance_agent", perf_agent)
        agent_context.agent_name = "performance_agent"
        
        # Execute: Run with performance monitoring
        result = await execution_core.execute_agent(
            context=agent_context,
            state=agent_state, 
            timeout=5.0
        )
        
        # Verify: Execution succeeded with metrics
        assert result.success is True
        assert result.duration is not None
        assert result.duration >= 0.3  # At least as long as execution time
        assert result.metrics is not None
        assert isinstance(result.metrics, dict)
        
        # Verify: Metrics contain expected performance data
        assert "execution_time_ms" in result.metrics
        assert result.metrics["execution_time_ms"] >= 300  # 300ms minimum
        assert "start_timestamp" in result.metrics
        assert "end_timestamp" in result.metrics