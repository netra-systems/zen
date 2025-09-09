"""
Analytics Service Database Integration Tests
==========================================

Comprehensive integration tests for Analytics Service database connectivity.
Tests actual ClickHouse and Redis connections with real services (NO MOCKS).

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Development Velocity
- Value Impact: Prevents database connectivity failures in production
- Strategic Impact: Ensures data pipeline reliability for customer analytics

Test Coverage:
- ClickHouse connection establishment and validation
- Redis connection management and caching operations
- Database manager initialization and health checks
- Connection pooling and concurrent access
- Error handling and reconnection logic
- Schema creation and table setup
- Real-world transaction scenarios
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from shared.isolated_environment import IsolatedEnvironment

from test_framework import setup_test_path

# CRITICAL: setup_test_path() MUST be called before any project imports per CLAUDE.md
setup_test_path()

from analytics_service.analytics_core.database.clickhouse_manager import (
    ClickHouseManager,
    ClickHouseConnectionError,
    ClickHouseQueryError,
)
from analytics_service.analytics_core.database.redis_manager import (
    RedisManager,
    RedisConnectionError,
)
from analytics_service.analytics_core.config import get_config
from shared.isolated_environment import get_env


class TestClickHouseDatabaseIntegration:
    """Integration tests for ClickHouse database connectivity."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation per CLAUDE.md requirements."""
        env = get_env()
        env.enable_isolation()
        
        # Set analytics-specific test configuration
        env.set("ENVIRONMENT", "test", "test_database_integration")
        env.set("CLICKHOUSE_HOST", "localhost", "test_database_integration")
        env.set("CLICKHOUSE_PORT", "9000", "test_database_integration")
        env.set("CLICKHOUSE_DATABASE", "analytics_test", "test_database_integration")
        env.set("CLICKHOUSE_USERNAME", "default", "test_database_integration")
        env.set("CLICKHOUSE_PASSWORD", "", "test_database_integration")
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def clickhouse_manager(self, isolated_test_env):
        """Create ClickHouse manager with test configuration."""
        config = get_config()
        manager = ClickHouseManager(
            host=config.clickhouse_host,
            port=config.clickhouse_port,
            database=config.clickhouse_database,
            user=config.clickhouse_username,
            password=config.clickhouse_password,
            max_connections=5,  # Smaller pool for tests
            connection_timeout=5,  # Faster timeout for tests
            query_timeout=10,  # Shorter timeout for tests
            max_retries=2,  # Fewer retries for tests
        )
        
        yield manager
        
        # Cleanup
        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_clickhouse_connection_establishment(self, clickhouse_manager):
        """Test establishing connection to ClickHouse."""
        # Test connection establishment
        await clickhouse_manager.connect()
        
        assert clickhouse_manager.is_connected()
        
        # Test basic query execution
        result = await clickhouse_manager.execute_query("SELECT 1 as test")
        assert result == [(1,)]

    @pytest.mark.asyncio
    async def test_clickhouse_connection_retry_logic(self, isolated_test_env):
        """Test ClickHouse connection retry mechanism with invalid host."""
        # Set invalid configuration to test retry logic
        isolated_test_env.set("CLICKHOUSE_HOST", "invalid-host", "test_retry")
        
        config = get_config()
        manager = ClickHouseManager(
            host="invalid-host",  # This should fail
            port=config.clickhouse_port,
            database=config.clickhouse_database,
            user=config.clickhouse_username,
            password=config.clickhouse_password,
            max_retries=2,
            retry_delay=0.1,  # Fast retry for tests
        )
        
        # Connection should fail after retries
        with pytest.raises(ClickHouseConnectionError):
            await manager.connect()

    @pytest.mark.asyncio
    async def test_clickhouse_health_check(self, clickhouse_manager):
        """Test ClickHouse health check functionality."""
        await clickhouse_manager.connect()
        
        # Test health check on connected instance
        is_healthy = await clickhouse_manager.health_check()
        assert is_healthy

    @pytest.mark.asyncio
    async def test_clickhouse_database_creation(self, clickhouse_manager):
        """Test creating analytics test database."""
        await clickhouse_manager.connect()
        
        # Create test database
        test_db_name = f"analytics_test_db_{int(time.time())}"
        await clickhouse_manager.execute_command(f"CREATE DATABASE IF NOT EXISTS {test_db_name}")
        
        # Verify database exists
        databases = await clickhouse_manager.execute_query("SHOW DATABASES")
        db_names = [db[0] for db in databases]
        assert test_db_name in db_names
        
        # Cleanup
        await clickhouse_manager.execute_command(f"DROP DATABASE IF EXISTS {test_db_name}")

    @pytest.mark.asyncio
    async def test_clickhouse_table_operations(self, clickhouse_manager):
        """Test ClickHouse table creation and data operations."""
        await clickhouse_manager.connect()
        
        # Create test table
        table_name = f"test_events_{int(time.time())}"
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            event_id UUID DEFAULT generateUUIDv4(),
            timestamp DateTime64(3) DEFAULT now(),
            user_id String,
            event_type String,
            properties String,
            event_value Float64
        ) ENGINE = MergeTree()
        ORDER BY (user_id, timestamp, event_id)
        """
        
        await clickhouse_manager.execute_command(create_table_sql)
        
        # Insert test data
        test_event = {
            "user_id": "test_user_123",
            "event_type": "test_event",
            "properties": json.dumps({"test": True}),
            "event_value": 42.0,
        }
        
        insert_sql = f"""
        INSERT INTO {table_name} (user_id, event_type, properties, event_value)
        VALUES (%(user_id)s, %(event_type)s, %(properties)s, %(event_value)s)
        """
        
        await clickhouse_manager.execute_command(insert_sql, test_event)
        
        # Query data
        select_sql = f"SELECT user_id, event_type, event_value FROM {table_name} WHERE user_id = 'test_user_123'"
        results = await clickhouse_manager.execute_query(select_sql)
        
        assert len(results) == 1
        assert results[0][0] == "test_user_123"
        assert results[0][1] == "test_event"
        assert results[0][2] == 42.0
        
        # Cleanup
        await clickhouse_manager.execute_command(f"DROP TABLE IF EXISTS {table_name}")

    @pytest.mark.asyncio
    async def test_clickhouse_concurrent_connections(self, clickhouse_manager):
        """Test multiple concurrent connections to ClickHouse."""
        await clickhouse_manager.connect()
        
        async def concurrent_query(query_id: int):
            """Execute a query with unique identifier."""
            result = await clickhouse_manager.execute_query(f"SELECT {query_id} as query_id")
            return result[0][0]
        
        # Execute 5 concurrent queries
        tasks = [concurrent_query(i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks)
        
        # Verify all queries executed successfully
        assert results == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_clickhouse_query_timeout_handling(self, clickhouse_manager):
        """Test ClickHouse query timeout handling."""
        # Create manager with very short timeout
        config = get_config()
        timeout_manager = ClickHouseManager(
            host=config.clickhouse_host,
            port=config.clickhouse_port,
            database=config.clickhouse_database,
            user=config.clickhouse_username,
            password=config.clickhouse_password,
            query_timeout=1,  # 1 second timeout
        )
        
        await timeout_manager.connect()
        
        try:
            # This query should timeout (sleep for 2 seconds)
            with pytest.raises(ClickHouseQueryError):
                await timeout_manager.execute_query("SELECT sleep(2)")
        finally:
            await timeout_manager.disconnect()


class TestRedisDatabaseIntegration:
    """Integration tests for Redis database connectivity."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation for Redis tests."""
        env = get_env()
        env.enable_isolation()
        
        # Set Redis-specific test configuration
        env.set("ENVIRONMENT", "test", "test_redis_integration")
        env.set("REDIS_HOST", "localhost", "test_redis_integration")
        env.set("REDIS_PORT", "6379", "test_redis_integration")
        env.set("REDIS_ANALYTICS_DB", "2", "test_redis_integration")
        env.set("REDIS_PASSWORD", "", "test_redis_integration")
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def redis_manager(self, isolated_test_env):
        """Create Redis manager with test configuration."""
        config = get_config()
        manager = RedisManager(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            max_connections=5,  # Smaller pool for tests
            connection_timeout=5,  # Faster timeout for tests
        )
        
        yield manager
        
        # Cleanup
        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_redis_connection_establishment(self, redis_manager):
        """Test establishing connection to Redis."""
        # Test connection establishment
        await redis_manager.connect()
        
        assert redis_manager.is_connected()
        
        # Test basic ping
        pong = await redis_manager.ping()
        assert pong is True

    @pytest.mark.asyncio
    async def test_redis_basic_operations(self, redis_manager):
        """Test basic Redis operations (set, get, delete)."""
        await redis_manager.connect()
        
        # Test SET and GET
        test_key = f"test_key_{int(time.time())}"
        test_value = {"data": "test_value", "timestamp": time.time()}
        
        await redis_manager.set(test_key, test_value, ex=300)
        retrieved_value = await redis_manager.get(test_key)
        
        assert retrieved_value == test_value
        
        # Test EXISTS
        exists = await redis_manager.exists(test_key)
        assert exists is True
        
        # Test DELETE
        deleted = await redis_manager.delete(test_key)
        assert deleted == 1
        
        # Verify deletion
        retrieved_after_delete = await redis_manager.get(test_key)
        assert retrieved_after_delete is None

    @pytest.mark.asyncio
    async def test_redis_expiration_handling(self, redis_manager):
        """Test Redis key expiration functionality."""
        await redis_manager.connect()
        
        # Set key with short expiration
        test_key = f"expire_test_{int(time.time())}"
        test_value = "expires_soon"
        
        await redis_manager.set(test_key, test_value, ex=1)
        
        # Verify key exists initially
        value = await redis_manager.get(test_key)
        assert value == test_value
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Verify key has expired
        expired_value = await redis_manager.get(test_key)
        assert expired_value is None

    @pytest.mark.asyncio
    async def test_redis_hash_operations(self, redis_manager):
        """Test Redis hash operations for structured data."""
        await redis_manager.connect()
        
        hash_key = f"user_session_{int(time.time())}"
        session_data = {
            "user_id": "user_123",
            "session_start": str(datetime.now(timezone.utc)),
            "page_views": "5",
            "last_activity": str(datetime.now(timezone.utc)),
        }
        
        # Set hash fields
        await redis_manager.hset(hash_key, session_data)
        
        # Get hash fields
        retrieved_data = await redis_manager.hgetall(hash_key)
        assert retrieved_data == session_data
        
        # Get specific field
        user_id = await redis_manager.hget(hash_key, "user_id")
        assert user_id == "user_123"
        
        # Update field
        await redis_manager.hset(hash_key, {"page_views": "6"})
        updated_views = await redis_manager.hget(hash_key, "page_views")
        assert updated_views == "6"
        
        # Cleanup
        await redis_manager.delete(hash_key)

    @pytest.mark.asyncio
    async def test_redis_list_operations(self, redis_manager):
        """Test Redis list operations for event queues."""
        await redis_manager.connect()
        
        list_key = f"event_queue_{int(time.time())}"
        
        # Push events to list
        events = [
            json.dumps({"event": "login", "user": "user1", "timestamp": time.time()}),
            json.dumps({"event": "click", "user": "user1", "timestamp": time.time()}),
            json.dumps({"event": "logout", "user": "user1", "timestamp": time.time()}),
        ]
        
        for event in events:
            await redis_manager.lpush(list_key, event)
        
        # Get list length
        length = await redis_manager.llen(list_key)
        assert length == 3
        
        # Pop events from list
        popped_events = []
        while await redis_manager.llen(list_key) > 0:
            event = await redis_manager.rpop(list_key)
            popped_events.append(event)
        
        # Verify events were popped in correct order (FIFO)
        assert len(popped_events) == 3
        assert json.loads(popped_events[0])["event"] == "login"
        assert json.loads(popped_events[1])["event"] == "click"
        assert json.loads(popped_events[2])["event"] == "logout"

    @pytest.mark.asyncio
    async def test_redis_pub_sub_operations(self, redis_manager):
        """Test Redis pub/sub for real-time notifications."""
        await redis_manager.connect()
        
        channel = f"test_channel_{int(time.time())}"
        test_message = {"type": "event_processed", "count": 10, "timestamp": time.time()}
        
        # Subscribe to channel
        pubsub = await redis_manager.subscribe(channel)
        
        # Publish message
        await redis_manager.publish(channel, test_message)
        
        # Receive message (with timeout)
        try:
            message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=2.0)
            if message:
                received_data = json.loads(message['data'])
                assert received_data == test_message
        except asyncio.TimeoutError:
            pytest.fail("Did not receive pub/sub message within timeout")
        finally:
            await pubsub.unsubscribe(channel)

    @pytest.mark.asyncio
    async def test_redis_concurrent_operations(self, redis_manager):
        """Test multiple concurrent Redis operations."""
        await redis_manager.connect()
        
        async def concurrent_set_get(op_id: int):
            """Perform concurrent set/get operations."""
            key = f"concurrent_key_{op_id}"
            value = f"concurrent_value_{op_id}"
            
            await redis_manager.set(key, value, ex=60)
            retrieved = await redis_manager.get(key)
            await redis_manager.delete(key)
            
            return retrieved == value
        
        # Execute 10 concurrent operations
        tasks = [concurrent_set_get(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded
        assert all(results)

    @pytest.mark.asyncio
    async def test_redis_connection_recovery(self, redis_manager):
        """Test Redis connection recovery after disconnect."""
        await redis_manager.connect()
        
        # Verify initial connection
        assert redis_manager.is_connected()
        
        # Force disconnect
        await redis_manager.disconnect()
        assert not redis_manager.is_connected()
        
        # Reconnect and test
        await redis_manager.connect()
        assert redis_manager.is_connected()
        
        # Test operation after reconnection
        test_key = f"recovery_test_{int(time.time())}"
        await redis_manager.set(test_key, "recovery_success")
        value = await redis_manager.get(test_key)
        assert value == "recovery_success"
        
        # Cleanup
        await redis_manager.delete(test_key)


class TestDatabaseIntegrationCombined:
    """Integration tests combining ClickHouse and Redis operations."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation for combined tests."""
        env = get_env()
        env.enable_isolation()
        
        # Set configuration for both databases
        env.set("ENVIRONMENT", "test", "test_combined_integration")
        env.set("CLICKHOUSE_HOST", "localhost", "test_combined_integration")
        env.set("CLICKHOUSE_PORT", "9000", "test_combined_integration")
        env.set("CLICKHOUSE_DATABASE", "analytics_test", "test_combined_integration")
        env.set("REDIS_HOST", "localhost", "test_combined_integration")
        env.set("REDIS_PORT", "6379", "test_combined_integration")
        env.set("REDIS_ANALYTICS_DB", "2", "test_combined_integration")
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def database_managers(self, isolated_test_env):
        """Create both ClickHouse and Redis managers."""
        config = get_config()
        
        clickhouse_manager = ClickHouseManager(
            host=config.clickhouse_host,
            port=config.clickhouse_port,
            database=config.clickhouse_database,
            user=config.clickhouse_username,
            password=config.clickhouse_password,
        )
        
        redis_manager = RedisManager(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
        )
        
        yield clickhouse_manager, redis_manager
        
        # Cleanup
        await clickhouse_manager.disconnect()
        await redis_manager.disconnect()

    @pytest.mark.asyncio
    async def test_combined_event_storage_and_caching(self, database_managers):
        """Test storing events in ClickHouse and caching aggregates in Redis."""
        clickhouse_manager, redis_manager = database_managers
        
        # Connect both managers
        await clickhouse_manager.connect()
        await redis_manager.connect()
        
        # Create test table in ClickHouse
        table_name = f"combined_test_events_{int(time.time())}"
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            event_id UUID DEFAULT generateUUIDv4(),
            timestamp DateTime64(3) DEFAULT now(),
            user_id String,
            event_type String,
            event_value Float64
        ) ENGINE = MergeTree()
        ORDER BY (user_id, timestamp, event_id)
        """
        await clickhouse_manager.execute_command(create_table_sql)
        
        # Insert test events
        test_user = f"test_user_{int(time.time())}"
        events = [
            {"user_id": test_user, "event_type": "login", "event_value": 1.0},
            {"user_id": test_user, "event_type": "click", "event_value": 5.0},
            {"user_id": test_user, "event_type": "purchase", "event_value": 100.0},
        ]
        
        for event in events:
            insert_sql = f"""
            INSERT INTO {table_name} (user_id, event_type, event_value)
            VALUES (%(user_id)s, %(event_type)s, %(event_value)s)
            """
            await clickhouse_manager.execute_command(insert_sql, event)
        
        # Calculate aggregates from ClickHouse
        aggregate_sql = f"""
        SELECT 
            user_id,
            count() as event_count,
            sum(event_value) as total_value
        FROM {table_name}
        WHERE user_id = '{test_user}'
        GROUP BY user_id
        """
        results = await clickhouse_manager.execute_query(aggregate_sql)
        
        assert len(results) == 1
        user_id, event_count, total_value = results[0]
        assert user_id == test_user
        assert event_count == 3
        assert total_value == 106.0
        
        # Cache aggregates in Redis
        cache_key = f"user_aggregates:{test_user}"
        cache_data = {
            "user_id": user_id,
            "event_count": event_count,
            "total_value": total_value,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
        await redis_manager.set(cache_key, cache_data, ex=3600)
        
        # Retrieve from cache
        cached_data = await redis_manager.get(cache_key)
        assert cached_data["user_id"] == test_user
        assert cached_data["event_count"] == 3
        assert cached_data["total_value"] == 106.0
        
        # Cleanup
        await clickhouse_manager.execute_command(f"DROP TABLE IF EXISTS {table_name}")
        await redis_manager.delete(cache_key)

    @pytest.mark.asyncio
    async def test_database_health_checks_combined(self, database_managers):
        """Test health checks for both database systems."""
        clickhouse_manager, redis_manager = database_managers
        
        # Connect both managers
        await clickhouse_manager.connect()
        await redis_manager.connect()
        
        # Test ClickHouse health
        ch_healthy = await clickhouse_manager.health_check()
        assert ch_healthy is True
        
        # Test Redis health
        redis_healthy = await redis_manager.ping()
        assert redis_healthy is True
        
        # Combined health check
        overall_healthy = ch_healthy and redis_healthy
        assert overall_healthy is True

    @pytest.mark.asyncio
    async def test_transaction_consistency_across_databases(self, database_managers):
        """Test maintaining consistency across ClickHouse and Redis operations."""
        clickhouse_manager, redis_manager = database_managers
        
        await clickhouse_manager.connect()
        await redis_manager.connect()
        
        # Simulate transaction: store event and update cache
        user_id = f"transaction_test_{int(time.time())}"
        session_id = str(uuid4())
        
        try:
            # Step 1: Store event in ClickHouse
            table_name = f"transaction_events_{int(time.time())}"
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                event_id UUID DEFAULT generateUUIDv4(),
                timestamp DateTime64(3) DEFAULT now(),
                user_id String,
                session_id String,
                event_type String
            ) ENGINE = MergeTree()
            ORDER BY (user_id, timestamp, event_id)
            """
            await clickhouse_manager.execute_command(create_table_sql)
            
            insert_sql = f"""
            INSERT INTO {table_name} (user_id, session_id, event_type)
            VALUES (%(user_id)s, %(session_id)s, %(event_type)s)
            """
            await clickhouse_manager.execute_command(insert_sql, {
                "user_id": user_id,
                "session_id": session_id,
                "event_type": "session_start"
            })
            
            # Step 2: Update session cache in Redis
            session_key = f"session:{session_id}"
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "event_count": 1,
            }
            await redis_manager.set(session_key, session_data, ex=3600)
            
            # Verify both operations succeeded
            # Check ClickHouse
            select_sql = f"SELECT user_id, session_id FROM {table_name} WHERE session_id = '{session_id}'"
            ch_results = await clickhouse_manager.execute_query(select_sql)
            assert len(ch_results) == 1
            assert ch_results[0][0] == user_id
            assert ch_results[0][1] == session_id
            
            # Check Redis
            cached_session = await redis_manager.get(session_key)
            assert cached_session["user_id"] == user_id
            assert cached_session["session_id"] == session_id
            assert cached_session["event_count"] == 1
            
            # Cleanup
            await clickhouse_manager.execute_command(f"DROP TABLE IF EXISTS {table_name}")
            await redis_manager.delete(session_key)
            
        except Exception as e:
            # In a real implementation, this would trigger rollback logic
            pytest.fail(f"Transaction consistency test failed: {e}")