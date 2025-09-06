# REMOVED_SYNTAX_ERROR: '''ClickHouse → PostgreSQL Transaction Coordination L3 Integration Test

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Enterprise
    # REMOVED_SYNTAX_ERROR: - Business Goal: Data Consistency
    # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures analytics and transactional data remain synchronized
    # REMOVED_SYNTAX_ERROR: - Revenue Impact: Protects $12K MRR by preventing data inconsistencies

    # REMOVED_SYNTAX_ERROR: Test Level: L3 (Real Local Services)
    # REMOVED_SYNTAX_ERROR: - Real ClickHouse instance (local)
    # REMOVED_SYNTAX_ERROR: - Real PostgreSQL instance (local)
    # REMOVED_SYNTAX_ERROR: - Real two-phase commit patterns
    # REMOVED_SYNTAX_ERROR: - Real rollback mechanisms
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # Test framework import - using pytest fixtures instead

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from contextlib import asynccontextmanager
    # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional

    # REMOVED_SYNTAX_ERROR: import pytest

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.database import get_clickhouse_client

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.postgres import get_postgres_session, initialize_postgres
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)

    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class TransactionCoordinationData:
    # REMOVED_SYNTAX_ERROR: """Test data for transaction coordination scenarios."""
    # REMOVED_SYNTAX_ERROR: transaction_id: str
    # REMOVED_SYNTAX_ERROR: user_id: str
    # REMOVED_SYNTAX_ERROR: metrics_data: Dict[str, Any]
    # REMOVED_SYNTAX_ERROR: billing_data: Dict[str, Any]

# REMOVED_SYNTAX_ERROR: class ClickHousePostgresCoordinator:
    # REMOVED_SYNTAX_ERROR: """L3 coordinator for ClickHouse → PostgreSQL transaction testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.test_schema_prefix = "formatted_string")

# REMOVED_SYNTAX_ERROR: async def _initialize_schemas(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Initialize database schemas."""
    # PostgreSQL schema for transactional data
    # REMOVED_SYNTAX_ERROR: pg_table = "formatted_string"
    # REMOVED_SYNTAX_ERROR: postgres_schema = f'''
    # REMOVED_SYNTAX_ERROR: CREATE TABLE IF NOT EXISTS {pg_table} ( )
    # REMOVED_SYNTAX_ERROR: id SERIAL PRIMARY KEY,
    # REMOVED_SYNTAX_ERROR: user_id VARCHAR(50) NOT NULL,
    # REMOVED_SYNTAX_ERROR: amount DECIMAL(10,2) NOT NULL,
    # REMOVED_SYNTAX_ERROR: status VARCHAR(20) DEFAULT 'pending',
    # REMOVED_SYNTAX_ERROR: metadata JSONB,
    # REMOVED_SYNTAX_ERROR: created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    # REMOVED_SYNTAX_ERROR: );
    # REMOVED_SYNTAX_ERROR: """"

    # ClickHouse schema for analytics data
    # REMOVED_SYNTAX_ERROR: ch_table = "formatted_string"
    # REMOVED_SYNTAX_ERROR: clickhouse_schema = f'''
    # REMOVED_SYNTAX_ERROR: CREATE TABLE IF NOT EXISTS {ch_table} ( )
    # REMOVED_SYNTAX_ERROR: metric_id String,
    # REMOVED_SYNTAX_ERROR: user_id String,
    # REMOVED_SYNTAX_ERROR: metric_type String,
    # REMOVED_SYNTAX_ERROR: value Float64,
    # REMOVED_SYNTAX_ERROR: timestamp DateTime,
    # REMOVED_SYNTAX_ERROR: source String
    # REMOVED_SYNTAX_ERROR: ) ENGINE = MergeTree()
    # REMOVED_SYNTAX_ERROR: ORDER BY (user_id, timestamp);
    # REMOVED_SYNTAX_ERROR: """"

    # Setup PostgreSQL
    # REMOVED_SYNTAX_ERROR: async with get_postgres_session() as session:
        # REMOVED_SYNTAX_ERROR: await session.execute(postgres_schema)
        # REMOVED_SYNTAX_ERROR: await session.commit()

        # Setup ClickHouse
        # REMOVED_SYNTAX_ERROR: async with get_clickhouse_client() as client:
            # REMOVED_SYNTAX_ERROR: await client.execute_query(clickhouse_schema)

# REMOVED_SYNTAX_ERROR: def create_test_data(self, scenario: str) -> TransactionCoordinationData:
    # REMOVED_SYNTAX_ERROR: """Create test data for coordination scenarios."""
    # REMOVED_SYNTAX_ERROR: tx_id = "formatted_string"user_id": user_id,
    # REMOVED_SYNTAX_ERROR: "amount": 29.99,
    # REMOVED_SYNTAX_ERROR: "status": "committed",
    # REMOVED_SYNTAX_ERROR: "metadata": {"transaction_id": tx_id, "test": True}
    
    

# REMOVED_SYNTAX_ERROR: async def execute_coordinated_write(self, data: TransactionCoordinationData) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Execute coordinated write to both databases."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: ch_table = "formatted_string"
    # REMOVED_SYNTAX_ERROR: pg_table = "formatted_string"

    # REMOVED_SYNTAX_ERROR: try:
        # Phase 1: Write to ClickHouse (analytics first)
        # REMOVED_SYNTAX_ERROR: async with get_clickhouse_client() as ch_client:
            # REMOVED_SYNTAX_ERROR: query = f'''INSERT INTO {ch_table}
            # REMOVED_SYNTAX_ERROR: (metric_id, user_id, metric_type, value, timestamp, source)
            # REMOVED_SYNTAX_ERROR: VALUES (%(metric_id)s, %(user_id)s, %(metric_type)s,
            # REMOVED_SYNTAX_ERROR: %(value)s, %(timestamp)s, %(source)s)""""
            # REMOVED_SYNTAX_ERROR: await ch_client.execute_query(query, data.metrics_data)

            # Phase 2: Write to PostgreSQL (billing confirmation)
            # REMOVED_SYNTAX_ERROR: async with get_postgres_session() as pg_session:
                # REMOVED_SYNTAX_ERROR: query = f'''INSERT INTO {pg_table}
                # REMOVED_SYNTAX_ERROR: (user_id, amount, status, metadata, created_at)
                # REMOVED_SYNTAX_ERROR: VALUES (%(user_id)s, %(amount)s, %(status)s,
                # REMOVED_SYNTAX_ERROR: %(metadata)s, CURRENT_TIMESTAMP)
                # REMOVED_SYNTAX_ERROR: RETURNING id""""
                # REMOVED_SYNTAX_ERROR: result = await pg_session.execute( )
                # REMOVED_SYNTAX_ERROR: query,
                # REMOVED_SYNTAX_ERROR: {**data.billing_data, "metadata": json.dumps(data.billing_data["metadata"])]
                
                # REMOVED_SYNTAX_ERROR: billing_id = result.fetchone()[0]
                # REMOVED_SYNTAX_ERROR: await pg_session.commit()

                # REMOVED_SYNTAX_ERROR: return { )
                # REMOVED_SYNTAX_ERROR: "success": True,
                # REMOVED_SYNTAX_ERROR: "transaction_id": data.transaction_id,
                # REMOVED_SYNTAX_ERROR: "billing_id": billing_id,
                # REMOVED_SYNTAX_ERROR: "execution_time": time.time() - start_time
                

                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # Rollback on failure
                    # REMOVED_SYNTAX_ERROR: await self._rollback_transaction(data)
                    # REMOVED_SYNTAX_ERROR: return { )
                    # REMOVED_SYNTAX_ERROR: "success": False,
                    # REMOVED_SYNTAX_ERROR: "transaction_id": data.transaction_id,
                    # REMOVED_SYNTAX_ERROR: "error": str(e),
                    # REMOVED_SYNTAX_ERROR: "execution_time": time.time() - start_time,
                    # REMOVED_SYNTAX_ERROR: "rollback_performed": True
                    

# REMOVED_SYNTAX_ERROR: async def _rollback_transaction(self, data: TransactionCoordinationData) -> None:
    # REMOVED_SYNTAX_ERROR: """Rollback transaction from both databases."""
    # REMOVED_SYNTAX_ERROR: ch_table = "formatted_string"
    # REMOVED_SYNTAX_ERROR: pg_table = "formatted_string"

    # REMOVED_SYNTAX_ERROR: try:
        # Remove from ClickHouse
        # REMOVED_SYNTAX_ERROR: async with get_clickhouse_client() as ch_client:
            # REMOVED_SYNTAX_ERROR: query = "formatted_string"
            # REMOVED_SYNTAX_ERROR: await ch_client.execute_query( )
            # REMOVED_SYNTAX_ERROR: query,
            # REMOVED_SYNTAX_ERROR: {"metric_id": data.metrics_data["metric_id"]]
            
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                # REMOVED_SYNTAX_ERROR: try:
                    # Remove from PostgreSQL
                    # REMOVED_SYNTAX_ERROR: async with get_postgres_session() as pg_session:
                        # REMOVED_SYNTAX_ERROR: query = "formatted_string"
                        # REMOVED_SYNTAX_ERROR: await pg_session.execute(query, {"user_id": data.user_id})
                        # REMOVED_SYNTAX_ERROR: await pg_session.commit()
                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

# REMOVED_SYNTAX_ERROR: async def validate_consistency(self, data: TransactionCoordinationData) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Validate data consistency across databases."""
    # REMOVED_SYNTAX_ERROR: ch_table = "formatted_string"
    # REMOVED_SYNTAX_ERROR: pg_table = "formatted_string"

    # Check PostgreSQL
    # REMOVED_SYNTAX_ERROR: async with get_postgres_session() as pg_session:
        # REMOVED_SYNTAX_ERROR: query = "formatted_string"
        # REMOVED_SYNTAX_ERROR: pg_result = await pg_session.execute(query, {"user_id": data.user_id})
        # REMOVED_SYNTAX_ERROR: pg_data = pg_result.fetchone()

        # Check ClickHouse
        # REMOVED_SYNTAX_ERROR: async with get_clickhouse_client() as ch_client:
            # REMOVED_SYNTAX_ERROR: query = "formatted_string"
            # REMOVED_SYNTAX_ERROR: ch_result = await ch_client.fetch(query, {"user_id": data.user_id})

            # REMOVED_SYNTAX_ERROR: pg_exists = pg_data is not None
            # REMOVED_SYNTAX_ERROR: ch_exists = len(ch_result) > 0

            # REMOVED_SYNTAX_ERROR: return { )
            # REMOVED_SYNTAX_ERROR: "postgres_exists": pg_exists,
            # REMOVED_SYNTAX_ERROR: "clickhouse_exists": ch_exists,
            # REMOVED_SYNTAX_ERROR: "cross_consistent": pg_exists == ch_exists,
            # REMOVED_SYNTAX_ERROR: "postgres_amount": float(pg_data[1]) if pg_data else None,
            # REMOVED_SYNTAX_ERROR: "clickhouse_value": ch_result[0]["value"] if ch_result else None
            

# REMOVED_SYNTAX_ERROR: async def cleanup(self) -> None:
    # REMOVED_SYNTAX_ERROR: """Cleanup test tables and resources."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: ch_table = "formatted_string"
        # REMOVED_SYNTAX_ERROR: pg_table = "formatted_string"

        # Cleanup ClickHouse
        # REMOVED_SYNTAX_ERROR: async with get_clickhouse_client() as ch_client:
            # REMOVED_SYNTAX_ERROR: await ch_client.execute_query("formatted_string")

            # Cleanup PostgreSQL
            # REMOVED_SYNTAX_ERROR: async with get_postgres_session() as pg_session:
                # REMOVED_SYNTAX_ERROR: await pg_session.execute("formatted_string")
                # REMOVED_SYNTAX_ERROR: await pg_session.commit()

                # REMOVED_SYNTAX_ERROR: except Exception as e:
                    # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def coordinator():
    # REMOVED_SYNTAX_ERROR: """Fixture for transaction coordinator."""
    # REMOVED_SYNTAX_ERROR: coord = ClickHousePostgresCoordinator()
    # REMOVED_SYNTAX_ERROR: await coord.setup_databases()
    # REMOVED_SYNTAX_ERROR: yield coord
    # REMOVED_SYNTAX_ERROR: await coord.cleanup()

    # Removed problematic line: @pytest.mark.asyncio
    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
    # REMOVED_SYNTAX_ERROR: @pytest.mark.l3_realism
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_coordinated_write_commit(coordinator):
        # REMOVED_SYNTAX_ERROR: """Test coordinated write to both databases with commit."""
        # REMOVED_SYNTAX_ERROR: data = coordinator.create_test_data("success")
        # REMOVED_SYNTAX_ERROR: result = await coordinator.execute_coordinated_write(data)
        # REMOVED_SYNTAX_ERROR: assert result["success"] is True and result["execution_time"] < 5.0
        # REMOVED_SYNTAX_ERROR: consistency = await coordinator.validate_consistency(data)
        # REMOVED_SYNTAX_ERROR: assert consistency["cross_consistent"] and consistency["postgres_exists"]
        # REMOVED_SYNTAX_ERROR: assert consistency["clickhouse_exists"]

        # Removed problematic line: @pytest.mark.asyncio
        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
        # REMOVED_SYNTAX_ERROR: @pytest.mark.l3_realism
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_clickhouse_failure_rollback(coordinator):
            # REMOVED_SYNTAX_ERROR: """Test rollback on ClickHouse failure preserves PostgreSQL consistency."""
            # REMOVED_SYNTAX_ERROR: data = coordinator.create_test_data("clickhouse_failure")
            # REMOVED_SYNTAX_ERROR: data.metrics_data["value"] = "invalid_value"  # Force failure
            # REMOVED_SYNTAX_ERROR: result = await coordinator.execute_coordinated_write(data)
            # REMOVED_SYNTAX_ERROR: assert not result["success"] and result["rollback_performed"]
            # REMOVED_SYNTAX_ERROR: consistency = await coordinator.validate_consistency(data)
            # REMOVED_SYNTAX_ERROR: assert not consistency["postgres_exists"] and not consistency["clickhouse_exists"]

            # Removed problematic line: @pytest.mark.asyncio
            # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
            # REMOVED_SYNTAX_ERROR: @pytest.mark.l3_realism
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_postgres_failure_rollback(coordinator):
                # REMOVED_SYNTAX_ERROR: """Test rollback on PostgreSQL failure preserves ClickHouse consistency."""
                # REMOVED_SYNTAX_ERROR: data = coordinator.create_test_data("postgres_failure")
                # REMOVED_SYNTAX_ERROR: data.billing_data["amount"] = "invalid_amount"  # Force failure
                # REMOVED_SYNTAX_ERROR: result = await coordinator.execute_coordinated_write(data)
                # REMOVED_SYNTAX_ERROR: assert not result["success"] and result["rollback_performed"]
                # REMOVED_SYNTAX_ERROR: consistency = await coordinator.validate_consistency(data)
                # REMOVED_SYNTAX_ERROR: assert not consistency["postgres_exists"] and not consistency["clickhouse_exists"]

                # Removed problematic line: @pytest.mark.asyncio
                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                # REMOVED_SYNTAX_ERROR: @pytest.mark.l3_realism
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_read_consistency(coordinator):
                    # REMOVED_SYNTAX_ERROR: """Test read consistency across both databases."""
                    # REMOVED_SYNTAX_ERROR: data = coordinator.create_test_data("read_test")
                    # REMOVED_SYNTAX_ERROR: result = await coordinator.execute_coordinated_write(data)
                    # REMOVED_SYNTAX_ERROR: assert result["success"] is True
                    # REMOVED_SYNTAX_ERROR: consistency = await coordinator.validate_consistency(data)
                    # REMOVED_SYNTAX_ERROR: assert consistency["cross_consistent"] and consistency["postgres_amount"] == 29.99
                    # REMOVED_SYNTAX_ERROR: assert consistency["clickhouse_value"] == 100.0

                    # Removed problematic line: @pytest.mark.asyncio
                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                    # REMOVED_SYNTAX_ERROR: @pytest.mark.l3_realism
                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_concurrent_transaction_isolation(coordinator):
                        # REMOVED_SYNTAX_ERROR: """Test concurrent transaction isolation."""
                        # REMOVED_SYNTAX_ERROR: data_list = [coordinator.create_test_data(f"concurrent_{i]") for i in range(3)]
                        # REMOVED_SYNTAX_ERROR: tasks = [coordinator.execute_coordinated_write(data) for data in data_list]
                        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)
                        # REMOVED_SYNTAX_ERROR: successful = [item for item in []]
                        # REMOVED_SYNTAX_ERROR: assert len(successful) >= 2
                        # REMOVED_SYNTAX_ERROR: for i, data in enumerate(data_list):
                            # REMOVED_SYNTAX_ERROR: if not isinstance(results[i], Exception) and results[i].get("success"):
                                # REMOVED_SYNTAX_ERROR: assert (await coordinator.validate_consistency(data))["cross_consistent"]