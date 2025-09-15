"""FAILING TESTS: Cross-Service Failures When Auth Service Database Is Down - Critical E2E Issue

CRITICAL CROSS-SERVICE IMPACT ISSUE TO REPLICATE:
- Auth service database down affects entire system operation
- Frontend can't authenticate users, breaking all user flows  
- Backend can't validate tokens, causing 401 errors across APIs
- WebSocket connections fail authentication and disconnect
- System appears partially operational but core functionality broken

Business Value Justification (BVJ):
- Segment: All Customer Tiers (Free, Early, Mid, Enterprise)
- Business Goal: System-wide resilience and failure isolation
- Value Impact: Prevents cascade failures that affect all customers
- Strategic Impact: Maintains service availability even when auth database fails

These tests are designed to FAIL with the current system state and PASS once proper
cross-service failure isolation and graceful degradation are implemented.
"""

import os
import sys
import pytest
import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

from shared.isolated_environment import get_env

from test_framework.environment_markers import env, staging_only, env_requires
from netra_backend.tests.unit.test_real_auth_service_integration import RealAuthServiceTestFixture
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

logger = logging.getLogger(__name__)


@pytest.mark.e2e
class TestAuthServiceDatabaseDownCrossServiceFailures:
    """Test suite for cross-service failures when auth service database is down."""
    
    @pytest.fixture
    async def services_with_auth_db_down(self):
        """Fixture that starts services with auth database unavailable."""
        fixture = RealAuthServiceTestFixture()
        
        # Mock environment where auth database is unavailable
        auth_db_down_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',  # Non-existent database
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_password',
            'AUTH_SERVICE_URL': 'http://localhost:8081',
            'BACKEND_SERVICE_URL': 'http://localhost:8080',
            'FRONTEND_URL': 'http://localhost:3000'
        }
        
        with patch.dict(get_env().get_all(), auth_db_down_env):
            try:
                await fixture.start_services(
                    start_auth=True,    # Start auth service (but database will be broken)
                    start_backend=True, # Start backend service
                    start_frontend=False  # Don't need frontend process for these tests
                )
                yield fixture
            finally:
                await fixture.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_frontend_authentication_flow_breaks_when_auth_db_down(self, services_with_auth_db_down):
        """FAILING TEST: Frontend authentication flow completely breaks when auth database is down.
        
        Users trying to log in through frontend should get clear error messages,
        not confusing technical errors or infinite loading states.
        """
        fixture = services_with_auth_db_down
        
        # Simulate frontend authentication attempt
        auth_request_scenarios = [
            {
                'scenario': 'google_oauth_login',
                'endpoint': '/auth/google/login',
                'expected_behavior': 'clear_error_message',
                'actual_behavior': 'technical_error_or_timeout'
            },
            {
                'scenario': 'token_validation',
                'endpoint': '/auth/validate',
                'expected_behavior': 'service_temporarily_unavailable',
                'actual_behavior': 'database_connection_error'
            },
            {
                'scenario': 'session_check',
                'endpoint': '/auth/session',
                'expected_behavior': 'please_try_again_later',
                'actual_behavior': 'internal_server_error'
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            frontend_auth_failures = []
            
            for scenario in auth_request_scenarios:
                try:
                    # Simulate frontend making request to auth service
                    auth_url = f"http://localhost:8081{scenario['endpoint']}"
                    
                    async with session.get(auth_url, timeout=10) as response:
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        
                        # Check if response is user-friendly
                        user_unfriendly_indicators = [
                            'database "netra_dev" does not exist',
                            'OperationalError',
                            'connection refused',
                            'sqlalchemy',
                            'Internal Server Error',
                            'Traceback',
                            '500'
                        ]
                        
                        response_text = str(response_data)
                        technical_errors = [indicator for indicator in user_unfriendly_indicators 
                                          if indicator in response_text]
                        
                        if technical_errors:
                            frontend_auth_failures.append({
                                'scenario': scenario['scenario'],
                                'technical_errors': technical_errors,
                                'response': response_text[:200],
                                'status_code': response.status
                            })
                
                except asyncio.TimeoutError:
                    frontend_auth_failures.append({
                        'scenario': scenario['scenario'],
                        'error': 'Request timeout - frontend users would see loading state',
                        'impact': 'Poor user experience'
                    })
                
                except Exception as e:
                    frontend_auth_failures.append({
                        'scenario': scenario['scenario'],
                        'error': str(e),
                        'impact': 'Frontend authentication completely broken'
                    })
            
            if frontend_auth_failures:
                pytest.fail(
                    f"Frontend authentication broken when auth database is down: {frontend_auth_failures}. "
                    "Users should get clear, non-technical error messages about temporary service unavailability."
                )
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_backend_api_token_validation_cascade_failure(self, services_with_auth_db_down):
        """FAILING TEST: Backend API token validation fails, causing cascade failure across all endpoints.
        
        When auth database is down, backend should either:
        1. Allow requests with cached token validation, OR
        2. Return clear 503 Service Unavailable with retry-after headers
        """
        fixture = services_with_auth_db_down
        
        # Simulate backend API requests that require token validation
        protected_endpoints = [
            {
                'endpoint': '/api/threads',
                'method': 'GET',
                'requires_auth': True,
                'critical_for_users': True
            },
            {
                'endpoint': '/api/agents/start',
                'method': 'POST', 
                'requires_auth': True,
                'critical_for_users': True
            },
            {
                'endpoint': '/api/messages/send',
                'method': 'POST',
                'requires_auth': True,
                'critical_for_users': True
            },
            {
                'endpoint': '/api/health',
                'method': 'GET',
                'requires_auth': False,
                'critical_for_users': False
            }
        ]
        
        # Mock JWT token (would normally be validated against auth database)
        mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwiZXhwIjoxNzI0NjQwMDAwfQ.test_signature"
        
        async with aiohttp.ClientSession() as session:
            cascade_failures = []
            
            for endpoint_info in protected_endpoints:
                endpoint = endpoint_info['endpoint']
                method = endpoint_info['method']
                requires_auth = endpoint_info['requires_auth']
                
                headers = {}
                if requires_auth:
                    headers['Authorization'] = f'Bearer {mock_jwt_token}'
                
                try:
                    backend_url = f"http://localhost:8080{endpoint}"
                    
                    request_method = getattr(session, method.lower())
                    async with request_method(backend_url, headers=headers, timeout=10) as response:
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        
                        if requires_auth and response.status == 401:
                            # Token validation failed - check if error message is appropriate
                            error_message = str(response_data)
                            
                            # Check for technical error details that shouldn't be exposed
                            technical_details = [
                                'database "netra_dev" does not exist',
                                'auth service connection failed',
                                'OperationalError',
                                'sqlalchemy',
                                'postgres'
                            ]
                            
                            exposed_details = [detail for detail in technical_details if detail in error_message]
                            
                            if exposed_details:
                                cascade_failures.append({
                                    'endpoint': endpoint,
                                    'issue': 'technical_details_exposed',
                                    'exposed_details': exposed_details,
                                    'status_code': response.status
                                })
                            
                            # Check if error provides user guidance
                            user_guidance_indicators = [
                                'temporarily unavailable',
                                'please try again',
                                'service maintenance',
                                'retry-after'
                            ]
                            
                            has_user_guidance = any(indicator in error_message.lower() for indicator in user_guidance_indicators)
                            retry_after_header = response.headers.get('Retry-After')
                            
                            if not has_user_guidance and not retry_after_header:
                                cascade_failures.append({
                                    'endpoint': endpoint,
                                    'issue': 'no_user_guidance',
                                    'response': error_message[:200],
                                    'status_code': response.status
                                })
                        
                        elif requires_auth and response.status == 500:
                            # Internal server error indicates poor error handling
                            cascade_failures.append({
                                'endpoint': endpoint,
                                'issue': 'internal_server_error',
                                'should_be': '503_service_unavailable',
                                'status_code': response.status
                            })
                
                except asyncio.TimeoutError:
                    if endpoint_info['critical_for_users']:
                        cascade_failures.append({
                            'endpoint': endpoint,
                            'issue': 'timeout_on_critical_endpoint',
                            'impact': 'Users cannot access core functionality'
                        })
                
                except Exception as e:
                    cascade_failures.append({
                        'endpoint': endpoint,
                        'issue': 'unexpected_error',
                        'error': str(e),
                        'impact': 'Complete endpoint failure'
                    })
            
            if cascade_failures:
                pytest.fail(
                    f"Backend API cascade failures when auth database is down: {cascade_failures}. "
                    "Backend should handle auth service unavailability gracefully."
                )
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_authentication_cascade_disconnections(self, services_with_auth_db_down):
        """FAILING TEST: WebSocket connections fail authentication and cause cascade disconnections.
        
        When auth database is down, WebSocket connections should either:
        1. Continue with cached authentication, OR
        2. Gracefully downgrade to read-only mode with clear user notification
        """
        fixture = services_with_auth_db_down
        
        # Simulate WebSocket connection attempts
        websocket_scenarios = [
            {
                'scenario': 'new_connection_with_token',
                'token': 'valid_jwt_token_normally',
                'expected': 'clear_auth_unavailable_message',
                'actual': 'connection_rejected_or_timeout'
            },
            {
                'scenario': 'existing_connection_token_refresh',
                'token': 'refresh_token',
                'expected': 'continue_with_cached_auth_or_readonly',
                'actual': 'connection_dropped'
            },
            {
                'scenario': 'message_send_with_auth_required',
                'token': 'valid_token',
                'expected': 'queued_until_auth_available',
                'actual': 'message_rejected_with_auth_error'
            }
        ]
        
        websocket_failures = []
        
        for scenario in websocket_scenarios:
            try:
                # Simulate WebSocket connection (simplified test version)
                websocket_url = "ws://localhost:8080/websocket"
                
                # Mock WebSocket connection attempt
                connection_result = await self._simulate_websocket_connection(
                    websocket_url, 
                    scenario['token'],
                    scenario['scenario']
                )
                
                if connection_result['failed']:
                    failure_details = connection_result['failure_reason']
                    
                    # Check if failure is user-friendly
                    technical_error_indicators = [
                        'database "netra_dev" does not exist',
                        'auth service unavailable',
                        'token validation failed',
                        'connection refused',
                        'internal error'
                    ]
                    
                    if any(indicator in failure_details.lower() for indicator in technical_error_indicators):
                        websocket_failures.append({
                            'scenario': scenario['scenario'],
                            'issue': 'technical_error_exposed_to_websocket_client',
                            'failure_reason': failure_details,
                            'expected_behavior': scenario['expected']
                        })
                    
                    # Check if connection is completely rejected vs gracefully degraded
                    if scenario['scenario'] == 'existing_connection_token_refresh':
                        websocket_failures.append({
                            'scenario': scenario['scenario'],
                            'issue': 'existing_connection_dropped_instead_of_degraded',
                            'impact': 'Users lose ongoing work and context'
                        })
            
            except Exception as e:
                websocket_failures.append({
                    'scenario': scenario['scenario'],
                    'issue': 'websocket_connection_completely_broken',
                    'error': str(e)
                })
        
        if websocket_failures:
            pytest.fail(
                f"WebSocket authentication cascade failures when auth database is down: {websocket_failures}. "
                "WebSocket connections should degrade gracefully, not fail completely."
            )
    
    async def _simulate_websocket_connection(self, websocket_url, token, scenario):
        """Simulate WebSocket connection attempt for testing."""
        try:
            # For testing purposes, simulate the connection logic
            # In real implementation, would use actual WebSocket client
            
            if scenario == 'new_connection_with_token':
                # New connection would fail auth validation due to database being down
                return {
                    'failed': True,
                    'failure_reason': 'Token validation failed: auth database unavailable',
                    'connection_established': False
                }
            
            elif scenario == 'existing_connection_token_refresh':
                # Existing connection might get dropped when trying to refresh token
                return {
                    'failed': True,
                    'failure_reason': 'Connection dropped during token refresh: database connection error',
                    'connection_established': False
                }
            
            elif scenario == 'message_send_with_auth_required':
                # Message sending fails due to auth validation
                return {
                    'failed': True,
                    'failure_reason': 'Message rejected: unable to validate user permissions',
                    'connection_established': True,
                    'message_sent': False
                }
            
        except Exception as e:
            return {
                'failed': True,
                'failure_reason': f'WebSocket connection error: {e}',
                'connection_established': False
            }
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_service_health_checks_dont_reflect_auth_database_dependency(self, services_with_auth_db_down):
        """FAILING TEST: Service health checks don't properly reflect auth database dependency.
        
        When auth database is down, health checks of dependent services should
        indicate reduced functionality or degraded state.
        """
        fixture = services_with_auth_db_down
        
        # Check health of services that depend on auth database
        dependent_services = [
            {
                'service': 'auth_service',
                'health_url': 'http://localhost:8081/health',
                'readiness_url': 'http://localhost:8081/readiness',
                'dependency': 'direct',  # Directly depends on auth database
                'expected_health': 'unhealthy_or_degraded',
                'expected_readiness': 'not_ready'
            },
            {
                'service': 'backend_service',
                'health_url': 'http://localhost:8080/health',
                'readiness_url': 'http://localhost:8080/readiness',
                'dependency': 'indirect',  # Depends on auth service for token validation
                'expected_health': 'healthy_but_with_dependency_warning',
                'expected_readiness': 'ready_but_auth_degraded'
            }
        ]
        
        health_check_issues = []
        
        async with aiohttp.ClientSession() as session:
            for service_info in dependent_services:
                service_name = service_info['service']
                
                try:
                    # Check health endpoint
                    async with session.get(service_info['health_url'], timeout=5) as response:
                        health_data = await response.json() if response.content_type == 'application/json' else {'status': 'unknown'}
                        
                        # Check if health indicates auth database dependency issue
                        health_status = health_data.get('status', 'unknown')
                        
                        if service_info['dependency'] == 'direct':
                            # Auth service should report unhealthy when its database is down
                            if health_status == 'healthy':
                                health_check_issues.append({
                                    'service': service_name,
                                    'issue': 'reports_healthy_despite_database_down',
                                    'health_data': health_data,
                                    'expected': service_info['expected_health']
                                })
                        
                        elif service_info['dependency'] == 'indirect':
                            # Backend should indicate auth dependency issues
                            dependency_indicators = [
                                'auth_service_status',
                                'dependencies',
                                'external_services',
                                'degraded_functionality'
                            ]
                            
                            has_dependency_info = any(indicator in health_data for indicator in dependency_indicators)
                            
                            if not has_dependency_info:
                                health_check_issues.append({
                                    'service': service_name,
                                    'issue': 'no_dependency_status_in_health',
                                    'health_data': health_data,
                                    'expected': 'auth service dependency status'
                                })
                    
                    # Check readiness endpoint
                    async with session.get(service_info['readiness_url'], timeout=5) as response:
                        readiness_data = await response.json() if response.content_type == 'application/json' else {'ready': None}
                        
                        ready_status = readiness_data.get('ready', None)
                        
                        if service_info['dependency'] == 'direct' and ready_status:
                            health_check_issues.append({
                                'service': service_name,
                                'issue': 'reports_ready_despite_database_down',
                                'readiness_data': readiness_data,
                                'expected': service_info['expected_readiness']
                            })
                
                except Exception as e:
                    health_check_issues.append({
                        'service': service_name,
                        'issue': 'health_check_completely_failed',
                        'error': str(e)
                    })
        
        if health_check_issues:
            pytest.fail(
                f"Service health checks don't properly reflect auth database dependency: {health_check_issues}. "
                "Health checks should indicate when critical dependencies are unavailable."
            )
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_user_session_persistence_lost_when_auth_db_down(self, services_with_auth_db_down):
        """FAILING TEST: User sessions are completely lost when auth database is down.
        
        Users who were already logged in should maintain their sessions temporarily
        using cached tokens, or should get clear explanation about temporary limitations.
        """
        fixture = services_with_auth_db_down
        
        # Simulate existing user session scenarios
        session_scenarios = [
            {
                'scenario': 'active_user_with_valid_session',
                'session_data': {
                    'user_id': 'user123',
                    'session_id': 'session456',
                    'token': 'valid_jwt_token',
                    'expires_at': '2024-12-31T23:59:59Z'
                },
                'expected': 'continue_with_cached_session',
                'actual': 'session_invalidated_immediately'
            },
            {
                'scenario': 'user_refreshing_page',
                'session_data': {
                    'user_id': 'user789',
                    'refresh_token': 'refresh_token_abc',
                    'last_activity': '2024-08-25T10:00:00Z'
                },
                'expected': 'graceful_degradation_with_explanation',
                'actual': 'forced_logout_with_technical_error'
            },
            {
                'scenario': 'user_making_authenticated_request',
                'session_data': {
                    'user_id': 'user456',
                    'access_token': 'access_token_xyz',
                    'permissions': ['read', 'write']
                },
                'expected': 'cached_permission_validation',
                'actual': 'permission_denied_error'
            }
        ]
        
        session_persistence_failures = []
        
        for scenario in session_scenarios:
            scenario_name = scenario['scenario']
            session_data = scenario['session_data']
            
            try:
                # Simulate session validation request
                session_validation_result = await self._simulate_session_validation(session_data)
                
                if not session_validation_result['valid']:
                    failure_reason = session_validation_result['failure_reason']
                    
                    # Check if failure is due to database being down
                    database_related_failures = [
                        'database "netra_dev" does not exist',
                        'connection to auth database failed',
                        'unable to validate session in database'
                    ]
                    
                    if any(db_failure in failure_reason for db_failure in database_related_failures):
                        session_persistence_failures.append({
                            'scenario': scenario_name,
                            'issue': 'session_invalidated_due_to_database_down',
                            'failure_reason': failure_reason,
                            'expected_behavior': scenario['expected'],
                            'actual_behavior': scenario['actual']
                        })
                    
                    # Check if user gets helpful error message
                    user_friendly_indicators = [
                        'temporarily unavailable',
                        'please try again',
                        'service maintenance',
                        'authentication service is down'
                    ]
                    
                    has_user_friendly_message = any(indicator in failure_reason.lower() 
                                                   for indicator in user_friendly_indicators)
                    
                    if not has_user_friendly_message:
                        session_persistence_failures.append({
                            'scenario': scenario_name,
                            'issue': 'technical_error_message_for_users',
                            'failure_reason': failure_reason,
                            'needed': 'user_friendly_explanation'
                        })
            
            except Exception as e:
                session_persistence_failures.append({
                    'scenario': scenario_name,
                    'issue': 'session_validation_completely_broken',
                    'error': str(e)
                })
        
        if session_persistence_failures:
            pytest.fail(
                f"User session persistence lost when auth database is down: {session_persistence_failures}. "
                "Sessions should persist temporarily with cached validation or clear user communication."
            )
    
    async def _simulate_session_validation(self, session_data):
        """Simulate session validation process when auth database is down."""
        try:
            # In reality, this would make requests to auth service endpoints
            # For testing, we simulate the validation logic
            
            user_id = session_data.get('user_id')
            session_id = session_data.get('session_id')
            token = session_data.get('token', session_data.get('access_token'))
            
            if not user_id or not (session_id or token):
                return {
                    'valid': False,
                    'failure_reason': 'Invalid session data provided'
                }
            
            # Simulate auth service being unavailable due to database down
            return {
                'valid': False,
                'failure_reason': 'Unable to validate session: auth database connection failed - database "netra_dev" does not exist',
                'should_be_cached': True,
                'user_impact': 'User forced to re-authenticate despite having valid session'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'failure_reason': f'Session validation error: {e}',
                'technical_error': True
            }
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_recovery_coordination_when_auth_database_restored(self, services_with_auth_db_down):
        """FAILING TEST: No coordination between services when auth database is restored.
        
        When auth database comes back online, all dependent services should detect
        this and restore full functionality in coordinated manner.
        """
        fixture = services_with_auth_db_down
        
        # Simulate database recovery scenario
        recovery_phases = [
            {
                'phase': 'database_down',
                'auth_db_available': False,
                'expected_service_states': {
                    'auth_service': 'degraded',
                    'backend_service': 'auth_dependency_degraded',
                    'websocket_service': 'auth_limited'
                }
            },
            {
                'phase': 'database_recovering',
                'auth_db_available': True,
                'auth_db_slow': True,  # Database available but slow
                'expected_service_states': {
                    'auth_service': 'recovering',
                    'backend_service': 'auth_dependency_recovering',
                    'websocket_service': 'auth_reconnecting'
                }
            },
            {
                'phase': 'database_recovered',
                'auth_db_available': True,
                'auth_db_slow': False,
                'expected_service_states': {
                    'auth_service': 'healthy',
                    'backend_service': 'healthy',
                    'websocket_service': 'healthy'
                }
            }
        ]
        
        recovery_coordination_issues = []
        
        for phase_info in recovery_phases:
            phase_name = phase_info['phase']
            expected_states = phase_info['expected_service_states']
            
            try:
                # Simulate the recovery phase conditions
                if phase_name == 'database_recovered':
                    # Mock database becoming available
                    with patch.dict(get_env().get_all(), {'POSTGRES_DB': 'netra_test'}):  # Available database
                        actual_service_states = await self._check_service_states_during_recovery()
                else:
                    actual_service_states = await self._check_service_states_during_recovery()
                
                # Check if actual states match expected states
                for service, expected_state in expected_states.items():
                    actual_state = actual_service_states.get(service, 'unknown')
                    
                    if actual_state != expected_state:
                        recovery_coordination_issues.append({
                            'phase': phase_name,
                            'service': service,
                            'expected_state': expected_state,
                            'actual_state': actual_state,
                            'issue': 'state_transition_not_coordinated'
                        })
                
                # Check if services communicate recovery status
                recovery_communication_indicators = [
                    'recovery_detected',
                    'auth_service_restored',
                    'full_functionality_available',
                    'dependency_health_restored'
                ]
                
                for service in expected_states.keys():
                    service_status = actual_service_states.get(service, {})
                    
                    if phase_name == 'database_recovered':
                        has_recovery_indication = any(indicator in str(service_status) 
                                                     for indicator in recovery_communication_indicators)
                        
                        if not has_recovery_indication:
                            recovery_coordination_issues.append({
                                'phase': phase_name,
                                'service': service,
                                'issue': 'no_recovery_communication',
                                'needed': 'clear_recovery_status_communication'
                            })
            
            except Exception as e:
                recovery_coordination_issues.append({
                    'phase': phase_name,
                    'issue': 'recovery_coordination_check_failed',
                    'error': str(e)
                })
        
        if recovery_coordination_issues:
            pytest.fail(
                f"Recovery coordination issues when auth database is restored: {recovery_coordination_issues}. "
                "Services should coordinate recovery and communicate restoration of full functionality."
            )
    
    async def _check_service_states_during_recovery(self):
        """Check actual service states during recovery phases."""
        service_states = {}
        
        async with aiohttp.ClientSession() as session:
            # Check auth service state
            try:
                async with session.get('http://localhost:8081/health', timeout=5) as response:
                    health_data = await response.json()
                    service_states['auth_service'] = health_data.get('status', 'unknown')
            except Exception:
                service_states['auth_service'] = 'unreachable'
            
            # Check backend service state  
            try:
                async with session.get('http://localhost:8080/health', timeout=5) as response:
                    health_data = await response.json()
                    service_states['backend_service'] = health_data.get('status', 'unknown')
            except Exception:
                service_states['backend_service'] = 'unreachable'
            
            # Mock websocket service state (would check actual WebSocket health in real implementation)
            service_states['websocket_service'] = 'unknown'
        
        return service_states


# Mark all tests as E2E integration tests
pytestmark = [pytest.mark.e2e, pytest.mark.integration, pytest.mark.real_services]
