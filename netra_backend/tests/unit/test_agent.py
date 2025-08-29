"""
Unit tests for base agent
Coverage Target: 70%
Business Value: Long-term maintainability
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.state import DeepAgentState


class ConcreteTestAgent(BaseSubAgent):
    """Concrete implementation of BaseSubAgent for testing"""
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Concrete execute implementation for testing"""
        pass
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Concrete check entry conditions implementation"""
        return True


class TestBaseSubAgent:
    """Test suite for BaseSubAgent"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager"""
        return MagicMock(spec=LLMManager)
    
    @pytest.fixture
    def instance(self, mock_llm_manager):
        """Create test instance using concrete implementation"""
        return ConcreteTestAgent(llm_manager=mock_llm_manager)
    
    def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert instance.name == "BaseSubAgent"
        assert instance.description == "This is the base sub-agent."
        assert instance.llm_manager is not None
    
    def test_state_management(self, instance):
        """Test agent state management"""
        from netra_backend.app.schemas.agent import SubAgentLifecycle
        assert instance.state == SubAgentLifecycle.PENDING
    
    def test_context_management(self, instance):
        """Test context management"""
        assert instance.context == {}
        instance.context['key'] = 'value'
        assert instance.context['key'] == 'value'
    
    @pytest.mark.asyncio
    async def test_shutdown(self, instance):
        """Test shutdown cleanup"""
        instance.context['test'] = 'data'
        await instance.shutdown()
        assert instance.context == {}
