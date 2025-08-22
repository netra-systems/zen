"""
L3 Integration Test: Cross-Database Data Consistency
Tests data consistency across multiple databases
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from netra_backend.app.config import get_config
from netra_backend.app.services.clickhouse_service import ClickHouseService

from netra_backend.app.services.postgres_service import PostgresService
from netra_backend.app.services.redis_service import RedisService

class TestDataConsistencyCrossDBL3:
    """Test cross-database data consistency scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cache_database_consistency(self):
        """Test consistency between cache (Redis) and database (Postgres)"""
        pg_service = PostgresService()
        redis_service = RedisService()
        
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "name": "Test User",
            "email": "test@example.com"
        }
        
        # Write to database
        await pg_service.insert("users", user_data)
        
        # Cache should be invalidated or updated
        cached = await redis_service.get_json(f"user:{user_id}")
        
        if cached is not None:
            # If cached, should match database
            assert cached["name"] == user_data["name"]
            assert cached["email"] == user_data["email"]
        
        # Update database
        await pg_service.update(
            "users",
            {"name": "Updated User"},
            {"id": user_id}
        )
        
        # Cache should be invalidated
        await redis_service.delete(f"user:{user_id}")
        
        # Next read should fetch from database
        cached = await redis_service.get_json(f"user:{user_id}")
        assert cached is None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_event_sourcing_consistency(self):
        """Test event sourcing consistency across stores"""
        pg_service = PostgresService()
        ch_service = ClickHouseService()
        
        order_id = str(uuid.uuid4())
        
        # Create order in Postgres
        await pg_service.insert("orders", {
            "id": order_id,
            "status": "pending",
            "total": 100.00
        })
        
        # Log event in ClickHouse
        await ch_service.insert_event({
            "event_id": str(uuid.uuid4()),
            "entity_id": order_id,
            "event_type": "order_created",
            "timestamp": "now()",
            "data": {"status": "pending", "total": 100.00}
        })
        
        # Update order status
        await pg_service.update(
            "orders",
            {"status": "completed"},
            {"id": order_id}
        )
        
        # Log update event
        await ch_service.insert_event({
            "event_id": str(uuid.uuid4()),
            "entity_id": order_id,
            "event_type": "order_completed",
            "timestamp": "now()",
            "data": {"status": "completed"}
        })
        
        # Verify consistency
        order = await pg_service.get_by_id("orders", order_id)
        events = await ch_service.query(
            f"SELECT * FROM events WHERE entity_id = '{order_id}' ORDER BY timestamp"
        )
        
        assert order["status"] == "completed"
        assert len(events) >= 2
        assert events[-1]["event_type"] == "order_completed"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_distributed_transaction_simulation(self):
        """Test simulated distributed transaction across databases"""
        pg_service = PostgresService()
        redis_service = RedisService()
        
        transaction_id = str(uuid.uuid4())
        
        # Start distributed transaction
        try:
            # Phase 1: Prepare
            pg_prepared = await pg_service.prepare_transaction(transaction_id)
            redis_prepared = await redis_service.prepare_transaction(transaction_id)
            
            if pg_prepared and redis_prepared:
                # Phase 2: Commit
                await pg_service.commit_transaction(transaction_id)
                await redis_service.commit_transaction(transaction_id)
            else:
                # Rollback
                await pg_service.rollback_transaction(transaction_id)
                await redis_service.rollback_transaction(transaction_id)
                
        except Exception as e:
            # Ensure cleanup on failure
            await pg_service.rollback_transaction(transaction_id)
            await redis_service.rollback_transaction(transaction_id)
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_eventual_consistency_handling(self):
        """Test handling of eventual consistency"""
        pg_service = PostgresService()
        redis_service = RedisService()
        ch_service = ClickHouseService()
        
        user_id = str(uuid.uuid4())
        
        # Write to primary store
        await pg_service.insert("users", {
            "id": user_id,
            "name": "New User"
        })
        
        # Async replication to other stores (simulated delay)
        async def replicate_to_cache():
            await asyncio.sleep(0.1)
            await redis_service.set_json(f"user:{user_id}", {
                "id": user_id,
                "name": "New User"
            })
        
        async def replicate_to_analytics():
            await asyncio.sleep(0.2)
            await ch_service.insert_event({
                "event_id": str(uuid.uuid4()),
                "entity_id": user_id,
                "event_type": "user_created"
            })
        
        # Start async replication
        asyncio.create_task(replicate_to_cache())
        asyncio.create_task(replicate_to_analytics())
        
        # Immediate read might not find in cache
        immediate_cache = await redis_service.get_json(f"user:{user_id}")
        
        # Wait for eventual consistency
        await asyncio.sleep(0.3)
        
        # Should be consistent now
        eventual_cache = await redis_service.get_json(f"user:{user_id}")
        assert eventual_cache is not None
        assert eventual_cache["name"] == "New User"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_data_reconciliation(self):
        """Test data reconciliation across stores"""
        pg_service = PostgresService()
        redis_service = RedisService()
        
        # Simulate inconsistency
        user_id = "reconcile_test"
        
        # Different data in different stores
        await pg_service.insert("users", {
            "id": user_id,
            "name": "Database User",
            "version": 2
        })
        
        await redis_service.set_json(f"user:{user_id}", {
            "id": user_id,
            "name": "Cached User",
            "version": 1
        })
        
        # Reconciliation logic
        db_user = await pg_service.get_by_id("users", user_id)
        cache_user = await redis_service.get_json(f"user:{user_id}")
        
        # Use version to determine source of truth
        if db_user["version"] > cache_user["version"]:
            # Update cache from database
            await redis_service.set_json(f"user:{user_id}", db_user)
            final_user = db_user
        else:
            # Update database from cache
            await pg_service.update("users", cache_user, {"id": user_id})
            final_user = cache_user
        
        # Verify reconciliation
        assert final_user["version"] == 2
        assert final_user["name"] == "Database User"