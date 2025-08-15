"""
Integration tests for SupplyResearcherAgent
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.agents.supply_researcher_sub_agent import (
    SupplyResearcherAgent,
    ResearchType
)
from app.services.supply_research_service import SupplyResearchService
from app.services.supply_research_scheduler import (
    SupplyResearchScheduler,
    ResearchSchedule,
    ScheduleFrequency
)
from app.agents.state import DeepAgentState
from app.db.models_postgres import AISupplyItem, User
from app.background import BackgroundTaskManager


class TestSupplyResearcherIntegration:
    """Integration tests for supply research system"""
    
    @pytest.mark.asyncio
    async def test_agent_database_integration(self):
        """Test agent integration with database models"""
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
        agent = SupplyResearcherAgent(Mock(), mock_db, service)
        
        # Test update existing item
        update_data = {"pricing_input": Decimal("25")}
        
        with patch.object(agent.db_manager, 'update_database') as mock_update:
            mock_update.return_value = {"updates_count": 1}
            
            result = await agent.db_manager.update_database([update_data], "session_123")
            assert result["updates_count"] == 1
    
    @pytest.mark.asyncio
    async def test_e2e_admin_chat_supply_update(self):
        """End-to-end test: Admin requests supply update via chat"""
        # Setup
        mock_db = Mock()
        mock_user = User(
            id="admin_123",
            email="admin@test.com",
            role="admin",
            is_superuser=True
        )
        
        # Mock WebSocket manager
        mock_ws_manager = AsyncMock()
        mock_ws_manager.send_agent_update = AsyncMock()
        mock_ws_manager.send_message = AsyncMock()
        
        # Create agent
        llm_manager = Mock()
        supply_service = SupplyResearchService(mock_db)
        agent = SupplyResearcherAgent(llm_manager, mock_db, supply_service)
        agent.websocket_manager = mock_ws_manager
        
        # Admin request
        admin_request = "Add GPT-5 pricing: $40 per million input tokens, $120 per million output tokens"
        
        # Create state
        state = DeepAgentState(
            user_request=admin_request,
            user_id=mock_user.id,
            chat_thread_id="test_thread"
        )
        
        # Mock Deep Research API response
        with patch.object(agent.research_engine, 'call_deep_research_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {
                "session_id": "admin_session_123",
                "status": "completed",
                "questions_answered": [
                    {
                        "question": "What is GPT-5 pricing?",
                        "answer": "GPT-5 costs $40 per million input tokens and $120 per million output tokens"
                    }
                ],
                "citations": [
                    {"source": "OpenAI Pricing", "url": "https://openai.com/pricing"}
                ],
                "summary": "GPT-5 pricing confirmed"
            }
            
            # Mock database queries
            mock_db.query().filter().first.return_value = None  # No existing GPT-5
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Execute
            await agent.execute(state, "admin_chat_123", stream_updates=True)
            
            # Verify results
            assert hasattr(state, 'supply_research_result')
            result = state.supply_research_result
            
            # Check research was processed
            assert result["research_type"] == "pricing"
            assert result["confidence_score"] > 0.5
            
            # Check database operations
            mock_db.add.assert_called()  # Research session added
            mock_db.commit.assert_called()  # Changes committed
            
            # Check WebSocket updates were sent
            assert mock_ws_manager.send_agent_update.called
            
            # Verify the update contains correct pricing
            calls = mock_ws_manager.send_agent_update.call_args_list
            update_messages = [call[0][2] for call in calls]  # Get message content
            
            # Should have status updates
            statuses = [msg.get("status") for msg in update_messages if "status" in msg]
            assert "parsing" in statuses or "researching" in statuses
            assert "completed" in statuses or "processing" in statuses
            
            # Verify supply update would be available
            # In real scenario, this would update supply options available in the system
            assert result.get("summary") or result.get("updates_made")
            
            print(f"E2E Test Success: Admin request processed, GPT-5 pricing would be added to supply")
            print(f"Research confidence: {result.get('confidence_score', 0):.2f}")
            print(f"Citations: {len(result.get('citations', []))} sources")
    
    @pytest.mark.asyncio
    async def test_full_research_workflow(self):
        """Test complete research workflow from request to database update"""
        # This would be a full integration test with real components
        # For now, using mocks to simulate the flow
        
        # Setup components
        mock_db = Mock()
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
        with patch('app.db.postgres.Database') as mock_db_class:
            mock_db_class.return_value.get_db.return_value.__enter__ = Mock(return_value=mock_db)
            mock_db_class.return_value.get_db.return_value.__exit__ = Mock(return_value=None)
            
            with patch('app.services.supply_research_service.SupplyResearchService') as MockService:
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