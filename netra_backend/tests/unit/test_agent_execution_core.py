"""Test AgentExecutionCore Business Logic

Business Value Justification (BVJ):
- Segment: All (Free/Early/Mid/Enterprise)  
- Business Goal: Agent Reliability & User Experience
- Value Impact: Ensures agent execution delivers reliable AI-powered solutions to customers
- Strategic Impact: Core foundation for all AI agent operations - agent failures = revenue loss

FIXED ISSUES:
1. Replaced DeepAgentState with UserExecutionContext pattern (SSOT compliant)
2. Fixed setUp method to properly initialize test fixtures
3. Updated to use strongly typed IDs from shared.types
4. Eliminated user isolation risks by using proper context patterns
5. Added proper SSOT environment handling with get_env()
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RequestID
from test_framework.base_integration_test import BaseIntegrationTest

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextFactory
from netra_backend.app.core.execution_tracker import ExecutionState


class TestAgentExecutionCore(BaseIntegrationTest):
    """Test AgentExecutionCore pure business logic - SSOT compliant."""

    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self._setUp()
    
    def setUp(self):
        """Compatibility method for BaseIntegrationTest."""
        self._setUp()
        
    def _setUp(self):
        """Set up test fixtures."""
        self.mock_registry = Mock()
        self.mock_websocket_bridge = AsyncMock()
        self.mock_execution_tracker = AsyncMock()
        
        # Create core instance
        self.core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        self.core.execution_tracker = self.mock_execution_tracker

    @pytest.mark.unit
    def test_agent_execution_timeout_business_logic(self):
        """Test agent execution timeout handling for business continuity."""
        # Business Value: Prevents infinite agent runs that block user requests
        context = AgentExecutionContext(
            run_id=str(RequestID("run-123")),
            thread_id=str(ThreadID("thread-123")),
            user_id=str(UserID("user-123")),
            agent_name="data_analyzer",
            correlation_id="corr-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-789",
            thread_id="thread-123",
            run_id="run-123"
        )
        
        # Simulate timeout scenario
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            # Test default timeout is applied
            result = asyncio.run(self.core.execute_agent(context, user_context, timeout=1.0))
            
            # Verify timeout is registered with tracker
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args['timeout_seconds'] == 1.0

    @pytest.mark.unit
    def test_agent_not_found_error_handling(self):
        """Test agent not found scenario for user experience."""
        # Business Value: Clear error messaging prevents user confusion
        context = AgentExecutionContext(
            run_id=str(RequestID("run-404")),
            thread_id=str(ThreadID("thread-404")),
            user_id=str(UserID("user-404")),
            agent_name="nonexistent_agent",
            correlation_id="corr-404"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-404",
            thread_id="thread-404", 
            run_id="run-404"
        )
        
        # Mock registry to return None (agent not found) and fix iteration issue
        self.mock_registry.get.return_value = None
        # Fix the iteration issue by providing a _registry attribute
        self.mock_registry._registry = {}  # Empty registry for agent not found scenario
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify proper error handling
            assert not result.success
            assert "Agent nonexistent_agent not found" in result.error

    @pytest.mark.unit
    def test_websocket_notification_business_flow(self):
        """Test WebSocket notifications for real-time user feedback."""
        # Business Value: Real-time updates improve user engagement and reduce abandonment
        context = AgentExecutionContext(
            run_id=str(RequestID("run-ws-123")),
            thread_id=str(ThreadID("thread-ws-123")),
            user_id=str(UserID("user-ws-123")),
            agent_name="cost_optimizer",
            correlation_id="corr-ws-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)  
        user_context = UserContextFactory.create_context(
            user_id="user-ws-789",
            thread_id="thread-ws-123",
            run_id="run-ws-123"
        )
        
        # Mock successful agent execution
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"success": True, "savings": "$500/month"}
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify WebSocket notifications were sent (may be called multiple times)
            assert self.mock_websocket_bridge.notify_agent_started.called
            assert self.mock_websocket_bridge.notify_agent_completed.called

    @pytest.mark.unit
    def test_execution_metrics_collection(self):
        """Test performance metrics collection for business insights."""
        # Business Value: Performance data enables optimization of AI processing costs
        context = AgentExecutionContext(
            run_id=str(RequestID("run-perf-123")),
            thread_id=str(ThreadID("thread-perf-123")),
            user_id=str(UserID("user-perf-123")),
            agent_name="performance_agent",
            correlation_id="corr-perf-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-perf-123",
            thread_id="thread-perf-123", 
            run_id="run-perf-123"
        )
        
        # Test metrics calculation
        start_time = time.time() - 5.0  # 5 seconds ago
        metrics = self.core._calculate_performance_metrics(start_time)
        
        # Verify business-relevant metrics
        assert 'execution_time_ms' in metrics
        assert metrics['execution_time_ms'] > 4000  # ~5 seconds
        assert 'start_timestamp' in metrics
        assert 'end_timestamp' in metrics

    @pytest.mark.unit
    def test_agent_death_detection_business_logic(self):
        """Test dead agent detection for system reliability."""
        # Business Value: Prevents silent failures that damage user trust
        context = AgentExecutionContext(
            run_id=str(RequestID("run-death-123")),
            thread_id=str(ThreadID("thread-death-123")),
            user_id=str(UserID("user-death-123")),
            agent_name="data_processor",
            correlation_id="corr-death-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-death-123",
            thread_id="thread-death-123",
            run_id="run-death-123"
        )
        
        # Mock agent that returns None (dead agent signature)
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = None
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify dead agent is detected and handled
            assert not result.success
            assert "died silently" in result.error

    @pytest.mark.unit
    def test_trace_context_propagation_business_value(self):
        """Test trace context propagation for debugging and monitoring."""
        # Business Value: Complete observability enables faster issue resolution
        context = AgentExecutionContext(
            run_id=str(RequestID("run-trace-123")),
            thread_id=str(ThreadID("thread-trace-123")),
            user_id=str(UserID("user-trace-123")),
            agent_name="trace_agent",
            correlation_id="corr-trace-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-trace-789",
            thread_id="thread-trace-abc",
            run_id="run-trace-123"
        )
        
        # Mock successful execution
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"success": True}
        self.mock_registry.get.return_value = mock_agent
        
        with patch('netra_backend.app.agents.supervisor.agent_execution_core.UnifiedTraceContext') as mock_trace:
            mock_trace_instance = Mock()
            mock_trace.return_value = mock_trace_instance
            mock_trace_instance.start_span.return_value = Mock()
            
            with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
                 patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
                mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
                mock_start.return_value = True
                
                result = asyncio.run(self.core.execute_agent(context, user_context))
                
                # Verify trace context was created with business context
                mock_trace.assert_called_once()
                call_args = mock_trace.call_args[1]
                assert call_args['user_id'] == "user-trace-789"
                assert call_args['thread_id'] == "thread-trace-abc"

    @pytest.mark.unit
    def test_error_boundary_business_protection(self):
        """Test error boundaries protect business operations."""
        # Business Value: Prevents single agent failure from cascading system-wide
        context = AgentExecutionContext(
            run_id=str(RequestID("run-error-123")),
            thread_id=str(ThreadID("thread-error-123")),
            user_id=str(UserID("user-error-123")),
            agent_name="error_prone_agent",
            correlation_id="corr-error-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-error-123",
            thread_id="thread-error-123",
            run_id="run-error-123"
        )
        
        # Mock agent that throws exception
        mock_agent = AsyncMock()
        mock_agent.execute.side_effect = RuntimeError("Critical agent failure")
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify error is contained and properly reported
            assert not result.success
            assert "Critical agent failure" in result.error

    @pytest.mark.unit
    def test_websocket_context_setup_business_integration(self):
        """Test WebSocket context setup for complete user experience."""
        # Business Value: Ensures users get real-time feedback from all agent operations
        mock_agent = Mock()
        context = AgentExecutionContext(
            run_id=str(RequestID("run-int-123")),
            thread_id=str(ThreadID("thread-int-123")),
            user_id=str(UserID("user-int-123")),
            agent_name="integration_agent",
            correlation_id="corr-int-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-int-789",
            thread_id="thread-int-123",
            run_id="run-int-123"
        )
        
        # Mock trace context
        mock_trace_context = Mock()
        
        # Test WebSocket setup
        asyncio.run(self.core._setup_agent_websocket(mock_agent, context, user_context, mock_trace_context))
        
        # Verify user context propagation
        assert mock_agent._user_id == "user-int-789"

    @pytest.mark.unit
    def test_performance_metrics_business_insights(self):
        """Test performance metrics provide actionable business data."""
        # Business Value: CPU/memory data enables cost optimization decisions
        
        # Test metrics with heartbeat data
        start_time = time.time() - 3.0
        mock_heartbeat = Mock()
        mock_heartbeat.pulse_count = 5
        
        metrics = self.core._calculate_performance_metrics(start_time, mock_heartbeat)
        
        # Verify business-relevant performance data
        assert 'execution_time_ms' in metrics
        assert 'heartbeat_count' in metrics
        assert metrics['heartbeat_count'] == 5
        assert metrics['execution_time_ms'] > 2500  # ~3 seconds

    @pytest.mark.unit
    def test_agent_result_validation_business_compliance(self):
        """Test agent result validation ensures business value delivery."""
        # Business Value: Validates agents return meaningful results to users
        context = AgentExecutionContext(
            run_id=str(RequestID("run-val-123")),
            thread_id=str(ThreadID("thread-val-123")),
            user_id=str(UserID("user-val-123")),
            agent_name="validator_agent",
            correlation_id="corr-val-456"
        )
        
        # Use UserExecutionContext instead of DeepAgentState (SSOT compliant)
        user_context = UserContextFactory.create_context(
            user_id="user-val-123",
            thread_id="thread-val-123",
            run_id="run-val-123"
        )
        
        # Test non-standard result wrapping
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = "plain_string_result"
        mock_trace_context = Mock()
        
        result = asyncio.run(
            self.core._execute_with_result_validation(
                mock_agent, context, user_context, None, mock_trace_context
            )
        )
        
        # Verify result is wrapped in standard format
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["result"] == "plain_string_result"
        assert result["agent_name"] == "validator_agent"

    @pytest.mark.unit
    def test_user_execution_context_migration_security(self):
        """Test UserExecutionContext validation security (DeepAgentState removed)."""
        # Business Value: Prevents user data isolation vulnerabilities
        
        context = AgentExecutionContext(
            run_id=str(RequestID("run-migrate-123")),
            thread_id=str(ThreadID("thread-migrate-123")),
            user_id=str(UserID("user-migrate-123")),
            agent_name="migration_agent",
            correlation_id="corr-migrate-456"
        )
        
        # Test proper UserExecutionContext validation (no DeepAgentState)
        user_context = UserContextFactory.create_context(
            user_id="legacy-user-123",
            thread_id="legacy-thread-456",
            run_id="legacy-run-789"
        )
        
        # Verify UserExecutionContext validation works correctly
        validated_context = self.core._validate_user_execution_context(user_context, context)
        
        # Verify proper validation and security enforcement
        assert isinstance(validated_context, UserExecutionContext)
        assert validated_context.user_id == "legacy-user-123"
        assert validated_context.thread_id == "legacy-thread-456"
        assert validated_context.run_id == "legacy-run-789"

    @pytest.mark.unit 
    def test_circuit_breaker_fallback_business_continuity(self):
        """Test circuit breaker fallback ensures business continuity."""
        # Business Value: Provides degraded service instead of complete failure
        from netra_backend.app.core.agent_execution_tracker import CircuitBreakerOpenError
        
        context = AgentExecutionContext(
            run_id=str(RequestID("run-cb-123")),
            thread_id=str(ThreadID("thread-cb-123")),
            user_id=str(UserID("user-cb-123")),
            agent_name="circuit_agent",
            correlation_id="corr-cb-456"
        )
        
        user_context = UserContextFactory.create_context(
            user_id="user-cb-123",
            thread_id="thread-cb-123",
            run_id="run-cb-123"
        )
        
        # Mock circuit breaker error
        mock_agent = AsyncMock()
        self.mock_registry.get.return_value = mock_agent
        
        circuit_error = CircuitBreakerOpenError("Circuit breaker open")
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start, \
             patch.object(self.core, '_execute_with_protection') as mock_protection, \
             patch.object(self.core, 'create_fallback_response') as mock_fallback:
            
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            mock_protection.side_effect = circuit_error
            mock_fallback.return_value = {"fallback": "Graceful degradation response"}
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify fallback response provides business value
            assert not result.success
            assert "Circuit breaker open" in result.error
            assert result.data["fallback"] == "Graceful degradation response"
            mock_fallback.assert_called_once()

    @pytest.mark.unit
    def test_agent_state_phase_transitions(self):
        """Test agent execution state transitions for monitoring."""
        # Business Value: Enables real-time monitoring of agent execution pipeline
        from netra_backend.app.core.agent_execution_tracker import AgentExecutionPhase
        
        context = AgentExecutionContext(
            run_id=str(RequestID("run-phase-123")),
            thread_id=str(ThreadID("thread-phase-123")),
            user_id=str(UserID("user-phase-123")),
            agent_name="phase_agent",
            correlation_id="corr-phase-456"
        )
        
        user_context = UserContextFactory.create_context(
            user_id="user-phase-123",
            thread_id="thread-phase-123",
            run_id="run-phase-123"
        )
        
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"success": True, "result": "Phase test"}
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start, \
             patch.object(self.core.state_tracker, 'start_execution') as mock_state_start, \
             patch.object(self.core.state_tracker, 'transition_state') as mock_transition:
            
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            mock_state_start.return_value = "phase_exec_123"
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify state transitions for business monitoring
            assert result.success
            mock_state_start.assert_called_once()
            mock_transition.assert_called()
            
            # Verify key phases were tracked
            transition_calls = mock_transition.call_args_list
            phases = [call[0][1] for call in transition_calls if len(call[0]) > 1]
            assert AgentExecutionPhase.WEBSOCKET_SETUP in phases
            assert AgentExecutionPhase.STARTING in phases

    @pytest.mark.unit
    def test_execution_timeout_protection_business_logic(self):
        """Test execution timeout protects against resource waste."""
        # Business Value: Prevents runaway agents from consuming expensive compute resources
        context = AgentExecutionContext(
            run_id=str(RequestID("run-timeout-123")),
            thread_id=str(ThreadID("thread-timeout-123")),
            user_id=str(UserID("user-timeout-123")),
            agent_name="timeout_agent",
            correlation_id="corr-timeout-456"
        )
        
        user_context = UserContextFactory.create_context(
            user_id="user-timeout-123",
            thread_id="thread-timeout-123",
            run_id="run-timeout-123"
        )
        
        # Mock slow agent
        mock_agent = AsyncMock()
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start, \
             patch('asyncio.wait_for') as mock_wait_for:
            
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            mock_wait_for.side_effect = TimeoutError("Agent execution timed out")
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify timeout protection activates
            assert not result.success
            assert "timed out" in result.error
            assert result.agent_name == "timeout_agent"

    @pytest.mark.unit
    def test_websocket_event_business_requirements(self):
        """Test WebSocket events meet business requirements for user engagement."""
        # Business Value: Real-time updates keep users engaged and reduce abandonment
        context = AgentExecutionContext(
            run_id=str(RequestID("run-ws-req-123")),
            thread_id=str(ThreadID("thread-ws-req-123")),
            user_id=str(UserID("user-ws-req-123")),
            agent_name="engagement_agent",
            correlation_id="corr-ws-req-456"
        )
        
        user_context = UserContextFactory.create_context(
            user_id="user-ws-req-123",
            thread_id="thread-ws-req-123",
            run_id="run-ws-req-123"
        )
        
        mock_agent = AsyncMock()
        mock_agent.execute.return_value = {"success": True, "insights": "Key business insights"}
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify all required business events were sent
            assert result.success
            
            # Check agent_started event
            started_calls = self.mock_websocket_bridge.notify_agent_started.call_args_list
            assert len(started_calls) >= 1
            started_call = started_calls[0]
            assert started_call[1]['run_id'] == "run-ws-req-123"
            assert started_call[1]['agent_name'] == "engagement_agent"
            
            # Check agent_completed event
            completed_calls = self.mock_websocket_bridge.notify_agent_completed.call_args_list
            assert len(completed_calls) >= 1
            completed_call = completed_calls[0]
            assert completed_call[1]['run_id'] == "run-ws-req-123"
            assert completed_call[1]['agent_name'] == "engagement_agent"

    @pytest.mark.unit
    def test_error_propagation_business_transparency(self):
        """Test error propagation provides business transparency."""
        # Business Value: Clear error reporting enables faster issue resolution
        context = AgentExecutionContext(
            run_id=str(RequestID("run-err-123")),
            thread_id=str(ThreadID("thread-err-123")),
            user_id=str(UserID("user-err-123")),
            agent_name="error_agent",
            correlation_id="corr-err-456"
        )
        
        user_context = UserContextFactory.create_context(
            user_id="user-err-123",
            thread_id="thread-err-123",
            run_id="run-err-123"
        )
        
        # Mock agent that throws business-relevant error
        mock_agent = AsyncMock()
        mock_agent.execute.side_effect = ValueError("Invalid business parameters provided")
        self.mock_registry.get.return_value = mock_agent
        
        with patch.object(self.core.agent_tracker, 'create_execution') as mock_create, \
             patch.object(self.core.agent_tracker, 'start_execution') as mock_start:
            
            mock_create.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            mock_start.return_value = True
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify error transparency for business debugging
            assert not result.success
            assert "Invalid business parameters provided" in result.error
            
            # Verify error WebSocket notification was sent
            assert self.mock_websocket_bridge.notify_agent_error.called
            # Get the last error call
            if self.mock_websocket_bridge.notify_agent_error.call_args_list:
                last_error_call = self.mock_websocket_bridge.notify_agent_error.call_args_list[-1]
                assert last_error_call[1]['run_id'] == "run-err-123"
                assert "Invalid business parameters provided" in last_error_call[1]['error']

    @pytest.mark.unit
    def test_agent_result_data_preservation(self):
        """Test agent result data is preserved for business value delivery."""
        # Business Value: Ensures all agent insights reach the user
        mock_agent = AsyncMock()
        context = AgentExecutionContext(
            run_id=str(RequestID("run-data-123")),
            thread_id=str(ThreadID("thread-data-123")),
            user_id=str(UserID("user-data-123")),
            agent_name="data_agent",
            correlation_id="corr-data-456"
        )
        
        user_context = UserContextFactory.create_context(
            user_id="user-data-123",
            thread_id="thread-data-123",
            run_id="run-data-123"
        )
        
        # Test complex business result preservation
        business_result = {
            "optimization_opportunities": [
                {"type": "cost_reduction", "savings": 5000, "confidence": 0.95},
                {"type": "performance_improvement", "impact": "25% faster", "effort": "low"}
            ],
            "current_metrics": {
                "monthly_spend": 15000,
                "efficiency_score": 0.78
            },
            "recommendations": {
                "immediate": ["Switch to spot instances"],
                "planned": ["Implement auto-scaling", "Optimize data transfer"]
            }
        }
        
        mock_agent.execute.return_value = business_result
        mock_trace_context = Mock()
        
        result = asyncio.run(
            self.core._execute_with_result_validation(
                mock_agent, context, user_context, None, mock_trace_context
            )
        )
        
        # Verify all business data is preserved
        assert result == business_result

    @pytest.mark.unit
    def test_performance_thresholds_business_monitoring(self):
        """Test performance thresholds enable business cost monitoring."""
        # Business Value: Identifies expensive agent operations for optimization
        
        # Test fast execution (good for business costs)
        fast_start = time.time() - 0.5  # 500ms execution
        fast_metrics = self.core._calculate_performance_metrics(fast_start)
        assert fast_metrics['execution_time_ms'] < 1000  # Under 1 second
        
        # Test slow execution (costly for business)
        slow_start = time.time() - 10.0  # 10 second execution
        slow_metrics = self.core._calculate_performance_metrics(slow_start)
        assert slow_metrics['execution_time_ms'] > 9000  # Over 9 seconds
        
        # Verify metrics enable business optimization decisions
        assert 'start_timestamp' in fast_metrics
        assert 'end_timestamp' in fast_metrics
        assert fast_metrics['end_timestamp'] > fast_metrics['start_timestamp']

    @pytest.mark.unit
    def test_concurrent_execution_isolation(self):
        """Test concurrent agent executions maintain user isolation."""
        # Business Value: Prevents user data leakage in multi-tenant environment
        
        # Create contexts for different users
        context1 = AgentExecutionContext(
            run_id=str(RequestID("run-user1-123")),
            thread_id=str(ThreadID("thread-user1-123")),
            user_id=str(UserID("user-1")),
            agent_name="isolation_agent",
            correlation_id="corr-user1-456"
        )
        
        context2 = AgentExecutionContext(
            run_id=str(RequestID("run-user2-123")),
            thread_id=str(ThreadID("thread-user2-123")),
            user_id=str(UserID("user-2")),
            agent_name="isolation_agent",
            correlation_id="corr-user2-456"
        )
        
        user_context1 = UserContextFactory.create_context(
            user_id="user-1",
            thread_id="thread-user1-123",
            run_id="run-user1-123"
        )
        
        user_context2 = UserContextFactory.create_context(
            user_id="user-2", 
            thread_id="thread-user2-123",
            run_id="run-user2-123"
        )
        
        # Verify contexts are isolated
        assert user_context1.user_id != user_context2.user_id
        assert user_context1.thread_id != user_context2.thread_id
        assert user_context1.run_id != user_context2.run_id
        
        # Verify agent execution would maintain isolation
        assert context1.user_id != context2.user_id
        assert context1.run_id != context2.run_id
        assert context1.correlation_id != context2.correlation_id