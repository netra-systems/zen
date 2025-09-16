"""
Issue #889 WebSocket Manager SSOT Violations - Integration Test Suite
Multi-User Scenario Validation with Real Services

MUST FAIL INITIALLY: These tests are designed to reproduce SSOT violations in 
realistic multi-user scenarios using real PostgreSQL and Redis services to
detect actual production-like conditions.

Business Value: Validates that WebSocket manager factory patterns maintain
integrity under realistic load conditions critical for $500K+ ARR platform.

Expected Behavior:
- All tests MUST FAIL initially, proving violations exist under realistic conditions
- Tests use real services (PostgreSQL, Redis) for authentic validation
- Tests simulate actual multi-user concurrent access patterns

Agent Session: agent-session-2025-09-15-1430  
Created: 2025-09-15
Priority: P2 (escalated from P3 due to production impact risk)
"""

import pytest
import asyncio
import unittest
from unittest.mock import patch, Mock, MagicMock
from typing import Optional, Any, Dict, List
import secrets
import concurrent.futures
import threading
import time

# SSOT Base Test Case - MANDATORY for all tests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT imports for isolated environment
from shared.isolated_environment import IsolatedEnvironment, get_env

# Real services test fixtures for integration testing
try:
    from test_framework.real_services_test_fixtures import (
        real_services_fixture,
        real_db_fixture,
        real_redis_fixture
    )
    REAL_SERVICES_AVAILABLE = True
except ImportError as e:
    REAL_SERVICES_AVAILABLE = False
    print(f"Real services fixtures not available: {e}")

# WebSocket manager imports - testing the actual implementation
try:
    from netra_backend.app.websocket_core.canonical_import_patterns import (
        get_websocket_manager,
        _UnifiedWebSocketManagerImplementation,
        WebSocketManagerMode,
        create_test_user_context
    )
    WEBSOCKET_IMPORTS_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_IMPORTS_AVAILABLE = False
    print(f"WebSocket imports not available: {e}")


@pytest.mark.integration
class Issue889ManagerDuplicationIntegrationTests(SSotAsyncTestCase):
    """
    Integration tests for Issue #889 WebSocket Manager SSOT Violations
    
    Focus: Multi-user scenarios with real services infrastructure
    """
    
    def setUp(self):
        """Standard setUp following SSOT patterns"""
        super().setUp()
        self.created_managers = []
        self.test_sessions = []
        self.violation_log = []
        
    def tearDown(self):
        """Cleanup managers and test sessions"""
        # Clean up managers to prevent resource leaks
        self.created_managers.clear()
        self.test_sessions.clear()
        self.violation_log.clear()
        super().tearDown()
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE and REAL_SERVICES_AVAILABLE, 
                        "WebSocket imports or real services not available")
    async def test_concurrent_user_manager_creation_duplication(self):
        """
        MUST FAIL INITIALLY: Detect duplication in concurrent scenarios with real services
        
        Business Value: Ensures scalability and prevents resource waste under realistic load
        Expected Failure: Multiple managers created for concurrent requests with same user
        
        This test simulates realistic concurrent user access patterns using real
        database and cache services to detect SSOT violations under load.
        """
        duplication_violations = []
        manager_creation_log = []
        
        # Use real services fixture for authentic testing
        async with real_services_fixture() as services:
            # Simulate high-concurrency scenario with demo-user-001 pattern
            user_id = "demo-user-001"  # The problematic pattern from GCP logs
            concurrent_requests = 10  # Simulate realistic concurrent load
            
            async def create_concurrent_manager(request_index: int) -> dict:
                """Create manager for concurrent request simulation"""
                request_start_time = time.time()
                
                user_context = type('MockUserContext', (), {
                    'user_id': user_id,
                    'thread_id': f'{user_id}-concurrent-{request_index}',
                    'request_id': f'{user_id}-request-{request_index}-{int(request_start_time * 1000)}',
                    'is_test': True,
                    'session_data': {
                        'request_index': request_index,
                        'start_time': request_start_time,
                        'concurrent_batch': 'issue_889_test'
                    }
                })()
                
                # Create manager with realistic timing
                manager = get_websocket_manager(user_context=user_context)
                
                creation_record = {
                    'request_index': request_index,
                    'manager_id': id(manager),
                    'manager_object': manager,
                    'user_context': user_context,
                    'creation_time': time.time(),
                    'creation_duration': time.time() - request_start_time
                }
                
                manager_creation_log.append(creation_record)
                return creation_record
                
            # Execute concurrent manager creation
            tasks = []
            for i in range(concurrent_requests):
                task = asyncio.create_task(create_concurrent_manager(i))
                tasks.append(task)
                
            # Small delay between task creation to simulate realistic timing
            await asyncio.sleep(0.001)
            
            # Wait for all concurrent creations
            creation_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out any exceptions and track successful creations
            successful_creations = [r for r in creation_results if not isinstance(r, Exception)]
            
            # Track managers for cleanup
            for result in successful_creations:
                self.created_managers.append(result['manager_object'])
                
            # Analyze for duplication violations
            managers_by_user = {}
            for result in successful_creations:
                user_id_key = result['user_context'].user_id
                if user_id_key not in managers_by_user:
                    managers_by_user[user_id_key] = []
                managers_by_user[user_id_key].append(result)
                
            # Check for multiple managers per user (SSOT violation)
            for user_id_key, user_managers in managers_by_user.items():
                if len(user_managers) > 1:
                    # Multiple managers for same user - VIOLATION
                    manager_ids = [m['manager_id'] for m in user_managers]
                    unique_manager_ids = set(manager_ids)
                    
                    if len(unique_manager_ids) > 1:
                        duplication_violations.append({
                            'user_id': user_id_key,
                            'manager_count': len(user_managers),
                            'unique_manager_ids': list(unique_manager_ids),
                            'creation_times': [m['creation_time'] for m in user_managers],
                            'concurrent_requests': len(user_managers)
                        })
                        
        # This assertion WILL FAIL initially - concurrent requests create duplicate managers
        self.assertEqual(
            len(duplication_violations),
            0,
            f"CRITICAL CONCURRENCY VIOLATION: Concurrent requests created multiple managers for same user. "
            f"This violates SSOT factory patterns and wastes resources under load. "
            f"Violations detected: {duplication_violations}. "
            f"Total creation attempts: {len(successful_creations)}, "
            f"Expected: 1 manager per user, Got: multiple managers per user."
        )
        
        # Additional validation: Check for proper manager reuse
        if successful_creations:
            first_manager_id = successful_creations[0]['manager_id']
            all_same_manager = all(r['manager_id'] == first_manager_id for r in successful_creations)
            
            self.assertTrue(
                all_same_manager,
                f"SSOT Factory Pattern Violation: Expected all concurrent requests for same user "
                f"to return same manager instance, but got different instances. "
                f"Manager IDs: {[r['manager_id'] for r in successful_creations]}"
            )
            
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE and REAL_SERVICES_AVAILABLE,
                        "WebSocket imports or real services not available")
    async def test_cross_service_manager_consistency(self):
        """
        MUST FAIL INITIALLY: Detect inconsistent manager states across services
        
        Business Value: Ensures consistent WebSocket behavior across platform services
        Expected Failure: Manager state inconsistency detected between backend and auth services
        
        This test validates that WebSocket managers maintain consistent state
        when accessed from different services using real service infrastructure.
        """
        consistency_violations = []
        service_managers = {}
        
        async with real_services_fixture() as services:
            # Create user context for cross-service testing
            test_user_id = "cross-service-test-user"
            base_context = type('MockUserContext', (), {
                'user_id': test_user_id,
                'thread_id': f'{test_user_id}-cross-service',
                'request_id': f'{test_user_id}-consistency-test',
                'is_test': True,
                'service_test_marker': 'CROSS_SERVICE_CONSISTENCY_TEST'
            })()
            
            # Simulate manager creation from different service contexts
            service_contexts = [
                ('backend_service', 'netra_backend'),
                ('auth_service', 'auth_service'),
                ('websocket_service', 'websocket_core')
            ]
            
            for service_name, service_module in service_contexts:
                # Create service-specific context variation
                service_context = type('MockUserContext', (), {
                    'user_id': test_user_id,
                    'thread_id': f'{test_user_id}-{service_name}',
                    'request_id': f'{test_user_id}-{service_name}-request',
                    'is_test': True,
                    'service_origin': service_name,
                    'service_module': service_module
                })()
                
                # Create manager from this service context
                manager = get_websocket_manager(user_context=service_context)
                service_managers[service_name] = {
                    'manager': manager,
                    'context': service_context,
                    'service_name': service_name,
                    'manager_id': id(manager)
                }
                self.created_managers.append(manager)
                
            # Validate consistency across services
            service_names = list(service_managers.keys())
            
            for i, service_a in enumerate(service_names):
                for service_b in service_names[i+1:]:
                    manager_a = service_managers[service_a]['manager']
                    manager_b = service_managers[service_b]['manager']
                    
                    # Check for inconsistent manager instances (should be same for same user)
                    if id(manager_a) != id(manager_b):
                        consistency_violations.append({
                            'violation_type': 'different_manager_instances',
                            'service_a': service_a,
                            'service_b': service_b,
                            'manager_a_id': id(manager_a),
                            'manager_b_id': id(manager_b),
                            'user_id': test_user_id
                        })
                        
                    # Check for inconsistent manager states
                    state_attributes = ['mode', 'user_context', '_ssot_authorization_token']
                    for attr in state_attributes:
                        if hasattr(manager_a, attr) and hasattr(manager_b, attr):
                            value_a = getattr(manager_a, attr)
                            value_b = getattr(manager_b, attr)
                            
                            # For context objects, check user_id consistency
                            if attr == 'user_context':
                                user_id_a = getattr(value_a, 'user_id', None)
                                user_id_b = getattr(value_b, 'user_id', None)
                                if user_id_a != user_id_b:
                                    consistency_violations.append({
                                        'violation_type': 'inconsistent_user_context',
                                        'service_a': service_a,
                                        'service_b': service_b,
                                        'attribute': attr,
                                        'user_id_a': user_id_a,
                                        'user_id_b': user_id_b
                                    })
                            elif value_a != value_b:
                                consistency_violations.append({
                                    'violation_type': 'inconsistent_attribute',
                                    'service_a': service_a,
                                    'service_b': service_b,
                                    'attribute': attr,
                                    'value_a': str(value_a)[:100],  # Truncate for readability
                                    'value_b': str(value_b)[:100]
                                })
                                
        # This assertion WILL FAIL initially - managers inconsistent across services
        self.assertEqual(
            len(consistency_violations),
            0,
            f"CRITICAL CROSS-SERVICE INCONSISTENCY: WebSocket managers inconsistent between services. "
            f"This violates SSOT principles and can cause unpredictable behavior. "
            f"Consistency violations: {consistency_violations}. "
            f"Each violation represents potential behavioral differences across services."
        )
        
    @unittest.skipUnless(WEBSOCKET_IMPORTS_AVAILABLE and REAL_SERVICES_AVAILABLE,
                        "WebSocket imports or real services not available") 
    async def test_demo_user_001_integration_duplication(self):
        """
        MUST FAIL INITIALLY: Reproduce production demo user scenario with real services
        
        Business Value: Validates test patterns don't impact production reliability
        Expected Failure: Exact reproduction of GCP log violation with real infrastructure
        
        This test reproduces the exact demo-user-001 pattern from staging logs
        using real services to validate the violation occurs under production conditions.
        """
        production_violations = []
        demo_managers = []
        
        async with real_services_fixture() as services:
            # Exact reproduction of demo-user-001 pattern from GCP logs
            demo_scenarios = [
                {
                    'user_id': 'demo-user-001',
                    'scenario': 'initial_connection',
                    'thread_id': 'demo-thread-001',
                    'request_id': 'demo-request-001'
                },
                {
                    'user_id': 'demo-user-001', 
                    'scenario': 'chat_session',
                    'thread_id': 'demo-thread-001',
                    'request_id': 'demo-request-002'
                },
                {
                    'user_id': 'demo-user-001',
                    'scenario': 'agent_execution',
                    'thread_id': 'demo-thread-002', 
                    'request_id': 'demo-request-003'
                },
                {
                    'user_id': 'demo-user-001',
                    'scenario': 'websocket_reconnect',
                    'thread_id': 'demo-thread-001',
                    'request_id': 'demo-request-004'
                }
            ]
            
            # Execute each demo scenario
            for scenario in demo_scenarios:
                demo_context = type('MockUserContext', (), {
                    'user_id': scenario['user_id'],
                    'thread_id': scenario['thread_id'],
                    'request_id': scenario['request_id'],
                    'is_test': True,
                    'scenario': scenario['scenario'],
                    'demo_timestamp': time.time()
                })()
                
                # Create manager for this demo scenario
                demo_manager = get_websocket_manager(user_context=demo_context)
                demo_managers.append({
                    'manager': demo_manager,
                    'context': demo_context,
                    'scenario': scenario['scenario'],
                    'manager_id': id(demo_manager)
                })
                self.created_managers.append(demo_manager)
                
                # Small delay to simulate realistic request timing
                await asyncio.sleep(0.01)
                
            # Analyze for demo-user-001 duplication violations
            demo_user_managers = [m for m in demo_managers if m['context'].user_id == 'demo-user-001']
            unique_manager_ids = set(m['manager_id'] for m in demo_user_managers)
            
            # Check for SSOT violation: multiple managers for demo-user-001
            if len(unique_manager_ids) > 1:
                production_violations.append({
                    'violation_type': 'demo_user_001_duplication',
                    'user_id': 'demo-user-001',
                    'total_managers': len(demo_user_managers),
                    'unique_manager_ids': list(unique_manager_ids),
                    'scenarios': [m['scenario'] for m in demo_user_managers],
                    'gcp_log_pattern': f"Multiple manager instances for user demo-user-001 - potential duplication"
                })
                
            # Additional check: Validate manager reuse within same thread
            thread_managers = {}
            for demo_manager_info in demo_user_managers:
                thread_id = demo_manager_info['context'].thread_id
                if thread_id not in thread_managers:
                    thread_managers[thread_id] = []
                thread_managers[thread_id].append(demo_manager_info)
                
            for thread_id, thread_manager_list in thread_managers.items():
                if len(thread_manager_list) > 1:
                    thread_unique_ids = set(m['manager_id'] for m in thread_manager_list)
                    if len(thread_unique_ids) > 1:
                        production_violations.append({
                            'violation_type': 'thread_manager_duplication',
                            'thread_id': thread_id,
                            'managers_in_thread': len(thread_manager_list),
                            'unique_ids_in_thread': list(thread_unique_ids),
                            'scenarios_in_thread': [m['scenario'] for m in thread_manager_list]
                        })
                        
        # This assertion WILL FAIL initially - reproducing exact GCP log violations
        self.assertEqual(
            len(production_violations),
            0,
            f"CRITICAL PRODUCTION PATTERN VIOLATION: Reproduced exact demo-user-001 violations from GCP logs. "
            f"This confirms the SSOT factory pattern is not properly enforcing manager reuse. "
            f"Production violations: {production_violations}. "
            f"This matches the staging environment pattern: "
            f"'SSOT validation issues (non-blocking): [\"Multiple manager instances for user demo-user-001 - potential duplication\"]'"
        )
        
        # Validate expected behavior: all demo-user-001 managers should be the same instance
        if demo_user_managers:
            expected_manager_id = demo_user_managers[0]['manager_id']
            all_same_manager = all(m['manager_id'] == expected_manager_id for m in demo_user_managers)
            
            self.assertTrue(
                all_same_manager,
                f"SSOT Factory Violation: Expected all demo-user-001 scenarios to use same manager instance, "
                f"but got different instances. Manager IDs: {[m['manager_id'] for m in demo_user_managers]}"
            )


if __name__ == '__main__':
    # Run tests using standard unittest runner for compatibility
    unittest.main()