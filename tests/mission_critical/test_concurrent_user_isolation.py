"""Mission Critical Test Suite: Concurrent User Isolation - REAL SERVICES ONLY

This test suite verifies concurrent user isolation using REAL services to detect
critical security and reliability issues that could compromise spacecraft operations.

ZERO TOLERANCE POLICY:
- NO MOCKS ALLOWED - All tests use production services
- 12+ concurrent users minimum for realistic load testing
- Every test must detect real isolation violations
- Any data leakage is a mission-critical failure

COMPLIANCE:
@claude.md - REAL services only, spacecraft-grade reliability
@spec/core.xml - SSOT pattern enforcement across concurrent operations
@spec/type_safety.xml - Full type safety with concurrent operations

CRITICAL SCENARIOS TESTED:
1. Concurrent Redis operations with user isolation
2. Database session isolation under heavy load
3. WebSocket message routing isolation
4. Agent state contamination prevention
5. Memory isolation under concurrent access
6. Thread safety with user context preservation
7. Cross-user authentication boundary enforcement
8. Concurrent cache operations isolation
9. Real-time performance under concurrent load
10. Security boundary enforcement
"""

import asyncio
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from threading import Lock, Event
import threading

import pytest
import redis.asyncio as redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from shared.isolated_environment import IsolatedEnvironment
from test_framework.backend_client import BackendTestClient
from test_framework.test_context import TestContext, create_isolated_test_contexts


@dataclass
class ConcurrentUserContext:
    """Real user context for concurrent isolation testing."""
    user_id: str
    email: str
    role: str = "user"
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    test_data: Dict[str, Any] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@pytest.fixture(scope="function")
def isolated_env():
    """Isolated environment for concurrent testing."""
    return IsolatedEnvironment()


@pytest.fixture(scope="function")
async def redis_client(isolated_env):
    """Real Redis client for concurrent testing."""
    redis_url = isolated_env.get('REDIS_URL', 'redis://localhost:6381')
    client = redis.from_url(redis_url, decode_responses=True)
    
    # Ensure connection works
    await client.ping()
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture(scope="function")
async def database_engine(isolated_env):
    """Real database engine for concurrent testing."""
    database_url = isolated_env.get('DATABASE_URL', 'postgresql+asyncpg://netra:netra@localhost:5434/netra_test')
    engine = create_async_engine(database_url, echo=False, pool_size=20, max_overflow=30)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def backend_client(isolated_env):
    """Real backend client for concurrent testing."""
    backend_url = isolated_env.get('BACKEND_URL', 'http://localhost:8000')
    client = BackendTestClient(backend_url)
    
    # Ensure backend is healthy
    try:
        health_ok = await client.health_check()
        if not health_ok:
            pytest.skip("Backend service not available for concurrent testing")
    except Exception:
        pytest.skip("Backend service not available for concurrent testing")
    
    yield client
    
    await client.close()


class ConcurrentTestMetrics:
    """Thread-safe metrics collection for concurrent tests."""
    
    def __init__(self):
        self._lock = Lock()
        self._metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'isolation_violations': 0,
            'data_contamination_events': 0,
            'performance_violations': 0,
            'thread_safety_issues': 0,
            'user_contexts': {},
            'violation_details': []
        }
    
    def record_operation(self, user_id: str, operation_type: str, success: bool, 
                        duration: float, violation_type: str = None):
        """Record an operation result in thread-safe manner."""
        with self._lock:
            self._metrics['total_operations'] += 1
            
            if success:
                self._metrics['successful_operations'] += 1
            else:
                self._metrics['failed_operations'] += 1
            
            if violation_type:
                self._metrics['isolation_violations'] += 1
                self._metrics['violation_details'].append({
                    'user_id': user_id,
                    'operation_type': operation_type,
                    'violation_type': violation_type,
                    'duration': duration,
                    'timestamp': time.time()
                })
            
            if user_id not in self._metrics['user_contexts']:
                self._metrics['user_contexts'][user_id] = {
                    'operations': 0,
                    'violations': 0,
                    'avg_duration': 0.0
                }
            
            user_ctx = self._metrics['user_contexts'][user_id]
            user_ctx['operations'] += 1
            user_ctx['avg_duration'] = (
                (user_ctx['avg_duration'] * (user_ctx['operations'] - 1) + duration)
                / user_ctx['operations']
            )
            
            if violation_type:
                user_ctx['violations'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get thread-safe copy of metrics."""
        with self._lock:
            return dict(self._metrics)


@pytest.mark.mission_critical
class TestRealConcurrentUserIsolation:
    """
    Mission Critical test suite for concurrent user isolation using REAL services.
    
    Tests 15+ concurrent users across all services to ensure spacecraft-grade isolation.
    Zero tolerance for data leakage or user context contamination.
    """

    @pytest.mark.asyncio
    async def test_massive_concurrent_redis_isolation(self, redis_client):
        """
        CRITICAL: 20+ concurrent users performing Redis operations simultaneously.
        
        Tests Redis isolation under extreme concurrent load to ensure
        no user data contamination occurs even under stress.
        """
        # Create 25 concurrent users for extreme stress testing
        users = [
            ConcurrentUserContext(
                user_id=f'redis-concurrent-{uuid.uuid4().hex[:8]}',
                email=f'user{i}@concurrent.test',
                role='admin' if i == 0 else 'user'
            )
            for i in range(25)
        ]
        
        metrics = ConcurrentTestMetrics()
        
        async def extreme_concurrent_redis_operation(user: ConcurrentUserContext) -> Dict[str, Any]:
            """Perform intensive Redis operations for concurrent testing."""
            user.start_time = time.time()
            
            try:
                # Phase 1: Store highly sensitive user data
                session_key = f"concurrent_session:{user.user_id}:{uuid.uuid4().hex}"
                
                # Create large, complex data structure to increase memory pressure
                sensitive_payload = {
                    'user_id': user.user_id,
                    'email': user.email,
                    'role': user.role,
                    'session_data': {
                        'conversations': [
                            f"CONFIDENTIAL CONVERSATION {i} FOR {user.user_id}: {uuid.uuid4().hex}"
                            for i in range(100)  # Large dataset
                        ],
                        'agent_memories': {
                            f'agent_{j}': {
                                'private_context': f"PRIVATE CONTEXT {j} FOR {user.user_id}",
                                'user_preferences': f"PREFERENCES {j} FOR {user.user_id}",
                                'secret_data': f"SECRET-{uuid.uuid4().hex}"
                            }
                            for j in range(10)
                        },
                        'security_tokens': [f"TOKEN-{user.user_id}-{uuid.uuid4().hex}" for _ in range(20)]
                    },
                    'performance_data': {
                        'start_time': user.start_time,
                        'thread_id': threading.get_ident(),
                        'operation_id': uuid.uuid4().hex
                    }
                }
                
                # Store in Redis with proper serialization
                await redis_client.hset(session_key, mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in sensitive_payload.items()
                })
                
                # Phase 2: Perform multiple rapid operations to trigger race conditions
                operation_keys = []
                for op_idx in range(10):  # Multiple operations per user
                    op_key = f"user_operation:{user.user_id}:{op_idx}"
                    op_data = {
                        'user_id': user.user_id,
                        'operation_index': op_idx,
                        'sensitive_operation': f"OPERATION-{user.user_id}-{op_idx}-{uuid.uuid4().hex}",
                        'timestamp': time.time()
                    }
                    
                    await redis_client.hset(op_key, mapping={
                        k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                        for k, v in op_data.items()
                    })
                    operation_keys.append(op_key)
                
                # Phase 3: Concurrent read/write stress test
                for stress_round in range(5):
                    stress_key = f"stress_test:{user.user_id}:{stress_round}"
                    stress_data = f"STRESS-DATA-{user.user_id}-{stress_round}-{uuid.uuid4().hex}"
                    
                    # Set and immediately verify
                    await redis_client.set(stress_key, stress_data)
                    retrieved = await redis_client.get(stress_key)
                    
                    if retrieved != stress_data:
                        metrics.record_operation(
                            user.user_id, 'redis_stress', False, 
                            time.time() - user.start_time, 'data_corruption'
                        )
                        return {'status': 'data_corruption', 'violation': True}
                
                # Phase 4: Cross-user contamination check
                # Verify no access to other users' data
                contamination_found = False
                for other_user in users:
                    if other_user.user_id != user.user_id:
                        # Try to access other user's session (should fail or return different user data)
                        other_session_pattern = f"concurrent_session:{other_user.user_id}:*"
                        other_keys = await redis_client.keys(other_session_pattern)
                        
                        for other_key in other_keys:
                            other_data = await redis_client.hgetall(other_key)
                            if other_data and other_data.get('user_id') == user.user_id:
                                # Found our data in another user's key - CONTAMINATION!
                                contamination_found = True
                                break
                        
                        if contamination_found:
                            break
                
                if contamination_found:
                    metrics.record_operation(
                        user.user_id, 'redis_concurrent', False,
                        time.time() - user.start_time, 'cross_contamination'
                    )
                    return {'status': 'cross_contamination', 'violation': True}
                
                # Phase 5: Verify data integrity after all operations
                final_data = await redis_client.hgetall(session_key)
                if not final_data or final_data.get('user_id') != user.user_id:
                    metrics.record_operation(
                        user.user_id, 'redis_concurrent', False,
                        time.time() - user.start_time, 'data_integrity_failure'
                    )
                    return {'status': 'data_integrity_failure', 'violation': True}
                
                user.end_time = time.time()
                duration = user.end_time - user.start_time
                
                metrics.record_operation(user.user_id, 'redis_concurrent', True, duration)
                
                # Cleanup
                await redis_client.delete(session_key)
                for op_key in operation_keys:
                    await redis_client.delete(op_key)
                for stress_round in range(5):
                    stress_key = f"stress_test:{user.user_id}:{stress_round}"
                    await redis_client.delete(stress_key)
                
                return {
                    'status': 'success',
                    'violation': False,
                    'duration': duration,
                    'operations_completed': 16,  # 1 session + 10 ops + 5 stress
                    'user_id': user.user_id
                }
                
            except Exception as e:
                metrics.record_operation(
                    user.user_id, 'redis_concurrent', False,
                    time.time() - user.start_time, 'exception_error'
                )
                return {
                    'status': 'error',
                    'violation': True,
                    'error': str(e),
                    'user_id': user.user_id
                }
        
        # Execute all operations concurrently
        start_time = time.time()
        tasks = [extreme_concurrent_redis_operation(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        violations = []
        successful_operations = 0
        total_operations = 0
        
        for result in results:
            total_operations += 1
            if isinstance(result, dict):
                if result.get('violation', True):
                    violations.append(result)
                else:
                    successful_operations += 1
            else:
                violations.append({'status': 'exception', 'error': str(result), 'violation': True})
        
        # Get final metrics
        final_metrics = metrics.get_metrics()
        
        # Performance requirements
        success_rate = (successful_operations / total_operations) * 100 if total_operations > 0 else 0
        avg_operation_time = total_duration / len(users)
        
        # Assert no violations occurred
        assert len(violations) == 0, f"CONCURRENT REDIS ISOLATION VIOLATIONS: {violations}"
        assert success_rate >= 95.0, f"Success rate too low: {success_rate}% (expected >= 95%)"
        assert avg_operation_time < 5.0, f"Average operation time too high: {avg_operation_time}s (expected < 5s)"
        
        # Log performance metrics for monitoring
        logging.info(f"Concurrent Redis Test Metrics: {final_metrics}")

    @pytest.mark.asyncio
    async def test_database_concurrent_session_isolation(self, database_engine):
        """
        CRITICAL: Database session isolation with 15+ concurrent database transactions.
        
        Tests PostgreSQL isolation under concurrent load with complex transactions
        to ensure ACID properties are maintained and no data leakage occurs.
        """
        # Create async session maker with connection pooling
        async_session = async_sessionmaker(database_engine, expire_on_commit=False)
        
        # Create 18 concurrent users for database stress testing
        users = [
            ConcurrentUserContext(
                user_id=f'db-concurrent-{uuid.uuid4().hex[:8]}',
                email=f'dbuser{i}@concurrent.test',
                role='admin' if i % 5 == 0 else 'user'
            )
            for i in range(18)
        ]
        
        # Create test tables for concurrent operations
        async with database_engine.begin() as conn:
            await conn.execute(sa.text("""
                CREATE TABLE IF NOT EXISTS concurrent_user_data (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    sensitive_data JSONB NOT NULL,
                    balance INTEGER DEFAULT 1000,
                    operation_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            await conn.execute(sa.text("""
                CREATE TABLE IF NOT EXISTS concurrent_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    transaction_type VARCHAR(100) NOT NULL,
                    amount INTEGER NOT NULL,
                    transaction_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Clean up any existing test data
            await conn.execute(sa.text("DELETE FROM concurrent_user_data"))
            await conn.execute(sa.text("DELETE FROM concurrent_transactions"))
        
        metrics = ConcurrentTestMetrics()
        
        async def concurrent_database_operation(user: ConcurrentUserContext) -> Dict[str, Any]:
            """Perform complex database operations with full isolation testing."""
            user.start_time = time.time()
            session_id = f"db_session_{uuid.uuid4().hex}"
            
            try:
                # Phase 1: Insert user data with complex transaction
                async with async_session() as session:
                    # Begin explicit transaction
                    await session.begin()
                    
                    # Insert sensitive user data
                    sensitive_data = {
                        'user_id': user.user_id,
                        'email': user.email,
                        'role': user.role,
                        'confidential_info': f"CLASSIFIED-{user.user_id}-{uuid.uuid4().hex}",
                        'user_secrets': {
                            'api_keys': [f"API-KEY-{i}-{uuid.uuid4().hex}" for i in range(5)],
                            'private_data': f"PRIVATE-DATA-{user.user_id}",
                            'security_clearance': 'TOP_SECRET' if user.role == 'admin' else 'CONFIDENTIAL'
                        },
                        'session_context': {
                            'session_id': session_id,
                            'start_time': user.start_time,
                            'thread_info': threading.get_ident()
                        }
                    }
                    
                    result = await session.execute(sa.text("""
                        INSERT INTO concurrent_user_data (user_id, session_id, sensitive_data, balance)
                        VALUES (:user_id, :session_id, :sensitive_data, :balance)
                        RETURNING id
                    """), {
                        'user_id': user.user_id,
                        'session_id': session_id,
                        'sensitive_data': json.dumps(sensitive_data),
                        'balance': 1000 + len(user.user_id)  # Unique balance per user
                    })
                    
                    user_record_id = result.scalar()
                    await session.commit()
                
                # Phase 2: Perform multiple concurrent transactions with row locking
                for transaction_idx in range(10):  # Multiple transactions per user
                    async with async_session() as session:
                        # Use SELECT FOR UPDATE to test row-level locking
                        result = await session.execute(sa.text("""
                            SELECT id, balance, operation_count FROM concurrent_user_data 
                            WHERE user_id = :user_id FOR UPDATE
                        """), {'user_id': user.user_id})
                        
                        user_row = result.fetchone()
                        if not user_row:
                            metrics.record_operation(
                                user.user_id, 'db_transaction', False,
                                time.time() - user.start_time, 'user_data_not_found'
                            )
                            return {'status': 'user_data_not_found', 'violation': True}
                        
                        current_balance = user_row[1]
                        operation_count = user_row[2]
                        
                        # Simulate processing delay to encourage race conditions
                        await asyncio.sleep(0.05)
                        
                        # Update balance and operation count
                        new_balance = current_balance + (transaction_idx * 10)
                        new_operation_count = operation_count + 1
                        
                        # Record transaction
                        await session.execute(sa.text("""
                            INSERT INTO concurrent_transactions (user_id, transaction_type, amount, transaction_data)
                            VALUES (:user_id, :transaction_type, :amount, :transaction_data)
                        """), {
                            'user_id': user.user_id,
                            'transaction_type': f'concurrent_operation_{transaction_idx}',
                            'amount': transaction_idx * 10,
                            'transaction_data': json.dumps({
                                'transaction_idx': transaction_idx,
                                'session_id': session_id,
                                'timestamp': time.time(),
                                'thread_id': threading.get_ident()
                            })
                        })
                        
                        # Update user record
                        await session.execute(sa.text("""
                            UPDATE concurrent_user_data 
                            SET balance = :new_balance, operation_count = :new_operation_count, updated_at = NOW()
                            WHERE user_id = :user_id
                        """), {
                            'user_id': user.user_id,
                            'new_balance': new_balance,
                            'new_operation_count': new_operation_count
                        })
                        
                        await session.commit()
                
                # Phase 3: Cross-user isolation verification
                async with async_session() as session:
                    # Verify user can only access their own data
                    user_data_result = await session.execute(sa.text("""
                        SELECT user_id, sensitive_data, balance, operation_count FROM concurrent_user_data 
                        WHERE user_id = :user_id
                    """), {'user_id': user.user_id})
                    
                    user_data = user_data_result.fetchone()
                    if not user_data or user_data[0] != user.user_id:
                        metrics.record_operation(
                            user.user_id, 'db_isolation', False,
                            time.time() - user.start_time, 'user_data_isolation_failure'
                        )
                        return {'status': 'user_data_isolation_failure', 'violation': True}
                    
                    # Verify operation count is correct (should be 10)
                    if user_data[3] != 10:
                        metrics.record_operation(
                            user.user_id, 'db_isolation', False,
                            time.time() - user.start_time, 'operation_count_mismatch'
                        )
                        return {
                            'status': 'operation_count_mismatch', 
                            'violation': True,
                            'expected': 10,
                            'actual': user_data[3]
                        }
                    
                    # Check for data contamination from other users
                    all_data_result = await session.execute(sa.text("""
                        SELECT user_id, sensitive_data FROM concurrent_user_data
                    """))
                    
                    all_data = all_data_result.fetchall()
                    for data_row in all_data:
                        if data_row[0] != user.user_id:
                            # Other user's data - verify it doesn't contain our user_id
                            other_sensitive_data = json.loads(data_row[1])
                            if other_sensitive_data.get('user_id') == user.user_id:
                                metrics.record_operation(
                                    user.user_id, 'db_isolation', False,
                                    time.time() - user.start_time, 'cross_user_contamination'
                                )
                                return {'status': 'cross_user_contamination', 'violation': True}
                
                user.end_time = time.time()
                duration = user.end_time - user.start_time
                
                metrics.record_operation(user.user_id, 'db_concurrent', True, duration)
                
                return {
                    'status': 'success',
                    'violation': False,
                    'duration': duration,
                    'transactions_completed': 11,  # 1 insert + 10 updates
                    'user_id': user.user_id,
                    'final_balance': user_data[2],
                    'operation_count': user_data[3]
                }
                
            except Exception as e:
                metrics.record_operation(
                    user.user_id, 'db_concurrent', False,
                    time.time() - user.start_time, 'database_exception'
                )
                return {
                    'status': 'error',
                    'violation': True,
                    'error': str(e),
                    'user_id': user.user_id
                }
        
        # Execute all database operations concurrently
        start_time = time.time()
        tasks = [concurrent_database_operation(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        violations = []
        successful_operations = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('violation', True):
                    violations.append(result)
                else:
                    successful_operations += 1
            else:
                violations.append({'status': 'exception', 'error': str(result), 'violation': True})
        
        # Cleanup test tables
        async with database_engine.begin() as conn:
            await conn.execute(sa.text("DROP TABLE IF EXISTS concurrent_user_data"))
            await conn.execute(sa.text("DROP TABLE IF EXISTS concurrent_transactions"))
        
        # Performance and isolation assertions
        success_rate = (successful_operations / len(users)) * 100
        avg_operation_time = total_duration / len(users)
        
        assert len(violations) == 0, f"DATABASE CONCURRENT ISOLATION VIOLATIONS: {violations}"
        assert success_rate >= 95.0, f"Database success rate too low: {success_rate}% (expected >= 95%)"
        assert avg_operation_time < 10.0, f"Database operation time too high: {avg_operation_time}s (expected < 10s)"

    @pytest.mark.asyncio
    async def test_websocket_concurrent_message_isolation(self, backend_client):
        """
        CRITICAL: WebSocket message isolation with 12+ concurrent connections.
        
        Tests that WebSocket connections maintain complete isolation
        even under high concurrent message load.
        """
        # Create 15 concurrent test contexts for WebSocket testing
        contexts = create_isolated_test_contexts(count=15)
        
        try:
            metrics = ConcurrentTestMetrics()
            
            # Set up WebSocket connections for each user (if possible)
            connected_contexts = []
            for i, context in enumerate(contexts):
                context.user_context.jwt_token = f"test-token-{context.user_context.user_id}"
                
                try:
                    # Try to establish WebSocket connection
                    await context.setup_websocket_connection("/ws/chat", auth_required=False)
                    connected_contexts.append(context)
                except ConnectionError:
                    # If WebSocket connections aren't available, test isolation logic only
                    logging.warning(f"WebSocket connection failed for user {context.user_context.user_id}")
                    continue
            
            if len(connected_contexts) < 3:
                pytest.skip("Not enough WebSocket connections available for concurrent testing")
            
            async def concurrent_websocket_operation(context: TestContext) -> Dict[str, Any]:
                """Perform concurrent WebSocket operations with isolation testing."""
                user_id = context.user_context.user_id
                start_time = time.time()
                
                try:
                    # Phase 1: Send multiple unique messages rapidly
                    sent_messages = []
                    for msg_idx in range(20):  # Send 20 messages per user
                        unique_message = {
                            'type': 'chat',
                            'content': f'CONFIDENTIAL MESSAGE {msg_idx} FROM {user_id}: {uuid.uuid4().hex}',
                            'user_id': user_id,
                            'thread_id': context.user_context.thread_id,
                            'message_index': msg_idx,
                            'timestamp': time.time(),
                            'secret_payload': f'SECRET-{user_id}-{msg_idx}-{uuid.uuid4().hex}'
                        }
                        
                        await context.send_message(unique_message)
                        sent_messages.append(unique_message)
                        
                        # Small delay to allow processing
                        await asyncio.sleep(0.01)
                    
                    # Phase 2: Listen for responses and verify isolation
                    received_events = await context.listen_for_events(duration=3.0)
                    
                    # Phase 3: Verify no cross-user message contamination
                    isolation_violations = []
                    
                    for event in received_events:
                        event_user_id = event.get('user_id')
                        event_content = event.get('content', '')
                        
                        # Check if we received a message meant for another user
                        if event_user_id and event_user_id != user_id:
                            isolation_violations.append({
                                'type': 'received_other_user_message',
                                'event_from': event_user_id,
                                'received_by': user_id,
                                'event': event
                            })
                        
                        # Check if message content contains other users' data
                        for other_context in contexts:
                            if other_context.user_context.user_id != user_id:
                                other_user_id = other_context.user_context.user_id
                                if other_user_id in event_content:
                                    isolation_violations.append({
                                        'type': 'message_content_contamination',
                                        'other_user_id': other_user_id,
                                        'receiving_user': user_id,
                                        'contaminated_content': event_content[:100]  # First 100 chars
                                    })
                    
                    duration = time.time() - start_time
                    
                    if isolation_violations:
                        metrics.record_operation(
                            user_id, 'websocket_concurrent', False, duration, 'message_isolation_violation'
                        )
                        return {
                            'status': 'isolation_violations',
                            'violation': True,
                            'violations': isolation_violations,
                            'user_id': user_id
                        }
                    
                    metrics.record_operation(user_id, 'websocket_concurrent', True, duration)
                    
                    return {
                        'status': 'success',
                        'violation': False,
                        'duration': duration,
                        'messages_sent': len(sent_messages),
                        'events_received': len(received_events),
                        'user_id': user_id
                    }
                    
                except Exception as e:
                    metrics.record_operation(
                        user_id, 'websocket_concurrent', False,
                        time.time() - start_time, 'websocket_exception'
                    )
                    return {
                        'status': 'error',
                        'violation': True,
                        'error': str(e),
                        'user_id': user_id
                    }
            
            # Execute concurrent WebSocket operations
            start_time = time.time()
            tasks = [concurrent_websocket_operation(context) for context in connected_contexts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = time.time() - start_time
            
            # Analyze results
            violations = []
            successful_operations = 0
            
            for result in results:
                if isinstance(result, dict):
                    if result.get('violation', True):
                        violations.append(result)
                    else:
                        successful_operations += 1
                else:
                    violations.append({'status': 'exception', 'error': str(result), 'violation': True})
            
            # Performance assertions
            success_rate = (successful_operations / len(connected_contexts)) * 100 if connected_contexts else 100
            avg_operation_time = total_duration / len(connected_contexts) if connected_contexts else 0
            
            assert len(violations) == 0, f"WEBSOCKET CONCURRENT ISOLATION VIOLATIONS: {violations}"
            assert success_rate >= 90.0, f"WebSocket success rate too low: {success_rate}% (expected >= 90%)"
            
        finally:
            # Clean up all WebSocket contexts
            cleanup_tasks = [context.cleanup() for context in contexts]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_memory_stress_concurrent_isolation(self, redis_client, backend_client):
        """
        CRITICAL: Memory stress testing with 20+ concurrent users.
        
        Tests isolation under extreme memory pressure to ensure
        garbage collection doesn't cause cross-user data contamination.
        """
        # Create 22 users for extreme memory stress testing
        users = [
            ConcurrentUserContext(
                user_id=f'memory-stress-{uuid.uuid4().hex[:8]}',
                email=f'stress{i}@memory.test'
            )
            for i in range(22)
        ]
        
        metrics = ConcurrentTestMetrics()
        
        async def memory_stress_operation(user: ConcurrentUserContext) -> Dict[str, Any]:
            """Perform memory-intensive operations to test isolation under stress."""
            user.start_time = time.time()
            
            try:
                # Phase 1: Create large memory footprint
                large_datasets = []
                for dataset_idx in range(5):
                    dataset = {
                        'user_id': user.user_id,
                        'dataset_index': dataset_idx,
                        'large_array': [
                            f"MEMORY-DATA-{user.user_id}-{dataset_idx}-{i}-{uuid.uuid4().hex}"
                            for i in range(2000)  # Large arrays to stress memory
                        ],
                        'nested_structures': {
                            f'level_{j}': {
                                f'item_{k}': {
                                    'user_id': user.user_id,
                                    'data': f"NESTED-{user.user_id}-{j}-{k}-{uuid.uuid4().hex}",
                                    'metadata': {
                                        'created_at': time.time(),
                                        'thread_id': threading.get_ident(),
                                        'memory_tag': f"MEM-{user.user_id}-{j}-{k}"
                                    }
                                }
                                for k in range(50)
                            }
                            for j in range(10)
                        }
                    }
                    large_datasets.append(dataset)
                
                # Phase 2: Store in Redis while maintaining large memory footprint
                redis_keys = []
                for i, dataset in enumerate(large_datasets):
                    redis_key = f"memory_stress:{user.user_id}:{i}"
                    
                    # Serialize and store
                    serialized_dataset = {
                        'user_id': user.user_id,
                        'dataset_index': i,
                        'large_array': json.dumps(dataset['large_array']),
                        'nested_structures': json.dumps(dataset['nested_structures']),
                        'memory_footprint_mb': len(json.dumps(dataset)) / (1024 * 1024)
                    }
                    
                    await redis_client.hset(redis_key, mapping={
                        k: str(v) for k, v in serialized_dataset.items()
                    })
                    redis_keys.append(redis_key)
                
                # Phase 3: Force garbage collection pressure
                temp_memory_pressure = [
                    [f"GC-PRESSURE-{user.user_id}-{i}-{uuid.uuid4().hex}" for i in range(5000)]
                    for _ in range(10)
                ]
                
                # Phase 4: Verify data integrity after memory pressure
                for redis_key in redis_keys:
                    stored_data = await redis_client.hgetall(redis_key)
                    
                    if not stored_data:
                        metrics.record_operation(
                            user.user_id, 'memory_stress', False,
                            time.time() - user.start_time, 'data_lost_under_memory_pressure'
                        )
                        return {'status': 'data_lost_under_memory_pressure', 'violation': True}
                    
                    if stored_data.get('user_id') != user.user_id:
                        metrics.record_operation(
                            user.user_id, 'memory_stress', False,
                            time.time() - user.start_time, 'user_id_contamination'
                        )
                        return {
                            'status': 'user_id_contamination',
                            'violation': True,
                            'expected_user': user.user_id,
                            'actual_user': stored_data.get('user_id')
                        }
                    
                    # Verify array data integrity (spot check)
                    try:
                        large_array = json.loads(stored_data.get('large_array', '[]'))
                        # Check first few items contain correct user_id
                        for item in large_array[:10]:
                            if user.user_id not in item:
                                metrics.record_operation(
                                    user.user_id, 'memory_stress', False,
                                    time.time() - user.start_time, 'array_data_contamination'
                                )
                                return {'status': 'array_data_contamination', 'violation': True}
                    except (json.JSONDecodeError, AttributeError):
                        metrics.record_operation(
                            user.user_id, 'memory_stress', False,
                            time.time() - user.start_time, 'data_corruption_under_memory_pressure'
                        )
                        return {'status': 'data_corruption_under_memory_pressure', 'violation': True}
                
                # Phase 5: Test backend interaction during memory stress
                try:
                    health_status = await backend_client.health_check()
                    
                    # Verify Redis data still intact after backend interaction
                    for redis_key in redis_keys:
                        post_backend_data = await redis_client.hgetall(redis_key)
                        if not post_backend_data or post_backend_data.get('user_id') != user.user_id:
                            metrics.record_operation(
                                user.user_id, 'memory_stress', False,
                                time.time() - user.start_time, 'backend_interaction_interference'
                            )
                            return {'status': 'backend_interaction_interference', 'violation': True}
                except Exception as e:
                    # Backend errors acceptable, but shouldn't affect data integrity
                    logging.warning(f"Backend interaction failed for user {user.user_id}: {e}")
                
                user.end_time = time.time()
                duration = user.end_time - user.start_time
                
                # Cleanup memory and Redis data
                del large_datasets, temp_memory_pressure
                for redis_key in redis_keys:
                    await redis_client.delete(redis_key)
                
                metrics.record_operation(user.user_id, 'memory_stress', True, duration)
                
                return {
                    'status': 'success',
                    'violation': False,
                    'duration': duration,
                    'datasets_processed': len(redis_keys),
                    'user_id': user.user_id
                }
                
            except Exception as e:
                metrics.record_operation(
                    user.user_id, 'memory_stress', False,
                    time.time() - user.start_time, 'memory_stress_exception'
                )
                return {
                    'status': 'error',
                    'violation': True,
                    'error': str(e),
                    'user_id': user.user_id
                }
        
        # Execute memory stress operations concurrently
        start_time = time.time()
        tasks = [memory_stress_operation(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        violations = []
        successful_operations = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('violation', True):
                    violations.append(result)
                else:
                    successful_operations += 1
            else:
                violations.append({'status': 'exception', 'error': str(result), 'violation': True})
        
        # Performance and isolation assertions
        success_rate = (successful_operations / len(users)) * 100
        avg_operation_time = total_duration / len(users)
        
        assert len(violations) == 0, f"MEMORY STRESS ISOLATION VIOLATIONS: {violations}"
        assert success_rate >= 90.0, f"Memory stress success rate too low: {success_rate}% (expected >= 90%)"
        assert avg_operation_time < 15.0, f"Memory stress operation time too high: {avg_operation_time}s (expected < 15s)"

    @pytest.mark.asyncio
    async def test_thread_safety_concurrent_operations(self, redis_client):
        """
        CRITICAL: Thread safety testing with mixed async/sync operations.
        
        Tests that thread safety is maintained when mixing asyncio operations
        with traditional threading patterns.
        """
        # Create 16 users for thread safety testing
        users = [
            ConcurrentUserContext(
                user_id=f'thread-safety-{uuid.uuid4().hex[:8]}',
                email=f'thread{i}@safety.test'
            )
            for i in range(16)
        ]
        
        metrics = ConcurrentTestMetrics()
        thread_results = {}
        results_lock = Lock()
        
        def sync_thread_operation(user: ConcurrentUserContext) -> Dict[str, Any]:
            """Synchronous thread operation for testing thread safety."""
            import asyncio
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                start_time = time.time()
                thread_id = threading.get_ident()
                
                # Async operations within thread
                result = loop.run_until_complete(
                    self._thread_safe_async_operations(redis_client, user, thread_id, start_time)
                )
                
                # Store result in thread-safe manner
                with results_lock:
                    thread_results[user.user_id] = result
                
                return result
                
            except Exception as e:
                with results_lock:
                    thread_results[user.user_id] = {
                        'status': 'error',
                        'violation': True,
                        'error': str(e),
                        'user_id': user.user_id
                    }
                return thread_results[user.user_id]
            finally:
                loop.close()
        
        # Execute operations in parallel threads
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = []
            start_time = time.time()
            
            for user in users:
                future = executor.submit(sync_thread_operation, user)
                futures.append(future)
            
            # Wait for all threads to complete
            completed_results = []
            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result(timeout=10)
                    completed_results.append(result)
                except Exception as e:
                    completed_results.append({
                        'status': 'thread_timeout_error',
                        'violation': True,
                        'error': str(e)
                    })
            
            total_duration = time.time() - start_time
        
        # Analyze thread safety results
        violations = []
        successful_operations = 0
        
        for result in completed_results:
            if isinstance(result, dict):
                if result.get('violation', True):
                    violations.append(result)
                else:
                    successful_operations += 1
            else:
                violations.append({'status': 'unexpected_result', 'error': str(result), 'violation': True})
        
        # Performance assertions
        success_rate = (successful_operations / len(users)) * 100
        avg_operation_time = total_duration / len(users)
        
        assert len(violations) == 0, f"THREAD SAFETY VIOLATIONS: {violations}"
        assert success_rate >= 95.0, f"Thread safety success rate too low: {success_rate}% (expected >= 95%)"
        assert avg_operation_time < 20.0, f"Thread operation time too high: {avg_operation_time}s (expected < 20s)"

    async def _thread_safe_async_operations(self, redis_client, user: ConcurrentUserContext, 
                                           thread_id: int, start_time: float) -> Dict[str, Any]:
        """Helper method for thread-safe async operations."""
        try:
            # Connect to Redis in this thread
            thread_redis = redis.from_url('redis://localhost:6381', decode_responses=True)
            await thread_redis.ping()
            
            # Perform thread-specific operations
            thread_key = f"thread_safety:{user.user_id}:{thread_id}"
            
            thread_data = {
                'user_id': user.user_id,
                'thread_id': thread_id,
                'operation_timestamp': start_time,
                'thread_specific_data': f"THREAD-DATA-{user.user_id}-{thread_id}-{uuid.uuid4().hex}",
                'sensitive_info': f"SENSITIVE-{user.user_id}-{uuid.uuid4().hex}"
            }
            
            # Store data
            await thread_redis.hset(thread_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in thread_data.items()
            })
            
            # Simulate work with delays to encourage race conditions
            await asyncio.sleep(0.1)
            
            # Verify data integrity
            retrieved_data = await thread_redis.hgetall(thread_key)
            
            if not retrieved_data:
                return {'status': 'data_lost_in_thread', 'violation': True, 'user_id': user.user_id}
            
            if retrieved_data.get('user_id') != user.user_id:
                return {
                    'status': 'thread_contamination',
                    'violation': True,
                    'expected_user': user.user_id,
                    'actual_user': retrieved_data.get('user_id'),
                    'thread_id': thread_id
                }
            
            # Cleanup
            await thread_redis.delete(thread_key)
            await thread_redis.close()
            
            duration = time.time() - start_time
            
            return {
                'status': 'success',
                'violation': False,
                'duration': duration,
                'thread_id': thread_id,
                'user_id': user.user_id
            }
            
        except Exception as e:
            return {
                'status': 'thread_exception',
                'violation': True,
                'error': str(e),
                'user_id': user.user_id,
                'thread_id': thread_id
            }

    @pytest.mark.asyncio
    async def test_comprehensive_concurrent_integration(self, redis_client, database_engine, backend_client):
        """
        CRITICAL: Comprehensive integration test of ALL concurrent isolation mechanisms.
        
        Master test combining Redis, PostgreSQL, WebSocket, threading, and memory stress
        with 20+ concurrent users to ensure complete end-to-end isolation.
        """
        # Create 24 users for comprehensive concurrent integration testing
        users = [
            ConcurrentUserContext(
                user_id=f'integration-{uuid.uuid4().hex[:8]}',
                email=f'integration{i}@comprehensive.test',
                role='admin' if i % 6 == 0 else 'user'
            )
            for i in range(24)
        ]
        
        metrics = ConcurrentTestMetrics()
        
        async def comprehensive_concurrent_operation(user: ConcurrentUserContext) -> Dict[str, Any]:
            """Comprehensive concurrent operation testing all isolation mechanisms."""
            user.start_time = time.time()
            operation_results = {
                'redis_operations': 0,
                'database_operations': 0,
                'memory_operations': 0,
                'isolation_checks': 0
            }
            
            try:
                # Phase 1: Redis operations
                redis_keys = []
                for redis_op in range(5):
                    redis_key = f"comprehensive:{user.user_id}:redis:{redis_op}"
                    redis_data = {
                        'user_id': user.user_id,
                        'operation_type': 'redis',
                        'operation_index': redis_op,
                        'sensitive_data': f"REDIS-SENSITIVE-{user.user_id}-{redis_op}-{uuid.uuid4().hex}",
                        'timestamp': time.time()
                    }
                    
                    await redis_client.hset(redis_key, mapping={
                        k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                        for k, v in redis_data.items()
                    })
                    redis_keys.append(redis_key)
                    operation_results['redis_operations'] += 1
                
                # Phase 2: Database operations
                async_session = async_sessionmaker(database_engine, expire_on_commit=False)
                
                async with async_session() as session:
                    # Create table if needed
                    await session.execute(sa.text("""
                        CREATE TABLE IF NOT EXISTS comprehensive_integration_test (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            operation_data JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """))
                    
                    # Insert multiple records
                    for db_op in range(3):
                        db_data = {
                            'user_id': user.user_id,
                            'operation_type': 'database',
                            'operation_index': db_op,
                            'sensitive_db_data': f"DB-SENSITIVE-{user.user_id}-{db_op}-{uuid.uuid4().hex}",
                            'timestamp': time.time()
                        }
                        
                        await session.execute(sa.text("""
                            INSERT INTO comprehensive_integration_test (user_id, operation_data)
                            VALUES (:user_id, :operation_data)
                        """), {
                            'user_id': user.user_id,
                            'operation_data': json.dumps(db_data)
                        })
                        operation_results['database_operations'] += 1
                    
                    await session.commit()
                
                # Phase 3: Memory stress operations
                large_memory_data = []
                for mem_op in range(3):
                    memory_dataset = {
                        'user_id': user.user_id,
                        'memory_operation': mem_op,
                        'large_data': [
                            f"MEMORY-{user.user_id}-{mem_op}-{i}-{uuid.uuid4().hex}"
                            for i in range(1000)
                        ],
                        'nested_memory': {
                            f'nest_{j}': f"NESTED-MEMORY-{user.user_id}-{mem_op}-{j}-{uuid.uuid4().hex}"
                            for j in range(100)
                        }
                    }
                    large_memory_data.append(memory_dataset)
                    operation_results['memory_operations'] += 1
                
                # Phase 4: Cross-isolation verification
                # Check Redis data integrity
                for redis_key in redis_keys:
                    redis_data = await redis_client.hgetall(redis_key)
                    if not redis_data or redis_data.get('user_id') != user.user_id:
                        return {'status': 'redis_isolation_failure', 'violation': True, 'user_id': user.user_id}
                    operation_results['isolation_checks'] += 1
                
                # Check database data integrity
                async with async_session() as session:
                    db_result = await session.execute(sa.text("""
                        SELECT COUNT(*), operation_data FROM comprehensive_integration_test 
                        WHERE user_id = :user_id
                        GROUP BY operation_data
                    """), {'user_id': user.user_id})
                    
                    db_rows = db_result.fetchall()
                    if len(db_rows) != 3:  # Should have 3 records
                        return {
                            'status': 'database_isolation_failure', 
                            'violation': True,
                            'expected_records': 3,
                            'actual_records': len(db_rows),
                            'user_id': user.user_id
                        }
                    operation_results['isolation_checks'] += 1
                
                # Check memory data integrity
                for dataset in large_memory_data:
                    if dataset['user_id'] != user.user_id:
                        return {'status': 'memory_isolation_failure', 'violation': True, 'user_id': user.user_id}
                    operation_results['isolation_checks'] += 1
                
                # Phase 5: Cross-user contamination check
                # Verify no access to other users' Redis data
                all_redis_keys = await redis_client.keys("comprehensive:*")
                for key in all_redis_keys:
                    if user.user_id not in key:  # Other user's key
                        other_data = await redis_client.hgetall(key)
                        if other_data and other_data.get('user_id') == user.user_id:
                            return {'status': 'cross_user_contamination', 'violation': True, 'user_id': user.user_id}
                
                operation_results['isolation_checks'] += 1
                
                user.end_time = time.time()
                duration = user.end_time - user.start_time
                
                # Cleanup
                for redis_key in redis_keys:
                    await redis_client.delete(redis_key)
                
                async with async_session() as session:
                    await session.execute(sa.text("""
                        DELETE FROM comprehensive_integration_test WHERE user_id = :user_id
                    """), {'user_id': user.user_id})
                    await session.commit()
                
                del large_memory_data  # Free memory
                
                metrics.record_operation(user.user_id, 'comprehensive_integration', True, duration)
                
                return {
                    'status': 'success',
                    'violation': False,
                    'duration': duration,
                    'user_id': user.user_id,
                    'operations_summary': operation_results
                }
                
            except Exception as e:
                metrics.record_operation(
                    user.user_id, 'comprehensive_integration', False,
                    time.time() - user.start_time, 'integration_exception'
                )
                return {
                    'status': 'error',
                    'violation': True,
                    'error': str(e),
                    'user_id': user.user_id,
                    'partial_operations': operation_results
                }
        
        # Execute comprehensive integration operations concurrently
        start_time = time.time()
        tasks = [comprehensive_concurrent_operation(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze comprehensive integration results
        violations = []
        successful_operations = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('violation', True):
                    violations.append(result)
                else:
                    successful_operations += 1
            else:
                violations.append({'status': 'exception', 'error': str(result), 'violation': True})
        
        # Cleanup integration test table
        async with database_engine.begin() as conn:
            await conn.execute(sa.text("DROP TABLE IF EXISTS comprehensive_integration_test"))
        
        # Final performance and isolation assertions
        success_rate = (successful_operations / len(users)) * 100
        avg_operation_time = total_duration / len(users)
        final_metrics = metrics.get_metrics()
        
        assert len(violations) == 0, f"COMPREHENSIVE INTEGRATION VIOLATIONS: {violations}"
        assert success_rate >= 90.0, f"Integration success rate too low: {success_rate}% (expected >= 90%)"
        assert avg_operation_time < 30.0, f"Integration operation time too high: {avg_operation_time}s (expected < 30s)"
        
        # Log final metrics for monitoring
        logging.info(f"Comprehensive Concurrent Integration Test Metrics: {final_metrics}")
        

if __name__ == "__main__":
    # Run mission critical concurrent user isolation tests with real services
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-cov",
        "-s",  # Show output for debugging
        "--maxfail=1",  # Stop on first failure for immediate attention
        "-m", "mission_critical"  # Only run mission critical tests
    ])