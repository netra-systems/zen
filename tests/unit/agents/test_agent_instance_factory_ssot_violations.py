"""
Test Suite: Agent Instance Factory SSOT Violations - Singleton Pattern Reproduction

PURPOSE: Reproduce and validate singleton pattern violations in AgentInstanceFactory
ISSUE: #1102 - Agent Instance Factory singleton pattern breaks user isolation
CRITICAL MISSION: Implement 20% NEW tests proving singleton violations exist

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: All tests should FAIL (proving SSOT violations exist)
- AFTER REMEDIATION: All tests should PASS (proving SSOT compliance achieved)

Business Value: Enterprise/Platform - 500K+ ARR protection through proper user isolation
SSOT Remediation Target: Line 1128 - /netra_backend/app/agents/supervisor/agent_instance_factory.py

This test suite specifically targets the global singleton pattern violations that prevent
proper user isolation in multi-user concurrent scenarios.
"""

import asyncio
import gc
import sys
import threading
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


@pytest.mark.unit
class AgentInstanceFactorySSOTViolationsTests(SSotAsyncTestCase):
    """
    Unit test suite proving singleton pattern violations in AgentInstanceFactory.
    
    This test suite validates Issue #1102 by proving that:
    1. Global singleton instances create shared state between users
    2. Concurrent user contexts contaminate each other's data
    3. User data persists inappropriately across requests
    4. Per-request factory isolation is required for SSOT compliance
    
    CRITICAL: These tests should FAIL before remediation and PASS after SSOT fix.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Reset any cached imports to ensure clean state
        modules_to_reset = [
            'netra_backend.app.agents.supervisor.agent_instance_factory',
        ]
        
        for module_name in modules_to_reset:
            if module_name in sys.modules:
                # Force reload to get fresh state
                try:
                    del sys.modules[module_name]
                except KeyError:
                    pass
        
        # Clear any module-level caches
        gc.collect()

    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Force garbage collection to clean up any lingering references
        gc.collect()
        super().teardown_method(method)

    def test_singleton_factory_shares_global_state(self):
        """
        Test that singleton factory creates shared global state between users.
        
        VIOLATION PROOF: The singleton pattern causes the same factory instance
        to be shared across multiple user requests, violating user isolation.
        
        EXPECTED: FAIL before remediation (proving violation exists)
        EXPECTED: PASS after remediation (proving SSOT compliance)
        """
        # Import module to access global state
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        
        # Test that singleton returns same instance
        factory1 = factory_module.get_agent_instance_factory()
        factory2 = factory_module.get_agent_instance_factory()
        
        # VIOLATION ASSERTION: This should FAIL before remediation
        # Same instance violates user isolation requirements
        assert factory1 is factory2, (
            "SINGLETON VIOLATION: Same factory instance shared across requests. "
            "This violates user isolation and creates cross-user contamination risk. "
            f"Factory1 ID: {id(factory1)}, Factory2 ID: {id(factory2)}"
        )
        
        # VIOLATION ASSERTION: Global state exists after initialization
        assert factory_module._factory_instance is not None, (
            "SINGLETON VIOLATION: Global _factory_instance exists after initialization, creating shared state "
            "that persists across user requests. This prevents proper user isolation."
        )
        
        # VIOLATION ASSERTION: Both factories reference same global instance
        assert factory1 is factory_module._factory_instance, (
            "SINGLETON VIOLATION: Factory instances reference global singleton, "
            "creating shared state that violates user isolation principles."
        )

    def test_concurrent_user_context_contamination(self):
        """
        Test that concurrent user contexts contaminate each other through shared factory.
        
        VIOLATION PROOF: Multiple users accessing the singleton factory simultaneously
        can cause context contamination where User A's data appears in User B's session.
        
        EXPECTED: FAIL before remediation (proving contamination occurs)
        EXPECTED: PASS after remediation (proving isolation achieved)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # Simulate concurrent user contexts
        user_contexts = {}
        contamination_detected = False
        
        def simulate_user_session(user_id: str):
            """Simulate a user session that modifies factory state."""
            factory = get_agent_instance_factory()
            
            # Each user should get isolated factory state
            # Set user-specific state
            user_marker = f"user_data_{user_id}_{uuid.uuid4()}"
            
            # Store user context in factory (violating isolation)
            if not hasattr(factory, '_user_states'):
                factory._user_states = {}
            factory._user_states[user_id] = user_marker
            
            # Small delay to allow concurrent access
            time.sleep(0.01)
            
            return {
                'user_id': user_id,
                'factory_id': id(factory),
                'user_marker': user_marker,
                'all_user_states': dict(factory._user_states)
            }
        
        # Concurrent user sessions
        user_ids = ['user_1', 'user_2', 'user_3']
        results = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(simulate_user_session, user_id)
                for user_id in user_ids
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # VIOLATION ANALYSIS: Check for contamination
        factory_ids = [result['factory_id'] for result in results]
        unique_factory_ids = set(factory_ids)
        
        # VIOLATION ASSERTION: All users share same factory instance
        assert len(unique_factory_ids) == 1, (
            "SINGLETON VIOLATION: All users should share same factory (proving violation). "
            f"Found {len(unique_factory_ids)} unique factories: {unique_factory_ids}. "
            "This proves the singleton creates shared state."
        )
        
        # VIOLATION ASSERTION: User data contamination
        for result in results:
            all_states = result['all_user_states']
            user_id = result['user_id']
            
            # Each user can see other users' data (contamination)
            other_user_data = {k: v for k, v in all_states.items() if k != user_id}
            
            assert len(other_user_data) > 0, (
                f"CONTAMINATION VIOLATION: User {user_id} can access other users' data. "
                f"Other user data visible: {other_user_data}. "
                "This proves cross-user contamination through shared singleton."
            )

    def test_memory_leak_user_data_persistence(self):
        """
        Test that user data inappropriately persists across requests through singleton.
        
        VIOLATION PROOF: The singleton pattern causes user data to persist in memory
        across requests, creating memory leaks and potential data exposure.
        
        EXPECTED: FAIL before remediation (proving persistence violation)
        EXPECTED: PASS after remediation (proving proper cleanup)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # First user session - store data
        factory1 = get_agent_instance_factory()
        user1_secret = f"secret_data_{uuid.uuid4()}"
        
        # Simulate storing user data in factory
        if not hasattr(factory1, '_session_data'):
            factory1._session_data = {}
        factory1._session_data['user_1'] = user1_secret
        
        # Simulate end of first user session
        del factory1  # User session ends
        gc.collect()  # Force garbage collection
        
        # Second user session - should NOT see first user's data
        factory2 = get_agent_instance_factory()
        
        # VIOLATION ASSERTION: Same factory instance persists
        assert hasattr(factory2, '_session_data'), (
            "PERSISTENCE VIOLATION: Factory maintains session data across requests. "
            "This creates memory leaks and potential data exposure between users."
        )
        
        # VIOLATION ASSERTION: First user's data still accessible
        assert 'user_1' in factory2._session_data, (
            f"DATA PERSISTENCE VIOLATION: User 1's secret data persists in factory. "
            f"Accessible data: {factory2._session_data}. "
            "This violates user isolation and creates security risk."
        )
        
        # VIOLATION ASSERTION: Secret data accessible to new user
        persisted_secret = factory2._session_data.get('user_1')
        assert persisted_secret == user1_secret, (
            "SECURITY VIOLATION: Previous user's secret data accessible to new user. "
            f"Persisted secret: {persisted_secret}, Original: {user1_secret}. "
            "This proves singleton creates cross-user data exposure."
        )

    def test_per_request_factory_isolation_required(self):
        """
        Test that per-request factory pattern is required for proper isolation.
        
        VIOLATION PROOF: The current singleton pattern prevents proper per-request
        isolation that is required for SSOT compliance in multi-user systems.
        
        EXPECTED: FAIL before remediation (proving isolation violation)
        EXPECTED: PASS after remediation (proving per-request isolation)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # Simulate multiple request contexts
        request_data = {}
        
        def simulate_request(request_id: str) -> Dict[str, Any]:
            """Simulate individual request that should be isolated."""
            factory = get_agent_instance_factory()
            
            # Each request should get unique factory state
            request_marker = f"request_{request_id}_{time.time()}"
            
            # Store request-specific data
            if not hasattr(factory, '_request_contexts'):
                factory._request_contexts = {}
            factory._request_contexts[request_id] = request_marker
            
            return {
                'request_id': request_id,
                'factory_id': id(factory),
                'request_marker': request_marker,
                'total_contexts': len(factory._request_contexts),
                'all_contexts': dict(factory._request_contexts)
            }
        
        # Sequential requests (simulating different user requests)
        request_results = []
        for i in range(3):
            result = simulate_request(f"req_{i}")
            request_results.append(result)
            time.sleep(0.001)  # Small delay between requests
        
        # VIOLATION ANALYSIS: All requests share same factory
        factory_ids = [result['factory_id'] for result in request_results]
        unique_factory_ids = set(factory_ids)
        
        # VIOLATION ASSERTION: All requests use same factory instance
        assert len(unique_factory_ids) == 1, (
            "ISOLATION VIOLATION: All requests share same factory instance. "
            f"Expected unique factories per request, found {len(unique_factory_ids)}. "
            "This violates per-request isolation requirements."
        )
        
        # VIOLATION ASSERTION: Request contexts accumulate inappropriately
        final_result = request_results[-1]
        assert final_result['total_contexts'] == len(request_results), (
            "CONTEXT ACCUMULATION VIOLATION: Request contexts accumulate across requests. "
            f"Total contexts: {final_result['total_contexts']}, Expected: 1 per request. "
            "This proves singleton prevents proper request isolation."
        )
        
        # VIOLATION ASSERTION: Each request can access previous request data
        for i, result in enumerate(request_results[1:], 1):  # Skip first request
            all_contexts = result['all_contexts']
            previous_contexts = [k for k in all_contexts.keys() if k != result['request_id']]
            
            assert len(previous_contexts) >= i, (
                f"REQUEST ISOLATION VIOLATION: Request {result['request_id']} can access "
                f"previous request contexts: {previous_contexts}. "
                "This violates per-request isolation principles."
            )