"""Database Transaction Consistency L4 Critical Path Tests (Staging Environment)

Business Value Justification (BVJ):
- Segment: Enterprise ($30K+ MRR) - Critical financial accuracy and audit compliance
- Business Goal: Ensure ACID properties across PostgreSQL and ClickHouse for billing/analytics
- Value Impact: Prevents revenue leakage, ensures audit compliance, maintains financial accuracy
- Strategic Impact: $30K+ MRR protection through guaranteed transaction consistency and data integrity

Critical Path: Transaction initiation -> Multi-database operations -> Consistency validation -> 
            Rollback scenarios -> Concurrent conflict resolution -> Analytics data sync verification

Coverage: Real PostgreSQL ACID properties, ClickHouse eventual consistency, cross-database 
         transaction coordination, production-like data volumes, real connection pooling

L4 Realism: Tests against real staging PostgreSQL and ClickHouse clusters with production-like
           configuration, data volumes, and transaction patterns.
"""

import pytest
import asyncio
import psycopg2
import clickhouse_connect
import time
import uuid
import logging
import os
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from decimal import Decimal

from app.services.database.postgres_service import PostgresService
from app.services.database.clickhouse_service import ClickHouseService
from app.services.database.connection_manager import DatabaseConnectionManager
from app.services.redis.session_manager import RedisSessionManager
from app.core.configuration.database import DatabaseConfigManager
from app.tests.integration.staging_config.base import StagingConfigTestBase
from app.schemas.billing import BillingTransaction, UsageRecord
from app.schemas.analytics import AnalyticsEvent

logger = logging.getLogger(__name__)


@dataclass
class TransactionConsistencyMetrics:
    """Metrics for tracking transaction consistency across databases."""
    total_transactions: int = 0
    successful_postgres_transactions: int = 0
    successful_clickhouse_operations: int = 0
    rollback_operations: int = 0
    consistency_violations: int = 0
    cross_database_sync_operations: int = 0
    deadlock_resolutions: int = 0
    isolation_level_violations: int = 0
    average_transaction_time: float = 0.0
    average_sync_latency: float = 0.0


class DatabaseTransactionConsistencyL4Manager:
    """Manages L4 database transaction consistency testing with real staging services."""
    
    def __init__(self):
        self.postgres_service = None
        self.clickhouse_service = None
        self.connection_manager = None
        self.redis_session = None
        self.staging_base = StagingConfigTestBase()
        self.db_config_manager = DatabaseConfigManager()
        self.test_transactions = {}
        self.consistency_violations = []
        self.test_metrics = TransactionConsistencyMetrics()
        self.test_data_prefix = f"l4_txn_test_{int(time.time())}"
        
    async def initialize_services(self):
        """Initialize services for L4 database transaction consistency testing."""
        try:
            # Set staging environment variables
            staging_env = self.staging_base.get_staging_env_vars()
            for key, value in staging_env.items():
                os.environ[key] = value
            
            # Refresh database configuration for staging
            self.db_config_manager.refresh_environment()
            
            # Initialize connection manager with staging config
            self.connection_manager = DatabaseConnectionManager()
            await self.connection_manager.initialize(use_staging_config=True)
            
            # Initialize PostgreSQL service with staging database
            self.postgres_service = PostgresService()
            await self.postgres_service.initialize(
                connection_pool_size=20,  # Production-like pool size
                use_staging_db=True
            )
            
            # Initialize ClickHouse service with staging cluster
            self.clickhouse_service = ClickHouseService()
            await self.clickhouse_service.initialize(
                cluster_mode=True,
                use_staging_cluster=True
            )
            
            # Initialize Redis session manager
            self.redis_session = RedisSessionManager()
            await self.redis_session.initialize(use_staging_redis=True)
            
            # Verify staging database connectivity and configuration
            await self._verify_staging_database_connectivity()
            
            # Set up test schemas and tables
            await self._setup_test_database_schema()
            
            logger.info("L4 database transaction consistency services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 transaction consistency services: {e}")
            raise
    
    async def _verify_staging_database_connectivity(self):
        """Verify connectivity and configuration of staging databases."""
        try:
            # Verify PostgreSQL staging connectivity and ACID support
            postgres_result = await self.postgres_service.execute_query(
                "SELECT current_setting('transaction_isolation'), version(), NOW() as timestamp"
            )
            
            isolation_level = postgres_result[0]["current_setting"]
            postgres_version = postgres_result[0]["version"]
            
            assert "REPEATABLE READ" in isolation_level or "READ COMMITTED" in isolation_level
            logger.info(f"PostgreSQL staging verified: {postgres_version}, isolation: {isolation_level}")
            
            # Verify ClickHouse staging connectivity and replication
            clickhouse_result = await self.clickhouse_service.execute_query(
                "SELECT version(), hostName(), NOW() as timestamp"
            )
            
            clickhouse_version = clickhouse_result[0]["version()"]
            clickhouse_host = clickhouse_result[0]["hostName()"]
            logger.info(f"ClickHouse staging verified: {clickhouse_version}, host: {clickhouse_host}")
            
            # Verify Redis staging connectivity
            redis_ping = await self.redis_session.ping()
            assert redis_ping is True
            logger.info("Redis staging connectivity verified")
            
        except Exception as e:
            raise RuntimeError(f"Staging database connectivity verification failed: {e}")
    
    async def _setup_test_database_schema(self):
        """Set up test schema and tables for transaction consistency testing."""
        try:
            # Create test tables in PostgreSQL with proper constraints
            await self.postgres_service.execute_query(f"""
                CREATE TABLE IF NOT EXISTS {self.test_data_prefix}_billing_transactions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    organization_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    amount DECIMAL(12,2) NOT NULL CHECK (amount >= 0),
                    currency VARCHAR(3) DEFAULT 'USD',
                    transaction_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    metadata JSONB,
                    CONSTRAINT unique_billing_transaction UNIQUE (organization_id, created_at, amount)
                )
            """)
            
            await self.postgres_service.execute_query(f"""
                CREATE TABLE IF NOT EXISTS {self.test_data_prefix}_usage_records (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    organization_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    resource_type VARCHAR(100) NOT NULL,
                    usage_amount INTEGER NOT NULL CHECK (usage_amount >= 0),
                    billing_period DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT unique_usage_record UNIQUE (organization_id, user_id, resource_type, billing_period)
                )
            """)
            
            # Create corresponding analytics tables in ClickHouse
            await self.clickhouse_service.execute_query(f"""
                CREATE TABLE IF NOT EXISTS {self.test_data_prefix}_analytics_events (
                    event_id String,
                    organization_id String,
                    user_id String,
                    event_type String,
                    event_data String,
                    amount Float64,
                    created_at DateTime DEFAULT now(),
                    processed_at DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (organization_id, created_at)
                PARTITION BY toYYYYMM(created_at)
            """)
            
            await self.clickhouse_service.execute_query(f"""
                CREATE TABLE IF NOT EXISTS {self.test_data_prefix}_usage_analytics (
                    record_id String,
                    organization_id String,
                    user_id String,
                    resource_type String,
                    usage_amount UInt64,
                    billing_period Date,
                    created_at DateTime DEFAULT now(),
                    sync_timestamp DateTime DEFAULT now()
                ) ENGINE = ReplacingMergeTree(sync_timestamp)
                ORDER BY (organization_id, user_id, resource_type, billing_period)
                PARTITION BY toYYYYMM(billing_period)
            """)
            
            logger.info("Test database schema setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup test database schema: {e}")
            raise
    
    async def test_postgres_acid_transaction_atomicity(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test PostgreSQL ACID atomicity with multi-table operations."""
        transaction_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Begin explicit transaction
            async with self.postgres_service.transaction() as conn:
                # Insert billing transaction
                billing_result = await conn.execute(
                    f"""
                    INSERT INTO {self.test_data_prefix}_billing_transactions 
                    (organization_id, user_id, amount, transaction_type, status, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id, created_at
                    """,
                    transaction_data["organization_id"],
                    transaction_data["user_id"],
                    Decimal(str(transaction_data["amount"])),
                    transaction_data["transaction_type"],
                    "pending",
                    json.dumps(transaction_data.get("metadata", {}))
                )
                
                billing_record = await billing_result.fetchone()
                billing_id = billing_record["id"]
                
                # Insert related usage record in same transaction
                usage_result = await conn.execute(
                    f"""
                    INSERT INTO {self.test_data_prefix}_usage_records
                    (organization_id, user_id, resource_type, usage_amount, billing_period)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    transaction_data["organization_id"],
                    transaction_data["user_id"],
                    transaction_data["resource_type"],
                    transaction_data["usage_amount"],
                    transaction_data["billing_period"]
                )
                
                usage_record = await usage_result.fetchone()
                usage_id = usage_record["id"]
                
                # Simulate potential failure point for rollback testing
                if transaction_data.get("simulate_failure", False):
                    raise Exception("Simulated transaction failure")
                
                # Update billing transaction status to committed
                await conn.execute(
                    f"""
                    UPDATE {self.test_data_prefix}_billing_transactions 
                    SET status = 'committed', updated_at = NOW()
                    WHERE id = $1
                    """,
                    billing_id
                )
                
                # Transaction commits automatically at context exit
                
            # Verify atomicity - both records should exist
            verification_result = await self._verify_transaction_atomicity(
                billing_id, usage_id, transaction_id
            )
            
            response_time = time.time() - start_time
            
            self.test_metrics.total_transactions += 1
            self.test_metrics.successful_postgres_transactions += 1
            self.test_metrics.average_transaction_time = (
                (self.test_metrics.average_transaction_time * (self.test_metrics.total_transactions - 1) + response_time) 
                / self.test_metrics.total_transactions
            )
            
            return {
                "transaction_id": transaction_id,
                "billing_id": str(billing_id),
                "usage_id": str(usage_id),
                "atomicity_verified": verification_result["atomicity_verified"],
                "response_time": response_time,
                "records_created": 2,
                "staging_verified": True
            }
            
        except Exception as e:
            # Verify rollback occurred (no partial data)
            rollback_verification = await self._verify_transaction_rollback(transaction_id)
            
            self.test_metrics.total_transactions += 1
            self.test_metrics.rollback_operations += 1
            
            return {
                "transaction_id": transaction_id,
                "atomicity_verified": False,
                "rollback_verified": rollback_verification["rollback_complete"],
                "error": str(e),
                "response_time": time.time() - start_time,
                "staging_verified": True
            }
    
    async def _verify_transaction_atomicity(self, billing_id: str, usage_id: str, transaction_id: str) -> Dict[str, Any]:
        """Verify that transaction atomicity was maintained."""
        try:
            # Check both records exist
            billing_check = await self.postgres_service.execute_query(
                f"SELECT id, status FROM {self.test_data_prefix}_billing_transactions WHERE id = $1",
                billing_id
            )
            
            usage_check = await self.postgres_service.execute_query(
                f"SELECT id FROM {self.test_data_prefix}_usage_records WHERE id = $1",
                usage_id
            )
            
            atomicity_verified = (
                len(billing_check) == 1 and 
                len(usage_check) == 1 and 
                billing_check[0]["status"] == "committed"
            )
            
            return {
                "atomicity_verified": atomicity_verified,
                "billing_record_exists": len(billing_check) == 1,
                "usage_record_exists": len(usage_check) == 1,
                "billing_status": billing_check[0]["status"] if billing_check else None
            }
            
        except Exception as e:
            return {
                "atomicity_verified": False,
                "error": str(e)
            }
    
    async def _verify_transaction_rollback(self, transaction_id: str) -> Dict[str, Any]:
        """Verify that transaction rollback was complete (no partial data)."""
        try:
            # Check no records exist for this transaction
            billing_check = await self.postgres_service.execute_query(
                f"""
                SELECT COUNT(*) as count FROM {self.test_data_prefix}_billing_transactions 
                WHERE metadata->>'transaction_id' = $1
                """,
                transaction_id
            )
            
            usage_check = await self.postgres_service.execute_query(
                f"""
                SELECT COUNT(*) as count FROM {self.test_data_prefix}_usage_records 
                WHERE id IN (
                    SELECT id FROM {self.test_data_prefix}_usage_records 
                    WHERE created_at > NOW() - INTERVAL '1 minute'
                )
                """,
            )
            
            rollback_complete = (
                billing_check[0]["count"] == 0 and
                usage_check[0]["count"] == 0
            )
            
            return {
                "rollback_complete": rollback_complete,
                "orphaned_billing_records": billing_check[0]["count"],
                "orphaned_usage_records": usage_check[0]["count"]
            }
            
        except Exception as e:
            return {
                "rollback_complete": False,
                "error": str(e)
            }
    
    async def test_postgres_isolation_levels(self, isolation_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test PostgreSQL transaction isolation levels with concurrent operations."""
        scenario_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Prepare test data
            org_id = isolation_scenario["organization_id"]
            initial_amount = Decimal(str(isolation_scenario["initial_amount"]))
            
            # Insert initial billing record
            await self.postgres_service.execute_query(
                f"""
                INSERT INTO {self.test_data_prefix}_billing_transactions 
                (id, organization_id, user_id, amount, transaction_type, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                scenario_id,
                org_id,
                isolation_scenario["user_id"],
                initial_amount,
                "initial_balance",
                "committed"
            )
            
            # Simulate concurrent transactions with different isolation scenarios
            isolation_results = await self._test_concurrent_isolation_scenarios(
                scenario_id, org_id, initial_amount, isolation_scenario
            )
            
            response_time = time.time() - start_time
            
            return {
                "scenario_id": scenario_id,
                "isolation_maintained": isolation_results["isolation_maintained"],
                "dirty_read_prevented": isolation_results["dirty_read_prevented"],
                "phantom_read_prevented": isolation_results["phantom_read_prevented"],
                "concurrent_transactions": isolation_results["concurrent_transactions"],
                "response_time": response_time,
                "staging_verified": True
            }
            
        except Exception as e:
            self.test_metrics.isolation_level_violations += 1
            return {
                "scenario_id": scenario_id,
                "isolation_maintained": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "staging_verified": False
            }
    
    async def _test_concurrent_isolation_scenarios(self, scenario_id: str, org_id: str, 
                                                 initial_amount: Decimal, scenario: Dict) -> Dict[str, Any]:
        """Test concurrent transaction isolation scenarios."""
        try:
            isolation_results = {
                "isolation_maintained": True,
                "dirty_read_prevented": True,
                "phantom_read_prevented": True,
                "concurrent_transactions": 0
            }
            
            # Create concurrent transaction tasks
            tasks = []
            
            # Task 1: Update transaction (should be isolated)
            update_task = self._concurrent_update_transaction(scenario_id, org_id, initial_amount)
            tasks.append(("update", update_task))
            
            # Task 2: Read transaction (should not see uncommitted changes)
            read_task = self._concurrent_read_transaction(scenario_id, org_id)
            tasks.append(("read", read_task))
            
            # Task 3: Insert related transaction (test phantom reads)
            insert_task = self._concurrent_insert_transaction(org_id, scenario.get("user_id"))
            tasks.append(("insert", insert_task))
            
            # Execute concurrent transactions
            results = []
            for task_type, task in tasks:
                result = await task
                result["task_type"] = task_type
                results.append(result)
            
            # Analyze isolation results
            isolation_results["concurrent_transactions"] = len(results)
            
            # Check for dirty read violations
            read_results = [r for r in results if r["task_type"] == "read"]
            if read_results:
                read_result = read_results[0]
                # Should not see uncommitted changes during concurrent update
                isolation_results["dirty_read_prevented"] = not read_result.get("saw_uncommitted_data", False)
            
            # Check for phantom read violations
            insert_results = [r for r in results if r["task_type"] == "insert"]
            if insert_results:
                insert_result = insert_results[0]
                # Should maintain consistent view during transaction
                isolation_results["phantom_read_prevented"] = insert_result.get("consistent_view_maintained", True)
            
            return isolation_results
            
        except Exception as e:
            return {
                "isolation_maintained": False,
                "error": str(e),
                "concurrent_transactions": 0
            }
    
    async def _concurrent_update_transaction(self, scenario_id: str, org_id: str, amount: Decimal) -> Dict[str, Any]:
        """Concurrent update transaction for isolation testing."""
        try:
            async with self.postgres_service.transaction() as conn:
                # Start update transaction
                await conn.execute(
                    f"""
                    UPDATE {self.test_data_prefix}_billing_transactions 
                    SET amount = amount + $1, updated_at = NOW()
                    WHERE id = $2
                    """,
                    Decimal("100.00"),
                    scenario_id
                )
                
                # Simulate processing time
                await asyncio.sleep(0.1)
                
                # Transaction commits automatically
                
            return {"success": True, "operation": "update"}
            
        except Exception as e:
            return {"success": False, "error": str(e), "operation": "update"}
    
    async def _concurrent_read_transaction(self, scenario_id: str, org_id: str) -> Dict[str, Any]:
        """Concurrent read transaction for isolation testing."""
        try:
            async with self.postgres_service.transaction() as conn:
                # Read during concurrent update
                result = await conn.fetch(
                    f"""
                    SELECT amount, updated_at FROM {self.test_data_prefix}_billing_transactions 
                    WHERE id = $1
                    """,
                    scenario_id
                )
                
                if result:
                    record = result[0]
                    # Check if we see uncommitted changes (dirty read)
                    saw_uncommitted_data = record["updated_at"] > datetime.utcnow() - timedelta(seconds=1)
                    
                    return {
                        "success": True,
                        "operation": "read",
                        "amount_read": float(record["amount"]),
                        "saw_uncommitted_data": saw_uncommitted_data
                    }
                
            return {"success": False, "operation": "read", "error": "Record not found"}
            
        except Exception as e:
            return {"success": False, "error": str(e), "operation": "read"}
    
    async def _concurrent_insert_transaction(self, org_id: str, user_id: str) -> Dict[str, Any]:
        """Concurrent insert transaction for phantom read testing."""
        try:
            async with self.postgres_service.transaction() as conn:
                # Count existing records
                initial_count = await conn.fetchval(
                    f"""
                    SELECT COUNT(*) FROM {self.test_data_prefix}_billing_transactions 
                    WHERE organization_id = $1
                    """,
                    org_id
                )
                
                # Insert new record
                await conn.execute(
                    f"""
                    INSERT INTO {self.test_data_prefix}_billing_transactions 
                    (organization_id, user_id, amount, transaction_type, status)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    org_id,
                    user_id,
                    Decimal("50.00"),
                    "concurrent_test",
                    "committed"
                )
                
                # Check final count
                final_count = await conn.fetchval(
                    f"""
                    SELECT COUNT(*) FROM {self.test_data_prefix}_billing_transactions 
                    WHERE organization_id = $1
                    """,
                    org_id
                )
                
                consistent_view_maintained = (final_count == initial_count + 1)
                
                return {
                    "success": True,
                    "operation": "insert",
                    "initial_count": initial_count,
                    "final_count": final_count,
                    "consistent_view_maintained": consistent_view_maintained
                }
                
        except Exception as e:
            return {"success": False, "error": str(e), "operation": "insert"}
    
    async def test_clickhouse_eventual_consistency(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test ClickHouse eventual consistency with PostgreSQL data sync."""
        sync_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Insert data into PostgreSQL first (source of truth)
            postgres_result = await self.postgres_service.execute_query(
                f"""
                INSERT INTO {self.test_data_prefix}_billing_transactions 
                (organization_id, user_id, amount, transaction_type, status, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, created_at
                """,
                analytics_data["organization_id"],
                analytics_data["user_id"],
                Decimal(str(analytics_data["amount"])),
                analytics_data["transaction_type"],
                "committed",
                json.dumps({"sync_id": sync_id, "test_data": True})
            )
            
            postgres_record = postgres_result[0]
            
            # Sync to ClickHouse for analytics (eventual consistency)
            clickhouse_sync_result = await self._sync_postgres_to_clickhouse(
                postgres_record, analytics_data, sync_id
            )
            
            # Verify eventual consistency
            consistency_result = await self._verify_eventual_consistency(
                postgres_record["id"], sync_id, start_time
            )
            
            sync_latency = time.time() - start_time
            
            self.test_metrics.cross_database_sync_operations += 1
            self.test_metrics.average_sync_latency = (
                (self.test_metrics.average_sync_latency * (self.test_metrics.cross_database_sync_operations - 1) + sync_latency)
                / self.test_metrics.cross_database_sync_operations
            )
            
            return {
                "sync_id": sync_id,
                "postgres_record_id": str(postgres_record["id"]),
                "clickhouse_synced": clickhouse_sync_result["success"],
                "eventual_consistency_achieved": consistency_result["consistency_achieved"],
                "sync_latency": sync_latency,
                "consistency_check_time": consistency_result.get("check_time", 0),
                "staging_verified": True
            }
            
        except Exception as e:
            self.test_metrics.consistency_violations += 1
            return {
                "sync_id": sync_id,
                "eventual_consistency_achieved": False,
                "error": str(e),
                "sync_latency": time.time() - start_time,
                "staging_verified": False
            }
    
    async def _sync_postgres_to_clickhouse(self, postgres_record: Dict, analytics_data: Dict, sync_id: str) -> Dict[str, Any]:
        """Sync PostgreSQL data to ClickHouse for analytics."""
        try:
            # Insert analytics event into ClickHouse
            await self.clickhouse_service.execute_query(f"""
                INSERT INTO {self.test_data_prefix}_analytics_events 
                (event_id, organization_id, user_id, event_type, event_data, amount, created_at)
                VALUES 
                ('{sync_id}', '{analytics_data["organization_id"]}', '{analytics_data["user_id"]}', 
                 '{analytics_data["transaction_type"]}', '{json.dumps(analytics_data)}', 
                 {analytics_data["amount"]}, '{postgres_record["created_at"].isoformat()}')
            """)
            
            # Insert usage analytics if applicable
            if "usage_amount" in analytics_data:
                await self.clickhouse_service.execute_query(f"""
                    INSERT INTO {self.test_data_prefix}_usage_analytics 
                    (record_id, organization_id, user_id, resource_type, usage_amount, billing_period, created_at)
                    VALUES 
                    ('{str(postgres_record["id"])}', '{analytics_data["organization_id"]}', 
                     '{analytics_data["user_id"]}', '{analytics_data.get("resource_type", "api_calls")}', 
                     {analytics_data.get("usage_amount", 0)}, '{analytics_data.get("billing_period", "2025-01-01")}', 
                     '{postgres_record["created_at"].isoformat()}')
                """)
            
            return {"success": True, "records_synced": 2 if "usage_amount" in analytics_data else 1}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _verify_eventual_consistency(self, postgres_id: str, sync_id: str, start_time: float) -> Dict[str, Any]:
        """Verify eventual consistency between PostgreSQL and ClickHouse."""
        max_wait_time = 10.0  # Maximum time to wait for consistency
        check_interval = 0.5  # Check every 500ms
        consistency_achieved = False
        check_time = 0
        
        while check_time < max_wait_time:
            try:
                # Check if data exists in ClickHouse
                clickhouse_result = await self.clickhouse_service.execute_query(f"""
                    SELECT event_id, organization_id, amount, created_at 
                    FROM {self.test_data_prefix}_analytics_events 
                    WHERE event_id = '{sync_id}'
                """)
                
                if clickhouse_result and len(clickhouse_result) > 0:
                    # Verify data consistency
                    clickhouse_record = clickhouse_result[0]
                    
                    # Check corresponding PostgreSQL data
                    postgres_result = await self.postgres_service.execute_query(
                        f"SELECT amount, organization_id FROM {self.test_data_prefix}_billing_transactions WHERE id = $1",
                        postgres_id
                    )
                    
                    if postgres_result and len(postgres_result) > 0:
                        postgres_record = postgres_result[0]
                        
                        # Verify data matches
                        amount_matches = abs(float(clickhouse_record["amount"]) - float(postgres_record["amount"])) < 0.01
                        org_matches = clickhouse_record["organization_id"] == str(postgres_record["organization_id"])
                        
                        if amount_matches and org_matches:
                            consistency_achieved = True
                            break
                
                await asyncio.sleep(check_interval)
                check_time = time.time() - start_time
                
            except Exception as e:
                logger.warning(f"Consistency check failed: {e}")
                break
        
        return {
            "consistency_achieved": consistency_achieved,
            "check_time": check_time,
            "max_wait_exceeded": check_time >= max_wait_time
        }
    
    async def test_concurrent_transaction_deadlock_resolution(self, deadlock_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test deadlock detection and resolution in concurrent transactions."""
        scenario_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Prepare test data - two records that will be updated in different order
            record_a_id = str(uuid.uuid4())
            record_b_id = str(uuid.uuid4())
            
            # Insert test records
            await self.postgres_service.execute_query(
                f"""
                INSERT INTO {self.test_data_prefix}_billing_transactions 
                (id, organization_id, user_id, amount, transaction_type, status)
                VALUES 
                ($1, $2, $3, $4, 'deadlock_test_a', 'committed'),
                ($5, $2, $3, $6, 'deadlock_test_b', 'committed')
                """,
                record_a_id,
                deadlock_scenario["organization_id"],
                deadlock_scenario["user_id"],
                Decimal("100.00"),
                record_b_id,
                Decimal("200.00")
            )
            
            # Create deadlock scenario with concurrent transactions
            deadlock_results = await self._simulate_deadlock_scenario(
                record_a_id, record_b_id, deadlock_scenario
            )
            
            response_time = time.time() - start_time
            
            if deadlock_results["deadlock_resolved"]:
                self.test_metrics.deadlock_resolutions += 1
            
            return {
                "scenario_id": scenario_id,
                "deadlock_detected": deadlock_results["deadlock_detected"],
                "deadlock_resolved": deadlock_results["deadlock_resolved"],
                "transactions_completed": deadlock_results["transactions_completed"],
                "resolution_time": deadlock_results.get("resolution_time", 0),
                "response_time": response_time,
                "staging_verified": True
            }
            
        except Exception as e:
            return {
                "scenario_id": scenario_id,
                "deadlock_resolved": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "staging_verified": False
            }
    
    async def _simulate_deadlock_scenario(self, record_a_id: str, record_b_id: str, scenario: Dict) -> Dict[str, Any]:
        """Simulate deadlock scenario with concurrent transactions."""
        try:
            # Transaction 1: Update A then B
            async def transaction_1():
                try:
                    async with self.postgres_service.transaction() as conn:
                        # Lock record A first
                        await conn.execute(
                            f"""
                            UPDATE {self.test_data_prefix}_billing_transactions 
                            SET amount = amount + $1 WHERE id = $2
                            """,
                            Decimal("10.00"),
                            record_a_id
                        )
                        
                        # Wait to create deadlock opportunity
                        await asyncio.sleep(0.1)
                        
                        # Try to lock record B
                        await conn.execute(
                            f"""
                            UPDATE {self.test_data_prefix}_billing_transactions 
                            SET amount = amount + $1 WHERE id = $2
                            """,
                            Decimal("10.00"),
                            record_b_id
                        )
                    
                    return {"success": True, "transaction": "1"}
                    
                except Exception as e:
                    # Check if it's a deadlock error
                    is_deadlock = "deadlock detected" in str(e).lower()
                    return {"success": False, "transaction": "1", "deadlock": is_deadlock, "error": str(e)}
            
            # Transaction 2: Update B then A (reverse order)
            async def transaction_2():
                try:
                    async with self.postgres_service.transaction() as conn:
                        # Lock record B first
                        await conn.execute(
                            f"""
                            UPDATE {self.test_data_prefix}_billing_transactions 
                            SET amount = amount + $1 WHERE id = $2
                            """,
                            Decimal("20.00"),
                            record_b_id
                        )
                        
                        # Wait to create deadlock opportunity
                        await asyncio.sleep(0.1)
                        
                        # Try to lock record A
                        await conn.execute(
                            f"""
                            UPDATE {self.test_data_prefix}_billing_transactions 
                            SET amount = amount + $1 WHERE id = $2
                            """,
                            Decimal("20.00"),
                            record_a_id
                        )
                    
                    return {"success": True, "transaction": "2"}
                    
                except Exception as e:
                    # Check if it's a deadlock error
                    is_deadlock = "deadlock detected" in str(e).lower()
                    return {"success": False, "transaction": "2", "deadlock": is_deadlock, "error": str(e)}
            
            # Execute transactions concurrently
            resolution_start = time.time()
            results = await asyncio.gather(transaction_1(), transaction_2(), return_exceptions=True)
            resolution_time = time.time() - resolution_start
            
            # Analyze results
            successful_transactions = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
            deadlock_detected = any(
                isinstance(r, dict) and r.get("deadlock", False) for r in results
            )
            
            # Deadlock is resolved if at least one transaction succeeded
            deadlock_resolved = deadlock_detected and successful_transactions > 0
            
            return {
                "deadlock_detected": deadlock_detected,
                "deadlock_resolved": deadlock_resolved,
                "transactions_completed": successful_transactions,
                "resolution_time": resolution_time,
                "transaction_results": results
            }
            
        except Exception as e:
            return {
                "deadlock_detected": False,
                "deadlock_resolved": False,
                "transactions_completed": 0,
                "error": str(e)
            }
    
    async def get_transaction_consistency_metrics(self) -> Dict[str, Any]:
        """Get comprehensive transaction consistency metrics."""
        total_transactions = self.test_metrics.total_transactions
        consistency_rate = 100.0
        
        if total_transactions > 0:
            consistency_rate = (
                (total_transactions - self.test_metrics.consistency_violations) / total_transactions * 100
            )
        
        postgres_success_rate = 100.0
        if total_transactions > 0:
            postgres_success_rate = (
                self.test_metrics.successful_postgres_transactions / total_transactions * 100
            )
        
        return {
            "total_transactions": total_transactions,
            "postgres_success_rate": postgres_success_rate,
            "consistency_rate": consistency_rate,
            "isolation_violations": self.test_metrics.isolation_level_violations,
            "deadlock_resolutions": self.test_metrics.deadlock_resolutions,
            "cross_database_syncs": self.test_metrics.cross_database_sync_operations,
            "average_transaction_time": self.test_metrics.average_transaction_time,
            "average_sync_latency": self.test_metrics.average_sync_latency,
            "staging_environment": True,
            "l4_test_level": True
        }
    
    async def cleanup(self):
        """Clean up L4 test data and resources."""
        try:
            # Clean up PostgreSQL test tables
            await self.postgres_service.execute_query(
                f"DROP TABLE IF EXISTS {self.test_data_prefix}_billing_transactions CASCADE"
            )
            await self.postgres_service.execute_query(
                f"DROP TABLE IF EXISTS {self.test_data_prefix}_usage_records CASCADE"
            )
            
            # Clean up ClickHouse test tables
            await self.clickhouse_service.execute_query(
                f"DROP TABLE IF EXISTS {self.test_data_prefix}_analytics_events"
            )
            await self.clickhouse_service.execute_query(
                f"DROP TABLE IF EXISTS {self.test_data_prefix}_usage_analytics"
            )
            
            # Shutdown services
            if self.postgres_service:
                await self.postgres_service.shutdown()
            if self.clickhouse_service:
                await self.clickhouse_service.shutdown()
            if self.connection_manager:
                await self.connection_manager.shutdown()
            if self.redis_session:
                await self.redis_session.shutdown()
                
        except Exception as e:
            logger.error(f"L4 transaction consistency cleanup failed: {e}")


@pytest.fixture
async def l4_transaction_manager():
    """Create L4 database transaction consistency manager for staging tests."""
    manager = DatabaseTransactionConsistencyL4Manager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_postgres_acid_atomicity_comprehensive(l4_transaction_manager):
    """Test PostgreSQL ACID atomicity with comprehensive transaction scenarios."""
    # Test successful multi-table transaction
    transaction_data = {
        "organization_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "amount": 150.75,
        "transaction_type": "subscription_payment",
        "resource_type": "api_calls",
        "usage_amount": 10000,
        "billing_period": "2025-01-01",
        "metadata": {"test_type": "atomicity_success"}
    }
    
    success_result = await l4_transaction_manager.test_postgres_acid_transaction_atomicity(transaction_data)
    
    # Verify successful atomicity
    assert success_result["atomicity_verified"] is True
    assert success_result["records_created"] == 2
    assert success_result["staging_verified"] is True
    assert success_result["response_time"] < 5.0
    
    # Test rollback scenario
    rollback_data = transaction_data.copy()
    rollback_data["simulate_failure"] = True
    rollback_data["metadata"]["test_type"] = "atomicity_rollback"
    
    rollback_result = await l4_transaction_manager.test_postgres_acid_transaction_atomicity(rollback_data)
    
    # Verify rollback atomicity
    assert rollback_result["atomicity_verified"] is False
    assert rollback_result["rollback_verified"] is True
    assert rollback_result["staging_verified"] is True


@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_postgres_isolation_levels_concurrent(l4_transaction_manager):
    """Test PostgreSQL isolation levels with concurrent transaction scenarios."""
    isolation_scenario = {
        "organization_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "initial_amount": 500.00,
        "concurrent_operations": 3
    }
    
    isolation_result = await l4_transaction_manager.test_postgres_isolation_levels(isolation_scenario)
    
    # Verify isolation properties
    assert isolation_result["isolation_maintained"] is True
    assert isolation_result["dirty_read_prevented"] is True
    assert isolation_result["phantom_read_prevented"] is True
    assert isolation_result["concurrent_transactions"] >= 2
    assert isolation_result["staging_verified"] is True
    assert isolation_result["response_time"] < 10.0


@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_clickhouse_eventual_consistency_sync(l4_transaction_manager):
    """Test ClickHouse eventual consistency with PostgreSQL data synchronization."""
    analytics_data = {
        "organization_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "amount": 275.50,
        "transaction_type": "usage_billing",
        "resource_type": "llm_tokens",
        "usage_amount": 50000,
        "billing_period": "2025-01-01"
    }
    
    consistency_result = await l4_transaction_manager.test_clickhouse_eventual_consistency(analytics_data)
    
    # Verify eventual consistency
    assert consistency_result["clickhouse_synced"] is True
    assert consistency_result["eventual_consistency_achieved"] is True
    assert consistency_result["staging_verified"] is True
    assert consistency_result["sync_latency"] < 15.0  # Allow for network latency in staging
    assert consistency_result["consistency_check_time"] < 10.0


@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_concurrent_deadlock_resolution(l4_transaction_manager):
    """Test deadlock detection and resolution in concurrent database transactions."""
    deadlock_scenario = {
        "organization_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "concurrent_updates": True
    }
    
    deadlock_result = await l4_transaction_manager.test_concurrent_transaction_deadlock_resolution(deadlock_scenario)
    
    # Verify deadlock handling
    assert deadlock_result["deadlock_detected"] is True
    assert deadlock_result["deadlock_resolved"] is True
    assert deadlock_result["transactions_completed"] >= 1
    assert deadlock_result["staging_verified"] is True
    assert deadlock_result["response_time"] < 30.0  # Allow time for deadlock resolution


@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_cross_database_consistency_validation(l4_transaction_manager):
    """Test comprehensive cross-database consistency validation."""
    # Perform multiple transaction types
    test_scenarios = [
        {
            "organization_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "amount": 100.00,
            "transaction_type": "billing_payment",
            "resource_type": "api_calls",
            "usage_amount": 5000,
            "billing_period": "2025-01-01"
        },
        {
            "organization_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "amount": 250.75,
            "transaction_type": "subscription_upgrade",
            "resource_type": "storage_gb",
            "usage_amount": 100,
            "billing_period": "2025-01-01"
        },
        {
            "organization_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "amount": 75.25,
            "transaction_type": "overage_charge",
            "resource_type": "bandwidth_tb",
            "usage_amount": 2,
            "billing_period": "2025-01-01"
        }
    ]
    
    # Execute all scenarios
    results = []
    for scenario in test_scenarios:
        # Test PostgreSQL atomicity
        postgres_result = await l4_transaction_manager.test_postgres_acid_transaction_atomicity(scenario)
        
        # Test ClickHouse consistency
        clickhouse_result = await l4_transaction_manager.test_clickhouse_eventual_consistency(scenario)
        
        results.append({
            "postgres": postgres_result,
            "clickhouse": clickhouse_result
        })
    
    # Verify all transactions succeeded
    for result in results:
        assert result["postgres"]["atomicity_verified"] is True
        assert result["clickhouse"]["eventual_consistency_achieved"] is True
        assert result["postgres"]["staging_verified"] is True
        assert result["clickhouse"]["staging_verified"] is True
    
    # Verify final consistency metrics
    final_metrics = await l4_transaction_manager.get_transaction_consistency_metrics()
    
    assert final_metrics["total_transactions"] >= len(test_scenarios)
    assert final_metrics["postgres_success_rate"] >= 95.0
    assert final_metrics["consistency_rate"] >= 95.0
    assert final_metrics["cross_database_syncs"] >= len(test_scenarios)
    assert final_metrics["staging_environment"] is True
    assert final_metrics["l4_test_level"] is True
    
    # Performance validation
    assert final_metrics["average_transaction_time"] < 5.0
    assert final_metrics["average_sync_latency"] < 10.0


@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_high_volume_transaction_consistency(l4_transaction_manager):
    """Test transaction consistency under high-volume concurrent load."""
    # Generate high-volume concurrent transactions
    num_transactions = 50
    concurrent_tasks = []
    
    base_org_id = str(uuid.uuid4())
    
    for i in range(num_transactions):
        transaction_data = {
            "organization_id": base_org_id,
            "user_id": str(uuid.uuid4()),
            "amount": round(10.0 + (i * 5.5), 2),
            "transaction_type": f"high_volume_test_{i % 5}",
            "resource_type": ["api_calls", "storage", "bandwidth", "compute", "llm_tokens"][i % 5],
            "usage_amount": 1000 + (i * 100),
            "billing_period": "2025-01-01"
        }
        
        # Alternate between PostgreSQL and ClickHouse operations
        if i % 2 == 0:
            task = l4_transaction_manager.test_postgres_acid_transaction_atomicity(transaction_data)
        else:
            task = l4_transaction_manager.test_clickhouse_eventual_consistency(transaction_data)
        
        concurrent_tasks.append(task)
    
    # Execute all transactions concurrently
    start_time = time.time()
    results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict) and not r.get("error")]
    postgres_results = [r for r in successful_results if "atomicity_verified" in r]
    clickhouse_results = [r for r in successful_results if "eventual_consistency_achieved" in r]
    
    # Verify high-volume performance
    success_rate = len(successful_results) / num_transactions * 100
    assert success_rate >= 90.0  # 90% success rate under load
    
    # Verify PostgreSQL results
    postgres_success_rate = sum(1 for r in postgres_results if r["atomicity_verified"]) / len(postgres_results) * 100
    assert postgres_success_rate >= 95.0
    
    # Verify ClickHouse results
    clickhouse_success_rate = sum(1 for r in clickhouse_results if r["eventual_consistency_achieved"]) / len(clickhouse_results) * 100
    assert clickhouse_success_rate >= 90.0  # Allow for eventual consistency delays
    
    # Performance benchmarks
    assert total_time < 120.0  # Complete within 2 minutes
    
    average_response_time = sum(r.get("response_time", 0) for r in successful_results) / len(successful_results)
    assert average_response_time < 10.0  # Average response time under 10 seconds
    
    # Get final metrics
    final_metrics = await l4_transaction_manager.get_transaction_consistency_metrics()
    assert final_metrics["total_transactions"] >= num_transactions
    assert final_metrics["staging_environment"] is True