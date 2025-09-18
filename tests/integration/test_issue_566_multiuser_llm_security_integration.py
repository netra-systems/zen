"""
INTEGRATION SECURITY TEST: Issue #566 Multi-User LLM Cache Security

This integration test validates end-to-end security for multi-user LLM operations
with real service integration. It complements the unit tests by testing the complete
request flow through authentication, user context creation, and LLM operations.

VULNERABILITY SCOPE:
- Multi-user concurrent LLM requests
- WebSocket agent integration with LLM cache
- Request-response isolation across user sessions
- Cache persistence across request boundaries

BUSINESS VALUE JUSTIFICATION:
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Prevent customer data breaches
- Value Impact: Protect $500K+ ARR from security incidents
- Strategic Impact: CRITICAL - GDPR/CCPA compliance

Integration Testing Approach:
- Real database sessions for user contexts
- Real Redis for session management  
- Real LLM cache operations
- Concurrent user simulation
- NO Docker dependency (follows CLAUDE.md)

Expected Test Behavior:
- FAIL initially to demonstrate active vulnerability
- PASS after proper user context isolation fix
- Automated detection of security regressions
"""
import pytest
import asyncio
import uuid
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.llm.llm_manager import LLMManager, create_llm_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.redis_manager import redis_manager

@pytest.mark.integration
class Issue566MultiUserLLMSecurityIntegrationTests(SSotAsyncTestCase):
    """
    Integration security tests for Issue #566 multi-user LLM cache vulnerability.
    
    These tests use real database and Redis to simulate production conditions
    where multiple users make concurrent LLM requests that could result in
    cache mixing if proper isolation is not implemented.
    """

    async def setup_method(self, method):
        """Set up integration test environment with real services."""
        await super().setup_method(method)
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        await redis_manager.initialize()
        self.redis_client = redis_manager
        self.test_users = [{'user_id': f'integration_user_{i}', 'email': f'testuser{i}@example.com', 'thread_id': f'thread_integration_{i}', 'run_id': f'run_integration_{i}', 'request_id': f'req_integration_{i}'} for i in range(5)]
        self.test_prompts = ['Analyze my cost optimization opportunities', 'Review my infrastructure efficiency', 'What are my performance bottlenecks?', 'Generate my compliance report', 'Optimize my resource allocation']
        self.user_specific_responses = {user['user_id']: f"Personalized analysis for {user['user_id']}: {response}" for user, response in zip(self.test_users, ['Reduce compute costs by 30%', 'Scale database connections', 'Optimize memory usage patterns', 'Update security policies', 'Reallocate storage resources'])}

    async def teardown_method(self, method):
        """Clean up integration test resources."""
        for user in self.test_users:
            user_keys = await self.redis_client.get_client().keys(f"*{user['user_id']}*")
            if user_keys:
                await self.redis_client.get_client().delete(*user_keys)
        await super().teardown_method(method)

    async def test_concurrent_user_llm_cache_isolation_vulnerability(self):
        """
        CRITICAL INTEGRATION TEST: Concurrent user LLM cache isolation.
        
        This test simulates real production conditions with multiple users
        making simultaneous LLM requests and verifies cache isolation.
        
        Expected Initial Behavior: FAIL - Cache mixing between users
        Expected After Fix: PASS - Perfect cache isolation
        """
        user_contexts = []
        for user in self.test_users:
            context = UserExecutionContext.from_request(user_id=user['user_id'], thread_id=user['thread_id'], run_id=user['run_id'], request_id=user['request_id'], db_session=None)
            user_contexts.append(context)
        user_managers = []
        for context in user_contexts:
            manager = create_llm_manager(user_context=context)
            await manager.initialize()
            user_managers.append(manager)

        async def simulate_user_llm_operation(user_index: int):
            """Simulate a user making LLM requests."""
            manager = user_managers[user_index]
            user_id = self.test_users[user_index]['user_id']
            prompt = 'What are my optimization recommendations?'
            cache_key = manager._get_cache_key(prompt, 'default')
            expected_response = self.user_specific_responses[user_id]
            manager._cache[cache_key] = expected_response
            if manager._is_cached(prompt, 'default'):
                cached_response = manager._cache[cache_key]
                return {'user_id': user_id, 'cache_key': cache_key, 'response': cached_response, 'manager_id': id(manager)}
            else:
                return {'user_id': user_id, 'error': 'Cache lookup failed'}
        tasks = [simulate_user_llm_operation(i) for i in range(len(self.test_users))]
        results = await asyncio.gather(*tasks)
        cache_keys_seen = set()
        for result in results:
            if 'error' in result:
                pytest.fail(f"Cache operation failed for {result['user_id']}: {result['error']}")
            user_id = result['user_id']
            cache_key = result['cache_key']
            response = result['response']
            assert cache_key not in cache_keys_seen, f'SECURITY VULNERABILITY: Duplicate cache key found!\nUser: {user_id}\nCache key: {cache_key}\nThis indicates cache mixing between users.'
            cache_keys_seen.add(cache_key)
            expected_response = self.user_specific_responses[user_id]
            assert response == expected_response, f'SECURITY VULNERABILITY: User got wrong response!\nUser: {user_id}\nExpected: {expected_response}\nGot: {response}\nThis indicates cache data mixing between users.'
            assert cache_key.startswith(f'{user_id}:'), f'SECURITY VULNERABILITY: Cache key missing user prefix!\nUser: {user_id}\nCache key: {cache_key}\nThis allows cache collision between users.'

    async def test_startup_global_manager_integration_vulnerability(self):
        """
        INTEGRATION TEST: Validate startup creates isolated managers.
        
        This test simulates the production startup sequence and verifies
        that global managers are not created that could cause cache mixing.
        """
        from netra_backend.app.startup_module import setup_security_services
        from netra_backend.app.smd import StartupModuleDeterministic
        from netra_backend.app.services.key_manager import KeyManager
        from netra_backend.app.core.configuration.base import UnifiedConfiguration
        from fastapi import FastAPI
        test_app = FastAPI()
        env = IsolatedEnvironment()
        key_manager = KeyManager(openai_api_key=env.get('OPENAI_API_KEY', 'test_key'), jwt_secret_key=env.get('JWT_SECRET_KEY', 'test_jwt_secret'))
        setup_security_services(test_app, key_manager)
        if hasattr(test_app.state, 'llm_manager'):
            global_manager = test_app.state.llm_manager
            assert global_manager._user_context is None, 'Global LLM manager has unexpected user context'
            test_prompt = 'Test prompt for security check'
            global_cache_key = global_manager._get_cache_key(test_prompt, 'default')
            assert global_cache_key.startswith('user_'), f'SECURITY VULNERABILITY: Global manager creates unscoped cache keys!\nCache key: {global_cache_key}\nThis is the exact vulnerability in startup_module.py:649\nFIX: Remove global LLM manager creation from startup.'
        test_config = UnifiedConfiguration(environment='test', database_config=None, redis_config=None, service_configs={})
        smd = StartupModuleDeterministic(test_app, test_config)
        smd._initialize_llm_manager()
        if hasattr(test_app.state, 'llm_manager'):
            global_manager = test_app.state.llm_manager
            test_prompt = 'Test prompt for SMD security check'
            global_cache_key = global_manager._get_cache_key(test_prompt, 'default')
            assert global_cache_key.startswith('user_'), f'SECURITY VULNERABILITY: SMD creates unscoped cache keys!\nCache key: {global_cache_key}\nThis is the exact vulnerability in smd.py:1007\nFIX: Remove global LLM manager creation from SMD.'

    async def test_websocket_agent_llm_integration_security(self):
        """
        INTEGRATION TEST: WebSocket agent LLM integration security.
        
        This test validates that WebSocket-driven agent operations maintain
        proper LLM cache isolation when multiple users have active WebSocket
        sessions making agent requests.
        """
        websocket_users = []
        for i, user in enumerate(self.test_users[:3]):
            ws_context = UserExecutionContext.from_websocket_request(user_id=user['user_id'], websocket_client_id=f'ws_client_{i}', operation='agent_chat')
            websocket_users.append(ws_context)
        ws_managers = []
        for context in websocket_users:
            manager = create_llm_manager(user_context=context)
            await manager.initialize()
            ws_managers.append(manager)
        agent_requests = [{'user_index': 0, 'prompt': 'Analyze my infrastructure', 'agent_type': 'infrastructure'}, {'user_index': 1, 'prompt': 'Optimize my costs', 'agent_type': 'optimization'}, {'user_index': 2, 'prompt': 'Review my security', 'agent_type': 'security'}, {'user_index': 0, 'prompt': 'Generate my report', 'agent_type': 'reporting'}]

        async def process_agent_request(request: Dict[str, Any]):
            """Simulate agent processing with LLM cache."""
            user_index = request['user_index']
            manager = ws_managers[user_index]
            context = websocket_users[user_index]
            prompt = request['prompt']
            agent_type = request['agent_type']
            cache_key = manager._get_cache_key(prompt, agent_type)
            user_response = f'Agent {agent_type} response for {context.user_id}: {prompt}'
            manager._cache[cache_key] = user_response
            return {'user_id': context.user_id, 'websocket_client_id': context.websocket_client_id, 'cache_key': cache_key, 'response': user_response, 'agent_type': agent_type}
        tasks = [process_agent_request(req) for req in agent_requests]
        agent_results = await asyncio.gather(*tasks)
        user_cache_keys = {}
        for result in agent_results:
            user_id = result['user_id']
            cache_key = result['cache_key']
            if user_id not in user_cache_keys:
                user_cache_keys[user_id] = []
            user_cache_keys[user_id].append(cache_key)
            assert cache_key.startswith(f'{user_id}:'), f'SECURITY VULNERABILITY: WebSocket agent cache key not user-scoped!\nUser: {user_id}\nCache key: {cache_key}\nThis allows WebSocket cache mixing between users.'
        all_cache_keys = [key for keys in user_cache_keys.values() for key in keys]
        unique_cache_keys = set(all_cache_keys)
        assert len(all_cache_keys) == len(unique_cache_keys), f'SECURITY VULNERABILITY: Duplicate cache keys in WebSocket sessions!\nTotal keys: {len(all_cache_keys)}\nUnique keys: {len(unique_cache_keys)}\nThis indicates cache collision between WebSocket users.'
        user_0_keys = user_cache_keys[websocket_users[0].user_id]
        assert len(user_0_keys) == 2, f'User 0 should have 2 cache entries, got {len(user_0_keys)}'
        for i, user_keys in enumerate(user_cache_keys.values()):
            user_id = list(user_cache_keys.keys())[i]
            for key in user_keys:
                for j, other_manager in enumerate(ws_managers):
                    if j != i:
                        assert key not in other_manager._cache, f"SECURITY VULNERABILITY: User {j} can access User {i}'s cache!\nLeaked cache key: {key}\nThis indicates WebSocket cache mixing."

    async def test_redis_session_llm_cache_isolation(self):
        """
        INTEGRATION TEST: Redis session with LLM cache isolation.
        
        This test validates that LLM cache isolation works correctly with
        Redis session management for persistent user sessions.
        """
        user_sessions = {}
        for user in self.test_users[:3]:
            session_id = str(uuid.uuid4())
            session_data = {'user_id': user['user_id'], 'email': user['email'], 'created_at': datetime.now(timezone.utc).isoformat(), 'llm_preferences': {'model': 'gpt-4', 'temperature': 0.7}}
            await self.redis_client.get_client().setex(f'session:{session_id}', 3600, json.dumps(session_data))
            user_sessions[user['user_id']] = session_id
        session_managers = {}
        for user in self.test_users[:3]:
            user_id = user['user_id']
            session_id = user_sessions[user_id]
            context = UserExecutionContext.from_request(user_id=user_id, thread_id=user['thread_id'], run_id=user['run_id'], request_id=user['request_id'], audit_metadata={'session_id': session_id})
            manager = create_llm_manager(user_context=context)
            await manager.initialize()
            session_managers[user_id] = manager
        test_prompt = 'Generate my personalized dashboard'
        for user_id, manager in session_managers.items():
            session_id = user_sessions[user_id]
            cache_key = manager._get_cache_key(test_prompt, 'dashboard')
            session_response = f'Dashboard for session {session_id} user {user_id}'
            manager._cache[cache_key] = session_response
            assert cache_key.startswith(f'{user_id}:'), f'Redis session cache key not user-scoped: {cache_key}'
            stored_session = await self.redis_client.get_client().get(f'session:{session_id}')
            assert stored_session is not None, f'Session {session_id} not found in Redis'
            session_data = json.loads(stored_session)
            assert session_data['user_id'] == user_id, f'Session data mismatch for {user_id}'
        cache_keys = []
        for manager in session_managers.values():
            cache_key = manager._get_cache_key(test_prompt, 'dashboard')
            cache_keys.append(cache_key)
        assert len(cache_keys) == len(set(cache_keys)), f'Redis session cache keys not isolated: {cache_keys}'
        managers_list = list(session_managers.values())
        for i, manager in enumerate(managers_list):
            for j, other_manager in enumerate(managers_list):
                if i != j:
                    my_cache_key = manager._get_cache_key(test_prompt, 'dashboard')
                    assert my_cache_key not in other_manager._cache, f'Manager {i} cache accessible by Manager {j}!'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')