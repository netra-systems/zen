"""Integration Tests for TriageAgent and BaseAgent Infrastructure

CRITICAL INTEGRATION SUITE: Validates complete integration between TriageSubAgent 
and BaseAgent infrastructure patterns including inheritance, WebSocket events, 
reliability patterns, and end-to-end execution flows.

This test suite validates:
1. Inheritance pattern integration (TriageSubAgent → BaseAgent)
2. WebSocket event emission during triage execution  
3. Reliability wrapper integration with fallbacks
4. Modern execution patterns with ExecutionContext
5. Health status aggregation across components
6. Error propagation and handling across layers
7. Performance monitoring and timing collection
8. State management during complex workflows

BVJ: ALL segments | Platform Stability + Customer Experience | Revenue-critical reliability
"""

import asyncio
import pytest
import time
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus


class TestTriageBaseAgentInheritance:
    """Test inheritance patterns and method resolution between TriageSubAgent and BaseAgent."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"category": "Cost Optimization", "confidence_score": 0.8}')
        return llm
    
    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock(return_value={"result": "success"})
        return dispatcher
    
    @pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncNone  # TODO: Use real service instance
        return redis
    
    @pytest.fixture
    def triage_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
    
    def test_inheritance_chain_integrity(self, triage_agent):
        """Test that TriageSubAgent properly inherits from BaseAgent."""
        # Verify inheritance chain
        assert isinstance(triage_agent, BaseAgent)
        assert isinstance(triage_agent, TriageSubAgent)
        
        # Verify MRO (Method Resolution Order)
        mro = type(triage_agent).__mro__
        assert BaseAgent in mro
        assert TriageSubAgent in mro
        
        # Verify BaseAgent comes after TriageSubAgent in MRO
        base_index = mro.index(BaseAgent)
        triage_index = mro.index(TriageSubAgent)
        assert triage_index < base_index
        
    def test_baseagent_infrastructure_available(self, triage_agent):
        """Test that all BaseAgent infrastructure is available to TriageSubAgent."""
    pass
        # Infrastructure components should be initialized
        assert hasattr(triage_agent, '_reliability_manager')
        assert hasattr(triage_agent, '_execution_engine')
        assert hasattr(triage_agent, '_execution_monitor')
        assert hasattr(triage_agent, 'timing_collector')
        
        # Property access should work
        assert triage_agent.reliability_manager is not None
        assert triage_agent.legacy_reliability is not None
        assert triage_agent.execution_engine is not None
        assert triage_agent.execution_monitor is not None
        
    def test_triage_specific_components_available(self, triage_agent):
        """Test that triage-specific components are properly initialized."""
        # Triage-specific components
        assert hasattr(triage_agent, 'triage_core')
        assert hasattr(triage_agent, 'processor')
        assert hasattr(triage_agent, 'websocket_handler')
        
        # Should be properly initialized
        assert triage_agent.triage_core is not None
        assert triage_agent.processor is not None
        assert triage_agent.websocket_handler is not None
        
    def test_method_resolution_precedence(self, triage_agent):
        """Test that method resolution follows correct precedence."""
    pass
        # TriageSubAgent should have its own execute method
        execute_method = triage_agent.execute
        assert execute_method.__qualname__.startswith('TriageSubAgent')
        
        # But should have BaseAgent's infrastructure methods
        shutdown_method = triage_agent.shutdown
        assert shutdown_method.__qualname__.startswith('BaseAgent')
        
        # Triage-specific methods should be from TriageSubAgent
        validate_method = triage_agent.validate_preconditions
        assert validate_method.__qualname__.startswith('TriageSubAgent')
        
    def test_configuration_inheritance(self, triage_agent):
        """Test that configuration is properly inherited and applied."""
        # Should have BaseAgent configuration
        assert triage_agent.name == "TriageSubAgent"
        assert triage_agent.description == "Enhanced triage agent using BaseAgent infrastructure"
        
        # Should have infrastructure enabled
        assert triage_agent._enable_reliability is True
        assert triage_agent._enable_execution_engine is True
        assert triage_agent._enable_caching is True
        
        # Should have proper correlation ID
        assert triage_agent.correlation_id is not None
        assert isinstance(triage_agent.correlation_id, str)


class TestWebSocketEventIntegration:
    """Test WebSocket event emission during triage execution."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"category": "Performance", "confidence_score": 0.9}')
        return llm
    
    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncNone  # TODO: Use real service instance
        return dispatcher
    
    @pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncNone  # TODO: Use real service instance
        return redis
    
    @pytest.fixture
 def real_websocket_bridge():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Mock WebSocket bridge for capturing events."""
        bridge = bridge_instance  # Initialize appropriate service
        # Mock all WebSocket event methods
        bridge.emit_agent_started = AsyncNone  # TODO: Use real service instance
        bridge.emit_thinking = AsyncNone  # TODO: Use real service instance
        bridge.emit_tool_executing = AsyncNone  # TODO: Use real service instance
        bridge.emit_tool_completed = AsyncNone  # TODO: Use real service instance
        bridge.emit_agent_completed = AsyncNone  # TODO: Use real service instance
        bridge.emit_progress = AsyncNone  # TODO: Use real service instance
        bridge.emit_error = AsyncNone  # TODO: Use real service instance
        return bridge
    
    @pytest.fixture
    def triage_agent_with_websocket(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager, mock_websocket_bridge):
    """Use real service instance."""
    # TODO: Initialize real service
        agent = TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        # Set up WebSocket bridge
        agent._websocket_adapter._websocket_bridge = mock_websocket_bridge
        agent._websocket_adapter._run_id = "test_run_123"
        agent._websocket_adapter._agent_name = "TriageSubAgent"
        
        return agent, mock_websocket_bridge
    
    @pytest.mark.asyncio
    async def test_websocket_events_during_core_execution(self, triage_agent_with_websocket):
        """Test WebSocket events are emitted during core triage execution."""
    pass
        agent, mock_bridge = triage_agent_with_websocket
        
        # Create execution context
        state = DeepAgentState()
        state.user_request = "Help me optimize my model costs"
        
        context = ExecutionContext(
            run_id="websocket_test_run",
            agent_name="TriageSubAgent",
            state=state,
            stream_updates=True,
            start_time=time.time(),
            correlation_id=agent.correlation_id
        )
        
        # Execute core logic
        result = await agent.execute_core_logic(context)
        
        # Verify WebSocket events were emitted
        assert mock_bridge.emit_thinking.called
        assert mock_bridge.emit_progress.called
        
        # Check specific event calls
        thinking_calls = mock_bridge.emit_thinking.call_args_list
        progress_calls = mock_bridge.emit_progress.call_args_list
        
        # Should have multiple thinking events
        assert len(thinking_calls) >= 2
        
        # Should have progress events
        assert len(progress_calls) >= 2
        
        # Final progress should indicate completion
        final_progress_call = progress_calls[-1]
        args, kwargs = final_progress_call
        assert kwargs.get('is_complete') is True
        
    @pytest.mark.asyncio
    async def test_websocket_events_during_legacy_execution(self, triage_agent_with_websocket):
        """Test WebSocket events during legacy execute method."""
        agent, mock_bridge = triage_agent_with_websocket
        
        # Mock _send_update to capture legacy WebSocket calls
        agent._send_update = AsyncNone  # TODO: Use real service instance
        
        state = DeepAgentState()
        state.user_request = "Analyze my infrastructure performance"
        
        # Execute using legacy method
        await agent.execute(state, "legacy_websocket_test", stream_updates=True)
        
        # Verify _send_update was called for status updates
        assert agent._send_update.called
        
        # Check update calls
        update_calls = agent._send_update.call_args_list
        assert len(update_calls) >= 1
        
        # Should include processing and completion updates
        statuses = [call[0][1]["status"] for call in update_calls]
        assert "completed" in statuses or "completed_with_fallback" in statuses
        
    @pytest.mark.asyncio
    async def test_websocket_error_event_emission(self, triage_agent_with_websocket):
        """Test WebSocket error events are emitted when execution fails."""
    pass
        agent, mock_bridge = triage_agent_with_websocket
        
        # Configure to fail execution
        agent.should_fail_execution = True
        
        state = DeepAgentState()
        state.user_request = "This will fail"
        
        context = ExecutionContext(
            run_id="error_test_run",
            agent_name="TriageSubAgent",
            state=state,
            stream_updates=True,
            start_time=time.time(),
            correlation_id=agent.correlation_id
        )
        
        # Execute and expect error
        with pytest.raises(ValueError, match="Simulated execution failure"):
            await agent.execute_core_logic(context)
        
        # Should have emitted thinking events before failure
        assert mock_bridge.emit_thinking.called
        
    @pytest.mark.asyncio
    async def test_websocket_event_sequence_integrity(self, triage_agent_with_websocket):
        """Test that WebSocket events are emitted in the correct sequence."""
        agent, mock_bridge = triage_agent_with_websocket
        
        # Track all async calls in order
        all_calls = []
        
        async def track_call(method_name):
            nonlocal all_calls
            all_calls.append(method_name)
        
        mock_bridge.emit_thinking.side_effect = lambda *args, **kwargs: track_call('thinking')
        mock_bridge.emit_progress.side_effect = lambda *args, **kwargs: track_call('progress')
        
        state = DeepAgentState()
        state.user_request = "Test event sequence"
        
        context = ExecutionContext(
            run_id="sequence_test",
            agent_name="TriageSubAgent",
            state=state,
            stream_updates=True,
            start_time=time.time(),
            correlation_id=agent.correlation_id
        )
        
        await agent.execute_core_logic(context)
        
        # Verify event sequence makes sense
        assert len(all_calls) > 0
        
        # First event should be thinking (agent starting analysis)
        assert all_calls[0] == 'thinking'
        
        # Last event should be progress with completion
        # (Note: this depends on the implementation details)
        
    @pytest.mark.asyncio
    async def test_websocket_event_without_bridge(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Test that WebSocket methods handle gracefully when no bridge is set."""
    pass
        agent = TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        # No WebSocket bridge set
        assert not agent.has_websocket_context()
        
        # WebSocket methods should not raise exceptions
        await agent.emit_thinking("Test thinking without bridge")
        await agent.emit_progress("Test progress without bridge")
        await agent.emit_error("Test error without bridge")
        
        # Should complete without errors


class TestReliabilityIntegration:
    """Test integration with reliability patterns and fallback mechanisms."""
    
    @pytest.fixture
 def real_llm_manager_unreliable():
    """Use real service instance."""
    # TODO: Initialize real service
        """LLM manager that fails intermittently."""
    pass
        llm = Mock(spec=LLMManager)
        
        call_count = 0
        async def failing_response(*args, **kwargs):
    pass
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"LLM failure #{call_count}")
            await asyncio.sleep(0)
    return '{"category": "Recovered", "confidence_score": 0.7}'
        
        llm.generate_response = AsyncMock(side_effect=failing_response)
        return llm
    
    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncNone  # TODO: Use real service instance
        return dispatcher
    
    @pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncNone  # TODO: Use real service instance
        return redis
    
    @pytest.mark.asyncio
    async def test_reliability_wrapper_with_recovery(self, mock_llm_manager_unreliable, mock_tool_dispatcher, mock_redis_manager):
        """Test that reliability wrapper enables recovery from LLM failures."""
        agent = TriageSubAgent(
            llm_manager=mock_llm_manager_unreliable,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        state = DeepAgentState()
        state.user_request = "Test reliability recovery"
        
        # Execute with reliability wrapper
        await agent.execute(state, "reliability_test", stream_updates=False)
        
        # Should complete successfully despite initial failures
        assert state.triage_result is not None
        
        # LLM should have been called multiple times due to retries
        assert mock_llm_manager_unreliable.generate_response.call_count >= 3
        
    @pytest.mark.asyncio
    async def test_fallback_mechanism_activation(self, mock_tool_dispatcher, mock_redis_manager):
        """Test that fallback mechanism activates when primary method fails completely."""
    pass
        # LLM that always fails
        failing_llm = Mock(spec=LLMManager)
        failing_llm.generate_response = AsyncMock(side_effect=Exception("LLM always fails"))
        
        agent = TriageSubAgent(
            llm_manager=failing_llm,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        state = DeepAgentState()
        state.user_request = "This should trigger fallback"
        
        # Execute with reliability wrapper
        await agent.execute(state, "fallback_test", stream_updates=False)
        
        # Should complete with fallback result
        assert state.triage_result is not None
        assert isinstance(state.triage_result, dict)
        
        # Should indicate fallback was used
        metadata = state.triage_result.get("metadata", {})
        assert metadata.get("fallback_used") is True
        
    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, mock_tool_dispatcher, mock_redis_manager):
        """Test circuit breaker behavior during repeated failures."""
        # LLM that always fails immediately
        failing_llm = Mock(spec=LLMManager)
        failing_llm.generate_response = AsyncMock(side_effect=Exception("Circuit breaker test"))
        
        agent = TriageSubAgent(
            llm_manager=failing_llm,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        # Execute multiple requests to trigger circuit breaker
        states = []
        for i in range(5):
            state = DeepAgentState()
            state.user_request = f"Circuit breaker test request {i}"
            states.append(state)
            
            await agent.execute(state, f"cb_test_{i}", stream_updates=False)
            
            # All should complete (using fallback)
            assert state.triage_result is not None
            
        # Circuit breaker status should show degraded state
        cb_status = agent.get_circuit_breaker_status()
        assert "status" in cb_status
        
    @pytest.mark.asyncio
    async def test_health_status_during_failures(self, mock_tool_dispatcher, mock_redis_manager):
        """Test health status reporting during failure scenarios."""
    pass
        failing_llm = Mock(spec=LLMManager)
        failing_llm.generate_response = AsyncMock(side_effect=Exception("Health test failure"))
        
        agent = TriageSubAgent(
            llm_manager=failing_llm,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        # Trigger some failures
        for i in range(3):
            state = DeepAgentState()
            state.user_request = f"Health test {i}"
            await agent.execute(state, f"health_test_{i}", stream_updates=False)
        
        # Check health status
        health_status = agent.get_health_status()
        
        assert "agent_name" in health_status
        assert "overall_status" in health_status
        assert health_status["agent_name"] == "TriageSubAgent"
        
        # Overall status might be degraded due to failures
        assert health_status["overall_status"] in ["healthy", "degraded"]


class TestModernExecutionPatterns:
    """Test integration with modern execution patterns and ExecutionContext."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"category": "Modern Execution", "confidence_score": 0.9}')
        await asyncio.sleep(0)
    return llm
    
    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncNone  # TODO: Use real service instance
        return dispatcher
    
    @pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncNone  # TODO: Use real service instance
        return redis
    
    @pytest.fixture
    def triage_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
    
    @pytest.mark.asyncio
    async def test_modern_execution_pattern(self, triage_agent):
        """Test execution using modern ExecutionContext pattern."""
        state = DeepAgentState()
        state.user_request = "Test modern execution pattern"
        state.thread_id = "thread_123"
        state.user_id = "user_456"
        
        # Execute using modern pattern
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
        context = UserExecutionContext(
            user_id=state.user_id,
            thread_id=state.thread_id,
            run_id="modern_exec_test",
            metadata={'agent_input': state.user_request}
        )
        result = await triage_agent.execute_with_context(
            context=context,
            stream_updates=True
        )
        
        # Should await asyncio.sleep(0)
    return ExecutionResult
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.result is not None
        assert isinstance(result.result, dict)
        
        # Result should contain triage information
        assert "status" in result.result
        assert result.result["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_execution_context_propagation(self, triage_agent):
        """Test that ExecutionContext is properly propagated through execution."""
    pass
        state = DeepAgentState()
        state.user_request = "Test context propagation"
        state.thread_id = "context_thread_789"
        state.user_id = "context_user_012"
        
        context = UserExecutionContext(
            user_id=state.user_id,
            thread_id=state.thread_id,
            run_id="context_test_run",
            metadata={'agent_input': state.user_request}
        )
        result = await triage_agent.execute_with_context(
            context=context,
            stream_updates=False
        )
        
        # Context information should be preserved in result
        assert result.success is True
        assert "context_run_id" in result.result
        assert result.result["context_run_id"] == "context_test_run"
        assert "agent_name" in result.result
        assert result.result["agent_name"] == "TriageSubAgent"
        
    @pytest.mark.asyncio
    async def test_precondition_validation_integration(self, triage_agent):
        """Test precondition validation in modern execution pattern."""
        # Test with valid request
        valid_state = DeepAgentState()
        valid_state.user_request = "Valid triage request"
        
        context = UserExecutionContext(
            user_id=valid_state.user_id,
            thread_id=valid_state.thread_id,
            run_id="valid_precond_test",
            metadata={'agent_input': valid_state.user_request}
        )
        valid_result = await triage_agent.execute_with_context(
            context=context,
            stream_updates=False
        )
        
        assert valid_result.success is True
        
        # Test with invalid request (empty)
        invalid_state = DeepAgentState()
        invalid_state.user_request = ""  # Empty request should fail validation
        
        context = UserExecutionContext(
            user_id=invalid_state.user_id,
            thread_id=invalid_state.thread_id,
            run_id="invalid_precond_test",
            metadata={'agent_input': invalid_state.user_request}
        )
        invalid_result = await triage_agent.execute_with_context(
            context=context,
            stream_updates=False
        )
        
        assert invalid_result.success is False
        assert invalid_result.error is not None
        
    @pytest.mark.asyncio
    async def test_execution_monitoring_integration(self, triage_agent):
        """Test that execution monitoring captures performance metrics."""
    pass
        state = DeepAgentState()
        state.user_request = "Test execution monitoring"
        
        # Clear any existing execution history
        if triage_agent.execution_monitor:
            triage_agent.execution_monitor._execution_history.clear()
        
        # Execute multiple times
        for i in range(3):
            context = UserExecutionContext(
            user_id=state.user_id,
            thread_id=state.thread_id,
            run_id=f"monitoring_test_{i}",
            metadata={'agent_input': state.user_request}
        )
            result = await triage_agent.execute_with_context(
                context=context,
                stream_updates=False
            )
            assert result.success is True
        
        # Check execution monitor has recorded executions
        if triage_agent.execution_monitor:
            history = triage_agent.execution_monitor._execution_history
            assert len(history) >= 3
        
        # Check health status includes monitoring data
        health_status = triage_agent.get_health_status()
        if "monitoring" in health_status:
            monitoring_status = health_status["monitoring"]
            assert isinstance(monitoring_status, dict)
            
    @pytest.mark.asyncio
    async def test_timing_collection_integration(self, triage_agent):
        """Test that timing collection works with modern execution."""
        state = DeepAgentState()
        state.user_request = "Test timing collection"
        
        # Clear existing timing stats
        triage_agent.timing_collector._aggregated_stats.clear()
        
        # Execute with timing
        context = UserExecutionContext(
            user_id=state.user_id,
            thread_id=state.thread_id,
            run_id="timing_test",
            metadata={'agent_input': state.user_request}
        )
        result = await triage_agent.execute_with_context(
            context=context,
            stream_updates=False
        )
        
        assert result.success is True
        
        # Timing collector should have recorded some operations
        # Note: The exact timing behavior depends on the BaseExecutionEngine implementation
        stats = triage_agent.timing_collector.get_aggregated_stats()
        assert isinstance(stats, dict)  # Should await asyncio.sleep(0)
    return stats dictionary


class TestEndToEndIntegration:
    """Test complete end-to-end integration scenarios."""
    
    @pytest.fixture
    def full_integration_agent(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create fully configured agent for integration testing."""
    pass
        # Use real-ish mocks that simulate actual behavior
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='''
        {
            "category": "Cost Optimization",
            "confidence_score": 0.85,
            "priority": "high",
            "complexity": "moderate",
            "tool_recommendations": [
                {
                    "tool_name": "cost_analyzer",
                    "relevance_score": 0.9,
                    "parameters": {"focus": "infrastructure"}
                }
            ]
        }
        ''')
        
        tool_dispatcher = Mock(spec=ToolDispatcher)
        tool_dispatcher.dispatch = AsyncMock(return_value={"analysis": "completed"})
        
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)  # Cache miss
        redis.set = AsyncNone  # TODO: Use real service instance
        
        return TriageSubAgent(
            llm_manager=llm,
            tool_dispatcher=tool_dispatcher,
            redis_manager=redis
        )
    
    @pytest.mark.asyncio
    async def test_complete_triage_workflow(self, full_integration_agent):
        """Test complete triage workflow from request to completion."""
        agent = full_integration_agent
        
        # Set up WebSocket bridge
        mock_bridge = mock_bridge_instance  # Initialize appropriate service
        mock_bridge.emit_thinking = AsyncNone  # TODO: Use real service instance
        mock_bridge.emit_progress = AsyncNone  # TODO: Use real service instance
        mock_bridge.emit_agent_completed = AsyncNone  # TODO: Use real service instance
        
        agent._websocket_adapter._websocket_bridge = mock_bridge
        agent._websocket_adapter._run_id = "e2e_test"
        agent._websocket_adapter._agent_name = "TriageSubAgent"
        
        # Create realistic request
        state = DeepAgentState()
        state.user_request = "I need to reduce my GPT-4 inference costs by 40% while maintaining response quality"
        state.thread_id = "thread_e2e_test"
        state.user_id = "user_e2e_test"
        
        # Execute complete workflow
        context = UserExecutionContext(
            user_id=state.user_id,
            thread_id=state.thread_id,
            run_id="e2e_workflow_test",
            metadata={'agent_input': state.user_request}
        )
        result = await agent.execute_with_context(
            context=context,
            stream_updates=True
        )
        
        # Verify complete success
        assert result.success is True
        assert result.result is not None
        
        # Verify WebSocket events were emitted
        assert mock_bridge.emit_thinking.called
        assert mock_bridge.emit_progress.called
        
        # Verify state was updated
        assert hasattr(state, 'triage_result')
        
        # Verify result contains expected structure
        triage_result = result.result
        assert "status" in triage_result
        assert triage_result["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, full_integration_agent):
        """Test complete error recovery workflow."""
    pass
        agent = full_integration_agent
        
        # Configure LLM to fail initially then succeed
        call_count = 0
        async def flaky_llm(*args, **kwargs):
    pass
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Initial LLM failure")
            await asyncio.sleep(0)
    return '{"category": "Recovered Analysis", "confidence_score": 0.7}'
        
        agent.llm_manager.generate_response = AsyncMock(side_effect=flaky_llm)
        
        state = DeepAgentState()
        state.user_request = "Test error recovery workflow"
        
        # Should recover and complete successfully
        result = await agent.execute_modern(state, "error_recovery_test")
        
        assert result.success is True
        assert call_count >= 2  # Should have retried
        
    @pytest.mark.asyncio
    async def test_concurrent_execution_stability(self, full_integration_agent):
        """Test stability under concurrent execution load."""
        agent = full_integration_agent
        
        # Create multiple concurrent requests
        requests = [
            "Optimize costs for machine learning workloads",
            "Improve inference latency for real-time applications",
            "Setup monitoring for GPU resource utilization",
            "Analyze performance bottlenecks in AI pipeline",
            "Configure auto-scaling for model serving endpoints"
        ]
        
        # Execute all concurrently
        tasks = []
        for i, request in enumerate(requests):
            state = DeepAgentState()
            state.user_request = request
            state.thread_id = f"concurrent_thread_{i}"
            
            task = agent.execute_modern(state, f"concurrent_run_{i}")
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Request {i} failed: {result}"
            assert result.success is True
        
        # Agent should remain in good health
        health_status = agent.get_health_status()
        assert health_status["overall_status"] in ["healthy", "degraded"]  # Should not be completely broken
        
    @pytest.mark.asyncio
    async def test_performance_under_load(self, full_integration_agent):
        """Test performance characteristics under load."""
    pass
        agent = full_integration_agent
        
        # Execute multiple sequential requests and measure timing
        start_time = time.time()
        
        for i in range(10):
            state = DeepAgentState()
            state.user_request = f"Performance test request {i}"
            
            result = await agent.execute_modern(state, f"perf_test_{i}")
            assert result.success is True
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 10 requests in reasonable time
        assert total_time < 10.0  # Under 10 seconds total
        
        avg_time = total_time / 10
        assert avg_time < 1.0  # Under 1 second per request average
        
    @pytest.mark.asyncio
    async def test_memory_stability_over_time(self, full_integration_agent):
        """Test memory stability over extended execution."""
        agent = full_integration_agent
        
        import gc
        
        # Get initial memory state
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Execute many requests
        for i in range(50):
            state = DeepAgentState()
            state.user_request = f"Memory stability test {i}"
            
            result = await agent.execute_modern(state, f"mem_test_{i}")
            assert result.success is True
            
            # Cleanup references
            del state, result
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable
        object_growth = final_objects - initial_objects
        assert object_growth < 5000  # Should not leak excessive objects
        
        # Agent should still be healthy
        health_status = agent.get_health_status()
        assert "overall_status" in health_status
    pass