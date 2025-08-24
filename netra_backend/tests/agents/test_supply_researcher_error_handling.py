"""
Error handling tests for SupplyResearcherAgent
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.supply_research_service import SupplyResearchService

class TestSupplyResearcherErrorHandling:
    """Test suite for SupplyResearcherAgent error handling"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        # Mock: Generic component isolation for controlled unit testing
        db = Mock()
        # Mock: Generic component isolation for controlled unit testing
        db.query = Mock()
        # Mock: Generic component isolation for controlled unit testing
        db.add = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        db.commit = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        db.rollback = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm = Mock(spec=LLMManager)
        return llm
    
    @pytest.fixture
    def mock_supply_service(self, mock_db):
        """Create mock supply research service"""
        # Mock: Component isolation for controlled unit testing
        service = Mock(spec=SupplyResearchService)
        service.db = mock_db
        # Mock: Component isolation for controlled unit testing
        service.get_supply_items = Mock(return_value=[])
        # Mock: Generic component isolation for controlled unit testing
        service.create_or_update_supply_item = Mock()
        # Mock: Component isolation for controlled unit testing
        service.validate_supply_data = Mock(return_value=(True, []))
        return service
    
    @pytest.fixture
    def agent(self, mock_llm_manager, mock_db, mock_supply_service):
        """Create SupplyResearcherAgent instance"""
        return SupplyResearcherAgent(
            llm_manager=mock_llm_manager,
            db=mock_db,
            supply_service=mock_supply_service
        )
    @pytest.mark.asyncio
    async def test_api_failure_handling(self, agent, mock_db):
        """Test handling Deep Research API failures"""
        state = DeepAgentState(
            user_request="Update pricing",
            chat_thread_id="test_thread",
            user_id="test_user"
        )
        
        with patch.object(agent.research_engine, 'call_deep_research_api', side_effect=Exception("API Error")):
            # Mock: Component isolation for controlled unit testing
            mock_db.query().filter().first.return_value = Mock(status="failed")
            
            with pytest.raises(Exception):
                await agent.execute(state, "test_run", False)
            
            assert state.supply_research_result["status"] == "error"