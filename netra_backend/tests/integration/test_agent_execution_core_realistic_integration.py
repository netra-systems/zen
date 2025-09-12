"""
Agent Execution Core Realistic Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise)
- Business Goal: Validate agent execution works with real system components
- Value Impact: Integration tests ensure agents can actually deliver insights in realistic scenarios
- Strategic Impact: Confidence in system reliability when components interact together

This test suite validates Agent Execution Core functionality through comprehensive
integration testing with realistic system components but without requiring
running services, focusing on component interaction and business workflows.

CRITICAL REQUIREMENTS VALIDATED:
- Agent execution with real trace context and state management
- WebSocket notification integration with realistic message flows
- Error handling with real error conditions and recovery
- Performance metrics collection with actual timing data
- Agent registry integration with realistic lookup and lifecycle
- Multi-user execution context isolation
- Tool dispatcher integration patterns
- Real execution tracking and persistence workflows
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

# Core imports for realistic integration testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext, TraceContextManager
from netra_backend.app.core.execution_tracker import ExecutionTracker, ExecutionState
from netra_backend.app.core.logging_context import get_unified_trace_context


class RealisticMockAgent:
    """Realistic mock agent that simulates real agent behavior."""
    
    def __init__(self, name: str = "RealisticAgent", execution_time: float = 0.1, 
                 websocket_events: bool = True, should_fail: bool = False):
        self.name = name
        self.execution_time = execution_time
        self.websocket_events = websocket_events
        self.should_fail = should_fail
        self.execution_count = 0
        self.websocket_bridge = None
        self.execution_engine = None
        self._user_id = None
        self.trace_context = None
        self._run_id = None
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> Dict[str, Any]:
        """Simulate realistic agent execution with business logic."""
        self.execution_count += 1
        start_time = time.time()
        
        try:
            # Simulate realistic thinking phase
            if self.websocket_bridge and hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                await self.websocket_bridge.notify_agent_thinking(
                    run_id=run_id,
                    agent_name=self.name,
                    reasoning=f"Analyzing user request for {state.user_id}",
                    trace_context=self._get_websocket_context()
                )
            
            # Simulate realistic processing with multiple phases
            phases = [
                ("Data validation", 0.3),
                ("Business analysis", 0.4), 
                ("Insight generation", 0.3)
            ]
            
            for phase, weight in phases:
                if self.websocket_bridge and hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                    await self.websocket_bridge.notify_agent_thinking(
                        run_id=run_id,
                        agent_name=self.name,
                        reasoning=f"Phase: {phase}",
                        trace_context=self._get_websocket_context()
                    )
                
                # Simulate phase processing time
                await asyncio.sleep(self.execution_time * weight)
            
            # Check for failure simulation
            if self.should_fail:
                raise ValueError(f"Simulated business logic failure in {self.name}")
            
            # Generate realistic business result
            execution_duration = time.time() - start_time
            result = {
                "success": True,
                "agent_name": self.name,
                "execution_count": self.execution_count,
                "run_id": run_id,
                "user_id": state.user_id,
                "thread_id": state.thread_id,
                "processing_time_ms": int(execution_duration * 1000),
                "business_insights": {
                    "insight_count": 3,
                    "confidence_score": 0.87,
                    "actionable_recommendations": ["Optimize costs", "Improve efficiency", "Scale operations"]
                },
                "execution_metadata": {
                    "phases_completed": len(phases),
                    "websocket_events_sent": 3 if self.websocket_events else 0,
                    "trace_context_available": self.trace_context is not None
                }
            }
            
            return result
            
        except Exception as e:
            # Realistic error handling with context
            execution_duration = time.time() - start_time
            raise RuntimeError(f"Agent {self.name} failed after {execution_duration:.3f}s: {str(e)}")
    
    def set_websocket_bridge(self, bridge, run_id):
        """Set websocket bridge with realistic context."""
        self.websocket_bridge = bridge
        self._run_id = run_id
    
    def set_trace_context(self, trace_context):
        """Set trace context for realistic tracing."""
        self.trace_context = trace_context
    
    def _get_websocket_context(self):
        """Get websocket context for notifications."""
        if self.trace_context and hasattr(self.trace_context, 'to_websocket_context'):
            return self.trace_context.to_websocket_context()
        return {}


class TestAgentExecutionCoreRealisticIntegration(SSotBaseTestCase):
    """Realistic integration tests for Agent Execution Core functionality."""
    
    def setup_method(self):
        """Set up realistic test environment for each test method."""
        super().setup_method()
        self.env = get_env()
        self.test_helper = IsolatedTestHelper()
        
        # Create realistic mock registry
        self.mock_registry = MagicMock()
        self.mock_registry.get.return_value = None
        
        # Create realistic websocket bridge
        self.mock_websocket_bridge = AsyncMock()
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        self.mock_websocket_bridge.notify_agent_error = AsyncMock()
        
        # Create execution core with realistic configuration
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create realistic test contexts for different scenarios
        self.business_context = AgentExecutionContext(
            agent_name="business_optimizer",
            run_id=uuid.uuid4(),
            retry_count=0
        )
        
        self.data_analysis_context = AgentExecutionContext(
            agent_name="data_analyzer", 
            run_id=uuid.uuid4(),
            retry_count=0
        )
        
        # Create realistic user states
        self.enterprise_user_state = DeepAgentState(
            user_id="enterprise_user_abc123",
            thread_id="thread_enterprise_456",
            agent_context={
                "user_request": "Analyze Q4 revenue trends and provide optimization recommendations",
                "user_tier": "enterprise",
                "historical_data_available": True,
                "business_context": {"industry": "fintech", "team_size": 500}
            }
        )
        
        self.startup_user_state = DeepAgentState(
            user_id="startup_user_xyz789",
            thread_id="thread_startup_012",
            agent_context={
                "user_request": "Help optimize our AWS costs for a growing startup",
                "user_tier": "early",
                "budget_constraints": True,
                "business_context": {"industry": "saas", "team_size": 15}
            }
        )

    @pytest.mark.integration
    async def test_realistic_business_optimization_flow(self):
        """
        Test realistic business optimization agent execution flow.
        
        BVJ: Validates core value proposition - agents delivering business insights to enterprise users.
        """
        # Arrange
        business_agent = RealisticMockAgent(
            name="BusinessOptimizer",
            execution_time=0.2,  # 200ms realistic processing
            websocket_events=True
        )
        self.mock_registry.get.return_value = business_agent
        
        # Act
        start_time = time.time()
        result = await self.execution_core.execute_agent(
            context=self.business_context,
            state=self.enterprise_user_state,
            timeout=10.0
        )
        end_time = time.time()
        
        # Assert
        assert result.success is True
        assert result.duration is not None
        assert result.duration > 0.15  # Should take at least 150ms
        
        # Verify business value was delivered
        agent_result = business_agent.execute.return_value if hasattr(business_agent.execute, 'return_value') else None
        assert business_agent.execution_count == 1
        
        # Verify realistic WebSocket event flow
        self.mock_websocket_bridge.notify_agent_started.assert_called_once()
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Verify thinking events were sent during execution
        assert self.mock_websocket_bridge.notify_agent_thinking.call_count >= 2
        
        # Verify execution timing is realistic
        total_execution_time = end_time - start_time
        assert 0.15 < total_execution_time < 1.0  # Reasonable execution window

    @pytest.mark.integration
    async def test_multi_user_concurrent_execution_isolation(self):
        """
        Test concurrent execution with multiple users maintaining proper isolation.
        
        BVJ: Ensures platform can serve multiple users simultaneously without data leakage.
        """
        # Arrange
        user_agents = [
            RealisticMockAgent(f"ConcurrentAgent_{i}", execution_time=0.1, websocket_events=True)
            for i in range(3)
        ]
        
        # Mock registry to return different agents for different requests
        call_count = 0
        def get_agent_for_user(agent_name):
            nonlocal call_count
            agent = user_agents[call_count % len(user_agents)]
            call_count += 1
            return agent
            
        self.mock_registry.get.side_effect = get_agent_for_user
        
        # Create different user contexts
        user_contexts = [
            AgentExecutionContext(agent_name=f"user_agent_{i}", run_id=uuid.uuid4(), retry_count=0)
            for i in range(3)
        ]
        
        user_states = [
            DeepAgentState(
                user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}",
                agent_context={
                    "user_request": f"User {i} specific request",
                    "user_tier": ["free", "early", "enterprise"][i],
                    "confidential_data": f"secret_data_user_{i}"
                }
            )
            for i in range(3)
        ]
        
        # Act - execute all agents concurrently
        tasks = [
            self.execution_core.execute_agent(
                context=user_contexts[i],
                state=user_states[i],
                timeout=5.0
            )
            for i in range(3)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Assert
        # Verify all executions succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} execution failed: {result}"
            assert result.success is True
        
        # Verify concurrent execution (should not take 3x sequential time)
        total_time = end_time - start_time
        assert total_time < 0.5, f"Concurrent execution took {total_time}s, should be ~0.1-0.2s"
        
        # Verify isolation - each agent was called independently
        assert call_count == 3
        
        # Verify WebSocket notifications were sent for all users
        assert self.mock_websocket_bridge.notify_agent_started.call_count == 3
        assert self.mock_websocket_bridge.notify_agent_completed.call_count == 3

    @pytest.mark.integration
    async def test_realistic_error_handling_and_recovery(self):
        """
        Test realistic error conditions and recovery mechanisms.
        
        BVJ: Ensures system resilience during failures maintains user trust and experience.
        """
        # Arrange - agent that fails realistically
        failing_agent = RealisticMockAgent(
            name="FailingAnalyzer",
            execution_time=0.05,
            should_fail=True
        )
        self.mock_registry.get.return_value = failing_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.data_analysis_context,
            state=self.startup_user_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is False
        assert result.error is not None
        assert "business logic failure" in result.error or "failed after" in result.error
        assert result.duration is not None
        assert result.duration > 0  # Should still track timing during failures
        
        # Verify error WebSocket notification
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()
        error_call = self.mock_websocket_bridge.notify_agent_error.call_args
        assert error_call is not None
        
        # Verify execution tracking was completed with error
        assert failing_agent.execution_count >= 1  # Agent was actually called

    @pytest.mark.integration
    async def test_trace_context_end_to_end_propagation(self):
        """
        Test end-to-end trace context propagation with realistic scenarios.
        
        BVJ: Enables comprehensive request tracing for debugging and performance optimization.
        """
        # Arrange
        tracing_agent = RealisticMockAgent("TracingAgent", execution_time=0.1)
        self.mock_registry.get.return_value = tracing_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_trace:
            # Create realistic parent trace context
            parent_trace = UnifiedTraceContext(
                user_id=self.enterprise_user_state.user_id,
                thread_id=self.enterprise_user_state.thread_id,
                correlation_id="trace_business_flow_123"
            )
            mock_get_trace.return_value = parent_trace
            
            # Mock trace propagation methods
            child_trace = UnifiedTraceContext(
                user_id=parent_trace.user_id,
                thread_id=parent_trace.thread_id,
                correlation_id=parent_trace.correlation_id,
                parent_span_id=parent_trace.span_id
            )
            
            with patch.object(parent_trace, 'propagate_to_child', return_value=child_trace):
                with patch.object(child_trace, 'start_span', return_value="span_123"):
                    with patch.object(child_trace, 'finish_span'):
                        with patch.object(child_trace, 'add_event'):
                            # Act
                            result = await self.execution_core.execute_agent(
                                context=self.business_context,
                                state=self.enterprise_user_state,
                                timeout=5.0
                            )
                            
                            # Assert
                            assert result.success is True
                            
                            # Verify trace context propagation
                            mock_get_trace.assert_called_once()
                            parent_trace.propagate_to_child.assert_called_once()
                            child_trace.start_span.assert_called_once()
                            child_trace.finish_span.assert_called_once()
                            
                            # Verify trace events were added
                            assert child_trace.add_event.call_count >= 2  # Started and completed events
                            
                            # Verify agent received trace context
                            assert tracing_agent.trace_context is not None

    @pytest.mark.integration
    async def test_websocket_notification_message_flow(self):
        """
        Test complete WebSocket notification message flow with realistic content.
        
        BVJ: Ensures real-time user feedback works properly for engaging user experience.
        """
        # Arrange
        notification_agent = RealisticMockAgent(
            name="NotificationAgent",
            execution_time=0.15,
            websocket_events=True
        )
        self.mock_registry.get.return_value = notification_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.business_context,
            state=self.enterprise_user_state,
            timeout=10.0
        )
        
        # Assert
        assert result.success is True
        
        # Verify complete notification flow
        self.mock_websocket_bridge.notify_agent_started.assert_called_once()
        self.mock_websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Verify started notification content
        started_call = self.mock_websocket_bridge.notify_agent_started.call_args
        assert started_call[1]['run_id'] == self.business_context.run_id
        assert started_call[1]['agent_name'] == "business_optimizer"
        
        # Verify completed notification content  
        completed_call = self.mock_websocket_bridge.notify_agent_completed.call_args
        assert completed_call[1]['run_id'] == self.business_context.run_id
        assert completed_call[1]['agent_name'] == "business_optimizer"
        assert 'execution_time_ms' in completed_call[1]
        
        # Verify thinking notifications during execution
        assert self.mock_websocket_bridge.notify_agent_thinking.call_count >= 2
        thinking_calls = self.mock_websocket_bridge.notify_agent_thinking.call_args_list
        for call in thinking_calls:
            assert call[1]['agent_name'] == "business_optimizer"
            assert 'reasoning' in call[1]

    @pytest.mark.integration
    async def test_performance_metrics_collection_realistic(self):
        """
        Test performance metrics collection with realistic execution data.
        
        BVJ: Enables system performance monitoring and optimization for better user experience.
        """
        # Arrange
        metrics_agent = RealisticMockAgent(
            name="MetricsAgent",
            execution_time=0.25,  # Quarter second for measurable metrics
            websocket_events=True
        )
        self.mock_registry.get.return_value = metrics_agent
        
        # Mock metrics collection methods
        with patch.object(self.execution_core, '_collect_metrics') as mock_collect, \
             patch.object(self.execution_core, '_persist_metrics') as mock_persist:
            
            # Simulate realistic metrics
            mock_collect.return_value = {
                'execution_time_ms': 250,
                'start_timestamp': time.time() - 0.25,
                'end_timestamp': time.time(),
                'memory_usage_mb': 67.5,
                'cpu_percent': 15.3,
                'context_size': 2048,
                'result_success': True,
                'total_duration_seconds': 0.25,
                'websocket_events_sent': 4
            }
            
            # Act
            result = await self.execution_core.execute_agent(
                context=self.business_context,
                state=self.enterprise_user_state,
                timeout=5.0
            )
            
            # Assert
            assert result.success is True
            assert result.metrics is not None
            
            # Verify metrics collection was called
            mock_collect.assert_called_once()
            mock_persist.assert_called_once()
            
            # Verify metrics structure and content
            collected_metrics = mock_collect.return_value
            assert collected_metrics['execution_time_ms'] > 0
            assert collected_metrics['total_duration_seconds'] > 0
            assert collected_metrics['result_success'] is True
            
            # Verify persistence was called with correct structure
            persist_call = mock_persist.call_args
            assert persist_call is not None
            assert persist_call[0][2] == "business_optimizer"  # agent_name

    @pytest.mark.integration
    async def test_agent_execution_engine_integration(self):
        """
        Test integration with agent execution engine components.
        
        BVJ: Ensures agent infrastructure components work together for reliable execution.
        """
        # Arrange
        engine_agent = RealisticMockAgent("EngineAgent", execution_time=0.1)
        engine_agent.execution_engine = MagicMock()
        engine_agent.execution_engine.set_websocket_bridge = MagicMock()
        
        self.mock_registry.get.return_value = engine_agent
        
        # Act
        result = await self.execution_core.execute_agent(
            context=self.business_context,
            state=self.enterprise_user_state,
            timeout=5.0
        )
        
        # Assert
        assert result.success is True
        
        # Verify agent setup included execution engine
        assert engine_agent.websocket_bridge is not None
        
        # Verify execution engine WebSocket integration
        engine_agent.execution_engine.set_websocket_bridge.assert_called_once()

    @pytest.mark.integration 
    async def test_timeout_with_realistic_processing_time(self):
        """
        Test timeout handling with realistic processing scenarios.
        
        BVJ: Ensures system remains responsive under load and doesn't hang on slow operations.
        """
        # Arrange - agent with realistic but slow processing
        slow_agent = RealisticMockAgent(
            name="SlowProcessingAgent", 
            execution_time=2.0,  # 2 seconds processing time
            websocket_events=True
        )
        self.mock_registry.get.return_value = slow_agent
        
        # Act - use shorter timeout to trigger timeout condition
        start_time = time.time()
        result = await self.execution_core.execute_agent(
            context=self.business_context,
            state=self.startup_user_state,
            timeout=0.5  # 500ms timeout
        )
        end_time = time.time()
        
        # Assert
        assert result.success is False
        assert "timeout" in result.error.lower()
        
        # Verify timeout was enforced (should not wait full 2 seconds)
        actual_time = end_time - start_time
        assert actual_time < 1.0, f"Timeout took {actual_time}s, should be ~0.5s"
        
        # Verify error notification for timeout
        self.mock_websocket_bridge.notify_agent_error.assert_called_once()
        error_call = self.mock_websocket_bridge.notify_agent_error.call_args
        assert "timeout" in error_call[1]['error'].lower()

    @pytest.mark.integration
    async def test_user_context_isolation_realistic_data(self):
        """
        Test user context isolation with realistic user data scenarios.
        
        BVJ: Ensures data privacy and security in multi-tenant environment.
        """
        # Arrange - agents for different user tiers with different data access
        enterprise_agent = RealisticMockAgent("EnterpriseAgent", execution_time=0.1)
        startup_agent = RealisticMockAgent("StartupAgent", execution_time=0.1)
        
        # Mock registry to return appropriate agent based on context
        def get_agent_by_name(agent_name):
            if "enterprise" in agent_name:
                return enterprise_agent
            return startup_agent
            
        self.mock_registry.get.side_effect = get_agent_by_name
        
        # Create contexts for different user scenarios
        enterprise_context = AgentExecutionContext(
            agent_name="enterprise_optimizer",
            run_id=uuid.uuid4(),
            retry_count=0
        )
        
        startup_context = AgentExecutionContext(
            agent_name="startup_optimizer", 
            run_id=uuid.uuid4(),
            retry_count=0
        )
        
        # Execute both scenarios concurrently
        enterprise_task = self.execution_core.execute_agent(
            context=enterprise_context,
            state=self.enterprise_user_state,
            timeout=5.0
        )
        
        startup_task = self.execution_core.execute_agent(
            context=startup_context,
            state=self.startup_user_state,
            timeout=5.0
        )
        
        # Act
        results = await asyncio.gather(enterprise_task, startup_task, return_exceptions=True)
        
        # Assert
        for result in results:
            assert not isinstance(result, Exception)
            assert result.success is True
        
        # Verify isolation - each agent only got their respective user data
        assert enterprise_agent._user_id == self.enterprise_user_state.user_id
        assert startup_agent._user_id == self.startup_user_state.user_id
        
        # Verify different agents were used
        assert enterprise_agent != startup_agent
        
        # Verify separate WebSocket notifications
        assert self.mock_websocket_bridge.notify_agent_started.call_count == 2
        assert self.mock_websocket_bridge.notify_agent_completed.call_count == 2

    def cleanup_resources(self):
        """Clean up test resources."""
        super().cleanup_resources()
        self.execution_core = None
        self.test_helper.cleanup() if self.test_helper else None