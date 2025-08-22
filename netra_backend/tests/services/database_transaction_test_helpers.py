"""
Helper functions for database transaction tests.
All functions ≤8 lines per requirements.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


def create_mock_session() -> AsyncMock:
    """Create a mock database session with standard configuration"""
    session = AsyncMock(spec=AsyncSession)
    _configure_session_methods(session)
    return session


def _configure_session_methods(session: AsyncMock) -> None:
    """Configure session methods for mocking"""
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()


def configure_mock_query_results(session: AsyncMock) -> None:
    """Configure mock query results for session"""
    mock_result = MagicMock()
    _setup_result_methods(mock_result)
    session.execute.return_value = mock_result


def _setup_result_methods(mock_result: MagicMock) -> None:
    """Setup mock result methods"""
    # Return a default mock entity for get operations
    mock_entity = MockDatabaseModel(id="test_id", name="Test Entity")
    mock_result.scalar_one_or_none.return_value = mock_entity
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = mock_entity


def create_mock_session_factory() -> tuple[MagicMock, AsyncMock]:
    """Create mock async session factory with context manager"""
    session = create_mock_session()
    session.begin = AsyncMock()
    session_context = _create_session_context(session)
    factory = _create_factory(session_context)
    return factory, session


def _create_session_context(session: AsyncMock) -> AsyncMock:
    """Create session context manager"""
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    return context


def _create_factory(session_context: AsyncMock) -> MagicMock:
    """Create session factory"""
    factory = MagicMock()
    factory.return_value = session_context
    return factory


def create_tracked_session_factory(created_sessions: List[Any]) -> callable:
    """Create session factory that tracks created sessions"""
    def factory():
        session = create_mock_session()
        created_sessions.append(session)
        return session
    return factory


async def run_transaction_cycle(repository, session_factory) -> None:
    """Run a single transaction cycle with proper cleanup"""
    session = session_factory()
    try:
        await repository.create(session, name='Cleanup Test')
    finally:
        await session.close()


async def run_multiple_transaction_cycles(repository, session_factory, count: int = 10) -> None:
    """Run multiple transaction cycles concurrently"""
    tasks = _create_transaction_tasks(repository, session_factory, count)
    await asyncio.gather(*tasks)


def _create_transaction_tasks(repository, session_factory, count: int) -> List:
    """Create list of transaction tasks"""
    return [run_transaction_cycle(repository, session_factory) for _ in range(count)]


def assert_all_sessions_closed(created_sessions: List[Any]) -> None:
    """Assert all sessions were properly closed"""
    assert len(created_sessions) > 0, "No sessions were created"
    for session in created_sessions:
        session.close.assert_called_once()


class MockDatabaseModel(Base):
    """Mock database model for testing - SQLAlchemy compatible"""
    
    __tablename__ = "mock_test_table"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    def __init__(self, id: str = None, name: str = None, **kwargs):
        if id:
            self.id = id
        self.name = name
        self._set_additional_attrs(kwargs)
    
    def _set_additional_attrs(self, kwargs: dict) -> None:
        """Set additional attributes from kwargs"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"MockDatabaseModel(id={self.id}, name={self.name})"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }