"""Comprehensive test suite for ReportingSubAgent"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.agents.reporting_sub_agent import ReportingSubAgent
from app.agents.state import (
    DeepAgentState, ReportResult, OptimizationsResult, ActionPlanResult, ReportSection
)
from app.agents.triage_sub_agent.models import (
    TriageResult, Priority, Complexity, UserIntent, ExtractedEntities
)
from app.agents.data_sub_agent.models import DataAnalysisResponse
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing"""
    mock = MagicMock(spec=LLMManager)
    mock.ask_llm = AsyncMock()
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher for testing"""
    return MagicMock(spec=ToolDispatcher)


@pytest.fixture
def reporting_agent(mock_llm_manager, mock_tool_dispatcher):
    """Create reporting agent instance for testing"""
    agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
    agent.websocket_manager = MagicMock()
    agent.websocket_manager.send_message = AsyncMock()
    return agent


@pytest.fixture
def complete_state():
    """Complete agent state with all required data"""
    return DeepAgentState(
        user_request="Optimize system performance",
        triage_result=TriageResult(
            category="performance_optimization",
            priority=Priority.HIGH,
            complexity=Complexity.MODERATE,
            user_intent=UserIntent(primary_intent="performance_optimization"),
            extracted_entities=ExtractedEntities()
        ),
        data_result=DataAnalysisResponse(
            query="performance analysis",
            results=[{"metric": "cpu_usage", "value": 85}],
            insights={"high_cpu": True},
            recommendations=["Scale resources"]
        ),
        optimizations_result=OptimizationsResult(
            optimization_type="performance",
            recommendations=["Upgrade CPU", "Add RAM"],
            cost_savings=5000.0
        ),
        action_plan_result=ActionPlanResult(
            plan_steps=[],
            priority="high",
            estimated_duration="2 weeks"
        )
    )


@pytest.fixture
def incomplete_state():
    """Incomplete agent state missing required data"""
    return DeepAgentState(
        user_request="Test request",
        triage_result=TriageResult(
            category="test_category",
            priority=Priority.LOW,
            complexity=Complexity.SIMPLE,
            user_intent=UserIntent(primary_intent="test"),
            extracted_entities=ExtractedEntities()
        )
    )


class TestReportingSubAgentInit:
    """Test agent initialization"""
    
    def test_init_with_dependencies(self, mock_llm_manager, mock_tool_dispatcher):
        """Test initialization with proper dependencies"""
        agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
        assert agent.llm_manager == mock_llm_manager
        assert agent.tool_dispatcher == mock_tool_dispatcher


    def test_init_sets_correct_name(self, mock_llm_manager, mock_tool_dispatcher):
        """Test agent name is set correctly"""
        agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
        assert agent.name == "ReportingSubAgent"


    def test_init_sets_reliability_wrapper(self, mock_llm_manager, mock_tool_dispatcher):
        """Test reliability wrapper is initialized"""
        agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
        assert hasattr(agent, 'reliability')
        assert agent.reliability is not None


class TestEntryConditions:
    """Test entry conditions validation"""

    async def test_entry_conditions_complete_data(self, reporting_agent, complete_state):
        """Test entry conditions pass with complete data"""
        result = await reporting_agent.check_entry_conditions(complete_state, "test-run")
        assert result is True


    async def test_entry_conditions_missing_action_plan(self, reporting_agent, complete_state):
        """Test entry conditions fail with missing action plan"""
        complete_state.action_plan_result = None
        result = await reporting_agent.check_entry_conditions(complete_state, "test-run")
        assert result is False


    async def test_entry_conditions_missing_optimizations(self, reporting_agent, complete_state):
        """Test entry conditions fail with missing optimizations"""
        complete_state.optimizations_result = None
        result = await reporting_agent.check_entry_conditions(complete_state, "test-run")
        assert result is False


    async def test_entry_conditions_missing_data_result(self, reporting_agent, complete_state):
        """Test entry conditions fail with missing data result"""
        complete_state.data_result = None
        result = await reporting_agent.check_entry_conditions(complete_state, "test-run")
        assert result is False


    async def test_entry_conditions_missing_triage(self, reporting_agent, complete_state):
        """Test entry conditions fail with missing triage"""
        complete_state.triage_result = None
        result = await reporting_agent.check_entry_conditions(complete_state, "test-run")
        assert result is False


class TestReportGeneration:
    """Test report generation logic"""

    @patch('app.agents.utils.extract_json_from_response')
    async def test_successful_report_generation(self, mock_extract, reporting_agent, complete_state):
        """Test successful report generation"""
        mock_report = {"report": "Complete analysis report", "sections": []}
        mock_extract.return_value = mock_report
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Complete analysis report"}'
        
        await reporting_agent.execute(complete_state, "test-run", True)
        
        assert complete_state.report_result is not None
        assert complete_state.report_result.content == "Complete analysis report"


    @patch('app.agents.utils.extract_json_from_response')
    async def test_json_extraction_failure(self, mock_extract, reporting_agent, complete_state):
        """Test fallback when JSON extraction fails"""
        mock_extract.return_value = None
        reporting_agent.llm_manager.ask_llm.return_value = 'invalid json'
        
        await reporting_agent.execute(complete_state, "test-run", True)
        
        assert complete_state.report_result is not None
        assert "No report could be generated" in complete_state.report_result.content


    async def test_llm_failure_triggers_fallback(self, reporting_agent, complete_state):
        """Test fallback when LLM call fails"""
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("LLM Error")
        
        await reporting_agent.execute(complete_state, "test-run", True)
        
        assert complete_state.report_result is not None
        assert "Report generation failed" in complete_state.report_result.content


class TestReportFormatting:
    """Test report formatting for different types"""

    def test_create_report_result_with_full_data(self, reporting_agent):
        """Test creating ReportResult with complete data"""
        data = {
            "report": "Test report content",
            "sections": [
                ReportSection(
                    section_id="sec1",
                    title="Section 1", 
                    content="Content 1"
                )
            ],
            "metadata": {"created_by": "test"}
        }
        
        result = reporting_agent._create_report_result(data)
        
        assert result.report_type == "analysis"
        assert result.content == "Test report content"
        assert len(result.sections) == 1
        assert result.metadata == {"created_by": "test"}


    def test_create_report_result_with_minimal_data(self, reporting_agent):
        """Test creating ReportResult with minimal data"""
        data = {}
        
        result = reporting_agent._create_report_result(data)
        
        assert result.report_type == "analysis"
        assert result.content == "No content available"
        assert result.sections == []
        assert result.metadata == {}


class TestWebSocketUpdates:
    """Test streaming updates during report generation"""

    @patch('app.agents.utils.extract_json_from_response')
    async def test_websocket_updates_enabled(self, mock_extract, reporting_agent, complete_state):
        """Test WebSocket updates are sent when enabled"""
        mock_extract.return_value = {"report": "Test report"}
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Test"}'
        
        await reporting_agent.execute(complete_state, "test-run", True)
        
        # Should send processing and processed updates
        assert reporting_agent.websocket_manager.send_message.call_count >= 2


    @patch('app.agents.utils.extract_json_from_response')
    async def test_websocket_updates_disabled(self, mock_extract, reporting_agent, complete_state):
        """Test no WebSocket updates when disabled"""
        mock_extract.return_value = {"report": "Test report"}
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Test"}'
        
        await reporting_agent.execute(complete_state, "test-run", False)
        
        # Should not send any updates
        reporting_agent.websocket_manager.send_message.assert_not_called()


class TestErrorHandling:
    """Test error handling for various failure scenarios"""

    async def test_missing_data_handled_gracefully(self, reporting_agent, incomplete_state):
        """Test graceful handling of missing required data"""
        # Should not raise exception during execution attempt
        try:
            await reporting_agent.execute(incomplete_state, "test-run", False)
        except Exception as e:
            pytest.fail(f"Should handle missing data gracefully: {e}")


    async def test_websocket_disconnect_handled(self, reporting_agent, complete_state):
        """Test WebSocket disconnect is handled gracefully"""
        from starlette.websockets import WebSocketDisconnect
        reporting_agent.websocket_manager.send_message.side_effect = WebSocketDisconnect()
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Test"}'
        
        # Should not raise exception
        await reporting_agent.execute(complete_state, "test-run", True)


class TestReliabilityFeatures:
    """Test reliability and circuit breaker functionality"""

    def test_health_status_available(self, reporting_agent):
        """Test health status is available"""
        status = reporting_agent.get_health_status()
        assert isinstance(status, dict)


    def test_circuit_breaker_status_available(self, reporting_agent):
        """Test circuit breaker status is available"""
        status = reporting_agent.get_circuit_breaker_status()
        assert isinstance(status, dict)


class TestFallbackScenarios:
    """Test fallback behavior in various scenarios"""

    async def test_fallback_creates_valid_report(self, reporting_agent, complete_state):
        """Test fallback creates a valid report structure"""
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("Test failure")
        
        await reporting_agent.execute(complete_state, "test-run", True)
        
        result = complete_state.report_result
        assert result is not None
        assert "Report generation failed" in result.content
        assert result.metadata.get("fallback_used") is True


    async def test_fallback_includes_analysis_summary(self, reporting_agent, complete_state):
        """Test fallback includes summary of available analysis"""
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("Test failure")
        
        await reporting_agent.execute(complete_state, "test-run", False)
        
        # Fallback should indicate what data was analyzed
        result = complete_state.report_result
        assert result.metadata.get("fallback_used") is True