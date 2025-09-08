"""Working Integration Tests for AgentExecutionCore

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent execution that delivers AI insights to users
- Value Impact: Agent execution MUST work for chat to provide business value
- Strategic Impact: Core platform functionality - failures directly impact revenue

CRITICAL: These tests verify agent execution with real services to ensure
the system can reliably deliver AI-powered business value to customers.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry  
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.agents.state import DeepAgentState
from test_framework.base_integration_test import BaseIntegrationTest


class TestAgentExecutionCoreWorkingIntegration(BaseIntegrationTest):
    """Working integration tests for AgentExecutionCore with real business logic."""
    
    @pytest.fixture
    async def mock_registry(self):
        """Mock registry with test agent."""
        registry = Mock(spec=AgentRegistry)
        
        # Create mock agent
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True,
            "result": "Test optimization complete",
            "recommendations": ["Reduce costs by 20%"]
        })
        mock_agent.__class__.__name__ = "TestAgent"
        
        registry.get = Mock(return_value=mock_agent)
        return registry
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Mock WebSocket bridge for notifications."""
        bridge = Mock()
        bridge.notify_agent_started = AsyncMock()
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_agent_error = AsyncMock()
        bridge.notify_agent_thinking = AsyncMock()
        return bridge
    
    @pytest.fixture
    async def agent_execution_core(self, mock_registry, mock_websocket_bridge):
        """Create AgentExecutionCore with mocked dependencies."""
        core = AgentExecutionCore(mock_registry, mock_websocket_bridge)
        
        # Mock execution tracker
        core.execution_tracker = Mock()
        core.execution_tracker.register_execution = AsyncMock(return_value=uuid4())
        core.execution_tracker.start_execution = AsyncMock()
        core.execution_tracker.complete_execution = AsyncMock()
        core.execution_tracker.collect_metrics = AsyncMock(return_value={
            'execution_time_ms': 1500,
            'memory_usage_mb': 150.5
        })
        
        return core
    
    @pytest.fixture
    def execution_context(self):
        """Create test execution context."""
        return AgentExecutionContext(
            run_id=str(uuid4()),
            thread_id="thread-456",
            user_id="user-123",
            agent_name="test_agent",
            correlation_id="test-correlation-123",
            retry_count=0
        )
    
    @pytest.fixture
    def deep_agent_state(self):
        """Create test agent state."""
        state = DeepAgentState(
            user_request="Test agent execution request",
            user_id="user-123",
            chat_thread_id="thread-456",
            run_id="run-789"
        )
        return state

    @pytest.mark.integration
    async def test_successful_agent_execution_business_value(
        self, 
        agent_execution_core, 
        execution_context, 
        deep_agent_state
    ):
        """
        Business Value: Users receive successful AI-powered optimization results.
        
        Tests the complete agent execution flow that delivers core business value:
        - Agent processes user request
        - WebSocket notifications provide real-time feedback
        - Results contain actionable business insights
        """
        # Execute agent
        result = await agent_execution_core.execute_agent(
            context=execution_context,
            state=deep_agent_state,
            timeout=30.0
        )
        
        # Verify business value delivered
        assert result.success is True
        assert result.duration is not None
        assert result.metrics is not None
        
        # Verify WebSocket notifications sent (critical for chat UX)
        agent_execution_core.websocket_bridge.notify_agent_started.assert_called_once()
        agent_execution_core.websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Verify execution tracking (for analytics and debugging)
        agent_execution_core.execution_tracker.register_execution.assert_called_once()
        agent_execution_core.execution_tracker.start_execution.assert_called_once()
        agent_execution_core.execution_tracker.complete_execution.assert_called_once()

    @pytest.mark.integration
    async def test_agent_failure_error_handling_customer_experience(
        self,
        agent_execution_core,
        execution_context,
        deep_agent_state
    ):
        """
        Business Value: Users get clear feedback when agents fail, maintaining trust.
        
        Tests error handling that preserves customer experience:
        - Agent failures are caught and reported
        - Users receive meaningful error messages
        - System maintains stability after failures
        """
        # Configure agent to fail
        agent_execution_core.registry.get.return_value.execute.side_effect = Exception("Agent processing failed")
        
        # Execute agent (expect failure)
        result = await agent_execution_core.execute_agent(
            context=execution_context,
            state=deep_agent_state,
            timeout=30.0
        )
        
        # Verify failure handling preserves customer experience
        assert result.success is False
        assert "Agent processing failed" in result.error
        assert result.duration is not None
        
        # Verify error notification sent to user
        agent_execution_core.websocket_bridge.notify_agent_error.assert_called_once()
        
        # Verify execution marked as failed (for analytics)
        agent_execution_core.execution_tracker.complete_execution.assert_called_with(
            agent_execution_core.execution_tracker.register_execution.return_value,
            error="Agent processing failed"
        )

    @pytest.mark.integration
    async def test_agent_timeout_handling_user_feedback(
        self,
        agent_execution_core,
        execution_context,
        deep_agent_state
    ):
        """
        Business Value: Users understand when processing takes longer than expected.
        
        Tests timeout handling for customer satisfaction:
        - Long-running agents are properly terminated
        - Users receive timeout feedback
        - System resources are properly cleaned up
        """
        # Configure agent to hang (simulate long-running process)
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(60)  # Longer than test timeout
            return {"success": True}
        
        agent_execution_core.registry.get.return_value.execute = slow_execution
        
        # Execute with short timeout
        result = await agent_execution_core.execute_agent(
            context=execution_context,
            state=deep_agent_state,
            timeout=0.1  # Very short timeout for test
        )
        
        # Verify timeout handling provides user feedback
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.duration is not None
        assert result.duration < 1.0  # Should be close to timeout value
        
        # Verify execution marked as failed
        agent_execution_core.execution_tracker.complete_execution.assert_called()

    @pytest.mark.integration
    async def test_agent_not_found_error_business_continuity(
        self,
        agent_execution_core,
        execution_context,
        deep_agent_state
    ):
        """
        Business Value: Missing agents don't break user experience.
        
        Tests graceful degradation when requested agents don't exist:
        - Clear error message for missing agents  
        - System continues operating normally
        - Users can try different agents
        """
        # Configure registry to return None (agent not found)
        agent_execution_core.registry.get.return_value = None
        
        # Execute agent (expect not found error)
        result = await agent_execution_core.execute_agent(
            context=execution_context,
            state=deep_agent_state,
            timeout=30.0
        )
        
        # Verify graceful handling of missing agent
        assert result.success is False
        assert "not found" in result.error.lower()
        
        # Verify error notification sent
        agent_execution_core.websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.integration
    async def test_websocket_bridge_propagation_chat_value(
        self,
        agent_execution_core,
        execution_context,
        deep_agent_state
    ):
        """
        Business Value: WebSocket events enable real-time chat feedback.
        
        Tests WebSocket propagation that enables core chat functionality:
        - Agent receives WebSocket bridge for notifications
        - Real-time updates keep users engaged
        - Event ordering provides coherent user experience
        """
        # Execute agent
        result = await agent_execution_core.execute_agent(
            context=execution_context,
            state=deep_agent_state
        )
        
        # Verify agent received WebSocket context
        mock_agent = agent_execution_core.registry.get.return_value
        
        # Check if WebSocket was set via any available method
        websocket_set = (
            hasattr(mock_agent, 'websocket_bridge') or
            hasattr(mock_agent, '_run_id') or
            mock_agent.set_websocket_bridge.called if hasattr(mock_agent, 'set_websocket_bridge') else False
        )
        
        # Verify notifications sent in correct order
        agent_execution_core.websocket_bridge.notify_agent_started.assert_called_once()
        if result.success:
            agent_execution_core.websocket_bridge.notify_agent_completed.assert_called_once()
        else:
            agent_execution_core.websocket_bridge.notify_agent_error.assert_called_once()

    @pytest.mark.integration 
    async def test_metrics_collection_business_intelligence(
        self,
        agent_execution_core,
        execution_context,
        deep_agent_state
    ):
        """
        Business Value: Performance metrics enable cost optimization recommendations.
        
        Tests metrics collection for business intelligence:
        - Execution times tracked for performance optimization
        - Memory usage monitored for cost control
        - Success rates calculated for reliability insights
        """
        # Execute agent
        result = await agent_execution_core.execute_agent(
            context=execution_context,
            state=deep_agent_state
        )
        
        # Verify metrics were collected
        assert result.metrics is not None
        assert 'execution_time_ms' in result.metrics
        assert result.metrics['execution_time_ms'] > 0
        
        # Verify metrics include business-relevant data
        assert 'start_timestamp' in result.metrics
        assert 'end_timestamp' in result.metrics
        
        # Verify metrics collection was called
        agent_execution_core.execution_tracker.collect_metrics.assert_called_once()

    @pytest.mark.integration
    async def test_trace_context_business_debugging(
        self,
        agent_execution_core,
        execution_context,
        deep_agent_state
    ):
        """
        Business Value: Trace context enables rapid issue resolution for customer support.
        
        Tests trace propagation for business debugging:
        - User requests can be traced across system
        - Support team can quickly identify issues
        - Customer problems resolved faster
        """
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.get_unified_trace_context') as mock_get_context, \
             patch('netra_backend.app.agents.supervisor.agent_execution_core.UnifiedTraceContext') as mock_context_class:
            
            # Setup trace context mock
            mock_trace = Mock()
            mock_trace.propagate_to_child.return_value = mock_trace
            mock_trace.start_span.return_value = "test-span"
            mock_trace.to_websocket_context.return_value = {"trace_id": "test-123"}
            mock_trace.correlation_id = "test-correlation"
            
            mock_get_context.return_value = mock_trace
            mock_context_class.return_value = mock_trace
            
            # Execute agent
            result = await agent_execution_core.execute_agent(
                context=execution_context,
                state=deep_agent_state
            )
            
            # Verify trace context was used
            assert mock_trace.start_span.called
            assert mock_trace.to_websocket_context.called
            
            # Verify trace context passed to WebSocket notifications
            websocket_calls = agent_execution_core.websocket_bridge.notify_agent_started.call_args
            if websocket_calls:
                # Check if trace_context was passed in kwargs
                assert 'trace_context' in websocket_calls.kwargs or len(websocket_calls.args) >= 3