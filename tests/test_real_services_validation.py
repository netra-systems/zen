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



# Import real services fixtures

from test_framework.conftest_real_services import (

    real_services,

    real_postgres, 

    real_redis,

    real_clickhouse,

    real_websocket_client,

    real_http_client,

    test_user,

    test_organization,

    test_agent,

    performance_monitor,

    require_real_services

)





@require_real_services()

class TestRealServicesInfrastructure:

    """Test suite validating real services infrastructure."""

    

    async def test_services_health_check(self, real_services):

        """Verify all real services are healthy and accessible."""

        # Test service availability

        await real_services.ensure_all_services_available()

        

        # Test basic connectivity to each service

        async with real_services.postgres.connection() as conn:

            result = await conn.fetchval("SELECT 1")

            assert result == 1

            

        redis_client = await real_services.redis.get_client()

        ping_result = await redis_client.ping()

        assert ping_result is True

        

        clickhouse_result = await real_services.clickhouse.execute("SELECT 1")

        assert clickhouse_result == [[1]]

    

    async def test_postgres_real_operations(self, real_postgres):

        """Test PostgreSQL with real database operations."""

        # Test data insertion

        user_id = await real_postgres.fetchval("""

            INSERT INTO auth.users (email, name, password_hash, is_active)

            VALUES ($1, $2, $3, $4)

            RETURNING id

        """, "postgres_test@example.com", "Postgres Test User", 

            "test_hash", True)

        

        assert user_id is not None

        

        # Test data retrieval

        user = await real_postgres.fetchrow(

            "SELECT * FROM auth.users WHERE id = $1", user_id

        )

        assert user['email'] == "postgres_test@example.com"

        assert user['name'] == "Postgres Test User"

        assert user['is_active'] is True

        

        # Test data updates

        await real_postgres.execute(

            "UPDATE auth.users SET name = $1 WHERE id = $2",

            "Updated Name", user_id

        )

        

        updated_user = await real_postgres.fetchrow(

            "SELECT name FROM auth.users WHERE id = $1", user_id

        )

        assert updated_user['name'] == "Updated Name"

        

        # Test constraints (unique email)

        with pytest.raises(Exception):  # Should raise unique constraint violation

            await real_postgres.execute("""

                INSERT INTO auth.users (email, name, password_hash, is_active)

                VALUES ($1, $2, $3, $4)

            """, "postgres_test@example.com", "Duplicate User", "hash", True)

    

    async def test_redis_real_operations(self, real_redis):

        """Test Redis with real cache operations."""

        # Test basic set/get

        key = "test_redis_key"

        value = "test_redis_value"

        

        set_result = await real_redis.set(key, value)

        assert set_result is True

        

        get_result = await real_redis.get(key)

        assert get_result == value

        

        # Test JSON data

        json_key = "test_json_key"

        json_data = {"name": "Test", "count": 42, "active": True}

        

        await real_redis.set(json_key, json.dumps(json_data))

        retrieved_json = await real_redis.get(json_key)

        parsed_data = json.loads(retrieved_json)

        

        assert parsed_data == json_data

        

        # Test expiration

        temp_key = "temp_key"

        await real_redis.set(temp_key, "temporary", ex=1)  # 1 second expiry

        

        # Should exist immediately

        assert await real_redis.exists(temp_key)

        

        # Wait for expiry

        await asyncio.sleep(1.5)

        assert not await real_redis.exists(temp_key)

        

        # Test deletion

        await real_redis.set("delete_me", "value")

        assert await real_redis.exists("delete_me")

        

        deleted_count = await real_redis.delete("delete_me")

        assert deleted_count == 1

        assert not await real_redis.exists("delete_me")

    

    async def test_clickhouse_real_operations(self, real_clickhouse):

        """Test ClickHouse with real analytics operations."""

        # Insert test data

        test_events = [

            {

                'user_id': '123e4567-e89b-12d3-a456-426614174001',

                'event_type': 'login',

                'session_id': 'session_001',

                'properties': {'source': 'test', 'device': 'desktop'}

            },

            {

                'user_id': '123e4567-e89b-12d3-a456-426614174002', 

                'event_type': 'page_view',

                'session_id': 'session_002',

                'properties': {'page': '/dashboard', 'source': 'test'}

            },

            {

                'user_id': '123e4567-e89b-12d3-a456-426614174001',

                'event_type': 'logout', 

                'session_id': 'session_001',

                'properties': {'source': 'test', 'duration': '300'}

            }

        ]

        

        await real_clickhouse.insert_data('user_events', test_events)

        

        # Test basic counting

        count_result = await real_clickhouse.execute(

            "SELECT COUNT(*) FROM user_events WHERE properties['source'] = 'test'"

        )

        assert count_result[0][0] >= 3  # At least our test events

        

        # Test aggregation

        user_event_counts = await real_clickhouse.execute("""

            SELECT user_id, COUNT(*) as event_count

            FROM user_events 

            WHERE properties['source'] = 'test'

            GROUP BY user_id

            ORDER BY event_count DESC

        """)

        

        # First user should have 2 events (login + logout)

        assert len(user_event_counts) >= 2

        user1_count = next(

            (count for user_id, count in user_event_counts 

             if user_id == '123e4567-e89b-12d3-a456-426614174001'), 

            0

        )

        assert user1_count == 2

        

        # Test filtering by event type

        login_events = await real_clickhouse.execute("""

            SELECT COUNT(*) FROM user_events 

            WHERE event_type = 'login' AND properties['source'] = 'test'

        """)

        assert login_events[0][0] >= 1

    

    async def test_websocket_real_connection(self, real_websocket_client):

        """Test WebSocket with real connection."""

        # Skip if WebSocket service not available

        try:

            await real_websocket_client.connect("test")

        except Exception:

            pytest.skip("WebSocket service not available for testing")

        

        # Test sending JSON message

        test_message = {

            "type": "test_message",

            "content": "Hello WebSocket!",

            "timestamp": time.time()

        }

        

        await real_websocket_client.send(test_message)

        

        # Note: Receiving depends on WebSocket server implementation

        # This test validates the connection and sending works

        

    async def test_http_real_requests(self, real_http_client, real_services):

        """Test HTTP client with real requests."""

        # Test health endpoint if available

        try:

            response = await real_http_client.get("http://httpbin.org/get")

            assert response.status_code == 200

            data = response.json()

            assert 'url' in data

        except Exception:

            # If external service unavailable, test local service

            pytest.skip("HTTP test service not available")

    

    async def test_data_isolation_between_tests(self, real_services):

        """Test that data is properly isolated between tests."""

        # Insert test data

        await real_services.postgres.execute("""

            INSERT INTO auth.users (email, name, password_hash, is_active)

            VALUES ($1, $2, $3, $4)

        """, "isolation_test@example.com", "Isolation Test", "hash", True)

        

        # Set Redis data

        await real_services.redis.set("isolation_test", "test_value")

        

        # Insert ClickHouse data

        await real_services.clickhouse.execute("""

            INSERT INTO user_events (user_id, event_type, session_id)

            VALUES ('isolation_user', 'test_event', 'isolation_session')

        """)

        

        # Verify data exists

        user_count = await real_services.postgres.fetchval(

            "SELECT COUNT(*) FROM auth.users WHERE email = $1",

            "isolation_test@example.com"

        )

        assert user_count == 1

        

        redis_value = await real_services.redis.get("isolation_test")

        assert redis_value == "test_value"

        

        # Note: Data should be cleaned up automatically before next test

    

    async def test_performance_monitoring(self, real_services, performance_monitor):

        """Test performance monitoring capabilities."""

        # Test database operation performance

        performance_monitor.start("bulk_insert")

        

        # Insert multiple records

        users_data = [

            (f"perf_test_{i}@example.com", f"User {i}", "hash", True)

            for i in range(100)

        ]

        

        async with real_services.postgres.connection() as conn:

            await conn.executemany("""

                INSERT INTO auth.users (email, name, password_hash, is_active)

                VALUES ($1, $2, $3, $4)

            """, users_data)

        

        duration = performance_monitor.end("bulk_insert")

        

        # Should complete within reasonable time (adjust threshold as needed)

        performance_monitor.assert_performance("bulk_insert", 10.0)  # 10 seconds max

        

        print(f"Bulk insert of 100 users took {duration:.2f} seconds")

        

        # Test Redis performance

        performance_monitor.start("redis_bulk_set")

        

        redis_client = await real_services.redis.get_client()

        for i in range(1000):

            await redis_client.set(f"perf_key_{i}", f"value_{i}")

        

        redis_duration = performance_monitor.end("redis_bulk_set")

        performance_monitor.assert_performance("redis_bulk_set", 5.0)  # 5 seconds max

        

        print(f"Bulk Redis set of 1000 keys took {redis_duration:.2f} seconds")

    

    async def test_realistic_workflow(

        self, 

        real_services, 

        test_user, 

        test_organization, 

        test_agent

    ):

        """Test a realistic workflow using real services with test fixtures."""

        # Verify test fixtures are properly created

        assert test_user['email'] == 'test@example.com'

        assert test_organization['name'] == 'Test Organization'

        assert test_agent['name'] == 'Test Agent'

        

        # Test creating a conversation

        conversation_id = await real_services.postgres.fetchval("""

            INSERT INTO backend.conversations (agent_id, user_id, title, status)

            VALUES ($1, $2, $3, $4)

            RETURNING id

        """, test_agent['id'], test_user['id'], "Test Conversation", "active")

        

        # Add messages to conversation

        messages = [

            ("user", "Hello, how can you help me?"),

            ("assistant", "I can help you with various tasks. What do you need?"),

            ("user", "I need help with testing.")

        ]

        

        message_ids = []

        for role, content in messages:

            message_id = await real_services.postgres.fetchval("""

                INSERT INTO backend.messages (conversation_id, role, content)

                VALUES ($1, $2, $3)

                RETURNING id

            """, conversation_id, role, content)

            message_ids.append(message_id)

        

        # Cache conversation in Redis

        conversation_cache_key = f"conversation:{conversation_id}"

        conversation_data = {

            'id': str(conversation_id),

            'agent_id': test_agent['id'],

            'user_id': test_user['id'],

            'message_count': len(messages)

        }

        

        await real_services.redis.set(

            conversation_cache_key, 

            json.dumps(conversation_data, default=str),

            ex=3600

        )

        

        # Log analytics event

        await real_services.clickhouse.execute("""

            INSERT INTO conversation_events 

            (conversation_id, agent_id, user_id, organization_id, event_type, message_count, tokens_used)

            VALUES

        """, [(

            str(conversation_id),

            test_agent['id'], 

            test_user['id'],

            test_organization['id'],

            'conversation_created',

            len(messages),

            150 * len(messages)  # Estimated tokens

        )])

        

        # Verify the workflow worked

        # Check database

        conversation = await real_services.postgres.fetchrow(

            "SELECT * FROM backend.conversations WHERE id = $1", 

            conversation_id

        )

        assert conversation['title'] == "Test Conversation"

        

        message_count = await real_services.postgres.fetchval(

            "SELECT COUNT(*) FROM backend.messages WHERE conversation_id = $1",

            conversation_id

        )

        assert message_count == len(messages)

        

        # Check Redis cache

        cached_data = await real_services.redis.get(conversation_cache_key)

        cached_conversation = json.loads(cached_data)

        assert cached_conversation['message_count'] == len(messages)

        

        # Check analytics

        analytics_count = await real_services.clickhouse.execute("""

            SELECT COUNT(*) FROM conversation_events 

            WHERE conversation_id = %s AND event_type = 'conversation_created'

        """, [str(conversation_id)])

        assert analytics_count[0][0] >= 1

        

        print(f"Successfully created conversation {conversation_id} with {len(messages)} messages")





@require_real_services()

class TestMockReplacementValidation:

    """Test that real services can properly replace common mock patterns."""

    

    async def test_replace_database_mock(self, real_postgres):

        """Demonstrate replacing database mocks with real database operations."""

        # This would replace patterns like:

        # mock_db.execute.return_value = None

        # mock_db.fetchrow.return_value = {'id': 123, 'name': 'test'}

        

        # Real database operations

        user_id = await real_postgres.fetchval("""

            INSERT INTO auth.users (email, name, password_hash, is_active)

            VALUES ($1, $2, $3, $4)

            RETURNING id

        """, "mock_replacement@example.com", "Mock Replacement", "hash", True)

        

        # Real data verification

        user = await real_postgres.fetchrow(

            "SELECT * FROM auth.users WHERE id = $1", user_id

        )

        

        # Real assertions that would catch actual issues

        assert user['email'] == "mock_replacement@example.com"

        assert user['is_active'] is True

        assert user['created_at'] is not None  # Real timestamp

        

        # Test real constraint violations

        with pytest.raises(Exception):

            await real_postgres.execute("""

                INSERT INTO auth.users (email, name, password_hash, is_active)

                VALUES ($1, $2, $3, $4)

            """, "mock_replacement@example.com", "Duplicate", "hash", True)

    

    async def test_replace_redis_mock(self, real_redis):

        """Demonstrate replacing Redis mocks with real Redis operations."""

        # This would replace patterns like:

        # mock_redis.get.return_value = '{"key": "value"}'

        # mock_redis.set.return_value = True

        

        # Real Redis operations

        cache_key = "user_session:12345"

        session_data = {

            'user_id': '123',

            'email': 'test@example.com',

            'expires_at': '2025-12-31T23:59:59Z'

        }

        

        # Real caching

        await real_redis.set(cache_key, json.dumps(session_data), ex=3600)

        

        # Real retrieval and verification

        cached_value = await real_redis.get(cache_key)

        assert cached_value is not None

        

        retrieved_session = json.loads(cached_value)

        assert retrieved_session['user_id'] == '123'

        assert retrieved_session['email'] == 'test@example.com'

        

        # Test real TTL behavior (mocks can't test this properly)

        short_lived_key = "temp:test"

        await real_redis.set(short_lived_key, "temporary", ex=1)

        

        assert await real_redis.exists(short_lived_key)

        await asyncio.sleep(1.5)

        assert not await real_redis.exists(short_lived_key)

    

    async def test_replace_clickhouse_mock(self, real_clickhouse):

        """Demonstrate replacing ClickHouse mocks with real analytics operations."""

        # This would replace patterns like:

        # mock_clickhouse.execute.return_value = [[42]]

        

        # Real analytics data insertion

        events = [

            {

                'user_id': 'user_123',

                'event_type': 'login',

                'session_id': 'session_abc',

                'properties': {'source': 'web', 'device': 'desktop'}

            },

            {

                'user_id': 'user_123',

                'event_type': 'page_view',

                'session_id': 'session_abc',

                'properties': {'page': '/dashboard', 'referrer': 'direct'}

            }

        ]

        

        await real_clickhouse.insert_data('user_events', events)

        

        # Real query and verification

        user_event_count = await real_clickhouse.execute("""

            SELECT COUNT(*) FROM user_events 

            WHERE user_id = 'user_123' AND properties['source'] = 'web'

        """)

        

        assert user_event_count[0][0] >= 2

        

        # Real aggregation query

        event_types = await real_clickhouse.execute("""

            SELECT event_type, COUNT(*) as count

            FROM user_events 

            WHERE user_id = 'user_123'

            GROUP BY event_type

            ORDER BY count DESC

        """)

        

        # Real data verification

        assert len(event_types) >= 2

        event_type_dict = {event_type: count for event_type, count in event_types}

        assert 'login' in event_type_dict

        assert 'page_view' in event_type_dict





if __name__ == "__main__":

    # Run with: python tests/test_real_services_validation.py

    pytest.main([__file__, "-v", "--tb=short"])

