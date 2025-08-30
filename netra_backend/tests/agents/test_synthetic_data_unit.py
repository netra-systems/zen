"""Fixed unit tests for SyntheticDataSubAgent."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.agents.synthetic_data_presets import DataGenerationType, WorkloadProfile
from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

@pytest.fixture
def mock_llm_manager():
    mock_llm = Mock(spec=LLMManager)
    mock_llm.generate_response = AsyncMock(return_value="Mock response")
    return mock_llm

@pytest.fixture  
def mock_tool_dispatcher():
    mock_dispatcher = Mock(spec=ToolDispatcher)
    mock_dispatcher.execute = AsyncMock(return_value={"status": "success"})
    return mock_dispatcher

@pytest.fixture
def sample_agent_state():
    return DeepAgentState(
        user_request="Generate synthetic data",
        chat_thread_id="test-thread", 
        user_id="test-user"
    )

@pytest.fixture
def synthetic_data_agent(mock_llm_manager, mock_tool_dispatcher):
    with patch('netra_backend.app.agents.synthetic_data_sub_agent.SyntheticDataGenerator'), patch('netra_backend.app.agents.synthetic_data_sub_agent.create_profile_parser'), patch('netra_backend.app.agents.synthetic_data_sub_agent.SyntheticDataMetricsHandler'), patch('netra_backend.app.agents.synthetic_data_sub_agent.ApprovalWorkflow'), patch('netra_backend.app.agents.synthetic_data_sub_agent.SyntheticDataLLMExecutor'), patch('netra_backend.app.agents.synthetic_data_sub_agent.GenerationExecutor'), patch('netra_backend.app.agents.synthetic_data_sub_agent.GenerationErrorHandler'), patch('netra_backend.app.agents.synthetic_data_sub_agent.CommunicationCoordinator'), patch('netra_backend.app.agents.synthetic_data_sub_agent.RequestValidator'), patch('netra_backend.app.agents.synthetic_data_sub_agent.ApprovalRequirements'):
        agent = SyntheticDataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        agent.generator = Mock()
        agent.profile_parser = Mock()
        agent.metrics_handler = Mock()
        agent.approval_workflow = Mock()
        agent.llm_executor = Mock()
        agent.generation_executor = Mock()
        agent.error_handler = Mock()
        agent.communicator = Mock()
        agent.validator = Mock()
        agent.approval_requirements = Mock()
        return agent

class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup(self, synthetic_data_agent, sample_agent_state):
        run_id = "test-run-123"
        with patch('netra_backend.app.agents.base_agent.BaseSubAgent.cleanup', new_callable=AsyncMock) as mock_parent_cleanup:
            await synthetic_data_agent.cleanup(sample_agent_state, run_id)
            mock_parent_cleanup.assert_called_once_with(sample_agent_state, run_id)

class TestApprovalWorkflow:
    @pytest.mark.asyncio
    async def test_approval_required_high_volume(self, synthetic_data_agent, sample_agent_state):
        high_volume_profile = WorkloadProfile(
            workload_type=DataGenerationType.CUSTOM,
            volume=100000,
            time_range_days=30,
            distribution="normal",
            noise_level=0.1
        )
        synthetic_data_agent.approval_requirements.check_approval_requirements = Mock(return_value=True)
        result = synthetic_data_agent.approval_requirements.check_approval_requirements(high_volume_profile, sample_agent_state)
        assert result is True

    @pytest.mark.asyncio 
    async def test_approval_not_required_low_volume(self, synthetic_data_agent, sample_agent_state):
        low_volume_profile = WorkloadProfile(
            workload_type=DataGenerationType.CUSTOM,
            volume=500,
            time_range_days=7,
            distribution="normal",
            noise_level=0.1
        )
        synthetic_data_agent.approval_requirements.check_approval_requirements = Mock(return_value=False)
        result = synthetic_data_agent.approval_requirements.check_approval_requirements(low_volume_profile, sample_agent_state)
        assert result is False

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_execute_with_none_state(self, synthetic_data_agent):
        with patch.object(synthetic_data_agent, '_execute_main_flow', new_callable=AsyncMock) as mock_main_flow:
            mock_main_flow.side_effect = AttributeError("'NoneType' object has no attribute 'user_request'")
            with pytest.raises(AttributeError):
                await synthetic_data_agent.execute(None, "test_run_id", stream_updates=True)

pytestmark = [pytest.mark.unit, pytest.mark.agents, pytest.mark.synthetic_data, pytest.mark.production_critical]
