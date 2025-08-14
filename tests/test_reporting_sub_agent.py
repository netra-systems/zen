"""Comprehensive test suite for ReportingSubAgent"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing"""
    mock = MagicMock()
    mock.ask_llm = AsyncMock()
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher for testing"""
    return MagicMock()


@pytest.fixture
def mock_state():
    """Mock agent state with all required data"""
    mock = MagicMock()
    mock.user_request = "Optimize system performance"
    
    # Mock triage result
    mock.triage_result = MagicMock()
    mock.triage_result.category = "performance_optimization"
    mock.triage_result.priority = "high"
    
    # Mock data result
    mock.data_result = MagicMock()
    mock.data_result.query = "performance analysis"
    mock.data_result.results = [{"metric": "cpu_usage", "value": 85}]
    
    # Mock optimizations result
    mock.optimizations_result = MagicMock()
    mock.optimizations_result.optimization_type = "performance"
    mock.optimizations_result.recommendations = ["Upgrade CPU", "Add RAM"]
    
    # Mock action plan result  
    mock.action_plan_result = MagicMock()
    mock.action_plan_result.priority = "high"
    mock.action_plan_result.estimated_duration = "2 weeks"
    
    # Mock report result (initially None)
    mock.report_result = None
    
    return mock


@pytest.fixture
def incomplete_state():
    """Mock agent state missing required data"""
    mock = MagicMock()
    mock.user_request = "Test request"
    mock.triage_result = MagicMock()
    mock.data_result = None
    mock.optimizations_result = None
    mock.action_plan_result = None
    mock.report_result = None
    return mock


@pytest.fixture
def reporting_agent(mock_llm_manager, mock_tool_dispatcher):
    """Create reporting agent instance for testing"""
    # Mock the imports to avoid dependency issues
    with patch('app.agents.reporting_sub_agent.BaseSubAgent') as mock_base:
        mock_base_instance = MagicMock()
        mock_base.return_value = mock_base_instance
        
        # Import and create the agent
        from app.agents.reporting_sub_agent import ReportingSubAgent
        agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # Set up WebSocket manager mock
        agent.websocket_manager = MagicMock()
        agent.websocket_manager.send_message = AsyncMock()
        
        return agent


class TestReportingSubAgentInit:
    """Test agent initialization"""
    
    def test_init_with_dependencies(self, mock_llm_manager, mock_tool_dispatcher):
        """Test initialization with proper dependencies"""
        with patch('app.agents.reporting_sub_agent.BaseSubAgent'):
            from app.agents.reporting_sub_agent import ReportingSubAgent
            agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert agent.llm_manager == mock_llm_manager
            assert agent.tool_dispatcher == mock_tool_dispatcher


    def test_init_sets_correct_name(self, mock_llm_manager, mock_tool_dispatcher):
        """Test agent name is set correctly"""
        with patch('app.agents.reporting_sub_agent.BaseSubAgent'):
            from app.agents.reporting_sub_agent import ReportingSubAgent
            agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert agent.name == "ReportingSubAgent"


    def test_init_sets_reliability_wrapper(self, mock_llm_manager, mock_tool_dispatcher):
        """Test reliability wrapper is initialized"""
        with patch('app.agents.reporting_sub_agent.BaseSubAgent'):
            from app.agents.reporting_sub_agent import ReportingSubAgent
            agent = ReportingSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert hasattr(agent, 'reliability')


class TestEntryConditions:
    """Test entry conditions validation"""

    async def test_entry_conditions_complete_data(self, reporting_agent, mock_state):
        """Test entry conditions pass with complete data"""
        result = await reporting_agent.check_entry_conditions(mock_state, "test-run")
        assert result is True


    async def test_entry_conditions_missing_action_plan(self, reporting_agent, mock_state):
        """Test entry conditions fail with missing action plan"""
        mock_state.action_plan_result = None
        result = await reporting_agent.check_entry_conditions(mock_state, "test-run")
        assert result is False


    async def test_entry_conditions_missing_optimizations(self, reporting_agent, mock_state):
        """Test entry conditions fail with missing optimizations"""
        mock_state.optimizations_result = None
        result = await reporting_agent.check_entry_conditions(mock_state, "test-run")
        assert result is False


    async def test_entry_conditions_missing_data_result(self, reporting_agent, mock_state):
        """Test entry conditions fail with missing data result"""
        mock_state.data_result = None
        result = await reporting_agent.check_entry_conditions(mock_state, "test-run")
        assert result is False


    async def test_entry_conditions_missing_triage(self, reporting_agent, mock_state):
        """Test entry conditions fail with missing triage"""
        mock_state.triage_result = None
        result = await reporting_agent.check_entry_conditions(mock_state, "test-run")
        assert result is False


class TestReportGeneration:
    """Test report generation logic"""

    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    @patch('app.agents.utils.extract_json_from_response')
    async def test_successful_report_generation(self, mock_extract, mock_validate, reporting_agent, mock_state):
        """Test successful report generation"""
        mock_validate.return_value = None  # Bypass validation
        mock_report = {"report": "Complete analysis report", "sections": []}
        mock_extract.return_value = mock_report
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Complete analysis report"}'
        
        await reporting_agent.execute(mock_state, "test-run", True)
        
        assert mock_state.report_result is not None
        assert mock_state.report_result.content == "Complete analysis report"


    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    @patch('app.agents.utils.extract_json_from_response')
    async def test_json_extraction_failure(self, mock_extract, mock_validate, reporting_agent, mock_state):
        """Test fallback when JSON extraction fails"""
        mock_validate.return_value = None  # Bypass validation
        mock_extract.return_value = None
        reporting_agent.llm_manager.ask_llm.return_value = 'invalid json'
        
        await reporting_agent.execute(mock_state, "test-run", True)
        
        assert mock_state.report_result is not None
        assert "No report could be generated" in mock_state.report_result.content


    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    async def test_llm_failure_triggers_fallback(self, mock_validate, reporting_agent, mock_state):
        """Test fallback when LLM call fails"""
        mock_validate.return_value = None  # Bypass validation
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("LLM Error")
        
        await reporting_agent.execute(mock_state, "test-run", True)
        
        assert mock_state.report_result is not None
        assert "Report generation failed" in mock_state.report_result.content


class TestReportFormatting:
    """Test report formatting for different types"""

    def test_create_report_result_with_full_data(self, reporting_agent):
        """Test creating ReportResult with complete data"""
        data = {
            "report": "Test report content",
            "sections": [],
            "metadata": {"created_by": "test"}
        }
        
        result = reporting_agent._create_report_result(data)
        
        assert result.report_type == "analysis"
        assert result.content == "Test report content"
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

    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    @patch('app.agents.utils.extract_json_from_response')
    async def test_websocket_updates_enabled(self, mock_extract, mock_validate, reporting_agent, mock_state):
        """Test WebSocket updates are sent when enabled"""
        mock_validate.return_value = None  # Bypass validation
        mock_extract.return_value = {"report": "Test report"}
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Test"}'
        
        await reporting_agent.execute(mock_state, "test-run", True)
        
        # Should send processing and processed updates
        assert reporting_agent.websocket_manager.send_message.call_count >= 2


    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    @patch('app.agents.utils.extract_json_from_response')
    async def test_websocket_updates_disabled(self, mock_extract, mock_validate, reporting_agent, mock_state):
        """Test no WebSocket updates when disabled"""
        mock_validate.return_value = None  # Bypass validation
        mock_extract.return_value = {"report": "Test report"}
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Test"}'
        
        await reporting_agent.execute(mock_state, "test-run", False)
        
        # Should not send any updates
        reporting_agent.websocket_manager.send_message.assert_not_called()


class TestErrorHandling:
    """Test error handling for various failure scenarios"""

    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    async def test_missing_data_handled_gracefully(self, mock_validate, reporting_agent, incomplete_state):
        """Test graceful handling of missing required data"""
        mock_validate.return_value = None  # Bypass validation
        # Should not raise exception during execution attempt
        try:
            await reporting_agent.execute(incomplete_state, "test-run", False)
        except Exception as e:
            pytest.fail(f"Should handle missing data gracefully: {e}")


    @patch('app.agents.input_validation.InputValidator.validate_and_raise')
    async def test_websocket_disconnect_handled(self, mock_validate, reporting_agent, mock_state):
        """Test WebSocket disconnect is handled gracefully"""
        mock_validate.return_value = None  # Bypass validation
        from starlette.websockets import WebSocketDisconnect
        reporting_agent.websocket_manager.send_message.side_effect = WebSocketDisconnect()
        reporting_agent.llm_manager.ask_llm.return_value = '{"report": "Test"}'
        
        # Should not raise exception
        await reporting_agent.execute(mock_state, "test-run", True)


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

    async def test_fallback_creates_valid_report(self, reporting_agent, mock_state):
        """Test fallback creates a valid report structure"""
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("Test failure")
        
        await reporting_agent.execute(mock_state, "test-run", True)
        
        result = mock_state.report_result
        assert result is not None
        assert "Report generation failed" in result.content
        assert result.metadata.get("fallback_used") is True


    async def test_fallback_includes_analysis_summary(self, reporting_agent, mock_state):
        """Test fallback includes summary of available analysis"""
        reporting_agent.llm_manager.ask_llm.side_effect = Exception("Test failure")
        
        await reporting_agent.execute(mock_state, "test-run", False)
        
        # Fallback should indicate what data was analyzed
        result = mock_state.report_result
        assert result.metadata.get("fallback_used") is True