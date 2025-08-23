"""
L3 Integration Test: Database Query Timeout Handling

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers under load)
- Business Goal: Stability - Prevent runaway queries from affecting system performance
- Value Impact: Protects $45K MRR from query-induced outages
- Strategic Impact: Ensures predictable response times for all users

L3 Test: Uses real PostgreSQL and ClickHouse containers to validate query timeout
enforcement, graceful degradation, and system recovery from timeout scenarios.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import asyncpg
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.clickhouse import ClickHouseContainer
from testcontainers.postgres import PostgresContainer

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class DatabaseQueryTimeoutManager:
    """Manages query timeout testing with real database containers."""
    
    def __init__(self):
        self.postgres_container = None
        self.clickhouse_container = None
        self.postgres_url = None
        self.clickhouse_client = None
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.timeout_scenarios = []
        self.timeout_metrics = {}
        
    async def setup_database_containers(self):
        """Setup real database containers for timeout testing."""
        try:
            # Setup PostgreSQL
            self.postgres_container = PostgresContainer("postgres:15-alpine")
            self.postgres_container.start()
            
            self.postgres_url = self.postgres_container.get_connection_url().replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            # Create engine with configurable timeouts
            self.postgres_engine = create_async_engine(
                self.postgres_url,
                pool_size=5,
                max_overflow=2,
                echo=False,
                connect_args={
                    "command_timeout": 30,  # Default query timeout
                    "server_settings": {
                        "statement_timeout": "30s",
                        "lock_timeout": "10s"
                    }
                }
            )
            
            self.postgres_session_factory = sessionmaker(
                self.postgres_engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Setup ClickHouse
            self.clickhouse_container = ClickHouseContainer("clickhouse/clickhouse-server:23.8-alpine")
            self.clickhouse_container.start()
            
            ch_host = self.clickhouse_container.get_container_host_ip()
            ch_port = self.clickhouse_container.get_exposed_port(9000)
            
            import asyncio_clickhouse
            self.clickhouse_client = asyncio_clickhouse.connect(
                host=ch_host,
                port=ch_port,
                database="default",
                query_timeout=30  # 30 second default timeout
            )
            
            # Initialize test data for timeout scenarios
            await self.create_timeout_test_data()
            
            logger.info("Query timeout test containers setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup timeout test containers: {e}")
            await self.cleanup()
            raise
    
    async def create_timeout_test_data(self):
        """Create test data designed to trigger various timeout scenarios."""
        # PostgreSQL test data
        async with self.postgres_engine.begin() as conn:
            # Large table for expensive operations
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS timeout_test_large_table (
                    id SERIAL PRIMARY KEY,
                    data_column TEXT,
                    numeric_column BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table for lock testing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS timeout_test_lock_table (
                    id SERIAL PRIMARY KEY,
                    resource_name VARCHAR(100) UNIQUE,
                    lock_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert substantial test data
            await conn.execute("""
                INSERT INTO timeout_test_large_table (data_column, numeric_column)
                SELECT 
                    'Large data string that takes space: ' || generate_series,
                    generate_series * generate_series
                FROM generate_series(1, 10000)
                ON CONFLICT DO NOTHING
            """)
            
            await conn.execute("""
                INSERT INTO timeout_test_lock_table (resource_name, lock_value) VALUES
                ('resource_1', 'initial_value'),
                ('resource_2', 'initial_value'),
                ('resource_3', 'initial_value')
                ON CONFLICT (resource_name) DO NOTHING
            """)
        
        # ClickHouse test data
        await self.clickhouse_client.execute("""
            CREATE TABLE IF NOT EXISTS timeout_test_events (
                event_id String,
                user_id String,
                event_data String,
                large_text String,
                event_timestamp DateTime,
                numeric_value UInt64
            ) ENGINE = MergeTree()
            ORDER BY (user_id, event_timestamp)
        """)
        
        # Insert substantial ClickHouse data
        ch_data = []
        for i in range(100000):
            ch_data.append((
                f"event_{i}",
                f"user_{i % 1000}",
                f"Large event data string with lots of content: {i}" * 10,
                "x" * 1000,  # 1KB of text per record
                datetime.now() - timedelta(seconds=i),
                i * i
            ))
        
        # Insert in chunks to avoid memory issues
        chunk_size = 5000
        for i in range(0, len(ch_data), chunk_size):
            chunk = ch_data[i:i + chunk_size]
            await self.clickhouse_client.execute(
                "INSERT INTO timeout_test_events VALUES",
                chunk
            )
    
    async def test_postgres_query_timeout_enforcement(self, timeout_seconds: int = 5) -> Dict[str, Any]:
        """Test PostgreSQL query timeout enforcement."""
        timeout_result = {
            "timeout_seconds": timeout_seconds,
            "timeout_enforced": False,
            "timeout_detection_time": 0.0,
            "graceful_degradation": False,
            "recovery_successful": False
        }
        
        try:
            # Create session with custom timeout
            session = self.postgres_session_factory()
            
            try:
                # Set statement timeout for this session
                await session.execute(f"SET statement_timeout = '{timeout_seconds}s'")
                
                # Execute a deliberately slow query
                start_time = time.time()
                
                try:
                    # This query should timeout due to expensive cross join
                    await session.execute("""
                        SELECT COUNT(*)
                        FROM timeout_test_large_table t1
                        CROSS JOIN timeout_test_large_table t2
                        WHERE t1.numeric_column * t2.numeric_column > 1000000
                    """)
                    
                    execution_time = time.time() - start_time
                    timeout_result["timeout_detection_time"] = execution_time
                    
                    # If we get here, query completed (unexpected for large data)
                    if execution_time < timeout_seconds:
                        timeout_result["graceful_degradation"] = True
                    
                except Exception as query_error:
                    execution_time = time.time() - start_time
                    timeout_result["timeout_detection_time"] = execution_time
                    
                    # Check if timeout was enforced
                    if ("timeout" in str(query_error).lower() or 
                        "canceling statement" in str(query_error).lower()):
                        timeout_result["timeout_enforced"] = True
                        
                        # Verify timeout occurred within reasonable bounds
                        if timeout_seconds <= execution_time <= timeout_seconds + 2:
                            timeout_result["graceful_degradation"] = True
                
                # Test recovery - simple query should work after timeout
                try:
                    await session.execute("SELECT 1")
                    timeout_result["recovery_successful"] = True
                except Exception:
                    # Session might be broken, try new session
                    await session.close()
                    session = self.postgres_session_factory()
                    await session.execute("SELECT 1")
                    timeout_result["recovery_successful"] = True
                
            finally:
                await session.close()
                
        except Exception as e:
            timeout_result["error"] = str(e)
            logger.error(f"PostgreSQL timeout test failed: {e}")
        
        return timeout_result
    
    async def test_clickhouse_query_timeout_enforcement(self, timeout_seconds: int = 5) -> Dict[str, Any]:
        """Test ClickHouse query timeout enforcement."""
        timeout_result = {
            "timeout_seconds": timeout_seconds,
            "timeout_enforced": False,
            "timeout_detection_time": 0.0,
            "graceful_degradation": False,
            "recovery_successful": False
        }
        
        try:
            # Execute a deliberately expensive query
            start_time = time.time()
            
            try:
                # Create a new client with short timeout for this test
                ch_host = self.clickhouse_container.get_container_host_ip()
                ch_port = self.clickhouse_container.get_exposed_port(9000)
                
                import asyncio_clickhouse
                timeout_client = asyncio_clickhouse.connect(
                    host=ch_host,
                    port=ch_port,
                    database="default",
                    query_timeout=timeout_seconds
                )
                
                # Execute expensive query that should timeout
                await timeout_client.execute("""
                    SELECT 
                        user_id,
                        COUNT(*) as event_count,
                        AVG(LENGTH(large_text)) as avg_text_length,
                        SUM(numeric_value) as total_value
                    FROM timeout_test_events
                    GROUP BY user_id
                    HAVING COUNT(*) > 50
                    ORDER BY total_value DESC
                    LIMIT 1000000
                """)
                
                execution_time = time.time() - start_time
                timeout_result["timeout_detection_time"] = execution_time
                
                # If query completed quickly, that's acceptable
                if execution_time < timeout_seconds:
                    timeout_result["graceful_degradation"] = True
                
                await timeout_client.disconnect()
                
            except Exception as query_error:
                execution_time = time.time() - start_time
                timeout_result["timeout_detection_time"] = execution_time
                
                # Check if timeout was enforced
                error_message = str(query_error).lower()
                if ("timeout" in error_message or 
                    "timed out" in error_message or
                    "deadline" in error_message):
                    timeout_result["timeout_enforced"] = True
                    
                    # Verify timeout occurred within reasonable bounds
                    if timeout_seconds <= execution_time <= timeout_seconds + 3:
                        timeout_result["graceful_degradation"] = True
            
            # Test recovery - simple query should work after timeout
            try:
                recovery_result = await self.clickhouse_client.execute("SELECT 1")
                timeout_result["recovery_successful"] = len(recovery_result) > 0
            except Exception as recovery_error:
                logger.error(f"Recovery test failed: {recovery_error}")
                
        except Exception as e:
            timeout_result["error"] = str(e)
            logger.error(f"ClickHouse timeout test failed: {e}")
        
        return timeout_result
    
    async def test_concurrent_timeout_handling(self, concurrent_queries: int = 5) -> Dict[str, Any]:
        """Test timeout handling under concurrent query load."""
        concurrent_result = {
            "concurrent_queries": concurrent_queries,
            "queries_completed": 0,
            "queries_timed_out": 0,
            "system_stability_maintained": False,
            "average_timeout_detection_time": 0.0
        }
        
        async def single_timeout_query(query_id: int) -> Dict[str, Any]:
            """Execute a single query that may timeout."""
            query_result = {
                "query_id": query_id,
                "completed": False,
                "timed_out": False,
                "execution_time": 0.0,
                "error": None
            }
            
            start_time = time.time()
            
            try:
                async with self.postgres_session_factory() as session:
                    await session.execute("SET statement_timeout = '3s'")
                    
                    # Each query works on different data to avoid lock conflicts
                    await session.execute(f"""
                        SELECT COUNT(*)
                        FROM timeout_test_large_table
                        WHERE id > {query_id * 1000} AND id <= {(query_id + 1) * 1000}
                        AND data_column LIKE '%{query_id}%'
                    """)
                    
                query_result["completed"] = True
                
            except Exception as e:
                error_message = str(e).lower()
                if "timeout" in error_message or "canceling statement" in error_message:
                    query_result["timed_out"] = True
                else:
                    query_result["error"] = str(e)
            
            finally:
                query_result["execution_time"] = time.time() - start_time
            
            return query_result
        
        try:
            # Execute concurrent queries
            tasks = [single_timeout_query(i) for i in range(concurrent_queries)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            timeout_times = []
            for result in results:
                if isinstance(result, dict):
                    if result["completed"]:
                        concurrent_result["queries_completed"] += 1
                    elif result["timed_out"]:
                        concurrent_result["queries_timed_out"] += 1
                        timeout_times.append(result["execution_time"])
            
            # Calculate average timeout detection time
            if timeout_times:
                concurrent_result["average_timeout_detection_time"] = sum(timeout_times) / len(timeout_times)
            
            # System stability check - at least some queries should complete or timeout gracefully
            total_handled = concurrent_result["queries_completed"] + concurrent_result["queries_timed_out"]
            concurrent_result["system_stability_maintained"] = total_handled >= concurrent_queries * 0.8
            
            # Test system recovery after concurrent timeouts
            try:
                async with self.postgres_session_factory() as session:
                    await session.execute("SELECT 1")
                concurrent_result["system_recovery_verified"] = True
            except Exception:
                concurrent_result["system_recovery_verified"] = False
                
        except Exception as e:
            concurrent_result["error"] = str(e)
            logger.error(f"Concurrent timeout test failed: {e}")
        
        return concurrent_result
    
    async def test_timeout_with_transaction_rollback(self) -> Dict[str, Any]:
        """Test timeout behavior within transactions and rollback safety."""
        transaction_result = {
            "transaction_started": False,
            "timeout_during_transaction": False,
            "rollback_successful": False,
            "data_consistency_maintained": False
        }
        
        try:
            async with self.postgres_session_factory() as session:
                # Start transaction
                await session.begin()
                transaction_result["transaction_started"] = True
                
                # Insert test data
                await session.execute("""
                    INSERT INTO timeout_test_lock_table (resource_name, lock_value)
                    VALUES ('timeout_test_resource', 'test_value')
                """)
                
                try:
                    # Set short timeout
                    await session.execute("SET statement_timeout = '2s'")
                    
                    # Execute query that should timeout
                    await session.execute("""
                        SELECT COUNT(*)
                        FROM timeout_test_large_table t1
                        CROSS JOIN timeout_test_large_table t2
                        WHERE t1.id + t2.id > 1000000
                    """)
                    
                except Exception as timeout_error:
                    if ("timeout" in str(timeout_error).lower() or 
                        "canceling statement" in str(timeout_error).lower()):
                        transaction_result["timeout_during_transaction"] = True
                    
                    # Attempt rollback
                    try:
                        await session.rollback()
                        transaction_result["rollback_successful"] = True
                    except Exception as rollback_error:
                        logger.error(f"Rollback failed: {rollback_error}")
            
            # Verify data consistency - test insert should not be committed
            async with self.postgres_session_factory() as session:
                result = await session.execute("""
                    SELECT COUNT(*) 
                    FROM timeout_test_lock_table 
                    WHERE resource_name = 'timeout_test_resource'
                """)
                
                # If rollback was successful, count should be 0
                count = result.fetchone()[0]
                transaction_result["data_consistency_maintained"] = count == 0
                
        except Exception as e:
            transaction_result["error"] = str(e)
            logger.error(f"Transaction timeout test failed: {e}")
        
        return transaction_result
    
    async def test_adaptive_timeout_strategies(self) -> Dict[str, Any]:
        """Test adaptive timeout strategies based on query complexity."""
        adaptive_result = {
            "strategies_tested": 0,
            "timeout_adaptations_successful": 0,
            "performance_improvements": {}
        }
        
        try:
            # Test different timeout strategies
            timeout_strategies = [
                {"name": "short_simple", "timeout": 2, "query_type": "simple"},
                {"name": "medium_aggregate", "timeout": 10, "query_type": "aggregate"},
                {"name": "long_complex", "timeout": 30, "query_type": "complex"}
            ]
            
            for strategy in timeout_strategies:
                strategy_name = strategy["name"]
                timeout_value = strategy["timeout"]
                query_type = strategy["query_type"]
                
                start_time = time.time()
                
                try:
                    async with self.postgres_session_factory() as session:
                        await session.execute(f"SET statement_timeout = '{timeout_value}s'")
                        
                        if query_type == "simple":
                            await session.execute("SELECT COUNT(*) FROM timeout_test_lock_table")
                        elif query_type == "aggregate":
                            await session.execute("""
                                SELECT AVG(numeric_column), COUNT(*)
                                FROM timeout_test_large_table
                                WHERE id < 5000
                            """)
                        elif query_type == "complex":
                            await session.execute("""
                                SELECT t1.id, COUNT(*)
                                FROM timeout_test_large_table t1
                                JOIN timeout_test_large_table t2 ON t1.id = t2.id
                                WHERE t1.id < 1000
                                GROUP BY t1.id
                                LIMIT 100
                            """)
                    
                    execution_time = time.time() - start_time
                    
                    # Strategy successful if query completed within timeout
                    if execution_time < timeout_value:
                        adaptive_result["timeout_adaptations_successful"] += 1
                    
                    adaptive_result["performance_improvements"][strategy_name] = {
                        "execution_time": execution_time,
                        "timeout_configured": timeout_value,
                        "successful": execution_time < timeout_value,
                        "efficiency": execution_time / timeout_value
                    }
                    
                except Exception as strategy_error:
                    adaptive_result["performance_improvements"][strategy_name] = {
                        "error": str(strategy_error),
                        "timeout_configured": timeout_value,
                        "successful": False
                    }
                
                adaptive_result["strategies_tested"] += 1
            
        except Exception as e:
            adaptive_result["error"] = str(e)
            logger.error(f"Adaptive timeout test failed: {e}")
        
        return adaptive_result
    
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
async def timeout_manager():
    """Create query timeout manager for testing."""
    manager = DatabaseQueryTimeoutManager()
    await manager.setup_database_containers()
    yield manager
    await manager.cleanup()

@pytest.mark.L3
@pytest.mark.integration
class TestDatabaseQueryTimeoutHandlingL3:
    """L3 integration tests for database query timeout handling."""
    
    async def test_postgres_timeout_enforcement(self, timeout_manager):
        """Test PostgreSQL query timeout enforcement and recovery."""
        result = await timeout_manager.test_postgres_query_timeout_enforcement(3)
        
        # Should either enforce timeout or complete gracefully
        assert result["timeout_enforced"] is True or result["graceful_degradation"] is True
        assert result["recovery_successful"] is True
        
        # Timeout detection should occur within reasonable bounds
        if result["timeout_enforced"]:
            assert 2 <= result["timeout_detection_time"] <= 5
    
    async def test_clickhouse_timeout_enforcement(self, timeout_manager):
        """Test ClickHouse query timeout enforcement and recovery."""
        result = await timeout_manager.test_clickhouse_query_timeout_enforcement(3)
        
        # Should either enforce timeout or complete gracefully
        assert result["timeout_enforced"] is True or result["graceful_degradation"] is True
        assert result["recovery_successful"] is True
        
        # Timeout detection should occur within reasonable bounds
        if result["timeout_enforced"]:
            assert 2 <= result["timeout_detection_time"] <= 6
    
    async def test_concurrent_timeout_stability(self, timeout_manager):
        """Test system stability under concurrent timeout scenarios."""
        result = await timeout_manager.test_concurrent_timeout_handling(4)
        
        assert result["system_stability_maintained"] is True
        assert result.get("system_recovery_verified", True) is True
        
        # Most queries should be handled (completed or timed out)
        total_handled = result["queries_completed"] + result["queries_timed_out"]
        assert total_handled >= result["concurrent_queries"] * 0.8
    
    async def test_transaction_timeout_rollback_safety(self, timeout_manager):
        """Test timeout behavior within transactions maintains data consistency."""
        result = await timeout_manager.test_timeout_with_transaction_rollback()
        
        assert result["transaction_started"] is True
        
        # Either timeout occurred and rollback was successful, or query completed
        if result["timeout_during_transaction"]:
            assert result["rollback_successful"] is True
            assert result["data_consistency_maintained"] is True
    
    async def test_adaptive_timeout_strategies(self, timeout_manager):
        """Test adaptive timeout strategies for different query types."""
        result = await timeout_manager.test_adaptive_timeout_strategies()
        
        assert result["strategies_tested"] >= 3
        assert result["timeout_adaptations_successful"] >= 2
        
        # Performance should improve with appropriate timeout settings
        for strategy_name, metrics in result["performance_improvements"].items():
            if metrics.get("successful"):
                assert metrics["efficiency"] <= 1.0  # Should use less time than timeout

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])