"""
CRUD tests for SupplyResearchService - create, update, and delete operations
Tests supply item creation, updates, and update log operations
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from netra_backend.app.services.supply_research_service import SupplyResearchService
from netra_backend.app.db.models_postgres import AISupplyItem, SupplyUpdateLog

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock()

@pytest.fixture
def service(mock_db_session):
    """Create SupplyResearchService instance with mock database"""
    return SupplyResearchService(mock_db_session)


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
    item.last_updated = datetime.now(UTC)
    return item


@pytest.fixture
def sample_update_log() -> SupplyUpdateLog:
    """Create compact sample SupplyUpdateLog fixture"""
    log = MagicMock(spec=SupplyUpdateLog)
    log.id = "log-1"
    log.supply_item_id = "supply-item-1"
    log.field_updated = "pricing_input"
    log.old_value = "0.02"
    log.new_value = "0.03"
    log.updated_at = datetime.now(UTC)
    return log


class TestSupplyItemCreate:
    """Test supply item creation operations"""
    
    def test_create_new_supply_item(self, service):
        """Test creating completely new supply item"""
        data: Dict[str, Any] = {
            "pricing_input": Decimal("0.03"),
            "pricing_output": Decimal("0.06"),
            "context_window": 8192,
            "availability_status": "available",
            "confidence_score": 0.9
        }
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            with patch('app.services.supply_research_service.AISupplyItem') as mock_item_class:
                with patch('app.services.supply_research_service.SupplyUpdateLog'):
                    mock_item = MagicMock()
                    mock_item.id = "new-item-id"
                    mock_item_class.return_value = mock_item
                    
                    result = service.create_or_update_supply_item(
                        "openai", "gpt-4", data, "session-1", "test-user"
                    )
            
            assert result == mock_item
    
    def test_create_item_with_minimal_data(self, service):
        """Test creating item with only required fields"""
        minimal_data: Dict[str, Any] = {
            "confidence_score": 0.8,
            "research_source": "official-api"
        }
        
        self._test_item_creation(service, minimal_data)
    
    def _test_item_creation(self, service, data: Dict[str, Any]):
        """Helper method for item creation tests"""
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            with patch('app.services.supply_research_service.AISupplyItem') as mock_item_class:
                with patch('app.services.supply_research_service.SupplyUpdateLog'):
                    mock_item = MagicMock()
                    mock_item_class.return_value = mock_item
                    
                    result = service.create_or_update_supply_item("openai", "gpt-4", data)
            
            assert result == mock_item


class TestSupplyItemUpdate:
    """Test supply item update operations"""
    
    def test_update_existing_item_no_changes(self, service, sample_supply_item):
        """Test updating item with identical data (no changes)"""
        data: Dict[str, Any] = {
            "pricing_input": sample_supply_item.pricing_input,
            "pricing_output": sample_supply_item.pricing_output,
            "confidence_score": sample_supply_item.confidence_score
        }
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = sample_supply_item
            
            result = service.create_or_update_supply_item("openai", "gpt-4", data)
            
            assert result == sample_supply_item
    
    def test_update_existing_item_single_change(self, service, sample_supply_item):
        """Test updating item with single field change"""
        new_pricing = Decimal("0.04")
        data: Dict[str, Any] = {
            "pricing_input": new_pricing,
            "pricing_output": sample_supply_item.pricing_output
        }
        
        self._test_item_update(service, sample_supply_item, data, new_pricing)
    
    def test_update_existing_item_multiple_changes(self, service, sample_supply_item):
        """Test updating item with multiple field changes"""
        data: Dict[str, Any] = {
            "pricing_input": Decimal("0.04"),
            "pricing_output": Decimal("0.08"),
            "context_window": 16384,
            "confidence_score": 0.95
        }
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = sample_supply_item
            
            with patch('app.services.supply_research_service.SupplyUpdateLog'):
                result = service.create_or_update_supply_item("openai", "gpt-4", data)
        
        assert sample_supply_item.pricing_input == Decimal("0.04")
        assert sample_supply_item.pricing_output == Decimal("0.08")
        assert sample_supply_item.context_window == 16384
        assert sample_supply_item.confidence_score == 0.95
    
    def _test_item_update(self, service, item, data: Dict[str, Any], expected_pricing):
        """Helper method for item update tests"""
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = item
            
            with patch('app.services.supply_research_service.SupplyUpdateLog'):
                result = service.create_or_update_supply_item("openai", "gpt-4", data, "session-1")
        
        assert result == item
        assert item.pricing_input == expected_pricing


class TestUpdateLogOperations:
    """Test update log retrieval and filtering"""
    
    def test_get_update_logs_no_filters(self, service, sample_update_log):
        """Test retrieving all update logs"""
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.order_by.return_value.limit.return_value
            mock_chain.all.return_value = [sample_update_log]
            
            result: List[SupplyUpdateLog] = service.get_update_logs()
            
            assert len(result) == 1
            assert result[0] == sample_update_log
    
    def test_get_update_logs_with_supply_item_filter(self, service, sample_update_log):
        """Test retrieving logs filtered by supply item ID"""
        with patch.object(service.db, 'query') as mock_query:
            self._setup_filtered_query_mock(mock_query, [sample_update_log])
            
            result: List[SupplyUpdateLog] = service.get_update_logs(
                supply_item_id="supply-item-1"
            )
            
            assert len(result) == 1
            assert result[0].supply_item_id == "supply-item-1"
    
    def test_get_update_logs_with_user_filter(self, service, sample_update_log):
        """Test retrieving logs filtered by updated_by user"""
        sample_update_log.updated_by = "system"
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_filtered_query_mock(mock_query, [sample_update_log])
            
            result: List[SupplyUpdateLog] = service.get_update_logs(updated_by="system")
            
            assert len(result) == 1
            assert result[0].updated_by == "system"
    
    def test_get_update_logs_with_date_range(self, service, sample_update_log):
        """Test retrieving logs within date range"""
        from datetime import timedelta
        
        start_date = datetime.now(UTC) - timedelta(days=1)
        end_date = datetime.now(UTC) + timedelta(days=1)
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_date_filtered_query_mock(mock_query, [sample_update_log])
            
            result: List[SupplyUpdateLog] = service.get_update_logs(
                start_date=start_date, end_date=end_date
            )
            
            assert len(result) == 1
    
    def test_get_update_logs_with_custom_limit(self, service):
        """Test retrieving logs with custom result limit"""
        logs = [MagicMock(spec=SupplyUpdateLog) for _ in range(10)]
        
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.order_by.return_value.limit.return_value
            mock_chain.all.return_value = logs[:3]  # Simulate limit=3
            
            result: List[SupplyUpdateLog] = service.get_update_logs(limit=3)
            
            assert len(result) == 3
    
    def _setup_filtered_query_mock(self, mock_query, return_logs: List[SupplyUpdateLog]):
        """Helper to setup filtered query mock"""
        mock_chain = (mock_query.return_value.filter.return_value
                     .order_by.return_value.limit.return_value)
        mock_chain.all.return_value = return_logs
    
    def _setup_date_filtered_query_mock(self, mock_query, return_logs: List[SupplyUpdateLog]):
        """Helper to setup date-filtered query mock"""
        mock_chain = (mock_query.return_value.filter.return_value.filter.return_value
                     .order_by.return_value.limit.return_value)
        mock_chain.all.return_value = return_logs


class TestTransactionHandling:
    """Test database transaction handling and error recovery"""
    
    def test_successful_transaction_commit(self, service):
        """Test successful database transaction commit"""
        data: Dict[str, Any] = {"confidence_score": 0.9}
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            with patch('app.services.supply_research_service.AISupplyItem'):
                with patch('app.services.supply_research_service.SupplyUpdateLog'):
                    service.create_or_update_supply_item("openai", "test-model", data)
    
    def test_error_handling_during_creation(self, service):
        """Test error handling during item creation"""
        with patch.object(service.db, 'query', side_effect=Exception("DB Error")):
            with pytest.raises(Exception):
                service.create_or_update_supply_item("openai", "test", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])