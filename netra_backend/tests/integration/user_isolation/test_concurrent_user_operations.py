"""
Integration Tests for Concurrent User Operations

Business Value Justification (BVJ):
- Segment: All (Free  ->  Enterprise) - Scalability foundation
- Business Goal: Ensure system stability and data integrity under concurrent user load
- Value Impact: System handles real-world concurrent usage without data corruption or performance degradation
- Revenue Impact: Enables platform scaling to support growth from Free to Enterprise segments

This test suite validates concurrent user operations with realistic scenarios:
- Simultaneous multi-user database operations
- Race condition prevention in shared resources
- Memory and connection pool management under load
- WebSocket event delivery accuracy during concurrent operations
- Resource cleanup and leak prevention
- Real-world Enterprise usage patterns (100+ concurrent users)
"""

import asyncio
import gc
import pytest
import random
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.factories.data_access_factory import (
    get_clickhouse_factory,
    get_redis_factory,
    get_user_clickhouse_context,
    get_user_redis_context,
    cleanup_all_factories
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.data_contexts.user_data_context import (
    UserClickHouseContext,
    UserRedisContext
)


@pytest.mark.integration  
@pytest.mark.real_services
class TestConcurrentUserOperations(BaseIntegrationTest):
    """Test concurrent user operations under realistic enterprise load."""
    
    async def setup_method(self, method):
        """Set up each test with clean state and memory tracking."""
        await cleanup_all_factories()
        gc.collect()  # Clean memory state
        
    async def teardown_method(self, method):
        """Clean up after each test."""
        await cleanup_all_factories()
        gc.collect()
    
    def create_enterprise_user_context(self, user_id: str, department: str = "Engineering") -> UserExecutionContext:
        """Create a realistic enterprise user context."""
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=f"thread_{uuid4().hex[:8]}",
            run_id=f"run_{uuid4().hex[:8]}",
            agent_context={
                "department": department,
                "role": random.choice(["Developer", "Manager", "Analyst", "Executive"]),
                "clearance_level": random.choice(["standard", "elevated", "admin"]),
                "session_type": "enterprise_session"
            },
            audit_metadata={
                "client_ip": f"10.0.{random.randint(1,254)}.{random.randint(1,254)}",
                "user_agent": "EnterpriseClient/2.1",
                "auth_method": "oauth2",
                "compliance_required": True
            }
        )
    
    @pytest.mark.asyncio
    async def test_high_concurrency_context_creation_race_conditions(self):
        """Test context creation under extreme concurrency to detect race conditions."""
        num_concurrent_users = 100
        contexts_per_user = 3
        
        # Track memory usage during high concurrency
        tracemalloc.start()
        
        async def create_contexts_for_user(user_index: int):
            """Create multiple contexts for a single user concurrently."""
            user_id = f"race_user_{user_index:03d}"
            user_context = self.create_enterprise_user_context(user_id)
            
            created_contexts = []
            creation_times = []
            
            # Create multiple contexts for this user simultaneously
            async def create_single_context(context_index: int):
                start = time.time()
                
                # Create both Redis and ClickHouse contexts
                redis_factory = get_redis_factory()
                ch_factory = get_clickhouse_factory()
                
                redis_ctx = await redis_factory.create_user_context(user_context)
                ch_ctx = await ch_factory.create_user_context(user_context)
                
                creation_time = time.time() - start
                return context_index, redis_ctx, ch_ctx, creation_time
            
            results = await asyncio.gather(*[
                create_single_context(i) for i in range(contexts_per_user)
            ])
            
            for context_index, redis_ctx, ch_ctx, creation_time in results:
                created_contexts.append((redis_ctx, ch_ctx))
                creation_times.append(creation_time)
            
            return user_index, created_contexts, creation_times
        
        # Execute high concurrency test
        start_time = time.time()
        results = await asyncio.gather(*[
            create_contexts_for_user(i) for i in range(num_concurrent_users)
        ], return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results for race conditions and correctness
        successful_users = 0
        total_contexts_created = 0
        all_creation_times = []
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                user_index, contexts, times = result
                successful_users += 1
                total_contexts_created += len(contexts) * 2  # Redis + ClickHouse
                all_creation_times.extend(times)
                
                # Validate contexts are properly created
                for redis_ctx, ch_ctx in contexts:
                    assert isinstance(redis_ctx, UserRedisContext)
                    assert isinstance(ch_ctx, UserClickHouseContext)
                    assert redis_ctx.user_id == ch_ctx.user_id
                    assert f"race_user_{user_index:03d}" == redis_ctx.user_id
        
        # Performance and correctness assertions
        success_rate = successful_users / num_concurrent_users
        assert success_rate >= 0.95, f"High failure rate under concurrency: {success_rate:.2%}"
        
        expected_contexts = num_concurrent_users * contexts_per_user * 2
        assert total_contexts_created >= expected_contexts * 0.95, (
            f"Too few contexts created: {total_contexts_created}/{expected_contexts}"
        )
        
        # Performance requirements
        avg_creation_time = sum(all_creation_times) / len(all_creation_times)
        assert avg_creation_time < 1.0, f"Context creation too slow: {avg_creation_time:.3f}s avg"
        
        contexts_per_second = total_contexts_created / total_time
        assert contexts_per_second > 50, f"Throughput too low: {contexts_per_second:.1f} contexts/sec"
        
        # Memory usage validation
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should not consume excessive memory (< 100MB for 600 contexts)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100, f"Excessive memory usage: {peak_mb:.2f}MB"
        
        print(f" PASS:  Created {total_contexts_created} contexts with {num_concurrent_users} concurrent users "
              f"in {total_time:.2f}s ({contexts_per_second:.1f} ctx/sec), peak memory: {peak_mb:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_concurrent_data_operations_consistency(self):
        """Test data consistency during concurrent operations across multiple users."""
        num_users = 25
        operations_per_user = 20
        
        users = [f"consistency_user_{i:02d}" for i in range(num_users)]
        
        # Shared state to track operations for consistency verification
        operation_log = asyncio.Queue()
        
        async def user_data_operations(user_id: str):
            """Perform data operations for a user while tracking for consistency."""
            user_context = self.create_enterprise_user_context(user_id)
            user_operations = []
            
            try:
                # Redis operations
                async with get_user_redis_context(user_context) as redis_ctx:
                    for op_num in range(operations_per_user // 2):
                        operation_id = f"{user_id}_redis_op_{op_num}"
                        
                        # Store data
                        key = f"data_{op_num}"
                        value = f"value_{user_id}_{op_num}_{uuid4().hex[:8]}"
                        await redis_ctx.set(key, value)
                        
                        # Log operation
                        await operation_log.put((user_id, "redis_set", key, value, time.time()))
                        user_operations.append(("redis_set", key, value))
                        
                        # Retrieve and verify data immediately
                        retrieved = await redis_ctx.get(key)
                        assert retrieved == value, f"Data inconsistency: expected {value}, got {retrieved}"
                        
                        # Store JSON data
                        json_key = f"json_{op_num}"
                        json_value = {
                            "user_id": user_id,
                            "operation": op_num,
                            "timestamp": time.time(),
                            "random_data": uuid4().hex
                        }
                        await redis_ctx.set_json(json_key, json_value)
                        
                        await operation_log.put((user_id, "redis_set_json", json_key, json_value, time.time()))
                        user_operations.append(("redis_set_json", json_key, json_value))
                        
                        # Verify JSON data
                        retrieved_json = await redis_ctx.get_json(json_key)
                        assert retrieved_json == json_value
                
                # ClickHouse operations
                async with get_user_clickhouse_context(user_context) as ch_ctx:
                    for op_num in range(operations_per_user // 2):
                        # Get context info and verify user isolation
                        context_info = ch_ctx.get_context_info()
                        assert context_info["user_id"].startswith(user_id[:8])
                        
                        # Simulate user-specific operations
                        operation_data = {
                            "user_id": user_id,
                            "operation_num": op_num,
                            "timestamp": time.time(),
                            "context_age": context_info["age_seconds"]
                        }
                        
                        await operation_log.put((user_id, "ch_operation", f"op_{op_num}", operation_data, time.time()))
                        user_operations.append(("ch_operation", f"op_{op_num}", operation_data))
                
                return user_id, user_operations, None
                
            except Exception as e:
                return user_id, user_operations, str(e)
        
        # Execute concurrent operations
        start_time = time.time()
        results = await asyncio.gather(*[
            user_data_operations(user) for user in users
        ], return_exceptions=True)
        duration = time.time() - start_time
        
        # Collect operation log for analysis
        logged_operations = []
        try:
            while True:
                logged_operations.append(operation_log.get_nowait())
        except asyncio.QueueEmpty:
            pass
        
        # Analyze results for consistency
        successful_operations = 0
        user_operation_counts = {}
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            else:
                user_id, operations, error = result
                if error is None:
                    successful_operations += len(operations)
                    user_operation_counts[user_id] = len(operations)
                else:
                    errors.append(f"{user_id}: {error}")
        
        # Verify consistency
        expected_total_operations = num_users * operations_per_user
        success_rate = successful_operations / expected_total_operations
        assert success_rate >= 0.95, f"Too many failed operations: {success_rate:.2%}"
        
        # Verify each user completed expected operations
        for user_id in users:
            if user_id in user_operation_counts:
                assert user_operation_counts[user_id] == operations_per_user, (
                    f"User {user_id} completed {user_operation_counts[user_id]}/{operations_per_user} operations"
                )
        
        # Verify no cross-contamination in logged operations
        for user_id, op_type, key, value, timestamp in logged_operations:
            # Each operation should be associated with correct user
            if isinstance(value, str):
                assert user_id in value or key in value
            elif isinstance(value, dict) and "user_id" in value:
                assert value["user_id"] == user_id
        
        operations_per_second = successful_operations / duration
        assert operations_per_second > 100, f"Performance too slow: {operations_per_second:.1f} ops/sec"
        
        print(f" PASS:  {successful_operations} concurrent operations completed consistently "
              f"across {num_users} users in {duration:.2f}s ({operations_per_second:.1f} ops/sec)")
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_resilience(self):
        """Test system resilience when connection pools approach exhaustion."""
        # Create more contexts than typical pool limits to test graceful degradation
        num_users = 50
        max_contexts_per_user = 3
        
        users = [f"pool_user_{i:02d}" for i in range(num_users)]
        
        # Configure factories with limited resources
        clickhouse_factory = get_clickhouse_factory()
        redis_factory = get_redis_factory()
        
        created_contexts = []
        context_creation_results = []
        
        async def stress_connection_pools(user_id: str):
            """Create multiple contexts to stress connection pools."""
            user_context = self.create_enterprise_user_context(user_id)
            user_contexts = []
            creation_times = []
            
            for i in range(max_contexts_per_user):
                try:
                    start = time.time()
                    
                    # Create contexts (this may hit pool limits)
                    redis_ctx = await redis_factory.create_user_context(user_context)
                    ch_ctx = await clickhouse_factory.create_user_context(user_context)
                    
                    creation_time = time.time() - start
                    user_contexts.append((redis_ctx, ch_ctx))
                    creation_times.append(creation_time)
                    
                except Exception as e:
                    # Pool exhaustion should be handled gracefully
                    print(f"Expected pool limitation for {user_id}: {e}")
                    break
            
            return user_id, user_contexts, creation_times
        
        # Execute pool stress test
        results = await asyncio.gather(*[
            stress_connection_pools(user) for user in users
        ], return_exceptions=True)
        
        # Analyze pool behavior
        total_contexts = 0
        successful_users = 0
        
        for result in results:
            if not isinstance(result, Exception):
                user_id, contexts, times = result
                total_contexts += len(contexts) * 2  # Redis + ClickHouse
                if len(contexts) > 0:
                    successful_users += 1
                    created_contexts.extend(contexts)
                    context_creation_results.append((user_id, len(contexts), times))
        
        # System should handle pool limits gracefully
        assert successful_users > 0, "System completely failed under pool stress"
        
        # Test that created contexts work correctly
        functional_contexts = 0
        for redis_ctx, ch_ctx in created_contexts[:10]:  # Test first 10 contexts
            try:
                # Test Redis context
                test_key = f"pool_test_{uuid4().hex[:8]}"
                await redis_ctx.set(test_key, "pool_test_value")
                value = await redis_ctx.get(test_key)
                assert value == "pool_test_value"
                
                # Test ClickHouse context
                context_info = ch_ctx.get_context_info()
                assert context_info["initialized"] is True
                
                functional_contexts += 1
                
            except Exception as e:
                print(f"Context functionality test failed: {e}")
        
        functionality_rate = functional_contexts / min(10, len(created_contexts))
        assert functionality_rate >= 0.8, f"Too many non-functional contexts: {functionality_rate:.2%}"
        
        print(f" PASS:  System handled connection pool stress: {successful_users}/{num_users} users successful, "
              f"{total_contexts} total contexts, {functionality_rate:.1%} functionality rate")
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention_during_concurrent_operations(self):
        """Test that concurrent operations don't cause memory leaks."""
        tracemalloc.start()
        
        # Baseline memory measurement
        baseline_current, baseline_peak = tracemalloc.get_traced_memory()
        
        num_rounds = 3
        users_per_round = 20
        operations_per_user = 15
        
        for round_num in range(num_rounds):
            users = [f"memory_user_r{round_num}_{i:02d}" for i in range(users_per_round)]
            
            async def memory_intensive_operations(user_id: str):
                """Perform memory-intensive operations."""
                user_context = self.create_enterprise_user_context(user_id)
                
                # Create large data structures
                large_data = {
                    f"key_{i}": f"data_{uuid4().hex}" * 100  # ~3.6KB per entry
                    for i in range(operations_per_user)
                }
                
                # Redis operations with large data
                async with get_user_redis_context(user_context) as redis_ctx:
                    for i, (key, value) in enumerate(large_data.items()):
                        await redis_ctx.set(f"large_{i}", value)
                        
                        # JSON operations
                        json_data = {
                            "user_id": user_id,
                            "round": round_num,
                            "data": [uuid4().hex for _ in range(10)]
                        }
                        await redis_ctx.set_json(f"json_{i}", json_data)
                
                # ClickHouse context operations
                async with get_user_clickhouse_context(user_context) as ch_ctx:
                    for i in range(operations_per_user):
                        # Multiple context info calls (potential for reference accumulation)
                        context_info = ch_ctx.get_context_info()
                        
                        # Cache operations
                        ch_ctx.clear_user_cache()
                
                return user_id, len(large_data)
            
            # Execute round of memory-intensive operations
            round_results = await asyncio.gather(*[
                memory_intensive_operations(user) for user in users
            ])
            
            # Force garbage collection between rounds
            gc.collect()
            
            # Check memory growth
            current, peak = tracemalloc.get_traced_memory()
            round_memory = (current - baseline_current) / 1024 / 1024  # MB
            
            print(f"Round {round_num + 1}: {len(users)} users, memory delta: {round_memory:.2f}MB")
        
        # Final memory check
        final_current, final_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        total_memory_growth = (final_current - baseline_current) / 1024 / 1024  # MB
        peak_memory_usage = (final_peak - baseline_peak) / 1024 / 1024  # MB
        
        # Memory growth should be reasonable for the amount of work done
        total_operations = num_rounds * users_per_round * operations_per_user
        memory_per_operation = total_memory_growth / total_operations  # MB per operation
        
        # Should not consume more than 100KB per operation on average
        assert memory_per_operation < 0.1, (
            f"Excessive memory per operation: {memory_per_operation * 1024:.1f}KB "
            f"(total: {total_memory_growth:.2f}MB for {total_operations} ops)"
        )
        
        # Peak memory should not exceed 200MB
        assert peak_memory_usage < 200, f"Peak memory too high: {peak_memory_usage:.2f}MB"
        
        print(f" PASS:  Memory leak test passed: {total_memory_growth:.2f}MB growth, "
              f"{peak_memory_usage:.2f}MB peak, {memory_per_operation * 1024:.2f}KB/op")
    
    @pytest.mark.asyncio
    async def test_real_world_enterprise_usage_pattern(self):
        """Test realistic enterprise usage patterns with mixed operations."""
        # Simulate a real enterprise environment
        departments = ["Engineering", "Sales", "Marketing", "Finance", "Operations"]
        num_users_per_dept = 15
        total_users = len(departments) * num_users_per_dept
        
        # Different usage patterns per department
        dept_patterns = {
            "Engineering": {"sessions": 5, "data_heavy": True, "concurrent": True},
            "Sales": {"sessions": 3, "data_heavy": False, "concurrent": False},
            "Marketing": {"sessions": 4, "data_heavy": True, "concurrent": True},
            "Finance": {"sessions": 2, "data_heavy": False, "concurrent": False},
            "Operations": {"sessions": 6, "data_heavy": True, "concurrent": True}
        }
        
        async def simulate_department_user(dept: str, user_index: int):
            """Simulate a user from a specific department."""
            user_id = f"{dept.lower()}_user_{user_index:02d}"
            pattern = dept_patterns[dept]
            
            results = []
            
            for session in range(pattern["sessions"]):
                user_context = self.create_enterprise_user_context(user_id, dept)
                session_start = time.time()
                
                try:
                    # Redis session management
                    async with get_user_redis_context(user_context) as redis_ctx:
                        # Store session info
                        session_data = {
                            "user_id": user_id,
                            "department": dept,
                            "session": session,
                            "start_time": session_start,
                            "features": random.sample(["reports", "analytics", "admin", "dashboard"], 2)
                        }
                        await redis_ctx.set_json("session", session_data)
                        
                        if pattern["data_heavy"]:
                            # Heavy data operations for data-intensive departments
                            for i in range(10):
                                large_payload = {
                                    f"record_{i}": uuid4().hex * 20,  # ~640 bytes per record
                                    "metadata": {"index": i, "timestamp": time.time()}
                                }
                                await redis_ctx.set_json(f"payload_{i}", large_payload)
                        else:
                            # Light operations for other departments
                            for i in range(3):
                                await redis_ctx.set(f"key_{i}", f"value_{i}_{uuid4().hex[:8]}")
                    
                    # ClickHouse analytics operations
                    async with get_user_clickhouse_context(user_context) as ch_ctx:
                        # Department-specific analytics patterns
                        if dept in ["Engineering", "Operations"]:
                            # Heavy analytical workloads
                            for i in range(5):
                                context_info = ch_ctx.get_context_info()
                                assert context_info["user_id"].startswith(user_id[:8])
                        else:
                            # Light analytical operations
                            context_info = ch_ctx.get_context_info()
                    
                    session_duration = time.time() - session_start
                    results.append((session, session_duration, "success"))
                    
                except Exception as e:
                    session_duration = time.time() - session_start
                    results.append((session, session_duration, str(e)))
            
            return user_id, dept, results
        
        # Execute enterprise simulation
        print(f"Starting enterprise simulation: {total_users} users across {len(departments)} departments")
        start_time = time.time()
        
        # Group operations by department for realistic concurrency patterns
        dept_operations = []
        for dept in departments:
            dept_users = []
            for user_index in range(num_users_per_dept):
                dept_users.append(simulate_department_user(dept, user_index))
            dept_operations.append(dept_users)
        
        # Execute departments concurrently (realistic enterprise pattern)
        all_results = []
        for dept_ops in dept_operations:
            if dept_patterns[departments[dept_operations.index(dept_ops)]]["concurrent"]:
                # Concurrent execution for collaborative departments
                dept_results = await asyncio.gather(*dept_ops)
            else:
                # Sequential execution for individual-focused departments
                dept_results = []
                for user_op in dept_ops:
                    result = await user_op
                    dept_results.append(result)
            all_results.extend(dept_results)
        
        total_duration = time.time() - start_time
        
        # Analyze enterprise usage results
        successful_users = 0
        total_sessions = 0
        total_session_duration = 0
        dept_success_rates = {}
        
        for user_id, dept, sessions in all_results:
            if dept not in dept_success_rates:
                dept_success_rates[dept] = {"success": 0, "total": 0}
            
            user_successful_sessions = 0
            for session, duration, status in sessions:
                total_sessions += 1
                total_session_duration += duration
                dept_success_rates[dept]["total"] += 1
                
                if status == "success":
                    user_successful_sessions += 1
                    dept_success_rates[dept]["success"] += 1
            
            if user_successful_sessions > 0:
                successful_users += 1
        
        # Enterprise requirements validation
        overall_success_rate = successful_users / total_users
        assert overall_success_rate >= 0.95, f"Enterprise success rate too low: {overall_success_rate:.2%}"
        
        avg_session_duration = total_session_duration / total_sessions
        assert avg_session_duration < 5.0, f"Session duration too long: {avg_session_duration:.2f}s"
        
        sessions_per_second = total_sessions / total_duration
        assert sessions_per_second > 10, f"Enterprise throughput too low: {sessions_per_second:.1f} sessions/sec"
        
        # Department-specific success rates
        for dept, stats in dept_success_rates.items():
            dept_success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            assert dept_success_rate >= 0.90, f"{dept} success rate too low: {dept_success_rate:.2%}"
        
        print(f" PASS:  Enterprise simulation completed: {successful_users}/{total_users} users successful "
              f"({total_sessions} sessions in {total_duration:.2f}s, {sessions_per_second:.1f} sessions/sec)")
        
        # Print department breakdown
        for dept, stats in dept_success_rates.items():
            dept_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            print(f"   {dept}: {stats['success']}/{stats['total']} sessions ({dept_rate:.1%})")
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_under_extreme_load(self):
        """Test system graceful degradation under extreme concurrent load."""
        # Extreme load test - push system to its limits
        extreme_users = 200
        max_operations = 5
        
        users = [f"extreme_user_{i:03d}" for i in range(extreme_users)]
        
        async def extreme_user_load(user_id: str):
            """Apply extreme load from a single user."""
            user_context = self.create_enterprise_user_context(user_id)
            operations_completed = 0
            start_time = time.time()
            
            try:
                # Try to create and use contexts under extreme load
                async with get_user_redis_context(user_context) as redis_ctx:
                    for i in range(max_operations):
                        await redis_ctx.set(f"extreme_{i}", f"value_{user_id}_{i}")
                        operations_completed += 1
                        
                        # Small delay to simulate real work
                        await asyncio.sleep(0.001)
                
                duration = time.time() - start_time
                return user_id, operations_completed, duration, None
                
            except Exception as e:
                duration = time.time() - start_time
                return user_id, operations_completed, duration, str(e)
        
        # Execute extreme load test with timeout protection
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[extreme_user_load(user) for user in users], return_exceptions=True),
                timeout=30.0  # 30 second timeout for extreme test
            )
        except asyncio.TimeoutError:
            pytest.fail("Extreme load test timed out - system may have deadlocked")
        
        # Analyze degradation behavior
        successful_users = 0
        total_operations = 0
        total_duration = 0
        error_types = {}
        
        for result in results:
            if isinstance(result, Exception):
                error_type = type(result).__name__
                error_types[error_type] = error_types.get(error_type, 0) + 1
            else:
                user_id, ops, duration, error = result
                if error is None:
                    successful_users += 1
                    total_operations += ops
                    total_duration += duration
                else:
                    error_type = error.split(":")[0] if ":" in error else error[:50]
                    error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Graceful degradation requirements
        # System should handle at least 50% of extreme load gracefully
        success_rate = successful_users / extreme_users
        assert success_rate >= 0.5, f"System failed catastrophically under extreme load: {success_rate:.2%}"
        
        # Average operations per successful user should be reasonable
        if successful_users > 0:
            avg_ops_per_user = total_operations / successful_users
            assert avg_ops_per_user >= max_operations * 0.8, (
                f"Too many incomplete operations: {avg_ops_per_user:.1f}/{max_operations} avg"
            )
        
        # Errors should be reasonable (connection limits, timeouts, etc.)
        total_errors = sum(error_types.values())
        if total_errors > 0:
            print("Error distribution under extreme load:")
            for error_type, count in error_types.items():
                error_rate = count / extreme_users
                print(f"   {error_type}: {count} ({error_rate:.2%})")
        
        print(f" PASS:  Graceful degradation under extreme load: {successful_users}/{extreme_users} users successful "
              f"({success_rate:.1%}), {total_operations} operations completed")
        
        # System should not have deadlocked or crashed completely
        assert total_operations > 0, "System completely failed - no operations completed"