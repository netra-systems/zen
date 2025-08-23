"""
Tests for Unit of Work pattern transaction handling.
All functions ≤8 lines per requirements.
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.database.unit_of_work import UnitOfWork
from netra_backend.tests.database_transaction_test_helpers import (
    create_mock_session_factory,
)

@pytest.fixture
def mock_async_session_factory():
    """Mock async session factory"""
    return create_mock_session_factory()

class TestUnitOfWorkTransactions:
    """Test Unit of Work pattern transaction handling"""
    
    async def test_unit_of_work_successful_transaction(self, mock_async_session_factory):
        """Test successful Unit of Work transaction"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                _verify_repositories_initialized(uow)
                _verify_session_injection(uow, mock_session)
        
        # Session should not be rolled back on success
        mock_session.rollback.assert_not_called()
    
    async def test_unit_of_work_rollback_on_exception(self, mock_async_session_factory):
        """Test Unit of Work rollback on exception"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            await _execute_failing_uow_transaction()
        
        # Should rollback on exception
        mock_session.rollback.assert_called_once()
    
    async def test_unit_of_work_with_external_session(self):
        """Test Unit of Work with externally provided session"""
        external_session = AsyncMock(spec=AsyncSession)
        
        async with UnitOfWork(external_session) as uow:
            assert uow._session is external_session
            assert uow._external_session == True
        
        _assert_external_session_not_modified(external_session)
    
    async def test_unit_of_work_repository_access(self, mock_async_session_factory):
        """Test repository access through Unit of Work"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                _test_repository_access(uow)
    
    async def test_unit_of_work_session_lifecycle(self, mock_async_session_factory):
        """Test Unit of Work session lifecycle management"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            async with UnitOfWork() as uow:
                assert uow._session is mock_session
                assert not uow._external_session
        
        # Session should be properly managed
        mock_session.close.assert_called_once()
    
    async def test_unit_of_work_nested_transactions(self, mock_async_session_factory):
        """Test nested transaction handling"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            await _execute_nested_transactions(UnitOfWork)
    
    async def test_unit_of_work_error_handling(self, mock_async_session_factory):
        """Test error handling in Unit of Work"""
        factory, mock_session = mock_async_session_factory
        
        with patch('app.services.database.unit_of_work.async_session_factory', factory):
            await _test_uow_error_scenarios(UnitOfWork, mock_session)

def _verify_repositories_initialized(uow) -> None:
    """Verify repositories are initialized"""
    assert uow.threads is not None
    assert uow.messages is not None
    assert uow.runs is not None
    assert uow.references is not None

def _verify_session_injection(uow, mock_session) -> None:
    """Verify session is injected into repositories"""
    assert uow.threads._session is mock_session
    assert uow.messages._session is mock_session

async def _execute_failing_uow_transaction() -> None:
    """Execute UoW transaction that fails"""
    try:
        async with UnitOfWork() as uow:
            # Simulate operation that raises exception
            raise ValueError("Simulated error in UoW")
    except ValueError:
        pass  # Expected exception

def _assert_external_session_not_modified(external_session: AsyncMock) -> None:
    """Assert external session is not modified"""
    # External session should not be closed
    external_session.close.assert_not_called()
    external_session.rollback.assert_not_called()

def _test_repository_access(uow) -> None:
    """Test repository access functionality"""
    # Test that repositories are accessible
    assert hasattr(uow, 'threads')
    assert hasattr(uow, 'messages')
    assert hasattr(uow, 'runs')
    assert hasattr(uow, 'references')

async def _execute_nested_transactions(UnitOfWork) -> None:
    """Execute nested transaction scenario"""
    async with UnitOfWork() as outer_uow:
        # Simulate nested operation
        async with UnitOfWork(outer_uow._session) as inner_uow:
            assert inner_uow._session is outer_uow._session
            assert inner_uow._external_session == True

async def _test_uow_error_scenarios(UnitOfWork, mock_session) -> None:
    """Test various error scenarios in UoW"""
    # Test that rollback is called on any exception
    try:
        async with UnitOfWork() as uow:
            raise RuntimeError("Test error")
    except RuntimeError:
        pass
    
    mock_session.rollback.assert_called()