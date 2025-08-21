"""Tests for CRUDService functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.core.service_interfaces import CRUDService
from netra_backend.app.core.exceptions_database import RecordNotFoundError


class MockModel:
    """Mock database model for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestCRUDService:
    """Test CRUDService functionality."""
    
    @pytest.fixture
    def crud_service(self):
        """Create a CRUD service for testing."""
        service = CRUDService("crud-service", MockModel, MockModel)
        
        # Mock session factory
        async def mock_factory():
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            return mock_session
        
        service.set_session_factory(mock_factory)
        return service

    def _setup_session_mock(self):
        """Helper: Setup mock session context."""
        mock_session = AsyncMock()
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        session_ctx.__aexit__ = AsyncMock(return_value=None)
        return mock_session, session_ctx

    def _mock_entity_creation(self, mock_session, entity):
        """Helper: Setup entity creation mocks."""
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        return entity

    def _verify_entity_creation(self, mock_session):
        """Helper: Verify entity creation calls."""
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_entity(self, crud_service):
        """Test creating an entity."""
        mock_data = {"name": "test", "value": 123}
        mock_session, session_ctx = self._setup_session_mock()
        mock_entity = MockModel(id=1, name="test", value=123)
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._mock_entity_creation(mock_session, mock_entity)
            
            with patch.object(crud_service, '_to_response_schema', return_value=mock_entity):
                result = await crud_service.create(mock_data)
                
                assert result == mock_entity
                self._verify_entity_creation(mock_session)

    def _setup_get_by_id_mock(self, mock_session, entity):
        """Helper: Setup get by ID mock."""
        mock_session.get = AsyncMock(return_value=entity)

    def _verify_get_by_id_call(self, mock_session, entity_id):
        """Helper: Verify get by ID call."""
        mock_session.get.assert_called_once_with(MockModel, entity_id)

    async def test_get_by_id_found(self, crud_service):
        """Test getting entity by ID when found."""
        entity_id = 1
        mock_entity = MockModel(id=entity_id, name="test")
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_get_by_id_mock(mock_session, mock_entity)
            
            with patch.object(crud_service, '_to_response_schema', return_value=mock_entity):
                result = await crud_service.get_by_id(entity_id)
                
                assert result == mock_entity
                self._verify_get_by_id_call(mock_session, entity_id)

    async def test_get_by_id_not_found(self, crud_service):
        """Test getting entity by ID when not found."""
        entity_id = 999
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_get_by_id_mock(mock_session, None)
            
            result = await crud_service.get_by_id(entity_id)
            
            assert result == None

    def _setup_update_mocks(self, mock_session, entity):
        """Helper: Setup update operation mocks."""
        mock_session.get = AsyncMock(return_value=entity)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

    def _apply_update_data(self, entity, update_data):
        """Helper: Apply update data to entity."""
        for key, value in update_data.items():
            setattr(entity, key, value)

    def _verify_update_calls(self, mock_session):
        """Helper: Verify update operation calls."""
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_update_entity_success(self, crud_service):
        """Test updating an existing entity."""
        entity_id = 1
        update_data = {"name": "updated"}
        mock_entity = MockModel(id=entity_id, name="original")
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_update_mocks(mock_session, mock_entity)
            self._apply_update_data(mock_entity, update_data)
            
            with patch.object(crud_service, '_to_response_schema', return_value=mock_entity):
                result = await crud_service.update(entity_id, update_data)
                
                assert result == mock_entity
                assert mock_entity.name == "updated"  # Field should be updated

    async def test_update_entity_not_found(self, crud_service):
        """Test updating non-existent entity."""
        entity_id = 999
        update_data = {"name": "updated"}
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_update_mocks(mock_session, None)
            
            with pytest.raises(RecordNotFoundError):
                await crud_service.update(entity_id, update_data)

    def _setup_delete_mocks(self, mock_session, entity):
        """Helper: Setup delete operation mocks."""
        mock_session.get = AsyncMock(return_value=entity)
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

    def _verify_delete_calls(self, mock_session, entity):
        """Helper: Verify delete operation calls."""
        mock_session.delete.assert_called_once_with(entity)
        mock_session.commit.assert_called_once()

    async def test_delete_entity_success(self, crud_service):
        """Test deleting an existing entity."""
        entity_id = 1
        mock_entity = MockModel(id=entity_id, name="test")
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_delete_mocks(mock_session, mock_entity)
            
            result = await crud_service.delete(entity_id)
            
            assert result == True
            self._verify_delete_calls(mock_session, mock_entity)

    async def test_delete_entity_not_found(self, crud_service):
        """Test deleting non-existent entity."""
        entity_id = 999
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_delete_mocks(mock_session, None)
            
            result = await crud_service.delete(entity_id)
            
            assert result == False

    def _setup_exists_mock(self, mock_session, entity):
        """Helper: Setup exists check mock."""
        mock_session.get = AsyncMock(return_value=entity)

    async def test_exists_true(self, crud_service):
        """Test entity exists check when entity exists."""
        entity_id = 1
        mock_entity = MockModel(id=entity_id)
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_exists_mock(mock_session, mock_entity)
            
            result = await crud_service.exists(entity_id)
            
            assert result == True

    async def test_exists_false(self, crud_service):
        """Test entity exists check when entity doesn't exist."""
        entity_id = 999
        mock_session, session_ctx = self._setup_session_mock()
        
        with patch.object(crud_service, 'get_db_session', return_value=session_ctx):
            self._setup_exists_mock(mock_session, None)
            
            result = await crud_service.exists(entity_id)
            
            assert result == False