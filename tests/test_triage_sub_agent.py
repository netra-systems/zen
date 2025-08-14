"""Comprehensive test suite for TriageSubAgent"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.triage_sub_agent.models import (
    TriageResult, TriageMetadata, Priority, Complexity, 
    ExtractedEntities, UserIntent, ValidationStatus
)
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing"""
    mock = MagicMock(spec=LLMManager)
    mock.ask_structured_llm = AsyncMock()
    mock.ask_llm = AsyncMock()
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher for testing"""
    return MagicMock(spec=ToolDispatcher)


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for testing"""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    return mock


@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Create triage agent instance for testing"""
    agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
    agent.websocket_manager = MagicMock()
    agent.websocket_manager.send_message = AsyncMock()
    return agent


@pytest.fixture
def sample_state():
    """Sample agent state for testing"""
    return DeepAgentState(user_request="Optimize cost for GPU workloads in production")


@pytest.fixture
def sample_triage_result():
    """Sample triage result for testing"""
    return TriageResult(
        category="Cost Optimization",
        confidence_score=0.9,
        priority=Priority.HIGH,
        complexity=Complexity.MODERATE,
        extracted_entities=ExtractedEntities(
            models_mentioned=["GPU"],
            metrics_mentioned=["cost"]
        ),
        user_intent=UserIntent(primary_intent="optimize"),
        metadata=TriageMetadata(triage_duration_ms=100)
    )


class TestTriageSubAgentInitialization:
    def test_agent_initialization_success(self, mock_llm_manager, mock_tool_dispatcher):
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher)
        assert agent.name == "TriageSubAgent"
        assert agent.llm_manager == mock_llm_manager
        assert agent.tool_dispatcher == mock_tool_dispatcher
        assert agent.triage_core is not None
        assert agent.reliability is not None

    def test_agent_initialization_with_redis(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        assert agent.triage_core.redis_manager == mock_redis_manager


class TestEntryConditions:
    
    async def test_check_entry_conditions_valid_request(self, triage_agent, sample_state):
        result = await triage_agent.check_entry_conditions(sample_state, "test-run-id")
        assert result is True

    async def test_check_entry_conditions_no_request(self, triage_agent):
        state = DeepAgentState(user_request="")
        result = await triage_agent.check_entry_conditions(state, "test-run-id")
        assert result is False

    async def test_check_entry_conditions_invalid_request(self, triage_agent):
        state = DeepAgentState(user_request="invalid request")
        with patch.object(triage_agent.triage_core.validator, 'validate_request') as mock_validate:
            mock_validate.return_value = ValidationStatus(is_valid=False, validation_errors=["Invalid request"])
            result = await triage_agent.check_entry_conditions(state, "test-run-id")
            assert result is False
            assert state.triage_result is not None
            assert state.triage_result.category == "Validation Error"


class TestCachingFunctionality:
    """Test caching functionality (cache hit/miss)"""
    
    async def test_cache_hit_scenario(self, triage_agent, sample_state, sample_triage_result):
        cached_data = sample_triage_result.model_dump()
        cached_data["metadata"] = {"cache_hit": False}
        triage_agent.triage_core.get_cached_result = AsyncMock(return_value=cached_data)
        
        await triage_agent.execute(sample_state, "test-run-id", False)
        
        assert sample_state.triage_result["metadata"]["cache_hit"] is True

    async def test_cache_miss_scenario(self, triage_agent, sample_state, sample_triage_result):
        triage_agent.triage_core.get_cached_result = AsyncMock(return_value=None)
        triage_agent._process_with_llm = AsyncMock(return_value=sample_triage_result.model_dump())
        triage_agent.triage_core.cache_result = AsyncMock()
        
        await triage_agent.execute(sample_state, "test-run-id", False)
        
        triage_agent.triage_core.cache_result.assert_called_once()


class TestRequestCategorization:
    """Test request categorization logic"""
    
    async def test_cost_optimization_categorization(self, triage_agent, mock_llm_manager):
        state = DeepAgentState(user_request="Reduce costs for ML training workloads")
        
        mock_result = TriageResult(category="Cost Optimization", confidence_score=0.95)
        mock_llm_manager.ask_structured_llm.return_value = mock_result
        
        await triage_agent.execute(state, "test-run-id", False)
        
        assert state.triage_result["category"] == "Cost Optimization"

    async def test_performance_optimization_categorization(self, triage_agent, mock_llm_manager):
        state = DeepAgentState(user_request="Improve inference speed for our models")
        
        mock_result = TriageResult(category="Performance Optimization", confidence_score=0.88)
        mock_llm_manager.ask_structured_llm.return_value = mock_result
        
        await triage_agent.execute(state, "test-run-id", False)
        
        assert state.triage_result["category"] == "Performance Optimization"


class TestEnrichmentFunctions:
    def test_entity_extraction_enrichment(self, triage_agent):
        request = "Optimize GPT-4 model costs with 90% accuracy threshold"
        result = {"category": "Cost Optimization"}
        enriched = triage_agent._enrich_triage_result(result, request)
        assert "extracted_entities" in enriched
        assert "user_intent" in enriched

    def test_entity_extraction_preserves_existing(self, triage_agent):
        request = "Test request"
        result = {"category": "Test", "extracted_entities": {"models_mentioned": ["existing"]}, "user_intent": {"primary_intent": "existing"}}
        enriched = triage_agent._enrich_triage_result(result, request)
        assert enriched["extracted_entities"]["models_mentioned"] == ["existing"]

    def test_admin_mode_detection_true(self, triage_agent):
        request = "Generate synthetic training data for model validation"
        result = {"category": "General Inquiry"}
        with patch.object(triage_agent.triage_core.intent_detector, 'detect_admin_mode', return_value=True):
            enriched = triage_agent._enrich_triage_result(result, request)
        assert enriched.get("is_admin_mode", True)

    def test_admin_mode_detection_false(self, triage_agent):
        request = "Show me cost analysis for last month"
        result = {"category": "Cost Optimization"}
        enriched = triage_agent._enrich_triage_result(result, request)
        assert not enriched.get("is_admin_mode", False)

    def test_tool_recommendations_added(self, triage_agent):
        request = "Analyze GPU utilization patterns"
        result = {"category": "Workload Analysis", "extracted_entities": {}}
        enriched = triage_agent._enrich_triage_result(result, request)
        assert "tool_recommendations" in enriched
        assert isinstance(enriched["tool_recommendations"], list)

    def test_tool_recommendations_preserved(self, triage_agent):
        request = "Test request"
        existing_tools = [{"tool_name": "existing", "relevance_score": 0.8}]
        result = {"category": "Test", "tool_recommendations": existing_tools}
        enriched = triage_agent._enrich_triage_result(result, request)
        assert enriched["tool_recommendations"] == existing_tools


class TestErrorHandlingAndReliability:
    async def test_llm_failure_fallback(self, triage_agent, sample_state):
        triage_agent.triage_core.get_cached_result = AsyncMock(return_value=None)
        triage_agent._process_with_llm = AsyncMock(return_value=None)
        await triage_agent.execute(sample_state, "test-run-id", False)
        assert sample_state.triage_result is not None

    async def test_structured_llm_fallback_to_regular(self, triage_agent, mock_llm_manager):
        mock_llm_manager.ask_structured_llm.side_effect = Exception("Structured failed")
        mock_llm_manager.ask_llm.return_value = '{"category": "Test", "confidence_score": 0.5}'
        result = await triage_agent._fallback_llm_processing("test prompt", "run-id", Exception())
        assert result is not None

    async def test_json_extraction_failure_returns_none(self, triage_agent, mock_llm_manager):
        mock_llm_manager.ask_llm.return_value = "Invalid JSON response"
        triage_agent.triage_core.extract_and_validate_json = MagicMock(return_value=None)
        result = await triage_agent._fallback_llm_processing("test prompt", "run-id", Exception())
        assert result is None

    async def test_retry_on_failure(self, triage_agent, sample_state):
        call_count = 0
        async def mock_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")
            return {"category": "Test", "confidence_score": 0.5}
        
        triage_agent._process_with_llm = mock_process
        triage_agent.triage_core.get_cached_result = AsyncMock(return_value=None)
        await triage_agent.execute(sample_state, "test-run-id", False)
        assert call_count >= 1


class TestWebSocketAndLogging:
    async def test_websocket_updates_sent(self, triage_agent, sample_state):
        triage_agent.triage_core.get_cached_result = AsyncMock(return_value=None)
        triage_agent._process_with_llm = AsyncMock(return_value={"category": "Test"})
        await triage_agent.execute(sample_state, "test-run-id", True)
        assert triage_agent.websocket_manager.send_message.call_count >= 2

    async def test_websocket_final_update_format(self, triage_agent, sample_triage_result):
        await triage_agent._send_final_update("test-run-id", sample_triage_result.model_dump())
        assert triage_agent.websocket_manager.send_message.called
        call_args = triage_agent.websocket_manager.send_message.call_args
        assert len(call_args[0]) >= 2

    def test_metadata_addition(self, triage_agent):
        result = {"category": "Test"}
        start_time = 1000.0
        with patch('time.time', return_value=1000.1):
            enhanced = triage_agent._add_metadata(result, start_time, 2)
        assert enhanced["metadata"]["triage_duration_ms"] == 100
        assert enhanced["metadata"]["retry_count"] == 2

    def test_performance_metrics_logging(self, triage_agent, sample_triage_result):
        result_dict = sample_triage_result.model_dump()
        result_dict["metadata"] = {"triage_duration_ms": 150, "cache_hit": False}
        triage_agent._log_performance_metrics("test-run-id", result_dict)

    async def test_cleanup_logs_metrics(self, triage_agent):
        state = DeepAgentState(user_request="test")
        state.triage_result = {"metadata": {"duration": 100}}
        await triage_agent.cleanup(state, "test-run-id")

    def test_health_status_returned(self, triage_agent):
        status = triage_agent.get_health_status()
        assert isinstance(status, dict)

    def test_circuit_breaker_status_returned(self, triage_agent):
        status = triage_agent.get_circuit_breaker_status()
        assert isinstance(status, dict)