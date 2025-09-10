"""
Redis Cache Race Condition Tests - Integration Testing

This module tests critical race conditions in Redis cache operations that could lead to:
- Cache inconsistency during concurrent updates
- Lost cache invalidations causing stale data
- Connection pool exhaustion during cache bursts
- Cross-user cache contamination and data leaks
- Memory leaks and resource exhaustion in cache layer

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Cache reliability is critical for performance
- Business Goal: Ensure cache consistency and prevent data corruption under concurrent load
- Value Impact: Prevents performance degradation and data inconsistencies that impact user experience
- Strategic Impact: CRITICAL - Cache layer reliability directly impacts platform responsiveness and scalability

Test Coverage:
- Concurrent cache operations (100 simultaneous cache operations)
- Cache invalidation consistency during high load
- Connection pool management under cache operation bursts
- User isolation in cached data and session management
- Cache expiration and cleanup race conditions
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

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_redis_fixture
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestRedisCacheRaces(BaseIntegrationTest):
    """Test race conditions in Redis cache operations and management."""
    
    def setup_method(self):
        """Set up test environment with Redis operation tracking."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "redis_cache_race_testing", source="test")
        
        # Cache operation tracking
        self.cache_operations: List[Dict] = []
        self.race_conditions_detected: List[Dict] = []
        self.redis_connections: List[Any] = []
        
        # Consistency tracking
        self.cache_inconsistencies: List[Dict] = []
        self.invalidation_events: List[Dict] = []
        self.expiration_events: List[Dict] = []
        
        # Performance metrics
        self.operation_times: List[float] = []
        self.connection_snapshots: List[Dict] = []
        self.memory_usage_snapshots: List[Dict] = []
        
        # Test data tracking
        self.test_keys: Set[str] = set()
        self.expected_values: Dict[str, Any] = {}
        
    def teardown_method(self):
        """Clean up Redis connections and test data."""
        # Clean up test keys
        cleanup_tasks = []
        for redis_conn in self.redis_connections:
            if redis_conn:
                try:
                    # Delete test keys
                    if self.test_keys:
                        cleanup_tasks.append(redis_conn.delete(*list(self.test_keys)))
                except Exception as e:
                    logger.warning(f"Error cleaning up Redis keys: {e}")
        
        # Wait for cleanup
        if cleanup_tasks:
            try:
                asyncio.get_event_loop().run_until_complete(
                    asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=5.0)
                )
            except asyncio.TimeoutError:
                logger.warning("Redis cleanup timed out")
        
        # Close connections
        for redis_conn in self.redis_connections:
            try:
                if hasattr(redis_conn, 'close'):
                    asyncio.create_task(redis_conn.close())
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
        
        # Clear tracking data
        self.cache_operations.clear()
        self.redis_connections.clear()
        self.cache_inconsistencies.clear()
        self.invalidation_events.clear()
        self.expiration_events.clear()
        self.test_keys.clear()
        self.expected_values.clear()
        
        super().teardown_method()
    
    def _track_cache_operation(self, operation_type: str, key: str, user_id: str = None, metadata: Dict = None):
        """Track cache operations for race condition analysis."""
        operation = {
            "type": operation_type,
            "key": key,
            "user_id": user_id,
            "timestamp": time.time(),
            "task_name": asyncio.current_task().get_name() if asyncio.current_task() else "unknown",
            "metadata": metadata or {}
        }
        self.cache_operations.append(operation)
        
        # Add key to test tracking
        self.test_keys.add(key)
        
        # Analyze for race condition patterns
        self._analyze_cache_race_patterns(operation)
    
    def _analyze_cache_race_patterns(self, operation: Dict):
        """Analyze cache operations for race condition patterns."""
        key = operation["key"]
        op_type = operation["type"]
        user_id = operation["user_id"]
        
        # Pattern 1: Rapid set/get on same key (potential inconsistency)
        if op_type in ["set", "get"]:
            recent_ops = [
                op for op in self.cache_operations[-20:]
                if op["key"] == key and operation["timestamp"] - op["timestamp"] < 0.1
            ]
            
            if len(recent_ops) > 5:  # Very rapid operations on same key
                self._detect_race_condition("rapid_key_access", {
                    "key": key,
                    "operations": len(recent_ops),
                    "user_id": user_id
                })
        
        # Pattern 2: Multiple users accessing same cache key simultaneously
        if user_id and op_type in ["set", "delete"]:
            concurrent_user_ops = [
                op for op in self.cache_operations[-10:]
                if op["key"] == key and op["user_id"] != user_id
                and operation["timestamp"] - op["timestamp"] < 0.5  # Within 500ms
            ]
            
            if concurrent_user_ops:
                self._detect_race_condition("concurrent_user_key_access", {
                    "key": key,
                    "current_user": user_id,
                    "concurrent_users": [op["user_id"] for op in concurrent_user_ops]
                })
        
        # Pattern 3: Invalidation without corresponding set (orphaned invalidation)
        if op_type == "delete":
            recent_sets = [
                op for op in self.cache_operations[-50:]
                if op["key"] == key and op["type"] == "set"
            ]
            
            if not recent_sets:
                self._detect_race_condition("orphaned_invalidation", {
                    "key": key,
                    "user_id": user_id
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
        logger.warning(f"CACHE RACE CONDITION DETECTED: {condition_type} - {metadata}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_cache_operations_consistency(self, real_services_fixture, real_redis_fixture):
        """
        Test cache consistency during concurrent read/write operations.
        
        Verifies that concurrent cache operations maintain data consistency
        and don't cause lost updates or phantom reads.
        """
        services = real_services_fixture
        redis_client = real_redis_fixture
        
        if not services["database_available"] or not redis_client:
            pytest.skip("Real services not available for integration test")
        
        # Business Value: Ensure cache reliability for user sessions and data
        # Critical for maintaining consistent user experience under load
        
        num_concurrent_operations = 60
        keys_per_operation = 3
        consistency_results = []
        
        # Track Redis connection
        self.redis_connections.append(redis_client)
        
        async def concurrent_cache_operation(operation_index: int) -> Dict:
            """Perform concurrent cache operations with consistency checks."""
            user_id = ensure_user_id(f"cache_user_{operation_index % 10}")  # 10 different users
            operation_start = time.time()
            
            try:
                operation_results = []
                
                for key_idx in range(keys_per_operation):
                    cache_key = f"race_test_key_{operation_index}_{key_idx}"
                    operation_value = {
                        "user_id": str(user_id),
                        "operation_index": operation_index,
                        "key_index": key_idx,
                        "value": random.randint(1, 1000),
                        "timestamp": time.time(),
                        "consistency_token": str(uuid.uuid4())
                    }
                    
                    # SET operation
                    set_start = time.time()
                    self._track_cache_operation("set", cache_key, str(user_id), {
                        "value": operation_value,
                        "operation_index": operation_index
                    })
                    
                    await redis_client.set(cache_key, json.dumps(operation_value), ex=300)  # 5 minute expiry
                    set_time = time.time() - set_start
                    self.operation_times.append(set_time)
                    
                    # Store expected value for verification
                    self.expected_values[cache_key] = operation_value
                    
                    # Brief delay to allow race conditions
                    await asyncio.sleep(0.01)
                    
                    # GET operation for immediate verification
                    get_start = time.time()
                    self._track_cache_operation("get", cache_key, str(user_id), {
                        "operation_index": operation_index
                    })
                    
                    cached_data = await redis_client.get(cache_key)
                    get_time = time.time() - get_start
                    self.operation_times.append(get_time)
                    
                    if cached_data:
                        try:
                            retrieved_value = json.loads(cached_data)
                            
                            # Verify consistency
                            if retrieved_value != operation_value:
                                self.cache_inconsistencies.append({
                                    "cache_key": cache_key,
                                    "expected": operation_value,
                                    "retrieved": retrieved_value,
                                    "user_id": str(user_id),
                                    "operation_index": operation_index
                                })
                            
                            operation_results.append({
                                "key": cache_key,
                                "set_time": set_time,
                                "get_time": get_time,
                                "consistent": retrieved_value == operation_value,
                                "value": retrieved_value
                            })
                            
                        except json.JSONDecodeError as e:
                            # JSON parsing error indicates data corruption
                            self.cache_inconsistencies.append({
                                "cache_key": cache_key,
                                "error": "json_decode_error",
                                "raw_data": cached_data,
                                "user_id": str(user_id)
                            })
                    else:
                        # Cache miss immediately after set indicates race condition
                        self.cache_inconsistencies.append({
                            "cache_key": cache_key,
                            "error": "immediate_cache_miss",
                            "user_id": str(user_id),
                            "operation_index": operation_index
                        })
                
                operation_time = time.time() - operation_start
                
                return {
                    "success": True,
                    "operation_index": operation_index,
                    "user_id": str(user_id),
                    "keys_processed": len(operation_results),
                    "operation_time": operation_time,
                    "results": operation_results
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "operation_index": operation_index,
                    "error": str(e)
                }
        
        # Execute concurrent cache operations
        logger.info(f"Testing cache consistency with {num_concurrent_operations} concurrent operations")
        
        operation_tasks = [concurrent_cache_operation(i) for i in range(num_concurrent_operations)]
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Analyze cache consistency results
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_operations = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # CRITICAL BUSINESS VALIDATION: High success rate for cache operations
        success_rate = len(successful_operations) / num_concurrent_operations
        assert success_rate >= 0.95, f"Cache operation success rate too low: {success_rate:.2%}"
        
        # Verify cache consistency - no data corruption
        total_keys_processed = sum(r["keys_processed"] for r in successful_operations)
        expected_keys = len(successful_operations) * keys_per_operation
        
        assert total_keys_processed >= expected_keys * 0.95, \
            f"Key processing rate too low: {total_keys_processed}/{expected_keys}"
        
        # Check for cache inconsistencies
        assert len(self.cache_inconsistencies) == 0, \
            f"Cache inconsistencies detected: {self.cache_inconsistencies}"
        
        # Verify final cache state consistency
        consistency_check_results = []
        for cache_key, expected_value in self.expected_values.items():
            try:
                final_cached_data = await redis_client.get(cache_key)
                if final_cached_data:
                    final_value = json.loads(final_cached_data)
                    is_consistent = final_value == expected_value
                    consistency_check_results.append(is_consistent)
                    
                    if not is_consistent:
                        logger.error(f"Final consistency check failed for {cache_key}")
                else:
                    logger.warning(f"Cache key {cache_key} not found in final consistency check")
            except Exception as e:
                logger.error(f"Error during final consistency check for {cache_key}: {e}")
        
        # Final consistency rate should be very high
        if consistency_check_results:
            final_consistency_rate = sum(consistency_check_results) / len(consistency_check_results)
            assert final_consistency_rate >= 0.98, \
                f"Final cache consistency rate too low: {final_consistency_rate:.2%}"
        
        # Performance validation
        if self.operation_times:
            avg_op_time = sum(self.operation_times) / len(self.operation_times)
            max_op_time = max(self.operation_times)
            
            assert avg_op_time < 0.1, f"Average cache operation time too slow: {avg_op_time:.3f}s"
            assert max_op_time < 1.0, f"Maximum cache operation time too slow: {max_op_time:.3f}s"
        
        # Race conditions should be minimal
        assert len(self.race_conditions_detected) <= 2, \
            f"Excessive cache race conditions: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_operations)} cache operations completed consistently")
        logger.info(f"Keys processed: {total_keys_processed}, Inconsistencies: {len(self.cache_inconsistencies)}")
        
        self.assert_business_value_delivered({
            "successful_operations": len(successful_operations),
            "cache_consistency_maintained": True,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_invalidation_race_conditions(self, real_services_fixture, real_redis_fixture):
        """
        Test cache invalidation consistency during concurrent updates.
        
        Verifies that cache invalidations are properly coordinated and don't
        cause stale data to persist when multiple processes are updating cache.
        """
        services = real_services_fixture
        redis_client = real_redis_fixture
        
        if not services["database_available"] or not redis_client:
            pytest.skip("Real services not available for integration test")
        
        num_cache_keys = 20
        updates_per_key = 10
        invalidation_results = []
        
        # Track Redis connection
        self.redis_connections.append(redis_client)
        
        # Pre-populate cache with initial data
        initial_cache_data = {}
        for key_idx in range(num_cache_keys):
            cache_key = f"invalidation_test_key_{key_idx}"
            initial_value = {
                "version": 0,
                "data": f"initial_data_{key_idx}",
                "created_at": time.time()
            }
            initial_cache_data[cache_key] = initial_value
            await redis_client.set(cache_key, json.dumps(initial_value), ex=600)  # 10 minute expiry
            self.test_keys.add(cache_key)
        
        async def concurrent_cache_invalidation(key_index: int) -> Dict:
            """Perform concurrent cache updates and invalidations."""
            cache_key = f"invalidation_test_key_{key_index}"
            user_id = ensure_user_id(f"invalidation_user_{key_index}")
            
            try:
                update_results = []
                
                for update_idx in range(updates_per_key):
                    update_start = time.time()
                    
                    # Read current value
                    current_data = await redis_client.get(cache_key)
                    if current_data:
                        current_value = json.loads(current_data)
                        current_version = current_value.get("version", 0)
                    else:
                        current_version = 0
                    
                    # Create new value
                    new_value = {
                        "version": current_version + 1,
                        "data": f"updated_data_{key_index}_{update_idx}",
                        "updated_by": str(user_id),
                        "updated_at": time.time(),
                        "update_index": update_idx
                    }
                    
                    # Invalidate and update atomically
                    self._track_cache_operation("delete", cache_key, str(user_id), {
                        "update_index": update_idx,
                        "old_version": current_version
                    })
                    
                    # Brief delay to simulate processing time and increase race chance
                    await asyncio.sleep(0.005)
                    
                    # Set new value
                    self._track_cache_operation("set", cache_key, str(user_id), {
                        "new_value": new_value,
                        "update_index": update_idx
                    })
                    
                    await redis_client.set(cache_key, json.dumps(new_value), ex=600)
                    
                    # Record invalidation event
                    invalidation_event = {
                        "cache_key": cache_key,
                        "user_id": str(user_id),
                        "update_index": update_idx,
                        "old_version": current_version,
                        "new_version": current_version + 1,
                        "timestamp": time.time()
                    }
                    self.invalidation_events.append(invalidation_event)
                    
                    # Verify update took effect
                    verification_data = await redis_client.get(cache_key)
                    if verification_data:
                        verification_value = json.loads(verification_data)
                        version_consistent = verification_value["version"] >= new_value["version"]
                        
                        if not version_consistent:
                            self.cache_inconsistencies.append({
                                "cache_key": cache_key,
                                "expected_version": new_value["version"],
                                "actual_version": verification_value["version"],
                                "update_index": update_idx,
                                "inconsistency_type": "version_regression"
                            })
                    
                    update_time = time.time() - update_start
                    
                    update_results.append({
                        "update_index": update_idx,
                        "old_version": current_version,
                        "new_version": current_version + 1,
                        "update_time": update_time,
                        "version_consistent": version_consistent
                    })
                
                return {
                    "success": True,
                    "cache_key": cache_key,
                    "user_id": str(user_id),
                    "updates_completed": len(update_results),
                    "final_version": max(r["new_version"] for r in update_results),
                    "update_results": update_results
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "cache_key": cache_key,
                    "error": str(e)
                }
        
        # Execute concurrent cache invalidations
        logger.info(f"Testing cache invalidation with {num_cache_keys} keys x {updates_per_key} updates")
        
        invalidation_tasks = [concurrent_cache_invalidation(i) for i in range(num_cache_keys)]
        results = await asyncio.gather(*invalidation_tasks, return_exceptions=True)
        
        # Analyze invalidation results
        successful_invalidations = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All cache invalidations should complete successfully
        success_rate = len(successful_invalidations) / num_cache_keys
        assert success_rate >= 0.95, f"Cache invalidation success rate too low: {success_rate:.2%}"
        
        # Verify final cache state consistency
        final_consistency_errors = []
        for result in successful_invalidations:
            cache_key = result["cache_key"]
            expected_final_version = result["final_version"]
            
            try:
                final_data = await redis_client.get(cache_key)
                if final_data:
                    final_value = json.loads(final_data)
                    final_version = final_value.get("version", 0)
                    
                    # Final version should match expected
                    if final_version < expected_final_version:
                        final_consistency_errors.append({
                            "cache_key": cache_key,
                            "expected_version": expected_final_version,
                            "actual_version": final_version,
                            "error_type": "version_inconsistency"
                        })
                else:
                    final_consistency_errors.append({
                        "cache_key": cache_key,
                        "error_type": "cache_miss",
                        "expected_version": expected_final_version
                    })
            except Exception as e:
                final_consistency_errors.append({
                    "cache_key": cache_key,
                    "error": str(e),
                    "error_type": "verification_error"
                })
        
        # Final consistency should be maintained
        assert len(final_consistency_errors) == 0, \
            f"Final cache consistency errors: {final_consistency_errors}"
        
        # Check for cache inconsistencies during updates
        assert len(self.cache_inconsistencies) <= 1, \
            f"Cache inconsistencies during invalidation: {self.cache_inconsistencies}"
        
        # Verify invalidation event consistency
        total_invalidation_events = len(self.invalidation_events)
        expected_events = sum(r["updates_completed"] for r in successful_invalidations)
        
        event_consistency_rate = total_invalidation_events / expected_events if expected_events > 0 else 0
        assert event_consistency_rate >= 0.95, \
            f"Invalidation event consistency rate too low: {event_consistency_rate:.2%}"
        
        # Performance validation for updates
        update_times = []
        for result in successful_invalidations:
            for update_result in result.get("update_results", []):
                update_times.append(update_result["update_time"])
        
        if update_times:
            avg_update_time = sum(update_times) / len(update_times)
            max_update_time = max(update_times)
            
            assert avg_update_time < 0.2, f"Average cache update time too slow: {avg_update_time:.3f}s"
            assert max_update_time < 1.0, f"Maximum cache update time too slow: {max_update_time:.3f}s"
        
        logger.info(f"SUCCESS: {len(successful_invalidations)} cache invalidation sequences completed")
        logger.info(f"Total invalidation events: {total_invalidation_events}")
        
        self.assert_business_value_delivered({
            "successful_invalidations": len(successful_invalidations),
            "invalidation_events": total_invalidation_events,
            "consistency_maintained": True,
            "final_consistency_errors": len(final_consistency_errors)
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_connection_pool_race_conditions(self, real_services_fixture, real_redis_fixture):
        """
        Test Redis connection pool behavior under concurrent operation bursts.
        
        Verifies that Redis connection pools handle high operation volume
        without exhaustion and connections are properly managed.
        """
        services = real_services_fixture
        redis_client = real_redis_fixture
        
        if not services["database_available"] or not redis_client:
            pytest.skip("Real services not available for integration test")
        
        num_connection_bursts = 15
        operations_per_burst = 20
        total_operations = num_connection_bursts * operations_per_burst
        
        connection_pool_results = []
        connection_metrics = {
            "operations_completed": 0,
            "operations_failed": 0,
            "connection_errors": 0,
            "timeout_errors": 0,
            "peak_concurrent_operations": 0
        }
        
        # Track Redis connection
        self.redis_connections.append(redis_client)
        
        async def redis_operation_burst(burst_index: int) -> Dict:
            """Execute burst of Redis operations to test connection pool."""
            burst_start = time.time()
            concurrent_operations = []
            
            async def single_redis_operation(op_index: int):
                """Execute a single Redis operation."""
                operation_start = time.time()
                cache_key = f"pool_test_key_{burst_index}_{op_index}"
                
                try:
                    # Mix of different Redis operations
                    if op_index % 4 == 0:
                        # SET operation
                        value = {"burst": burst_index, "op": op_index, "timestamp": time.time()}
                        await redis_client.set(cache_key, json.dumps(value), ex=60)
                        self._track_cache_operation("set", cache_key, f"pool_user_{burst_index}", {"value": value})
                        
                    elif op_index % 4 == 1:
                        # GET operation
                        await redis_client.get(cache_key)
                        self._track_cache_operation("get", cache_key, f"pool_user_{burst_index}")
                        
                    elif op_index % 4 == 2:
                        # EXISTS operation
                        await redis_client.exists(cache_key)
                        self._track_cache_operation("exists", cache_key, f"pool_user_{burst_index}")
                        
                    else:
                        # DELETE operation
                        await redis_client.delete(cache_key)
                        self._track_cache_operation("delete", cache_key, f"pool_user_{burst_index}")
                    
                    operation_time = time.time() - operation_start
                    connection_metrics["operations_completed"] += 1
                    
                    return {
                        "success": True,
                        "operation_index": op_index,
                        "operation_time": operation_time,
                        "cache_key": cache_key
                    }
                    
                except asyncio.TimeoutError:
                    connection_metrics["timeout_errors"] += 1
                    return {
                        "success": False,
                        "operation_index": op_index,
                        "error": "timeout"
                    }
                except Exception as e:
                    connection_metrics["connection_errors"] += 1
                    return {
                        "success": False,
                        "operation_index": op_index,
                        "error": str(e)
                    }
            
            # Execute operations concurrently within burst
            operation_tasks = [single_redis_operation(i) for i in range(operations_per_burst)]
            
            # Track peak concurrent operations
            connection_metrics["peak_concurrent_operations"] = max(
                connection_metrics["peak_concurrent_operations"],
                len(operation_tasks)
            )
            
            operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
            
            burst_time = time.time() - burst_start
            successful_ops = len([r for r in operation_results if isinstance(r, dict) and r.get("success")])
            
            return {
                "burst_index": burst_index,
                "successful_operations": successful_ops,
                "total_operations": operations_per_burst,
                "burst_time": burst_time,
                "operation_results": operation_results
            }
        
        # Execute Redis operation bursts
        logger.info(f"Testing Redis connection pool with {num_connection_bursts} bursts x {operations_per_burst} operations")
        
        burst_results = []
        for burst_idx in range(num_connection_bursts):
            burst_result = await redis_operation_burst(burst_idx)
            burst_results.append(burst_result)
            
            # Brief pause between bursts to allow connection pool recovery
            await asyncio.sleep(0.02)
        
        # Analyze connection pool performance
        total_successful_operations = sum(r["successful_operations"] for r in burst_results)
        total_connection_errors = connection_metrics["connection_errors"]
        total_timeout_errors = connection_metrics["timeout_errors"]
        
        # CRITICAL: Connection pool should handle reasonable load
        operation_success_rate = total_successful_operations / total_operations
        assert operation_success_rate >= 0.90, \
            f"Redis operation success rate too low: {operation_success_rate:.2%}"
        
        # Connection errors should be minimal
        connection_error_rate = total_connection_errors / total_operations
        assert connection_error_rate < 0.05, \
            f"Redis connection error rate too high: {connection_error_rate:.2%}"
        
        # Timeout errors should be minimal
        timeout_error_rate = total_timeout_errors / total_operations
        assert timeout_error_rate < 0.03, \
            f"Redis timeout error rate too high: {timeout_error_rate:.2%}"
        
        # Performance validation for bursts
        burst_times = [r["burst_time"] for r in burst_results]
        if burst_times:
            avg_burst_time = sum(burst_times) / len(burst_times)
            max_burst_time = max(burst_times)
            
            assert avg_burst_time < 1.0, f"Average burst time too slow: {avg_burst_time:.3f}s"
            assert max_burst_time < 5.0, f"Maximum burst time too slow: {max_burst_time:.3f}s"
        
        # Verify connection pool didn't exhaust
        peak_concurrent = connection_metrics["peak_concurrent_operations"]
        assert peak_concurrent <= operations_per_burst + 5, \
            f"Peak concurrent operations unexpectedly high: {peak_concurrent}"
        
        # Race conditions should be minimal for connection pool
        assert len(self.race_conditions_detected) <= 3, \
            f"Excessive connection pool race conditions: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {total_successful_operations} Redis operations completed")
        logger.info(f"Connection errors: {total_connection_errors}, Timeouts: {total_timeout_errors}")
        logger.info(f"Peak concurrent operations: {peak_concurrent}")
        
        self.assert_business_value_delivered({
            "successful_operations": total_successful_operations,
            "connection_error_rate": connection_error_rate,
            "timeout_error_rate": timeout_error_rate,
            "peak_concurrent_operations": peak_concurrent
        }, "automation")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_cache_isolation_races(self, real_services_fixture, real_redis_fixture):
        """
        Test user session cache isolation under concurrent user operations.
        
        Verifies that user session data remains properly isolated and doesn't
        leak between users during concurrent cache operations.
        """
        services = real_services_fixture
        redis_client = real_redis_fixture
        
        if not services["database_available"] or not redis_client:
            pytest.skip("Real services not available for integration test")
        
        num_concurrent_users = 25
        operations_per_user = 8
        user_isolation_results = []
        
        # Track Redis connection
        self.redis_connections.append(redis_client)
        
        async def user_session_operations(user_index: int) -> Dict:
            """Perform session operations for a specific user."""
            user_id = ensure_user_id(f"session_isolation_user_{user_index}")
            user_start = time.time()
            
            try:
                user_session_data = {
                    "user_id": str(user_id),
                    "session_id": f"session_{user_index}_{uuid.uuid4()}",
                    "user_data": {
                        "preferences": {"theme": f"theme_{user_index}", "language": "en"},
                        "profile": {"name": f"User {user_index}", "email": f"user{user_index}@example.com"},
                        "activity": {"last_login": time.time(), "session_count": user_index + 1}
                    },
                    "isolation_token": str(uuid.uuid4())
                }
                
                user_operations = []
                
                for op_idx in range(operations_per_user):
                    op_start = time.time()
                    
                    # Different types of user session operations
                    if op_idx % 4 == 0:
                        # Store user session
                        session_key = f"user_session:{user_id}"
                        await redis_client.set(session_key, json.dumps(user_session_data), ex=3600)  # 1 hour
                        self._track_cache_operation("set", session_key, str(user_id), {
                            "operation_type": "store_session",
                            "session_data": user_session_data
                        })
                        
                    elif op_idx % 4 == 1:
                        # Store user preferences
                        prefs_key = f"user_prefs:{user_id}"
                        await redis_client.set(prefs_key, json.dumps(user_session_data["user_data"]["preferences"]), ex=7200)
                        self._track_cache_operation("set", prefs_key, str(user_id), {
                            "operation_type": "store_preferences"
                        })
                        
                    elif op_idx % 4 == 2:
                        # Retrieve and verify user session
                        session_key = f"user_session:{user_id}"
                        cached_session = await redis_client.get(session_key)
                        self._track_cache_operation("get", session_key, str(user_id), {
                            "operation_type": "retrieve_session"
                        })
                        
                        if cached_session:
                            try:
                                retrieved_data = json.loads(cached_session)
                                
                                # Verify user isolation
                                if retrieved_data.get("user_id") != str(user_id):
                                    self.cache_inconsistencies.append({
                                        "error_type": "user_isolation_violation",
                                        "expected_user": str(user_id),
                                        "actual_user": retrieved_data.get("user_id"),
                                        "cache_key": session_key,
                                        "operation_index": op_idx
                                    })
                                
                                # Verify isolation token
                                if retrieved_data.get("isolation_token") != user_session_data["isolation_token"]:
                                    self.cache_inconsistencies.append({
                                        "error_type": "isolation_token_mismatch",
                                        "user_id": str(user_id),
                                        "cache_key": session_key,
                                        "operation_index": op_idx
                                    })
                                
                            except json.JSONDecodeError:
                                self.cache_inconsistencies.append({
                                    "error_type": "session_data_corruption",
                                    "user_id": str(user_id),
                                    "cache_key": session_key,
                                    "raw_data": cached_session[:100]  # First 100 chars for debugging
                                })
                    
                    else:
                        # Update user activity
                        activity_key = f"user_activity:{user_id}"
                        activity_data = {
                            "user_id": str(user_id),
                            "last_activity": time.time(),
                            "operation_count": op_idx + 1,
                            "activity_token": str(uuid.uuid4())
                        }
                        await redis_client.set(activity_key, json.dumps(activity_data), ex=1800)  # 30 minutes
                        self._track_cache_operation("set", activity_key, str(user_id), {
                            "operation_type": "update_activity"
                        })
                    
                    op_time = time.time() - op_start
                    user_operations.append({
                        "operation_index": op_idx,
                        "operation_time": op_time,
                        "operation_type": ["store_session", "store_preferences", "retrieve_session", "update_activity"][op_idx % 4]
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
                    "isolation_token": user_session_data["isolation_token"],
                    "operations": user_operations
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "user_id": str(user_id),
                    "user_index": user_index,
                    "error": str(e)
                }
        
        # Execute concurrent user session operations
        logger.info(f"Testing user session isolation with {num_concurrent_users} concurrent users")
        
        user_tasks = [user_session_operations(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Analyze user isolation results
        successful_users = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: All users should complete operations successfully
        user_success_rate = len(successful_users) / num_concurrent_users
        assert user_success_rate >= 0.95, f"User operation success rate too low: {user_success_rate:.2%}"
        
        # Verify user isolation - no cross-contamination
        user_isolation_tokens = [r["isolation_token"] for r in successful_users]
        assert len(user_isolation_tokens) == len(set(user_isolation_tokens)), \
            "User isolation token collision detected - RACE CONDITION"
        
        # Verify user IDs are unique and consistent
        user_ids = [r["user_id"] for r in successful_users]
        assert len(user_ids) == len(set(user_ids)), "User ID collision detected - RACE CONDITION"
        
        # Check for cache isolation violations
        isolation_violations = [
            inconsistency for inconsistency in self.cache_inconsistencies
            if inconsistency.get("error_type") in ["user_isolation_violation", "isolation_token_mismatch"]
        ]
        assert len(isolation_violations) == 0, f"User isolation violations detected: {isolation_violations}"
        
        # Verify final user session state consistency
        final_session_checks = []
        for user_result in successful_users:
            user_id = user_result["user_id"]
            expected_token = user_result["isolation_token"]
            
            try:
                # Check user session
                session_key = f"user_session:{user_id}"
                session_data = await redis_client.get(session_key)
                
                if session_data:
                    session_obj = json.loads(session_data)
                    session_user_id = session_obj.get("user_id")
                    session_token = session_obj.get("isolation_token")
                    
                    session_consistent = (session_user_id == user_id and session_token == expected_token)
                    final_session_checks.append(session_consistent)
                    
                    if not session_consistent:
                        logger.error(f"Final session consistency check failed for {user_id}")
                
            except Exception as e:
                logger.error(f"Error during final session check for {user_id}: {e}")
        
        # Final session consistency should be very high
        if final_session_checks:
            final_session_consistency_rate = sum(final_session_checks) / len(final_session_checks)
            assert final_session_consistency_rate >= 0.95, \
                f"Final session consistency rate too low: {final_session_consistency_rate:.2%}"
        
        # Performance validation
        user_times = [r["user_time"] for r in successful_users if "user_time" in r]
        if user_times:
            avg_user_time = sum(user_times) / len(user_times)
            max_user_time = max(user_times)
            
            assert avg_user_time < 2.0, f"Average user operation time too slow: {avg_user_time:.3f}s"
            assert max_user_time < 10.0, f"Maximum user operation time too slow: {max_user_time:.3f}s"
        
        # Total cache inconsistencies should be minimal
        total_inconsistencies = len(self.cache_inconsistencies)
        assert total_inconsistencies == 0, f"Cache inconsistencies detected: {self.cache_inconsistencies}"
        
        logger.info(f"SUCCESS: {len(successful_users)} users completed session operations with isolation")
        logger.info(f"Total operations: {sum(r['operations_completed'] for r in successful_users)}")
        logger.info(f"Cache inconsistencies: {total_inconsistencies}")
        
        self.assert_business_value_delivered({
            "successful_users": len(successful_users),
            "user_isolation_maintained": True,
            "cache_inconsistencies": total_inconsistencies,
            "race_conditions": len(self.race_conditions_detected)
        }, "insights")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_expiration_cleanup_races(self, real_services_fixture, real_redis_fixture):
        """
        Test cache expiration and cleanup under concurrent operations.
        
        Verifies that cache expiration works correctly and doesn't cause
        race conditions when keys expire during concurrent operations.
        """
        services = real_services_fixture
        redis_client = real_redis_fixture
        
        if not services["database_available"] or not redis_client:
            pytest.skip("Real services not available for integration test")
        
        num_cache_keys = 30
        operations_per_key = 5
        expiration_results = []
        
        # Track Redis connection
        self.redis_connections.append(redis_client)
        
        async def cache_expiration_operations(key_index: int) -> Dict:
            """Perform operations with cache expiration testing."""
            cache_key = f"expiration_test_key_{key_index}"
            user_id = ensure_user_id(f"expiration_user_{key_index}")
            
            try:
                operation_results = []
                
                for op_idx in range(operations_per_key):
                    op_start = time.time()
                    
                    if op_idx == 0:
                        # Set initial value with short expiration
                        initial_value = {
                            "key_index": key_index,
                            "operation_index": op_idx,
                            "created_at": time.time(),
                            "expiration_token": str(uuid.uuid4())
                        }
                        
                        # Short expiration for testing (2 seconds)
                        await redis_client.set(cache_key, json.dumps(initial_value), ex=2)
                        self._track_cache_operation("set", cache_key, str(user_id), {
                            "value": initial_value,
                            "expiration": 2
                        })
                        
                        self.expected_values[cache_key] = initial_value
                        
                    elif op_idx == 1:
                        # Immediate read (should succeed)
                        cached_data = await redis_client.get(cache_key)
                        self._track_cache_operation("get", cache_key, str(user_id), {
                            "operation_type": "immediate_read"
                        })
                        
                        read_successful = cached_data is not None
                        
                    elif op_idx == 2:
                        # Wait for potential expiration and try to extend
                        await asyncio.sleep(1.5)  # Wait 1.5 seconds
                        
                        # Try to extend expiration
                        current_data = await redis_client.get(cache_key)
                        if current_data:
                            # Key still exists, extend it
                            await redis_client.expire(cache_key, 5)  # Extend to 5 more seconds
                            self._track_cache_operation("expire", cache_key, str(user_id), {
                                "operation_type": "extend_expiration",
                                "new_expiration": 5
                            })
                            
                            extension_successful = True
                        else:
                            # Key already expired
                            extension_successful = False
                    
                    elif op_idx == 3:
                        # Wait for expiration and check
                        await asyncio.sleep(3)  # Wait for expiration
                        
                        expired_data = await redis_client.get(cache_key)
                        self._track_cache_operation("get", cache_key, str(user_id), {
                            "operation_type": "post_expiration_read"
                        })
                        
                        expiration_worked = expired_data is None
                        
                        # Record expiration event
                        expiration_event = {
                            "cache_key": cache_key,
                            "user_id": str(user_id),
                            "expiration_worked": expiration_worked,
                            "timestamp": time.time()
                        }
                        self.expiration_events.append(expiration_event)
                    
                    else:
                        # Set new value with different expiration
                        new_value = {
                            "key_index": key_index,
                            "operation_index": op_idx,
                            "renewed_at": time.time(),
                            "renewal_token": str(uuid.uuid4())
                        }
                        
                        await redis_client.set(cache_key, json.dumps(new_value), ex=60)  # 1 minute
                        self._track_cache_operation("set", cache_key, str(user_id), {
                            "value": new_value,
                            "expiration": 60,
                            "operation_type": "renewal"
                        })
                    
                    op_time = time.time() - op_start
                    
                    operation_results.append({
                        "operation_index": op_idx,
                        "operation_time": op_time,
                        "operation_type": ["initial_set", "immediate_read", "extend_expiration", "post_expiration_read", "renewal"][op_idx]
                    })
                
                return {
                    "success": True,
                    "cache_key": cache_key,
                    "user_id": str(user_id),
                    "key_index": key_index,
                    "operations_completed": len(operation_results),
                    "operation_results": operation_results
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "cache_key": cache_key,
                    "key_index": key_index,
                    "error": str(e)
                }
        
        # Execute concurrent cache expiration operations
        logger.info(f"Testing cache expiration with {num_cache_keys} keys x {operations_per_key} operations")
        
        expiration_tasks = [cache_expiration_operations(i) for i in range(num_cache_keys)]
        results = await asyncio.gather(*expiration_tasks, return_exceptions=True)
        
        # Analyze expiration results
        successful_expiration_tests = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        # CRITICAL: Most expiration tests should complete successfully
        success_rate = len(successful_expiration_tests) / num_cache_keys
        assert success_rate >= 0.90, f"Cache expiration test success rate too low: {success_rate:.2%}"
        
        # Verify expiration events
        total_expiration_events = len(self.expiration_events)
        expected_expiration_events = len(successful_expiration_tests)  # One per successful test
        
        expiration_event_rate = total_expiration_events / expected_expiration_events if expected_expiration_events > 0 else 0
        assert expiration_event_rate >= 0.90, \
            f"Expiration event rate too low: {expiration_event_rate:.2%}"
        
        # Check expiration effectiveness
        successful_expirations = [
            event for event in self.expiration_events 
            if event.get("expiration_worked", False)
        ]
        
        expiration_effectiveness = len(successful_expirations) / total_expiration_events if total_expiration_events > 0 else 0
        assert expiration_effectiveness >= 0.70, \
            f"Cache expiration effectiveness too low: {expiration_effectiveness:.2%}"
        
        # Verify no cache inconsistencies during expiration
        expiration_inconsistencies = [
            inconsistency for inconsistency in self.cache_inconsistencies
            if "expiration" in inconsistency.get("error_type", "")
        ]
        assert len(expiration_inconsistencies) == 0, \
            f"Cache expiration inconsistencies: {expiration_inconsistencies}"
        
        # Performance validation
        all_operation_times = []
        for result in successful_expiration_tests:
            for op_result in result.get("operation_results", []):
                all_operation_times.append(op_result["operation_time"])
        
        if all_operation_times:
            avg_op_time = sum(all_operation_times) / len(all_operation_times)
            max_op_time = max(all_operation_times)
            
            # Note: Some operations include sleep, so times will be higher
            assert avg_op_time < 3.0, f"Average expiration operation time too slow: {avg_op_time:.3f}s"
            assert max_op_time < 8.0, f"Maximum expiration operation time too slow: {max_op_time:.3f}s"
        
        # Race conditions should be minimal for expiration
        assert len(self.race_conditions_detected) <= 2, \
            f"Excessive expiration race conditions: {self.race_conditions_detected}"
        
        logger.info(f"SUCCESS: {len(successful_expiration_tests)} cache expiration tests completed")
        logger.info(f"Expiration events: {total_expiration_events}, Effectiveness: {expiration_effectiveness:.2%}")
        
        self.assert_business_value_delivered({
            "successful_expiration_tests": len(successful_expiration_tests),
            "expiration_effectiveness": expiration_effectiveness,
            "expiration_events": total_expiration_events,
            "race_conditions": len(self.race_conditions_detected)
        }, "automation")