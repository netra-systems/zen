"""
L3 Integration Test: PostgreSQL Data Persistence
Tests PostgreSQL data persistence and integrity
"""

import pytest
import asyncio
import asyncpg
from unittest.mock import patch, AsyncMock
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.postgres_service import PostgresService
from netra_backend.app.config import settings
import uuid

# Add project root to path


class TestDataPersistencePostgresL3:
    """Test PostgreSQL data persistence scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_data_insert_and_retrieval(self):
        """Test data insertion and retrieval"""
        pg_service = PostgresService()
        
        test_data = {
            "id": str(uuid.uuid4()),
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "NOW()"
        }
        
        # Insert data
        inserted = await pg_service.insert(
            table="users",
            data=test_data
        )
        
        assert inserted is not None
        
        # Retrieve data
        retrieved = await pg_service.get_by_id(
            table="users",
            id=test_data["id"]
        )
        
        assert retrieved is not None
        assert retrieved["name"] == "Test User"
        assert retrieved["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_transaction_commit_rollback(self):
        """Test transaction commit and rollback"""
        pg_service = PostgresService()
        
        # Test successful transaction
        async with pg_service.transaction() as tx:
            await tx.execute("INSERT INTO users (id, name) VALUES ($1, $2)", "1", "User1")
            await tx.execute("INSERT INTO users (id, name) VALUES ($1, $2)", "2", "User2")
            # Auto-commit on successful exit
        
        # Verify both inserted
        count = await pg_service.count("users", where="id IN ('1', '2')")
        assert count == 2
        
        # Test rollback on error
        try:
            async with pg_service.transaction() as tx:
                await tx.execute("INSERT INTO users (id, name) VALUES ($1, $2)", "3", "User3")
                raise Exception("Simulated error")
        except:
            pass
        
        # User3 should not exist
        exists = await pg_service.exists("users", id="3")
        assert exists is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_bulk_insert_performance(self):
        """Test bulk insert performance"""
        pg_service = PostgresService()
        
        # Prepare bulk data
        bulk_data = [
            {"id": str(uuid.uuid4()), "name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(100)
        ]
        
        # Bulk insert
        start_time = asyncio.get_event_loop().time()
        inserted_count = await pg_service.bulk_insert(
            table="users",
            data=bulk_data
        )
        duration = asyncio.get_event_loop().time() - start_time
        
        assert inserted_count == 100
        assert duration < 5  # Should be fast
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_data_update_consistency(self):
        """Test data update consistency"""
        pg_service = PostgresService()
        
        user_id = str(uuid.uuid4())
        
        # Insert initial data
        await pg_service.insert(
            table="users",
            data={"id": user_id, "name": "Initial", "version": 1}
        )
        
        # Concurrent updates
        async def update_name(new_name):
            return await pg_service.update(
                table="users",
                data={"name": new_name, "version": 2},
                where={"id": user_id}
            )
        
        tasks = [update_name(f"Name{i}") for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check final state
        final = await pg_service.get_by_id("users", user_id)
        assert final["version"] == 2
        assert final["name"] in [f"Name{i}" for i in range(5)]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_data_deletion_cascade(self):
        """Test cascading deletion"""
        pg_service = PostgresService()
        
        user_id = str(uuid.uuid4())
        
        # Insert parent and child records
        await pg_service.insert("users", {"id": user_id, "name": "Parent"})
        await pg_service.insert("user_sessions", {"id": "s1", "user_id": user_id})
        await pg_service.insert("user_sessions", {"id": "s2", "user_id": user_id})
        
        # Delete parent (should cascade)
        deleted = await pg_service.delete("users", where={"id": user_id})
        
        assert deleted == 1
        
        # Check children are deleted
        sessions = await pg_service.count("user_sessions", where={"user_id": user_id})
        assert sessions == 0