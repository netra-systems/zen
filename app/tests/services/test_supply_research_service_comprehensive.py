"""
Comprehensive tests for SupplyResearchService with complete coverage
Tests business logic, database operations, price calculations, validation, and error handling
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch, call
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.supply_research_service import SupplyResearchService
from app.db.models_postgres import AISupplyItem, ResearchSession, SupplyUpdateLog, User


class MockSession:
    """Mock database session for testing"""
    def __init__(self):
        self.query_results = {}
        self.added_objects = []
        self.committed = False
        self.rollback_called = False
        self.queries = []
    
    def query(self, model):
        self.queries.append(("query", model))
        return MockQuery(self.query_results.get(model, []))
    
    def add(self, obj):
        self.added_objects.append(obj)
    
    def commit(self):
        self.committed = True
    
    def rollback(self):
        self.rollback_called = True


class MockQuery:
    """Mock database query for testing"""
    def __init__(self, results):
        self.results = results
        self.filters = []
        self.joins = []
        self.orders = []
        self._limit = None
    
    def filter(self, *args):
        self.filters.extend(args)
        return self
    
    def join(self, *args):
        self.joins.extend(args)
        return self
    
    def order_by(self, *args):
        self.orders.extend(args)
        return self
    
    def limit(self, count):
        self._limit = count
        return self
    
    def first(self):
        return self.results[0] if self.results else None
    
    def all(self):
        if self._limit:
            return self.results[:self._limit]
        return self.results
    
    def count(self):
        return len(self.results)
    
    def update(self, values):
        return len(self.results)


class MockRedisManager:
    """Mock Redis manager for testing"""
    def __init__(self, available=True):
        self.available = available
        self.data = {}
    
    def __init__(self):
        if not self.available:
            raise Exception("Redis not available")


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MockSession()


@pytest.fixture
def service(mock_db):
    """Create SupplyResearchService instance"""
    return SupplyResearchService(mock_db)


@pytest.fixture
def sample_supply_item():
    """Create sample AISupplyItem"""
    item = MagicMock(spec=AISupplyItem)
    item.id = "supply-item-1"
    item.provider = "openai"
    item.model_name = "gpt-4"
    item.pricing_input = Decimal("0.03")
    item.pricing_output = Decimal("0.06")
    item.context_window = 8192
    item.max_output_tokens = 4096
    item.capabilities = ["text-generation", "code"]
    item.availability_status = "available"
    item.api_endpoints = ["https://api.openai.com"]
    item.performance_metrics = {"latency_p50": 100}
    item.confidence_score = 0.9
    item.research_source = "official-api"
    item.last_updated = datetime.utcnow()
    return item


@pytest.fixture
def sample_research_session():
    """Create sample ResearchSession"""
    session = MagicMock(spec=ResearchSession)
    session.id = "session-1"
    session.query = "Research latest pricing for GPT-4"
    session.status = "completed"
    session.initiated_by = "user-1"
    session.created_at = datetime.utcnow()
    return session


@pytest.fixture
def sample_update_log():
    """Create sample SupplyUpdateLog"""
    log = MagicMock(spec=SupplyUpdateLog)
    log.id = "log-1"
    log.supply_item_id = "supply-item-1"
    log.field_updated = "pricing_input"
    log.old_value = "0.02"
    log.new_value = "0.03"
    log.research_session_id = "session-1"
    log.update_reason = "Price update"
    log.updated_by = "system"
    log.updated_at = datetime.utcnow()
    return log


class TestServiceInitialization:
    """Test service initialization"""
    
    def test_initialization_with_redis(self, mock_db):
        """Test initialization with Redis available"""
        with patch('app.services.supply_research_service.RedisManager') as mock_redis_class:
            mock_redis_instance = MockRedisManager()
            mock_redis_class.return_value = mock_redis_instance
            
            service = SupplyResearchService(mock_db)
            
            assert service.db == mock_db
            assert service.redis_manager == mock_redis_instance
            assert service.cache_ttl == 3600
    
    def test_initialization_without_redis(self, mock_db):
        """Test initialization when Redis is not available"""
        with patch('app.services.supply_research_service.RedisManager', side_effect=Exception("Redis not available")):
            service = SupplyResearchService(mock_db)
            
            assert service.db == mock_db
            assert service.redis_manager == None
            assert service.cache_ttl == 3600


class TestSupplyItemRetrieval:
    """Test supply item retrieval methods"""
    
    def test_get_supply_items_no_filters(self, service, sample_supply_item):
        """Test getting supply items without filters"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_items()
        
        assert len(result) == 1
        assert result[0] == sample_supply_item
        
        # Verify query was constructed correctly
        query_calls = [call for call in service.db.queries if call[0] == "query"]
        assert len(query_calls) == 1
        assert query_calls[0][1] == AISupplyItem
    
    def test_get_supply_items_with_provider_filter(self, service, sample_supply_item):
        """Test getting supply items filtered by provider"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_items(provider="openai")
        
        assert len(result) == 1
        assert result[0] == sample_supply_item
    
    def test_get_supply_items_with_model_name_filter(self, service, sample_supply_item):
        """Test getting supply items filtered by model name"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_items(model_name="gpt")
        
        assert len(result) == 1
        assert result[0] == sample_supply_item
    
    def test_get_supply_items_with_availability_filter(self, service, sample_supply_item):
        """Test getting supply items filtered by availability"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_items(availability_status="available")
        
        assert len(result) == 1
        assert result[0] == sample_supply_item
    
    def test_get_supply_items_with_confidence_filter(self, service, sample_supply_item):
        """Test getting supply items filtered by minimum confidence"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_items(min_confidence=0.8)
        
        assert len(result) == 1
        assert result[0] == sample_supply_item
    
    def test_get_supply_items_all_filters(self, service, sample_supply_item):
        """Test getting supply items with all filters applied"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_items(
            provider="openai",
            model_name="gpt",
            availability_status="available",
            min_confidence=0.8
        )
        
        assert len(result) == 1
        assert result[0] == sample_supply_item
    
    def test_get_supply_items_empty_result(self, service):
        """Test getting supply items when no items match"""
        service.db.query_results[AISupplyItem] = []
        
        result = service.get_supply_items()
        
        assert len(result) == 0
    
    def test_get_supply_item_by_id_exists(self, service, sample_supply_item):
        """Test getting supply item by ID when it exists"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        result = service.get_supply_item_by_id("supply-item-1")
        
        assert result == sample_supply_item
    
    def test_get_supply_item_by_id_not_exists(self, service):
        """Test getting supply item by ID when it doesn't exist"""
        service.db.query_results[AISupplyItem] = []
        
        result = service.get_supply_item_by_id("non-existent-id")
        
        assert result == None


class TestSupplyItemCreateUpdate:
    """Test supply item creation and updates"""
    
    def test_create_or_update_supply_item_new(self, service):
        """Test creating new supply item"""
        service.db.query_results[AISupplyItem] = []  # No existing item
        
        data = {
            "pricing_input": Decimal("0.03"),
            "pricing_output": Decimal("0.06"),
            "context_window": 8192,
            "capabilities": ["text-generation"],
            "availability_status": "available",
            "confidence_score": 0.9,
            "research_source": "official-api"
        }
        
        with patch('app.services.supply_research_service.SupplyUpdateLog') as mock_log_class:
            with patch('app.services.supply_research_service.AISupplyItem') as mock_item_class:
                mock_item = MagicMock()
                mock_item.id = "new-item-id"
                mock_item_class.return_value = mock_item
                
                result = service.create_or_update_supply_item(
                    "openai",
                    "gpt-4",
                    data,
                    research_session_id="session-1",
                    updated_by="test-user"
                )
        
        assert result == mock_item
        assert service.db.committed
        assert len(service.db.added_objects) == 2  # Item + log
    
    def test_create_or_update_supply_item_existing_no_changes(self, service, sample_supply_item):
        """Test updating existing supply item with no changes"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        # Data matches existing item
        data = {
            "pricing_input": sample_supply_item.pricing_input,
            "pricing_output": sample_supply_item.pricing_output,
            "context_window": sample_supply_item.context_window,
        }
        
        result = service.create_or_update_supply_item("openai", "gpt-4", data)
        
        assert result == sample_supply_item
        assert service.db.committed
        # Should not add any update logs for unchanged fields
        assert len([obj for obj in service.db.added_objects if isinstance(obj, SupplyUpdateLog)]) == 0
    
    def test_create_or_update_supply_item_existing_with_changes(self, service, sample_supply_item):
        """Test updating existing supply item with changes"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        # Change pricing
        new_pricing = Decimal("0.04")
        data = {
            "pricing_input": new_pricing,
            "pricing_output": sample_supply_item.pricing_output,
        }
        
        with patch('app.services.supply_research_service.SupplyUpdateLog') as mock_log_class:
            mock_log = MagicMock()
            mock_log_class.return_value = mock_log
            
            result = service.create_or_update_supply_item(
                "openai",
                "gpt-4",
                data,
                research_session_id="session-1"
            )
        
        assert result == sample_supply_item
        assert sample_supply_item.pricing_input == new_pricing
        assert sample_supply_item.last_updated != None
        assert service.db.committed
        # Should add update log
        assert len(service.db.added_objects) >= 1
    
    def test_create_or_update_supply_item_multiple_changes(self, service, sample_supply_item):
        """Test updating existing supply item with multiple changes"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        data = {
            "pricing_input": Decimal("0.04"),
            "pricing_output": Decimal("0.08"),
            "context_window": 16384,
            "confidence_score": 0.95
        }
        
        with patch('app.services.supply_research_service.SupplyUpdateLog') as mock_log_class:
            mock_log_class.return_value = MagicMock()
            
            result = service.create_or_update_supply_item("openai", "gpt-4", data)
        
        # All changed fields should be updated
        assert sample_supply_item.pricing_input == Decimal("0.04")
        assert sample_supply_item.pricing_output == Decimal("0.08")
        assert sample_supply_item.context_window == 16384
        assert sample_supply_item.confidence_score == 0.95
        
        # Should create multiple update logs
        added_logs = len(service.db.added_objects)
        assert added_logs >= 3  # At least 3 changes logged


class TestResearchSessionOperations:
    """Test research session operations"""
    
    def test_get_research_sessions_no_filters(self, service, sample_research_session):
        """Test getting research sessions without filters"""
        service.db.query_results[ResearchSession] = [sample_research_session]
        
        result = service.get_research_sessions()
        
        assert len(result) == 1
        assert result[0] == sample_research_session
    
    def test_get_research_sessions_with_status_filter(self, service, sample_research_session):
        """Test getting research sessions filtered by status"""
        service.db.query_results[ResearchSession] = [sample_research_session]
        
        result = service.get_research_sessions(status="completed")
        
        assert len(result) == 1
        assert result[0] == sample_research_session
    
    def test_get_research_sessions_with_user_filter(self, service, sample_research_session):
        """Test getting research sessions filtered by user"""
        service.db.query_results[ResearchSession] = [sample_research_session]
        
        result = service.get_research_sessions(initiated_by="user-1")
        
        assert len(result) == 1
        assert result[0] == sample_research_session
    
    def test_get_research_sessions_with_limit(self, service):
        """Test getting research sessions with custom limit"""
        # Create multiple sessions
        sessions = [MagicMock(spec=ResearchSession) for _ in range(10)]
        service.db.query_results[ResearchSession] = sessions
        
        result = service.get_research_sessions(limit=5)
        
        assert len(result) == 5
    
    def test_get_research_session_by_id_exists(self, service, sample_research_session):
        """Test getting research session by ID when it exists"""
        service.db.query_results[ResearchSession] = [sample_research_session]
        
        result = service.get_research_session_by_id("session-1")
        
        assert result == sample_research_session
    
    def test_get_research_session_by_id_not_exists(self, service):
        """Test getting research session by ID when it doesn't exist"""
        service.db.query_results[ResearchSession] = []
        
        result = service.get_research_session_by_id("non-existent")
        
        assert result == None


class TestUpdateLogOperations:
    """Test update log operations"""
    
    def test_get_update_logs_no_filters(self, service, sample_update_log):
        """Test getting update logs without filters"""
        service.db.query_results[SupplyUpdateLog] = [sample_update_log]
        
        result = service.get_update_logs()
        
        assert len(result) == 1
        assert result[0] == sample_update_log
    
    def test_get_update_logs_with_supply_item_filter(self, service, sample_update_log):
        """Test getting update logs filtered by supply item ID"""
        service.db.query_results[SupplyUpdateLog] = [sample_update_log]
        
        result = service.get_update_logs(supply_item_id="supply-item-1")
        
        assert len(result) == 1
        assert result[0] == sample_update_log
    
    def test_get_update_logs_with_user_filter(self, service, sample_update_log):
        """Test getting update logs filtered by updated_by"""
        service.db.query_results[SupplyUpdateLog] = [sample_update_log]
        
        result = service.get_update_logs(updated_by="system")
        
        assert len(result) == 1
        assert result[0] == sample_update_log
    
    def test_get_update_logs_with_date_filters(self, service, sample_update_log):
        """Test getting update logs filtered by date range"""
        service.db.query_results[SupplyUpdateLog] = [sample_update_log]
        
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        result = service.get_update_logs(
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(result) == 1
        assert result[0] == sample_update_log
    
    def test_get_update_logs_with_limit(self, service):
        """Test getting update logs with custom limit"""
        logs = [MagicMock(spec=SupplyUpdateLog) for _ in range(10)]
        service.db.query_results[SupplyUpdateLog] = logs
        
        result = service.get_update_logs(limit=3)
        
        assert len(result) == 3


class TestPriceChangeCalculations:
    """Test price change calculations"""
    
    def test_calculate_price_changes_no_provider_filter(self, service):
        """Test calculating price changes without provider filter"""
        # Create mock update logs
        log1 = MagicMock(spec=SupplyUpdateLog)
        log1.supply_item_id = "item-1"
        log1.field_updated = "pricing_input"
        log1.old_value = '"0.02"'
        log1.new_value = '"0.03"'
        log1.updated_at = datetime.utcnow()
        
        log2 = MagicMock(spec=SupplyUpdateLog)
        log2.supply_item_id = "item-2"
        log2.field_updated = "pricing_output"
        log2.old_value = '"0.05"'
        log2.new_value = '"0.06"'
        log2.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log1, log2]
        
        # Mock supply items for the logs
        item1 = MagicMock(spec=AISupplyItem)
        item1.provider = "openai"
        item1.model_name = "gpt-4"
        
        item2 = MagicMock(spec=AISupplyItem)
        item2.provider = "anthropic"
        item2.model_name = "claude-2"
        
        # Return appropriate items for each query
        def mock_query_side_effect(model):
            if model == SupplyUpdateLog:
                query = MockQuery([log1, log2])
                return query
            elif model == AISupplyItem:
                # Return different item based on supply_item_id filter
                if hasattr(query, 'filters') and any('item-1' in str(f) for f in query.filters):
                    return MockQuery([item1])
                elif hasattr(query, 'filters') and any('item-2' in str(f) for f in query.filters):
                    return MockQuery([item2])
                return MockQuery([item1, item2])
            return MockQuery([])
        
        # Create a more sophisticated mock
        with patch.object(service.db, 'query', side_effect=lambda model: (
            MockQuery([log1, log2]) if model == SupplyUpdateLog else
            MockQuery([item1]) if str(model).find('item-1') != -1 else
            MockQuery([item2]) if str(model).find('item-2') != -1 else
            MockQuery([item1])  # Default to item1
        )):
            # Need to mock the individual queries for supply items
            with patch.object(service, 'get_supply_item_by_id', side_effect=lambda item_id: item1 if item_id == 'item-1' else item2):
                result = service.calculate_price_changes()
        
        assert "total_changes" in result
        assert "all_changes" in result
        assert result["total_changes"] == 2
        assert len(result["all_changes"]) == 2
        
        # Check individual changes
        changes = result["all_changes"]
        assert changes[0]["provider"] == "openai"
        assert changes[0]["model"] == "gpt-4"
        assert changes[0]["field"] == "pricing_input"
        assert changes[0]["percent_change"] == 50.0  # 0.02 to 0.03 is 50% increase
    
    def test_calculate_price_changes_with_provider_filter(self, service):
        """Test calculating price changes with provider filter"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = '"0.02"'
        log.new_value = '"0.03"'
        log.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log]
        
        item = MagicMock(spec=AISupplyItem)
        item.provider = "openai"
        item.model_name = "gpt-4"
        
        with patch.object(service, 'get_supply_item_by_id', return_value=item):
            result = service.calculate_price_changes(provider="openai")
        
        assert result["total_changes"] == 1
        assert len(result["all_changes"]) == 1
    
    def test_calculate_price_changes_zero_old_value(self, service):
        """Test calculating price changes when old value is zero"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = '"0.00"'
        log.new_value = '"0.03"'
        log.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log]
        
        item = MagicMock(spec=AISupplyItem)
        item.provider = "openai"
        item.model_name = "gpt-4"
        
        with patch.object(service, 'get_supply_item_by_id', return_value=item):
            result = service.calculate_price_changes()
        
        # Should handle zero old value gracefully (skip calculation)
        assert len(result["all_changes"]) == 0
    
    def test_calculate_price_changes_invalid_json(self, service):
        """Test calculating price changes with invalid JSON in logs"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = 'invalid-json'
        log.new_value = '"0.03"'
        log.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log]
        
        result = service.calculate_price_changes()
        
        # Should handle invalid JSON gracefully
        assert len(result["all_changes"]) == 0
    
    def test_calculate_price_changes_no_changes(self, service):
        """Test calculating price changes when no changes exist"""
        service.db.query_results[SupplyUpdateLog] = []
        
        result = service.calculate_price_changes()
        
        assert result["total_changes"] == 0
        assert "message" in result
        assert "No price changes detected" in result["message"]
    
    def test_calculate_price_changes_sorting(self, service):
        """Test that price changes are sorted by magnitude"""
        # Create logs with different percentage changes
        log1 = MagicMock(spec=SupplyUpdateLog)
        log1.supply_item_id = "item-1"
        log1.field_updated = "pricing_input"
        log1.old_value = '"0.02"'  
        log1.new_value = '"0.022"'  # 10% increase
        log1.updated_at = datetime.utcnow()
        
        log2 = MagicMock(spec=SupplyUpdateLog)
        log2.supply_item_id = "item-2"
        log2.field_updated = "pricing_input"
        log2.old_value = '"0.02"'
        log2.new_value = '"0.03"'  # 50% increase
        log2.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log1, log2]
        
        item1 = MagicMock(spec=AISupplyItem)
        item1.provider = "openai"
        item1.model_name = "gpt-3.5"
        
        item2 = MagicMock(spec=AISupplyItem)
        item2.provider = "openai"
        item2.model_name = "gpt-4"
        
        with patch.object(service, 'get_supply_item_by_id', side_effect=lambda item_id: item1 if item_id == 'item-1' else item2):
            result = service.calculate_price_changes()
        
        # Should be sorted by percentage change magnitude (largest first)
        changes = result["all_changes"]
        assert len(changes) == 2
        assert changes[0]["percent_change"] == 50.0  # Larger change first
        assert changes[1]["percent_change"] == 10.0  # Smaller change second
    
    def test_calculate_price_changes_statistics(self, service):
        """Test that price change statistics are calculated correctly"""
        # Create logs with mix of increases and decreases
        log_increase = MagicMock(spec=SupplyUpdateLog)
        log_increase.supply_item_id = "item-1"
        log_increase.field_updated = "pricing_input"
        log_increase.old_value = '"0.02"'
        log_increase.new_value = '"0.03"'  # 50% increase
        log_increase.updated_at = datetime.utcnow()
        
        log_decrease = MagicMock(spec=SupplyUpdateLog)
        log_decrease.supply_item_id = "item-2"
        log_decrease.field_updated = "pricing_input"
        log_decrease.old_value = '"0.04"'
        log_decrease.new_value = '"0.03"'  # 25% decrease
        log_decrease.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log_increase, log_decrease]
        
        item = MagicMock(spec=AISupplyItem)
        item.provider = "openai"
        item.model_name = "gpt-4"
        
        with patch.object(service, 'get_supply_item_by_id', return_value=item):
            result = service.calculate_price_changes()
        
        assert result["total_changes"] == 2
        assert result["increases"] == 1
        assert result["decreases"] == 1
        assert result["average_increase_percent"] == 50.0
        assert result["average_decrease_percent"] == -25.0
        assert len(result["largest_changes"]) <= 10  # Top 10 limit


class TestProviderComparison:
    """Test provider comparison functionality"""
    
    def test_get_provider_comparison_with_data(self, service):
        """Test provider comparison with available data"""
        # Create mock items for different providers
        openai_item = MagicMock(spec=AISupplyItem)
        openai_item.model_name = "gpt-4"
        openai_item.pricing_input = Decimal("0.03")
        openai_item.pricing_output = Decimal("0.06")
        openai_item.context_window = 8192
        openai_item.last_updated = datetime.utcnow()
        
        anthropic_item = MagicMock(spec=AISupplyItem)
        anthropic_item.model_name = "claude-2"
        anthropic_item.pricing_input = Decimal("0.025")
        anthropic_item.pricing_output = Decimal("0.05")
        anthropic_item.context_window = 100000
        anthropic_item.last_updated = datetime.utcnow()
        
        def mock_get_supply_items(provider=None):
            if provider == "openai":
                return [openai_item]
            elif provider == "anthropic":
                return [anthropic_item]
            elif provider == "google":
                return []
            elif provider == "mistral":
                return []
            elif provider == "cohere":
                return []
            return []
        
        with patch.object(service, 'get_supply_items', side_effect=mock_get_supply_items):
            result = service.get_provider_comparison()
        
        assert "providers" in result
        assert "analysis" in result
        
        providers = result["providers"]
        assert "openai" in providers
        assert "anthropic" in providers
        
        # Check OpenAI data
        openai_data = providers["openai"]
        assert openai_data["flagship_model"] == "gpt-4"
        assert openai_data["input_price"] == 0.03
        assert openai_data["output_price"] == 0.06
        assert openai_data["context_window"] == 8192
        assert openai_data["model_count"] == 1
        
        # Check Anthropic data
        anthropic_data = providers["anthropic"]
        assert anthropic_data["flagship_model"] == "claude-2"
        assert anthropic_data["input_price"] == 0.025
        
        # Check analysis
        analysis = result["analysis"]
        assert analysis["cheapest_input"]["provider"] == "anthropic"
        assert analysis["cheapest_input"]["price"] == 0.025
        assert analysis["most_expensive_input"]["provider"] == "openai"
        assert analysis["most_expensive_input"]["price"] == 0.03
        assert analysis["price_spread"] == 0.005  # 0.03 - 0.025
    
    def test_get_provider_comparison_no_valid_providers(self, service):
        """Test provider comparison when no providers have pricing data"""
        def mock_get_supply_items(provider=None):
            item = MagicMock(spec=AISupplyItem)
            item.model_name = "test-model"
            item.pricing_input = None  # No pricing data
            item.pricing_output = None
            item.context_window = 4096
            item.last_updated = datetime.utcnow()
            return [item] if provider in ["openai", "anthropic"] else []
        
        with patch.object(service, 'get_supply_items', side_effect=mock_get_supply_items):
            result = service.get_provider_comparison()
        
        assert "providers" in result
        assert "analysis" in result
        assert result["analysis"] == {}  # No analysis possible without pricing
    
    def test_get_provider_comparison_no_data(self, service):
        """Test provider comparison when no providers have data"""
        with patch.object(service, 'get_supply_items', return_value=[]):
            result = service.get_provider_comparison()
        
        providers = result["providers"]
        for provider in ["openai", "anthropic", "google", "mistral", "cohere"]:
            assert provider not in providers or providers[provider]["model_count"] == 0


class TestAnomalyDetection:
    """Test anomaly detection functionality"""
    
    def test_detect_anomalies_significant_price_changes(self, service):
        """Test anomaly detection for significant price changes"""
        with patch.object(service, 'calculate_price_changes') as mock_calc:
            mock_calc.return_value = {
                "all_changes": [
                    {
                        "provider": "openai",
                        "model": "gpt-4",
                        "field": "pricing_input",
                        "percent_change": 60.0,  # Significant change
                        "updated_at": datetime.utcnow().isoformat()
                    },
                    {
                        "provider": "anthropic",
                        "model": "claude-2",
                        "field": "pricing_output",
                        "percent_change": 15.0,  # Moderate change
                        "updated_at": datetime.utcnow().isoformat()
                    }
                ]
            }
            
            anomalies = service.detect_anomalies(threshold=0.2)  # 20% threshold
        
        # Should detect both as anomalies (both > 20%)
        assert len(anomalies) == 2
        
        # Check high severity anomaly
        high_severity = next(a for a in anomalies if a["percent_change"] == 60.0)
        assert high_severity["severity"] == "high"
        assert high_severity["type"] == "significant_price_change"
        
        # Check medium severity anomaly
        medium_severity = next(a for a in anomalies if a["percent_change"] == 15.0)
        assert medium_severity["severity"] == "medium"
    
    def test_detect_anomalies_stale_data(self, service):
        """Test anomaly detection for stale data"""
        # Create stale items
        old_item = MagicMock(spec=AISupplyItem)
        old_item.provider = "openai"
        old_item.model_name = "gpt-3.5"
        old_item.last_updated = datetime.utcnow() - timedelta(days=35)  # Stale
        
        recent_item = MagicMock(spec=AISupplyItem)
        recent_item.provider = "anthropic"
        recent_item.model_name = "claude-2"
        recent_item.last_updated = datetime.utcnow() - timedelta(days=5)  # Recent
        
        service.db.query_results[AISupplyItem] = [old_item, recent_item]
        
        with patch.object(service, 'calculate_price_changes') as mock_calc:
            mock_calc.return_value = {"all_changes": []}
            
            anomalies = service.detect_anomalies()
        
        # Should detect stale data anomaly
        stale_anomalies = [a for a in anomalies if a["type"] == "stale_data"]
        assert len(stale_anomalies) == 1
        
        stale_anomaly = stale_anomalies[0]
        assert stale_anomaly["provider"] == "openai"
        assert stale_anomaly["model"] == "gpt-3.5"
        assert stale_anomaly["severity"] == "low"
    
    def test_detect_anomalies_custom_threshold(self, service):
        """Test anomaly detection with custom threshold"""
        with patch.object(service, 'calculate_price_changes') as mock_calc:
            mock_calc.return_value = {
                "all_changes": [
                    {
                        "provider": "openai",
                        "model": "gpt-4",
                        "field": "pricing_input",
                        "percent_change": 30.0,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                ]
            }
            
            # Higher threshold - should not detect as anomaly
            anomalies = service.detect_anomalies(threshold=0.5)  # 50% threshold
        
        price_anomalies = [a for a in anomalies if a["type"] == "significant_price_change"]
        assert len(price_anomalies) == 0  # 30% < 50% threshold
    
    def test_detect_anomalies_no_anomalies(self, service):
        """Test anomaly detection when no anomalies exist"""
        service.db.query_results[AISupplyItem] = []  # No stale items
        
        with patch.object(service, 'calculate_price_changes') as mock_calc:
            mock_calc.return_value = {"all_changes": []}  # No price changes
            
            anomalies = service.detect_anomalies()
        
        assert len(anomalies) == 0


@pytest.mark.asyncio
class TestMarketReportGeneration:
    """Test market report generation"""
    
    async def test_generate_market_report_complete(self, service):
        """Test comprehensive market report generation"""
        # Mock provider comparison
        provider_comparison = {
            "providers": {
                "openai": {"flagship_model": "gpt-4", "input_price": 0.03},
                "anthropic": {"flagship_model": "claude-2", "input_price": 0.025}
            },
            "analysis": {"cheapest_input": {"provider": "anthropic", "price": 0.025}}
        }
        
        # Mock price changes
        price_changes = {
            "weekly": {"total_changes": 2, "increases": 1, "decreases": 1},
            "monthly": {"total_changes": 5, "increases": 3, "decreases": 2}
        }
        
        # Mock anomalies
        anomalies = [
            {"type": "significant_price_change", "provider": "openai", "severity": "high"}
        ]
        
        # Mock research sessions
        research_session = MagicMock(spec=ResearchSession)
        research_session.id = "session-1"
        research_session.query = "Research OpenAI pricing updates"
        research_session.status = "completed"
        research_session.created_at = datetime.utcnow()
        
        with patch.object(service, 'get_provider_comparison', return_value=provider_comparison):
            with patch.object(service, 'calculate_price_changes', return_value=price_changes["weekly"]):
                with patch.object(service, 'detect_anomalies', return_value=anomalies):
                    with patch.object(service, 'get_research_sessions', return_value=[research_session]):
                        with patch.object(service, 'get_supply_items', return_value=[MagicMock()]):
                            # Mock database counts
                            service.db.query_results[AISupplyItem] = [MagicMock()] * 10  # Total models
                            
                            report = await service.generate_market_report()
        
        assert "generated_at" in report
        assert "sections" in report
        
        sections = report["sections"]
        assert "provider_comparison" in sections
        assert "price_changes" in sections
        assert "anomalies" in sections
        assert "statistics" in sections
        assert "recent_research" in sections
        
        # Check statistics section
        stats = sections["statistics"]
        assert "total_models" in stats
        assert "available_models" in stats
        assert "deprecated_models" in stats
        assert "providers_tracked" in stats
        
        # Check recent research section
        recent_research = sections["recent_research"]
        assert len(recent_research) == 1
        assert recent_research[0]["id"] == "session-1"
        assert recent_research[0]["status"] == "completed"
    
    async def test_generate_market_report_truncated_query(self, service):
        """Test market report with long research session query"""
        long_query = "A" * 150  # Query longer than 100 characters
        research_session = MagicMock(spec=ResearchSession)
        research_session.id = "session-1"
        research_session.query = long_query
        research_session.status = "completed"
        research_session.created_at = datetime.utcnow()
        
        with patch.object(service, 'get_provider_comparison', return_value={"providers": {}, "analysis": {}}):
            with patch.object(service, 'calculate_price_changes', return_value={"total_changes": 0}):
                with patch.object(service, 'detect_anomalies', return_value=[]):
                    with patch.object(service, 'get_research_sessions', return_value=[research_session]):
                        with patch.object(service, 'get_supply_items', return_value=[]):
                            report = await service.generate_market_report()
        
        recent_research = report["sections"]["recent_research"]
        assert len(recent_research[0]["query"]) <= 103  # 100 + "..."
        assert recent_research[0]["query"].endswith("...")


class TestDataValidation:
    """Test data validation functionality"""
    
    def test_validate_supply_data_valid(self, service):
        """Test validation of valid supply data"""
        valid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "0.03",
            "pricing_output": "0.06",
            "context_window": 8192,
            "confidence_score": 0.9,
            "availability_status": "available"
        }
        
        is_valid, errors = service.validate_supply_data(valid_data)
        
        assert is_valid == True
        assert len(errors) == 0
    
    def test_validate_supply_data_missing_required(self, service):
        """Test validation with missing required fields"""
        invalid_data = {
            "pricing_input": "0.03"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert len(errors) >= 1
        assert any("Missing required field: provider" in error for error in errors)
        assert any("Missing required field: model_name" in error for error in errors)
    
    def test_validate_supply_data_negative_pricing(self, service):
        """Test validation with negative pricing"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "-0.03",
            "pricing_output": "-0.06"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Input pricing cannot be negative" in error for error in errors)
        assert any("Output pricing cannot be negative" in error for error in errors)
    
    def test_validate_supply_data_unrealistic_pricing(self, service):
        """Test validation with unrealistically high pricing"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "15000",  # Unrealistically high
            "pricing_output": "20000"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("pricing seems unrealistically high" in error for error in errors)
    
    def test_validate_supply_data_invalid_pricing_format(self, service):
        """Test validation with invalid pricing format"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "pricing_input": "not-a-number",
            "pricing_output": "also-not-a-number"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Invalid input pricing format" in error for error in errors)
        assert any("Invalid output pricing format" in error for error in errors)
    
    def test_validate_supply_data_invalid_context_window(self, service):
        """Test validation with invalid context window"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "context_window": "not-a-number"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Invalid context window format" in error for error in errors)
    
    def test_validate_supply_data_negative_context_window(self, service):
        """Test validation with negative context window"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "context_window": -1000
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Context window cannot be negative" in error for error in errors)
    
    def test_validate_supply_data_unrealistic_context_window(self, service):
        """Test validation with unrealistically large context window"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "context_window": 50000000  # 50M tokens - unrealistic
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Context window seems unrealistically large" in error for error in errors)
    
    def test_validate_supply_data_invalid_confidence_score(self, service):
        """Test validation with invalid confidence score"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "confidence_score": 1.5  # Out of range
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Confidence score must be between 0 and 1" in error for error in errors)
    
    def test_validate_supply_data_invalid_confidence_format(self, service):
        """Test validation with invalid confidence score format"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "confidence_score": "not-a-number"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Invalid confidence score format" in error for error in errors)
    
    def test_validate_supply_data_invalid_availability_status(self, service):
        """Test validation with invalid availability status"""
        invalid_data = {
            "provider": "openai",
            "model_name": "gpt-4",
            "availability_status": "invalid_status"
        }
        
        is_valid, errors = service.validate_supply_data(invalid_data)
        
        assert is_valid == False
        assert any("Invalid availability status" in error for error in errors)
    
    def test_validate_supply_data_valid_availability_statuses(self, service):
        """Test validation with all valid availability statuses"""
        valid_statuses = ["available", "deprecated", "preview", "waitlist"]
        
        for status in valid_statuses:
            data = {
                "provider": "openai",
                "model_name": "gpt-4",
                "availability_status": status
            }
            
            is_valid, errors = service.validate_supply_data(data)
            assert is_valid == True, f"Status '{status}' should be valid"


class TestDatabaseIntegration:
    """Test database integration and query construction"""
    
    def test_query_construction_with_joins(self, service):
        """Test that queries with joins are constructed correctly"""
        # This tests the calculate_price_changes method which uses joins
        service.db.query_results[SupplyUpdateLog] = []
        
        result = service.calculate_price_changes(provider="openai")
        
        # Should have made queries
        assert len(service.db.queries) > 0
        
        # First query should be for SupplyUpdateLog
        assert service.db.queries[0] == ("query", SupplyUpdateLog)
    
    def test_transaction_handling_create_item(self, service):
        """Test transaction handling during item creation"""
        service.db.query_results[AISupplyItem] = []  # No existing item
        
        data = {
            "pricing_input": Decimal("0.03"),
            "confidence_score": 0.9
        }
        
        with patch('app.services.supply_research_service.AISupplyItem') as mock_item_class:
            with patch('app.services.supply_research_service.SupplyUpdateLog') as mock_log_class:
                mock_item = MagicMock()
                mock_item.id = "new-item"
                mock_item_class.return_value = mock_item
                mock_log_class.return_value = MagicMock()
                
                result = service.create_or_update_supply_item("openai", "gpt-4", data)
        
        # Should have committed transaction
        assert service.db.committed == True
        assert len(service.db.added_objects) >= 2  # Item + log
    
    def test_error_handling_database_errors(self, service):
        """Test error handling for database errors"""
        # Mock database to raise exception on query
        def failing_query(model):
            raise Exception("Database connection failed")
        
        service.db.query = failing_query
        
        # Should handle database errors gracefully
        with pytest.raises(Exception):
            service.get_supply_items()


class TestCaching:
    """Test caching functionality when Redis is available"""
    
    def test_redis_not_available(self, mock_db):
        """Test service behavior when Redis is not available"""
        with patch('app.services.supply_research_service.RedisManager', side_effect=Exception("Redis unavailable")):
            service = SupplyResearchService(mock_db)
            
            assert service.redis_manager == None
            
            # Service should still function normally
            service.db.query_results[AISupplyItem] = []
            result = service.get_supply_items()
            assert result == []


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_provider_list_comparison(self, service):
        """Test provider comparison with empty provider list"""
        with patch.object(service, 'get_supply_items', return_value=[]):
            result = service.get_provider_comparison()
            
            # Should not crash with empty data
            assert "providers" in result
            assert "analysis" in result
    
    def test_price_changes_with_null_values(self, service):
        """Test price changes calculation with null values in logs"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = None
        log.new_value = '"0.03"'
        log.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log]
        
        with patch.object(service, 'get_supply_item_by_id', return_value=MagicMock()):
            result = service.calculate_price_changes()
        
        # Should handle null values gracefully
        assert "total_changes" in result
    
    def test_very_large_price_changes(self, service):
        """Test handling of very large price changes"""
        log = MagicMock(spec=SupplyUpdateLog)
        log.supply_item_id = "item-1"
        log.field_updated = "pricing_input"
        log.old_value = '"0.001"'
        log.new_value = '"10.0"'  # 999900% increase
        log.updated_at = datetime.utcnow()
        
        service.db.query_results[SupplyUpdateLog] = [log]
        
        item = MagicMock(spec=AISupplyItem)
        item.provider = "test"
        item.model_name = "test-model"
        
        with patch.object(service, 'get_supply_item_by_id', return_value=item):
            result = service.calculate_price_changes()
        
        # Should handle very large percentage changes
        assert len(result["all_changes"]) == 1
        change = result["all_changes"][0]
        assert change["percent_change"] > 1000  # Very large increase
    
    def test_concurrent_updates(self, service, sample_supply_item):
        """Test handling of concurrent updates to same item"""
        service.db.query_results[AISupplyItem] = [sample_supply_item]
        
        data1 = {"pricing_input": Decimal("0.04")}
        data2 = {"pricing_output": Decimal("0.08")}
        
        with patch('app.services.supply_research_service.SupplyUpdateLog') as mock_log_class:
            mock_log_class.return_value = MagicMock()
            
            # Simulate concurrent updates
            result1 = service.create_or_update_supply_item("openai", "gpt-4", data1)
            result2 = service.create_or_update_supply_item("openai", "gpt-4", data2)
        
        # Both updates should succeed
        assert result1 == sample_supply_item
        assert result2 == sample_supply_item
        assert service.db.committed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])