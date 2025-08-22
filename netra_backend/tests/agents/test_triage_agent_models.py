"""
Triage agent model validation and cleanup tests
Tests Pydantic model validation and cleanup functionality
COMPLIANCE: 450-line max file, 25-line max functions
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent import (
    Complexity,
    KeyParameters,
    Priority,
    # Add project root to path
    TriageResult,
    UserIntent,
)

# Add project root to path
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager


@pytest.fixture
def mock_llm_manager():
    """Create a mock LLM manager."""
    mock = Mock(spec=LLMManager)
    mock.ask_llm = AsyncMock()
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Structured generation not available in test"))
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Create a mock tool dispatcher."""
    return Mock(spec=ToolDispatcher)


@pytest.fixture
def mock_redis_manager():
    """Create a mock Redis manager."""
    mock = Mock(spec=RedisManager)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Create a TriageSubAgent instance with mocked dependencies."""
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)


@pytest.fixture
def sample_state():
    """Create a sample DeepAgentState."""
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