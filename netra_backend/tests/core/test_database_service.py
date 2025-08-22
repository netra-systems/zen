"""Tests for DatabaseService functionality."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.core.exceptions_service import ServiceError

from netra_backend.app.core.service_interfaces import DatabaseService

class TestDatabaseService:
    """Test DatabaseService functionality."""
    
    def test_initialization(self):
        """Test DatabaseService initialization."""
        service = DatabaseService("db-service")
        
        assert service.service_name == "db-service"
        assert service._session_factory == None
    
    def test_set_session_factory(self):
        """Test setting session factory."""
        service = DatabaseService("db-service")
        mock_factory = Mock()
        
        service.set_session_factory(mock_factory)
        
        assert service._session_factory == mock_factory

    def _verify_session_error(self, exc_info, expected_message):
        """Helper: Verify session error message."""
        assert expected_message in str(exc_info.value)

    async def test_get_db_session_no_factory(self):
        """Test getting DB session without factory configured."""
        service = DatabaseService("db-service")
        
        with pytest.raises(ServiceError) as exc_info:
            async with service.get_db_session():
                pass
        
        self._verify_session_error(exc_info, "Database session factory not configured")

    def _create_mock_session(self):
        """Helper: Create mock session with close method."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session

    def _create_mock_context_manager(self, session):
        """Helper: Create mock async context manager."""
        class MockAsyncContextManager:
            def __init__(self, session):
                self.session = session
            
            async def __aenter__(self):
                return self.session
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None  # The service will handle the close
        
        return MockAsyncContextManager(session)

    def _create_mock_factory(self, session):
        """Helper: Create mock session factory."""
        def mock_factory():
            return self._create_mock_context_manager(session)
        return mock_factory

    def _verify_session_close_called(self, mock_session):
        """Helper: Verify session close was called."""
        mock_session.close.assert_called_once()

    async def test_get_db_session_success(self):
        """Test successful DB session acquisition."""
        service = DatabaseService("db-service")
        mock_session = self._create_mock_session()
        mock_factory = self._create_mock_factory(mock_session)
        
        service.set_session_factory(mock_factory)
        
        async with service.get_db_session() as session:
            assert session == mock_session
        
        self._verify_session_close_called(mock_session)

    def _create_error_handling_session(self):
        """Helper: Create session with error handling methods."""
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session

    def _setup_error_context_mock(self):
        """Helper: Setup error context mock."""
        return patch('app.schemas.shared_types.ErrorContext.get_all_context', return_value={})

    def _verify_error_handling(self, mock_session):
        """Helper: Verify error handling calls."""
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    async def test_get_db_session_exception(self):
        """Test DB session with exception handling."""
        service = DatabaseService("db-service")
        mock_session = self._create_error_handling_session()
        mock_factory = self._create_mock_factory(mock_session)
        
        service.set_session_factory(mock_factory)
        
        # Mock the ErrorContext.get_all_context to return empty dict
        with self._setup_error_context_mock():
            with pytest.raises(ServiceError):
                async with service.get_db_session():
                    raise Exception("Database error")
        
        self._verify_error_handling(mock_session)