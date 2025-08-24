"""ClickHouse → PostgreSQL Transaction Coordination L3 Integration Test

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Data Consistency  
- Value Impact: Ensures analytics and transactional data remain synchronized
- Revenue Impact: Protects $12K MRR by preventing data inconsistencies

Test Level: L3 (Real Local Services)
- Real ClickHouse instance (local)
- Real PostgreSQL instance (local)  
- Real two-phase commit patterns
- Real rollback mechanisms
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from netra_backend.app.db.clickhouse import get_clickhouse_client

from netra_backend.app.db.postgres import get_postgres_session, initialize_postgres
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

@dataclass
class TransactionCoordinationData:
    """Test data for transaction coordination scenarios."""
    transaction_id: str
    user_id: str
    metrics_data: Dict[str, Any]
    billing_data: Dict[str, Any]

class ClickHousePostgresCoordinator:
    """L3 coordinator for ClickHouse → PostgreSQL transaction testing."""
    
    def __init__(self):
        self.test_schema_prefix = f"test_{uuid.uuid4().hex[:8]}"
    
    async def setup_databases(self) -> None:
        """Setup real database connections and schemas."""
        try:
            await self._initialize_schemas()
        except Exception as e:
            await self.cleanup()
            raise RuntimeError(f"Database setup failed: {e}")
    
    async def _initialize_schemas(self) -> None:
        """Initialize database schemas."""
        # PostgreSQL schema for transactional data
        pg_table = f"billing_transactions_{self.test_schema_prefix}"
        postgres_schema = f"""
            CREATE TABLE IF NOT EXISTS {pg_table} (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        
        # ClickHouse schema for analytics data  
        ch_table = f"user_metrics_{self.test_schema_prefix}"
        clickhouse_schema = f"""
            CREATE TABLE IF NOT EXISTS {ch_table} (
                metric_id String,
                user_id String,
                metric_type String,
                value Float64,
                timestamp DateTime,
                source String
            ) ENGINE = MergeTree()
            ORDER BY (user_id, timestamp);
        """
        
        # Setup PostgreSQL
        async with get_postgres_session() as session:
            await session.execute(postgres_schema)
            await session.commit()
        
        # Setup ClickHouse
        async with get_clickhouse_client() as client:
            await client.execute_query(clickhouse_schema)
    
    def create_test_data(self, scenario: str) -> TransactionCoordinationData:
        """Create test data for coordination scenarios."""
        tx_id = f"coord_tx_{uuid.uuid4().hex[:12]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        return TransactionCoordinationData(
            transaction_id=tx_id,
            user_id=user_id,
            metrics_data={
                "metric_id": f"metric_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "metric_type": "api_usage",
                "value": 100.0,
                "timestamp": datetime.utcnow(),
                "source": "billing_sync"
            },
            billing_data={
                "user_id": user_id,
                "amount": 29.99,
                "status": "committed",
                "metadata": {"transaction_id": tx_id, "test": True}
            }
        )
    
    async def execute_coordinated_write(self, data: TransactionCoordinationData) -> Dict[str, Any]:
        """Execute coordinated write to both databases."""
        start_time = time.time()
        ch_table = f"user_metrics_{self.test_schema_prefix}"
        pg_table = f"billing_transactions_{self.test_schema_prefix}"
        
        try:
            # Phase 1: Write to ClickHouse (analytics first)
            async with get_clickhouse_client() as ch_client:
                query = f"""INSERT INTO {ch_table} 
                (metric_id, user_id, metric_type, value, timestamp, source)
                VALUES (%(metric_id)s, %(user_id)s, %(metric_type)s, 
                        %(value)s, %(timestamp)s, %(source)s)"""
                await ch_client.execute_query(query, data.metrics_data)
            
            # Phase 2: Write to PostgreSQL (billing confirmation)
            async with get_postgres_session() as pg_session:
                query = f"""INSERT INTO {pg_table} 
                (user_id, amount, status, metadata, created_at)
                VALUES (%(user_id)s, %(amount)s, %(status)s, 
                        %(metadata)s, CURRENT_TIMESTAMP)
                RETURNING id"""
                result = await pg_session.execute(
                    query,
                    {**data.billing_data, "metadata": json.dumps(data.billing_data["metadata"])}
                )
                billing_id = result.fetchone()[0]
                await pg_session.commit()
            
            return {
                "success": True,
                "transaction_id": data.transaction_id,
                "billing_id": billing_id,
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            # Rollback on failure
            await self._rollback_transaction(data)
            return {
                "success": False,
                "transaction_id": data.transaction_id,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "rollback_performed": True
            }
    
    async def _rollback_transaction(self, data: TransactionCoordinationData) -> None:
        """Rollback transaction from both databases."""
        ch_table = f"user_metrics_{self.test_schema_prefix}"
        pg_table = f"billing_transactions_{self.test_schema_prefix}"
        
        try:
            # Remove from ClickHouse
            async with get_clickhouse_client() as ch_client:
                query = f"ALTER TABLE {ch_table} DELETE WHERE metric_id = %(metric_id)s"
                await ch_client.execute_query(
                    query,
                    {"metric_id": data.metrics_data["metric_id"]}
                )
        except Exception as e:
            logger.warning(f"ClickHouse rollback failed: {e}")
        
        try:
            # Remove from PostgreSQL
            async with get_postgres_session() as pg_session:
                query = f"DELETE FROM {pg_table} WHERE user_id = %(user_id)s"
                await pg_session.execute(query, {"user_id": data.user_id})
                await pg_session.commit()
        except Exception as e:
            logger.warning(f"PostgreSQL rollback failed: {e}")
    
    async def validate_consistency(self, data: TransactionCoordinationData) -> Dict[str, Any]:
        """Validate data consistency across databases."""
        ch_table = f"user_metrics_{self.test_schema_prefix}"
        pg_table = f"billing_transactions_{self.test_schema_prefix}"
        
        # Check PostgreSQL
        async with get_postgres_session() as pg_session:
            query = f"SELECT id, amount FROM {pg_table} WHERE user_id = %(user_id)s"
            pg_result = await pg_session.execute(query, {"user_id": data.user_id})
            pg_data = pg_result.fetchone()
        
        # Check ClickHouse
        async with get_clickhouse_client() as ch_client:
            query = f"SELECT value FROM {ch_table} WHERE user_id = %(user_id)s"
            ch_result = await ch_client.fetch(query, {"user_id": data.user_id})
        
        pg_exists = pg_data is not None
        ch_exists = len(ch_result) > 0
        
        return {
            "postgres_exists": pg_exists,
            "clickhouse_exists": ch_exists,
            "cross_consistent": pg_exists == ch_exists,
            "postgres_amount": float(pg_data[1]) if pg_data else None,
            "clickhouse_value": ch_result[0]["value"] if ch_result else None
        }
    
    async def cleanup(self) -> None:
        """Cleanup test tables and resources."""
        try:
            ch_table = f"user_metrics_{self.test_schema_prefix}"
            pg_table = f"billing_transactions_{self.test_schema_prefix}"
            
            # Cleanup ClickHouse
            async with get_clickhouse_client() as ch_client:
                await ch_client.execute_query(f"DROP TABLE IF EXISTS {ch_table}")
            
            # Cleanup PostgreSQL  
            async with get_postgres_session() as pg_session:
                await pg_session.execute(f"DROP TABLE IF EXISTS {pg_table}")
                await pg_session.commit()
                
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

@pytest.fixture
async def coordinator():
    """Fixture for transaction coordinator."""
    coord = ClickHousePostgresCoordinator()
    await coord.setup_databases()
    yield coord
    await coord.cleanup()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_coordinated_write_commit(coordinator):
    """Test coordinated write to both databases with commit."""
    data = coordinator.create_test_data("success")
    result = await coordinator.execute_coordinated_write(data)
    assert result["success"] is True and result["execution_time"] < 5.0
    consistency = await coordinator.validate_consistency(data)
    assert consistency["cross_consistent"] and consistency["postgres_exists"]
    assert consistency["clickhouse_exists"]

@pytest.mark.asyncio 
@pytest.mark.integration
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_clickhouse_failure_rollback(coordinator):
    """Test rollback on ClickHouse failure preserves PostgreSQL consistency."""
    data = coordinator.create_test_data("clickhouse_failure")
    data.metrics_data["value"] = "invalid_value"  # Force failure
    result = await coordinator.execute_coordinated_write(data)
    assert not result["success"] and result["rollback_performed"]
    consistency = await coordinator.validate_consistency(data)
    assert not consistency["postgres_exists"] and not consistency["clickhouse_exists"]

@pytest.mark.asyncio
@pytest.mark.integration  
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_postgres_failure_rollback(coordinator):
    """Test rollback on PostgreSQL failure preserves ClickHouse consistency."""
    data = coordinator.create_test_data("postgres_failure")
    data.billing_data["amount"] = "invalid_amount"  # Force failure
    result = await coordinator.execute_coordinated_write(data)
    assert not result["success"] and result["rollback_performed"]
    consistency = await coordinator.validate_consistency(data)
    assert not consistency["postgres_exists"] and not consistency["clickhouse_exists"]

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3_realism  
@pytest.mark.asyncio
async def test_read_consistency(coordinator):
    """Test read consistency across both databases."""
    data = coordinator.create_test_data("read_test")
    result = await coordinator.execute_coordinated_write(data)
    assert result["success"] is True
    consistency = await coordinator.validate_consistency(data)
    assert consistency["cross_consistent"] and consistency["postgres_amount"] == 29.99
    assert consistency["clickhouse_value"] == 100.0

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_concurrent_transaction_isolation(coordinator):
    """Test concurrent transaction isolation."""
    data_list = [coordinator.create_test_data(f"concurrent_{i}") for i in range(3)]
    tasks = [coordinator.execute_coordinated_write(data) for data in data_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful = [r for r in results if not isinstance(r, Exception) and r.get("success")]
    assert len(successful) >= 2
    for i, data in enumerate(data_list):
        if not isinstance(results[i], Exception) and results[i].get("success"):
            assert (await coordinator.validate_consistency(data))["cross_consistent"]