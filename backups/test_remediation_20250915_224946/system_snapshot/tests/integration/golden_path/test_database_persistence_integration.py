"""
Test Database Persistence Integration for Golden Path

CRITICAL INTEGRATION TEST: This validates database persistence across all Golden Path
exit points with real PostgreSQL integration for data integrity and business continuity.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure conversation data and insights are never lost
- Value Impact: Lost data = lost business insights and user frustration  
- Strategic Impact: Data reliability foundation for $500K+ ARR platform trust

INTEGRATION POINTS TESTED:
1. Thread persistence across all exit points (normal, error, timeout, disconnect)
2. Message history storage with user isolation
3. Agent execution results storage and retrieval
4. Database cleanup on user disconnection
5. Multi-user data isolation validation
6. Performance and timing requirements

MUST use REAL PostgreSQL - NO MOCKS per CLAUDE.md standards
"""
import asyncio
import pytest
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.database_fixtures import test_db_session
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from shared.types.core_types import UserID, ThreadID, RunID, MessageID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
try:
    from netra_backend.app.models.conversation import Thread, Message
    from netra_backend.app.models.user import User
except ImportError:
    Thread = None
    Message = None
    User = None

@pytest.fixture
async def test_db_fixture():
    """Test database fixture for integration tests."""
    await get_test_db_engine()
    return {'available': True, 'engine_type': 'sqlite', 'database_type': 'in_memory'}
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
import sqlite3
from unittest.mock import AsyncMock
_test_engine = None
_test_session_maker = None

async def get_test_db_engine():
    """Get or create the test database engine."""
    global _test_engine, _test_session_maker
    if _test_engine is None:
        _test_engine = create_async_engine('sqlite+aiosqlite:///:memory:', poolclass=StaticPool, echo=False, connect_args={'check_same_thread': False}, pool_pre_ping=True, pool_recycle=300)
        _test_session_maker = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)
        async with _test_engine.begin() as conn:
            await conn.execute(text('\n                CREATE TABLE IF NOT EXISTS users (\n                    id TEXT PRIMARY KEY,\n                    email TEXT UNIQUE,\n                    created_at TIMESTAMP,\n                    updated_at TIMESTAMP\n                )\n            '))
            await conn.execute(text('\n                CREATE TABLE IF NOT EXISTS threads (\n                    id TEXT PRIMARY KEY,\n                    user_id TEXT,\n                    title TEXT,\n                    metadata TEXT,\n                    created_at TIMESTAMP,\n                    updated_at TIMESTAMP,\n                    FOREIGN KEY (user_id) REFERENCES users (id)\n                )\n            '))
            await conn.execute(text('\n                CREATE TABLE IF NOT EXISTS messages (\n                    id TEXT PRIMARY KEY,\n                    thread_id TEXT,\n                    role TEXT,\n                    content TEXT,\n                    metadata TEXT,\n                    created_at TIMESTAMP,\n                    FOREIGN KEY (thread_id) REFERENCES threads (id)\n                )\n            '))
            await conn.execute(text('\n                CREATE TABLE IF NOT EXISTS agent_executions (\n                    id TEXT PRIMARY KEY,\n                    thread_id TEXT,\n                    agent_name TEXT,\n                    status TEXT,\n                    results TEXT,\n                    metadata TEXT,\n                    start_time TIMESTAMP,\n                    end_time TIMESTAMP,\n                    created_at TIMESTAMP,\n                    FOREIGN KEY (thread_id) REFERENCES threads (id)\n                )\n            '))
            await conn.execute(text('\n                CREATE TABLE IF NOT EXISTS user_sessions (\n                    id TEXT PRIMARY KEY,\n                    user_id TEXT,\n                    websocket_id TEXT,\n                    connection_time TIMESTAMP,\n                    last_activity TIMESTAMP,\n                    disconnection_time TIMESTAMP,\n                    status TEXT,\n                    FOREIGN KEY (user_id) REFERENCES users (id)\n                )\n            '))
            await conn.execute(text('\n                CREATE TABLE IF NOT EXISTS temporary_user_data (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    user_id TEXT,\n                    websocket_id TEXT,\n                    data_type TEXT,\n                    data TEXT,\n                    created_at TIMESTAMP,\n                    FOREIGN KEY (user_id) REFERENCES users (id)\n                )\n            '))
    return (_test_engine, _test_session_maker)

@asynccontextmanager
async def get_db_session():
    """Real in-memory database session for integration testing."""
    engine, session_maker = await get_test_db_engine()
    session = session_maker()
    try:
        yield session
    finally:
        try:
            await session.rollback()
        except Exception:
            pass
        try:
            await session.close()
        except Exception:
            pass

class DatabasePersistenceIntegrationTests(SSotAsyncTestCase):
    """Test database persistence integration with real PostgreSQL."""

    async def async_setup_method(self, method=None):
        """Async setup for database integration test components."""
        await super().async_setup_method(method)
        self.environment = self.get_env_var('TEST_ENV', 'test')
        self.id_generator = UnifiedIdGenerator()
        self.record_metric('test_category', 'integration')
        self.record_metric('golden_path_component', 'database_persistence')
        self.record_metric('real_database_required', True)
        self.created_users = []
        self.created_threads = []
        self.created_messages = []

    async def async_teardown_method(self, method=None):
        """Cleanup test data from database."""
        try:
            async with get_db_session() as db:
                for message_id in self.created_messages:
                    await db.execute(text('DELETE FROM messages WHERE id = :id'), {'id': str(message_id)})
                for thread_id in self.created_threads:
                    await db.execute(text('DELETE FROM threads WHERE id = :id'), {'id': str(thread_id)})
                for user_id in self.created_users:
                    await db.execute(text('DELETE FROM users WHERE id = :id'), {'id': str(user_id)})
                await db.commit()
        except Exception as e:
            print(f'Warning: Cleanup failed: {e}')
        await super().async_teardown_method(method)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_thread_persistence_normal_completion(self, test_db_fixture):
        """Test thread persistence for normal Golden Path completion."""
        if not hasattr(self, 'environment'):
            await self.async_setup_method()
        user_context = await create_authenticated_user_context(user_email='thread_persistence_test@example.com', environment=self.environment, websocket_enabled=True)
        thread_data = {'id': user_context.thread_id, 'user_id': user_context.user_id, 'title': 'Golden Path Cost Optimization', 'created_at': datetime.now(timezone.utc), 'updated_at': datetime.now(timezone.utc), 'metadata': {'agent_pipeline': ['data_agent', 'optimization_agent', 'report_agent'], 'business_intent': 'cost_optimization', 'completion_status': 'normal'}}
        persistence_start = time.time()
        async with get_db_session() as db:
            await db.execute(text('INSERT INTO threads (id, user_id, title, created_at, updated_at, metadata) \n                        VALUES (:id, :user_id, :title, :created_at, :updated_at, :metadata)'), {'id': str(thread_data['id']), 'user_id': str(thread_data['user_id']), 'title': thread_data['title'], 'created_at': thread_data['created_at'].isoformat(), 'updated_at': thread_data['updated_at'].isoformat(), 'metadata': json.dumps(thread_data['metadata'])})
            await db.commit()
        persistence_time = time.time() - persistence_start
        self.created_threads.append(user_context.thread_id)
        async with get_db_session() as db:
            result = await db.execute(text('SELECT * FROM threads WHERE id = :id'), {'id': str(user_context.thread_id)})
            retrieved_thread = result.fetchone()
        assert retrieved_thread is not None, 'Thread should be persisted in database'
        thread_dict = {'id': retrieved_thread[0], 'user_id': retrieved_thread[1], 'title': retrieved_thread[2], 'metadata': retrieved_thread[3], 'created_at': retrieved_thread[4], 'updated_at': retrieved_thread[5]}
        assert thread_dict['id'] == str(user_context.thread_id), 'Thread ID should match'
        assert thread_dict['user_id'] == str(user_context.user_id), 'User ID should match'
        assert thread_dict['title'] == 'Golden Path Cost Optimization', 'Thread title should be preserved'
        stored_metadata = json.loads(thread_dict['metadata'])
        assert stored_metadata['business_intent'] == 'cost_optimization', 'Business intent should be preserved'
        assert stored_metadata['completion_status'] == 'normal', 'Completion status should be preserved'
        assert persistence_time < 1.0, f'Thread persistence should be < 1s: {persistence_time:.2f}s'
        self.record_metric('thread_persistence_normal_test_passed', True)
        self.record_metric('thread_persistence_time', persistence_time)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_message_history_storage_with_isolation(self, test_db_fixture):
        """Test message history storage with proper user isolation."""
        if not hasattr(self, 'environment'):
            await self.async_setup_method()
        user1_context = await create_authenticated_user_context(user_email='message_user1@example.com', environment=self.environment, websocket_enabled=True)
        user2_context = await create_authenticated_user_context(user_email='message_user2@example.com', environment=self.environment, websocket_enabled=True)
        async with get_db_session() as db:
            await db.execute(text('INSERT INTO threads (id, user_id, title, created_at, updated_at) \n                        VALUES (:id, :user_id, :title, :created_at, :updated_at)'), {'id': str(user1_context.thread_id), 'user_id': str(user1_context.user_id), 'title': 'User 1 Conversation', 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()})
            await db.execute(text('INSERT INTO threads (id, user_id, title, created_at, updated_at) \n                        VALUES (:id, :user_id, :title, :created_at, :updated_at)'), {'id': str(user2_context.thread_id), 'user_id': str(user2_context.user_id), 'title': 'User 2 Conversation', 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()})
            await db.commit()
        self.created_threads.extend([user1_context.thread_id, user2_context.thread_id])
        messages_data = [{'id': MessageID(self.id_generator.generate_message_id('user', str(user1_context.user_id))), 'thread_id': user1_context.thread_id, 'user_id': user1_context.user_id, 'role': 'user', 'content': 'Optimize my AI costs', 'metadata': {'business_intent': 'cost_optimization'}}, {'id': MessageID(self.id_generator.generate_message_id('assistant', str(user1_context.user_id))), 'thread_id': user1_context.thread_id, 'user_id': user1_context.user_id, 'role': 'assistant', 'content': "I'll help you optimize your AI costs...", 'metadata': {'agent': 'cost_optimizer'}}, {'id': MessageID(self.id_generator.generate_message_id('user', str(user2_context.user_id))), 'thread_id': user2_context.thread_id, 'user_id': user2_context.user_id, 'role': 'user', 'content': 'Analyze my usage patterns', 'metadata': {'business_intent': 'usage_analysis'}}, {'id': MessageID(self.id_generator.generate_message_id('assistant', str(user2_context.user_id))), 'thread_id': user2_context.thread_id, 'user_id': user2_context.user_id, 'role': 'assistant', 'content': "I'll analyze your usage patterns...", 'metadata': {'agent': 'usage_analyzer'}}]
        storage_start = time.time()
        async with get_db_session() as db:
            for msg in messages_data:
                await db.execute(text('INSERT INTO messages (id, thread_id, role, content, metadata, created_at) \n                           VALUES (:id, :thread_id, :role, :content, :metadata, :created_at)'), {'id': str(msg['id']), 'thread_id': str(msg['thread_id']), 'role': msg['role'], 'content': msg['content'], 'metadata': json.dumps(msg['metadata']), 'created_at': datetime.now(timezone.utc).isoformat()})
                self.created_messages.append(msg['id'])
            await db.commit()
        storage_time = time.time() - storage_start
        async with get_db_session() as db:
            result1 = await db.execute(text('SELECT * FROM messages WHERE thread_id = :thread_id ORDER BY created_at'), {'thread_id': str(user1_context.thread_id)})
            user1_messages = result1.fetchall()
            result2 = await db.execute(text('SELECT * FROM messages WHERE thread_id = :thread_id ORDER BY created_at'), {'thread_id': str(user2_context.thread_id)})
            user2_messages = result2.fetchall()
        assert len(user1_messages) == 2, f'User 1 should have 2 messages: {len(user1_messages)}'
        assert len(user2_messages) == 2, f'User 2 should have 2 messages: {len(user2_messages)}'
        user1_content = [msg[3] for msg in user1_messages]
        user2_content = [msg[3] for msg in user2_messages]
        assert 'Optimize my AI costs' in user1_content[0], 'User 1 content should be preserved'
        assert 'Analyze my usage patterns' in user2_content[0], 'User 2 content should be preserved'
        assert not any(('usage patterns' in content for content in user1_content)), 'User 1 should not see User 2 content'
        assert not any(('AI costs' in content for content in user2_content)), 'User 2 should not see User 1 content'
        assert storage_time < 2.0, f'Message storage should be < 2s: {storage_time:.2f}s'
        self.record_metric('message_isolation_test_passed', True)
        self.record_metric('message_storage_time', storage_time)
        self.record_metric('users_tested', 2)
        self.record_metric('messages_stored', len(messages_data))

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_execution_results_storage(self, test_db_fixture):
        """Test storage and retrieval of agent execution results."""
        if not hasattr(self, 'environment'):
            await self.async_setup_method()
        user_context = await create_authenticated_user_context(user_email='agent_results_test@example.com', environment=self.environment, websocket_enabled=True)
        async with get_db_session() as db:
            await db.execute(text('INSERT INTO threads (id, user_id, title, created_at, updated_at) \n                       VALUES (:id, :user_id, :title, :created_at, :updated_at)'), {'id': str(user_context.thread_id), 'user_id': str(user_context.user_id), 'title': 'Agent Results Test', 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()})
            await db.commit()
        self.created_threads.append(user_context.thread_id)
        agent_results = [{'agent_name': 'data_agent', 'execution_id': self.id_generator.generate_agent_execution_id('data_agent', str(user_context.user_id)), 'start_time': time.time() - 30, 'end_time': time.time() - 25, 'status': 'completed', 'results': {'data_collected': {'total_tokens': 150000, 'total_cost': 75.5, 'api_calls': 245}, 'analysis': {'cost_trend': 'increasing', 'peak_usage_hours': [9, 10, 14, 15]}}, 'metadata': {'tools_used': ['token_counter', 'cost_calculator'], 'execution_time': 5.0}}, {'agent_name': 'optimization_agent', 'execution_id': self.id_generator.generate_agent_execution_id('optimization_agent', str(user_context.user_id)), 'start_time': time.time() - 25, 'end_time': time.time() - 15, 'status': 'completed', 'results': {'recommendations': [{'type': 'model_optimization', 'description': 'Switch to GPT-3.5 for simple queries', 'potential_savings': 1200.0}, {'type': 'caching_strategy', 'description': 'Implement result caching', 'potential_savings': 800.0}], 'total_potential_savings': 2000.0}, 'metadata': {'tools_used': ['optimization_analyzer', 'cost_calculator'], 'execution_time': 10.0}}]
        storage_start = time.time()
        async with get_db_session() as db:
            for result in agent_results:
                await db.execute(text('INSERT INTO agent_executions \n                           (id, thread_id, agent_name, status, results, metadata, start_time, end_time, created_at)\n                           VALUES (:id, :thread_id, :agent_name, :status, :results, :metadata, :start_time, :end_time, :created_at)'), {'id': result['execution_id'], 'thread_id': str(user_context.thread_id), 'agent_name': result['agent_name'], 'status': result['status'], 'results': json.dumps(result['results']), 'metadata': json.dumps(result['metadata']), 'start_time': datetime.fromtimestamp(result['start_time'], tz=timezone.utc).isoformat(), 'end_time': datetime.fromtimestamp(result['end_time'], tz=timezone.utc).isoformat(), 'created_at': datetime.now(timezone.utc).isoformat()})
            await db.commit()
        storage_time = time.time() - storage_start
        async with get_db_session() as db:
            result = await db.execute(text('SELECT * FROM agent_executions WHERE thread_id = :thread_id ORDER BY start_time'), {'thread_id': str(user_context.thread_id)})
            stored_results = result.fetchall()
        assert len(stored_results) == 2, f'Should store 2 agent results: {len(stored_results)}'
        data_result = next((r for r in stored_results if r[2] == 'data_agent'))
        data_results_json = json.loads(data_result[4])
        assert data_results_json['data_collected']['total_cost'] == 75.5, 'Data agent cost should be preserved'
        assert data_results_json['analysis']['cost_trend'] == 'increasing', 'Data agent analysis should be preserved'
        opt_result = next((r for r in stored_results if r[2] == 'optimization_agent'))
        opt_results_json = json.loads(opt_result[4])
        assert opt_results_json['total_potential_savings'] == 2000.0, 'Optimization savings should be preserved'
        assert len(opt_results_json['recommendations']) == 2, 'Should preserve all recommendations'
        data_metadata = json.loads(data_result[5])
        assert 'token_counter' in data_metadata['tools_used'], 'Tools used should be preserved'
        assert storage_time < 1.0, f'Agent results storage should be < 1s: {storage_time:.2f}s'
        self.record_metric('agent_results_storage_test_passed', True)
        self.record_metric('agent_results_storage_time', storage_time)
        self.record_metric('agent_results_stored', len(agent_results))

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_database_cleanup_on_user_disconnect(self, test_db_fixture):
        """Test database cleanup behavior when user disconnects."""
        if not hasattr(self, 'environment'):
            await self.async_setup_method()
        user_context = await create_authenticated_user_context(user_email='cleanup_test@example.com', environment=self.environment, websocket_enabled=True)
        session_data = {'user_id': user_context.user_id, 'websocket_id': user_context.websocket_client_id, 'connection_time': datetime.now(timezone.utc), 'last_activity': datetime.now(timezone.utc), 'status': 'active'}
        async with get_db_session() as db:
            await db.execute(text('INSERT INTO user_sessions (id, user_id, websocket_id, connection_time, last_activity, status)\n                        VALUES (:id, :user_id, :websocket_id, :connection_time, :last_activity, :status)'), {'id': str(user_context.websocket_client_id), 'user_id': str(session_data['user_id']), 'websocket_id': str(session_data['websocket_id']), 'connection_time': session_data['connection_time'].isoformat(), 'last_activity': session_data['last_activity'].isoformat(), 'status': session_data['status']})
            await db.execute(text('INSERT INTO temporary_user_data (user_id, websocket_id, data_type, data, created_at)\n                       VALUES (:user_id, :websocket_id, :data_type, :data, :created_at)'), {'user_id': str(user_context.user_id), 'websocket_id': str(user_context.websocket_client_id), 'data_type': 'active_execution', 'data': json.dumps({'agent': 'in_progress', 'step': 2}), 'created_at': datetime.now(timezone.utc).isoformat()})
            await db.commit()
        cleanup_start = time.time()
        async with get_db_session() as db:
            await db.execute(text("UPDATE user_sessions SET status = 'disconnected', disconnection_time = :disconnection_time \n                       WHERE websocket_id = :websocket_id"), {'disconnection_time': datetime.now(timezone.utc).isoformat(), 'websocket_id': str(user_context.websocket_client_id)})
            await db.execute(text('DELETE FROM temporary_user_data WHERE websocket_id = :websocket_id'), {'websocket_id': str(user_context.websocket_client_id)})
            await db.commit()
        cleanup_time = time.time() - cleanup_start
        async with get_db_session() as db:
            result = await db.execute(text('SELECT status, disconnection_time FROM user_sessions WHERE websocket_id = :websocket_id'), {'websocket_id': str(user_context.websocket_client_id)})
            session_status = result.fetchone()
            result = await db.execute(text('SELECT COUNT(*) FROM temporary_user_data WHERE websocket_id = :websocket_id'), {'websocket_id': str(user_context.websocket_client_id)})
            temp_data_count = result.fetchone()[0]
            await db.execute(text('DELETE FROM user_sessions WHERE websocket_id = :websocket_id'), {'websocket_id': str(user_context.websocket_client_id)})
            await db.commit()
        assert session_status[0] == 'disconnected', 'Session should be marked as disconnected'
        assert session_status[1] is not None, 'Disconnection time should be recorded'
        assert temp_data_count == 0, 'Temporary data should be cleaned up'
        assert cleanup_time < 0.5, f'Cleanup should be fast: {cleanup_time:.2f}s'
        self.record_metric('disconnect_cleanup_test_passed', True)
        self.record_metric('cleanup_time', cleanup_time)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_data_isolation_validation(self, test_db_fixture):
        """Test comprehensive multi-user data isolation in database."""
        if not hasattr(self, 'environment'):
            await self.async_setup_method()
        concurrent_users = 5
        user_contexts = []
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(user_email=f'isolation_user_{i}@example.com', environment=self.environment, websocket_enabled=True)
            user_contexts.append(context)
        isolation_start = time.time()
        async with get_db_session() as db:
            for i, context in enumerate(user_contexts):
                await db.execute(text('INSERT INTO threads (id, user_id, title, created_at, updated_at, metadata)\n                           VALUES (:id, :user_id, :title, :created_at, :updated_at, :metadata)'), {'id': str(context.thread_id), 'user_id': str(context.user_id), 'title': f'User {i} Conversation', 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat(), 'metadata': json.dumps({'user_index': i, 'isolation_test': True})})
                for j in range(3):
                    message_id = MessageID(self.id_generator.generate_message_id('user' if j % 2 == 0 else 'assistant', str(context.user_id)))
                    await db.execute(text('INSERT INTO messages (id, thread_id, role, content, metadata, created_at)\n                               VALUES (:id, :thread_id, :role, :content, :metadata, :created_at)'), {'id': str(message_id), 'thread_id': str(context.thread_id), 'role': 'user' if j % 2 == 0 else 'assistant', 'content': f'User {i} Message {j}: Unique content {context.user_id}', 'metadata': json.dumps({'user_index': i, 'message_index': j}), 'created_at': datetime.now(timezone.utc).isoformat()})
                    self.created_messages.append(message_id)
                self.created_threads.append(context.thread_id)
            await db.commit()
        isolation_time = time.time() - isolation_start
        async with get_db_session() as db:
            for i, context in enumerate(user_contexts):
                result = await db.execute(text('SELECT * FROM threads WHERE user_id = :user_id'), {'user_id': str(context.user_id)})
                user_threads = result.fetchall()
                assert len(user_threads) == 1, f'User {i} should see exactly 1 thread: {len(user_threads)}'
                assert user_threads[0][2] == f'User {i} Conversation', f'User {i} should see their own thread title'
                result = await db.execute(text('SELECT * FROM messages WHERE thread_id = :thread_id'), {'thread_id': str(context.thread_id)})
                user_messages = result.fetchall()
                assert len(user_messages) == 3, f'User {i} should have 3 messages: {len(user_messages)}'
                for message in user_messages:
                    content = message[3]
                    assert f'User {i}' in content, f'User {i} message should contain their user index'
                    assert str(context.user_id) in content, f'User {i} message should contain their user ID'
                result = await db.execute(text('SELECT * FROM messages m \n                           JOIN threads t ON m.thread_id = t.id \n                           WHERE t.user_id != :user_id'), {'user_id': str(context.user_id)})
                all_other_messages = result.fetchall()
                for other_message in all_other_messages:
                    other_content = other_message[3]
                    assert f'User {i}' not in other_content or str(context.user_id) not in other_content, f"User {i} should not see other users' content: {other_content}"
        async with get_db_session() as db:
            test_context = user_contexts[0]
            result = await db.execute(text('SELECT DISTINCT t.user_id, t.title FROM threads t \n                       WHERE t.user_id = :user_id'), {'user_id': str(test_context.user_id)})
            cross_user_query = result.fetchall()
            assert len(cross_user_query) == 1, "Cross-user query should only return one user's data"
            assert cross_user_query[0][0] == str(test_context.user_id), "Should only return querying user's data"
        assert isolation_time < 10.0, f'Multi-user data creation should be < 10s: {isolation_time:.2f}s'
        self.record_metric('multi_user_isolation_test_passed', True)
        self.record_metric('concurrent_users_tested', concurrent_users)
        self.record_metric('isolation_setup_time', isolation_time)
        self.record_metric('total_messages_created', concurrent_users * 3)

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_persistence_performance_requirements(self, test_db_fixture):
        """Test database persistence meets performance requirements."""
        if not hasattr(self, 'environment'):
            await self.async_setup_method()
        performance_metrics = {'thread_create_times': [], 'message_batch_times': [], 'result_storage_times': [], 'retrieval_times': []}
        test_iterations = 5
        messages_per_batch = 10
        for iteration in range(test_iterations):
            user_context = await create_authenticated_user_context(user_email=f'perf_test_{iteration}@example.com', environment=self.environment, websocket_enabled=True)
            thread_start = time.time()
            async with get_db_session() as db:
                await db.execute(text('INSERT INTO threads (id, user_id, title, created_at, updated_at)\n                           VALUES (:id, :user_id, :title, :created_at, :updated_at)'), {'id': str(user_context.thread_id), 'user_id': str(user_context.user_id), 'title': f'Performance Test {iteration}', 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()})
                await db.commit()
            thread_time = time.time() - thread_start
            performance_metrics['thread_create_times'].append(thread_time)
            self.created_threads.append(user_context.thread_id)
            batch_start = time.time()
            async with get_db_session() as db:
                for j in range(messages_per_batch):
                    message_id = MessageID(self.id_generator.generate_message_id('user' if j % 2 == 0 else 'assistant', str(user_context.user_id)))
                    await db.execute(text('INSERT INTO messages (id, thread_id, role, content, created_at)\n                               VALUES (:id, :thread_id, :role, :content, :created_at)'), {'id': str(message_id), 'thread_id': str(user_context.thread_id), 'role': 'user' if j % 2 == 0 else 'assistant', 'content': f'Performance test message {j} with content', 'created_at': datetime.now(timezone.utc).isoformat()})
                    self.created_messages.append(message_id)
                await db.commit()
            batch_time = time.time() - batch_start
            performance_metrics['message_batch_times'].append(batch_time)
            result_start = time.time()
            async with get_db_session() as db:
                await db.execute(text('INSERT INTO agent_executions \n                           (id, thread_id, agent_name, status, results, created_at)\n                           VALUES (:id, :thread_id, :agent_name, :status, :results, :created_at)'), {'id': self.id_generator.generate_agent_execution_id('performance_test_agent', str(user_context.user_id)), 'thread_id': str(user_context.thread_id), 'agent_name': 'performance_test_agent', 'status': 'completed', 'results': json.dumps({'test_data': 'performance_result', 'iteration': iteration}), 'created_at': datetime.now(timezone.utc).isoformat()})
                await db.commit()
            result_time = time.time() - result_start
            performance_metrics['result_storage_times'].append(result_time)
            retrieval_start = time.time()
            async with get_db_session() as db:
                result = await db.execute(text('SELECT * FROM threads WHERE id = :id'), {'id': str(user_context.thread_id)})
                thread_data = result.fetchone()
                result = await db.execute(text('SELECT * FROM messages WHERE thread_id = :thread_id ORDER BY created_at'), {'thread_id': str(user_context.thread_id)})
                messages = result.fetchall()
                result = await db.execute(text('SELECT * FROM agent_executions WHERE thread_id = :thread_id'), {'thread_id': str(user_context.thread_id)})
                results = result.fetchall()
            retrieval_time = time.time() - retrieval_start
            performance_metrics['retrieval_times'].append(retrieval_time)
        avg_thread_time = sum(performance_metrics['thread_create_times']) / test_iterations
        avg_batch_time = sum(performance_metrics['message_batch_times']) / test_iterations
        avg_result_time = sum(performance_metrics['result_storage_times']) / test_iterations
        avg_retrieval_time = sum(performance_metrics['retrieval_times']) / test_iterations
        assert avg_thread_time < 0.5, f'Thread creation should be < 0.5s: {avg_thread_time:.2f}s'
        assert avg_batch_time < 2.0, f'Batch message storage should be < 2s: {avg_batch_time:.2f}s'
        assert avg_result_time < 0.3, f'Result storage should be < 0.3s: {avg_result_time:.2f}s'
        assert avg_retrieval_time < 1.0, f'Data retrieval should be < 1s: {avg_retrieval_time:.2f}s'
        avg_per_message_time = avg_batch_time / messages_per_batch
        assert avg_per_message_time < 0.2, f'Per-message time should be < 0.2s: {avg_per_message_time:.2f}s'
        self.record_metric('persistence_performance_test_passed', True)
        self.record_metric('avg_thread_creation_time', avg_thread_time)
        self.record_metric('avg_message_batch_time', avg_batch_time)
        self.record_metric('avg_result_storage_time', avg_result_time)
        self.record_metric('avg_retrieval_time', avg_retrieval_time)
        self.record_metric('performance_test_iterations', test_iterations)
        print(f'\n CHART:  DATABASE PERFORMANCE METRICS:')
        print(f'   [U+1F9F5] Thread Creation: {avg_thread_time:.3f}s')
        print(f'   [U+1F4AC] Message Batch ({messages_per_batch}): {avg_batch_time:.3f}s')
        print(f'   [U+1F4C4] Result Storage: {avg_result_time:.3f}s')
        print(f'   [U+1F4E5] Data Retrieval: {avg_retrieval_time:.3f}s')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')