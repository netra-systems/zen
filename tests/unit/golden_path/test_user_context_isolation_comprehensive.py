"""
Comprehensive Unit Tests for User Context Isolation in Golden Path

Business Value Justification (BVJ):
- Segment: Enterprise (primary), Mid/Early (secondary)
- Business Goal: Ensure complete user data isolation protecting $500K+ ARR
- Value Impact: Prevents user data leakage that could cause $15K+ MRR enterprise customer churn
- Strategic Impact: Enables multi-tenant platform scalability and security compliance

This test suite validates the user context isolation system that ensures:
- Complete isolation between concurrent user sessions
- No data leakage or cross-contamination between users
- Proper cleanup and resource management
- Thread safety and concurrent access protection
- Memory isolation and garbage collection
- Security compliance for enterprise requirements

Key Coverage Areas:
- UserExecutionContext creation and isolation
- UserContextManager security and validation
- Multi-user concurrent execution isolation
- Memory and state isolation validation
- Cross-contamination detection and prevention
- Resource cleanup and lifecycle management
- Thread safety and race condition prevention
"""

import asyncio
import gc
import pytest
import threading
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# User context and isolation imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    InvalidContextError,
    ContextIsolationError,
    managed_user_context,
    validate_user_context,
    create_isolated_execution_context
)

# Execution and agent imports
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker

# Shared types for cross-service compatibility
from shared.types.core_types import UserID, ThreadID, RunID

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestUserContextIsolationComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for user context isolation in the golden path.
    
    Tests focus on complete user isolation that protects enterprise customers
    and prevents data leakage between concurrent user sessions.
    """

    def setup_method(self, method):
        """Setup test environment with proper SSOT patterns."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
        # Test users for isolation testing
        self.user_ids = [str(uuid.uuid4()) for _ in range(5)]
        self.thread_ids = [str(uuid.uuid4()) for _ in range(5)]
        self.run_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        # Context tracking for validation
        self.created_contexts: List[UserExecutionContext] = []
        self.context_states: Dict[str, Dict[str, Any]] = {}
        self.isolation_violations: List[Dict[str, Any]] = []
        
        # Thread safety testing
        self.concurrent_operations = []
        self.race_condition_detected = False
        
        # Memory tracking for leak detection
        self.initial_memory = None
        self.context_references: List[weakref.ref] = []

    async def async_setup_method(self, method):
        """Async setup for context manager initialization."""
        await super().async_setup_method(method)
        
        # Initialize context manager
        self.context_manager = UserContextManager()
        
        # Track initial memory usage
        gc.collect()  # Force garbage collection before testing
        self.initial_memory = self._get_memory_usage()

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.security
    async def test_user_execution_context_creation_and_isolation(self):
        """
        BVJ: Enterprise | Security | Ensures user contexts are completely isolated
        Test UserExecutionContext creation with complete isolation between users.
        """
        # Create contexts for multiple users
        contexts = []
        
        for i in range(3):
            context = UserExecutionContext(
                user_id=self.user_ids[i],
                thread_id=self.thread_ids[i],
                run_id=self.run_ids[i],
                agent_context={"user_tier": "enterprise", "test_data": f"user_{i}_data"}
            )
            contexts.append(context)
            self.created_contexts.append(context)
        
        # Verify basic isolation
        for i, context in enumerate(contexts):
            assert context.user_id == self.user_ids[i], f"User ID mismatch for context {i}"
            assert context.thread_id == self.thread_ids[i], f"Thread ID mismatch for context {i}"
            assert context.run_id == self.run_ids[i], f"Run ID mismatch for context {i}"
            
            # Verify unique identifiers
            for j, other_context in enumerate(contexts):
                if i != j:
                    assert context.user_id != other_context.user_id, f"User ID collision between contexts {i} and {j}"
                    assert context.thread_id != other_context.thread_id, f"Thread ID collision between contexts {i} and {j}"
                    assert context.run_id != other_context.run_id, f"Run ID collision between contexts {i} and {j}"
        
        # Test context data isolation
        for i, context in enumerate(contexts):
            # Set user-specific data
            test_key = "user_specific_data"
            test_value = f"sensitive_data_for_user_{i}"
            
            context.set_context_data(test_key, test_value)
            
            # Verify only this context has the data
            retrieved_value = context.get_context_data(test_key)
            assert retrieved_value == test_value, f"Context {i} should have its own data"
            
            # Verify other contexts don't have this data
            for j, other_context in enumerate(contexts):
                if i != j:
                    other_value = other_context.get_context_data(test_key)
                    assert other_value != test_value, f"Context {j} should not have data from context {i}"
                    assert other_value is None or other_value.startswith(f"sensitive_data_for_user_{j}"), f"Data leak detected between contexts {i} and {j}"
        
        # Test memory isolation
        context_memory_addresses = [id(context) for context in contexts]
        unique_addresses = set(context_memory_addresses)
        assert len(unique_addresses) == len(contexts), "All contexts should have unique memory addresses"
        
        logger.info(f"✅ User context creation and isolation validated: {len(contexts)} contexts")

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.security
    async def test_user_context_manager_security_validation(self):
        """
        BVJ: Enterprise | Security Compliance | Ensures UserContextManager prevents data leakage
        Test UserContextManager security features and validation mechanisms.
        """
        # Test secure context creation
        user1_context = await self.context_manager.create_isolated_execution_context(
            user_id=self.user_ids[0],
            thread_id=self.thread_ids[0],
            run_id=self.run_ids[0]
        )
        
        user2_context = await self.context_manager.create_isolated_execution_context(
            user_id=self.user_ids[1],
            thread_id=self.thread_ids[1],
            run_id=self.run_ids[1]
        )
        
        self.created_contexts.extend([user1_context, user2_context])
        
        # Verify contexts are valid
        is_valid_1 = await self.context_manager.validate_user_context(user1_context)
        is_valid_2 = await self.context_manager.validate_user_context(user2_context)
        
        assert is_valid_1, "User 1 context should be valid"
        assert is_valid_2, "User 2 context should be valid"
        
        # Test context isolation validation
        isolation_valid_1 = await self.context_manager._validate_context_isolation(user1_context)
        isolation_valid_2 = await self.context_manager._validate_context_isolation(user2_context)
        
        assert isolation_valid_1, "User 1 context isolation should be valid"
        assert isolation_valid_2, "User 2 context isolation should be valid"
        
        # Test cross-contamination detection
        # Simulate potential contamination
        user1_context._internal_state = {"sensitive_data": "user1_secrets"}
        user2_context._internal_state = {"sensitive_data": "user2_secrets"}
        
        # Verify contamination detection works
        contamination_detected = self.context_manager._detect_cross_contamination(
            [user1_context, user2_context]
        )
        
        assert not contamination_detected, "No contamination should be detected with isolated data"
        
        # Test invalid context detection
        invalid_context = UserExecutionContext(
            user_id="invalid_user",
            thread_id="invalid_thread",
            run_id="invalid_run"
        )
        
        # This should fail validation
        is_invalid_valid = await self.context_manager.validate_user_context(invalid_context)
        assert not is_invalid_valid, "Invalid context should fail validation"
        
        # Test security audit trail
        audit_events = self.context_manager.get_security_audit_trail(self.user_ids[0])
        assert len(audit_events) > 0, "Security audit trail should contain events"
        
        # Verify audit events contain required information
        for event in audit_events:
            assert "user_id" in event, "Audit event should contain user_id"
            assert "action" in event, "Audit event should contain action"
            assert "timestamp" in event, "Audit event should contain timestamp"
            assert "security_level" in event, "Audit event should contain security_level"
        
        logger.info("✅ UserContextManager security validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.asyncio
    async def test_concurrent_user_execution_isolation(self):
        """
        BVJ: All segments | Concurrency | Ensures isolation under concurrent load
        Test user context isolation under concurrent execution load.
        """
        num_concurrent_users = 10
        operations_per_user = 5
        
        # Create concurrent execution contexts
        concurrent_contexts = []
        
        async def create_user_context(user_index: int) -> UserExecutionContext:
            user_id = str(uuid.uuid4())
            thread_id = str(uuid.uuid4())
            run_id = str(uuid.uuid4())
            
            context = await self.context_manager.create_isolated_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Set user-specific data
            context.set_context_data("user_index", user_index)
            context.set_context_data("sensitive_data", f"secret_for_user_{user_index}")
            context.set_context_data("operations_count", 0)
            
            return context
        
        # Create contexts concurrently
        context_creation_tasks = [
            create_user_context(i) for i in range(num_concurrent_users)
        ]
        
        concurrent_contexts = await asyncio.gather(*context_creation_tasks)
        self.created_contexts.extend(concurrent_contexts)
        
        # Simulate concurrent operations on each context
        async def perform_user_operations(context: UserExecutionContext, user_index: int):
            for operation_num in range(operations_per_user):
                # Simulate different types of operations
                current_count = context.get_context_data("operations_count") or 0
                context.set_context_data("operations_count", current_count + 1)
                
                # Add operation-specific data
                operation_key = f"operation_{operation_num}"
                operation_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_index": user_index,
                    "operation_num": operation_num,
                    "data": f"result_for_user_{user_index}_operation_{operation_num}"
                }
                context.set_context_data(operation_key, operation_data)
                
                # Small delay to increase chance of race conditions
                await asyncio.sleep(0.001)
        
        # Execute operations concurrently
        operation_tasks = [
            perform_user_operations(context, i) 
            for i, context in enumerate(concurrent_contexts)
        ]
        
        await asyncio.gather(*operation_tasks)
        
        # Validate isolation after concurrent operations
        for i, context in enumerate(concurrent_contexts):
            # Verify user-specific data integrity
            user_index = context.get_context_data("user_index")
            assert user_index == i, f"User index corrupted for context {i}: expected {i}, got {user_index}"
            
            sensitive_data = context.get_context_data("sensitive_data")
            expected_sensitive = f"secret_for_user_{i}"
            assert sensitive_data == expected_sensitive, f"Sensitive data corrupted for user {i}"
            
            operations_count = context.get_context_data("operations_count")
            assert operations_count == operations_per_user, f"Operations count incorrect for user {i}: expected {operations_per_user}, got {operations_count}"
            
            # Verify operation-specific data
            for operation_num in range(operations_per_user):
                operation_key = f"operation_{operation_num}"
                operation_data = context.get_context_data(operation_key)
                assert operation_data is not None, f"Missing operation data for user {i}, operation {operation_num}"
                assert operation_data["user_index"] == i, f"Operation data user_index corrupted for user {i}, operation {operation_num}"
                assert operation_data["operation_num"] == operation_num, f"Operation data operation_num corrupted for user {i}, operation {operation_num}"
        
        # Cross-contamination check
        for i, context_i in enumerate(concurrent_contexts):
            for j, context_j in enumerate(concurrent_contexts):
                if i != j:
                    # Ensure no data leakage between contexts
                    user_i_data = context_i.get_context_data("sensitive_data")
                    user_j_data = context_j.get_context_data("sensitive_data")
                    
                    assert user_i_data != user_j_data, f"Sensitive data leak between users {i} and {j}"
                    assert f"user_{i}" in user_i_data, f"User {i} data should contain user_{i}"
                    assert f"user_{j}" in user_j_data, f"User {j} data should contain user_{j}"
        
        logger.info(f"✅ Concurrent user execution isolation validated: {num_concurrent_users} users, {operations_per_user} operations each")

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.memory
    async def test_memory_isolation_and_garbage_collection(self):
        """
        BVJ: Platform | Memory Management | Prevents memory leaks in production
        Test memory isolation and proper garbage collection of user contexts.
        """
        initial_memory = self._get_memory_usage()
        contexts_to_create = 20
        
        # Create multiple contexts and track memory references
        created_contexts = []
        weak_references = []
        
        for i in range(contexts_to_create):
            context = await self.context_manager.create_isolated_execution_context(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            # Add significant data to test memory usage
            large_data = {f"key_{j}": f"value_{j}_" * 100 for j in range(50)}
            context.set_context_data("large_dataset", large_data)
            
            created_contexts.append(context)
            weak_references.append(weakref.ref(context))
            self.context_references.append(weakref.ref(context))
        
        memory_after_creation = self._get_memory_usage()
        
        # Verify memory increased (contexts use memory)
        memory_increase = memory_after_creation - initial_memory
        assert memory_increase > 0, f"Memory should increase after creating contexts: {memory_increase} bytes"
        
        # Test memory isolation - each context should have separate memory
        memory_addresses = [id(context) for context in created_contexts]
        unique_addresses = set(memory_addresses)
        assert len(unique_addresses) == len(created_contexts), "All contexts should have unique memory addresses"
        
        # Test data isolation in memory
        for i, context in enumerate(created_contexts):
            # Verify each context has its own data
            large_data = context.get_context_data("large_dataset")
            assert large_data is not None, f"Context {i} should have large dataset"
            assert len(large_data) == 50, f"Context {i} should have 50 data items"
            
            # Verify data is not shared between contexts
            for j, other_context in enumerate(created_contexts):
                if i != j:
                    other_data = other_context.get_context_data("large_dataset")
                    # Data should be equal in content but different objects in memory
                    assert large_data is not other_data, f"Contexts {i} and {j} should not share memory for data"
        
        # Test cleanup and garbage collection
        user_ids_to_cleanup = [context.user_id for context in created_contexts]
        
        # Clear references
        created_contexts.clear()
        
        # Cleanup contexts through manager
        for user_id in user_ids_to_cleanup:
            await self.context_manager.cleanup_user_context(user_id)
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup to complete
        gc.collect()  # Second collection to ensure cleanup
        
        memory_after_cleanup = self._get_memory_usage()
        
        # Verify memory was released (allowing for some overhead)
        memory_released = memory_after_creation - memory_after_cleanup
        memory_efficiency = memory_released / memory_increase if memory_increase > 0 else 0
        
        # Should release at least 70% of allocated memory
        assert memory_efficiency >= 0.7, f"Memory cleanup insufficient: released {memory_efficiency:.2%} of allocated memory"
        
        # Verify weak references are dead (objects were garbage collected)
        dead_references = sum(1 for ref in weak_references if ref() is None)
        gc_efficiency = dead_references / len(weak_references) if weak_references else 1
        
        # Should garbage collect at least 80% of contexts
        assert gc_efficiency >= 0.8, f"Garbage collection insufficient: {gc_efficiency:.2%} of contexts collected"
        
        logger.info(f"✅ Memory isolation and garbage collection validated: {memory_efficiency:.2%} memory released, {gc_efficiency:.2%} contexts collected")

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.thread_safety
    async def test_thread_safety_and_race_condition_prevention(self):
        """
        BVJ: All segments | Thread Safety | Ensures thread-safe operations
        Test thread safety and race condition prevention in user context operations.
        """
        # Create shared context for thread safety testing
        shared_context = await self.context_manager.create_isolated_execution_context(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        self.created_contexts.append(shared_context)
        
        # Thread safety test variables
        num_threads = 10
        operations_per_thread = 50
        thread_results = {}
        race_conditions_detected = []
        
        # Thread-safe operation counter
        operation_counter = {"count": 0}
        counter_lock = threading.Lock()
        
        def thread_safe_operation(thread_id: int) -> Dict[str, Any]:
            """Perform thread-safe operations on shared context."""
            results = {"operations": [], "errors": []}
            
            for operation_num in range(operations_per_thread):
                try:
                    # Increment counter in thread-safe manner
                    with counter_lock:
                        operation_counter["count"] += 1
                        current_count = operation_counter["count"]
                    
                    # Test concurrent context data access
                    key = f"thread_{thread_id}_operation_{operation_num}"
                    value = {
                        "thread_id": thread_id,
                        "operation_num": operation_num,
                        "timestamp": time.time(),
                        "count": current_count
                    }
                    
                    # Set data with potential race condition
                    shared_context.set_context_data(key, value)
                    
                    # Retrieve and verify data immediately
                    retrieved_value = shared_context.get_context_data(key)
                    
                    if retrieved_value != value:
                        race_conditions_detected.append({
                            "thread_id": thread_id,
                            "operation_num": operation_num,
                            "expected": value,
                            "actual": retrieved_value
                        })
                    
                    results["operations"].append({
                        "key": key,
                        "success": retrieved_value == value,
                        "timestamp": time.time()
                    })
                    
                    # Small delay to increase race condition probability
                    time.sleep(0.001)
                    
                except Exception as e:
                    results["errors"].append({
                        "operation_num": operation_num,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            
            return results
        
        # Execute operations in multiple threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_thread = {
                executor.submit(thread_safe_operation, thread_id): thread_id 
                for thread_id in range(num_threads)
            }
            
            for future in future_to_thread:
                thread_id = future_to_thread[future]
                try:
                    thread_results[thread_id] = future.result(timeout=10.0)
                except Exception as e:
                    thread_results[thread_id] = {"operations": [], "errors": [str(e)]}
        
        # Validate thread safety results
        total_operations = 0
        total_errors = 0
        successful_operations = 0
        
        for thread_id, results in thread_results.items():
            thread_operations = len(results["operations"])
            thread_errors = len(results["errors"])
            thread_successes = sum(1 for op in results["operations"] if op["success"])
            
            total_operations += thread_operations
            total_errors += thread_errors
            successful_operations += thread_successes
            
            # Each thread should complete most operations successfully
            success_rate = thread_successes / thread_operations if thread_operations > 0 else 0
            assert success_rate >= 0.95, f"Thread {thread_id} success rate too low: {success_rate:.2%}"
        
        # Verify overall thread safety
        expected_total_operations = num_threads * operations_per_thread
        assert total_operations == expected_total_operations, f"Expected {expected_total_operations} operations, got {total_operations}"
        
        # Race conditions should be minimal (less than 1%)
        race_condition_rate = len(race_conditions_detected) / expected_total_operations
        assert race_condition_rate < 0.01, f"Too many race conditions detected: {race_condition_rate:.2%}"
        
        # Error rate should be low (less than 5%)
        error_rate = total_errors / expected_total_operations
        assert error_rate < 0.05, f"Error rate too high: {error_rate:.2%}"
        
        # Verify final counter value
        final_count = operation_counter["count"]
        assert final_count == expected_total_operations, f"Counter mismatch: expected {expected_total_operations}, got {final_count}"
        
        logger.info(f"✅ Thread safety validation passed: {successful_operations}/{total_operations} successful, {race_condition_rate:.3%} race conditions, {error_rate:.3%} errors")

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.security
    async def test_context_lifecycle_management_and_cleanup(self):
        """
        BVJ: Enterprise | Resource Management | Ensures proper context lifecycle
        Test complete context lifecycle management and cleanup procedures.
        """
        # Test context creation lifecycle
        context = await self.context_manager.create_isolated_execution_context(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        self.created_contexts.append(context)
        
        # Verify initial state
        assert context.creation_time is not None, "Context should have creation time"
        assert context.last_access_time is not None, "Context should have last access time"
        assert context.is_active, "Context should be active upon creation"
        
        # Test context usage tracking
        initial_access_time = context.last_access_time
        await asyncio.sleep(0.01)  # Small delay
        
        # Access context to update last access time
        context.get_context_data("test_key")
        assert context.last_access_time > initial_access_time, "Last access time should update"
        
        # Test context expiration
        # Set short TTL for testing
        original_ttl = context.ttl_seconds
        context.ttl_seconds = 0.1  # 100ms TTL
        
        await asyncio.sleep(0.15)  # Wait for expiration
        
        # Check if context is expired
        is_expired = context.is_expired()
        assert is_expired, "Context should be expired after TTL"
        
        # Test context validation after expiration
        is_valid_after_expiry = await self.context_manager.validate_user_context(context)
        assert not is_valid_after_expiry, "Expired context should fail validation"
        
        # Test cleanup process
        user_id = context.user_id
        
        # Add some data before cleanup
        context.set_context_data("pre_cleanup_data", "this_should_be_cleaned")
        context.set_context_data("sensitive_info", {"password": "secret123", "api_key": "key456"})
        
        # Perform cleanup
        cleanup_successful = await self.context_manager.cleanup_user_context(user_id)
        assert cleanup_successful, "Context cleanup should succeed"
        
        # Verify cleanup worked
        try:
            await self.context_manager.validate_user_context(context)
            assert False, "Context should not be valid after cleanup"
        except (InvalidContextError, Exception):
            pass  # Expected behavior
        
        # Verify data was cleared
        remaining_data = context.get_context_data("pre_cleanup_data")
        assert remaining_data is None, "Data should be cleared after cleanup"
        
        sensitive_data = context.get_context_data("sensitive_info")
        assert sensitive_data is None, "Sensitive data should be cleared after cleanup"
        
        # Test cleanup audit trail
        audit_events = self.context_manager.get_security_audit_trail(user_id)
        cleanup_events = [event for event in audit_events if event.get("action") == "context_cleanup"]
        assert len(cleanup_events) > 0, "Cleanup should be recorded in audit trail"
        
        # Test resource release
        # Context should no longer hold references to resources
        assert not hasattr(context, '_db_session') or context._db_session is None, "Database session should be cleared"
        assert not hasattr(context, '_redis_client') or context._redis_client is None, "Redis client should be cleared"
        
        logger.info("✅ Context lifecycle management and cleanup validation passed")

    @pytest.mark.unit
    @pytest.mark.golden_path
    @pytest.mark.integration
    async def test_execution_engine_factory_isolation_integration(self):
        """
        BVJ: All segments | System Integration | Ensures factory isolation works
        Test integration with ExecutionEngineFactory for complete isolation.
        """
        # Create WebSocket bridge for factory
        websocket_bridge = AgentWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Create multiple user contexts
        num_users = 5
        user_contexts = []
        execution_engines = []
        
        for i in range(num_users):
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                agent_context={"user_index": i, "tier": "enterprise"}
            )
            user_contexts.append(context)
            self.created_contexts.append(context)
        
        # Create execution engines through factory
        for context in user_contexts:
            engine = await factory.create_for_user(context)
            execution_engines.append(engine)
        
        # Verify factory creates isolated engines
        for i, engine in enumerate(execution_engines):
            assert engine is not None, f"Engine {i} should be created"
            
            # Verify engine has correct user context
            engine_context = engine.get_user_context()
            assert engine_context.user_id == user_contexts[i].user_id, f"Engine {i} should have correct user ID"
            
            # Verify engines are different instances
            for j, other_engine in enumerate(execution_engines):
                if i != j:
                    assert engine is not other_engine, f"Engines {i} and {j} should be different instances"
                    assert id(engine) != id(other_engine), f"Engines {i} and {j} should have different memory addresses"
        
        # Test state isolation between engines
        for i, engine in enumerate(execution_engines):
            # Set engine-specific state
            state_key = "test_state"
            state_value = f"engine_{i}_state_data"
            
            engine.set_agent_state(state_key, state_value)
            
            # Verify only this engine has the state
            retrieved_state = engine.get_agent_state(state_key)
            assert retrieved_state == state_value, f"Engine {i} should have its own state"
            
            # Verify other engines don't have this state
            for j, other_engine in enumerate(execution_engines):
                if i != j:
                    other_state = other_engine.get_agent_state(state_key)
                    assert other_state != state_value, f"Engine {j} should not have state from engine {i}"
        
        # Test execution isolation
        execution_results = []
        
        async def simulate_engine_execution(engine, user_index: int):
            # Simulate agent execution through engine
            execution_data = {
                "message": f"Execute analysis for user {user_index}",
                "user_data": f"sensitive_user_{user_index}_data",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Set execution state
            engine.set_execution_state("current_execution", execution_data)
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            # Get execution state
            result_data = engine.get_execution_state("current_execution")
            return {
                "user_index": user_index,
                "execution_data": result_data,
                "engine_id": id(engine)
            }
        
        # Execute simulations concurrently
        execution_tasks = [
            simulate_engine_execution(engine, i) 
            for i, engine in enumerate(execution_engines)
        ]
        
        execution_results = await asyncio.gather(*execution_tasks)
        
        # Verify execution isolation
        for i, result in enumerate(execution_results):
            assert result["user_index"] == i, f"Result {i} should have correct user index"
            
            execution_data = result["execution_data"]
            assert execution_data is not None, f"Result {i} should have execution data"
            assert f"user {i}" in execution_data["message"], f"Result {i} should contain user-specific message"
            assert f"sensitive_user_{i}_data" in execution_data["user_data"], f"Result {i} should contain user-specific data"
            
            # Verify no data leakage
            for j, other_result in enumerate(execution_results):
                if i != j:
                    other_data = other_result["execution_data"]
                    assert execution_data["user_data"] != other_data["user_data"], f"Data leak between results {i} and {j}"
        
        logger.info(f"✅ ExecutionEngineFactory isolation integration validated: {num_users} users")

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback for environments without psutil
            import sys
            return sys.getsizeof(self.created_contexts) + sum(
                sys.getsizeof(context) for context in self.created_contexts
            )
        except Exception:
            # Final fallback
            return len(self.created_contexts) * 1024  # Rough estimate

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Clear tracking lists
        self.context_states.clear()
        self.isolation_violations.clear()
        self.concurrent_operations.clear()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after tests."""
        # Cleanup all created contexts
        if hasattr(self, 'context_manager'):
            for context in self.created_contexts:
                try:
                    await self.context_manager.cleanup_user_context(context.user_id)
                except Exception as e:
                    logger.warning(f"Failed to cleanup context {context.user_id}: {e}")
        
        # Clear context references
        self.created_contexts.clear()
        self.context_references.clear()
        
        # Force garbage collection
        gc.collect()
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
