"""Test Database Connection Pooling and Dependency Injection

This test ensures that database sessions are properly injected
through FastAPI dependencies and that async context managers
are correctly handled.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.dependencies import DbDep, get_db_dependency
from app.services.database.thread_repository import ThreadRepository
from app.db.postgres import get_async_db


class TestDatabaseConnectionPooling:
    """Test suite for database connection pooling and dependency injection"""

    @pytest.mark.asyncio
    async def test_get_db_dependency_returns_async_session(self):
        """Test that get_db_dependency properly yields AsyncSession"""
        mock_session = MagicMock(spec=AsyncSession)
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield mock_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            async with get_db_dependency() as session:
                assert isinstance(session, AsyncSession)
                assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_db_dependency_validates_session_type(self):
        """Test that get_db_dependency validates session type"""
        invalid_session = MagicMock()  # Not an AsyncSession
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield invalid_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            with pytest.raises(RuntimeError, match="Expected AsyncSession"):
                async with get_db_dependency() as session:
                    pass

    @pytest.mark.asyncio
    async def test_repository_receives_async_session(self):
        """Test that repository methods receive AsyncSession, not context manager"""
        mock_session = MagicMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        ))
        
        thread_repo = ThreadRepository()
        result = await thread_repo.find_by_user(mock_session, "test_user_id")
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_fastapi_dependency_injection(self):
        """Test that FastAPI properly injects AsyncSession through DbDep"""
        app = FastAPI()
        mock_session = MagicMock(spec=AsyncSession)
        
        @asynccontextmanager
        async def mock_get_db_dependency():
            yield mock_session
        
        @app.get("/test")
        async def test_endpoint(db: DbDep):
            assert isinstance(db, AsyncSession)
            return {"session_type": type(db).__name__}
        
        with patch('app.dependencies.get_db_dependency', mock_get_db_dependency):
            with TestClient(app) as client:
                response = client.get("/test")
                assert response.status_code == 200
                assert response.json()["session_type"] == "MagicMock"

    @pytest.mark.asyncio
    async def test_connection_pool_logging(self):
        """Test that connection pool operations are properly logged"""
        mock_session = MagicMock(spec=AsyncSession)
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield mock_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            with patch('app.dependencies.logger') as mock_logger:
                async with get_db_dependency() as session:
                    mock_logger.debug.assert_called_with(
                        f"Dependency injected session type: {type(mock_session).__name__}"
                    )

    @pytest.mark.asyncio
    async def test_context_manager_not_passed_to_repository(self):
        """Ensure context manager itself is never passed to repository methods"""
        from contextlib import _AsyncGeneratorContextManager
        
        # Create a mock that would fail if execute is called
        mock_context_manager = MagicMock(spec=_AsyncGeneratorContextManager)
        mock_context_manager.execute = MagicMock(
            side_effect=AttributeError("'_AsyncGeneratorContextManager' object has no attribute 'execute'")
        )
        
        thread_repo = ThreadRepository()
        
        # This should raise AttributeError if context manager is passed
        with pytest.raises(AttributeError, match="has no attribute 'execute'"):
            await thread_repo.find_by_user(mock_context_manager, "test_user_id")

    @pytest.mark.asyncio
    async def test_get_async_db_session_lifecycle(self):
        """Test the complete lifecycle of async database session"""
        mock_session = MagicMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield mock_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            # Test successful transaction
            async with get_db_dependency() as session:
                assert session == mock_session
            
            # Test transaction with error
            with pytest.raises(ValueError):
                async with get_db_dependency() as session:
                    raise ValueError("Test error")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        """Test that multiple concurrent sessions work correctly"""
        sessions = []
        
        async def create_session():
            async with get_db_dependency() as session:
                sessions.append(session)
                return session
        
        mock_session1 = MagicMock(spec=AsyncSession)
        mock_session2 = MagicMock(spec=AsyncSession)
        mock_sessions = [mock_session1, mock_session2]
        session_index = 0
        
        @asynccontextmanager
        async def mock_get_async_db():
            nonlocal session_index
            yield mock_sessions[session_index % 2]
            session_index += 1
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            import asyncio
            await asyncio.gather(create_session(), create_session())
            
            assert len(sessions) == 2
            assert all(isinstance(s, AsyncSession) for s in sessions)