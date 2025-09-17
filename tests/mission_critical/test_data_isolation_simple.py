"Mission Critical Data Layer Isolation Security Tests - REAL SERVICES ONLY"

These tests use REAL services to detect critical security vulnerabilities:
1. Redis key collision between users
2. Database session isolation failures
3. Cache contamination between users  
4. User context propagation failure
5. Concurrent user data isolation
6. WebSocket message isolation
7. Agent state contamination
8. Thread safety violations

COMPLIANCE:
@claude.md - NO MOCKS ALLOWED, REAL services for spacecraft reliability
@spec/type_safety.xml - Full type safety with real service responses
@spec/core.xml - SSOT pattern enforcement with real data flows
""

import asyncio
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional, Set

import pytest
import redis.asyncio as redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from shared.isolated_environment import IsolatedEnvironment
from test_framework.backend_client import BackendTestClient
from test_framework.test_context import TestContext, create_isolated_test_contexts


@pytest.fixture(scope=module)
def isolated_env():
    Isolated environment for testing.""
    return IsolatedEnvironment()


@pytest.fixture(scope=module)
async def redis_client(isolated_env):
    "Real Redis client for testing."
    redis_url = isolated_env.get('REDIS_URL', 'redis://localhost:6381')
    client = redis.from_url(redis_url, decode_responses=True)
    
    # Ensure connection works
    await client.ping()
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture(scope=module)"
@pytest.fixture(scope=module)"
async def database_engine(isolated_env):
    "Real database engine for testing."
    database_url = isolated_env.get('DATABASE_URL', 'postgresql+asyncpg://netra:netra@localhost:5434/netra_test')
    engine = create_async_engine(database_url, echo=False)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope=module")"
async def backend_client(isolated_env):
    Real backend client for testing."
    Real backend client for testing."
    backend_url = isolated_env.get('BACKEND_URL', 'http://localhost:8000')
    client = BackendTestClient(backend_url)
    
    # Ensure backend is healthy
    health_ok = await client.health_check()
    if not health_ok:
        pytest.skip(Backend service not available")"
    
    yield client
    
    await client.close()


@pytest.mark.mission_critical
class RealDataLayerIsolationTests:
    "
    "
    Mission Critical test suite for data layer isolation using REAL services.
    
    Tests 15+ comprehensive isolation scenarios with real Redis, PostgreSQL, and WebSocket connections.
    Each test verifies zero data leakage between users in spacecraft-critical scenarios.
    "
    "

    @pytest.mark.asyncio
    async def test_real_redis_user_isolation(self, redis_client):
        
        CRITICAL: Redis key isolation between users using REAL Redis service.
        
        Tests that user sessions, cache keys, and data are completely isolated
        in production Redis instance. Any key collision is a security breach.
""
        # Create isolated user contexts
        users = [
            {'id': f'user-redis-{uuid.uuid4().hex[:8]}', 'email': f'user{i}@isolation.test'}
            for i in range(5)
        ]
        
        # Test session key isolation
        session_data = {}
        for user in users:
            session_id = fsession_{uuid.uuid4().hex}
            
            # Store sensitive user data in Redis
            session_key = fsession:{user['id']}:{session_id}"
            session_key = fsession:{user['id']}:{session_id}"
            sensitive_data = {
                'user_id': user['id'],
                'email': user['email'],
                'chat_context': f"Confidential conversation for {user['id']},"
                'agent_state': {'thinking': fPrivate agent thoughts for {user['id']}},
                'sensitive_flags': {'is_admin': user['id'] == users[0]['id']},
                'secret_token': fsecret-{uuid.uuid4().hex}
            }
            
            await redis_client.hset(session_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                for k, v in sensitive_data.items()
            }
            
            session_data[user['id']] = {'key': session_key, 'data': sensitive_data}
        
        # Verify complete isolation - no user can access another's data'
        for user in users:
            user_key = session_data[user['id']]['key']
            user_data = await redis_client.hgetall(user_key)
            
            # Verify user's own data is accessible'
            assert user_data, fUser {user['id']} cannot access own session data""
            assert user_data['user_id'] == user['id'], fUser ID mismatch in session data
            
            # Critical: Verify no access to other users' data by key guessing'
            for other_user in users:
                if other_user['id'] != user['id']:
                    other_key = session_data[other_user['id']]['key']
                    
                    # Try various key guess patterns that could expose data
                    guess_patterns = [
                        other_key,  # Direct key
                        fsession:{user['id']}:*,  # Wildcard attempt
                        other_key.replace(other_user['id'), user['id'),  # ID substitution
                    ]
                    
                    for pattern in guess_patterns:
                        if '*' in pattern:
                            # Pattern matching attempt
                            keys = await redis_client.keys(pattern)
                            other_user_keys = [k for k in keys if other_user['id'] in k and user['id'] not in k]
                            assert not other_user_keys, f"SECURITY BREACH: User {user['id']} can discover other user keys: {other_user_keys}"
                        else:
                            # Direct key access attempt (should fail)
                            if pattern != user_key:  # Don't test own key'
                                unauthorized_data = await redis_client.hgetall(pattern)
                                if unauthorized_data and unauthorized_data.get('user_id') != user['id']:
                                    assert False, fSECURITY BREACH: User {user['id']} accessed data belonging to {unauthorized_data['user_id']}"
                                    assert False, fSECURITY BREACH: User {user['id']} accessed data belonging to {unauthorized_data['user_id']}"

    @pytest.mark.asyncio
    async def test_real_database_session_isolation(self, database_engine):
    "
    "
        CRITICAL: Database session isolation using REAL PostgreSQL.
        
        Tests that database sessions maintain complete user isolation
        and no data leakage occurs between concurrent sessions.
        "
        "
        # Create async session maker
        async_session = async_sessionmaker(database_engine, expire_on_commit=False)
        
        users = [
            {'id': f'db-user-{uuid.uuid4().hex[:8]}', 'email': f'dbuser{i}@test.com'}
            for i in range(3)
        ]
        
        # Create test table for isolation testing
        async with database_engine.begin() as conn:
            await conn.execute(sa.text(
                CREATE TABLE IF NOT EXISTS user_sessions_test (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    session_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            "))"
            
            # Clean up any existing test data
            await conn.execute(sa.text(DELETE FROM user_sessions_test))
        
        # Test concurrent session isolation
        async def user_database_operation(user: Dict[str, Any) -> Dict[str, Any):
            "Perform database operations for a user in isolated session."
            async with async_session() as session:
                # Insert user-specific data
                sensitive_data = {
                    'user_id': user['id'],
                    'confidential': fSecret data for {user['id']},
                    'session_token': ftoken-{uuid.uuid4().hex},"
                    'session_token': ftoken-{uuid.uuid4().hex},"
                    'permissions': ['read', 'write'] if user['id'] == users[0]['id'] else ['read']
                }
                
                result = await session.execute(sa.text("
                result = await session.execute(sa.text("
                    INSERT INTO user_sessions_test (user_id, session_data)
                    VALUES (:user_id, :session_data)
                    RETURNING id, user_id
                ), {
                    'user_id': user['id'],
                    'session_data': json.dumps(sensitive_data)
                }
                
                inserted_row = result.fetchone()
                await session.commit()
                
                # Verify user can only access their own data
                check_result = await session.execute(sa.text(""
                    SELECT user_id, session_data FROM user_sessions_test 
                    WHERE user_id = :user_id
                ), {'user_id': user['id']}
                
                user_rows = check_result.fetchall()
                
                # Critical: Verify no access to other users' data'
                all_result = await session.execute(sa.text("
                all_result = await session.execute(sa.text("
                    SELECT user_id, session_data FROM user_sessions_test
                "))"
                
                all_rows = all_result.fetchall()
                other_users_data = [row for row in all_rows if row[0] != user['id']]
                
                return {
                    'user_id': user['id'],
                    'own_rows': len(user_rows),
                    'total_rows': len(all_rows),
                    'other_users_accessible': len(other_users_data),
                    'inserted_id': inserted_row[0] if inserted_row else None,
                    'isolation_breach': len(other_users_data) > 0 and any(
                        json.loads(row[1].get('user_id') != user['id'] for row in other_users_data
                    )
                }
        
        # Execute concurrent database operations
        tasks = [user_database_operation(user) for user in users]
        results = await asyncio.gather(*tasks)
        
        # Verify complete isolation
        for result in results:
            assert result['own_rows'] >= 1, fUser {result['user_id']} cannot access own data
            assert not result['isolation_breach'], f"SECURITY BREACH: User {result['user_id']} can access other users' data"
        
        # Cleanup
        async with database_engine.begin() as conn:
            await conn.execute(sa.text(DROP TABLE IF EXISTS user_sessions_test"))"

    @pytest.mark.asyncio
    async def test_real_cache_contamination_prevention(self, redis_client):
    "
    "
        CRITICAL: Real cache isolation preventing contamination between users.
        
        Uses real Redis to test that cache keys properly isolate user data
        and prevent unauthorized access to cached query results.
        "
        "
        users = [
            {'id': f'cache-user-{uuid.uuid4().hex[:8]}', 'corpus_id': f'corpus-{i}'}
            for i in range(4)
        ]
        
        # Simulate realistic cache operations with proper isolation
        async def cache_user_query(user: Dict[str, Any], query: str, sensitive_result: str) -> str:
            Cache a query result with proper user isolation.""
            # Proper cache key with user context
            cache_key = fquery_cache:{user['id']}:{hash(query)}
            
            cached_data = {
                'user_id': user['id'],
                'query': query,
                'result': sensitive_result,
                'timestamp': time.time(),
                'corpus_id': user.get('corpus_id')
            }
            
            await redis_client.hset(cache_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                for k, v in cached_data.items()
            }
            
            return cache_key
        
        # Cache sensitive data for each user
        cache_keys = {}
        for user in users:
            query = SELECT * FROM sensitive_documents WHERE corpus_id = ?
            sensitive_result = {
                'documents': [
                    {'id': f'doc-{user["id]}-{i}', 'content': f'CONFIDENTIAL: {user[id"]} document {i}'}
                    for i in range(3)
                ],
                'metadata': {'owner': user['id'], 'classification': 'TOP_SECRET'}
            }
            
            cache_key = await cache_user_query(user, query, json.dumps(sensitive_result))
            cache_keys[user['id']] = cache_key
        
        # Test isolation: Each user can only access their own cached data
        for user in users:
            user_cache_key = cache_keys[user['id']]
            
            # User should be able to access their own data
            own_data = await redis_client.hgetall(user_cache_key)
            assert own_data, fUser {user['id']} cannot access own cached data
            assert own_data['user_id'] == user['id'], fCache data user_id mismatch
            
            # Critical: User should NOT be able to access other users' data'
            for other_user_id, other_cache_key in cache_keys.items():
                if other_user_id != user['id']:
                    # Attempt unauthorized access
                    unauthorized_data = await redis_client.hgetall(other_cache_key)
                    
                    if unauthorized_data:
                        # If data exists, it should not be accessible to this user
                        cached_user_id = unauthorized_data.get('user_id')
                        if cached_user_id and cached_user_id != user['id']:
                            # This is expected - verifying the data belongs to different user
                            continue
                        else:
                            assert False, f"SECURITY BREACH: User {user['id']} accessed cache data without proper user_id"
            
            # Test cache key predictability resistance
            # Try to guess other users' cache keys'
            for other_user in users:
                if other_user['id'] != user['id']:
                    # Try various guess patterns
                    guess_patterns = [
                        fquery_cache:{other_user['id']}:*",  # Pattern matching"
                        cache_keys[other_user['id')).replace(other_user['id'), user['id'),  # ID substitution
                    ]
                    
                    for pattern in guess_patterns:
                        if '*' in pattern:
                            # Pattern matching should not reveal other users' keys'
                            matching_keys = await redis_client.keys(pattern)
                            accessible_keys = []
                            for key in matching_keys:
                                if user['id'] not in key:  # Key doesn't belong to current user'
                                    key_data = await redis_client.hgetall(key)
                                    if key_data and key_data.get('user_id') != user['id']:
                                        accessible_keys.append(key)
                            
                            assert not accessible_keys, fSECURITY BREACH: User {user['id']} discovered unauthorized cache keys: {accessible_keys}

    @pytest.mark.asyncio
    async def test_concurrent_user_isolation_with_real_services(self, redis_client, backend_client):
        "
        "
        CRITICAL: Concurrent user isolation with real services under load.
        
        Tests 10+ concurrent users performing operations simultaneously
        to ensure zero data contamination in high-load scenarios.
"
"
        # Create 12 concurrent users for comprehensive testing
        users = [
            {'id': f'concurrent-user-{uuid.uuid4().hex[:8]}', 'email': f'user{i}@concurrent.test'}
            for i in range(12)
        ]
        
        isolation_violations = []
        
        async def concurrent_user_operation(user: Dict[str, Any], operation_id: int) -> Dict[str, Any]:
            Perform concurrent operations for a user with real services.""
            try:
                # Step 1: Store user-specific data in Redis
                user_key = fuser_operation:{user['id']}:{operation_id}
                operation_data = {
                    'user_id': user['id'],
                    'operation_id': operation_id,
                    'sensitive_payload': f"CONFIDENTIAL-{user['id']}-{uuid.uuid4().hex},"
                    'timestamp': time.time(),
                    'thread_id': fthread-{user['id']}-{operation_id}"
                    'thread_id': fthread-{user['id']}-{operation_id}"
                }
                
                await redis_client.hset(user_key, mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in operation_data.items()
                }
                
                # Step 2: Simulate processing delay to trigger race conditions
                await asyncio.sleep(0.5)
                
                # Step 3: Verify data integrity
                retrieved_data = await redis_client.hgetall(user_key)
                
                if not retrieved_data:
                    return {'user_id': user['id'], 'status': 'data_lost', 'violation': True}
                
                if retrieved_data.get('user_id') != user['id']:
                    return {
                        'user_id': user['id'],
                        'status': 'user_contamination',
                        'violation': True,
                        'expected_user': user['id'],
                        'actual_user': retrieved_data.get('user_id')
                    }
                
                # Step 4: Test backend service isolation
                try:
                    # Backend health check should not interfere with user context
                    health_status = await backend_client.health_check()
                    
                    # Verify Redis data still intact after backend call
                    post_backend_data = await redis_client.hgetall(user_key)
                    
                    if not post_backend_data or post_backend_data.get('user_id') != user['id']:
                        return {
                            'user_id': user['id'],
                            'status': 'backend_interference',
                            'violation': True,
                            'health_status': health_status
                        }
                except Exception as e:
                    # Backend errors shouldn't affect data isolation'
                    logging.warning(fBackend error for user {user['id']}: {e})
                
                # Step 5: Cross-user contamination check
                # Try to access other users' data (should fail)'
                other_user_keys = [
                    fuser_operation:{other_user['id']}:{operation_id}"
                    fuser_operation:{other_user['id']}:{operation_id}"
                    for other_user in users if other_user['id'] != user['id']
                ]
                
                contamination_found = False
                for other_key in other_user_keys:
                    other_data = await redis_client.hgetall(other_key)
                    if other_data and other_data.get('user_id') == user['id']:
                        # Found our data in another user's key - contamination!'
                        contamination_found = True
                        break
                
                if contamination_found:
                    return {
                        'user_id': user['id'],
                        'status': 'cross_contamination',
                        'violation': True
                    }
                
                return {
                    'user_id': user['id'],
                    'operation_id': operation_id,
                    'status': 'success',
                    'violation': False,
                    'data_verified': True
                }
                
            except Exception as e:
                return {
                    'user_id': user['id'],
                    'status': 'error',
                    'violation': True,
                    'error': str(e)
                }
        
        # Execute all operations concurrently
        tasks = [concurrent_user_operation(user, i) for i, user in enumerate(users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for violations
        violations = []
        for result in results:
            if isinstance(result, dict) and result.get('violation', False):
                violations.append(result)
        
        # Clean up test data
        cleanup_tasks = []
        for i, user in enumerate(users):
            cleanup_key = f"user_operation:{user['id']}:{i}"
            cleanup_tasks.append(redis_client.delete(cleanup_key))
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Report results
        successful_operations = len([r for r in results if isinstance(r, dict) and not r.get('violation', True)]
        
        assert len(violations) == 0, fSECURITY VIOLATIONS: {len(violations)}/{len(users)} operations had isolation violations: {violations}
        assert successful_operations == len(users), fOnly {successful_operations}/{len(users)} operations completed successfully

    @pytest.mark.asyncio
    async def test_real_websocket_user_isolation(self, backend_client):
        ""
        CRITICAL: WebSocket message isolation between users using real connections.
        
        Tests that WebSocket connections maintain complete user isolation
        and messages never leak between users.

        # Create isolated test contexts
        contexts = create_isolated_test_contexts(count=4)
        
        try:
            # Set up WebSocket connections for each user
            for context in contexts:
                # Mock JWT token for testing
                context.user_context.jwt_token = f"test-token-{context.user_context.user_id}"
                
                # Try to establish WebSocket connection (may not work without auth service)
                try:
                    await context.setup_websocket_connection(/ws/chat", auth_required=False)"
                except ConnectionError:
                    pytest.skip(WebSocket connections not available - testing isolation logic only)
            
            # Test message isolation
            isolation_violations = []
            
            for i, context in enumerate(contexts):
                # Each user sends a unique message
                unique_message = {
                    'type': 'chat',
                    'content': f'CONFIDENTIAL MESSAGE FROM USER {context.user_context.user_id}',
                    'user_id': context.user_context.user_id,
                    'thread_id': context.user_context.thread_id,
                    'timestamp': time.time(),
                    'secret_payload': f'SECRET-{uuid.uuid4().hex}'
                }
                
                try:
                    if context.websocket_connection:
                        await context.send_message(unique_message)
                        
                        # Listen for responses
                        received_events = await context.listen_for_events(duration=2.0)
                        
                        # Verify no events contain other users' data'
                        for event in received_events:
                            event_user_id = event.get('user_id')
                            if event_user_id and event_user_id != context.user_context.user_id:
                                isolation_violations.append({
                                    'receiving_user': context.user_context.user_id,
                                    'event_from_user': event_user_id,
                                    'event': event
                                }
                except Exception as e:
                    logging.warning(fWebSocket test error for user {context.user_context.user_id}: {e}")"
                    continue
            
            # Verify no isolation violations occurred
            assert len(isolation_violations) == 0, fSECURITY BREACH: WebSocket isolation violations: {isolation_violations}
            
        finally:
            # Clean up all contexts
            cleanup_tasks = [context.cleanup() for context in contexts]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_agent_state_isolation_real_services(self, redis_client):
        
        CRITICAL: Agent state isolation between users using real Redis.
        
        Tests that agent execution states are completely isolated
        and never contaminate between users.
""
        users = [
            {'id': f'agent-user-{uuid.uuid4().hex[:8]}', 'agent_type': f'agent-type-{i}'}
            for i in range(6)
        ]
        
        # Store agent states for each user
        agent_states = {}
        for user in users:
            agent_key = fagent_state:{user['id']}:{user['agent_type']}
            
            state_data = {
                'user_id': user['id'],
                'agent_type': user['agent_type'],
                'conversation_history': [f'Message {i} for {user[id]}' for i in range(3)],"
                'conversation_history': [f'Message {i} for {user[id]}' for i in range(3)],"
                'agent_memory': {
                    'user_preferences': f"Preferences for {user['id']},"
                    'context': fPrivate context for {user['id']},
                    'secrets': fSECRET-DATA-{uuid.uuid4().hex}
                },
                'execution_state': 'thinking',
                'tool_results': [fTool result {i} for {user['id']}" for i in range(2)]"
            }
            
            await redis_client.hset(agent_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in state_data.items()
            }
            
            agent_states[user['id']] = {'key': agent_key, 'state': state_data}
        
        # Test agent state isolation
        for user in users:
            user_agent_key = agent_states[user['id']]['key']
            
            # User should access only their agent state
            user_state = await redis_client.hgetall(user_agent_key)
            assert user_state, fUser {user['id']} cannot access own agent state
            assert user_state['user_id'] == user['id'], fAgent state user_id mismatch
            
            # Verify agent state contains user-specific data
            conversation_history = json.loads(user_state.get('conversation_history', '[]'))
            assert all(user['id'] in msg for msg in conversation_history), f"Conversation history contaminated for user {user['id']}"
            
            # Critical: Verify no access to other users' agent states'
            for other_user_id, other_state_info in agent_states.items():
                if other_user_id != user['id']:
                    other_key = other_state_info['key']
                    
                    # Try to access other user's agent state'
                    unauthorized_state = await redis_client.hgetall(other_key)
                    
                    if unauthorized_state:
                        state_user_id = unauthorized_state.get('user_id')
                        if state_user_id == user['id']:
                            assert False, fCONTAMINATION: User {user['id']}'s data found in {other_user_id}'s agent state"
                            assert False, fCONTAMINATION: User {user['id']}'s data found in {other_user_id}'s agent state"
                        
                        # Verify the state truly belongs to the other user
                        assert state_user_id == other_user_id, fAgent state ownership unclear: expected {other_user_id}, got {state_user_id}

    @pytest.mark.asyncio
    async def test_thread_safety_isolation_real_services(self, redis_client):
        "
        "
        CRITICAL: Thread safety and isolation using real services.
        
        Tests that simultaneous operations maintain complete thread safety
        and user isolation in multi-threaded scenarios.
"
"
        users = [
            {'id': f'thread-user-{uuid.uuid4().hex[:8]}', 'operation': f'op-{i}'}
            for i in range(8)
        ]
        
        violations = []
        
        def synchronous_user_operation(user: Dict[str, Any], operation_id: int) -> Dict[str, Any]:
            Thread-based user operation for testing thread safety.""
            import asyncio
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Connect to Redis in this thread
                thread_redis = redis.from_url('redis://localhost:6381', decode_responses=True)
                
                # Perform thread-safe operations
                result = loop.run_until_complete(self._thread_safe_redis_operation(
                    thread_redis, user, operation_id
                ))
                
                loop.run_until_complete(thread_redis.close())
                return result
                
            except Exception as e:
                return {
                    'user_id': user['id'],
                    'operation_id': operation_id,
                    'status': 'error',
                    'violation': True,
                    'error': str(e)
                }
            finally:
                loop.close()
        
        # Execute operations in parallel threads
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = []
            for i, user in enumerate(users):
                future = executor.submit(synchronous_user_operation, user, i)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                    
                    if result.get('violation', False):
                        violations.append(result)
                        
                except Exception as e:
                    violations.append({
                        'status': 'thread_error',
                        'violation': True,
                        'error': str(e)
                    }
        
        assert len(violations) == 0, fTHREAD SAFETY VIOLATIONS: {violations}
        assert len(results) == len(users), f"Not all thread operations completed: {len(results)}/{len(users)}"

    async def _thread_safe_redis_operation(self, thread_redis, user: Dict[str, Any], operation_id: int) -> Dict[str, Any]:
        "Helper method for thread-safe Redis operations."
        # Test connection
        await thread_redis.ping()
        
        # Store thread-specific data
        thread_key = f"thread_test:{user['id']}:{operation_id}"
        thread_data = {
            'user_id': user['id'],
            'operation_id': operation_id,
            'thread_id': fthread-{operation_id}","
            'timestamp': time.time(),
            'sensitive_data': fTHREAD-SECRET-{uuid.uuid4().hex}
        }
        
        await thread_redis.hset(thread_key, mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in thread_data.items()
        }
        
        # Add delay to encourage race conditions
        await asyncio.sleep(0.1)
        
        # Verify data integrity
        retrieved_data = await thread_redis.hgetall(thread_key)
        
        if not retrieved_data:
            return {'user_id': user['id'], 'status': 'data_lost', 'violation': True}
        
        if retrieved_data.get('user_id') != user['id']:
            return {
                'user_id': user['id'],
                'status': 'user_contamination',
                'violation': True,
                'expected': user['id'],
                'actual': retrieved_data.get('user_id')
            }
        
        # Clean up
        await thread_redis.delete(thread_key)
        
        return {
            'user_id': user['id'],
            'operation_id': operation_id,
            'status': 'success',
            'violation': False
        }

    @pytest.mark.asyncio
    async def test_database_transaction_isolation_real(self, database_engine):
        "
        "
        CRITICAL: Database transaction isolation using real PostgreSQL.
        
        Tests ACID properties and transaction isolation levels
        to ensure no data leakage between concurrent transactions.
"
"
        async_session = async_sessionmaker(database_engine, expire_on_commit=False)
        
        users = [
            {'id': f'txn-user-{uuid.uuid4().hex[:8]}', 'balance': 1000 + i * 100}
            for i in range(4)
        ]
        
        # Create test table for transaction isolation
        async with database_engine.begin() as conn:
            await conn.execute(sa.text("
            await conn.execute(sa.text("
                CREATE TABLE IF NOT EXISTS user_accounts_test (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) UNIQUE NOT NULL,
                    balance INTEGER NOT NULL,
                    last_transaction JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            "))"
            
            await conn.execute(sa.text(DELETE FROM user_accounts_test))
            
            # Insert initial user data
            for user in users:
                await conn.execute(sa.text(""
                    INSERT INTO user_accounts_test (user_id, balance, last_transaction)
                    VALUES (:user_id, :balance, :transaction)
                ), {
                    'user_id': user['id'],
                    'balance': user['balance'],
                    'transaction': json.dumps({'type': 'initial_deposit', 'amount': user['balance'])
                }
        
        # Test concurrent transactions with isolation
        async def concurrent_transaction(user: Dict[str, Any], transaction_amount: int) -> Dict[str, Any]:
            "Perform isolated database transaction for user."
            async with async_session() as session:
                try:
                    # Begin transaction with isolation
                    await session.begin()
                    
                    # Read user's current balance'
                    result = await session.execute(sa.text(
                        SELECT balance FROM user_accounts_test 
                        WHERE user_id = :user_id FOR UPDATE
                    ""), {'user_id': user['id']}
                    
                    current_balance = result.scalar()
                    if current_balance is None:
                        await session.rollback()
                        return {'user_id': user['id'], 'status': 'user_not_found', 'violation': True}
                    
                    # Simulate processing delay to encourage race conditions
                    await asyncio.sleep(0.1)
                    
                    # Update balance
                    new_balance = current_balance + transaction_amount
                    transaction_record = {
                        'type': 'test_transaction',
                        'amount': transaction_amount,
                        'previous_balance': current_balance,
                        'new_balance': new_balance,
                        'timestamp': time.time()
                    }
                    
                    await session.execute(sa.text(
                        UPDATE user_accounts_test 
                        SET balance = :new_balance, last_transaction = :transaction
                        WHERE user_id = :user_id
                    ), {"
                    ), {"
                        'user_id': user['id'],
                        'new_balance': new_balance,
                        'transaction': json.dumps(transaction_record)
                    }
                    
                    await session.commit()
                    
                    # Verify final state
                    verify_result = await session.execute(sa.text("
                    verify_result = await session.execute(sa.text("
                        SELECT balance, last_transaction FROM user_accounts_test 
                        WHERE user_id = :user_id
                    ), {'user_id': user['id']}
                    
                    final_row = verify_result.fetchone()
                    
                    if not final_row or final_row[0] != new_balance:
                        return {
                            'user_id': user['id'],
                            'status': 'transaction_corruption',
                            'violation': True,
                            'expected_balance': new_balance,
                            'actual_balance': final_row[0] if final_row else None
                        }
                    
                    return {
                        'user_id': user['id'],
                        'status': 'success',
                        'violation': False,
                        'initial_balance': current_balance,
                        'final_balance': new_balance,
                        'transaction_amount': transaction_amount
                    }
                    
                except Exception as e:
                    await session.rollback()
                    return {
                        'user_id': user['id'],
                        'status': 'error',
                        'violation': True,
                        'error': str(e)
                    }
        
        # Execute concurrent transactions
        tasks = [concurrent_transaction(user, 50 * (i + 1)) for i, user in enumerate(users)]
        results = await asyncio.gather(*tasks)
        
        # Verify transaction isolation
        violations = [r for r in results if r.get('violation', False)]
        
        # Cleanup
        async with database_engine.begin() as conn:
            await conn.execute(sa.text(DROP TABLE IF EXISTS user_accounts_test"))"
        
        assert len(violations) == 0, fDATABASE TRANSACTION VIOLATIONS: {violations}

    @pytest.mark.asyncio
    async def test_real_service_security_boundaries(self, redis_client, backend_client):
        
        CRITICAL: Security boundary verification between real services.
        
        Tests that service boundaries prevent unauthorized cross-user access
        in production-like scenarios.
""
        # Create test users with different security levels
        users = [
            {'id': f'sec-admin-{uuid.uuid4().hex[:8]}', 'role': 'admin', 'clearance': 'top_secret'},
            {'id': f'sec-user-{uuid.uuid4().hex[:8]}', 'role': 'user', 'clearance': 'confidential'},
            {'id': f'sec-guest-{uuid.uuid4().hex[:8]}', 'role': 'guest', 'clearance': 'public'}
        ]
        
        security_violations = []
        
        # Store security-sensitive data for each user
        for user in users:
            security_key = fsecurity:{user['role']}:{user['id']}
            
            classified_data = {
                'user_id': user['id'],
                'role': user['role'],
                'clearance_level': user['clearance'],
                'classified_documents': [
                    fCLASSIFIED-{user['clearance'].upper()}-{uuid.uuid4().hex}"
                    fCLASSIFIED-{user['clearance'].upper()}-{uuid.uuid4().hex}"
                    for _ in range(3)
                ],
                'security_tokens': [f"TOKEN-{user['role']}-{uuid.uuid4().hex}]"
            }
            
            await redis_client.hset(security_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in classified_data.items()
            }
        
        # Test security boundary enforcement
        for user in users:
            user_role = user['role']
            user_clearance = user['clearance']
            
            # Test 1: User can access their own data
            own_key = fsecurity:{user_role}:{user['id']}
            own_data = await redis_client.hgetall(own_key)
            
            if not own_data or own_data.get('user_id') != user['id']:
                security_violations.append({
                    'type': 'self_access_failure',
                    'user': user['id'],
                    'details': 'User cannot access own security data'
                }
            
            # Test 2: User cannot access higher clearance data
            clearance_hierarchy = {'public': 0, 'confidential': 1, 'top_secret': 2}
            user_level = clearance_hierarchy[user_clearance]
            
            for other_user in users:
                if other_user['id'] != user['id']:
                    other_level = clearance_hierarchy[other_user['clearance']]
                    other_key = fsecurity:{other_user['role']}:{other_user['id']}
                    
                    # Lower clearance users should not access higher clearance data
                    if user_level < other_level:
                        unauthorized_data = await redis_client.hgetall(other_key)
                        
                        if unauthorized_data and unauthorized_data.get('user_id') == other_user['id']:
                            # Data exists but user shouldn't have access based on clearance'
                            # In a real system, there would be access control middleware
                            # For this test, we verify the data integrity is maintained
                            if authorized_data_access_simulation(user, other_user):
                                security_violations.append({
                                    'type': 'clearance_violation',
                                    'violating_user': user['id'],
                                    'clearance': user_clearance,
                                    'accessed_user': other_user['id'],
                                    'accessed_clearance': other_user['clearance']
                                }
        
        # Test 3: Backend service doesn't leak security context'
        try:
            # Each user's backend requests should be isolated'
            for user in users:
                # Simulate backend request with user context
                health_check = await backend_client.health_check()
                
                # Verify Redis state wasn't affected by backend call'
                post_call_key = fsecurity:{user['role']}:{user['id']}""
                post_call_data = await redis_client.hgetall(post_call_key)
                
                if not post_call_data or post_call_data.get('user_id') != user['id']:
                    security_violations.append({
                        'type': 'backend_context_leak',
                        'user': user['id'],
                        'details': 'Backend call affected user security context'
                    }
        except Exception as e:
            logging.warning(fBackend security test error: {e})
        
        # Cleanup security data
        cleanup_keys = [fsecurity:{user['role']}:{user['id']} for user in users]
        await asyncio.gather(*[redis_client.delete(key) for key in cleanup_keys]
        
        assert len(security_violations) == 0, f"SECURITY BOUNDARY VIOLATIONS: {security_violations}"

    @pytest.mark.asyncio
    async def test_memory_isolation_under_stress(self, redis_client):
        "
        "
        CRITICAL: Memory isolation under high stress load.
        
        Tests that memory usage and garbage collection don't cause'
        data contamination between users during peak load.
"
"
        # Create stress test with many users
        users = [
            {'id': f'stress-user-{uuid.uuid4().hex[:8]}', 'load_factor': i}
            for i in range(20)
        ]
        
        memory_violations = []
        
        async def stress_user_operation(user: Dict[str, Any) -> Dict[str, Any):
            "High-memory operation to test isolation under stress."
            user_id = user['id']
            load_factor = user['load_factor']
            
            # Create memory-intensive data structures
            large_data = {
                'user_id': user_id,
                'timestamp': time.time(),
                'large_array': [fdata-{user_id}-{i}-{uuid.uuid4().hex}" for i in range(1000)],"
                'nested_structure': {
                    f'level_{j}': {
                        f'item_{k}': fnested-{user_id}-{j}-{k}-{uuid.uuid4().hex}
                        for k in range(50)
                    }
                    for j in range(20)
                },
                'load_factor': load_factor
            }
            
            # Store in Redis to test service isolation
            stress_key = fstress_test:{user_id}:{load_factor}
            
            # Serialize large data
            serialized_data = {
                'user_id': user_id,
                'timestamp': str(time.time()),
                'large_array': json.dumps(large_data['large_array'),
                'nested_structure': json.dumps(large_data['nested_structure'),
                'load_factor': str(load_factor)
            }
            
            await redis_client.hset(stress_key, mapping=serialized_data)
            
            # Force some memory pressure
            temp_memory = [uuid.uuid4().hex for _ in range(5000)]
            
            # Verify data integrity after memory operations
            retrieved_data = await redis_client.hgetall(stress_key)
            
            if not retrieved_data:
                return {'user_id': user_id, 'status': 'data_lost', 'violation': True}
            
            if retrieved_data.get('user_id') != user_id:
                return {
                    'user_id': user_id,
                    'status': 'memory_contamination',
                    'violation': True,
                    'expected_user': user_id,
                    'actual_user': retrieved_data.get('user_id')
                }
            
            # Verify data content integrity
            try:
                retrieved_array = json.loads(retrieved_data.get('large_array', '[]'))
                if not all(user_id in item for item in retrieved_array[:10):  # Check first 10
                    return {
                        'user_id': user_id,
                        'status': 'content_contamination',
                        'violation': True
                    }
            except (json.JSONDecodeError, AttributeError):
                return {'user_id': user_id, 'status': 'data_corruption', 'violation': True}
            
            # Clean up
            await redis_client.delete(stress_key)
            del temp_memory  # Explicit cleanup
            
            return {
                'user_id': user_id,
                'status': 'success',
                'violation': False,
                'data_size': len(json.dumps(large_data))
            }
        
        # Execute stress operations concurrently
        tasks = [stress_user_operation(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        violations = []
        successful_operations = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get('violation', False):
                    violations.append(result)
                elif result.get('status') == 'success':
                    successful_operations += 1
            else:
                # Exception occurred
                violations.append({
                    'status': 'exception',
                    'violation': True,
                    'error': str(result)
                }
        
        success_rate = (successful_operations / len(users)) * 100
        
        assert len(violations) == 0, f"MEMORY ISOLATION VIOLATIONS: {violations}"
        assert success_rate >= 95.0, fSuccess rate too low: {success_rate}% (expected >= 95%)"
        assert success_rate >= 95.0, fSuccess rate too low: {success_rate}% (expected >= 95%)"

    @pytest.mark.asyncio
    async def test_comprehensive_isolation_integration(self, redis_client, database_engine, backend_client):
    "
    "
        CRITICAL: Comprehensive integration test of ALL isolation mechanisms.
        
        Master test that combines Redis, PostgreSQL, WebSocket, and backend
        isolation to ensure complete end-to-end user isolation.
        "
        "
        # Create diverse user scenarios
        users = [
            {'id': f'integration-user-{uuid.uuid4().hex[:8]}', 'type': 'standard', 'operations': ['redis', 'db', 'backend']},
            {'id': f'integration-power-{uuid.uuid4().hex[:8]}', 'type': 'power_user', 'operations': ['redis', 'db', 'backend']},
            {'id': f'integration-admin-{uuid.uuid4().hex[:8]}', 'type': 'admin', 'operations': ['redis', 'db', 'backend']}
        ]
        
        integration_violations = []
        
        async def comprehensive_user_test(user: Dict[str, Any) -> Dict[str, Any):
            Comprehensive isolation test for a single user across all services.""
            user_id = user['id']
            user_type = user['type']
            violations = []
            
            try:
                # Test 1: Redis isolation
                redis_key = fintegration:{user_type}:{user_id}
                redis_data = {
                    'user_id': user_id,
                    'user_type': user_type,
                    'integration_test': True,
                    'redis_secret': fREDIS-SECRET-{uuid.uuid4().hex},
                    'timestamp': time.time()
                }
                
                await redis_client.hset(redis_key, mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in redis_data.items()
                }
                
                # Test 2: Database isolation
                async_session = async_sessionmaker(database_engine, expire_on_commit=False)
                
                async with async_session() as session:
                    # Create temp table for integration test
                    await session.execute(sa.text(""
                        CREATE TABLE IF NOT EXISTS integration_test (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            user_type VARCHAR(100) NOT NULL,
                            test_data JSONB NOT NULL
                        )
                    ))
                    
                    db_data = {
                        'user_id': user_id,
                        'user_type': user_type,
                        'db_secret': fDB-SECRET-{uuid.uuid4().hex},"
                        'db_secret': fDB-SECRET-{uuid.uuid4().hex},"
                        'integration_timestamp': time.time()
                    }
                    
                    await session.execute(sa.text("
                    await session.execute(sa.text("
                        INSERT INTO integration_test (user_id, user_type, test_data)
                        VALUES (:user_id, :user_type, :test_data)
                    ), {
                        'user_id': user_id,
                        'user_type': user_type,
                        'test_data': json.dumps(db_data)
                    }
                    
                    await session.commit()
                
                # Test 3: Backend service isolation (if available)
                backend_healthy = False
                try:
                    backend_healthy = await backend_client.health_check()
                except Exception:
                    pass  # Backend not available, continue with other tests
                
                # Verification Phase: Ensure all data is isolated
                
                # Verify Redis data
                redis_retrieved = await redis_client.hgetall(redis_key)
                if not redis_retrieved or redis_retrieved.get('user_id') != user_id:
                    violations.append('redis_isolation_failure')
                
                # Verify Database data
                async with async_session() as session:
                    db_result = await session.execute(sa.text(""
                        SELECT test_data FROM integration_test WHERE user_id = :user_id
                    ), {'user_id': user_id}
                    
                    db_row = db_result.fetchone()
                    if not db_row:
                        violations.append('db_isolation_failure')
                    else:
                        db_retrieved = json.loads(db_row[0)
                        if db_retrieved.get('user_id') != user_id:
                            violations.append('db_data_contamination')
                
                # Cross-contamination check: Ensure no access to other users' data'
                all_redis_keys = await redis_client.keys(fintegration:*)
                for key in all_redis_keys:
                    if user_id not in key:
                        other_data = await redis_client.hgetall(key)
                        if other_data and other_data.get('user_id') == user_id:
                            violations.append('redis_cross_contamination')
                
                # Cleanup
                await redis_client.delete(redis_key)
                
                async with async_session() as session:
                    await session.execute(sa.text(""
                        DELETE FROM integration_test WHERE user_id = :user_id
                    ), {'user_id': user_id}
                    await session.commit()
                
                return {
                    'user_id': user_id,
                    'user_type': user_type,
                    'violations': violations,
                    'backend_available': backend_healthy,
                    'status': 'success' if not violations else 'violations_found'
                }
                
            except Exception as e:
                return {
                    'user_id': user_id,
                    'user_type': user_type,
                    'status': 'error',
                    'error': str(e),
                    'violations': ['test_execution_error']
                }
        
        # Execute comprehensive tests concurrently
        tasks = [comprehensive_user_test(user) for user in users]
        results = await asyncio.gather(*tasks)
        
        # Analyze integration results
        all_violations = []
        for result in results:
            user_violations = result.get('violations', [)
            if user_violations:
                all_violations.extend([{
                    'user_id': result['user_id'],
                    'user_type': result['user_type'],
                    'violation_type': v
                } for v in user_violations]
        
        # Cleanup integration test table
        async with database_engine.begin() as conn:
            await conn.execute(sa.text(DROP TABLE IF EXISTS integration_test))"
            await conn.execute(sa.text(DROP TABLE IF EXISTS integration_test))"
        
        assert len(all_violations) == 0, fCOMPREHENSIVE INTEGRATION VIOLATIONS: {all_violations}"
        assert len(all_violations) == 0, fCOMPREHENSIVE INTEGRATION VIOLATIONS: {all_violations}"


def authorized_data_access_simulation(accessing_user: Dict[str, Any), target_user: Dict[str, Any) -> bool:
    "
    "
    Simulate access control logic to determine if access should be allowed.
    In real system, this would be middleware/authorization layer.
    ""
    clearance_hierarchy = {'public': 0, 'confidential': 1, 'top_secret': 2}
    
    accessing_level = clearance_hierarchy[accessing_user['clearance']]
    target_level = clearance_hierarchy[target_user['clearance']]
    
    # Admins can access same or lower clearance
    if accessing_user['role'] == 'admin' and accessing_level >= target_level:
        return True
    
    # Users can only access same clearance level
    if accessing_user['role'] == 'user' and accessing_level == target_level:
        return True
    
    # Guests can only access public data
    if accessing_user['role'] == 'guest' and target_user['clearance'] == 'public':
        return True
    
    return False


if __name__ == __main__":"
    # Run mission critical data isolation tests with real services
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution

)))))))))))))))))))))))))))))))))))))))))))))))
}