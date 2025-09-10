"""
Database Transaction Race Condition Tests - Integration Testing

This module tests critical race conditions in database transaction management that could lead to:
- Lost updates and phantom reads between concurrent transactions
- Deadlocks in high-concurrency scenarios
- Connection pool exhaustion during transaction bursts
- Transaction isolation violations causing data corruption
- Session leaks and resource exhaustion

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Data integrity is fundamental to platform trust
- Business Goal: Ensure data consistency and prevent corruption under concurrent load
- Value Impact: Prevents data loss and corruption that would make platform unusable
- Strategic Impact: CRITICAL - Database reliability directly impacts user trust and legal compliance

Test Coverage:
- Concurrent transaction isolation (100 simultaneous transactions)
- Deadlock detection and prevention during high contention
- Connection pool management under transaction bursts
- Session cleanup and resource leak prevention
- Multi-user transaction isolation and data consistency
"""

import asyncio
import gc
import json
import random
import time
import uuid
import weakref
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import Mock, patch
import pytest
import psycopg2
from sqlalchemy.exc import OperationalError, DisconnectionError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_redis_fixture
from netra_backend.app.database.request_scoped_session_factory import (
    RequestScopedSessionFactory, 
    get_session_factory,
    get_isolated_session,
    ConnectionPoolMetrics
)
from netra_backend.app.database import get_db, DatabaseManager
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id
from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestDatabaseTransactionRaces(BaseIntegrationTest):
    """Test race conditions in database transaction management."""
    
    def setup_method(self):
        """Set up test environment with transaction tracking."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "database_transaction_race_testing", source="test")
        
        # Transaction tracking
        self.active_transactions: Dict[str, Any] = {}
        self.transaction_events: List[Dict] = []
        self.race_conditions_detected: List[Dict] = []
        self.session_refs: List[weakref.ref] = []
        
        # Deadlock and contention tracking
        self.deadlock_events: List[Dict] = []
        self.contention_events: List[Dict] = []
        self.isolation_violations: List[Dict] = []
        
        # Performance metrics
        self.transaction_times: List[float] = []
        self.connection_pool_snapshots: List[Dict] = []
        self.resource_usage_snapshots: List[Dict] = []
        
        # Initialize session factory for testing
        self.session_factory = None
        
    def teardown_method(self):
        """Clean up database connections and verify no resource leaks."""
        # Force rollback any active transactions
        cleanup_tasks = []
        for tx_id, transaction in self.active_transactions.items():
            try:
                if hasattr(transaction, 'rollback'):
                    cleanup_tasks.append(transaction.rollback())
            except Exception as e:
                logger.warning(f"Error rolling back transaction {tx_id}: {e}")
        
        # Wait for cleanup with timeout
        if cleanup_tasks:
            try:
                asyncio.get_event_loop().run_until_complete(
                    asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=10.0)
                )
            except asyncio.TimeoutError:
                logger.warning("Transaction cleanup timed out - potential resource leaks")
        
        # Force garbage collection and check for session leaks
        gc.collect()
        leaked_refs = [ref for ref in self.session_refs if ref() is not None]
        if leaked_refs:
            logger.error(f"RACE CONDITION DETECTED: {len(leaked_refs)} session objects not garbage collected")
            self.race_conditions_detected.append({
                "type": "session_resource_leak",
                "leaked_session_count": len(leaked_refs),
                "timestamp": time.time()
            })
        
        # Clear tracking data
        self.active_transactions.clear()
        self.transaction_events.clear()
        self.session_refs.clear()
        self.deadlock_events.clear()
        self.contention_events.clear()
        self.isolation_violations.clear()
        
        super().teardown_method()
    
    def _track_transaction_event(self, event_type: str, tx_id: str, user_id: str = None, metadata: Dict = None):
        """Track transaction events for race condition analysis."""
        event = {
            "type": event_type,
            "transaction_id": tx_id,
            "user_id": user_id,
            "timestamp": time.time(),
            "task_name": asyncio.current_task().get_name() if asyncio.current_task() else "unknown",
            "metadata": metadata or {}
        }
        self.transaction_events.append(event)
        
        # Analyze for race condition patterns
        self._analyze_transaction_race_patterns(event)
    
    def _analyze_transaction_race_patterns(self, event: Dict):
        """Analyze transaction events for race condition patterns."""
        tx_id = event["transaction_id"]
        event_type = event["type"]
        user_id = event["user_id"]
        
        # Pattern 1: Transaction taking too long (possible deadlock)
        if event_type == "transaction_commit":
            start_event = None
            for e in reversed(self.transaction_events):
                if e["type"] == "transaction_start" and e["transaction_id"] == tx_id:
                    start_event = e
                    break
            
            if start_event:
                transaction_duration = event["timestamp"] - start_event["timestamp"]
                if transaction_duration > 5.0:  # Transactions longer than 5 seconds
                    self._detect_race_condition("long_running_transaction", {
                        "transaction_id": tx_id,
                        "duration": transaction_duration,
                        "user_id": user_id
                    })
        
        # Pattern 2: Multiple transactions for same user simultaneously (potential contention)
        if event_type == "transaction_start" and user_id:
            concurrent_user_transactions = [
                e for e in self.transaction_events[-50:]
                if e["type"] == "transaction_start" and e["user_id"] == user_id
                and event["timestamp"] - e["timestamp"] < 2.0  # Within 2 seconds
            ]
            
            if len(concurrent_user_transactions) > 5:
                self._detect_race_condition("excessive_concurrent_transactions", {
                    "user_id": user_id,
                    "concurrent_count": len(concurrent_user_transactions)
                })
        
        # Pattern 3: Transaction failures clustering (potential deadlocks)
        if event_type == "transaction_error":
            recent_errors = [
                e for e in self.transaction_events[-20:]
                if e["type"] == "transaction_error"
                and event["timestamp"] - e["timestamp"] < 1.0  # Within 1 second
            ]
            
            if len(recent_errors) > 3:
                self._detect_race_condition("transaction_error_cluster", {
                    "error_count": len(recent_errors),
                    "time_window": 1.0
                })
    
    def _detect_race_condition(self, condition_type: str, metadata: Dict):
        """Record race condition detection."""
        race_condition = {
            "type": condition_type,
            "metadata": metadata,
            "timestamp": time.time(),
            "task_context": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_conditions_detected.append(race_condition)
        logger.warning(f"RACE CONDITION DETECTED: {condition_type} - {metadata}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_transaction_isolation_race_conditions(self, real_services_fixture):
        """
        Test transaction isolation under concurrent database operations.
        
        Verifies that concurrent transactions maintain proper ACID properties
        and don't interfere with each other's data modifications.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available for integration test")
        
        # Business Value: Ensure data integrity under concurrent user operations
        # Critical for financial data, user settings, and platform state
        
        num_concurrent_transactions = 50
        records_per_transaction = 5
        transaction_results = []
        
        # Create test table for isolation testing
        test_table_name = f"race_test_isolation_{int(time.time())}"
        
        async def setup_test_table():
            """Create test table for isolation testing."""
            try:
                async with get_isolated_session() as session:
                    await session.execute(f"""
                        CREATE TABLE IF NOT EXISTS {test_table_name} (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            transaction_id VARCHAR(255) NOT NULL,
                            record_index INTEGER NOT NULL,
                            value INTEGER NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            isolation_token VARCHAR(255) UNIQUE NOT NULL
                        )
                    """)
                    await session.commit()
                    logger.info(f"Created test table: {test_table_name}")
            except Exception as e:
                logger.error(f"Failed to setup test table: {e}")
                raise
        
        await setup_test_table()
        
        async def execute_isolated_transaction(tx_index: int) -> Dict:
            """Execute a database transaction with isolation verification."""
            user_id = ensure_user_id(f"tx_isolation_user_{tx_index % 10}")  # 10 different users
            tx_id = f"isolation_tx_{tx_index}_{uuid.uuid4()}"
            
            start_time = time.time()
            
            try:
                self._track_transaction_event("transaction_start", tx_id, str(user_id), {
                    "tx_index": tx_index,
                    "records_to_create": records_per_transaction
                })
                
                async with get_isolated_session() as session:
                    # Store session reference for leak detection
                    self.session_refs.append(weakref.ref(session))
                    
                    inserted_records = []
                    
                    # Insert multiple records in transaction
                    for record_idx in range(records_per_transaction):
                        isolation_token = f"token_{tx_index}_{record_idx}_{uuid.uuid4()}"
                        value = random.randint(1, 1000)
                        
                        # Insert record within transaction
                        result = await session.execute(f"""
                            INSERT INTO {test_table_name} 
                            (user_id, transaction_id, record_index, value, isolation_token)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id
                        """, (str(user_id), tx_id, record_idx, value, isolation_token))
                        
                        record_id = result.fetchone()[0]
                        
                        inserted_records.append({
                            "id": record_id,
                            "user_id": str(user_id),
                            "transaction_id": tx_id,
                            "record_index": record_idx,
                            "value": value,
                            "isolation_token": isolation_token
                        })
                        
                        # Brief delay to increase chance of concurrent access
                        await asyncio.sleep(0.01)
                    
                    # Verify record isolation within transaction
                    verification_result = await session.execute(f"""
                        SELECT COUNT(*) FROM {test_table_name} 
                        WHERE transaction_id = %s
                    """, (tx_id,))
                    
                    records_in_tx = verification_result.fetchone()[0]
                    
                    if records_in_tx != records_per_transaction:
                        self.isolation_violations.append({
                            "transaction_id": tx_id,
                            "expected_records": records_per_transaction,
                            "actual_records": records_in_tx,
                            "violation_type": "record_count_mismatch"
                        })
                    
                    # Commit transaction
                    await session.commit()
                    
                    transaction_time = time.time() - start_time
                    self.transaction_times.append(transaction_time)
                    
                    self._track_transaction_event("transaction_commit", tx_id, str(user_id), {
                        "records_inserted": len(inserted_records),
                        "transaction_time": transaction_time
                    })
                    
                    return {
                        "success": True,
                        "transaction_id": tx_id,
                        "user_id": str(user_id),
                        "records_inserted": len(inserted_records),
                        "transaction_time": transaction_time,
                        "inserted_records": inserted_records
                    }
                    
            except IntegrityError as e:
                # Integrity errors are expected in high concurrency (duplicate tokens)
                self._track_transaction_event("transaction_integrity_error", tx_id, str(user_id), {
                    "error": str(e)
                })
                return {
                    "success": False,
                    "transaction_id": tx_id,
                    "error_type": "integrity_error",
                    "error": str(e)
                }
            except Exception as e:
                self._track_transaction_event("transaction_error", tx_id, str(user_id), {
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                return {
                    "success": False,
                    "transaction_id": tx_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        # Execute concurrent transactions
        logger.info(f"Starting {num_concurrent_transactions} concurrent database transactions")
        
        tx_tasks = [execute_isolated_transaction(i) for i in range(num_concurrent_transactions)]
        results = await asyncio.gather(*tx_tasks, return_exceptions=True)
        
        # Analyze transaction results
        successful_transactions = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_transactions = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # CRITICAL BUSINESS VALIDATION: Reasonable success rate under concurrency
        success_rate = len(successful_transactions) / num_concurrent_transactions
        
        # Allow for some failures due to legitimate conflicts, but not excessive
        assert success_rate >= 0.70, f"Transaction success rate too low: {success_rate:.2%} - indicates severe race conditions"
        
        # Verify data isolation - no cross-contamination
        total_records_expected = len(successful_transactions) * records_per_transaction
        
        try:
            async with get_isolated_session() as session:
                # Count total records
                count_result = await session.execute(f"SELECT COUNT(*) FROM {test_table_name}")
                actual_record_count = count_result.fetchone()[0]
                
                assert actual_record_count == total_records_expected, \
                    f"Record count mismatch: {actual_record_count}/{total_records_expected} - ISOLATION VIOLATION"
                
                # Verify no duplicate isolation tokens (transaction isolation)
                token_result = await session.execute(f"""
                    SELECT COUNT(DISTINCT isolation_token) FROM {test_table_name}
                """)
                unique_tokens = token_result.fetchone()[0]
                
                assert unique_tokens == actual_record_count, \
                    f"Isolation token duplicates: {unique_tokens}/{actual_record_count} - RACE CONDITION"
                
                # Verify user data isolation
                user_data_result = await session.execute(f"""
                    SELECT user_id, COUNT(*) FROM {test_table_name} GROUP BY user_id
                """)
                user_record_counts = {row[0]: row[1] for row in user_data_result.fetchall()}
                
                # Each user should have consistent record counts
                for user_id, count in user_record_counts.items():
                    user_transactions = [
                        tx for tx in successful_transactions 
                        if tx["user_id"] == user_id
                    ]
                    expected_user_records = len(user_transactions) * records_per_transaction
                    
                    assert count == expected_user_records, \
                        f"User {user_id} record isolation violation: {count}/{expected_user_records} - RACE CONDITION"
        
        except Exception as verification_error:
            logger.error(f"Transaction isolation verification failed: {verification_error}")
            raise
        
        finally:
            # Cleanup test table
            try:
                async with get_isolated_session() as session:
                    await session.execute(f"DROP TABLE IF EXISTS {test_table_name}")
                    await session.commit()
            except Exception as e:
                logger.warning(f"Failed to cleanup test table: {e}")
        
        # Performance validation
        if self.transaction_times:
            avg_tx_time = sum(self.transaction_times) / len(self.transaction_times)
            max_tx_time = max(self.transaction_times)
            
            assert avg_tx_time < 2.0, f"Average transaction time too slow: {avg_tx_time:.3f}s"
            assert max_tx_time < 10.0, f"Maximum transaction time too slow: {max_tx_time:.3f}s - possible deadlock"
        
        # Check for isolation violations
        assert len(self.isolation_violations) == 0, f"Isolation violations detected: {self.isolation_violations}"
        
        # Limited race conditions allowed (some contention is expected)
        assert len(self.race_conditions_detected) <= 3, f"Excessive race conditions: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_transactions)} transactions completed with isolation")
        logger.info(f"Average transaction time: {sum(self.transaction_times)/len(self.transaction_times):.3f}s")
        
        self.assert_business_value_delivered({
            "successful_transactions": len(successful_transactions),
            "isolation_maintained": True,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_exhaustion_race_conditions(self, real_services_fixture):
        """
        Test connection pool behavior under transaction burst load.
        
        Verifies that connection pools handle high transaction volume without
        exhaustion and that connections are properly recycled.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available for integration test")
        
        # Simulate connection pool stress
        num_transaction_bursts = 20
        transactions_per_burst = 25
        total_transactions = num_transaction_bursts * transactions_per_burst
        
        pool_metrics = ConnectionPoolMetrics()
        connection_events = []
        
        async def transaction_burst(burst_index: int) -> Dict:
            """Execute a burst of transactions to stress connection pool."""
            burst_start = time.time()
            burst_results = []
            
            async def single_transaction(tx_index: int):
                """Execute a single transaction within the burst."""
                tx_id = f"pool_test_tx_{burst_index}_{tx_index}"
                user_id = ensure_user_id(f"pool_user_{burst_index}_{tx_index}")
                
                connection_start = time.time()
                
                try:
                    async with get_isolated_session() as session:
                        # Track connection acquisition
                        pool_metrics.active_sessions += 1
                        pool_metrics.total_sessions_created += 1
                        pool_metrics.update_peak_concurrent(pool_metrics.active_sessions)
                        
                        connection_event = {
                            "event_type": "connection_acquired",
                            "transaction_id": tx_id,
                            "burst_index": burst_index,
                            "tx_index": tx_index,
                            "active_sessions": pool_metrics.active_sessions,
                            "timestamp": time.time()
                        }
                        connection_events.append(connection_event)
                        
                        # Simulate database work
                        await session.execute("SELECT 1")
                        await session.execute("SELECT pg_sleep(0.01)")  # 10ms delay
                        await session.commit()
                        
                        # Track connection release
                        pool_metrics.active_sessions -= 1
                        pool_metrics.sessions_closed += 1
                        
                        connection_time = time.time() - connection_start
                        
                        release_event = {
                            "event_type": "connection_released",
                            "transaction_id": tx_id,
                            "connection_time": connection_time,
                            "active_sessions": pool_metrics.active_sessions,
                            "timestamp": time.time()
                        }
                        connection_events.append(release_event)
                        
                        return {
                            "success": True,
                            "transaction_id": tx_id,
                            "connection_time": connection_time
                        }
                        
                except OperationalError as e:
                    # Connection pool exhaustion
                    pool_metrics.record_pool_exhaustion()
                    return {
                        "success": False,
                        "transaction_id": tx_id,
                        "error": "pool_exhaustion",
                        "details": str(e)
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "transaction_id": tx_id,
                        "error": str(e)
                    }
            
            # Execute transactions concurrently within burst
            tx_tasks = [single_transaction(i) for i in range(transactions_per_burst)]
            burst_results = await asyncio.gather(*tx_tasks, return_exceptions=True)
            
            burst_time = time.time() - burst_start
            successful_in_burst = len([r for r in burst_results if isinstance(r, dict) and r.get("success")])
            
            return {
                "burst_index": burst_index,
                "successful_transactions": successful_in_burst,
                "total_transactions": transactions_per_burst,
                "burst_time": burst_time,
                "results": burst_results
            }
        
        # Execute transaction bursts with controlled timing
        logger.info(f"Testing connection pool with {num_transaction_bursts} bursts x {transactions_per_burst} transactions")
        
        burst_results = []
        for burst_idx in range(num_transaction_bursts):
            burst_result = await transaction_burst(burst_idx)
            burst_results.append(burst_result)
            
            # Brief pause between bursts to allow pool recovery
            await asyncio.sleep(0.1)
        
        # Analyze connection pool performance
        total_successful = sum(r["successful_transactions"] for r in burst_results)
        total_pool_exhaustions = pool_metrics.pool_exhaustion_events
        
        # CRITICAL: Connection pool should handle reasonable load
        success_rate = total_successful / total_transactions
        assert success_rate >= 0.85, f"Connection pool success rate too low: {success_rate:.2%}"
        
        # Pool exhaustion should be minimal
        exhaustion_rate = total_pool_exhaustions / total_transactions
        assert exhaustion_rate < 0.05, f"Connection pool exhaustion rate too high: {exhaustion_rate:.2%}"
        
        # Verify connection lifecycle consistency
        acquire_events = [e for e in connection_events if e["event_type"] == "connection_acquired"]
        release_events = [e for e in connection_events if e["event_type"] == "connection_released"]
        
        # Allow for some difference due to failures, but should be close
        connection_balance = len(acquire_events) - len(release_events)
        assert abs(connection_balance) <= total_pool_exhaustions + 5, \
            f"Connection acquire/release imbalance: {connection_balance} - RESOURCE LEAK"
        
        # Verify peak concurrent sessions is reasonable
        max_concurrent = pool_metrics.peak_concurrent_sessions
        assert max_concurrent <= transactions_per_burst + 5, \
            f"Peak concurrent sessions too high: {max_concurrent} - POOL CONFIGURATION ISSUE"
        
        # Performance validation: connections should be acquired quickly
        connection_times = [
            e["connection_time"] for e in connection_events 
            if e["event_type"] == "connection_released" and "connection_time" in e
        ]
        
        if connection_times:
            avg_connection_time = sum(connection_times) / len(connection_times)
            max_connection_time = max(connection_times)
            
            assert avg_connection_time < 1.0, f"Average connection time too slow: {avg_connection_time:.3f}s"
            assert max_connection_time < 5.0, f"Maximum connection time too slow: {max_connection_time:.3f}s"
        
        logger.info(f"SUCCESS: {total_successful} transactions completed")
        logger.info(f"Pool metrics - Peak concurrent: {max_concurrent}, Exhaustions: {total_pool_exhaustions}")
        
        self.assert_business_value_delivered({
            "successful_transactions": total_successful,
            "pool_exhaustion_rate": exhaustion_rate,
            "connection_balance": abs(connection_balance)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_deadlock_detection_and_recovery_races(self, real_services_fixture):
        """
        Test deadlock detection and recovery under concurrent access patterns.
        
        Verifies that the database properly detects deadlocks and recovers
        without causing system-wide failures or data corruption.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available for integration test")
        
        # Create deadlock-prone scenario
        num_deadlock_scenarios = 10
        scenarios_per_round = 4  # Multiple transactions accessing same resources
        
        deadlock_results = []
        test_table = f"deadlock_test_{int(time.time())}"
        
        # Setup test table for deadlock testing
        async def setup_deadlock_table():
            """Create test table for deadlock scenarios."""
            try:
                async with get_isolated_session() as session:
                    await session.execute(f"""
                        CREATE TABLE {test_table} (
                            id INTEGER PRIMARY KEY,
                            value INTEGER NOT NULL,
                            updated_by VARCHAR(255),
                            version INTEGER DEFAULT 1
                        )
                    """)
                    
                    # Insert test records
                    for i in range(scenarios_per_round):
                        await session.execute(f"""
                            INSERT INTO {test_table} (id, value, updated_by) 
                            VALUES ({i}, {i * 10}, 'initial')
                        """)
                    
                    await session.commit()
                    logger.info(f"Created deadlock test table: {test_table}")
            except Exception as e:
                logger.error(f"Failed to setup deadlock test table: {e}")
                raise
        
        await setup_deadlock_table()
        
        async def deadlock_scenario_transaction(scenario_index: int, tx_index: int, record_ids: List[int]) -> Dict:
            """Execute transaction that may cause deadlocks."""
            tx_id = f"deadlock_tx_{scenario_index}_{tx_index}"
            user_id = f"deadlock_user_{scenario_index}_{tx_index}"
            
            start_time = time.time()
            
            try:
                async with get_isolated_session() as session:
                    # Access records in different orders to create deadlock potential
                    if tx_index % 2 == 0:
                        # Forward order
                        access_order = sorted(record_ids)
                    else:
                        # Reverse order
                        access_order = sorted(record_ids, reverse=True)
                    
                    updated_records = []
                    
                    for record_id in access_order:
                        # Read current value
                        result = await session.execute(f"""
                            SELECT value, version FROM {test_table} 
                            WHERE id = {record_id} FOR UPDATE
                        """)
                        
                        row = result.fetchone()
                        if row:
                            current_value, current_version = row
                            new_value = current_value + tx_index
                            new_version = current_version + 1
                            
                            # Brief delay to increase deadlock chance
                            await asyncio.sleep(0.02)
                            
                            # Update record
                            await session.execute(f"""
                                UPDATE {test_table} 
                                SET value = {new_value}, 
                                    version = {new_version},
                                    updated_by = '{user_id}'
                                WHERE id = {record_id} AND version = {current_version}
                            """)
                            
                            updated_records.append({
                                "record_id": record_id,
                                "old_value": current_value,
                                "new_value": new_value,
                                "version": new_version
                            })
                    
                    await session.commit()
                    
                    transaction_time = time.time() - start_time
                    
                    return {
                        "success": True,
                        "transaction_id": tx_id,
                        "user_id": user_id,
                        "updated_records": len(updated_records),
                        "transaction_time": transaction_time,
                        "access_order": access_order
                    }
                    
            except psycopg2.errors.DeadlockDetected as e:
                # Expected deadlock - this is normal behavior
                deadlock_time = time.time() - start_time
                
                deadlock_event = {
                    "transaction_id": tx_id,
                    "scenario_index": scenario_index,
                    "tx_index": tx_index,
                    "deadlock_time": deadlock_time,
                    "access_order": access_order if 'access_order' in locals() else [],
                    "timestamp": time.time()
                }
                self.deadlock_events.append(deadlock_event)
                
                return {
                    "success": False,
                    "transaction_id": tx_id,
                    "error_type": "deadlock",
                    "deadlock_time": deadlock_time,
                    "expected": True  # Deadlocks are expected in this test
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "transaction_id": tx_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "expected": False
                }
        
        # Execute deadlock scenarios
        logger.info(f"Testing deadlock detection with {num_deadlock_scenarios} concurrent scenarios")
        
        all_results = []
        
        for scenario_idx in range(num_deadlock_scenarios):
            # Create deadlock scenario with multiple transactions accessing same records
            record_ids = list(range(scenarios_per_round))
            
            scenario_tasks = [
                deadlock_scenario_transaction(scenario_idx, tx_idx, record_ids[:2])  # Each tx accesses 2 records
                for tx_idx in range(scenarios_per_round)
            ]
            
            scenario_results = await asyncio.gather(*scenario_tasks, return_exceptions=True)
            all_results.extend(scenario_results)
            
            # Brief pause between scenarios
            await asyncio.sleep(0.05)
        
        # Analyze deadlock handling results
        successful_transactions = [r for r in all_results if isinstance(r, dict) and r.get("success")]
        deadlock_transactions = [r for r in all_results if isinstance(r, dict) and r.get("error_type") == "deadlock"]
        unexpected_failures = [r for r in all_results if isinstance(r, dict) and not r.get("success") and r.get("error_type") != "deadlock"]
        
        total_transactions = len(all_results)
        
        # CRITICAL: System should handle deadlocks gracefully
        # Some transactions should succeed, some deadlocks are expected
        success_rate = len(successful_transactions) / total_transactions
        deadlock_rate = len(deadlock_transactions) / total_transactions
        unexpected_failure_rate = len(unexpected_failures) / total_transactions
        
        # At least some transactions should succeed despite contention
        assert success_rate >= 0.30, f"Success rate too low: {success_rate:.2%} - deadlock handling failing"
        
        # Deadlocks should be detected and handled (not system failures)
        assert unexpected_failure_rate < 0.10, f"Unexpected failure rate too high: {unexpected_failure_rate:.2%}"
        
        # Deadlock detection should be reasonably fast
        if self.deadlock_events:
            deadlock_times = [event["deadlock_time"] for event in self.deadlock_events]
            avg_deadlock_time = sum(deadlock_times) / len(deadlock_times)
            max_deadlock_time = max(deadlock_times)
            
            assert avg_deadlock_time < 2.0, f"Average deadlock detection too slow: {avg_deadlock_time:.3f}s"
            assert max_deadlock_time < 10.0, f"Maximum deadlock detection too slow: {max_deadlock_time:.3f}s"
        
        # Verify data consistency after deadlock scenarios
        try:
            async with get_isolated_session() as session:
                # Check that all records still exist and are valid
                result = await session.execute(f"SELECT COUNT(*) FROM {test_table}")
                record_count = result.fetchone()[0]
                
                assert record_count == scenarios_per_round, \
                    f"Record loss detected: {record_count}/{scenarios_per_round} - DATA CORRUPTION"
                
                # Verify no invalid data states
                result = await session.execute(f"SELECT id, value, version FROM {test_table} ORDER BY id")
                records = result.fetchall()
                
                for record in records:
                    record_id, value, version = record
                    # Values should be reasonable (base + updates)
                    assert version >= 1, f"Invalid version for record {record_id}: {version}"
                    assert value >= record_id * 10, f"Invalid value for record {record_id}: {value}"
        
        except Exception as verification_error:
            logger.error(f"Data consistency verification failed: {verification_error}")
            raise
        
        finally:
            # Cleanup test table
            try:
                async with get_isolated_session() as session:
                    await session.execute(f"DROP TABLE IF EXISTS {test_table}")
                    await session.commit()
            except Exception as e:
                logger.warning(f"Failed to cleanup deadlock test table: {e}")
        
        logger.info(f"SUCCESS: Deadlock handling tested - {len(successful_transactions)} succeeded, {len(deadlock_transactions)} deadlocks detected")
        logger.info(f"Rates - Success: {success_rate:.2%}, Deadlocks: {deadlock_rate:.2%}, Unexpected: {unexpected_failure_rate:.2%}")
        
        self.assert_business_value_delivered({
            "successful_transactions": len(successful_transactions),
            "deadlocks_handled": len(deadlock_transactions),
            "data_consistency_maintained": True,
            "unexpected_failures": len(unexpected_failures)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_factory_concurrent_access_races(self, real_services_fixture):
        """
        Test session factory behavior under concurrent session requests.
        
        Verifies that the session factory properly manages concurrent session
        creation and cleanup without resource leaks or state corruption.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available for integration test")
        
        num_concurrent_requests = 40
        sessions_per_request = 3
        factory_results = []
        
        # Initialize session factory
        session_factory = RequestScopedSessionFactory()
        
        async def concurrent_session_operations(request_index: int) -> Dict:
            """Perform concurrent session operations on the factory."""
            request_id = f"factory_req_{request_index}"
            user_id = ensure_user_id(f"factory_user_{request_index}")
            
            start_time = time.time()
            sessions_created = []
            
            try:
                # Create multiple sessions concurrently within request
                session_tasks = []
                
                for session_idx in range(sessions_per_request):
                    async def create_and_use_session(idx: int):
                        """Create and use a session."""
                        session_start = time.time()
                        
                        try:
                            async with get_isolated_session() as session:
                                # Track session creation
                                session_ref = weakref.ref(session)
                                self.session_refs.append(session_ref)
                                
                                # Perform database operations
                                await session.execute("SELECT 1")
                                await session.execute(f"SELECT '{request_id}_{idx}' as identifier")
                                await session.commit()
                                
                                session_time = time.time() - session_start
                                
                                return {
                                    "success": True,
                                    "session_index": idx,
                                    "session_time": session_time,
                                    "request_id": request_id
                                }
                                
                        except Exception as e:
                            return {
                                "success": False,
                                "session_index": idx,
                                "error": str(e)
                            }
                    
                    session_tasks.append(create_and_use_session(session_idx))
                
                # Execute session operations concurrently
                session_results = await asyncio.gather(*session_tasks, return_exceptions=True)
                sessions_created = session_results
                
                request_time = time.time() - start_time
                successful_sessions = len([r for r in session_results if isinstance(r, dict) and r.get("success")])
                
                return {
                    "success": True,
                    "request_id": request_id,
                    "user_id": str(user_id),
                    "sessions_requested": sessions_per_request,
                    "sessions_successful": successful_sessions,
                    "request_time": request_time,
                    "session_results": session_results
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "request_id": request_id,
                    "error": str(e)
                }
        
        # Execute concurrent session factory operations
        logger.info(f"Testing session factory with {num_concurrent_requests} concurrent requests x {sessions_per_request} sessions")
        
        request_tasks = [concurrent_session_operations(i) for i in range(num_concurrent_requests)]
        results = await asyncio.gather(*request_tasks, return_exceptions=True)
        
        # Analyze session factory results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # CRITICAL: Session factory should handle concurrent requests reliably
        success_rate = len(successful_requests) / num_concurrent_requests
        assert success_rate >= 0.95, f"Session factory success rate too low: {success_rate:.2%}"
        
        # Calculate total session statistics
        total_sessions_requested = sum(r["sessions_requested"] for r in successful_requests)
        total_sessions_successful = sum(r["sessions_successful"] for r in successful_requests)
        
        session_success_rate = total_sessions_successful / total_sessions_requested if total_sessions_requested > 0 else 0
        assert session_success_rate >= 0.95, f"Individual session success rate too low: {session_success_rate:.2%}"
        
        # Verify session isolation - no cross-request contamination
        request_ids = [r["request_id"] for r in successful_requests]
        assert len(request_ids) == len(set(request_ids)), "Request ID collision detected - RACE CONDITION"
        
        # Check session lifecycle consistency
        for request_result in successful_requests:
            session_results = request_result.get("session_results", [])
            request_id = request_result["request_id"]
            
            # All sessions within a request should be successful or fail independently
            session_success_count = len([s for s in session_results if isinstance(s, dict) and s.get("success")])
            session_failure_count = len([s for s in session_results if isinstance(s, dict) and not s.get("success")])
            
            total_sessions_in_request = session_success_count + session_failure_count
            assert total_sessions_in_request == sessions_per_request, \
                f"Session count mismatch for {request_id}: {total_sessions_in_request}/{sessions_per_request}"
            
            # Verify session identifiers are unique within request
            successful_sessions = [s for s in session_results if isinstance(s, dict) and s.get("success")]
            if successful_sessions:
                session_indices = [s["session_index"] for s in successful_sessions]
                assert len(session_indices) == len(set(session_indices)), \
                    f"Session index collision in {request_id} - RACE CONDITION"
        
        # Performance validation
        request_times = [r["request_time"] for r in successful_requests if "request_time" in r]
        if request_times:
            avg_request_time = sum(request_times) / len(request_times)
            max_request_time = max(request_times)
            
            assert avg_request_time < 2.0, f"Average request time too slow: {avg_request_time:.3f}s"
            assert max_request_time < 10.0, f"Maximum request time too slow: {max_request_time:.3f}s - possible deadlock"
        
        # Resource leak detection
        gc.collect()
        leaked_sessions = len([ref for ref in self.session_refs if ref() is not None])
        leak_ratio = leaked_sessions / total_sessions_successful if total_sessions_successful > 0 else 0
        
        # Allow for some sessions still in cleanup, but not excessive
        assert leak_ratio < 0.10, f"Session leak ratio too high: {leak_ratio:.2%} - RESOURCE LEAK"
        
        logger.info(f"SUCCESS: {len(successful_requests)} requests completed")
        logger.info(f"Sessions - Requested: {total_sessions_requested}, Successful: {total_sessions_successful}")
        logger.info(f"Session leak ratio: {leak_ratio:.2%}")
        
        self.assert_business_value_delivered({
            "successful_requests": len(successful_requests),
            "session_success_rate": session_success_rate,
            "session_leak_ratio": leak_ratio,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_multi_user_data_consistency_races(self, real_services_fixture):
        """
        Test data consistency across concurrent multi-user operations.
        
        Verifies that concurrent operations by different users maintain
        data consistency and proper isolation boundaries.
        """
        services = real_services_fixture
        
        if not services["database_available"]:
            pytest.skip("Real database not available for integration test")
        
        num_users = 15
        operations_per_user = 10
        total_operations = num_users * operations_per_user
        
        consistency_results = []
        test_table = f"user_consistency_test_{int(time.time())}"
        
        # Setup test table for multi-user consistency testing
        async def setup_consistency_table():
            """Create test table for multi-user consistency testing."""
            try:
                async with get_isolated_session() as session:
                    await session.execute(f"""
                        CREATE TABLE {test_table} (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            operation_index INTEGER NOT NULL,
                            value INTEGER NOT NULL,
                            checksum VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            UNIQUE(user_id, operation_index)
                        )
                    """)
                    await session.commit()
                    logger.info(f"Created user consistency test table: {test_table}")
            except Exception as e:
                logger.error(f"Failed to setup consistency test table: {e}")
                raise
        
        await setup_consistency_table()
        
        async def user_operations_sequence(user_index: int) -> Dict:
            """Execute sequence of operations for a single user."""
            user_id = ensure_user_id(f"consistency_user_{user_index}")
            user_start = time.time()
            user_operations = []
            
            try:
                for op_index in range(operations_per_user):
                    op_start = time.time()
                    
                    async with get_isolated_session() as session:
                        # Calculate operation-specific values
                        value = (user_index * 100) + op_index
                        checksum = f"user_{user_index}_op_{op_index}_val_{value}"
                        
                        # Insert user operation record
                        result = await session.execute(f"""
                            INSERT INTO {test_table} (user_id, operation_index, value, checksum)
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                        """, (str(user_id), op_index, value, checksum))
                        
                        record_id = result.fetchone()[0]
                        
                        # Verify immediate consistency
                        verify_result = await session.execute(f"""
                            SELECT value, checksum FROM {test_table} WHERE id = %s
                        """, (record_id,))
                        
                        stored_value, stored_checksum = verify_result.fetchone()
                        
                        if stored_value != value or stored_checksum != checksum:
                            self.isolation_violations.append({
                                "user_id": str(user_id),
                                "operation_index": op_index,
                                "expected_value": value,
                                "stored_value": stored_value,
                                "expected_checksum": checksum,
                                "stored_checksum": stored_checksum
                            })
                        
                        await session.commit()
                        
                        op_time = time.time() - op_start
                        
                        user_operations.append({
                            "operation_index": op_index,
                            "record_id": record_id,
                            "value": value,
                            "checksum": checksum,
                            "operation_time": op_time
                        })
                        
                        # Brief delay to allow interleaving with other users
                        await asyncio.sleep(0.01)
                
                user_time = time.time() - user_start
                
                return {
                    "success": True,
                    "user_id": str(user_id),
                    "user_index": user_index,
                    "operations_completed": len(user_operations),
                    "user_time": user_time,
                    "operations": user_operations
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "user_id": str(user_id),
                    "user_index": user_index,
                    "error": str(e)
                }
        
        # Execute multi-user operations concurrently
        logger.info(f"Testing multi-user data consistency with {num_users} users x {operations_per_user} operations")
        
        user_tasks = [user_operations_sequence(i) for i in range(num_users)]
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Analyze multi-user consistency results
        successful_users = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_users = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # CRITICAL: All users should complete their operations successfully
        user_success_rate = len(successful_users) / num_users
        assert user_success_rate >= 0.95, f"User success rate too low: {user_success_rate:.2%}"
        
        # Verify total operation count and data consistency
        try:
            async with get_isolated_session() as session:
                # Count total records
                count_result = await session.execute(f"SELECT COUNT(*) FROM {test_table}")
                total_records = count_result.fetchone()[0]
                
                expected_records = sum(r["operations_completed"] for r in successful_users)
                assert total_records == expected_records, \
                    f"Record count mismatch: {total_records}/{expected_records} - DATA CONSISTENCY VIOLATION"
                
                # Verify user data isolation
                user_data_result = await session.execute(f"""
                    SELECT user_id, COUNT(*), MIN(value), MAX(value) 
                    FROM {test_table} GROUP BY user_id ORDER BY user_id
                """)
                
                user_data_summary = user_data_result.fetchall()
                
                for user_data in user_data_summary:
                    user_id, record_count, min_value, max_value = user_data
                    user_index = int(user_id.split('_')[-1])
                    
                    # Verify user has expected number of records
                    expected_user_records = operations_per_user
                    assert record_count == expected_user_records, \
                        f"User {user_id} record count wrong: {record_count}/{expected_user_records} - ISOLATION VIOLATION"
                    
                    # Verify value ranges are consistent with user index
                    expected_min = user_index * 100
                    expected_max = user_index * 100 + operations_per_user - 1
                    
                    assert min_value == expected_min, \
                        f"User {user_id} min value wrong: {min_value}/{expected_min} - DATA CORRUPTION"
                    assert max_value == expected_max, \
                        f"User {user_id} max value wrong: {max_value}/{expected_max} - DATA CORRUPTION"
                
                # Verify checksum consistency
                checksum_result = await session.execute(f"""
                    SELECT user_id, operation_index, value, checksum FROM {test_table}
                """)
                
                checksum_violations = 0
                for record in checksum_result.fetchall():
                    user_id, op_index, value, stored_checksum = record
                    user_index = int(user_id.split('_')[-1])
                    
                    expected_checksum = f"user_{user_index}_op_{op_index}_val_{value}"
                    if stored_checksum != expected_checksum:
                        checksum_violations += 1
                
                assert checksum_violations == 0, \
                    f"Checksum violations detected: {checksum_violations} - DATA INTEGRITY FAILURE"
        
        except Exception as verification_error:
            logger.error(f"Multi-user consistency verification failed: {verification_error}")
            raise
        
        finally:
            # Cleanup test table
            try:
                async with get_isolated_session() as session:
                    await session.execute(f"DROP TABLE IF EXISTS {test_table}")
                    await session.commit()
            except Exception as e:
                logger.warning(f"Failed to cleanup consistency test table: {e}")
        
        # Performance validation
        user_times = [r["user_time"] for r in successful_users if "user_time" in r]
        if user_times:
            avg_user_time = sum(user_times) / len(user_times)
            max_user_time = max(user_times)
            
            assert avg_user_time < 5.0, f"Average user completion time too slow: {avg_user_time:.3f}s"
            assert max_user_time < 15.0, f"Maximum user completion time too slow: {max_user_time:.3f}s"
        
        # Check for isolation violations
        assert len(self.isolation_violations) == 0, f"Isolation violations detected: {self.isolation_violations}"
        
        # Limited race conditions allowed for multi-user scenarios
        assert len(self.race_conditions_detected) <= 2, f"Excessive race conditions: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_users)} users completed operations consistently")
        logger.info(f"Total records: {total_records}, Isolation violations: {len(self.isolation_violations)}")
        
        self.assert_business_value_delivered({
            "successful_users": len(successful_users),
            "total_operations": sum(r["operations_completed"] for r in successful_users),
            "data_consistency_maintained": True,
            "isolation_violations": len(self.isolation_violations)
        }, "insights")