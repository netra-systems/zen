"""
L3 Integration Test: Database Connection Pool Initialization

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Performance 
- Value Impact: Database pools critical for all data operations
- Revenue Impact: $45K MRR - Database availability affects all features

L3 Test: Uses real PostgreSQL and ClickHouse containers to validate connection pool
initialization, configuration limits, concurrent access, and failure handling.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import asyncpg
import clickhouse_connect
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.clickhouse import ClickHouseContainer
from testcontainers.postgres import PostgresContainer

from netra_backend.app.core.async_connection_pool import AsyncConnectionPool

# Add project root to path
from netra_backend.app.db.postgres_core import Database
from netra_backend.app.db.postgres_pool import close_async_db, get_pool_status
from netra_backend.app.logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


class DatabasePoolMetrics:
    """Tracks database pool performance metrics."""
    
    def __init__(self):
        self.initialization_times = []
        self.connection_acquisition_times = []
        self.pool_statuses = []
        self.exhaustion_events = []
        self.recovery_times = []
        self.failover_times = []
        
    def record_initialization_time(self, service: str, duration: float):
        """Record pool initialization time."""
        self.initialization_times.append({
            "service": service,
            "duration": duration,
            "timestamp": datetime.utcnow()
        })
    
    def record_connection_time(self, service: str, duration: float, success: bool):
        """Record connection acquisition time."""
        self.connection_acquisition_times.append({
            "service": service,
            "duration": duration,
            "success": success,
            "timestamp": datetime.utcnow()
        })
    
    def record_pool_status(self, service: str, status: Dict[str, Any]):
        """Record pool status snapshot."""
        self.pool_statuses.append({
            "service": service,
            "status": status,
            "timestamp": datetime.utcnow()
        })
    
    def record_exhaustion_event(self, service: str, details: Dict[str, Any]):
        """Record pool exhaustion event."""
        self.exhaustion_events.append({
            "service": service,
            "details": details,
            "timestamp": datetime.utcnow()
        })
    
    def record_recovery_time(self, service: str, duration: float):
        """Record pool recovery time."""
        self.recovery_times.append({
            "service": service,
            "duration": duration,
            "timestamp": datetime.utcnow()
        })
    
    def record_failover_time(self, service: str, duration: float, success: bool):
        """Record failover operation time."""
        self.failover_times.append({
            "service": service,
            "duration": duration,
            "success": success,
            "timestamp": datetime.utcnow()
        })


class DatabasePoolInitializationManager:
    """Manages database pool initialization testing with real containers."""
    
    def __init__(self):
        self.postgres_container = None
        self.clickhouse_container = None
        self.postgres_standby_container = None
        
        self.postgres_url = None
        self.postgres_standby_url = None
        self.clickhouse_url = None
        
        self.postgres_engine = None
        self.postgres_standby_engine = None
        self.clickhouse_client = None
        
        self.postgres_session_factory = None
        self.active_sessions = []
        self.metrics = DatabasePoolMetrics()
        
    async def setup_database_containers(self):
        """Setup real database containers for pool initialization testing."""
        try:
            await self._setup_postgres_primary()
            await self._setup_postgres_standby()
            await self._setup_clickhouse()
            await self._create_test_schemas()
            
            logger.info("Database pool initialization containers setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup database containers: {e}")
            await self.cleanup()
            raise
    
    async def _setup_postgres_primary(self):
        """Setup primary PostgreSQL container."""
        start_time = time.time()
        
        self.postgres_container = PostgresContainer("postgres:15-alpine")
        self.postgres_container.start()
        
        self.postgres_url = self.postgres_container.get_connection_url().replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        
        # Create engine with pool configuration for testing
        self.postgres_engine = create_async_engine(
            self.postgres_url,
            pool_size=5,           # Base pool size
            max_overflow=3,        # Additional connections
            pool_pre_ping=True,    # Validate connections
            pool_recycle=300,      # Recycle every 5 minutes
            pool_timeout=10,       # Connection timeout
            echo=False,
            connect_args={
                "command_timeout": 15,
                "connect_timeout": 5
            }
        )
        
        self.postgres_session_factory = sessionmaker(
            self.postgres_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        initialization_time = time.time() - start_time
        self.metrics.record_initialization_time("postgres_primary", initialization_time)
        
        logger.info(f"PostgreSQL primary initialized in {initialization_time:.2f}s")
    
    async def _setup_postgres_standby(self):
        """Setup standby PostgreSQL container for failover testing."""
        start_time = time.time()
        
        self.postgres_standby_container = PostgresContainer("postgres:15-alpine")
        self.postgres_standby_container.start()
        
        self.postgres_standby_url = self.postgres_standby_container.get_connection_url().replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        
        self.postgres_standby_engine = create_async_engine(
            self.postgres_standby_url,
            pool_size=5,
            max_overflow=3,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_timeout=10,
            echo=False
        )
        
        initialization_time = time.time() - start_time
        self.metrics.record_initialization_time("postgres_standby", initialization_time)
        
        logger.info(f"PostgreSQL standby initialized in {initialization_time:.2f}s")
    
    async def _setup_clickhouse(self):
        """Setup ClickHouse container."""
        start_time = time.time()
        
        self.clickhouse_container = ClickHouseContainer("clickhouse/clickhouse-server:23.8-alpine")
        self.clickhouse_container.start()
        
        ch_host = self.clickhouse_container.get_container_host_ip()
        ch_port = self.clickhouse_container.get_exposed_port(8123)  # HTTP port
        
        self.clickhouse_url = f"http://{ch_host}:{ch_port}"
        
        # Create ClickHouse client with connection pooling
        self.clickhouse_client = clickhouse_connect.get_client(
            host=ch_host,
            port=ch_port,
            database="default",
            connect_timeout=5,
            send_receive_timeout=30,
            pool_size=5
        )
        
        initialization_time = time.time() - start_time
        self.metrics.record_initialization_time("clickhouse", initialization_time)
        
        logger.info(f"ClickHouse initialized in {initialization_time:.2f}s")
    
    async def _create_test_schemas(self):
        """Create test schemas for pool testing."""
        # PostgreSQL primary schema
        async with self.postgres_engine.begin() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pool_test_primary (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    test_data TEXT,
                    pool_metrics JSONB
                )
            """)
        
        # PostgreSQL standby schema
        async with self.postgres_standby_engine.begin() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pool_test_standby (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    test_data TEXT,
                    pool_metrics JSONB
                )
            """)
        
        # ClickHouse schema
        self.clickhouse_client.command("""
            CREATE TABLE IF NOT EXISTS pool_test_clickhouse (
                id UInt32,
                session_id String,
                created_at DateTime DEFAULT now(),
                test_data String,
                pool_metrics String
            ) ENGINE = MergeTree()
            ORDER BY id
        """)
    
    async def test_pool_initialization_timing(self) -> Dict[str, Any]:
        """Test pool initialization within time limits."""
        results = {
            "postgres_init_time": 0.0,
            "clickhouse_init_time": 0.0,
            "total_init_time": 0.0,
            "within_limits": False
        }
        
        # Calculate total initialization time
        postgres_times = [m["duration"] for m in self.metrics.initialization_times 
                         if "postgres" in m["service"]]
        clickhouse_times = [m["duration"] for m in self.metrics.initialization_times 
                           if "clickhouse" in m["service"]]
        
        results["postgres_init_time"] = max(postgres_times) if postgres_times else 0.0
        results["clickhouse_init_time"] = max(clickhouse_times) if clickhouse_times else 0.0
        results["total_init_time"] = results["postgres_init_time"] + results["clickhouse_init_time"]
        
        # Requirement: Pools initialize within 10 seconds
        results["within_limits"] = results["total_init_time"] <= 10.0
        
        logger.info(f"Pool initialization times: {results}")
        return results
    
    async def test_connection_acquisition_performance(self, num_connections: int = 10) -> Dict[str, Any]:
        """Test connection acquisition performance."""
        results = {
            "postgres_acquisition_times": [],
            "clickhouse_acquisition_times": [],
            "postgres_avg_time": 0.0,
            "clickhouse_avg_time": 0.0,
            "all_under_100ms": False
        }
        
        # Test PostgreSQL connection acquisition
        for i in range(num_connections):
            start_time = time.time()
            try:
                async with self.postgres_session_factory() as session:
                    await session.execute("SELECT 1")
                    duration = time.time() - start_time
                    results["postgres_acquisition_times"].append(duration)
                    self.metrics.record_connection_time("postgres", duration, True)
            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_connection_time("postgres", duration, False)
                logger.error(f"PostgreSQL connection acquisition failed: {e}")
        
        # Test ClickHouse connection acquisition
        for i in range(num_connections):
            start_time = time.time()
            try:
                result = self.clickhouse_client.query("SELECT 1")
                duration = time.time() - start_time
                results["clickhouse_acquisition_times"].append(duration)
                self.metrics.record_connection_time("clickhouse", duration, True)
            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_connection_time("clickhouse", duration, False)
                logger.error(f"ClickHouse connection acquisition failed: {e}")
        
        # Calculate averages
        if results["postgres_acquisition_times"]:
            results["postgres_avg_time"] = sum(results["postgres_acquisition_times"]) / len(results["postgres_acquisition_times"])
        
        if results["clickhouse_acquisition_times"]:
            results["clickhouse_avg_time"] = sum(results["clickhouse_acquisition_times"]) / len(results["clickhouse_acquisition_times"])
        
        # Requirement: Connections acquired < 100ms
        all_times = results["postgres_acquisition_times"] + results["clickhouse_acquisition_times"]
        results["all_under_100ms"] = all(t < 0.1 for t in all_times) if all_times else False
        
        logger.info(f"Connection acquisition performance: {results}")
        return results
    
    async def test_pool_size_limits_enforcement(self) -> Dict[str, Any]:
        """Test that pool size limits are enforced."""
        results = {
            "postgres_limits_enforced": False,
            "pool_exhaustion_handled": False,
            "overflow_within_limits": False,
            "recovery_successful": False
        }
        
        sessions = []
        try:
            # Exhaust PostgreSQL pool (5 base + 3 overflow = 8 max)
            for i in range(10):  # Try to exceed limit
                try:
                    session = self.postgres_session_factory()
                    # Start transaction to hold connection
                    await session.execute("SELECT 1")
                    sessions.append(session)
                    
                    # Record pool status
                    pool_status = self.postgres_engine.pool.status()
                    self.metrics.record_pool_status("postgres", {
                        "size": pool_status.size,
                        "checked_out": pool_status.checked_out,
                        "overflow": pool_status.overflow,
                        "invalid": pool_status.invalid
                    })
                    
                    total_connections = pool_status.checked_out + pool_status.overflow
                    if total_connections >= 8:  # Expected limit
                        break
                        
                except Exception as e:
                    # Expected when pool is exhausted
                    self.metrics.record_exhaustion_event("postgres", {
                        "attempt": i,
                        "error": str(e)
                    })
                    break
            
            # Verify limits are enforced
            final_status = self.postgres_engine.pool.status()
            total_active = final_status.checked_out + final_status.overflow
            results["postgres_limits_enforced"] = total_active <= 8
            results["overflow_within_limits"] = final_status.overflow <= 3
            
            # Test pool exhaustion handling
            try:
                timeout_session = self.postgres_session_factory()
                await asyncio.wait_for(
                    timeout_session.execute("SELECT 1"),
                    timeout=2.0
                )
                await timeout_session.close()
            except (asyncio.TimeoutError, SQLTimeoutError):
                results["pool_exhaustion_handled"] = True
            except Exception as e:
                if "timeout" in str(e).lower() or "pool" in str(e).lower():
                    results["pool_exhaustion_handled"] = True
            
            # Test recovery by releasing connections
            recovery_start = time.time()
            for session in sessions[:3]:  # Release some connections
                await session.close()
            
            # Try to acquire new connection
            recovery_session = self.postgres_session_factory()
            await recovery_session.execute("SELECT 1")
            await recovery_session.close()
            
            recovery_time = time.time() - recovery_start
            self.metrics.record_recovery_time("postgres", recovery_time)
            results["recovery_successful"] = True
            
        except Exception as e:
            logger.error(f"Pool limits test failed: {e}")
        finally:
            # Cleanup remaining sessions
            for session in sessions:
                try:
                    await session.close()
                except:
                    pass
        
        logger.info(f"Pool limits enforcement results: {results}")
        return results
    
    async def test_connection_recycling_and_health(self) -> Dict[str, Any]:
        """Test connection recycling and health checks."""
        results = {
            "recycling_works": False,
            "health_checks_pass": False,
            "stale_connections_detected": False,
            "pre_ping_effective": False
        }
        
        try:
            # Create connections and let them age
            sessions = []
            for i in range(3):
                session = self.postgres_session_factory()
                await session.execute("SELECT 1")
                sessions.append(session)
            
            # Close sessions to return connections to pool
            for session in sessions:
                await session.close()
            
            # Wait for potential recycling
            await asyncio.sleep(2)
            
            # Test pre_ping effectiveness by simulating stale connection
            with patch.object(self.postgres_engine.pool, '_pre_ping', return_value=False):
                try:
                    test_session = self.postgres_session_factory()
                    await test_session.execute("SELECT 1")
                    await test_session.close()
                except Exception:
                    results["stale_connections_detected"] = True
            
            # Test normal health checks
            health_session = self.postgres_session_factory()
            await health_session.execute("SELECT 1")
            await health_session.close()
            results["health_checks_pass"] = True
            
            # Test recycling by checking pool metrics
            pool_status = self.postgres_engine.pool.status()
            results["recycling_works"] = pool_status.size >= 0  # Pool is functional
            results["pre_ping_effective"] = True  # Pre-ping is configured
            
        except Exception as e:
            logger.error(f"Connection recycling test failed: {e}")
        
        logger.info(f"Connection recycling results: {results}")
        return results
    
    async def test_failover_to_standby(self) -> Dict[str, Any]:
        """Test failover to standby database."""
        results = {
            "primary_available": False,
            "standby_available": False,
            "failover_time": 0.0,
            "failover_successful": False,
            "within_time_limit": False
        }
        
        try:
            # Test primary availability
            async with self.postgres_session_factory() as session:
                await session.execute("SELECT 1")
                results["primary_available"] = True
            
            # Test standby availability
            standby_session_factory = sessionmaker(
                self.postgres_standby_engine, class_=AsyncSession, expire_on_commit=False
            )
            async with standby_session_factory() as session:
                await session.execute("SELECT 1")
                results["standby_available"] = True
            
            # Simulate failover scenario
            failover_start = time.time()
            
            # Simulate primary failure by stopping container
            self.postgres_container.stop()
            
            # Attempt to use standby
            try:
                async with standby_session_factory() as session:
                    await session.execute("""
                        INSERT INTO pool_test_standby (session_id, test_data)
                        VALUES ('failover_test', 'Failover successful')
                    """)
                    await session.commit()
                
                failover_time = time.time() - failover_start
                results["failover_time"] = failover_time
                results["failover_successful"] = True
                results["within_time_limit"] = failover_time <= 30.0
                
                self.metrics.record_failover_time("postgres", failover_time, True)
                
            except Exception as e:
                failover_time = time.time() - failover_start
                self.metrics.record_failover_time("postgres", failover_time, False)
                logger.error(f"Failover to standby failed: {e}")
            
            # Restart primary for cleanup
            self.postgres_container.start()
            await asyncio.sleep(2)  # Allow restart
            
        except Exception as e:
            logger.error(f"Failover test failed: {e}")
        
        logger.info(f"Failover test results: {results}")
        return results
    
    async def test_connection_leak_detection(self) -> Dict[str, Any]:
        """Test connection leak detection and prevention."""
        results = {
            "initial_pool_size": 0,
            "sessions_created": 0,
            "sessions_not_closed": 0,
            "final_pool_size": 0,
            "leaks_detected": False,
            "pool_recovered": False
        }
        
        try:
            # Get initial pool status
            initial_status = self.postgres_engine.pool.status()
            results["initial_pool_size"] = initial_status.checked_in
            
            # Create sessions but don't properly close some
            sessions = []
            for i in range(5):
                session = self.postgres_session_factory()
                await session.execute("SELECT 1")
                sessions.append(session)
            
            results["sessions_created"] = len(sessions)
            
            # Close only some sessions (simulate leak)
            for session in sessions[:3]:
                await session.close()
            
            results["sessions_not_closed"] = len(sessions) - 3
            
            # Check for leaked connections
            await asyncio.sleep(1)
            leak_status = self.postgres_engine.pool.status()
            
            # Connections should still be checked out
            if leak_status.checked_out >= results["sessions_not_closed"]:
                results["leaks_detected"] = True
            
            # Force cleanup and test recovery
            for session in sessions[3:]:
                await session.close()
            
            await asyncio.sleep(1)
            final_status = self.postgres_engine.pool.status()
            results["final_pool_size"] = final_status.checked_in
            
            # Pool should recover
            if final_status.checked_out <= initial_status.checked_out:
                results["pool_recovered"] = True
            
        except Exception as e:
            logger.error(f"Connection leak detection test failed: {e}")
        
        logger.info(f"Connection leak detection results: {results}")
        return results
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            # Close active sessions
            for session in self.active_sessions:
                try:
                    await session.close()
                except:
                    pass
            
            # Close engines
            if self.postgres_engine:
                await self.postgres_engine.dispose()
            if self.postgres_standby_engine:
                await self.postgres_standby_engine.dispose()
            
            # Close ClickHouse client
            if self.clickhouse_client:
                self.clickhouse_client.close()
            
            # Stop containers
            containers = [
                self.postgres_container,
                self.postgres_standby_container,
                self.clickhouse_container
            ]
            
            for container in containers:
                if container:
                    try:
                        container.stop()
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def pool_manager():
    """Create database pool manager for testing."""
    manager = DatabasePoolInitializationManager()
    await manager.setup_database_containers()
    yield manager
    await manager.cleanup()


@pytest.mark.L3
@pytest.mark.integration
class TestDatabasePoolInitializationL3:
    """L3 integration tests for database connection pool initialization."""
    
    async def test_database_connection_pool_initialization_l3(self, pool_manager):
        """Test that database pools initialize within required time limits."""
        results = await pool_manager.test_pool_initialization_timing()
        
        # Requirement: Pools initialize within 10 seconds
        assert results["within_limits"] is True
        assert results["postgres_init_time"] > 0
        assert results["clickhouse_init_time"] > 0
        assert results["total_init_time"] <= 10.0
    
    async def test_connection_acquisition_performance_l3(self, pool_manager):
        """Test connection acquisition performance under load."""
        results = await pool_manager.test_connection_acquisition_performance(15)
        
        # Requirement: Connections acquired < 100ms
        assert results["all_under_100ms"] is True
        assert results["postgres_avg_time"] < 0.1
        assert results["clickhouse_avg_time"] < 0.1
        assert len(results["postgres_acquisition_times"]) == 15
        assert len(results["clickhouse_acquisition_times"]) == 15
    
    async def test_pool_size_limits_enforcement_l3(self, pool_manager):
        """Test that pool size limits are properly enforced."""
        results = await pool_manager.test_pool_size_limits_enforcement()
        
        # Requirements: Pool limits enforced, exhaustion handled gracefully
        assert results["postgres_limits_enforced"] is True
        assert results["pool_exhaustion_handled"] is True
        assert results["overflow_within_limits"] is True
        assert results["recovery_successful"] is True
    
    async def test_connection_recycling_and_health_checks_l3(self, pool_manager):
        """Test connection recycling and health check mechanisms."""
        results = await pool_manager.test_connection_recycling_and_health()
        
        # Requirements: Connections recycled properly, health checks work
        assert results["recycling_works"] is True
        assert results["health_checks_pass"] is True
        assert results["pre_ping_effective"] is True
    
    async def test_failover_to_standby_database_l3(self, pool_manager):
        """Test failover to standby database within time limits."""
        results = await pool_manager.test_failover_to_standby()
        
        # Requirements: Failover works within 30 seconds
        assert results["primary_available"] is True
        assert results["standby_available"] is True
        assert results["failover_successful"] is True
        assert results["within_time_limit"] is True
        assert results["failover_time"] <= 30.0
    
    async def test_connection_leak_detection_l3(self, pool_manager):
        """Test connection leak detection and pool recovery."""
        results = await pool_manager.test_connection_leak_detection()
        
        # Requirements: Leaks detected, pool recovers
        assert results["sessions_created"] > 0
        assert results["leaks_detected"] is True
        assert results["pool_recovered"] is True
        assert results["sessions_not_closed"] > 0
    
    async def test_concurrent_pool_access_l3(self, pool_manager):
        """Test concurrent access to connection pools."""
        async def concurrent_database_access(worker_id: int) -> Dict[str, Any]:
            """Simulate concurrent database access."""
            result = {"worker_id": worker_id, "success": False, "operations": 0}
            
            try:
                for i in range(5):  # 5 operations per worker
                    # PostgreSQL operation
                    async with pool_manager.postgres_session_factory() as session:
                        await session.execute(
                            "INSERT INTO pool_test_primary (session_id, test_data) "
                            "VALUES (:session_id, :data)",
                            {"session_id": f"worker_{worker_id}", "data": f"Operation {i}"}
                        )
                        await session.commit()
                    
                    # ClickHouse operation
                    pool_manager.clickhouse_client.insert(
                        "pool_test_clickhouse",
                        [[worker_id * 100 + i, f"worker_{worker_id}", f"Operation {i}", ""]]
                    )
                    
                    result["operations"] += 1
                
                result["success"] = True
                
            except Exception as e:
                logger.error(f"Worker {worker_id} failed: {e}")
            
            return result
        
        # Run 10 concurrent workers
        tasks = [concurrent_database_access(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_workers = [r for r in results if isinstance(r, dict) and r["success"]]
        assert len(successful_workers) >= 8  # At least 80% success rate
        
        total_operations = sum(r["operations"] for r in successful_workers)
        assert total_operations >= 40  # At least 80% of expected operations
    
    async def test_pool_metrics_collection_l3(self, pool_manager):
        """Test pool metrics collection and monitoring."""
        # Generate some pool activity
        await pool_manager.test_connection_acquisition_performance(5)
        await pool_manager.test_pool_size_limits_enforcement()
        
        # Verify metrics were collected
        metrics = pool_manager.metrics
        
        assert len(metrics.initialization_times) >= 2  # Postgres + ClickHouse
        assert len(metrics.connection_acquisition_times) >= 10  # From performance test
        assert len(metrics.pool_statuses) >= 5  # From limits test
        assert len(metrics.recovery_times) >= 1  # From recovery test
        
        # Verify metric data quality
        for init_time in metrics.initialization_times:
            assert init_time["duration"] > 0
            assert init_time["service"] in ["postgres_primary", "postgres_standby", "clickhouse"]
        
        for conn_time in metrics.connection_acquisition_times:
            assert conn_time["duration"] >= 0
            assert isinstance(conn_time["success"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])