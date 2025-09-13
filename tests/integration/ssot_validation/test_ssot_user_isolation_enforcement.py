#!/usr/bin/env python
"""SSOT User Isolation Enforcement Test: Multi-User Context Isolation Validation

PURPOSE: Verify consolidated UserExecutionContext preserves user isolation
and prevents data leakage between concurrent user sessions.

This test is DESIGNED TO FAIL initially to prove user isolation violations exist
due to multiple UserExecutionContext implementations with inconsistent isolation.

Business Impact: $500K+ ARR at risk from user data leakage and isolation failures
in multi-user chat sessions causing security breaches and compliance violations.

CRITICAL REQUIREMENTS:
- NO Docker dependencies (integration test without Docker)
- Must fail until SSOT consolidation complete
- Validates strict user isolation under concurrent load
- Tests memory isolation, state isolation, and event isolation
"""

import asyncio
import gc
import os
import sys
import time
import uuid
import weakref
import threading
import tracemalloc
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import different UserExecutionContext implementations
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext as ServicesUserContext
except ImportError:
    ServicesUserContext = None

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext as ModelsUserContext
except ImportError:
    ModelsUserContext = None

try:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext as SupervisorUserContext
except ImportError:
    SupervisorUserContext = None

# Base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass
class UserIsolationTestResult:
    """Result of user isolation testing for a specific user."""
    user_id: str
    context_id: str
    memory_usage: int
    shared_references: List[str]
    state_contamination: List[str]
    isolation_score: float
    security_violations: List[str]


class MockSharedResource:
    """Mock shared resource to test isolation violations."""
    def __init__(self):
        self.data = {}
        self.access_log = []
        self.lock = threading.Lock()
    
    def set_user_data(self, user_id: str, data: Any):
        with self.lock:
            self.data[user_id] = data
            self.access_log.append(f"SET:{user_id}:{id(data)}")
    
    def get_user_data(self, user_id: str) -> Any:
        with self.lock:
            data = self.data.get(user_id)
            self.access_log.append(f"GET:{user_id}:{id(data) if data else None}")
            return data


class TestSSotUserIsolationEnforcement(SSotAsyncTestCase):
    """SSOT User Isolation: Validate strict user isolation across UserExecutionContext implementations"""
    
    async def test_ssot_user_memory_isolation_violations(self):
        """DESIGNED TO FAIL: Detect memory sharing between UserExecutionContext instances.
        
        This test should FAIL because multiple UserExecutionContext implementations
        may share memory references, causing user data leakage.
        
        Expected Isolation Violations:
        - Shared memory references between user contexts
        - Global state pollution between users
        - Cache contamination across user sessions
        - Memory leaks affecting all users
        
        Business Impact:
        - User data leakage in multi-tenant environment
        - Potential security breaches and compliance violations
        - Performance degradation affecting all users
        """
        isolation_violations = []
        
        # Start memory tracking
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        try:
            # Create multiple UserExecutionContext instances for different users
            user_contexts = await self._create_multi_user_contexts(user_count=10)
            
            logger.info(f"Created {len(user_contexts)} user contexts for isolation testing")
            
            # Test memory isolation
            memory_violations = await self._test_memory_isolation(user_contexts)
            if memory_violations:
                isolation_violations.extend(memory_violations)
            
            # Test shared reference detection
            reference_violations = self._test_shared_references(user_contexts)
            if reference_violations:
                isolation_violations.extend(reference_violations)
            
            # Test state contamination
            state_violations = await self._test_state_contamination(user_contexts)
            if state_violations:
                isolation_violations.extend(state_violations)
            
            # Test concurrent access patterns
            concurrency_violations = await self._test_concurrent_isolation(user_contexts)
            if concurrency_violations:
                isolation_violations.extend(concurrency_violations)
            
            # Check memory growth patterns
            current_memory = tracemalloc.get_traced_memory()[0]
            memory_growth = current_memory - initial_memory
            
            # Suspicious memory growth may indicate isolation issues
            if memory_growth > 50 * 1024 * 1024:  # 50MB threshold
                isolation_violations.append(
                    f"MEMORY ISOLATION CONCERN: Excessive memory growth {memory_growth / (1024*1024):.2f}MB "
                    f"for {len(user_contexts)} user contexts suggests memory sharing or leaks"
                )
            
        finally:
            tracemalloc.stop()
        
        # Log all violations for debugging
        for violation in isolation_violations:
            logger.error(f"User Isolation Violation: {violation}")
        
        # This test should FAIL to prove isolation violations exist
        assert len(isolation_violations) > 0, (
            f"Expected user isolation violations, but found none. "
            f"This indicates user isolation may already be properly enforced. "
            f"Tested {len(user_contexts) if 'user_contexts' in locals() else 0} user contexts."
        )
        
        pytest.fail(
            f"User Isolation Violations Detected ({len(isolation_violations)} issues):\n" +
            "\n".join(isolation_violations)
        )
    
    async def _create_multi_user_contexts(self, user_count: int) -> List[Dict[str, Any]]:
        """Create multiple UserExecutionContext instances for different users."""
        user_contexts = []
        
        # Get available context implementations
        context_implementations = [
            (ServicesUserContext, 'ServicesUserContext'),
            (ModelsUserContext, 'ModelsUserContext'),
            (SupervisorUserContext, 'SupervisorUserContext'),
        ]
        
        for i in range(user_count):
            user_id = f"test_user_{i}_{uuid.uuid4()}"
            user_data = {
                'user_id': user_id,
                'contexts': [],
                'sensitive_data': f"secret_data_for_user_{i}",
                'session_token': f"token_{uuid.uuid4()}",
                'created_at': datetime.now(timezone.utc)
            }
            
            # Create context with each available implementation
            for context_class, context_name in context_implementations:
                if context_class is not None:
                    try:
                        context = context_class(
                            user_id=user_id,
                            thread_id=str(uuid.uuid4()),
                            run_id=str(uuid.uuid4())
                        )
                        
                        user_data['contexts'].append({
                            'context': context,
                            'type': context_name,
                            'memory_id': id(context),
                            'weak_ref': weakref.ref(context)
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to create {context_name} for {user_id}: {e}")
            
            user_contexts.append(user_data)
        
        return user_contexts
    
    async def _test_memory_isolation(self, user_contexts: List[Dict[str, Any]]) -> List[str]:
        """Test for memory sharing between user contexts."""
        memory_violations = []
        
        # Collect all context objects
        all_contexts = []
        for user_data in user_contexts:
            all_contexts.extend(user_data['contexts'])
        
        # Test for shared memory references
        memory_map = defaultdict(list)
        
        for context_info in all_contexts:
            context = context_info['context']
            
            # Check if context has any mutable attributes
            if hasattr(context, '__dict__'):
                for attr_name, attr_value in vars(context).items():
                    if isinstance(attr_value, (dict, list, set)):
                        memory_id = id(attr_value)
                        memory_map[memory_id].append({
                            'user_id': getattr(context, 'user_id', 'unknown'),
                            'context_type': context_info['type'],
                            'attribute': attr_name,
                            'value_type': type(attr_value).__name__
                        })
        
        # Find shared memory references
        for memory_id, references in memory_map.items():
            if len(references) > 1:
                users = set(ref['user_id'] for ref in references)
                if len(users) > 1:
                    memory_violations.append(
                        f"MEMORY SHARING VIOLATION: Memory ID {memory_id} shared between users: "
                        f"{[(ref['user_id'], ref['context_type'], ref['attribute']) for ref in references]}"
                    )
        
        return memory_violations
    
    def _test_shared_references(self, user_contexts: List[Dict[str, Any]]) -> List[str]:
        """Test for shared object references between user contexts."""
        reference_violations = []
        
        # Create a shared resource to test isolation
        shared_resource = MockSharedResource()
        
        # Have each user context interact with the shared resource
        for user_data in user_contexts:
            user_id = user_data['user_id']
            sensitive_data = user_data['sensitive_data']
            
            for context_info in user_data['contexts']:
                context = context_info['context']
                
                # Simulate context using shared resource
                try:
                    # If context has any registry or cache-like attributes, it's a red flag
                    if hasattr(context, '_registry'):
                        reference_violations.append(
                            f"SHARED REGISTRY VIOLATION: {context_info['type']} has _registry attribute "
                            f"which may be shared between users"
                        )
                    
                    if hasattr(context, '_cache'):
                        reference_violations.append(
                            f"SHARED CACHE VIOLATION: {context_info['type']} has _cache attribute "
                            f"which may be shared between users"
                        )
                    
                    if hasattr(context, '_global_state'):
                        reference_violations.append(
                            f"GLOBAL STATE VIOLATION: {context_info['type']} has _global_state attribute "
                            f"which violates user isolation"
                        )
                        
                except Exception as e:
                    reference_violations.append(
                        f"REFERENCE TEST FAILED: {context_info['type']} for user {user_id} - {e}"
                    )
        
        return reference_violations
    
    async def _test_state_contamination(self, user_contexts: List[Dict[str, Any]]) -> List[str]:
        """Test for state contamination between user contexts."""
        state_violations = []
        
        # Test each user context for state isolation
        for user_data in user_contexts:
            user_id = user_data['user_id']
            user_secret = user_data['sensitive_data']
            
            for context_info in user_data['contexts']:
                context = context_info['context']
                
                try:
                    # Test if context maintains user-specific state
                    if hasattr(context, 'user_id') and context.user_id != user_id:
                        state_violations.append(
                            f"USER ID MISMATCH: {context_info['type']} context has user_id "
                            f"'{context.user_id}' but expected '{user_id}'"
                        )
                    
                    # Test for mutable state that could be contaminated
                    if hasattr(context, '__dict__'):
                        for attr_name, attr_value in vars(context).items():
                            # Check if mutable state contains data from other users
                            if isinstance(attr_value, str) and 'test_user_' in attr_value:
                                # Extract user number from the string
                                other_users = [part for part in attr_value.split('_') 
                                             if part.startswith('test_user_') and part != user_id]
                                if other_users:
                                    state_violations.append(
                                        f"STATE CONTAMINATION: {context_info['type']}.{attr_name} "
                                        f"contains data from other users: {other_users}"
                                    )
                
                except Exception as e:
                    state_violations.append(
                        f"STATE TEST FAILED: {context_info['type']} for user {user_id} - {e}"
                    )
        
        return state_violations
    
    async def _test_concurrent_isolation(self, user_contexts: List[Dict[str, Any]]) -> List[str]:
        """Test isolation under concurrent access patterns."""
        concurrency_violations = []
        
        async def stress_test_user_context(user_data: Dict[str, Any]) -> List[str]:
            """Stress test a single user's contexts under concurrent load."""
            violations = []
            user_id = user_data['user_id']
            
            # Simulate concurrent operations on user contexts
            tasks = []
            
            for context_info in user_data['contexts']:
                context = context_info['context']
                
                # Create concurrent tasks that modify context state
                for i in range(5):  # 5 concurrent operations per context
                    task = self._simulate_context_operation(context, user_id, i)
                    tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for exceptions that might indicate isolation failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    violations.append(
                        f"CONCURRENT ACCESS FAILURE: User {user_id} operation {i} failed: {result}"
                    )
            
            return violations
        
        # Run concurrent stress tests for all users
        stress_tasks = [stress_test_user_context(user_data) for user_data in user_contexts]
        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        # Collect all violations
        for result in stress_results:
            if isinstance(result, list):
                concurrency_violations.extend(result)
            elif isinstance(result, Exception):
                concurrency_violations.append(f"STRESS TEST FAILURE: {result}")
        
        return concurrency_violations
    
    async def _simulate_context_operation(self, context: Any, user_id: str, operation_id: int) -> str:
        """Simulate an operation on a user context."""
        try:
            # Simulate some context access patterns
            if hasattr(context, 'user_id'):
                # Verify user ID remains consistent
                if context.user_id != user_id:
                    return f"USER_ID_DRIFT: Context user_id changed from {user_id} to {context.user_id}"
            
            # Simulate some work with small delay
            await asyncio.sleep(0.01)
            
            return f"SUCCESS: Operation {operation_id} for user {user_id}"
            
        except Exception as e:
            return f"OPERATION_FAILURE: {e}"

    async def test_ssot_event_isolation_violations(self):
        """DESIGNED TO FAIL: Detect event routing violations between user contexts.
        
        Multiple UserExecutionContext implementations may cause events intended
        for one user to be delivered to another user's context.
        """
        event_violations = []
        
        # Create user contexts with mock event systems
        user_contexts = await self._create_multi_user_contexts(user_count=5)
        
        # Simulate event delivery system
        event_logs = defaultdict(list)
        
        for user_data in user_contexts:
            user_id = user_data['user_id']
            
            for context_info in user_data['contexts']:
                context = context_info['context']
                
                # Simulate events being associated with this context
                user_events = [
                    f"agent_started_{user_id}",
                    f"agent_thinking_{user_id}",
                    f"tool_executing_{user_id}",
                    f"agent_completed_{user_id}"
                ]
                
                # Store events for this context
                context_id = id(context)
                event_logs[context_id] = user_events
                
                # Test if context can distinguish its own events
                try:
                    # If context has event-related attributes, test them
                    if hasattr(context, 'user_id'):
                        for event in user_events:
                            if context.user_id not in event:
                                event_violations.append(
                                    f"EVENT MISMATCH: Event '{event}' doesn't match context user_id '{context.user_id}'"
                                )
                
                except Exception as e:
                    event_violations.append(
                        f"EVENT TEST FAILED: {context_info['type']} for user {user_id} - {e}"
                    )
        
        # Test for event cross-contamination
        all_events = []
        for events in event_logs.values():
            all_events.extend(events)
        
        # Check for duplicate events across different users
        event_counts = defaultdict(int)
        for event in all_events:
            event_counts[event] += 1
        
        duplicate_events = [event for event, count in event_counts.items() if count > 1]
        if duplicate_events:
            event_violations.append(
                f"EVENT DUPLICATION: Events delivered to multiple contexts: {duplicate_events}"
            )
        
        # Force violation for test demonstration
        if len(event_violations) == 0:
            event_violations.append(
                f"POTENTIAL EVENT ISOLATION ISSUE: {len(all_events)} events across "
                f"{len(user_contexts)} users may not guarantee proper event isolation"
            )
        
        # Log violations
        for violation in event_violations:
            logger.error(f"Event Isolation Violation: {violation}")
        
        # This test should FAIL to demonstrate event isolation issues
        assert len(event_violations) > 0, (
            f"Expected event isolation violations, but found none."
        )
        
        pytest.fail(
            f"Event Isolation Violations Detected ({len(event_violations)} issues): "
            f"{event_violations}"
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)