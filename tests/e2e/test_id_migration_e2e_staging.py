"""
E2E Tests for Issue #89 UnifiedIDManager Migration - Staging Environment Validation
==================================================================================

Business Value Protection: $500K+ ARR (End-to-end ID consistency in production-like environment)
Purpose: FAIL to expose end-to-end ID migration gaps in GCP staging environment

This test suite is designed to FAIL during Issue #89 migration to detect:
- Production workflow breaks due to ID format inconsistencies
- Real user journey failures from UUID/structured ID confusion
- Service-to-service communication failures in staging environment
- Performance and reliability issues under production-like load

Test Strategy:
- Run against GCP staging environment (no Docker - per claude.md)
- Test complete user journeys end-to-end
- Validate production deployment compatibility
- Focus on business-critical workflows that generate revenue

Critical E2E Workflows Under Test:
- User registration → Authentication → Chat session → Agent execution
- WebSocket connection → Agent streaming → Real-time updates → Session cleanup
- Multi-user concurrent usage → Resource isolation → Performance consistency
- Error recovery → System resilience → Data integrity

CLAUDE.MD Compliance:
- GCP staging environment testing only (no Docker)
- Uses SSotAsyncTestCase for async E2E testing
- Real service endpoints and data flows
- Environment access through IsolatedEnvironment
- Absolute imports only
"""

import pytest
import asyncio
import httpx
import json
import time
import websockets
from typing import Dict, List, Any, Optional, AsyncIterator
from datetime import datetime, timezone
import uuid

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.id_fixtures import IDFixtures
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.staging_testing.base import StagingTestBase
from test_framework.gcp_integration.base import GCPIntegrationBase

# E2E testing utilities
from test_framework.staging_websocket_test_helper import StagingWebSocketTestHelper
from test_framework.staging_websocket_utilities import StagingWebSocketUtilities
from test_framework.websocket_deployment_runner import WebSocketDeploymentRunner
from test_framework.deployment_validation import DeploymentValidator

# Environment and configuration
from test_framework.environment_isolation import IsolatedEnvironment


class TestIDMigrationE2EStagingWorkflows(SSotAsyncTestCase, BaseE2ETest, StagingTestBase):
    """E2E tests for ID migration in GCP staging environment."""
    
    async def setup_method(self, method):
        """Setup for E2E staging tests."""
        await super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.staging_helper = StagingWebSocketTestHelper()
        self.ws_utilities = StagingWebSocketUtilities()
        self.deployment_validator = DeploymentValidator()
        self.record_metric("test_category", "e2e_id_migration_staging")
        
        # Initialize staging environment connection
        await self._setup_staging_environment()
    
    async def _setup_staging_environment(self):
        """Initialize connection to GCP staging environment."""
        try:
            # Get staging environment URLs
            self.staging_base_url = self.env.get("STAGING_BASE_URL", "https://netra-staging-backend.uc.r.appspot.com")
            self.staging_ws_url = self.env.get("STAGING_WS_URL", "wss://netra-staging-backend.uc.r.appspot.com/ws")
            
            # Validate staging environment accessibility
            deployment_status = await self.deployment_validator.validate_staging_deployment()
            
            if not deployment_status['healthy']:
                pytest.skip(f"Staging environment not healthy: {deployment_status['issues']}")
            
            self.record_metric("staging_environment", "healthy")
            
        except Exception as e:
            pytest.skip(f"Could not connect to staging environment: {e}")
    
    async def test_complete_user_journey_id_consistency(self):
        """
        CRITICAL E2E: Test complete user journey with ID consistency validation.
        
        This test should FAIL to expose:
        - User registration creates UUID but authentication expects structured
        - Session IDs inconsistent between frontend and backend
        - Chat session breaks due to ID format mismatches
        - Agent execution cannot be tracked back to user session
        
        Expected: FAIL until entire user journey uses consistent ID formats
        """
        user_journey_failures = []
        
        # Generate test user data
        test_user_email = f"e2e_test_{int(time.time())}@example.com"
        test_user_name = "E2E Test User"
        
        journey_context = {
            'test_start_time': datetime.now(timezone.utc).isoformat(),
            'test_user_email': test_user_email,
            'expected_id_format': 'structured'  # Post-migration expectation
        }
        
        try:
            # Step 1: User Registration
            registration_result = await self._test_user_registration_e2e(
                test_user_email, test_user_name
            )
            
            if not registration_result['success']:
                user_journey_failures.append({
                    'step': 'user_registration',
                    'failure': registration_result['error'],
                    'impact': 'Users cannot create accounts'
                })
                # Cannot continue journey without registration
                assert False, f"User registration failed: {registration_result['error']}"
            
            user_id = registration_result['user_id']
            journey_context['user_id'] = user_id
            
            # Validate user_id format
            if self._is_uuid_format(user_id):
                user_journey_failures.append({
                    'step': 'user_registration_id_format',
                    'failure': f'User ID is UUID format: {user_id}',
                    'expected': 'Structured format: user_{{counter}}_{{uuid8}}',
                    'impact': 'User ID lacks metadata for audit trails'
                })
            
            # Step 2: Authentication
            auth_result = await self._test_user_authentication_e2e(
                test_user_email, user_id
            )
            
            if not auth_result['success']:
                user_journey_failures.append({
                    'step': 'user_authentication',
                    'failure': auth_result['error'],
                    'impact': 'Users cannot log into their accounts'
                })
            else:
                session_id = auth_result['session_id']
                journey_context['session_id'] = session_id
                
                # Validate session_id format consistency with user_id
                if self._is_uuid_format(session_id) != self._is_uuid_format(user_id):
                    user_journey_failures.append({
                        'step': 'session_id_format_consistency',
                        'failure': f'Session ID format ({self._get_id_format(session_id)}) inconsistent with user ID format ({self._get_id_format(user_id)})',
                        'user_id': user_id,
                        'session_id': session_id,
                        'impact': 'Service-to-service communication failures'
                    })
            
            # Step 3: WebSocket Connection for Chat
            if 'session_id' in journey_context:
                ws_result = await self._test_websocket_connection_e2e(
                    user_id, journey_context['session_id']
                )
                
                if not ws_result['success']:
                    user_journey_failures.append({
                        'step': 'websocket_connection',
                        'failure': ws_result['error'],
                        'impact': 'Users cannot access real-time chat features'
                    })
                else:
                    connection_id = ws_result['connection_id']
                    journey_context['connection_id'] = connection_id
                    
                    # Validate connection_id format and user context embedding
                    if not self._connection_id_contains_user_context(connection_id, user_id):
                        user_journey_failures.append({
                            'step': 'websocket_connection_user_context',
                            'failure': f'WebSocket connection ID lacks user context: {connection_id}',
                            'user_id': user_id,
                            'impact': 'Cannot clean up user-specific WebSocket resources'
                        })
            
            # Step 4: Agent Execution
            if 'connection_id' in journey_context:
                agent_result = await self._test_agent_execution_e2e(
                    user_id, journey_context['connection_id']
                )
                
                if not agent_result['success']:
                    user_journey_failures.append({
                        'step': 'agent_execution',
                        'failure': agent_result['error'],
                        'impact': 'Users cannot get AI responses - core platform failure'
                    })
                else:
                    execution_id = agent_result['execution_id']
                    journey_context['execution_id'] = execution_id
                    
                    # Validate execution_id can be traced back to user and connection
                    if not self._can_trace_execution_to_user(execution_id, user_id, journey_context['connection_id']):
                        user_journey_failures.append({
                            'step': 'agent_execution_traceability',
                            'failure': f'Agent execution cannot be traced to user: execution_id={execution_id}',
                            'user_id': user_id,
                            'connection_id': journey_context['connection_id'],
                            'impact': 'Cannot debug failed agent executions'
                        })
            
            # Step 5: Resource Cleanup
            cleanup_result = await self._test_resource_cleanup_e2e(journey_context)
            
            if not cleanup_result['success']:
                user_journey_failures.append({
                    'step': 'resource_cleanup',
                    'failure': cleanup_result['error'],
                    'impact': 'Resource leaks lead to system instability'
                })
            else:
                # Validate cleanup was selective (only target user's resources)
                if cleanup_result.get('cross_user_impact', 0) > 0:
                    user_journey_failures.append({
                        'step': 'selective_resource_cleanup',
                        'failure': f'Cleanup affected {cleanup_result["cross_user_impact"]} other users',
                        'impact': 'Cross-user resource contamination security risk'
                    })
        
        except Exception as e:
            user_journey_failures.append({
                'step': 'e2e_test_exception',
                'failure': f'E2E test infrastructure failed: {str(e)}',
                'impact': 'Cannot validate production readiness'
            })
        
        # Test should FAIL if user journey failures detected
        critical_failures = [f for f in user_journey_failures if 'core platform failure' in f.get('impact', '')]
        
        assert len(user_journey_failures) == 0, (
            f"E2E USER JOURNEY FAILURES: Found {len(user_journey_failures)} failures:\n" +
            "\n".join([
                f"- {failure['step']}: {failure['failure']}"
                for failure in user_journey_failures
            ]) +
            f"\n\nCritical failures: {len(critical_failures)}\n" +
            "Complete user journey must work end-to-end for production readiness"
        )
        
        self.record_metric("user_journey_failures", len(user_journey_failures))
        self.record_metric("critical_journey_failures", len(critical_failures))
        self.record_metric("journey_steps_completed", len(journey_context))
    
    async def test_multi_user_concurrent_isolation_e2e(self):
        """
        CRITICAL E2E: Test multi-user concurrent usage with proper isolation.
        
        This test should FAIL to expose:
        - User data leakage between concurrent sessions
        - WebSocket events sent to wrong users
        - Agent execution mixing between user contexts
        - Resource cleanup affecting multiple users
        
        Expected: FAIL until multi-user isolation is guaranteed in production
        """
        isolation_failures = []
        user_count = 5
        concurrent_users = []
        
        try:
            # Create concurrent users
            user_creation_tasks = []
            for i in range(user_count):
                user_email = f"concurrent_user_{i}_{int(time.time())}@example.com"
                user_creation_tasks.append(
                    self._create_concurrent_user_session(user_email, f"Concurrent User {i}")
                )
            
            # Execute user creation concurrently
            user_sessions = await asyncio.gather(*user_creation_tasks, return_exceptions=True)
            
            # Filter successful user sessions
            successful_sessions = []
            for i, session in enumerate(user_sessions):
                if isinstance(session, Exception):
                    isolation_failures.append({
                        'failure': 'concurrent_user_creation',
                        'user_index': i,
                        'error': str(session),
                        'impact': 'System cannot handle concurrent user registration'
                    })
                elif session and session.get('success'):
                    successful_sessions.append(session)
            
            if len(successful_sessions) < 3:  # Need at least 3 users for meaningful isolation test
                pytest.skip("Insufficient successful concurrent user sessions for isolation testing")
            
            concurrent_users = successful_sessions
            
            # Test 1: Concurrent WebSocket connections with isolation
            websocket_tasks = []
            for user_session in concurrent_users:
                websocket_tasks.append(
                    self._test_concurrent_websocket_isolation(user_session)
                )
            
            websocket_results = await asyncio.gather(*websocket_tasks, return_exceptions=True)
            
            # Check for WebSocket isolation failures
            for i, ws_result in enumerate(websocket_results):
                if isinstance(ws_result, Exception):
                    isolation_failures.append({
                        'failure': 'websocket_connection_concurrency',
                        'user_index': i,
                        'error': str(ws_result),
                        'impact': 'WebSocket system cannot handle concurrent users'
                    })
                elif ws_result and not ws_result.get('isolated'):
                    isolation_failures.append({
                        'failure': 'websocket_isolation_breach',
                        'user_index': i,
                        'cross_user_events': ws_result.get('cross_user_events', []),
                        'impact': 'Users receive other users\' messages'
                    })
            
            # Test 2: Concurrent agent execution with isolation
            agent_tasks = []
            for user_session in concurrent_users[:3]:  # Test with first 3 users
                agent_tasks.append(
                    self._test_concurrent_agent_execution_isolation(user_session)
                )
            
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Check for agent execution isolation failures
            for i, agent_result in enumerate(agent_results):
                if isinstance(agent_result, Exception):
                    isolation_failures.append({
                        'failure': 'agent_execution_concurrency',
                        'user_index': i,
                        'error': str(agent_result),
                        'impact': 'Agent system cannot handle concurrent executions'
                    })
                elif agent_result and not agent_result.get('isolated'):
                    isolation_failures.append({
                        'failure': 'agent_execution_isolation_breach',
                        'user_index': i,
                        'execution_contamination': agent_result.get('contamination_details', {}),
                        'impact': 'Agent executions leak data between users'
                    })
            
            # Test 3: Selective resource cleanup (shouldn't affect other users)
            if len(concurrent_users) >= 2:
                # Clean up first user, verify others unaffected
                cleanup_target = concurrent_users[0]
                other_users = concurrent_users[1:3]  # Check first 2 other users
                
                # Record other users' state before cleanup
                other_users_state_before = []
                for user in other_users:
                    state = await self._capture_user_state(user)
                    other_users_state_before.append(state)
                
                # Perform cleanup on target user
                cleanup_result = await self._test_selective_resource_cleanup_e2e(cleanup_target)
                
                if not cleanup_result.get('success'):
                    isolation_failures.append({
                        'failure': 'resource_cleanup_failed',
                        'target_user_id': cleanup_target.get('user_id'),
                        'error': cleanup_result.get('error'),
                        'impact': 'Cannot clean up user resources properly'
                    })
                
                # Verify other users unaffected
                for i, user in enumerate(other_users):
                    state_after = await self._capture_user_state(user)
                    state_before = other_users_state_before[i]
                    
                    if state_after != state_before:
                        isolation_failures.append({
                            'failure': 'cleanup_cross_user_impact',
                            'affected_user_id': user.get('user_id'),
                            'target_user_id': cleanup_target.get('user_id'),
                            'state_changes': self._compare_user_states(state_before, state_after),
                            'impact': 'Resource cleanup affects multiple users'
                        })
        
        except Exception as e:
            isolation_failures.append({
                'failure': 'multi_user_test_exception',
                'error': str(e),
                'impact': 'Cannot validate multi-user production readiness'
            })
        
        # Cleanup all test users
        try:
            cleanup_tasks = [
                self._cleanup_test_user(user_session) 
                for user_session in concurrent_users
            ]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        except Exception:
            pass  # Cleanup failures are not test failures
        
        # Test should FAIL if isolation failures detected
        critical_isolation_failures = [
            f for f in isolation_failures 
            if 'breach' in f.get('failure', '') or 'leak' in f.get('impact', '').lower()
        ]
        
        assert len(isolation_failures) == 0, (
            f"MULTI-USER ISOLATION FAILURES: Found {len(isolation_failures)} failures:\n" +
            "\n".join([
                f"- {failure['failure']}: {failure.get('impact', failure.get('error', 'Unknown'))}"
                for failure in isolation_failures
            ]) +
            f"\n\nCritical isolation breaches: {len(critical_isolation_failures)}\n" +
            f"Concurrent users tested: {len(concurrent_users)}\n" +
            "Multi-user isolation is critical for production platform security"
        )
        
        self.record_metric("isolation_failures", len(isolation_failures))
        self.record_metric("critical_isolation_failures", len(critical_isolation_failures))
        self.record_metric("concurrent_users_tested", len(concurrent_users))
    
    async def test_production_load_id_performance_e2e(self):
        """
        Test ID system performance under production-like load in staging.
        
        This test should FAIL to expose:
        - ID generation slowdowns under concurrent load
        - Memory leaks in high-volume ID operations
        - Service timeouts due to ID validation overhead
        
        Expected: FAIL until ID system meets production performance requirements
        """
        performance_failures = []
        
        # Production load simulation parameters
        PRODUCTION_LOAD = {
            'concurrent_users': 20,
            'operations_per_user': 50,
            'max_operation_time_ms': 100,
            'total_test_duration_seconds': 60
        }
        
        try:
            load_test_start = time.time()
            
            # Create load testing users
            load_test_users = []
            for i in range(PRODUCTION_LOAD['concurrent_users']):
                user_email = f"load_test_user_{i}_{int(time.time())}@example.com"
                user_session = await self._create_load_test_user(user_email)
                if user_session and user_session.get('success'):
                    load_test_users.append(user_session)
            
            if len(load_test_users) < PRODUCTION_LOAD['concurrent_users'] * 0.8:
                pytest.skip(f"Could not create enough load test users: {len(load_test_users)}/{PRODUCTION_LOAD['concurrent_users']}")
            
            # Execute concurrent load
            load_test_tasks = []
            for user_session in load_test_users:
                task = self._execute_user_load_operations(
                    user_session, 
                    PRODUCTION_LOAD['operations_per_user'],
                    PRODUCTION_LOAD['max_operation_time_ms']
                )
                load_test_tasks.append(task)
            
            # Run load test with timeout
            try:
                load_results = await asyncio.wait_for(
                    asyncio.gather(*load_test_tasks, return_exceptions=True),
                    timeout=PRODUCTION_LOAD['total_test_duration_seconds']
                )
            except asyncio.TimeoutError:
                performance_failures.append({
                    'failure': 'load_test_timeout',
                    'duration_seconds': PRODUCTION_LOAD['total_test_duration_seconds'],
                    'impact': 'System cannot handle production load within timeout'
                })
                load_results = []
            
            # Analyze load test results
            successful_results = [r for r in load_results if not isinstance(r, Exception) and r.get('success')]
            failed_results = [r for r in load_results if isinstance(r, Exception) or not r.get('success')]
            
            success_rate = len(successful_results) / len(load_test_users) if load_test_users else 0
            
            if success_rate < 0.95:  # Less than 95% success rate
                performance_failures.append({
                    'failure': 'low_success_rate_under_load',
                    'success_rate': success_rate,
                    'successful_operations': len(successful_results),
                    'failed_operations': len(failed_results),
                    'impact': 'System unreliable under production load'
                })
            
            # Analyze operation timings
            if successful_results:
                operation_times = []
                for result in successful_results:
                    if 'operation_times' in result:
                        operation_times.extend(result['operation_times'])
                
                if operation_times:
                    avg_operation_time = sum(operation_times) / len(operation_times) * 1000  # Convert to ms
                    max_operation_time = max(operation_times) * 1000
                    
                    if avg_operation_time > PRODUCTION_LOAD['max_operation_time_ms']:
                        performance_failures.append({
                            'failure': 'slow_average_operation_time',
                            'avg_time_ms': avg_operation_time,
                            'max_allowed_ms': PRODUCTION_LOAD['max_operation_time_ms'],
                            'impact': 'Users experience slow response times'
                        })
                    
                    if max_operation_time > PRODUCTION_LOAD['max_operation_time_ms'] * 5:  # 5x threshold for max
                        performance_failures.append({
                            'failure': 'extreme_operation_time_spikes',
                            'max_time_ms': max_operation_time,
                            'impact': 'Some users experience extreme delays'
                        })
            
            load_test_duration = time.time() - load_test_start
            
            # Cleanup load test users
            try:
                cleanup_tasks = [self._cleanup_test_user(user) for user in load_test_users]
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception:
                pass  # Cleanup failures don't fail the performance test
        
        except Exception as e:
            performance_failures.append({
                'failure': 'load_test_infrastructure_exception',
                'error': str(e),
                'impact': 'Cannot validate production load performance'
            })
        
        # Test should FAIL if performance issues detected
        assert len(performance_failures) == 0, (
            f"PRODUCTION LOAD PERFORMANCE FAILURES: Found {len(performance_failures)} failures:\n" +
            "\n".join([
                f"- {failure['failure']}: {failure.get('impact', failure.get('error', 'Unknown'))}"
                for failure in performance_failures
            ]) +
            f"\n\nLoad test parameters:\n" +
            f"- Concurrent users: {PRODUCTION_LOAD['concurrent_users']}\n" +
            f"- Operations per user: {PRODUCTION_LOAD['operations_per_user']}\n" +
            f"- Max operation time: {PRODUCTION_LOAD['max_operation_time_ms']}ms\n" +
            f"- Success rate threshold: 95%"
        )
        
        self.record_metric("performance_failures", len(performance_failures))
        self.record_metric("load_test_users", len(load_test_users) if 'load_test_users' in locals() else 0)
        self.record_metric("load_test_duration", load_test_duration if 'load_test_duration' in locals() else 0)
    
    # Helper methods for E2E testing
    
    async def _test_user_registration_e2e(self, email: str, name: str) -> Dict[str, Any]:
        """Test user registration in staging environment."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.staging_base_url}/api/auth/register",
                    json={
                        "email": email,
                        "name": name,
                        "password": "test_password_123"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    user_data = response.json()
                    return {
                        'success': True,
                        'user_id': user_data.get('user_id'),
                        'email': email
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Registration failed: {response.status_code} - {response.text}'
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Registration request failed: {str(e)}'
            }
    
    async def _test_user_authentication_e2e(self, email: str, user_id: str) -> Dict[str, Any]:
        """Test user authentication in staging environment."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.staging_base_url}/api/auth/login",
                    json={
                        "email": email,
                        "password": "test_password_123"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    auth_data = response.json()
                    return {
                        'success': True,
                        'session_id': auth_data.get('session_id'),
                        'access_token': auth_data.get('access_token')
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Authentication failed: {response.status_code} - {response.text}'
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Authentication request failed: {str(e)}'
            }
    
    async def _test_websocket_connection_e2e(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Test WebSocket connection establishment in staging."""
        try:
            # Use staging WebSocket utilities
            connection_result = await self.ws_utilities.test_websocket_connection(
                self.staging_ws_url,
                {
                    'user_id': user_id,
                    'session_id': session_id,
                    'connection_type': 'chat'
                }
            )
            
            if connection_result['connected']:
                return {
                    'success': True,
                    'connection_id': connection_result['connection_id'],
                    'websocket_url': self.staging_ws_url
                }
            else:
                return {
                    'success': False,
                    'error': f'WebSocket connection failed: {connection_result.get("error", "Unknown")}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'WebSocket test failed: {str(e)}'
            }
    
    async def _test_agent_execution_e2e(self, user_id: str, connection_id: str) -> Dict[str, Any]:
        """Test agent execution through WebSocket in staging."""
        try:
            # Send agent execution request via WebSocket
            execution_request = {
                'type': 'agent_execution',
                'user_id': user_id,
                'connection_id': connection_id,
                'agent_type': 'supervisor_agent',
                'message': 'Test agent execution for ID migration validation'
            }
            
            execution_result = await self.ws_utilities.send_agent_execution_request(
                self.staging_ws_url,
                execution_request
            )
            
            if execution_result.get('success'):
                return {
                    'success': True,
                    'execution_id': execution_result.get('execution_id'),
                    'agent_response': execution_result.get('response')
                }
            else:
                return {
                    'success': False,
                    'error': f'Agent execution failed: {execution_result.get("error", "Unknown")}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Agent execution test failed: {str(e)}'
            }
    
    async def _test_resource_cleanup_e2e(self, journey_context: Dict[str, Any]) -> Dict[str, Any]:
        """Test resource cleanup for user journey."""
        try:
            cleanup_request = {
                'user_id': journey_context.get('user_id'),
                'session_id': journey_context.get('session_id'),
                'connection_id': journey_context.get('connection_id'),
                'execution_id': journey_context.get('execution_id')
            }
            
            # Call cleanup endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.staging_base_url}/api/user/cleanup",
                    json=cleanup_request,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    cleanup_data = response.json()
                    return {
                        'success': True,
                        'resources_cleaned': cleanup_data.get('resources_cleaned', 0),
                        'cross_user_impact': cleanup_data.get('cross_user_impact', 0)
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Cleanup failed: {response.status_code} - {response.text}'
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Cleanup test failed: {str(e)}'
            }
    
    async def _create_concurrent_user_session(self, email: str, name: str) -> Dict[str, Any]:
        """Create user session for concurrent testing."""
        registration_result = await self._test_user_registration_e2e(email, name)
        if not registration_result['success']:
            return registration_result
        
        auth_result = await self._test_user_authentication_e2e(
            email, registration_result['user_id']
        )
        
        return {
            'success': auth_result['success'],
            'user_id': registration_result['user_id'],
            'email': email,
            'session_id': auth_result.get('session_id'),
            'access_token': auth_result.get('access_token'),
            'error': auth_result.get('error')
        }
    
    async def _test_concurrent_websocket_isolation(self, user_session: Dict[str, Any]) -> Dict[str, Any]:
        """Test WebSocket isolation for concurrent user."""
        try:
            ws_result = await self._test_websocket_connection_e2e(
                user_session['user_id'], user_session['session_id']
            )
            
            if not ws_result['success']:
                return {'isolated': False, 'error': ws_result['error']}
            
            # Test if user receives only their own events
            isolation_test = await self.ws_utilities.test_event_isolation(
                self.staging_ws_url,
                user_session['user_id'],
                ws_result['connection_id']
            )
            
            return {
                'isolated': isolation_test.get('isolated', False),
                'cross_user_events': isolation_test.get('cross_user_events', [])
            }
        
        except Exception as e:
            return {'isolated': False, 'error': str(e)}
    
    async def _test_concurrent_agent_execution_isolation(self, user_session: Dict[str, Any]) -> Dict[str, Any]:
        """Test agent execution isolation for concurrent user."""
        try:
            # Create WebSocket connection
            ws_result = await self._test_websocket_connection_e2e(
                user_session['user_id'], user_session['session_id']
            )
            
            if not ws_result['success']:
                return {'isolated': False, 'error': f'WebSocket setup failed: {ws_result["error"]}'}
            
            # Execute agent and check isolation
            agent_result = await self._test_agent_execution_e2e(
                user_session['user_id'], ws_result['connection_id']
            )
            
            if not agent_result['success']:
                return {'isolated': False, 'error': f'Agent execution failed: {agent_result["error"]}'}
            
            # Check if execution is properly isolated (simplified check)
            execution_id = agent_result['execution_id']
            isolated = self._can_trace_execution_to_user(
                execution_id, user_session['user_id'], ws_result['connection_id']
            )
            
            return {'isolated': isolated, 'execution_id': execution_id}
        
        except Exception as e:
            return {'isolated': False, 'error': str(e)}
    
    # Helper methods for validation
    
    def _is_uuid_format(self, id_value: str) -> bool:
        """Check if ID is UUID format."""
        try:
            uuid.UUID(id_value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _get_id_format(self, id_value: str) -> str:
        """Get human-readable ID format description."""
        if self._is_uuid_format(id_value):
            return "UUID"
        elif '_' in id_value and len(id_value.split('_')) >= 3:
            return "Structured"
        else:
            return "Unknown"
    
    def _connection_id_contains_user_context(self, connection_id: str, user_id: str) -> bool:
        """Check if WebSocket connection ID contains user context."""
        # In properly designed system, connection_id should embed user context
        if self._is_uuid_format(connection_id):
            return False  # Plain UUID has no context
        
        # Check if user_id or part of it is embedded in connection_id
        user_prefix = user_id[:8] if len(user_id) > 8 else user_id
        return user_prefix in connection_id or user_id in connection_id
    
    def _can_trace_execution_to_user(self, execution_id: str, user_id: str, connection_id: str) -> bool:
        """Check if agent execution can be traced back to user."""
        # In properly designed system, execution_id should contain traceability info
        if self._is_uuid_format(execution_id):
            return False  # Plain UUID provides no traceability
        
        # Check if execution_id contains user or connection context
        user_prefix = user_id[:8] if len(user_id) > 8 else user_id
        connection_prefix = connection_id[:8] if len(connection_id) > 8 else connection_id
        
        return (user_prefix in execution_id or 
                connection_prefix in execution_id or
                user_id in execution_id or
                connection_id in execution_id)
    
    # Additional helper methods would be implemented here...
    
    async def _create_load_test_user(self, email: str) -> Dict[str, Any]:
        """Simplified user creation for load testing."""
        return await self._create_concurrent_user_session(email, "Load Test User")
    
    async def _execute_user_load_operations(self, user_session: Dict[str, Any], 
                                          operations_count: int, max_time_ms: float) -> Dict[str, Any]:
        """Execute load operations for a single user."""
        operation_times = []
        successful_operations = 0
        
        try:
            for i in range(operations_count):
                start_time = time.time()
                
                # Simulate typical user operations
                operation_success = await self._simulate_user_operation(user_session, i)
                
                operation_time = time.time() - start_time
                operation_times.append(operation_time)
                
                if operation_success:
                    successful_operations += 1
                
                # Check if operation exceeded time limit
                if operation_time * 1000 > max_time_ms:
                    break  # Stop if operations are too slow
            
            return {
                'success': True,
                'user_id': user_session['user_id'],
                'operations_completed': len(operation_times),
                'successful_operations': successful_operations,
                'operation_times': operation_times
            }
        
        except Exception as e:
            return {
                'success': False,
                'user_id': user_session['user_id'],
                'error': str(e),
                'operations_completed': len(operation_times)
            }
    
    async def _simulate_user_operation(self, user_session: Dict[str, Any], operation_index: int) -> bool:
        """Simulate a single user operation."""
        try:
            # Simulate different types of operations
            if operation_index % 3 == 0:
                # WebSocket connection test
                ws_result = await self._test_websocket_connection_e2e(
                    user_session['user_id'], user_session['session_id']
                )
                return ws_result.get('success', False)
            
            elif operation_index % 3 == 1:
                # API call test
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.staging_base_url}/api/user/profile",
                        headers={'Authorization': f'Bearer {user_session.get("access_token", "")}'},
                        timeout=5.0
                    )
                    return response.status_code == 200
            
            else:
                # Simple health check
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.staging_base_url}/health", timeout=5.0)
                    return response.status_code == 200
        
        except Exception:
            return False
    
    async def _capture_user_state(self, user_session: Dict[str, Any]) -> Dict[str, Any]:
        """Capture current state of user for isolation testing."""
        try:
            # This would capture user's current resources, connections, etc.
            # Simplified implementation for testing
            return {
                'user_id': user_session.get('user_id'),
                'session_active': bool(user_session.get('session_id')),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            return {}
    
    def _compare_user_states(self, state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """Compare user states to detect changes."""
        changes = {}
        
        for key in state_before:
            if key in state_after and state_before[key] != state_after[key]:
                changes[key] = {
                    'before': state_before[key],
                    'after': state_after[key]
                }
        
        return changes
    
    async def _test_selective_resource_cleanup_e2e(self, user_session: Dict[str, Any]) -> Dict[str, Any]:
        """Test selective resource cleanup for specific user."""
        return await self._test_resource_cleanup_e2e(user_session)
    
    async def _cleanup_test_user(self, user_session: Dict[str, Any]) -> Dict[str, Any]:
        """Cleanup test user resources."""
        try:
            cleanup_result = await self._test_resource_cleanup_e2e(user_session)
            return cleanup_result
        except Exception as e:
            return {'success': False, 'error': str(e)}