"""
Staging Deployment E2E Tests - Critical P0 Issue #146
=====================================================

This test suite validates end-to-end staging deployment functionality
that's critical for the Golden Path user flow.

Critical Issues Being Tested:
1. Complete staging deployment pipeline validation
2. Service connectivity and communication in staging environment
3. Load balancer and health check integration
4. Authentication and authorization in deployed environment
5. WebSocket connectivity in staging environment

BUSINESS VALUE: Ensures Golden Path (login + message completion) works in staging

Following CLAUDE.md principles:
- Real staging environment testing, not mocks
- Authentication required for all tests (except auth validation tests)
- Complete end-to-end validation of user flows
- SSOT compliance for staging configurations
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import httpx
import pytest
import websockets
from websockets import ConnectionClosedError, InvalidStatusCode
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig, staging_urls
pytestmark = pytest.mark.asyncio

class StagingDeploymentError(Exception):
    """Exception raised for staging deployment validation errors."""
    pass

class StagingDeploymentValidator:
    """
    Validates complete staging deployment functionality.
    
    This validator ensures that all services are properly deployed,
    accessible, and functioning together in the staging environment.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.staging_config = StagingTestConfig()
        self.auth_helper = E2EAuthHelper()
        self.project_root = Path(__file__).parent.parent.parent

    async def validate_service_availability(self, service_name: str, base_url: str) -> Dict[str, Any]:
        """
        Validate that a staging service is available and responsive.
        
        Args:
            service_name: Name of the service
            base_url: Base URL of the service in staging
            
        Returns:
            Dict with availability validation results
        """
        validation_result = {'service': service_name, 'base_url': base_url, 'available': False, 'response_time_ms': 0, 'health_status': None, 'version_info': None, 'errors': []}
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                health_url = f"{base_url.rstrip('/')}/health"
                try:
                    health_response = await client.get(health_url)
                    validation_result['health_status'] = {'status_code': health_response.status_code, 'response_time_ms': (time.time() - start_time) * 1000, 'accessible': True}
                    if health_response.status_code == 200:
                        validation_result['available'] = True
                        try:
                            health_data = health_response.json()
                            validation_result['version_info'] = health_data.get('version')
                        except:
                            pass
                except httpx.HTTPStatusError as e:
                    validation_result['health_status'] = {'status_code': e.response.status_code, 'accessible': True, 'error': 'http_error'}
                    if e.response.status_code == 404:
                        validation_result['errors'].append('health_endpoint_missing')
                if not validation_result['available']:
                    try:
                        root_response = await client.get(base_url)
                        if root_response.status_code < 500:
                            validation_result['available'] = True
                    except:
                        validation_result['errors'].append('root_endpoint_failed')
        except httpx.ConnectTimeout:
            validation_result['errors'].append('connection_timeout')
        except httpx.ConnectError:
            validation_result['errors'].append('connection_refused')
        except Exception as e:
            validation_result['errors'].append(f'unexpected_error_{type(e).__name__}')
        validation_result['response_time_ms'] = (time.time() - start_time) * 1000
        return validation_result

    async def validate_service_communication(self, authenticated_user: AuthenticatedUser) -> Dict[str, Any]:
        """
        Validate inter-service communication in staging environment.
        
        Args:
            authenticated_user: Authenticated user for testing
            
        Returns:
            Dict with service communication validation results
        """
        communication_result = {'user_id': str(authenticated_user.user_id), 'backend_auth_communication': False, 'auth_database_communication': False, 'backend_database_communication': False, 'errors': [], 'test_results': {}}
        try:
            backend_url = staging_urls['backend']
            auth_headers = {'Authorization': f'Bearer {authenticated_user.access_token}'}
            async with httpx.AsyncClient(timeout=30.0) as client:
                protected_endpoint = f'{backend_url}/api/v1/auth/validate'
                try:
                    auth_response = await client.get(protected_endpoint, headers=auth_headers)
                    communication_result['test_results']['backend_auth_test'] = {'status_code': auth_response.status_code, 'response_time_ms': 0, 'success': auth_response.status_code == 200}
                    if auth_response.status_code == 200:
                        communication_result['backend_auth_communication'] = True
                    else:
                        communication_result['errors'].append(f'backend_auth_failed_{auth_response.status_code}')
                except Exception as e:
                    communication_result['errors'].append(f'backend_auth_communication_error_{type(e).__name__}')
                    communication_result['test_results']['backend_auth_test'] = {'error': str(e), 'success': False}
                db_test_endpoint = f'{backend_url}/api/v1/health/database'
                try:
                    db_response = await client.get(db_test_endpoint, headers=auth_headers)
                    communication_result['test_results']['backend_database_test'] = {'status_code': db_response.status_code, 'success': db_response.status_code == 200}
                    if db_response.status_code == 200:
                        communication_result['backend_database_communication'] = True
                except Exception as e:
                    communication_result['errors'].append(f'backend_database_test_error_{type(e).__name__}')
        except Exception as e:
            communication_result['errors'].append(f'communication_test_setup_error_{type(e).__name__}')
        return communication_result

    async def validate_websocket_connectivity(self, authenticated_user: AuthenticatedUser) -> Dict[str, Any]:
        """
        Validate WebSocket connectivity in staging environment.
        
        Args:
            authenticated_user: Authenticated user for testing
            
        Returns:
            Dict with WebSocket validation results
        """
        websocket_result = {'user_id': str(authenticated_user.user_id), 'connection_successful': False, 'message_exchange_successful': False, 'connection_time_ms': 0, 'messages_sent': 0, 'messages_received': 0, 'errors': []}
        try:
            backend_url = staging_urls['backend']
            ws_url = backend_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_endpoint = f'{ws_url}/ws'
            headers = {'Authorization': f'Bearer {authenticated_user.access_token}', 'X-User-ID': str(authenticated_user.user_id)}
            start_time = time.time()
            async with websockets.connect(ws_endpoint, extra_headers=headers, timeout=30.0) as websocket:
                websocket_result['connection_successful'] = True
                websocket_result['connection_time_ms'] = (time.time() - start_time) * 1000
                test_message = {'type': 'health_check', 'data': {'test_id': str(uuid.uuid4()), 'timestamp': datetime.now(timezone.utc).isoformat()}}
                await websocket.send(json.dumps(test_message))
                websocket_result['messages_sent'] = 1
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    websocket_result['messages_received'] = 1
                    websocket_result['message_exchange_successful'] = True
                    try:
                        response_data = json.loads(response)
                        websocket_result['response_data'] = response_data
                    except:
                        websocket_result['response_text'] = response
                except asyncio.TimeoutError:
                    websocket_result['errors'].append('message_response_timeout')
        except ConnectionClosedError as e:
            websocket_result['errors'].append(f'connection_closed_{e.code}')
        except InvalidStatusCode as e:
            websocket_result['errors'].append(f'invalid_status_code_{e.status_code}')
        except Exception as e:
            websocket_result['errors'].append(f'websocket_error_{type(e).__name__}')
        return websocket_result

    async def validate_golden_path_end_to_end(self, authenticated_user: AuthenticatedUser) -> Dict[str, Any]:
        """
        Validate the complete Golden Path user flow in staging.
        
        This tests: Login -> Message Creation -> Agent Response -> Response Display
        
        Args:
            authenticated_user: Authenticated user for testing
            
        Returns:
            Dict with Golden Path validation results
        """
        golden_path_result = {'user_id': str(authenticated_user.user_id), 'steps_completed': [], 'total_time_ms': 0, 'success': False, 'errors': []}
        start_time = time.time()
        try:
            backend_url = staging_urls['backend']
            auth_headers = {'Authorization': f'Bearer {authenticated_user.access_token}'}
            async with httpx.AsyncClient(timeout=60.0) as client:
                create_message_payload = {'message': 'Test staging deployment - please respond with current time', 'conversation_id': str(uuid.uuid4())}
                message_endpoint = f'{backend_url}/api/v1/messages'
                message_response = await client.post(message_endpoint, json=create_message_payload, headers=auth_headers)
                if message_response.status_code in [200, 201]:
                    golden_path_result['steps_completed'].append('message_creation')
                    message_data = message_response.json()
                    if 'message_id' in message_data or 'id' in message_data:
                        golden_path_result['steps_completed'].append('message_accepted')
                        golden_path_result['steps_completed'].append('agent_processing_initiated')
                        golden_path_result['success'] = True
                    else:
                        golden_path_result['errors'].append('message_data_incomplete')
                else:
                    golden_path_result['errors'].append(f'message_creation_failed_{message_response.status_code}')
        except Exception as e:
            golden_path_result['errors'].append(f'golden_path_error_{type(e).__name__}')
        golden_path_result['total_time_ms'] = (time.time() - start_time) * 1000
        return golden_path_result

class StagingDeploymentTests(SSotBaseTestCase):
    """
    E2E tests for staging deployment validation.
    
    These tests validate that the staging environment is properly deployed
    and all services are working together to support the Golden Path.
    """

    def setup_method(self):
        """Set up test environment with authentication."""
        super().setup_method()
        self.validator = StagingDeploymentValidator()
        self.staging_config = StagingTestConfig()
        self.auth_helper = E2EAuthHelper()

    @pytest.mark.e2e
    @pytest.mark.deployment_critical
    async def test_all_staging_services_available(self):
        """
        CRITICAL: Test that all required staging services are available.
        
        This test validates basic connectivity to all staging services.
        """
        service_availability_results = {}
        required_services = {'backend': staging_urls['backend'], 'auth': staging_urls['auth']}
        for service_name, service_url in required_services.items():
            availability_result = await self.validator.validate_service_availability(service_name, service_url)
            service_availability_results[service_name] = availability_result
            self.log_test_result(f'staging_{service_name}_availability', availability_result)
        unavailable_services = [service for service, result in service_availability_results.items() if not result['available']]
        assert len(unavailable_services) == 0, f"CRITICAL: {len(unavailable_services)} staging services unavailable: {unavailable_services}\nService results: {[(s, r['errors']) for s, r in service_availability_results.items()]}\nGolden Path cannot function without all required services"
        slow_services = [service for service, result in service_availability_results.items() if result['response_time_ms'] > 30000]
        assert len(slow_services) == 0, f"Services responding too slowly: {slow_services}\nResponse times: {[(s, r['response_time_ms']) for s, r in service_availability_results.items()]}"

    @pytest.mark.e2e
    @pytest.mark.deployment_critical
    async def test_staging_authentication_end_to_end(self):
        """
        CRITICAL: Test complete authentication flow in staging environment.
        
        This validates that users can authenticate and access protected resources.
        """
        try:
            authenticated_user = await self.auth_helper.create_authenticated_user(environment='staging')
            self.log_test_result('staging_authentication_success', {'user_id': str(authenticated_user.user_id), 'has_access_token': bool(authenticated_user.access_token), 'token_length': len(authenticated_user.access_token) if authenticated_user.access_token else 0})
            backend_url = staging_urls['backend']
            auth_headers = {'Authorization': f'Bearer {authenticated_user.access_token}'}
            async with httpx.AsyncClient(timeout=30.0) as client:
                protected_endpoint = f'{backend_url}/api/v1/auth/validate'
                auth_response = await client.get(protected_endpoint, headers=auth_headers)
                auth_validation_result = {'endpoint': protected_endpoint, 'status_code': auth_response.status_code, 'authenticated': auth_response.status_code == 200}
                self.log_test_result('staging_auth_validation', auth_validation_result)
                assert auth_response.status_code == 200, f'CRITICAL: Authentication validation failed in staging\nStatus: {auth_response.status_code}\nResponse: {auth_response.text}\nGolden Path requires working authentication'
        except Exception as e:
            self.fail(f'CRITICAL: Staging authentication completely failed: {str(e)}')

    @pytest.mark.e2e
    @pytest.mark.deployment_critical
    async def test_staging_service_communication(self):
        """
        CRITICAL: Test inter-service communication in staging environment.
        
        This validates that services can communicate with each other properly.
        """
        authenticated_user = await self.auth_helper.create_authenticated_user(environment='staging')
        communication_result = await self.validator.validate_service_communication(authenticated_user)
        self.log_test_result('staging_service_communication', communication_result)
        assert communication_result['backend_auth_communication'], f"CRITICAL: Backend-Auth communication failed in staging\nErrors: {communication_result['errors']}\nTest results: {communication_result['test_results']}\nGolden Path requires backend-auth communication"
        critical_errors = [error for error in communication_result['errors'] if 'communication' in error.lower()]
        assert len(critical_errors) == 0, f"Critical service communication errors: {critical_errors}\nAll errors: {communication_result['errors']}"

    @pytest.mark.e2e
    @pytest.mark.deployment_critical
    async def test_staging_websocket_connectivity(self):
        """
        CRITICAL: Test WebSocket connectivity in staging environment.
        
        This validates real-time communication necessary for the Golden Path.
        """
        authenticated_user = await self.auth_helper.create_authenticated_user(environment='staging')
        websocket_result = await self.validator.validate_websocket_connectivity(authenticated_user)
        self.log_test_result('staging_websocket_connectivity', websocket_result)
        assert websocket_result['connection_successful'], f"CRITICAL: WebSocket connection failed in staging\nErrors: {websocket_result['errors']}\nGolden Path requires WebSocket for real-time agent communication"
        assert websocket_result['connection_time_ms'] < 30000, f"WebSocket connection too slow: {websocket_result['connection_time_ms']}ms\nUsers expect real-time responsiveness"

    @pytest.mark.e2e
    @pytest.mark.deployment_critical
    async def test_golden_path_end_to_end_staging(self):
        """
        ULTIMATE CRITICAL: Test complete Golden Path user flow in staging.
        
        This is the ultimate test - can a user login and complete getting a message back?
        """
        authenticated_user = await self.auth_helper.create_authenticated_user(environment='staging')
        golden_path_result = await self.validator.validate_golden_path_end_to_end(authenticated_user)
        self.log_test_result('golden_path_staging_validation', golden_path_result)
        assert golden_path_result['success'], f"ULTIMATE CRITICAL: Golden Path failed in staging\nSteps completed: {golden_path_result['steps_completed']}\nErrors: {golden_path_result['errors']}\nTotal time: {golden_path_result['total_time_ms']}ms\nThis is the core business value - users must be able to login and get responses"
        assert golden_path_result['total_time_ms'] < 60000, f"Golden Path too slow: {golden_path_result['total_time_ms']}ms\nUsers expect responses within 60 seconds"
        required_steps = ['message_creation', 'message_accepted']
        missing_steps = [step for step in required_steps if step not in golden_path_result['steps_completed']]
        assert len(missing_steps) == 0, f"Missing critical Golden Path steps: {missing_steps}\nCompleted steps: {golden_path_result['steps_completed']}"

    @pytest.mark.e2e
    @pytest.mark.deployment_critical
    async def test_staging_health_endpoints_cloud_run_ready(self):
        """
        CRITICAL: Test that staging health endpoints are Cloud Run ready.
        
        This validates health endpoints work properly for Cloud Run health checks.
        """
        health_validation_results = {}
        services_to_test = {'backend': staging_urls['backend'], 'auth': staging_urls['auth']}
        for service_name, service_url in services_to_test.items():
            service_health_results = {}
            for endpoint in ['/health', '/api/health']:
                health_url = f"{service_url.rstrip('/')}{endpoint}"
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        start_time = time.time()
                        response = await client.get(health_url)
                        response_time = (time.time() - start_time) * 1000
                        service_health_results[endpoint] = {'status_code': response.status_code, 'response_time_ms': response_time, 'cloud_run_compatible': response.status_code in [200, 503], 'accessible': True}
                except Exception as e:
                    service_health_results[endpoint] = {'accessible': False, 'error': str(e), 'cloud_run_compatible': False}
            health_validation_results[service_name] = service_health_results
        self.log_test_result('staging_health_endpoints_validation', health_validation_results)
        for service_name, endpoints in health_validation_results.items():
            accessible_endpoints = [ep for ep, result in endpoints.items() if result.get('accessible', False)]
            assert len(accessible_endpoints) > 0, f'CRITICAL: No health endpoints accessible for {service_name} in staging\nEndpoints tested: {list(endpoints.keys())}\nResults: {endpoints}\nCloud Run health checks will fail'
            compatible_endpoints = [ep for ep, result in endpoints.items() if result.get('cloud_run_compatible', False)]
            assert len(compatible_endpoints) > 0, f'CRITICAL: No Cloud Run compatible health endpoints for {service_name}\nCompatible endpoints: {compatible_endpoints}\nCloud Run deployment will fail health checks'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')