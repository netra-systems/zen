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
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from netra_backend.app.agents.base_agent import BaseAgent
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
        super().__init__(*args, **kwargs)
        self.core_logic_calls = 0
        self.validation_calls = 0
        self.should_fail_validation = False
        self.should_fail_execution = False
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        self.validation_calls += 1
        return not self.should_fail_validation
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        self.core_logic_calls += 1
        if self.should_fail_execution:
            raise ValueError("Simulated execution failure")
        return {
            "status": "success",
            "message": "Mock execution completed",
            "context_run_id": context.run_id,
            "agent_name": context.agent_name
        }


class TestBaseAgentReliabilityInfrastructure:
    """Test reliability management infrastructure (circuit breakers, retries, health)."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value="Mock LLM response")
        return llm
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher for testing."""
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock(return_value={"result": "Mock tool result"})
        return dispatcher
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis manager for testing."""
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
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
        assert agent._reliability_manager is not None
        assert isinstance(agent._reliability_manager, ReliabilityManager)
        assert agent._legacy_reliability is not None
        
        # Verify property access
        assert agent.reliability_manager is not None
        assert agent.legacy_reliability is not None
        
        # Verify circuit breaker configuration
        circuit_status = agent.get_circuit_breaker_status()
        assert "status" in circuit_status
        
    def test_reliability_infrastructure_initialization_disabled(self, mock_llm_manager):
        """Test reliability infrastructure is not initialized when disabled."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoReliabilityAgent",
            enable_reliability=False
        )
        
        # Verify reliability infrastructure is not initialized
        assert agent._enable_reliability is False
        assert agent._reliability_manager is None
        assert agent._legacy_reliability is None
        
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
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityFailureAgent",
            enable_reliability=True,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Simulated failure {call_count}")
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
    async def test_execute_with_reliability_with_fallback(self, mock_llm_manager, mock_tool_dispatcher):
        """Test fallback execution when primary operation fails."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ReliabilityFallbackAgent",
            enable_reliability=True,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        async def failing_operation():
            raise ValueError("Primary operation always fails")
        
        async def fallback_operation():
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
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoReliabilityAgent",
            enable_reliability=False
        )
        
        async def dummy_operation():
            return "dummy"
        
        with pytest.raises(RuntimeError, match="Reliability not enabled"):
            asyncio.run(agent.execute_with_reliability(
                operation=dummy_operation,
                operation_name="test_operation"
            ))


class TestBaseAgentExecutionEngine:
    """Test execution engine patterns (modern execution, monitoring, context handling)."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value="Mock response")
        return llm
    
    def test_execution_engine_initialization_enabled(self, mock_llm_manager):
        """Test execution engine is properly initialized when enabled."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionEngineAgent",
            enable_execution_engine=True,
            enable_reliability=True  # Required for execution engine
        )
        
        # Verify execution infrastructure is initialized
        assert agent._enable_execution_engine is True
        assert agent._execution_engine is not None
        assert isinstance(agent._execution_engine, BaseExecutionEngine)
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
        assert agent._execution_engine is None
        assert agent._execution_monitor is None
        
        # Verify property access returns None
        assert agent.execution_engine is None
        assert agent.execution_monitor is None
        
    @pytest.mark.asyncio
    async def test_execute_modern_success(self, mock_llm_manager):
        """Test successful modern execution pattern."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ModernExecutionAgent",
            enable_reliability=True,
            enable_execution_engine=True
        )
        
        # Create test state
        state = DeepAgentState()
        state.user_request = "Test user request"
        state.thread_id = "test_thread_123"
        state.user_id = "test_user_456"
        
        # Execute using modern pattern
        result = await agent.execute_modern(
            state=state,
            run_id="test_run_789",
            stream_updates=True
        )
        
        # Verify execution result
        assert isinstance(result, ExecutionResult)
        assert result.success is True
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
        
        result = await agent.execute_modern(
            state=state,
            run_id="validation_fail_run"
        )
        
        # Execution should fail due to validation
        assert result.success is False
        assert result.error is not None
        assert agent.validation_calls == 1
        assert agent.core_logic_calls == 0  # Should not reach core logic
        
    @pytest.mark.asyncio
    async def test_execute_modern_execution_failure(self, mock_llm_manager):
        """Test modern execution with core logic failure."""
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
        
        result = await agent.execute_modern(
            state=state,
            run_id="execution_fail_run"
        )
        
        # Execution should fail in core logic
        assert result.success is False
        assert result.error is not None
        assert "Simulated execution failure" in str(result.error)
        assert agent.validation_calls == 1
        assert agent.core_logic_calls == 1
        
    def test_execute_modern_not_enabled_error(self, mock_llm_manager):
        """Test error when trying to use modern execution without enabling it."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="NoModernExecutionAgent",
            enable_execution_engine=False
        )
        
        state = DeepAgentState()
        
        with pytest.raises(RuntimeError, match="Modern execution engine not enabled"):
            asyncio.run(agent.execute_modern(state, "test_run"))


class TestBaseAgentWebSocketInfrastructure:
    """Test WebSocket infrastructure (event emission, bridge integration, update methods)."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        return llm
    
    @pytest.fixture
    def mock_websocket_bridge(self):
        """Mock WebSocket bridge for testing."""
        bridge = Mock()
        bridge.notify_agent_thinking = AsyncMock()
        bridge.notify_agent_completed = AsyncMock()
        bridge.notify_custom = AsyncMock()
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
        mock_bridge = Mock()
        agent.set_websocket_bridge(mock_bridge, "test_run_123")
        
        # Verify WebSocket context is available
        assert agent.has_websocket_context()
        
    @pytest.mark.asyncio
    async def test_websocket_event_emission_methods(self, mock_llm_manager):
        """Test all WebSocket event emission methods."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="WebSocketEventsAgent"
        )
        
        # Mock the WebSocket bridge
        mock_bridge = Mock()
        mock_bridge.emit_agent_started = AsyncMock()
        mock_bridge.emit_thinking = AsyncMock()
        mock_bridge.emit_tool_executing = AsyncMock()
        mock_bridge.emit_tool_completed = AsyncMock()
        mock_bridge.emit_agent_completed = AsyncMock()
        mock_bridge.emit_progress = AsyncMock()
        mock_bridge.emit_error = AsyncMock()
        mock_bridge.emit_tool_started = AsyncMock()
        mock_bridge.emit_subagent_started = AsyncMock()
        mock_bridge.emit_subagent_completed = AsyncMock()
        
        agent._websocket_adapter._websocket_bridge = mock_bridge
        agent._websocket_adapter._run_id = "test_run"
        agent._websocket_adapter._agent_name = "WebSocketEventsAgent"
        
        # Test all emission methods
        await agent.emit_agent_started("Agent started message")
        mock_bridge.emit_agent_started.assert_called_once()
        
        await agent.emit_thinking("Thinking about the problem", step_number=1)
        mock_bridge.emit_thinking.assert_called_once()
        
        await agent.emit_tool_executing("test_tool", {"param": "value"})
        mock_bridge.emit_tool_executing.assert_called_once()
        
        await agent.emit_tool_completed("test_tool", {"result": "success"})
        mock_bridge.emit_tool_completed.assert_called_once()
        
        await agent.emit_agent_completed({"final_result": "completed"})
        mock_bridge.emit_agent_completed.assert_called_once()
        
        await agent.emit_progress("50% complete", is_complete=False)
        mock_bridge.emit_progress.assert_called_once()
        
        await agent.emit_error("Test error", "ValidationError", {"details": "test"})
        mock_bridge.emit_error.assert_called_once()
        
        # Test backward compatibility methods
        await agent.emit_tool_started("test_tool", {"param": "value"})
        mock_bridge.emit_tool_started.assert_called_once()
        
        await agent.emit_subagent_started("SubAgent", "sub_123")
        mock_bridge.emit_subagent_started.assert_called_once()
        
        await agent.emit_subagent_completed("SubAgent", "sub_123", {"result": "done"}, 1500.0)
        mock_bridge.emit_subagent_completed.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('netra_backend.app.agents.base_agent.get_agent_websocket_bridge')
    async def test_send_update_integration(self, mock_get_bridge, mock_llm_manager):
        """Test _send_update method integration with AgentWebSocketBridge."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="SendUpdateAgent"
        )
        
        # Mock the bridge
        mock_bridge = Mock()
        mock_bridge.notify_agent_thinking = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()
        mock_bridge.notify_custom = AsyncMock()
        mock_get_bridge.return_value = mock_bridge
        
        # Test processing update
        await agent._send_update("test_run", {
            "status": "processing",
            "message": "Processing request..."
        })
        mock_bridge.notify_agent_thinking.assert_called_once_with(
            "test_run", "SendUpdateAgent", "Processing request..."
        )
        
        # Test completion update
        mock_bridge.reset_mock()
        await agent._send_update("test_run", {
            "status": "completed",
            "message": "Task completed",
            "result": {"data": "test"}
        })
        mock_bridge.notify_agent_completed.assert_called_once_with(
            "test_run", "SendUpdateAgent", result={"data": "test"}, execution_time_ms=None
        )
        
        # Test custom status update
        mock_bridge.reset_mock()
        await agent._send_update("test_run", {
            "status": "custom_status",
            "message": "Custom message",
            "data": "custom_data"
        })
        mock_bridge.notify_custom.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_send_helper_methods(self, mock_llm_manager):
        """Test WebSocket helper methods for common update patterns."""
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="HelperMethodsAgent"
        )
        
        # Mock _send_update to track calls
        agent._send_update = AsyncMock()
        
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
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        return llm
    
    def test_health_status_basic_components(self, mock_llm_manager):
        """Test basic health status reporting."""
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
        
        # Mock healthy components
        with patch.object(agent._legacy_reliability, 'get_health_status') as mock_legacy_health:
            with patch.object(agent._execution_engine, 'get_health_status') as mock_execution_health:
                # Test healthy state
                mock_legacy_health.return_value = {"overall_health": "healthy"}
                mock_execution_health.return_value = {"monitor": {"status": "healthy"}}
                
                health_status = agent.get_health_status()
                assert health_status["overall_status"] == "healthy"
                
                # Test degraded state (legacy unhealthy)
                mock_legacy_health.return_value = {"overall_health": "degraded"}
                health_status = agent.get_health_status()
                assert health_status["overall_status"] == "degraded"
                
                # Test degraded state (execution unhealthy)
                mock_legacy_health.return_value = {"overall_health": "healthy"}
                mock_execution_health.return_value = {"monitor": {"status": "degraded"}}
                health_status = agent.get_health_status()
                assert health_status["overall_status"] == "degraded"


class TestBaseAgentPropertyInitialization:
    """Test property initialization patterns (optional features, configuration, SSOT access)."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        return llm
    
    @pytest.fixture
    def mock_dependencies(self):
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
        assert agent._user_id == "user_456"
        
        # Verify infrastructure components
        assert agent._reliability_manager is not None
        assert agent._execution_engine is not None
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
        
        assert agent1._reliability_manager is not None
        assert agent1._execution_engine is None
        assert agent1._execution_monitor is None
        
        # Only execution engine enabled (requires reliability)
        agent2 = MockBaseAgent(
            llm_manager=mock_llm_manager,
            name="ExecutionOnlyAgent",
            enable_reliability=True,  # Required
            enable_execution_engine=True,
            enable_caching=False
        )
        
        assert agent2._reliability_manager is not None
        assert agent2._execution_engine is not None
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
        
        assert agent3._reliability_manager is None
        assert agent3._execution_engine is None
        assert agent3.redis_manager is not None
        
    def test_caching_initialization_requirements(self, mock_llm_manager):
        """Test caching infrastructure initialization requirements."""
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
        
    @patch.dict('os.environ', {'TEST_COLLECTION_MODE': '1'})
    def test_test_collection_mode_handling(self, mock_llm_manager):
        """Test special handling during test collection mode."""
        agent = MockBaseAgent(llm_manager=mock_llm_manager)
        
        # Should have disabled logging during test collection
        assert agent._subagent_logging_enabled is False
        
    def test_timing_collector_initialization(self, mock_llm_manager):
        """Test timing collector is properly initialized."""
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
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        return llm
    
    def test_state_transition_validation_errors(self, mock_llm_manager):
        """Test invalid state transitions are properly rejected."""
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
        agent = MockBaseAgent(
            llm_manager=mock_llm_manager,
            enable_reliability=True
        )
        
        # Mock cleanup methods to raise errors
        with patch.object(agent.timing_collector, 'complete_execution', side_effect=Exception("Cleanup error")):
            with patch.object(agent._reliability_manager, 'reset_health_tracking', side_effect=Exception("Health cleanup error")):
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
        # Mock agent_config to have missing attributes
        with patch('netra_backend.app.agents.base_agent.agent_config') as mock_config:
            # Missing timeout attribute
            mock_config.timeout = None
            mock_config.retry = Mock()
            mock_config.retry.max_retries = 3
            mock_config.retry.base_delay = 1.0
            mock_config.retry.max_delay = 30.0
            
            # Should still initialize successfully with defaults
            agent = MockBaseAgent(
                llm_manager=mock_llm_manager,
                enable_reliability=True
            )
            
            assert agent._reliability_manager is not None
            
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