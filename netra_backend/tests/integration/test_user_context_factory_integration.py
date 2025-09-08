"""
Test User Context Factory and Isolation Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure complete multi-user isolation and prevent data leakage between user sessions
- Value Impact: Multi-user isolation is critical for data security and user trust
- Strategic Impact: Platform must support 10+ concurrent users with zero cross-contamination

This test suite validates the user context factory and isolation patterns:
1. User context creation and lifecycle management
2. Factory pattern isolation between concurrent users
3. Session scoping and proper cleanup
4. Data isolation verification across user boundaries
"""

import asyncio
import uuid
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, SessionID,
    AgentExecutionContext, ExecutionContextState,
    ensure_user_id, ensure_thread_id, ensure_run_id
)

# User context and factory components
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextFactory
)
from netra_backend.app.agents.supervisor.execution_factory import (
    ExecutionEngineFactory,
    ExecutionFactoryConfig
)
from netra_backend.app.services.factory_adapter import (
    FactoryAdapter,
    AdapterConfig,
    create_request_context
)
from netra_backend.app.dependencies import (
    validate_session_is_request_scoped,
    SessionIsolationError
)

# Models for testing
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread
from netra_backend.app.models.session import Session


class TestUserContextFactoryIntegration(BaseIntegrationTest):
    """Test user context factory with real isolation and database persistence."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_creates_isolated_contexts(self, real_services_fixture, isolated_env):
        """Test UserContextFactory creates properly isolated execution contexts."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Create test users
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        
        user1 = User(id=str(user1_id), email="user1@isolation.test", name="User 1")
        user2 = User(id=str(user2_id), email="user2@isolation.test", name="User 2")
        
        db.add_all([user1, user2])
        await db.commit()
        
        # Create separate threads
        thread1_id = ensure_thread_id(str(uuid.uuid4()))
        thread2_id = ensure_thread_id(str(uuid.uuid4()))
        
        thread1 = Thread(id=str(thread1_id), user_id=str(user1_id), title="User 1 Thread")
        thread2 = Thread(id=str(thread2_id), user_id=str(user2_id), title="User 2 Thread")
        
        db.add_all([thread1, thread2])
        await db.commit()
        
        # Initialize context factory
        context_factory = UserContextFactory()
        
        # Create isolated contexts for each user
        context1 = await context_factory.create_user_context(
            user_id=user1_id,
            thread_id=thread1_id,
            run_id=ensure_run_id(str(uuid.uuid4())),
            database_session=db,
            isolation_level="per_user"
        )
        
        context2 = await context_factory.create_user_context(
            user_id=user2_id,
            thread_id=thread2_id,
            run_id=ensure_run_id(str(uuid.uuid4())),
            database_session=db,
            isolation_level="per_user"
        )
        
        # Verify contexts are properly isolated
        assert context1.user_id != context2.user_id
        assert context1.thread_id != context2.thread_id
        assert context1.run_id != context2.run_id
        
        # Verify each context can only access its own user's data
        user1_from_context1 = await context1.get_user()
        assert user1_from_context1.id == str(user1_id)
        assert user1_from_context1.email == "user1@isolation.test"
        
        user2_from_context2 = await context2.get_user()
        assert user2_from_context2.id == str(user2_id)
        assert user2_from_context2.email == "user2@isolation.test"
        
        # Verify cross-contamination prevention
        # Context1 should not be able to access User2's data
        user2_threads_from_context1 = await context1.get_user_threads()
        context1_thread_ids = [thread.id for thread in user2_threads_from_context1]
        assert str(thread2_id) not in context1_thread_ids
        
        # Context2 should not be able to access User1's data  
        user1_threads_from_context2 = await context2.get_user_threads()
        context2_thread_ids = [thread.id for thread in user1_threads_from_context2]
        assert str(thread1_id) not in context2_thread_ids
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_context_creation_no_leakage(self, real_services_fixture, isolated_env):
        """Test concurrent context creation with no data leakage between users."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        context_factory = UserContextFactory()
        
        # Create multiple users for concurrent testing
        user_count = 5
        users = []
        threads = []
        
        for i in range(user_count):
            user_id = ensure_user_id(str(uuid.uuid4()))
            thread_id = ensure_thread_id(str(uuid.uuid4()))
            
            user = User(
                id=str(user_id),
                email=f"concurrent.user.{i}@test.com",
                name=f"Concurrent User {i}",
                created_at=datetime.utcnow()
            )
            
            thread = Thread(
                id=str(thread_id),
                user_id=str(user_id),
                title=f"Concurrent Thread {i}",
                created_at=datetime.utcnow()
            )
            
            users.append(user)
            threads.append(thread)
        
        db.add_all(users + threads)
        await db.commit()
        
        async def create_context_for_user(user: User, thread: Thread) -> UserExecutionContext:
            """Create context for a specific user."""
            return await context_factory.create_user_context(
                user_id=ensure_user_id(user.id),
                thread_id=ensure_thread_id(thread.id),
                run_id=ensure_run_id(str(uuid.uuid4())),
                database_session=db,
                isolation_level="per_request"
            )
        
        # Create contexts concurrently
        context_tasks = [
            create_context_for_user(users[i], threads[i]) 
            for i in range(user_count)
        ]
        
        contexts = await asyncio.gather(*context_tasks)
        
        # Verify all contexts were created successfully
        assert len(contexts) == user_count
        
        # Verify each context has the correct user association
        for i, context in enumerate(contexts):
            assert context.user_id == ensure_user_id(users[i].id)
            assert context.thread_id == ensure_thread_id(threads[i].id)
            
            # Verify context can access its own user's data
            context_user = await context.get_user()
            assert context_user.id == users[i].id
            assert context_user.email == f"concurrent.user.{i}@test.com"
        
        # Verify no cross-contamination between contexts
        for i in range(user_count):
            context_threads = await contexts[i].get_user_threads()
            context_thread_ids = [thread.id for thread in context_threads]
            
            # Each context should only see its own thread
            assert str(threads[i].id) in context_thread_ids
            
            # Each context should NOT see other users' threads
            for j in range(user_count):
                if i != j:
                    assert str(threads[j].id) not in context_thread_ids
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_scoped_context_lifecycle(self, real_services_fixture, isolated_env):
        """Test session-scoped context lifecycle and proper cleanup."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Verify session is properly scoped at the start
        validate_session_is_request_scoped(db, "lifecycle_test_start")
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        session_id = SessionID(str(uuid.uuid4()))
        
        # Create test data
        test_user = User(id=str(user_id), email="lifecycle@test.com", name="Lifecycle User")
        test_thread = Thread(id=str(thread_id), user_id=str(user_id), title="Lifecycle Thread")
        test_session = Session(
            id=str(session_id),
            user_id=str(user_id),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        db.add_all([test_user, test_thread, test_session])
        await db.commit()
        
        # Create session manager for context lifecycle
        session_manager = UserSessionManager()
        
        # Test context creation within session scope
        @asynccontextmanager
        async def scoped_context_manager():
            """Context manager for scoped user context."""
            context = await session_manager.create_scoped_context(
                user_id=user_id,
                thread_id=thread_id,
                session_id=session_id,
                database_session=db
            )
            
            try:
                yield context
            finally:
                await session_manager.cleanup_context(context)
        
        # Use scoped context
        async with scoped_context_manager() as scoped_context:
            # Verify context is active and functional
            assert scoped_context.user_id == user_id
            assert scoped_context.thread_id == thread_id
            assert scoped_context.is_active()
            
            # Verify database access works within scope
            context_user = await scoped_context.get_user()
            assert context_user.email == "lifecycle@test.com"
            
            # Verify session validation
            is_valid_session = await scoped_context.validate_session()
            assert is_valid_session
        
        # After context manager exits, context should be cleaned up
        assert not scoped_context.is_active()
        
        # Verify session is still properly scoped after cleanup
        validate_session_is_request_scoped(db, "lifecycle_test_end")
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_adapter_integration_with_real_services(self, real_services_fixture, isolated_env):
        """Test FactoryAdapter integration with real database and Redis services."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        # Create test data
        test_user = User(id=str(user_id), email="adapter@test.com", name="Adapter Test User")
        test_thread = Thread(id=str(thread_id), user_id=str(user_id), title="Adapter Test Thread")
        
        db.add_all([test_user, test_thread])
        await db.commit()
        
        # Configure factory adapter
        adapter_config = AdapterConfig(
            user_id=user_id,
            thread_id=thread_id,
            database_session=db,
            redis_connection=redis,
            enable_caching=True,
            isolation_level="per_request"
        )
        
        factory_adapter = FactoryAdapter(config=adapter_config)
        
        # Create request context through adapter
        request_context = await factory_adapter.create_request_context(
            request_id=RequestID(str(uuid.uuid4())),
            user_agent="Integration Test Client",
            client_ip="127.0.0.1"
        )
        
        # Verify request context integrates with real services
        assert request_context.user_id == user_id
        assert request_context.has_database_access()
        assert request_context.has_cache_access()
        
        # Test database operations through adapter
        user_from_adapter = await factory_adapter.get_user_by_id(user_id)
        assert user_from_adapter.email == "adapter@test.com"
        
        # Test caching operations through adapter
        cache_key = f"user:{user_id}:profile"
        cache_data = {"email": "adapter@test.com", "name": "Adapter Test User"}
        
        await factory_adapter.set_cache(cache_key, cache_data)
        cached_result = await factory_adapter.get_cache(cache_key)
        
        assert cached_result["email"] == "adapter@test.com"
        assert cached_result["name"] == "Adapter Test User"
        
        # Verify adapter maintains isolation
        isolation_report = await factory_adapter.generate_isolation_report()
        assert isolation_report["user_id"] == str(user_id)
        assert isolation_report["isolation_violations"] == 0
        assert isolation_report["cache_namespace_isolated"] is True
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_factory_user_context_integration(self, real_services_fixture, isolated_env):
        """Test ExecutionEngineFactory integration with user context isolation."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Create test users for factory testing
        user1_id = ensure_user_id(str(uuid.uuid4()))
        user2_id = ensure_user_id(str(uuid.uuid4()))
        
        user1 = User(id=str(user1_id), email="factory1@test.com", name="Factory User 1")
        user2 = User(id=str(user2_id), email="factory2@test.com", name="Factory User 2")
        
        thread1_id = ensure_thread_id(str(uuid.uuid4()))
        thread2_id = ensure_thread_id(str(uuid.uuid4()))
        
        thread1 = Thread(id=str(thread1_id), user_id=str(user1_id), title="Factory Thread 1")
        thread2 = Thread(id=str(thread2_id), user_id=str(user2_id), title="Factory Thread 2")
        
        db.add_all([user1, user2, thread1, thread2])
        await db.commit()
        
        # Create execution factory configurations for each user
        factory_config1 = ExecutionFactoryConfig(
            user_id=user1_id,
            thread_id=thread1_id,
            run_id=ensure_run_id(str(uuid.uuid4())),
            database_session=db,
            isolation_level="per_user"
        )
        
        factory_config2 = ExecutionFactoryConfig(
            user_id=user2_id,
            thread_id=thread2_id,
            run_id=ensure_run_id(str(uuid.uuid4())),
            database_session=db,
            isolation_level="per_user"
        )
        
        # Create separate execution factories
        execution_factory1 = ExecutionEngineFactory(config=factory_config1)
        execution_factory2 = ExecutionEngineFactory(config=factory_config2)
        
        # Create execution contexts through factories
        context1 = await execution_factory1.create_execution_context()
        context2 = await execution_factory2.create_execution_context()
        
        # Verify contexts are isolated
        assert context1.user_id == user1_id
        assert context2.user_id == user2_id
        assert context1.thread_id != context2.thread_id
        
        # Verify each factory can only access its user's data
        user1_data = await execution_factory1.get_user_execution_data()
        user2_data = await execution_factory2.get_user_execution_data()
        
        assert user1_data["user"]["email"] == "factory1@test.com"
        assert user2_data["user"]["email"] == "factory2@test.com"
        
        # Verify cross-contamination protection
        factory1_threads = await execution_factory1.get_available_threads()
        factory2_threads = await execution_factory2.get_available_threads()
        
        factory1_thread_ids = [thread["id"] for thread in factory1_threads]
        factory2_thread_ids = [thread["id"] for thread in factory2_threads]
        
        # Each factory should only see its own user's threads
        assert str(thread1_id) in factory1_thread_ids
        assert str(thread2_id) not in factory1_thread_ids
        
        assert str(thread2_id) in factory2_thread_ids
        assert str(thread1_id) not in factory2_thread_ids
        
        await db.close()

    def _create_test_db_session(self) -> AsyncSession:
        """Create test database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session

    def _create_test_redis_connection(self):
        """Create test Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock()
        mock_redis.delete = AsyncMock()
        return mock_redis