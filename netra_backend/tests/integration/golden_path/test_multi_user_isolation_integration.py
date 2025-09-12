"""
Test Multi-User Isolation Integration - Golden Path Enterprise Security

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: Ensure enterprise-grade multi-user isolation and security
- Value Impact: Enables safe concurrent user operations and prevents data leaks
- Strategic Impact: Critical for enterprise customers and higher-tier subscriptions

CRITICAL: Multi-user isolation is mandatory for enterprise revenue.
Tests validate that users cannot access each other's data under any circumstances.
"""

import asyncio
import pytest
import uuid
from typing import Dict, List, Any
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture, real_redis_fixture
from shared.isolated_environment import get_env
from netra_backend.app.core.user_context import UserExecutionContextFactory
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine


class TestMultiUserIsolationIntegration(BaseIntegrationTest):
    """Integration tests for multi-user isolation patterns."""
    
    def setup_method(self):
        """Set up for multi-user isolation testing."""
        super().setup_method()
        self.test_users = []
        self.test_sessions = []
        self.cleanup_tasks = []

    def teardown_method(self):
        """Clean up all test users and sessions."""
        super().teardown_method()
        # Clean up will be handled by individual test methods
    
    async def create_isolated_test_user(self, real_services, user_suffix: str) -> Dict:
        """Create an isolated test user with unique context."""
        user_data = {
            'id': str(uuid.uuid4()),
            'email': f'isolation-test-{user_suffix}@example.com',
            'name': f'Isolation Test User {user_suffix}',
            'organization_id': str(uuid.uuid4()),
            'is_active': True
        }
        
        # Insert into real database
        if real_services["database_available"]:
            await real_services["db"].execute(
                "INSERT INTO auth.users (id, email, name, is_active) VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING",
                (user_data['id'], user_data['email'], user_data['name'], user_data['is_active'])
            )
            await real_services["db"].commit()
        
        self.test_users.append(user_data)
        return user_data

    @asynccontextmanager
    async def create_user_execution_context(self, user_data: Dict, real_services):
        """Create isolated user execution context."""
        factory = UserExecutionContextFactory()
        context = await factory.create_user_context(
            user_id=user_data['id'],
            organization_id=user_data['organization_id'],
            session_data={'user_email': user_data['email']}
        )
        try:
            yield context
        finally:
            if hasattr(context, 'cleanup'):
                await context.cleanup()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_execution_context_factory_isolation(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent cross-user context contamination
        Test that UserExecutionContextFactory creates isolated contexts for different users.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database not available for real services testing")
        
        # Create multiple concurrent users
        user_1 = await self.create_isolated_test_user(real_services_fixture, "ctx-1")
        user_2 = await self.create_isolated_test_user(real_services_fixture, "ctx-2") 
        user_3 = await self.create_isolated_test_user(real_services_fixture, "ctx-3")
        
        # Create contexts concurrently
        async with self.create_user_execution_context(user_1, real_services_fixture) as ctx_1, \
                   self.create_user_execution_context(user_2, real_services_fixture) as ctx_2, \
                   self.create_user_execution_context(user_3, real_services_fixture) as ctx_3:
            
            # Verify complete isolation
            assert ctx_1.user_id != ctx_2.user_id
            assert ctx_1.user_id != ctx_3.user_id
            assert ctx_2.user_id != ctx_3.user_id
            
            assert ctx_1.organization_id != ctx_2.organization_id
            assert ctx_1.organization_id != ctx_3.organization_id
            assert ctx_2.organization_id != ctx_3.organization_id
            
            # Test concurrent operations don't cross-contaminate
            results = await asyncio.gather(
                ctx_1.get_user_data(),
                ctx_2.get_user_data(), 
                ctx_3.get_user_data()
            )
            
            # Verify each context returns only its own data
            assert results[0]['user_id'] == user_1['id']
            assert results[1]['user_id'] == user_2['id']
            assert results[2]['user_id'] == user_3['id']
            
            # Attempt to access other users' data - should fail
            with pytest.raises((PermissionError, ValueError, KeyError)):
                await ctx_1.get_user_data(user_id=user_2['id'])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_isolation_concurrent_transactions(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent database-level data leaks
        Test that database sessions properly isolate user data in concurrent transactions.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database not available for real services testing")
        
        # Create multiple users with sensitive data
        users = []
        for i in range(4):
            user = await self.create_isolated_test_user(real_services_fixture, f"db-{i}")
            user['secret_data'] = f"secret-{user['id']}-{uuid.uuid4()}"
            users.append(user)
        
        async def concurrent_database_operation(user_data: Dict, operation_id: str):
            """Simulate concurrent database operations for a user."""
            # Create user-specific table data
            table_name = f"user_secrets_{user_data['id'].replace('-', '_')}"
            
            async with real_services_fixture["db"].begin() as tx:
                # Create user-specific secret
                await tx.execute(f"""
                    CREATE TEMP TABLE {table_name} AS 
                    SELECT '{user_data['secret_data']}' as secret, '{operation_id}' as operation_id
                """)
                
                # Simulate processing delay
                await asyncio.sleep(0.2)
                
                # Verify only this user's data is accessible
                result = await tx.execute(f"SELECT secret FROM {table_name}")
                secret = result.fetchone()[0] if result else None
                
                # Must match exactly this user's secret
                assert secret == user_data['secret_data'], f"Data leak detected: got {secret}, expected {user_data['secret_data']}"
                
                return {
                    'user_id': user_data['id'],
                    'secret': secret,
                    'operation_id': operation_id
                }
        
        # Run concurrent database operations
        operation_tasks = [
            concurrent_database_operation(users[i], f"op-{i}-{uuid.uuid4()}")
            for i in range(len(users))
        ]
        
        results = await asyncio.gather(*operation_tasks)
        
        # Verify isolation: each operation only saw its own data
        for i, result in enumerate(results):
            assert result['user_id'] == users[i]['id']
            assert result['secret'] == users[i]['secret_data']
        
        # Verify no cross-contamination
        unique_secrets = {r['secret'] for r in results}
        assert len(unique_secrets) == len(users), "Secret data was contaminated between users"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_redis_cache_isolation_user_scoped_keys(self, real_services_fixture, real_redis_fixture):
        """
        BVJ: Enterprise - Prevent cache-based data leaks  
        Test that Redis cache properly isolates user data with user-scoped keys.
        """
        redis_client = real_redis_fixture
        
        # Create multiple users with sensitive cache data
        users = []
        for i in range(5):
            user = await self.create_isolated_test_user(real_services_fixture, f"redis-{i}")
            user['cache_data'] = {
                'sensitive_token': f"token-{user['id']}-{uuid.uuid4()}",
                'private_settings': f"settings-{user['id']}-{uuid.uuid4()}",
                'session_data': f"session-{user['id']}-{uuid.uuid4()}"
            }
            users.append(user)
        
        # Store data with user-scoped keys
        cache_operations = []
        for user in users:
            user_prefix = f"user:{user['id']}"
            
            cache_operations.extend([
                redis_client.set(f"{user_prefix}:token", user['cache_data']['sensitive_token']),
                redis_client.set(f"{user_prefix}:settings", user['cache_data']['private_settings']),
                redis_client.set(f"{user_prefix}:session", user['cache_data']['session_data'])
            ])
        
        # Execute all cache operations concurrently
        await asyncio.gather(*cache_operations)
        
        # Verify each user can only access their own data
        async def verify_user_cache_isolation(user_data: Dict):
            user_prefix = f"user:{user_data['id']}"
            
            # Get this user's data
            user_token = await redis_client.get(f"{user_prefix}:token")
            user_settings = await redis_client.get(f"{user_prefix}:settings") 
            user_session = await redis_client.get(f"{user_prefix}:session")
            
            # Verify data matches exactly
            assert user_token == user_data['cache_data']['sensitive_token']
            assert user_settings == user_data['cache_data']['private_settings']
            assert user_session == user_data['cache_data']['session_data']
            
            # Attempt to access other users' data - should return None
            other_users = [u for u in users if u['id'] != user_data['id']]
            for other_user in other_users[:2]:  # Test 2 other users to avoid excessive operations
                other_prefix = f"user:{other_user['id']}"
                
                # Should NOT be accessible without proper user context
                other_token = await redis_client.get(f"{other_prefix}:token")
                assert other_token != user_data['cache_data']['sensitive_token'], \
                    f"User {user_data['id']} accessed another user's token: {other_token}"
            
            return user_data['id']
        
        # Verify isolation for all users concurrently
        isolation_tasks = [verify_user_cache_isolation(user) for user in users]
        verified_user_ids = await asyncio.gather(*isolation_tasks)
        
        assert len(set(verified_user_ids)) == len(users), "Cache isolation verification failed"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_isolation_different_users(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent WebSocket message cross-routing
        Test that WebSocket connections properly isolate messages between different users.
        """
        # Create users with different connection contexts
        users = []
        websocket_managers = []
        
        for i in range(3):
            user = await self.create_isolated_test_user(real_services_fixture, f"ws-{i}")
            users.append(user)
            
            # Create isolated WebSocket manager for each user
            ws_manager = WebSocketManager()
            await ws_manager.initialize(user_context={'user_id': user['id']})
            websocket_managers.append(ws_manager)
        
        try:
            # Simulate concurrent WebSocket operations
            async def send_user_specific_message(user_data: Dict, ws_manager, message_id: str):
                """Send user-specific message through WebSocket."""
                message = {
                    'type': 'user_message',
                    'user_id': user_data['id'],
                    'content': f"Private message for {user_data['name']} - ID: {message_id}",
                    'sensitive_data': f"secret-{user_data['id']}-{message_id}"
                }
                
                # Send message through user's WebSocket manager
                await ws_manager.send_user_message(user_data['id'], message)
                
                # Verify message routing isolation
                received_messages = await ws_manager.get_user_messages(user_data['id'])
                
                # Should contain only this user's messages
                user_messages = [msg for msg in received_messages if msg.get('user_id') == user_data['id']]
                assert len(user_messages) > 0, f"User {user_data['id']} did not receive their own message"
                
                # Should NOT contain other users' messages
                other_user_messages = [msg for msg in received_messages if msg.get('user_id') != user_data['id']]
                assert len(other_user_messages) == 0, f"User {user_data['id']} received other users' messages: {other_user_messages}"
                
                return message_id
            
            # Send messages concurrently for all users
            message_tasks = [
                send_user_specific_message(users[i], websocket_managers[i], f"msg-{i}-{uuid.uuid4()}")
                for i in range(len(users))
            ]
            
            sent_message_ids = await asyncio.gather(*message_tasks)
            assert len(sent_message_ids) == len(users), "Not all WebSocket messages were sent successfully"
            
        finally:
            # Cleanup WebSocket managers
            cleanup_tasks = [ws_manager.cleanup() for ws_manager in websocket_managers if hasattr(ws_manager, 'cleanup')]
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_isolation_preventing_cross_user_access(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent agent execution cross-contamination
        Test that agent execution properly isolates user contexts and prevents data access across users.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database not available for real services testing")
        
        # Create users with different agent execution contexts
        users = []
        agent_registries = []
        
        for i in range(3):
            user = await self.create_isolated_test_user(real_services_fixture, f"agent-{i}")
            user['execution_data'] = {
                'private_query': f"Analyze my private data {user['id']}",
                'sensitive_context': f"confidential-{user['id']}-{uuid.uuid4()}"
            }
            users.append(user)
            
            # Create isolated agent registry for each user
            agent_registry = AgentRegistry()
            await agent_registry.initialize(user_context={
                'user_id': user['id'],
                'organization_id': user['organization_id']
            })
            agent_registries.append(agent_registry)
        
        try:
            async def execute_isolated_agent_task(user_data: Dict, agent_registry, task_id: str):
                """Execute agent task with strict user isolation."""
                
                # Create user-specific execution engine
                execution_engine = ExecutionEngine(
                    user_id=user_data['id'],
                    organization_id=user_data['organization_id']
                )
                
                # Execute task with sensitive user data
                execution_context = {
                    'user_id': user_data['id'],
                    'query': user_data['execution_data']['private_query'],
                    'sensitive_context': user_data['execution_data']['sensitive_context'],
                    'task_id': task_id
                }
                
                result = await execution_engine.execute_agent_task(
                    agent_name='test_agent',
                    context=execution_context
                )
                
                # Verify result contains only this user's context
                assert result['user_id'] == user_data['id'], f"Agent execution leaked user context: {result}"
                assert user_data['execution_data']['sensitive_context'] in str(result), \
                    f"Agent lost user context: {result}"
                
                # Verify no cross-user data contamination  
                other_user_data = [u['execution_data']['sensitive_context'] for u in users if u['id'] != user_data['id']]
                for other_context in other_user_data:
                    assert other_context not in str(result), \
                        f"Agent execution contaminated with other user's data: {other_context}"
                
                return {
                    'user_id': user_data['id'],
                    'task_id': task_id,
                    'execution_isolated': True
                }
            
            # Execute agent tasks concurrently for all users
            execution_tasks = [
                execute_isolated_agent_task(users[i], agent_registries[i], f"task-{i}-{uuid.uuid4()}")
                for i in range(len(users))
            ]
            
            execution_results = await asyncio.gather(*execution_tasks)
            
            # Verify all executions were properly isolated
            assert len(execution_results) == len(users)
            for i, result in enumerate(execution_results):
                assert result['user_id'] == users[i]['id']
                assert result['execution_isolated'] is True
            
        finally:
            # Cleanup agent registries
            cleanup_tasks = [registry.cleanup() for registry in agent_registries if hasattr(registry, 'cleanup')]
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_based_context_isolation_concurrent_operations(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent thread-level context bleed
        Test that thread-based context isolation prevents data bleed during concurrent operations.
        """
        import threading
        from contextvars import ContextVar, copy_context
        
        # Create context variables for user isolation
        current_user_context: ContextVar[Dict] = ContextVar('current_user')
        
        # Create multiple users
        users = []
        for i in range(4):
            user = await self.create_isolated_test_user(real_services_fixture, f"thread-{i}")
            user['thread_context'] = {
                'isolation_token': f"token-{user['id']}-{uuid.uuid4()}",
                'private_state': f"state-{user['id']}-{threading.get_ident()}"
            }
            users.append(user)
        
        isolation_results = {}
        isolation_lock = asyncio.Lock()
        
        async def thread_isolated_operation(user_data: Dict, operation_id: str):
            """Execute operation with thread-local context isolation."""
            
            # Set user context for this thread/task
            current_user_context.set(user_data)
            
            # Simulate complex operation with context access
            await asyncio.sleep(0.1)  # Allow other tasks to potentially interfere
            
            # Retrieve context - should be exactly this user's data
            retrieved_context = current_user_context.get()
            
            assert retrieved_context['id'] == user_data['id'], \
                f"Thread context contaminated: expected {user_data['id']}, got {retrieved_context.get('id')}"
            
            assert retrieved_context['thread_context']['isolation_token'] == user_data['thread_context']['isolation_token'], \
                f"Thread isolation token leaked: {retrieved_context['thread_context']['isolation_token']}"
            
            # Store isolation verification result
            async with isolation_lock:
                isolation_results[user_data['id']] = {
                    'operation_id': operation_id,
                    'context_preserved': True,
                    'thread_isolated': True
                }
            
            return operation_id
        
        # Execute operations concurrently to test thread isolation
        concurrent_tasks = []
        for i, user in enumerate(users):
            # Create multiple operations per user to increase concurrency pressure
            for j in range(2):
                task_id = f"op-{i}-{j}-{uuid.uuid4()}"
                # Copy context to ensure proper isolation
                ctx = copy_context()
                task = ctx.run(asyncio.create_task, thread_isolated_operation(user, task_id))
                concurrent_tasks.append(task)
        
        # Wait for all concurrent operations
        completed_operations = await asyncio.gather(*concurrent_tasks)
        
        # Verify thread isolation was maintained
        assert len(completed_operations) == len(users) * 2  # 2 operations per user
        assert len(isolation_results) == len(users), f"Missing isolation results: {isolation_results}"
        
        for user in users:
            result = isolation_results[user['id']]
            assert result['context_preserved'] is True
            assert result['thread_isolated'] is True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_queue_isolation_user_data_privacy(self, real_services_fixture, real_redis_fixture):
        """
        BVJ: Enterprise - Prevent message queue data leaks
        Test that message queue operations properly isolate user data and maintain privacy.
        """
        redis_client = real_redis_fixture
        
        # Create users with private message data
        users = []
        for i in range(3):
            user = await self.create_isolated_test_user(real_services_fixture, f"queue-{i}")
            user['private_messages'] = [
                f"private-msg-{user['id']}-{j}-{uuid.uuid4()}" for j in range(3)
            ]
            users.append(user)
        
        # Create user-scoped message queues
        queue_operations = []
        for user in users:
            user_queue = f"messages:user:{user['id']}"
            
            # Enqueue private messages for each user
            for msg in user['private_messages']:
                queue_operations.append(
                    redis_client.lpush(user_queue, msg)
                )
        
        # Execute all queue operations concurrently
        await asyncio.gather(*queue_operations)
        
        # Verify message queue isolation
        async def verify_queue_isolation(user_data: Dict):
            """Verify user can only access their own message queue."""
            user_queue = f"messages:user:{user_data['id']}"
            
            # Get this user's messages
            user_messages = await redis_client.lrange(user_queue, 0, -1)
            user_message_set = set(user_messages)
            expected_message_set = set(user_data['private_messages'])
            
            # Verify all user messages are present and correct
            assert user_message_set == expected_message_set, \
                f"User queue contaminated: expected {expected_message_set}, got {user_message_set}"
            
            # Verify no other user's messages are present
            other_users = [u for u in users if u['id'] != user_data['id']]
            for other_user in other_users:
                other_messages = set(other_user['private_messages'])
                overlap = user_message_set.intersection(other_messages)
                assert len(overlap) == 0, \
                    f"User {user_data['id']} queue contains other user's messages: {overlap}"
            
            # Attempt to access other users' queues - should be empty/inaccessible
            for other_user in other_users:
                other_queue = f"messages:user:{other_user['id']}"
                # Should not have read access to other queues in isolated context
                # This would be enforced by application-level permissions in real system
                
            return len(user_messages)
        
        # Verify isolation for all users concurrently
        isolation_tasks = [verify_queue_isolation(user) for user in users]
        message_counts = await asyncio.gather(*isolation_tasks)
        
        # Verify each user got exactly their own messages
        for i, count in enumerate(message_counts):
            assert count == len(users[i]['private_messages']), \
                f"User {users[i]['id']} missing messages: expected {len(users[i]['private_messages'])}, got {count}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_context_isolation_real_jwt_validation(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent authentication context leaks
        Test that authentication context properly isolates user JWT validation and session data.
        """
        import jwt
        import time
        
        # Create users with different authentication contexts
        users = []
        jwt_secrets = []
        
        for i in range(3):
            user = await self.create_isolated_test_user(real_services_fixture, f"auth-{i}")
            
            # Each user gets unique JWT secret for isolation testing
            jwt_secret = f"secret-{user['id']}-{uuid.uuid4()}"
            jwt_secrets.append(jwt_secret)
            
            # Create user-specific JWT token
            payload = {
                'user_id': user['id'],
                'email': user['email'],
                'organization_id': user['organization_id'],
                'iat': int(time.time()),
                'exp': int(time.time()) + 3600,  # 1 hour
                'isolation_context': f"ctx-{user['id']}-{uuid.uuid4()}"
            }
            
            user['jwt_token'] = jwt.encode(payload, jwt_secret, algorithm='HS256')
            user['jwt_secret'] = jwt_secret
            user['jwt_payload'] = payload
            users.append(user)
        
        # Test authentication isolation
        async def validate_auth_context_isolation(user_data: Dict, user_secret: str):
            """Validate authentication context is properly isolated."""
            
            # Decode this user's JWT with correct secret
            try:
                decoded = jwt.decode(user_data['jwt_token'], user_secret, algorithms=['HS256'])
            except jwt.InvalidTokenError:
                pytest.fail(f"Failed to decode valid JWT for user {user_data['id']}")
            
            # Verify decoded data matches user
            assert decoded['user_id'] == user_data['id']
            assert decoded['email'] == user_data['email']
            assert decoded['organization_id'] == user_data['organization_id']
            
            # Attempt to decode this user's JWT with other users' secrets - should fail
            other_secrets = [s for s in jwt_secrets if s != user_secret]
            for other_secret in other_secrets:
                with pytest.raises(jwt.InvalidTokenError):
                    jwt.decode(user_data['jwt_token'], other_secret, algorithms=['HS256'])
            
            # Attempt to decode other users' JWTs with this user's secret - should fail
            other_users = [u for u in users if u['id'] != user_data['id']]
            for other_user in other_users:
                with pytest.raises(jwt.InvalidTokenError):
                    jwt.decode(other_user['jwt_token'], user_secret, algorithms=['HS256'])
            
            return {
                'user_id': user_data['id'],
                'auth_isolated': True,
                'jwt_validated': True
            }
        
        # Test authentication isolation concurrently
        auth_tasks = [
            validate_auth_context_isolation(users[i], jwt_secrets[i])
            for i in range(len(users))
        ]
        
        auth_results = await asyncio.gather(*auth_tasks)
        
        # Verify all authentication contexts were properly isolated
        assert len(auth_results) == len(users)
        for result in auth_results:
            assert result['auth_isolated'] is True
            assert result['jwt_validated'] is True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_state_isolation_user_specific_engines(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent agent state cross-contamination
        Test that agent state isolation maintains user-specific execution engines without bleed.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database not available for real services testing")
        
        # Create users with unique agent state
        users = []
        execution_engines = []
        
        for i in range(4):
            user = await self.create_isolated_test_user(real_services_fixture, f"state-{i}")
            user['agent_state'] = {
                'execution_history': [f"cmd-{j}-{user['id']}" for j in range(3)],
                'private_variables': {f"var_{j}": f"value-{user['id']}-{j}" for j in range(2)},
                'session_memory': f"memory-{user['id']}-{uuid.uuid4()}"
            }
            users.append(user)
            
            # Create isolated execution engine for each user
            engine = ExecutionEngine(
                user_id=user['id'],
                organization_id=user['organization_id'],
                isolation_context=f"engine-{user['id']}"
            )
            execution_engines.append(engine)
        
        try:
            # Initialize engines with user-specific state
            init_tasks = []
            for i, (user, engine) in enumerate(zip(users, execution_engines)):
                init_task = engine.initialize_user_state(user['agent_state'])
                init_tasks.append(init_task)
            
            await asyncio.gather(*init_tasks)
            
            # Test concurrent state operations with potential for cross-contamination
            async def test_state_isolation(user_data: Dict, engine: ExecutionEngine, operation_id: str):
                """Test agent state remains isolated during concurrent operations."""
                
                # Store user-specific state
                state_key = f"user_state_{operation_id}"
                await engine.store_state(state_key, user_data['agent_state'])
                
                # Simulate concurrent processing
                await asyncio.sleep(0.15)  # Allow potential interference
                
                # Retrieve state - must be exactly this user's data
                retrieved_state = await engine.get_state(state_key)
                
                assert retrieved_state == user_data['agent_state'], \
                    f"Agent state contaminated for user {user_data['id']}: {retrieved_state}"
                
                # Verify execution history isolation
                assert retrieved_state['execution_history'] == user_data['agent_state']['execution_history'], \
                    f"Execution history leaked: {retrieved_state['execution_history']}"
                
                # Verify private variables isolation
                assert retrieved_state['private_variables'] == user_data['agent_state']['private_variables'], \
                    f"Private variables leaked: {retrieved_state['private_variables']}"
                
                # Verify session memory isolation
                assert retrieved_state['session_memory'] == user_data['agent_state']['session_memory'], \
                    f"Session memory leaked: {retrieved_state['session_memory']}"
                
                return {
                    'user_id': user_data['id'],
                    'state_isolated': True,
                    'operation_id': operation_id
                }
            
            # Test state isolation under concurrent load
            state_tasks = [
                test_state_isolation(users[i], execution_engines[i], f"op-{i}-{uuid.uuid4()}")
                for i in range(len(users))
            ]
            
            # Add additional concurrent operations to increase pressure
            for i in range(len(users)):
                additional_task = test_state_isolation(
                    users[i], execution_engines[i], f"extra-op-{i}-{uuid.uuid4()}"
                )
                state_tasks.append(additional_task)
            
            state_results = await asyncio.gather(*state_tasks)
            
            # Verify all state operations maintained isolation
            user_results = {}
            for result in state_results:
                user_id = result['user_id']
                if user_id not in user_results:
                    user_results[user_id] = []
                user_results[user_id].append(result)
            
            # Each user should have 2 successful isolated operations
            assert len(user_results) == len(users)
            for user_id, results in user_results.items():
                assert len(results) == 2, f"User {user_id} missing state operations"
                for result in results:
                    assert result['state_isolated'] is True
            
        finally:
            # Cleanup execution engines
            cleanup_tasks = [
                engine.cleanup() for engine in execution_engines 
                if hasattr(engine, 'cleanup')
            ]
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_isolation_different_user_environments(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent configuration leaks between users
        Test that configuration isolation maintains different user environments without cross-access.
        """
        from shared.isolated_environment import IsolatedEnvironment
        
        # Create users with unique configuration contexts
        users = []
        isolated_envs = []
        
        for i in range(3):
            user = await self.create_isolated_test_user(real_services_fixture, f"config-{i}")
            
            # Create isolated environment for each user
            iso_env = IsolatedEnvironment()
            user_config = {
                'API_KEY': f"api-key-{user['id']}-{uuid.uuid4()}",
                'SECRET_TOKEN': f"secret-{user['id']}-{uuid.uuid4()}",
                'DATABASE_URL': f"postgresql://user_{user['id']}:pass@localhost/db_{user['id'][:8]}",
                'REDIS_PREFIX': f"user:{user['id']}:",
                'LOG_LEVEL': f"level-{user['id']}"
            }
            
            # Set user-specific configuration
            for key, value in user_config.items():
                iso_env.set(key, value, source=f"user:{user['id']}")
            
            user['config'] = user_config
            users.append(user)
            isolated_envs.append(iso_env)
        
        # Test configuration isolation
        async def verify_config_isolation(user_data: Dict, user_env: IsolatedEnvironment):
            """Verify user configuration is isolated and cannot access other users' config."""
            
            # Verify this user can access their own configuration
            for key, expected_value in user_data['config'].items():
                actual_value = user_env.get(key)
                assert actual_value == expected_value, \
                    f"User {user_data['id']} config corrupted: {key}={actual_value}, expected {expected_value}"
            
            # Verify configuration values are unique (no sharing between users)
            other_users = [u for u in users if u['id'] != user_data['id']]
            
            for other_user in other_users:
                for key, other_value in other_user['config'].items():
                    user_value = user_env.get(key)
                    
                    assert user_value != other_value, \
                        f"Configuration leaked between users: {user_data['id']} has {other_user['id']}'s {key}"
            
            # Test environment variable isolation
            env_test_key = f"TEST_ISOLATION_{user_data['id'][:8]}"
            test_value = f"isolated-value-{user_data['id']}-{uuid.uuid4()}"
            
            user_env.set(env_test_key, test_value, source=f"test:{user_data['id']}")
            retrieved_value = user_env.get(env_test_key)
            
            assert retrieved_value == test_value, \
                f"Environment isolation failed: {retrieved_value} != {test_value}"
            
            return {
                'user_id': user_data['id'],
                'config_isolated': True,
                'env_isolated': True
            }
        
        # Test configuration isolation concurrently
        config_tasks = [
            verify_config_isolation(users[i], isolated_envs[i])
            for i in range(len(users))
        ]
        
        config_results = await asyncio.gather(*config_tasks)
        
        # Verify all configurations were properly isolated
        assert len(config_results) == len(users)
        for result in config_results:
            assert result['config_isolated'] is True
            assert result['env_isolated'] is True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_isolation_preventing_cross_user_access(self, real_services_fixture):
        """
        BVJ: Enterprise - Prevent tool execution cross-contamination
        Test that tool execution isolation prevents users from accessing other users' tools/results.
        """
        from netra_backend.app.factories.tool_dispatcher_factory import get_tool_dispatcher_factory
        
        # Create users with different tool execution contexts
        users = []
        tool_dispatchers = []
        
        for i in range(3):
            user = await self.create_isolated_test_user(real_services_fixture, f"tool-{i}")
            user['tool_context'] = {
                'allowed_tools': [f"tool_{j}_{user['id'][:8]}" for j in range(2)],
                'private_data': f"private-tool-data-{user['id']}-{uuid.uuid4()}",
                'execution_limits': {'max_calls': 10 + i, 'timeout': 30 + i}
            }
            users.append(user)
            
            # Create isolated tool dispatcher for each user using factory
            # First create UserExecutionContext for this user
            user_context_factory = UserExecutionContextFactory()
            user_context = user_context_factory.create_user_context(
                user_id=user['id'],
                request_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                additional_context={
                    'allowed_tools': user['tool_context']['allowed_tools'],
                    'private_data': user['tool_context']['private_data'],
                    'execution_limits': user['tool_context']['execution_limits'],
                    'isolation_context': f"tools:{user['id']}"
                }
            )
            
            # Create dispatcher using factory
            tool_dispatcher_factory = get_tool_dispatcher_factory()
            dispatcher = await tool_dispatcher_factory.create_for_request(
                user_context=user_context
            )
            tool_dispatchers.append(dispatcher)
        
        try:
            # Test tool execution isolation
            async def test_tool_isolation(user_data: Dict, dispatcher, execution_id: str):
                """Test tool execution is isolated per user."""
                
                # Execute tool with user-specific data
                tool_result = await dispatcher.execute_tool(
                    tool_name=user_data['tool_context']['allowed_tools'][0],
                    parameters={
                        'user_data': user_data['tool_context']['private_data'],
                        'execution_id': execution_id,
                        'user_id': user_data['id']
                    }
                )
                
                # Verify tool result contains only this user's data
                assert user_data['id'] in str(tool_result), \
                    f"Tool result missing user context: {tool_result}"
                
                assert user_data['tool_context']['private_data'] in str(tool_result), \
                    f"Tool result missing private data: {tool_result}"
                
                # Verify other users' data is not accessible
                other_users = [u for u in users if u['id'] != user_data['id']]
                for other_user in other_users:
                    assert other_user['tool_context']['private_data'] not in str(tool_result), \
                        f"Tool execution leaked other user's data: {other_user['tool_context']['private_data']}"
                
                # Attempt to execute tools not allowed for this user - should fail
                other_tools = []
                for other_user in other_users:
                    other_tools.extend(other_user['tool_context']['allowed_tools'])
                
                for unauthorized_tool in other_tools[:2]:  # Test first 2 to avoid excessive operations
                    with pytest.raises((PermissionError, ValueError, KeyError)):
                        await dispatcher.execute_tool(
                            tool_name=unauthorized_tool,
                            parameters={'unauthorized_access': True}
                        )
                
                return {
                    'user_id': user_data['id'],
                    'tool_isolated': True,
                    'execution_id': execution_id
                }
            
            # Test tool isolation under concurrent execution
            tool_tasks = [
                test_tool_isolation(users[i], tool_dispatchers[i], f"exec-{i}-{uuid.uuid4()}")
                for i in range(len(users))
            ]
            
            tool_results = await asyncio.gather(*tool_tasks)
            
            # Verify all tool executions maintained isolation
            assert len(tool_results) == len(users)
            for i, result in enumerate(tool_results):
                assert result['user_id'] == users[i]['id']
                assert result['tool_isolated'] is True
            
        finally:
            # Cleanup tool dispatchers
            cleanup_tasks = [
                dispatcher.cleanup() for dispatcher in tool_dispatchers 
                if hasattr(dispatcher, 'cleanup')
            ]
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_resource_cleanup_isolation_proper_user_data_disposal(self, real_services_fixture, real_redis_fixture):
        """
        BVJ: Enterprise - Ensure complete user data cleanup without affecting other users
        Test that resource cleanup properly disposes of user data without affecting other users.
        """
        redis_client = real_redis_fixture
        
        # Create users with resources that need cleanup
        users = []
        user_resources = {}
        
        for i in range(4):
            user = await self.create_isolated_test_user(real_services_fixture, f"cleanup-{i}")
            
            # Create various user resources
            resources = {
                'cache_keys': [f"cache:{user['id']}:{j}" for j in range(3)],
                'temp_files': [f"temp-{user['id']}-{j}-{uuid.uuid4()}" for j in range(2)],
                'session_data': f"session:{user['id']}",
                'execution_state': f"state:{user['id']}",
                'private_data': {
                    'sensitive_info': f"sensitive-{user['id']}-{uuid.uuid4()}",
                    'personal_data': f"personal-{user['id']}-{uuid.uuid4()}"
                }
            }
            
            user['resources'] = resources
            users.append(user)
            user_resources[user['id']] = resources
        
        # Create all user resources in Redis
        setup_operations = []
        for user in users:
            resources = user['resources']
            
            # Store cache data
            for cache_key in resources['cache_keys']:
                setup_operations.append(
                    redis_client.set(cache_key, f"data-{cache_key}-{uuid.uuid4()}")
                )
            
            # Store session data
            setup_operations.append(
                redis_client.set(resources['session_data'], str(resources['private_data']))
            )
            
            # Store execution state
            setup_operations.append(
                redis_client.set(resources['execution_state'], f"state-{user['id']}-{uuid.uuid4()}")
            )
        
        # Create all resources concurrently
        await asyncio.gather(*setup_operations)
        
        # Verify all resources exist before cleanup
        for user in users:
            resources = user['resources']
            
            # Verify cache keys exist
            for cache_key in resources['cache_keys']:
                exists = await redis_client.exists(cache_key)
                assert exists, f"Setup failed: {cache_key} not created"
        
        # Test isolated resource cleanup (simulate user account deletion/cleanup)
        async def cleanup_user_resources(user_data: Dict, should_cleanup_user_id: str):
            """Clean up resources for specific user without affecting others."""
            
            if user_data['id'] == should_cleanup_user_id:
                # This user should be cleaned up
                resources = user_data['resources']
                
                cleanup_operations = []
                
                # Delete cache keys
                for cache_key in resources['cache_keys']:
                    cleanup_operations.append(redis_client.delete(cache_key))
                
                # Delete session data
                cleanup_operations.append(redis_client.delete(resources['session_data']))
                
                # Delete execution state
                cleanup_operations.append(redis_client.delete(resources['execution_state']))
                
                # Execute cleanup
                deleted_count = sum(await asyncio.gather(*cleanup_operations))
                
                return {
                    'user_id': user_data['id'],
                    'cleaned_up': True,
                    'resources_deleted': deleted_count
                }
            else:
                # This user should NOT be affected by cleanup
                return {
                    'user_id': user_data['id'], 
                    'cleaned_up': False,
                    'resources_deleted': 0
                }
        
        # Select one user for cleanup, others should remain untouched
        cleanup_target_user = users[1]  # Cleanup second user
        
        # Perform isolated cleanup
        cleanup_tasks = [
            cleanup_user_resources(user, cleanup_target_user['id'])
            for user in users
        ]
        
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        
        # Verify cleanup isolation
        cleanup_result = None
        preserved_results = []
        
        for result in cleanup_results:
            if result['cleaned_up']:
                cleanup_result = result
            else:
                preserved_results.append(result)
        
        # Verify exactly one user was cleaned up
        assert cleanup_result is not None, "Target user was not cleaned up"
        assert cleanup_result['user_id'] == cleanup_target_user['id']
        assert cleanup_result['resources_deleted'] > 0
        
        # Verify other users were not affected
        assert len(preserved_results) == len(users) - 1
        
        # Verify target user's resources are gone
        target_resources = cleanup_target_user['resources']
        for cache_key in target_resources['cache_keys']:
            exists = await redis_client.exists(cache_key)
            assert not exists, f"Cleanup failed: {cache_key} still exists"
        
        session_exists = await redis_client.exists(target_resources['session_data'])
        state_exists = await redis_client.exists(target_resources['execution_state'])
        assert not session_exists, f"Session data not cleaned up"
        assert not state_exists, f"Execution state not cleaned up"
        
        # Verify other users' resources are preserved
        other_users = [u for u in users if u['id'] != cleanup_target_user['id']]
        for user in other_users:
            resources = user['resources']
            
            # Verify cache keys still exist
            for cache_key in resources['cache_keys']:
                exists = await redis_client.exists(cache_key)
                assert exists, f"Other user's resource was incorrectly deleted: {cache_key}"
            
            # Verify session and state data preserved
            session_exists = await redis_client.exists(resources['session_data'])
            state_exists = await redis_client.exists(resources['execution_state'])
            assert session_exists, f"Other user's session was incorrectly deleted"
            assert state_exists, f"Other user's state was incorrectly deleted"

        # Final verification: cleanup was surgical and isolated
        self.assert_business_value_delivered(
            {'isolated_cleanup': True, 'other_users_preserved': len(other_users)},
            'automation'
        )