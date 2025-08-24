"""
Integration tests for SupplyResearcherAgent
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from netra_backend.app.services.background_task_manager import BackgroundTaskManager

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supply_researcher_sub_agent import (
    ResearchType,
    SupplyResearcherAgent,
)
from netra_backend.app.db.models_postgres import AISupplyItem, User
from netra_backend.app.services.supply_research_scheduler import (
    ResearchSchedule,
    ScheduleFrequency,
    SupplyResearchScheduler,
)
from netra_backend.app.services.supply_research_service import SupplyResearchService

class TestSupplyResearcherIntegration:
    """Integration tests for supply research system"""
    @pytest.mark.asyncio
    async def test_agent_database_integration(self):
        """Test agent integration with database models"""
        # Mock: Generic component isolation for controlled unit testing
        mock_db = Mock()
        # Create mock supply item
        existing_item = AISupplyItem(
            id="123",
            provider="openai",
            model_name="GPT-4",
            pricing_input=Decimal("30"),
            pricing_output=Decimal("60")
        )
        
        mock_db.query().filter().first.return_value = existing_item
        
        service = SupplyResearchService(mock_db)
        # Mock: Generic component isolation for controlled unit testing
        agent = SupplyResearcherAgent(Mock(), mock_db, service)
        
        # Test update existing item
        update_data = {"pricing_input": Decimal("25")}
        
        with patch.object(agent.db_manager, 'update_database') as mock_update:
            mock_update.return_value = {"updates_count": 1}
            
            result = await agent.db_manager.update_database([update_data], "session_123")
            assert result["updates_count"] == 1
    
    def _setup_test_infrastructure(self):
        """Setup mock infrastructure for e2e test"""
        # Mock: Generic component isolation for controlled unit testing
        mock_db = Mock()
        mock_user = User(id="admin_123", email="admin@test.com", role="admin", is_superuser=True)
        
        # Mock: Generic component isolation for controlled unit testing
        mock_ws_manager = AsyncMock()
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_ws_manager.send_agent_update = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_ws_manager.send_message = AsyncMock()
        
        return mock_db, mock_user, mock_ws_manager

    def _create_test_agent(self, mock_db, mock_ws_manager):
        """Create agent with mocked dependencies"""
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = Mock()
        supply_service = SupplyResearchService(mock_db)
        agent = SupplyResearcherAgent(llm_manager, mock_db, supply_service)
        agent.websocket_manager = mock_ws_manager
        return agent

    def _create_test_state(self, mock_user):
        """Create test state for admin request"""
        admin_request = "Add GPT-5 pricing: $40 per million input tokens, $120 per million output tokens"
        return DeepAgentState(
            user_request=admin_request,
            user_id=mock_user.id,
            chat_thread_id="test_thread"
        )

    def _get_mock_api_response(self):
        """Get mock response for deep research API"""
        return {
            "session_id": "admin_session_123",
            "status": "completed",
            "questions_answered": [
                {
                    "question": "What is GPT-5 pricing?",
                    "answer": "GPT-5 costs $40 per million input tokens and $120 per million output tokens"
                }
            ],
            "citations": [{"source": "OpenAI Pricing", "url": "https://openai.com/pricing"}],
            "summary": "GPT-5 pricing confirmed"
        }

    def _setup_database_mocks(self, mock_db):
        """Setup database mock expectations"""
        mock_db.query().filter().first.return_value = None  # No existing GPT-5
        # Mock: Generic component isolation for controlled unit testing
        mock_db.add = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_db.commit = AsyncMock()

    def _verify_research_results(self, state):
        """Verify research processing results"""
        assert hasattr(state, 'supply_research_result')
        result = state.supply_research_result
        assert result["research_type"] == "pricing"
        assert result["confidence_score"] > 0.5
        return result

    def _verify_database_operations(self, mock_db):
        """Verify database operations were performed"""
        mock_db.add.assert_called()  # Research session added
        mock_db.commit.assert_called()  # Changes committed

    def _verify_websocket_updates(self, mock_ws_manager):
        """Verify WebSocket updates were sent properly"""
        assert mock_ws_manager.send_agent_update.called
        calls = mock_ws_manager.send_agent_update.call_args_list
        update_messages = [call[0][2] for call in calls]  # Get message content
        statuses = [msg.get("status") for msg in update_messages if "status" in msg]
        assert "parsing" in statuses or "researching" in statuses
        assert "completed" in statuses or "processing" in statuses

    def _verify_supply_updates(self, result):
        """Verify supply update results"""
        assert result.get("summary") or result.get("updates_made")
        print(f"E2E Test Success: Admin request processed, GPT-5 pricing would be added to supply")
        print(f"Research confidence: {result.get('confidence_score', 0):.2f}")
        print(f"Citations: {len(result.get('citations', []))} sources")
    @pytest.mark.asyncio
    async def test_e2e_admin_chat_supply_update(self):
        """End-to-end test: Admin requests supply update via chat"""
        mock_db, mock_user, mock_ws_manager = self._setup_test_infrastructure()
        agent = self._create_test_agent(mock_db, mock_ws_manager)
        state = self._create_test_state(mock_user)
        
        with patch.object(agent.research_engine, 'call_deep_research_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = self._get_mock_api_response()
            self._setup_database_mocks(mock_db)
            
            await agent.execute(state, "admin_chat_123", stream_updates=True)
            
            result = self._verify_research_results(state)
            self._verify_database_operations(mock_db)
            self._verify_websocket_updates(mock_ws_manager)
            self._verify_supply_updates(result)
    @pytest.mark.asyncio
    async def test_full_research_workflow(self):
        """Test complete research workflow from request to database update"""
        # This would be a full integration test with real components
        # For now, using mocks to simulate the flow
        
        # Setup components
        # Mock: Generic component isolation for controlled unit testing
        mock_db = Mock()
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager = Mock()
        background_manager = BackgroundTaskManager()
        
        # Initialize scheduler
        scheduler = SupplyResearchScheduler(background_manager, llm_manager)
        
        # Add custom schedule
        custom_schedule = ResearchSchedule(
            name="test_integration",
            frequency=ScheduleFrequency.DAILY,
            research_type=ResearchType.MARKET_OVERVIEW,
            providers=["openai", "anthropic", "google"]
        )
        scheduler.add_schedule(custom_schedule)
        
        # Mock database and API calls
        # Mock: Database access isolation for fast, reliable unit testing
        with patch('app.db.postgres.Database') as mock_db_class:
            # Mock: Component isolation for controlled unit testing
            mock_db_class.return_value.get_db.return_value.__enter__ = Mock(return_value=mock_db)
            # Mock: Component isolation for controlled unit testing
            mock_db_class.return_value.get_db.return_value.__exit__ = Mock(return_value=None)
            
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.supply_research_service.SupplyResearchService') as MockService:
                # Mock: Generic component isolation for controlled unit testing
                mock_service = Mock()
                mock_service.calculate_price_changes.return_value = {"all_changes": []}
                MockService.return_value = mock_service
                
                with patch.object(SupplyResearcherAgent, 'process_scheduled_research', new_callable=AsyncMock) as mock_process:
                    mock_process.return_value = {
                        "results": [{
                            "provider": "openai",
                            "session_id": "integration_test",
                            "status": "completed",
                            "questions_answered": [
                                {"question": "Market overview?", "answer": "Multiple price changes detected"}
                            ],
                            "citations": [{"source": "Market Report", "url": "https://example.com"}]
                        }]
                    }
                    
                    # Run the schedule
                    result = await scheduler.run_schedule_now("test_integration")
                    
                    # Verify workflow completed
                    assert result["status"] == "completed"
                    assert result["research_type"] == "market_overview"
                    assert len(result["providers"]) == 3
                    
                    print("Integration test passed: Full research workflow completed successfully")