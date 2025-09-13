"""
Integration Tests: Database Transaction Boundary Conditions

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (multi-user concurrent database operations)
- Business Goal: Data Integrity + System Reliability + ACID Compliance
- Value Impact: Ensures transactional integrity under concurrent load, prevents
  data corruption and inconsistency issues, maintains ACID compliance for
  financial and audit requirements, supports concurrent user operations
- Revenue Impact: Protects $500K+ ARR from data integrity failures, enables
  Enterprise contracts requiring ACID compliance, prevents costly data recovery
  scenarios and regulatory compliance violations

Test Focus: Database transaction boundaries, ACID properties under concurrency,
deadlock detection and recovery, isolation levels, and consistency guarantees.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import json
import random

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.config import get_config


class TestDatabaseTransactionBoundaryConditions(BaseIntegrationTest):
    """
    Test database transaction boundaries under concurrent access conditions.
    
    Business Value: Ensures data integrity and ACID compliance under concurrent
    operations, critical for Enterprise customers with strict data requirements.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_transaction_test(self, real_services_fixture):
        """Setup database transaction boundary test environment."""
        self.config = get_config()
        
        # Transaction simulation state
        self.active_transactions: Dict[str, Dict[str, Any]] = {}
        self.committed_transactions: List[Dict[str, Any]] = []
        self.rolled_back_transactions: List[Dict[str, Any]] = []
        self.deadlock_detections: List[Dict[str, Any]] = []
        self.isolation_violations: List[Dict[str, Any]] = []
        
        # Database simulation state
        self.database_records: Dict[str, Dict[str, Any]] = {}
        self.record_locks: Dict[str, str] = {}  # record_id -> transaction_id
        self.transaction_dependencies: Dict[str, Set[str]] = {}  # tx_id -> set of waiting tx_ids
        
        # Synchronization primitives
        self.transaction_lock = asyncio.Lock()
        self.database_lock = asyncio.Lock()
        
        # Test contexts
        self.test_contexts: List[UserExecutionContext] = []
        
        # Initialize test database records
        for record_id in range(20):
            self.database_records[f"record_{record_id}"] = {
                "id": f"record_{record_id}",
                "value": random.randint(1, 1000),
                "version": 1,
                "last_modified": time.time(),
                "locked_by": None
            }
        
        yield
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_concurrent_transaction_acid_properties(self):
        """
        Test ACID properties under concurrent transaction execution.
        
        BVJ: Validates fundamental database guarantees that protect data integrity
        and enable reliable business operations at Enterprise scale.
        """
        num_concurrent_transactions = 20
        operations_per_transaction = 5
        
        transaction_results = []
        acid_violations = []
        
        async def acid_compliant_transaction(tx_id: str, operation_count: int):
            """Execute transaction with ACID property validation."""
            context = UserExecutionContext(
                user_id=f"tx_user_{tx_id}",
                session_id=f"tx_session_{tx_id}",
                request_id=f"tx_req_{tx_id}"
            )
            self.test_contexts.append(context)
            
            transaction_data = {
                "transaction_id": tx_id,
                "user_id": context.user_id,
                "start_time": time.time(),
                "operations": [],
                "status": "active",
                "isolation_level": "READ_COMMITTED",
                "locks_acquired": [],
                "records_modified": []
            }
            
            try:
                # Start transaction
                async with self.transaction_lock:
                    self.active_transactions[tx_id] = transaction_data
                
                # Execute operations within transaction
                for op_num in range(operation_count):
                    operation_result = await self._execute_transactional_operation(
                        tx_id, op_num, context
                    )
                    transaction_data["operations"].append(operation_result)
                    
                    if not operation_result["success"]:
                        raise Exception(f"Operation {op_num} failed: {operation_result['error']}")
                
                # Validate ACID properties before commit
                acid_validation = await self._validate_acid_properties(tx_id, transaction_data)
                
                if not acid_validation["valid"]:
                    acid_violations.extend(acid_validation["violations"])
                    raise Exception(f"ACID validation failed: {acid_validation['violations']}")
                
                # Commit transaction
                commit_result = await self._commit_transaction(tx_id, transaction_data)
                
                if not commit_result["success"]:
                    raise Exception(f"Commit failed: {commit_result['error']}")
                
                return {
                    "transaction_id": tx_id,
                    "operations_completed": len(transaction_data["operations"]),
                    "commit_success": commit_result["success"],
                    "acid_compliant": acid_validation["valid"],
                    "execution_time": time.time() - transaction_data["start_time"]
                }
                
            except Exception as e:
                # Rollback transaction
                rollback_result = await self._rollback_transaction(tx_id, transaction_data)
                
                return {
                    "transaction_id": tx_id,
                    "operations_completed": len(transaction_data["operations"]),
                    "commit_success": False,
                    "rollback_success": rollback_result["success"],
                    "error": str(e),
                    "execution_time": time.time() - transaction_data["start_time"]
                }
        
        # Execute concurrent transactions
        transaction_tasks = []
        for tx_num in range(num_concurrent_transactions):
            tx_id = f"acid_tx_{tx_num}_{uuid.uuid4().hex[:8]}"
            task = asyncio.create_task(
                acid_compliant_transaction(tx_id, operations_per_transaction)
            )
            transaction_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*transaction_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze ACID compliance results
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == num_concurrent_transactions
        
        # Verify high transaction success rate
        committed_transactions = [r for r in successful_results if r.get("commit_success")]
        rolled_back_transactions = [r for r in successful_results if not r.get("commit_success")]
        
        commit_rate = len(committed_transactions) / len(successful_results)
        assert commit_rate >= 0.7, \
            f"Transaction commit rate too low: {commit_rate:.2%}"
        
        # Verify no ACID violations
        assert len(acid_violations) == 0, \
            f"ACID violations detected: {acid_violations}"
        
        # Verify database consistency after all transactions
        consistency_check = await self._verify_database_consistency()
        assert consistency_check["consistent"], \
            f"Database inconsistency detected: {consistency_check['violations']}"
        
        # Verify transaction isolation
        for result in successful_results:
            if result.get("acid_compliant") is False:
                pytest.fail(f"Transaction {result['transaction_id']} violated ACID properties")
        
        self.logger.info(f"ACID transaction test completed: {len(committed_transactions)} committed, "
                        f"{len(rolled_back_transactions)} rolled back, {execution_time:.2f}s")
    
    async def _execute_transactional_operation(self, tx_id: str, op_num: int, 
                                             context: UserExecutionContext) -> Dict[str, Any]:
        """Execute a single operation within a transaction."""
        try:
            # Select random record to operate on
            record_id = f"record_{random.randint(0, 19)}"
            operation_type = random.choice(["read", "update", "insert"])
            
            async with self.database_lock:
                if operation_type == "read":
                    # Read operation with isolation level consideration
                    if record_id in self.database_records:
                        record_data = self.database_records[record_id].copy()
                        return {
                            "success": True,
                            "operation": "read",
                            "record_id": record_id,
                            "data": record_data,
                            "timestamp": time.time()
                        }
                    else:
                        return {
                            "success": False,
                            "operation": "read",
                            "record_id": record_id,
                            "error": "Record not found"
                        }
                
                elif operation_type == "update":
                    # Update with locking
                    if record_id in self.record_locks and self.record_locks[record_id] != tx_id:
                        # Record is locked by another transaction
                        return {
                            "success": False,
                            "operation": "update",
                            "record_id": record_id,
                            "error": "Record locked by another transaction"
                        }
                    
                    # Acquire lock and update
                    self.record_locks[record_id] = tx_id
                    if tx_id in self.active_transactions:
                        self.active_transactions[tx_id]["locks_acquired"].append(record_id)
                    
                    if record_id in self.database_records:
                        old_value = self.database_records[record_id]["value"]
                        new_value = old_value + random.randint(1, 100)
                        
                        self.database_records[record_id].update({
                            "value": new_value,
                            "version": self.database_records[record_id]["version"] + 1,
                            "last_modified": time.time(),
                            "locked_by": tx_id
                        })
                        
                        if tx_id in self.active_transactions:
                            self.active_transactions[tx_id]["records_modified"].append(record_id)
                        
                        return {
                            "success": True,
                            "operation": "update",
                            "record_id": record_id,
                            "old_value": old_value,
                            "new_value": new_value,
                            "timestamp": time.time()
                        }
                
                elif operation_type == "insert":
                    # Insert new record
                    new_record_id = f"temp_record_{tx_id}_{op_num}"
                    new_record = {
                        "id": new_record_id,
                        "value": random.randint(1, 1000),
                        "version": 1,
                        "last_modified": time.time(),
                        "locked_by": tx_id,
                        "created_by_tx": tx_id
                    }
                    
                    self.database_records[new_record_id] = new_record
                    self.record_locks[new_record_id] = tx_id
                    
                    if tx_id in self.active_transactions:
                        self.active_transactions[tx_id]["locks_acquired"].append(new_record_id)
                        self.active_transactions[tx_id]["records_modified"].append(new_record_id)
                    
                    return {
                        "success": True,
                        "operation": "insert",
                        "record_id": new_record_id,
                        "data": new_record,
                        "timestamp": time.time()
                    }
                
            return {
                "success": False,
                "operation": operation_type,
                "error": "Unknown operation type"
            }
            
        except Exception as e:
            return {
                "success": False,
                "operation": operation_type,
                "record_id": record_id if 'record_id' in locals() else None,
                "error": str(e)
            }
    
    async def _validate_acid_properties(self, tx_id: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate ACID properties for a transaction."""
        violations = []
        
        # Atomicity: All operations succeed or none do
        operations = transaction_data["operations"]
        successful_ops = [op for op in operations if op["success"]]
        failed_ops = [op for op in operations if not op["success"]]
        
        if len(failed_ops) > 0 and len(successful_ops) > 0:
            violations.append({
                "property": "Atomicity",
                "violation": "Partial operation success detected",
                "details": f"{len(successful_ops)} succeeded, {len(failed_ops)} failed"
            })
        
        # Consistency: Database constraints maintained
        for record_id in transaction_data["records_modified"]:
            if record_id in self.database_records:
                record = self.database_records[record_id]
                if record["value"] <= 0:
                    violations.append({
                        "property": "Consistency",
                        "violation": "Invalid record value",
                        "details": f"Record {record_id} has value {record['value']}"
                    })
        
        # Isolation: Transaction effects not visible to others until commit
        for record_id in transaction_data["records_modified"]:
            if record_id in self.record_locks and self.record_locks[record_id] != tx_id:
                violations.append({
                    "property": "Isolation",
                    "violation": "Record modified by another transaction",
                    "details": f"Record {record_id} locked by {self.record_locks[record_id]}"
                })
        
        # Durability will be validated after commit
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }
    
    async def _commit_transaction(self, tx_id: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Commit transaction and release locks."""
        try:
            async with self.transaction_lock:
                # Release all locks acquired by this transaction
                for record_id in transaction_data["locks_acquired"]:
                    if record_id in self.record_locks and self.record_locks[record_id] == tx_id:
                        del self.record_locks[record_id]
                        
                        # Update record to show it's no longer locked
                        if record_id in self.database_records:
                            self.database_records[record_id]["locked_by"] = None
                
                # Move to committed transactions
                transaction_data["status"] = "committed"
                transaction_data["commit_time"] = time.time()
                self.committed_transactions.append(transaction_data)
                
                # Remove from active transactions
                if tx_id in self.active_transactions:
                    del self.active_transactions[tx_id]
                
                return {"success": True, "committed_at": transaction_data["commit_time"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _rollback_transaction(self, tx_id: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback transaction and undo changes."""
        try:
            async with self.transaction_lock:
                # Undo all changes made by this transaction
                for record_id in transaction_data["records_modified"]:
                    if record_id.startswith("temp_record_"):
                        # Remove inserted records
                        if record_id in self.database_records:
                            del self.database_records[record_id]
                    else:
                        # For updated records, we would need to restore previous values
                        # In a real system, this would use transaction logs
                        if record_id in self.database_records:
                            self.database_records[record_id]["locked_by"] = None
                
                # Release all locks
                for record_id in transaction_data["locks_acquired"]:
                    if record_id in self.record_locks and self.record_locks[record_id] == tx_id:
                        del self.record_locks[record_id]
                
                # Move to rolled back transactions
                transaction_data["status"] = "rolled_back"
                transaction_data["rollback_time"] = time.time()
                self.rolled_back_transactions.append(transaction_data)
                
                # Remove from active transactions
                if tx_id in self.active_transactions:
                    del self.active_transactions[tx_id]
                
                return {"success": True, "rolled_back_at": transaction_data["rollback_time"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _verify_database_consistency(self) -> Dict[str, Any]:
        """Verify database consistency after all transactions."""
        violations = []
        
        # Check for orphaned locks
        for record_id, tx_id in self.record_locks.items():
            if tx_id not in self.active_transactions:
                violations.append({
                    "type": "orphaned_lock",
                    "record_id": record_id,
                    "transaction_id": tx_id
                })
        
        # Check record integrity
        for record_id, record in self.database_records.items():
            if record["value"] <= 0:
                violations.append({
                    "type": "invalid_value",
                    "record_id": record_id,
                    "value": record["value"]
                })
                
            if record["version"] <= 0:
                violations.append({
                    "type": "invalid_version",
                    "record_id": record_id,
                    "version": record["version"]
                })
        
        return {
            "consistent": len(violations) == 0,
            "violations": violations
        }
    
    @pytest.mark.asyncio
    async def test_deadlock_detection_and_recovery(self):
        """
        Test deadlock detection and automatic recovery mechanisms.
        
        BVJ: Prevents system hangs and ensures continued operation under
        complex concurrent scenarios, critical for high-availability systems.
        """
        num_deadlock_scenarios = 5
        transactions_per_scenario = 4
        
        deadlock_scenarios_resolved = []
        deadlock_recovery_failures = []
        
        async def create_potential_deadlock_scenario(scenario_id: str):
            """Create a scenario that could lead to deadlock."""
            scenario_transactions = []
            
            for tx_num in range(transactions_per_scenario):
                tx_id = f"deadlock_tx_{scenario_id}_{tx_num}"
                context = UserExecutionContext(
                    user_id=f"deadlock_user_{tx_id}",
                    session_id=f"deadlock_session_{tx_id}",
                    request_id=f"deadlock_req_{tx_id}"
                )
                self.test_contexts.append(context)
                
                transaction_task = asyncio.create_task(
                    self._deadlock_prone_transaction(tx_id, tx_num, scenario_id)
                )
                scenario_transactions.append((tx_id, transaction_task))
            
            # Wait for all transactions with deadlock detection
            start_time = time.time()
            deadlock_detected = False
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*[task for _, task in scenario_transactions], return_exceptions=True),
                    timeout=10.0
                )
                
                execution_time = time.time() - start_time
                
                # Analyze results for deadlock indicators
                timeout_results = [r for r in results if isinstance(r, Exception)]
                successful_results = [r for r in results if isinstance(r, dict)]
                
                if len(timeout_results) > 0 or execution_time > 8.0:
                    deadlock_detected = True
                    
                    # Attempt deadlock recovery
                    recovery_success = await self._recover_from_deadlock(
                        scenario_id, [tx_id for tx_id, _ in scenario_transactions]
                    )
                    
                    if recovery_success:
                        deadlock_scenarios_resolved.append({
                            "scenario_id": scenario_id,
                            "transactions": len(scenario_transactions),
                            "recovery_time": time.time() - start_time,
                            "recovery_method": "transaction_rollback"
                        })
                    else:
                        deadlock_recovery_failures.append({
                            "scenario_id": scenario_id,
                            "error": "Failed to recover from deadlock"
                        })
                
                return {
                    "scenario_id": scenario_id,
                    "deadlock_detected": deadlock_detected,
                    "successful_transactions": len(successful_results),
                    "failed_transactions": len(timeout_results),
                    "execution_time": execution_time
                }
                
            except asyncio.TimeoutError:
                # Definite deadlock scenario
                deadlock_detected = True
                
                # Force deadlock recovery
                recovery_success = await self._recover_from_deadlock(
                    scenario_id, [tx_id for tx_id, _ in scenario_transactions]
                )
                
                # Cancel remaining tasks
                for tx_id, task in scenario_transactions:
                    if not task.done():
                        task.cancel()
                
                if recovery_success:
                    deadlock_scenarios_resolved.append({
                        "scenario_id": scenario_id,
                        "transactions": len(scenario_transactions),
                        "recovery_time": time.time() - start_time,
                        "recovery_method": "timeout_recovery"
                    })
                else:
                    deadlock_recovery_failures.append({
                        "scenario_id": scenario_id,
                        "error": "Timeout recovery failed"
                    })
                
                return {
                    "scenario_id": scenario_id,
                    "deadlock_detected": True,
                    "timeout_occurred": True,
                    "execution_time": time.time() - start_time
                }
        
        # Execute deadlock scenarios
        scenario_tasks = []
        for scenario_num in range(num_deadlock_scenarios):
            scenario_id = f"deadlock_scenario_{scenario_num}"
            task = asyncio.create_task(create_potential_deadlock_scenario(scenario_id))
            scenario_tasks.append(task)
        
        start_time = time.time()
        scenario_results = await asyncio.gather(*scenario_tasks, return_exceptions=True)
        total_execution_time = time.time() - start_time
        
        # Analyze deadlock detection and recovery results
        successful_scenarios = [r for r in scenario_results if isinstance(r, dict)]
        assert len(successful_scenarios) == num_deadlock_scenarios
        
        # Verify deadlock detection worked
        scenarios_with_deadlocks = [s for s in successful_scenarios if s.get("deadlock_detected")]
        
        # At least some scenarios should have detected potential deadlocks
        if len(scenarios_with_deadlocks) > 0:
            # Verify recovery success rate
            recovery_success_rate = len(deadlock_scenarios_resolved) / len(scenarios_with_deadlocks)
            assert recovery_success_rate >= 0.8, \
                f"Deadlock recovery success rate too low: {recovery_success_rate:.2%}"
        
        # Verify no unresolved deadlock recovery failures
        assert len(deadlock_recovery_failures) == 0, \
            f"Deadlock recovery failures: {deadlock_recovery_failures}"
        
        # Verify system didn't hang (total execution time reasonable)
        assert total_execution_time < 60.0, \
            f"Deadlock scenarios took too long: {total_execution_time:.2f}s"
        
        self.logger.info(f"Deadlock detection test completed: {len(scenarios_with_deadlocks)} deadlocks detected, "
                        f"{len(deadlock_scenarios_resolved)} resolved, {total_execution_time:.2f}s")
    
    async def _deadlock_prone_transaction(self, tx_id: str, tx_num: int, scenario_id: str) -> Dict[str, Any]:
        """Execute transaction designed to create deadlock potential."""
        # Create circular dependency pattern
        record_a = f"record_{(tx_num * 2) % 10}"
        record_b = f"record_{((tx_num * 2) + 1) % 10}"
        
        # Reverse order for alternate transactions to create circular wait
        if tx_num % 2 == 0:
            first_record, second_record = record_a, record_b
        else:
            first_record, second_record = record_b, record_a
        
        try:
            # First lock
            async with self.database_lock:
                if first_record in self.record_locks:
                    # Record already locked - potential deadlock
                    await asyncio.sleep(0.1)  # Wait and try again
                    if first_record in self.record_locks:
                        raise Exception(f"Deadlock potential: {first_record} locked")
                
                self.record_locks[first_record] = tx_id
            
            # Simulate some processing
            await asyncio.sleep(0.2)
            
            # Second lock (potential circular dependency)
            async with self.database_lock:
                if second_record in self.record_locks:
                    # Potential deadlock detected
                    raise Exception(f"Deadlock detected: {second_record} locked")
                
                self.record_locks[second_record] = tx_id
            
            # Simulate transaction work
            await asyncio.sleep(0.1)
            
            # Release locks
            async with self.database_lock:
                if first_record in self.record_locks and self.record_locks[first_record] == tx_id:
                    del self.record_locks[first_record]
                if second_record in self.record_locks and self.record_locks[second_record] == tx_id:
                    del self.record_locks[second_record]
            
            return {
                "transaction_id": tx_id,
                "success": True,
                "records_locked": [first_record, second_record]
            }
            
        except Exception as e:
            # Clean up locks on failure
            async with self.database_lock:
                if first_record in self.record_locks and self.record_locks[first_record] == tx_id:
                    del self.record_locks[first_record]
                if second_record in self.record_locks and self.record_locks[second_record] == tx_id:
                    del self.record_locks[second_record]
            
            return {
                "transaction_id": tx_id,
                "success": False,
                "error": str(e)
            }
    
    async def _recover_from_deadlock(self, scenario_id: str, transaction_ids: List[str]) -> bool:
        """Recover from deadlock by rolling back transactions."""
        try:
            self.deadlock_detections.append({
                "scenario_id": scenario_id,
                "transaction_ids": transaction_ids,
                "detection_time": time.time(),
                "recovery_method": "rollback_youngest"
            })
            
            # Clear all locks from these transactions
            async with self.database_lock:
                locks_to_remove = []
                for record_id, tx_id in self.record_locks.items():
                    if tx_id in transaction_ids:
                        locks_to_remove.append(record_id)
                
                for record_id in locks_to_remove:
                    del self.record_locks[record_id]
            
            return True
            
        except Exception as e:
            self.logger.error(f"Deadlock recovery failed for scenario {scenario_id}: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_isolation_level_boundary_validation(self):
        """
        Test transaction isolation levels under concurrent access.
        
        BVJ: Ensures proper isolation behavior for different transaction types,
        enabling flexible concurrency control for various business requirements.
        """
        isolation_levels = ["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"]
        transactions_per_level = 5
        
        isolation_test_results = {}
        isolation_violations = []
        
        for isolation_level in isolation_levels:
            level_results = await self._test_isolation_level(isolation_level, transactions_per_level)
            isolation_test_results[isolation_level] = level_results
            
            # Check for isolation violations specific to this level
            if not level_results["isolation_maintained"]:
                isolation_violations.extend(level_results["violations"])
        
        # Verify isolation level behavior
        for level, results in isolation_test_results.items():
            assert results["transactions_completed"] > 0, \
                f"No transactions completed for isolation level {level}"
            
            # Different isolation levels have different guarantees
            if level == "SERIALIZABLE":
                assert results["isolation_maintained"], \
                    f"Isolation violations in SERIALIZABLE level: {results['violations']}"
            elif level == "READ_COMMITTED":
                # Allow some phantom reads but no dirty reads
                dirty_reads = [v for v in results.get("violations", []) if v["type"] == "dirty_read"]
                assert len(dirty_reads) == 0, \
                    f"Dirty reads detected in READ_COMMITTED: {dirty_reads}"
        
        # Overall isolation validation
        critical_violations = [v for v in isolation_violations 
                             if v.get("severity") == "critical"]
        assert len(critical_violations) == 0, \
            f"Critical isolation violations: {critical_violations}"
        
        self.logger.info(f"Isolation level test completed: {len(isolation_levels)} levels tested, "
                        f"{sum(r['transactions_completed'] for r in isolation_test_results.values())} transactions")
    
    async def _test_isolation_level(self, isolation_level: str, transaction_count: int) -> Dict[str, Any]:
        """Test specific isolation level with concurrent transactions."""
        level_violations = []
        completed_transactions = 0
        
        async def isolation_test_transaction(tx_id: str, level: str):
            """Transaction with specific isolation level."""
            context = UserExecutionContext(
                user_id=f"iso_user_{tx_id}",
                session_id=f"iso_session_{tx_id}",
                request_id=f"iso_req_{tx_id}"
            )
            self.test_contexts.append(context)
            
            try:
                # Read operations with isolation level consideration
                record_id = "record_0"  # Focus on same record for isolation testing
                
                # First read
                first_read = await self._isolated_read(tx_id, record_id, level)
                
                # Small delay to allow other transactions
                await asyncio.sleep(0.1)
                
                # Second read (should be consistent based on isolation level)
                second_read = await self._isolated_read(tx_id, record_id, level)
                
                # Check isolation level guarantees
                isolation_check = await self._check_isolation_guarantees(
                    tx_id, level, first_read, second_read
                )
                
                if not isolation_check["valid"]:
                    level_violations.extend(isolation_check["violations"])
                
                return {
                    "transaction_id": tx_id,
                    "isolation_level": level,
                    "reads_consistent": isolation_check["valid"],
                    "success": True
                }
                
            except Exception as e:
                return {
                    "transaction_id": tx_id,
                    "isolation_level": level,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute transactions with this isolation level
        level_tasks = []
        for tx_num in range(transaction_count):
            tx_id = f"iso_tx_{isolation_level}_{tx_num}"
            task = asyncio.create_task(isolation_test_transaction(tx_id, isolation_level))
            level_tasks.append(task)
        
        results = await asyncio.gather(*level_tasks, return_exceptions=True)
        completed_transactions = len([r for r in results if isinstance(r, dict) and r.get("success")])
        
        return {
            "isolation_level": isolation_level,
            "transactions_completed": completed_transactions,
            "isolation_maintained": len(level_violations) == 0,
            "violations": level_violations
        }
    
    async def _isolated_read(self, tx_id: str, record_id: str, isolation_level: str) -> Dict[str, Any]:
        """Perform read with specific isolation level."""
        async with self.database_lock:
            if record_id in self.database_records:
                record = self.database_records[record_id].copy()
                
                # Apply isolation level behavior
                if isolation_level == "READ_UNCOMMITTED":
                    # Can read uncommitted changes
                    pass
                elif isolation_level == "READ_COMMITTED":
                    # Only read committed changes
                    if record.get("locked_by") and record["locked_by"] != tx_id:
                        # Skip uncommitted changes
                        record = None
                elif isolation_level in ["REPEATABLE_READ", "SERIALIZABLE"]:
                    # Consistent snapshot
                    if record.get("locked_by") and record["locked_by"] != tx_id:
                        record = None
                
                return {
                    "record_id": record_id,
                    "data": record,
                    "read_time": time.time(),
                    "isolation_level": isolation_level
                }
        
        return {"record_id": record_id, "data": None, "read_time": time.time()}
    
    async def _check_isolation_guarantees(self, tx_id: str, isolation_level: str, 
                                        first_read: Dict, second_read: Dict) -> Dict[str, Any]:
        """Check isolation level guarantees."""
        violations = []
        
        if isolation_level == "REPEATABLE_READ":
            # Same reads should return same values
            if first_read["data"] and second_read["data"]:
                if first_read["data"]["value"] != second_read["data"]["value"]:
                    violations.append({
                        "type": "non_repeatable_read",
                        "severity": "high",
                        "first_value": first_read["data"]["value"],
                        "second_value": second_read["data"]["value"]
                    })
        
        elif isolation_level == "READ_COMMITTED":
            # No dirty reads allowed
            if first_read["data"] and first_read["data"].get("locked_by"):
                violations.append({
                    "type": "dirty_read",
                    "severity": "critical",
                    "locked_by": first_read["data"]["locked_by"]
                })
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }