"""
Error handling tests for SupplyResearcherAgent
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from netra_backend.app.services.supply_research_service import SupplyResearchService
from netra_backend.app.agents.state import DeepAgentState
from llm.llm_manager import LLMManager

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestSupplyResearcherErrorHandling:
    """Test suite for SupplyResearcherAgent error handling"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = Mock()
        db.query = Mock()
        db.add = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager"""
        llm = Mock(spec=LLMManager)
        return llm
    
    @pytest.fixture
    def mock_supply_service(self, mock_db):
        """Create mock supply research service"""
        service = Mock(spec=SupplyResearchService)
        service.db = mock_db
        service.get_supply_items = Mock(return_value=[])
        service.create_or_update_supply_item = Mock()
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
    async def test_api_failure_handling(self, agent, mock_db):
        """Test handling Deep Research API failures"""
        state = DeepAgentState(
            user_request="Update pricing",
            chat_thread_id="test_thread",
            user_id="test_user"
        )
        
        with patch.object(agent.research_engine, 'call_deep_research_api', side_effect=Exception("API Error")):
            mock_db.query().filter().first.return_value = Mock(status="failed")
            
            with pytest.raises(Exception):
                await agent.execute(state, "test_run", False)
            
            assert state.supply_research_result["status"] == "error"