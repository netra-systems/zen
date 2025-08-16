"""
Real database operations tests with actual database connections.
All functions ≤8 lines per requirements.
"""

from datetime import datetime
from app.db.postgres import Database
from app.redis_manager import RedisManager
from app.db.clickhouse import get_clickhouse_client
from app.db.models_postgres import User
from .real_services_test_fixtures import (
    skip_if_no_database,
    skip_if_no_redis, 
    skip_if_no_clickhouse
)


class TestRealDatabaseOperations:
    """Test suite for real database operations"""
    
    @skip_if_no_database
    async def test_postgresql_operations(self):
        """Test PostgreSQL operations with real database"""
        db_instance = Database()
        db = db_instance.SessionLocal()
        
        try:
            user = await _test_postgresql_crud(db)
            await _verify_postgresql_operations(db, user)
        finally:
            db.close()
    
    @skip_if_no_redis
    async def test_redis_operations(self):
        """Test Redis operations with real instance"""
        redis = RedisManager()
        
        try:
            await _test_redis_basic_operations(redis)
            await _test_redis_hash_operations(redis)
            await _test_redis_list_operations(redis)
            await _cleanup_redis_test_data(redis)
        finally:
            await redis.close()
    
    @skip_if_no_clickhouse
    async def test_clickhouse_operations(self):
        """Test ClickHouse operations with real database"""
        async with get_clickhouse_client() as clickhouse:
            try:
                await _create_clickhouse_test_table(clickhouse)
                await _insert_clickhouse_test_data(clickhouse)
                await _verify_clickhouse_data(clickhouse)
            finally:
                await _cleanup_clickhouse_test_table(clickhouse)
    
    @skip_if_no_database
    async def test_database_transactions(self):
        """Test database transaction handling"""
        db_instance = Database()
        db = db_instance.SessionLocal()
        
        try:
            await _test_transaction_commit(db)
            await _test_transaction_rollback(db)
        finally:
            db.close()
    
    @skip_if_no_redis
    async def test_redis_expiration(self):
        """Test Redis key expiration"""
        redis = RedisManager()
        
        try:
            await _test_key_expiration(redis)
        finally:
            await redis.close()
    
    @skip_if_no_clickhouse
    async def test_clickhouse_aggregations(self):
        """Test ClickHouse aggregation queries"""
        async with get_clickhouse_client() as clickhouse:
            try:
                await _test_clickhouse_aggregations(clickhouse)
            finally:
                await _cleanup_clickhouse_test_table(clickhouse)


async def _test_postgresql_crud(db) -> User:
    """Test PostgreSQL CRUD operations"""
    # Create user
    user = User(
        username="test_pg_user",
        email="test@pg.com",
        full_name="Test PG User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def _verify_postgresql_operations(db, user: User) -> None:
    """Verify PostgreSQL operations"""
    assert user.id is not None
    
    # Update user
    user.full_name = "Updated PG User"
    db.commit()
    db.refresh(user)
    assert user.full_name == "Updated PG User"
    
    _verify_user_query(db, user)
    _cleanup_user(db, user)


def _verify_user_query(db, user: User) -> None:
    """Verify user query operations"""
    found = db.query(User).filter(User.id == user.id).first()
    assert found is not None
    assert found.username == "test_pg_user"


def _cleanup_user(db, user: User) -> None:
    """Clean up test user"""
    db.delete(user)
    db.commit()


async def _test_redis_basic_operations(redis: RedisManager) -> None:
    """Test basic Redis operations"""
    # Set and get
    await redis.set("test_key", "test_value", expire=60)
    value = await redis.get("test_key")
    assert value == "test_value"


async def _test_redis_hash_operations(redis: RedisManager) -> None:
    """Test Redis hash operations"""
    await redis.hset("test_hash", "field1", "value1")
    await redis.hset("test_hash", "field2", "value2")
    hash_data = await redis.hgetall("test_hash")
    assert hash_data["field1"] == "value1"
    assert hash_data["field2"] == "value2"


async def _test_redis_list_operations(redis: RedisManager) -> None:
    """Test Redis list operations"""
    await redis.lpush("test_list", "item1")
    await redis.lpush("test_list", "item2")
    list_items = await redis.lrange("test_list", 0, -1)
    assert len(list_items) == 2


async def _cleanup_redis_test_data(redis: RedisManager) -> None:
    """Clean up Redis test data"""
    await redis.delete("test_key")
    await redis.delete("test_hash")
    await redis.delete("test_list")


async def _create_clickhouse_test_table(clickhouse) -> None:
    """Create ClickHouse test table"""
    await clickhouse.execute("""
        CREATE TABLE IF NOT EXISTS test_metrics (
            timestamp DateTime,
            metric String,
            value Float64
        ) ENGINE = MergeTree()
        ORDER BY timestamp
    """)


async def _insert_clickhouse_test_data(clickhouse) -> None:
    """Insert test data into ClickHouse"""
    data = [
        {"timestamp": datetime.now(), "metric": "cpu", "value": 75.5},
        {"timestamp": datetime.now(), "metric": "memory", "value": 82.3},
        {"timestamp": datetime.now(), "metric": "disk", "value": 45.7}
    ]
    await clickhouse.insert_batch("test_metrics", data)


async def _verify_clickhouse_data(clickhouse) -> None:
    """Verify ClickHouse data"""
    results = await clickhouse.query("""
        SELECT metric, avg(value) as avg_value
        FROM test_metrics
        GROUP BY metric
    """)
    
    assert len(results) == 3
    assert any(r["metric"] == "cpu" for r in results)


async def _cleanup_clickhouse_test_table(clickhouse) -> None:
    """Clean up ClickHouse test table"""
    await clickhouse.execute("DROP TABLE IF EXISTS test_metrics")


async def _test_transaction_commit(db) -> None:
    """Test transaction commit"""
    # Test transaction that should commit
    user = User(username="tx_test", email="tx@test.com", full_name="TX Test")
    db.add(user)
    db.commit()
    
    # Verify committed
    found = db.query(User).filter(User.username == "tx_test").first()
    assert found is not None
    
    # Cleanup
    db.delete(found)
    db.commit()


async def _test_transaction_rollback(db) -> None:
    """Test transaction rollback"""
    # Test transaction that should rollback
    user = User(username="rb_test", email="rb@test.com", full_name="RB Test")
    db.add(user)
    db.rollback()
    
    # Verify not committed
    found = db.query(User).filter(User.username == "rb_test").first()
    assert found is None


async def _test_key_expiration(redis: RedisManager) -> None:
    """Test Redis key expiration"""
    await redis.set("expire_test", "value", expire=1)
    
    # Key should exist initially
    value = await redis.get("expire_test")
    assert value == "value"
    
    # Wait for expiration and verify
    import asyncio
    await asyncio.sleep(2)
    expired_value = await redis.get("expire_test")
    assert expired_value is None


async def _test_clickhouse_aggregations(clickhouse) -> None:
    """Test ClickHouse aggregation functions"""
    await _create_clickhouse_test_table(clickhouse)
    await _insert_clickhouse_test_data(clickhouse)
    
    # Test various aggregations
    results = await clickhouse.query("""
        SELECT 
            count(*) as total_count,
            max(value) as max_value,
            min(value) as min_value
        FROM test_metrics
    """)
    
    assert len(results) == 1
    assert results[0]["total_count"] == 3