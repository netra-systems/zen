"""
Basic tests for SupplyResearchService - initialization and retrieval operations
Tests service initialization, Redis handling, and supply item retrieval methods
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.db.models_postgres import AISupplyItem, ResearchSession

# Add project root to path
from app.services.supply_research_service import SupplyResearchService

# Add project root to path


@pytest.fixture
def service():
    """Create SupplyResearchService instance with mock database"""
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    return SupplyResearchService(mock_db)


@pytest.fixture
def sample_supply_item() -> AISupplyItem:
    """Create compact sample AISupplyItem fixture"""
    item = MagicMock(spec=AISupplyItem)
    item.id = "supply-item-1"
    item.provider = "openai"
    item.model_name = "gpt-4"
    item.pricing_input = Decimal("0.03")
    item.pricing_output = Decimal("0.06")
    item.confidence_score = 0.9
    item.availability_status = "available"
    item.last_updated = datetime.now(UTC)
    return item


class TestServiceInitialization:
    """Test service initialization with and without Redis"""
    
    def test_initialization_with_redis(self):
        """Test initialization with Redis available"""
        mock_db = MagicMock()
        with patch('app.services.supply_research_service.RedisManager') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            
            service = SupplyResearchService(mock_db)
            
            assert service.db == mock_db
            assert service.redis_manager == mock_instance
    
    def test_initialization_without_redis(self):
        """Test initialization when Redis unavailable"""
        mock_db = MagicMock()
        with patch('app.services.supply_research_service.RedisManager', 
                   side_effect=Exception("Redis not available")):
            service = SupplyResearchService(mock_db)
            
            assert service.db == mock_db
            assert service.redis_manager is None


class TestSupplyItemRetrieval:
    """Test supply item retrieval methods with various filters"""
    
    def test_get_supply_items_no_filters(self, service, sample_supply_item):
        """Test getting all supply items without filters"""
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.order_by.return_value.all.return_value = [sample_supply_item]
            
            result: List[AISupplyItem] = service.get_supply_items()
            
            assert len(result) == 1
            assert result[0] == sample_supply_item
    
    def test_get_supply_items_with_provider_filter(self, service, sample_supply_item):
        """Test retrieving items filtered by provider"""
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.filter.return_value.order_by.return_value
            mock_chain.all.return_value = [sample_supply_item]
            
            result: List[AISupplyItem] = service.get_supply_items(provider="openai")
            
            assert len(result) == 1
            assert result[0].provider == "openai"
    
    def test_get_supply_items_with_availability_filter(self, service, sample_supply_item):
        """Test retrieving items filtered by availability"""
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.filter.return_value.order_by.return_value
            mock_chain.all.return_value = [sample_supply_item]
            
            result: List[AISupplyItem] = service.get_supply_items(availability_status="available")
            
            assert len(result) == 1
            assert result[0].availability_status == "available"
    
    def test_get_supply_items_with_confidence_filter(self, service, sample_supply_item):
        """Test retrieving items filtered by minimum confidence"""
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.filter.return_value.order_by.return_value
            mock_chain.all.return_value = [sample_supply_item]
            
            result: List[AISupplyItem] = service.get_supply_items(min_confidence=0.8)
            
            assert len(result) == 1
            assert result[0].confidence_score >= 0.8
    
    def test_get_supply_items_empty_result(self, service):
        """Test retrieving when no items match filters"""
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.order_by.return_value.all.return_value = []
            
            result: List[AISupplyItem] = service.get_supply_items()
            
            assert len(result) == 0
    
    def test_get_supply_item_by_id_exists(self, service, sample_supply_item):
        """Test retrieving existing item by ID"""
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.filter.return_value
            mock_chain.first.return_value = sample_supply_item
            
            result: Optional[AISupplyItem] = service.get_supply_item_by_id("supply-item-1")
            
            assert result == sample_supply_item
    
    def test_get_supply_item_by_id_not_exists(self, service):
        """Test retrieving non-existent item by ID"""
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.filter.return_value
            mock_chain.first.return_value = None
            
            result: Optional[AISupplyItem] = service.get_supply_item_by_id("non-existent")
            
            assert result is None


class TestResearchSessionRetrieval:
    """Test research session retrieval operations"""
    
    def test_get_research_sessions_no_filters(self, service):
        """Test retrieving all research sessions"""
        sample_session = self._create_sample_session("session-1", "completed")
        
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.order_by.return_value.limit.return_value
            mock_chain.all.return_value = [sample_session]
            
            result: List[ResearchSession] = service.get_research_sessions()
            
            assert len(result) == 1
            assert result[0] == sample_session
    
    def test_get_research_sessions_with_status_filter(self, service):
        """Test retrieving sessions filtered by status"""
        completed_session = self._create_sample_session("session-1", "completed")
        
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = (mock_query.return_value.filter.return_value
                         .order_by.return_value.limit.return_value)
            mock_chain.all.return_value = [completed_session]
            
            result: List[ResearchSession] = service.get_research_sessions(status="completed")
            
            assert len(result) == 1
            assert result[0].status == "completed"
    
    def test_get_research_session_by_id(self, service):
        """Test retrieving session by ID"""
        target_session = self._create_sample_session("session-1", "completed")
        
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.filter.return_value
            mock_chain.first.return_value = target_session
            
            result: Optional[ResearchSession] = service.get_research_session_by_id("session-1")
            
            assert result == target_session
    
    def _create_sample_session(self, session_id: str, status: str) -> ResearchSession:
        """Helper to create sample research session"""
        session = MagicMock(spec=ResearchSession)
        session.id = session_id
        session.status = status
        return session


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])