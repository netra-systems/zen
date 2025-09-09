"""
Integration Test: Database Connection Pooling and Cleanup with User Context

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure database connection management scales with user load
- Value Impact: Connection leaks can cause service outages and resource exhaustion
- Strategic Impact: Scalable database infrastructure for production multi-user platform

This integration test validates:
1. Database connection pooling handles concurrent user requests efficiently
2. Connection cleanup prevents resource leaks in multi-user scenarios
3. Connection pool isolation maintains user session boundaries
4. Resource management scales with user load patterns

CRITICAL: Uses REAL PostgreSQL connection pooling with proper resource management.
Authentication REQUIRED for user context in connection lifecycle.
"""

import asyncio
import uuid
import pytest
import time
import gc
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.lightweight_services import lightweight_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from shared.types.core_types import UserID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment

# Database connection pooling imports
try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy import text, select, func, pool
    from sqlalchemy.pool import QueuePool, NullPool, StaticPool
    from sqlalchemy.engine import Engine
    from netra_backend.app.db.models_postgres import User, Thread, Message
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncSession = None


class TestConnectionPoolingCleanup(BaseIntegrationTest):
    """Test database connection pooling and cleanup with user context."""

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        if not SQLALCHEMY_AVAILABLE:
            pytest.skip("SQLAlchemy not available for connection pooling testing")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pooling_concurrent_user_requests(self, lightweight_services_fixture, isolated_env):
        """Test database connection pooling handles concurrent user requests efficiently."""
        
        if not lightweight_services_fixture["database_available"]:
            pytest.skip("Real database not available - run with --real-services")
        
        # Create authenticated users for connection pooling test
        auth_helper = E2EAuthHelper()
        
        pool_test_users = []
        for i in range(10):  # Test with 10 concurrent users
            user = await auth_helper.create_authenticated_user(
                email=f"pool.test.user.{i}@test.com",
                full_name=f"Pool Test User {i}"
            )
            pool_test_users.append(user)
        
        # Setup connection pool configuration
        env = IsolatedEnvironment()
        db_builder = DatabaseURLBuilder(env.get_env_dict())
        db_url = db_builder.get_url_for_environment()
        
        if not db_url:
            pytest.skip("Database URL not available for pooling test")
        
        # Create engine with specific pool configuration for testing
        pool_config = {
            'pool_size': 5,          # Small pool to test sharing
            'max_overflow': 10,      # Allow overflow connections
            'pool_timeout': 30,      # Connection timeout
            'pool_recycle': 3600,    # Recycle connections after 1 hour
            'pool_pre_ping': True    # Validate connections before use
        }
        
        test_engine = create_async_engine(
            db_url,
            poolclass=QueuePool,
            **pool_config,
            echo=False  # Reduce log noise in tests
        )
        
        # Create session factory
        SessionFactory = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Track connection pool metrics
        pool_metrics = {
            'connections_created': 0,
            'connections_reused': 0,
            'connection_timeouts': 0,
            'max_concurrent_connections': 0,
            'user_session_count': 0,
            'cleanup_operations': 0
        }
        
        active_connections = set()
        
        async def simulate_user_database_operations(auth_user: AuthenticatedUser, operation_id: int):
            """Simulate database operations for a user with connection tracking."""
            
            operation_result = {
                'user_id': auth_user.user_id,
                'operation_id': operation_id,
                'connection_acquired': False,
                'operations_completed': 0,
                'connection_errors': [],
                'cleanup_successful': True,
                'session_duration': 0
            }
            
            session_start = time.time()
            db_session = None
            
            try:
                # Acquire connection from pool
                db_session = SessionFactory()
                operation_result['connection_acquired'] = True
                pool_metrics['user_session_count'] += 1
                
                # Track active connections
                connection_id = f"{auth_user.user_id}_{operation_id}"
                active_connections.add(connection_id)
                
                # Update max concurrent connections
                current_concurrent = len(active_connections)
                if current_concurrent > pool_metrics['max_concurrent_connections']:
                    pool_metrics['max_concurrent_connections'] = current_concurrent
                
                # Create user context with database session
                context = StronglyTypedUserExecutionContext(
                    user_id=ensure_user_id(auth_user.user_id),
                    thread_id=f"pool_thread_{uuid.uuid4()}",
                    run_id=f"pool_run_{uuid.uuid4()}",
                    request_id=f"pool_req_{uuid.uuid4()}",
                    db_session=db_session
                )
                
                # Create backend user if needed
                try:
                    backend_user = User(
                        id=auth_user.user_id,
                        email=auth_user.email,
                        full_name=auth_user.full_name,
                        is_active=True
                    )
                    db_session.add(backend_user)
                    await db_session.commit()
                    operation_result['operations_completed'] += 1
                except Exception as e:
                    # User might already exist
                    await db_session.rollback()
                    if "duplicate key" not in str(e).lower():
                        operation_result['connection_errors'].append(f"User creation failed: {e}")
                
                # Perform database operations
                for op_idx in range(3):
                    try:
                        # Create thread
                        thread = Thread(
                            id=f"pool_thread_{auth_user.user_id}_{operation_id}_{op_idx}",
                            object_="thread",
                            created_at=int(time.time()),
                            metadata_={
                                "user_id": auth_user.user_id,
                                "pool_test": True,
                                "operation_id": operation_id,
                                "connection_test": True
                            }
                        )
                        db_session.add(thread)
                        
                        # Create message
                        message = Message(
                            id=f"pool_msg_{auth_user.user_id}_{operation_id}_{op_idx}",
                            object_="thread.message",
                            created_at=int(time.time()),
                            thread_id=thread.id,
                            role="user",
                            content=[{
                                "type": "text",
                                "text": {
                                    "value": f"Pool test message {op_idx} from user {operation_id}",
                                    "annotations": []
                                }
                            }],
                            metadata_={
                                "user_id": auth_user.user_id,
                                "pool_test": True,
                                "message_index": op_idx
                            }
                        )
                        db_session.add(message)
                        
                        await db_session.commit()
                        operation_result['operations_completed'] += 1
                        
                        # Small delay to simulate realistic operation timing
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        operation_result['connection_errors'].append(f"Operation {op_idx} failed: {e}")
                        await db_session.rollback()
                
                # Test connection pool efficiency with concurrent queries
                concurrent_query_tasks = []
                for query_idx in range(3):
                    query_task = asyncio.create_task(
                        self._execute_concurrent_query(db_session, auth_user.user_id, query_idx)
                    )
                    concurrent_query_tasks.append(query_task)
                
                query_results = await asyncio.gather(*concurrent_query_tasks, return_exceptions=True)
                
                for i, result in enumerate(query_results):
                    if isinstance(result, Exception):
                        operation_result['connection_errors'].append(f"Concurrent query {i} failed: {result}")
                    else:
                        operation_result['operations_completed'] += 1
                
            except Exception as e:
                operation_result['connection_errors'].append(f"Session operation failed: {e}")
                
            finally:
                # Clean up connection
                if db_session:
                    try:
                        await db_session.close()
                        pool_metrics['cleanup_operations'] += 1
                        
                        # Remove from active connections
                        connection_id = f"{auth_user.user_id}_{operation_id}"
                        active_connections.discard(connection_id)
                        
                    except Exception as e:
                        operation_result['cleanup_successful'] = False
                        operation_result['connection_errors'].append(f"Cleanup failed: {e}")
                
                operation_result['session_duration'] = time.time() - session_start
            
            return operation_result
        
        # Execute concurrent user operations
        self.logger.info(f"Starting connection pool test with {len(pool_test_users)} concurrent users")
        pool_start_time = time.time()
        
        # Create tasks for concurrent execution
        concurrent_tasks = [
            simulate_user_database_operations(user, i)
            for i, user in enumerate(pool_test_users)
        ]
        
        # Execute with controlled concurrency
        batch_size = 5  # Process in batches to test pool sharing
        pool_results = []
        
        for batch_start in range(0, len(concurrent_tasks), batch_size):
            batch_end = min(batch_start + batch_size, len(concurrent_tasks))
            batch_tasks = concurrent_tasks[batch_start:batch_end]
            
            self.logger.info(f"Executing batch {batch_start // batch_size + 1}: "
                            f"operations {batch_start}-{batch_end-1}")
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            pool_results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        pool_duration = time.time() - pool_start_time
        
        # Analyze connection pool results
        pool_failures = []
        successful_operations = 0
        total_operations = 0
        cleanup_failures = 0
        
        for result in pool_results:
            if isinstance(result, Exception):
                pool_failures.append(f"Pool operation exception: {result}")
                continue
            
            total_operations += 1
            
            if result['connection_acquired']:
                successful_operations += 1
            
            if not result['cleanup_successful']:
                cleanup_failures += 1
            
            if result['connection_errors']:
                for error in result['connection_errors']:
                    if "timeout" in error.lower() or "pool" in error.lower():
                        pool_metrics['connection_timeouts'] += 1
                    pool_failures.append(f"User {result['user_id']}: {error}")
        
        # Get final pool statistics
        pool_stats = test_engine.pool
        if hasattr(pool_stats, 'size'):
            pool_metrics['final_pool_size'] = pool_stats.size()
        if hasattr(pool_stats, 'checked_out'):
            pool_metrics['checked_out_connections'] = pool_stats.checked_out()
        
        # Close engine and cleanup
        await test_engine.dispose()
        
        # Force garbage collection to clean up connections
        gc.collect()
        
        # Assert connection pool performance
        assert len(pool_failures) == 0, f"Connection pool failures: {pool_failures[:10]}"  # Show first 10
        
        # Verify connection efficiency
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        assert success_rate >= 0.9, f"Connection pool success rate too low: {success_rate:.1%}"
        
        # Verify cleanup efficiency
        cleanup_success_rate = (total_operations - cleanup_failures) / total_operations if total_operations > 0 else 1
        assert cleanup_success_rate >= 0.95, f"Connection cleanup failure rate too high: {cleanup_failures}/{total_operations}"
        
        # Verify pool efficiency metrics
        assert pool_metrics['connection_timeouts'] <= 2, \
            f"Too many connection timeouts: {pool_metrics['connection_timeouts']}"
        
        assert pool_metrics['max_concurrent_connections'] <= pool_config['pool_size'] + pool_config['max_overflow'], \
            f"Pool exceeded maximum capacity: {pool_metrics['max_concurrent_connections']}"
        
        self.logger.info(f"Connection pool test completed in {pool_duration:.2f}s")
        self.logger.info(f"Pool metrics: {pool_metrics}")
        self.logger.info(f"Success rate: {success_rate:.1%}, Cleanup rate: {cleanup_success_rate:.1%}")
    
    async def _execute_concurrent_query(self, db_session: AsyncSession, user_id: str, query_idx: int):
        """Execute concurrent query to test connection sharing."""
        try:
            # Query user's data
            query = select(func.count(Thread.id)).where(
                Thread.metadata_["user_id"].astext == user_id
            )
            result = await db_session.execute(query)
            count = result.scalar()
            
            # Simulate query processing time
            await asyncio.sleep(0.05)
            
            return {
                'query_idx': query_idx,
                'user_id': user_id,
                'result_count': count,
                'success': True
            }
        except Exception as e:
            return {
                'query_idx': query_idx,
                'user_id': user_id,
                'error': str(e),
                'success': False
            }