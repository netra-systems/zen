"""
Test Repository Factory for Auth Service
Provides repository instances for testing without direct database access
"""
import asyncio
from typing import AsyncGenerator, Optional
from test_framework.database.test_database_manager import TestDatabaseManager as DatabaseTestManager
# Removed non-existent AuthManager import - using AuthDatabaseManager instead
from shared.isolated_environment import IsolatedEnvironment

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.database.models import Base
from auth_service.auth_core.database.repository import (
    AuthUserRepository,
    AuthSessionRepository,
    AuthAuditRepository
)
from shared.isolated_environment import get_env


class RepositoryFactory:
    """Factory for creating test repository instances with proper isolation."""
    
    def __init__(self, use_real_db: bool = False):
        """
        Initialize test repository factory.
        
        Args:
            use_real_db: If True, use real database; if False, use mocks
        """
        self.use_real_db = use_real_db
        self._engine = None
        self._session_factory = None
        self._session = None
    
    async def initialize(self):
        """Initialize the factory with database connection."""
        if self.use_real_db:
            await self._initialize_real_db()
        else:
            await self._initialize_mock_db()
    
    async def _initialize_real_db(self):
        """Initialize with real database connection."""
        database_url = AuthConfig.get_database_url()
        self._engine = AuthDatabaseManager.create_async_engine(database_url)
        
        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        from sqlalchemy.ext.asyncio import async_sessionmaker
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def _initialize_mock_db(self):
        """Initialize with mock database."""
        self._session = AsyncMock(spec=AsyncSession)
        
        # Setup basic mock behaviors
        self._session.commit = AsyncNone  # TODO: Use real service instance
        self._session.rollback = AsyncNone  # TODO: Use real service instance
        self._session.close = AsyncNone  # TODO: Use real service instance
        self._session.flush = AsyncNone  # TODO: Use real service instance
        self._session.add = MagicNone  # TODO: Use real service instance
        self._session.execute = AsyncNone  # TODO: Use real service instance
        self._session.begin = AsyncNone  # TODO: Use real service instance
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if self.use_real_db:
            if not self._session_factory:
                await self.initialize()
            return self._session_factory()
        else:
            if not self._session:
                await self.initialize()
            return self._session
    
    async def get_user_repository(self) -> AuthUserRepository:
        """Get user repository instance."""
        session = await self.get_session()
        return AuthUserRepository(session)
    
    async def get_session_repository(self) -> AuthSessionRepository:
        """Get session repository instance."""
        session = await self.get_session()
        return AuthSessionRepository(session)
    
    async def get_audit_repository(self) -> AuthAuditRepository:
        """Get audit repository instance."""
        session = await self.get_session()
        return AuthAuditRepository(session)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.use_real_db:
            if self._engine:
                # Clean up tables
                async with self._engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await self._engine.dispose()
        else:
            # Clean up mocks if needed
            pass


@pytest.fixture
async def test_repository_factory() -> AsyncGenerator[RepositoryFactory, None]:
    """Pytest fixture for test repository factory with mock database."""
    factory = RepositoryFactory(use_real_db=False)
    await factory.initialize()
    yield factory
    await factory.cleanup()


@pytest.fixture
async def real_test_repository_factory() -> AsyncGenerator[RepositoryFactory, None]:
    """Pytest fixture for test repository factory with real database."""
    factory = RepositoryFactory(use_real_db=True)
    await factory.initialize()
    yield factory
    await factory.cleanup()


@pytest.fixture
async def mock_user_repository(test_repository_factory: RepositoryFactory) -> AuthUserRepository:
    """Get mock user repository."""
    return await test_repository_factory.get_user_repository()


@pytest.fixture
async def mock_session_repository(test_repository_factory: RepositoryFactory) -> AuthSessionRepository:
    """Get mock session repository."""
    return await test_repository_factory.get_session_repository()


@pytest.fixture
async def mock_audit_repository(test_repository_factory: RepositoryFactory) -> AuthAuditRepository:
    """Get mock audit repository."""
    return await test_repository_factory.get_audit_repository()


@pytest.fixture
async def real_user_repository(real_test_repository_factory: RepositoryFactory) -> AuthUserRepository:
    """Get real user repository."""
    return await real_test_repository_factory.get_user_repository()


@pytest.fixture
async def real_session_repository(real_test_repository_factory: RepositoryFactory) -> AuthSessionRepository:
    """Get real session repository."""
    return await real_test_repository_factory.get_session_repository()


@pytest.fixture
async def real_audit_repository(real_test_repository_factory: RepositoryFactory) -> AuthAuditRepository:
    """Get real audit repository."""
    return await real_test_repository_factory.get_audit_repository()