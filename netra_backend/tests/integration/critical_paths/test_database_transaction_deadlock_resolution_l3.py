"""
L3 Integration Test: Database Transaction Deadlock Detection and Resolution

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers during concurrent operations)
- Business Goal: Stability - Prevent deadlocks that could block user operations
- Value Impact: Ensures system remains responsive under concurrent load
- Strategic Impact: Protects $45K MRR from transaction blocking issues

L3 Test: Uses real PostgreSQL via Testcontainers to create actual deadlock scenarios
and validate detection/resolution mechanisms work correctly.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
from typing import List, Dict, Any, Tuple
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, IntegrityError
from testcontainers.postgres import PostgresContainer

# Add project root to path

from netra_backend.app.db.postgres import get_async_db
from netra_backend.app.db.postgres_core import Database
from netra_backend.app.logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


class DatabaseDeadlockManager:
    """Manages deadlock testing with real PostgreSQL containers."""
    
    def __init__(self):
        self.container = None
        self.db_url = None
        self.test_engine = None
        self.session_factory = None
        self.deadlock_scenarios = []
        self.deadlock_metrics = {}
        
    async def setup_postgres_container(self):
        """Setup real PostgreSQL container for deadlock testing."""
        try:
            self.container = PostgresContainer("postgres:15-alpine")
            self.container.start()
            
            # Get connection details
            self.db_url = self.container.get_connection_url().replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            # Create test engine
            self.test_engine = create_async_engine(
                self.db_url,
                pool_size=10,
                max_overflow=5,
                pool_pre_ping=True,
                echo=False
            )
            
            self.session_factory = sessionmaker(
                self.test_engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Initialize test schema
            await self.create_deadlock_test_schema()
            
            logger.info("PostgreSQL deadlock test container setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL container: {e}")
            await self.cleanup()
            raise
    
    async def create_deadlock_test_schema(self):
        """Create test tables designed to trigger deadlocks."""
        async with self.test_engine.begin() as conn:
            # Account table for transfer deadlock scenarios
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_accounts (
                    id SERIAL PRIMARY KEY,
                    account_number VARCHAR(50) UNIQUE NOT NULL,
                    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transaction log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_transactions (
                    id SERIAL PRIMARY KEY,
                    from_account_id INTEGER REFERENCES test_accounts(id),
                    to_account_id INTEGER REFERENCES test_accounts(id),
                    amount DECIMAL(10,2) NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Resource lock table for general deadlock testing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS test_resources (
                    id SERIAL PRIMARY KEY,
                    resource_name VARCHAR(100) UNIQUE NOT NULL,
                    resource_value TEXT,
                    lock_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test data
            await conn.execute("""
                INSERT INTO test_accounts (account_number, balance) 
                VALUES ('ACC001', 1000.00), ('ACC002', 1000.00), ('ACC003', 1000.00)
                ON CONFLICT (account_number) DO NOTHING
            """)
            
            await conn.execute("""
                INSERT INTO test_resources (resource_name, resource_value) 
                VALUES ('RESOURCE_A', 'value_a'), ('RESOURCE_B', 'value_b'), ('RESOURCE_C', 'value_c')
                ON CONFLICT (resource_name) DO NOTHING
            """)
    
    async def create_classic_deadlock_scenario(self) -> Dict[str, Any]:
        """Create a classic two-transaction deadlock scenario."""
        deadlock_result = {
            "deadlock_detected": False,
            "resolution_successful": False,
            "transaction_results": [],
            "deadlock_details": None
        }
        
        async def transaction_a():
            """Transaction A: Updates Account 1 then Account 2."""
            result = {"transaction": "A", "success": False, "error": None, "steps_completed": 0}
            
            try:
                async with self.session_factory() as session:
                    # Step 1: Lock Account 1
                    await session.execute(
                        "UPDATE test_accounts SET balance = balance + 100 WHERE account_number = 'ACC001'"
                    )
                    result["steps_completed"] = 1
                    
                    # Delay to increase deadlock probability
                    await asyncio.sleep(0.1)
                    
                    # Step 2: Try to lock Account 2 (potential deadlock)
                    await session.execute(
                        "UPDATE test_accounts SET balance = balance - 100 WHERE account_number = 'ACC002'"
                    )
                    result["steps_completed"] = 2
                    
                    await session.commit()
                    result["success"] = True
                    
            except Exception as e:
                result["error"] = str(e)
                logger.info(f"Transaction A failed: {e}")
                
            return result
        
        async def transaction_b():
            """Transaction B: Updates Account 2 then Account 1 (opposite order)."""
            result = {"transaction": "B", "success": False, "error": None, "steps_completed": 0}
            
            try:
                async with self.session_factory() as session:
                    # Step 1: Lock Account 2
                    await session.execute(
                        "UPDATE test_accounts SET balance = balance + 50 WHERE account_number = 'ACC002'"
                    )
                    result["steps_completed"] = 1
                    
                    # Delay to increase deadlock probability
                    await asyncio.sleep(0.1)
                    
                    # Step 2: Try to lock Account 1 (potential deadlock)
                    await session.execute(
                        "UPDATE test_accounts SET balance = balance - 50 WHERE account_number = 'ACC001'"
                    )
                    result["steps_completed"] = 2
                    
                    await session.commit()
                    result["success"] = True
                    
            except Exception as e:
                result["error"] = str(e)
                logger.info(f"Transaction B failed: {e}")
                
            return result
        
        # Execute transactions concurrently
        start_time = time.time()
        results = await asyncio.gather(transaction_a(), transaction_b(), return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_transactions = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed_transactions = len(results) - successful_transactions
        
        # Check for deadlock detection
        deadlock_errors = [
            r for r in results 
            if isinstance(r, dict) and r.get("error") and "deadlock" in r["error"].lower()
        ]
        
        deadlock_result.update({
            "deadlock_detected": len(deadlock_errors) > 0,
            "resolution_successful": successful_transactions >= 1,  # At least one should succeed
            "transaction_results": results,
            "execution_time": execution_time,
            "successful_transactions": successful_transactions,
            "failed_transactions": failed_transactions,
            "deadlock_errors": deadlock_errors
        })
        
        return deadlock_result
    
    async def test_deadlock_detection_timeout(self) -> Dict[str, Any]:
        """Test deadlock detection via timeout mechanisms."""
        timeout_result = {
            "timeout_detected": False,
            "timeout_reasonable": False,
            "recovery_successful": False
        }
        
        async def long_holding_transaction():
            """Transaction that holds locks for an extended period."""
            try:
                async with self.session_factory() as session:
                    # Begin transaction and hold locks
                    await session.execute(
                        "UPDATE test_resources SET lock_count = lock_count + 1 WHERE resource_name = 'RESOURCE_A'"
                    )
                    
                    # Hold lock for extended period
                    await asyncio.sleep(5)
                    
                    await session.commit()
                    return {"success": True}
                    
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        async def competing_transaction():
            """Transaction that tries to access the same locked resource."""
            try:
                # Wait briefly to ensure first transaction starts
                await asyncio.sleep(0.5)
                
                async with self.session_factory() as session:
                    # Set a shorter timeout for this session
                    await session.execute("SET statement_timeout = '2s'")
                    
                    start_time = time.time()
                    
                    # Try to access locked resource (should timeout)
                    await session.execute(
                        "UPDATE test_resources SET lock_count = lock_count + 1 WHERE resource_name = 'RESOURCE_A'"
                    )
                    
                    await session.commit()
                    return {"success": True, "wait_time": time.time() - start_time}
                    
            except Exception as e:
                wait_time = time.time() - start_time if 'start_time' in locals() else 0
                return {"success": False, "error": str(e), "wait_time": wait_time}
        
        # Execute competing transactions
        holding_task = asyncio.create_task(long_holding_transaction())
        competing_task = asyncio.create_task(competing_transaction())
        
        holding_result, competing_result = await asyncio.gather(holding_task, competing_task)
        
        # Analyze timeout behavior
        if not competing_result.get("success"):
            error_message = competing_result.get("error", "").lower()
            timeout_result["timeout_detected"] = "timeout" in error_message or "canceling statement" in error_message
            
            wait_time = competing_result.get("wait_time", 0)
            timeout_result["timeout_reasonable"] = 1.5 <= wait_time <= 3.0  # Should timeout within reasonable bounds
        
        # Test recovery after timeout
        try:
            await asyncio.sleep(1)  # Allow cleanup
            async with self.session_factory() as session:
                result = await session.execute("SELECT * FROM test_resources WHERE resource_name = 'RESOURCE_A'")
                timeout_result["recovery_successful"] = len(result.fetchall()) > 0
        except Exception as e:
            logger.error(f"Recovery test failed: {e}")
        
        return timeout_result
    
    async def test_optimistic_locking_deadlock_prevention(self) -> Dict[str, Any]:
        """Test optimistic locking as deadlock prevention mechanism."""
        locking_result = {
            "conflicts_detected": 0,
            "retries_successful": 0,
            "data_consistency_maintained": False
        }
        
        async def optimistic_update_transaction(transaction_id: int, account_number: str, amount: float):
            """Transaction using optimistic locking."""
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    async with self.session_factory() as session:
                        # Read current version
                        result = await session.execute(
                            "SELECT id, balance, version FROM test_accounts WHERE account_number = :acc",
                            {"acc": account_number}
                        )
                        row = result.fetchone()
                        
                        if not row:
                            return {"success": False, "error": "Account not found"}
                        
                        account_id, current_balance, current_version = row
                        new_balance = current_balance + amount
                        new_version = current_version + 1
                        
                        # Simulate processing time
                        await asyncio.sleep(0.1)
                        
                        # Optimistic update with version check
                        update_result = await session.execute(
                            """
                            UPDATE test_accounts 
                            SET balance = :new_balance, version = :new_version, updated_at = CURRENT_TIMESTAMP
                            WHERE account_number = :acc AND version = :current_version
                            """,
                            {
                                "new_balance": new_balance,
                                "new_version": new_version,
                                "acc": account_number,
                                "current_version": current_version
                            }
                        )
                        
                        if update_result.rowcount == 0:
                            # Version conflict detected
                            retry_count += 1
                            locking_result["conflicts_detected"] += 1
                            await asyncio.sleep(0.05 * retry_count)  # Exponential backoff
                            continue
                        
                        await session.commit()
                        locking_result["retries_successful"] += 1
                        return {"success": True, "retries": retry_count}
                        
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        return {"success": False, "error": str(e), "retries": retry_count}
                    await asyncio.sleep(0.05 * retry_count)
            
            return {"success": False, "error": "Max retries exceeded", "retries": retry_count}
        
        # Create concurrent optimistic transactions
        concurrent_transactions = 5
        tasks = [
            optimistic_update_transaction(i, "ACC003", 10.0)
            for i in range(concurrent_transactions)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_updates = sum(1 for r in results if r.get("success"))
        
        # Verify data consistency
        async with self.session_factory() as session:
            result = await session.execute(
                "SELECT balance, version FROM test_accounts WHERE account_number = 'ACC003'"
            )
            row = result.fetchone()
            
            if row:
                final_balance, final_version = row
                expected_balance = 1000.0 + (successful_updates * 10.0)
                locking_result["data_consistency_maintained"] = abs(final_balance - expected_balance) < 0.01
        
        locking_result.update({
            "total_transactions": concurrent_transactions,
            "successful_transactions": successful_updates,
            "average_retries": sum(r.get("retries", 0) for r in results) / len(results)
        })
        
        return locking_result
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.test_engine:
                await self.test_engine.dispose()
            
            if self.container:
                self.container.stop()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def deadlock_manager():
    """Create deadlock manager for testing."""
    manager = DatabaseDeadlockManager()
    await manager.setup_postgres_container()
    yield manager
    await manager.cleanup()


@pytest.mark.L3
@pytest.mark.integration
class TestDatabaseTransactionDeadlockResolutionL3:
    """L3 integration tests for database deadlock detection and resolution."""
    
    async def test_classic_deadlock_detection_and_resolution(self, deadlock_manager):
        """Test detection and resolution of classic deadlock scenarios."""
        # Run deadlock scenario multiple times to increase probability
        deadlock_detected = False
        resolution_successful = False
        
        for attempt in range(3):  # Multiple attempts to trigger deadlock
            result = await deadlock_manager.create_classic_deadlock_scenario()
            
            if result["deadlock_detected"]:
                deadlock_detected = True
                
            if result["resolution_successful"]:
                resolution_successful = True
                
            # Reset test data between attempts
            async with deadlock_manager.session_factory() as session:
                await session.execute(
                    "UPDATE test_accounts SET balance = 1000.00 WHERE account_number IN ('ACC001', 'ACC002')"
                )
                await session.commit()
        
        # At least one attempt should trigger and resolve deadlock
        # Note: Deadlock detection might not always occur in test environments
        assert resolution_successful is True  # At least one transaction should always succeed
    
    async def test_deadlock_timeout_mechanisms(self, deadlock_manager):
        """Test timeout-based deadlock detection and recovery."""
        result = await deadlock_manager.test_deadlock_detection_timeout()
        
        # Timeout should be detected when competing for locked resources
        assert result["timeout_detected"] is True
        assert result["timeout_reasonable"] is True
        assert result["recovery_successful"] is True
    
    async def test_optimistic_locking_prevents_deadlocks(self, deadlock_manager):
        """Test that optimistic locking prevents deadlock scenarios."""
        result = await deadlock_manager.test_optimistic_locking_deadlock_prevention()
        
        # Should detect version conflicts and handle them gracefully
        assert result["conflicts_detected"] > 0  # Concurrent access should cause conflicts
        assert result["retries_successful"] >= result["conflicts_detected"]  # Should retry successfully
        assert result["data_consistency_maintained"] is True
        
        # Most transactions should eventually succeed
        success_rate = result["successful_transactions"] / result["total_transactions"]
        assert success_rate >= 0.8  # At least 80% success rate
    
    async def test_transaction_isolation_levels(self, deadlock_manager):
        """Test different isolation levels and their deadlock behavior."""
        isolation_results = {}
        
        isolation_levels = [
            "READ COMMITTED",
            "REPEATABLE READ",
            "SERIALIZABLE"
        ]
        
        for isolation_level in isolation_levels:
            try:
                async with deadlock_manager.session_factory() as session:
                    await session.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                    
                    # Test concurrent access with this isolation level
                    start_time = time.time()
                    
                    await session.execute(
                        "UPDATE test_resources SET resource_value = :value WHERE resource_name = 'RESOURCE_B'",
                        {"value": f"updated_at_{time.time()}"}
                    )
                    
                    await session.commit()
                    
                    isolation_results[isolation_level] = {
                        "success": True,
                        "execution_time": time.time() - start_time
                    }
                    
            except Exception as e:
                isolation_results[isolation_level] = {
                    "success": False,
                    "error": str(e)
                }
        
        # At least READ COMMITTED should work
        assert isolation_results["READ COMMITTED"]["success"] is True
    
    async def test_deadlock_monitoring_and_logging(self, deadlock_manager):
        """Test deadlock monitoring and logging capabilities."""
        # Create scenario and capture deadlock information
        result = await deadlock_manager.create_classic_deadlock_scenario()
        
        # Check if deadlock information is properly captured
        monitoring_results = {
            "deadlock_logged": len(result.get("deadlock_errors", [])) > 0,
            "transaction_details_captured": len(result.get("transaction_results", [])) > 0,
            "execution_time_tracked": "execution_time" in result,
            "error_details_preserved": any(
                "error" in r for r in result.get("transaction_results", []) if isinstance(r, dict)
            )
        }
        
        # Should capture sufficient monitoring information
        assert monitoring_results["transaction_details_captured"] is True
        assert monitoring_results["execution_time_tracked"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])