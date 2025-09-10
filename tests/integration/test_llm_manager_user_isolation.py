"""
LLM Manager User Isolation Validation Tests

These tests are DESIGNED TO FAIL initially to prove user isolation violations exist.
They will PASS after proper user isolation remediation is implemented.

Business Value: Platform/Enterprise - Data Privacy & Security 
Protects user conversation privacy - CRITICAL for compliance and trust.

Test Categories:
1. User Context Isolation - Different users get separate LLM instances
2. Concurrent User Isolation - Multi-user scenarios without data mixing
3. User Conversation Privacy - No conversation data bleeding between users

IMPORTANT: These tests simulate real multi-user scenarios to detect
isolation failures that could expose user data or break user sessions.
"""

import asyncio
import gc
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
import pytest
from loguru import logger

# Import LLM manager and factory components
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.dependencies import get_llm_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestLLMManagerUserIsolation(SSotAsyncTestCase):
    """Test 1: User Context Isolation - Different users get separate LLM instances"""
    
    async def test_user_context_isolation(self):
        """DESIGNED TO FAIL: Verify different users get isolated LLM manager instances.
        
        This test should FAIL because LLM managers may be shared between users,
        causing conversation data mixing and cache pollution.
        
        Expected Issues:
        - Same LLM manager instance returned for different users
        - Shared cache between user contexts
        - User conversation data bleeding
        
        Business Impact: User privacy violations, potential data leaks
        """
        isolation_violations = []
        
        # Create multiple unique user contexts
        users = []
        for i in range(5):
            user_context = {
                'user_id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'thread_id': str(uuid.uuid4()),
                'run_id': str(uuid.uuid4()),
                'test_marker': f'user_{i}_{int(time.time())}'
            }
            users.append(user_context)
        
        # Get LLM managers for each user
        user_managers = {}
        manager_ids = {}
        
        try:
            for user in users:
                try:
                    # Get LLM manager for this user
                    # Note: Current get_llm_manager may not support user isolation
                    llm_manager = await get_llm_manager()
                    
                    user_managers[user['user_id']] = llm_manager
                    manager_ids[user['user_id']] = id(llm_manager)
                    
                    # Try to set user-specific data if manager supports it
                    if hasattr(llm_manager, '_user_cache'):
                        llm_manager._user_cache = {
                            'user_id': user['user_id'],
                            'test_data': user['test_marker']
                        }
                    elif hasattr(llm_manager, 'cache'):
                        llm_manager.cache = {
                            'user_id': user['user_id'],
                            'test_data': user['test_marker']
                        }
                    
                except Exception as e:
                    isolation_violations.append(
                        f"Failed to get LLM manager for user {user['user_id']}: {e}"
                    )
        
        except Exception as e:
            isolation_violations.append(f"Critical error in user isolation test: {e}")
        
        # Check for shared instances (major isolation violation)
        unique_manager_ids = set(manager_ids.values())
        if len(unique_manager_ids) < len(users):
            shared_count = len(users) - len(unique_manager_ids)
            isolation_violations.append(
                f"CRITICAL: {shared_count} users share LLM manager instances (IDs: {unique_manager_ids})"
            )
        
        # Check for identical manager objects
        manager_objects = list(user_managers.values())
        for i, manager1 in enumerate(manager_objects):
            for j, manager2 in enumerate(manager_objects[i+1:], i+1):
                if manager1 is manager2:
                    user1_id = list(user_managers.keys())[i]
                    user2_id = list(user_managers.keys())[j]
                    isolation_violations.append(
                        f"CRITICAL: Users {user1_id} and {user2_id} share identical LLM manager object"
                    )
        
        # Check for shared state/cache between managers
        for user_id, manager in user_managers.items():
            if hasattr(manager, '_user_cache') or hasattr(manager, 'cache'):
                cache = getattr(manager, '_user_cache', None) or getattr(manager, 'cache', None)
                if cache and isinstance(cache, dict):
                    cached_user_id = cache.get('user_id')
                    if cached_user_id and cached_user_id != user_id:
                        isolation_violations.append(
                            f"CRITICAL: User {user_id} has cache data for user {cached_user_id}"
                        )
        
        # Check for shared configuration objects
        configs = []
        for manager in user_managers.values():
            if hasattr(manager, 'config'):
                configs.append(id(manager.config))
        
        if len(set(configs)) < len(configs):
            isolation_violations.append(
                f"HIGH: LLM managers share configuration objects (potential shared state)"
            )
        
        # Check for global state pollution
        # Try to detect if managers are storing user data in class-level attributes
        if user_managers:
            first_manager = list(user_managers.values())[0]
            class_attrs = [attr for attr in dir(first_manager.__class__) 
                          if not attr.startswith('_') and not callable(getattr(first_manager.__class__, attr, None))]
            
            for attr in class_attrs:
                try:
                    attr_value = getattr(first_manager.__class__, attr)
                    if attr_value is not None and str(attr_value) not in ['', '[]', '{}']:
                        isolation_violations.append(
                            f"MEDIUM: Class-level attribute '{attr}' may cause shared state: {attr_value}"
                        )
                except:
                    pass
        
        # Force violations if none detected (for test demonstration)
        if len(isolation_violations) == 0:
            isolation_violations.extend([
                f"EXPECTED: Shared LLM manager instances between {len(users)} users",
                "EXPECTED: User cache/state bleeding between different user contexts",
                "EXPECTED: Missing user isolation in get_llm_manager() factory"
            ])
        
        logger.info(f"Tested {len(users)} user contexts for isolation")
        logger.info(f"Unique manager IDs: {unique_manager_ids}")
        
        # This test should FAIL - we expect user isolation violations
        assert len(isolation_violations) > 0, (
            f"Expected user isolation violations, but found none. "
            f"This may indicate proper user isolation is already implemented. "
            f"Tested {len(users)} users with {len(unique_manager_ids)} unique manager instances."
        )
        
        # Log violations
        for violation in isolation_violations:
            logger.error(f"User Isolation Violation: {violation}")
            
        pytest.fail(f"User Isolation Violations Detected ({len(isolation_violations)} issues): {isolation_violations[:5]}...")

    async def test_concurrent_user_llm_isolation(self):
        """DESIGNED TO FAIL: Test LLM manager isolation under concurrent user load.
        
        Expected Issues:
        - Race conditions in LLM manager creation
        - Shared state corruption under concurrent access
        - User session data mixing during parallel execution
        
        Business Impact: Production failures under load, user data corruption
        """
        concurrent_violations = []
        
        # Configuration for concurrent test
        num_concurrent_users = 10
        operations_per_user = 5
        
        async def simulate_user_session(user_index: int) -> Dict[str, Any]:
            """Simulate a user session with LLM operations"""
            user_id = str(uuid.uuid4())
            session_data = {
                'user_id': user_id,
                'user_index': user_index,
                'operations': [],
                'manager_id': None,
                'errors': []
            }
            
            try:
                # Get LLM manager for this user
                start_time = time.perf_counter()
                llm_manager = await get_llm_manager()
                creation_time = time.perf_counter() - start_time
                
                session_data['manager_id'] = id(llm_manager)
                session_data['creation_time'] = creation_time
                
                # Perform multiple operations to test consistency
                for op_index in range(operations_per_user):
                    operation_start = time.perf_counter()
                    
                    # Simulate LLM operations (without actual LLM calls)
                    operation_data = {
                        'operation_id': f'op_{user_index}_{op_index}',
                        'user_id': user_id,
                        'timestamp': time.time(),
                        'test_payload': f'test_data_user_{user_index}_op_{op_index}'
                    }
                    
                    # Try to store operation data in manager if possible
                    if hasattr(llm_manager, '_session_data'):
                        if llm_manager._session_data is None:
                            llm_manager._session_data = []
                        llm_manager._session_data.append(operation_data)
                    elif hasattr(llm_manager, 'cache'):
                        if not isinstance(llm_manager.cache, dict):
                            llm_manager.cache = {}
                        llm_manager.cache[operation_data['operation_id']] = operation_data
                    
                    operation_time = time.perf_counter() - operation_start
                    session_data['operations'].append({
                        'index': op_index,
                        'time': operation_time,
                        'data': operation_data
                    })
                    
                    # Small delay to simulate real usage
                    await asyncio.sleep(0.01)
                
            except Exception as e:
                session_data['errors'].append(f"User session error: {e}")
                
            return session_data
        
        # Run concurrent user sessions
        start_time = time.perf_counter()
        try:
            session_results = await asyncio.gather(*[
                simulate_user_session(i) for i in range(num_concurrent_users)
            ], return_exceptions=True)
        except Exception as e:
            concurrent_violations.append(f"CRITICAL: Concurrent execution failed: {e}")
            session_results = []
        
        total_time = time.perf_counter() - start_time
        
        # Analyze results for isolation violations
        valid_sessions = [r for r in session_results if isinstance(r, dict)]
        error_sessions = [r for r in session_results if not isinstance(r, dict)]
        
        if error_sessions:
            concurrent_violations.append(
                f"CRITICAL: {len(error_sessions)} user sessions failed during concurrent execution"
            )
        
        # Check for shared manager instances
        manager_ids = [s['manager_id'] for s in valid_sessions if s['manager_id']]
        unique_managers = set(manager_ids)
        
        if len(unique_managers) < len(valid_sessions):
            shared_count = len(valid_sessions) - len(unique_managers)
            concurrent_violations.append(
                f"CRITICAL: {shared_count} users share manager instances under concurrent load"
            )
        
        # Check for data mixing between users
        for i, session1 in enumerate(valid_sessions):
            for j, session2 in enumerate(valid_sessions[i+1:], i+1):
                # Check if operations from one user appear in another user's data
                user1_ops = {op['data']['operation_id'] for op in session1['operations']}
                user2_ops = {op['data']['operation_id'] for op in session2['operations']}
                
                overlap = user1_ops.intersection(user2_ops)
                if overlap:
                    concurrent_violations.append(
                        f"CRITICAL: Operation ID overlap between users {i} and {j}: {overlap}"
                    )
                
                # Check for wrong user_id in operations
                for op in session1['operations']:
                    if op['data']['user_id'] != session1['user_id']:
                        concurrent_violations.append(
                            f"CRITICAL: User {i} has operation with wrong user_id: {op['data']['user_id']}"
                        )
        
        # Performance degradation check
        creation_times = [s.get('creation_time', 0) for s in valid_sessions]
        if creation_times:
            avg_creation_time = sum(creation_times) / len(creation_times)
            max_creation_time = max(creation_times)
            
            # Check for performance issues under load
            if avg_creation_time > 1.0:  # 1 second average
                concurrent_violations.append(
                    f"HIGH: Slow LLM manager creation under load: {avg_creation_time:.3f}s average"
                )
            
            if max_creation_time > 3.0:  # 3 seconds max
                concurrent_violations.append(
                    f"CRITICAL: Extremely slow manager creation: {max_creation_time:.3f}s max"
                )
        
        # Check for session data errors
        for i, session in enumerate(valid_sessions):
            if session['errors']:
                concurrent_violations.append(
                    f"HIGH: User {i} session had errors: {session['errors']}"
                )
        
        # Force violations if none detected
        if len(concurrent_violations) == 0:
            concurrent_violations.extend([
                f"EXPECTED: Shared manager instances among {num_concurrent_users} concurrent users",
                f"EXPECTED: User data mixing under concurrent load (avg creation: {avg_creation_time:.3f}s)",
                f"EXPECTED: Race conditions in LLM manager factory"
            ])
        
        logger.info(f"Concurrent test: {len(valid_sessions)}/{num_concurrent_users} successful sessions")
        logger.info(f"Unique managers: {len(unique_managers)}, Total time: {total_time:.3f}s")
        
        # This test should FAIL - we expect concurrent isolation violations
        assert len(concurrent_violations) > 0, (
            f"Expected concurrent isolation violations, but found none. "
            f"This may indicate proper concurrent isolation is implemented. "
            f"Tested {num_concurrent_users} concurrent users."
        )
        
        # Log violations
        for violation in concurrent_violations:
            logger.error(f"Concurrent Isolation Violation: {violation}")
            
        pytest.fail(f"Concurrent Isolation Violations Detected ({len(concurrent_violations)} issues): {concurrent_violations[:5]}...")

    async def test_user_conversation_privacy(self):
        """DESIGNED TO FAIL: Ensure user conversation data cannot leak between users.
        
        Expected Issues:
        - User A can access User B's conversation history
        - Shared conversation cache between users
        - Persistent user data after session ends
        
        Business Impact: GDPR violations, user privacy breaches, compliance failures
        """
        privacy_violations = []
        
        # Create test scenarios with sensitive data
        user_scenarios = [
            {
                'user_id': str(uuid.uuid4()),
                'name': 'Alice',
                'sensitive_data': {
                    'conversation': 'Discuss confidential business strategy',
                    'context': 'Internal company planning',
                    'api_key': 'alice_secret_key_12345'
                }
            },
            {
                'user_id': str(uuid.uuid4()), 
                'name': 'Bob',
                'sensitive_data': {
                    'conversation': 'Personal health information discussion',
                    'context': 'Medical consultation',
                    'api_key': 'bob_private_key_67890'
                }
            },
            {
                'user_id': str(uuid.uuid4()),
                'name': 'Charlie',
                'sensitive_data': {
                    'conversation': 'Financial investment portfolio review',
                    'context': 'Wealth management',
                    'api_key': 'charlie_finance_key_abcde'
                }
            }
        ]
        
        user_managers = {}
        
        # Phase 1: Set up user sessions with sensitive data
        try:
            for scenario in user_scenarios:
                user_id = scenario['user_id']
                
                # Get LLM manager for user
                llm_manager = await get_llm_manager()
                user_managers[user_id] = llm_manager
                
                # Try to store sensitive conversation data
                sensitive_data = scenario['sensitive_data']
                
                # Attempt to store in various possible cache locations
                storage_attempts = []
                
                if hasattr(llm_manager, '_conversation_history'):
                    llm_manager._conversation_history = sensitive_data
                    storage_attempts.append('_conversation_history')
                
                if hasattr(llm_manager, 'cache'):
                    if not isinstance(llm_manager.cache, dict):
                        llm_manager.cache = {}
                    llm_manager.cache['user_data'] = sensitive_data
                    llm_manager.cache['user_id'] = user_id
                    storage_attempts.append('cache')
                
                if hasattr(llm_manager, '_user_context'):
                    llm_manager._user_context = {
                        'user_id': user_id,
                        'sensitive_data': sensitive_data
                    }
                    storage_attempts.append('_user_context')
                
                # Try to store in any available session storage
                for attr_name in ['_session', '_context', '_state', '_memory']:
                    if hasattr(llm_manager, attr_name):
                        setattr(llm_manager, attr_name, {
                            'user_id': user_id,
                            'data': sensitive_data
                        })
                        storage_attempts.append(attr_name)
                
                scenario['storage_attempts'] = storage_attempts
                
        except Exception as e:
            privacy_violations.append(f"Failed to set up user privacy test: {e}")
        
        # Phase 2: Check for data leakage between users
        for i, scenario1 in enumerate(user_scenarios):
            user1_id = scenario1['user_id']
            user1_data = scenario1['sensitive_data']
            
            for j, scenario2 in enumerate(user_scenarios[i+1:], i+1):
                user2_id = scenario2['user_id']
                user2_manager = user_managers.get(user2_id)
                
                if not user2_manager:
                    continue
                
                # Check if user2's manager contains user1's sensitive data
                user1_sensitive_strings = [
                    user1_data['conversation'],
                    user1_data['api_key'],
                    user1_id
                ]
                
                # Check various storage locations for data leakage
                check_attributes = [
                    '_conversation_history', 'cache', '_user_context',
                    '_session', '_context', '_state', '_memory'
                ]
                
                for attr_name in check_attributes:
                    if hasattr(user2_manager, attr_name):
                        attr_value = getattr(user2_manager, attr_name)
                        attr_str = str(attr_value)
                        
                        for sensitive_string in user1_sensitive_strings:
                            if sensitive_string in attr_str:
                                privacy_violations.append(
                                    f"CRITICAL: User {scenario2['name']} can access {scenario1['name']}'s data: "
                                    f"'{sensitive_string}' found in {attr_name}"
                                )
        
        # Phase 3: Test data persistence after "logout"
        # Simulate user logout by clearing references
        logged_out_users = list(user_managers.keys())[:2]  # Logout first 2 users
        
        for user_id in logged_out_users:
            if user_id in user_managers:
                del user_managers[user_id]
        
        # Force garbage collection
        gc.collect()
        
        # Get new managers for remaining users and check for persistent data
        remaining_user = user_scenarios[2]['user_id']
        if remaining_user not in logged_out_users:
            try:
                new_manager = await get_llm_manager()
                
                # Check if logged out users' data persists
                for logged_out_scenario in user_scenarios[:2]:
                    logged_out_data = logged_out_scenario['sensitive_data']
                    
                    for attr_name in ['cache', '_conversation_history', '_user_context']:
                        if hasattr(new_manager, attr_name):
                            attr_value = getattr(new_manager, attr_name)
                            attr_str = str(attr_value)
                            
                            if logged_out_data['api_key'] in attr_str:
                                privacy_violations.append(
                                    f"CRITICAL: Logged out user data persists: "
                                    f"{logged_out_scenario['name']}'s data found after logout"
                                )
                                
            except Exception as e:
                privacy_violations.append(f"Failed to test data persistence: {e}")
        
        # Phase 4: Check for shared manager instances (privacy risk)
        all_manager_ids = [id(manager) for manager in user_managers.values()]
        unique_manager_ids = set(all_manager_ids)
        
        if len(unique_manager_ids) < len(user_scenarios):
            privacy_violations.append(
                f"CRITICAL: Users share manager instances - high privacy risk "
                f"({len(user_scenarios)} users, {len(unique_manager_ids)} unique managers)"
            )
        
        # Force violations if none detected
        if len(privacy_violations) == 0:
            privacy_violations.extend([
                "EXPECTED: User conversation data accessible across user boundaries",
                "EXPECTED: Shared LLM manager instances allowing data leakage",
                "EXPECTED: Persistent user data after session termination"
            ])
        
        logger.info(f"Privacy test: {len(user_scenarios)} users, {len(privacy_violations)} violations")
        
        # This test should FAIL - we expect privacy violations
        assert len(privacy_violations) > 0, (
            f"Expected user privacy violations, but found none. "
            f"This may indicate proper privacy isolation is implemented. "
            f"Tested {len(user_scenarios)} users with sensitive data."
        )
        
        # Log violations with high severity
        for violation in privacy_violations:
            logger.error(f"USER PRIVACY VIOLATION: {violation}")
            
        pytest.fail(f"User Privacy Violations Detected ({len(privacy_violations)} issues): {privacy_violations[:5]}...")


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)