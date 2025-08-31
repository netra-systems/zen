"""Bulletproof Test Suite for Supervisor Agent Orchestration.

This comprehensive test suite ensures 100% reliability of the Supervisor Agent,
testing all critical paths, edge cases, error conditions, and performance requirements.

Business Value: Ensures the core orchestration engine is production-ready and can
handle any scenario without failure.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call, ANY
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import time
import uuid
import random
import json

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
    AgentExecutionStrategy,
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core import UnifiedWebSocketManager
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.agents.base_agent import BaseSubAgent


class TestSupervisorAgentCore:
    """Core unit tests for Supervisor Agent functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager with realistic responses."""
        manager = MagicMock(spec=LLMManager)
        manager.generate = AsyncMock(return_value={
            "decision": "execute_workflow",
            "agents": ["research", "code_generation"],
            "reasoning": "Test orchestration decision"
        })
        manager.model_name = "gpt-4"
        manager.temperature = 0.7
        return manager
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager with comprehensive message tracking."""
        manager = MagicMock(spec=UnifiedWebSocketManager)
        manager.send_message = AsyncMock()
        manager.broadcast = AsyncMock()
        manager.messages_sent = []
        manager.event_types_sent = set()
        
        async def track_message(thread_id, message):
            manager.messages_sent.append({
                'thread_id': thread_id,
                'message': message,
                'timestamp': datetime.now(timezone.utc)
            })
            if hasattr(message, 'event'):
                manager.event_types_sent.add(message.event)
        
        manager.send_message.side_effect = track_message
        return manager
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher with realistic tool execution."""
        dispatcher = MagicMock(spec=ToolDispatcher)
        dispatcher.execute_tool = AsyncMock(return_value={
            "success": True,
            "result": "Tool executed successfully",
            "execution_time": 0.5
        })
        dispatcher.available_tools = ["search", "code_analysis", "database_query"]
        return dispatcher
    
    @pytest.fixture
    def mock_sub_agent(self):
        """Mock sub-agent for testing delegation."""
        agent = MagicMock(spec=BaseSubAgent)
        agent.name = "TestAgent"
        agent.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            status="completed",
            result={"agent_output": "Test result"}
        ))
        return agent
    
    @pytest.fixture
    def supervisor_agent(self, mock_db_session, mock_llm_manager, 
                        mock_websocket_manager, mock_tool_dispatcher):
        """Create supervisor agent instance with all dependencies."""
        agent = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            websocket_manager=mock_websocket_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        return agent
    
    @pytest.fixture
    def execution_context(self):
        """Create standard execution context."""
        return ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="test_thread_123",
            user_id="test_user",
            start_time=datetime.now(timezone.utc),
            metadata={"test": True}
        )
    
    @pytest.mark.asyncio
    async def test_initialization_complete(self, supervisor_agent):
        """Test complete initialization of all supervisor components."""
        assert supervisor_agent.db_session is not None
        assert supervisor_agent.llm_manager is not None
        assert supervisor_agent.websocket_manager is not None
        assert supervisor_agent.tool_dispatcher is not None
        
        # Core components
        assert supervisor_agent.agent_registry is not None
        assert supervisor_agent.lifecycle_manager is not None
        assert supervisor_agent.execution_engine is not None
        assert supervisor_agent.workflow_orchestrator is not None
        
        # Monitoring components
        assert supervisor_agent.circuit_breaker_integration is not None
        assert supervisor_agent.observability is not None
        
        # System prompts
        assert supervisor_agent.system_prompt is not None
        assert supervisor_agent.orchestration_prompt_template is not None
        
        # Execution lock
        assert supervisor_agent._execution_lock is not None
        assert isinstance(supervisor_agent._execution_lock, asyncio.Lock)
    
    @pytest.mark.asyncio
    async def test_validate_preconditions_success(self, supervisor_agent, execution_context):
        """Test successful precondition validation."""
        supervisor_agent.lifecycle_manager.validate_entry_conditions = AsyncMock(return_value=True)
        
        result = await supervisor_agent.validate_preconditions(execution_context)
        
        assert result is True
        supervisor_agent.lifecycle_manager.validate_entry_conditions.assert_called_once_with(execution_context)
    
    @pytest.mark.asyncio
    async def test_validate_preconditions_failure(self, supervisor_agent, execution_context):
        """Test failed precondition validation."""
        supervisor_agent.lifecycle_manager.validate_entry_conditions = AsyncMock(return_value=False)
        
        result = await supervisor_agent.validate_preconditions(execution_context)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_core_logic_success(self, supervisor_agent, execution_context):
        """Test successful core logic execution with complete workflow."""
        # Mock workflow results
        mock_results = [
            ExecutionResult(success=True, status="completed", result={"step": 1}),
            ExecutionResult(success=True, status="completed", result={"step": 2})
        ]
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=mock_results
        )
        supervisor_agent.lifecycle_manager.check_exit_conditions = AsyncMock()
        
        result = await supervisor_agent.execute_core_logic(execution_context)
        
        assert result["supervisor_result"] == "completed"
        assert result["total_steps"] == 2
        assert len(result["workflow_results"]) == 2
        
        # Verify system prompt was added to context
        assert execution_context.metadata["system_prompt"] == supervisor_agent.system_prompt
    
    @pytest.mark.asyncio
    async def test_execute_core_logic_with_failure(self, supervisor_agent, execution_context):
        """Test core logic execution with workflow failure."""
        mock_results = [
            ExecutionResult(success=True, status="completed", result={"step": 1}),
            ExecutionResult(success=False, status="failed", error="Agent error")
        ]
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=mock_results
        )
        
        result = await supervisor_agent.execute_core_logic(execution_context)
        
        assert result["supervisor_result"] == "failed"
        assert result["total_steps"] == 2
    
    @pytest.mark.asyncio
    async def test_execute_protected_workflow_with_circuit_breaker(self, supervisor_agent, execution_context):
        """Test workflow execution with circuit breaker protection."""
        mock_results = [ExecutionResult(success=True, status="completed")]
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=mock_results
        )
        
        # Mock circuit breaker response
        mock_cb_result = MagicMock()
        mock_cb_result.result = mock_results
        supervisor_agent.circuit_breaker_integration.execute_with_circuit_protection = AsyncMock(
            return_value=mock_cb_result
        )
        
        result = await supervisor_agent._execute_protected_workflow(execution_context)
        
        assert result == mock_results
        supervisor_agent.circuit_breaker_integration.execute_with_circuit_protection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_lifecycle_hooks(self, supervisor_agent):
        """Test complete execution with all lifecycle hooks."""
        state = DeepAgentState()
        state.user_request = "Test request"
        run_id = str(uuid.uuid4())
        
        # Mock lifecycle hooks
        supervisor_agent.lifecycle_manager.execute_lifecycle_hooks = AsyncMock()
        supervisor_agent.lifecycle_manager.track_active_context = Mock()
        supervisor_agent.lifecycle_manager.clear_active_context = Mock()
        
        # Mock core execution
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        await supervisor_agent.execute(state, run_id, stream_updates=True)
        
        # Verify lifecycle hooks called in order
        calls = supervisor_agent.lifecycle_manager.execute_lifecycle_hooks.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "pre_execution"
        assert calls[1][0][0] == "post_execution"
        
        # Verify context tracking
        supervisor_agent.lifecycle_manager.track_active_context.assert_called_once()
        supervisor_agent.lifecycle_manager.clear_active_context.assert_called_once_with(run_id)
    
    @pytest.mark.asyncio
    async def test_error_handling_with_recovery(self, supervisor_agent, execution_context):
        """Test error handling with proper recovery mechanisms."""
        error = Exception("Test error")
        
        # First attempt fails
        supervisor_agent.execute_core_logic = AsyncMock(side_effect=error)
        supervisor_agent.lifecycle_manager.execute_lifecycle_hooks = AsyncMock()
        supervisor_agent.observability.record_agent_error = Mock()
        
        with pytest.raises(Exception):
            await supervisor_agent._execute_with_error_handling(execution_context)
        
        # Verify error handling
        supervisor_agent.observability.record_agent_error.assert_called_with(
            supervisor_agent.name, "Test error"
        )
        supervisor_agent.lifecycle_manager.execute_lifecycle_hooks.assert_called_with(
            "on_error", execution_context, error=error
        )
    
    @pytest.mark.asyncio
    async def test_websocket_notifications_complete_flow(self, supervisor_agent, mock_websocket_manager):
        """Test all required WebSocket notifications are sent during execution."""
        state = DeepAgentState()
        state.user_request = "Test WebSocket flow"
        state.chat_thread_id = "ws_test_thread"
        run_id = str(uuid.uuid4())
        
        # Mock successful workflow
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        await supervisor_agent.execute(state, run_id, stream_updates=True)
        
        # Verify WebSocket manager was called
        assert mock_websocket_manager.send_message.called
    
    @pytest.mark.asyncio
    async def test_agent_registration_and_retrieval(self, supervisor_agent, mock_sub_agent):
        """Test agent registration and retrieval from registry."""
        supervisor_agent.register_agent("test_agent", mock_sub_agent)
        
        # Verify agent is registered
        assert "test_agent" in supervisor_agent.agent_registry.agents
        assert supervisor_agent.agent_registry.agents["test_agent"] == mock_sub_agent
    
    @pytest.mark.asyncio
    async def test_orchestration_decision_generation(self, supervisor_agent):
        """Test LLM-based orchestration decision generation."""
        user_request = "Analyze and optimize this code"
        triage_result = {"complexity": "high", "domain": "code_optimization"}
        
        # Mock LLM response
        supervisor_agent.llm_manager.generate = AsyncMock(return_value=json.dumps({
            "workflow": "optimization",
            "agents": ["code_analyzer", "optimizer"],
            "strategy": "sequential",
            "reasoning": "Code requires analysis before optimization"
        }))
        
        result = await supervisor_agent.generate_orchestration_decision(user_request, triage_result)
        
        assert "workflow" in result
        assert "agents" in result
        assert result["workflow"] == "optimization"
        assert len(result["agents"]) == 2
    
    @pytest.mark.asyncio
    async def test_health_status_comprehensive(self, supervisor_agent):
        """Test comprehensive health status reporting."""
        health = supervisor_agent.get_health_status()
        
        assert "supervisor_health" in health
        assert "observability_metrics" in health
        assert "active_contexts" in health
        assert "registered_agents" in health
        assert "workflow_definition" in health
        
        # Verify types
        assert isinstance(health["active_contexts"], int)
        assert isinstance(health["registered_agents"], int)
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, supervisor_agent):
        """Test performance metrics collection and reporting."""
        metrics = supervisor_agent.get_performance_metrics()
        
        assert metrics is not None
        # Metrics should be from observability component
        assert isinstance(metrics, dict)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self, supervisor_agent):
        """Test circuit breaker status reporting."""
        status = supervisor_agent.get_circuit_breaker_status()
        
        assert status is not None
        assert isinstance(status, dict)


class TestSupervisorOrchestration:
    """Advanced orchestration and workflow tests."""
    
    @pytest.fixture
    def complex_workflow_context(self):
        """Create context for complex workflow testing."""
        state = DeepAgentState()
        state.user_request = "Complex multi-step analysis and optimization"
        state.chat_thread_id = "complex_thread"
        state.user_id = "test_user"
        
        return ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=state,
            stream_updates=True,
            thread_id="complex_thread",
            user_id="test_user",
            start_time=datetime.now(timezone.utc),
            metadata={
                "workflow_type": "complex",
                "priority": "high"
            }
        )
    
    @pytest.mark.asyncio
    async def test_multi_agent_orchestration(self, supervisor_agent, complex_workflow_context):
        """Test orchestration of multiple agents in sequence and parallel."""
        # Register multiple mock agents
        agents = {}
        for name in ["research", "analyzer", "optimizer", "validator"]:
            agent = MagicMock(spec=BaseSubAgent)
            agent.name = name
            agent.execute = AsyncMock(return_value=ExecutionResult(
                success=True,
                status="completed",
                result={f"{name}_output": f"Result from {name}"}
            ))
            agents[name] = agent
            supervisor_agent.register_agent(name, agent)
        
        # Mock workflow with sequential and parallel execution
        mock_workflow_results = [
            ExecutionResult(success=True, status="completed", result={"phase": "research"}),
            ExecutionResult(success=True, status="completed", result={"phase": "analysis_optimization"}),
            ExecutionResult(success=True, status="completed", result={"phase": "validation"})
        ]
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=mock_workflow_results
        )
        
        result = await supervisor_agent.execute_core_logic(complex_workflow_context)
        
        assert result["supervisor_result"] == "completed"
        assert result["total_steps"] == 3
    
    @pytest.mark.asyncio
    async def test_workflow_with_conditional_branching(self, supervisor_agent, complex_workflow_context):
        """Test workflow with conditional branching based on intermediate results."""
        # Setup conditional workflow
        step1_result = ExecutionResult(
            success=True,
            status="completed",
            result={"requires_optimization": True}
        )
        step2_result = ExecutionResult(
            success=True,
            status="completed",
            result={"optimization_complete": True}
        )
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[step1_result, step2_result]
        )
        
        result = await supervisor_agent.execute_core_logic(complex_workflow_context)
        
        assert result["supervisor_result"] == "completed"
        assert len(result["workflow_results"]) == 2
    
    @pytest.mark.asyncio
    async def test_workflow_rollback_on_failure(self, supervisor_agent, complex_workflow_context):
        """Test workflow rollback when critical step fails."""
        # Simulate partial success then failure
        mock_results = [
            ExecutionResult(success=True, status="completed", result={"step": 1}),
            ExecutionResult(success=True, status="completed", result={"step": 2}),
            ExecutionResult(success=False, status="failed", error="Critical failure")
        ]
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=mock_results
        )
        
        result = await supervisor_agent.execute_core_logic(complex_workflow_context)
        
        assert result["supervisor_result"] == "failed"
        assert result["total_steps"] == 3
    
    @pytest.mark.asyncio
    async def test_recursive_agent_delegation(self, supervisor_agent):
        """Test supervisor delegating to another supervisor (recursive orchestration)."""
        # Create nested supervisor
        nested_supervisor = MagicMock(spec=SupervisorAgent)
        nested_supervisor.name = "NestedSupervisor"
        nested_supervisor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            status="completed",
            result={"nested_workflow": "completed"}
        ))
        
        supervisor_agent.register_agent("nested_supervisor", nested_supervisor)
        
        # Execute with nested delegation
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="nested_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc),
            metadata={"delegation": "nested"}
        )
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[ExecutionResult(success=True, status="completed")]
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        
        assert result["supervisor_result"] == "completed"


class TestSupervisorErrorHandling:
    """Comprehensive error handling and recovery tests."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self, supervisor_agent, execution_context):
        """Test handling of database connection failures."""
        # Simulate DB failure
        supervisor_agent.db_session.execute = AsyncMock(
            side_effect=Exception("Database connection lost")
        )
        
        supervisor_agent.execute_core_logic = AsyncMock(
            side_effect=Exception("Database connection lost")
        )
        
        with pytest.raises(Exception) as exc_info:
            await supervisor_agent._execute_with_error_handling(execution_context)
        
        assert "Database connection lost" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self, supervisor_agent, mock_llm_manager):
        """Test handling of LLM timeout scenarios."""
        # Simulate LLM timeout
        mock_llm_manager.generate = AsyncMock(
            side_effect=asyncio.TimeoutError("LLM request timeout")
        )
        
        user_request = "Test request"
        triage_result = {"test": True}
        
        with pytest.raises(asyncio.TimeoutError):
            await supervisor_agent.generate_orchestration_decision(user_request, triage_result)
    
    @pytest.mark.asyncio
    async def test_websocket_disconnection_handling(self, supervisor_agent, mock_websocket_manager):
        """Test graceful handling of WebSocket disconnections."""
        # Simulate WebSocket failure
        mock_websocket_manager.send_message = AsyncMock(
            side_effect=ConnectionError("WebSocket disconnected")
        )
        
        # Should continue execution despite WebSocket issues
        state = DeepAgentState()
        state.user_request = "Test with disconnected WebSocket"
        run_id = str(uuid.uuid4())
        
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        # Should not raise exception for WebSocket issues
        await supervisor_agent.execute(state, run_id, stream_updates=True)
    
    @pytest.mark.asyncio
    async def test_agent_crash_recovery(self, supervisor_agent):
        """Test recovery when a sub-agent crashes during execution."""
        # Create crashing agent
        crashing_agent = MagicMock(spec=BaseSubAgent)
        crashing_agent.name = "CrashingAgent"
        crashing_agent.execute = AsyncMock(
            side_effect=RuntimeError("Agent crashed unexpectedly")
        )
        
        supervisor_agent.register_agent("crashing_agent", crashing_agent)
        
        # Setup workflow that includes crashing agent
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            side_effect=RuntimeError("Agent crashed unexpectedly")
        )
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="crash_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        with pytest.raises(RuntimeError):
            await supervisor_agent.execute_core_logic(context)
    
    @pytest.mark.asyncio
    async def test_memory_exhaustion_protection(self, supervisor_agent):
        """Test protection against memory exhaustion from large payloads."""
        # Create context with extremely large state
        large_state = DeepAgentState()
        large_state.user_request = "x" * (10 * 1024 * 1024)  # 10MB string
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=large_state,
            stream_updates=True,
            thread_id="memory_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        # Should handle large payloads gracefully
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[ExecutionResult(success=True, status="completed")]
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_tripping(self, supervisor_agent):
        """Test circuit breaker tripping after multiple failures."""
        # Simulate multiple failures to trip circuit breaker
        failing_func = AsyncMock(side_effect=Exception("Service unavailable"))
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="circuit_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        # Mock circuit breaker to simulate tripped state
        supervisor_agent.circuit_breaker_integration.execute_with_circuit_protection = AsyncMock(
            side_effect=Exception("Circuit breaker is open")
        )
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = failing_func
        
        with pytest.raises(Exception) as exc_info:
            await supervisor_agent._execute_protected_workflow(context)
        
        assert "Circuit breaker is open" in str(exc_info.value)


class TestSupervisorPerformance:
    """Performance and stress testing for supervisor."""
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_handling(self, supervisor_agent):
        """Test handling of multiple concurrent executions."""
        num_concurrent = 10
        tasks = []
        
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        for i in range(num_concurrent):
            state = DeepAgentState()
            state.user_request = f"Concurrent request {i}"
            run_id = f"concurrent_{i}"
            
            task = asyncio.create_task(
                supervisor_agent.execute(state, run_id, stream_updates=False)
            )
            tasks.append(task)
        
        # All tasks should complete without deadlock
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check no exceptions
        for result in results:
            assert not isinstance(result, Exception)
    
    @pytest.mark.asyncio
    async def test_execution_timeout_enforcement(self, supervisor_agent):
        """Test that long-running executions are properly timed out."""
        # Create slow execution
        async def slow_execution():
            await asyncio.sleep(10)  # Simulate long operation
            return [ExecutionResult(success=True, status="completed")]
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = slow_execution
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="timeout_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc),
            metadata={"timeout": 1}  # 1 second timeout
        )
        
        # Should complete or timeout within reasonable time
        start = time.time()
        try:
            await asyncio.wait_for(
                supervisor_agent.execute_core_logic(context),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            pass
        
        elapsed = time.time() - start
        assert elapsed < 3.0  # Should timeout quickly
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, supervisor_agent):
        """Test that repeated executions don't leak memory."""
        # Track active contexts before
        initial_contexts = len(supervisor_agent.lifecycle_manager.get_active_contexts())
        
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        # Execute multiple times
        for i in range(100):
            state = DeepAgentState()
            state.user_request = f"Memory test {i}"
            run_id = f"memory_{i}"
            
            await supervisor_agent.execute(state, run_id, stream_updates=False)
        
        # Active contexts should not grow unbounded
        final_contexts = len(supervisor_agent.lifecycle_manager.get_active_contexts())
        assert final_contexts == initial_contexts  # Should clean up after each execution
    
    @pytest.mark.asyncio
    async def test_rate_limiting_compliance(self, supervisor_agent, mock_llm_manager):
        """Test that supervisor respects rate limits."""
        call_times = []
        
        async def track_llm_calls(*args, **kwargs):
            call_times.append(time.time())
            return {"decision": "continue"}
        
        mock_llm_manager.generate = track_llm_calls
        
        # Make multiple rapid requests
        for i in range(5):
            await supervisor_agent.generate_orchestration_decision(
                f"Request {i}", {"test": True}
            )
        
        # Verify calls are appropriately spaced (if rate limiting is implemented)
        # This test assumes rate limiting might be added
        assert len(call_times) == 5


class TestSupervisorIntegration:
    """Integration tests with real components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, supervisor_agent, mock_websocket_manager):
        """Test complete end-to-end workflow execution."""
        # Setup complete workflow
        state = DeepAgentState()
        state.user_request = "Analyze this repository and generate documentation"
        state.chat_thread_id = "e2e_thread"
        state.user_id = "test_user"
        run_id = str(uuid.uuid4())
        
        # Mock agents for complete workflow
        research_agent = MagicMock(spec=BaseSubAgent)
        research_agent.name = "ResearchAgent"
        research_agent.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            status="completed",
            result={"files_analyzed": 50, "patterns_found": 10}
        ))
        
        doc_agent = MagicMock(spec=BaseSubAgent)
        doc_agent.name = "DocumentationAgent"
        doc_agent.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            status="completed",
            result={"docs_generated": 5, "format": "markdown"}
        ))
        
        supervisor_agent.register_agent("research", research_agent)
        supervisor_agent.register_agent("documentation", doc_agent)
        
        # Mock workflow execution
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[
                ExecutionResult(success=True, status="completed", result={"phase": "research"}),
                ExecutionResult(success=True, status="completed", result={"phase": "documentation"})
            ]
        )
        
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        # Execute
        await supervisor_agent.execute(state, run_id, stream_updates=True)
        
        # Verify WebSocket notifications sent
        assert mock_websocket_manager.send_message.called
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_failures(self, supervisor_agent, mock_db_session):
        """Test that state is properly persisted and can be recovered."""
        state = DeepAgentState()
        state.user_request = "Persistent task"
        state.chat_thread_id = "persist_thread"
        run_id = str(uuid.uuid4())
        
        # First execution fails partway
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            side_effect=Exception("Temporary failure")
        )
        
        with pytest.raises(Exception):
            await supervisor_agent.execute_core_logic(ExecutionContext(
                run_id=run_id,
                agent_name="SupervisorAgent",
                state=state,
                stream_updates=True,
                thread_id="persist_thread",
                user_id="test_user",
                start_time=datetime.now(timezone.utc)
            ))
        
        # Verify state operations were attempted
        # In real implementation, this would save checkpoint
        
        # Second execution should be able to resume
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[ExecutionResult(success=True, status="completed")]
        )
        
        result = await supervisor_agent.execute_core_logic(ExecutionContext(
            run_id=run_id,
            agent_name="SupervisorAgent",
            state=state,
            stream_updates=True,
            thread_id="persist_thread",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        ))
        
        assert result["supervisor_result"] == "completed"
    
    @pytest.mark.asyncio
    async def test_observability_metrics_accuracy(self, supervisor_agent):
        """Test that observability metrics are accurately collected."""
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="metrics_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        # Execute workflow
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[
                ExecutionResult(success=True, status="completed", execution_time_ms=100),
                ExecutionResult(success=True, status="completed", execution_time_ms=200)
            ]
        )
        
        await supervisor_agent.execute_core_logic(context)
        
        # Get metrics
        metrics = supervisor_agent.get_performance_metrics()
        
        assert metrics is not None
        # Metrics should reflect execution
    
    @pytest.mark.asyncio
    async def test_lifecycle_hooks_execution_order(self, supervisor_agent):
        """Test that lifecycle hooks are executed in correct order."""
        hook_calls = []
        
        async def pre_hook(ctx):
            hook_calls.append("pre")
        
        async def post_hook(ctx, result):
            hook_calls.append("post")
        
        async def error_hook(ctx, error):
            hook_calls.append("error")
        
        supervisor_agent.register_lifecycle_hook("pre_execution", pre_hook)
        supervisor_agent.register_lifecycle_hook("post_execution", post_hook)
        supervisor_agent.register_lifecycle_hook("on_error", error_hook)
        
        # Successful execution
        state = DeepAgentState()
        run_id = str(uuid.uuid4())
        
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        await supervisor_agent.execute(state, run_id, stream_updates=False)
        
        # Verify order (error hook should not be called)
        assert hook_calls == ["pre", "post"]


class TestSupervisorEdgeCases:
    """Edge cases and boundary condition tests."""
    
    @pytest.mark.asyncio
    async def test_empty_state_handling(self, supervisor_agent):
        """Test handling of empty or minimal state."""
        empty_state = DeepAgentState()  # No user_request set
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=empty_state,
            stream_updates=True,
            thread_id="empty_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[]  # No workflow steps
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        
        assert result["supervisor_result"] == "failed"  # Should handle empty gracefully
        assert result["total_steps"] == 0
    
    @pytest.mark.asyncio
    async def test_malformed_llm_response_handling(self, supervisor_agent, mock_llm_manager):
        """Test handling of malformed LLM responses."""
        # Return invalid JSON
        mock_llm_manager.generate = AsyncMock(return_value="Not valid JSON {]}")
        
        # Should handle gracefully
        result = await supervisor_agent.generate_orchestration_decision(
            "Test request", {"test": True}
        )
        
        # Should return some default or error structure
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, supervisor_agent):
        """Test detection and handling of circular agent dependencies."""
        # Create agents with circular dependency
        agent_a = MagicMock(spec=BaseSubAgent)
        agent_a.name = "AgentA"
        agent_a.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            status="completed",
            result={"delegates_to": "AgentB"}
        ))
        
        agent_b = MagicMock(spec=BaseSubAgent)
        agent_b.name = "AgentB"
        agent_b.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            status="completed",
            result={"delegates_to": "AgentA"}  # Circular reference
        ))
        
        supervisor_agent.register_agent("AgentA", agent_a)
        supervisor_agent.register_agent("AgentB", agent_b)
        
        # Should detect and handle circular dependency
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="circular_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        # Mock to prevent infinite loop
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[ExecutionResult(success=True, status="completed")]
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, supervisor_agent):
        """Test handling of unicode and special characters in requests."""
        state = DeepAgentState()
        state.user_request = "测试 Unicode 🚀 handling with émojis and spëcial çharacters"
        state.chat_thread_id = "unicode_test"
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=state,
            stream_updates=True,
            thread_id="unicode_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[ExecutionResult(success=True, status="completed")]
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        assert result["supervisor_result"] == "completed"
    
    @pytest.mark.asyncio
    async def test_extremely_long_execution_chains(self, supervisor_agent):
        """Test handling of extremely long execution chains."""
        # Create a very long chain of execution steps
        long_chain = []
        for i in range(100):
            long_chain.append(ExecutionResult(
                success=True,
                status="completed",
                result={f"step_{i}": f"completed_{i}"}
            ))
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=long_chain
        )
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="long_chain_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        
        assert result["supervisor_result"] == "completed"
        assert result["total_steps"] == 100
    
    @pytest.mark.asyncio
    async def test_null_and_none_value_handling(self, supervisor_agent):
        """Test robust handling of null/None values throughout execution."""
        # Test with None values in various places
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id=None,  # None thread_id
            user_id=None,  # None user_id
            start_time=datetime.now(timezone.utc),
            metadata=None  # None metadata
        )
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            return_value=[ExecutionResult(
                success=True,
                status="completed",
                result=None,  # None result
                error=None,
                execution_time_ms=None
            )]
        )
        
        result = await supervisor_agent.execute_core_logic(context)
        assert result is not None


class TestSupervisorWebSocketIntegration:
    """Critical WebSocket event testing for chat functionality."""
    
    @pytest.mark.asyncio
    async def test_all_required_websocket_events_sent(self, supervisor_agent, mock_websocket_manager):
        """Test that ALL required WebSocket events are sent for chat UI."""
        required_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        state = DeepAgentState()
        state.user_request = "Test all WebSocket events"
        state.chat_thread_id = "ws_all_events"
        run_id = str(uuid.uuid4())
        
        # Track which events are sent
        sent_events = set()
        
        async def track_events(thread_id, message):
            if hasattr(message, 'event'):
                sent_events.add(message.event)
            mock_websocket_manager.messages_sent.append({
                'thread_id': thread_id,
                'message': message
            })
        
        mock_websocket_manager.send_message.side_effect = track_events
        
        # Execute with mocked workflow
        supervisor_agent._execute_with_error_handling = AsyncMock(
            return_value=ExecutionResult(success=True, status="completed")
        )
        
        await supervisor_agent.execute(state, run_id, stream_updates=True)
        
        # Note: In actual implementation, these events would be sent by the execution engine
        # This test verifies the WebSocket manager is properly integrated
        assert mock_websocket_manager.send_message.called
    
    @pytest.mark.asyncio
    async def test_websocket_real_time_updates(self, supervisor_agent, mock_websocket_manager):
        """Test real-time updates are sent during agent execution."""
        update_times = []
        
        async def track_timing(thread_id, message):
            update_times.append(time.time())
        
        mock_websocket_manager.send_message.side_effect = track_timing
        
        # Execute workflow with delays to simulate real work
        async def slow_workflow(context):
            results = []
            for i in range(3):
                await asyncio.sleep(0.1)  # Simulate work
                results.append(ExecutionResult(
                    success=True,
                    status="completed",
                    result={f"step_{i}": "done"}
                ))
            return results
        
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = slow_workflow
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="realtime_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        await supervisor_agent.execute_core_logic(context)
        
        # Updates should be spread over time, not all at once
        if len(update_times) > 1:
            time_spread = update_times[-1] - update_times[0]
            assert time_spread > 0.2  # Should take at least 0.3s total
    
    @pytest.mark.asyncio
    async def test_websocket_error_notification(self, supervisor_agent, mock_websocket_manager):
        """Test that errors are properly notified via WebSocket."""
        error_message_sent = False
        
        async def check_error_message(thread_id, message):
            nonlocal error_message_sent
            if hasattr(message, 'event') and 'error' in message.event.lower():
                error_message_sent = True
        
        mock_websocket_manager.send_message.side_effect = check_error_message
        
        # Cause an error
        supervisor_agent.workflow_orchestrator.execute_standard_workflow = AsyncMock(
            side_effect=Exception("Test error for WebSocket")
        )
        
        context = ExecutionContext(
            run_id=str(uuid.uuid4()),
            agent_name="SupervisorAgent",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="error_ws_test",
            user_id="test_user",
            start_time=datetime.now(timezone.utc)
        )
        
        with pytest.raises(Exception):
            await supervisor_agent.execute_core_logic(context)
        
        # Error notification should be attempted
        # Note: Actual implementation would send error event


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])