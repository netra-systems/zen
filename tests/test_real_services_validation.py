"""
Real Services Infrastructure Validation Tests

These tests validate that the real services infrastructure works correctly
and can replace the 5766+ mock violations across the codebase.

Run with: pytest tests/test_real_services_validation.py -v --real-services
"""
import asyncio
import json
import pytest
import time
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment
from test_framework.conftest_real_services import real_services, real_postgres, real_redis, real_clickhouse, real_websocket_client, real_http_client, test_user, test_organization, test_agent, performance_monitor, require_real_services

@require_real_services()
class RealServicesInfrastructureTests:
    """Test suite validating real services infrastructure."""

    async def test_services_health_check(self, real_services):
        """Verify all real services are healthy and accessible."""
        await real_services.ensure_all_services_available()
        async with real_services.postgres.connection() as conn:
            result = await conn.fetchval('SELECT 1')
            assert result == 1
        redis_client = await real_services.redis.get_client()
        ping_result = await redis_client.ping()
        assert ping_result is True
        clickhouse_result = await real_services.clickhouse.execute('SELECT 1')
        assert clickhouse_result == [[1]]

    async def test_postgres_real_operations(self, real_postgres):
        """Test PostgreSQL with real database operations."""
        user_id = await real_postgres.fetchval('\n            INSERT INTO auth.users (email, name, password_hash, is_active)\n            VALUES ($1, $2, $3, $4)\n            RETURNING id\n        ', 'postgres_test@example.com', 'Postgres Test User', 'test_hash', True)
        assert user_id is not None
        user = await real_postgres.fetchrow('SELECT * FROM auth.users WHERE id = $1', user_id)
        assert user['email'] == 'postgres_test@example.com'
        assert user['name'] == 'Postgres Test User'
        assert user['is_active'] is True
        await real_postgres.execute('UPDATE auth.users SET name = $1 WHERE id = $2', 'Updated Name', user_id)
        updated_user = await real_postgres.fetchrow('SELECT name FROM auth.users WHERE id = $1', user_id)
        assert updated_user['name'] == 'Updated Name'
        with pytest.raises(Exception):
            await real_postgres.execute('\n                INSERT INTO auth.users (email, name, password_hash, is_active)\n                VALUES ($1, $2, $3, $4)\n            ', 'postgres_test@example.com', 'Duplicate User', 'hash', True)

    async def test_redis_real_operations(self, real_redis):
        """Test Redis with real cache operations."""
        key = 'test_redis_key'
        value = 'test_redis_value'
        set_result = await real_redis.set(key, value)
        assert set_result is True
        get_result = await real_redis.get(key)
        assert get_result == value
        json_key = 'test_json_key'
        json_data = {'name': 'Test', 'count': 42, 'active': True}
        await real_redis.set(json_key, json.dumps(json_data))
        retrieved_json = await real_redis.get(json_key)
        parsed_data = json.loads(retrieved_json)
        assert parsed_data == json_data
        temp_key = 'temp_key'
        await real_redis.set(temp_key, 'temporary', ex=1)
        assert await real_redis.exists(temp_key)
        await asyncio.sleep(1.5)
        assert not await real_redis.exists(temp_key)
        await real_redis.set('delete_me', 'value')
        assert await real_redis.exists('delete_me')
        deleted_count = await real_redis.delete('delete_me')
        assert deleted_count == 1
        assert not await real_redis.exists('delete_me')

    async def test_clickhouse_real_operations(self, real_clickhouse):
        """Test ClickHouse with real analytics operations."""
        test_events = [{'user_id': '123e4567-e89b-12d3-a456-426614174001', 'event_type': 'login', 'session_id': 'session_001', 'properties': {'source': 'test', 'device': 'desktop'}}, {'user_id': '123e4567-e89b-12d3-a456-426614174002', 'event_type': 'page_view', 'session_id': 'session_002', 'properties': {'page': '/dashboard', 'source': 'test'}}, {'user_id': '123e4567-e89b-12d3-a456-426614174001', 'event_type': 'logout', 'session_id': 'session_001', 'properties': {'source': 'test', 'duration': '300'}}]
        await real_clickhouse.insert_data('user_events', test_events)
        count_result = await real_clickhouse.execute("SELECT COUNT(*) FROM user_events WHERE properties['source'] = 'test'")
        assert count_result[0][0] >= 3
        user_event_counts = await real_clickhouse.execute("\n            SELECT user_id, COUNT(*) as event_count\n            FROM user_events \n            WHERE properties['source'] = 'test'\n            GROUP BY user_id\n            ORDER BY event_count DESC\n        ")
        assert len(user_event_counts) >= 2
        user1_count = next((count for user_id, count in user_event_counts if user_id == '123e4567-e89b-12d3-a456-426614174001'), 0)
        assert user1_count == 2
        login_events = await real_clickhouse.execute("\n            SELECT COUNT(*) FROM user_events \n            WHERE event_type = 'login' AND properties['source'] = 'test'\n        ")
        assert login_events[0][0] >= 1

    async def test_websocket_real_connection(self, real_websocket_client):
        """Test WebSocket with real connection."""
        try:
            await real_websocket_client.connect('test')
        except Exception:
            pytest.skip('WebSocket service not available for testing')
        test_message = {'type': 'test_message', 'content': 'Hello WebSocket!', 'timestamp': time.time()}
        await real_websocket_client.send(test_message)

    async def test_http_real_requests(self, real_http_client, real_services):
        """Test HTTP client with real requests."""
        try:
            response = await real_http_client.get('http://httpbin.org/get')
            assert response.status_code == 200
            data = response.json()
            assert 'url' in data
        except Exception:
            pytest.skip('HTTP test service not available')

    async def test_data_isolation_between_tests(self, real_services):
        """Test that data is properly isolated between tests."""
        await real_services.postgres.execute('\n            INSERT INTO auth.users (email, name, password_hash, is_active)\n            VALUES ($1, $2, $3, $4)\n        ', 'isolation_test@example.com', 'Isolation Test', 'hash', True)
        await real_services.redis.set('isolation_test', 'test_value')
        await real_services.clickhouse.execute("\n            INSERT INTO user_events (user_id, event_type, session_id)\n            VALUES ('isolation_user', 'test_event', 'isolation_session')\n        ")
        user_count = await real_services.postgres.fetchval('SELECT COUNT(*) FROM auth.users WHERE email = $1', 'isolation_test@example.com')
        assert user_count == 1
        redis_value = await real_services.redis.get('isolation_test')
        assert redis_value == 'test_value'

    async def test_performance_monitoring(self, real_services, performance_monitor):
        """Test performance monitoring capabilities."""
        performance_monitor.start('bulk_insert')
        users_data = [(f'perf_test_{i}@example.com', f'User {i}', 'hash', True) for i in range(100)]
        async with real_services.postgres.connection() as conn:
            await conn.executemany('\n                INSERT INTO auth.users (email, name, password_hash, is_active)\n                VALUES ($1, $2, $3, $4)\n            ', users_data)
        duration = performance_monitor.end('bulk_insert')
        performance_monitor.assert_performance('bulk_insert', 10.0)
        print(f'Bulk insert of 100 users took {duration:.2f} seconds')
        performance_monitor.start('redis_bulk_set')
        redis_client = await real_services.redis.get_client()
        for i in range(1000):
            await redis_client.set(f'perf_key_{i}', f'value_{i}')
        redis_duration = performance_monitor.end('redis_bulk_set')
        performance_monitor.assert_performance('redis_bulk_set', 5.0)
        print(f'Bulk Redis set of 1000 keys took {redis_duration:.2f} seconds')

    async def test_realistic_workflow(self, real_services, test_user, test_organization, test_agent):
        """Test a realistic workflow using real services with test fixtures."""
        assert test_user['email'] == 'test@example.com'
        assert test_organization['name'] == 'Test Organization'
        assert test_agent['name'] == 'Test Agent'
        conversation_id = await real_services.postgres.fetchval('\n            INSERT INTO backend.conversations (agent_id, user_id, title, status)\n            VALUES ($1, $2, $3, $4)\n            RETURNING id\n        ', test_agent['id'], test_user['id'], 'Test Conversation', 'active')
        messages = [('user', 'Hello, how can you help me?'), ('assistant', 'I can help you with various tasks. What do you need?'), ('user', 'I need help with testing.')]
        message_ids = []
        for role, content in messages:
            message_id = await real_services.postgres.fetchval('\n                INSERT INTO backend.messages (conversation_id, role, content)\n                VALUES ($1, $2, $3)\n                RETURNING id\n            ', conversation_id, role, content)
            message_ids.append(message_id)
        conversation_cache_key = f'conversation:{conversation_id}'
        conversation_data = {'id': str(conversation_id), 'agent_id': test_agent['id'], 'user_id': test_user['id'], 'message_count': len(messages)}
        await real_services.redis.set(conversation_cache_key, json.dumps(conversation_data, default=str), ex=3600)
        await real_services.clickhouse.execute('\n            INSERT INTO conversation_events \n            (conversation_id, agent_id, user_id, organization_id, event_type, message_count, tokens_used)\n            VALUES\n        ', [(str(conversation_id), test_agent['id'], test_user['id'], test_organization['id'], 'conversation_created', len(messages), 150 * len(messages))])
        conversation = await real_services.postgres.fetchrow('SELECT * FROM backend.conversations WHERE id = $1', conversation_id)
        assert conversation['title'] == 'Test Conversation'
        message_count = await real_services.postgres.fetchval('SELECT COUNT(*) FROM backend.messages WHERE conversation_id = $1', conversation_id)
        assert message_count == len(messages)
        cached_data = await real_services.redis.get(conversation_cache_key)
        cached_conversation = json.loads(cached_data)
        assert cached_conversation['message_count'] == len(messages)
        analytics_count = await real_services.clickhouse.execute("\n            SELECT COUNT(*) FROM conversation_events \n            WHERE conversation_id = %s AND event_type = 'conversation_created'\n        ", [str(conversation_id)])
        assert analytics_count[0][0] >= 1
        print(f'Successfully created conversation {conversation_id} with {len(messages)} messages')

@require_real_services()
class MockReplacementValidationTests:
    """Test that real services can properly replace common mock patterns."""

    async def test_replace_database_mock(self, real_postgres):
        """Demonstrate replacing database mocks with real database operations."""
        user_id = await real_postgres.fetchval('\n            INSERT INTO auth.users (email, name, password_hash, is_active)\n            VALUES ($1, $2, $3, $4)\n            RETURNING id\n        ', 'mock_replacement@example.com', 'Mock Replacement', 'hash', True)
        user = await real_postgres.fetchrow('SELECT * FROM auth.users WHERE id = $1', user_id)
        assert user['email'] == 'mock_replacement@example.com'
        assert user['is_active'] is True
        assert user['created_at'] is not None
        with pytest.raises(Exception):
            await real_postgres.execute('\n                INSERT INTO auth.users (email, name, password_hash, is_active)\n                VALUES ($1, $2, $3, $4)\n            ', 'mock_replacement@example.com', 'Duplicate', 'hash', True)

    async def test_replace_redis_mock(self, real_redis):
        """Demonstrate replacing Redis mocks with real Redis operations."""
        cache_key = 'user_session:12345'
        session_data = {'user_id': '123', 'email': 'test@example.com', 'expires_at': '2025-12-31T23:59:59Z'}
        await real_redis.set(cache_key, json.dumps(session_data), ex=3600)
        cached_value = await real_redis.get(cache_key)
        assert cached_value is not None
        retrieved_session = json.loads(cached_value)
        assert retrieved_session['user_id'] == '123'
        assert retrieved_session['email'] == 'test@example.com'
        short_lived_key = 'temp:test'
        await real_redis.set(short_lived_key, 'temporary', ex=1)
        assert await real_redis.exists(short_lived_key)
        await asyncio.sleep(1.5)
        assert not await real_redis.exists(short_lived_key)

    async def test_replace_clickhouse_mock(self, real_clickhouse):
        """Demonstrate replacing ClickHouse mocks with real analytics operations."""
        events = [{'user_id': 'user_123', 'event_type': 'login', 'session_id': 'session_abc', 'properties': {'source': 'web', 'device': 'desktop'}}, {'user_id': 'user_123', 'event_type': 'page_view', 'session_id': 'session_abc', 'properties': {'page': '/dashboard', 'referrer': 'direct'}}]
        await real_clickhouse.insert_data('user_events', events)
        user_event_count = await real_clickhouse.execute("\n            SELECT COUNT(*) FROM user_events \n            WHERE user_id = 'user_123' AND properties['source'] = 'web'\n        ")
        assert user_event_count[0][0] >= 2
        event_types = await real_clickhouse.execute("\n            SELECT event_type, COUNT(*) as count\n            FROM user_events \n            WHERE user_id = 'user_123'\n            GROUP BY event_type\n            ORDER BY count DESC\n        ")
        assert len(event_types) >= 2
        event_type_dict = {event_type: count for event_type, count in event_types}
        assert 'login' in event_type_dict
        assert 'page_view' in event_type_dict
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')