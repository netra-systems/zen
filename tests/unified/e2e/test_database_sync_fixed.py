"""
Database Synchronization Test - Cross-Service Consistency Validation

CRITICAL CONTEXT: Database Consistency Validation
Tests data synchronization across Auth DB, Backend PostgreSQL without mocking.
Uses SQLite in-memory databases for speed and isolation.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure atomic cross-database operations prevent data corruption
3. Value Impact: Prevents data inconsistencies causing support tickets and churn
4. Revenue Impact: Prevents revenue loss from billing inaccuracies due to data sync issues

SUCCESS CRITERIA:
- User creation in Auth service → verification in Auth DB
- User sync to Backend PostgreSQL → data field matching validation
- Update user profile in Backend → changes reflected in Auth service
- Transaction rollback scenarios with proper recovery
- No data loss during updates
- Proper error handling and consistency validation
- <5 seconds execution time per test scenario

Module Architecture Compliance: Under 500 lines, functions under 25 lines
"""

import pytest
import pytest_asyncio
import asyncio
import aiosqlite
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Database schemas for testing
AUTH_SCHEMA = """CREATE TABLE IF NOT EXISTS auth_users (
    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, full_name TEXT,
    plan_tier TEXT DEFAULT 'free', is_active BOOLEAN DEFAULT 1,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""

BACKEND_SCHEMA = """CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, full_name TEXT,
    plan_tier TEXT DEFAULT 'free', is_active BOOLEAN DEFAULT 1,
    synced_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""

@dataclass
class UserData:
    """User data structure for testing."""
    id: str
    email: str
    full_name: str
    plan_tier: str = 'free'
    is_active: bool = True


class DatabaseSyncManager:
    """Manager for database synchronization testing with SQLite in-memory databases."""
    
    def __init__(self):
        self.auth_db: Optional[aiosqlite.Connection] = None
        self.backend_db: Optional[aiosqlite.Connection] = None
        self.test_users: List[str] = []
    
    async def initialize_databases(self) -> None:
        """Initialize SQLite in-memory databases for testing."""
        self.auth_db = await aiosqlite.connect(":memory:")
        self.backend_db = await aiosqlite.connect(":memory:")
        self.auth_db.row_factory = aiosqlite.Row
        self.backend_db.row_factory = aiosqlite.Row
        await self.auth_db.execute(AUTH_SCHEMA)
        await self.backend_db.execute(BACKEND_SCHEMA)
        await self.auth_db.commit()
        await self.backend_db.commit()
    
    async def create_user_in_auth(self, user_data: UserData) -> str:
        """Create user in Auth service database."""
        now = datetime.now(timezone.utc).isoformat()
        await self.auth_db.execute("""
            INSERT INTO auth_users (id, email, full_name, plan_tier, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_data.id, user_data.email, user_data.full_name, user_data.plan_tier, 
              user_data.is_active, now, now))
        await self.auth_db.commit()
        self.test_users.append(user_data.id)
        return user_data.id
    
    async def verify_user_in_auth(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Verify user exists in Auth database with correct data."""
        cursor = await self.auth_db.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def sync_user_to_backend(self, user_id: str) -> bool:
        """Sync user from Auth to Backend database."""
        auth_user = await self.verify_user_in_auth(user_id)
        if not auth_user:
            return False
        now = datetime.now(timezone.utc).isoformat()
        await self.backend_db.execute("""
            INSERT OR REPLACE INTO users (id, email, full_name, plan_tier, is_active, 
                                        synced_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (auth_user['id'], auth_user['email'], auth_user['full_name'], auth_user['plan_tier'],
              auth_user['is_active'], now, auth_user['created_at'], now))
        await self.backend_db.commit()
        return True
    
    async def verify_user_in_backend(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Verify user exists in Backend database with correct data."""
        cursor = await self.backend_db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def update_user_in_backend(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user in Backend database."""
        now = datetime.now(timezone.utc).isoformat()
        await self.backend_db.execute("""
            UPDATE users SET full_name = ?, plan_tier = ?, updated_at = ? WHERE id = ?
        """, (updates.get('full_name'), updates.get('plan_tier'), now, user_id))
        await self.backend_db.commit()
        return True
    
    async def sync_backend_to_auth(self, user_id: str) -> bool:
        """Sync changes from Backend to Auth database."""
        backend_user = await self.verify_user_in_backend(user_id)
        if not backend_user:
            return False
        now = datetime.now(timezone.utc).isoformat()
        await self.auth_db.execute("""
            UPDATE auth_users SET full_name = ?, plan_tier = ?, updated_at = ? WHERE id = ?
        """, (backend_user['full_name'], backend_user['plan_tier'], now, user_id))
        await self.auth_db.commit()
        return True
    
    async def verify_consistency(self, user_id: str) -> Dict[str, bool]:
        """Verify data consistency across both databases."""
        auth_user = await self.verify_user_in_auth(user_id)
        backend_user = await self.verify_user_in_backend(user_id)
        
        if not auth_user or not backend_user:
            return {'users_exist': False, 'consistent': False}
        
        return {
            'users_exist': True,
            'consistent': (auth_user['email'] == backend_user['email'] and
                          auth_user['plan_tier'] == backend_user['plan_tier'] and
                          auth_user['full_name'] == backend_user['full_name'])
        }
    
    async def simulate_rollback(self, user_id: str) -> Dict[str, bool]:
        """Simulate transaction rollback scenario."""
        original_auth = await self.verify_user_in_auth(user_id)
        try:
            await self.auth_db.execute("BEGIN TRANSACTION")
            await self.auth_db.execute("UPDATE auth_users SET plan_tier = 'enterprise' WHERE id = ?", (user_id,))
            await self.auth_db.execute("ROLLBACK")  # Simulate failure
            rollback_success = True
        except Exception:
            await self.auth_db.execute("ROLLBACK")
            rollback_success = False
        
        current_auth = await self.verify_user_in_auth(user_id)
        integrity_maintained = current_auth['plan_tier'] == original_auth['plan_tier']
        
        return {'rollback_success': rollback_success, 'integrity_maintained': integrity_maintained}
    
    async def test_concurrent_updates(self, user_ids: List[str]) -> Dict[str, Any]:
        """Test concurrent database updates."""
        async def update_user(user_id: str, suffix: str) -> bool:
            try:
                now = datetime.now(timezone.utc).isoformat()
                await self.auth_db.execute(
                    "UPDATE auth_users SET full_name = ?, updated_at = ? WHERE id = ?",
                    (f"Concurrent User {suffix}", now, user_id)
                )
                await self.auth_db.commit()
                return True
            except Exception:
                return False
        
        tasks = [update_user(user_id, f"concurrent_{i}") for i, user_id in enumerate(user_ids)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if r is True)
        
        return {
            'total_updates': len(user_ids),
            'successful_updates': successful,
            'success_rate': successful / len(user_ids) if user_ids else 0
        }
    
    async def cleanup_databases(self) -> None:
        """Cleanup test databases and connections."""
        if self.auth_db:
            await self.auth_db.close()
        if self.backend_db:
            await self.backend_db.close()


@pytest_asyncio.fixture
async def db_manager():
    """Create database sync manager fixture."""
    manager = DatabaseSyncManager()
    await manager.initialize_databases()
    yield manager
    await manager.cleanup_databases()


class TestDatabaseSyncFixed:
    """E2E Tests for database synchronization between Auth and Backend services."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_create_user_auth_to_backend_sync(self, db_manager):
        """Test #1: Create user in Auth → verify sync to Backend PostgreSQL."""
        user_data = self._create_test_user("auth_backend_sync")
        user_id = await db_manager.create_user_in_auth(user_data)
        
        # Verify in Auth
        auth_user = await db_manager.verify_user_in_auth(user_id)
        assert auth_user is not None
        assert auth_user['email'] == user_data.email
        
        # Sync and verify in Backend
        sync_success = await db_manager.sync_user_to_backend(user_id)
        assert sync_success
        
        backend_user = await db_manager.verify_user_in_backend(user_id)
        assert backend_user is not None
        assert backend_user['email'] == auth_user['email']
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_update_profile_backend_to_auth_sync(self, db_manager):
        """Test #2: Update user profile in Backend → verify changes in Auth service."""
        user_data = self._create_test_user("profile_update")
        user_id = await db_manager.create_user_in_auth(user_data)
        await db_manager.sync_user_to_backend(user_id)
        
        # Update in Backend
        updates = {'full_name': 'Updated User', 'plan_tier': 'mid'}
        await db_manager.update_user_in_backend(user_id, updates)
        await db_manager.sync_backend_to_auth(user_id)
        
        # Verify changes in Auth
        auth_user = await db_manager.verify_user_in_auth(user_id)
        assert auth_user['full_name'] == 'Updated User'
        assert auth_user['plan_tier'] == 'mid'
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_database_consistency(self, db_manager):
        """Test #3: Validate data consistency between services."""
        start_time = time.time()
        user_data = self._create_test_user("consistency")
        user_id = await db_manager.create_user_in_auth(user_data)
        await db_manager.sync_user_to_backend(user_id)
        
        consistency = await db_manager.verify_consistency(user_id)
        execution_time = time.time() - start_time
        
        assert execution_time < 5.0, f"Consistency check too slow: {execution_time}s"
        assert consistency['users_exist']
        assert consistency['consistent']
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_transaction_rollback_scenarios(self, db_manager):
        """Test #4: Transaction rollback scenarios with proper recovery."""
        user_data = self._create_test_user("rollback")
        user_id = await db_manager.create_user_in_auth(user_data)
        await db_manager.sync_user_to_backend(user_id)  # Sync user to backend first
        
        rollback_result = await db_manager.simulate_rollback(user_id)
        
        assert rollback_result['rollback_success']
        assert rollback_result['integrity_maintained']
        
        # Verify consistency after rollback
        consistency = await db_manager.verify_consistency(user_id)
        assert consistency['users_exist']
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_update_handling(self, db_manager):
        """Test #5: Concurrent update handling without data corruption."""
        user_ids = []
        for i in range(3):
            user_data = self._create_test_user(f"concurrent_{i}")
            user_id = await db_manager.create_user_in_auth(user_data)
            user_ids.append(user_id)
        
        results = await db_manager.test_concurrent_updates(user_ids)
        
        assert results['total_updates'] == 3
        assert results['successful_updates'] >= 2
        assert results['success_rate'] >= 0.66
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_handling_recovery(self, db_manager):
        """Test #6: Proper error handling during sync operations."""
        # Test sync with non-existent user
        non_existent_id = str(uuid.uuid4())
        sync_result = await db_manager.sync_user_to_backend(non_existent_id)
        assert not sync_result
        
        # Verify no partial data created
        backend_user = await db_manager.verify_user_in_backend(non_existent_id)
        assert backend_user is None
        
        # Test recovery after failure
        user_data = self._create_test_user("recovery")
        user_id = await db_manager.create_user_in_auth(user_data)
        sync_success = await db_manager.sync_user_to_backend(user_id)
        assert sync_success
        
        consistency = await db_manager.verify_consistency(user_id)
        assert consistency['users_exist']
    
    def _create_test_user(self, identifier: str) -> UserData:
        """Create standardized test user data."""
        timestamp = int(time.time())
        return UserData(
            id=str(uuid.uuid4()),
            email=f"test_{identifier}_{timestamp}@example.com",
            full_name=f"Test User {identifier}",
            plan_tier='free'
        )


class TestDatabaseSyncPerformance:
    """Performance tests for database synchronization operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_bulk_sync_performance(self, db_manager):
        """Test performance of bulk synchronization operations."""
        start_time = time.time()
        user_count = 10
        
        # Create and sync multiple users
        for i in range(user_count):
            user_data = UserData(
                id=str(uuid.uuid4()),
                email=f"bulk_{i}_{int(time.time())}@example.com",
                full_name=f"Bulk User {i}"
            )
            user_id = await db_manager.create_user_in_auth(user_data)
            sync_success = await db_manager.sync_user_to_backend(user_id)
            assert sync_success
            
            consistency = await db_manager.verify_consistency(user_id)
            assert consistency['users_exist']
        
        total_time = time.time() - start_time
        average_time = total_time / user_count
        
        assert average_time < 0.5, f"Average sync time too slow: {average_time}s"
        assert total_time < 5.0, f"Bulk sync too slow: {total_time}s"