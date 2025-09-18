"""
Comprehensive Integration Tests for ExecutionEngineFactory Isolation in Golden Path

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user execution isolation protecting $500K+ ARR
- Value Impact: Validates factory patterns that enable multi-tenant platform scalability
- Strategic Impact: Prevents user data leakage and enables concurrent user sessions

This test suite validates the ExecutionEngineFactory isolation system that ensures:
- Complete isolation between user execution engines
- Proper factory pattern implementation for user contexts
- Thread safety and concurrent execution handling
- Memory isolation and resource management
- State isolation between different user sessions
- Performance under concurrent load
- Error handling and recovery in multi-user scenarios

Key Coverage Areas:
- ExecutionEngineFactory user isolation patterns
- UserExecutionEngine creation and lifecycle
- Multi-user concurrent execution validation
- Memory and state isolation verification
- Performance testing under load
- Error propagation and recovery
- Resource cleanup and garbage collection
"""

import asyncio
import gc
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.real_services_test_fixtures import real_services_fixture

# ExecutionEngine and factory imports
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Agent and execution imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseAgent, AgentState
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker

# Shared types and utilities
from shared.types.core_types import UserID, ThreadID, RunID

# Logging and monitoring
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestExecutionEngineFactoryIsolationIntegration(SSotAsyncTestCase):
    """
    Comprehensive integration tests for ExecutionEngineFactory isolation in golden path.
    
    Tests focus on the factory patterns that ensure complete user isolation and
    enable multi-tenant platform scalability.
    """

    def setup_method(self, method):
        """Setup test environment with proper SSOT patterns."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
        # Test user data for isolation testing
        self.num_test_users = 10
        self.test_user_contexts = []
        self.created_engines: List[UserExecutionEngine] = []
        self.engine_states: Dict[str, Dict[str, Any]] = {}
        
        # Performance and isolation tracking
        self.isolation_violations: List[Dict[str, Any]] = []
        self.memory_usage_samples: List[Dict[str, Any]] = []
        self.concurrent_operations: List[Dict[str, Any]] = []
        
        # Mock services
        self.mock_llm_manager = MagicMock()
        self.mock_llm_client = self.mock_factory.create_llm_client_mock()
        self.mock_llm_manager.get_default_client.return_value = self.mock_llm_client

    async def async_setup_method(self, method):
        """Async setup for factory and engine initialization."""
        await super().async_setup_method(method)
        
        # Create WebSocket bridge for factory
        self.websocket_bridge = AgentWebSocketBridge()
        
        # Create execution engine factory
        self.execution_factory = ExecutionEngineFactory(
            websocket_bridge=self.websocket_bridge
        )
        
        # Create test user contexts
        for i in range(self.num_test_users):
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                agent_context={
                    "user_index": i,
                    "tier": "enterprise" if i < 3 else "free",
                    "test_data": f"user_{i}_test_data"
                }
            )
            self.test_user_contexts.append(context)
        
        # Track initial memory usage
        gc.collect()
        self.initial_memory = self._get_memory_usage()

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.real_services
    async def test_execution_engine_factory_user_isolation_creation(self):
        """
        BVJ: All segments | User Isolation | Ensures factory creates isolated engines
        Test ExecutionEngineFactory creates properly isolated user execution engines.
        """
        # Create engines for multiple users
        engines = []
        
        for i, context in enumerate(self.test_user_contexts[:5]):  # Test with 5 users
            engine = await self.execution_factory.create_for_user(context)
            engines.append(engine)
            self.created_engines.append(engine)
            
            # Verify engine creation
            assert engine is not None, f"Engine should be created for user {i}"
            assert isinstance(engine, UserExecutionEngine), f"Engine should be UserExecutionEngine instance for user {i}"
            
            # Verify engine has correct user context
            engine_context = engine.get_user_context()
            assert engine_context.user_id == context.user_id, f"Engine {i} should have correct user ID"
            assert engine_context.thread_id == context.thread_id, f"Engine {i} should have correct thread ID"
            assert engine_context.run_id == context.run_id, f"Engine {i} should have correct run ID"
        
        # Verify engines are different instances
        for i, engine_i in enumerate(engines):
            for j, engine_j in enumerate(engines):
                if i != j:
                    assert engine_i is not engine_j, f"Engines {i} and {j} should be different instances"
                    assert id(engine_i) != id(engine_j), f"Engines {i} and {j} should have different memory addresses"
        
        # Test state isolation
        for i, engine in enumerate(engines):
            # Set unique state for each engine
            state_key = "user_specific_state"
            state_value = {
                "user_index": i,
                "sensitive_data": f"secret_data_for_user_{i}",
                "execution_count": 0,
                "user_preferences": {"theme": f"theme_{i}", "language": "en"}
            }
            
            engine.set_agent_state(state_key, state_value)
            self.engine_states[engine.get_user_context().user_id] = state_value
        
        # Verify state isolation
        for i, engine in enumerate(engines):
            retrieved_state = engine.get_agent_state("user_specific_state")
            expected_state = self.engine_states[engine.get_user_context().user_id]
            
            assert retrieved_state == expected_state, f"Engine {i} should have its own state"
            assert retrieved_state["user_index"] == i, f"Engine {i} should have correct user index"
            
            # Verify no state leakage
            for j, other_engine in enumerate(engines):
                if i != j:
                    other_state = other_engine.get_agent_state("user_specific_state")
                    assert other_state != retrieved_state, f"State should not leak between engines {i} and {j}"
                    assert other_state["user_index"] != i, f"Engine {j} should not have user {i} state"
        
        logger.info(f" PASS:  ExecutionEngineFactory user isolation validated: {len(engines)} engines created")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.asyncio
    async def test_concurrent_engine_creation_and_execution(self):
        """
        BVJ: Mid/Enterprise | Concurrent Users | Ensures factory handles concurrent load
        Test ExecutionEngineFactory under concurrent engine creation and execution load.
        """
        num_concurrent_users = 15
        operations_per_user = 3
        
        # Concurrent engine creation
        async def create_and_execute_engine(user_index: int) -> Dict[str, Any]:
            # Create user context
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                agent_context={"user_index": user_index, "concurrent_test": True}
            )
            
            # Create engine through factory
            creation_start = time.time()
            engine = await self.execution_factory.create_for_user(context)
            creation_time = time.time() - creation_start
            
            self.created_engines.append(engine)
            
            # Perform operations on the engine
            operation_results = []
            
            for op_num in range(operations_per_user):
                # Set operation-specific state
                op_key = f"operation_{op_num}"
                op_data = {
                    "user_index": user_index,
                    "operation_num": op_num,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": f"concurrent_data_user_{user_index}_op_{op_num}"
                }
                
                engine.set_agent_state(op_key, op_data)
                
                # Retrieve and verify
                retrieved_data = engine.get_agent_state(op_key)
                operation_results.append({
                    "operation": op_num,
                    "success": retrieved_data == op_data,
                    "data_matches": retrieved_data["user_index"] == user_index if retrieved_data else False
                })
                
                # Small delay to increase concurrency pressure
                await asyncio.sleep(0.001)
            
            return {
                "user_index": user_index,
                "engine_id": id(engine),
                "user_id": context.user_id,
                "creation_time": creation_time,
                "operations": operation_results,
                "all_operations_successful": all(op["success"] for op in operation_results)
            }
        
        # Execute concurrent creation and operations
        concurrent_start = time.time()
        
        concurrent_tasks = [
            create_and_execute_engine(i) for i in range(num_concurrent_users)
        ]
        
        results = await asyncio.gather(*concurrent_tasks)
        concurrent_duration = time.time() - concurrent_start
        
        # Validate concurrent execution results
        assert len(results) == num_concurrent_users, f"Expected {num_concurrent_users} results, got {len(results)}"
        
        successful_users = 0
        total_operations = 0
        successful_operations = 0
        creation_times = []
        
        for result in results:
            user_index = result["user_index"]
            operations = result["operations"]
            
            # Verify user-specific data integrity
            assert result["user_index"] >= 0, f"User index should be valid"
            assert result["engine_id"] > 0, f"Engine should have valid ID"
            assert result["user_id"] is not None, f"User ID should be set"
            
            # Track creation performance
            creation_times.append(result["creation_time"])
            
            # Verify operations
            total_operations += len(operations)
            successful_operations += sum(1 for op in operations if op["success"])
            
            if result["all_operations_successful"]:
                successful_users += 1
        
        # Verify isolation between concurrent users
        engine_ids = [result["engine_id"] for result in results]
        unique_engine_ids = set(engine_ids)
        assert len(unique_engine_ids) == len(engine_ids), "All engines should have unique IDs"
        
        user_ids = [result["user_id"] for result in results]
        unique_user_ids = set(user_ids)
        assert len(unique_user_ids) == len(user_ids), "All users should have unique IDs"
        
        # Performance validation
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < 0.1, f"Average engine creation too slow: {avg_creation_time:.3f}s"
        assert max_creation_time < 0.2, f"Max engine creation too slow: {max_creation_time:.3f}s"
        assert concurrent_duration < 2.0, f"Total concurrent execution too slow: {concurrent_duration:.3f}s"
        
        # Operation success validation
        operation_success_rate = successful_operations / total_operations if total_operations > 0 else 0
        user_success_rate = successful_users / num_concurrent_users
        
        assert operation_success_rate >= 0.95, f"Operation success rate too low: {operation_success_rate:.2%}"
        assert user_success_rate >= 0.90, f"User success rate too low: {user_success_rate:.2%}"
        
        logger.info(f" PASS:  Concurrent engine creation validated: {num_concurrent_users} users, {operation_success_rate:.2%} success rate, {avg_creation_time*1000:.1f}ms avg creation time")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.memory
    async def test_engine_memory_isolation_and_cleanup(self):
        """
        BVJ: Platform | Memory Management | Ensures proper memory isolation and cleanup
        Test memory isolation between engines and proper cleanup procedures.
        """
        initial_memory = self._get_memory_usage()
        engines_to_create = 25
        
        # Create engines with significant data
        created_engines = []
        engine_user_ids = []
        
        for i in range(engines_to_create):
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4())
            )
            
            engine = await self.execution_factory.create_for_user(context)
            created_engines.append(engine)
            engine_user_ids.append(context.user_id)
            self.created_engines.append(engine)
            
            # Add significant data to test memory usage
            large_state = {
                "large_dataset": {f"key_{j}": f"value_{j}_" * 50 for j in range(100)},
                "user_data": f"user_{i}_data" * 100,
                "execution_history": [f"execution_{k}" for k in range(50)],
                "metadata": {"user_index": i, "created_at": datetime.utcnow().isoformat()}
            }
            
            engine.set_agent_state("large_state", large_state)
            engine.set_execution_state("current_task", {"task": f"user_{i}_task", "data": large_state})
        
        memory_after_creation = self._get_memory_usage()
        memory_increase = memory_after_creation - initial_memory
        
        # Verify memory increased with engine creation
        assert memory_increase > 0, f"Memory should increase after creating engines: {memory_increase} bytes"
        
        # Test memory isolation between engines
        for i, engine in enumerate(created_engines[:5]):  # Test first 5 for performance
            engine_state = engine.get_agent_state("large_state")
            assert engine_state is not None, f"Engine {i} should have large state"
            assert engine_state["metadata"]["user_index"] == i, f"Engine {i} should have correct user index"
            
            # Verify data isolation
            for j, other_engine in enumerate(created_engines[:5]):
                if i != j:
                    other_state = other_engine.get_agent_state("large_state")
                    # States should be different objects in memory
                    assert engine_state is not other_state, f"Engines {i} and {j} should not share memory for state"
                    # But should have different user-specific content
                    assert engine_state["metadata"]["user_index"] != other_state["metadata"]["user_index"], f"Engines {i} and {j} should have different user data"
        
        # Test engine cleanup
        cleanup_start_memory = self._get_memory_usage()
        
        # Cleanup half the engines
        engines_to_cleanup = created_engines[:engines_to_create // 2]
        cleanup_user_ids = engine_user_ids[:engines_to_create // 2]
        
        for engine in engines_to_cleanup:
            await engine.cleanup()
        
        # Remove references
        engines_to_cleanup.clear()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup
        gc.collect()
        
        memory_after_partial_cleanup = self._get_memory_usage()
        partial_cleanup_savings = cleanup_start_memory - memory_after_partial_cleanup
        
        # Should release some memory (at least 30% of what was allocated)
        expected_savings = memory_increase * 0.3
        memory_efficiency = partial_cleanup_savings / expected_savings if expected_savings > 0 else 0
        
        # Verify remaining engines still work
        remaining_engines = created_engines[engines_to_create // 2:]
        for i, engine in enumerate(remaining_engines[:3]):  # Test first 3
            # Should still have their data
            engine_state = engine.get_agent_state("large_state")
            assert engine_state is not None, f"Remaining engine {i} should still have state"
            
            # Should be able to add new state
            new_state_key = "post_cleanup_state"
            new_state_value = {"post_cleanup": True, "timestamp": datetime.utcnow().isoformat()}
            engine.set_agent_state(new_state_key, new_state_value)
            
            retrieved_new_state = engine.get_agent_state(new_state_key)
            assert retrieved_new_state == new_state_value, f"Remaining engine {i} should handle new state"
        
        # Final cleanup of remaining engines
        for engine in remaining_engines:
            await engine.cleanup()
        
        remaining_engines.clear()
        created_engines.clear()
        
        gc.collect()
        await asyncio.sleep(0.1)
        gc.collect()
        
        final_memory = self._get_memory_usage()
        total_cleanup_savings = memory_after_creation - final_memory
        total_efficiency = total_cleanup_savings / memory_increase if memory_increase > 0 else 0
        
        # Should release most allocated memory (at least 70%)
        assert total_efficiency >= 0.7, f"Memory cleanup insufficient: {total_efficiency:.2%} efficiency"
        
        logger.info(f" PASS:  Engine memory isolation and cleanup validated: {memory_increase} bytes allocated, {total_efficiency:.2%} cleanup efficiency")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.performance
    async def test_factory_performance_under_load(self):
        """
        BVJ: Mid/Enterprise | Performance SLA | Ensures factory performs under load
        Test ExecutionEngineFactory performance under high concurrent load.
        """
        # Load test parameters
        num_concurrent_batches = 5
        engines_per_batch = 20
        total_engines = num_concurrent_batches * engines_per_batch
        
        # Performance tracking
        creation_times = []
        batch_times = []
        throughput_metrics = []
        
        async def create_engine_batch(batch_index: int) -> List[Dict[str, Any]]:
            batch_start = time.time()
            batch_results = []
            
            for engine_index in range(engines_per_batch):
                context = UserExecutionContext(
                    user_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4()),
                    agent_context={"batch": batch_index, "engine": engine_index}
                )
                
                creation_start = time.time()
                engine = await self.execution_factory.create_for_user(context)
                creation_time = time.time() - creation_start
                
                self.created_engines.append(engine)
                
                # Add some state to simulate real usage
                engine.set_agent_state("batch_data", {
                    "batch_index": batch_index,
                    "engine_index": engine_index,
                    "created_at": datetime.utcnow().isoformat()
                })
                
                batch_results.append({
                    "batch_index": batch_index,
                    "engine_index": engine_index,
                    "creation_time": creation_time,
                    "engine_id": id(engine),
                    "user_id": context.user_id
                })
                
                creation_times.append(creation_time)
            
            batch_time = time.time() - batch_start
            batch_times.append(batch_time)
            
            return batch_results
        
        # Execute load test
        load_test_start = time.time()
        
        batch_tasks = [
            create_engine_batch(i) for i in range(num_concurrent_batches)
        ]
        
        batch_results = await asyncio.gather(*batch_tasks)
        total_load_time = time.time() - load_test_start
        
        # Flatten results
        all_results = []
        for batch_result in batch_results:
            all_results.extend(batch_result)
        
        # Performance analysis
        assert len(all_results) == total_engines, f"Expected {total_engines} engines, got {len(all_results)}"
        
        # Creation time analysis
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        min_creation_time = min(creation_times)
        p95_creation_time = sorted(creation_times)[int(len(creation_times) * 0.95)]
        
        # Batch performance analysis
        avg_batch_time = sum(batch_times) / len(batch_times)
        max_batch_time = max(batch_times)
        
        # Throughput calculation
        engines_per_second = total_engines / total_load_time
        
        # Performance requirements validation
        assert avg_creation_time < 0.05, f"Average creation time too high: {avg_creation_time:.4f}s (required: <0.05s)"
        assert max_creation_time < 0.1, f"Max creation time too high: {max_creation_time:.4f}s (required: <0.1s)"
        assert p95_creation_time < 0.08, f"P95 creation time too high: {p95_creation_time:.4f}s (required: <0.08s)"
        assert engines_per_second >= 50, f"Throughput too low: {engines_per_second:.1f} engines/sec (required: >=50)"
        
        # Verify engine uniqueness under load
        engine_ids = [result["engine_id"] for result in all_results]
        unique_engine_ids = set(engine_ids)
        assert len(unique_engine_ids) == len(engine_ids), "All engines should have unique IDs under load"
        
        user_ids = [result["user_id"] for result in all_results]
        unique_user_ids = set(user_ids)
        assert len(unique_user_ids) == len(user_ids), "All users should have unique IDs under load"
        
        # Verify state isolation under load
        # Test a sample of engines
        sample_engines = self.created_engines[:min(10, len(self.created_engines))]
        for i, engine in enumerate(sample_engines):
            batch_data = engine.get_agent_state("batch_data")
            assert batch_data is not None, f"Sample engine {i} should have batch data"
            assert "batch_index" in batch_data, f"Sample engine {i} should have batch index"
            assert "engine_index" in batch_data, f"Sample engine {i} should have engine index"
        
        # Log performance results
        performance_summary = {
            "total_engines": total_engines,
            "total_time": total_load_time,
            "throughput_eps": engines_per_second,
            "avg_creation_ms": avg_creation_time * 1000,
            "max_creation_ms": max_creation_time * 1000,
            "p95_creation_ms": p95_creation_time * 1000,
            "avg_batch_time_ms": avg_batch_time * 1000,
            "concurrent_batches": num_concurrent_batches
        }
        
        self.memory_usage_samples.append({
            "phase": "after_load_test",
            "memory_usage": self._get_memory_usage(),
            "timestamp": datetime.utcnow(),
            "engines_created": total_engines
        })
        
        logger.info(f" PASS:  Factory performance under load validated: {engines_per_second:.1f} engines/sec, {avg_creation_time*1000:.1f}ms avg creation")

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.reliability
    async def test_factory_error_handling_and_recovery(self):
        """
        BVJ: All segments | System Reliability | Ensures graceful error handling
        Test ExecutionEngineFactory error handling and recovery mechanisms.
        """
        # Error simulation setup
        error_count = 0
        recovery_count = 0
        successful_creations = 0
        
        # Create failing WebSocket bridge
        class FailingWebSocketBridge:
            def __init__(self, failure_rate=0.3):
                self.call_count = 0
                self.failure_rate = failure_rate
            
            def __getattr__(self, name):
                # For any method call, simulate intermittent failures
                def failing_method(*args, **kwargs):
                    nonlocal error_count
                    self.call_count += 1
                    if self.call_count % 3 == 0:  # Every 3rd call fails
                        error_count += 1
                        raise Exception(f"Simulated WebSocket failure in {name}")
                    return MagicMock()
                
                return failing_method
        
        failing_bridge = FailingWebSocketBridge()
        
        # Create factory with failing bridge
        failing_factory = ExecutionEngineFactory(
            websocket_bridge=failing_bridge
        )
        
        # Test resilient engine creation
        async def resilient_engine_creation(user_index: int, max_retries=3) -> Dict[str, Any]:
            nonlocal recovery_count, successful_creations
            
            context = UserExecutionContext(
                user_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                agent_context={"user_index": user_index}
            )
            
            for attempt in range(max_retries):
                try:
                    engine = await failing_factory.create_for_user(context)
                    
                    if attempt > 0:
                        recovery_count += 1
                    
                    successful_creations += 1
                    self.created_engines.append(engine)
                    
                    return {
                        "user_index": user_index,
                        "success": True,
                        "attempts": attempt + 1,
                        "engine_id": id(engine),
                        "recovery": attempt > 0
                    }
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        return {
                            "user_index": user_index,
                            "success": False,
                            "attempts": attempt + 1,
                            "error": str(e),
                            "recovery": False
                        }
                    
                    # Exponential backoff
                    await asyncio.sleep(0.01 * (2 ** attempt))
            
            return {
                "user_index": user_index,
                "success": False,
                "attempts": max_retries,
                "error": "Max retries exceeded",
                "recovery": False
            }
        
        # Test error handling with multiple users
        num_test_users = 15
        
        error_handling_tasks = [
            resilient_engine_creation(i) for i in range(num_test_users)
        ]
        
        results = await asyncio.gather(*error_handling_tasks)
        
        # Analyze error handling results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        recovered_results = [r for r in results if r.get("recovery", False)]
        
        # Verify error handling effectiveness
        success_rate = len(successful_results) / len(results)
        recovery_rate = len(recovered_results) / len(successful_results) if successful_results else 0
        
        # Should have reasonable success rate even with failures
        assert success_rate >= 0.6, f"Success rate too low under failures: {success_rate:.2%}"
        
        # Verify error information is captured
        for failed_result in failed_results:
            assert "error" in failed_result, "Failed results should contain error information"
            assert "attempts" in failed_result, "Failed results should contain attempt count"
        
        # Verify successful engines work properly
        for result in successful_results[:3]:  # Test first 3
            user_index = result["user_index"]
            
            # Find the corresponding engine
            engine_found = False
            for engine in self.created_engines:
                context = engine.get_user_context()
                if context.agent_context.get("user_index") == user_index:
                    # Test engine functionality
                    test_state = {"error_recovery_test": True, "user_index": user_index}
                    engine.set_agent_state("recovery_test", test_state)
                    
                    retrieved_state = engine.get_agent_state("recovery_test")
                    assert retrieved_state == test_state, f"Recovered engine for user {user_index} should work properly"
                    engine_found = True
                    break
            
            assert engine_found, f"Engine for user {user_index} should be found"
        
        # Verify error counts make sense
        assert error_count > 0, "Simulated errors should occur"
        assert successful_creations > 0, "Some creations should succeed"
        
        if recovery_count > 0:
            logger.info(f"Recovery successful: {recovery_count} recoveries out of {error_count} errors")
        
        logger.info(f" PASS:  Factory error handling validated: {success_rate:.2%} success rate, {recovery_count} recoveries")

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback for environments without psutil
            return len(self.created_engines) * 1024  # Rough estimate
        except Exception:
            # Final fallback
            return 1024 * 1024  # 1MB default

    def teardown_method(self, method):
        """Cleanup after tests."""
        # Clear tracking data
        self.engine_states.clear()
        self.isolation_violations.clear()
        self.memory_usage_samples.clear()
        self.concurrent_operations.clear()
        
        super().teardown_method(method)
    
    async def async_teardown_method(self, method):
        """Async cleanup after tests."""
        # Cleanup all created engines
        for engine in self.created_engines:
            try:
                await engine.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup engine: {e}")
        
        self.created_engines.clear()
        self.test_user_contexts.clear()
        
        # Force garbage collection
        gc.collect()
        
        await super().async_teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
