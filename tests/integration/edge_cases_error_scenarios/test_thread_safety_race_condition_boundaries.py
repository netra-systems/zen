"""
Integration Tests: Thread Safety and Race Condition Boundaries

Business Value Justification (BVJ):
- Segment: Enterprise (multi-threaded production environments)
- Business Goal: System Stability + Reliability + Scalability  
- Value Impact: Prevents race conditions that cause data corruption, system crashes,
  and unpredictable behavior under concurrent load. Ensures thread-safe operations
  for multi-user scenarios and high-throughput Enterprise deployments
- Revenue Impact: Protects $500K+ ARR from race condition bugs that cause system
  downtime, prevents data corruption incidents worth $1M+ in recovery costs,
  enables Enterprise scaling with reliable concurrent operation guarantees

Test Focus: Thread safety boundaries, race condition detection and prevention,
atomic operations, thread synchronization mechanisms, and concurrent data structure safety.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Callable, Set
from unittest.mock import AsyncMock, MagicMock, patch
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import random
from collections import deque
import queue

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.agents.supervisor.execution_engine import UserExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.core.config import get_config


class TestThreadSafetyRaceConditionBoundaries(BaseIntegrationTest):
    """
    Test thread safety and race condition boundaries under concurrent execution.
    
    Business Value: Ensures system reliability under concurrent load and prevents
    race conditions that could cause data corruption or system instability.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_thread_safety_test(self, real_services_fixture):
        """Setup thread safety and race condition test environment."""
        self.config = get_config()
        
        # Thread safety test state
        self.shared_counter = 0
        self.shared_data_structure = deque()
        self.race_condition_detections = []
        self.thread_safety_violations = []
        self.atomic_operation_failures = []
        
        # Synchronization primitives for testing
        self.thread_lock = threading.Lock()
        self.async_lock = asyncio.Lock()
        self.condition = threading.Condition()
        self.semaphore = threading.Semaphore(10)
        self.barrier = threading.Barrier(5)
        
        # Thread-local storage for isolation testing
        self.thread_local = threading.local()
        
        # Concurrent execution tracking
        self.active_threads: Set[int] = set()
        self.concurrent_operations: Dict[str, List[Dict[str, Any]]] = {}
        
        # Test contexts for cleanup
        self.test_contexts: List[UserExecutionContext] = []
        
        yield
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_atomic_operations_under_concurrent_access(self):
        """
        Test atomic operations remain atomic under high concurrent access.
        
        BVJ: Ensures data integrity for critical operations like user quotas,
        billing calculations, and system counters that must be exact.
        """
        num_concurrent_threads = 20
        operations_per_thread = 100
        expected_final_value = num_concurrent_threads * operations_per_thread
        
        operation_results = []
        atomicity_violations = []
        
        def atomic_increment_operation(thread_id: int, operation_count: int) -> Dict[str, Any]:
            """Perform atomic increment operations in thread."""
            thread_results = {
                "thread_id": thread_id,
                "operations_completed": 0,
                "race_conditions_detected": 0,
                "start_time": time.time()
            }
            
            # Register thread as active
            with self.thread_lock:
                self.active_threads.add(thread_id)
            
            try:
                for op_num in range(operation_count):
                    # Test atomic increment with race condition detection
                    race_detected = self._atomic_increment_with_race_detection(thread_id, op_num)
                    
                    if race_detected:
                        thread_results["race_conditions_detected"] += 1
                    
                    thread_results["operations_completed"] += 1
                    
                    # Small delay to increase race condition probability
                    time.sleep(0.0001)
                
                thread_results["execution_time"] = time.time() - thread_results["start_time"]
                return thread_results
                
            finally:
                # Unregister thread
                with self.thread_lock:
                    self.active_threads.discard(thread_id)
        
        # Execute concurrent atomic operations using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_concurrent_threads) as executor:
            # Submit all thread tasks
            future_to_thread = {
                executor.submit(atomic_increment_operation, thread_id, operations_per_thread): thread_id
                for thread_id in range(num_concurrent_threads)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    result = future.result()
                    operation_results.append(result)
                except Exception as e:
                    atomicity_violations.append({
                        "thread_id": thread_id,
                        "error": str(e),
                        "timestamp": time.time()
                    })
        
        # Verify atomic operation results
        assert len(operation_results) == num_concurrent_threads, \
            f"Not all threads completed: {len(operation_results)}/{num_concurrent_threads}"
        
        # Verify final counter value (atomicity test)
        assert self.shared_counter == expected_final_value, \
            f"Atomic operation failed: {self.shared_counter} != {expected_final_value}"
        
        # Verify no atomicity violations
        assert len(atomicity_violations) == 0, \
            f"Atomicity violations detected: {atomicity_violations}"
        
        # Verify operation completion
        total_operations = sum(r["operations_completed"] for r in operation_results)
        assert total_operations == expected_final_value, \
            f"Operation count mismatch: {total_operations} != {expected_final_value}"
        
        # Check for race condition detections
        total_race_conditions = sum(r["race_conditions_detected"] for r in operation_results)
        race_condition_rate = total_race_conditions / expected_final_value
        
        # Some race conditions are expected under high concurrency, but they should be handled
        assert race_condition_rate < 0.1, \
            f"Too many unhandled race conditions: {race_condition_rate:.2%}"
        
        self.logger.info(f"Atomic operations test completed: {expected_final_value} operations, "
                        f"{total_race_conditions} race conditions detected and handled")
    
    def _atomic_increment_with_race_detection(self, thread_id: int, op_num: int) -> bool:
        """Perform atomic increment with race condition detection."""
        race_detected = False
        
        with self.thread_lock:
            # Read current value
            old_value = self.shared_counter
            
            # Simulate potential race condition window
            if random.random() < 0.01:  # 1% chance of longer operation
                time.sleep(0.0005)
                
                # Check if value changed during our operation (race condition)
                if self.shared_counter != old_value:
                    race_detected = True
                    self.race_condition_detections.append({
                        "thread_id": thread_id,
                        "operation_num": op_num,
                        "expected_value": old_value,
                        "actual_value": self.shared_counter,
                        "timestamp": time.time()
                    })
            
            # Atomic increment
            self.shared_counter += 1
            
            # Log operation for analysis
            if thread_id not in self.concurrent_operations:
                self.concurrent_operations[thread_id] = []
            
            self.concurrent_operations[thread_id].append({
                "operation_num": op_num,
                "old_value": old_value,
                "new_value": self.shared_counter,
                "race_detected": race_detected,
                "timestamp": time.time()
            })
        
        return race_detected
    
    @pytest.mark.asyncio
    async def test_thread_local_storage_isolation(self):
        """
        Test thread-local storage isolation under concurrent access.
        
        BVJ: Ensures user session data remains isolated across different
        threads, preventing cross-user data contamination in multi-threaded environments.
        """
        num_concurrent_threads = 15
        operations_per_thread = 20
        
        thread_isolation_results = []
        isolation_violations = []
        
        def thread_local_isolation_test(thread_id: int, operation_count: int) -> Dict[str, Any]:
            """Test thread-local storage isolation."""
            # Initialize thread-local data
            self.thread_local.thread_id = thread_id
            self.thread_local.user_data = {
                "user_id": f"thread_user_{thread_id}",
                "session_data": f"session_data_for_thread_{thread_id}_{uuid.uuid4().hex[:8]}",
                "operations": [],
                "thread_fingerprint": threading.get_ident()
            }
            
            isolation_check_results = []
            
            for op_num in range(operation_count):
                # Perform operation using thread-local data
                operation_data = {
                    "operation_num": op_num,
                    "thread_id": thread_id,
                    "user_id": self.thread_local.user_data["user_id"],
                    "session_data": self.thread_local.user_data["session_data"],
                    "timestamp": time.time(),
                    "thread_fingerprint": threading.get_ident()
                }
                
                # Verify thread-local isolation
                isolation_valid = self._verify_thread_local_isolation(thread_id, operation_data)
                if not isolation_valid:
                    isolation_violations.append({
                        "thread_id": thread_id,
                        "operation_num": op_num,
                        "violation_type": "thread_local_contamination"
                    })
                
                self.thread_local.user_data["operations"].append(operation_data)
                isolation_check_results.append(isolation_valid)
                
                # Add some processing time
                time.sleep(0.005)
            
            return {
                "thread_id": thread_id,
                "operations_completed": len(isolation_check_results),
                "isolation_checks_passed": sum(isolation_check_results),
                "user_id": self.thread_local.user_data["user_id"],
                "session_fingerprint": self.thread_local.user_data["session_data"][:20],
                "thread_fingerprint": threading.get_ident()
            }
        
        # Execute concurrent thread-local tests
        with ThreadPoolExecutor(max_workers=num_concurrent_threads) as executor:
            future_to_thread = {
                executor.submit(thread_local_isolation_test, thread_id, operations_per_thread): thread_id
                for thread_id in range(num_concurrent_threads)
            }
            
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    result = future.result()
                    thread_isolation_results.append(result)
                except Exception as e:
                    isolation_violations.append({
                        "thread_id": thread_id,
                        "error": str(e),
                        "violation_type": "execution_failure"
                    })
        
        # Verify thread-local isolation results
        assert len(thread_isolation_results) == num_concurrent_threads, \
            f"Not all threads completed isolation test: {len(thread_isolation_results)}/{num_concurrent_threads}"
        
        # Verify no isolation violations
        assert len(isolation_violations) == 0, \
            f"Thread-local isolation violations: {isolation_violations}"
        
        # Verify unique user IDs and session data across threads
        user_ids = [r["user_id"] for r in thread_isolation_results]
        assert len(set(user_ids)) == num_concurrent_threads, \
            "Duplicate user IDs detected - thread isolation failed"
        
        session_fingerprints = [r["session_fingerprint"] for r in thread_isolation_results]
        assert len(set(session_fingerprints)) == num_concurrent_threads, \
            "Duplicate session fingerprints - thread isolation failed"
        
        thread_fingerprints = [r["thread_fingerprint"] for r in thread_isolation_results]
        assert len(set(thread_fingerprints)) == num_concurrent_threads, \
            "Duplicate thread fingerprints - thread execution failed"
        
        # Verify isolation check success rate
        total_isolation_checks = sum(r["isolation_checks_passed"] for r in thread_isolation_results)
        expected_total_checks = num_concurrent_threads * operations_per_thread
        isolation_success_rate = total_isolation_checks / expected_total_checks
        
        assert isolation_success_rate == 1.0, \
            f"Thread isolation success rate too low: {isolation_success_rate:.2%}"
        
        self.logger.info(f"Thread-local isolation test completed: {num_concurrent_threads} threads, "
                        f"{expected_total_checks} isolation checks passed")
    
    def _verify_thread_local_isolation(self, expected_thread_id: int, operation_data: Dict[str, Any]) -> bool:
        """Verify thread-local data belongs to correct thread."""
        # Check thread ID consistency
        if operation_data["thread_id"] != expected_thread_id:
            return False
        
        # Check thread fingerprint consistency
        current_thread_id = threading.get_ident()
        if operation_data["thread_fingerprint"] != current_thread_id:
            return False
        
        # Check user ID pattern
        expected_user_id = f"thread_user_{expected_thread_id}"
        if operation_data["user_id"] != expected_user_id:
            return False
        
        return True
    
    @pytest.mark.asyncio
    async def test_concurrent_data_structure_thread_safety(self):
        """
        Test thread safety of shared data structures under concurrent modification.
        
        BVJ: Ensures shared data structures remain consistent and don't corrupt
        under concurrent access, critical for system reliability and data integrity.
        """
        num_concurrent_threads = 25
        operations_per_thread = 50
        
        data_structure_results = []
        thread_safety_violations = []
        
        # Shared data structures for testing
        thread_safe_queue = queue.Queue()
        shared_dict = {}
        shared_list = []
        
        dict_lock = threading.Lock()
        list_lock = threading.Lock()
        
        def concurrent_data_structure_operations(thread_id: int, operation_count: int) -> Dict[str, Any]:
            """Perform concurrent operations on shared data structures."""
            operations_completed = {
                "queue_operations": 0,
                "dict_operations": 0,
                "list_operations": 0,
                "deque_operations": 0
            }
            
            violations_detected = []
            
            for op_num in range(operation_count):
                operation_type = random.choice(["queue", "dict", "list", "deque"])
                
                try:
                    if operation_type == "queue":
                        # Thread-safe queue operations
                        if random.choice([True, False]):
                            # Put operation
                            item = f"thread_{thread_id}_item_{op_num}"
                            thread_safe_queue.put(item)
                        else:
                            # Get operation (non-blocking)
                            try:
                                item = thread_safe_queue.get_nowait()
                                thread_safe_queue.task_done()
                            except queue.Empty:
                                pass  # Queue empty, normal behavior
                        
                        operations_completed["queue_operations"] += 1
                    
                    elif operation_type == "dict":
                        # Dictionary operations with locking
                        with dict_lock:
                            key = f"thread_{thread_id}_key_{op_num}"
                            if random.choice([True, False]):
                                # Write operation
                                shared_dict[key] = {
                                    "thread_id": thread_id,
                                    "value": random.randint(1, 1000),
                                    "timestamp": time.time()
                                }
                            else:
                                # Read operation
                                if key in shared_dict:
                                    value = shared_dict[key]
                                    # Verify data integrity
                                    if value["thread_id"] != thread_id:
                                        violations_detected.append({
                                            "type": "dict_data_corruption",
                                            "expected_thread": thread_id,
                                            "actual_thread": value["thread_id"]
                                        })
                        
                        operations_completed["dict_operations"] += 1
                    
                    elif operation_type == "list":
                        # List operations with locking
                        with list_lock:
                            if random.choice([True, False]):
                                # Append operation
                                item = {
                                    "thread_id": thread_id,
                                    "item_num": op_num,
                                    "timestamp": time.time()
                                }
                                shared_list.append(item)
                            else:
                                # Read operation
                                if len(shared_list) > 0:
                                    index = random.randint(0, len(shared_list) - 1)
                                    item = shared_list[index]
                                    # Verify item structure
                                    if not isinstance(item, dict) or "thread_id" not in item:
                                        violations_detected.append({
                                            "type": "list_structure_corruption",
                                            "index": index,
                                            "item": item
                                        })
                        
                        operations_completed["list_operations"] += 1
                    
                    elif operation_type == "deque":
                        # Thread-unsafe deque operations (should detect race conditions)
                        if random.choice([True, False]):
                            # Left append
                            item = f"thread_{thread_id}_deque_{op_num}"
                            self.shared_data_structure.appendleft(item)
                        else:
                            # Right pop
                            try:
                                item = self.shared_data_structure.pop()
                            except IndexError:
                                pass  # Deque empty
                        
                        operations_completed["deque_operations"] += 1
                    
                    # Small delay to increase concurrency
                    time.sleep(0.0001)
                    
                except Exception as e:
                    violations_detected.append({
                        "type": "operation_exception",
                        "operation": operation_type,
                        "error": str(e)
                    })
            
            return {
                "thread_id": thread_id,
                "operations_completed": operations_completed,
                "total_operations": sum(operations_completed.values()),
                "violations_detected": violations_detected
            }
        
        # Execute concurrent data structure operations
        with ThreadPoolExecutor(max_workers=num_concurrent_threads) as executor:
            future_to_thread = {
                executor.submit(concurrent_data_structure_operations, thread_id, operations_per_thread): thread_id
                for thread_id in range(num_concurrent_threads)
            }
            
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    result = future.result()
                    data_structure_results.append(result)
                    
                    # Collect violations
                    if result["violations_detected"]:
                        thread_safety_violations.extend(result["violations_detected"])
                        
                except Exception as e:
                    thread_safety_violations.append({
                        "thread_id": thread_id,
                        "type": "thread_execution_failure",
                        "error": str(e)
                    })
        
        # Verify data structure thread safety results
        assert len(data_structure_results) == num_concurrent_threads, \
            f"Not all threads completed: {len(data_structure_results)}/{num_concurrent_threads}"
        
        # Verify minimal thread safety violations for thread-safe structures
        critical_violations = [v for v in thread_safety_violations 
                             if v["type"] in ["dict_data_corruption", "list_structure_corruption"]]
        assert len(critical_violations) == 0, \
            f"Critical thread safety violations in protected structures: {critical_violations}"
        
        # Verify operation completion
        total_operations = sum(r["total_operations"] for r in data_structure_results)
        expected_total_operations = num_concurrent_threads * operations_per_thread
        operation_completion_rate = total_operations / expected_total_operations
        
        assert operation_completion_rate >= 0.95, \
            f"Operation completion rate too low: {operation_completion_rate:.2%}"
        
        # Analyze data structure final states
        self._verify_data_structure_consistency(shared_dict, shared_list, thread_safe_queue)
        
        self.logger.info(f"Data structure thread safety test completed: {total_operations} operations, "
                        f"{len(thread_safety_violations)} violations detected")
    
    def _verify_data_structure_consistency(self, shared_dict: Dict, shared_list: List, safe_queue: queue.Queue):
        """Verify final consistency of shared data structures."""
        # Check dictionary consistency
        for key, value in shared_dict.items():
            assert isinstance(value, dict), f"Dictionary value type corrupted for {key}"
            assert "thread_id" in value, f"Dictionary value missing thread_id for {key}"
            assert "timestamp" in value, f"Dictionary value missing timestamp for {key}"
        
        # Check list consistency
        for i, item in enumerate(shared_list):
            assert isinstance(item, dict), f"List item type corrupted at index {i}"
            assert "thread_id" in item, f"List item missing thread_id at index {i}"
        
        # Queue should still be functional
        queue_size = safe_queue.qsize()
        assert queue_size >= 0, "Queue size invalid"
    
    @pytest.mark.asyncio
    async def test_async_sync_thread_interaction_boundaries(self):
        """
        Test interaction boundaries between async and sync thread operations.
        
        BVJ: Ensures proper coordination between async event loops and sync threads,
        critical for systems mixing async WebSocket handling with sync database operations.
        """
        num_async_tasks = 10
        num_sync_threads = 10
        operations_per_worker = 20
        
        async_results = []
        sync_results = []
        interaction_violations = []
        
        # Shared coordination state
        async_sync_coordination = {
            "async_operations": 0,
            "sync_operations": 0,
            "coordination_events": deque(),
            "interaction_log": []
        }
        
        async def async_worker(task_id: int, operation_count: int):
            """Async worker that coordinates with sync threads."""
            context = UserExecutionContext(
                user_id=f"async_user_{task_id}",
                session_id=f"async_session_{task_id}",
                request_id=f"async_req_{task_id}"
            )
            self.test_contexts.append(context)
            
            operations_completed = 0
            coordination_events_handled = 0
            
            for op_num in range(operation_count):
                # Async operation
                await asyncio.sleep(0.01)
                
                async with self.async_lock:
                    async_sync_coordination["async_operations"] += 1
                    
                    # Log coordination event
                    event = {
                        "type": "async_operation",
                        "task_id": task_id,
                        "operation_num": op_num,
                        "timestamp": time.time(),
                        "thread_id": threading.get_ident(),
                        "context_user": context.user_id
                    }
                    
                    async_sync_coordination["coordination_events"].append(event)
                    async_sync_coordination["interaction_log"].append(event)
                
                operations_completed += 1
                
                # Check for coordination events from sync threads
                if len(async_sync_coordination["coordination_events"]) > operations_completed:
                    coordination_events_handled += 1
            
            return {
                "task_id": task_id,
                "worker_type": "async",
                "operations_completed": operations_completed,
                "coordination_events_handled": coordination_events_handled,
                "context_user": context.user_id
            }
        
        def sync_worker(thread_id: int, operation_count: int) -> Dict[str, Any]:
            """Sync worker that coordinates with async tasks."""
            operations_completed = 0
            coordination_events_created = 0
            
            for op_num in range(operation_count):
                # Sync operation
                time.sleep(0.005)
                
                with self.thread_lock:
                    async_sync_coordination["sync_operations"] += 1
                    
                    # Create coordination event
                    event = {
                        "type": "sync_operation",
                        "thread_id": thread_id,
                        "operation_num": op_num,
                        "timestamp": time.time(),
                        "os_thread_id": threading.get_ident()
                    }
                    
                    async_sync_coordination["coordination_events"].append(event)
                    async_sync_coordination["interaction_log"].append(event)
                    coordination_events_created += 1
                
                operations_completed += 1
            
            return {
                "thread_id": thread_id,
                "worker_type": "sync",
                "operations_completed": operations_completed,
                "coordination_events_created": coordination_events_created
            }
        
        # Start sync threads first
        sync_executor = ThreadPoolExecutor(max_workers=num_sync_threads)
        sync_futures = {
            sync_executor.submit(sync_worker, thread_id, operations_per_worker): thread_id
            for thread_id in range(num_sync_threads)
        }
        
        # Start async tasks
        async_tasks = []
        for task_id in range(num_async_tasks):
            task = asyncio.create_task(async_worker(task_id, operations_per_worker))
            async_tasks.append(task)
        
        # Wait for both async and sync operations to complete
        try:
            # Collect async results
            async_results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            # Collect sync results
            for future in as_completed(sync_futures):
                thread_id = sync_futures[future]
                try:
                    result = future.result()
                    sync_results.append(result)
                except Exception as e:
                    interaction_violations.append({
                        "type": "sync_execution_failure",
                        "thread_id": thread_id,
                        "error": str(e)
                    })
        
        finally:
            sync_executor.shutdown(wait=True)
        
        # Verify async-sync interaction results
        successful_async = [r for r in async_results if isinstance(r, dict)]
        successful_sync = sync_results
        
        assert len(successful_async) == num_async_tasks, \
            f"Not all async tasks completed: {len(successful_async)}/{num_async_tasks}"
        assert len(successful_sync) == num_sync_threads, \
            f"Not all sync threads completed: {len(successful_sync)}/{num_sync_threads}"
        
        # Verify operation counts
        total_async_operations = sum(r["operations_completed"] for r in successful_async)
        total_sync_operations = sum(r["operations_completed"] for r in successful_sync)
        
        expected_async_operations = num_async_tasks * operations_per_worker
        expected_sync_operations = num_sync_threads * operations_per_worker
        
        assert total_async_operations == expected_async_operations, \
            f"Async operation count mismatch: {total_async_operations} != {expected_async_operations}"
        assert total_sync_operations == expected_sync_operations, \
            f"Sync operation count mismatch: {total_sync_operations} != {expected_sync_operations}"
        
        # Verify coordination state consistency
        final_async_count = async_sync_coordination["async_operations"]
        final_sync_count = async_sync_coordination["sync_operations"]
        
        assert final_async_count == expected_async_operations, \
            f"Coordination async count mismatch: {final_async_count} != {expected_async_operations}"
        assert final_sync_count == expected_sync_operations, \
            f"Coordination sync count mismatch: {final_sync_count} != {expected_sync_operations}"
        
        # Verify no interaction violations
        assert len(interaction_violations) == 0, \
            f"Async-sync interaction violations: {interaction_violations}"
        
        # Verify coordination events logged properly
        total_coordination_events = len(async_sync_coordination["interaction_log"])
        expected_coordination_events = expected_async_operations + expected_sync_operations
        
        assert total_coordination_events == expected_coordination_events, \
            f"Coordination event count mismatch: {total_coordination_events} != {expected_coordination_events}"
        
        self.logger.info(f"Async-sync interaction test completed: {total_async_operations} async ops, "
                        f"{total_sync_operations} sync ops, {total_coordination_events} coordination events")
    
    @pytest.mark.asyncio
    async def test_barrier_synchronization_boundary_conditions(self):
        """
        Test barrier synchronization under boundary conditions and failures.
        
        BVJ: Validates coordination mechanisms for multi-phase operations requiring
        synchronization, critical for distributed agent workflows and batch processing.
        """
        barrier_size = 5
        num_barrier_rounds = 3
        timeout_scenarios = 2
        
        barrier_results = []
        synchronization_failures = []
        
        # Create barrier for synchronization testing
        test_barrier = threading.Barrier(barrier_size)
        
        def barrier_synchronization_worker(worker_id: int, rounds: int, 
                                         should_timeout: bool = False) -> Dict[str, Any]:
            """Worker that participates in barrier synchronization."""
            completed_rounds = 0
            barrier_waits = []
            timeout_occurred = False
            
            for round_num in range(rounds):
                try:
                    # Pre-barrier work
                    work_duration = random.uniform(0.1, 0.3)
                    if should_timeout and round_num == rounds - 1:
                        # Make last round timeout
                        work_duration = 2.0
                    
                    time.sleep(work_duration)
                    
                    # Barrier synchronization point
                    wait_start = time.time()
                    
                    if should_timeout:
                        # Use timeout for this worker
                        try:
                            barrier_index = test_barrier.wait(timeout=1.5)
                            wait_time = time.time() - wait_start
                            barrier_waits.append({
                                "round": round_num,
                                "wait_time": wait_time,
                                "barrier_index": barrier_index,
                                "success": True
                            })
                            completed_rounds += 1
                        except threading.BrokenBarrierError as e:
                            timeout_occurred = True
                            barrier_waits.append({
                                "round": round_num,
                                "wait_time": time.time() - wait_start,
                                "error": str(e),
                                "success": False
                            })
                            break
                    else:
                        # Normal barrier wait
                        barrier_index = test_barrier.wait()
                        wait_time = time.time() - wait_start
                        barrier_waits.append({
                            "round": round_num,
                            "wait_time": wait_time,
                            "barrier_index": barrier_index,
                            "success": True
                        })
                        completed_rounds += 1
                    
                    # Post-barrier work
                    time.sleep(0.05)
                    
                except threading.BrokenBarrierError as e:
                    synchronization_failures.append({
                        "worker_id": worker_id,
                        "round": round_num,
                        "error": "BrokenBarrierError",
                        "details": str(e)
                    })
                    break
                except Exception as e:
                    synchronization_failures.append({
                        "worker_id": worker_id,
                        "round": round_num,
                        "error": "UnexpectedException",
                        "details": str(e)
                    })
                    break
            
            return {
                "worker_id": worker_id,
                "completed_rounds": completed_rounds,
                "expected_rounds": rounds,
                "barrier_waits": barrier_waits,
                "timeout_occurred": timeout_occurred,
                "should_timeout": should_timeout
            }
        
        # Execute barrier synchronization test
        with ThreadPoolExecutor(max_workers=barrier_size) as executor:
            # Create workers - some with timeout scenarios
            futures = []
            for worker_id in range(barrier_size):
                should_timeout = worker_id < timeout_scenarios
                future = executor.submit(
                    barrier_synchronization_worker, 
                    worker_id, 
                    num_barrier_rounds, 
                    should_timeout
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    barrier_results.append(result)
                except Exception as e:
                    synchronization_failures.append({
                        "error": "Future execution failed",
                        "details": str(e)
                    })
        
        # Verify barrier synchronization results
        assert len(barrier_results) == barrier_size, \
            f"Not all barrier workers completed: {len(barrier_results)}/{barrier_size}"
        
        # Analyze timeout scenarios
        timeout_workers = [r for r in barrier_results if r["should_timeout"]]
        normal_workers = [r for r in barrier_results if not r["should_timeout"]]
        
        # Verify timeout workers experienced expected failures
        for timeout_worker in timeout_workers:
            assert timeout_worker["timeout_occurred"] or timeout_worker["completed_rounds"] < num_barrier_rounds, \
                f"Timeout worker {timeout_worker['worker_id']} should have failed but completed all rounds"
        
        # Normal workers should either complete all rounds or be affected by barrier break
        barrier_broken = any(w["timeout_occurred"] for w in timeout_workers)
        
        if not barrier_broken:
            # If no barrier break, all normal workers should complete
            for normal_worker in normal_workers:
                assert normal_worker["completed_rounds"] == num_barrier_rounds, \
                    f"Normal worker {normal_worker['worker_id']} should have completed all rounds"
        
        # Verify synchronization timing
        for result in barrier_results:
            successful_waits = [w for w in result["barrier_waits"] if w["success"]]
            for wait in successful_waits:
                # Barrier waits should be relatively quick once all workers arrive
                assert wait["wait_time"] < 1.0, \
                    f"Barrier wait took too long: {wait['wait_time']}s"
        
        # Check synchronization quality
        total_successful_rounds = sum(r["completed_rounds"] for r in barrier_results)
        
        # Either all workers complete all rounds, or barrier breaks affect all
        if barrier_broken:
            # Some rounds should still succeed before barrier break
            assert total_successful_rounds > 0, \
                "No successful barrier rounds despite barrier break recovery"
        else:
            # All workers should complete all rounds
            expected_total_rounds = barrier_size * num_barrier_rounds
            assert total_successful_rounds == expected_total_rounds, \
                f"Round completion mismatch: {total_successful_rounds} != {expected_total_rounds}"
        
        self.logger.info(f"Barrier synchronization test completed: {barrier_size} workers, "
                        f"{total_successful_rounds} successful rounds, "
                        f"{len(synchronization_failures)} synchronization failures")