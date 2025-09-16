"""Database repository test fixtures and helpers.

This module provides reusable fixtures and helper functions for testing
database repositories with mocked behavior. All functions are  <= 8 lines.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.database.unit_of_work import UnitOfWork

@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    _setup_session_methods(session)
    return session

def _setup_session_methods(session):
    """Setup mock methods for database session."""
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.begin = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock(side_effect=_mock_refresh)
    session.execute = AsyncMock()
    session.scalar = AsyncMock()

async def _mock_refresh(entity):
    """Mock refresh to update entity with ID."""
    if hasattr(entity, 'id') and not entity.id:
        entity.id = "test_id_123"

@pytest.fixture
def mock_models():
    """Create mock database model classes."""
    return {
        'Thread': _create_thread_mock,
        'Message': _create_message_mock,
        'Run': _create_run_mock,
        'Reference': _create_reference_mock
    }

def _create_thread_mock(**kwargs):
    """Create mock thread object."""
    return AsyncMock(
        id=kwargs.get('id', f'thread_{datetime.now().timestamp()}'),
        user_id=kwargs.get('user_id'),
        title=kwargs.get('title'),
        created_at=kwargs.get('created_at', datetime.now()),
        updated_at=kwargs.get('updated_at', datetime.now())
    )

def _create_message_mock(**kwargs):
    """Create mock message object."""
    return AsyncMock(
        id=kwargs.get('id', f'msg_{datetime.now().timestamp()}'),
        thread_id=kwargs.get('thread_id'),
        content=kwargs.get('content'),
        role=kwargs.get('role'),
        created_at=kwargs.get('created_at', datetime.now())
    )

def _create_run_mock(**kwargs):
    """Create mock run object."""
    return AsyncMock(
        id=kwargs.get('id', f'run_{datetime.now().timestamp()}'),
        thread_id=kwargs.get('thread_id'),
        status=kwargs.get('status', 'completed'),
        created_at=kwargs.get('created_at', datetime.now())
    )

def _create_reference_mock(**kwargs):
    """Create mock reference object."""
    return AsyncMock(
        id=kwargs.get('id', f'ref_{datetime.now().timestamp()}'),
        message_id=kwargs.get('message_id'),
        source=kwargs.get('source'),
        content=kwargs.get('content')
    )

@pytest.fixture
def unit_of_work(mock_session, mock_models):
    """Create a test unit of work instance with mocked repositories."""
    from netra_backend.tests.helpers.database_repository_helpers import (
        setup_message_mock_behavior,
        setup_reference_mock_behavior,
        setup_run_mock_behavior,
        setup_thread_mock_behavior,
    )
    
    # Create a proper async context manager for the session factory
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    
    with patch('netra_backend.app.services.database.unit_of_work.async_session_factory') as mock_factory, \
         patch('netra_backend.app.services.database.unit_of_work.validate_session', return_value=True):
        mock_factory.return_value = mock_context
        
        with patch('netra_backend.app.services.database.unit_of_work.ThreadRepository') as MockThreadRepo, \
             patch('netra_backend.app.services.database.unit_of_work.MessageRepository') as MockMessageRepo, \
             patch('netra_backend.app.services.database.unit_of_work.RunRepository') as MockRunRepo, \
             patch('netra_backend.app.services.database.unit_of_work.ReferenceRepository') as MockReferenceRepo:
            
            # Create mock repositories
            mock_thread_repo = AsyncMock()
            mock_message_repo = AsyncMock()
            mock_run_repo = AsyncMock()
            mock_reference_repo = AsyncMock()
            
            # Setup mock behaviors
            setup_thread_mock_behavior(mock_thread_repo)
            setup_message_mock_behavior(mock_message_repo)
            setup_run_mock_behavior(mock_run_repo)
            setup_reference_mock_behavior(mock_reference_repo)
            
            # Configure repository mocks
            MockThreadRepo.return_value = mock_thread_repo
            MockMessageRepo.return_value = mock_message_repo
            MockRunRepo.return_value = mock_run_repo
            MockReferenceRepo.return_value = mock_reference_repo
            
            uow = UnitOfWork()
            yield uow