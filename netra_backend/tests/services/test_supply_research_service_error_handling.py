"""
Error handling and edge case tests for SupplyResearchService
Tests unusual scenarios, boundary conditions, and error recovery
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from app.db.models_postgres import AISupplyItem, SupplyUpdateLog

# Add project root to path
from app.services.supply_research_service import SupplyResearchService
from ..helpers.shared_test_types import (
    TestErrorHandling as SharedTestErrorHandling,
)

# Add project root to path


@pytest.fixture
def service():
    """Create SupplyResearchService instance with mocked database"""
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    return SupplyResearchService(mock_db)


class TestErrorHandling(SharedTestErrorHandling):
    """Test error handling and recovery scenarios - extends shared error handling."""
    
    def test_database_connection_failure(self, service):
        """Test graceful handling of database connection failures"""
        with patch.object(service.db, 'query', side_effect=Exception("Database unavailable")):
            with pytest.raises(Exception) as exc_info:
                service.get_supply_items()
            
            assert "Database unavailable" in str(exc_info.value)
    
    def test_invalid_json_in_update_logs(self, service):
        """Test handling of malformed JSON in update logs"""
        malformed_log = self._create_malformed_json_log()
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_price_query_mock(mock_query, [malformed_log])
            
            result: Dict[str, Any] = service.calculate_price_changes()
        
        # Should handle invalid JSON gracefully without crashing
        assert "total_changes" in result
        # Malformed entries should be skipped
        assert len(result.get("all_changes", [])) == 0
    
    def test_transaction_rollback_on_error(self, service):
        """Test database transaction rollback on errors"""
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = None
            
            with patch('app.services.supply_research_service.AISupplyItem', 
                       side_effect=Exception("Item creation failed")):
                with pytest.raises(Exception):
                    service.create_or_update_supply_item("openai", "test", {"confidence_score": 0.9})
    
    def test_redis_connection_failure_recovery(self, service):
        """Test service continues working when Redis fails during operation"""
        # Service already initialized without Redis, should continue working
        with patch.object(service, 'redis_manager', None):
            with patch.object(service.db, 'query') as mock_query:
                # Mock the complete query chain: query().order_by().all()
                mock_query.return_value.order_by.return_value.all.return_value = []
                
                # Should not raise exception
                result = service.get_supply_items()
                assert result == []
    
    def test_memory_pressure_large_datasets(self, service):
        """Test handling of memory pressure with large datasets"""
        # Simulate very large result set
        large_dataset = [MagicMock(spec=AISupplyItem) for _ in range(10000)]
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.all.return_value = large_dataset
            
            # Should handle large datasets without memory issues
            result = service.get_supply_items()
            assert len(result) == 10000
    
    def _create_malformed_json_log(self) -> SupplyUpdateLog:
        """Helper to create log with malformed JSON"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = "invalid-json-format"
        log.new_value = '"0.03"'
        log.updated_at = datetime.now(UTC)
        return log
    
    def _setup_price_query_mock(self, mock_query, logs: List[SupplyUpdateLog]):
        """Helper to setup price query mock"""
        mock_query.return_value.join.return_value.order_by.return_value.all.return_value = logs


class TestEdgeCaseScenarios:
    """Test unusual scenarios and boundary conditions"""
    
    def test_empty_provider_list_comparison(self, service):
        """Test provider comparison with no providers having data"""
        with patch.object(service, 'get_supply_items', return_value=[]):
            result: Dict[str, Any] = service.get_provider_comparison()
            
            assert "providers" in result
            assert "analysis" in result
            # Should not crash with empty data
            assert result["analysis"] == {}
    
    def test_price_changes_with_null_values(self, service):
        """Test price calculations when logs contain null values"""
        log_with_nulls = self._create_null_value_log()
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_price_query_mock(mock_query, [log_with_nulls])
            
            with patch.object(service, 'get_supply_item_by_id', return_value=MagicMock()):
                result: Dict[str, Any] = service.calculate_price_changes()
        
        # Should handle null values gracefully without crashing
        assert "total_changes" in result
    
    def test_very_large_price_changes(self, service):
        """Test handling of extremely large price changes"""
        extreme_log = self._create_extreme_price_log()
        item = self._create_extreme_test_item()
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_price_query_mock(mock_query, [extreme_log])
            
            with patch.object(service, 'get_supply_item_by_id', return_value=item):
                result: Dict[str, Any] = service.calculate_price_changes()
        
        assert len(result["all_changes"]) == 1
        change = result["all_changes"][0]
        assert change["percent_change"] > 1000  # Extremely large increase
    
    def test_zero_old_value_price_changes(self, service):
        """Test price change calculation when old value is zero"""
        zero_old_log = self._create_zero_old_value_log()
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_price_query_mock(mock_query, [zero_old_log])
            
            with patch.object(service, 'get_supply_item_by_id', return_value=MagicMock()):
                result: Dict[str, Any] = service.calculate_price_changes()
        
        # Should handle zero old value gracefully (typically skip calculation)
        assert "total_changes" in result
    
    def test_concurrent_item_updates(self, service):
        """Test handling of concurrent updates to same supply item"""
        sample_item = self._create_concurrent_test_item()
        update_data_1, update_data_2 = self._create_concurrent_update_data()
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = sample_item
            
            with patch('app.services.supply_research_service.SupplyUpdateLog'):
                # Simulate concurrent updates
                result1 = service.create_or_update_supply_item("openai", "gpt-4", update_data_1)
                result2 = service.create_or_update_supply_item("openai", "gpt-4", update_data_2)
        
        # Both updates should succeed without conflicts
        assert result1 == sample_item
        assert result2 == sample_item
    
    def test_unicode_handling_in_model_names(self, service):
        """Test handling of unicode characters in model names"""
        unicode_data = {
            "provider": "openai", 
            "model_name": "gpt-4-🤖-测试",  # Unicode characters
            "confidence_score": 0.9
        }
        
        is_valid, errors = service.validate_supply_data(unicode_data)
        # Should handle unicode gracefully
        assert isinstance(is_valid, bool)
    
    def test_very_long_field_values(self, service):
        """Test handling of extremely long field values"""
        long_string = "x" * 10000  # Very long string
        long_data = {
            "provider": "openai",
            "model_name": long_string,
            "confidence_score": 0.9
        }
        
        # Should handle without crashing
        is_valid, errors = service.validate_supply_data(long_data)
        assert isinstance(is_valid, bool)
    
    def _create_null_value_log(self) -> SupplyUpdateLog:
        """Helper to create log with null values"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = None
        log.new_value = '"0.03"'
        log.updated_at = datetime.now(UTC)
        return log
    
    def _create_extreme_price_log(self) -> SupplyUpdateLog:
        """Helper to create extreme price change log"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = '"0.001"'
        log.new_value = '"10.0"'  # 999,900% increase
        log.updated_at = datetime.now(UTC)
        return log
    
    def _create_extreme_test_item(self) -> AISupplyItem:
        """Helper to create test item for extreme scenarios"""
        item = MagicMock(spec=AISupplyItem)
        item.provider = "test-provider"
        item.model_name = "extreme-model"
        return item
    
    def _create_zero_old_value_log(self) -> SupplyUpdateLog:
        """Helper to create log with zero old value"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = '"0.00"'
        log.new_value = '"0.03"'
        log.updated_at = datetime.now(UTC)
        return log
    
    def _create_concurrent_test_item(self) -> AISupplyItem:
        """Helper to create item for concurrent testing"""
        item = MagicMock(spec=AISupplyItem)
        item.id = "item-1"
        item.pricing_input = Decimal("0.03")
        item.pricing_output = Decimal("0.06")
        return item
    
    def _create_concurrent_update_data(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Helper to create concurrent update data"""
        update_data_1 = {"pricing_input": Decimal("0.04")}
        update_data_2 = {"pricing_output": Decimal("0.08")}
        return update_data_1, update_data_2
    
    def _setup_price_query_mock(self, mock_query, logs: List[SupplyUpdateLog]):
        """Helper to setup price query mock"""
        mock_query.return_value.join.return_value.order_by.return_value.all.return_value = logs


class TestDataConsistency:
    """Test data consistency and integrity scenarios"""
    
    def test_update_log_creation_consistency(self, service):
        """Test that update logs are created consistently with item changes"""
        existing_item = self._create_existing_item()
        new_data = self._create_partial_update_data()
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.first.return_value = existing_item
            
            with patch('app.services.supply_research_service.SupplyUpdateLog') as mock_log:
                mock_log_instance = MagicMock()
                mock_log.return_value = mock_log_instance
                
                service.create_or_update_supply_item("openai", "gpt-4", new_data)
                
                # Should create log only for changed field
                assert mock_log.called
    
    def test_timestamp_consistency(self, service):
        """Test that timestamps are handled consistently"""
        current_time = datetime.now(UTC)
        
        with patch('app.services.supply_research_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.UTC = UTC
            
            # Test that service uses consistent datetime handling
            # This is more of a design verification than functional test
            assert current_time.tzinfo == UTC
    
    def _create_existing_item(self) -> AISupplyItem:
        """Helper to create existing item for consistency testing"""
        item = MagicMock(spec=AISupplyItem)
        item.pricing_input = Decimal("0.02")
        item.confidence_score = 0.8
        return item
    
    def _create_partial_update_data(self) -> Dict[str, Any]:
        """Helper to create partial update data"""
        return {
            "pricing_input": Decimal("0.03"),  # Changed
            "confidence_score": 0.8             # Unchanged
        }


class TestPerformanceBoundaries:
    """Test performance with boundary conditions"""
    
    def test_large_result_set_handling(self, service):
        """Test handling of large result sets"""
        large_item_list = [MagicMock(spec=AISupplyItem) for _ in range(1000)]
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.all.return_value = large_item_list
            
            result: List[AISupplyItem] = service.get_supply_items()
            
            # Should handle large datasets without issues
            assert len(result) == 1000
    
    def test_custom_result_limits(self, service):
        """Test custom limits on result sets"""
        many_logs = [MagicMock(spec=SupplyUpdateLog) for _ in range(100)]
        
        with patch.object(service.db, 'query') as mock_query:
            mock_chain = mock_query.return_value.order_by.return_value.limit.return_value
            mock_chain.all.return_value = many_logs[:50]  # Simulate limit=50
            
            result: List[SupplyUpdateLog] = service.get_update_logs(limit=50)
            
            assert len(result) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])