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
        with patch.object(self.core.execution_tracker, 'register_execution') as mock_register:
            mock_register.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            
            # Test default timeout is applied
            result = asyncio.run(self.core.execute_agent(context, user_context, timeout=1.0))
            
            # Verify timeout is registered with tracker
            mock_register.assert_called_once()
            call_args = mock_register.call_args[1]
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
        
        # Mock registry to return None (agent not found)
        self.mock_registry.get.return_value = None
        
        with patch.object(self.core.execution_tracker, 'register_execution') as mock_register:
            mock_register.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            
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
        
        with patch.object(self.core.execution_tracker, 'register_execution') as mock_register:
            mock_register.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            
            result = asyncio.run(self.core.execute_agent(context, user_context))
            
            # Verify WebSocket notifications were sent
            self.mock_websocket_bridge.notify_agent_started.assert_called_once()
            self.mock_websocket_bridge.notify_agent_completed.assert_called_once()

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
        
        with patch.object(self.core.execution_tracker, 'register_execution') as mock_register:
            mock_register.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            
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
            
            with patch.object(self.core.execution_tracker, 'register_execution') as mock_register:
                mock_register.return_value = UUID('12345678-1234-5678-9abc-123456789012')
                
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
        
        with patch.object(self.core.execution_tracker, 'register_execution') as mock_register:
            mock_register.return_value = UUID('12345678-1234-5678-9abc-123456789012')
            
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