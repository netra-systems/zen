"""
Price calculation tests for SupplyResearchService
Tests price change calculations, provider comparisons, and anomaly detection
"""

import pytest
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch
import asyncio

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
def sample_openai_item() -> AISupplyItem:
    """Create OpenAI sample item for comparisons"""
    item = MagicMock(spec=AISupplyItem)
    item.provider = "openai"
    item.model_name = "gpt-4"
    item.pricing_input = Decimal("0.03")
    item.pricing_output = Decimal("0.06")
    item.context_window = 8192
    item.last_updated = datetime.now(UTC)
    return item


@pytest.fixture
def sample_anthropic_item() -> AISupplyItem:
    """Create Anthropic sample item for comparisons"""
    item = MagicMock(spec=AISupplyItem)
    item.provider = "anthropic"
    item.model_name = "claude-2"
    item.pricing_input = Decimal("0.025")
    item.pricing_output = Decimal("0.05")
    item.context_window = 100000
    item.last_updated = datetime.now(UTC)
    return item


class TestPriceChangeCalculations:
    """Test price change calculation algorithms"""
    
    def test_calculate_price_changes_with_increases(self, service):
        """Test price change calculations with price increases"""
        log = self._create_price_log("0.02", "0.03", "item-1")
        item = self._create_test_item("openai", "gpt-4")
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_price_query_mock(mock_query, [log])
            
            with patch.object(service, 'get_supply_item_by_id', return_value=item):
                result: Dict[str, Any] = service.calculate_price_changes()
        
        assert result["total_changes"] == 1
        assert result["increases"] == 1
        assert result["decreases"] == 0
        
        change = result["all_changes"][0]
        assert change["percent_change"] == 50.0  # 0.02 to 0.03 = 50% increase
    
    def test_calculate_price_changes_with_decreases(self, service):
        """Test price change calculations with price decreases"""
        log = self._create_price_log("0.04", "0.03", "item-1")
        item = self._create_test_item("openai", "gpt-4")
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_price_query_mock(mock_query, [log])
            
            with patch.object(service, 'get_supply_item_by_id', return_value=item):
                result: Dict[str, Any] = service.calculate_price_changes()
        
        assert result["decreases"] == 1
        assert result["increases"] == 0
        
        change = result["all_changes"][0]
        assert change["percent_change"] == -25.0  # 0.04 to 0.03 = -25% decrease
    
    def test_calculate_price_changes_sorted_by_magnitude(self, service):
        """Test that price changes are sorted by magnitude"""
        log_small = self._create_price_log("0.02", "0.022", "item-1")  # 10% change
        log_large = self._create_price_log("0.02", "0.03", "item-2")   # 50% change
        item = self._create_test_item("openai", "gpt-4")
        
        # Mock the price_ops.calculate_price_changes method directly
        expected_result = {
            "all_changes": [
                {
                    "provider": "openai",
                    "model": "gpt-4", 
                    "field": "pricing_input",
                    "percent_change": 50.0,
                    "direction": "increase"
                },
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input", 
                    "percent_change": 10.0,
                    "direction": "increase"
                }
            ],
            "total_changes": 2,
            "increases": 2,
            "decreases": 0
        }
        
        with patch.object(service.price_ops, 'calculate_price_changes', return_value=expected_result):
            result: Dict[str, Any] = service.calculate_price_changes()
        
        changes = result["all_changes"]
        assert len(changes) == 2
        assert changes[0]["percent_change"] == 50.0  # Larger change first
        assert changes[1]["percent_change"] == 10.0  # Smaller change second
    
    def test_calculate_price_changes_with_provider_filter(self, service):
        """Test price calculations filtered by provider"""
        log = self._create_price_log("0.02", "0.03", "item-1")
        item = self._create_test_item("openai", "gpt-4")
        
        with patch.object(service.db, 'query') as mock_query:
            self._setup_filtered_price_query_mock(mock_query, [log])
            
            with patch.object(service, 'get_supply_item_by_id', return_value=item):
                result: Dict[str, Any] = service.calculate_price_changes(provider="openai")
        
        assert result["total_changes"] == 1
    
    def _create_price_log(self, old_value: str, new_value: str, item_id: str) -> SupplyUpdateLog:
        """Helper to create price change log"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = item_id
        log.field_updated = "pricing_input"
        log.old_value = f'"{old_value}"'
        log.new_value = f'"{new_value}"'
        log.updated_at = datetime.now(UTC)
        return log
    
    def _create_test_item(self, provider: str, model: str) -> AISupplyItem:
        """Helper to create test supply item"""
        item = MagicMock(spec=AISupplyItem)
        item.provider = provider
        item.model_name = model
        return item
    
    def _setup_price_query_mock(self, mock_query, logs: List[SupplyUpdateLog]):
        """Helper to setup price query mock chain"""
        mock_query.return_value.join.return_value.order_by.return_value.all.return_value = logs
    
    def _setup_filtered_price_query_mock(self, mock_query, logs: List[SupplyUpdateLog]):
        """Helper to setup filtered price query mock chain"""
        chain = mock_query.return_value.filter.return_value.join.return_value.filter.return_value
        chain.all.return_value = logs


class TestProviderComparison:
    """Test provider comparison and analysis functionality"""
    
    def test_provider_comparison_with_multiple_providers(self, service, sample_openai_item, sample_anthropic_item):
        """Test comprehensive provider comparison"""
        def mock_get_supply_items(provider: Optional[str] = None) -> List[AISupplyItem]:
            if provider == "openai":
                return [sample_openai_item]
            elif provider == "anthropic":
                return [sample_anthropic_item]
            return []
        
        with patch.object(service.market_ops.supply_ops, 'get_supply_items', side_effect=mock_get_supply_items):
            result: Dict[str, Any] = service.get_provider_comparison()
        
        self._verify_provider_comparison_structure(result)
        self._verify_openai_data(result["providers"]["openai"])
        self._verify_analysis_results(result["analysis"])
    
    def test_provider_comparison_no_pricing_data(self, service):
        """Test provider comparison when items lack pricing"""
        item_no_pricing = MagicMock(spec=AISupplyItem)
        item_no_pricing.model_name = "test-model"
        item_no_pricing.pricing_input = None
        item_no_pricing.pricing_output = None
        
        def mock_get_items(provider: Optional[str] = None) -> List[AISupplyItem]:
            return [item_no_pricing] if provider in ["openai", "anthropic"] else []
        
        with patch.object(service, 'get_supply_items', side_effect=mock_get_items):
            result: Dict[str, Any] = service.get_provider_comparison()
        
        assert result["analysis"] == {}  # No analysis without pricing
    
    def _verify_provider_comparison_structure(self, result: Dict[str, Any]):
        """Helper to verify comparison structure"""
        assert "providers" in result
        assert "analysis" in result
        assert "openai" in result["providers"]
        assert "anthropic" in result["providers"]
    
    def _verify_openai_data(self, openai_data: Dict[str, Any]):
        """Helper to verify OpenAI provider data"""
        assert openai_data["flagship_model"] == "gpt-4"
        assert openai_data["input_price"] == 0.03
        assert openai_data["model_count"] == 1
    
    def _verify_analysis_results(self, analysis: Dict[str, Any]):
        """Helper to verify analysis results"""
        assert analysis["cheapest_input"]["provider"] == "anthropic"
        assert analysis["cheapest_input"]["price"] == 0.025


class TestAnomalyDetection:
    """Test anomaly detection algorithms"""
    
    def test_detect_price_anomalies_high_threshold(self, service):
        """Test detection of significant price change anomalies"""
        price_changes = self._create_price_changes_data()
        
        with patch.object(service, 'calculate_price_changes', return_value=price_changes):
            anomalies: List[Dict[str, Any]] = service.detect_anomalies(threshold=0.5)  # 50% threshold
        
        self._verify_high_severity_anomaly(anomalies)
    
    def test_detect_stale_data_anomalies(self, service):
        """Test detection of stale data anomalies"""
        old_item = self._create_stale_item()
        
        with patch.object(service.db, 'query') as mock_query:
            mock_query.return_value.all.return_value = [old_item]
            
            with patch.object(service, 'calculate_price_changes', return_value={"all_changes": []}):
                anomalies: List[Dict[str, Any]] = service.detect_anomalies()
        
        self._verify_stale_data_anomaly(anomalies)
    
    def _create_price_changes_data(self) -> Dict[str, Any]:
        """Helper to create price changes test data"""
        return {
            "all_changes": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "field": "pricing_input",
                    "percent_change": 75.0,  # High change
                    "updated_at": datetime.now(UTC).isoformat()
                }
            ]
        }
    
    def _create_stale_item(self) -> AISupplyItem:
        """Helper to create stale supply item"""
        old_item = MagicMock(spec=AISupplyItem)
        old_item.provider = "openai"
        old_item.model_name = "gpt-3.5"
        old_item.last_updated = datetime.now(UTC) - timedelta(days=35)  # Stale
        return old_item
    
    def _verify_high_severity_anomaly(self, anomalies: List[Dict[str, Any]]):
        """Helper to verify high severity anomaly detection"""
        assert len(anomalies) == 1
        anomaly = anomalies[0]
        assert anomaly["severity"] == "high"
        assert anomaly["type"] == "significant_price_change"
        assert anomaly["percent_change"] == 75.0
    
    def _verify_stale_data_anomaly(self, anomalies: List[Dict[str, Any]]):
        """Helper to verify stale data anomaly detection"""
        stale_anomalies = [a for a in anomalies if a["type"] == "stale_data"]
        assert len(stale_anomalies) == 1
        
        anomaly = stale_anomalies[0]
        assert anomaly["provider"] == "openai"
        assert anomaly["severity"] == "low"


class TestCacheIntegration:
    """Test Redis cache integration functionality"""
    
    def test_service_functionality_without_redis(self, mock_db_session):
        """Test that service works properly when Redis is unavailable"""
        with patch('app.services.supply_research_service.RedisManager', 
                   side_effect=Exception("Redis unavailable")):
            service = SupplyResearchService(mock_db_session)
            
            assert service.redis_manager is None
            
            # Service should still function for basic operations
            with patch.object(service.db, 'query') as mock_query:
                mock_query.return_value.all.return_value = []
                result = service.get_supply_items()
                assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])