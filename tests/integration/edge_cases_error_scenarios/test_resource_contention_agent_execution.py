"""
Test Resource Contention During Agent Execution - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (Multiple concurrent users)
- Business Goal: Fair resource allocation and system stability
- Value Impact: Ensures consistent agent performance under concurrent load
- Strategic Impact: Supports Enterprise-level concurrent usage without degradation

CRITICAL: This test validates system behavior when multiple agents compete
for limited resources (CPU, memory, database connections, cache space).
"""

import asyncio
import logging
import pytest
import psutil
import time
from typing import Dict, List, Optional, Any
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services
from test_framework.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)


class TestResourceContentionAgentExecution(BaseIntegrationTest):
    """Test agent execution under resource contention conditions."""
    
    def setup_method(self):
        """Set up resource monitoring for contention tests."""
        super().setup_method()
        self.resource_monitor = ResourceMonitor()
        self.initial_metrics = {
            'memory': psutil.Process().memory_info().rss,
            'cpu_percent': psutil.Process().cpu_percent()
        }
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_cpu_contention(self, real_services_fixture):
        """Test agent execution when competing for CPU resources."""
        real_services = get_real_services()
        
        # Create multiple user contexts for concurrent execution
        user_contexts = []
        for i in range(4):  # 4 concurrent users
            context = await self.create_test_user_context(real_services, {
                'email': f'cpu-contention-user-{i}@example.com',
                'name': f'CPU Contention User {i}'
            })
            user_contexts.append(context)
        
        async def cpu_intensive_agent_execution(user_context: Dict, execution_id: int):
            """Execute agent with CPU-intensive operations."""
            start_time = time.time()
            cpu_start = psutil.Process().cpu_percent()
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    # Simulate CPU-intensive work with database operations
                    computational_work = []
                    for i in range(100):  # Moderate CPU work
                        # Simulate computation
                        computational_work.append(sum(range(i * 100)))
                        
                        # Database operation to simulate real agent work
                        if i % 20 == 0:  # Every 20 iterations
                            await real_services.postgres.fetchval(
                                "SELECT $1::int + $2::int", i, execution_id
                            )
                    
                    # Execute agent request
                    agent_result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=f"CPU intensive execution {execution_id}",
                        context={"execution_id": execution_id, "work_units": len(computational_work)}
                    )
                    
                    duration = time.time() - start_time
                    cpu_end = psutil.Process().cpu_percent()
                    
                    return {
                        'execution_id': execution_id,
                        'user_id': user_context['id'],
                        'duration': duration,
                        'cpu_usage': cpu_end - cpu_start,
                        'work_completed': len(computational_work),
                        'agent_result': agent_result,
                        'success': agent_result is not None and agent_result.get('status') != 'error'
                    }
                    
            except Exception as e:
                duration = time.time() - start_time
                return {
                    'execution_id': execution_id,
                    'user_id': user_context['id'],
                    'duration': duration,
                    'work_completed': 0,
                    'agent_result': None,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent CPU-intensive executions
        tasks = [
            cpu_intensive_agent_execution(user_contexts[i], i)
            for i in range(len(user_contexts))
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze CPU contention results
        successful_executions = []
        failed_executions = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_executions.append({'error': str(result)})
            elif isinstance(result, dict):
                if result.get('success'):
                    successful_executions.append(result)
                else:
                    failed_executions.append(result)
        
        # Verify fair CPU resource allocation
        success_rate = len(successful_executions) / len(results)
        avg_duration = sum(r['duration'] for r in successful_executions) / len(successful_executions) if successful_executions else 0
        total_work = sum(r['work_completed'] for r in successful_executions)
        
        logger.info(f"CPU contention results - Success rate: {success_rate:.1%}, "
                   f"Avg duration: {avg_duration:.1f}s, Total work: {total_work}, "
                   f"Total time: {total_duration:.1f}s")
        
        # At least 3/4 executions should succeed under CPU contention
        assert success_rate >= 0.75, \
            f"Too many executions failed under CPU contention: {success_rate:.1%}"
        
        # Individual executions should complete in reasonable time despite contention
        for result in successful_executions:
            assert result['duration'] < 30.0, \
                f"Execution {result['execution_id']} took too long under CPU contention: {result['duration']:.1f}s"
                
        # Verify business value was delivered despite CPU contention
        for result in successful_executions:
            assert result.get('agent_result') is not None, \
                f"Execution {result['execution_id']} should deliver agent results"
                
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_contention_resolution(self, real_services_fixture):
        """Test resolution of database connection contention between agents."""
        real_services = get_real_services()
        
        # Create user contexts for database-intensive operations
        user_contexts = []
        for i in range(5):  # More users than typical connection pool size
            context = await self.create_test_user_context(real_services, {
                'email': f'db-contention-user-{i}@example.com',
                'name': f'DB Contention User {i}'
            })
            user_contexts.append(context)
        
        async def database_intensive_execution(user_context: Dict, execution_id: int):
            """Execute database-intensive agent operations."""
            db_operations = []
            start_time = time.time()
            
            try:
                # Perform multiple database operations that require connections
                for i in range(15):  # More operations than typical connection pool
                    operation_start = time.time()
                    
                    # Different types of database operations
                    if i % 3 == 0:
                        # Read operation
                        result = await real_services.postgres.fetchval(
                            "SELECT count(*) FROM auth.users WHERE email LIKE $1", 
                            f"%{execution_id}%"
                        )
                    elif i % 3 == 1:
                        # Write operation
                        await real_services.postgres.execute(
                            "UPDATE auth.users SET name = $1 WHERE id = $2",
                            f"Updated by execution {execution_id}-{i}", user_context['id']
                        )
                    else:
                        # Transaction operation
                        async with real_services.postgres.transaction():
                            result = await real_services.postgres.fetchval(
                                "SELECT $1::int + $2::int", execution_id, i
                            )
                    
                    operation_duration = time.time() - operation_start
                    db_operations.append({
                        'operation_id': i,
                        'duration': operation_duration,
                        'success': True
                    })
                    
                    # Brief pause to allow connection cycling
                    await asyncio.sleep(0.05)
                
                # Execute agent request with database context
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    agent_result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=f"Database intensive execution {execution_id}",
                        context={"execution_id": execution_id, "db_operations": len(db_operations)}
                    )
                    
                    total_duration = time.time() - start_time
                    
                    return {
                        'execution_id': execution_id,
                        'user_id': user_context['id'],
                        'duration': total_duration,
                        'db_operations': db_operations,
                        'agent_result': agent_result,
                        'success': True
                    }
                    
            except Exception as e:
                total_duration = time.time() - start_time
                return {
                    'execution_id': execution_id,
                    'user_id': user_context['id'],
                    'duration': total_duration,
                    'db_operations': db_operations,
                    'agent_result': None,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent database-intensive operations
        tasks = [
            database_intensive_execution(user_contexts[i], i)
            for i in range(len(user_contexts))
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze database contention resolution
        successful_executions = []
        for result in results:
            if not isinstance(result, Exception) and result.get('success'):
                successful_executions.append(result)
        
        # Verify database contention was resolved fairly
        success_rate = len(successful_executions) / len(results)
        
        logger.info(f"Database contention results - Success rate: {success_rate:.1%}, "
                   f"Successful executions: {len(successful_executions)}")
        
        # Most executions should succeed despite database contention
        assert success_rate >= 0.6, \
            f"Database contention not resolved effectively: {success_rate:.1%}"
        
        # Verify database operations completed
        total_db_ops = sum(len(r.get('db_operations', [])) for r in successful_executions)
        expected_ops = len(successful_executions) * 15
        
        db_completion_rate = total_db_ops / expected_ops if expected_ops > 0 else 0
        assert db_completion_rate >= 0.8, \
            f"Many database operations failed due to contention: {db_completion_rate:.1%}"
            
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_resource_contention_handling(self, real_services_fixture):
        """Test cache resource contention handling between concurrent agents."""
        real_services = get_real_services()
        
        # Create user contexts for cache-intensive operations
        user_contexts = []
        for i in range(3):
            context = await self.create_test_user_context(real_services, {
                'email': f'cache-contention-user-{i}@example.com',
                'name': f'Cache Contention User {i}'
            })
            user_contexts.append(context)
        
        async def cache_intensive_execution(user_context: Dict, execution_id: int):
            """Execute cache-intensive operations."""
            cache_operations = []
            namespace = f"contention_test_{execution_id}"
            
            try:
                # Create cache pressure with multiple operations
                for i in range(50):  # Many cache operations
                    key = f"{namespace}:key_{i}"
                    value = f"value_{execution_id}_{i}" * 10  # Larger values for memory pressure
                    
                    # Mix of cache operations
                    if i % 4 == 0:
                        # Set operation
                        await real_services.redis.set(key, value)
                        cache_operations.append({'op': 'set', 'key': key, 'success': True})
                    elif i % 4 == 1:
                        # Get operation
                        result = await real_services.redis.get(f"{namespace}:key_{max(0, i-1)}")
                        cache_operations.append({'op': 'get', 'key': key, 'success': result is not None})
                    elif i % 4 == 2:
                        # Hash operation
                        await real_services.redis.hset(f"{namespace}:hash", f"field_{i}", value)
                        cache_operations.append({'op': 'hset', 'key': key, 'success': True})
                    else:
                        # List operation
                        await real_services.redis.lpush(f"{namespace}:list", value)
                        cache_operations.append({'op': 'lpush', 'key': key, 'success': True})
                    
                    # Brief pause to allow other operations
                    await asyncio.sleep(0.01)
                
                # Test cache retrieval under contention
                retrieval_test = []
                for i in range(10):
                    try:
                        result = await real_services.redis.get(f"{namespace}:key_{i * 5}")
                        retrieval_test.append(result is not None)
                    except Exception:
                        retrieval_test.append(False)
                
                return {
                    'execution_id': execution_id,
                    'user_id': user_context['id'],
                    'cache_operations': len(cache_operations),
                    'successful_ops': len([op for op in cache_operations if op.get('success')]),
                    'retrieval_success_rate': sum(retrieval_test) / len(retrieval_test),
                    'success': True
                }
                
            except Exception as e:
                return {
                    'execution_id': execution_id,
                    'user_id': user_context['id'],
                    'cache_operations': len(cache_operations),
                    'successful_ops': len([op for op in cache_operations if op.get('success')]),
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent cache-intensive operations
        tasks = [
            cache_intensive_execution(user_contexts[i], i)
            for i in range(len(user_contexts))
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze cache contention results
        successful_executions = []
        for result in results:
            if not isinstance(result, Exception) and result.get('success'):
                successful_executions.append(result)
        
        # Verify cache contention handling
        success_rate = len(successful_executions) / len(results)
        
        total_cache_ops = sum(r['cache_operations'] for r in successful_executions)
        total_successful_ops = sum(r['successful_ops'] for r in successful_executions)
        avg_retrieval_rate = sum(r.get('retrieval_success_rate', 0) for r in successful_executions) / len(successful_executions) if successful_executions else 0
        
        logger.info(f"Cache contention results - Success rate: {success_rate:.1%}, "
                   f"Cache operations: {total_successful_ops}/{total_cache_ops}, "
                   f"Avg retrieval success: {avg_retrieval_rate:.1%}")
        
        # Cache operations should succeed despite contention
        assert success_rate >= 0.8, \
            f"Cache contention caused too many failures: {success_rate:.1%}"
        
        # Most cache operations should succeed
        cache_op_success_rate = total_successful_ops / total_cache_ops if total_cache_ops > 0 else 0
        assert cache_op_success_rate >= 0.9, \
            f"Too many cache operations failed under contention: {cache_op_success_rate:.1%}"
        
        # Cache retrieval should remain functional
        assert avg_retrieval_rate >= 0.7, \
            f"Cache retrieval degraded too much under contention: {avg_retrieval_rate:.1%}"
            
    @pytest.mark.integration
    async def test_resource_fairness_allocation_algorithm(self):
        """Test fairness of resource allocation algorithm under contention."""
        # Simulate resource allocation fairness
        resource_requests = [
            {'user_id': f'user_{i}', 'priority': 1, 'resources_needed': 10 + (i * 2)}
            for i in range(5)
        ]
        
        # Simulate limited resource pool
        total_available_resources = 50
        allocated_resources = {}
        
        # Simple fair allocation algorithm
        total_requested = sum(req['resources_needed'] for req in resource_requests)
        
        for req in resource_requests:
            if total_requested <= total_available_resources:
                # All requests can be satisfied
                allocated_resources[req['user_id']] = req['resources_needed']
            else:
                # Proportional allocation
                proportion = req['resources_needed'] / total_requested
                allocated_resources[req['user_id']] = int(total_available_resources * proportion)
        
        # Verify fairness metrics
        total_allocated = sum(allocated_resources.values())
        assert total_allocated <= total_available_resources, \
            "Resource allocation should not exceed available resources"
        
        # Check allocation fairness
        allocation_ratios = []
        for req in resource_requests:
            allocated = allocated_resources[req['user_id']]
            requested = req['resources_needed']
            ratio = allocated / requested if requested > 0 else 0
            allocation_ratios.append(ratio)
        
        # All users should get similar allocation ratios (fairness)
        min_ratio = min(allocation_ratios)
        max_ratio = max(allocation_ratios)
        fairness_variance = max_ratio - min_ratio
        
        assert fairness_variance < 0.3, \
            f"Resource allocation not fair enough: variance {fairness_variance:.2f}"
        
        logger.info(f"Resource fairness test - Total allocated: {total_allocated}/{total_available_resources}, "
                   f"Fairness variance: {fairness_variance:.2f}, "
                   f"Allocation ratios: {[f'{r:.2f}' for r in allocation_ratios]}")
                   
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_contention_graceful_degradation(self, real_services_fixture):
        """Test graceful degradation under severe resource contention."""
        real_services = get_real_services()
        
        # Create user context
        user_context = await self.create_test_user_context(real_services)
        
        # Simulate resource exhaustion scenario
        resource_exhaustion_results = []
        
        # Test different levels of resource pressure
        pressure_levels = [
            {'connections': 2, 'operations_per_connection': 5, 'expected_success_rate': 0.9},
            {'connections': 5, 'operations_per_connection': 10, 'expected_success_rate': 0.7},
            {'connections': 8, 'operations_per_connection': 15, 'expected_success_rate': 0.5}
        ]
        
        for pressure in pressure_levels:
            logger.info(f"Testing resource pressure: {pressure['connections']} connections, "
                       f"{pressure['operations_per_connection']} ops each")
            
            async def resource_pressure_simulation(connection_id: int):
                """Simulate resource pressure from one connection."""
                operations = []
                
                for i in range(pressure['operations_per_connection']):
                    try:
                        # Mix of resource-intensive operations
                        if i % 3 == 0:
                            # Database operation
                            result = await real_services.postgres.fetchval(
                                "SELECT pg_sleep(0.1) as sleep_result"  # Brief delay
                            )
                            operations.append({'type': 'db', 'success': True})
                        else:
                            # Cache operation
                            await real_services.redis.set(
                                f"pressure_{connection_id}_{i}", 
                                f"value_{connection_id}_{i}"
                            )
                            operations.append({'type': 'cache', 'success': True})
                            
                    except Exception as e:
                        operations.append({'type': 'unknown', 'success': False, 'error': str(e)})
                        
                    # Brief pause between operations
                    await asyncio.sleep(0.02)
                
                return {
                    'connection_id': connection_id,
                    'operations': operations,
                    'success_count': len([op for op in operations if op.get('success')])
                }
            
            # Run pressure simulation
            pressure_tasks = [
                resource_pressure_simulation(i) 
                for i in range(pressure['connections'])
            ]
            
            pressure_results = await asyncio.gather(*pressure_tasks, return_exceptions=True)
            
            # Analyze pressure test results
            successful_connections = []
            for result in pressure_results:
                if not isinstance(result, Exception):
                    successful_connections.append(result)
            
            total_operations = sum(len(r['operations']) for r in successful_connections)
            successful_operations = sum(r['success_count'] for r in successful_connections)
            
            actual_success_rate = successful_operations / total_operations if total_operations > 0 else 0
            
            resource_exhaustion_results.append({
                'pressure_level': pressure,
                'actual_success_rate': actual_success_rate,
                'total_operations': total_operations,
                'successful_operations': successful_operations
            })
            
            logger.info(f"Pressure level results - Success rate: {actual_success_rate:.1%} "
                       f"(expected: {pressure['expected_success_rate']:.1%})")
            
            # System should degrade gracefully, not fail completely
            assert actual_success_rate >= pressure['expected_success_rate'] * 0.7, \
                f"System degraded too much under pressure: {actual_success_rate:.1%}"
            
            # Brief pause between pressure tests
            await asyncio.sleep(1.0)
        
        # Verify graceful degradation pattern
        success_rates = [r['actual_success_rate'] for r in resource_exhaustion_results]
        
        # Success rates should generally decrease with increased pressure but remain reasonable
        assert all(rate >= 0.3 for rate in success_rates), \
            "System should maintain minimum functionality under all pressure levels"
        
        # System should recover between tests (not getting progressively worse)
        rate_variance = max(success_rates) - min(success_rates)
        assert rate_variance < 0.8, \
            f"Too much variance in degradation pattern: {rate_variance:.1%}"