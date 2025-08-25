"""Unit tests for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Ensures orchestration logic correctness.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
from netra_backend.app.agents.base.interface import ExecutionContext


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for testing."""
    return {
        # Mock: Session isolation for controlled testing without external state
        "db_session": AsyncMock(),
        # Mock: LLM provider isolation to prevent external API usage and costs
        "llm_manager": MagicMock(),
        # Mock: WebSocket connection isolation for testing without network overhead
        "websocket_manager": AsyncMock(),
        # Mock: Tool execution isolation for predictable agent testing
        "tool_dispatcher": MagicMock(),
        # Mock: Generic component isolation for controlled unit testing
        "cache_manager": AsyncMock()
    }


@pytest.fixture
def orchestrator(mock_dependencies):
    """Create orchestrator instance for testing."""
    return ChatOrchestrator(**mock_dependencies)


@pytest.fixture
def execution_context():
    """Create mock execution context."""
    # Mock: Service component isolation for predictable testing behavior
    context = MagicMock(spec=ExecutionContext)
    context.request_id = "test_123"
    # Mock: Generic component isolation for controlled unit testing
    context.state = MagicMock()
    context.state.user_request = "What is the TCO for GPT-4?"
    return context


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly."""
    assert orchestrator.name == "ChatOrchestrator"
    assert orchestrator.semantic_cache_enabled == True
    assert orchestrator.intent_classifier is not None
    assert orchestrator.confidence_manager is not None


@pytest.mark.asyncio
async def test_intent_classification(orchestrator, execution_context):
    """Test intent classification process."""
    # Mock: Async component isolation for testing without real async operations
    orchestrator.intent_classifier.classify = AsyncMock(
        return_value=(IntentType.TCO_ANALYSIS, 0.95)
    )
    
    intent, confidence = await orchestrator._process_intent(execution_context)
    
    assert intent == IntentType.TCO_ANALYSIS
    assert confidence == 0.95
    orchestrator.intent_classifier.classify.assert_called_once()


@pytest.mark.asyncio
async def test_cache_check_high_confidence(orchestrator, execution_context):
    """Test cache check with high confidence."""
    # Mock: Service component isolation for predictable testing behavior
    orchestrator.confidence_manager.get_threshold = MagicMock(return_value=0.9)
    
    should_use = orchestrator._should_use_cache(IntentType.TCO_ANALYSIS, 0.95)
    
    assert should_use == True


@pytest.mark.asyncio
async def test_cache_check_low_confidence(orchestrator, execution_context):
    """Test cache check with low confidence."""
    # Mock: Service component isolation for predictable testing behavior
    orchestrator.confidence_manager.get_threshold = MagicMock(return_value=0.9)
    
    should_use = orchestrator._should_use_cache(IntentType.TCO_ANALYSIS, 0.7)
    
    assert should_use == False


@pytest.mark.asyncio
async def test_execution_pipeline(orchestrator, execution_context):
    """Test execution pipeline flow."""
    plan = [{"agent": "researcher", "action": "research", "params": {}}]
    # Mock: Async component isolation for testing without real async operations
    orchestrator.execution_planner.generate_plan = AsyncMock(return_value=plan)
    # Mock: Async component isolation for testing without real async operations
    orchestrator.pipeline_executor.execute = AsyncMock(
        return_value={"status": "success", "data": {}}
    )
    
    result = await orchestrator._execute_pipeline(
        execution_context, IntentType.TCO_ANALYSIS, 0.95
    )
    
    assert result["status"] == "success"
    orchestrator.pipeline_executor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_trace_logging(orchestrator):
    """Test trace logging functionality."""
    await orchestrator.trace_logger.log("Test action", {"detail": "test"})
    
    traces = orchestrator.trace_logger.get_compressed_trace()
    
    assert len(traces) > 0
    assert "Test action" in traces[0]


@pytest.mark.asyncio
async def test_error_handling(orchestrator, execution_context):
    """Test error handling in orchestration."""
    # Mock: Async component isolation for testing without real async operations
    orchestrator.intent_classifier.classify = AsyncMock(
        side_effect=Exception("Classification failed")
    )
    
    result = await orchestrator.execute_core_logic(execution_context)
    
    assert "error" in result
    assert "Classification failed" in result["error"]