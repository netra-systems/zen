import pytest
from unittest.mock import MagicMock, AsyncMock
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.data_sub_agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.schemas import AnalysisRequest, RequestModel, Settings
from app.llm.llm_manager import LLMManager

@pytest.fixture
def mock_llm_manager():
    mock = MagicMock(spec=LLMManager)
    mock.arun = AsyncMock()
    mock.ask_llm = AsyncMock()
    return mock

@pytest.fixture
def analysis_request():
    return AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(
            id="test_run",
            user_id="test_user",
            query="Test message",
            workloads=[]
        )
    )

@pytest.mark.asyncio
async def test_triage_sub_agent(mock_llm_manager, analysis_request):
    mock_llm_manager.arun.return_value = '{"category": "Data Analysis", "justification": "The user wants to analyze data."}'
    agent = TriageSubAgent(mock_llm_manager)
    state = {
        "analysis_request": analysis_request,
        "messages": [],
        "run_id": "test_run",
        "stream_updates": False,
        "current_agent": "TriageSubAgent",
        "tool_calls": None,
    }
    result = await agent.run(state, "test_run", False)
    assert result["current_agent"] == "DataSubAgent"
    assert result["triage_result"]["category"] == "Data Analysis"

@pytest.mark.asyncio
async def test_data_sub_agent(mock_llm_manager, analysis_request):
    agent = DataSubAgent(mock_llm_manager)
    state = {
        "analysis_request": analysis_request,
        "messages": [],
        "run_id": "test_run",
        "stream_updates": False,
        "current_agent": "DataSubAgent",
        "tool_calls": None,
        "triage_result": {"category": "Data Analysis"}
    }
    result = await agent.run(state, "test_run", False)
    assert result["current_agent"] == "OptimizationsCoreSubAgent"
    assert "processed_data" in result

@pytest.mark.asyncio
async def test_optimizations_core_sub_agent(mock_llm_manager, analysis_request):
    agent = OptimizationsCoreSubAgent(mock_llm_manager)
    state = {
        "analysis_request": analysis_request,
        "messages": [],
        "run_id": "test_run",
        "stream_updates": False,
        "current_agent": "OptimizationsCoreSubAgent",
        "tool_calls": None,
        "processed_data": {"summary": "some data"}
    }
    result = await agent.run(state, "test_run", False)
    assert result["current_agent"] == "ActionsToMeetGoalsSubAgent"
    assert "optimizations" in result

@pytest.mark.asyncio
async def test_actions_to_meet_goals_sub_agent(mock_llm_manager, analysis_request):
    agent = ActionsToMeetGoalsSubAgent(mock_llm_manager)
    state = {
        "analysis_request": analysis_request,
        "messages": [],
        "run_id": "test_run",
        "stream_updates": False,
        "current_agent": "ActionsToMeetGoalsSubAgent",
        "tool_calls": None,
        "optimizations": ["some optimization"]
    }
    result = await agent.run(state, "test_run", False)
    assert result["current_agent"] == "ReportingSubAgent"
    assert "action_plan" in result

@pytest.mark.asyncio
async def test_reporting_sub_agent(mock_llm_manager, analysis_request):
    agent = ReportingSubAgent(mock_llm_manager)
    state = {
        "analysis_request": analysis_request,
        "messages": [],
        "run_id": "test_run",
        "stream_updates": False,
        "current_agent": "ReportingSubAgent",
        "tool_calls": None,
        "action_plan": {"title": "some plan"}
    }
    result = await agent.run(state, "test_run", False)
    assert result["current_agent"] == "__end__"
    assert "report" in result
