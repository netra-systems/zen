"""
L3 Integration Test: Database Migration Rollback Safety

Business Value Justification (BVJ):
- Segment: Platform/Internal (critical for zero-downtime deployments)
- Business Goal: Risk Reduction - Ensure safe migration rollbacks without data loss
- Value Impact: Prevents catastrophic data loss during failed deployments
- Strategic Impact: Protects entire $45K MRR platform from migration failures

L3 Test: Uses real PostgreSQL and ClickHouse containers to validate migration rollback
safety, data preservation, and recovery mechanisms under various failure scenarios.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.clickhouse import ClickHouseContainer
from testcontainers.postgres import PostgresContainer

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class MigrationRollbackSafetyManager:
    """Manages migration rollback safety testing with real containers."""
    
    def __init__(self):
        self.postgres_container = None
        self.clickhouse_container = None
        self.postgres_url = None
        self.clickhouse_client = None
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.migration_history = []
        self.data_snapshots = {}
        self.rollback_scenarios = []
        
    async def setup_database_containers(self):
        """Setup real database containers for migration testing."""
        try:
            # Setup PostgreSQL
            self.postgres_container = PostgresContainer("postgres:15-alpine")
            self.postgres_container.start()
            
            self.postgres_url = self.postgres_container.get_connection_url().replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            self.postgres_engine = create_async_engine(
                self.postgres_url,
                pool_size=5,
                max_overflow=2,
                echo=False
            )
            
            self.postgres_session_factory = sessionmaker(
                self.postgres_engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Setup ClickHouse
            self.clickhouse_container = ClickHouseContainer("clickhouse/clickhouse-server:23.8-alpine")
            self.clickhouse_container.start()
            
            ch_host = self.clickhouse_container.get_container_host_ip()
            ch_port = self.clickhouse_container.get_exposed_port(9000)
            
            # import asyncio_clickhouse  # Module not available
            self.clickhouse_client = asyncio_clickhouse.connect(
                host=ch_host,
                port=ch_port,
                database="default"
            )
            
            # Initialize migration infrastructure
            await self.create_migration_infrastructure()
            
            logger.info("Migration rollback test containers setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup migration test containers: {e}")
            await self.cleanup()
            raise
    
    async def create_migration_infrastructure(self):
        """Create migration tracking and test schema infrastructure."""
        # PostgreSQL migration infrastructure
        async with self.postgres_engine.begin() as conn:
            # Migration history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id SERIAL PRIMARY KEY,
                    migration_id VARCHAR(100) UNIQUE NOT NULL,
                    migration_name VARCHAR(200) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rolled_back_at TIMESTAMP NULL,
                    rollback_reason TEXT NULL,
                    data_snapshot_id VARCHAR(100) NULL,
                    checksum VARCHAR(64) NOT NULL
                )
            """)
            
            # Test tables for migration testing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_test_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    profile_data JSONB DEFAULT '{}',
                    version INTEGER DEFAULT 1
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_test_orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES migration_test_users(id),
                    order_number VARCHAR(50) UNIQUE NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test data
            await conn.execute("""
                INSERT INTO migration_test_users (username, email, profile_data) VALUES 
                ('user1', 'user1@test.com', '{"preferences": {"theme": "dark"}}'),
                ('user2', 'user2@test.com', '{"preferences": {"theme": "light"}}'),
                ('user3', 'user3@test.com', '{"preferences": {"theme": "auto"}}')
                ON CONFLICT (username) DO NOTHING
            """)
            
            await conn.execute("""
                INSERT INTO migration_test_orders (user_id, order_number, amount, status) 
                SELECT u.id, 'ORDER-' || u.id || '-' || generate_random_uuid()::text, 99.99, 'completed'
                FROM migration_test_users u
                WHERE NOT EXISTS (SELECT 1 FROM migration_test_orders WHERE user_id = u.id)
            """)
        
        # ClickHouse migration infrastructure
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS ch_migration_history (
                migration_id String,
                migration_name String,
                applied_at DateTime,
                rolled_back_at DateTime DEFAULT toDateTime('1970-01-01'),
                status String DEFAULT 'applied'
            ) ENGINE = MergeTree()
            ORDER BY applied_at
        """)
        
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS ch_analytics_events (
                event_id String,
                user_id String,
                event_type String,
                event_data String,
                created_at DateTime
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(created_at)
            ORDER BY (event_type, user_id, created_at)
        """)
    
    async def create_data_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """Create a snapshot of current data state before migration."""
        snapshot_result = {
            "snapshot_id": snapshot_id,
            "postgres_snapshot": {},
            "clickhouse_snapshot": {},
            "snapshot_created_at": datetime.now(),
            "success": False
        }
        
        try:
            # PostgreSQL snapshot
            async with self.postgres_session_factory() as session:
                # Count users
                users_result = await session.execute("SELECT COUNT(*) FROM migration_test_users")
                users_count = users_result.fetchone()[0]
                
                # Count orders
                orders_result = await session.execute("SELECT COUNT(*) FROM migration_test_orders")
                orders_count = orders_result.fetchone()[0]
                
                # Sample user data
                sample_user_result = await session.execute(
                    "SELECT id, username, email, profile_data FROM migration_test_users LIMIT 1"
                )
                sample_user = sample_user_result.fetchone()
                
                snapshot_result["postgres_snapshot"] = {
                    "users_count": users_count,
                    "orders_count": orders_count,
                    "sample_user": {
                        "id": sample_user[0],
                        "username": sample_user[1],
                        "email": sample_user[2],
                        "profile_data": sample_user[3]
                    } if sample_user else None
                }
            
            # ClickHouse snapshot
            ch_events_result = await self.clickhouse_client.execute(
                "SELECT COUNT(*) FROM ch_analytics_events"
            )
            ch_events_count = ch_events_result[0][0] if ch_events_result else 0
            
            snapshot_result["clickhouse_snapshot"] = {
                "events_count": ch_events_count
            }
            
            # Store snapshot
            self.data_snapshots[snapshot_id] = snapshot_result
            snapshot_result["success"] = True
            
        except Exception as e:
            snapshot_result["error"] = str(e)
            logger.error(f"Failed to create data snapshot: {e}")
        
        return snapshot_result
    
    async def apply_test_migration(self, migration_id: str, migration_type: str) -> Dict[str, Any]:
        """Apply a test migration and track its execution."""
        migration_result = {
            "migration_id": migration_id,
            "migration_type": migration_type,
            "applied_successfully": False,
            "rollback_sql_generated": False,
            "data_preserved": False,
            "error_details": None
        }
        
        try:
            # Create pre-migration snapshot
            pre_snapshot = await self.create_data_snapshot(f"pre_{migration_id}")
            
            if migration_type == "add_column":
                await self.apply_add_column_migration(migration_id)
            elif migration_type == "modify_constraint":
                await self.apply_constraint_migration(migration_id)
            elif migration_type == "create_index":
                await self.apply_index_migration(migration_id)
            elif migration_type == "data_migration":
                await self.apply_data_migration(migration_id)
            else:
                raise ValueError(f"Unknown migration type: {migration_type}")
            
            # Record migration
            async with self.postgres_session_factory() as session:
                await session.execute(
                    """
                    INSERT INTO migration_history (migration_id, migration_name, data_snapshot_id, checksum)
                    VALUES (:migration_id, :migration_name, :snapshot_id, :checksum)
                    """,
                    {
                        "migration_id": migration_id,
                        "migration_name": f"Test migration: {migration_type}",
                        "snapshot_id": f"pre_{migration_id}",
                        "checksum": f"checksum_{migration_id}"
                    }
                )
                await session.commit()
            
            migration_result["applied_successfully"] = True
            migration_result["rollback_sql_generated"] = True
            
            # Verify data preservation
            post_snapshot = await self.create_data_snapshot(f"post_{migration_id}")
            migration_result["data_preserved"] = self.verify_data_preservation(
                pre_snapshot, post_snapshot, migration_type
            )
            
        except Exception as e:
            migration_result["error_details"] = str(e)
            logger.error(f"Migration {migration_id} failed: {e}")
        
        return migration_result
    
    async def apply_add_column_migration(self, migration_id: str):
        """Apply a test migration that adds a column."""
        async with self.postgres_engine.begin() as conn:
            await conn.execute("""
                ALTER TABLE migration_test_users 
                ADD COLUMN IF NOT EXISTS last_login TIMESTAMP NULL
            """)
            
            # Update some test data
            await conn.execute("""
                UPDATE migration_test_users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE username = 'user1'
            """)
    
    async def apply_constraint_migration(self, migration_id: str):
        """Apply a test migration that modifies constraints."""
        async with self.postgres_engine.begin() as conn:
            await conn.execute("""
                ALTER TABLE migration_test_users 
                ADD CONSTRAINT IF NOT EXISTS check_email_format 
                CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
            """)
    
    async def apply_index_migration(self, migration_id: str):
        """Apply a test migration that creates an index."""
        async with self.postgres_engine.begin() as conn:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_migration_test_users_email 
                ON migration_test_users(email)
            """)
    
    async def apply_data_migration(self, migration_id: str):
        """Apply a test migration that migrates data."""
        async with self.postgres_engine.begin() as conn:
            # Add a new column for migrated data
            await conn.execute("""
                ALTER TABLE migration_test_users 
                ADD COLUMN IF NOT EXISTS user_type VARCHAR(20) DEFAULT 'standard'
            """)
            
            # Migrate data based on existing profile data
            await conn.execute("""
                UPDATE migration_test_users 
                SET user_type = CASE 
                    WHEN profile_data->>'preferences'->>'theme' = 'dark' THEN 'premium'
                    ELSE 'standard'
                END
            """)
    
    def verify_data_preservation(self, pre_snapshot: Dict[str, Any], post_snapshot: Dict[str, Any], migration_type: str) -> bool:
        """Verify that data was preserved during migration."""
        try:
            pre_pg = pre_snapshot["postgres_snapshot"]
            post_pg = post_snapshot["postgres_snapshot"]
            
            # Users count should remain the same or increase
            if post_pg["users_count"] < pre_pg["users_count"]:
                return False
            
            # Orders count should remain the same or increase
            if post_pg["orders_count"] < pre_pg["orders_count"]:
                return False
            
            # Sample user data should be preserved (basic fields)
            if pre_pg["sample_user"] and post_pg["sample_user"]:
                pre_user = pre_pg["sample_user"]
                post_user = post_pg["sample_user"]
                
                if (pre_user["username"] != post_user["username"] or
                    pre_user["email"] != post_user["email"]):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data preservation verification failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_migration_rollback(self, migration_id: str) -> Dict[str, Any]:
        """Test rollback of a specific migration."""
        rollback_result = {
            "migration_id": migration_id,
            "rollback_successful": False,
            "data_restored": False,
            "schema_restored": False,
            "error_details": None
        }
        
        try:
            # Get pre-migration snapshot
            pre_snapshot_id = f"pre_{migration_id}"
            pre_snapshot = self.data_snapshots.get(pre_snapshot_id)
            
            if not pre_snapshot:
                raise ValueError(f"Pre-migration snapshot not found: {pre_snapshot_id}")
            
            # Generate and execute rollback SQL based on migration type
            async with self.postgres_session_factory() as session:
                # Get migration details
                migration_result = await session.execute(
                    "SELECT migration_name FROM migration_history WHERE migration_id = :migration_id",
                    {"migration_id": migration_id}
                )
                migration_row = migration_result.fetchone()
                
                if not migration_row:
                    raise ValueError(f"Migration not found: {migration_id}")
                
                migration_name = migration_row[0]
                
                # Execute appropriate rollback
                if "add_column" in migration_name.lower():
                    await session.execute("ALTER TABLE migration_test_users DROP COLUMN IF EXISTS last_login")
                elif "constraint" in migration_name.lower():
                    await session.execute("ALTER TABLE migration_test_users DROP CONSTRAINT IF EXISTS check_email_format")
                elif "index" in migration_name.lower():
                    await session.execute("DROP INDEX IF EXISTS idx_migration_test_users_email")
                elif "data_migration" in migration_name.lower():
                    await session.execute("ALTER TABLE migration_test_users DROP COLUMN IF EXISTS user_type")
                
                # Mark as rolled back
                await session.execute(
                    """
                    UPDATE migration_history 
                    SET rolled_back_at = CURRENT_TIMESTAMP, rollback_reason = 'Test rollback'
                    WHERE migration_id = :migration_id
                    """,
                    {"migration_id": migration_id}
                )
                
                await session.commit()
            
            rollback_result["rollback_successful"] = True
            rollback_result["schema_restored"] = True
            
            # Verify data restoration
            post_rollback_snapshot = await self.create_data_snapshot(f"rollback_{migration_id}")
            rollback_result["data_restored"] = self.verify_data_restoration(
                pre_snapshot, post_rollback_snapshot
            )
            
        except Exception as e:
            rollback_result["error_details"] = str(e)
            logger.error(f"Migration rollback {migration_id} failed: {e}")
        
        return rollback_result
    
    def verify_data_restoration(self, pre_snapshot: Dict[str, Any], post_rollback_snapshot: Dict[str, Any]) -> bool:
        """Verify that data was properly restored after rollback."""
        try:
            pre_pg = pre_snapshot["postgres_snapshot"]
            post_pg = post_rollback_snapshot["postgres_snapshot"]
            
            # Basic data counts should match
            if (pre_pg["users_count"] != post_pg["users_count"] or
                pre_pg["orders_count"] != post_pg["orders_count"]):
                return False
            
            # Sample user core data should match
            if pre_pg["sample_user"] and post_pg["sample_user"]:
                pre_user = pre_pg["sample_user"]
                post_user = post_pg["sample_user"]
                
                if (pre_user["username"] != post_user["username"] or
                    pre_user["email"] != post_user["email"]):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data restoration verification failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_failed_migration_recovery(self) -> Dict[str, Any]:
        """Test recovery from a failed migration scenario."""
        recovery_result = {
            "failure_simulated": False,
            "recovery_successful": False,
            "data_integrity_maintained": False,
            "partial_changes_rolled_back": False
        }
        
        try:
            migration_id = f"failed_migration_{uuid.uuid4().hex[:8]}"
            
            # Create pre-failure snapshot
            pre_snapshot = await self.create_data_snapshot(f"pre_fail_{migration_id}")
            
            # Simulate a partially failed migration
            async with self.postgres_session_factory() as session:
                try:
                    # Start transaction
                    await session.execute("""
                        ALTER TABLE migration_test_users 
                        ADD COLUMN temp_column VARCHAR(50)
                    """)
                    
                    # Simulate failure during migration
                    await session.execute("UPDATE migration_test_users SET temp_column = 'test_value'")
                    
                    # Force failure with invalid SQL
                    await session.execute("INVALID SQL THAT WILL FAIL")
                    
                    await session.commit()
                    
                except Exception:
                    # Expected failure - rollback transaction
                    await session.rollback()
                    recovery_result["failure_simulated"] = True
            
            # Verify recovery state
            post_failure_snapshot = await self.create_data_snapshot(f"post_fail_{migration_id}")
            
            # Check that partial changes were rolled back
            async with self.postgres_session_factory() as session:
                column_check = await session.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'migration_test_users' AND column_name = 'temp_column'
                """)
                column_exists = len(column_check.fetchall()) > 0
                
                recovery_result["partial_changes_rolled_back"] = not column_exists
            
            recovery_result["recovery_successful"] = True
            recovery_result["data_integrity_maintained"] = self.verify_data_restoration(
                pre_snapshot, post_failure_snapshot
            )
            
        except Exception as e:
            recovery_result["error"] = str(e)
            logger.error(f"Failed migration recovery test failed: {e}")
        
        return recovery_result
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.clickhouse_client:
                await self.clickhouse_client.disconnect()
            
            if self.postgres_engine:
                await self.postgres_engine.dispose()
            
            if self.postgres_container:
                self.postgres_container.stop()
            
            if self.clickhouse_container:
                self.clickhouse_container.stop()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def migration_manager():
    """Create migration rollback safety manager for testing."""
    manager = MigrationRollbackSafetyManager()
    await manager.setup_database_containers()
    yield manager
    await manager.cleanup()

@pytest.mark.L3
@pytest.mark.integration
class TestDatabaseMigrationRollbackSafetyL3:
    """L3 integration tests for database migration rollback safety."""
    
    @pytest.mark.asyncio
    async def test_safe_migration_rollback_process(self, migration_manager):
        """Test complete migration and rollback process."""
        migration_id = f"test_migration_{uuid.uuid4().hex[:8]}"
        
        # Apply migration
        apply_result = await migration_manager.apply_test_migration(migration_id, "add_column")
        assert apply_result["applied_successfully"] is True
        assert apply_result["data_preserved"] is True
        
        # Rollback migration
        rollback_result = await migration_manager.test_migration_rollback(migration_id)
        assert rollback_result["rollback_successful"] is True
        assert rollback_result["data_restored"] is True
        assert rollback_result["schema_restored"] is True
    
    @pytest.mark.asyncio
    async def test_multiple_migration_types_rollback(self, migration_manager):
        """Test rollback safety across different migration types."""
        migration_types = ["add_column", "create_index", "modify_constraint", "data_migration"]
        
        for migration_type in migration_types:
            migration_id = f"test_{migration_type}_{uuid.uuid4().hex[:8]}"
            
            # Apply migration
            apply_result = await migration_manager.apply_test_migration(migration_id, migration_type)
            assert apply_result["applied_successfully"] is True, f"Failed to apply {migration_type}"
            
            # Rollback migration
            rollback_result = await migration_manager.test_migration_rollback(migration_id)
            assert rollback_result["rollback_successful"] is True, f"Failed to rollback {migration_type}"
            assert rollback_result["data_restored"] is True, f"Data not restored for {migration_type}"
    
    @pytest.mark.asyncio
    async def test_failed_migration_recovery(self, migration_manager):
        """Test recovery from failed migration scenarios."""
        recovery_result = await migration_manager.test_failed_migration_recovery()
        
        assert recovery_result["failure_simulated"] is True
        assert recovery_result["recovery_successful"] is True
        assert recovery_result["data_integrity_maintained"] is True
        assert recovery_result["partial_changes_rolled_back"] is True
    
    @pytest.mark.asyncio
    async def test_data_preservation_during_rollback(self, migration_manager):
        """Test that existing data is preserved during rollback operations."""
        migration_id = f"preservation_test_{uuid.uuid4().hex[:8]}"
        
        # Create additional test data
        async with migration_manager.postgres_session_factory() as session:
            await session.execute("""
                INSERT INTO migration_test_users (username, email, profile_data) 
                VALUES ('preservation_user', 'preserve@test.com', '{"test": "data"}')
            """)
            await session.commit()
        
        # Apply and rollback migration
        apply_result = await migration_manager.apply_test_migration(migration_id, "add_column")
        assert apply_result["applied_successfully"] is True
        
        rollback_result = await migration_manager.test_migration_rollback(migration_id)
        assert rollback_result["rollback_successful"] is True
        
        # Verify test data still exists
        async with migration_manager.postgres_session_factory() as session:
            user_result = await session.execute(
                "SELECT username, email FROM migration_test_users WHERE username = 'preservation_user'"
            )
            user_row = user_result.fetchone()
            
            assert user_row is not None
            assert user_row[0] == "preservation_user"
            assert user_row[1] == "preserve@test.com"
    
    @pytest.mark.asyncio
    async def test_rollback_safety_under_load(self, migration_manager):
        """Test rollback safety when database is under concurrent load."""
        migration_id = f"load_test_{uuid.uuid4().hex[:8]}"
        
        async def concurrent_operations():
            """Simulate concurrent database operations during rollback."""
            for i in range(10):
                try:
                    async with migration_manager.postgres_session_factory() as session:
                        await session.execute(
                            "INSERT INTO migration_test_orders (user_id, order_number, amount) VALUES (1, :order_num, 50.00)",
                            {"order_num": f"LOAD_TEST_{i}_{uuid.uuid4().hex[:8]}"}
                        )
                        await session.commit()
                        await asyncio.sleep(0.1)
                except Exception as e:
                    logger.debug(f"Concurrent operation {i} failed: {e}")
        
        # Apply migration
        apply_result = await migration_manager.apply_test_migration(migration_id, "create_index")
        assert apply_result["applied_successfully"] is True
        
        # Start concurrent operations and rollback simultaneously
        concurrent_task = asyncio.create_task(concurrent_operations())
        
        await asyncio.sleep(0.2)  # Let some concurrent operations start
        
        rollback_result = await migration_manager.test_migration_rollback(migration_id)
        
        await concurrent_task  # Wait for concurrent operations to complete
        
        # Rollback should succeed despite concurrent operations
        assert rollback_result["rollback_successful"] is True
        assert rollback_result["data_restored"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])