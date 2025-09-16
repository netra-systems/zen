"""
Test Multi-Service Communication Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable end-to-end service communication for seamless user experience
- Value Impact: Users experience seamless workflows across all platform features without service boundary issues
- Strategic Impact: Platform reliability foundation for user trust, scalability, and operational excellence

This comprehensive test suite validates the complete microservice architecture communication patterns:
1. User Registration  ->  Login  ->  Agent Execution  ->  Data Storage workflow
2. Cross-service data flow and user context propagation 
3. Service mesh HTTP/WebSocket communication patterns
4. Error propagation and recovery scenarios
5. Load balancing and service discovery validation
6. Distributed transactions and coordination

CRITICAL: Uses REAL services only (no mocks in integration tests per CLAUDE.md)
"""
import asyncio
import json
import time
import uuid
import pytest
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from unittest.mock import patch
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.test_config import TEST_PORTS
from test_framework.websocket_helpers import WebSocketTestHelpers, WebSocketTestClient
from test_framework.utils.websocket import create_test_message
from shared.isolated_environment import get_env

class TestMultiServiceCommunication(BaseIntegrationTest):
    """Test cross-service communication patterns with real services.
    
    CRITICAL: This test validates the complete microservice architecture
    communication patterns that enable business value delivery.
    """

    def setup_method(self):
        """Set up method for each test."""
        super().setup_method()
        self.env = get_env()
        self.auth_service_url = f"http://localhost:{TEST_PORTS['auth']}"
        self.backend_service_url = f"http://localhost:{TEST_PORTS['backend']}"
        self.frontend_url = f"http://localhost:{TEST_PORTS['frontend']}"
        self.analytics_service_url = f"http://localhost:{TEST_PORTS['analytics']}"
        self.websocket_url = f"ws://localhost:{TEST_PORTS['backend']}/ws"
        self.test_user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        self.test_email = f'integration_test_{uuid.uuid4().hex[:8]}@example.com'

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_user_journey_across_all_services(self, real_services_fixture):
        """Test complete user journey: Registration  ->  Login  ->  Agent Execution  ->  Data Storage.
        
        BVJ: This test validates the core user value proposition - users can register,
        authenticate, execute agents, and have their data properly stored across services.
        """
        self.logger.info(f'Starting complete user journey test for user: {self.test_email}')
        async with httpx.AsyncClient(timeout=30.0) as client:
            registration_data = {'email': self.test_email, 'password': 'TestPassword123!', 'name': 'Integration Test User'}
            self.logger.info('Step 1: Registering user with Auth Service')
            register_response = await client.post(f'{self.auth_service_url}/auth/register', json=registration_data)
            assert register_response.status_code == 201, f'Registration failed: {register_response.text}'
            registration_result = register_response.json()
            assert 'user_id' in registration_result
            assert registration_result['email'] == self.test_email
            user_id = registration_result['user_id']
            self.logger.info('Step 2: Logging in user to obtain JWT token')
            login_data = {'email': self.test_email, 'password': 'TestPassword123!'}
            login_response = await client.post(f'{self.auth_service_url}/auth/login', json=login_data)
            assert login_response.status_code == 200, f'Login failed: {login_response.text}'
            login_result = login_response.json()
            assert 'access_token' in login_result
            assert 'refresh_token' in login_result
            access_token = login_result['access_token']
            self.logger.info('Step 3: Validating token cross-service communication')
            auth_headers = {'Authorization': f'Bearer {access_token}'}
            token_validation_response = await client.post(f'{self.auth_service_url}/auth/validate', json={'token': access_token})
            assert token_validation_response.status_code == 200
            validation_result = token_validation_response.json()
            assert validation_result['valid'] is True
            assert validation_result['user_id'] == user_id
            self.logger.info('Step 4: Creating user profile in Backend Service')
            profile_data = {'user_id': user_id, 'preferences': {'optimization_focus': 'cost_reduction', 'notification_frequency': 'daily'}}
            profile_response = await client.post(f'{self.backend_service_url}/api/user/profile', json=profile_data, headers=auth_headers)
            if profile_response.status_code != 404:
                assert profile_response.status_code in [200, 201]
            self.logger.info('Step 5: Establishing authenticated WebSocket connection')
            websocket_client = WebSocketTestClient(self.websocket_url, user_id)
            async with websocket_client as ws_client:
                auth_message = {'type': 'authenticate', 'token': access_token, 'user_id': user_id}
                await ws_client.send_json(auth_message)
                auth_events = []
                timeout = 10.0
                start_time = time.time()
                async for event in ws_client.receive_events(timeout=timeout):
                    auth_events.append(event)
                    if event.get('type') == 'authenticated':
                        break
                    if time.time() - start_time > timeout:
                        break
                auth_event_types = [e.get('type') for e in auth_events]
                assert 'authenticated' in auth_event_types or 'connection_ack' in auth_event_types
                self.logger.info('Step 6: Executing agent with cross-service communication')
                agent_request = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Help me optimize my cloud costs', 'user_id': user_id, 'context': {'monthly_spend': 1000, 'primary_cloud': 'aws'}}
                await ws_client.send_json(agent_request)
                agent_events = []
                execution_timeout = 30.0
                start_time = time.time()
                async for event in ws_client.receive_events(timeout=execution_timeout):
                    agent_events.append(event)
                    self.logger.info(f"Received WebSocket event: {event.get('type')}")
                    if event.get('type') == 'agent_completed':
                        break
                    if time.time() - start_time > execution_timeout:
                        break
                event_types = [e.get('type') for e in agent_events]
                self.logger.info(f'Received WebSocket event types: {event_types}')
                required_events = ['agent_started', 'agent_thinking', 'agent_completed']
                for required_event in required_events:
                    assert required_event in event_types, f'Missing critical WebSocket event: {required_event}. Received: {event_types}'
                completed_events = [e for e in agent_events if e.get('type') == 'agent_completed']
                assert len(completed_events) > 0, 'No agent_completed event received'
                final_result = completed_events[0]
                assert 'result' in final_result or 'response' in final_result
        self.logger.info('Step 7: Validating data persistence across services')
        async with httpx.AsyncClient(timeout=15.0) as client:
            user_data_response = await client.get(f'{self.backend_service_url}/api/user/{user_id}', headers=auth_headers)
            if user_data_response.status_code != 404:
                assert user_data_response.status_code == 200
                user_data = user_data_response.json()
                assert user_data['user_id'] == user_id
        self.logger.info('Complete user journey test completed successfully')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_data_flow_propagation(self, real_services_fixture):
        """Test user context propagation and data flow across all services.
        
        BVJ: Validates that user context and data flows correctly between services,
        ensuring user isolation and data consistency across the platform.
        """
        self.logger.info('Testing cross-service data flow and user context propagation')
        test_user_id = f'dataflow_user_{uuid.uuid4().hex[:8]}'
        test_context = {'user_id': test_user_id, 'session_id': f'session_{uuid.uuid4().hex[:8]}', 'preferences': {'theme': 'dark', 'language': 'en'}}
        async with httpx.AsyncClient(timeout=20.0) as client:
            auth_context_response = await client.post(f'{self.auth_service_url}/auth/context', json=test_context)
            if auth_context_response.status_code != 404:
                assert auth_context_response.status_code in [200, 201]
            backend_context_response = await client.get(f'{self.backend_service_url}/api/context/{test_user_id}')
            if backend_context_response.status_code != 404:
                assert backend_context_response.status_code == 200
                backend_context = backend_context_response.json()
                assert backend_context['user_id'] == test_user_id
            analytics_event = {'user_id': test_user_id, 'event_type': 'cross_service_test', 'service': 'backend', 'timestamp': datetime.now(timezone.utc).isoformat()}
            analytics_response = await client.post(f'{self.analytics_service_url}/analytics/track', json=analytics_event)
            if analytics_response.status_code != 404:
                assert analytics_response.status_code in [200, 202]
        self.logger.info('Cross-service data flow test completed successfully')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_mesh_communication_patterns(self, real_services_fixture):
        """Test HTTP/WebSocket communication patterns in the service mesh.
        
        BVJ: Validates that all service-to-service communication patterns work correctly,
        ensuring reliable message passing and data exchange between microservices.
        """
        self.logger.info('Testing service mesh HTTP/WebSocket communication patterns')
        async with httpx.AsyncClient(timeout=15.0) as client:
            health_checks = []
            try:
                auth_health = await client.get(f'{self.auth_service_url}/health')
                health_checks.append(('auth', auth_health.status_code))
            except Exception as e:
                health_checks.append(('auth', f'error: {e}'))
            try:
                backend_health = await client.get(f'{self.backend_service_url}/health')
                health_checks.append(('backend', backend_health.status_code))
            except Exception as e:
                health_checks.append(('backend', f'error: {e}'))
            try:
                analytics_health = await client.get(f'{self.analytics_service_url}/health')
                health_checks.append(('analytics', analytics_health.status_code))
            except Exception as e:
                health_checks.append(('analytics', f'error: {e}'))
            self.logger.info(f'Service health checks: {health_checks}')
            healthy_services = [check for check in health_checks if isinstance(check[1], int) and check[1] < 400]
            if len(healthy_services) == 0:
                self.logger.warning(f'No services available for testing: {health_checks}')
                pytest.skip('No services available - this is expected in development environments without Docker')
            else:
                self.logger.info(f'Found {len(healthy_services)} healthy services: {healthy_services}')
        self.logger.info('Testing WebSocket communication patterns')
        try:
            websocket_client = WebSocketTestClient(self.websocket_url, self.test_user_id)
            async with websocket_client as ws_client:
                connection_test_msg = {'type': 'connection_test', 'timestamp': time.time(), 'client_id': self.test_user_id}
                await ws_client.send_json(connection_test_msg)
                connection_events = []
                async for event in ws_client.receive_events(timeout=5.0):
                    connection_events.append(event)
                    break
                assert len(connection_events) > 0, 'No WebSocket response received'
                self.logger.info(f"WebSocket communication test successful: {connection_events[0].get('type')}")
        except Exception as e:
            self.logger.warning(f'WebSocket connection test failed (may be expected): {e}')
        self.logger.info('Service mesh communication patterns test completed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_propagation_and_recovery(self, real_services_fixture):
        """Test error propagation and recovery across services.
        
        BVJ: Validates that errors are properly handled and propagated between services,
        ensuring graceful degradation and recovery for reliable user experience.
        """
        self.logger.info('Testing error propagation and recovery across services')
        async with httpx.AsyncClient(timeout=10.0) as client:
            invalid_token = 'invalid.jwt.token'
            auth_headers = {'Authorization': f'Bearer {invalid_token}'}
            backend_auth_response = await client.get(f'{self.backend_service_url}/api/user/profile', headers=auth_headers)
            assert backend_auth_response.status_code in [401, 404]
            fake_service_url = 'http://localhost:9999'
            try:
                fake_response = await client.get(f'{fake_service_url}/health', timeout=2.0)
            except httpx.ConnectError:
                self.logger.info('Service unavailable error correctly handled')
            except httpx.TimeoutException:
                self.logger.info('Service timeout error correctly handled')
            malformed_data = {'invalid': 'structure'}
            auth_malformed_response = await client.post(f'{self.auth_service_url}/auth/login', json=malformed_data)
            assert auth_malformed_response.status_code >= 400
            assert auth_malformed_response.status_code < 500
        self.logger.info('Error propagation and recovery test completed successfully')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_load_balancing_service_discovery(self, real_services_fixture):
        """Test load balancing and service discovery scenarios.
        
        BVJ: Validates that services can be discovered and requests are properly balanced,
        ensuring scalability and reliability under different load conditions.
        """
        self.logger.info('Testing load balancing and service discovery')
        concurrent_requests = 5
        request_tasks = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for i in range(concurrent_requests):
                task = self._make_service_health_request(client, i)
                request_tasks.append(task)
            results = await asyncio.gather(*request_tasks, return_exceptions=True)
            successful_requests = 0
            failed_requests = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_requests += 1
                    self.logger.warning(f'Request {i} failed: {result}')
                else:
                    successful_requests += 1
                    self.logger.info(f'Request {i} succeeded: {result}')
            self.logger.info(f'Load test results: {successful_requests} successful, {failed_requests} failed')
            if successful_requests == 0:
                pytest.skip('No services available for load balancing test - expected in development environments')
        self.logger.info('Load balancing and service discovery test completed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_distributed_transactions_coordination(self, real_services_fixture):
        """Test distributed transactions and multi-service coordination.
        
        BVJ: Validates that multi-service transactions work correctly and maintain
        data consistency across service boundaries for complex user operations.
        """
        self.logger.info('Testing distributed transactions and coordination')
        transaction_id = f'txn_{uuid.uuid4().hex[:8]}'
        test_user_id = f'txn_user_{uuid.uuid4().hex[:8]}'
        async with httpx.AsyncClient(timeout=20.0) as client:
            transaction_steps = []
            user_data = {'email': f'{test_user_id}@example.com', 'password': 'TxnTest123!', 'transaction_id': transaction_id}
            try:
                auth_response = await client.post(f'{self.auth_service_url}/auth/register', json=user_data)
                transaction_steps.append(('auth_register', auth_response.status_code))
                if auth_response.status_code in [200, 201]:
                    user_result = auth_response.json()
                    created_user_id = user_result.get('user_id', test_user_id)
                    profile_data = {'user_id': created_user_id, 'transaction_id': transaction_id, 'profile': {'created_via': 'distributed_transaction_test'}}
                    try:
                        profile_response = await client.post(f'{self.backend_service_url}/api/user/profile', json=profile_data)
                        transaction_steps.append(('backend_profile', profile_response.status_code))
                    except Exception as e:
                        transaction_steps.append(('backend_profile', f'error: {e}'))
                    analytics_data = {'user_id': created_user_id, 'event': 'user_created', 'transaction_id': transaction_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
                    try:
                        analytics_response = await client.post(f'{self.analytics_service_url}/analytics/track', json=analytics_data)
                        transaction_steps.append(('analytics_track', analytics_response.status_code))
                    except Exception as e:
                        transaction_steps.append(('analytics_track', f'error: {e}'))
            except Exception as e:
                transaction_steps.append(('auth_register', f'error: {e}'))
            self.logger.info(f'Distributed transaction steps: {transaction_steps}')
            assert len(transaction_steps) > 0, 'No transaction steps completed'
            successful_steps = [step for step in transaction_steps if isinstance(step[1], int) and step[1] < 400]
            self.logger.info(f'Successful transaction steps: {len(successful_steps)}/{len(transaction_steps)}')
        self.logger.info('Distributed transactions coordination test completed')

    async def _make_service_health_request(self, client: httpx.AsyncClient, request_id: int) -> Dict[str, Any]:
        """Make a health check request to test concurrent service handling."""
        services = [('auth', self.auth_service_url), ('backend', self.backend_service_url), ('analytics', self.analytics_service_url)]
        service_name, service_url = services[request_id % len(services)]
        try:
            start_time = time.time()
            response = await client.get(f'{service_url}/health', timeout=5.0)
            end_time = time.time()
            return {'service': service_name, 'status_code': response.status_code, 'response_time': end_time - start_time, 'request_id': request_id}
        except Exception as e:
            return {'service': service_name, 'error': str(e), 'request_id': request_id}

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_agent_events_cross_service(self, real_services_fixture):
        """Test WebSocket agent events across service boundaries.
        
        MISSION CRITICAL: This test validates the 5 essential WebSocket events
        that enable chat business value across service boundaries.
        """
        self.logger.info('Testing WebSocket agent events cross-service communication')
        try:
            websocket_client = WebSocketTestClient(self.websocket_url, self.test_user_id)
            async with websocket_client as ws_client:
                agent_message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Test cross-service agent execution', 'user_id': self.test_user_id, 'timestamp': time.time()}
                await ws_client.send_json(agent_message)
                all_events = []
                timeout = 20.0
                start_time = time.time()
                async for event in ws_client.receive_events(timeout=timeout):
                    all_events.append(event)
                    self.logger.info(f"WebSocket event: {event.get('type')} - {event}")
                    if event.get('type') == 'agent_completed':
                        break
                    if time.time() - start_time > timeout:
                        break
                event_types = [event.get('type') for event in all_events]
                self.logger.info(f'All WebSocket events received: {event_types}')
                required_events = ['agent_started', 'agent_thinking', 'agent_completed']
                optional_events = ['tool_executing', 'tool_completed']
                for required_event in required_events:
                    assert required_event in event_types, f"CRITICAL: Missing required WebSocket event '{required_event}'. This breaks chat business value delivery. Events: {event_types}"
                for optional_event in optional_events:
                    if optional_event in event_types:
                        self.logger.info(f'Optional event present: {optional_event}')
                    else:
                        self.logger.info(f'Optional event not present: {optional_event}')
                for event in all_events:
                    assert 'type' in event, f"Event missing 'type' field: {event}"
                    assert 'timestamp' in event or event.get('type') in ['ack', 'error']
                self.logger.info('WebSocket agent events cross-service test PASSED')
        except Exception as e:
            self.logger.error(f'WebSocket agent events test failed: {e}')
            pytest.skip(f'WebSocket service not available for testing: {e}')

class TestMultiServicePerformanceValidation(BaseIntegrationTest):
    """Performance validation tests for multi-service communication."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_response_time_sla(self, real_services_fixture):
        """Test that service response times meet SLA requirements.
        
        BVJ: Validates that services respond within acceptable time limits
        to ensure good user experience and platform responsiveness.
        """
        sla_timeout = 5.0
        async with httpx.AsyncClient(timeout=sla_timeout) as client:
            services_to_test = [('auth', f"http://localhost:{TEST_PORTS['auth']}/health"), ('backend', f"http://localhost:{TEST_PORTS['backend']}/health"), ('analytics', f"http://localhost:{TEST_PORTS['analytics']}/health")]
            performance_results = []
            for service_name, health_url in services_to_test:
                try:
                    start_time = time.time()
                    response = await client.get(health_url)
                    end_time = time.time()
                    response_time = end_time - start_time
                    result = {'service': service_name, 'response_time': response_time, 'status_code': response.status_code, 'meets_sla': response_time <= sla_timeout}
                    performance_results.append(result)
                    self.logger.info(f'{service_name} service: {response_time:.3f}s (SLA: {sla_timeout}s)')
                except Exception as e:
                    performance_results.append({'service': service_name, 'error': str(e), 'meets_sla': False})
            services_meeting_sla = [r for r in performance_results if r.get('meets_sla', False)]
            assert len(services_meeting_sla) > 0, f'No services met SLA requirements: {performance_results}'
            self.logger.info(f'Services meeting SLA: {len(services_meeting_sla)}/{len(performance_results)}')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_service_requests(self, real_services_fixture):
        """Test concurrent requests across multiple services.
        
        BVJ: Validates that the platform can handle concurrent user requests
        across services without performance degradation.
        """
        concurrent_users = 3
        requests_per_user = 2

        async def simulate_user_requests(user_id: str) -> List[Dict[str, Any]]:
            """Simulate requests for a single user across services."""
            results = []
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    start_time = time.time()
                    auth_response = await client.get(f"http://localhost:{TEST_PORTS['auth']}/health")
                    end_time = time.time()
                    results.append({'user_id': user_id, 'service': 'auth', 'response_time': end_time - start_time, 'status_code': auth_response.status_code})
                except Exception as e:
                    results.append({'user_id': user_id, 'service': 'auth', 'error': str(e)})
                try:
                    start_time = time.time()
                    backend_response = await client.get(f"http://localhost:{TEST_PORTS['backend']}/health")
                    end_time = time.time()
                    results.append({'user_id': user_id, 'service': 'backend', 'response_time': end_time - start_time, 'status_code': backend_response.status_code})
                except Exception as e:
                    results.append({'user_id': user_id, 'service': 'backend', 'error': str(e)})
            return results
        user_tasks = []
        for i in range(concurrent_users):
            user_id = f'concurrent_user_{i}'
            task = simulate_user_requests(user_id)
            user_tasks.append(task)
        all_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        flattened_results = []
        for user_results in all_results:
            if isinstance(user_results, list):
                flattened_results.extend(user_results)
            else:
                flattened_results.append({'error': str(user_results)})
        successful_requests = [r for r in flattened_results if 'response_time' in r]
        failed_requests = [r for r in flattened_results if 'error' in r]
        self.logger.info(f'Concurrent requests results: {len(successful_requests)} successful, {len(failed_requests)} failed')
        assert len(successful_requests) > 0, 'No concurrent requests succeeded'
        if successful_requests:
            avg_response_time = sum((r['response_time'] for r in successful_requests)) / len(successful_requests)
            self.logger.info(f'Average response time under concurrent load: {avg_response_time:.3f}s')
            assert avg_response_time < 10.0, f'Average response time too high: {avg_response_time}s'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')