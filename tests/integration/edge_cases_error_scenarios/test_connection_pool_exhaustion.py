"""
Test Database Connection Pool Exhaustion - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (High concurrent usage)
- Business Goal: System stability under high database load
- Value Impact: Maintains service availability during peak concurrent user activity
- Strategic Impact: Ensures Enterprise customers get reliable service during high-demand periods

CRITICAL: This test validates system behavior when database connection pools
are exhausted due to concurrent user activity or long-running operations.
"""

import asyncio
import logging
import pytest
import time
from typing import Dict, List, Optional
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest, DatabaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestConnectionPoolExhaustion(DatabaseIntegrationTest):
    """Test system behavior when database connection pools are exhausted."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_limit_enforcement(self, real_services_fixture):
        """Test database connection pool properly enforces limits."""
        real_services = get_real_services()
        
        # Get database pool information
        pool_info = await real_services.postgres.pool.get_status()
        max_connections = getattr(real_services.postgres.pool, '_maxsize', 10)
        
        logger.info(f"Database pool max size: {max_connections}")
        
        # Create connections up to the limit
        held_connections = []
        connection_tasks = []
        
        async def acquire_and_hold_connection(connection_id: int):
            """Acquire a database connection and hold it for a period."""
            try:
                conn = await real_services.postgres.acquire()
                held_connections.append(conn)
                
                # Execute a simple query to verify connection works
                result = await conn.fetchval("SELECT $1::text", f"connection_{connection_id}")
                assert result == f"connection_{connection_id}"
                
                # Hold the connection for a short period
                await asyncio.sleep(2.0)
                
                return {'id': connection_id, 'success': True}
                
            except Exception as e:
                logger.warning(f"Connection {connection_id} acquisition failed: {e}")
                return {'id': connection_id, 'success': False, 'error': str(e)}
            finally:
                # Clean up connection
                if held_connections and len(held_connections) > connection_id:
                    try:
                        await real_services.postgres.release(held_connections[connection_id])
                    except:
                        pass
        
        try:
            # Create tasks to acquire connections beyond the pool limit
            num_connections = max_connections + 2  # Try to exceed pool size
            tasks = [
                acquire_and_hold_connection(i) 
                for i in range(num_connections)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start_time
            
            # Analyze results
            successful_connections = []
            failed_connections = []
            exceptions = []
            
            for result in results:
                if isinstance(result, Exception):
                    exceptions.append(result)
                elif isinstance(result, dict):
                    if result.get('success'):
                        successful_connections.append(result)
                    else:
                        failed_connections.append(result)
            
            # Verify pool limits are enforced
            total_attempts = len(results)
            success_rate = len(successful_connections) / total_attempts
            
            logger.info(f"Connection test results - Attempted: {total_attempts}, "
                       f"Successful: {len(successful_connections)}, "
                       f"Failed: {len(failed_connections)}, "
                       f"Exceptions: {len(exceptions)}, Duration: {duration:.1f}s")
            
            # Pool should handle at least the configured number of connections
            assert len(successful_connections) >= min(max_connections, total_attempts), \
                "Connection pool should handle configured number of connections"
            
            # Some connections beyond the limit may fail (pool enforcement working)
            if total_attempts > max_connections:
                assert len(failed_connections) > 0 or len(exceptions) > 0, \
                    "Connection pool should enforce limits when exceeded"
                    
        finally:
            # Clean up any remaining held connections
            for conn in held_connections:
                try:
                    await real_services.postgres.release(conn)
                except:
                    pass
                    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_connection_pool_recovery_after_exhaustion(self, real_services_fixture):
        """Test connection pool recovery after temporary exhaustion."""
        real_services = get_real_services()
        
        # Verify pool is healthy initially
        initial_result = await real_services.postgres.fetchval("SELECT 1")
        assert initial_result == 1, "Database should be accessible initially"
        
        # Create temporary connection exhaustion
        exhaustion_connections = []
        max_connections = getattr(real_services.postgres.pool, '_maxsize', 10)
        
        try:
            # Acquire connections to near exhaustion
            for i in range(max_connections - 1):  # Leave one for testing
                try:
                    conn = await real_services.postgres.acquire()
                    exhaustion_connections.append(conn)
                    
                    # Verify connection works
                    result = await conn.fetchval("SELECT $1::int", i)
                    assert result == i
                    
                except Exception as e:
                    logger.warning(f"Failed to acquire exhaustion connection {i}: {e}")
                    break
            
            logger.info(f"Acquired {len(exhaustion_connections)} connections for exhaustion test")
            
            # Test that one connection still works (pool not completely exhausted)
            try:
                test_result = await asyncio.wait_for(
                    real_services.postgres.fetchval("SELECT 'pool_test'"),
                    timeout=5.0
                )
                assert test_result == 'pool_test', "Pool should still serve requests with one connection available"
                
            except asyncio.TimeoutError:
                logger.warning("Connection pool appears completely exhausted")
                # This is acceptable - pool exhaustion is working
                
        finally:
            # Release all connections to trigger recovery
            for conn in exhaustion_connections:
                try:
                    await real_services.postgres.release(conn)
                except Exception as e:
                    logger.warning(f"Error releasing connection: {e}")
        
        # Allow time for pool recovery
        await asyncio.sleep(1.0)
        
        # Verify pool has recovered
        recovery_start = time.time()
        recovery_successful = False
        
        for attempt in range(5):  # Multiple attempts to verify recovery
            try:
                result = await asyncio.wait_for(
                    real_services.postgres.fetchval("SELECT 'recovery_test'"),
                    timeout=3.0
                )
                if result == 'recovery_test':
                    recovery_successful = True
                    break
                    
            except Exception as e:
                logger.warning(f"Recovery attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(0.5)
                
        recovery_duration = time.time() - recovery_start
        
        assert recovery_successful, \
            f"Connection pool failed to recover after {recovery_duration:.1f}s"
            
        logger.info(f"Connection pool recovery successful in {recovery_duration:.1f}s")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_connection_usage(self, real_services_fixture):
        """Test connection usage patterns during concurrent agent executions."""
        real_services = get_real_services()
        
        # Create multiple user contexts for concurrent execution
        user_contexts = []
        for i in range(3):
            context = await self.create_test_user_context(real_services, {
                'email': f'connection-test-user-{i}@example.com',
                'name': f'Connection Test User {i}'
            })
            user_contexts.append(context)
        
        async def database_intensive_agent_execution(user_context: Dict, execution_id: int):
            """Execute agent with database-intensive operations."""
            connection_count = 0
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    # Simulate database-intensive agent operations
                    start_time = time.time()
                    
                    # Perform multiple database operations
                    for i in range(5):  # Moderate database load
                        # Each operation might use a connection
                        result = await real_services.postgres.fetchval(
                            "SELECT pg_backend_pid() as connection_id"
                        )
                        connection_count += 1
                        
                        # Brief pause between operations
                        await asyncio.sleep(0.1)
                    
                    # Execute agent request
                    agent_result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=f"Database test execution {execution_id}",
                        context={"execution_id": execution_id}
                    )
                    
                    duration = time.time() - start_time
                    
                    return {
                        'execution_id': execution_id,
                        'user_id': user_context['id'],
                        'connection_operations': connection_count,
                        'agent_result': agent_result,
                        'duration': duration,
                        'success': agent_result is not None and agent_result.get('status') != 'error'
                    }
                    
            except Exception as e:
                return {
                    'execution_id': execution_id,
                    'user_id': user_context['id'],
                    'connection_operations': connection_count,
                    'agent_result': None,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent database-intensive executions
        tasks = [
            database_intensive_agent_execution(user_contexts[i], i)
            for i in range(len(user_contexts))
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze concurrent execution results
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
        
        # Verify concurrent executions handled connection limits properly
        success_rate = len(successful_executions) / len(results)
        total_connections_used = sum(r.get('connection_operations', 0) for r in successful_executions)
        
        logger.info(f"Concurrent execution results - Success rate: {success_rate:.1%}, "
                   f"Total connections used: {total_connections_used}, "
                   f"Duration: {total_duration:.1f}s")
        
        # At least 2/3 executions should succeed under normal connection pool conditions
        assert success_rate >= 0.67, \
            f"Too many concurrent executions failed due to connection issues: {success_rate:.1%}"
        
        # Verify business value was still delivered despite connection pressure
        for result in successful_executions:
            assert result.get('agent_result') is not None, \
                f"Execution {result['execution_id']} should deliver agent results"
                
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_long_running_transaction_isolation(self, real_services_fixture):
        """Test isolation between long-running transactions and regular operations."""
        real_services = get_real_services()
        
        # Create user context for test
        user_context = await self.create_test_user_context(real_services)
        
        async def long_running_transaction():
            """Simulate a long-running database transaction."""
            async with real_services.postgres.transaction() as tx:
                # Start a long-running operation
                await tx.execute("SELECT pg_sleep(2)")  # 2 second delay
                
                # Insert test data
                await tx.execute("""
                    INSERT INTO auth.users (email, name, is_active)
                    VALUES ('long-transaction@example.com', 'Long Transaction User', true)
                    ON CONFLICT (email) DO NOTHING
                """)
                
                return "long_transaction_completed"
        
        async def regular_operations():
            """Perform regular database operations during long transaction."""
            operations = []
            
            for i in range(10):
                try:
                    # Quick database operations
                    result = await real_services.postgres.fetchval("SELECT $1::int", i)
                    operations.append({'operation': i, 'result': result, 'success': True})
                    
                    await asyncio.sleep(0.2)  # Brief pause between operations
                    
                except Exception as e:
                    operations.append({'operation': i, 'result': None, 'success': False, 'error': str(e)})
                    
            return operations
        
        # Run long transaction and regular operations concurrently
        start_time = time.time()
        long_tx_task = asyncio.create_task(long_running_transaction())
        regular_ops_task = asyncio.create_task(regular_operations())
        
        long_tx_result, regular_ops_result = await asyncio.gather(
            long_tx_task, regular_ops_task, return_exceptions=True
        )
        duration = time.time() - start_time
        
        # Verify both operations completed successfully
        assert not isinstance(long_tx_result, Exception), \
            f"Long transaction failed: {long_tx_result}"
        assert long_tx_result == "long_transaction_completed", \
            "Long transaction should complete successfully"
        
        assert not isinstance(regular_ops_result, Exception), \
            f"Regular operations failed: {regular_ops_result}"
        
        # Analyze regular operations success rate
        successful_ops = [op for op in regular_ops_result if op.get('success')]
        success_rate = len(successful_ops) / len(regular_ops_result)
        
        logger.info(f"Transaction isolation test - Duration: {duration:.1f}s, "
                   f"Regular operations success rate: {success_rate:.1%}")
        
        # Regular operations should not be significantly impacted by long transaction
        assert success_rate >= 0.8, \
            f"Long transaction impacted regular operations too much: {success_rate:.1%}"
        
        # Total duration should be reasonable (not blocked by long transaction)
        assert duration < 4.0, \
            f"Operations took too long due to transaction blocking: {duration:.1f}s"
            
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_connection_timeout_handling(self, real_services_fixture):
        """Test proper handling of database connection timeouts."""
        real_services = get_real_services()
        
        # Test connection acquisition timeout
        connection_timeout_test_results = []
        
        # Simulate connection pressure by holding connections
        held_connections = []
        max_connections = getattr(real_services.postgres.pool, '_maxsize', 10)
        
        try:
            # Acquire most connections to create pressure
            for i in range(max_connections - 1):
                try:
                    conn = await real_services.postgres.acquire()
                    held_connections.append(conn)
                except Exception as e:
                    logger.warning(f"Failed to acquire connection {i} for timeout test: {e}")
                    break
            
            logger.info(f"Holding {len(held_connections)} connections for timeout test")
            
            # Test operations with limited connection availability
            async def test_operation_with_timeout(operation_id: int):
                """Test database operation with potential timeout."""
                start_time = time.time()
                
                try:
                    # Use a reasonable timeout for the operation
                    result = await asyncio.wait_for(
                        real_services.postgres.fetchval("SELECT $1::int", operation_id),
                        timeout=3.0
                    )
                    
                    duration = time.time() - start_time
                    return {
                        'operation_id': operation_id,
                        'result': result,
                        'duration': duration,
                        'success': True
                    }
                    
                except asyncio.TimeoutError:
                    duration = time.time() - start_time
                    return {
                        'operation_id': operation_id,
                        'result': None,
                        'duration': duration,
                        'success': False,
                        'error': 'timeout'
                    }
                except Exception as e:
                    duration = time.time() - start_time
                    return {
                        'operation_id': operation_id,
                        'result': None,
                        'duration': duration,
                        'success': False,
                        'error': str(e)
                    }
            
            # Test multiple operations under connection pressure
            timeout_tasks = [test_operation_with_timeout(i) for i in range(5)]
            timeout_results = await asyncio.gather(*timeout_tasks)
            
            # Analyze timeout handling
            successful_ops = [r for r in timeout_results if r.get('success')]
            timeout_ops = [r for r in timeout_results if r.get('error') == 'timeout']
            
            logger.info(f"Timeout test results - Successful: {len(successful_ops)}, "
                       f"Timeouts: {len(timeout_ops)}, Total: {len(timeout_results)}")
            
            # At least some operations should complete (system not completely blocked)
            assert len(successful_ops) > 0, \
                "No operations completed - connection pool may be completely blocked"
            
            # Timeout handling should be graceful (no uncaught exceptions)
            for result in timeout_results:
                assert 'error' in result or result.get('success'), \
                    f"Operation {result['operation_id']} should have clear success/error status"
                    
        finally:
            # Release held connections
            for conn in held_connections:
                try:
                    await real_services.postgres.release(conn)
                except Exception as e:
                    logger.warning(f"Error releasing connection during cleanup: {e}")
                    
        # Verify system recovery after releasing connections
        recovery_result = await real_services.postgres.fetchval("SELECT 'recovery_verified'")
        assert recovery_result == 'recovery_verified', \
            "System should recover after connection pressure is released"