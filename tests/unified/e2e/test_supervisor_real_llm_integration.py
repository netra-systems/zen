"""E2E Tests for Supervisor with Real LLM Integration.

Tests complete supervisor workflow with actual LLM calls.
Business Value: Validates end-to-end AI optimization value creation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from netra_backend.app.agents.supervisor_agent_modern import ModernSupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import get_config


@pytest.mark.real_llm
@pytest.mark.e2e
class TestSupervisorE2EWithRealLLM:
    """E2E tests using real LLM integration."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        config = get_config()
        config.OPENAI_API_KEY = "test-key"  # Will use mock in tests
        return config
    
    @pytest.fixture
    def llm_manager(self, config):
        """LLM manager for testing."""
        return LLMManager(config)
    
    @pytest.fixture
    def mock_dependencies(self, llm_manager):
        """Mock dependencies for supervisor."""
        return {
            "db_session": AsyncMock(),
            "llm_manager": llm_manager,
            "websocket_manager": AsyncMock(),
            "tool_dispatcher": Mock()
        }
    
    @pytest.fixture
    def supervisor(self, mock_dependencies):
        """Modern supervisor agent instance."""
        return ModernSupervisorAgent(
            mock_dependencies["db_session"],
            mock_dependencies["llm_manager"],
            mock_dependencies["websocket_manager"],
            mock_dependencies["tool_dispatcher"]
        )
    
    @pytest.fixture
    def optimization_request_state(self):
        """Sample state for AI optimization request."""
        state = DeepAgentState()
        state.user_request = "I need help optimizing my AI costs. My current monthly spend is $50,000 on GPT-4 calls and I'm seeing high latency."
        state.user_id = "enterprise_user_123"
        state.chat_thread_id = "thread_opt_456"
        state.conversation_history = [
            {"role": "user", "content": state.user_request}
        ]
        return state
    
    @pytest.mark.asyncio
    async def test_complete_optimization_workflow_e2e(self, supervisor, optimization_request_state):
        """Test complete optimization workflow end-to-end."""
        run_id = "e2e_test_run_001"
        
        # Execute the supervisor workflow
        result_state = await supervisor.run(
            optimization_request_state.user_request,
            optimization_request_state.chat_thread_id,
            optimization_request_state.user_id,
            run_id
        )
        
        # Validate workflow completion
        assert result_state is not None
        assert hasattr(result_state, 'user_request')
        
        # Validate health status after execution
        health = supervisor.get_health_status()
        assert health["supervisor_health"]["overall_healthy"] is True
        
        # Validate metrics were recorded
        metrics = supervisor.get_performance_metrics()
        assert metrics["metrics"]["total_workflows"] >= 1
    
    @pytest.mark.asyncio
    async def test_supervisor_agent_lifecycle_e2e(self, supervisor, optimization_request_state):
        """Test supervisor agent lifecycle management."""
        run_id = "lifecycle_test_002"
        
        # Test execution with stream updates
        await supervisor.execute(
            optimization_request_state, 
            run_id, 
            stream_updates=True
        )
        
        # Validate lifecycle tracking
        active_contexts = supervisor.lifecycle_manager.get_active_contexts()
        # Context should be cleaned up after execution
        assert run_id not in active_contexts
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_protection_e2e(self, supervisor):
        """Test circuit breaker protection in E2E scenario."""
        # Create invalid state to trigger failures
        invalid_state = DeepAgentState()
        # Missing required fields to trigger validation errors
        
        run_id = "circuit_breaker_test_003"
        
        # This should trigger circuit breaker protection
        with pytest.raises(Exception):  # ValidationError expected
            await supervisor.execute(invalid_state, run_id, stream_updates=False)
        
        # Validate circuit breaker status
        cb_status = supervisor.get_circuit_breaker_status()
        assert "supervisor" in cb_status
    
    @pytest.mark.asyncio
    async def test_observability_e2e(self, supervisor, optimization_request_state):
        """Test observability features in E2E scenario."""
        run_id = "observability_test_004"
        
        # Execute workflow
        await supervisor.execute(
            optimization_request_state,
            run_id,
            stream_updates=True
        )
        
        # Validate observability data
        metrics = supervisor.get_performance_metrics()
        assert "timestamp" in metrics
        assert "metrics" in metrics
        assert metrics["metrics"]["total_workflows"] >= 1
        
        # Validate health status
        health = supervisor.get_health_status()
        assert "observability_metrics" in health
        assert "registered_agents" in health
    
    @pytest.mark.asyncio
    async def test_websocket_updates_e2e(self, supervisor, optimization_request_state, mock_dependencies):
        """Test WebSocket updates during E2E execution."""
        run_id = "websocket_test_005"
        await supervisor.execute(optimization_request_state, run_id, stream_updates=True)
        websocket_manager = mock_dependencies["websocket_manager"]
        websocket_manager.send_agent_update.assert_called()
        calls = websocket_manager.send_agent_update.call_args_list
        assert len(calls) > 0
        self._validate_websocket_call_structure(calls, run_id)
    
    def _validate_websocket_call_structure(self, calls, run_id):
        """Validate WebSocket call structure and arguments."""
        for call in calls:
            args, kwargs = call
            assert len(args) == 3  # run_id, agent_name, update
            assert args[0] == run_id  # run_id
            assert isinstance(args[1], str)  # agent_name
            assert isinstance(args[2], dict)  # update data
    
    def test_workflow_definition_compliance(self, supervisor):
        """Test workflow definition compliance with unified spec."""
        definition = supervisor.workflow_orchestrator.get_workflow_definition()
        
        # Validate standard workflow agents are present
        agent_names = [step["agent_name"] for step in definition]
        expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
        
        for agent in expected_agents:
            assert agent in agent_names, f"Missing required agent: {agent}"
        
        # Validate step structure
        for step in definition:
            assert "agent_name" in step
            assert "step_type" in step
            assert "order" in step
            assert "metadata" in step
    
    def test_agent_registry_initialization(self, supervisor):
        """Test agent registry proper initialization."""
        registry = supervisor.agent_registry
        
        # Validate core agents are registered
        assert "triage" in registry.agents
        assert "data" in registry.agents
        assert "optimization" in registry.agents
        assert "actions" in registry.agents
        assert "reporting" in registry.agents
        
        # Validate WebSocket manager is set
        for agent in registry.agents.values():
            assert hasattr(agent, 'websocket_manager')
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_e2e(self, supervisor):
        """Test error handling and recovery in E2E scenario."""
        # Create problematic state
        problematic_state = DeepAgentState()
        problematic_state.user_request = "" # Empty request to trigger validation
        problematic_state.user_id = "test_user"
        problematic_state.chat_thread_id = "test_thread"
        
        run_id = "error_recovery_test_006"
        
        # This should handle errors gracefully
        with pytest.raises(Exception):  # ValidationError expected
            await supervisor.execute(problematic_state, run_id, stream_updates=False)
        
        # Validate error metrics were recorded
        metrics = supervisor.get_performance_metrics()
        assert "error_counts_by_agent" in metrics["metrics"]
    
    @pytest.mark.asyncio
    async def test_performance_under_load_e2e(self, supervisor, optimization_request_state):
        """Test supervisor performance under concurrent load."""
        tasks = self._create_concurrent_execution_tasks(supervisor, optimization_request_state)
        await asyncio.gather(*tasks, return_exceptions=True)
        metrics = supervisor.get_performance_metrics()
        assert metrics["metrics"]["total_workflows"] >= 3
        self._validate_performance_percentiles(metrics)
    
    def _create_concurrent_execution_tasks(self, supervisor, optimization_request_state):
        """Create multiple concurrent execution tasks for load testing."""
        tasks = []
        for i in range(3):  # Light load for E2E testing
            run_id = f"load_test_{i:03d}"
            task = supervisor.execute(optimization_request_state, run_id, stream_updates=False)
            tasks.append(task)
        return tasks
    
    def _validate_performance_percentiles(self, metrics):
        """Validate performance percentiles are calculated correctly."""
        assert "performance_percentiles" in metrics
        percentiles = metrics["performance_percentiles"]
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
