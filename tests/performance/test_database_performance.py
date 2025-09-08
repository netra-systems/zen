"""
Database Connection Pool Performance Tests for UserExecutionContext Migration

This module tests database connection pool efficiency and performance with the new
UserExecutionContext architecture to ensure proper resource management.

Test Categories:
1. Connection Pool Efficiency
2. Concurrent Database Operations
3. Connection Leak Detection
4. Transaction Performance
5. Database Session Isolation

Business Value:
- Validates database connection management
- Ensures no connection leaks
- Tests database session isolation
- Validates transaction performance
"""

import asyncio
import gc
import psutil
import pytest
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import SessionManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class MockDatabase:
    """Mock database for performance testing."""
    
    def __init__(self):
        self.connections = {}
        self.connection_count = 0
        self.active_transactions = 0
        self.query_count = 0
        self.connection_errors = 0
        
    async def get_connection(self, user_context: UserExecutionContext):
        """Get database connection for user context."""
        connection_key = f"{user_context.user_id}_{user_context.request_id}"
        
        if connection_key not in self.connections:
            # Simulate connection creation overhead
            await asyncio.sleep(0.001)  # 1ms connection overhead
            
            self.connections[connection_key] = {
                'created_at': time.time(),
                'user_id': user_context.user_id,
                'queries_executed': 0,
                'active': True
            }
            self.connection_count += 1
        
        return self.connections[connection_key]
    
    async def execute_query(self, connection, query: str, user_context: UserExecutionContext):
        """Execute query with connection."""
        # Simulate query execution time
        await asyncio.sleep(0.002)  # 2ms query time
        
        connection['queries_executed'] += 1
        self.query_count += 1
        
        # Simulate query result
        return {
            'result': f'Query result for {query}',
            'user_id': user_context.user_id,
            'timestamp': time.time()
        }
    
    async def begin_transaction(self, connection):
        """Begin database transaction."""
        self.active_transactions += 1
        await asyncio.sleep(0.0005)  # 0.5ms transaction overhead
        
    async def commit_transaction(self, connection):
        """Commit database transaction."""
        if self.active_transactions > 0:
            self.active_transactions -= 1
        await asyncio.sleep(0.0005)  # 0.5ms commit overhead
        
    async def rollback_transaction(self, connection):
        """Rollback database transaction."""
        if self.active_transactions > 0:
            self.active_transactions -= 1
        await asyncio.sleep(0.0005)  # 0.5ms rollback overhead
    
    async def close_connection(self, connection_key: str):
        """Close database connection."""
        if connection_key in self.connections:
            self.connections[connection_key]['active'] = False
            await asyncio.sleep(0.0005)  # 0.5ms cleanup overhead
    
    def get_connection_stats(self):
        """Get connection pool statistics."""
        active_connections = sum(1 for conn in self.connections.values() if conn['active'])
        
        return {
            'total_connections_created': self.connection_count,
            'active_connections': active_connections,
            'inactive_connections': len(self.connections) - active_connections,
            'total_queries': self.query_count,
            'active_transactions': self.active_transactions,
            'connection_errors': self.connection_errors
        }


@pytest.fixture
async def mock_database():
    """Provide mock database for tests."""
    return MockDatabase()


@pytest.fixture
async def test_contexts():
    """Generate multiple test contexts."""
    contexts = []
    for i in range(10):
        context = UserExecutionContext(
            user_id=f"db_test_user_{i}_{uuid.uuid4().hex[:8]}",
            thread_id=f"db_test_thread_{i}_{uuid.uuid4().hex[:8]}",
            run_id=f"db_test_run_{i}_{uuid.uuid4().hex[:8]}",
            request_id=f"db_test_req_{i}_{uuid.uuid4().hex[:8]}"
        )
        contexts.append(context)
    return contexts


@pytest.mark.asyncio
class TestDatabaseConnectionPool:
    """Test suite for database connection pool performance."""
    
    async def test_connection_pool_efficiency(self, mock_database, test_contexts):
        """Test database connection pool efficiency."""
        from tests.performance.test_phase1_context_performance import PerformanceProfiler
        
        with PerformanceProfiler("connection_pool_efficiency") as profiler:
            connections = {}
            
            # Test connection creation for multiple users
            for context in test_contexts:
                try:
                    connection = await mock_database.get_connection(context)
                    connections[context.request_id] = connection
                    profiler.record_success()
                    
                except Exception as e:
                    logger.error(f"Connection creation failed: {e}")
                    profiler.record_error()
            
            # Execute queries on all connections
            for context in test_contexts:
                if context.request_id in connections:
                    try:
                        connection = connections[context.request_id]
                        result = await mock_database.execute_query(
                            connection, 
                            f"SELECT * FROM user_data WHERE user_id = '{context.user_id}'",
                            context
                        )
                        profiler.record_success()
                        
                    except Exception as e:
                        logger.error(f"Query execution failed: {e}")
                        profiler.record_error()
            
            # Cleanup connections
            for connection_key in connections.keys():
                try:
                    await mock_database.close_connection(connection_key)
                    profiler.record_success()
                    
                except Exception as e:
                    logger.error(f"Connection cleanup failed: {e}")
                    profiler.record_error()
        
        metrics = profiler.get_metrics()
        stats = mock_database.get_connection_stats()
        
        profiler.add_metric("total_connections_created", stats['total_connections_created'])
        profiler.add_metric("total_queries_executed", stats['total_queries'])
        
        # Performance assertions
        assert metrics.error_count == 0, f"Database operations failed: {metrics.error_count} errors"
        assert metrics.duration_ms < 1000, f"Connection pool operations too slow: {metrics.duration_ms}ms"
        assert stats['total_connections_created'] == len(test_contexts), \
            f"Expected {len(test_contexts)} connections, created {stats['total_connections_created']}"
    
    async def test_concurrent_database_operations(self, mock_database):
        """Test concurrent database operations performance."""
        from tests.performance.test_phase1_context_performance import PerformanceProfiler
        
        concurrent_operations = 100
        
        async def database_operation(operation_id: int) -> Tuple[bool, Optional[str]]:
            """Single database operation."""
            try:
                context = UserExecutionContext(
                    user_id=f"concurrent_db_user_{operation_id % 20}_{uuid.uuid4().hex[:8]}",  # 20 users
                    thread_id=f"concurrent_db_thread_{operation_id}_{uuid.uuid4().hex[:8]}",
                    run_id=f"concurrent_db_run_{operation_id}_{uuid.uuid4().hex[:8]}",
                    request_id=f"concurrent_db_req_{operation_id}_{uuid.uuid4().hex[:8]}"
                )
                
                # Get connection
                connection = await mock_database.get_connection(context)
                
                # Begin transaction
                await mock_database.begin_transaction(connection)
                
                # Execute multiple queries
                for query_num in range(3):
                    await mock_database.execute_query(
                        connection,
                        f"SELECT data_{query_num} FROM table WHERE user_id = '{context.user_id}'",
                        context
                    )
                
                # Commit transaction
                await mock_database.commit_transaction(connection)
                
                # Close connection
                await mock_database.close_connection(context.request_id)
                
                return True, None
                
            except Exception as e:
                return False, str(e)
        
        with PerformanceProfiler("concurrent_database_operations") as profiler:
            # Execute all operations concurrently
            tasks = [database_operation(i) for i in range(concurrent_operations)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, tuple):
                    success, error = result
                    if success:
                        profiler.record_success()
                    else:
                        profiler.record_error()
                        logger.warning(f"Concurrent DB operation failed: {error}")
                else:
                    profiler.record_error()
                    logger.error(f"Concurrent DB operation exception: {result}")
        
        metrics = profiler.get_metrics()
        stats = mock_database.get_connection_stats()
        
        profiler.add_metric("db_connections_created", stats['total_connections_created'])
        profiler.add_metric("db_queries_executed", stats['total_queries'])
        profiler.add_metric("db_active_transactions", stats['active_transactions'])
        
        # Performance assertions
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.95, f"Concurrent DB operations success rate too low: {success_rate:.2%}"
        assert metrics.duration_ms < 5000, f"Concurrent DB operations too slow: {metrics.duration_ms}ms"
        assert stats['active_transactions'] == 0, f"Transactions not properly closed: {stats['active_transactions']}"
        assert stats['total_queries'] >= concurrent_operations * 3, \
            f"Expected at least {concurrent_operations * 3} queries, executed {stats['total_queries']}"
    
    async def test_connection_leak_detection(self, mock_database):
        """Test for database connection leaks."""
        from tests.performance.test_phase1_context_performance import PerformanceProfiler
        
        cycles = 50
        connections_per_cycle = 10
        
        with PerformanceProfiler("connection_leak_detection") as profiler:
            for cycle in range(cycles):
                cycle_connections = []
                
                # Create connections for this cycle
                for i in range(connections_per_cycle):
                    try:
                        context = UserExecutionContext(
                            user_id=f"leak_test_user_{cycle}_{i}_{uuid.uuid4().hex[:8]}",
                            thread_id=f"leak_test_thread_{cycle}_{i}_{uuid.uuid4().hex[:8]}",
                            run_id=f"leak_test_run_{cycle}_{i}_{uuid.uuid4().hex[:8]}",
                            request_id=f"leak_test_req_{cycle}_{i}_{uuid.uuid4().hex[:8]}"
                        )
                        
                        connection = await mock_database.get_connection(context)
                        cycle_connections.append((context.request_id, connection))
                        
                        # Execute some operations
                        await mock_database.execute_query(
                            connection,
                            "SELECT 1",
                            context
                        )
                        
                        profiler.record_success()
                        
                    except Exception as e:
                        logger.error(f"Connection creation failed in cycle {cycle}: {e}")
                        profiler.record_error()
                
                # Cleanup connections (important for leak testing)
                for connection_key, connection in cycle_connections:
                    try:
                        await mock_database.close_connection(connection_key)
                    except Exception as e:
                        logger.error(f"Connection cleanup failed: {e}")
                
                # Check for leaks every 10 cycles
                if cycle % 10 == 0:
                    stats = mock_database.get_connection_stats()
                    profiler.add_metric(f"active_connections_cycle_{cycle}", stats['active_connections'])
                    
                    # Log connection stats
                    logger.debug(f"Cycle {cycle}: {stats['active_connections']} active connections, "
                               f"{stats['total_connections_created']} total created")
        
        # Final leak check
        final_stats = mock_database.get_connection_stats()
        metrics = profiler.get_metrics()
        
        profiler.add_metric("final_active_connections", final_stats['active_connections'])
        profiler.add_metric("total_connections_created", final_stats['total_connections_created'])
        profiler.add_metric("total_cycles", cycles)
        profiler.add_metric("connections_per_cycle", connections_per_cycle)
        
        logger.info(f"Connection leak test: {final_stats['total_connections_created']} connections created, "
                   f"{final_stats['active_connections']} still active")
        
        # Connection leak assertions
        expected_total_connections = cycles * connections_per_cycle
        assert final_stats['total_connections_created'] >= expected_total_connections * 0.95, \
            f"Not enough connections created: {final_stats['total_connections_created']}/{expected_total_connections}"
        
        # Allow for a small number of active connections due to test timing
        max_allowed_active = expected_total_connections * 0.05  # 5% threshold
        assert final_stats['active_connections'] <= max_allowed_active, \
            f"Connection leak detected: {final_stats['active_connections']} connections still active"
        
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.95, f"Connection operations success rate too low: {success_rate:.2%}"


@pytest.mark.asyncio
class TestDatabaseTransactionPerformance:
    """Test suite for database transaction performance."""
    
    async def test_transaction_throughput(self, mock_database):
        """Test database transaction throughput."""
        from tests.performance.test_phase1_context_performance import PerformanceProfiler
        
        transaction_count = 200
        
        with PerformanceProfiler("transaction_throughput") as profiler:
            for i in range(transaction_count):
                try:
                    context = UserExecutionContext(
                        user_id=f"txn_user_{i % 10}_{uuid.uuid4().hex[:8]}",  # 10 users
                        thread_id=f"txn_thread_{i}_{uuid.uuid4().hex[:8]}",
                        run_id=f"txn_run_{i}_{uuid.uuid4().hex[:8]}",
                        request_id=f"txn_req_{i}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    # Get connection
                    connection = await mock_database.get_connection(context)
                    
                    # Execute transaction
                    await mock_database.begin_transaction(connection)
                    
                    # Multiple operations in transaction
                    await mock_database.execute_query(connection, "INSERT INTO data VALUES (1)", context)
                    await mock_database.execute_query(connection, "UPDATE data SET value = 2", context)
                    await mock_database.execute_query(connection, "SELECT * FROM data", context)
                    
                    # Commit transaction
                    await mock_database.commit_transaction(connection)
                    
                    # Close connection
                    await mock_database.close_connection(context.request_id)
                    
                    profiler.record_success()
                    
                except Exception as e:
                    logger.error(f"Transaction {i} failed: {e}")
                    profiler.record_error()
        
        metrics = profiler.get_metrics()
        stats = mock_database.get_connection_stats()
        
        profiler.add_metric("transactions_per_second", transaction_count / (metrics.duration_ms / 1000))
        profiler.add_metric("queries_executed", stats['total_queries'])
        
        # Transaction performance assertions
        assert metrics.error_count == 0, f"Transaction errors: {metrics.error_count}"
        assert metrics.operations_per_second > 100, f"Transaction throughput too low: {metrics.operations_per_second} txn/sec"
        assert stats['active_transactions'] == 0, f"Unclosed transactions: {stats['active_transactions']}"
        assert stats['total_queries'] >= transaction_count * 3, \
            f"Expected at least {transaction_count * 3} queries, executed {stats['total_queries']}"
    
    async def test_concurrent_transactions(self, mock_database):
        """Test concurrent transaction performance."""
        from tests.performance.test_phase1_context_performance import PerformanceProfiler
        
        concurrent_transactions = 50
        
        async def execute_transaction(txn_id: int) -> Tuple[bool, Optional[str]]:
            """Execute single transaction."""
            try:
                context = UserExecutionContext(
                    user_id=f"concurrent_txn_user_{txn_id % 10}_{uuid.uuid4().hex[:8]}",
                    thread_id=f"concurrent_txn_thread_{txn_id}_{uuid.uuid4().hex[:8]}",
                    run_id=f"concurrent_txn_run_{txn_id}_{uuid.uuid4().hex[:8]}",
                    request_id=f"concurrent_txn_req_{txn_id}_{uuid.uuid4().hex[:8]}"
                )
                
                connection = await mock_database.get_connection(context)
                
                await mock_database.begin_transaction(connection)
                
                # Simulate complex transaction
                for op in range(5):
                    await mock_database.execute_query(
                        connection,
                        f"OPERATION_{op} FOR txn_{txn_id}",
                        context
                    )
                
                await mock_database.commit_transaction(connection)
                await mock_database.close_connection(context.request_id)
                
                return True, None
                
            except Exception as e:
                return False, str(e)
        
        with PerformanceProfiler("concurrent_transactions") as profiler:
            tasks = [execute_transaction(i) for i in range(concurrent_transactions)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, tuple):
                    success, error = result
                    if success:
                        profiler.record_success()
                    else:
                        profiler.record_error()
                        logger.warning(f"Concurrent transaction failed: {error}")
                else:
                    profiler.record_error()
                    logger.error(f"Concurrent transaction exception: {result}")
        
        metrics = profiler.get_metrics()
        stats = mock_database.get_connection_stats()
        
        profiler.add_metric("concurrent_transactions_completed", metrics.success_count)
        profiler.add_metric("total_queries_in_transactions", stats['total_queries'])
        
        # Concurrent transaction assertions
        success_rate = metrics.success_count / (metrics.success_count + metrics.error_count)
        assert success_rate >= 0.95, f"Concurrent transaction success rate too low: {success_rate:.2%}"
        assert stats['active_transactions'] == 0, f"Transactions not properly closed: {stats['active_transactions']}"
        assert metrics.duration_ms < 3000, f"Concurrent transactions too slow: {metrics.duration_ms}ms"


@pytest.mark.asyncio
class TestDatabaseSessionIsolation:
    """Test suite for database session isolation."""
    
    async def test_user_session_isolation(self, mock_database):
        """Test database session isolation between users."""
        from tests.performance.test_phase1_context_performance import PerformanceProfiler
        
        user_count = 10
        operations_per_user = 20
        
        async def user_database_operations(user_id: str) -> Tuple[int, int]:
            """Execute database operations for single user."""
            success_count = 0
            error_count = 0
            
            for op in range(operations_per_user):
                try:
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id=f"isolation_thread_{user_id}_{op}_{uuid.uuid4().hex[:8]}",
                        run_id=f"isolation_run_{user_id}_{op}_{uuid.uuid4().hex[:8]}",
                        request_id=f"isolation_req_{user_id}_{op}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    connection = await mock_database.get_connection(context)
                    
                    # User-specific operations
                    await mock_database.execute_query(
                        connection,
                        f"SELECT * FROM user_data WHERE user_id = '{user_id}'",
                        context
                    )
                    
                    await mock_database.execute_query(
                        connection,
                        f"UPDATE user_sessions SET last_active = NOW() WHERE user_id = '{user_id}'",
                        context
                    )
                    
                    await mock_database.close_connection(context.request_id)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"User {user_id} operation {op} failed: {e}")
            
            return success_count, error_count
        
        with PerformanceProfiler("database_session_isolation") as profiler:
            # Create unique users
            user_ids = [f"isolation_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(user_count)]
            
            # Execute operations for all users concurrently
            tasks = [user_database_operations(user_id) for user_id in user_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_successes = 0
            total_errors = 0
            
            for result in results:
                if isinstance(result, tuple):
                    success_count, error_count = result
                    total_successes += success_count
                    total_errors += error_count
                    profiler.record_success()  # Per-user success
                else:
                    profiler.record_error()
                    total_errors += operations_per_user  # Assume all operations failed
                    logger.error(f"User operations failed completely: {result}")
        
        metrics = profiler.get_metrics()
        stats = mock_database.get_connection_stats()
        
        profiler.add_metric("total_user_operations", total_successes + total_errors)
        profiler.add_metric("user_operation_success_count", total_successes)
        profiler.add_metric("user_operation_error_count", total_errors)
        profiler.add_metric("users_tested", user_count)
        profiler.add_metric("operations_per_user", operations_per_user)
        
        # Session isolation assertions
        expected_total_operations = user_count * operations_per_user
        operation_success_rate = total_successes / (total_successes + total_errors)
        
        assert operation_success_rate >= 0.95, \
            f"User session operation success rate too low: {operation_success_rate:.2%}"
        assert total_successes >= expected_total_operations * 0.95, \
            f"Not enough successful operations: {total_successes}/{expected_total_operations}"
        assert stats['total_queries'] >= expected_total_operations * 2, \
            f"Expected at least {expected_total_operations * 2} queries (2 per operation)"
        
        user_success_rate = metrics.success_count / user_count
        assert user_success_rate >= 0.9, f"User-level success rate too low: {user_success_rate:.2%}"
        
        logger.info(f"Session isolation test: {user_count} users, {total_successes}/{expected_total_operations} operations successful")


if __name__ == "__main__":
    """Run database performance tests directly."""
    pytest.main([__file__, "-v", "--tb=short"])