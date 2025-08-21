"""
Core tests for SupplyResearcherAgent - Basic functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock
from decimal import Decimal

from app.agents.supply_researcher_sub_agent import (
    SupplyResearcherAgent,
    ResearchType
)
from app.services.supply_research_service import SupplyResearchService
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager


class TestSupplyResearcherAgentCore:
    """Test suite for SupplyResearcherAgent core functionality"""
    
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
        llm.ask_llm = AsyncMock(return_value="Mock LLM response")
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
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.name == "SupplyResearcherAgent"
        assert agent.confidence_threshold == 0.7
        assert agent.research_timeout == 300
        assert len(agent.parser.provider_patterns) > 0
    
    def test_parse_pricing_request(self, agent):
        """Test parsing pricing-related requests"""
        request = "Add GPT-5 pricing information"
        parsed = agent.parser.parse_natural_language_request(request)
        
        assert parsed["research_type"] == ResearchType.PRICING
        assert parsed["provider"] == "openai"
        assert "gpt" in parsed["model_name"].lower()
    
    def test_parse_capability_request(self, agent):
        """Test parsing capability-related requests"""
        request = "What are the context window limits for Claude-3"
        parsed = agent.parser.parse_natural_language_request(request)
        
        assert parsed["research_type"] == ResearchType.CAPABILITIES
        assert parsed["provider"] == "anthropic"
        assert "claude" in parsed["model_name"].lower()
    
    def test_parse_availability_request(self, agent):
        """Test parsing availability-related requests"""
        request = "Check API availability for Gemini models"
        parsed = agent.parser.parse_natural_language_request(request)
        
        assert parsed["research_type"] == ResearchType.AVAILABILITY
        assert parsed["provider"] == "google"
    
    def test_generate_pricing_query(self, agent):
        """Test generating Deep Research query for pricing"""
        parsed = {
            "research_type": ResearchType.PRICING,
            "provider": "openai",
            "model_name": "GPT-4",
            "timeframe": "current"
        }
        
        query = agent.research_engine.generate_research_query(parsed)
        assert "pricing" in query.lower()
        assert "input tokens" in query.lower()
        assert "output tokens" in query.lower()
    
    def test_generate_market_overview_query(self, agent):
        """Test generating Deep Research query for market overview"""
        parsed = {
            "research_type": ResearchType.MARKET_OVERVIEW,
            "provider": None,
            "model_name": None,
            "timeframe": "monthly"
        }
        
        query = agent.research_engine.generate_research_query(parsed)
        assert "comprehensive overview" in query.lower()
        assert "market" in query.lower()
    
    def test_extract_supply_data(self, agent):
        """Test extracting structured data from research results"""
        research_result = {
            "questions_answered": [
                {
                    "question": "What is the pricing?",
                    "answer": "The model costs $15 per million input tokens and $60 per million output tokens with 128K context window"
                }
            ]
        }
        parsed_request = {"provider": "openai", "model_name": "GPT-4"}
        
        supply_items = agent.data_extractor.extract_supply_data(research_result, parsed_request)
        
        assert len(supply_items) > 0
        assert supply_items[0]["pricing_input"] == Decimal("15")
        assert supply_items[0]["pricing_output"] == Decimal("60")
        assert supply_items[0]["context_window"] == 128000
    
    def test_calculate_confidence_score(self, agent):
        """Test confidence score calculation"""
        research_result = {
            "citations": [
                {"source": "Official Documentation", "url": "https://example.com"},
                {"source": "Pricing Page", "url": "https://example.com/pricing"}
            ]
        }
        extracted_data = [
            {
                "pricing_input": Decimal("10"),
                "pricing_output": Decimal("20"),
                "context_window": 100000
            }
        ]
        
        score = agent.data_extractor.calculate_confidence_score(research_result, extracted_data)
        assert score > 0.5
        assert score <= 1.0