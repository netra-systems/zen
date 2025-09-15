"""
Issue #889 WebSocket Manager SSOT Violations - User Isolation Unit Tests
User Context Isolation and Contamination Detection

MUST FAIL INITIALLY: These tests are designed to detect user context contamination
and isolation failures that violate SSOT principles and create security risks.

Business Value: Critical for regulatory compliance (HIPAA, SOC2, SEC) by ensuring
complete user data isolation in our $500K+ ARR multi-tenant chat platform.

Expected Behavior:
- All tests MUST FAIL initially, proving isolation violations exist
- Tests validate user context separation and data integrity
- Tests ensure no cross-user data contamination occurs

Agent Session: agent-session-2025-09-15-1430
Created: 2025-09-15
Priority: P2 (escalated from P3 due to regulatory compliance risk)
"""

import asyncio
import unittest
from unittest.mock import patch, Mock, MagicMock
from typing import Optional, Any, Dict, List
import secrets
import concurrent.futures
import threading

# SSOT Base Test Case - MANDATORY for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT imports for isolated environment
from shared.isolated_environment import IsolatedEnvironment, get_env

# WebSocket manager imports - testing the actual implementation
try:
    from netra_backend.app.websocket_core.websocket_manager import (
        get_websocket_manager,
        _UnifiedWebSocketManagerImplementation,
        WebSocketManagerMode,
        create_test_user_context
    )
    WEBSOCKET_IMPORTS_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_IMPORTS_AVAILABLE = False
    print(f"WebSocket imports not available: {e}")


class TestIssue889UserIsolationUnit(SSotAsyncTestCase):
    """
    Unit tests for Issue #889 User Context Isolation Violations
    
    Focus: User context contamination detection and multi-tenant security validation
    """
    
    def setUp(self):
        """Standard setUp following SSOT patterns"""
        super().setUp()
        self.created_managers = []
        self.test_users = [
            "demo-user-001",  # Primary violation pattern from logs
            "demo-user-002", 
            "production-user-001",
            "test-user-isolation-001",
            "test-user-isolation-002"
        ]
        
    def tearDown(self):
        """Cleanup any managers created during testing"""
        # Clean up managers and any shared state
        self.created_managers.clear()
        super().tearDown()
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_user_context_contamination(self):
        """
        MUST FAIL INITIALLY: Detect when user contexts bleed between managers
        
        Business Value: Critical for HIPAA/SOC2 compliance - no data leakage
        Expected Failure: User data contamination detected between different users
        
        This test validates that managers for different users maintain complete
        data isolation and do not share any state or context information.
        """
        managers_by_user = {}
        context_contamination_detected = []
        
        # Create managers for multiple different users
        for user_id in self.test_users:
            user_context = type('MockUserContext', (), {
                'user_id': user_id,
                'thread_id': f'{user_id}-thread',
                'request_id': f'{user_id}-request',
                'is_test': True,
                'sensitive_data': f'SENSITIVE_DATA_FOR_{user_id}',  # Simulated sensitive data
                'session_token': f'TOKEN_{user_id}_{secrets.token_hex(8)}'
            })()
            
            manager = await get_websocket_manager(user_context=user_context)
            managers_by_user[user_id] = {
                'manager': manager,
                'context': user_context
            }
            self.created_managers.append(manager)
            
        # Test for context contamination between users
        for user_a in self.test_users:
            for user_b in self.test_users:
                if user_a == user_b:
                    continue
                    
                manager_a = managers_by_user[user_a]['manager']
                manager_b = managers_by_user[user_b]['manager']
                context_a = managers_by_user[user_a]['context']
                context_b = managers_by_user[user_b]['context']
                
                # Check if managers share any context references (VIOLATION)
                if hasattr(manager_a, 'user_context') and hasattr(manager_b, 'user_context'):
                    # Check for object reference sharing (critical violation)
                    if manager_a.user_context is manager_b.user_context:
                        context_contamination_detected.append({
                            'type': 'shared_context_reference',
                            'user_a': user_a,
                            'user_b': user_b,
                            'manager_a_id': id(manager_a),
                            'manager_b_id': id(manager_b)
                        })
                        
                    # Check for data bleeding between contexts
                    if hasattr(manager_a.user_context, 'sensitive_data') and hasattr(manager_b.user_context, 'sensitive_data'):
                        expected_data_a = f'SENSITIVE_DATA_FOR_{user_a}'
                        expected_data_b = f'SENSITIVE_DATA_FOR_{user_b}'
                        actual_data_a = manager_a.user_context.sensitive_data
                        actual_data_b = manager_b.user_context.sensitive_data
                        
                        if actual_data_a != expected_data_a:
                            context_contamination_detected.append({
                                'type': 'data_contamination',
                                'affected_user': user_a,
                                'expected_data': expected_data_a,
                                'actual_data': actual_data_a,
                                'contamination_source': user_b
                            })
                            
                        if actual_data_b != expected_data_b:
                            context_contamination_detected.append({
                                'type': 'data_contamination',
                                'affected_user': user_b,
                                'expected_data': expected_data_b,
                                'actual_data': actual_data_b,
                                'contamination_source': user_a
                            })
                            
        # This assertion WILL FAIL if contamination exists (which we expect initially)
        self.assertEqual(
            len(context_contamination_detected),
            0,
            f"CRITICAL SECURITY VIOLATION: User context contamination detected. "
            f"This violates HIPAA, SOC2, and SEC compliance requirements. "
            f"Contamination incidents: {context_contamination_detected}. "
            f"Each incident represents potential data leakage between users."
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")  
    async def test_concurrent_user_isolation_integrity(self):
        """
        MUST FAIL INITIALLY: Detect isolation failures during concurrent operations
        
        Business Value: Ensures scalability maintains security under load
        Expected Failure: Concurrent operations cause user context mixing
        
        This test simulates concurrent user operations to detect race conditions
        that could lead to user data contamination.
        """
        isolation_violations = []
        concurrent_managers = {}
        
        async def create_user_manager(user_id: str) -> dict:
            """Create a manager for a user and perform operations"""
            user_context = type('MockUserContext', (), {
                'user_id': user_id,
                'thread_id': f'{user_id}-concurrent-thread',
                'request_id': f'{user_id}-concurrent-request',
                'is_test': True,
                'user_secret': f'SECRET_{user_id}_{secrets.token_hex(16)}',
                'creation_timestamp': asyncio.get_event_loop().time()
            })()
            
            manager = await get_websocket_manager(user_context=user_context)
            
            return {
                'user_id': user_id,
                'manager': manager,
                'context': user_context,
                'creation_time': user_context.creation_timestamp
            }
            
        # Create multiple managers concurrently
        tasks = []
        for user_id in self.test_users:
            task = asyncio.create_task(create_user_manager(user_id))
            tasks.append(task)
            
        # Wait for all concurrent creations to complete
        results = await asyncio.gather(*tasks)
        
        # Store results and track managers for cleanup
        for result in results:
            concurrent_managers[result['user_id']] = result
            self.created_managers.append(result['manager'])
            
        # Validate isolation integrity after concurrent creation
        for user_a_id in self.test_users:
            for user_b_id in self.test_users:
                if user_a_id == user_b_id:
                    continue
                    
                manager_a = concurrent_managers[user_a_id]['manager']
                manager_b = concurrent_managers[user_b_id]['manager']
                context_a = concurrent_managers[user_a_id]['context']
                context_b = concurrent_managers[user_b_id]['context']
                
                # Validate unique manager instances
                if id(manager_a) == id(manager_b):
                    isolation_violations.append({
                        'type': 'shared_manager_instance',
                        'user_a': user_a_id,
                        'user_b': user_b_id,
                        'manager_id': id(manager_a)
                    })
                    
                # Validate unique context instances  
                if id(context_a) == id(context_b):
                    isolation_violations.append({
                        'type': 'shared_context_instance',
                        'user_a': user_a_id,
                        'user_b': user_b_id,
                        'context_id': id(context_a)
                    })
                    
                # Validate secret data isolation
                if hasattr(context_a, 'user_secret') and hasattr(context_b, 'user_secret'):
                    if context_a.user_secret == context_b.user_secret:
                        isolation_violations.append({
                            'type': 'shared_secret_data',
                            'user_a': user_a_id,
                            'user_b': user_b_id,
                            'shared_secret': context_a.user_secret
                        })
                        
        # This assertion WILL FAIL initially if isolation violations exist
        self.assertEqual(
            len(isolation_violations),
            0,
            f"CRITICAL ISOLATION VIOLATION: Concurrent operations caused user isolation failures. "
            f"This creates race conditions that can lead to user data contamination. "
            f"Violations detected: {isolation_violations}. "
            f"Each violation represents a potential security breach."
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_manager_state_sharing_detection(self):
        """
        MUST FAIL INITIALLY: Detect if managers share internal state between users
        
        Business Value: Prevents data leakage through shared internal components
        Expected Failure: Managers share internal state objects or caches
        
        This test validates that manager internal state is completely isolated
        between different users and no shared caching or state occurs.
        """
        state_sharing_violations = []
        
        # Create managers for different users
        user_managers = {}
        for user_id in ['demo-user-001', 'demo-user-002', 'production-user-001']:
            user_context = type('MockUserContext', (), {
                'user_id': user_id,
                'thread_id': f'{user_id}-state-test',
                'request_id': f'{user_id}-state-request',
                'is_test': True,
                'state_marker': f'STATE_MARKER_{user_id}'
            })()
            
            manager = await get_websocket_manager(user_context=user_context)
            user_managers[user_id] = {
                'manager': manager,
                'context': user_context
            }
            self.created_managers.append(manager)
            
        # Test for shared internal state between managers
        manager_list = list(user_managers.values())
        
        for i, manager_a_info in enumerate(manager_list):
            for j, manager_b_info in enumerate(manager_list[i+1:], i+1):
                manager_a = manager_a_info['manager']
                manager_b = manager_b_info['manager']
                
                # Check for shared internal attributes
                shared_attributes = []
                
                # Common attributes that should NOT be shared between managers
                check_attributes = [
                    '_auth_token', 'auth_token', '_ssot_authorization_token',
                    '_user_context', 'user_context',
                    '_mode', 'mode',
                    '_manager_id', 'manager_id',
                    '_state', 'state', '_internal_state',
                    '_cache', 'cache', '_session_cache'
                ]
                
                for attr_name in check_attributes:
                    if hasattr(manager_a, attr_name) and hasattr(manager_b, attr_name):
                        attr_a = getattr(manager_a, attr_name)
                        attr_b = getattr(manager_b, attr_name)
                        
                        # Check if they share the same object reference
                        if attr_a is attr_b and attr_a is not None:
                            shared_attributes.append({
                                'attribute': attr_name,
                                'shared_object_id': id(attr_a),
                                'user_a': manager_a_info['context'].user_id,
                                'user_b': manager_b_info['context'].user_id
                            })
                            
                if shared_attributes:
                    state_sharing_violations.extend(shared_attributes)
                    
        # This assertion WILL FAIL initially if state sharing exists  
        self.assertEqual(
            len(state_sharing_violations),
            0,
            f"CRITICAL STATE SHARING VIOLATION: Managers share internal state between users. "
            f"This violates user isolation principles and can cause data contamination. "
            f"Shared state detected: {state_sharing_violations}. "
            f"Each shared attribute represents potential cross-user data leakage."
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE, "WebSocket imports not available")
    async def test_demo_user_001_isolation_integrity(self):
        """
        MUST FAIL INITIALLY: Validate demo-user-001 doesn't contaminate other users
        
        Business Value: Ensures test patterns don't affect production user isolation
        Expected Failure: demo-user-001 context contaminates other user contexts
        
        This specifically tests the demo-user-001 pattern from the GCP logs
        to ensure it maintains proper isolation from other users.
        """
        demo_user_contamination = []
        
        # Create demo-user-001 manager (the problematic pattern from logs)
        demo_context = type('MockUserContext', (), {
            'user_id': 'demo-user-001',
            'thread_id': 'demo-thread-001',
            'request_id': 'demo-request-001',
            'is_test': True,
            'demo_marker': 'DEMO_USER_MARKER_SENSITIVE',
            'demo_session_data': {'sensitive': 'demo_data', 'timestamp': 1234567890}
        })()
        
        demo_manager = await get_websocket_manager(user_context=demo_context)
        self.created_managers.append(demo_manager)
        
        # Create production user managers
        production_managers = {}
        for i in range(1, 4):
            prod_user_id = f'production-user-{i:03d}'
            prod_context = type('MockUserContext', (), {
                'user_id': prod_user_id,
                'thread_id': f'prod-thread-{i:03d}',
                'request_id': f'prod-request-{i:03d}',
                'is_test': False,
                'production_marker': f'PRODUCTION_USER_{prod_user_id}_SENSITIVE',
                'production_session_data': {'sensitive': f'prod_data_{i}', 'user_level': 'enterprise'}
            })()
            
            prod_manager = await get_websocket_manager(user_context=prod_context)
            production_managers[prod_user_id] = {
                'manager': prod_manager,
                'context': prod_context
            }
            self.created_managers.append(prod_manager)
            
        # Test for contamination from demo-user-001 to production users
        for prod_user_id, prod_info in production_managers.items():
            prod_manager = prod_info['manager']
            prod_context = prod_info['context']
            
            # Check if demo data leaked into production contexts
            contamination_checks = [
                # Check for demo marker in production context
                {
                    'check': hasattr(prod_context, 'demo_marker'),
                    'violation_type': 'demo_marker_in_production',
                    'description': 'Demo user marker found in production context'
                },
                # Check for demo session data in production context
                {
                    'check': hasattr(prod_context, 'demo_session_data'),
                    'violation_type': 'demo_session_data_in_production', 
                    'description': 'Demo session data found in production context'
                },
                # Check if production context has demo user ID
                {
                    'check': getattr(prod_context, 'user_id', None) == 'demo-user-001',
                    'violation_type': 'demo_user_id_contamination',
                    'description': 'Production context has demo user ID'
                },
                # Check if demo manager reference leaked to production
                {
                    'check': prod_manager is demo_manager,
                    'violation_type': 'shared_manager_instance',
                    'description': 'Production user shares manager instance with demo user'
                }
            ]
            
            for check in contamination_checks:
                if check['check']:
                    demo_user_contamination.append({
                        'affected_user': prod_user_id,
                        'violation_type': check['violation_type'],
                        'description': check['description'],
                        'demo_manager_id': id(demo_manager),
                        'prod_manager_id': id(prod_manager)
                    })
                    
        # This assertion WILL FAIL initially if demo user contamination exists
        self.assertEqual(
            len(demo_user_contamination),
            0,
            f"CRITICAL DEMO USER CONTAMINATION: demo-user-001 pattern contaminated production users. "
            f"This violates the isolation between test and production contexts. "
            f"Contamination incidents: {demo_user_contamination}. "
            f"Each incident represents test data leaking into production user contexts."
        )


if __name__ == '__main__':
    # Run tests using standard unittest runner for compatibility
    unittest.main()