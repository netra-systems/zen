"""
Performance & Load Testing: Database Connection Pooling Under Load

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure efficient database resource utilization under concurrent load
- Value Impact: Users experience consistent database performance without connection bottlenecks
- Strategic Impact: Proper connection pooling enables cost-effective scaling and prevents database overload

CRITICAL: This test validates database connection pooling behavior, connection reuse efficiency,
and database performance under various concurrent load scenarios.
"""

import asyncio
import pytest
import time
import statistics
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import psutil
import os
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


@dataclass
class ConnectionPoolMetrics:
    """Database connection pool performance metrics."""
    pool_name: str
    concurrent_connections: int
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_operation_time: float
    max_operation_time: float
    min_operation_time: float
    p95_operation_time: float
    connection_acquisition_times: List[float]
    connection_reuse_rate: float
    pool_exhaustion_events: int
    timeout_events: int
    errors: List[str] = field(default_factory=list)


@dataclass
class DatabaseLoadTestResult:
<<<<<<< HEAD
    """Results from database load testing."""
=======
    \"\"\"Results from database load testing.\"\"\"
>>>>>>> a2eccc9923a36b1445ee11732d4a1fb88b08f53d
    test_name: str
    duration: float
    operations_per_second: float
    connection_metrics: ConnectionPoolMetrics
    resource_usage: Dict[str, Any]
    performance_degradation: float


class TestDatabaseConnectionPoolingPerformance(BaseIntegrationTest):
<<<<<<< HEAD
    """Test database connection pooling performance under load."""
=======
    \"\"\"Test database connection pooling performance under load.\"\"\"
>>>>>>> a2eccc9923a36b1445ee11732d4a1fb88b08f53d
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_connection_pool_concurrent_access(self, real_services_fixture):
        \"\"\"
        Test database connection pool performance with concurrent access.
        
        Performance SLA:
        - Connection acquisition: <50ms (p95)
        - Operation completion: <100ms (p95)
        - Connection reuse rate: >80%
        - No pool exhaustion under 50 concurrent operations
        \"\"\"
        db = real_services_fixture[\"db\"]
        concurrent_operations = 50
        operations_per_connection = 10
        
        connection_metrics = ConnectionPoolMetrics(
            pool_name=\"primary_db_pool\",
            concurrent_connections=concurrent_operations,
            total_operations=0,
            successful_operations=0,
            failed_operations=0,
            average_operation_time=0,
            max_operation_time=0,
            min_operation_time=float('inf'),
            p95_operation_time=0,
            connection_acquisition_times=[],
            connection_reuse_rate=0,
            pool_exhaustion_events=0,
            timeout_events=0
        )
        
        operation_times = []
        
        async def database_operation_cycle(operation_id: int) -> Dict[str, Any]:
<<<<<<< HEAD
            """Perform a cycle of database operations."""
=======
            \"\"\"Perform a cycle of database operations.\"\"\"
>>>>>>> a2eccc9923a36b1445ee11732d4a1fb88b08f53d
            cycle_result = {
                \"operation_id\": operation_id,
                \"operations_completed\": 0,
                \"total_time\": 0,
                \"errors\": []
            }
            
            cycle_start = time.time()
            
            try:
                for i in range(operations_per_connection):
                    operation_start = time.time()
                    
                    # Connection acquisition time measurement
                    acquisition_start = time.time()
                    
                    # Simulate various database operations
                    operation_type = i % 4
                    if operation_type == 0:
                        # Simple SELECT query
                        result = await db.execute(\"SELECT 1 as test_value, $1 as operation_id\", operation_id)
                    elif operation_type == 1:
                        # SELECT with WHERE clause
                        result = await db.execute(\"SELECT $1 as operation_id WHERE $1 > 0\", operation_id)
                    elif operation_type == 2:
                        # Multi-row SELECT simulation
                        result = await db.execute(\"SELECT generate_series(1, $1) as sequence, $2 as operation_id\", min(5, operation_id % 10 + 1), operation_id)
                    else:
                        # Complex query simulation
                        result = await db.execute(\"SELECT COUNT(*) as count, $1 as operation_id FROM generate_series(1, $2) GROUP BY $1\", operation_id, min(10, operation_id % 20 + 1))
                    
                    acquisition_time = time.time() - acquisition_start
                    connection_metrics.connection_acquisition_times.append(acquisition_time)
                    
                    operation_time = time.time() - operation_start
                    operation_times.append(operation_time)
                    
                    cycle_result[\"operations_completed\"] += 1
                    
                    # Small delay to simulate processing
                    await asyncio.sleep(0.001)
                    
            except asyncio.TimeoutError:
                connection_metrics.timeout_events += 1
                cycle_result[\"errors\"].append(f\"Timeout in operation cycle {operation_id}\")
            except Exception as e:
                cycle_result[\"errors\"].append(f\"Error in operation cycle {operation_id}: {str(e)}\")
            
            cycle_result[\"total_time\"] = time.time() - cycle_start
            return cycle_result
        
        # Execute concurrent database operations
        test_start = time.time()
        
        operation_tasks = [
            database_operation_cycle(i)
            for i in range(concurrent_operations)
        ]
        
        results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        test_duration = time.time() - test_start
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and not r.get(\"errors\")]
        failed_results = [r for r in results if isinstance(r, dict) and r.get(\"errors\")]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        # Calculate metrics
        connection_metrics.total_operations = sum(r.get(\"operations_completed\", 0) for r in results if isinstance(r, dict))
        connection_metrics.successful_operations = sum(r.get(\"operations_completed\", 0) for r in successful_results)
        connection_metrics.failed_operations = len(failed_results) + len(exceptions)
        
        if operation_times:
            connection_metrics.average_operation_time = statistics.mean(operation_times)
            connection_metrics.max_operation_time = max(operation_times)
            connection_metrics.min_operation_time = min(operation_times)
            
            # Calculate p95
            operation_times_ms = [t * 1000 for t in operation_times]
            operation_times_ms.sort()
            p95_index = int(len(operation_times_ms) * 0.95)
            connection_metrics.p95_operation_time = operation_times_ms[p95_index] if operation_times_ms else 0
        
        # Calculate connection acquisition metrics
        if connection_metrics.connection_acquisition_times:
            acquisition_times_ms = [t * 1000 for t in connection_metrics.connection_acquisition_times]
            acquisition_p95_index = int(len(acquisition_times_ms) * 0.95)
            acquisition_p95 = acquisition_times_ms[acquisition_p95_index] if acquisition_times_ms else 0
        else:
            acquisition_p95 = 0
        
        # Calculate operations per second
        operations_per_second = connection_metrics.total_operations / test_duration if test_duration > 0 else 0
        
        # Performance assertions
        success_rate = connection_metrics.successful_operations / connection_metrics.total_operations if connection_metrics.total_operations > 0 else 0
        
        assert acquisition_p95 < 50, f\"Connection acquisition p95 {acquisition_p95:.1f}ms exceeds 50ms SLA\"
        assert connection_metrics.p95_operation_time < 100, f\"Operation p95 time {connection_metrics.p95_operation_time:.1f}ms exceeds 100ms SLA\"
        assert success_rate >= 0.95, f\"Success rate {success_rate:.3f} below 95% threshold\"
        assert connection_metrics.pool_exhaustion_events == 0, f\"Pool exhaustion events detected: {connection_metrics.pool_exhaustion_events}\"
        assert connection_metrics.timeout_events <= 2, f\"Too many timeout events: {connection_metrics.timeout_events}\"
        
        print(f\"✅ Database Connection Pool Performance Results:\")
        print(f\"   Concurrent operations: {concurrent_operations}\")
        print(f\"   Total operations: {connection_metrics.total_operations}\")
        print(f\"   Successful operations: {connection_metrics.successful_operations}\")
        print(f\"   Failed operations: {connection_metrics.failed_operations}\")
        print(f\"   Operations/second: {operations_per_second:.1f}\")
        print(f\"   Success rate: {success_rate:.3f}\")
        print(f\"   Avg operation time: {connection_metrics.average_operation_time*1000:.1f}ms\")
        print(f\"   P95 operation time: {connection_metrics.p95_operation_time:.1f}ms\")
        print(f\"   Connection acquisition p95: {acquisition_p95:.1f}ms\")
        print(f\"   Pool exhaustion events: {connection_metrics.pool_exhaustion_events}\")
        print(f\"   Timeout events: {connection_metrics.timeout_events}\")
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.real_services
    async def test_connection_pool_stress_limits(self, real_services_fixture):
        \"\"\"
        Test database connection pool behavior at stress limits.
        
        Performance SLA:
        - Graceful degradation under stress
        - No connection leaks
        - Recovery after stress period
        \"\"\"
        db = real_services_fixture[\"db\"]
        
        # Stress test parameters - push beyond normal limits
        max_concurrent_connections = 100  # High concurrency
        stress_duration = 30  # 30 seconds of stress
        operation_frequency = 0.01  # 10ms between operations
        
        stress_metrics = {
            \"total_operations\": 0,
            \"successful_operations\": 0,
            \"failed_operations\": 0,
            \"connection_errors\": 0,
            \"timeout_errors\": 0,
            \"peak_concurrent_operations\": 0,
            \"recovery_time\": 0
        }
        
        # Track active operations
        active_operations = set()
        active_operations_lock = asyncio.Lock()
        
        async def stress_database_operation(operation_id: int) -> Dict[str, Any]:
            \"\"\"Single stress test database operation.\"\"\"
            async with active_operations_lock:
                active_operations.add(operation_id)
                current_active = len(active_operations)
                stress_metrics[\"peak_concurrent_operations\"] = max(\n                    stress_metrics[\"peak_concurrent_operations\"],\n                    current_active\n                )
            
            result = {\"operation_id\": operation_id, \"success\": False, \"error\": None}
            
            try:\n                operation_start = time.time()\n                \n                # Vary operation complexity to simulate real workload\n                complexity = operation_id % 5\n                if complexity == 0:\n                    # Simple query\n                    await db.execute(\"SELECT 1\")\n                elif complexity == 1:\n                    # Medium complexity\n                    await db.execute(\"SELECT generate_series(1, 10)\")\n                elif complexity == 2:\n                    # Higher complexity\n                    await db.execute(\"SELECT COUNT(*) FROM generate_series(1, 100)\")\n                elif complexity == 3:\n                    # With parameters\n                    await db.execute(\"SELECT $1 as param, generate_series(1, $2)\", operation_id, min(20, operation_id % 30))\n                else:\n                    # Complex aggregation\n                    await db.execute(\"SELECT AVG(value), COUNT(*) FROM generate_series(1, $1) as value GROUP BY value % 5\", min(50, operation_id % 60))\n                \n                operation_time = time.time() - operation_start\n                \n                result[\"success\"] = True\n                result[\"operation_time\"] = operation_time\n                stress_metrics[\"successful_operations\"] += 1\n                \n            except asyncio.TimeoutError:\n                stress_metrics[\"timeout_errors\"] += 1\n                result[\"error\"] = \"timeout\"\n            except Exception as e:\n                stress_metrics[\"connection_errors\"] += 1\n                result[\"error\"] = str(e)\n            finally:\n                async with active_operations_lock:\n                    active_operations.discard(operation_id)\n                stress_metrics[\"total_operations\"] += 1\n            \n            return result\n        \n        # Run stress test\n        print(f\"🔥 Starting database stress test for {stress_duration}s...\")\n        stress_start = time.time()\n        end_time = stress_start + stress_duration\n        operation_counter = 0\n        \n        # Launch operations continuously during stress period\n        stress_tasks = []\n        while time.time() < end_time:\n            # Launch new operation\n            task = asyncio.create_task(stress_database_operation(operation_counter))\n            stress_tasks.append(task)\n            operation_counter += 1\n            \n            # Limit concurrent operations to prevent system overload\n            if len(stress_tasks) >= max_concurrent_connections:\n                # Wait for some operations to complete\n                done, pending = await asyncio.wait(stress_tasks, return_when=asyncio.FIRST_COMPLETED, timeout=0.1)\n                stress_tasks = list(pending)\n            \n            await asyncio.sleep(operation_frequency)\n        \n        # Wait for remaining operations to complete\n        if stress_tasks:\n            await asyncio.gather(*stress_tasks, return_exceptions=True)\n        \n        stress_end = time.time()\n        actual_stress_duration = stress_end - stress_start\n        \n        # Test recovery after stress\n        recovery_start = time.time()\n        \n        # Perform simple operations to test recovery\n        recovery_operations = 10\n        recovery_results = []\n        \n        for i in range(recovery_operations):\n            try:\n                await db.execute(\"SELECT 1 as recovery_test\")\n                recovery_results.append(True)\n            except Exception as e:\n                recovery_results.append(False)\n                print(f\"Recovery operation {i} failed: {e}\")\n            await asyncio.sleep(0.1)\n        \n        recovery_time = time.time() - recovery_start\n        stress_metrics[\"recovery_time\"] = recovery_time\n        recovery_success_rate = sum(recovery_results) / len(recovery_results)\n        \n        # Calculate final metrics\n        operations_per_second = stress_metrics[\"total_operations\"] / actual_stress_duration\n        success_rate = stress_metrics[\"successful_operations\"] / stress_metrics[\"total_operations\"] if stress_metrics[\"total_operations\"] > 0 else 0\n        \n        # Stress test assertions - more lenient than normal operations\n        assert success_rate >= 0.70, f\"Stress test success rate {success_rate:.3f} below 70% threshold\"\n        assert recovery_success_rate >= 0.90, f\"Recovery success rate {recovery_success_rate:.3f} below 90% threshold\"\n        assert recovery_time < 5.0, f\"Recovery time {recovery_time:.2f}s exceeds 5s limit\"\n        \n        print(f\"✅ Database Connection Pool Stress Test Results:\")\n        print(f\"   Stress duration: {actual_stress_duration:.2f}s\")\n        print(f\"   Total operations: {stress_metrics['total_operations']}\")\n        print(f\"   Successful operations: {stress_metrics['successful_operations']}\")\n        print(f\"   Failed operations: {stress_metrics['failed_operations']}\")\n        print(f\"   Operations/second: {operations_per_second:.1f}\")\n        print(f\"   Success rate: {success_rate:.3f}\")\n        print(f\"   Peak concurrent operations: {stress_metrics['peak_concurrent_operations']}\")\n        print(f\"   Connection errors: {stress_metrics['connection_errors']}\")\n        print(f\"   Timeout errors: {stress_metrics['timeout_errors']}\")\n        print(f\"   Recovery time: {recovery_time:.2f}s\")\n        print(f\"   Recovery success rate: {recovery_success_rate:.3f}\")\n    \n    @pytest.mark.integration\n    @pytest.mark.performance\n    @pytest.mark.real_services\n    async def test_connection_pool_efficiency_patterns(self, real_services_fixture):\n        \"\"\"
        Test database connection pool efficiency with various usage patterns.
        
        Performance SLA:
        - Connection reuse efficiency: >80%
        - No connection leaks over time
        - Consistent performance across different patterns
        \"\"\"
        db = real_services_fixture[\"db\"]
        
        # Test different usage patterns
        patterns = [\n            {\"name\": \"burst\", \"operations\": 50, \"concurrency\": 25, \"delay\": 0},\n            {\"name\": \"steady\", \"operations\": 100, \"concurrency\": 10, \"delay\": 0.01},\n            {\"name\": \"mixed\", \"operations\": 75, \"concurrency\": 15, \"delay\": 0.005}\n        ]\n        \n        pattern_results = []\n        \n        for pattern in patterns:\n            print(f\"🔄 Testing {pattern['name']} usage pattern...\")\n            \n            pattern_start = time.time()\n            operation_times = []\n            errors = []\n            \n            async def pattern_operation(op_id: int, delay: float) -> float:\n                \"\"\"Execute operation with pattern-specific characteristics.\"\"\"\n                if delay > 0:\n                    await asyncio.sleep(random.uniform(0, delay * 2))\n                \n                start_time = time.time()\n                try:\n                    # Simulate different query types\n                    query_type = op_id % 3\n                    if query_type == 0:\n                        await db.execute(\"SELECT $1 as operation_id\", op_id)\n                    elif query_type == 1:\n                        await db.execute(\"SELECT COUNT(*) FROM generate_series(1, $1)\", min(10, op_id % 15 + 1))\n                    else:\n                        await db.execute(\"SELECT $1, generate_series(1, 3)\", op_id)\n                    \n                    return time.time() - start_time\n                except Exception as e:\n                    errors.append(f\"Pattern {pattern['name']} operation {op_id} failed: {str(e)}\")\n                    return -1\n            \n            # Execute pattern operations\n            if pattern[\"concurrency\"] == pattern[\"operations\"]:  # Burst pattern\n                tasks = [pattern_operation(i, pattern[\"delay\"]) for i in range(pattern[\"operations\"])]\n                results = await asyncio.gather(*tasks, return_exceptions=True)\n                operation_times = [r for r in results if isinstance(r, float) and r > 0]\n            else:  # Controlled concurrency\n                semaphore = asyncio.Semaphore(pattern[\"concurrency\"])\n                \n                async def controlled_operation(op_id: int):\n                    async with semaphore:\n                        return await pattern_operation(op_id, pattern[\"delay\"])\n                \n                tasks = [controlled_operation(i) for i in range(pattern[\"operations\"])]\n                results = await asyncio.gather(*tasks, return_exceptions=True)\n                operation_times = [r for r in results if isinstance(r, float) and r > 0]\n            \n            pattern_duration = time.time() - pattern_start\n            \n            # Calculate pattern metrics\n            if operation_times:\n                pattern_metrics = {\n                    \"name\": pattern[\"name\"],\n                    \"total_operations\": pattern[\"operations\"],\n                    \"successful_operations\": len(operation_times),\n                    \"failed_operations\": len(errors),\n                    \"success_rate\": len(operation_times) / pattern[\"operations\"],\n                    \"average_time\": statistics.mean(operation_times),\n                    \"max_time\": max(operation_times),\n                    \"min_time\": min(operation_times),\n                    \"operations_per_second\": len(operation_times) / pattern_duration,\n                    \"total_duration\": pattern_duration\n                }\n            else:\n                pattern_metrics = {\n                    \"name\": pattern[\"name\"],\n                    \"total_operations\": pattern[\"operations\"],\n                    \"successful_operations\": 0,\n                    \"failed_operations\": len(errors),\n                    \"success_rate\": 0,\n                    \"average_time\": 0,\n                    \"max_time\": 0,\n                    \"min_time\": 0,\n                    \"operations_per_second\": 0,\n                    \"total_duration\": pattern_duration\n                }\n            \n            pattern_results.append(pattern_metrics)\n            \n            # Pattern-specific assertions\n            assert pattern_metrics[\"success_rate\"] >= 0.95, f\"Pattern {pattern['name']} success rate {pattern_metrics['success_rate']:.3f} below 95%\"\n            assert pattern_metrics[\"average_time\"] < 0.1, f\"Pattern {pattern['name']} avg time {pattern_metrics['average_time']:.3f}s exceeds 100ms\"\n        \n        # Cross-pattern consistency checks\n        success_rates = [p[\"success_rate\"] for p in pattern_results]\n        avg_times = [p[\"average_time\"] for p in pattern_results]\n        \n        # Ensure consistent performance across patterns\n        success_rate_variance = max(success_rates) - min(success_rates)\n        avg_time_variance = max(avg_times) - min(avg_times)\n        \n        assert success_rate_variance < 0.1, f\"Success rate variance {success_rate_variance:.3f} too high across patterns\"\n        assert avg_time_variance < 0.05, f\"Average time variance {avg_time_variance:.3f}s too high across patterns\"\n        \n        print(f\"✅ Connection Pool Efficiency Pattern Results:\")\n        for pattern_metrics in pattern_results:\n            print(f\"   {pattern_metrics['name'].title()} Pattern:\")\n            print(f\"     Operations: {pattern_metrics['successful_operations']}/{pattern_metrics['total_operations']}\")\n            print(f\"     Success rate: {pattern_metrics['success_rate']:.3f}\")\n            print(f\"     Avg time: {pattern_metrics['average_time']*1000:.1f}ms\")\n            print(f\"     Throughput: {pattern_metrics['operations_per_second']:.1f} ops/s\")\n        \n        print(f\"   Cross-Pattern Variance:\")\n        print(f\"     Success rate variance: {success_rate_variance:.3f}\")\n        print(f\"     Avg time variance: {avg_time_variance*1000:.1f}ms\")"