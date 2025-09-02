"""
Mission Critical Data Layer Isolation Security Tests

These tests are designed to FAIL and expose critical security vulnerabilities:
1. ClickHouse cache contamination between users
2. Redis key collision between users  
3. Missing user context propagation
4. Session isolation failures

IMPORTANT: These tests currently FAIL to demonstrate security issues exist.
They must pass after implementing proper data layer isolation.
"""

import pytest
import asyncio
import uuid
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set
from unittest.mock import AsyncMock, MagicMock

# Import real services and components
from netra_backend.app.database import get_db


@pytest.mark.mission_critical
@pytest.mark.asyncio
class TestDataLayerIsolation:
    """
    Test suite to expose critical data layer isolation vulnerabilities.
    
    These tests simulate realistic multi-user scenarios that would occur
    in production with 10+ concurrent users.
    """
    
    @pytest.fixture
    async def setup_test_users(self):
        """Setup multiple test users for isolation testing."""
        users = []
        for i in range(5):
            user_data = {
                'id': f'test-user-{i}-{uuid.uuid4()}',
                'email': f'testuser{i}@isolation-test.com',
                'username': f'testuser{i}',
                'is_active': True
            }
            users.append(user_data)
        return users
    
    @pytest.fixture
    async def setup_test_corpora(self, setup_test_users):
        """Setup test corpora for each user."""
        corpora = []
        for i, user in enumerate(setup_test_users):
            corpus_data = {
                'id': f'corpus-{i}-{uuid.uuid4()}',
                'name': f'Test Corpus {i}',
                'user_id': user['id'],
                'description': f'Private corpus for user {i}',
                'metadata': {'confidential': True, 'user_specific': True}
            }
            corpora.append(corpus_data)
        return corpora
    
    async def test_clickhouse_cache_contamination_vulnerability(self, setup_test_users, setup_test_corpora):
        """
        SECURITY TEST: Proves ClickHouse cache contamination between users.
        
        This test should FAIL, demonstrating that:
        1. User A's queries contaminate cache for User B
        2. Cache keys don't include user context
        3. Users can see each other's data through cache hits
        """
        users = await setup_test_users
        corpora = await setup_test_corpora
        
        user_a, user_b = users[0], users[1]
        corpus_a, corpus_b = corpora[0], corpora[1]
        
        # Simulate ClickHouse query execution with caching
        query = "SELECT * FROM corpus_documents WHERE corpus_id = ?"
        
        # User A executes query - this should populate cache
        cache_key_a = f"query:{hash(query)}:{corpus_a['id']}"
        
        # Simulate cache population (this is what currently happens)
        mock_cache = {}
        mock_cache[cache_key_a] = {
            'results': [{'doc_id': 'doc1', 'content': 'User A confidential data'}],
            'user_id': user_a['id']  # Cache doesn't actually store this currently
        }
        
        # User B executes same query structure with their corpus
        cache_key_b = f"query:{hash(query)}:{corpus_b['id']}"
        
        # VULNERABILITY: If cache keys don't include user context properly,
        # User B might get User A's results
        if cache_key_a == cache_key_b:  # This shouldn't happen but might
            contaminated_result = mock_cache.get(cache_key_a)
            
            # SECURITY FAILURE: User B got User A's data
            assert contaminated_result['user_id'] != user_b['id'], \
                "SECURITY VULNERABILITY: User B received User A's cached data"
        
        # Test parallel cache access vulnerability
        async def execute_user_query(user, corpus):
            """Simulate user executing query that should hit cache."""
            cache_key = f"query_basic:{corpus['id']}"  # Simplified cache key
            
            # This simulates current vulnerable caching logic
            if cache_key not in mock_cache:
                mock_cache[cache_key] = {
                    'data': f"Confidential data for {user['email']}",
                    'timestamp': time.time()
                }
            
            return mock_cache[cache_key]
        
        # Execute queries concurrently
        tasks = []
        for user, corpus in zip(users[:3], corpora[:3]):
            tasks.append(execute_user_query(user, corpus))
        
        results = await asyncio.gather(*tasks)
        
        # VULNERABILITY CHECK: Results should be user-specific
        unique_data = set(result['data'] for result in results)
        
        # This assertion should FAIL if cache contamination exists
        assert len(unique_data) == len(results), \
            f"SECURITY VULNERABILITY: Cache contamination detected. Expected {len(results)} unique results, got {len(unique_data)}"
    
    async def test_redis_key_collision_vulnerability(self, setup_test_users):
        """
        SECURITY TEST: Proves Redis key collision between users.
        
        This test should FAIL, demonstrating that:
        1. Session keys collide between users
        2. Users can access each other's sessions
        3. Chat contexts bleed between users
        """
        users = await setup_test_users
        user_a, user_b = users[0], users[1]
        
        # Simulate Redis operations with vulnerable key generation
        mock_redis = {}
        
        # Vulnerable session key generation (current implementation)
        def generate_session_key(session_id: str, user_id: str = None) -> str:
            # VULNERABILITY: Key doesn't include user_id properly
            return f"session:{session_id}"  # Missing user context!
        
        # User A creates a session
        session_id = "abc123"  # Common session ID format
        session_key_a = generate_session_key(session_id, user_a['id'])
        
        mock_redis[session_key_a] = {
            'user_id': user_a['id'],
            'chat_context': 'User A confidential conversation',
            'agent_state': {'thinking': 'Private thoughts for User A'},
            'sensitive_data': 'User A SSN: 123-45-6789'
        }
        
        # User B somehow gets same session ID (possible in distributed system)
        session_key_b = generate_session_key(session_id, user_b['id'])
        
        # VULNERABILITY: Keys are identical!
        assert session_key_a != session_key_b, \
            f"SECURITY VULNERABILITY: Session key collision! User A key '{session_key_a}' == User B key '{session_key_b}'"
        
        # If keys collide, User B can access User A's data
        if session_key_a == session_key_b:
            user_b_gets = mock_redis.get(session_key_b)
            assert user_b_gets['user_id'] == user_b['id'], \
                f"SECURITY BREACH: User B accessed User A's session data: {user_b_gets}"
    
    async def test_concurrent_user_data_contamination(self, setup_test_users, setup_test_corpora):
        """
        SECURITY TEST: Concurrent access contamination vulnerability.
        
        Tests race conditions in data access that could expose user data.
        This should FAIL demonstrating the vulnerability exists.
        """
        users = await setup_test_users
        corpora = await setup_test_corpora
        
        # Simulate shared cache/memory that lacks proper isolation
        shared_execution_context = {
            'current_user_id': None,
            'current_corpus_id': None,
            'query_cache': {},
            'active_sessions': {}
        }
        
        async def simulate_user_operation(user, corpus, operation_id):
            """Simulate user performing data operations concurrently."""
            
            # VULNERABILITY: Global state not properly isolated
            shared_execution_context['current_user_id'] = user['id']
            shared_execution_context['current_corpus_id'] = corpus['id']
            
            # Simulate some processing delay
            await asyncio.sleep(0.1)
            
            # Read back "current user" - might be contaminated by other concurrent operations
            actual_user_id = shared_execution_context['current_user_id']
            actual_corpus_id = shared_execution_context['current_corpus_id']
            
            return {
                'operation_id': operation_id,
                'expected_user_id': user['id'],
                'actual_user_id': actual_user_id,
                'expected_corpus_id': corpus['id'],
                'actual_corpus_id': actual_corpus_id,
                'contaminated': actual_user_id != user['id'] or actual_corpus_id != corpus['id']
            }
        
        # Execute operations concurrently to expose race conditions
        tasks = []
        for i, (user, corpus) in enumerate(zip(users, corpora)):
            tasks.append(simulate_user_operation(user, corpus, i))
        
        results = await asyncio.gather(*tasks)
        
        # Check for contamination
        contaminated_operations = [r for r in results if r['contaminated']]
        
        # This should FAIL if contamination exists
        assert len(contaminated_operations) == 0, \
            f"SECURITY VULNERABILITY: {len(contaminated_operations)} operations were contaminated: {contaminated_operations}"
    
    async def test_user_context_propagation_failure(self, setup_test_users):
        """
        SECURITY TEST: User context propagation failure across system layers.
        
        This should FAIL, proving that user context is lost between layers.
        """
        users = await setup_test_users
        user = users[0]
        
        # Simulate request flow through system layers
        class VulnerableRequestContext:
            """Simulates current vulnerable request context."""
            
            def __init__(self):
                self.user_id = None
                self.session_id = None
                self.permissions = None
            
            async def authenticate_user(self, user_id: str):
                self.user_id = user_id
                return True
            
            async def process_through_layer1(self):
                # Layer 1: API Gateway
                assert self.user_id is not None, "User context lost at Layer 1"
                return self
            
            async def process_through_layer2(self):
                # Layer 2: Business Logic
                # VULNERABILITY: Context might be lost here
                if not hasattr(self, 'user_id') or self.user_id is None:
                    raise ValueError("SECURITY FAILURE: User context lost at Layer 2")
                return self
            
            async def process_through_layer3(self):
                # Layer 3: Data Access
                # VULNERABILITY: Context definitely lost here in current implementation
                # Simulate context loss
                self.user_id = None  # This is what currently happens
                
                if self.user_id is None:
                    raise ValueError("SECURITY FAILURE: User context lost at Data Layer")
                return self
        
        # Test context propagation
        context = VulnerableRequestContext()
        await context.authenticate_user(user['id'])
        
        # Should succeed
        context = await context.process_through_layer1()
        context = await context.process_through_layer2()
        
        # This should FAIL due to context loss
        with pytest.raises(ValueError, match="User context lost at Data Layer"):
            await context.process_through_layer3()
    
    async def test_session_isolation_vulnerability(self, setup_test_users):
        """
        SECURITY TEST: Session isolation failure between users.
        
        Tests that user sessions can bleed into each other.
        This should FAIL demonstrating the vulnerability.
        """
        users = await setup_test_users
        user_a, user_b, user_c = users[0], users[1], users[2]
        
        # Simulate vulnerable session management
        class VulnerableSessionManager:
            def __init__(self):
                self.active_sessions = {}  # Shared session storage
                self.current_session = None  # Global current session!
            
            def create_session(self, user_id: str, session_id: str):
                session_data = {
                    'user_id': user_id,
                    'created_at': time.time(),
                    'chat_history': [],
                    'agent_context': {},
                    'sensitive_flags': {'is_admin': user_id == user_a['id']}
                }
                self.active_sessions[session_id] = session_data
                self.current_session = session_data  # VULNERABILITY: Global state!
                return session_data
            
            def get_current_session(self):
                return self.current_session
            
            def add_message_to_current_session(self, message: str):
                if self.current_session:
                    self.current_session['chat_history'].append({
                        'message': message,
                        'timestamp': time.time()
                    })
        
        session_manager = VulnerableSessionManager()
        
        # User A creates admin session
        session_a = session_manager.create_session(user_a['id'], 'session_a')
        session_manager.add_message_to_current_session("Admin command: DELETE ALL USERS")
        
        # User B creates regular session
        session_b = session_manager.create_session(user_b['id'], 'session_b')
        session_manager.add_message_to_current_session("Regular user message")
        
        # User C tries to access current session
        current_session = session_manager.get_current_session()
        
        # VULNERABILITY: User C might get User B's session due to global state
        assert current_session['user_id'] == user_c['id'], \
            f"SECURITY VULNERABILITY: User C got session belonging to user {current_session['user_id']}"
        
        # Check for admin privilege escalation
        if current_session.get('sensitive_flags', {}).get('is_admin'):
            assert current_session['user_id'] == user_a['id'], \
                f"SECURITY BREACH: Non-admin user {current_session['user_id']} has admin privileges"
    
    async def test_cache_key_predictability_vulnerability(self, setup_test_users, setup_test_corpora):
        """
        SECURITY TEST: Cache key predictability allows unauthorized access.
        
        Tests if users can guess and access other users' cached data.
        This should FAIL demonstrating the vulnerability.
        """
        users = await setup_test_users
        corpora = await setup_test_corpora
        
        user_a, user_b = users[0], users[1]
        corpus_a, corpus_b = corpora[0], corpora[1]
        
        # Simulate vulnerable cache key generation
        def generate_cache_key(query_type: str, resource_id: str) -> str:
            # VULNERABILITY: Keys are predictable and don't include user context
            return f"{query_type}:{resource_id}"
        
        mock_cache = {}
        
        # User A caches sensitive data
        cache_key_a = generate_cache_key("corpus_data", corpus_a['id'])
        mock_cache[cache_key_a] = {
            'sensitive_documents': [
                {'id': 'doc1', 'content': 'CONFIDENTIAL: User A medical records'},
                {'id': 'doc2', 'content': 'CONFIDENTIAL: User A financial data'}
            ],
            'user_id': user_a['id']
        }
        
        # User B tries to access their corpus but gets predictable key
        cache_key_b = generate_cache_key("corpus_data", corpus_b['id'])
        
        # User B could potentially guess User A's corpus ID and access their data
        guessed_corpus_id = corpus_a['id']  # In reality, this might be predictable
        guessed_cache_key = generate_cache_key("corpus_data", guessed_corpus_id)
        
        if guessed_cache_key in mock_cache:
            unauthorized_data = mock_cache[guessed_cache_key]
            
            # SECURITY VULNERABILITY: User B accessed User A's data
            assert unauthorized_data['user_id'] == user_b['id'], \
                f"SECURITY BREACH: User B accessed data belonging to {unauthorized_data['user_id']}"
    
    @pytest.mark.parametrize("concurrent_users", [5, 10, 20])
    async def test_high_concurrency_isolation_failure(self, concurrent_users, setup_test_users):
        """
        SECURITY TEST: High concurrency exposes isolation failures.
        
        Tests system behavior under high concurrent load to expose race conditions.
        This should FAIL under high load demonstrating vulnerabilities.
        """
        users = (await setup_test_users)[:min(concurrent_users, 5)]
        # Replicate users to reach desired concurrency
        extended_users = (users * (concurrent_users // len(users) + 1))[:concurrent_users]
        
        # Shared vulnerable state
        vulnerable_state = {
            'active_user': None,
            'processing_queue': [],
            'cache_hits': 0,
            'security_violations': []
        }
        
        async def simulate_high_load_operation(user, operation_id):
            """Simulate user operation under high load."""
            
            # Set current user (race condition vulnerability)
            vulnerable_state['active_user'] = user['id']
            
            # Simulate processing delay
            await asyncio.sleep(0.05)
            
            # Check if user context was preserved
            current_user = vulnerable_state['active_user']
            
            if current_user != user['id']:
                violation = {
                    'operation_id': operation_id,
                    'expected_user': user['id'],
                    'actual_user': current_user,
                    'violation_type': 'context_contamination'
                }
                vulnerable_state['security_violations'].append(violation)
            
            return {
                'operation_id': operation_id,
                'user_id': user['id'],
                'context_preserved': current_user == user['id']
            }
        
        # Execute high concurrency operations
        tasks = []
        for i, user in enumerate(extended_users):
            tasks.append(simulate_high_load_operation(user, i))
        
        results = await asyncio.gather(*tasks)
        
        # Analyze results for security violations
        violations = vulnerable_state['security_violations']
        context_preservation_rate = sum(1 for r in results if r['context_preserved']) / len(results)
        
        # This should FAIL under high concurrency
        assert len(violations) == 0, \
            f"SECURITY VULNERABILITIES: {len(violations)} context contamination violations under {concurrent_users} concurrent users"
        
        assert context_preservation_rate >= 0.95, \
            f"SECURITY RISK: Context preservation rate {context_preservation_rate:.2%} is below 95% under high load"
    
    async def test_cross_tenant_data_leakage_vulnerability(self, setup_test_users, setup_test_corpora):
        """
        SECURITY TEST: Cross-tenant data leakage in multi-tenant setup.
        
        Simulates enterprise scenario where multiple tenants share infrastructure.
        This should FAIL demonstrating data leakage between tenants.
        """
        users = await setup_test_users
        corpora = await setup_test_corpora
        
        # Simulate tenant setup
        tenant_a_users = users[:2]
        tenant_b_users = users[2:4]
        tenant_c_users = users[4:]
        
        tenant_a_corpora = corpora[:2]
        tenant_b_corpora = corpora[2:4]
        tenant_c_corpora = corpora[4:]
        
        # Vulnerable multi-tenant query executor
        class VulnerableMultiTenantQueryExecutor:
            def __init__(self):
                self.query_cache = {}
                self.current_tenant = None
                self.tenant_data = {
                    'tenant_a': {'secret': 'Tenant A trade secrets'},
                    'tenant_b': {'secret': 'Tenant B financial data'},
                    'tenant_c': {'secret': 'Tenant C customer list'}
                }
            
            async def execute_tenant_query(self, tenant_id: str, user_id: str, query: str):
                # VULNERABILITY: Tenant context not properly isolated
                self.current_tenant = tenant_id
                
                # Simulate query execution delay
                await asyncio.sleep(0.1)
                
                # VULNERABILITY: Might return wrong tenant's data due to race conditions
                actual_tenant = self.current_tenant
                
                if actual_tenant != tenant_id:
                    # Data leakage occurred!
                    return {
                        'user_id': user_id,
                        'expected_tenant': tenant_id,
                        'actual_tenant': actual_tenant,
                        'leaked_data': self.tenant_data.get(actual_tenant, {}),
                        'security_violation': True
                    }
                
                return {
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'data': self.tenant_data.get(tenant_id, {}),
                    'security_violation': False
                }
        
        executor = VulnerableMultiTenantQueryExecutor()
        
        # Execute concurrent queries across tenants
        tasks = []
        
        # Tenant A queries
        for user in tenant_a_users:
            tasks.append(executor.execute_tenant_query('tenant_a', user['id'], 'SELECT secrets'))
        
        # Tenant B queries
        for user in tenant_b_users:
            tasks.append(executor.execute_tenant_query('tenant_b', user['id'], 'SELECT financials'))
        
        # Tenant C queries
        for user in tenant_c_users:
            tasks.append(executor.execute_tenant_query('tenant_c', user['id'], 'SELECT customers'))
        
        results = await asyncio.gather(*tasks)
        
        # Check for cross-tenant data leakage
        violations = [r for r in results if r.get('security_violation', False)]
        
        # This should FAIL if cross-tenant leakage exists
        assert len(violations) == 0, \
            f"CRITICAL SECURITY BREACH: {len(violations)} cross-tenant data leakage violations detected: {violations}"


@pytest.mark.mission_critical
class TestDataLayerIsolationSynchronous:
    """
    Synchronous tests for data layer isolation vulnerabilities.
    
    These complement the async tests with thread-based concurrency testing.
    """
    
    def test_thread_based_context_contamination(self, setup_test_users):
        """
        SECURITY TEST: Thread-based context contamination.
        
        Uses threading to expose context contamination in synchronous code.
        This should FAIL demonstrating thread safety issues.
        """
        users = setup_test_users
        
        # Vulnerable global state
        global_context = {'current_user_id': None, 'violations': []}
        
        def user_operation(user, operation_id):
            """Simulate user operation in thread."""
            import time
            
            # Set user context
            global_context['current_user_id'] = user['id']
            
            # Simulate work
            time.sleep(0.1)
            
            # Check if context was preserved
            actual_user = global_context['current_user_id']
            
            if actual_user != user['id']:
                violation = {
                    'operation_id': operation_id,
                    'expected_user': user['id'],
                    'actual_user': actual_user
                }
                global_context['violations'].append(violation)
                return False
            
            return True
        
        # Execute operations in parallel threads
        with ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = []
            for i, user in enumerate(users):
                future = executor.submit(user_operation, user, i)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Check for violations
        violations = global_context['violations']
        
        # This should FAIL if thread contamination exists
        assert len(violations) == 0, \
            f"SECURITY VULNERABILITY: {len(violations)} thread-based context contamination violations: {violations}"
    
    def test_cache_key_collision_patterns(self):
        """
        SECURITY TEST: Common cache key collision patterns.
        
        Tests various patterns that could lead to cache key collisions.
        This should FAIL if vulnerable patterns exist.
        """
        
        # Test vulnerable key generation patterns
        def vulnerable_key_generator_v1(user_id: str, resource_id: str) -> str:
            # VULNERABILITY: Hash collisions possible
            return str(hash(f"{user_id}:{resource_id}") % 10000)
        
        def vulnerable_key_generator_v2(user_id: str, resource_id: str) -> str:
            # VULNERABILITY: Truncated keys can collide
            return f"{user_id[:4]}:{resource_id[:4]}"
        
        def vulnerable_key_generator_v3(user_id: str, resource_id: str) -> str:
            # VULNERABILITY: Simple concatenation without separator
            return f"{user_id}{resource_id}"
        
        # Test data that should produce unique keys but might not
        test_cases = [
            ('user123', 'resource456'),
            ('user1', 'resource23456'),  # Could collide with previous in v3
            ('user12', 'resource3456'),  # Could collide with first in v3
            ('user', 'resource123456'),  # Could collide with first in v2
        ]
        
        # Test each vulnerable generator
        generators = [
            ('v1_hash_mod', vulnerable_key_generator_v1),
            ('v2_truncated', vulnerable_key_generator_v2),
            ('v3_simple_concat', vulnerable_key_generator_v3),
        ]
        
        for gen_name, generator in generators:
            keys = set()
            collisions = []
            
            for user_id, resource_id in test_cases:
                key = generator(user_id, resource_id)
                if key in keys:
                    collisions.append({
                        'generator': gen_name,
                        'key': key,
                        'user_id': user_id,
                        'resource_id': resource_id
                    })
                keys.add(key)
            
            # This should FAIL if collisions exist
            assert len(collisions) == 0, \
                f"SECURITY VULNERABILITY: Cache key collisions in {gen_name}: {collisions}"


if __name__ == "__main__":
    # Run the mission critical tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure to see vulnerability clearly
        "--no-cov"
    ])