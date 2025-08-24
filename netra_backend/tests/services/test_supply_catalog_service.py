"""Test supply catalog service for AI model and resource management."""

import sys
from pathlib import Path

from unittest.mock import MagicMock, patch

import pytest

from netra_backend.app.db import models_postgres
from netra_backend.app.schemas.Supply import (
    SupplyOptionCreate,
    SupplyOptionUpdate,
)

from netra_backend.app.services.supply_catalog_service import SupplyCatalogService

@pytest.fixture
def supply_catalog_service():
    """Create a test supply catalog service instance."""
    return SupplyCatalogService()

@pytest.fixture  
def mock_db_session():
    """Create a mock database session."""
    # Mock: Generic component isolation for controlled unit testing
    return MagicMock()

class TestSupplyCatalogService:
    """Test supply catalog service basic functionality."""

    def test_get_all_options(self, supply_catalog_service, mock_db_session):
        """Test retrieving all supply options."""
        # Mock the database response with proper attribute configuration
        # Mock: Generic component isolation for controlled unit testing
        mock_option1 = MagicMock()
        mock_option1.id = 1
        mock_option1.name = "gpt-4"
        mock_option1.provider = "OpenAI"
        
        # Mock: Generic component isolation for controlled unit testing
        mock_option2 = MagicMock()
        mock_option2.id = 2
        mock_option2.name = "claude-3"
        mock_option2.provider = "Anthropic"
        
        mock_options = [mock_option1, mock_option2]
        mock_db_session.query.return_value.all.return_value = mock_options
        
        result = supply_catalog_service.get_all_options(mock_db_session)
        
        assert len(result) == 2
        assert result[0].name == "gpt-4"
        assert result[1].provider == "Anthropic"
        mock_db_session.query.assert_called_once()

    def test_get_option_by_id(self, supply_catalog_service, mock_db_session):
        """Test retrieving supply option by ID."""
        # Mock: Generic component isolation for controlled unit testing
        mock_option = MagicMock()
        mock_option.id = 1
        mock_option.name = "gpt-4"
        mock_option.provider = "OpenAI"
        mock_db_session.get.return_value = mock_option
        
        result = supply_catalog_service.get_option_by_id(mock_db_session, 1)
        
        assert result != None
        assert result.name == "gpt-4"
        mock_db_session.get.assert_called_once_with(models_postgres.SupplyOption, 1)

    def test_get_option_by_name(self, supply_catalog_service, mock_db_session):
        """Test retrieving supply option by name."""
        # Mock: Generic component isolation for controlled unit testing
        mock_option = MagicMock()
        mock_option.name = "gpt-4"
        mock_option.provider = "OpenAI"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_option
        
        result = supply_catalog_service.get_option_by_name(mock_db_session, "gpt-4")
        
        assert result != None
        assert result.name == "gpt-4"
        mock_db_session.query.assert_called_once()

    def test_create_option(self, supply_catalog_service, mock_db_session):
        """Test creating a new supply option."""
        option_data = SupplyOptionCreate(
            provider="OpenAI",
            family="GPT-4",
            name="gpt-4-test",
            cost_per_million_tokens_usd={"prompt": 10.0, "completion": 30.0},
            quality_score=0.95
        )
        
        # Mock: Service component isolation for predictable testing behavior
        mock_option = MagicMock(id=1, name="gpt-4-test")
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_db_session.add = MagicMock()
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_db_session.commit = MagicMock()
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_db_session.refresh = MagicMock()
        
        with patch.object(models_postgres, 'SupplyOption', return_value=mock_option):
            result = supply_catalog_service.create_option(mock_db_session, option_data)
            
            assert result != None
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    def test_update_option(self, supply_catalog_service, mock_db_session):
        """Test updating an existing supply option."""
        # Mock: Service component isolation for predictable testing behavior
        mock_option = MagicMock(id=1, name="gpt-4")
        # Mock: Service component isolation for predictable testing behavior
        supply_catalog_service.get_option_by_id = MagicMock(return_value=mock_option)
        
        update_data = SupplyOptionUpdate(name="gpt-4-updated")
        
        result = supply_catalog_service.update_option(mock_db_session, 1, update_data)
        
        assert result != None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_delete_option(self, supply_catalog_service, mock_db_session):
        """Test deleting a supply option."""
        # Mock: Service component isolation for predictable testing behavior
        mock_option = MagicMock(id=1, name="gpt-4")
        # Mock: Service component isolation for predictable testing behavior
        supply_catalog_service.get_option_by_id = MagicMock(return_value=mock_option)
        
        result = supply_catalog_service.delete_option(mock_db_session, 1)
        
        assert result == True
        mock_db_session.delete.assert_called_once_with(mock_option)
        mock_db_session.commit.assert_called_once()

    def test_delete_option_not_found(self, supply_catalog_service, mock_db_session):
        """Test deleting non-existent supply option."""
        # Mock: Service component isolation for predictable testing behavior
        supply_catalog_service.get_option_by_id = MagicMock(return_value=None)
        
        result = supply_catalog_service.delete_option(mock_db_session, 999)
        
        assert result == False
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()

    def test_autofill_catalog_empty(self, supply_catalog_service, mock_db_session):
        """Test autofilling catalog when empty."""
        # Mock: Service component isolation for predictable testing behavior
        supply_catalog_service.get_all_options = MagicMock(return_value=[])
        # Mock: Generic component isolation for controlled unit testing
        supply_catalog_service.create_option = MagicMock()
        
        supply_catalog_service.autofill_catalog(mock_db_session)
        
        # Should create default options (5 in the implementation)
        assert supply_catalog_service.create_option.call_count == 5

    def test_autofill_catalog_existing_data(self, supply_catalog_service, mock_db_session):
        """Test autofilling catalog when data already exists."""
        # Mock: Generic component isolation for controlled unit testing
        supply_catalog_service.get_all_options = MagicMock(return_value=[MagicMock()])
        # Mock: Generic component isolation for controlled unit testing
        supply_catalog_service.create_option = MagicMock()
        
        supply_catalog_service.autofill_catalog(mock_db_session)
        
        # Should not create new options if data exists
        supply_catalog_service.create_option.assert_not_called()
