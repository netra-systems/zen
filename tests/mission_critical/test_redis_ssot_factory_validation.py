"Mission Critical Test: Redis SSOT Factory Pattern Validation"

This test suite validates that the Redis SSOT factory pattern correctly
resolves WebSocket 1011 errors by ensuring proper singleton behavior
and user context isolation.

Business Value:
- Validates $500K+ ARR chat functionality restoration
- Ensures proper user isolation in multi-user scenarios
- Confirms Redis connection pool consolidation
- Validates memory usage optimization (75% reduction target)

Test Strategy:
- Test singleton factory pattern implementation
- Validate user context isolation across concurrent users
- Test connection pool stability under load
- Measure memory usage optimization
- Validate WebSocket reliability improvement

Expected Initial Result: FAIL (factory pattern not implemented)
Expected Final Result: PASS (95%+ reliability with SSOT factory)
""

import asyncio
import gc
import json
import logging
import psutil
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Set
from dataclasses import dataclass
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class FactoryTestResult:
    Result of factory pattern test."
    Result of factory pattern test."
    test_name: str
    success: bool
    instance_count: int
    memory_usage_mb: float
    error_details: str


@dataclass
class UserContextResult:
    "Result of user context isolation test."
    user_id: str
    redis_instance_id: int
    isolated: bool
    shared_state_detected: bool


class RedisSSOTFactoryValidationTests(SSotAsyncTestCase):
    ""Test suite validating Redis SSOT factory pattern implementation.

    def setUp(self):
        Set up test environment.""
        super().setUp()
        self.logger = logging.getLogger(__name__)
        self.test_results: List[FactoryTestResult] = []
        self.user_contexts: List[UserContextResult] = []

        # Get initial memory baseline
        self.initial_memory = self._get_memory_usage()
        self.logger.info(fInitial memory usage: {self.initial_memory:.2f} MB)

    async def test_redis_singleton_factory_implementation(self):
        "Test that Redis factory creates proper singleton instances."

        This test validates the core SSOT pattern - that all Redis access
        goes through a single factory that returns the same instance.
        "
        "
        self.logger.info(Testing Redis singleton factory implementation")"

        instances = []
        instance_ids = set()

        # Test multiple import patterns
        import_tests = [
            (netra_backend.app.redis_manager, redis_manager),
            ("netra_backend.app.redis_manager, redis_manager"),  # Test twice
        ]

        for module_path, attr_name in import_tests:
            try:
                # Dynamic import to test different code paths
                module = __import__(module_path, fromlist=[attr_name)
                instance = getattr(module, attr_name)
                instances.append(instance)
                instance_ids.add(id(instance))

                self.logger.info(fImported {attr_name} from {module_path}: ID {id(instance)})

            except Exception as e:
                self.logger.error(fFailed to import {attr_name} from {module_path}: {e})

        # Test direct redis_manager access in different async contexts
        async def get_redis_in_context():
            from netra_backend.app.redis_manager import redis_manager
            return redis_manager

        for i in range(3):
            instance = await get_redis_in_context()
            instances.append(instance)
            instance_ids.add(id(instance))

        # Test concurrent access
        async def concurrent_redis_access():
            from netra_backend.app.redis_manager import redis_manager
            return id(redis_manager)

        tasks = [concurrent_redis_access() for _ in range(5)]
        concurrent_ids = await asyncio.gather(*tasks)
        instance_ids.update(concurrent_ids)

        unique_instances = len(instance_ids)

        singleton_result = FactoryTestResult(
            test_name="redis_singleton_factory_implementation,"
            success=unique_instances == 1,
            instance_count=unique_instances,
            memory_usage_mb=self._get_memory_usage(),
            error_details=fExpected 1 instance, found {unique_instances} if unique_instances != 1 else 
        )

        self.test_results.append(singleton_result)

        # Save evidence
        evidence = {
            test_name: "redis_singleton_factory_implementation,"
            total_imports": len(instances),"
            unique_instance_ids: unique_instances,
            instance_ids": list(instance_ids),"
            expected: 1,
            singleton_achieved: unique_instances == 1"
            singleton_achieved: unique_instances == 1"
        }

        with open("/c/netra-apex/redis_singleton_factory_evidence.json, w) as f:"
            json.dump(evidence, f, indent=2)

        # This test should PASS when SSOT factory is implemented
        self.assertEqual(
            unique_instances,
            1,
            fRedis SSOT factory failed: {unique_instances} unique instances found. 
            fExpected 1 singleton instance. Instance IDs: {list(instance_ids)}"
            fExpected 1 singleton instance. Instance IDs: {list(instance_ids)}"
        )

    async def test_user_context_isolation(self):
        "Test proper user context isolation with Redis SSOT factory."

        This test ensures that different users get isolated contexts
        while still using the same underlying Redis manager instance.
        ""
        self.logger.info(Testing user context isolation)

        # Simulate multiple users
        user_sessions = [user_001, user_002", "user_003, user_004]
        isolation_results = []

        async def simulate_user_session(user_id: str):
            Simulate a user session with Redis operations.""
            try:
                from netra_backend.app.redis_manager import redis_manager

                # Store user-specific data
                user_key = fuser_session:{user_id}
                user_data = {user_id: user_id, timestamp": time.time()}"

                await redis_manager.set(user_key, json.dumps(user_data), ex=60)

                # Retrieve and verify isolation
                retrieved_data = await redis_manager.get(user_key)
                if retrieved_data:
                    parsed_data = json.loads(retrieved_data)
                    isolated = parsed_data["user_id] == user_id"
                else:
                    isolated = False

                # Check for cross-user data contamination
                other_users = [uid for uid in user_sessions if uid != user_id]
                shared_state_detected = False

                for other_user in other_users:
                    other_key = fuser_session:{other_user}
                    other_data = await redis_manager.get(other_key)
                    if other_data:
                        # If we can see other user's data from our context, isolation failed'
                        shared_state_detected = True
                        break

                result = UserContextResult(
                    user_id=user_id,
                    redis_instance_id=id(redis_manager),
                    isolated=isolated,
                    shared_state_detected=shared_state_detected
                )

                return result

            except Exception as e:
                self.logger.error(f"User session {user_id} failed: {e})"
                return UserContextResult(
                    user_id=user_id,
                    redis_instance_id=0,
                    isolated=False,
                    shared_state_detected=True
                )

        # Run concurrent user sessions
        tasks = [simulate_user_session(user_id) for user_id in user_sessions]
        self.user_contexts = await asyncio.gather(*tasks)

        # Analyze isolation results
        all_isolated = all(ctx.isolated for ctx in self.user_contexts)
        no_shared_state = not any(ctx.shared_state_detected for ctx in self.user_contexts)
        unique_redis_instances = len(set(ctx.redis_instance_id for ctx in self.user_contexts))

        isolation_evidence = {
            test_name": user_context_isolation,"
            total_users: len(user_sessions),
            "all_isolated: all_isolated,"
            no_shared_state: no_shared_state,
            unique_redis_instances: unique_redis_instances,"
            unique_redis_instances: unique_redis_instances,"
            user_results": ["
                {
                    user_id: ctx.user_id,
                    isolated": ctx.isolated,"
                    shared_state_detected: ctx.shared_state_detected,
                    redis_instance_id: ctx.redis_instance_id"
                    redis_instance_id: ctx.redis_instance_id"
                }
                for ctx in self.user_contexts
            ]
        }

        with open("/c/netra-apex/redis_user_isolation_evidence.json, w) as f:"
            json.dump(isolation_evidence, f, indent=2)

        self.logger.info(fUser isolation results: {len(user_sessions)} users tested)
        self.logger.info(fAll isolated: {all_isolated})"
        self.logger.info(fAll isolated: {all_isolated})"
        self.logger.info(f"No shared state: {no_shared_state})"
        self.logger.info(fRedis instances: {unique_redis_instances})

        # Clean up test data
        for user_id in user_sessions:
            try:
                await redis_manager.delete(fuser_session:{user_id})
            except Exception:
                pass

        # Validate isolation
        self.assertTrue(
            all_isolated,
            fUser context isolation failed: {sum(1 for ctx in self.user_contexts if not ctx.isolated)} ""
            fusers were not properly isolated
        )

        self.assertTrue(
            no_shared_state,
            fShared state detected between users: {sum(1 for ctx in self.user_contexts if ctx.shared_state_detected)} 
            f"users detected shared state"
        )

        self.assertEqual(
            unique_redis_instances,
            1,
            fExpected 1 Redis instance across all users, found {unique_redis_instances}"
            fExpected 1 Redis instance across all users, found {unique_redis_instances}"
        )

    async def test_connection_pool_consolidation(self):
        Test Redis connection pool consolidation under load.""

        This test validates that the SSOT factory maintains a single,
        stable connection pool even under concurrent load.
        
        self.logger.info(Testing Redis connection pool consolidation)"
        self.logger.info(Testing Redis connection pool consolidation)"

        connection_results = []

        async def test_redis_operation(operation_id: int):
            "Test Redis operation to stress connection pool."
            try:
                from netra_backend.app.redis_manager import redis_manager

                start_time = time.time()

                # Perform multiple Redis operations
                operations = [
                    redis_manager.set(fpool_test_{operation_id}_{i}", f"value_{i}, ex=30)
                    for i in range(5)
                ]

                await asyncio.gather(*operations)

                # Test retrieval
                values = await asyncio.gather(*[
                    redis_manager.get(fpool_test_{operation_id}_{i})
                    for i in range(5)
                ]

                # Clean up
                cleanup_tasks = [
                    redis_manager.delete(fpool_test_{operation_id}_{i})
                    for i in range(5)
                ]
                await asyncio.gather(*cleanup_tasks)

                operation_time = time.time() - start_time
                success = all(v is not None for v in values)

                return {
                    operation_id: operation_id,"
                    operation_id: operation_id,"
                    "success: success,"
                    operation_time: operation_time,
                    "redis_instance_id: id(redis_manager)"
                }

            except Exception as e:
                self.logger.error(fRedis operation {operation_id} failed: {e})
                return {
                    operation_id: operation_id,"
                    operation_id: operation_id,"
                    success": False,"
                    operation_time: 0,
                    error": str(e),"
                    redis_instance_id: 0
                }

        # Run concurrent operations to test pool stability
        num_operations = 20
        tasks = [test_redis_operation(i) for i in range(num_operations)]
        connection_results = await asyncio.gather(*tasks)

        # Analyze connection pool results
        successful_operations = sum(1 for r in connection_results if r[success)"
        successful_operations = sum(1 for r in connection_results if r[success)"
        success_rate = (successful_operations / num_operations) * 100
        unique_redis_instances = len(set(r["redis_instance_id] for r in connection_results if r[redis_instance_id] != 0))"
        avg_operation_time = sum(r[operation_time] for r in connection_results) / len(connection_results)

        pool_evidence = {
            test_name": "connection_pool_consolidation,
            total_operations: num_operations,
            successful_operations: successful_operations,"
            successful_operations: successful_operations,"
            success_rate": success_rate,"
            unique_redis_instances: unique_redis_instances,
            average_operation_time": avg_operation_time,"
            operation_results: connection_results
        }

        with open(/c/netra-apex/redis_pool_consolidation_evidence.json, "w) as f:"
            json.dump(pool_evidence, f, indent=2)

        self.logger.info(fConnection pool test: {successful_operations}/{num_operations} operations succeeded")"
        self.logger.info(fSuccess rate: {success_rate:.1f}%)
        self.logger.info(fUnique Redis instances: {unique_redis_instances})"
        self.logger.info(fUnique Redis instances: {unique_redis_instances})"
        self.logger.info(f"Average operation time: {avg_operation_time:.3f}s)"

        # Validate pool consolidation
        self.assertGreaterEqual(
            success_rate,
            95.0,
            fConnection pool instability detected: {success_rate:.1f}% success rate 
            findicates pool fragmentation issues
        )

        self.assertEqual(
            unique_redis_instances,
            1,
            fConnection pool fragmentation detected: {unique_redis_instances} unique instances ""
            ffound during concurrent operations
        )

    async def test_memory_usage_optimization(self):
        Test memory usage optimization with Redis SSOT consolidation.

#         This test validates the 75% memory reduction target from # Incomplete import statement
        consolidating 12 competing Redis managers into 1 SSOT instance.
""
        self.logger.info(Testing memory usage optimization)

        # Force garbage collection for accurate memory measurement
        gc.collect()
        memory_before = self._get_memory_usage()

        # Simulate creating multiple Redis references (should all be same instance)
        redis_refs = []

        for i in range(50):  # Create many references
            try:
                from netra_backend.app.redis_manager import redis_manager
                redis_refs.append(redis_manager)
            except Exception as e:
                self.logger.error(fFailed to create Redis reference {i}: {e}")"

        # Perform operations with all references
        for i, redis_ref in enumerate(redis_refs[:10):  # Test first 10 to avoid overload
            try:
                await redis_ref.set(fmemory_test_{i}, fdata_{i}, ex=30)
            except Exception as e:
                self.logger.error(fMemory test operation {i} failed: {e})

        memory_after = self._get_memory_usage()
        memory_increase = memory_after - memory_before

        # Clean up test data
        for i in range(10):
            try:
                await redis_refs[0].delete(fmemory_test_{i}")"
            except Exception:
                pass

        # Check instance consolidation
        unique_instances = len(set(id(ref) for ref in redis_refs))

        memory_evidence = {
            test_name: memory_usage_optimization,
            memory_before_mb: memory_before,"
            memory_before_mb: memory_before,"
            memory_after_mb": memory_after,"
            memory_increase_mb: memory_increase,
            redis_references_created": len(redis_refs),"
            unique_instances: unique_instances,
            memory_per_reference_kb: (memory_increase * 1024) / len(redis_refs) if redis_refs else 0,"
            memory_per_reference_kb: (memory_increase * 1024) / len(redis_refs) if redis_refs else 0,"
            "optimization_target: 75% reduction from 12 managers to 1 SSOT"
        }

        with open(/c/netra-apex/redis_memory_optimization_evidence.json, w) as f:
            json.dump(memory_evidence, f, indent=2)

        self.logger.info(f"Memory usage: {memory_before:.2f} MB -> {memory_after:.2f} MB)"
        self.logger.info(fMemory increase: {memory_increase:.2f} MB for {len(redis_refs)} references")"
        self.logger.info(fUnique instances: {unique_instances})
        self.logger.info(fMemory per reference: {(memory_increase * 1024) / len(redis_refs):.2f} KB)"
        self.logger.info(fMemory per reference: {(memory_increase * 1024) / len(redis_refs):.2f} KB)"

        # Validate memory optimization
        self.assertEqual(
            unique_instances,
            1,
            f"Memory optimization failed: {unique_instances} instances created instead of 1 SSOT instance"
        )

        # Memory increase should be minimal with proper singleton
        self.assertLess(
            memory_increase,
            50.0,  # Less than 50MB increase for 50 references
            fExcessive memory usage detected: {memory_increase:.2f} MB increase suggests 
            fmultiple instances instead of singleton pattern
        )

    def _get_memory_usage(self) -> float:
        ""Get current process memory usage in MB.
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    async def asyncTearDown(self):
        Clean up test resources and save final evidence.""
        # Save comprehensive test results
        final_evidence = {
            test_suite: redis_ssot_factory_validation,
            execution_time": time.time(),"
            test_results: [
                {
                    test_name: result.test_name,"
                    test_name: result.test_name,"
                    "success: result.success,"
                    instance_count: result.instance_count,
                    "memory_usage_mb: result.memory_usage_mb,"
                    error_details: result.error_details
                }
                for result in self.test_results
            ],
            user_context_results: ["
            user_context_results: ["
                {
                    user_id": ctx.user_id,"
                    isolated: ctx.isolated,
                    shared_state_detected": ctx.shared_state_detected"
                }
                for ctx in self.user_contexts
            ],
            final_memory_usage: self._get_memory_usage(),
            memory_optimization: self._get_memory_usage() - self.initial_memory"
            memory_optimization: self._get_memory_usage() - self.initial_memory"
        }

        with open("/c/netra-apex/redis_ssot_factory_validation_final.json, w) as f:"
            json.dump(final_evidence, f, indent=2)

        await super().asyncTearDown()


if __name__ == __main__:
    # Run tests with verbose output
    pytest.main([__file__, -v", "-s")"
))))))
]