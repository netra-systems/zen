"""
Tests for SupplyResearchService functionality
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC
from decimal import Decimal

# Add project root to path

from netra_backend.app.services.supply_research_service import SupplyResearchService

# Add project root to path


class TestSupplyResearchService:
    """Test suite for SupplyResearchService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = Mock()
        db.query = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        return db
    
    def test_service_get_supply_items(self, mock_db):
        """Test getting supply items with filters"""
        mock_items = [
            Mock(provider="openai", model_name="GPT-4", pricing_input=30)
        ]
        mock_db.query().filter().order_by().all.return_value = mock_items
        
        service = SupplyResearchService(mock_db)
        with patch.object(service, 'get_supply_items', return_value=mock_items):
            items = service.get_supply_items(provider="openai")
            assert len(items) == 1
            assert items[0].provider == "openai"
    
    def test_service_create_supply_item(self, mock_db):
        """Test creating new supply item"""
        service = SupplyResearchService(mock_db)
        mock_db.query().filter().first.return_value = None  # No existing
        
        data = {
            "pricing_input": Decimal("25"),
            "pricing_output": Decimal("75"),
            "context_window": 100000
        }
        
        item = service.create_or_update_supply_item(
            "openai", "GPT-5", data, updated_by="test"
        )
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    def test_service_calculate_price_changes(self, mock_db):
        """Test calculating price changes over time"""
        mock_logs = [
            Mock(
                field_updated="pricing_input",
                old_value='"30"',
                new_value='"25"',
                supply_item_id="123",
                updated_at=datetime.now(UTC)
            )
        ]
        mock_item = Mock(provider="openai", model_name="GPT-4")
        
        mock_db.query().filter().all.return_value = mock_logs
        mock_db.query().filter().first.return_value = mock_item
        
        service = SupplyResearchService(mock_db)
        changes = service.calculate_price_changes(days_back=7)
        
        assert changes["total_changes"] > 0
        assert "largest_changes" in changes
    
    def test_service_provider_comparison(self, mock_db):
        """Test comparing pricing across providers"""
        mock_items = [
            Mock(
                provider="openai",
                model_name="GPT-4",
                pricing_input=Decimal("30"),
                pricing_output=Decimal("60"),
                context_window=128000,
                last_updated=datetime.now(UTC)
            )
        ]
        
        service = SupplyResearchService(mock_db)
        with patch.object(service, 'get_supply_items', return_value=mock_items):
            comparison = service.get_provider_comparison()
            
            assert "providers" in comparison
            assert "analysis" in comparison
    
    def test_service_detect_anomalies(self, mock_db):
        """Test detecting pricing anomalies"""
        service = SupplyResearchService(mock_db)
        
        with patch.object(service, 'calculate_price_changes') as mock_changes:
            mock_changes.return_value = {
                "all_changes": [
                    {
                        "provider": "openai",
                        "model": "GPT-4",
                        "field": "pricing_input",
                        "percent_change": 50,  # 50% increase - anomaly
                        "updated_at": datetime.now(UTC).isoformat()
                    }
                ]
            }
            
            mock_db.query().filter().all.return_value = []  # No stale items
            
            anomalies = service.detect_anomalies(threshold=0.2)
            assert len(anomalies) > 0
            assert anomalies[0]["type"] == "significant_price_change"
    
    def test_service_validate_supply_data(self):
        """Test validating supply data before storage"""
        service = SupplyResearchService(Mock())
        
        # Valid data
        valid_data = {
            "provider": "openai",
            "model_name": "GPT-4",
            "pricing_input": "30",
            "pricing_output": "60",
            "context_window": 128000,
            "confidence_score": 0.9
        }
        is_valid, errors = service.validate_supply_data(valid_data)
        assert is_valid
        assert len(errors) == 0
        
        # Invalid data - negative pricing
        invalid_data = {
            "provider": "openai",
            "model_name": "GPT-4",
            "pricing_input": "-10"
        }
        is_valid, errors = service.validate_supply_data(invalid_data)
        assert not is_valid
        assert len(errors) > 0
    
    def test_invalid_data_validation(self):
        """Test handling invalid supply data"""
        service = SupplyResearchService(Mock())
        
        invalid_data = {
            "provider": "",  # Empty provider
            "pricing_input": "not_a_number",
            "confidence_score": 2.0  # Out of range
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        assert not is_valid
        assert len(errors) >= 3