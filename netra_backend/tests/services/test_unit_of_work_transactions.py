"""
Focused tests for Unit of Work pattern transaction handling
Tests UoW transaction management, rollback behavior, and external session handling
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path

from netra_backend.app.services.database.unit_of_work import UnitOfWork

# Add project root to path


class TestUnitOfWorkTransactions:
    """Test Unit of Work pattern transaction handling"""
    
    @pytest.fixture
    def mock_async_session_factory(self):
        """Mock async session factory"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.begin = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        
        # Create a context manager that returns the session
        session_context = AsyncMock()
        session_context.__aenter__ = AsyncMock(return_value=session)
        session_context.__aexit__ = AsyncMock(return_value=None)
        
        factory = MagicMock()
        factory.return_value = session_context
        return factory, session
    
    def _assert_uow_repositories_initialized(self, uow, mock_session):
        """Assert UoW repositories are properly initialized"""
        assert uow.threads != None
        assert uow.messages != None
        assert uow.runs != None
        assert uow.references != None
        assert uow.threads._session is mock_session
        assert uow.messages._session is mock_session
    async def test_unit_of_work_successful_transaction(self, mock_async_session_factory):
        """Test successful Unit of Work transaction"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                self._assert_uow_repositories_initialized(uow, mock_session)
        mock_session.rollback.assert_not_called()
    async def test_unit_of_work_rollback_on_exception(self, mock_async_session_factory):
        """Test Unit of Work rollback on exception"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            try:
                async with UnitOfWork() as uow:
                    raise ValueError("Simulated error in UoW")
            except ValueError:
                pass
        mock_session.rollback.assert_called_once()

    def _assert_external_session_handling(self, external_session, uow):
        """Assert external session is handled correctly"""
        assert uow._session is external_session
        assert uow._external_session == True
        external_session.close.assert_not_called()
        external_session.rollback.assert_not_called()
    async def test_unit_of_work_with_external_session(self):
        """Test Unit of Work with externally provided session"""
        external_session = AsyncMock(spec=AsyncSession)
        async with UnitOfWork(external_session) as uow:
            self._assert_external_session_handling(external_session, uow)
    async def test_unit_of_work_nested_transaction_handling(self, mock_async_session_factory):
        """Test nested Unit of Work transaction behavior"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as outer_uow:
                # Nested UoW should use same session
                async with UnitOfWork(outer_uow._session) as inner_uow:
                    assert inner_uow._session is outer_uow._session
                    assert inner_uow._external_session == True
    async def test_unit_of_work_repository_isolation(self, mock_async_session_factory):
        """Test repository isolation within Unit of Work"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                # All repositories should share the same session
                assert uow.threads._session is mock_session
                assert uow.messages._session is mock_session
                assert uow.runs._session is mock_session
                assert uow.references._session is mock_session
    async def test_unit_of_work_transaction_state_consistency(self, mock_async_session_factory):
        """Test transaction state consistency across operations"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                # Simulate multiple repository operations
                uow.threads.operation_log.append(('test_op', 'data1'))
                uow.messages.operation_log.append(('test_op', 'data2'))
                # Session should remain consistent
                assert uow._session is mock_session
        # Should complete successfully without rollback
        mock_session.rollback.assert_not_called()
    async def test_unit_of_work_exception_propagation(self, mock_async_session_factory):
        """Test exception propagation from Unit of Work context"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            test_exception = RuntimeError("Test exception for propagation")
            with pytest.raises(RuntimeError, match="Test exception for propagation"):
                async with UnitOfWork() as uow:
                    raise test_exception
        # Should have attempted rollback
        mock_session.rollback.assert_called_once()
    async def test_unit_of_work_session_cleanup_on_success(self, mock_async_session_factory):
        """Test proper session cleanup on successful completion"""
        factory, mock_session = mock_async_session_factory
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                pass  # Successful completion
        # Should not call rollback on success
        mock_session.rollback.assert_not_called()
        # Session context should have been properly exited
        factory.return_value.__aexit__.assert_called_once()
    async def test_unit_of_work_external_session_no_cleanup(self):
        """Test external session is not cleaned up by Unit of Work"""
        external_session = AsyncMock(spec=AsyncSession)
        async with UnitOfWork(external_session) as uow:
            pass
        # External session should not be managed by UoW
        external_session.close.assert_not_called()
        external_session.rollback.assert_not_called()
        external_session.commit.assert_not_called()