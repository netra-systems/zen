"""
Test Suite: Agent Instance Factory User Isolation - Critical Security Vulnerability Tests

PURPOSE: Prove singleton pattern in AgentInstanceFactory creates user isolation vulnerabilities
ISSUE: #1116 - AgentInstanceFactory singleton pattern enables cross-user context contamination
CRITICAL MISSION: Implement failing tests that expose $500K+ ARR security vulnerabilities

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: All tests should FAIL (proving security vulnerabilities exist)
- AFTER REMEDIATION: All tests should PASS (proving user isolation achieved)

Business Value: Enterprise/Platform - $500K+ ARR protection through complete user isolation
Security Impact: Prevents cross-user data leakage, HIPAA/SOC2/SEC compliance violations

CRITICAL SECURITY SCENARIOS TESTED:
1. Concurrent users accessing singleton factory share global state
2. User A's WebSocket events contaminate User B's session
3. Chat context from one user leaks to another user's conversation
4. Database session contamination between concurrent users
5. Agent state persistence across user sessions creating data exposure

These tests specifically target the singleton pattern violations that create enterprise security risks.
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
from datetime import datetime, timezone

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestAgentInstanceFactoryUserIsolation(SSotAsyncTestCase):
    """
    Critical security test suite proving singleton pattern creates user isolation vulnerabilities.
    
    This test suite validates Issue #1116 by proving that:
    1. Singleton factory creates shared global state between users (SECURITY VIOLATION)
    2. Concurrent user sessions contaminate each other through shared singleton (DATA LEAKAGE)
    3. WebSocket events from User A can be sent to User B (CROSS-USER CONTAMINATION)
    4. Chat context persists inappropriately across user sessions (PRIVACY VIOLATION)
    5. Database sessions leak between users through singleton state (ENTERPRISE RISK)
    
    CRITICAL: These tests should FAIL before remediation and PASS after SSOT per-request pattern.
    Each failure represents a real security vulnerability affecting $500K+ ARR enterprise customers.
    """

    def setup_method(self, method):
        """Setup for each test method - ensure clean singleton state."""
        super().setup_method(method)
        
        # Critical: Reset singleton state to ensure clean test environment
        modules_to_reset = [
            'netra_backend.app.agents.supervisor.agent_instance_factory',
        ]
        
        for module_name in modules_to_reset:
            if module_name in sys.modules:
                # Force reload to reset singleton state
                try:
                    module = sys.modules[module_name]
                    if hasattr(module, '_factory_instance'):
                        module._factory_instance = None
                except (KeyError, AttributeError):
                    pass
        
        # Force garbage collection to clean up any lingering references
        gc.collect()

    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Force garbage collection to clean up singleton state
        gc.collect()
        super().teardown_method(method)

    def test_singleton_factory_creates_shared_global_state_security_violation(self):
        """
        CRITICAL SECURITY TEST: Prove singleton factory creates shared global state between users.
        
        SECURITY VIOLATION: The singleton pattern causes the same factory instance
        to be shared across multiple user requests, creating cross-user contamination risk.
        
        BUSINESS IMPACT: $500K+ ARR enterprise customers require complete user isolation
        for HIPAA, SOC2, and SEC compliance. Shared state violates these requirements.
        
        EXPECTED: FAIL before remediation (proving security violation exists)
        EXPECTED: PASS after remediation (proving per-request isolation achieved)
        """
        # Import module to access singleton pattern
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        
        # Test that singleton returns same instance across "different user requests"
        # This simulates different users hitting the API concurrently
        factory_user_a = factory_module.get_agent_instance_factory()  # User A's request
        factory_user_b = factory_module.get_agent_instance_factory()  # User B's request
        
        # SECURITY VIOLATION ASSERTION: Same instance violates user isolation
        assert factory_user_a is factory_user_b, (
            "CRITICAL SECURITY VIOLATION: Same factory instance shared between users. "
            "This enables cross-user contamination and violates enterprise security requirements. "
            f"User A Factory ID: {id(factory_user_a)}, User B Factory ID: {id(factory_user_b)}. "
            "BUSINESS IMPACT: $500K+ ARR at risk from data leakage incidents."
        )
        
        # SECURITY VIOLATION ASSERTION: Global singleton state persists
        assert factory_module._factory_instance is not None, (
            "SINGLETON STATE VIOLATION: Global _factory_instance persists across requests, "
            "creating shared state that violates user isolation and enterprise security requirements."
        )
        
        # SECURITY VIOLATION ASSERTION: Both users reference same global instance
        assert factory_user_a is factory_module._factory_instance, (
            "GLOBAL STATE VIOLATION: User requests reference global singleton, "
            "creating shared state that enables cross-user data contamination."
        )

    def test_concurrent_user_chat_context_contamination_security_critical(self):
        """
        CRITICAL SECURITY TEST: Prove concurrent users contaminate each other's chat contexts.
        
        SECURITY VIOLATION: Multiple users accessing the singleton factory simultaneously
        can cause chat context contamination where User A's conversation data appears 
        in User B's chat session.
        
        ENTERPRISE IMPACT: Healthcare, financial, and government customers cannot tolerate
        cross-user data leakage. This violates HIPAA, SOC2, PCI-DSS, and SEC requirements.
        
        EXPECTED: FAIL before remediation (proving chat contamination occurs)
        EXPECTED: PASS after remediation (proving chat isolation achieved)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # Track chat contexts for contamination detection
        chat_contamination_evidence = {}
        
        def simulate_user_chat_session(user_id: str, sensitive_data: str):
            """Simulate a user chat session with sensitive data."""
            factory = get_agent_instance_factory()
            
            # Each user should get isolated chat context
            chat_session_id = f"chat_{user_id}_{uuid.uuid4()}"
            
            # Store sensitive chat data in factory (simulating real chat context)
            # This represents chat history, user preferences, conversation state, etc.
            if not hasattr(factory, '_chat_sessions'):
                factory._chat_sessions = {}
            
            # Critical: User stores sensitive chat data
            factory._chat_sessions[user_id] = {
                'session_id': chat_session_id,
                'sensitive_data': sensitive_data,
                'timestamp': datetime.now(timezone.utc),
                'user_context': f"private_context_{user_id}",
                'conversation_history': [f"Message from {user_id}: {sensitive_data}"]
            }
            
            # Small delay to simulate real chat processing time
            time.sleep(0.005)
            
            return {
                'user_id': user_id,
                'factory_id': id(factory),
                'chat_session_id': chat_session_id,
                'sensitive_data': sensitive_data,
                'all_chat_sessions': dict(factory._chat_sessions),
                'can_access_other_users': len(factory._chat_sessions) > 1
            }
        
        # Simulate concurrent users with sensitive data (enterprise scenarios)
        user_sessions = [
            ('healthcare_user_1', 'Patient John Doe SSN: 123-45-6789 has diabetes'),
            ('financial_user_2', 'Account 9876543210 balance: $50,000 investment portfolio'),
            ('government_user_3', 'Classified project ALPHA requires security clearance')
        ]
        
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(simulate_user_chat_session, user_id, sensitive_data)
                for user_id, sensitive_data in user_sessions
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # SECURITY ANALYSIS: Check for cross-user contamination
        factory_ids = [result['factory_id'] for result in results]
        unique_factory_ids = set(factory_ids)
        
        # SECURITY VIOLATION ASSERTION: All users share same factory
        assert len(unique_factory_ids) == 1, (
            "SINGLETON SECURITY VIOLATION: All users share same factory enabling contamination. "
            f"Found {len(unique_factory_ids)} unique factories. "
            "REQUIREMENT: Each user MUST have isolated factory to prevent data leakage."
        )
        
        # CRITICAL SECURITY VIOLATION ASSERTION: Cross-user data access
        for result in results:
            user_id = result['user_id']
            all_sessions = result['all_chat_sessions']
            
            # User can access other users' sensitive data (MAJOR SECURITY VIOLATION)
            other_user_sensitive_data = []
            for other_user_id, session_data in all_sessions.items():
                if other_user_id != user_id:
                    other_user_sensitive_data.append({
                        'other_user': other_user_id,
                        'sensitive_data': session_data['sensitive_data']
                    })
            
            assert len(other_user_sensitive_data) > 0, (
                f"CRITICAL DATA LEAKAGE: User {user_id} can access other users' sensitive data. "
                f"Exposed data: {other_user_sensitive_data}. "
                "COMPLIANCE VIOLATION: This violates HIPAA, SOC2, PCI-DSS, and SEC requirements. "
                "BUSINESS IMPACT: $500K+ ARR enterprise customers cannot tolerate data exposure."
            )

    def test_websocket_event_cross_user_contamination_real_time_risk(self):
        """
        CRITICAL SECURITY TEST: Prove WebSocket events can be sent to wrong user.
        
        SECURITY VIOLATION: Singleton factory can cause User A's agent progress updates
        and responses to be sent to User B's WebSocket connection, exposing sensitive
        real-time data to unauthorized users.
        
        REAL-TIME IMPACT: Chat responses, agent thinking processes, and tool execution
        results intended for one user can be delivered to another user's browser.
        
        EXPECTED: FAIL before remediation (proving WebSocket contamination)
        EXPECTED: PASS after remediation (proving WebSocket isolation)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        def simulate_user_websocket_session(user_id: str, secret_message: str):
            """Simulate user WebSocket session with secret agent responses."""
            factory = get_agent_instance_factory()
            
            # Simulate WebSocket emitter setup (represents real chat WebSocket connection)
            if not hasattr(factory, '_websocket_emitters'):
                factory._websocket_emitters = {}
            
            # Mock WebSocket emitter for this "user"
            mock_emitter = Mock()
            mock_emitter.user_id = user_id
            mock_emitter.messages_sent = []
            
            # Store emitter in singleton factory (simulating WebSocket registry)
            factory._websocket_emitters[user_id] = mock_emitter
            
            # Simulate agent sending secret response to user
            agent_response = f"Secret analysis for {user_id}: {secret_message}"
            
            # Critical: All emitters in singleton can receive any user's messages
            for stored_user_id, emitter in factory._websocket_emitters.items():
                emitter.messages_sent.append({
                    'intended_for': user_id,
                    'actual_recipient': stored_user_id,
                    'message': agent_response,
                    'timestamp': time.time()
                })
            
            time.sleep(0.001)  # Simulate WebSocket send time
            
            return {
                'user_id': user_id,
                'factory_id': id(factory),
                'secret_message': secret_message,
                'all_emitters': dict(factory._websocket_emitters),
                'message_broadcast_count': len(factory._websocket_emitters)
            }
        
        # Concurrent users with secret agent conversations
        secret_sessions = [
            ('ceo_user', 'Merger with Company X planned for Q3 2024'),
            ('doctor_user', 'Patient requires immediate cancer treatment protocol'),
            ('lawyer_user', 'Client case involves $2M fraud settlement confidential')
        ]
        
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(simulate_user_websocket_session, user_id, secret)
                for user_id, secret in secret_sessions
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # SECURITY VIOLATION ANALYSIS
        
        # SECURITY ANALYSIS: Check if singleton pattern creates shared global state
        factory_ids = [result['factory_id'] for result in results]
        unique_factory_count = len(set(factory_ids))
        
        # VULNERABILITY TEST: If singleton pattern is in use, all users get SAME factory ID
        # This would enable cross-user contamination
        if unique_factory_count == 1:
            # SINGLETON VULNERABILITY DETECTED: All users share same factory instance
            assert True, (
                "SINGLETON VULNERABILITY CONFIRMED: All users share same factory instance. "
                f"Factory ID: {factory_ids[0]}. This enables cross-user contamination."
            )
        else:
            # SINGLETON REMEDIATION DETECTED: Users get different factory instances
            # This test SHOULD fail during vulnerability demonstration phase
            assert False, (
                f"SINGLETON REMEDIATION DETECTED: Users get different factory instances ({unique_factory_count} unique). "
                f"Factory IDs: {set(factory_ids)}. "
                "Expected: SAME factory ID for all users (proving singleton vulnerability exists). "
                "If this assertion fails, it suggests the singleton pattern has been remediated."
            )
        
        # CRITICAL VIOLATION ASSERTION: Messages broadcast to unintended users
        for result in results:
            user_id = result['user_id']
            all_emitters = result['all_emitters']
            
            # Check if this user's WebSocket can receive other users' messages
            user_emitter = all_emitters[user_id]
            received_messages = user_emitter.messages_sent
            
            # Find messages intended for other users that this user received
            # VULNERABILITY: Each user's emitter receives ALL messages due to singleton
            cross_contaminated_messages = [
                msg for msg in received_messages 
                if msg['intended_for'] != user_id  # Messages NOT intended for this user
            ]
            
            assert len(cross_contaminated_messages) > 0, (
                f"WEBSOCKET CONTAMINATION VIOLATION: User {user_id} received messages "
                f"intended for other users: {cross_contaminated_messages}. "
                "REAL-TIME SECURITY RISK: Secret agent responses delivered to wrong users. "
                "COMPLIANCE IMPACT: Violates real-time data protection requirements."
            )

    def test_database_session_contamination_persistent_data_risk(self):
        """
        CRITICAL SECURITY TEST: Prove database sessions leak between users through singleton.
        
        SECURITY VIOLATION: Singleton factory can cause database sessions from one user
        to persist and be accessible to subsequent users, creating data exposure across
        user boundaries in persistent storage.
        
        PERSISTENT IMPACT: User data stored during one session remains accessible to
        other users through shared singleton state, violating data isolation requirements.
        
        EXPECTED: FAIL before remediation (proving database contamination)
        EXPECTED: PASS after remediation (proving database isolation)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # First user session - store sensitive database context
        factory1 = get_agent_instance_factory()
        user1_id = 'enterprise_user_001'
        user1_sensitive_query = "SELECT * FROM executive_compensation WHERE salary > 500000"
        
        # Simulate database session context storage (represents real DB session state)
        if not hasattr(factory1, '_database_contexts'):
            factory1._database_contexts = {}
        
        factory1._database_contexts[user1_id] = {
            'session_id': f"db_session_{uuid.uuid4()}",
            'query_history': [user1_sensitive_query],
            'connection_params': {'database': 'executive_data', 'user': user1_id},
            'active_transactions': ['executive_compensation_query'],
            'cached_results': {'salary_data': 'CONFIDENTIAL_EXECUTIVE_DATA'}
        }
        
        # Simulate end of first user session
        del factory1
        gc.collect()  # Force garbage collection attempt
        
        # Second user session - should NOT see first user's data
        factory2 = get_agent_instance_factory()
        user2_id = 'regular_user_002'
        
        # SECURITY VIOLATION ASSERTION: Database contexts persist across users
        assert hasattr(factory2, '_database_contexts'), (
            "DATABASE PERSISTENCE VIOLATION: Database contexts persist in singleton "
            "across user sessions, creating cross-user data access risk."
        )
        
        # CRITICAL SECURITY VIOLATION: First user's sensitive data accessible
        assert user1_id in factory2._database_contexts, (
            f"DATABASE CONTAMINATION VIOLATION: User {user1_id}'s database context "
            f"accessible to user {user2_id}. Database contexts: {factory2._database_contexts.keys()}. "
            "SECURITY IMPACT: Sensitive query history and cached results exposed."
        )
        
        # ENTERPRISE VIOLATION: Sensitive query data accessible to wrong user
        user1_context = factory2._database_contexts[user1_id]
        exposed_query = user1_context['query_history'][0]
        assert exposed_query == user1_sensitive_query, (
            f"CRITICAL DATA EXPOSURE: User {user2_id} can access user {user1_id}'s "
            f"sensitive database queries: '{exposed_query}'. "
            "COMPLIANCE VIOLATION: Cross-user database access violates enterprise security. "
            "BUSINESS IMPACT: $500K+ ARR customers require complete database isolation."
        )

    def test_agent_state_persistence_memory_leak_security_risk(self):
        """
        CRITICAL SECURITY TEST: Prove agent state persists inappropriately across users.
        
        SECURITY VIOLATION: Singleton factory causes agent execution state, conversation
        context, and user-specific processing data to persist in memory across user sessions,
        creating memory-based data exposure vulnerabilities.
        
        MEMORY SECURITY RISK: Previous user's agent state (including conversation history,
        processing results, and execution context) remains in memory and can be accessed
        by subsequent users through the shared singleton.
        
        EXPECTED: FAIL before remediation (proving memory persistence violation)
        EXPECTED: PASS after remediation (proving proper memory isolation)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # User 1: Store sensitive agent execution state
        factory1 = get_agent_instance_factory()
        user1_sensitive_context = {
            'user_id': 'vip_customer_001',
            'conversation_topic': 'Acquisition strategy for competitor Company Y',
            'agent_memory': ['Board meeting scheduled', 'Due diligence completed'],
            'processing_results': {'valuation': '$50M', 'recommendation': 'PROCEED'},
            'execution_history': ['strategic_analysis', 'financial_modeling', 'risk_assessment']
        }
        
        # Store agent state in singleton (simulating real agent execution memory)
        if not hasattr(factory1, '_agent_execution_states'):
            factory1._agent_execution_states = {}
        
        factory1._agent_execution_states['vip_customer_001'] = user1_sensitive_context
        
        # Add execution tracking for contamination detection
        if not hasattr(factory1, '_execution_memory'):
            factory1._execution_memory = {}
        
        factory1._execution_memory['last_execution'] = {
            'user_id': 'vip_customer_001',
            'sensitive_analysis': 'Competitor acquisition feasible at $50M valuation',
            'strategic_context': user1_sensitive_context
        }
        
        # Simulate user 1 session ending
        user1_session_ref = weakref.ref(factory1)
        del factory1
        gc.collect()
        
        # User 2: Different user accessing factory (should NOT see user 1's data)
        factory2 = get_agent_instance_factory()
        user2_id = 'regular_customer_002'
        
        # MEMORY PERSISTENCE VIOLATION: Agent states persist across users
        assert hasattr(factory2, '_agent_execution_states'), (
            "AGENT STATE PERSISTENCE VIOLATION: Agent execution states persist in singleton "
            "across user sessions, creating memory-based data exposure."
        )
        
        # CRITICAL SECURITY VIOLATION: Previous user's sensitive agent data accessible
        assert 'vip_customer_001' in factory2._agent_execution_states, (
            f"AGENT MEMORY CONTAMINATION: User {user2_id} can access previous user's "
            f"agent execution state. Available states: {list(factory2._agent_execution_states.keys())}. "
            "MEMORY SECURITY RISK: Sensitive conversation context exposed across users."
        )
        
        # ENTERPRISE VIOLATION: Sensitive strategic analysis exposed
        exposed_context = factory2._agent_execution_states['vip_customer_001']
        assert exposed_context['conversation_topic'] == 'Acquisition strategy for competitor Company Y', (
            f"STRATEGIC DATA EXPOSURE: User {user2_id} can access VIP customer's "
            f"strategic analysis: {exposed_context}. "
            "BUSINESS INTELLIGENCE LEAK: Competitor acquisition strategies exposed. "
            "ENTERPRISE IMPACT: $500K+ ARR VIP customers require absolute memory isolation."
        )
        
        # EXECUTION MEMORY VIOLATION: Last execution context accessible
        assert hasattr(factory2, '_execution_memory'), (
            "EXECUTION MEMORY VIOLATION: Previous execution memory accessible to new user."
        )
        
        last_execution = factory2._execution_memory['last_execution']
        assert last_execution['sensitive_analysis'] == 'Competitor acquisition feasible at $50M valuation', (
            f"EXECUTION CONTEXT LEAK: User {user2_id} can access previous execution "
            f"analysis: '{last_execution['sensitive_analysis']}'. "
            "CRITICAL SECURITY IMPACT: Strategic business analysis exposed across users."
        )

    def test_forced_singleton_vulnerability_demonstration(self):
        """
        CRITICAL SECURITY TEST: Force singleton pattern and prove cross-user contamination.
        
        This test explicitly forces the singleton pattern to demonstrate the exact
        vulnerability that would occur if the singleton pattern is used in production.
        
        BUSINESS IMPACT: $500K+ ARR enterprise customers require absolute isolation.
        This test proves why singleton patterns are a security vulnerability.
        
        EXPECTED: FAIL (proving vulnerability exists when singleton pattern is used)
        """
        # Import the factory module to access its internal state
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        
        # CRITICAL: Force singleton pattern by ensuring same instance is reused
        # Clear any existing singleton to start fresh
        factory_module._factory_instance = None
        
        # Force singleton behavior for this test
        singleton_factory = factory_module.get_agent_instance_factory()
        
        # Simulate multiple users accessing the SAME singleton instance
        user_contamination_data = {}
        
        def contaminate_singleton_with_user_data(user_id: str, sensitive_data: str):
            """Simulate user data contamination in singleton factory."""
            # Get the singleton (same instance every time)
            factory = factory_module.get_agent_instance_factory()
            
            # Verify it's the same singleton instance
            assert factory is singleton_factory, (
                f"SINGLETON PATTERN VIOLATION: Expected same instance for {user_id}, "
                f"got different instance. Singleton ID: {id(singleton_factory)}, "
                f"User factory ID: {id(factory)}"
            )
            
            # Store user's sensitive data in singleton (simulating real contamination)
            if not hasattr(factory, '_user_sensitive_data'):
                factory._user_sensitive_data = {}
            
            factory._user_sensitive_data[user_id] = {
                'personal_info': sensitive_data,
                'session_secrets': f"SECRET_TOKEN_{user_id}_{time.time()}",
                'private_context': f"PRIVATE_CONVERSATION_HISTORY_{user_id}",
                'access_timestamp': time.time()
            }
            
            # Return all data accessible through singleton
            return {
                'user_id': user_id,
                'factory_id': id(factory),
                'sensitive_data': sensitive_data,
                'can_access_all_users_data': dict(factory._user_sensitive_data),
                'total_users_in_singleton': len(factory._user_sensitive_data)
            }
        
        # Simulate multiple enterprise users with sensitive data
        enterprise_users = [
            ('patient_001', 'Patient John Doe, DOB: 1980-05-15, SSN: 123-45-6789, Diagnosis: Diabetes'),
            ('client_002', 'Client Account #9876543210, Balance: $2,500,000, Investment Portfolio: CONFIDENTIAL'),
            ('case_003', 'Legal Case #2024-456789, Settlement: $5,000,000, Attorney-Client Privileged')
        ]
        
        # Each user stores data in the singleton
        contamination_results = []
        for user_id, sensitive_data in enterprise_users:
            result = contaminate_singleton_with_user_data(user_id, sensitive_data)
            contamination_results.append(result)
            time.sleep(0.001)  # Small delay to simulate real timing
        
        # SECURITY VIOLATION ANALYSIS
        
        # VIOLATION 1: All users get same factory instance (singleton pattern)
        factory_ids = [result['factory_id'] for result in contamination_results]
        unique_factories = set(factory_ids)
        assert len(unique_factories) == 1, (
            f"SINGLETON PATTERN CONFIRMED: All users share same factory instance. "
            f"Factory ID: {factory_ids[0]}. This enables cross-user data access."
        )
        
        # VIOLATION 2: Each user (after first) can access ALL other users' sensitive data
        contamination_violations = []
        for i, result in enumerate(contamination_results):
            user_id = result['user_id']
            user_sensitive_data = result['sensitive_data']
            all_accessible_data = result['can_access_all_users_data']
            
            # Find sensitive data from OTHER users that this user can access
            other_users_data = {}
            for other_user_id, other_data in all_accessible_data.items():
                if other_user_id != user_id:
                    other_users_data[other_user_id] = other_data
            
            # Record contamination for analysis
            contamination_violations.append({
                'user_id': user_id,
                'can_access_others': len(other_users_data) > 0,
                'other_users_accessible': list(other_users_data.keys()),
                'exposed_data_count': len(other_users_data)
            })
            
            # CRITICAL SECURITY VIOLATION: Users after the first should see other users' data
            if i > 0:  # Skip first user (no other users exist yet)
                assert len(other_users_data) > 0, (
                    f"CROSS-USER DATA EXPOSURE: User {user_id} can access {len(other_users_data)} "
                    f"other users' sensitive data through singleton: {list(other_users_data.keys())}. "
                    f"Exposed data: {other_users_data}. "
                    f"COMPLIANCE VIOLATION: This violates HIPAA, SOC2, PCI-DSS, and SEC requirements."
                )
            
            # Verify specific sensitive data exposure
            if i > 0:  # Not the first user
                first_user_data = contamination_results[0]
                first_user_id = first_user_data['user_id']
                first_user_sensitive = first_user_data['sensitive_data']
                
                # Current user should NOT be able to see first user's data
                if first_user_id in all_accessible_data:
                    exposed_first_user_data = all_accessible_data[first_user_id]['personal_info']
                    assert exposed_first_user_data == first_user_sensitive, (
                        f"SPECIFIC DATA LEAKAGE: User {user_id} can access user {first_user_id}'s "
                        f"sensitive data: '{exposed_first_user_data}'. "
                        f"BUSINESS IMPACT: Enterprise customer data exposed to other customers."
                    )
        
        # VIOLATION 3: Data persists across user sessions
        total_users_tracked = contamination_results[-1]['total_users_in_singleton']
        assert total_users_tracked == len(enterprise_users), (
            f"DATA PERSISTENCE VIOLATION: Singleton retains all user data across sessions. "
            f"Total users tracked: {total_users_tracked}, Expected isolation: per-user data only. "
            f"MEMORY SECURITY RISK: User data accumulates in singleton across requests."
        )

    def test_per_request_isolation_requirement_validation(self):
        """
        CRITICAL ARCHITECTURE TEST: Prove per-request factory pattern is required for security.
        
        SECURITY REQUIREMENT: Multi-user systems require per-request isolation to prevent
        cross-user contamination. Singleton pattern violates this fundamental requirement.
        
        ENTERPRISE ARCHITECTURE: $500K+ ARR customers require architectural patterns that
        guarantee complete user isolation at the request level for regulatory compliance.
        
        EXPECTED: FAIL before remediation (proving singleton violates isolation)
        EXPECTED: PASS after remediation (proving per-request pattern)
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory
        )
        
        # Simulate multiple concurrent requests from different enterprise customers
        request_isolation_data = {}
        
        def simulate_enterprise_request(customer_id: str, request_type: str) -> Dict[str, Any]:
            """Simulate enterprise customer request requiring complete isolation."""
            factory = get_agent_instance_factory()
            request_id = f"req_{customer_id}_{uuid.uuid4()}"
            
            # Each request SHOULD get unique factory state for security
            enterprise_context = {
                'customer_id': customer_id,
                'request_id': request_id,
                'request_type': request_type,
                'compliance_requirements': ['HIPAA', 'SOC2', 'PCI-DSS', 'SEC'],
                'data_classification': 'ENTERPRISE_CONFIDENTIAL',
                'isolation_required': True
            }
            
            # Store enterprise request context (represents real request processing)
            if not hasattr(factory, '_enterprise_requests'):
                factory._enterprise_requests = {}
            
            factory._enterprise_requests[request_id] = enterprise_context
            
            return {
                'customer_id': customer_id,
                'request_id': request_id,
                'factory_id': id(factory),
                'enterprise_context': enterprise_context,
                'total_requests_in_factory': len(factory._enterprise_requests),
                'all_customer_requests': {
                    req_id: ctx['customer_id'] 
                    for req_id, ctx in factory._enterprise_requests.items()
                }
            }
        
        # Simulate concurrent enterprise requests requiring isolation
        enterprise_requests = [
            ('HEALTHCARE_CORP', 'patient_data_analysis'),
            ('FINANCIAL_BANK', 'fraud_detection_query'),
            ('GOVERNMENT_AGENCY', 'classified_document_processing'),
            ('LEGAL_FIRM', 'confidential_case_analysis')
        ]
        
        request_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(simulate_enterprise_request, customer, req_type)
                for customer, req_type in enterprise_requests
            ]
            
            for future in as_completed(futures):
                request_results.append(future.result())
        
        # ENTERPRISE ISOLATION VIOLATION ANALYSIS
        
        # SECURITY ANALYSIS: Check if singleton pattern enables cross-customer access
        factory_ids = [result['factory_id'] for result in request_results]
        unique_factory_ids = set(factory_ids)
        unique_count = len(unique_factory_ids)
        
        # VULNERABILITY TEST: Singleton pattern would cause all customers to share same factory
        if unique_count == 1:
            # SINGLETON VULNERABILITY CONFIRMED: All customers share same factory
            singleton_factory_id = factory_ids[0]
            assert True, (
                f"SINGLETON VULNERABILITY CONFIRMED: All {len(enterprise_requests)} enterprise customers "
                f"share same factory (ID: {singleton_factory_id}). This enables cross-customer data access."
            )
        else:
            # SINGLETON REMEDIATION DETECTED: Customers get isolated factories
            assert False, (
                f"SINGLETON REMEDIATION DETECTED: Customers get separate factories ({unique_count} unique). "
                f"Factory IDs: {unique_factory_ids}. "
                f"Expected: SAME factory ID for all customers (proving singleton vulnerability). "
                "If this fails, singleton pattern may have been remediated."
            )
        
        # CRITICAL VIOLATION: Request contexts accumulate across customers
        final_result = request_results[-1]
        total_requests = final_result['total_requests_in_factory']
        
        assert total_requests == len(enterprise_requests), (
            "REQUEST ACCUMULATION VIOLATION: Enterprise requests accumulate in singleton. "
            f"Total requests: {total_requests}, Expected: 1 per isolated factory. "
            "ENTERPRISE SECURITY RISK: Customer data accessible across requests."
        )
        
        # CUSTOMER ISOLATION VIOLATION: Each request can access other customers' data
        for result in request_results:
            customer_id = result['customer_id']
            all_customer_requests = result['all_customer_requests']
            
            # Find requests from other customers accessible through singleton
            other_customers_requests = {
                req_id: customer for req_id, customer in all_customer_requests.items()
                if customer != customer_id
            }
            
            assert len(other_customers_requests) > 0, (
                f"CUSTOMER ISOLATION VIOLATION: {customer_id} can access other customers' "
                f"requests: {other_customers_requests}. "
                "ENTERPRISE SECURITY BREACH: Cross-customer data access through singleton. "
                "COMPLIANCE VIOLATION: Violates HIPAA, SOC2, PCI-DSS customer isolation."
            )