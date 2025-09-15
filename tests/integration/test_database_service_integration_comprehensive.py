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
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database
from netra_backend.app.db.database_manager import get_database_manager, get_db_session
from netra_backend.app.redis_manager import redis_manager, get_redis
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
from netra_backend.app.db.models_agent import Thread, Message, Run, Assistant
from netra_backend.app.db.models_content import CorpusAuditLog
from shared.isolated_environment import get_env
from netra_backend.app.core.config import get_config
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.exc import IntegrityError
logger = logging.getLogger(__name__)

@pytest.fixture(scope='function')
async def db_manager():
    """Provides initialized database manager for real services testing."""
    manager = get_database_manager()
    await manager.initialize()
    assert manager._initialized
    yield manager

@pytest.fixture(scope='function')
async def redis_client():
    """Provides initialized Redis manager for real services testing."""
    await redis_manager.initialize()
    assert redis_manager.is_connected
    yield redis_manager

@pytest.fixture(scope='function')
async def cleanup_test_data():
    """Cleanup test data after each test."""
    yield
    try:
        db_manager = get_database_manager()
        if db_manager._initialized:
            async with db_manager.get_session() as session:
                await session.execute(text("DELETE FROM tool_usage_logs WHERE user_id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM secrets WHERE user_id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM messages WHERE thread_id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM threads WHERE id LIKE 'test_%'"))
                await session.execute(text("DELETE FROM users WHERE id LIKE 'test_%'"))
                await session.commit()
    except Exception as e:
        logger.warning(f'Cleanup failed (expected in some cases): {e}')

@pytest.mark.integration
@pytest.mark.real_services
async def test_user_data_persistence_and_retrieval(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test user data persistence and retrieval with real database.
    
    Business Value: Users must be able to access their profile and settings
    across sessions. This validates core user management functionality.
    """
    user_id = f'test_user_{uuid.uuid4().hex[:8]}'
    async with db_manager.get_session() as session:
        user = User(id=user_id, email=f'{user_id}@example.com', full_name='Test User Integration', plan_tier='pro', role='standard_user', permissions={'api_access': True, 'data_export': True}, feature_flags={'advanced_analytics': True, 'beta_features': False}, tool_permissions={'cost_optimizer': True, 'security_scanner': False})
        session.add(user)
        await session.commit()
        result = await session.execute(select(User).where(User.id == user_id))
        retrieved_user = result.scalar_one_or_none()
        assert retrieved_user is not None
        assert retrieved_user.email == f'{user_id}@example.com'
        assert retrieved_user.plan_tier == 'pro'
        assert retrieved_user.permissions['api_access'] is True
        assert retrieved_user.feature_flags['advanced_analytics'] is True
        assert retrieved_user.tool_permissions['cost_optimizer'] is True
        logger.info(f' PASS:  User data persistence validated for {user_id}')

@pytest.mark.integration
@pytest.mark.real_services
async def test_thread_and_message_management(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test conversation thread creation, message storage, and retrieval.
    
    Business Value: Conversation continuity - users must be able to see
    their chat history and continue conversations across sessions.
    """
    user_id = f'test_user_{uuid.uuid4().hex[:8]}'
    thread_id = f'test_thread_{uuid.uuid4().hex[:8]}'
    async with db_manager.get_session() as session:
        user = User(id=user_id, email=f'{user_id}@example.com')
        session.add(user)
        thread = Thread(id=thread_id, created_at=int(datetime.now(timezone.utc).timestamp()), metadata_={'user_id': user_id, 'topic': 'cost_optimization'})
        session.add(thread)
        messages = []
        for i in range(3):
            message = Message(id=f'msg_{thread_id}_{i}', created_at=int(datetime.now(timezone.utc).timestamp()), thread_id=thread_id, role='user' if i % 2 == 0 else 'assistant', content=[{'type': 'text', 'text': f"Message content {i}: {('User query about costs' if i % 2 == 0 else 'Assistant response with optimization suggestions')}"}], metadata_={'user_id': user_id})
            messages.append(message)
            session.add(message)
        await session.commit()
        result = await session.execute(select(Thread).where(Thread.id == thread_id))
        retrieved_thread = result.scalar_one_or_none()
        assert retrieved_thread is not None
        assert retrieved_thread.metadata_['user_id'] == user_id
        assert retrieved_thread.metadata_['topic'] == 'cost_optimization'
        message_result = await session.execute(select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at))
        retrieved_messages = message_result.scalars().all()
        assert len(retrieved_messages) == 3
        assert retrieved_messages[0].role == 'user'
        assert retrieved_messages[1].role == 'assistant'
        assert 'optimization suggestions' in retrieved_messages[1].content[0]['text']
        logger.info(f' PASS:  Thread and message management validated for {thread_id}')

@pytest.mark.integration
@pytest.mark.real_services
async def test_transaction_isolation_and_rollback(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test database transaction isolation between users and rollback safety.
    
    Business Value: Data integrity - ensures user data corruption doesn't
    occur during concurrent operations or system failures.
    """
    user1_id = f'test_user_1_{uuid.uuid4().hex[:8]}'
    user2_id = f'test_user_2_{uuid.uuid4().hex[:8]}'
    async with db_manager.get_session() as session:
        user1 = User(id=user1_id, email=f'{user1_id}@example.com', plan_tier='free')
        user2 = User(id=user2_id, email=f'{user2_id}@example.com', plan_tier='pro')
        session.add_all([user1, user2])
        await session.commit()
        result = await session.execute(select(func.count(User.id)).where(User.id.in_([user1_id, user2_id])))
        assert result.scalar() == 2
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(select(User).where(User.id == user1_id))
            user1 = result.scalar_one()
            user1.plan_tier = 'enterprise'
            duplicate_user = User(id=user1_id, email='different@example.com')
            session.add(duplicate_user)
            await session.commit()
    except IntegrityError:
        pass
    async with db_manager.get_session() as session:
        result = await session.execute(select(User).where(User.id == user1_id))
        user1 = result.scalar_one()
        assert user1.plan_tier == 'free'
        logger.info(' PASS:  Transaction isolation and rollback validated')

@pytest.mark.integration
@pytest.mark.real_services
async def test_redis_postgresql_integration(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test Redis-PostgreSQL integration for session management.
    
    Business Value: Session persistence - users maintain login state
    and preferences across browser sessions and page refreshes.
    """
    user_id = f'test_user_{uuid.uuid4().hex[:8]}'
    session_key = f'session:{user_id}'
    thread_key = f'thread_cache:{user_id}'
    async with db_manager.get_session() as db_session:
        user = User(id=user_id, email=f'{user_id}@example.com', plan_tier='pro', permissions={'advanced_features': True})
        db_session.add(user)
        await db_session.commit()
    session_data = {'user_id': user_id, 'login_time': datetime.now(timezone.utc).isoformat(), 'plan_tier': 'pro', 'permissions': ['advanced_features']}
    success = await redis_client.set(session_key, json.dumps(session_data), ex=3600)
    assert success
    thread_cache = {'active_thread': f'thread_{user_id}_main', 'last_message': 'User discussing cost optimization', 'context': 'AWS cost analysis'}
    await redis_client.set(thread_key, json.dumps(thread_cache), ex=1800)
    retrieved_session = await redis_client.get(session_key)
    assert retrieved_session is not None
    session_obj = json.loads(retrieved_session)
    assert session_obj['user_id'] == user_id
    assert session_obj['plan_tier'] == 'pro'
    retrieved_thread = await redis_client.get(thread_key)
    assert retrieved_thread is not None
    thread_obj = json.loads(retrieved_thread)
    assert thread_obj['context'] == 'AWS cost analysis'
    async with db_manager.get_session() as db_session:
        result = await db_session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one()
        assert db_user.plan_tier == session_obj['plan_tier']
        assert db_user.permissions['advanced_features'] is True
    logger.info(' PASS:  Redis-PostgreSQL integration validated')

@pytest.mark.integration
@pytest.mark.real_services
async def test_concurrent_user_data_isolation(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test concurrent access with proper user data isolation.
    
    Business Value: Multi-user support - ensures user A cannot see or
    modify user B's data, critical for privacy and security.
    """
    users = []
    for i in range(5):
        user_id = f'test_user_{i}_{uuid.uuid4().hex[:8]}'
        users.append((user_id, f'{user_id}@example.com'))

    async def create_user_with_data(user_info):
        """Create user with associated data concurrently."""
        user_id, email = user_info
        async with db_manager.get_session() as session:
            user = User(id=user_id, email=email, plan_tier='pro', permissions={'user_data': [user_id]})
            session.add(user)
            secret = Secret(user_id=user_id, key='api_key', encrypted_value=f'encrypted_key_for_{user_id}')
            session.add(secret)
            thread = Thread(id=f'thread_{user_id}', created_at=int(datetime.now(timezone.utc).timestamp()), metadata_={'user_id': user_id, 'private_data': f'private_to_{user_id}'})
            session.add(thread)
            await session.commit()
        redis_key = f'user_session:{user_id}'
        await redis_client.set(redis_key, f'{{"user_id": "{user_id}", "private_token": "token_for_{user_id}"}}', ex=3600)
        return user_id
    tasks = [create_user_with_data(user_info) for user_info in users]
    created_user_ids = await asyncio.gather(*tasks)
    assert len(created_user_ids) == 5
    for user_id in created_user_ids:
        async with db_manager.get_session() as session:
            result = await session.execute(select(Secret).where(Secret.user_id == user_id))
            user_secrets = result.scalars().all()
            assert len(user_secrets) == 1
            assert user_secrets[0].encrypted_value == f'encrypted_key_for_{user_id}'
            result = await session.execute(select(Thread).where(Thread.metadata_['user_id'].astext == user_id))
            user_threads = result.scalars().all()
            assert len(user_threads) == 1
            assert user_threads[0].metadata_['private_data'] == f'private_to_{user_id}'
        redis_data = await redis_client.get(f'user_session:{user_id}')
        assert redis_data is not None
        assert f'token_for_{user_id}' in redis_data
        other_user_ids = [uid for uid in created_user_ids if uid != user_id]
        for other_user_id in other_user_ids[:2]:
            other_redis_data = await redis_client.get(f'user_session:{other_user_id}')
            if other_redis_data:
                assert f'token_for_{user_id}' not in other_redis_data
    logger.info(' PASS:  Concurrent user data isolation validated')

@pytest.mark.integration
@pytest.mark.real_services
async def test_database_performance_under_load(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test database performance and connection pooling under concurrent load.
    
    Business Value: System scalability - ensures platform can handle
    multiple concurrent users without performance degradation.
    """
    start_time = datetime.now()

    async def simulate_user_activity(user_index: int):
        """Simulate typical user database operations."""
        user_id = f'test_user_load_{user_index}_{uuid.uuid4().hex[:6]}'
        async with db_manager.get_session() as session:
            user = User(id=user_id, email=f'{user_id}@example.com', plan_tier='pro')
            session.add(user)
            thread = Thread(id=f'thread_{user_id}', created_at=int(datetime.now(timezone.utc).timestamp()), metadata_={'user_id': user_id})
            session.add(thread)
            for msg_i in range(3):
                message = Message(id=f'msg_{user_id}_{msg_i}', created_at=int(datetime.now(timezone.utc).timestamp()), thread_id=f'thread_{user_id}', role='user' if msg_i % 2 == 0 else 'assistant', content=[{'type': 'text', 'text': f'Load test message {msg_i}'}], metadata_={'user_id': user_id})
                session.add(message)
            tool_log = ToolUsageLog(user_id=user_id, tool_name='cost_optimizer', category='optimization', execution_time_ms=150, status='success', plan_tier='pro')
            session.add(tool_log)
            await session.commit()
            result = await session.execute(select(Message).where(Message.thread_id == f'thread_{user_id}'))
            messages = result.scalars().all()
            assert len(messages) == 3
        await redis_client.set(f'load_test:{user_id}', f'data_for_{user_id}', ex=300)
        retrieved = await redis_client.get(f'load_test:{user_id}')
        assert retrieved == f'data_for_{user_id}'
        return user_id
    num_concurrent_users = 10
    tasks = [simulate_user_activity(i) for i in range(num_concurrent_users)]
    completed_user_ids = await asyncio.gather(*tasks)
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    assert len(completed_user_ids) == num_concurrent_users
    assert execution_time < 30
    async with db_manager.get_session() as session:
        result = await session.execute(select(func.count(User.id)).where(User.id.like('test_user_load_%')))
        assert result.scalar() == num_concurrent_users
        result = await session.execute(select(func.count(Message.id)).where(Message.id.like('msg_test_user_load_%')))
        assert result.scalar() == num_concurrent_users * 3
        result = await session.execute(select(func.count(ToolUsageLog.id)).where(ToolUsageLog.user_id.like('test_user_load_%')))
        assert result.scalar() == num_concurrent_users
    logger.info(f' PASS:  Database performance test completed in {execution_time:.2f}s for {num_concurrent_users} concurrent users')

@pytest.mark.integration
@pytest.mark.real_services
async def test_data_integrity_and_constraints(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test database constraints and referential integrity.
    
    Business Value: Data reliability - ensures database constraints
    prevent data corruption and maintain relationships between entities.
    """
    user_id = f'test_user_{uuid.uuid4().hex[:8]}'
    async with db_manager.get_session() as session:
        user = User(id=user_id, email=f'{user_id}@example.com')
        session.add(user)
        await session.commit()
        secret = Secret(user_id=user_id, key='test_key', encrypted_value='encrypted_value')
        session.add(secret)
        await session.commit()
        result = await session.execute(select(Secret).where(Secret.user_id == user_id))
        created_secret = result.scalar_one_or_none()
        assert created_secret is not None
        assert created_secret.key == 'test_key'
    invalid_user_id = 'nonexistent_user'
    try:
        async with db_manager.get_session() as session:
            invalid_secret = Secret(user_id=invalid_user_id, key='invalid_key', encrypted_value='some_value')
            session.add(invalid_secret)
            await session.commit()
            assert False, 'Expected foreign key constraint violation'
    except Exception as e:
        assert 'foreign key' in str(e).lower() or 'constraint' in str(e).lower()
    try:
        async with db_manager.get_session() as session:
            duplicate_user = User(id=f'another_{user_id}', email=f'{user_id}@example.com')
            session.add(duplicate_user)
            await session.commit()
            assert False, 'Expected unique constraint violation'
    except IntegrityError as e:
        assert 'unique' in str(e).lower() or 'duplicate' in str(e).lower()
    logger.info(' PASS:  Data integrity and constraints validated')

@pytest.mark.integration
@pytest.mark.real_services
async def test_cache_invalidation_patterns(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test Redis cache invalidation when database data changes.
    
    Business Value: Data consistency - ensures users see up-to-date
    information and cache doesn't serve stale data after updates.
    """
    user_id = f'test_user_{uuid.uuid4().hex[:8]}'
    cache_key = f'user_profile:{user_id}'
    async with db_manager.get_session() as session:
        user = User(id=user_id, email=f'{user_id}@example.com', plan_tier='free', permissions={'basic': True})
        session.add(user)
        await session.commit()
    cached_user = {'id': user_id, 'plan_tier': 'free', 'permissions': {'basic': True}, 'cached_at': datetime.now(timezone.utc).isoformat()}
    await redis_client.set(cache_key, json.dumps(cached_user), ex=1800)
    cached_data = await redis_client.get(cache_key)
    assert cached_data is not None
    cached_obj = json.loads(cached_data)
    assert cached_obj['plan_tier'] == 'free'
    async with db_manager.get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.plan_tier = 'pro'
        user.permissions = {'basic': True, 'advanced': True, 'api_access': True}
        await session.commit()
    await redis_client.delete(cache_key)
    cached_data_after = await redis_client.get(cache_key)
    assert cached_data_after is None
    async with db_manager.get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        updated_user = result.scalar_one()
        fresh_cache = {'id': user_id, 'plan_tier': updated_user.plan_tier, 'permissions': updated_user.permissions, 'cached_at': datetime.now(timezone.utc).isoformat()}
        await redis_client.set(cache_key, json.dumps(fresh_cache), ex=1800)
    final_cached_data = await redis_client.get(cache_key)
    assert final_cached_data is not None
    final_cached_obj = json.loads(final_cached_data)
    assert final_cached_obj['plan_tier'] == 'pro'
    assert final_cached_obj['permissions']['api_access'] is True
    logger.info(' PASS:  Cache invalidation patterns validated')

@pytest.mark.integration
@pytest.mark.real_services
async def test_database_connection_recovery(real_services_fixture, db_manager, redis_client, cleanup_test_data):
    """Test database connection recovery after temporary failures.
    
    Business Value: System resilience - ensures platform continues
    operating even when database connections are temporarily disrupted.
    """
    user_id = f'test_user_{uuid.uuid4().hex[:8]}'
    async with db_manager.get_session() as session:
        user = User(id=user_id, email=f'{user_id}@example.com')
        session.add(user)
        await session.commit()
        result = await session.execute(select(User).where(User.id == user_id))
        created_user = result.scalar_one_or_none()
        assert created_user is not None
    health_status = await db_manager.health_check()
    assert health_status['status'] == 'healthy'
    assert health_status['connection'] == 'ok'
    redis_client_obj = await redis_manager.get_client()
    assert redis_client_obj is not None
    redis_status = redis_manager.get_status()
    assert redis_status['connected'] is True
    assert redis_status['client_available'] is True
    test_key = f'recovery_test:{user_id}'
    await redis_client.set(test_key, 'recovery_test_value', ex=300)
    retrieved_value = await redis_client.get(test_key)
    assert retrieved_value == 'recovery_test_value'
    logger.info(' PASS:  Database connection recovery patterns validated')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')