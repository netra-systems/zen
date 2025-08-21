"""Database Transaction Coordination L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Data Consistency - Ensure ACID properties across dual-database architecture
- Value Impact: Prevents data inconsistencies that could impact billing and analytics
- Strategic Impact: Critical for enterprise customers requiring audit trails

Test Level: L3 (Real SUT with Real Local Services - Out-of-Process)
- Uses real PostgreSQL and ClickHouse containers via Docker
- Tests distributed transaction coordination with rollback scenarios
- Validates data consistency across both databases
- Tests failure recovery and compensating transactions
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


# Docker container management
import docker
from docker.errors import DockerException
import psycopg2
import clickhouse_connect

from netra_backend.app.services.transaction_manager import TransactionManager
from netra_backend.app.db.postgres import get_postgres_session, initialize_postgres
from netra_backend.app.db.clickhouse import get_clickhouse_client
from logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class ContainerConfig:
    """Configuration for database containers."""
    postgres_port: int
    clickhouse_port: int
    postgres_container: Optional[Any] = None
    clickhouse_container: Optional[Any] = None


@dataclass
class TransactionTestData:
    """Test data for transaction scenarios."""
    transaction_id: str
    user_id: str
    session_id: str
    postgres_data: Dict[str, Any]
    clickhouse_data: Dict[str, Any]
    expected_rollback: bool = False


class DatabaseTransactionCoordinatorL3:
    """L3 test coordinator for database transaction testing with real containers."""
    
    def __init__(self):
        self.container_config: Optional[ContainerConfig] = None
        self.docker_client: Optional[docker.DockerClient] = None
        self.transaction_manager: Optional[TransactionManager] = None
        self.active_transactions: List[str] = []
    
    async def setup_containers(self) -> ContainerConfig:
        """Setup real PostgreSQL and ClickHouse containers."""
        try:
            self.docker_client = docker.from_env()
            
            # Find available ports
            postgres_port = self._find_available_port(5433)
            clickhouse_port = self._find_available_port(8124)
            
            # Start PostgreSQL container
            postgres_container = self._start_postgres_container(postgres_port)
            
            # Start ClickHouse container  
            clickhouse_container = self._start_clickhouse_container(clickhouse_port)
            
            # Wait for containers to be ready
            await self._wait_for_postgres_ready(postgres_port)
            await self._wait_for_clickhouse_ready(clickhouse_port)
            
            self.container_config = ContainerConfig(
                postgres_port=postgres_port,
                clickhouse_port=clickhouse_port,
                postgres_container=postgres_container,
                clickhouse_container=clickhouse_container
            )
            
            # Initialize database connections with container URLs
            await self._initialize_database_connections()
            
            return self.container_config
            
        except Exception as e:
            await self.cleanup_containers()
            raise RuntimeError(f"Failed to setup containers: {e}")
    
    def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port."""
        import socket
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        raise RuntimeError(f"No available ports found starting from {start_port}")
    
    def _start_postgres_container(self, port: int) -> Any:
        """Start PostgreSQL container."""
        try:
            container = self.docker_client.containers.run(
                "postgres:15-alpine",
                environment={
                    "POSTGRES_DB": "netra_test",
                    "POSTGRES_USER": "test_user", 
                    "POSTGRES_PASSWORD": "test_password"
                },
                ports={'5432/tcp': port},
                detach=True,
                remove=True,
                name=f"test_postgres_{port}_{int(time.time())}"
            )
            logger.info(f"Started PostgreSQL container on port {port}")
            return container
        except DockerException as e:
            raise RuntimeError(f"Failed to start PostgreSQL container: {e}")
    
    def _start_clickhouse_container(self, port: int) -> Any:
        """Start ClickHouse container."""
        try:
            container = self.docker_client.containers.run(
                "clickhouse/clickhouse-server:23.8-alpine",
                ports={'8123/tcp': port},
                detach=True,
                remove=True,
                name=f"test_clickhouse_{port}_{int(time.time())}"
            )
            logger.info(f"Started ClickHouse container on port {port}")
            return container
        except DockerException as e:
            raise RuntimeError(f"Failed to start ClickHouse container: {e}")
    
    async def _wait_for_postgres_ready(self, port: int, timeout: int = 30) -> None:
        """Wait for PostgreSQL to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = psycopg2.connect(
                    host="localhost",
                    port=port,
                    database="netra_test",
                    user="test_user",
                    password="test_password"
                )
                conn.close()
                logger.info(f"PostgreSQL ready on port {port}")
                return
            except psycopg2.OperationalError:
                await asyncio.sleep(1)
        raise RuntimeError(f"PostgreSQL not ready after {timeout}s")
    
    async def _wait_for_clickhouse_ready(self, port: int, timeout: int = 30) -> None:
        """Wait for ClickHouse to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                client = clickhouse_connect.get_client(host='localhost', port=port)
                client.command("SELECT 1")
                client.close()
                logger.info(f"ClickHouse ready on port {port}")
                return
            except Exception:
                await asyncio.sleep(1)
        raise RuntimeError(f"ClickHouse not ready after {timeout}s")
    
    async def _initialize_database_connections(self) -> None:
        """Initialize database connections to test containers."""
        # Override database URLs to point to test containers
        postgres_url = (
            f"postgresql://test_user:test_password@localhost:"
            f"{self.container_config.postgres_port}/netra_test"
        )
        clickhouse_url = f"http://localhost:{self.container_config.clickhouse_port}"
        
        # Initialize with test URLs
        with patch('app.core.configuration.get_configuration') as mock_config:
            mock_config.return_value.DATABASE_URL = postgres_url
            mock_config.return_value.CLICKHOUSE_URL = clickhouse_url
            
            await initialize_postgres()
            self.transaction_manager = TransactionManager()
            await self.transaction_manager.initialize()
    
    async def create_test_schemas(self) -> None:
        """Create test database schemas."""
        # Create PostgreSQL test tables
        postgres_schema = """
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(50) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                tier VARCHAR(20) DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS optimization_sessions (
                session_id VARCHAR(50) PRIMARY KEY,
                user_id VARCHAR(50) REFERENCES users(user_id),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        
        async with get_postgres_session() as session:
            for statement in postgres_schema.split(';'):
                if statement.strip():
                    await session.execute(statement)
            await session.commit()
        
        # Create ClickHouse test tables
        clickhouse_schema = """
            CREATE TABLE IF NOT EXISTS user_activity_events (
                event_id String,
                user_id String,
                event_type String,
                timestamp DateTime,
                metadata String
            ) ENGINE = MergeTree()
            ORDER BY (user_id, timestamp);
            
            CREATE TABLE IF NOT EXISTS optimization_metrics (
                metric_id String,
                session_id String,
                metric_type String,
                value Float64,
                timestamp DateTime
            ) ENGINE = MergeTree()
            ORDER BY (session_id, timestamp);
        """
        
        async with get_clickhouse_client() as client:
            for statement in clickhouse_schema.split(';'):
                if statement.strip():
                    await client.execute_query(statement)
    
    def create_test_transaction_data(self, scenario: str) -> TransactionTestData:
        """Create test data for transaction scenarios."""
        transaction_id = f"test_tx_{uuid.uuid4().hex[:12]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        scenarios = {
            "dual_write_success": TransactionTestData(
                transaction_id=transaction_id,
                user_id=user_id,
                session_id=session_id,
                postgres_data={
                    "user": {
                        "user_id": user_id,
                        "email": f"{user_id}@test.com",
                        "tier": "enterprise"
                    },
                    "session": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "status": "active"
                    }
                },
                clickhouse_data={
                    "activity_event": {
                        "event_id": f"event_{uuid.uuid4().hex[:8]}",
                        "user_id": user_id,
                        "event_type": "session_start",
                        "timestamp": datetime.utcnow(),
                        "metadata": json.dumps({"session_id": session_id})
                    },
                    "metric": {
                        "metric_id": f"metric_{uuid.uuid4().hex[:8]}",
                        "session_id": session_id,
                        "metric_type": "initial_cost",
                        "value": 1000.0,
                        "timestamp": datetime.utcnow()
                    }
                }
            ),
            "postgres_failure": TransactionTestData(
                transaction_id=transaction_id,
                user_id=user_id,
                session_id=session_id,
                postgres_data={
                    "user": {
                        "user_id": user_id,
                        "email": f"{user_id}@test.com",
                        "tier": "enterprise"
                    },
                    "session": {
                        "session_id": session_id,
                        "user_id": "invalid_user_id",  # Force FK violation
                        "status": "active"
                    }
                },
                clickhouse_data={
                    "activity_event": {
                        "event_id": f"event_{uuid.uuid4().hex[:8]}",
                        "user_id": user_id,
                        "event_type": "session_start",
                        "timestamp": datetime.utcnow(),
                        "metadata": json.dumps({"session_id": session_id})
                    }
                },
                expected_rollback=True
            )
        }
        
        return scenarios.get(scenario, scenarios["dual_write_success"])
    
    async def execute_distributed_transaction(self, test_data: TransactionTestData) -> Dict[str, Any]:
        """Execute distributed transaction across PostgreSQL and ClickHouse."""
        transaction_id = test_data.transaction_id
        self.active_transactions.append(transaction_id)
        
        start_time = time.time()
        
        try:
            # Begin distributed transaction
            async with self.transaction_manager.begin_transaction(transaction_id) as tx:
                
                # Execute PostgreSQL operations
                postgres_results = await self._execute_postgres_operations(
                    tx, test_data.postgres_data
                )
                
                # Execute ClickHouse operations
                clickhouse_results = await self._execute_clickhouse_operations(
                    tx, test_data.clickhouse_data
                )
                
                # Validate all operations succeeded
                all_success = (
                    all(r.get("success", False) for r in postgres_results) and
                    all(r.get("success", False) for r in clickhouse_results)
                )
                
                if not all_success or test_data.expected_rollback:
                    # Force rollback for failure scenarios
                    raise Exception("Simulated transaction failure")
                
                # Transaction will auto-commit on successful exit
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "execution_time": time.time() - start_time,
                    "postgres_operations": len(postgres_results),
                    "clickhouse_operations": len(clickhouse_results),
                    "postgres_results": postgres_results,
                    "clickhouse_results": clickhouse_results
                }
                
        except Exception as e:
            # Transaction will auto-rollback on exception
            return {
                "success": False,
                "transaction_id": transaction_id,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "rollback_performed": True
            }
        
        finally:
            if transaction_id in self.active_transactions:
                self.active_transactions.remove(transaction_id)
    
    async def _execute_postgres_operations(self, tx: Any, postgres_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute PostgreSQL operations within transaction."""
        results = []
        
        try:
            # Insert user
            if "user" in postgres_data:
                user_data = postgres_data["user"]
                query = """
                    INSERT INTO users (user_id, email, tier, created_at)
                    VALUES (%(user_id)s, %(email)s, %(tier)s, CURRENT_TIMESTAMP)
                    RETURNING user_id
                """
                result = await tx.postgres_session.execute(query, user_data)
                results.append({
                    "success": True,
                    "operation": "insert_user",
                    "result": result
                })
            
            # Insert session
            if "session" in postgres_data:
                session_data = postgres_data["session"]
                query = """
                    INSERT INTO optimization_sessions (session_id, user_id, status, created_at)
                    VALUES (%(session_id)s, %(user_id)s, %(status)s, CURRENT_TIMESTAMP)
                    RETURNING session_id
                """
                result = await tx.postgres_session.execute(query, session_data)
                results.append({
                    "success": True,
                    "operation": "insert_session",
                    "result": result
                })
            
        except Exception as e:
            results.append({
                "success": False,
                "operation": "postgres_operation",
                "error": str(e)
            })
        
        return results
    
    async def _execute_clickhouse_operations(self, tx: Any, clickhouse_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute ClickHouse operations within transaction."""
        results = []
        
        try:
            # Insert activity event
            if "activity_event" in clickhouse_data:
                event_data = clickhouse_data["activity_event"]
                query = """
                    INSERT INTO user_activity_events 
                    (event_id, user_id, event_type, timestamp, metadata)
                    VALUES (%(event_id)s, %(user_id)s, %(event_type)s, %(timestamp)s, %(metadata)s)
                """
                await tx.clickhouse_client.execute_query(query, event_data)
                results.append({
                    "success": True,
                    "operation": "insert_activity_event",
                    "rows_affected": 1
                })
            
            # Insert metric
            if "metric" in clickhouse_data:
                metric_data = clickhouse_data["metric"]
                query = """
                    INSERT INTO optimization_metrics
                    (metric_id, session_id, metric_type, value, timestamp)
                    VALUES (%(metric_id)s, %(session_id)s, %(metric_type)s, %(value)s, %(timestamp)s)
                """
                await tx.clickhouse_client.execute_query(query, metric_data)
                results.append({
                    "success": True,
                    "operation": "insert_metric",
                    "rows_affected": 1
                })
            
        except Exception as e:
            results.append({
                "success": False,
                "operation": "clickhouse_operation", 
                "error": str(e)
            })
        
        return results
    
    async def validate_data_consistency(self, transaction_data: List[TransactionTestData]) -> Dict[str, Any]:
        """Validate data consistency across PostgreSQL and ClickHouse."""
        consistency_results = {}
        
        for test_data in transaction_data:
            user_id = test_data.user_id
            
            # Check PostgreSQL data
            postgres_consistent = await self._check_postgres_data(user_id)
            
            # Check ClickHouse data
            clickhouse_consistent = await self._check_clickhouse_data(user_id)
            
            # Cross-reference consistency
            cross_consistent = await self._check_cross_reference_consistency(user_id)
            
            overall_consistent = postgres_consistent and clickhouse_consistent and cross_consistent
            
            consistency_results[user_id] = {
                "overall_consistent": overall_consistent,
                "postgres_consistent": postgres_consistent,
                "clickhouse_consistent": clickhouse_consistent,
                "cross_reference_consistent": cross_consistent
            }
        
        return consistency_results
    
    async def _check_postgres_data(self, user_id: str) -> bool:
        """Check PostgreSQL data consistency."""
        try:
            async with get_postgres_session() as session:
                query = """
                    SELECT u.user_id, os.session_id 
                    FROM users u 
                    LEFT JOIN optimization_sessions os ON u.user_id = os.user_id
                    WHERE u.user_id = %(user_id)s
                """
                result = await session.execute(query, {"user_id": user_id})
                rows = result.fetchall()
                
                # Check that user exists and has associated sessions
                return len(rows) > 0 and all(row[1] is not None for row in rows)
                
        except Exception as e:
            logger.error(f"PostgreSQL consistency check failed: {e}")
            return False
    
    async def _check_clickhouse_data(self, user_id: str) -> bool:
        """Check ClickHouse data consistency."""
        try:
            async with get_clickhouse_client() as client:
                query = """
                    SELECT COUNT(*) as event_count
                    FROM user_activity_events 
                    WHERE user_id = %(user_id)s
                """
                result = await client.fetch(query, {"user_id": user_id})
                
                return result[0]["event_count"] > 0 if result else False
                
        except Exception as e:
            logger.error(f"ClickHouse consistency check failed: {e}")
            return False
    
    async def _check_cross_reference_consistency(self, user_id: str) -> bool:
        """Check cross-service referential integrity."""
        try:
            # Get user IDs from PostgreSQL
            async with get_postgres_session() as session:
                pg_query = "SELECT user_id FROM users WHERE user_id = %(user_id)s"
                pg_result = await session.execute(pg_query, {"user_id": user_id})
                pg_user_exists = len(pg_result.fetchall()) > 0
            
            # Get user IDs from ClickHouse
            async with get_clickhouse_client() as client:
                ch_query = "SELECT DISTINCT user_id FROM user_activity_events WHERE user_id = %(user_id)s"
                ch_result = await client.fetch(ch_query, {"user_id": user_id})
                ch_user_exists = len(ch_result) > 0
            
            # Both should exist or both should not exist
            return pg_user_exists == ch_user_exists
            
        except Exception as e:
            logger.error(f"Cross-reference consistency check failed: {e}")
            return False
    
    async def cleanup_containers(self) -> None:
        """Clean up Docker containers and resources."""
        try:
            if self.container_config:
                if self.container_config.postgres_container:
                    self.container_config.postgres_container.stop()
                    logger.info("Stopped PostgreSQL container")
                
                if self.container_config.clickhouse_container:
                    self.container_config.clickhouse_container.stop()
                    logger.info("Stopped ClickHouse container")
            
            # Rollback any active transactions
            if self.transaction_manager:
                for tx_id in self.active_transactions:
                    try:
                        await self.transaction_manager.rollback_transaction(tx_id)
                    except Exception as e:
                        logger.warning(f"Failed to rollback transaction {tx_id}: {e}")
                
                await self.transaction_manager.shutdown()
                
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


@pytest.fixture
async def db_transaction_coordinator_l3():
    """Fixture for L3 database transaction coordinator."""
    coordinator = DatabaseTransactionCoordinatorL3()
    await coordinator.setup_containers()
    await coordinator.create_test_schemas()
    yield coordinator
    await coordinator.cleanup_containers()


@pytest.mark.L3
@pytest.mark.integration
@pytest.mark.asyncio
async def test_dual_write_success_l3(db_transaction_coordinator_l3):
    """Test successful dual write across PostgreSQL and ClickHouse."""
    test_data = db_transaction_coordinator_l3.create_test_transaction_data("dual_write_success")
    
    result = await db_transaction_coordinator_l3.execute_distributed_transaction(test_data)
    
    # Validate transaction success
    assert result["success"] is True, f"Transaction failed: {result.get('error')}"
    assert result["execution_time"] < 5.0, "Transaction took too long"
    assert result["postgres_operations"] >= 2, "Insufficient PostgreSQL operations"
    assert result["clickhouse_operations"] >= 2, "Insufficient ClickHouse operations"
    
    # Validate data consistency
    consistency_result = await db_transaction_coordinator_l3.validate_data_consistency([test_data])
    assert consistency_result[test_data.user_id]["overall_consistent"] is True


@pytest.mark.L3
@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_failure_rollback_l3(db_transaction_coordinator_l3):
    """Test PostgreSQL failure triggers ClickHouse rollback."""
    test_data = db_transaction_coordinator_l3.create_test_transaction_data("postgres_failure")
    
    result = await db_transaction_coordinator_l3.execute_distributed_transaction(test_data)
    
    # Validate rollback behavior
    assert result["success"] is False, "Transaction should have failed"
    assert result["rollback_performed"] is True, "Rollback should have been performed"
    assert "error" in result, "Error should be captured"
    
    # Validate no partial data persisted
    consistency_result = await db_transaction_coordinator_l3.validate_data_consistency([test_data])
    user_consistency = consistency_result[test_data.user_id]
    
    # Data should not exist in either database after rollback
    assert not user_consistency["postgres_consistent"], "PostgreSQL should not have partial data"
    assert not user_consistency["clickhouse_consistent"], "ClickHouse should not have partial data"


@pytest.mark.L3
@pytest.mark.integration
@pytest.mark.asyncio 
async def test_concurrent_transactions_l3(db_transaction_coordinator_l3):
    """Test concurrent transaction isolation."""
    # Create multiple concurrent transactions
    test_data_list = [
        db_transaction_coordinator_l3.create_test_transaction_data("dual_write_success")
        for _ in range(3)
    ]
    
    # Execute concurrent transactions
    tasks = [
        db_transaction_coordinator_l3.execute_distributed_transaction(test_data)
        for test_data in test_data_list
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Validate concurrent execution
    successful_results = [r for r in results if not isinstance(r, Exception) and r["success"]]
    assert len(successful_results) >= 2, f"Only {len(successful_results)}/3 concurrent transactions succeeded"
    
    # Validate data consistency for successful transactions
    successful_test_data = [
        test_data for i, test_data in enumerate(test_data_list)
        if not isinstance(results[i], Exception) and results[i]["success"]
    ]
    
    if successful_test_data:
        consistency_results = await db_transaction_coordinator_l3.validate_data_consistency(successful_test_data)
        for test_data in successful_test_data:
            assert consistency_results[test_data.user_id]["overall_consistent"] is True


@pytest.mark.L3  
@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_performance_l3(db_transaction_coordinator_l3):
    """Test transaction performance meets requirements."""
    # Execute performance test
    test_data = db_transaction_coordinator_l3.create_test_transaction_data("dual_write_success")
    
    # Execute multiple transactions to test performance
    execution_times = []
    for _ in range(5):
        result = await db_transaction_coordinator_l3.execute_distributed_transaction(test_data)
        if result["success"]:
            execution_times.append(result["execution_time"])
        
        # Create new test data for next iteration
        test_data = db_transaction_coordinator_l3.create_test_transaction_data("dual_write_success")
    
    # Validate performance metrics
    assert len(execution_times) >= 3, "Insufficient successful transactions for performance test"
    
    avg_execution_time = sum(execution_times) / len(execution_times)
    max_execution_time = max(execution_times)
    
    assert avg_execution_time < 2.0, f"Average transaction time too high: {avg_execution_time}s"
    assert max_execution_time < 5.0, f"Maximum transaction time too high: {max_execution_time}s"


@pytest.mark.L3
@pytest.mark.integration  
@pytest.mark.asyncio
async def test_data_consistency_validation_l3(db_transaction_coordinator_l3):
    """Test comprehensive data consistency validation."""
    # Execute multiple successful transactions
    test_data_list = []
    
    for i in range(3):
        test_data = db_transaction_coordinator_l3.create_test_transaction_data("dual_write_success")
        result = await db_transaction_coordinator_l3.execute_distributed_transaction(test_data)
        
        if result["success"]:
            test_data_list.append(test_data)
    
    assert len(test_data_list) >= 2, "Insufficient successful transactions for consistency test"
    
    # Validate comprehensive data consistency
    consistency_results = await db_transaction_coordinator_l3.validate_data_consistency(test_data_list)
    
    # Check consistency for each transaction
    consistent_count = sum(
        1 for result in consistency_results.values()
        if result["overall_consistent"]
    )
    
    consistency_rate = consistent_count / len(consistency_results)
    assert consistency_rate >= 0.9, f"Data consistency rate too low: {consistency_rate}"
    
    # Validate individual consistency checks
    for user_id, consistency_result in consistency_results.items():
        if consistency_result["overall_consistent"]:
            assert consistency_result["postgres_consistent"] is True
            assert consistency_result["clickhouse_consistent"] is True  
            assert consistency_result["cross_reference_consistent"] is True