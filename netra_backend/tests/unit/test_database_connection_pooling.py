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

from netra_backend.app.dependencies import DbDep, get_db_dependency
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.db.postgres import get_async_db

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestDatabaseConnectionPooling:
    """Test suite for database connection pooling and dependency injection"""
    async def test_get_db_dependency_returns_async_session(self):
        """Test that get_db_dependency properly yields AsyncSession"""
        mock_session = MagicMock(spec=AsyncSession)
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield mock_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            # get_db_dependency is an async generator, iterate to get the session
            async_gen = get_db_dependency()
            session = await async_gen.__anext__()
            assert isinstance(session, AsyncSession)
            assert session == mock_session
            # Clean up the generator
            try:
                await async_gen.aclose()
            except StopAsyncIteration:
                pass
    async def test_get_db_dependency_validates_session_type(self):
        """Test that get_db_dependency validates session type"""
        invalid_session = MagicMock()  # Not an AsyncSession
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield invalid_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            with pytest.raises(RuntimeError, match="Expected AsyncSession"):
                async_gen = get_db_dependency()
                await async_gen.__anext__()
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
    async def test_fastapi_dependency_injection(self):
        """Test that FastAPI properly injects AsyncSession through DbDep"""
        app = FastAPI()
        mock_session = MagicMock(spec=AsyncSession)
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield mock_session
        
        @app.get("/test")
        async def test_endpoint(db: DbDep):
            assert isinstance(db, AsyncSession)
            return {"session_type": type(db).__name__}
        
        # Mock the underlying _get_async_db function that get_db_dependency uses
        with patch('app.dependencies._get_async_db', mock_get_async_db), \
             patch('app.dependencies.logger') as mock_logger:
            with TestClient(app) as client:
                response = client.get("/test")
                assert response.status_code == 200
                assert response.json()["session_type"] == "MagicMock"
    async def test_connection_pool_logging(self):
        """Test that connection pool operations are properly logged"""
        mock_session = MagicMock(spec=AsyncSession)
        
        @asynccontextmanager
        async def mock_get_async_db():
            yield mock_session
        
        with patch('app.dependencies._get_async_db', mock_get_async_db):
            with patch('app.dependencies.logger') as mock_logger:
                async_gen = get_db_dependency()
                session = await async_gen.__anext__()
                mock_logger.debug.assert_called_with(
                    f"Dependency injected session type: {type(mock_session).__name__}"
                )
                try:
                    await async_gen.aclose()
                except StopAsyncIteration:
                    pass
    async def test_context_manager_not_passed_to_repository(self):
        """Ensure context manager itself is never passed to repository methods"""
        from contextlib import _AsyncGeneratorContextManager
        
        # Create a mock context manager without execute attribute
        mock_context_manager = MagicMock(spec=_AsyncGeneratorContextManager)
        # Remove execute attribute to ensure AttributeError naturally occurs
        del mock_context_manager.execute
        
        thread_repo = ThreadRepository()
        
        # Repository catches AttributeError and returns empty list
        # This tests that the context manager fails gracefully when used incorrectly
        with patch('app.services.database.thread_repository.logger'):
            result = await thread_repo.find_by_user(mock_context_manager, "test_user_id")
            assert result == []  # Repository should return empty list when error occurs
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
            async_gen = get_db_dependency()
            session = await async_gen.__anext__()
            assert session == mock_session
            try:
                await async_gen.aclose()
            except StopAsyncIteration:
                pass
    async def test_multiple_concurrent_sessions(self):
        """Test that multiple concurrent sessions work correctly"""
        sessions = []
        
        async def create_session():
            async_gen = get_db_dependency()
            session = await async_gen.__anext__()
            sessions.append(session)
            try:
                await async_gen.aclose()
            except StopAsyncIteration:
                pass
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