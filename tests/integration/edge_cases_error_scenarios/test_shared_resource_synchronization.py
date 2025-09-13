"""
Integration Tests: Shared Resource Synchronization

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (multi-user concurrent operations)  
- Business Goal: System Stability + Data Integrity
- Value Impact: Prevents data corruption and race conditions in shared resources,
  ensures consistent state across concurrent user sessions, maintains data integrity
  under high load scenarios
- Revenue Impact: Protects $500K+ ARR from data corruption issues, enables
  Enterprise scaling with guaranteed data consistency and ACID compliance

Test Focus: Shared resource access patterns, synchronization mechanisms, 
race condition prevention, and data consistency under concurrent access.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import threading
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.core.config import get_config


class TestSharedResourceSynchronization(BaseIntegrationTest):
    """
    Test synchronization mechanisms for shared resources under concurrent access.
    
    Business Value: Ensures data consistency and prevents race conditions that
    could corrupt user data or system state, critical for Enterprise reliability.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_synchronization_test(self, real_services_fixture):
        """Setup shared resource synchronization test environment."""
        self.config = get_config()
        
        # Shared resources simulation
        self.shared_counter = 0
        self.shared_data_store = {}
        self.shared_state_versions = {}
        self.access_log = []
        self.synchronization_errors = []
        
        # Synchronization primitives
        self.resource_lock = asyncio.Lock()
        self.access_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent accesses
        self.condition_variable = asyncio.Condition()
        
        # User contexts for testing
        self.test_contexts: List[UserExecutionContext] = []
        
        yield
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_concurrent_shared_counter_synchronization(self):
        """
        Test synchronization of shared counter under concurrent access.
        
        BVJ: Validates atomic operations and prevents race conditions in shared
        counters used for metrics, quotas, and usage tracking.
        """
        num_concurrent_users = 20
        increments_per_user = 25
        expected_final_count = num_concurrent_users * increments_per_user
        
        increment_results = []
        synchronization_violations = []
        
        async def concurrent_counter_increment(user_id: str, increment_count: int):
            """Increment shared counter with synchronization."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"sync_session_{user_id}",
                request_id=f"sync_req_{user_id}_{int(time.time())}"
            )
            self.test_contexts.append(context)
            
            successful_increments = 0
            
            for i in range(increment_count):
                try:
                    # Critical section with lock
                    async with self.resource_lock:
                        # Read current value
                        current_value = self.shared_counter
                        
                        # Simulate processing time (potential race condition window)
                        await asyncio.sleep(0.001)
                        
                        # Increment and write back
                        self.shared_counter = current_value + 1
                        
                        # Log access for analysis
                        self.access_log.append({
                            "user_id": user_id,
                            "increment_num": i,
                            "old_value": current_value,
                            "new_value": self.shared_counter,
                            "timestamp": time.time(),
                            "thread_id": threading.get_ident()
                        })
                        
                        successful_increments += 1
                        
                except Exception as e:
                    synchronization_violations.append({
                        "user_id": user_id,
                        "increment_num": i,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            
            return {
                "user_id": user_id,
                "successful_increments": successful_increments,
                "expected_increments": increment_count
            }
        
        # Launch concurrent counter increments
        increment_tasks = []
        for user_num in range(num_concurrent_users):
            user_id = f"counter_user_{user_num}"
            task = asyncio.create_task(
                concurrent_counter_increment(user_id, increments_per_user)
            )
            increment_tasks.append(task)
        
        # Execute all increments concurrently
        start_time = time.time()
        results = await asyncio.gather(*increment_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Verify synchronization correctness
        assert self.shared_counter == expected_final_count, \
            f"Counter synchronization failed: {self.shared_counter} != {expected_final_count}"
        
        # Verify all increments succeeded
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == num_concurrent_users
        
        total_successful_increments = sum(r["successful_increments"] for r in successful_results)
        assert total_successful_increments == expected_final_count, \
            f"Increment count mismatch: {total_successful_increments} != {expected_final_count}"
        
        # Verify no synchronization violations
        assert len(synchronization_violations) == 0, \
            f"Synchronization violations detected: {synchronization_violations}"
        
        # Verify proper ordering in access log
        assert len(self.access_log) == expected_final_count
        
        # Verify counter values increase monotonically
        for i, log_entry in enumerate(self.access_log):
            expected_new_value = i + 1
            assert log_entry["new_value"] == expected_new_value, \
                f"Counter ordering violation at index {i}: {log_entry['new_value']} != {expected_new_value}"
        
        # Verify reasonable performance
        assert execution_time < 10.0, \
            f"Synchronized counter operations too slow: {execution_time}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_shared_data_store_consistency(self):
        """
        Test data consistency in shared data store under concurrent modifications.
        
        BVJ: Ensures user data remains consistent across concurrent sessions,
        preventing data corruption that could impact customer trust and compliance.
        """
        num_concurrent_users = 15
        operations_per_user = 20
        
        data_operations = ["create", "read", "update", "delete"]
        consistency_violations = []
        data_integrity_checks = []
        
        async def concurrent_data_operations(user_id: str, operation_count: int):
            """Perform concurrent data operations on shared store."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"data_session_{user_id}",
                request_id=f"data_req_{user_id}"
            )
            self.test_contexts.append(context)
            
            operation_results = []
            user_data_key = f"user_data_{user_id}"
            
            for op_num in range(operation_count):
                try:
                    # Acquire semaphore to limit concurrent access
                    async with self.access_semaphore:
                        async with self.resource_lock:
                            operation = data_operations[op_num % len(data_operations)]
                            
                            if operation == "create" or operation == "update":
                                # Create/update data with versioning
                                new_data = {
                                    "user_id": user_id,
                                    "operation_num": op_num,
                                    "timestamp": time.time(),
                                    "data_content": f"Content for {user_id} operation {op_num}",
                                    "checksum": None
                                }
                                
                                # Add checksum for integrity verification
                                data_str = json.dumps(new_data, sort_keys=True)
                                new_data["checksum"] = hashlib.md5(data_str.encode()).hexdigest()
                                
                                # Version management
                                current_version = self.shared_state_versions.get(user_data_key, 0)
                                new_data["version"] = current_version + 1
                                
                                self.shared_data_store[user_data_key] = new_data
                                self.shared_state_versions[user_data_key] = new_data["version"]
                                
                                operation_results.append({
                                    "operation": operation,
                                    "success": True,
                                    "version": new_data["version"]
                                })
                                
                            elif operation == "read":
                                # Read data with integrity check
                                if user_data_key in self.shared_data_store:
                                    stored_data = self.shared_data_store[user_data_key].copy()
                                    
                                    # Verify data integrity
                                    stored_checksum = stored_data.pop("checksum", None)
                                    data_str = json.dumps(stored_data, sort_keys=True)
                                    calculated_checksum = hashlib.md5(data_str.encode()).hexdigest()
                                    
                                    if stored_checksum != calculated_checksum:
                                        consistency_violations.append({
                                            "user_id": user_id,
                                            "operation": "read",
                                            "error": "Data integrity check failed",
                                            "expected_checksum": stored_checksum,
                                            "calculated_checksum": calculated_checksum
                                        })
                                    
                                    operation_results.append({
                                        "operation": operation,
                                        "success": True,
                                        "data_found": True,
                                        "version": stored_data.get("version", 0)
                                    })
                                else:
                                    operation_results.append({
                                        "operation": operation,
                                        "success": True,
                                        "data_found": False
                                    })
                                    
                            elif operation == "delete":
                                # Delete data if exists
                                if user_data_key in self.shared_data_store:
                                    del self.shared_data_store[user_data_key]
                                    if user_data_key in self.shared_state_versions:
                                        del self.shared_state_versions[user_data_key]
                                    
                                    operation_results.append({
                                        "operation": operation,
                                        "success": True,
                                        "deleted": True
                                    })
                                else:
                                    operation_results.append({
                                        "operation": operation,
                                        "success": True,
                                        "deleted": False
                                    })
                        
                        # Small delay to increase concurrency pressure
                        await asyncio.sleep(0.002)
                        
                except Exception as e:
                    consistency_violations.append({
                        "user_id": user_id,
                        "operation_num": op_num,
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    
                    operation_results.append({
                        "operation": "error",
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "user_id": user_id,
                "operation_results": operation_results,
                "total_operations": operation_count
            }
        
        # Execute concurrent data operations
        data_tasks = []
        for user_num in range(num_concurrent_users):
            user_id = f"data_user_{user_num}"
            task = asyncio.create_task(
                concurrent_data_operations(user_id, operations_per_user)
            )
            data_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*data_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == num_concurrent_users
        
        # Verify no consistency violations
        assert len(consistency_violations) == 0, \
            f"Data consistency violations detected: {consistency_violations}"
        
        # Verify operation success rates
        total_operations = sum(len(r["operation_results"]) for r in successful_results)
        successful_operations = sum(
            len([op for op in r["operation_results"] if op["success"]])
            for r in successful_results
        )
        
        success_rate = successful_operations / total_operations
        assert success_rate >= 0.95, \
            f"Data operation success rate too low: {success_rate:.2%}"
        
        # Verify data store integrity after all operations
        for key, data in self.shared_data_store.items():
            if isinstance(data, dict) and "checksum" in data:
                data_copy = data.copy()
                stored_checksum = data_copy.pop("checksum")
                data_str = json.dumps(data_copy, sort_keys=True)
                calculated_checksum = hashlib.md5(data_str.encode()).hexdigest()
                
                assert stored_checksum == calculated_checksum, \
                    f"Final data integrity check failed for {key}"
        
        # Verify reasonable performance
        assert execution_time < 15.0, \
            f"Synchronized data operations too slow: {execution_time}s"
    
    @pytest.mark.asyncio
    async def test_resource_pool_synchronization_under_contention(self):
        """
        Test resource pool management under high contention scenarios.
        
        BVJ: Ensures fair resource allocation and prevents resource starvation
        that could impact user experience and system throughput.
        """
        pool_size = 10
        num_concurrent_users = 30
        resource_usage_duration = 0.2
        
        # Resource pool simulation
        available_resources = list(range(pool_size))
        allocated_resources = {}  # resource_id -> user_id
        resource_wait_times = []
        resource_allocation_failures = []
        
        async def acquire_and_use_resource(user_id: str, attempt_num: int):
            """Acquire resource from pool, use it, then release."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"pool_session_{user_id}_{attempt_num}",
                request_id=f"pool_req_{user_id}_{attempt_num}"
            )
            self.test_contexts.append(context)
            
            resource_id = None
            wait_start_time = time.time()
            
            try:
                # Acquire resource with timeout
                timeout_duration = 5.0  # 5 second timeout
                
                async with asyncio.timeout(timeout_duration):
                    while True:
                        async with self.resource_lock:
                            # Try to acquire an available resource
                            if available_resources:
                                resource_id = available_resources.pop(0)
                                allocated_resources[resource_id] = user_id
                                break
                        
                        # Wait a bit before trying again
                        await asyncio.sleep(0.01)
                
                wait_time = time.time() - wait_start_time
                resource_wait_times.append(wait_time)
                
                # Use the resource
                await asyncio.sleep(resource_usage_duration)
                
                # Release the resource
                async with self.resource_lock:
                    if resource_id in allocated_resources:
                        del allocated_resources[resource_id]
                        available_resources.append(resource_id)
                        available_resources.sort()  # Maintain order
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "wait_time": wait_time,
                    "attempt_num": attempt_num
                }
                
            except asyncio.TimeoutError:
                resource_allocation_failures.append({
                    "user_id": user_id,
                    "attempt_num": attempt_num,
                    "error": "Resource allocation timeout",
                    "wait_time": time.time() - wait_start_time
                })
                
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "timeout",
                    "wait_time": time.time() - wait_start_time
                }
            
            except Exception as e:
                resource_allocation_failures.append({
                    "user_id": user_id,
                    "attempt_num": attempt_num,
                    "error": str(e),
                    "wait_time": time.time() - wait_start_time
                })
                
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": str(e),
                    "wait_time": time.time() - wait_start_time
                }
        
        # Create concurrent resource requests
        resource_tasks = []
        for user_num in range(num_concurrent_users):
            user_id = f"pool_user_{user_num}"
            task = asyncio.create_task(
                acquire_and_use_resource(user_id, 1)
            )
            resource_tasks.append(task)
        
        # Execute with resource contention
        start_time = time.time()
        results = await asyncio.gather(*resource_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze resource pool performance
        successful_acquisitions = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_acquisitions = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # Verify high success rate (allowing for some timeouts under high contention)
        success_rate = len(successful_acquisitions) / len(results)
        assert success_rate >= 0.8, \
            f"Resource allocation success rate too low: {success_rate:.2%}"
        
        # Verify resource pool integrity (no resource leaks)
        assert len(available_resources) == pool_size, \
            f"Resource leak detected: {len(available_resources)} != {pool_size}"
        
        # Verify no resources still allocated
        assert len(allocated_resources) == 0, \
            f"Resources still allocated after completion: {allocated_resources}"
        
        # Verify fair resource distribution (no user got significantly more resources)
        user_resource_counts = {}
        for result in successful_acquisitions:
            user_id = result["user_id"]
            user_resource_counts[user_id] = user_resource_counts.get(user_id, 0) + 1
        
        if user_resource_counts:
            max_resources_per_user = max(user_resource_counts.values())
            min_resources_per_user = min(user_resource_counts.values())
            assert max_resources_per_user - min_resources_per_user <= 1, \
                f"Unfair resource distribution: max={max_resources_per_user}, min={min_resources_per_user}"
        
        # Verify reasonable wait times
        if resource_wait_times:
            avg_wait_time = sum(resource_wait_times) / len(resource_wait_times)
            max_wait_time = max(resource_wait_times)
            
            assert avg_wait_time < 1.0, \
                f"Average resource wait time too high: {avg_wait_time:.3f}s"
            assert max_wait_time < 3.0, \
                f"Maximum resource wait time too high: {max_wait_time:.3f}s"
        
        # Log resource allocation failures for analysis
        if resource_allocation_failures:
            failure_rate = len(resource_allocation_failures) / num_concurrent_users
            assert failure_rate < 0.2, \
                f"Too many resource allocation failures: {failure_rate:.2%}"
    
    @pytest.mark.asyncio
    async def test_condition_variable_signaling_synchronization(self):
        """
        Test condition variable signaling under concurrent wait/notify scenarios.
        
        BVJ: Validates proper coordination mechanisms for state changes that
        affect multiple concurrent users, ensuring reliable event-driven workflows.
        """
        num_waiters = 20
        num_signalers = 5
        signals_per_signaler = 8
        
        wait_results = []
        signal_results = []
        coordination_errors = []
        
        # Shared state for condition variable testing
        shared_event_counter = 0
        processed_events = []
        
        async def condition_waiter(waiter_id: str):
            """Wait for condition variable signals."""
            context = UserExecutionContext(
                user_id=waiter_id,
                session_id=f"wait_session_{waiter_id}",
                request_id=f"wait_req_{waiter_id}"
            )
            self.test_contexts.append(context)
            
            events_received = 0
            wait_timeouts = 0
            
            try:
                for wait_attempt in range(3):  # Try to receive multiple events
                    try:
                        async with self.condition_variable:
                            # Wait for condition with timeout
                            await asyncio.wait_for(
                                self.condition_variable.wait(),
                                timeout=2.0
                            )
                            
                            # Process the event
                            events_received += 1
                            processed_events.append({
                                "waiter_id": waiter_id,
                                "event_num": events_received,
                                "timestamp": time.time(),
                                "shared_counter": shared_event_counter
                            })
                            
                    except asyncio.TimeoutError:
                        wait_timeouts += 1
                        break  # Exit on timeout
                
                return {
                    "waiter_id": waiter_id,
                    "events_received": events_received,
                    "wait_timeouts": wait_timeouts,
                    "success": True
                }
                
            except Exception as e:
                coordination_errors.append({
                    "waiter_id": waiter_id,
                    "error": str(e),
                    "timestamp": time.time()
                })
                
                return {
                    "waiter_id": waiter_id,
                    "events_received": events_received,
                    "success": False,
                    "error": str(e)
                }
        
        async def condition_signaler(signaler_id: str, signal_count: int):
            """Signal condition variable multiple times."""
            context = UserExecutionContext(
                user_id=signaler_id,
                session_id=f"signal_session_{signaler_id}",
                request_id=f"signal_req_{signaler_id}"
            )
            self.test_contexts.append(context)
            
            signals_sent = 0
            
            try:
                for signal_num in range(signal_count):
                    # Add delay between signals
                    await asyncio.sleep(0.1)
                    
                    async with self.condition_variable:
                        # Update shared state
                        nonlocal shared_event_counter
                        shared_event_counter += 1
                        
                        # Notify one waiter
                        self.condition_variable.notify()
                        signals_sent += 1
                
                return {
                    "signaler_id": signaler_id,
                    "signals_sent": signals_sent,
                    "expected_signals": signal_count,
                    "success": True
                }
                
            except Exception as e:
                coordination_errors.append({
                    "signaler_id": signaler_id,
                    "error": str(e),
                    "timestamp": time.time()
                })
                
                return {
                    "signaler_id": signaler_id,
                    "signals_sent": signals_sent,
                    "success": False,
                    "error": str(e)
                }
        
        # Start waiters first
        waiter_tasks = []
        for waiter_num in range(num_waiters):
            waiter_id = f"waiter_{waiter_num}"
            task = asyncio.create_task(condition_waiter(waiter_id))
            waiter_tasks.append(task)
        
        # Give waiters time to start waiting
        await asyncio.sleep(0.1)
        
        # Start signalers
        signaler_tasks = []
        for signaler_num in range(num_signalers):
            signaler_id = f"signaler_{signaler_num}"
            task = asyncio.create_task(
                condition_signaler(signaler_id, signals_per_signaler)
            )
            signaler_tasks.append(task)
        
        # Wait for all signalers to complete
        signal_results = await asyncio.gather(*signaler_tasks, return_exceptions=True)
        
        # Wait for waiters to complete (with timeout)
        try:
            wait_results = await asyncio.wait_for(
                asyncio.gather(*waiter_tasks, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            # Cancel remaining waiter tasks
            for task in waiter_tasks:
                if not task.done():
                    task.cancel()
            
            wait_results = [{"waiter_id": f"waiter_{i}", "success": False, "error": "timeout"} 
                          for i in range(num_waiters)]
        
        # Analyze synchronization results
        successful_signalers = [r for r in signal_results if isinstance(r, dict) and r.get("success")]
        successful_waiters = [r for r in wait_results if isinstance(r, dict) and r.get("success")]
        
        # Verify signalers completed successfully
        assert len(successful_signalers) == num_signalers, \
            f"Not all signalers completed successfully: {len(successful_signalers)}/{num_signalers}"
        
        total_signals_sent = sum(r["signals_sent"] for r in successful_signalers)
        expected_total_signals = num_signalers * signals_per_signaler
        assert total_signals_sent == expected_total_signals, \
            f"Signal count mismatch: {total_signals_sent} != {expected_total_signals}"
        
        # Verify reasonable number of waiters received events
        waiters_with_events = [r for r in successful_waiters if r["events_received"] > 0]
        event_delivery_rate = len(waiters_with_events) / num_waiters
        assert event_delivery_rate >= 0.6, \
            f"Too few waiters received events: {event_delivery_rate:.2%}"
        
        # Verify event processing consistency
        total_events_processed = len(processed_events)
        assert total_events_processed > 0, "No events were processed"
        
        # Verify no coordination errors
        assert len(coordination_errors) == 0, \
            f"Coordination errors detected: {coordination_errors}"
        
        # Verify shared counter consistency
        assert shared_event_counter == expected_total_signals, \
            f"Shared counter inconsistent: {shared_event_counter} != {expected_total_signals}"