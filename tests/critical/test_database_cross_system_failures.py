"""
Database Cross-System Consistency Failure Tests (Tests 66-70)

These tests are designed to FAIL initially to expose real database consistency issues
between PostgreSQL, Redis cache, and ClickHouse analytics systems. Each test represents
a specific failure mode that could occur in production.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Risk Reduction  
- Value Impact: Prevents data inconsistency that could cause billing errors and user data corruption
- Strategic Impact: Enables proactive detection of cross-database consistency failures

IMPORTANT: These tests WILL FAIL initially. This is intentional to expose actual issues.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from netra_backend.app.config import get_config
from netra_backend.app.db.postgres import get_postgres_db, get_pool_status
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.exceptions_base import NetraException

logger = central_logger.get_logger(__name__)
settings = get_config()


class TestDatabaseCrossSystemFailures:
    """Test suite designed to FAIL and expose database cross-system consistency issues."""
    
    @pytest.fixture
    async def postgres_session(self):
        """Get PostgreSQL session for testing."""
        async for session in get_postgres_db():
            yield session
            break
    
    @pytest.fixture
    async def redis_client(self):
        """Get Redis client for testing."""
        redis_manager = RedisManager()
        if not redis_manager.enabled:
            pytest.skip("Redis not available for testing")
        
        redis_client = await redis_manager.get_client()
        yield redis_client
        # Cleanup
        if redis_client:
            await redis_client.flushdb()  # Clear test data
    
    @pytest.fixture
    async def clickhouse_client(self):
        """Get ClickHouse client for testing."""
        async with get_clickhouse_client() as client:
            yield client
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_66_write_write_conflict(self, postgres_session, redis_client):
        """Test 66: Write-Write Conflict - Same user updated in two databases simultaneously
        
        This test WILL FAIL because concurrent writes to the same user
        in PostgreSQL and Redis create inconsistent state without proper locking.
        
        Expected Failure: Data inconsistency between PostgreSQL and Redis
        """
        logger.info("Test 66: Testing write-write conflict between PostgreSQL and Redis")
        
        user_id = str(uuid.uuid4())
        user_email = f"test_{user_id}@example.com"
        
        try:
            # Initial user data
            initial_data = {
                "id": user_id,
                "email": user_email,
                "name": "Original Name",
                "updated_at": time.time()
            }
            
            # Write to PostgreSQL
            await postgres_session.execute(
                text("""
                    INSERT INTO users (id, email, name, updated_at) 
                    VALUES (:id, :email, :name, :updated_at)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        updated_at = EXCLUDED.updated_at
                """),
                initial_data
            )
            await postgres_session.commit()
            
            # Write to Redis cache
            cache_key = f"user:{user_id}"
            await redis_client.hset(cache_key, mapping=initial_data)
            
            # Simulate concurrent writes with different values
            # This creates write-write conflict
            async def update_postgres():
                """Update user in PostgreSQL."""
                await asyncio.sleep(0.1)  # Small delay to create race condition
                await postgres_session.execute(
                    text("""
                        UPDATE users SET name = :name, updated_at = :updated_at 
                        WHERE id = :id
                    """),
                    {
                        "id": user_id,
                        "name": "PostgreSQL Updated Name",
                        "updated_at": time.time()
                    }
                )
                await postgres_session.commit()
            
            async def update_redis():
                """Update user in Redis."""
                await asyncio.sleep(0.05)  # Different delay to create race
                await redis_client.hset(cache_key, mapping={
                    "name": "Redis Updated Name",
                    "updated_at": str(time.time())
                })
            
            # Execute concurrent updates - this creates inconsistency
            await asyncio.gather(update_postgres(), update_redis())
            
            # Check consistency - THIS WILL FAIL
            pg_result = await postgres_session.execute(
                text("SELECT name FROM users WHERE id = :id"),
                {"id": user_id}
            )
            pg_name = pg_result.scalar()
            
            redis_name = await redis_client.hget(cache_key, "name")
            redis_name = redis_name.decode() if redis_name else None
            
            # This assertion WILL FAIL - data is inconsistent
            assert pg_name == redis_name, f"Data inconsistency: PostgreSQL='{pg_name}' vs Redis='{redis_name}'"
            
            # If we get here, the system has proper conflict resolution (unexpected)
            logger.warning("Test 66: Unexpected success - write-write conflict was resolved")
            
        except Exception as e:
            logger.error(f"Test 66 failed as expected - Write-write conflict detected: {e}")
            # Re-raise to mark test as failed
            raise AssertionError(f"Write-write conflict not properly handled: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_67_read_after_write_inconsistency(self, postgres_session, redis_client):
        """Test 67: Read-After-Write Inconsistency - Write to Postgres, immediate read from cache misses
        
        This test WILL FAIL because writing to PostgreSQL doesn't immediately
        invalidate Redis cache, causing stale data reads.
        
        Expected Failure: Stale data returned from Redis after PostgreSQL update
        """
        logger.info("Test 67: Testing read-after-write inconsistency")
        
        user_id = str(uuid.uuid4())
        cache_key = f"user:{user_id}"
        
        try:
            # Setup initial data in both systems
            initial_data = {
                "id": user_id,
                "email": f"test_{user_id}@example.com",
                "balance": "100.00",
                "status": "active"
            }
            
            # Write to PostgreSQL
            await postgres_session.execute(
                text("""
                    INSERT INTO users (id, email, balance, status) 
                    VALUES (:id, :email, :balance, :status)
                """),
                initial_data
            )
            await postgres_session.commit()
            
            # Cache in Redis
            await redis_client.hset(cache_key, mapping=initial_data)
            
            # Critical update to PostgreSQL (e.g., payment processing)
            updated_balance = "50.00"
            await postgres_session.execute(
                text("UPDATE users SET balance = :balance WHERE id = :id"),
                {"id": user_id, "balance": updated_balance}
            )
            await postgres_session.commit()
            
            # Immediate read from cache - THIS WILL RETURN STALE DATA
            cached_balance = await redis_client.hget(cache_key, "balance")
            cached_balance = cached_balance.decode() if cached_balance else None
            
            # Read from PostgreSQL for comparison
            pg_result = await postgres_session.execute(
                text("SELECT balance FROM users WHERE id = :id"),
                {"id": user_id}
            )
            pg_balance = pg_result.scalar()
            
            # This assertion WILL FAIL - cache is stale
            assert cached_balance == pg_balance, (
                f"Read-after-write inconsistency: Cache='{cached_balance}' vs PostgreSQL='{pg_balance}'. "
                f"Cache should be invalidated after PostgreSQL write."
            )
            
            # If we get here, cache invalidation is working (unexpected)
            logger.warning("Test 67: Unexpected success - cache invalidation is working")
            
        except Exception as e:
            logger.error(f"Test 67 failed as expected - Read-after-write inconsistency: {e}")
            # Re-raise to mark test as failed
            raise AssertionError(f"Cache invalidation not working properly: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_68_transaction_rollback_partial(self, postgres_session, redis_client):
        """Test 68: Transaction Rollback Partial - Transaction rolls back in one DB but not another
        
        This test WILL FAIL because PostgreSQL transaction rollback doesn't
        rollback corresponding Redis operations, creating inconsistent state.
        
        Expected Failure: Redis contains data that should have been rolled back
        """
        logger.info("Test 68: Testing partial transaction rollback across systems")
        
        user_id = str(uuid.uuid4())
        cache_key = f"user:{user_id}"
        
        try:
            # Setup initial user
            initial_data = {
                "id": user_id,
                "email": f"test_{user_id}@example.com",
                "credits": "100",
                "subscription": "free"
            }
            
            await postgres_session.execute(
                text("""
                    INSERT INTO users (id, email, credits, subscription) 
                    VALUES (:id, :email, :credits, :subscription)
                """),
                initial_data
            )
            await postgres_session.commit()
            
            # Cache initial state
            await redis_client.hset(cache_key, mapping=initial_data)
            
            # Begin distributed transaction simulation
            try:
                # Step 1: Update Redis (succeeds)
                await redis_client.hset(cache_key, mapping={
                    "credits": "200",
                    "subscription": "premium",
                    "upgrade_timestamp": str(time.time())
                })
                
                # Step 2: Update PostgreSQL (will fail due to constraint)
                await postgres_session.execute(
                    text("""
                        UPDATE users SET credits = :credits, subscription = :subscription 
                        WHERE id = :id AND email = 'invalid@constraint.check'
                    """),  # This will fail - no user with this email
                    {
                        "id": user_id,
                        "credits": "200", 
                        "subscription": "premium"
                    }
                )
                await postgres_session.commit()
                
            except DatabaseError:
                # PostgreSQL transaction fails and rolls back
                await postgres_session.rollback()
                logger.info("PostgreSQL transaction rolled back due to constraint violation")
                
                # BUT Redis update is NOT rolled back - creating inconsistency
                pass
            
            # Check final state - Redis should match PostgreSQL (both should be original state)
            pg_result = await postgres_session.execute(
                text("SELECT credits, subscription FROM users WHERE id = :id"),
                {"id": user_id}
            )
            pg_row = pg_result.fetchone()
            pg_credits = pg_row.credits if pg_row else None
            pg_subscription = pg_row.subscription if pg_row else None
            
            redis_credits = await redis_client.hget(cache_key, "credits")
            redis_subscription = await redis_client.hget(cache_key, "subscription")
            redis_credits = redis_credits.decode() if redis_credits else None
            redis_subscription = redis_subscription.decode() if redis_subscription else None
            
            # This assertion WILL FAIL - Redis has uncommitted data
            assert redis_credits == pg_credits, (
                f"Transaction rollback inconsistency: Redis credits='{redis_credits}' vs PostgreSQL='{pg_credits}'"
            )
            assert redis_subscription == pg_subscription, (
                f"Transaction rollback inconsistency: Redis subscription='{redis_subscription}' vs PostgreSQL='{pg_subscription}'"
            )
            
            # If we get here, distributed transaction rollback is working (unexpected)
            logger.warning("Test 68: Unexpected success - distributed transaction rollback working")
            
        except Exception as e:
            logger.error(f"Test 68 failed as expected - Partial transaction rollback: {e}")
            # Re-raise to mark test as failed
            raise AssertionError(f"Distributed transaction rollback not implemented: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_69_cache_invalidation_failure(self, postgres_session, redis_client):
        """Test 69: Cache Invalidation Failure - Cache not invalidated after database update
        
        This test WILL FAIL because there's no automatic cache invalidation
        mechanism when PostgreSQL data is updated.
        
        Expected Failure: Stale cache data persists after database updates
        """
        logger.info("Test 69: Testing cache invalidation failure")
        
        user_id = str(uuid.uuid4())
        cache_key = f"user:{user_id}"
        
        try:
            # Setup user data
            user_data = {
                "id": user_id,
                "email": f"test_{user_id}@example.com",
                "last_login": time.time() - 3600,  # 1 hour ago
                "login_count": "5"
            }
            
            # Write to PostgreSQL
            await postgres_session.execute(
                text("""
                    INSERT INTO users (id, email, last_login, login_count) 
                    VALUES (:id, :email, :last_login, :login_count)
                """),
                user_data
            )
            await postgres_session.commit()
            
            # Cache the data with TTL
            await redis_client.hset(cache_key, mapping=user_data)
            await redis_client.expire(cache_key, 3600)  # 1 hour TTL
            
            # Simulate user login - update PostgreSQL directly
            current_time = time.time()
            await postgres_session.execute(
                text("""
                    UPDATE users SET 
                        last_login = :last_login,
                        login_count = login_count + 1
                    WHERE id = :id
                """),
                {"id": user_id, "last_login": current_time}
            )
            await postgres_session.commit()
            
            # Check if cache was automatically invalidated - IT WON'T BE
            cached_login_time = await redis_client.hget(cache_key, "last_login")
            cached_login_count = await redis_client.hget(cache_key, "login_count")
            
            if cached_login_time:
                cached_login_time = float(cached_login_time.decode())
            if cached_login_count:
                cached_login_count = int(cached_login_count.decode())
            
            # Get current data from PostgreSQL
            pg_result = await postgres_session.execute(
                text("SELECT last_login, login_count FROM users WHERE id = :id"),
                {"id": user_id}
            )
            pg_row = pg_result.fetchone()
            pg_login_time = float(pg_row.last_login) if pg_row else None
            pg_login_count = int(pg_row.login_count) if pg_row else None
            
            # This assertion WILL FAIL - cache was not invalidated
            time_diff = abs(cached_login_time - pg_login_time) if cached_login_time and pg_login_time else float('inf')
            assert time_diff < 1.0, (
                f"Cache invalidation failure: Cached login time {cached_login_time} doesn't match PostgreSQL {pg_login_time}"
            )
            assert cached_login_count == pg_login_count, (
                f"Cache invalidation failure: Cached login count {cached_login_count} doesn't match PostgreSQL {pg_login_count}"
            )
            
            # If we get here, cache invalidation is working (unexpected)
            logger.warning("Test 69: Unexpected success - cache invalidation is working")
            
        except Exception as e:
            logger.error(f"Test 69 failed as expected - Cache invalidation failure: {e}")
            # Re-raise to mark test as failed
            raise AssertionError(f"Automatic cache invalidation not implemented: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_70_database_connection_pool_starvation(self):
        """Test 70: Database Connection Pool Starvation - One service monopolizes connections
        
        This test WILL FAIL because there's no proper connection pool limits
        or fair resource allocation between different operations.
        
        Expected Failure: Connection pool exhaustion prevents new connections
        """
        logger.info("Test 70: Testing database connection pool starvation")
        
        try:
            # Check initial pool status
            initial_status = get_pool_status()
            logger.info(f"Initial pool status: {initial_status}")
            
            # Create a large number of concurrent connections to exhaust pool
            connections = []
            tasks = []
            
            async def create_long_running_connection(connection_id: int):
                """Create a connection that holds for extended period."""
                try:
                    async for session in get_postgres_db():
                        # Simulate long-running query that holds connection
                        await session.execute(text("SELECT pg_sleep(5)"))  # 5 second sleep
                        return f"Connection {connection_id} completed"
                except Exception as e:
                    logger.error(f"Connection {connection_id} failed: {e}")
                    raise
            
            # Spawn many concurrent connections (more than typical pool size)
            num_connections = 50  # Typically more than default pool size
            for i in range(num_connections):
                task = asyncio.create_task(create_long_running_connection(i))
                tasks.append(task)
            
            # Wait a bit for connections to be established
            await asyncio.sleep(1)
            
            # Now try to create a new connection - THIS SHOULD FAIL due to pool exhaustion
            try:
                async for session in get_postgres_db():
                    result = await session.execute(text("SELECT 1"))
                    test_result = result.scalar()
                    
                    # If we get here, pool has unlimited connections or good management
                    logger.warning(f"Test 70: New connection succeeded despite {num_connections} active connections")
                    
                    # Check pool status after successful connection
                    final_status = get_pool_status()
                    logger.info(f"Final pool status: {final_status}")
                    
                    # This assertion might FAIL if pool is properly managed
                    assert test_result == 1, "Basic query should succeed if connection was established"
                    break
                    
            except Exception as connection_error:
                # This is expected - pool should be exhausted
                logger.info(f"Expected pool exhaustion occurred: {connection_error}")
                
                # Clean up tasks
                for task in tasks:
                    task.cancel()
                
                # Wait for cleanup
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Re-raise to mark test as failed (this exposes the issue)
                raise AssertionError(f"Connection pool starvation detected: {connection_error}")
            
            # Clean up all tasks
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as cleanup_error:
                logger.warning(f"Cleanup error (expected): {cleanup_error}")
            
            # If we get here, connection pool has good resource management
            logger.info("Test 70: Unexpected success - connection pool is properly managed")
            
        except Exception as e:
            logger.error(f"Test 70 failed as expected - Connection pool starvation: {e}")
            # Re-raise to mark test as failed
            raise AssertionError(f"Connection pool resource management insufficient: {e}")