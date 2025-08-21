"""
L3 Integration Test: PostgreSQL Connection Pool Exhaustion and Recovery

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Stability - Prevent database connection exhaustion
- Value Impact: Prevents service outages that could affect $45K MRR
- Strategic Impact: Ensures platform reliability under load

L3 Test: Uses real PostgreSQL via Testcontainers to validate connection pool behavior.
Tests pool exhaustion, recovery mechanisms, and connection lifecycle management.
"""

import pytest
import asyncio
import time
import uuid
from typing import List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
import psycopg2
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from netra_backend.app.db.postgres import get_async_db, get_postgres_session
from netra_backend.app.db.postgres_core import Database, async_engine
from netra_backend.app.db.postgres_pool import get_pool_status, close_async_db
from logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PostgresPoolExhaustionManager:
    """Manages PostgreSQL connection pool testing with real containers."""
    
    def __init__(self):
        self.container = None
        self.db_url = None
        self.test_engine = None
        self.session_factory = None
        self.active_connections = []
        self.pool_metrics = {}
        
    async def setup_postgres_container(self):
        """Setup real PostgreSQL container for L3 testing."""
        try:
            self.container = PostgresContainer("postgres:15-alpine")
            self.container.start()
            
            # Get connection details
            self.db_url = self.container.get_connection_url().replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            # Create test engine with limited pool size
            self.test_engine = create_async_engine(
                self.db_url,
                pool_size=5,  # Small pool for exhaustion testing
                max_overflow=2,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            
            self.session_factory = sessionmaker(
                self.test_engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Initialize test schema
            await self.create_test_schema()
            
            logger.info("PostgreSQL container setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL container: {e}")
            await self.cleanup()
            raise
    
    async def create_test_schema(self):
        """Create test tables for connection pool testing."""
        async with self.test_engine.begin() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pool_test_table (
                    id SERIAL PRIMARY KEY,
                    connection_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    test_data TEXT
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pool_test_connection_id 
                ON pool_test_table(connection_id)
            """)
    
    async def exhaust_connection_pool(self, target_connections: int = 8) -> List[AsyncSession]:
        """Exhaust the connection pool by creating multiple sessions."""
        sessions = []
        
        try:
            for i in range(target_connections):
                session = self.session_factory()
                
                # Start a transaction to hold the connection
                await session.execute("SELECT 1")
                await session.execute(
                    "INSERT INTO pool_test_table (connection_id, test_data) "
                    "VALUES (:conn_id, :data)",
                    {"conn_id": f"conn_{i}", "data": f"Test data {i}"}
                )
                
                sessions.append(session)
                self.active_connections.append(session)
                
                # Record pool metrics
                pool_status = self.test_engine.pool.status()
                self.pool_metrics[f"step_{i}"] = {
                    "size": pool_status.size,
                    "checked_in": pool_status.checked_in,
                    "checked_out": pool_status.checked_out,
                    "overflow": pool_status.overflow,
                    "invalid": pool_status.invalid
                }
                
                logger.debug(f"Created connection {i+1}, pool status: {pool_status}")
            
            return sessions
            
        except Exception as e:
            # Cleanup partial sessions on error
            for session in sessions:
                try:
                    await session.close()
                except:
                    pass
            raise
    
    async def test_pool_exhaustion_behavior(self) -> Dict[str, Any]:
        """Test behavior when pool is exhausted."""
        results = {
            "exhaustion_achieved": False,
            "timeout_occurred": False,
            "recovery_successful": False,
            "error_details": None
        }
        
        try:
            # Exhaust the pool
            sessions = await self.exhaust_connection_pool(8)
            results["exhaustion_achieved"] = True
            
            # Try to create one more connection (should timeout)
            start_time = time.time()
            try:
                timeout_session = self.session_factory()
                await asyncio.wait_for(
                    timeout_session.execute("SELECT 1"), 
                    timeout=2.0
                )
                await timeout_session.close()
            except asyncio.TimeoutError:
                results["timeout_occurred"] = True
                logger.info("Pool exhaustion timeout occurred as expected")
            except Exception as e:
                results["error_details"] = str(e)
                logger.info(f"Pool exhaustion error: {e}")
            
            # Release half the connections
            for i in range(len(sessions) // 2):
                await sessions[i].close()
                
            # Test recovery
            await asyncio.sleep(1)  # Allow pool to recover
            recovery_session = self.session_factory()
            await recovery_session.execute("SELECT 1")
            await recovery_session.close()
            results["recovery_successful"] = True
            
            # Cleanup remaining sessions
            for session in sessions[len(sessions) // 2:]:
                await session.close()
                
        except Exception as e:
            results["error_details"] = str(e)
            logger.error(f"Pool exhaustion test failed: {e}")
        
        return results
    
    async def test_connection_lifecycle(self) -> Dict[str, Any]:
        """Test complete connection lifecycle management."""
        results = {
            "connection_created": False,
            "transaction_completed": False,
            "connection_released": False,
            "pool_status_tracked": False
        }
        
        try:
            initial_status = self.test_engine.pool.status()
            
            # Create and use connection
            async with self.session_factory() as session:
                results["connection_created"] = True
                
                # Perform transaction
                await session.execute(
                    "INSERT INTO pool_test_table (connection_id, test_data) "
                    "VALUES (:conn_id, :data)",
                    {"conn_id": "lifecycle_test", "data": "Connection lifecycle test"}
                )
                await session.commit()
                results["transaction_completed"] = True
                
                # Check pool status during use
                active_status = self.test_engine.pool.status()
                assert active_status.checked_out >= initial_status.checked_out
            
            # Verify connection was released
            await asyncio.sleep(0.1)
            final_status = self.test_engine.pool.status()
            results["connection_released"] = True
            results["pool_status_tracked"] = True
            
            # Verify pool statistics
            assert final_status.checked_out <= initial_status.checked_out
            
        except Exception as e:
            logger.error(f"Connection lifecycle test failed: {e}")
            raise
        
        return results
    
    async def test_concurrent_connection_requests(self, concurrent_count: int = 10) -> Dict[str, Any]:
        """Test concurrent connection requests behavior."""
        results = {
            "requests_completed": 0,
            "timeouts_occurred": 0,
            "errors_occurred": 0,
            "average_response_time": 0.0,
            "max_response_time": 0.0
        }
        
        async def single_connection_request(request_id: int) -> Dict[str, Any]:
            start_time = time.time()
            request_result = {
                "id": request_id,
                "success": False,
                "response_time": 0.0,
                "error": None
            }
            
            try:
                async with self.session_factory() as session:
                    await session.execute("SELECT 1")
                    await session.execute(
                        "INSERT INTO pool_test_table (connection_id, test_data) "
                        "VALUES (:conn_id, :data)",
                        {"conn_id": f"concurrent_{request_id}", "data": f"Concurrent test {request_id}"}
                    )
                    await session.commit()
                    
                request_result["success"] = True
                
            except Exception as e:
                request_result["error"] = str(e)
                
            finally:
                request_result["response_time"] = time.time() - start_time
                
            return request_result
        
        # Execute concurrent requests
        tasks = [single_connection_request(i) for i in range(concurrent_count)]
        request_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        response_times = []
        for result in request_results:
            if isinstance(result, dict):
                if result["success"]:
                    results["requests_completed"] += 1
                    response_times.append(result["response_time"])
                else:
                    results["errors_occurred"] += 1
                    if "timeout" in str(result.get("error", "")).lower():
                        results["timeouts_occurred"] += 1
        
        if response_times:
            results["average_response_time"] = sum(response_times) / len(response_times)
            results["max_response_time"] = max(response_times)
        
        return results
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            # Close active connections
            for connection in self.active_connections:
                try:
                    await connection.close()
                except:
                    pass
            
            # Close test engine
            if self.test_engine:
                await self.test_engine.dispose()
            
            # Stop container
            if self.container:
                self.container.stop()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def pool_manager():
    """Create PostgreSQL pool manager for testing."""
    manager = PostgresPoolExhaustionManager()
    await manager.setup_postgres_container()
    yield manager
    await manager.cleanup()


@pytest.mark.L3
@pytest.mark.integration
class TestPostgresConnectionPoolExhaustionL3:
    """L3 integration tests for PostgreSQL connection pool exhaustion."""
    
    async def test_connection_pool_exhaustion_and_recovery(self, pool_manager):
        """Test that connection pool handles exhaustion gracefully."""
        results = await pool_manager.test_pool_exhaustion_behavior()
        
        assert results["exhaustion_achieved"] is True
        assert results["timeout_occurred"] is True or results["error_details"] is not None
        assert results["recovery_successful"] is True
    
    async def test_connection_lifecycle_management(self, pool_manager):
        """Test complete connection lifecycle from creation to release."""
        results = await pool_manager.test_connection_lifecycle()
        
        assert results["connection_created"] is True
        assert results["transaction_completed"] is True
        assert results["connection_released"] is True
        assert results["pool_status_tracked"] is True
    
    async def test_concurrent_connection_performance(self, pool_manager):
        """Test performance under concurrent connection requests."""
        results = await pool_manager.test_concurrent_connection_requests(15)
        
        # Should handle at least 80% of requests successfully
        success_rate = results["requests_completed"] / 15
        assert success_rate >= 0.8
        
        # Response times should be reasonable
        assert results["average_response_time"] < 2.0
        assert results["max_response_time"] < 5.0
    
    async def test_pool_monitoring_and_metrics(self, pool_manager):
        """Test pool status monitoring and metrics collection."""
        # Create some connections to generate metrics
        sessions = await pool_manager.exhaust_connection_pool(3)
        
        # Verify metrics were collected
        assert len(pool_manager.pool_metrics) >= 3
        
        # Verify pool status tracking
        for step, metrics in pool_manager.pool_metrics.items():
            assert "size" in metrics
            assert "checked_out" in metrics
            assert "checked_in" in metrics
            assert isinstance(metrics["checked_out"], int)
        
        # Cleanup
        for session in sessions:
            await session.close()
    
    async def test_pool_configuration_limits(self, pool_manager):
        """Test that pool respects configured limits."""
        initial_status = pool_manager.test_engine.pool.status()
        
        # Verify pool configuration
        assert pool_manager.test_engine.pool.size() == 5  # Configured pool size
        
        # Test overflow behavior
        sessions = []
        try:
            for i in range(8):  # More than pool_size + max_overflow
                session = pool_manager.session_factory()
                await session.execute("SELECT 1")
                sessions.append(session)
                
                current_status = pool_manager.test_engine.pool.status()
                # Should not exceed configured limits significantly
                total_connections = current_status.checked_out + current_status.overflow
                assert total_connections <= 10  # Some tolerance for timing
                
        finally:
            for session in sessions:
                try:
                    await session.close()
                except:
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])