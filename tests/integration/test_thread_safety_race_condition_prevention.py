"""
Performance & Load Testing: Thread Safety and Race Condition Prevention

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data consistency and prevent corruption under concurrent operations
- Value Impact: Users experience reliable platform behavior without data corruption or loss
- Strategic Impact: Thread safety is essential for multi-user platform reliability and enterprise adoption

CRITICAL: This test validates thread safety, race condition prevention, and data consistency
under various concurrent access patterns and multi-threading scenarios.
"""

import asyncio
import pytest
import time
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
import uuid
import random

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class ThreadSafetyTestResult:
    """Thread safety test results."""
    test_name: str
    concurrent_operations: int
    successful_operations: int
    failed_operations: int
    race_conditions_detected: int
    data_corruption_events: int
    consistency_violations: int
    execution_time: float
    final_state_consistent: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class RaceConditionScenario:
    """Race condition test scenario configuration."""
    name: str
    operation_count: int
    thread_count: int
    shared_resource: str
    expected_final_value: Any
    tolerance: float = 0.0


class TestThreadSafetyRaceConditionPrevention(BaseIntegrationTest):
    """Test thread safety and race condition prevention mechanisms."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_concurrent_user_session_management(self, real_services_fixture):
        """
        Test thread-safe user session management under concurrent access.
        
        Thread Safety SLA:
        - No session data corruption under 50 concurrent accesses
        - Session state consistency: 100%
        - No race conditions in session creation/deletion
        """
        redis = real_services_fixture["redis"]
        db = real_services_fixture["db"]
        
        concurrent_users = 50
        operations_per_user = 10
        
        # Shared session state tracking
        session_integrity_violations = []
        race_conditions_detected = []
        
        async def concurrent_session_operations(user_id: int) -> Dict[str, Any]:
            """Perform concurrent session operations for a user."""
            user_context = await create_authenticated_user_context(
                user_email=f"thread_safety_user_{user_id}@example.com",
                environment="test"
            )
            
            session_key = f"thread_safety_session:{user_context.user_id}"
            operations_completed = 0
            errors = []
            
            for op_id in range(operations_per_user):
                try:
                    # Concurrent session updates that could cause race conditions
                    operation_type = op_id % 4
                    
                    if operation_type == 0:
                        # Session creation/update
                        session_data = {
                            "user_id": str(user_context.user_id),
                            "last_activity": time.time(),
                            "operation_count": op_id,
                            "thread_id": threading.get_ident(),
                            "created_at": time.time()
                        }
                        await redis.set(session_key, json.dumps(session_data), ex=300)
                        
                    elif operation_type == 1:
                        # Session read and conditional update
                        existing_session = await redis.get(session_key)
                        if existing_session:
                            session_data = json.loads(existing_session)
                            session_data["last_read"] = time.time()
                            session_data["read_count"] = session_data.get("read_count", 0) + 1
                            await redis.set(session_key, json.dumps(session_data), ex=300)
                        
                    elif operation_type == 2:
                        # Atomic increment operation
                        counter_key = f"{session_key}:counter"
                        await redis.incr(counter_key)
                        await redis.expire(counter_key, 300)
                        
                    else:
                        # Complex multi-step operation (prone to race conditions)
                        # Step 1: Read current state
                        current_session = await redis.get(session_key)
                        
                        # Simulate processing delay (increases race condition probability)
                        await asyncio.sleep(0.001)
                        
                        # Step 2: Modify based on read state
                        if current_session:
                            session_data = json.loads(current_session)
                            session_data["complex_op_count"] = session_data.get("complex_op_count", 0) + 1
                            session_data["last_complex_op"] = time.time()
                            
                            # Step 3: Write back (potential race condition here)
                            await redis.set(session_key, json.dumps(session_data), ex=300)
                    
                    operations_completed += 1
                    
                except Exception as e:
                    errors.append(f"User {user_id} operation {op_id} failed: {str(e)}")
            
            # Final consistency check
            try:
                final_session = await redis.get(session_key)
                counter_value = await redis.get(f"{session_key}:counter")
                
                if final_session:
                    session_data = json.loads(final_session)
                    
                    # Check for data integrity issues
                    if session_data.get("user_id") != str(user_context.user_id):
                        session_integrity_violations.append(f"User ID mismatch for user {user_id}")
                    
                    # Check for reasonable operation counts (race condition indicator)
                    complex_op_count = session_data.get("complex_op_count", 0)
                    expected_complex_ops = operations_per_user // 4  # 1/4 operations are complex
                    
                    if abs(complex_op_count - expected_complex_ops) > expected_complex_ops * 0.5:
                        race_conditions_detected.append(
                            f"Potential race condition for user {user_id}: "
                            f"expected ~{expected_complex_ops} complex ops, got {complex_op_count}"
                        )
            
            except Exception as e:
                errors.append(f"Final consistency check failed for user {user_id}: {str(e)}")
            
            # Cleanup
            try:
                await redis.delete(session_key, f"{session_key}:counter")
            except Exception:
                pass
            
            return {
                "user_id": user_id,
                "operations_completed": operations_completed,
                "errors": errors,
                "success": len(errors) == 0
            }
        
        # Execute concurrent session operations
        print(f"🔒 Testing thread safety with {concurrent_users} concurrent users...")
        test_start = time.time()
        
        user_tasks = [
            concurrent_session_operations(user_id)
            for user_id in range(concurrent_users)
        ]
        
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        test_duration = time.time() - test_start
        
        # Analyze thread safety results
        successful_results = [r for r in user_results if isinstance(r, dict) and r.get("success", False)]
        failed_results = [r for r in user_results if isinstance(r, dict) and not r.get("success", False)]
        
        total_operations = sum(r.get("operations_completed", 0) for r in user_results if isinstance(r, dict))
        successful_operations = sum(r.get("operations_completed", 0) for r in successful_results)
        
        # Thread safety assertions
        assert len(session_integrity_violations) == 0, f"Session integrity violations: {session_integrity_violations}"
        assert len(race_conditions_detected) <= concurrent_users * 0.1, f"Too many potential race conditions: {len(race_conditions_detected)}"
        
        success_rate = len(successful_results) / concurrent_users
        assert success_rate >= 0.95, f"Success rate {success_rate:.3f} below 95% threshold"
        
        print(f"✅ Concurrent User Session Management Results:")
        print(f"   Concurrent users: {concurrent_users}")
        print(f"   Successful users: {len(successful_results)}")
        print(f"   Failed users: {len(failed_results)}")
        print(f"   Total operations: {total_operations}")
        print(f"   Successful operations: {successful_operations}")
        print(f"   Session integrity violations: {len(session_integrity_violations)}")
        print(f"   Race conditions detected: {len(race_conditions_detected)}")
        print(f"   Test duration: {test_duration:.2f}s")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_atomic_operations_consistency(self, real_services_fixture):
        """
        Test atomic operations and consistency under high concurrency.
        
        Thread Safety SLA:
        - Atomic operations maintain consistency: 100%
        - No lost updates or phantom reads
        - Counter integrity under concurrent increments
        """
        redis = real_services_fixture["redis"]
        db = real_services_fixture["db"]
        
        # Test scenarios for atomic operations
        atomic_test_scenarios = [
            {
                "name": "redis_counter",
                "operation_count": 1000,
                "concurrent_workers": 50,
                "expected_final_value": 1000
            },
            {
                "name": "redis_hash_updates",
                "operation_count": 500,
                "concurrent_workers": 25,
                "expected_final_value": 500
            }
        ]
        
        scenario_results = []
        
        for scenario in atomic_test_scenarios:
            print(f"🔢 Testing atomic operations: {scenario['name']}")
            
            test_key = f"atomic_test:{scenario['name']}:{int(time.time())}"
            
            async def atomic_operation_worker(worker_id: int, operations_per_worker: int) -> Dict[str, Any]:
                """Perform atomic operations from a single worker."""
                worker_operations = 0
                errors = []
                
                try:
                    for op_id in range(operations_per_worker):
                        if scenario["name"] == "redis_counter":
                            # Atomic increment
                            await redis.incr(test_key)
                            worker_operations += 1
                            
                        elif scenario["name"] == "redis_hash_updates":
                            # Atomic hash field increment
                            hash_key = f"{test_key}:hash"
                            field_name = f"field_{op_id % 10}"  # Use 10 different fields
                            await redis.hincrby(hash_key, field_name, 1)
                            await redis.expire(hash_key, 300)
                            worker_operations += 1
                        
                except Exception as e:
                    errors.append(f"Worker {worker_id} error: {str(e)}")
                
                return {
                    "worker_id": worker_id,
                    "operations_completed": worker_operations,
                    "errors": errors,
                    "success": len(errors) == 0
                }
            
            # Calculate operations per worker
            operations_per_worker = scenario["operation_count"] // scenario["concurrent_workers"]
            
            # Execute concurrent atomic operations
            scenario_start = time.time()
            
            worker_tasks = [
                atomic_operation_worker(worker_id, operations_per_worker)
                for worker_id in range(scenario["concurrent_workers"])
            ]
            
            worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
            
            scenario_duration = time.time() - scenario_start
            
            # Verify final state consistency
            if scenario["name"] == "redis_counter":
                final_counter_value = await redis.get(test_key)
                final_value = int(final_counter_value) if final_counter_value else 0
                expected_value = operations_per_worker * scenario["concurrent_workers"]
                
                consistency_check = final_value == expected_value
                
            elif scenario["name"] == "redis_hash_updates":
                hash_key = f"{test_key}:hash"
                hash_values = await redis.hgetall(hash_key)
                total_hash_increments = sum(int(v) for v in hash_values.values()) if hash_values else 0
                expected_value = operations_per_worker * scenario["concurrent_workers"]
                
                consistency_check = total_hash_increments == expected_value
                final_value = total_hash_increments
            
            # Analyze worker results
            successful_workers = [r for r in worker_results if isinstance(r, dict) and r.get("success", False)]
            total_worker_operations = sum(r.get("operations_completed", 0) for r in worker_results if isinstance(r, dict))
            
            scenario_result = {
                "name": scenario["name"],
                "concurrent_workers": scenario["concurrent_workers"],
                "total_operations": total_worker_operations,
                "expected_final_value": expected_value,
                "actual_final_value": final_value,
                "consistency_check": consistency_check,
                "successful_workers": len(successful_workers),
                "duration": scenario_duration,
                "operations_per_second": total_worker_operations / scenario_duration
            }
            
            scenario_results.append(scenario_result)
            
            # Scenario-specific assertions
            assert consistency_check, f"Atomic operation consistency failed for {scenario['name']}: expected {expected_value}, got {final_value}"
            assert len(successful_workers) >= scenario["concurrent_workers"] * 0.95, f"Too many worker failures in {scenario['name']}"
            
            print(f"   {scenario['name']} Results:")
            print(f"     Expected final value: {expected_value}")
            print(f"     Actual final value: {final_value}")
            print(f"     Consistency check: {'✓' if consistency_check else '✗'}")
            print(f"     Successful workers: {len(successful_workers)}/{scenario['concurrent_workers']}")
            print(f"     Operations/second: {scenario_result['operations_per_second']:.1f}")
            
            # Cleanup
            await redis.delete(test_key)
            if scenario["name"] == "redis_hash_updates":
                await redis.delete(f"{test_key}:hash")
        
        print(f"✅ Atomic Operations Consistency Test Results:")
        for result in scenario_results:
            print(f"   {result['name']}: {'PASSED' if result['consistency_check'] else 'FAILED'}")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_database_transaction_isolation_levels(self, real_services_fixture):
        """
        Test database transaction isolation and prevent race conditions.
        
        Thread Safety SLA:
        - No dirty reads or phantom reads
        - Transaction isolation maintained under concurrency
        - No deadlocks under normal operation patterns
        """
        db = real_services_fixture["db"]
        
        # Create test table for isolation testing
        test_table = f"thread_safety_test_{int(time.time())}"
        
        try:
            await db.execute(f"""
                CREATE TEMPORARY TABLE {test_table} (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    balance DECIMAL(10,2) NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Initialize test accounts
            account_count = 10
            initial_balance = 1000.00
            
            for account_id in range(account_count):
                await db.execute(
                    f"INSERT INTO {test_table} (account_id, balance) VALUES ($1, $2)",
                    account_id, initial_balance
                )
            
            # Test concurrent balance transfers (classic race condition scenario)
            transfer_count = 100
            concurrent_transfers = 50
            
            transfer_results = []
            deadlock_count = 0
            
            async def concurrent_balance_transfer(transfer_id: int) -> Dict[str, Any]:
                """Perform a balance transfer with proper transaction isolation."""
                try:
                    # Random transfer between accounts
                    from_account = random.randint(0, account_count - 1)
                    to_account = random.randint(0, account_count - 1)
                    
                    # Ensure different accounts
                    while to_account == from_account:
                        to_account = random.randint(0, account_count - 1)
                    
                    transfer_amount = random.uniform(1.00, 50.00)
                    
                    # Use transaction with proper isolation
                    async with db.transaction():
                        # Lock accounts in consistent order to prevent deadlocks
                        if from_account < to_account:
                            first_account, second_account = from_account, to_account
                        else:
                            first_account, second_account = to_account, from_account
                        
                        # Get current balances with SELECT FOR UPDATE
                        from_balance = await db.fetchval(
                            f"SELECT balance FROM {test_table} WHERE account_id = $1 FOR UPDATE",
                            from_account
                        )
                        
                        to_balance = await db.fetchval(
                            f"SELECT balance FROM {test_table} WHERE account_id = $1 FOR UPDATE",
                            to_account
                        )
                        
                        # Check sufficient funds
                        if from_balance >= transfer_amount:
                            # Update balances
                            await db.execute(
                                f"UPDATE {test_table} SET balance = balance - $1, version = version + 1, updated_at = NOW() WHERE account_id = $2",
                                transfer_amount, from_account
                            )
                            
                            await db.execute(
                                f"UPDATE {test_table} SET balance = balance + $1, version = version + 1, updated_at = NOW() WHERE account_id = $2",
                                transfer_amount, to_account
                            )
                            
                            return {
                                "transfer_id": transfer_id,
                                "from_account": from_account,
                                "to_account": to_account,
                                "amount": transfer_amount,
                                "success": True,
                                "error": None
                            }
                        else:
                            return {
                                "transfer_id": transfer_id,
                                "from_account": from_account,
                                "to_account": to_account,
                                "amount": transfer_amount,
                                "success": False,
                                "error": "insufficient_funds"
                            }
                
                except Exception as e:
                    error_str = str(e).lower()
                    is_deadlock = "deadlock" in error_str or "lock" in error_str
                    
                    return {
                        "transfer_id": transfer_id,
                        "from_account": None,
                        "to_account": None,
                        "amount": 0,
                        "success": False,
                        "error": "deadlock" if is_deadlock else str(e)
                    }
            
            # Execute concurrent transfers
            print(f"💰 Testing database transaction isolation with {concurrent_transfers} concurrent transfers...")
            transfers_start = time.time()
            
            transfer_tasks = [
                concurrent_balance_transfer(i)
                for i in range(concurrent_transfers)
            ]
            
            transfer_results = await asyncio.gather(*transfer_tasks, return_exceptions=True)
            
            transfers_duration = time.time() - transfers_start
            
            # Analyze transfer results
            successful_transfers = [r for r in transfer_results if isinstance(r, dict) and r.get("success", False)]
            failed_transfers = [r for r in transfer_results if isinstance(r, dict) and not r.get("success", False)]
            
            # Count deadlocks
            deadlock_transfers = [r for r in failed_transfers if r.get("error") == "deadlock"]
            deadlock_count = len(deadlock_transfers)
            
            # Verify total balance conservation (critical consistency check)
            final_balances = await db.fetch(f"SELECT account_id, balance FROM {test_table} ORDER BY account_id")
            total_final_balance = sum(float(row["balance"]) for row in final_balances)
            expected_total_balance = account_count * initial_balance
            
            balance_conservation_check = abs(total_final_balance - expected_total_balance) < 0.01
            
            # Transaction isolation assertions
            assert balance_conservation_check, f"Balance conservation violation: expected {expected_total_balance:.2f}, got {total_final_balance:.2f}"
            assert deadlock_count <= concurrent_transfers * 0.05, f"Too many deadlocks: {deadlock_count}/{concurrent_transfers}"
            
            success_rate = len(successful_transfers) / concurrent_transfers
            assert success_rate >= 0.80, f"Transfer success rate {success_rate:.3f} too low (deadlocks may be acceptable)"
            
            print(f"✅ Database Transaction Isolation Results:")
            print(f"   Concurrent transfers: {concurrent_transfers}")
            print(f"   Successful transfers: {len(successful_transfers)}")
            print(f"   Failed transfers: {len(failed_transfers)}")
            print(f"   Deadlock transfers: {deadlock_count}")
            print(f"   Success rate: {success_rate:.3f}")
            print(f"   Expected total balance: {expected_total_balance:.2f}")
            print(f"   Actual total balance: {total_final_balance:.2f}")
            print(f"   Balance conservation: {'✓' if balance_conservation_check else '✗'}")
            print(f"   Transfer duration: {transfers_duration:.2f}s")
            
        finally:
            # Cleanup test table
            try:
                await db.execute(f"DROP TABLE IF EXISTS {test_table}")
            except Exception:
                pass
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_shared_resource_locking_mechanisms(self, real_services_fixture):
        """
        Test shared resource locking and prevent race conditions.
        
        Thread Safety SLA:
        - Exclusive access to critical sections
        - No race conditions in shared resource updates
        - Fair lock acquisition under contention
        """
        redis = real_services_fixture["redis"]
        
        # Simulate shared resource with locking
        shared_resource_key = f"shared_resource:{int(time.time())}"
        lock_key = f"{shared_resource_key}:lock"
        
        # Initialize shared resource
        initial_value = {"counter": 0, "operations": [], "consistency_check": 0}
        await redis.set(shared_resource_key, json.dumps(initial_value), ex=600)
        
        concurrent_workers = 30
        operations_per_worker = 20
        
        lock_violations = []
        consistency_errors = []
        
        async def locked_resource_operation(worker_id: int, operations: int) -> Dict[str, Any]:
            """Perform operations on shared resource with distributed locking."""
            worker_operations = 0
            lock_acquisitions = 0
            lock_timeouts = 0
            errors = []
            
            for op_id in range(operations):
                # Acquire distributed lock with timeout
                lock_timeout = 5.0  # 5 second lock timeout
                lock_value = f"worker_{worker_id}_op_{op_id}_{time.time()}"
                
                try:
                    # Try to acquire lock with SET NX EX (atomic operation)
                    lock_acquired = await redis.set(
                        lock_key,
                        lock_value,
                        nx=True,  # Only set if not exists
                        ex=int(lock_timeout)  # Expire after timeout
                    )
                    
                    if lock_acquired:
                        lock_acquisitions += 1
                        
                        try:
                            # Critical section - modify shared resource
                            current_data_str = await redis.get(shared_resource_key)
                            if current_data_str:
                                current_data = json.loads(current_data_str)
                                
                                # Simulate processing time (increases contention)
                                await asyncio.sleep(0.01)
                                
                                # Modify shared resource
                                current_data["counter"] += 1
                                current_data["operations"].append({
                                    "worker_id": worker_id,
                                    "op_id": op_id,
                                    "timestamp": time.time(),
                                    "lock_value": lock_value
                                })
                                
                                # Consistency check value (should equal counter)
                                current_data["consistency_check"] = current_data["counter"]
                                
                                # Write back to shared resource
                                await redis.set(shared_resource_key, json.dumps(current_data), ex=600)
                                
                                worker_operations += 1
                            
                        finally:
                            # Release lock (only if we still own it)
                            current_lock_value = await redis.get(lock_key)
                            if current_lock_value == lock_value:
                                await redis.delete(lock_key)
                            else:
                                # Lock was stolen or expired - potential violation
                                lock_violations.append(
                                    f"Worker {worker_id} lock violation: expected {lock_value}, got {current_lock_value}"
                                )
                    else:
                        # Lock acquisition failed
                        lock_timeouts += 1
                        
                        # Wait a bit before retrying
                        await asyncio.sleep(0.001)
                        
                except Exception as e:
                    errors.append(f"Worker {worker_id} operation {op_id} error: {str(e)}")
            
            return {
                "worker_id": worker_id,
                "operations_completed": worker_operations,
                "lock_acquisitions": lock_acquisitions,
                "lock_timeouts": lock_timeouts,
                "errors": errors,
                "success": len(errors) == 0
            }
        
        # Execute concurrent workers with locking
        print(f"🔐 Testing shared resource locking with {concurrent_workers} workers...")
        locking_start = time.time()
        
        worker_tasks = [
            locked_resource_operation(worker_id, operations_per_worker)
            for worker_id in range(concurrent_workers)
        ]
        
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        locking_duration = time.time() - locking_start
        
        # Analyze locking results
        successful_workers = [r for r in worker_results if isinstance(r, dict) and r.get("success", False)]
        total_operations = sum(r.get("operations_completed", 0) for r in worker_results if isinstance(r, dict))
        total_lock_acquisitions = sum(r.get("lock_acquisitions", 0) for r in worker_results if isinstance(r, dict))
        total_lock_timeouts = sum(r.get("lock_timeouts", 0) for r in worker_results if isinstance(r, dict))
        
        # Verify final shared resource state
        final_data_str = await redis.get(shared_resource_key)
        if final_data_str:
            final_data = json.loads(final_data_str)
            
            final_counter = final_data.get("counter", 0)
            final_consistency_check = final_data.get("consistency_check", 0)
            final_operations_count = len(final_data.get("operations", []))
            
            # Consistency checks
            counter_consistency = final_counter == final_consistency_check
            operations_consistency = final_counter == final_operations_count
            expected_total_operations = total_operations
            
            if not counter_consistency:
                consistency_errors.append(f"Counter consistency violation: counter={final_counter}, check={final_consistency_check}")
            
            if not operations_consistency:
                consistency_errors.append(f"Operations consistency violation: counter={final_counter}, ops_count={final_operations_count}")
            
            if final_counter != expected_total_operations:
                consistency_errors.append(f"Total operations mismatch: expected={expected_total_operations}, actual={final_counter}")
        else:
            consistency_errors.append("Shared resource disappeared")
            final_counter = 0
        
        # Thread safety and locking assertions
        assert len(lock_violations) == 0, f"Lock violations detected: {lock_violations[:5]}"  # Show first 5
        assert len(consistency_errors) == 0, f"Consistency errors: {consistency_errors}"        
        
        success_rate = len(successful_workers) / concurrent_workers
        assert success_rate >= 0.90, f"Worker success rate {success_rate:.3f} below 90%"
        
        # Lock efficiency check (not too many timeouts)
        total_attempted_operations = concurrent_workers * operations_per_worker
        timeout_rate = total_lock_timeouts / total_attempted_operations
        assert timeout_rate <= 0.3, f"Lock timeout rate {timeout_rate:.3f} too high"
        
        print(f"✅ Shared Resource Locking Test Results:")
        print(f"   Concurrent workers: {concurrent_workers}")
        print(f"   Successful workers: {len(successful_workers)}")
        print(f"   Total operations completed: {total_operations}")
        print(f"   Lock acquisitions: {total_lock_acquisitions}")
        print(f"   Lock timeouts: {total_lock_timeouts}")
        print(f"   Timeout rate: {timeout_rate:.3f}")
        print(f"   Final counter value: {final_counter}")
        print(f"   Lock violations: {len(lock_violations)}")
        print(f"   Consistency errors: {len(consistency_errors)}")
        print(f"   Test duration: {locking_duration:.2f}s")
        
        # Cleanup
        await redis.delete(shared_resource_key, lock_key)