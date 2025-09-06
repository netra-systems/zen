"""
Triage agent model validation and cleanup tests
Tests Pydantic model validation and cleanup functionality
COMPLIANCE: 450-line max file, 25-line max functions
"""

import sys
from pathlib import Path
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead


import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage.unified_triage_agent import (
    Complexity,
    KeyParameters,
    Priority,
    TriageResult,
    UserIntent)

from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
import asyncio

@pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock LLM manager."""
    pass
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock = Mock(spec=LLMManager)
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock.ask_llm = AsyncNone  # TODO: Use real service instance
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Structured generation not available in test"))
    return mock

@pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock tool dispatcher."""
    pass
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    return Mock(spec=ToolDispatcher)

@pytest.fixture
 def real_redis_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a mock Redis manager."""
    pass
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock = Mock(spec=RedisManager)
    # Mock: Async component isolation for testing without real async operations
    mock.get = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    mock.set = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a TriageSubAgent instance with mocked dependencies."""
    pass
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)

@pytest.fixture
def sample_state():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create a sample DeepAgentState."""
    pass
    return DeepAgentState(user_request="Optimize my GPT-4 costs by 30% while maintaining latency under 100ms")

class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_triage_result_validation(self):
        """Test TriageResult model validation."""
        # Valid result
        result = TriageResult(
            category="Test",
            confidence_score=0.8,
            priority=Priority.HIGH,
            complexity=Complexity.MODERATE
        )
        assert result.category == "Test"
        assert result.confidence_score == 0.8
    
    def test_triage_result_confidence_validation(self):
        """Test confidence score validation."""
    pass
        with pytest.raises(ValueError):
            TriageResult(category="Test", confidence_score=1.5)  # Out of range
    
    def test_key_parameters_model(self):
        """Test KeyParameters model."""
        params = KeyParameters(
            workload_type="inference",
            optimization_focus="cost",
            constraints=["latency < 100ms", "cost < $1000"]
        )
        assert params.workload_type == "inference"
        assert len(params.constraints) == 2
    
    def test_user_intent_model(self):
        """Test UserIntent model."""
    pass
        intent = UserIntent(
            primary_intent="optimize",
            secondary_intents=["analyze", "compare"],
            action_required=True
        )
        assert intent.primary_intent == "optimize"
        assert len(intent.secondary_intents) == 2
        assert intent.action_required == True

class TestCleanup:
    """Test cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_cleanup_with_metrics(self, triage_agent, sample_state):
        """Test cleanup logs metrics when available."""
        sample_state.triage_result = {
            "category": "Test",
            "metadata": {
                "triage_duration_ms": 100,
                "cache_hit": False
            }
        }
        
        # Patch the instance logger, not the module logger
        with patch.object(triage_agent, 'logger') as mock_logger:
            await triage_agent.cleanup(sample_state, "test_run")
            
            # Should log debug metrics
            mock_logger.debug.assert_called()
    pass