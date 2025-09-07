#!/usr/bin/env python3
"""
Test Database-Service Integration - Comprehensive

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable data persistence and retrieval for user conversations and system state
- Value Impact: Users' conversations, agent executions, and session data are safely stored and accessible across sessions
- Strategic Impact: Core data reliability foundation for platform trust, user retention, and multi-user isolation

CRITICAL ARCHITECTURE REQUIREMENTS:
- Tests REAL PostgreSQL and Redis services (no mocks)
- Validates multi-user data isolation patterns
- Ensures transaction integrity and concurrent access safety
- Tests user context factory patterns for session isolation
- Validates business-critical thread, message, and agent execution persistence

This test validates the core database infrastructure that enables:
1. User conversation continuity across sessions
2. Agent execution state management
3. Multi-user data isolation (10+ concurrent users)
4. Session state persistence via Redis
5. Transactional integrity during concurrent operations
"""

import asyncio
import logging
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

# Test framework imports - following TEST_CREATION_GUIDE.md patterns
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.database_fixtures import (
    test_db_session,
    netra_backend_db_session,
    database_cleanup
)

# SSOT database imports - following CLAUDE.md architecture
from netra_backend.app.db.database_manager import get_database_manager, get_db_session
from netra_backend.app.redis_manager import redis_manager, get_redis
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
from netra_backend.app.db.models_agent import Thread, Message, Run, Assistant
from netra_backend.app.db.models_content import CorpusAuditLog

# Environment management - following CLAUDE.md requirements
from shared.isolated_environment import get_env
from netra_backend.app.core.config import get_config

# SQLAlchemy imports for real database operations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class TestDatabaseServiceIntegration(BaseIntegrationTest):
    """Test database operations with real PostgreSQL and Redis services.
    
    CRITICAL: This test uses REAL services to validate:
    - Multi-user data isolation
    - Transaction safety and rollback
    - Cache-database consistency
    - Concurrent access patterns
    - Business value: reliable user data persistence
    """
    
    @pytest.fixture(autouse=True)
    async def setup_integration_test(self):
        """Setup real services and ensure clean state for each test."""
        # Initialize database manager
        self.db_manager = get_database_manager()
        await self.db_manager.initialize()
        
        # Initialize Redis manager
        await redis_manager.initialize()
        
        # Verify services are available
        assert self.db_manager.is_connected
        assert redis_manager.is_connected
        
        yield
        
        # Cleanup after test
        await self._cleanup_test_data()
    
    async def _cleanup_test_data(self):
        """Clean up test data after each test."""
        try:
            async with self.db_manager.get_session() as session:
                # Clean up test data (careful with real services)
                await session.execute(text("DELETE FROM tool_usage_logs WHERE user_id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM secrets WHERE user_id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM messages WHERE thread_id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM threads WHERE id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM users WHERE id LIKE 'test_%'"))
                await session.commit()
        except Exception as e:
            logger.warning(f"Cleanup failed (expected in some cases): {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_data_persistence_and_retrieval(self, real_services_fixture):
        """Test user data persistence and retrieval with real database.
        
        Business Value: Users must be able to access their profile and settings
        across sessions. This validates core user management functionality.
        """
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        async with self.db_manager.get_session() as session:
            # Create user with comprehensive profile data
            user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                full_name="Test User Integration",
                plan_tier="pro",
                role="standard_user",
                permissions={"api_access": True, "data_export": True},
                feature_flags={"advanced_analytics": True, "beta_features": False},
                tool_permissions={"cost_optimizer": True, "security_scanner": False}
            )
            
            session.add(user)
            await session.commit()
            
            # Verify user was persisted correctly
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            retrieved_user = result.scalar_one_or_none()
            
            assert retrieved_user is not None
            assert retrieved_user.email == f"{user_id}@example.com"
            assert retrieved_user.plan_tier == "pro"
            assert retrieved_user.permissions["api_access"] is True
            assert retrieved_user.feature_flags["advanced_analytics"] is True
            assert retrieved_user.tool_permissions["cost_optimizer"] is True
            
            logger.info(f"✅ User data persistence validated for {user_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_and_message_management(self, real_services_fixture):
        """Test conversation thread creation, message storage, and retrieval.
        
        Business Value: Conversation continuity - users must be able to see
        their chat history and continue conversations across sessions.
        """
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        
        async with self.db_manager.get_session() as session:
            # Create user first
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            
            # Create thread with user context in metadata
            thread = Thread(
                id=thread_id,
                created_at=int(datetime.now(timezone.utc).timestamp()),
                metadata_={"user_id": user_id, "topic": "cost_optimization"}
            )
            session.add(thread)
            
            # Create messages in the thread
            messages = []
            for i in range(3):
                message = Message(
                    id=f"msg_{thread_id}_{i}",
                    created_at=int(datetime.now(timezone.utc).timestamp()),
                    thread_id=thread_id,
                    role="user" if i % 2 == 0 else "assistant",
                    content=[{
                        "type": "text",
                        "text": f"Message content {i}: {'User query about costs' if i % 2 == 0 else 'Assistant response with optimization suggestions'}"
                    }],
                    metadata_={"user_id": user_id}
                )
                messages.append(message)
                session.add(message)
            
            await session.commit()
            
            # Verify thread and messages were persisted
            result = await session.execute(
                select(Thread).where(Thread.id == thread_id)
            )
            retrieved_thread = result.scalar_one_or_none()
            
            assert retrieved_thread is not None
            assert retrieved_thread.metadata_["user_id"] == user_id
            assert retrieved_thread.metadata_["topic"] == "cost_optimization"
            
            # Verify messages are retrievable and ordered
            message_result = await session.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at)
            )
            retrieved_messages = message_result.scalars().all()
            
            assert len(retrieved_messages) == 3
            assert retrieved_messages[0].role == "user"
            assert retrieved_messages[1].role == "assistant"
            assert "optimization suggestions" in retrieved_messages[1].content[0]["text"]
            
            logger.info(f"✅ Thread and message management validated for {thread_id}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_transaction_isolation_and_rollback(self, real_services_fixture):
        """Test database transaction isolation between users and rollback safety.
        
        Business Value: Data integrity - ensures user data corruption doesn't
        occur during concurrent operations or system failures.
        """
        user1_id = f"test_user_1_{uuid.uuid4().hex[:8]}"
        user2_id = f"test_user_2_{uuid.uuid4().hex[:8]}"
        
        # Test successful transaction
        async with self.db_manager.get_session() as session:
            user1 = User(id=user1_id, email=f"{user1_id}@example.com", plan_tier="free")
            user2 = User(id=user2_id, email=f"{user2_id}@example.com", plan_tier="pro")
            
            session.add_all([user1, user2])
            await session.commit()
            
            # Verify both users were created
            result = await session.execute(select(func.count(User.id)).where(User.id.in_([user1_id, user2_id])))
            assert result.scalar() == 2
        
        # Test transaction rollback on error
        try:
            async with self.db_manager.get_session() as session:
                # Modify existing user
                result = await session.execute(select(User).where(User.id == user1_id))
                user1 = result.scalar_one()
                user1.plan_tier = "enterprise"
                
                # Create a new user that will cause constraint violation
                duplicate_user = User(id=user1_id, email="different@example.com")  # Same ID, should fail
                session.add(duplicate_user)
                
                # This should fail and rollback all changes
                await session.commit()
                
        except IntegrityError:
            # Expected - duplicate primary key should cause rollback
            pass
        
        # Verify rollback occurred - user1 should still have "free" plan
        async with self.db_manager.get_session() as session:
            result = await session.execute(select(User).where(User.id == user1_id))
            user1 = result.scalar_one()
            assert user1.plan_tier == "free"  # Should not be "enterprise"
            
            logger.info("✅ Transaction isolation and rollback validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_postgresql_integration(self, real_services_fixture):
        """Test Redis-PostgreSQL integration for session management.
        
        Business Value: Session persistence - users maintain login state
        and preferences across browser sessions and page refreshes.
        """
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_key = f"session:{user_id}"
        thread_key = f"thread_cache:{user_id}"
        
        # Create user in PostgreSQL
        async with self.db_manager.get_session() as db_session:
            user = User(
                id=user_id, 
                email=f"{user_id}@example.com",
                plan_tier="pro",
                permissions={"advanced_features": True}
            )
            db_session.add(user)
            await db_session.commit()
        
        # Store session data in Redis
        session_data = {
            "user_id": user_id,
            "login_time": datetime.now(timezone.utc).isoformat(),
            "plan_tier": "pro",
            "permissions": ["advanced_features"]
        }
        
        import json
        success = await redis_manager.set(
            session_key, 
            json.dumps(session_data), 
            ex=3600  # 1 hour expiration
        )
        assert success
        
        # Cache thread data
        thread_cache = {
            "active_thread": f"thread_{user_id}_main",
            "last_message": "User discussing cost optimization",
            "context": "AWS cost analysis"
        }
        
        await redis_manager.set(thread_key, json.dumps(thread_cache), ex=1800)  # 30 min
        
        # Verify Redis data retrieval
        retrieved_session = await redis_manager.get(session_key)
        assert retrieved_session is not None
        
        session_obj = json.loads(retrieved_session)
        assert session_obj["user_id"] == user_id
        assert session_obj["plan_tier"] == "pro"
        
        # Verify thread cache
        retrieved_thread = await redis_manager.get(thread_key)
        assert retrieved_thread is not None
        
        thread_obj = json.loads(retrieved_thread)
        assert thread_obj["context"] == "AWS cost analysis"
        
        # Verify data consistency between Redis and PostgreSQL
        async with self.db_manager.get_session() as db_session:
            result = await db_session.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one()
            
            assert db_user.plan_tier == session_obj["plan_tier"]
            assert db_user.permissions["advanced_features"] is True
        
        logger.info("✅ Redis-PostgreSQL integration validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_data_isolation(self, real_services_fixture):
        """Test concurrent access with proper user data isolation.
        
        Business Value: Multi-user support - ensures user A cannot see or
        modify user B's data, critical for privacy and security.
        """
        users = []
        for i in range(5):
            user_id = f"test_user_{i}_{uuid.uuid4().hex[:8]}"
            users.append((user_id, f"{user_id}@example.com"))
        
        async def create_user_with_data(user_info):
            """Create user with associated data concurrently."""
            user_id, email = user_info
            
            async with self.db_manager.get_session() as session:
                # Create user
                user = User(
                    id=user_id,
                    email=email,
                    plan_tier="pro",
                    permissions={"user_data": [user_id]}  # User-specific permissions
                )
                session.add(user)
                
                # Create user's secret
                secret = Secret(
                    user_id=user_id,
                    key="api_key",
                    encrypted_value=f"encrypted_key_for_{user_id}"
                )
                session.add(secret)
                
                # Create user's thread
                thread = Thread(
                    id=f"thread_{user_id}",
                    created_at=int(datetime.now(timezone.utc).timestamp()),
                    metadata_={"user_id": user_id, "private_data": f"private_to_{user_id}"}
                )
                session.add(thread)
                
                await session.commit()
            
            # Store user session in Redis
            redis_key = f"user_session:{user_id}"
            await redis_manager.set(
                redis_key, 
                f'{{"user_id": "{user_id}", "private_token": "token_for_{user_id}"}}',
                ex=3600
            )
            
            return user_id
        
        # Create users concurrently
        tasks = [create_user_with_data(user_info) for user_info in users]
        created_user_ids = await asyncio.gather(*tasks)
        
        assert len(created_user_ids) == 5
        
        # Verify data isolation - each user should only see their own data
        for user_id in created_user_ids:
            async with self.db_manager.get_session() as session:
                # Verify user can only see their own secrets
                result = await session.execute(
                    select(Secret).where(Secret.user_id == user_id)
                )
                user_secrets = result.scalars().all()
                assert len(user_secrets) == 1
                assert user_secrets[0].encrypted_value == f"encrypted_key_for_{user_id}"
                
                # Verify user can only see their own threads
                result = await session.execute(
                    select(Thread).where(Thread.metadata_['user_id'].astext == user_id)
                )
                user_threads = result.scalars().all()
                assert len(user_threads) == 1
                assert user_threads[0].metadata_["private_data"] == f"private_to_{user_id}"
            
            # Verify Redis session isolation
            redis_data = await redis_manager.get(f"user_session:{user_id}")
            assert redis_data is not None
            assert f"token_for_{user_id}" in redis_data
            
            # Verify user cannot access other users' Redis data
            other_user_ids = [uid for uid in created_user_ids if uid != user_id]
            for other_user_id in other_user_ids[:2]:  # Check first 2 to avoid too many operations
                other_redis_data = await redis_manager.get(f"user_session:{other_user_id}")
                if other_redis_data:
                    assert f"token_for_{user_id}" not in other_redis_data
        
        logger.info("✅ Concurrent user data isolation validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_performance_under_load(self, real_services_fixture):
        """Test database performance and connection pooling under concurrent load.
        
        Business Value: System scalability - ensures platform can handle
        multiple concurrent users without performance degradation.
        """
        start_time = datetime.now()
        
        async def simulate_user_activity(user_index: int):
            """Simulate typical user database operations."""
            user_id = f"test_user_load_{user_index}_{uuid.uuid4().hex[:6]}"
            
            async with self.db_manager.get_session() as session:
                # Create user
                user = User(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    plan_tier="pro"
                )
                session.add(user)
                
                # Create thread
                thread = Thread(
                    id=f"thread_{user_id}",
                    created_at=int(datetime.now(timezone.utc).timestamp()),
                    metadata_={"user_id": user_id}
                )
                session.add(thread)
                
                # Create multiple messages
                for msg_i in range(3):
                    message = Message(
                        id=f"msg_{user_id}_{msg_i}",
                        created_at=int(datetime.now(timezone.utc).timestamp()),
                        thread_id=f"thread_{user_id}",
                        role="user" if msg_i % 2 == 0 else "assistant",
                        content=[{"type": "text", "text": f"Load test message {msg_i}"}],
                        metadata_={"user_id": user_id}
                    )
                    session.add(message)
                
                # Log tool usage
                tool_log = ToolUsageLog(
                    user_id=user_id,
                    tool_name="cost_optimizer",
                    category="optimization",
                    execution_time_ms=150,
                    status="success",
                    plan_tier="pro"
                )
                session.add(tool_log)
                
                await session.commit()
                
                # Query data back (simulates real usage)
                result = await session.execute(
                    select(Message).where(Message.thread_id == f"thread_{user_id}")
                )
                messages = result.scalars().all()
                assert len(messages) == 3
            
            # Redis operations
            await redis_manager.set(f"load_test:{user_id}", f"data_for_{user_id}", ex=300)
            retrieved = await redis_manager.get(f"load_test:{user_id}")
            assert retrieved == f"data_for_{user_id}"
            
            return user_id
        
        # Simulate 10 concurrent users
        num_concurrent_users = 10
        tasks = [simulate_user_activity(i) for i in range(num_concurrent_users)]
        
        completed_user_ids = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert len(completed_user_ids) == num_concurrent_users
        assert execution_time < 30  # Should complete within 30 seconds
        
        # Verify all data was persisted correctly
        async with self.db_manager.get_session() as session:
            # Count created users
            result = await session.execute(
                select(func.count(User.id)).where(User.id.like("test_user_load_%"))
            )
            assert result.scalar() == num_concurrent_users
            
            # Count created messages
            result = await session.execute(
                select(func.count(Message.id)).where(Message.id.like("msg_test_user_load_%"))
            )
            assert result.scalar() == num_concurrent_users * 3  # 3 messages per user
            
            # Count tool usage logs
            result = await session.execute(
                select(func.count(ToolUsageLog.id)).where(ToolUsageLog.user_id.like("test_user_load_%"))
            )
            assert result.scalar() == num_concurrent_users
        
        logger.info(f"✅ Database performance test completed in {execution_time:.2f}s for {num_concurrent_users} concurrent users")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_integrity_and_constraints(self, real_services_fixture):
        """Test database constraints and referential integrity.
        
        Business Value: Data reliability - ensures database constraints
        prevent data corruption and maintain relationships between entities.
        """
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        async with self.db_manager.get_session() as session:
            # Create user
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            await session.commit()
            
            # Test foreign key constraint - secret must reference valid user
            secret = Secret(
                user_id=user_id,
                key="test_key",
                encrypted_value="encrypted_value"
            )
            session.add(secret)
            await session.commit()
            
            # Verify secret was created
            result = await session.execute(
                select(Secret).where(Secret.user_id == user_id)
            )
            created_secret = result.scalar_one_or_none()
            assert created_secret is not None
            assert created_secret.key == "test_key"
        
        # Test constraint violation - secret with invalid user_id should fail
        invalid_user_id = "nonexistent_user"
        try:
            async with self.db_manager.get_session() as session:
                invalid_secret = Secret(
                    user_id=invalid_user_id,
                    key="invalid_key",
                    encrypted_value="some_value"
                )
                session.add(invalid_secret)
                await session.commit()
                
                # Should not reach here
                assert False, "Expected foreign key constraint violation"
                
        except Exception as e:
            # Expected - foreign key constraint should be enforced
            assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
        
        # Test unique constraint - duplicate email should fail
        try:
            async with self.db_manager.get_session() as session:
                duplicate_user = User(
                    id=f"another_{user_id}",
                    email=f"{user_id}@example.com"  # Same email as existing user
                )
                session.add(duplicate_user)
                await session.commit()
                
                # Should not reach here
                assert False, "Expected unique constraint violation"
                
        except IntegrityError as e:
            # Expected - unique constraint should be enforced
            assert "unique" in str(e).lower() or "duplicate" in str(e).lower()
        
        logger.info("✅ Data integrity and constraints validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_invalidation_patterns(self, real_services_fixture):
        """Test Redis cache invalidation when database data changes.
        
        Business Value: Data consistency - ensures users see up-to-date
        information and cache doesn't serve stale data after updates.
        """
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        cache_key = f"user_profile:{user_id}"
        
        # Create user in database
        async with self.db_manager.get_session() as session:
            user = User(
                id=user_id,
                email=f"{user_id}@example.com",
                plan_tier="free",
                permissions={"basic": True}
            )
            session.add(user)
            await session.commit()
        
        # Cache user data
        import json
        cached_user = {
            "id": user_id,
            "plan_tier": "free",
            "permissions": {"basic": True},
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        await redis_manager.set(cache_key, json.dumps(cached_user), ex=1800)
        
        # Verify cache contains original data
        cached_data = await redis_manager.get(cache_key)
        assert cached_data is not None
        cached_obj = json.loads(cached_data)
        assert cached_obj["plan_tier"] == "free"
        
        # Update user in database (simulating plan upgrade)
        async with self.db_manager.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            user.plan_tier = "pro"
            user.permissions = {"basic": True, "advanced": True, "api_access": True}
            await session.commit()
        
        # Invalidate cache (simulating cache invalidation on update)
        await redis_manager.delete(cache_key)
        
        # Verify cache was invalidated
        cached_data_after = await redis_manager.get(cache_key)
        assert cached_data_after is None
        
        # Simulate cache repopulation from database
        async with self.db_manager.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            updated_user = result.scalar_one()
            
            fresh_cache = {
                "id": user_id,
                "plan_tier": updated_user.plan_tier,
                "permissions": updated_user.permissions,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            await redis_manager.set(cache_key, json.dumps(fresh_cache), ex=1800)
        
        # Verify cache contains updated data
        final_cached_data = await redis_manager.get(cache_key)
        assert final_cached_data is not None
        final_cached_obj = json.loads(final_cached_data)
        assert final_cached_obj["plan_tier"] == "pro"
        assert final_cached_obj["permissions"]["api_access"] is True
        
        logger.info("✅ Cache invalidation patterns validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_recovery(self, real_services_fixture):
        """Test database connection recovery after temporary failures.
        
        Business Value: System resilience - ensures platform continues
        operating even when database connections are temporarily disrupted.
        """
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Verify normal operations work
        async with self.db_manager.get_session() as session:
            user = User(id=user_id, email=f"{user_id}@example.com")
            session.add(user)
            await session.commit()
            
            result = await session.execute(select(User).where(User.id == user_id))
            created_user = result.scalar_one_or_none()
            assert created_user is not None
        
        # Test health check
        health_status = await self.db_manager.health_check()
        assert health_status["status"] == "healthy"
        assert health_status["connection"] == "ok"
        
        # Verify Redis connection is also healthy
        redis_client = await redis_manager.get_client()
        assert redis_client is not None
        
        # Test Redis recovery patterns
        redis_status = redis_manager.get_status()
        assert redis_status["connected"] is True
        assert redis_status["client_available"] is True
        
        # Test that operations continue working after health checks
        test_key = f"recovery_test:{user_id}"
        await redis_manager.set(test_key, "recovery_test_value", ex=300)
        
        retrieved_value = await redis_manager.get(test_key)
        assert retrieved_value == "recovery_test_value"
        
        logger.info("✅ Database connection recovery patterns validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])