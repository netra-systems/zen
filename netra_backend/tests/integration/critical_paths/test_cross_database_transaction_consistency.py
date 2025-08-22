"""
L3 Integration Test: Cross-Database Transaction Consistency (PostgreSQL + ClickHouse)

Business Value Justification (BVJ):
- Segment: Enterprise (multi-database analytics pipeline)
- Business Goal: Data Integrity - Ensure consistency between operational and analytics data
- Value Impact: Critical for enterprise customers relying on real-time analytics
- Strategic Impact: Enables $30K+ MRR enterprise features requiring dual-database consistency

L3 Test: Uses real PostgreSQL and ClickHouse containers to validate cross-database
transaction consistency, rollback scenarios, and data synchronization patterns.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.clickhouse import ClickHouseContainer
from testcontainers.postgres import PostgresContainer

import asyncio_clickhouse
from app.db.clickhouse import get_clickhouse_client

# Add project root to path
from app.db.postgres import get_async_db
from app.logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


class CrossDatabaseConsistencyManager:
    """Manages cross-database consistency testing with real containers."""
    
    def __init__(self):
        self.postgres_container = None
        self.clickhouse_container = None
        self.postgres_url = None
        self.clickhouse_client = None
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.sync_operations = []
        self.consistency_metrics = {}
        
    async def setup_database_containers(self):
        """Setup real PostgreSQL and ClickHouse containers."""
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
            
            self.clickhouse_client = asyncio_clickhouse.connect(
                host=ch_host,
                port=ch_port,
                database="default"
            )
            
            # Initialize schemas
            await self.create_cross_database_schema()
            
            logger.info("Cross-database test containers setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup database containers: {e}")
            await self.cleanup()
            raise
    
    async def create_cross_database_schema(self):
        """Create schemas in both databases for consistency testing."""
        # PostgreSQL operational schema
        async with self.postgres_engine.begin() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS operational_events (
                    id SERIAL PRIMARY KEY,
                    event_id UUID UNIQUE NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    event_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_to_analytics BOOLEAN DEFAULT FALSE,
                    sync_timestamp TIMESTAMP NULL
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) UNIQUE NOT NULL,
                    profile_data JSONB,
                    last_activity TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(100) NOT NULL,
                    last_sync_timestamp TIMESTAMP,
                    records_synced INTEGER DEFAULT 0,
                    sync_errors INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active'
                )
            """)
        
        # ClickHouse analytics schema
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                event_id String,
                user_id String,
                event_type String,
                event_data String,
                created_at DateTime,
                synced_at DateTime DEFAULT now(),
                processing_metadata String DEFAULT ''
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(created_at)
            ORDER BY (event_type, user_id, created_at)
        """)
        
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS user_analytics (
                user_id String,
                profile_snapshot String,
                last_activity DateTime,
                version UInt32,
                snapshot_timestamp DateTime DEFAULT now()
            ) ENGINE = ReplacingMergeTree(version)
            PARTITION BY toYYYYMM(snapshot_timestamp)
            ORDER BY user_id
        """)
        
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS sync_metrics (
                sync_id String,
                source_table String,
                target_table String,
                records_processed UInt64,
                sync_duration_ms UInt64,
                sync_timestamp DateTime,
                errors_count UInt32 DEFAULT 0
            ) ENGINE = MergeTree()
            ORDER BY sync_timestamp
        """)
    
    async def test_atomic_cross_database_operation(self, user_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test atomic operation across both databases."""
        operation_result = {
            "postgres_success": False,
            "clickhouse_success": False,
            "consistency_maintained": False,
            "rollback_required": False,
            "error_details": None
        }
        
        postgres_session = None
        event_id = str(uuid.uuid4())
        
        try:
            # Phase 1: PostgreSQL operational insert
            postgres_session = self.postgres_session_factory()
            
            await postgres_session.execute(
                """
                INSERT INTO operational_events (event_id, user_id, event_type, event_data, created_at)
                VALUES (:event_id, :user_id, :event_type, :event_data, :created_at)
                """,
                {
                    "event_id": event_id,
                    "user_id": user_id,
                    "event_type": event_data.get("type", "unknown"),
                    "event_data": json.dumps(event_data),
                    "created_at": datetime.now()
                }
            )
            
            # Don't commit yet - keep transaction open
            operation_result["postgres_success"] = True
            
            # Phase 2: ClickHouse analytics insert
            await self.clickhouse_client.execute(
                """
                INSERT INTO analytics_events 
                (event_id, user_id, event_type, event_data, created_at, synced_at)
                VALUES
                """,
                [(
                    event_id,
                    user_id,
                    event_data.get("type", "unknown"),
                    json.dumps(event_data),
                    datetime.now(),
                    datetime.now()
                )]
            )
            
            operation_result["clickhouse_success"] = True
            
            # Phase 3: Verify both operations succeeded before committing
            # Check ClickHouse insert
            ch_verify = await self.clickhouse_client.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE event_id = %s",
                [event_id]
            )
            
            if ch_verify[0][0] == 1:
                # Both operations successful - commit PostgreSQL
                await postgres_session.execute(
                    "UPDATE operational_events SET synced_to_analytics = TRUE, sync_timestamp = CURRENT_TIMESTAMP WHERE event_id = :event_id",
                    {"event_id": event_id}
                )
                await postgres_session.commit()
                operation_result["consistency_maintained"] = True
            else:
                # ClickHouse verification failed - rollback
                await postgres_session.rollback()
                operation_result["rollback_required"] = True
                
        except Exception as e:
            operation_result["error_details"] = str(e)
            operation_result["rollback_required"] = True
            
            try:
                if postgres_session:
                    await postgres_session.rollback()
                
                # Attempt to remove ClickHouse record if it was inserted
                if operation_result["clickhouse_success"]:
                    await self.clickhouse_client.execute(
                        "ALTER TABLE analytics_events DELETE WHERE event_id = %s",
                        [event_id]
                    )
                    
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed: {cleanup_error}")
        
        finally:
            if postgres_session:
                await postgres_session.close()
        
        return operation_result
    
    async def test_eventual_consistency_sync(self, batch_size: int = 100) -> Dict[str, Any]:
        """Test eventual consistency synchronization between databases."""
        sync_result = {
            "records_created": 0,
            "records_synced": 0,
            "sync_successful": False,
            "consistency_verified": False,
            "sync_metrics": {}
        }
        
        try:
            # Step 1: Create batch of operational events
            event_ids = []
            user_ids = [f"sync_user_{i}" for i in range(batch_size)]
            
            async with self.postgres_session_factory() as session:
                for i, user_id in enumerate(user_ids):
                    event_id = str(uuid.uuid4())
                    event_ids.append(event_id)
                    
                    await session.execute(
                        """
                        INSERT INTO operational_events (event_id, user_id, event_type, event_data)
                        VALUES (:event_id, :user_id, :event_type, :event_data)
                        """,
                        {
                            "event_id": event_id,
                            "user_id": user_id,
                            "event_type": "sync_test",
                            "event_data": json.dumps({"test_index": i})
                        }
                    )
                
                await session.commit()
                sync_result["records_created"] = len(event_ids)
            
            # Step 2: Simulate eventual consistency sync process
            sync_start_time = time.time()
            
            # Get unsynced events
            async with self.postgres_session_factory() as session:
                unsynced_result = await session.execute(
                    """
                    SELECT event_id, user_id, event_type, event_data, created_at
                    FROM operational_events 
                    WHERE synced_to_analytics = FALSE AND event_type = 'sync_test'
                    ORDER BY created_at
                    """
                )
                unsynced_events = unsynced_result.fetchall()
            
            # Batch sync to ClickHouse
            if unsynced_events:
                ch_records = []
                for event in unsynced_events:
                    ch_records.append((
                        event[0],  # event_id
                        event[1],  # user_id
                        event[2],  # event_type
                        event[3],  # event_data
                        event[4],  # created_at
                        datetime.now()  # synced_at
                    ))
                
                await self.clickhouse_client.execute(
                    """
                    INSERT INTO analytics_events 
                    (event_id, user_id, event_type, event_data, created_at, synced_at)
                    VALUES
                    """,
                    ch_records
                )
                
                # Mark as synced in PostgreSQL
                event_ids_to_update = [event[0] for event in unsynced_events]
                async with self.postgres_session_factory() as session:
                    await session.execute(
                        """
                        UPDATE operational_events 
                        SET synced_to_analytics = TRUE, sync_timestamp = CURRENT_TIMESTAMP
                        WHERE event_id = ANY(:event_ids)
                        """,
                        {"event_ids": event_ids_to_update}
                    )
                    await session.commit()
                
                sync_result["records_synced"] = len(ch_records)
                sync_result["sync_successful"] = True
            
            sync_duration = time.time() - sync_start_time
            
            # Step 3: Verify consistency
            await asyncio.sleep(1)  # Allow for processing
            
            # Count in both databases
            async with self.postgres_session_factory() as session:
                pg_count_result = await session.execute(
                    "SELECT COUNT(*) FROM operational_events WHERE event_type = 'sync_test' AND synced_to_analytics = TRUE"
                )
                pg_synced_count = pg_count_result.fetchone()[0]
            
            ch_count_result = await self.clickhouse_client.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE event_type = 'sync_test'"
            )
            ch_count = ch_count_result[0][0]
            
            sync_result["consistency_verified"] = pg_synced_count == ch_count == batch_size
            
            sync_result["sync_metrics"] = {
                "sync_duration_seconds": sync_duration,
                "records_per_second": batch_size / sync_duration if sync_duration > 0 else 0,
                "postgres_synced_count": pg_synced_count,
                "clickhouse_count": ch_count
            }
            
        except Exception as e:
            sync_result["error"] = str(e)
            logger.error(f"Eventual consistency sync failed: {e}")
        
        return sync_result
    
    async def test_rollback_consistency(self) -> Dict[str, Any]:
        """Test rollback scenarios for consistency maintenance."""
        rollback_result = {
            "rollback_scenarios_tested": 0,
            "successful_rollbacks": 0,
            "data_integrity_maintained": False
        }
        
        scenarios = [
            ("postgres_failure", "Simulate PostgreSQL failure after ClickHouse insert"),
            ("clickhouse_failure", "Simulate ClickHouse failure after PostgreSQL insert"),
            ("network_timeout", "Simulate network timeout during sync")
        ]
        
        for scenario_name, scenario_desc in scenarios:
            try:
                rollback_result["rollback_scenarios_tested"] += 1
                
                user_id = f"rollback_user_{scenario_name}"
                event_id = str(uuid.uuid4())
                
                if scenario_name == "postgres_failure":
                    # Insert to ClickHouse first, then fail PostgreSQL
                    await self.clickhouse_client.execute(
                        "INSERT INTO analytics_events (event_id, user_id, event_type, event_data, created_at) VALUES",
                        [(event_id, user_id, "rollback_test", "{}", datetime.now())]
                    )
                    
                    # Simulate PostgreSQL failure (don't insert)
                    # Cleanup ClickHouse
                    await self.clickhouse_client.execute(
                        "ALTER TABLE analytics_events DELETE WHERE event_id = %s",
                        [event_id]
                    )
                    rollback_result["successful_rollbacks"] += 1
                
                elif scenario_name == "clickhouse_failure":
                    # Insert to PostgreSQL first
                    async with self.postgres_session_factory() as session:
                        await session.execute(
                            "INSERT INTO operational_events (event_id, user_id, event_type, event_data) VALUES (:event_id, :user_id, :event_type, :event_data)",
                            {"event_id": event_id, "user_id": user_id, "event_type": "rollback_test", "event_data": "{}"}
                        )
                        
                        # Simulate ClickHouse failure - rollback PostgreSQL
                        await session.rollback()
                    
                    rollback_result["successful_rollbacks"] += 1
                
                elif scenario_name == "network_timeout":
                    # Simulate partial success with timeout
                    async with self.postgres_session_factory() as session:
                        await session.execute(
                            "INSERT INTO operational_events (event_id, user_id, event_type, event_data) VALUES (:event_id, :user_id, :event_type, :event_data)",
                            {"event_id": event_id, "user_id": user_id, "event_type": "timeout_test", "event_data": "{}"}
                        )
                        
                        # Simulate timeout during ClickHouse sync
                        await asyncio.sleep(0.1)
                        
                        # Rollback due to timeout
                        await session.rollback()
                    
                    rollback_result["successful_rollbacks"] += 1
                
            except Exception as e:
                logger.error(f"Rollback scenario {scenario_name} failed: {e}")
        
        # Verify no orphaned data exists
        try:
            async with self.postgres_session_factory() as session:
                pg_orphans = await session.execute(
                    "SELECT COUNT(*) FROM operational_events WHERE event_type IN ('rollback_test', 'timeout_test')"
                )
                pg_orphan_count = pg_orphans.fetchone()[0]
            
            ch_orphans = await self.clickhouse_client.execute(
                "SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('rollback_test', 'timeout_test')"
            )
            ch_orphan_count = ch_orphans[0][0]
            
            rollback_result["data_integrity_maintained"] = pg_orphan_count == 0 and ch_orphan_count == 0
            
        except Exception as e:
            logger.error(f"Orphan data check failed: {e}")
        
        return rollback_result
    
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
async def cross_db_manager():
    """Create cross-database consistency manager for testing."""
    manager = CrossDatabaseConsistencyManager()
    await manager.setup_database_containers()
    yield manager
    await manager.cleanup()


@pytest.mark.L3
@pytest.mark.integration
class TestCrossDatabaseTransactionConsistencyL3:
    """L3 integration tests for cross-database transaction consistency."""
    
    async def test_atomic_cross_database_operations(self, cross_db_manager):
        """Test atomic operations that span PostgreSQL and ClickHouse."""
        user_id = "atomic_test_user"
        event_data = {"type": "user_action", "action": "test_atomic", "timestamp": time.time()}
        
        result = await cross_db_manager.test_atomic_cross_database_operation(user_id, event_data)
        
        # Should achieve consistency or proper rollback
        assert result["postgres_success"] is True
        assert result["clickhouse_success"] is True
        assert result["consistency_maintained"] is True or result["rollback_required"] is True
        
        # If rollback was required, no orphaned data should remain
        if result["rollback_required"]:
            assert result["consistency_maintained"] is False
    
    async def test_eventual_consistency_synchronization(self, cross_db_manager):
        """Test eventual consistency synchronization between databases."""
        result = await cross_db_manager.test_eventual_consistency_sync(50)
        
        assert result["records_created"] == 50
        assert result["sync_successful"] is True
        assert result["consistency_verified"] is True
        assert result["records_synced"] == 50
        
        # Performance requirements for sync process
        assert result["sync_metrics"]["records_per_second"] > 100  # Minimum sync performance
        assert result["sync_metrics"]["sync_duration_seconds"] < 5  # Max sync time
    
    async def test_rollback_consistency_scenarios(self, cross_db_manager):
        """Test various rollback scenarios maintain data integrity."""
        result = await cross_db_manager.test_rollback_consistency()
        
        assert result["rollback_scenarios_tested"] >= 3
        assert result["successful_rollbacks"] == result["rollback_scenarios_tested"]
        assert result["data_integrity_maintained"] is True
    
    async def test_concurrent_cross_database_operations(self, cross_db_manager):
        """Test concurrent operations across both databases."""
        concurrent_operations = 10
        
        async def single_operation(operation_id: int):
            user_id = f"concurrent_user_{operation_id}"
            event_data = {"type": "concurrent_test", "operation_id": operation_id}
            return await cross_db_manager.test_atomic_cross_database_operation(user_id, event_data)
        
        # Execute concurrent operations
        tasks = [single_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_operations = sum(
            1 for r in results 
            if isinstance(r, dict) and r.get("consistency_maintained")
        )
        
        # Should handle most concurrent operations successfully
        success_rate = successful_operations / concurrent_operations
        assert success_rate >= 0.8  # At least 80% success rate
    
    async def test_data_consistency_verification(self, cross_db_manager):
        """Test comprehensive data consistency verification."""
        # Create test data
        test_events = [
            {"user_id": f"verify_user_{i}", "type": "verification_test", "data": {"index": i}}
            for i in range(20)
        ]
        
        # Insert and sync data
        for event in test_events:
            await cross_db_manager.test_atomic_cross_database_operation(
                event["user_id"], event
            )
        
        # Verify consistency
        await asyncio.sleep(1)  # Allow for processing
        
        # Count records in both databases
        async with cross_db_manager.postgres_session_factory() as session:
            pg_result = await session.execute(
                "SELECT COUNT(*) FROM operational_events WHERE event_type = 'verification_test'"
            )
            pg_count = pg_result.fetchone()[0]
        
        ch_result = await cross_db_manager.clickhouse_client.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE event_type = 'verification_test'"
        )
        ch_count = ch_result[0][0]
        
        # Counts should match
        assert pg_count == ch_count
        assert pg_count >= len(test_events) * 0.8  # Allow for some failures


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])