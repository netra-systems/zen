"""Comprehensive BaseAgent Infrastructure Tests

CRITICAL TEST SUITE: Validates SSOT refactoring and infrastructure consolidation.

This test suite validates:
1. Reliability management (circuit breakers, retries, health monitoring)
2. Execution engine patterns (modern execution, precondition validation)
3. WebSocket infrastructure (event emission, bridge integration)
4. Health monitoring (component aggregation, status reporting)
5. Property initialization (optional features, configuration)

BVJ: ALL segments | Platform Stability | Prevents reliability regressions
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.registry import DeepAgentState
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.schemas.core_enums import ExecutionStatus
from shared.isolated_environment import get_env


class MockBaseAgent(BaseAgent):
    """Mock implementation for testing BaseAgent infrastructure."""
    
    def __init__(self, *args, **kwargs):
    pass
        super().__init__(*args, **kwargs)
        self.core_logic_calls = 0
        self.validation_calls = 0
        self.should_fail_validation = False
        self.should_fail_execution = False
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        self.validation_calls += 1
        return not self.should_fail_validation
    
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> ExecutionResult:
        """Modern execution pattern using UserExecutionContext."""
        
        # Create ExecutionContext for validation
        exec_context = ExecutionContext(
            request_id=context.run_id,
            run_id=context.run_id,
            agent_name=self.name,
            stream_updates=stream_updates,
            user_id=context.user_id
        )
        
        # Call validate_preconditions
        if not await self.validate_preconditions(exec_context):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                request_id=context.run_id,
                data=None,
                error_message="Validation failed"
            )
        
        # Only increment core_logic_calls if validation passed
        self.core_logic_calls += 1
        
        if self.should_fail_execution:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                request_id=context.run_id,
                data=None,
                error_message="Simulated execution failure"
            )
            
        return ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id=context.run_id,
            data={
                "status": "success",
                "message": "Mock execution completed",
                "context_run_id": context.run_id,
                "agent_name": self.name
            },
            error_message=None
        )


class TestBaseAgentReliabilityInfrastructure:
    """Test reliability management infrastructure (circuit breakers, retries, health)."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        """Mock LLM manager for testing."""
    pass
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value="Mock LLM response")
        return llm
    
    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
        """Mock tool dispatcher for testing."""
    pass
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock(return_value={"result": "Mock tool result"})
        return dispatcher
    
    @pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        """Mock Redis manager for testing."""
    pass
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncNone  # TODO: Use real service instance
        return redis
    
    def test_reliability_infrastructure_initialization_enabled(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Test reliability infrastructure is properly initialized when enabled."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityTestAgent",
            enable_reliability=True,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
        
        # Verify reliability infrastructure is initialized
        assert agent._enable_reliability is True
        assert agent.reliability_manager is not None
        assert isinstance(agent.reliability_manager, ReliabilityManager)
        assert agent.legacy_reliability is not None
        
        # Verify property access
        assert agent.reliability_manager is not None
        assert agent.legacy_reliability is not None
        
        # Verify circuit breaker configuration
        circuit_status = agent.get_circuit_breaker_status()
        assert "status" in circuit_status
        
    def test_reliability_infrastructure_initialization_disabled(self, mock_llm_manager):
        """Test reliability infrastructure is not initialized when disabled."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoReliabilityAgent",
            enable_reliability=False
        )
        
        # Verify reliability infrastructure is not initialized
        assert agent._enable_reliability is False
        assert agent.reliability_manager is None
        assert agent.legacy_reliability is None
        
        # Verify property access returns None
        assert agent.reliability_manager is None
        assert agent.legacy_reliability is None
        
        # Circuit breaker status should indicate not available
        circuit_status = agent.get_circuit_breaker_status()
        assert circuit_status["status"] == "not_available"
        assert "reason" in circuit_status
        
    @pytest.mark.asyncio
    async def test_execute_with_reliability_success(self, mock_llm_manager, mock_tool_dispatcher):
        """Test successful execution with reliability wrapper."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilitySuccessAgent",
            enable_reliability=True,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Mock operation that succeeds
        async def success_operation():
            await asyncio.sleep(0.01)  # Simulate work
            await asyncio.sleep(0)
    return {"result": "success"}
        
        result = await agent.execute_with_reliability(
            operation=success_operation,
            operation_name="test_success_operation",
            timeout=5.0
        )
        
        assert result == {"result": "success"}
        
    @pytest.mark.asyncio
    async def test_execute_with_reliability_failure_and_recovery(self, mock_llm_manager, mock_tool_dispatcher):
        """Test failure handling and recovery with reliability wrapper."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityFailureAgent",
            enable_reliability=True,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        call_count = 0
        
        async def flaky_operation():
    pass
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Simulated failure {call_count}")
            await asyncio.sleep(0)
    return {"result": "recovered", "attempts": call_count}
        
        # Should succeed after retries
        result = await agent.execute_with_reliability(
            operation=flaky_operation,
            operation_name="test_flaky_operation",
            timeout=10.0
        )
        
        assert result["result"] == "recovered"
        assert call_count >= 3  # Should have retried
        
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Circuit breaker behavior needs refactoring in UnifiedRetryHandler")
    async def test_execute_with_reliability_with_fallback(self, mock_llm_manager, mock_tool_dispatcher):
        """Test fallback execution when primary operation fails."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityFallbackAgent",
            enable_reliability=True,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Mock the circuit breaker to prevent it from opening
        mock_circuit_breaker = mock_circuit_breaker_instance  # Initialize appropriate service
        mock_circuit_breaker.is_open = Mock(return_value=False)
        mock_circuit_breaker.is_closed = Mock(return_value=True)
        mock_circuit_breaker.record_success = record_success_instance  # Initialize appropriate service
        mock_circuit_breaker.record_failure = record_failure_instance  # Initialize appropriate service
        mock_circuit_breaker.reset = reset_instance  # Initialize appropriate service
        
        # Replace the circuit breaker with our mock
        agent.circuit_breaker._circuit_breaker = mock_circuit_breaker
        if hasattr(agent, '_unified_reliability_handler') and agent._unified_reliability_handler:
            agent._unified_reliability_handler.circuit_breaker = mock_circuit_breaker
        
        async def failing_operation():
            raise ValueError("Primary operation always fails")
        
        async def fallback_operation():
            await asyncio.sleep(0)
    return {"result": "fallback_success", "source": "fallback"}
        
        result = await agent.execute_with_reliability(
            operation=failing_operation,
            operation_name="test_fallback_operation",
            fallback=fallback_operation,
            timeout=5.0
        )
        
        assert result["result"] == "fallback_success"
        assert result["source"] == "fallback"
        
    def test_execute_with_reliability_not_enabled_error(self, mock_llm_manager):
        """Test error when trying to use reliability without enabling it."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoReliabilityAgent",
            enable_reliability=False
        )
        
        async def dummy_operation():
    pass
            await asyncio.sleep(0)
    return "dummy"
        
        with pytest.raises(RuntimeError, match="Reliability not enabled"):
            asyncio.run(agent.execute_with_reliability(
                operation=dummy_operation,
                operation_name="test_operation"
            ))


class TestBaseAgentExecutionEngine:
    """Test execution engine patterns (modern execution, monitoring, context handling)."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value="Mock response")
        return llm
    
    def test_execution_engine_initialization_enabled(self, mock_llm_manager):
        """Test execution engine is properly initialized when enabled."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionEngineAgent",
            enable_execution_engine=True,
            enable_reliability=True  # Required for execution engine
        )
        
        # Verify execution infrastructure is initialized
        assert agent._enable_execution_engine is True
        assert agent.execution_engine is not None
        assert isinstance(agent.execution_engine, BaseExecutionEngine)
        assert agent._execution_monitor is not None
        assert isinstance(agent._execution_monitor, ExecutionMonitor)
        
        # Verify property access
        assert agent.execution_engine is not None
        assert agent.execution_monitor is not None
        
    def test_execution_engine_initialization_disabled(self, mock_llm_manager):
        """Test execution engine is not initialized when disabled."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoExecutionEngineAgent",
            enable_execution_engine=False
        )
        
        # Verify execution infrastructure is not initialized
        assert agent._enable_execution_engine is False
        assert agent.execution_engine is None
        # Monitor is always created for basic tracking
        assert agent._execution_monitor is not None
        
        # Verify property access
        assert agent.execution_engine is None
        assert agent.execution_monitor is not None
        
    @pytest.mark.asyncio
    async def test_execute_modern_success(self, mock_llm_manager):
        """Test successful modern execution pattern."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ModernExecutionAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Create test state
        state = DeepAgentState()
        state.user_request = "Test user request"
        state.chat_thread_id = "test_thread_123"
        state.user_id = "test_user_456"
        
        # Execute using modern pattern
        context = UserExecutionContext(
            user_id=state.user_id,
            thread_id=state.chat_thread_id,
            run_id="test_run_789",
            metadata={'agent_input': state.user_request}
        )
        result = await agent.execute_with_context(
            context=context,
            stream_updates=True
        )
        
        # Verify execution result
        assert isinstance(result, ExecutionResult)
        assert result.is_success is True
        assert result.result is not None
        assert result.result["status"] == "success"
        assert result.result["context_run_id"] == "test_run_789"
        
        # Verify agent methods were called
        assert agent.validation_calls == 1
        assert agent.core_logic_calls == 1
        
    @pytest.mark.asyncio
    async def test_execute_modern_validation_failure(self, mock_llm_manager):
        """Test modern execution with validation failure."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ValidationFailureAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Configure agent to fail validation
        agent.should_fail_validation = True
        
        state = DeepAgentState()
        state.user_request = "Test request"
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="validation_fail_run",
            metadata={'agent_input': state.user_request}
        )
        result = await agent.execute_with_context(
            context=context,
            stream_updates=False
        )
        
        # Execution should fail due to validation
        assert result.is_success is False
        assert result.error is not None
        assert agent.validation_calls == 1
        assert agent.core_logic_calls == 0  # Should not reach core logic
        
    @pytest.mark.asyncio
    async def test_execute_modern_execution_failure(self, mock_llm_manager):
        """Test modern execution with core logic failure."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionFailureAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Configure agent to fail execution
        agent.should_fail_execution = True
        
        state = DeepAgentState()
        state.user_request = "Test request"
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="execution_fail_run",
            metadata={'agent_input': state.user_request}
        )
        result = await agent.execute_with_context(
            context=context,
            stream_updates=False
        )
        
        # Execution should fail in core logic
        assert result.is_success is False
        assert result.error is not None
        assert "Simulated execution failure" in str(result.error)
        assert agent.validation_calls == 1
        assert agent.core_logic_calls == 1
        
    @pytest.mark.asyncio
    async def test_execute_modern_not_enabled_error(self, mock_llm_manager):
        """Test that execute_modern works even without execution engine (backward compatibility)."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoModernExecutionAgent",
            enable_execution_engine=False
        )
        
        state = DeepAgentState()
        
        # Should work with direct execution fallback (with deprecation warning)
        with pytest.warns(DeprecationWarning, match="execute_modern.*is deprecated"):
            result = await agent.execute_modern(state, "test_run")
            
        # Verify it executed successfully with fallback
        assert result is not None
        assert result.status == ExecutionStatus.SUCCESS


class TestBaseAgentWebSocketInfrastructure:
    """Test WebSocket infrastructure (event emission, bridge integration, update methods)."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        await asyncio.sleep(0)
    return llm
    
    @pytest.fixture
 def real_websocket_bridge():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Mock WebSocket bridge for testing."""
        bridge = bridge_instance  # Initialize appropriate service
        bridge.notify_agent_thinking = AsyncNone  # TODO: Use real service instance
        bridge.notify_agent_completed = AsyncNone  # TODO: Use real service instance
        bridge.notify_custom = AsyncNone  # TODO: Use real service instance
        return bridge
    
    def test_websocket_bridge_integration(self, mock_llm_manager):
        """Test WebSocket bridge integration and event emission."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="WebSocketAgent"
        )
        
        # Initially no WebSocket context
        assert not agent.has_websocket_context()
        
        # Set WebSocket bridge
        mock_bridge = mock_bridge_instance  # Initialize appropriate service
        agent.set_websocket_bridge(mock_bridge, "test_run_123")
        
        # Verify WebSocket context is available
        assert agent.has_websocket_context()
        
    @pytest.mark.asyncio
    async def test_websocket_event_emission_methods(self, mock_llm_manager):
        """Test all WebSocket event emission methods."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="WebSocketEventsAgent"
        )
        
        # Mock the WebSocket bridge with the methods that WebSocketBridgeAdapter actually calls
        mock_bridge = mock_bridge_instance  # Initialize appropriate service
        mock_bridge.notify_agent_started = AsyncNone  # TODO: Use real service instance
        mock_bridge.notify_agent_thinking = AsyncNone  # TODO: Use real service instance
        mock_bridge.notify_tool_executing = AsyncNone  # TODO: Use real service instance
        mock_bridge.notify_tool_completed = AsyncNone  # TODO: Use real service instance
        mock_bridge.notify_agent_completed = AsyncNone  # TODO: Use real service instance
        mock_bridge.notify_progress_update = AsyncNone  # TODO: Use real service instance  # emit_progress calls this
        mock_bridge.notify_agent_error = AsyncNone  # TODO: Use real service instance      # emit_error calls this
        mock_bridge.notify_custom = AsyncNone  # TODO: Use real service instance           # subagent methods call this
        
        # Use the proper method to set the bridge
        agent.set_websocket_bridge(mock_bridge, "test_run")
        
        # Test all emission methods
        await agent.emit_agent_started("Agent started message")
        mock_bridge.notify_agent_started.assert_called_once()
        
        await agent.emit_thinking("Thinking about the problem", step_number=1)
        mock_bridge.notify_agent_thinking.assert_called_once()
        
        await agent.emit_tool_executing("test_tool", {"param": "value"})
        mock_bridge.notify_tool_executing.assert_called_once()
        
        await agent.emit_tool_completed("test_tool", {"result": "success"})
        mock_bridge.notify_tool_completed.assert_called_once()
        
        await agent.emit_agent_completed({"final_result": "completed"})
        mock_bridge.notify_agent_completed.assert_called_once()
        
        await agent.emit_progress("50% complete", is_complete=False)
        mock_bridge.notify_progress_update.assert_called_once()
        
        await agent.emit_error("Test error", "ValidationError", {"details": "test"})
        mock_bridge.notify_agent_error.assert_called_once()
        
        # Test backward compatibility methods
        await agent.emit_tool_started("test_tool", {"param": "value"})
        # emit_tool_started calls emit_tool_executing, which calls notify_tool_executing
        assert mock_bridge.notify_tool_executing.call_count == 2  # Called twice: once above, once here
        
        await agent.emit_subagent_started("SubAgent", "sub_123")
        # emit_subagent_started calls notify_custom
        assert mock_bridge.notify_custom.call_count == 1
        
        await agent.emit_subagent_completed("SubAgent", "sub_123", {"result": "done"}, 1500.0)
        # emit_subagent_completed also calls notify_custom
        assert mock_bridge.notify_custom.call_count == 2
        
    @pytest.mark.asyncio
    async def test_send_update_integration(self, mock_llm_manager):
        """Test _send_update method integration with user emitter."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="SendUpdateAgent"
        )
        
        # Create a user context
        user_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )
        agent.set_user_context(user_context)
        
        # Mock the emitter
        mock_emitter = mock_emitter_instance  # Initialize appropriate service
        mock_emitter.emit_agent_thinking = AsyncNone  # TODO: Use real service instance
        mock_emitter.emit_agent_completed = AsyncNone  # TODO: Use real service instance
        mock_emitter.emit_custom_event = AsyncNone  # TODO: Use real service instance
        
        # Mock the _get_user_emitter method to await asyncio.sleep(0)
    return our mock
        with patch.object(agent, '_get_user_emitter', return_value=mock_emitter):
            # Test processing update
            await agent._send_update("test_run", {
                "status": "processing",
                "message": "Processing request..."
            })
            mock_emitter.emit_agent_thinking.assert_called_once_with(
                "SendUpdateAgent", 
                {"agent_name": "SendUpdateAgent", "message": "Processing request..."}
            )
            
            # Test completion update
            mock_emitter.reset_mock()
            await agent._send_update("test_run", {
                "status": "completed",
                "message": "Task completed",
                "result": {"data": "test"}
            })
            mock_emitter.emit_agent_completed.assert_called_once_with(
                "SendUpdateAgent",
                {"result": {"data": "test"}, "execution_time_ms": None, "agent_name": "SendUpdateAgent"}
            )
            
            # Test custom status update
            mock_emitter.reset_mock()
            await agent._send_update("test_run", {
                "status": "custom_status",
                "message": "Custom message",
                "data": "custom_data"
            })
            mock_emitter.emit_custom_event.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_send_helper_methods(self, mock_llm_manager):
        """Test WebSocket helper methods for common update patterns."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="HelperMethodsAgent"
        )
        
        # Mock _send_update to track calls
        agent._send_update = AsyncNone  # TODO: Use real service instance
        
        # Test send_processing_update
        await agent.send_processing_update("test_run", "Processing data...")
        agent._send_update.assert_called_with("test_run", {
            "status": "processing",
            "message": "Processing data..."
        })
        
        # Test send_completion_update (normal)
        agent._send_update.reset_mock()
        await agent.send_completion_update("test_run", {"result": "success"}, fallback=False)
        agent._send_update.assert_called_with("test_run", {
            "status": "completed",
            "message": "Operation completed successfully",
            "result": {"result": "success"}
        })
        
        # Test send_completion_update (with fallback)
        agent._send_update.reset_mock()
        await agent.send_completion_update("test_run", {"result": "fallback"}, fallback=True)
        agent._send_update.assert_called_with("test_run", {
            "status": "completed_with_fallback",
            "message": "Operation completed with fallback method",
            "result": {"result": "fallback"}
        })


class TestBaseAgentHealthMonitoring:
    """Test health monitoring infrastructure (component aggregation, status reporting)."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        await asyncio.sleep(0)
    return llm
    
    def test_health_status_basic_components(self, mock_llm_manager):
        """Test basic health status reporting."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="HealthTestAgent"
        )
        
        health_status = agent.get_health_status()
        
        # Verify basic health components
        assert "agent_name" in health_status
        assert health_status["agent_name"] == "HealthTestAgent"
        assert "state" in health_status
        assert health_status["state"] == SubAgentLifecycle.PENDING.value
        assert "websocket_available" in health_status
        assert "overall_status" in health_status
        
    def test_health_status_with_reliability_components(self, mock_llm_manager):
        """Test health status with reliability components enabled."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityHealthAgent",
            enable_reliability=True
        )
        
        health_status = agent.get_health_status()
        
        # Verify reliability component is included
        assert "legacy_reliability" in health_status
        assert "overall_status" in health_status
        
        # Test circuit breaker status access
        circuit_status = agent.get_circuit_breaker_status()
        assert "status" in circuit_status
        
    def test_health_status_with_execution_engine(self, mock_llm_manager):
        """Test health status with execution engine enabled."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionHealthAgent",
            enable_reliability=True,  # Required for execution engine
            enable_execution_engine=True
        )
        
        health_status = agent.get_health_status()
        
        # Verify execution engine components are included
        assert "legacy_reliability" in health_status
        assert "modern_execution" in health_status
        assert "monitoring" in health_status
        assert "overall_status" in health_status
        
    def test_health_status_overall_determination(self, mock_llm_manager):
        """Test overall health status determination logic."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="OverallHealthAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Test health status structure and content
        health_status = agent.get_health_status()
        
        # Verify basic structure
        assert "agent_name" in health_status
        assert health_status["agent_name"] == "OverallHealthAgent"
        assert "state" in health_status
        assert "websocket_available" in health_status
        assert "uses_unified_reliability" in health_status
        
        # Verify it doesn't crash and returns reasonable data
        assert isinstance(health_status, dict)
        assert health_status["uses_unified_reliability"] == True


class TestBaseAgentPropertyInitialization:
    """Test property initialization patterns (optional features, configuration, SSOT access)."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        return llm
    
    @pytest.fixture
 def real_dependencies():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Mock all optional dependencies."""
        return {
            'tool_dispatcher': Mock(spec=ToolDispatcher),
            'redis_manager': Mock(spec=RedisManager)
        }
    
    def test_minimal_initialization(self, mock_llm_manager):
        """Test minimal agent initialization with only required parameters."""
        agent = MockBaseAgent(llm_manager=mock_llm_manager)
        
        # Verify default values
        assert agent.name == "BaseAgent"  # Default name
        assert agent.description == "This is the base sub-agent."
        assert agent.state == SubAgentLifecycle.PENDING
        assert agent.llm_manager == mock_llm_manager
        assert agent.correlation_id is not None
        
        # Verify optional features are disabled by default
        assert agent._enable_reliability is True  # Default enabled
        assert agent._enable_execution_engine is True  # Default enabled
        assert agent._enable_caching is False  # Default disabled
        
    def test_full_initialization_with_all_features(self, mock_llm_manager, mock_dependencies):
        """Test full initialization with all features enabled."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="FullFeaturesAgent",
            description="Agent with all features enabled",
            agent_id="agent_123",
            user_id="user_456",
            enable_reliability=True,
            enable_execution_engine=True,
            enable_caching=True,
            tool_dispatcher=mock_dependencies['tool_dispatcher'],
            redis_manager=mock_dependencies['redis_manager']
        )
        
        # Verify all features are initialized
        assert agent.name == "FullFeaturesAgent"
        assert agent.description == "Agent with all features enabled"
        assert agent.agent_id == "agent_123"
        # Note: user_id instance variables were removed - agents should use context.user_id instead
        
        # Verify infrastructure components
        assert agent.reliability_manager is not None
        assert agent.execution_engine is not None
        assert agent._execution_monitor is not None
        
        # Verify properties
        assert agent.tool_dispatcher is not None
        assert agent.redis_manager is not None
        assert agent.cache_ttl == 3600
        assert agent.max_retries == 3
        
    def test_selective_feature_initialization(self, mock_llm_manager, mock_dependencies):
        """Test selective feature initialization."""
        # Only reliability enabled
        agent1 = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityOnlyAgent",
            enable_reliability=True,
            enable_execution_engine=False,
            enable_caching=False
        )
        
        assert agent1.reliability_manager is not None
        assert agent1.execution_engine is None
        assert agent1._execution_monitor is not None  # Monitor always created for basic tracking
        
        # Only execution engine enabled (requires reliability)
        agent2 = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionOnlyAgent",
            enable_reliability=True,  # Required
            enable_execution_engine=True,
            enable_caching=False
        )
        
        assert agent2.reliability_manager is not None
        assert agent2.execution_engine is not None
        assert agent2._execution_monitor is not None
        
        # Only caching enabled
        agent3 = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="CachingOnlyAgent",
            enable_reliability=False,
            enable_execution_engine=False,
            enable_caching=True,
            redis_manager=mock_dependencies['redis_manager']
        )
        
        assert agent3.reliability_manager is None
        assert agent3.execution_engine is None
        assert agent3.redis_manager is not None
        
    def test_caching_initialization_requirements(self, mock_llm_manager):
        """Test caching infrastructure initialization requirements."""
    pass
        # Caching enabled but no Redis manager - should not initialize caching
        agent1 = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoCachingAgent",
            enable_caching=True,
            redis_manager=None
        )
        
        # Should not crash, but caching infrastructure won't be fully initialized
        assert agent1._enable_caching is True
        assert agent1.redis_manager is None
        
        # Caching enabled with Redis manager - should initialize properly
        mock_redis = Mock(spec=RedisManager)
        agent2 = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="WithCachingAgent",
            enable_caching=True,
            redis_manager=mock_redis
        )
        
        assert agent2._enable_caching is True
        assert agent2.redis_manager is not None
        
    def test_test_collection_mode_handling(self, mock_llm_manager):
        """Test special handling during test collection mode."""
        agent = MockBaseAgent(llm_manager=mock_llm_manager)
        
        # Should have disabled logging during test collection
        assert agent._subagent_logging_enabled is False
        
    def test_timing_collector_initialization(self, mock_llm_manager):
        """Test timing collector is properly initialized."""
    pass
        agent_name = "TimingTestAgent"
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name=agent_name
        )
        
        # Verify timing collector
        assert agent.timing_collector is not None
        assert agent.timing_collector.agent_name == agent_name
        
        # Test timing collection works
        agent.timing_collector.start_execution(agent.correlation_id)
        with agent.timing_collector.time_operation("test_op"):
            time.sleep(0.001)  # Minimal sleep
        tree = agent.timing_collector.complete_execution()
        
        assert tree is not None
        assert len(tree.entries) > 0


class TestBaseAgentEdgeCasesAndErrorScenarios:
    """Test edge cases, error scenarios, and boundary conditions."""
    
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        llm = Mock(spec=LLMManager)
        return llm
    
    def test_state_transition_validation_errors(self, mock_llm_manager):
        """Test invalid state transitions are properly rejected."""
    pass
        agent = MockBaseAgent(llm_manager=mock_llm_manager)
        
        # Valid transitions should work
        agent.set_state(SubAgentLifecycle.RUNNING)
        assert agent.state == SubAgentLifecycle.RUNNING
        
        agent.set_state(SubAgentLifecycle.COMPLETED)
        assert agent.state == SubAgentLifecycle.COMPLETED
        
        # Invalid transition should raise error
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent.set_state(SubAgentLifecycle.PENDING)  # Cannot go back to PENDING from COMPLETED
            
        # Terminal state (SHUTDOWN) should not allow transitions
        agent.set_state(SubAgentLifecycle.SHUTDOWN)
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent.set_state(SubAgentLifecycle.RUNNING)
            
    @pytest.mark.asyncio
    async def test_multiple_shutdown_idempotency(self, mock_llm_manager):
        """Test multiple shutdowns are idempotent and don't cause errors."""
        agent = MockBaseAgent(llm_manager=mock_llm_manager)
        
        # Set up some state
        agent.context = {"test": "data"}
        agent.set_state(SubAgentLifecycle.RUNNING)
        
        # First shutdown
        await agent.shutdown()
        assert agent.state == SubAgentLifecycle.SHUTDOWN
        assert agent.context == {}
        
        # Multiple subsequent shutdowns should be safe
        for _ in range(3):
            await agent.shutdown()
            assert agent.state == SubAgentLifecycle.SHUTDOWN
            
    @pytest.mark.asyncio
    async def test_shutdown_with_cleanup_errors(self, mock_llm_manager):
        """Test shutdown handles cleanup errors gracefully."""
    pass
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            enable_reliability=True
        )
        
        # Mock cleanup methods to raise errors
        with patch.object(agent.timing_collector, 'complete_execution', side_effect=Exception("Cleanup error")):
            with patch.object(agent.reliability_manager, 'reset_health_tracking', side_effect=Exception("Health cleanup error")):
                # Should not raise exception despite cleanup errors
                await agent.shutdown()
                assert agent.state == SubAgentLifecycle.SHUTDOWN
                
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, mock_llm_manager):
        """Test WebSocket errors are handled gracefully."""
        agent = MockBaseAgent(llm_manager=mock_llm_manager)
        
        # Mock _send_update to raise exception
        with patch.object(agent, '_send_update', side_effect=Exception("WebSocket error")):
            # Should not raise exception
            try:
                await agent.send_processing_update("test_run", "Processing...")
            except Exception:
                pytest.fail("WebSocket errors should be handled gracefully")
                
    def test_configuration_error_resilience(self, mock_llm_manager):
        """Test agent handles configuration errors gracefully."""
    pass
        # Mock agent_config to have missing attributes
        with patch('netra_backend.app.agents.base_agent.agent_config') as mock_config:
            # Missing timeout attribute
            mock_config.timeout = None
            mock_config.retry = retry_instance  # Initialize appropriate service
            mock_config.retry.max_retries = 3
            mock_config.retry.base_delay = 1.0
            mock_config.retry.max_delay = 30.0
            
            # Should still initialize successfully with defaults
            agent = MockBaseAgent(
                llm_manager=mock_llm_manager,
                enable_reliability=True
            )
            
            assert agent.reliability_manager is not None
            
    def test_concurrent_access_safety(self, mock_llm_manager):
        """Test agent properties are safe for concurrent access."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Multiple threads accessing properties should be safe
        import threading
        
        results = []
        errors = []
        
        def access_properties():
            try:
                # Access various properties
                _ = agent.reliability_manager
                _ = agent.execution_engine
                _ = agent.get_health_status()
                _ = agent.get_circuit_breaker_status()
                results.append("success")
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_properties)
            threads.append(thread)
            
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 10
    pass