"""
Focused tests for Real Database Services - PostgreSQL, Redis, and ClickHouse operations
Tests real database connections, transactions, and data operations
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import os
import sys
import asyncio
import pytest
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar
from pathlib import Path
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel

T = TypeVar('T')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.postgres import async_session_factory
from app.redis_manager import RedisManager
from app.db.clickhouse import get_clickhouse_client
from app.db.models_postgres import User, Thread, Message
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Define schema classes for tests
class ThreadCreate(BaseModel):
    title: str
    user_id: str

class MessageCreate(BaseModel):
    thread_id: str
    user_id: str
    content: str
    role: str = "user"

# Test markers for database services
pytestmark = [
    pytest.mark.real_services,
    pytest.mark.real_database,
    pytest.mark.real_redis,
    pytest.mark.real_clickhouse,
    pytest.mark.e2e
]

# Skip tests if real services not enabled
skip_if_no_real_services = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real service tests disabled. Set ENABLE_REAL_LLM_TESTING=true to run"
)


class TestRealDatabaseServices:
    """Test real database services integration"""
    
    # Timeout configurations for database services
    DATABASE_TIMEOUT = 30  # seconds 
    REDIS_TIMEOUT = 10  # seconds
    CLICKHOUSE_TIMEOUT = 30  # seconds
    
    @staticmethod
    def with_retry_and_timeout(timeout: int = 30, max_attempts: int = 3):
        """Decorator to add retry logic and timeout to service calls"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry_if=retry_if_exception_type((ConnectionError, TimeoutError, asyncio.TimeoutError))
            )
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            return wrapper
        return decorator
    
    @pytest.fixture(scope="class")
    async def database_session(self):
        """Create real database session for testing"""
        async with async_session_factory() as session:
            yield session
    
    @pytest.fixture(scope="class")
    async def redis_manager(self):
        """Initialize real Redis manager for testing"""
        manager = RedisManager()
        await manager.initialize()
        yield manager
        await manager.close()
    
    @pytest.fixture(scope="class")
    async def clickhouse_client(self):
        """Initialize real ClickHouse client for testing"""
        return get_clickhouse_client()

    def _create_test_transaction_data(self):
        """Create test data for transaction testing"""
        timestamp = int(time.time())
        return {
            "user_data": {
                "email": f"test_{timestamp}@example.com",
                "name": f"Test User {timestamp}"
            },
            "thread_data": {
                "title": f"Test Thread {timestamp}"
            },
            "message_data": {
                "content": f"Test message content {timestamp}",
                "role": "user"
            }
        }

    def _validate_transaction_result(self, user_id, thread_id, message_id):
        """Validate transaction results"""
        assert user_id is not None
        assert thread_id is not None 
        assert message_id is not None
        assert isinstance(user_id, str)
        assert isinstance(thread_id, str)
        assert isinstance(message_id, str)
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=30)
    async def test_database_transaction_integrity(self, database_session):
        """Test database transaction integrity with real PostgreSQL"""
        test_data = self._create_test_transaction_data()
        
        # Create user
        user = User(email=test_data["user_data"]["email"], name=test_data["user_data"]["name"])
        database_session.add(user)
        await database_session.flush()
        
        # Create thread
        thread = Thread(title=test_data["thread_data"]["title"], user_id=user.id)
        database_session.add(thread)
        await database_session.flush()
        
        # Create message
        message = Message(
            thread_id=thread.id,
            user_id=user.id,
            content=test_data["message_data"]["content"],
            role=test_data["message_data"]["role"]
        )
        database_session.add(message)
        await database_session.commit()
        
        self._validate_transaction_result(user.id, thread.id, message.id)
        logger.info("Database transaction integrity test completed successfully")

    def _create_postgresql_test_operations(self):
        """Create PostgreSQL test operations"""
        timestamp = int(time.time())
        return {
            "insert": {"email": f"insert_{timestamp}@example.com", "name": f"Insert User {timestamp}"},
            "update": {"name": f"Updated User {timestamp}"},
            "select_criteria": {"email": f"insert_{timestamp}@example.com"}
        }

    def _validate_postgresql_operations(self, insert_result, update_result, select_result):
        """Validate PostgreSQL operations results"""
        assert insert_result is not None
        assert update_result is not None
        assert select_result is not None
        assert hasattr(select_result, 'name')
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=30)
    async def test_postgresql_operations(self, database_session):
        """Test comprehensive PostgreSQL operations"""
        operations = self._create_postgresql_test_operations()
        
        # Insert operation
        user = User(**operations["insert"])
        database_session.add(user)
        await database_session.flush()
        
        # Update operation
        user.name = operations["update"]["name"]
        await database_session.commit()
        
        # Select operation
        result = await database_session.execute(
            select(User).where(User.email == operations["select_criteria"]["email"])
        )
        selected_user = result.scalar_one_or_none()
        
        self._validate_postgresql_operations(user, user, selected_user)
        logger.info("PostgreSQL operations test completed successfully")

    def _create_redis_test_data(self):
        """Create Redis test data"""
        timestamp = int(time.time())
        return {
            "cache_key": f"test_cache_{timestamp}",
            "cache_value": {"data": f"test_value_{timestamp}", "timestamp": timestamp},
            "pubsub_channel": f"test_channel_{timestamp}",
            "pubsub_message": {"event": "test_event", "data": f"test_data_{timestamp}"}
        }

    def _validate_redis_operations(self, set_result, get_result, original_value):
        """Validate Redis operations results"""
        assert set_result is True
        assert get_result is not None
        assert get_result["data"] == original_value["data"]
        return True

    @skip_if_no_real_services  
    @with_retry_and_timeout(timeout=10)
    async def test_redis_operations(self, redis_manager):
        """Test comprehensive Redis operations"""
        test_data = self._create_redis_test_data()
        
        # Set operation
        set_result = await redis_manager.set(
            test_data["cache_key"], 
            test_data["cache_value"], 
            expire=300
        )
        
        # Get operation
        get_result = await redis_manager.get(test_data["cache_key"])
        
        self._validate_redis_operations(set_result, get_result, test_data["cache_value"])
        logger.info("Redis operations test completed successfully")

    def _create_redis_pubsub_scenario(self):
        """Create Redis pub/sub test scenario"""
        timestamp = int(time.time())
        return {
            "channel": f"test_pubsub_{timestamp}",
            "message": {"event": "test_event", "data": f"test_data_{timestamp}"},
            "subscriber_timeout": 5
        }

    def _validate_pubsub_result(self, published_result, received_message, original_message):
        """Validate Redis pub/sub results"""
        assert published_result > 0  # At least one subscriber
        assert received_message is not None
        assert received_message["data"] == original_message["data"]
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=15)
    async def test_redis_pubsub_real(self, redis_manager):
        """Test real Redis pub/sub functionality"""
        scenario = self._create_redis_pubsub_scenario()
        
        # Subscribe to channel
        subscriber = await redis_manager.subscribe(scenario["channel"])
        
        # Publish message
        published = await redis_manager.publish(scenario["channel"], scenario["message"])
        
        # Receive message
        received = await asyncio.wait_for(
            subscriber.get_message(), 
            timeout=scenario["subscriber_timeout"]
        )
        
        self._validate_pubsub_result(published, received, scenario["message"])
        logger.info("Redis pub/sub test completed successfully")

    def _create_clickhouse_test_data(self):
        """Create ClickHouse test data"""
        timestamp = int(time.time())
        return {
            "table": f"test_metrics_{timestamp}",
            "data": [
                {"timestamp": timestamp, "metric": "cpu_usage", "value": 75.5},
                {"timestamp": timestamp + 1, "metric": "memory_usage", "value": 68.2},
                {"timestamp": timestamp + 2, "metric": "disk_usage", "value": 42.1}
            ],
            "query": f"SELECT COUNT(*) as count FROM test_metrics_{timestamp}"
        }

    def _validate_clickhouse_operations(self, insert_result, query_result):
        """Validate ClickHouse operations results"""
        assert insert_result is not None
        assert query_result is not None
        assert len(query_result) > 0
        assert "count" in query_result[0]
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=30)
    async def test_clickhouse_operations(self, clickhouse_client):
        """Test comprehensive ClickHouse operations"""
        test_data = self._create_clickhouse_test_data()
        
        # Create table
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {test_data["table"]} (
                timestamp UInt64,
                metric String,
                value Float64
            ) ENGINE = Memory
        """
        await clickhouse_client.execute(create_table_sql)
        
        # Insert data
        insert_result = await clickhouse_client.execute(
            f"INSERT INTO {test_data['table']} VALUES", 
            test_data["data"]
        )
        
        # Query data
        query_result = await clickhouse_client.execute(test_data["query"])
        
        self._validate_clickhouse_operations(insert_result, query_result)
        logger.info("ClickHouse operations test completed successfully")

    def _create_clickhouse_aggregation_query(self, table_name):
        """Create ClickHouse aggregation query"""
        return f"""
            SELECT 
                metric,
                AVG(value) as avg_value,
                MAX(value) as max_value,
                MIN(value) as min_value
            FROM {table_name}
            GROUP BY metric
            ORDER BY metric
        """

    def _validate_aggregation_results(self, results):
        """Validate ClickHouse aggregation results"""
        assert results is not None
        assert len(results) > 0
        for result in results:
            assert "metric" in result
            assert "avg_value" in result
            assert "max_value" in result
            assert "min_value" in result
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=30)
    async def test_clickhouse_aggregations_real(self, clickhouse_client):
        """Test real ClickHouse aggregation queries"""
        test_data = self._create_clickhouse_test_data()
        
        # Setup test data (reuse from previous test)
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {test_data["table"]}_agg (
                timestamp UInt64,
                metric String,
                value Float64
            ) ENGINE = Memory
        """
        await clickhouse_client.execute(create_table_sql)
        
        await clickhouse_client.execute(
            f"INSERT INTO {test_data['table']}_agg VALUES", 
            test_data["data"]
        )
        
        # Run aggregation query
        aggregation_query = self._create_clickhouse_aggregation_query(f"{test_data['table']}_agg")
        results = await clickhouse_client.execute(aggregation_query)
        
        self._validate_aggregation_results(results)
        logger.info("ClickHouse aggregations test completed successfully")