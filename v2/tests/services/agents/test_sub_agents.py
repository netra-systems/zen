import pytest
from unittest.mock import MagicMock, AsyncMock
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.schemas import RequestModel, Settings
from app.llm.llm_manager import LLMManager

@pytest.fixture
def mock_llm_manager():
    mock = MagicMock(spec=LLMManager)
    mock.arun = AsyncMock()
    mock.ask_llm = AsyncMock(return_value='{}')
    return mock

@pytest.fixture
def request_model():
    return RequestModel(
        id="test_run",
        user_id="test_user",
        query="Test message",
        workloads=[]
    )

@pytest.mark.asyncio
async def test_triage_sub_agent(mock_llm_manager, request_model):
    mock_llm_manager.ask_llm.return_value = '{"category": "Data Analysis"}'
    agent = TriageSubAgent(mock_llm_manager)
    input_data = {"request": request_model.model_dump()}
    result = await agent.run(input_data, "test_run", False)
    assert "triage_result" in result
    assert result["triage_result"]["category"] == "Data Analysis"

@pytest.mark.asyncio
async def test_data_sub_agent(mock_llm_manager, request_model):
    mock_llm_manager.ask_llm.return_value = '{"data": "some data"}'
    agent = DataSubAgent(mock_llm_manager)
    input_data = {"request": request_model.model_dump(), "triage_result": {"category": "Data Analysis"}}
    result = await agent.run(input_data, "test_run", False)
    assert "data_result" in result

@pytest.mark.asyncio
async def test_optimizations_core_sub_agent(mock_llm_manager, request_model):
    mock_llm_manager.ask_llm.return_value = '{"optimizations": ["optimization 1"]}'
    agent = OptimizationsCoreSubAgent(mock_llm_manager)
    input_data = {"request": request_model.model_dump(), "data_result": {"data": "some data"}}
    result = await agent.run(input_data, "test_run", False)
    assert "optimizations_result" in result

@pytest.mark.asyncio
async def test_actions_to_meet_goals_sub_agent(mock_llm_manager, request_model):
    mock_llm_manager.ask_llm.return_value = '{"action_plan": ["action 1"]}'
    agent = ActionsToMeetGoalsSubAgent(mock_llm_manager)
    input_data = {"request": request_model.model_dump(), "optimizations_result": {"optimizations": ["optimization 1"]}}
    result = await agent.run(input_data, "test_run", False)
    assert "action_plan_result" in result

@pytest.mark.asyncio
async def test_reporting_sub_agent(mock_llm_manager, request_model):
    mock_llm_manager.ask_llm.return_value = '{"report": "some report"}'
    agent = ReportingSubAgent(mock_llm_manager)
    input_data = {"request": request_model.model_dump(), "action_plan_result": {"action_plan": ["action 1"]}}
    result = await agent.run(input_data, "test_run", False)
    assert "report_result" in result