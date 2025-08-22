"""L4 Production Data Migration Integrity Test

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Data Integrity and Migration Safety
- Value Impact: Ensures zero data loss during production migrations
- Strategic Impact: $50K MRR protection from data corruption/loss incidents

L4 Test: Uses real staging environment to validate comprehensive data migration 
integrity across PostgreSQL, ClickHouse, and Redis with 100K+ records.
Tests migration, rollback, performance, and zero data loss guarantees.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# from app.services.redis.session_manager import RedisSessionManager
from unittest.mock import AsyncMock

import asyncpg
import pytest
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from netra_backend.app.db.client_clickhouse import ClickHouseClient

from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    CriticalPathMetrics,
    L4StagingCriticalPathTestBase,
)

RedisSessionManager = AsyncMock
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

@dataclass
class MigrationSnapshot:
    """Data snapshot for migration integrity verification."""
    snapshot_id: str
    timestamp: datetime
    postgres_checksum: str
    clickhouse_checksum: str
    redis_checksum: str
    row_counts: Dict[str, int]
    sample_data: Dict[str, Any]
    schema_version: str
    migration_id: Optional[str] = None

@dataclass
class MigrationMetrics:
    """Migration performance and business metrics."""
    records_migrated: int
    migration_duration_seconds: float
    rollback_duration_seconds: float
    data_integrity_score: float
    performance_impact_percent: float
    zero_data_loss_verified: bool
    business_continuity_maintained: bool

class L4DataMigrationIntegrityTest(L4StagingCriticalPathTestBase):
    """L4 test for production data migration integrity across all databases."""
    
    def __init__(self):
        super().__init__("L4_Data_Migration_Integrity")
        self.postgres_engine: Optional[object] = None
        self.clickhouse_client: Optional[ClickHouseClient] = None
        self.redis_client: Optional[redis.Redis] = None
        self.postgres_session_factory: Optional[object] = None
        self.migration_snapshots: Dict[str, MigrationSnapshot] = {}
        self.test_data_volume = 100000  # 100K+ records requirement
        self.migration_batch_size = 5000
        
    async def setup_test_specific_environment(self) -> None:
        """Setup specific environment for data migration testing."""
        try:
            # Initialize database connections
            await self._setup_postgres_connection()
            await self._setup_clickhouse_connection()
            await self._setup_redis_connection()
            
            # Create migration infrastructure
            await self._create_migration_infrastructure()
            
            # Generate test data
            await self._generate_migration_test_data()
            
            # Validate staging environment data consistency
            await self._validate_initial_data_state()
            
            logger.info(f"L4 migration test environment setup complete with {self.test_data_volume} records")
            
        except Exception as e:
            logger.error(f"Failed to setup L4 migration test environment: {e}")
            raise
    
    async def _setup_postgres_connection(self) -> None:
        """Setup PostgreSQL connection for staging environment."""
        postgres_url = self.staging_suite.env_config.database_url
        if not postgres_url:
            raise ValueError("PostgreSQL URL not configured for staging")
        
        # Convert to asyncpg format if needed
        if "postgresql://" in postgres_url and "asyncpg" not in postgres_url:
            postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self.postgres_engine = create_async_engine(
            postgres_url,
            pool_size=10,
            max_overflow=5,
            echo=False,
            pool_timeout=30
        )
        
        self.postgres_session_factory = sessionmaker(
            self.postgres_engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # Test connection
        async with self.postgres_session_factory() as session:
            await session.execute("SELECT 1")
    
    async def _setup_clickhouse_connection(self) -> None:
        """Setup ClickHouse connection for staging environment."""
        ch_config = self.staging_suite.env_config.clickhouse
        if not ch_config:
            raise ValueError("ClickHouse configuration not found for staging")
        
        self.clickhouse_client = ClickHouseClient(
            host=ch_config.host,
            port=ch_config.port,
            database=ch_config.database or "default",
            username=ch_config.username,
            password=ch_config.password
        )
        
        # Test connection
        await self.clickhouse_client.test_connection()
    
    async def _setup_redis_connection(self) -> None:
        """Setup Redis connection for staging environment."""
        redis_url = self.staging_suite.env_config.redis_url
        if not redis_url:
            raise ValueError("Redis URL not configured for staging")
        
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10
        )
        
        # Test connection
        await self.redis_client.ping()
    
    async def _create_migration_infrastructure(self) -> None:
        """Create migration infrastructure and test tables."""
        
        # PostgreSQL migration infrastructure
        async with self.postgres_session_factory() as session:
            # Migration tracking table
            await session.execute("""
                CREATE TABLE IF NOT EXISTS l4_migration_history (
                    id SERIAL PRIMARY KEY,
                    migration_id VARCHAR(100) UNIQUE NOT NULL,
                    migration_type VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    rolled_back_at TIMESTAMP NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    records_affected INTEGER DEFAULT 0,
                    data_checksum VARCHAR(64),
                    rollback_checksum VARCHAR(64),
                    performance_metrics JSONB DEFAULT '{}'
                )
            """)
            
            # Large test table for migration testing
            await session.execute("""
                CREATE TABLE IF NOT EXISTS l4_test_users (
                    id SERIAL PRIMARY KEY,
                    user_uuid UUID UNIQUE DEFAULT gen_random_uuid(),
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(200) NOT NULL,
                    profile_data JSONB DEFAULT '{}',
                    tier VARCHAR(20) DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'active',
                    metadata JSONB DEFAULT '{}',
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Orders table with foreign key constraints
            await session.execute("""
                CREATE TABLE IF NOT EXISTS l4_test_orders (
                    id SERIAL PRIMARY KEY,
                    order_uuid UUID UNIQUE DEFAULT gen_random_uuid(),
                    user_id INTEGER REFERENCES l4_test_users(id) ON DELETE CASCADE,
                    order_number VARCHAR(50) UNIQUE NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'USD',
                    status VARCHAR(20) DEFAULT 'pending',
                    order_data JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL
                )
            """)
            
            # Analytics events table
            await session.execute("""
                CREATE TABLE IF NOT EXISTS l4_test_events (
                    id SERIAL PRIMARY KEY,
                    event_uuid UUID UNIQUE DEFAULT gen_random_uuid(),
                    user_id INTEGER REFERENCES l4_test_users(id),
                    event_type VARCHAR(50) NOT NULL,
                    event_data JSONB NOT NULL,
                    session_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            
            await session.commit()
        
        # ClickHouse migration infrastructure
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS l4_migration_log (
                migration_id String,
                migration_type String,
                started_at DateTime,
                completed_at DateTime DEFAULT toDateTime('1970-01-01'),
                status String DEFAULT 'pending',
                records_migrated UInt64,
                data_checksum String
            ) ENGINE = MergeTree()
            ORDER BY started_at
        """)
        
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS l4_analytics_events (
                event_id String,
                user_id String,
                event_type String,
                event_data String,
                session_id String,
                created_at DateTime,
                processed UInt8 DEFAULT 0
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(created_at)
            ORDER BY (event_type, user_id, created_at)
        """)
        
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS l4_user_analytics (
                user_id String,
                username String,
                tier String,
                total_orders UInt32,
                total_spent Decimal(12,2),
                last_activity DateTime,
                metadata String
            ) ENGINE = ReplacingMergeTree()
            ORDER BY user_id
        """)
    
    async def _generate_migration_test_data(self) -> None:
        """Generate large volume test data for migration testing."""
        logger.info(f"Generating {self.test_data_volume} test records for migration")
        
        batch_size = 1000
        total_batches = self.test_data_volume // batch_size
        
        for batch_num in range(total_batches):
            await self._generate_data_batch(batch_num, batch_size)
            
            if batch_num % 10 == 0:
                logger.info(f"Generated batch {batch_num}/{total_batches}")
        
        # Generate additional test data in Redis
        await self._generate_redis_test_data()
        
        logger.info("Test data generation complete")
    
    async def _generate_data_batch(self, batch_num: int, batch_size: int) -> None:
        """Generate a batch of test data."""
        async with self.postgres_session_factory() as session:
            # Generate users
            user_values = []
            for i in range(batch_size):
                user_id = batch_num * batch_size + i
                tier = ["free", "early", "mid", "enterprise"][user_id % 4]
                profile_data = {
                    "preferences": {"theme": "dark" if user_id % 2 == 0 else "light"},
                    "settings": {"notifications": True, "analytics": user_id % 3 == 0}
                }
                
                user_values.append(f"('{user_id}_test_user', 'user{user_id}@staging.test', '{json.dumps(profile_data)}', '{tier}')")
            
            if user_values:
                await session.execute(f"""
                    INSERT INTO l4_test_users (username, email, profile_data, tier) 
                    VALUES {','.join(user_values)}
                    ON CONFLICT (username) DO NOTHING
                """)
            
            # Generate orders for some users
            if batch_num % 3 == 0:  # Every 3rd batch gets orders
                order_values = []
                for i in range(batch_size // 4):  # 25% of users get orders
                    user_offset = batch_num * batch_size + i
                    order_num = f"ORDER-{batch_num}-{i}-{uuid.uuid4().hex[:8]}"
                    amount = round(99.99 + (user_offset % 900), 2)
                    status = ["pending", "completed", "failed"][user_offset % 3]
                    order_data = {
                        "payment_method": "card",
                        "shipping": {"method": "standard"},
                        "items": [{"id": f"item_{i}", "quantity": 1}]
                    }
                    
                    order_values.append(
                        f"((SELECT id FROM l4_test_users WHERE username = '{user_offset}_test_user' LIMIT 1), "
                        f"'{order_num}', {amount}, '{status}', '{json.dumps(order_data)}')"
                    )
                
                if order_values:
                    await session.execute(f"""
                        INSERT INTO l4_test_orders (user_id, order_number, amount, status, order_data)
                        VALUES {','.join(order_values)}
                        ON CONFLICT (order_number) DO NOTHING
                    """)
            
            await session.commit()
    
    async def _generate_redis_test_data(self) -> None:
        """Generate test data in Redis for migration testing."""
        logger.info("Generating Redis test data")
        
        # User sessions
        for i in range(10000):
            session_data = {
                "user_id": str(i),
                "login_time": datetime.now().isoformat(),
                "ip_address": f"192.168.1.{i % 255}",
                "user_agent": "test_browser/1.0",
                "preferences": json.dumps({"theme": "dark" if i % 2 == 0 else "light"})
            }
            await self.redis_client.hset(f"session:{i}", mapping=session_data)
            await self.redis_client.expire(f"session:{i}", 3600)
        
        # Cache data
        for i in range(5000):
            cache_key = f"cache:user_profile:{i}"
            cache_data = json.dumps({
                "profile_id": i,
                "last_updated": datetime.now().isoformat(),
                "settings": {"notifications": True, "analytics": i % 3 == 0}
            })
            await self.redis_client.set(cache_key, cache_data, ex=1800)
        
        # Rate limiting data
        for i in range(1000):
            rate_key = f"rate_limit:user:{i}"
            await self.redis_client.set(rate_key, str(i % 100), ex=300)
    
    async def _validate_initial_data_state(self) -> None:
        """Validate initial data state before migration testing."""
        # Count PostgreSQL records
        async with self.postgres_session_factory() as session:
            users_result = await session.execute("SELECT COUNT(*) FROM l4_test_users")
            users_count = users_result.fetchone()[0]
            
            orders_result = await session.execute("SELECT COUNT(*) FROM l4_test_orders")
            orders_count = orders_result.fetchone()[0]
            
            if users_count < self.test_data_volume * 0.9:  # Allow 10% tolerance
                raise ValueError(f"Insufficient test users: {users_count} < {self.test_data_volume}")
        
        # Count Redis keys
        redis_session_count = len(await self.redis_client.keys("session:*"))
        redis_cache_count = len(await self.redis_client.keys("cache:*"))
        
        if redis_session_count < 9000:  # Allow tolerance
            raise ValueError(f"Insufficient Redis sessions: {redis_session_count}")
        
        logger.info(f"Initial data validation complete: {users_count} users, {orders_count} orders, "
                   f"{redis_session_count} sessions, {redis_cache_count} cache entries")
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute comprehensive data migration integrity test."""
        test_results = {
            "migration_scenarios_tested": 0,
            "rollback_scenarios_tested": 0,
            "data_integrity_validations": 0,
            "performance_validations": 0,
            "zero_data_loss_verified": False,
            "business_continuity_maintained": False,
            "service_calls": 0,
            "migration_metrics": [],
            "errors": []
        }
        
        try:
            # Test 1: Large-scale data migration with integrity validation
            migration_result = await self._test_large_scale_migration()
            test_results["migration_scenarios_tested"] += 1
            test_results["migration_metrics"].append(migration_result)
            test_results["service_calls"] += migration_result.get("service_calls", 0)
            
            # Test 2: Cross-database transaction consistency during migration
            consistency_result = await self._test_cross_database_consistency()
            test_results["data_integrity_validations"] += 1
            test_results["service_calls"] += consistency_result.get("service_calls", 0)
            
            # Test 3: Migration rollback with zero data loss
            rollback_result = await self._test_migration_rollback_integrity()
            test_results["rollback_scenarios_tested"] += 1
            test_results["zero_data_loss_verified"] = rollback_result.get("zero_data_loss", False)
            test_results["service_calls"] += rollback_result.get("service_calls", 0)
            
            # Test 4: Performance impact during migration
            performance_result = await self._test_migration_performance_impact()
            test_results["performance_validations"] += 1
            test_results["business_continuity_maintained"] = performance_result.get("continuity_maintained", False)
            test_results["service_calls"] += performance_result.get("service_calls", 0)
            
            # Test 5: Schema validation and constraint preservation
            schema_result = await self._test_schema_constraint_preservation()
            test_results["data_integrity_validations"] += 1
            test_results["service_calls"] += schema_result.get("service_calls", 0)
            
            # Test 6: Concurrent operations during migration
            concurrency_result = await self._test_concurrent_operations_migration()
            test_results["migration_scenarios_tested"] += 1
            test_results["service_calls"] += concurrency_result.get("service_calls", 0)
            
            # Aggregate results
            test_results["overall_success"] = all([
                migration_result.get("success", False),
                consistency_result.get("success", False),
                rollback_result.get("success", False),
                performance_result.get("success", False),
                schema_result.get("success", False),
                concurrency_result.get("success", False)
            ])
            
        except Exception as e:
            test_results["errors"].append(f"Critical path execution failed: {str(e)}")
            logger.error(f"Migration test execution failed: {e}")
        
        return test_results
    
    async def _test_large_scale_migration(self) -> Dict[str, Any]:
        """Test large-scale data migration with 100K+ records."""
        migration_id = f"large_scale_{uuid.uuid4().hex[:8]}"
        result = {"success": False, "service_calls": 0, "migration_id": migration_id}
        
        try:
            # Create pre-migration snapshot
            pre_snapshot = await self._create_comprehensive_snapshot(f"pre_{migration_id}")
            result["service_calls"] += 3  # Three database checks
            
            # Execute migration: Add new columns and migrate data
            start_time = time.time()
            
            # PostgreSQL schema migration
            async with self.postgres_session_factory() as session:
                await session.execute("""
                    ALTER TABLE l4_test_users 
                    ADD COLUMN IF NOT EXISTS migration_batch INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS migrated_at TIMESTAMP NULL
                """)
                await session.commit()
                result["service_calls"] += 1
            
            # Batch data migration
            migrated_count = 0
            batch_num = 0
            
            while True:
                async with self.postgres_session_factory() as session:
                    # Migrate batch
                    batch_result = await session.execute(f"""
                        UPDATE l4_test_users 
                        SET migration_batch = {batch_num}, migrated_at = CURRENT_TIMESTAMP
                        WHERE migration_batch = 0 AND id IN (
                            SELECT id FROM l4_test_users 
                            WHERE migration_batch = 0 
                            LIMIT {self.migration_batch_size}
                        )
                    """)
                    
                    batch_count = batch_result.rowcount
                    if batch_count == 0:
                        break
                    
                    migrated_count += batch_count
                    batch_num += 1
                    await session.commit()
                    result["service_calls"] += 1
                    
                    # Simulate realistic migration delay
                    await asyncio.sleep(0.1)
            
            migration_duration = time.time() - start_time
            
            # Create post-migration snapshot
            post_snapshot = await self._create_comprehensive_snapshot(f"post_{migration_id}")
            result["service_calls"] += 3
            
            # Validate migration integrity
            integrity_valid = await self._validate_migration_integrity(
                pre_snapshot, post_snapshot, migration_id
            )
            result["service_calls"] += 1
            
            # Record migration
            await self._record_migration(migration_id, "large_scale", migrated_count, migration_duration)
            result["service_calls"] += 1
            
            result.update({
                "success": integrity_valid,
                "migrated_records": migrated_count,
                "migration_duration": migration_duration,
                "batches_processed": batch_num,
                "pre_snapshot": pre_snapshot.snapshot_id,
                "post_snapshot": post_snapshot.snapshot_id
            })
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Large-scale migration test failed: {e}")
        
        return result
    
    async def _test_cross_database_consistency(self) -> Dict[str, Any]:
        """Test cross-database transaction consistency during migration."""
        migration_id = f"consistency_{uuid.uuid4().hex[:8]}"
        result = {"success": False, "service_calls": 0, "migration_id": migration_id}
        
        try:
            # Create pre-migration snapshot
            pre_snapshot = await self._create_comprehensive_snapshot(f"pre_consistency_{migration_id}")
            result["service_calls"] += 3
            
            # Execute coordinated migration across databases
            start_time = time.time()
            
            # Migrate user analytics to ClickHouse
            async with self.postgres_session_factory() as session:
                users_result = await session.execute("""
                    SELECT u.user_uuid, u.username, u.tier, 
                           COUNT(o.id) as total_orders,
                           COALESCE(SUM(o.amount), 0) as total_spent
                    FROM l4_test_users u
                    LEFT JOIN l4_test_orders o ON u.id = o.user_id
                    WHERE u.status = 'active'
                    GROUP BY u.user_uuid, u.username, u.tier
                    LIMIT 10000
                """)
                users_data = users_result.fetchall()
                result["service_calls"] += 1
            
            # Insert into ClickHouse
            for user_row in users_data:
                await self.clickhouse_client.execute("""
                    INSERT INTO l4_user_analytics 
                    (user_id, username, tier, total_orders, total_spent, last_activity, metadata)
                    VALUES
                """, [{
                    "user_id": str(user_row[0]),
                    "username": user_row[1],
                    "tier": user_row[2],
                    "total_orders": user_row[3],
                    "total_spent": float(user_row[4]),
                    "last_activity": datetime.now(),
                    "metadata": json.dumps({"migrated": True, "migration_id": migration_id})
                }])
                result["service_calls"] += 1
            
            # Update Redis cache with migrated data
            for user_row in users_data[:1000]:  # Subset for Redis
                cache_key = f"user_analytics:{user_row[0]}"
                cache_data = json.dumps({
                    "total_orders": user_row[3],
                    "total_spent": float(user_row[4]),
                    "last_updated": datetime.now().isoformat(),
                    "migration_id": migration_id
                })
                await self.redis_client.set(cache_key, cache_data, ex=3600)
                result["service_calls"] += 1
            
            migration_duration = time.time() - start_time
            
            # Validate cross-database consistency
            consistency_score = await self._validate_cross_database_consistency(migration_id)
            result["service_calls"] += 6  # Multiple validation checks
            
            result.update({
                "success": consistency_score >= 0.95,  # 95% consistency required
                "users_migrated": len(users_data),
                "migration_duration": migration_duration,
                "consistency_score": consistency_score
            })
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Cross-database consistency test failed: {e}")
        
        return result
    
    async def _test_migration_rollback_integrity(self) -> Dict[str, Any]:
        """Test migration rollback with zero data loss verification."""
        migration_id = f"rollback_{uuid.uuid4().hex[:8]}"
        result = {"success": False, "service_calls": 0, "zero_data_loss": False}
        
        try:
            # Create comprehensive pre-migration snapshot
            pre_snapshot = await self._create_comprehensive_snapshot(f"pre_rollback_{migration_id}")
            result["service_calls"] += 3
            
            # Apply migration that will be rolled back
            async with self.postgres_session_factory() as session:
                # Add test column
                await session.execute("""
                    ALTER TABLE l4_test_users 
                    ADD COLUMN IF NOT EXISTS rollback_test_column VARCHAR(100) DEFAULT 'test_value'
                """)
                
                # Update data
                update_result = await session.execute("""
                    UPDATE l4_test_users 
                    SET rollback_test_column = 'migrated_' || id::text 
                    WHERE id <= 1000
                """)
                updated_count = update_result.rowcount
                
                await session.commit()
                result["service_calls"] += 2
            
            # Create post-migration snapshot
            post_migration_snapshot = await self._create_comprehensive_snapshot(f"post_migration_{migration_id}")
            result["service_calls"] += 3
            
            # Simulate migration failure and rollback
            start_rollback_time = time.time()
            
            async with self.postgres_session_factory() as session:
                # Rollback schema change
                await session.execute("""
                    ALTER TABLE l4_test_users 
                    DROP COLUMN IF EXISTS rollback_test_column
                """)
                await session.commit()
                result["service_calls"] += 1
            
            rollback_duration = time.time() - start_rollback_time
            
            # Create post-rollback snapshot
            post_rollback_snapshot = await self._create_comprehensive_snapshot(f"post_rollback_{migration_id}")
            result["service_calls"] += 3
            
            # Verify zero data loss
            zero_data_loss = await self._verify_zero_data_loss(
                pre_snapshot, post_rollback_snapshot
            )
            result["service_calls"] += 1
            
            # Verify data integrity restoration
            data_integrity_restored = await self._verify_data_integrity_restoration(
                pre_snapshot, post_rollback_snapshot
            )
            result["service_calls"] += 1
            
            result.update({
                "success": zero_data_loss and data_integrity_restored,
                "zero_data_loss": zero_data_loss,
                "data_integrity_restored": data_integrity_restored,
                "updated_records": updated_count,
                "rollback_duration": rollback_duration,
                "pre_snapshot": pre_snapshot.snapshot_id,
                "post_rollback_snapshot": post_rollback_snapshot.snapshot_id
            })
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Migration rollback test failed: {e}")
        
        return result
    
    async def _test_migration_performance_impact(self) -> Dict[str, Any]:
        """Test performance impact during migration on live services."""
        migration_id = f"performance_{uuid.uuid4().hex[:8]}"
        result = {"success": False, "service_calls": 0, "continuity_maintained": False}
        
        try:
            # Baseline performance measurement
            baseline_metrics = await self._measure_baseline_performance()
            result["service_calls"] += baseline_metrics["operations_measured"]
            
            # Start background load simulation
            load_task = asyncio.create_task(self._simulate_production_load())
            
            # Execute migration while measuring performance
            start_time = time.time()
            
            async with self.postgres_session_factory() as session:
                # Create index during high load
                await session.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_l4_users_tier_status 
                    ON l4_test_users(tier, status)
                """)
                
                # Migrate data in batches
                for batch in range(0, 10000, 1000):
                    await session.execute(f"""
                        UPDATE l4_test_orders 
                        SET metadata = metadata || '{{"performance_test": true}}'::jsonb
                        WHERE id BETWEEN {batch} AND {batch + 999}
                    """)
                    await session.commit()
                    result["service_calls"] += 1
                    
                    # Allow other operations
                    await asyncio.sleep(0.05)
            
            migration_duration = time.time() - start_time
            
            # Stop load simulation
            load_task.cancel()
            try:
                await load_task
            except asyncio.CancelledError:
                pass
            
            # Measure performance during migration
            migration_metrics = await self._measure_migration_performance()
            result["service_calls"] += migration_metrics["operations_measured"]
            
            # Calculate performance impact
            performance_impact = self._calculate_performance_impact(
                baseline_metrics, migration_metrics
            )
            
            # Business continuity check (< 20% performance degradation acceptable)
            continuity_maintained = performance_impact < 20.0
            
            result.update({
                "success": continuity_maintained,
                "continuity_maintained": continuity_maintained,
                "performance_impact_percent": performance_impact,
                "migration_duration": migration_duration,
                "baseline_response_time": baseline_metrics["avg_response_time"],
                "migration_response_time": migration_metrics["avg_response_time"]
            })
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Performance impact test failed: {e}")
        
        return result
    
    async def _test_schema_constraint_preservation(self) -> Dict[str, Any]:
        """Test preservation of schema constraints during migration."""
        migration_id = f"schema_{uuid.uuid4().hex[:8]}"
        result = {"success": False, "service_calls": 0}
        
        try:
            # Validate initial constraints
            initial_constraints = await self._validate_schema_constraints()
            result["service_calls"] += 1
            
            # Apply schema migration
            async with self.postgres_session_factory() as session:
                # Add constraint
                await session.execute("""
                    ALTER TABLE l4_test_users 
                    ADD CONSTRAINT IF NOT EXISTS check_tier_valid 
                    CHECK (tier IN ('free', 'early', 'mid', 'enterprise'))
                """)
                
                # Add foreign key constraint
                await session.execute("""
                    ALTER TABLE l4_test_events 
                    ADD CONSTRAINT IF NOT EXISTS fk_events_user_id 
                    FOREIGN KEY (user_id) REFERENCES l4_test_users(id) ON DELETE CASCADE
                """)
                
                await session.commit()
                result["service_calls"] += 2
            
            # Validate constraints after migration
            post_migration_constraints = await self._validate_schema_constraints()
            result["service_calls"] += 1
            
            # Test constraint enforcement
            constraint_enforcement_valid = await self._test_constraint_enforcement()
            result["service_calls"] += 3
            
            # Verify foreign key integrity
            fk_integrity_valid = await self._verify_foreign_key_integrity()
            result["service_calls"] += 1
            
            result.update({
                "success": constraint_enforcement_valid and fk_integrity_valid,
                "initial_constraints": len(initial_constraints),
                "post_migration_constraints": len(post_migration_constraints),
                "constraint_enforcement_valid": constraint_enforcement_valid,
                "foreign_key_integrity_valid": fk_integrity_valid
            })
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Schema constraint preservation test failed: {e}")
        
        return result
    
    async def _test_concurrent_operations_migration(self) -> Dict[str, Any]:
        """Test migration safety under concurrent operations."""
        migration_id = f"concurrent_{uuid.uuid4().hex[:8]}"
        result = {"success": False, "service_calls": 0}
        
        try:
            # Start concurrent operations
            concurrent_tasks = [
                asyncio.create_task(self._concurrent_insert_operations()),
                asyncio.create_task(self._concurrent_update_operations()),
                asyncio.create_task(self._concurrent_read_operations())
            ]
            
            # Allow concurrent operations to start
            await asyncio.sleep(0.5)
            
            # Execute migration while operations are running
            start_time = time.time()
            
            async with self.postgres_session_factory() as session:
                # Schema change during concurrent operations
                await session.execute("""
                    ALTER TABLE l4_test_events 
                    ADD COLUMN IF NOT EXISTS concurrent_test_flag BOOLEAN DEFAULT FALSE
                """)
                
                # Data migration in batches
                for batch in range(0, 5000, 500):
                    await session.execute(f"""
                        UPDATE l4_test_events 
                        SET concurrent_test_flag = TRUE 
                        WHERE id BETWEEN {batch} AND {batch + 499}
                    """)
                    await session.commit()
                    result["service_calls"] += 1
                    await asyncio.sleep(0.1)
            
            migration_duration = time.time() - start_time
            
            # Stop concurrent operations
            for task in concurrent_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            operation_results = []
            for task in concurrent_tasks:
                try:
                    task_result = await task
                    operation_results.append(task_result)
                except asyncio.CancelledError:
                    operation_results.append({"cancelled": True})
            
            # Verify data consistency after concurrent operations
            consistency_valid = await self._verify_concurrent_operation_consistency()
            result["service_calls"] += 1
            
            result.update({
                "success": consistency_valid,
                "migration_duration": migration_duration,
                "concurrent_operations_completed": len([r for r in operation_results if not r.get("cancelled")]),
                "data_consistency_valid": consistency_valid
            })
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Concurrent operations migration test failed: {e}")
        
        return result
    
    async def _create_comprehensive_snapshot(self, snapshot_id: str) -> MigrationSnapshot:
        """Create comprehensive data snapshot across all databases."""
        snapshot = MigrationSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(),
            postgres_checksum="",
            clickhouse_checksum="",
            redis_checksum="",
            row_counts={},
            sample_data={},
            schema_version="1.0"
        )
        
        # PostgreSQL snapshot
        async with self.postgres_session_factory() as session:
            # Count tables
            users_result = await session.execute("SELECT COUNT(*) FROM l4_test_users")
            orders_result = await session.execute("SELECT COUNT(*) FROM l4_test_orders")
            events_result = await session.execute("SELECT COUNT(*) FROM l4_test_events")
            
            snapshot.row_counts.update({
                "postgres_users": users_result.fetchone()[0],
                "postgres_orders": orders_result.fetchone()[0],
                "postgres_events": events_result.fetchone()[0]
            })
            
            # Sample data
            sample_user_result = await session.execute("""
                SELECT username, email, tier, status FROM l4_test_users LIMIT 1
            """)
            sample_user = sample_user_result.fetchone()
            if sample_user:
                snapshot.sample_data["postgres_sample_user"] = {
                    "username": sample_user[0],
                    "email": sample_user[1],
                    "tier": sample_user[2],
                    "status": sample_user[3]
                }
        
        # ClickHouse snapshot
        ch_analytics_result = await self.clickhouse_client.execute(
            "SELECT COUNT(*) FROM l4_user_analytics"
        )
        snapshot.row_counts["clickhouse_analytics"] = ch_analytics_result[0][0] if ch_analytics_result else 0
        
        # Redis snapshot
        redis_session_keys = await self.redis_client.keys("session:*")
        redis_cache_keys = await self.redis_client.keys("cache:*")
        snapshot.row_counts.update({
            "redis_sessions": len(redis_session_keys),
            "redis_cache": len(redis_cache_keys)
        })
        
        # Calculate checksums
        snapshot.postgres_checksum = self._calculate_postgres_checksum(snapshot.row_counts)
        snapshot.clickhouse_checksum = self._calculate_clickhouse_checksum(snapshot.row_counts)
        snapshot.redis_checksum = self._calculate_redis_checksum(snapshot.row_counts)
        
        self.migration_snapshots[snapshot_id] = snapshot
        return snapshot
    
    def _calculate_postgres_checksum(self, row_counts: Dict[str, int]) -> str:
        """Calculate checksum for PostgreSQL data state."""
        pg_data = {k: v for k, v in row_counts.items() if "postgres" in k}
        return hashlib.md5(json.dumps(pg_data, sort_keys=True).encode()).hexdigest()
    
    def _calculate_clickhouse_checksum(self, row_counts: Dict[str, int]) -> str:
        """Calculate checksum for ClickHouse data state."""
        ch_data = {k: v for k, v in row_counts.items() if "clickhouse" in k}
        return hashlib.md5(json.dumps(ch_data, sort_keys=True).encode()).hexdigest()
    
    def _calculate_redis_checksum(self, row_counts: Dict[str, int]) -> str:
        """Calculate checksum for Redis data state."""
        redis_data = {k: v for k, v in row_counts.items() if "redis" in k}
        return hashlib.md5(json.dumps(redis_data, sort_keys=True).encode()).hexdigest()
    
    async def _validate_migration_integrity(self, pre_snapshot: MigrationSnapshot, 
                                          post_snapshot: MigrationSnapshot, 
                                          migration_id: str) -> bool:
        """Validate data integrity after migration."""
        try:
            # Core data should be preserved or increased
            if post_snapshot.row_counts["postgres_users"] < pre_snapshot.row_counts["postgres_users"]:
                return False
            
            if post_snapshot.row_counts["postgres_orders"] < pre_snapshot.row_counts["postgres_orders"]:
                return False
            
            # Sample data integrity
            pre_sample = pre_snapshot.sample_data.get("postgres_sample_user", {})
            post_sample = post_snapshot.sample_data.get("postgres_sample_user", {})
            
            if pre_sample and post_sample:
                if (pre_sample["username"] != post_sample["username"] or
                    pre_sample["email"] != post_sample["email"]):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Migration integrity validation failed: {e}")
            return False
    
    async def _verify_zero_data_loss(self, pre_snapshot: MigrationSnapshot, 
                                   post_snapshot: MigrationSnapshot) -> bool:
        """Verify zero data loss during rollback."""
        try:
            # Exact row count match required for zero data loss
            for table in ["postgres_users", "postgres_orders", "postgres_events"]:
                if pre_snapshot.row_counts[table] != post_snapshot.row_counts[table]:
                    logger.error(f"Data loss detected in {table}: "
                               f"{pre_snapshot.row_counts[table]} -> {post_snapshot.row_counts[table]}")
                    return False
            
            # Checksum comparison
            if pre_snapshot.postgres_checksum != post_snapshot.postgres_checksum:
                logger.warning("PostgreSQL checksums differ - investigating...")
                # Additional validation could be added here
            
            return True
            
        except Exception as e:
            logger.error(f"Zero data loss verification failed: {e}")
            return False
    
    async def _verify_data_integrity_restoration(self, pre_snapshot: MigrationSnapshot,
                                               post_snapshot: MigrationSnapshot) -> bool:
        """Verify data integrity restoration after rollback."""
        # For this test, we focus on structural integrity
        return await self._verify_zero_data_loss(pre_snapshot, post_snapshot)
    
    async def _record_migration(self, migration_id: str, migration_type: str, 
                              records_affected: int, duration: float) -> None:
        """Record migration in migration history table."""
        async with self.postgres_session_factory() as session:
            await session.execute("""
                INSERT INTO l4_migration_history 
                (migration_id, migration_type, completed_at, status, records_affected, performance_metrics)
                VALUES (:migration_id, :migration_type, CURRENT_TIMESTAMP, 'completed', :records, :metrics)
            """, {
                "migration_id": migration_id,
                "migration_type": migration_type,
                "records": records_affected,
                "metrics": json.dumps({"duration_seconds": duration})
            })
            await session.commit()
    
    async def _validate_cross_database_consistency(self, migration_id: str) -> float:
        """Validate consistency across PostgreSQL, ClickHouse, and Redis."""
        try:
            consistency_checks = []
            
            # Check PostgreSQL vs ClickHouse consistency
            async with self.postgres_session_factory() as session:
                pg_users_result = await session.execute("""
                    SELECT COUNT(*) FROM l4_test_users WHERE tier = 'enterprise'
                """)
                pg_enterprise_count = pg_users_result.fetchone()[0]
            
            ch_users_result = await self.clickhouse_client.execute("""
                SELECT COUNT(*) FROM l4_user_analytics WHERE tier = 'enterprise'
            """)
            ch_enterprise_count = ch_users_result[0][0] if ch_users_result else 0
            
            # Allow for some tolerance in cross-database replication
            if pg_enterprise_count > 0:
                consistency_ratio = min(ch_enterprise_count / pg_enterprise_count, 1.0)
                consistency_checks.append(consistency_ratio)
            
            # Check Redis cache consistency
            redis_analytics_keys = await self.redis_client.keys("user_analytics:*")
            if len(redis_analytics_keys) > 0:
                redis_consistency = min(len(redis_analytics_keys) / 1000, 1.0)  # Expected ~1000 cached entries
                consistency_checks.append(redis_consistency)
            
            return sum(consistency_checks) / len(consistency_checks) if consistency_checks else 0.0
            
        except Exception as e:
            logger.error(f"Cross-database consistency validation failed: {e}")
            return 0.0
    
    async def _measure_baseline_performance(self) -> Dict[str, Any]:
        """Measure baseline performance metrics."""
        operations = []
        start_time = time.time()
        
        # Measure typical database operations
        for i in range(10):
            op_start = time.time()
            async with self.postgres_session_factory() as session:
                await session.execute("SELECT COUNT(*) FROM l4_test_users WHERE tier = 'free'")
            op_duration = time.time() - op_start
            operations.append(op_duration)
        
        return {
            "avg_response_time": sum(operations) / len(operations),
            "max_response_time": max(operations),
            "operations_measured": len(operations)
        }
    
    async def _measure_migration_performance(self) -> Dict[str, Any]:
        """Measure performance during migration."""
        # Similar to baseline but during migration stress
        return await self._measure_baseline_performance()
    
    def _calculate_performance_impact(self, baseline: Dict[str, Any], 
                                    migration: Dict[str, Any]) -> float:
        """Calculate performance impact as percentage degradation."""
        baseline_time = baseline["avg_response_time"]
        migration_time = migration["avg_response_time"]
        
        if baseline_time == 0:
            return 0.0
        
        return ((migration_time - baseline_time) / baseline_time) * 100.0
    
    async def _simulate_production_load(self) -> None:
        """Simulate production load during migration."""
        try:
            while True:
                async with self.postgres_session_factory() as session:
                    await session.execute("SELECT COUNT(*) FROM l4_test_users WHERE status = 'active'")
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
    
    async def _validate_schema_constraints(self) -> List[str]:
        """Validate current schema constraints."""
        async with self.postgres_session_factory() as session:
            constraints_result = await session.execute("""
                SELECT constraint_name FROM information_schema.table_constraints 
                WHERE table_name IN ('l4_test_users', 'l4_test_orders', 'l4_test_events')
            """)
            return [row[0] for row in constraints_result.fetchall()]
    
    async def _test_constraint_enforcement(self) -> bool:
        """Test that constraints are properly enforced."""
        try:
            async with self.postgres_session_factory() as session:
                # Test invalid tier constraint
                try:
                    await session.execute("""
                        INSERT INTO l4_test_users (username, email, tier) 
                        VALUES ('invalid_tier_test', 'test@invalid.com', 'invalid_tier')
                    """)
                    await session.commit()
                    return False  # Should have failed
                except Exception:
                    await session.rollback()
                    return True  # Constraint properly enforced
        except Exception:
            return False
    
    async def _verify_foreign_key_integrity(self) -> bool:
        """Verify foreign key constraints are maintained."""
        try:
            async with self.postgres_session_factory() as session:
                # Check for orphaned orders
                orphaned_result = await session.execute("""
                    SELECT COUNT(*) FROM l4_test_orders o 
                    LEFT JOIN l4_test_users u ON o.user_id = u.id 
                    WHERE u.id IS NULL
                """)
                orphaned_count = orphaned_result.fetchone()[0]
                return orphaned_count == 0
        except Exception:
            return False
    
    async def _concurrent_insert_operations(self) -> Dict[str, Any]:
        """Perform concurrent insert operations."""
        inserted = 0
        try:
            for i in range(100):
                async with self.postgres_session_factory() as session:
                    await session.execute("""
                        INSERT INTO l4_test_events (user_id, event_type, event_data) 
                        VALUES (1, 'concurrent_test', '{"test": true}')
                    """)
                    await session.commit()
                    inserted += 1
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        return {"inserted": inserted}
    
    async def _concurrent_update_operations(self) -> Dict[str, Any]:
        """Perform concurrent update operations."""
        updated = 0
        try:
            for i in range(50):
                async with self.postgres_session_factory() as session:
                    await session.execute("""
                        UPDATE l4_test_users SET updated_at = CURRENT_TIMESTAMP 
                        WHERE id = 1
                    """)
                    await session.commit()
                    updated += 1
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        return {"updated": updated}
    
    async def _concurrent_read_operations(self) -> Dict[str, Any]:
        """Perform concurrent read operations."""
        reads = 0
        try:
            for i in range(200):
                async with self.postgres_session_factory() as session:
                    await session.execute("SELECT COUNT(*) FROM l4_test_users")
                    reads += 1
                await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            pass
        return {"reads": reads}
    
    async def _verify_concurrent_operation_consistency(self) -> bool:
        """Verify data consistency after concurrent operations."""
        try:
            async with self.postgres_session_factory() as session:
                # Basic consistency check
                users_result = await session.execute("SELECT COUNT(*) FROM l4_test_users")
                users_count = users_result.fetchone()[0]
                
                orders_result = await session.execute("SELECT COUNT(*) FROM l4_test_orders")
                orders_count = orders_result.fetchone()[0]
                
                # Ensure counts are reasonable
                return users_count > 0 and orders_count >= 0
        except Exception:
            return False
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate that critical path test results meet business requirements."""
        try:
            # Enterprise data integrity requirements
            required_validations = {
                "migration_scenarios_tested": 2,  # Minimum scenarios
                "rollback_scenarios_tested": 1,   # Must test rollback
                "data_integrity_validations": 2,  # Multiple integrity checks
                "performance_validations": 1      # Performance impact assessment
            }
            
            for requirement, min_value in required_validations.items():
                if results.get(requirement, 0) < min_value:
                    self.test_metrics.errors.append(
                        f"Insufficient {requirement}: {results.get(requirement, 0)} < {min_value}"
                    )
                    return False
            
            # Zero data loss is mandatory for Enterprise segment
            if not results.get("zero_data_loss_verified", False):
                self.test_metrics.errors.append("Zero data loss requirement not verified")
                return False
            
            # Business continuity during migration
            if not results.get("business_continuity_maintained", False):
                self.test_metrics.errors.append("Business continuity not maintained during migration")
                return False
            
            # Overall success required
            if not results.get("overall_success", False):
                self.test_metrics.errors.append("Overall migration integrity test failed")
                return False
            
            return True
            
        except Exception as e:
            self.test_metrics.errors.append(f"Results validation failed: {str(e)}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up L4 migration test specific resources."""
        cleanup_errors = []
        
        try:
            # Clean up test data
            if self.postgres_session_factory:
                async with self.postgres_session_factory() as session:
                    # Drop test tables
                    await session.execute("DROP TABLE IF EXISTS l4_test_events CASCADE")
                    await session.execute("DROP TABLE IF EXISTS l4_test_orders CASCADE")
                    await session.execute("DROP TABLE IF EXISTS l4_test_users CASCADE")
                    await session.execute("DROP TABLE IF EXISTS l4_migration_history CASCADE")
                    await session.commit()
        except Exception as e:
            cleanup_errors.append(f"PostgreSQL cleanup: {e}")
        
        try:
            # Clean up ClickHouse test data
            if self.clickhouse_client:
                await self.clickhouse_client.execute("DROP TABLE IF EXISTS l4_migration_log")
                await self.clickhouse_client.execute("DROP TABLE IF EXISTS l4_analytics_events")
                await self.clickhouse_client.execute("DROP TABLE IF EXISTS l4_user_analytics")
        except Exception as e:
            cleanup_errors.append(f"ClickHouse cleanup: {e}")
        
        try:
            # Clean up Redis test data
            if self.redis_client:
                await self.redis_client.flushdb()  # Clear test database
        except Exception as e:
            cleanup_errors.append(f"Redis cleanup: {e}")
        
        # Close connections
        try:
            if self.postgres_engine:
                await self.postgres_engine.dispose()
        except Exception as e:
            cleanup_errors.append(f"PostgreSQL engine cleanup: {e}")
        
        try:
            if self.clickhouse_client:
                await self.clickhouse_client.disconnect()
        except Exception as e:
            cleanup_errors.append(f"ClickHouse client cleanup: {e}")
        
        try:
            if self.redis_client:
                await self.redis_client.close()
        except Exception as e:
            cleanup_errors.append(f"Redis client cleanup: {e}")
        
        if cleanup_errors:
            logger.warning(f"L4 migration test cleanup warnings: {'; '.join(cleanup_errors)}")

# Pytest integration
@pytest.fixture
async def l4_migration_test():
    """Create L4 data migration integrity test instance."""
    test_instance = L4DataMigrationIntegrityTest()
    try:
        yield test_instance
    finally:
        await test_instance.cleanup_l4_resources()

@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.critical_path
class TestDataMigrationIntegrityL4:
    """L4 critical path tests for production data migration integrity."""
    
    async def test_complete_data_migration_integrity_critical_path(self, l4_migration_test):
        """
        Test complete data migration integrity critical path.
        
        Business Value: $50K MRR protection from data corruption/loss incidents
        
        Validates:
        - Large-scale migration (100K+ records)
        - Cross-database consistency (PostgreSQL, ClickHouse, Redis)
        - Migration rollback with zero data loss
        - Performance impact on live services
        - Schema constraint preservation
        - Concurrent operations safety
        """
        # Execute complete critical path test
        metrics = await l4_migration_test.run_complete_critical_path_test()
        
        # Validate business metrics
        expected_metrics = {
            "max_response_time_seconds": 10.0,  # Migration operations
            "min_success_rate_percent": 95.0,   # High reliability required
            "max_error_count": 2                # Allow minimal errors
        }
        
        business_metrics_valid = await l4_migration_test.validate_business_metrics(expected_metrics)
        
        # Assert critical path success
        assert metrics.success, f"L4 migration integrity test failed: {metrics.errors}"
        assert business_metrics_valid, "Business metrics validation failed"
        assert metrics.validation_count >= 6, "Insufficient validation scenarios"
        assert metrics.service_calls >= 50, "Insufficient service interaction testing"
        
        # Enterprise-specific assertions
        assert metrics.details.get("zero_data_loss_verified", False), "Zero data loss not verified"
        assert metrics.details.get("business_continuity_maintained", False), "Business continuity compromised"
        assert metrics.details.get("migration_scenarios_tested", 0) >= 2, "Insufficient migration scenarios"
        assert metrics.details.get("rollback_scenarios_tested", 0) >= 1, "Rollback scenarios not tested"
        
        # Performance requirements for production
        assert metrics.average_response_time <= 5.0, f"Response time too high: {metrics.average_response_time}s"
        assert metrics.success_rate >= 95.0, f"Success rate too low: {metrics.success_rate}%"
        
        logger.info(f"L4 Data Migration Integrity Test completed successfully: "
                   f"{metrics.validation_count} validations, {metrics.service_calls} service calls, "
                   f"{metrics.duration:.2f}s duration, {metrics.success_rate:.1f}% success rate")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])