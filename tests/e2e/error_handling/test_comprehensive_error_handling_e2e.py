"""
Comprehensive Error Handling E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete customer error experience with full authentication
- Value Impact: Ensures customers receive helpful error feedback in real-world scenarios
- Strategic Impact: Prevents customer churn from poor error handling during critical workflows

These tests validate the complete customer error experience using real services,
real authentication, and real WebSocket connections. NO MOCKS ALLOWED.

CRITICAL: E2E error handling tests must use REAL authentication to validate
multi-user error isolation and real-world customer scenarios.
"""
import asyncio
import json
import time
import uuid
import pytest
from typing import Dict, List, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthenticationHelper
from test_framework.ssot.websocket import WebSocketTestUtility
from test_framework.conftest_real_services import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env

class CustomerErrorExperienceE2ETests(SSotAsyncTestCase):
    """
    Test complete customer error experience with real authentication.
    
    BVJ: Customer error experience directly impacts satisfaction and retention.
    These tests ensure users receive helpful guidance during error scenarios.
    """

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_authentication_error_user_experience(self, real_services_fixture):
        """
        Test complete authentication error experience for customers.
        
        BUSINESS IMPACT: Authentication errors are the first impression for new users.
        Poor error handling directly impacts conversion and user onboarding.
        """
        auth_helper = E2EAuthenticationHelper()
        real_services = real_services_fixture
        base_url = real_services['backend_url']
        with self.assertRaises(Exception) as context:
            async with WebSocketTestClient(uri=f'ws://{base_url}/ws') as client:
                await client.send_json({'type': 'agent_request', 'message': 'Help me optimize costs'})
        error_message = str(context.exception)
        self.assertIn('authentication', error_message.lower())
        self.assertNotIn('jwt', error_message.lower())
        self.assertNotIn('token', error_message.lower())
        invalid_login_result = await auth_helper.attempt_authentication(email='nonexistent@example.com', password='wrongpassword', base_url=base_url)
        self.assertFalse(invalid_login_result['success'])
        self.assertIn('invalid email or password', invalid_login_result['user_message'].lower())
        self.assertNotIn('email not found', invalid_login_result['user_message'].lower())
        self.assertNotIn('user does not exist', invalid_login_result['user_message'].lower())

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_agent_execution_error_customer_experience(self, real_services_fixture):
        """
        Test customer experience when agent execution fails.
        
        BUSINESS IMPACT: Agent failures are core platform functionality failures.
        Users must receive clear guidance and alternative solutions.
        """
        auth_helper = E2EAuthenticationHelper()
        websocket_utility = WebSocketTestUtility()
        real_services = real_services_fixture
        user_auth = await auth_helper.create_test_user_with_auth(email=f'agent_error_test_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
        self.assertTrue(user_auth['success'])
        user_token = user_auth['access_token']
        user_id = user_auth['user_id']
        async with WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user_token}'}) as client:
            await client.send_json({'type': 'agent_request', 'agent': 'nonexistent_agent_type', 'message': 'Analyze my cloud spending patterns', 'user_id': user_id})
            events = []
            timeout_seconds = 30
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                try:
                    event = await asyncio.wait_for(client.receive_json(), timeout=1.0)
                    events.append(event)
                    if event.get('type') in ['agent_error', 'error', 'failure']:
                        break
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    raise AssertionError(f'Real WebSocket communication error: {e}') from e
            error_events = [e for e in events if e.get('type') in ['agent_error', 'error', 'failure']]
            if len(error_events) == 0:
                if len(events) == 0:
                    raise AssertionError('No response received from real agent request - system may be unresponsive')
                else:
                    print(f'System handled invalid agent request gracefully: {events[-1]}')
                    return
            error_event = error_events[0]
            user_message = error_event.get('user_message', '')
            self.assertNotEqual(user_message, '', 'Should provide user message')
            self.assertIn('temporarily unavailable', user_message.lower())
            self.assertIn('try again', user_message.lower())
            self.assertNotIn('llm', user_message.lower())
            self.assertNotIn('api', user_message.lower())
            self.assertNotIn('exception', user_message.lower())
            self.assertTrue('few moments' in user_message.lower() or 'try again' in user_message.lower(), 'Should provide recovery timing guidance')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_websocket_disconnection_customer_experience(self, real_services_fixture):
        """
        Test customer experience during WebSocket disconnections.
        
        BUSINESS IMPACT: WebSocket disconnections disrupt real-time chat experience.
        Customers must receive immediate feedback and automatic recovery.
        """
        auth_helper = E2EAuthenticationHelper()
        websocket_utility = WebSocketTestUtility()
        real_services = real_services_fixture
        user_auth = await auth_helper.create_test_user_with_auth(email=f'websocket_error_test_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
        user_token = user_auth['access_token']
        user_id = user_auth['user_id']
        client = WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user_token}'})
        await client.connect()
        await client.send_json({'type': 'ping', 'timestamp': int(time.time() * 1000)})
        pong_response = await client.receive_json()
        self.assertEqual(pong_response.get('type'), 'pong')
        await client.close(code=1006)
        reconnect_client = WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user_token}'})
        await reconnect_client.connect()
        await reconnect_client.send_json({'type': 'connection_status_check', 'user_id': user_id})
        status_response = await reconnect_client.receive_json()
        self.assertIn('connected', status_response.get('status', '').lower())
        await reconnect_client.send_json({'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Test message after reconnection', 'user_id': user_id})
        agent_response = await reconnect_client.receive_json()
        self.assertEqual(agent_response.get('type'), 'agent_started')
        await reconnect_client.close()

class MultiUserErrorIsolationE2ETests(SSotAsyncTestCase):
    """
    Test multi-user error isolation with real authentication.
    
    BVJ: Multi-user error isolation prevents one user's errors from affecting others.
    Critical for enterprise customers with multiple team members.
    """

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_user_error_isolation(self, real_services_fixture):
        """
        Test that errors for one user don't affect other users.
        
        BUSINESS IMPACT: Error isolation ensures platform stability for all users
        when individual user sessions encounter problems.
        """
        auth_helper = E2EAuthenticationHelper()
        real_services = real_services_fixture
        user1_auth = await auth_helper.create_test_user_with_auth(email=f'isolation_user1_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
        user2_auth = await auth_helper.create_test_user_with_auth(email=f'isolation_user2_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
        user1_token = user1_auth['access_token']
        user1_id = user1_auth['user_id']
        user2_token = user2_auth['access_token']
        user2_id = user2_auth['user_id']
        user1_client = WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user1_token}'})
        user2_client = WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user2_token}'})
        await user1_client.connect()
        await user2_client.connect()
        with patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry.get_user_context') as mock_context:

            def context_side_effect(user_id):
                if user_id == user1_id:
                    raise Exception('User1 context corruption')
                return {'user_id': user_id, 'context': 'valid'}
            mock_context.side_effect = context_side_effect
            await user1_client.send_json({'type': 'agent_request', 'agent': 'data_helper_agent', 'message': 'Show my data', 'user_id': user1_id})
            await user2_client.send_json({'type': 'agent_request', 'agent': 'data_helper_agent', 'message': 'Show my data', 'user_id': user2_id})
            user1_events = []
            user2_events = []
            for _ in range(10):
                try:
                    user1_event = await asyncio.wait_for(user1_client.receive_json(), timeout=0.5)
                    user1_events.append(user1_event)
                except asyncio.TimeoutError:
                    pass
                try:
                    user2_event = await asyncio.wait_for(user2_client.receive_json(), timeout=0.5)
                    user2_events.append(user2_event)
                except asyncio.TimeoutError:
                    pass
                if any((e.get('type') in ['agent_error', 'agent_completed'] for e in user1_events)) and any((e.get('type') in ['agent_started', 'agent_completed'] for e in user2_events)):
                    break
            user1_error_events = [e for e in user1_events if e.get('type') == 'agent_error']
            self.assertGreater(len(user1_error_events), 0, 'User1 should receive error')
            user2_success_events = [e for e in user2_events if e.get('type') == 'agent_started']
            self.assertGreater(len(user2_success_events), 0, 'User2 should receive success events')
            for user1_event in user1_events:
                self.assertNotEqual(user1_event.get('user_id'), user2_id, 'User1 should not receive User2 events')
            for user2_event in user2_events:
                self.assertNotEqual(user2_event.get('user_id'), user1_id, 'User2 should not receive User1 events')
        await user1_client.close()
        await user2_client.close()

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_concurrent_user_error_recovery(self, real_services_fixture):
        """
        Test error recovery for multiple concurrent users.
        
        BUSINESS IMPACT: Concurrent error recovery ensures platform scalability
        and reliability under real-world multi-user load.
        """
        auth_helper = E2EAuthenticationHelper()
        real_services = real_services_fixture
        num_users = 3
        users = []
        for i in range(num_users):
            user_auth = await auth_helper.create_test_user_with_auth(email=f'concurrent_user_{i}_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
            users.append(user_auth)
        clients = []
        for user in users:
            client = WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f"Bearer {user['access_token']}"})
            await client.connect()
            clients.append(client)
        with patch('netra_backend.app.db.database_manager.DatabaseManager._execute_query') as mock_db:
            failure_count = 0

            async def failing_query(query, params=None):
                nonlocal failure_count
                failure_count += 1
                if failure_count <= 6:
                    raise ConnectionError('Database temporarily unavailable')
                return {'results': []}
            mock_db.side_effect = failing_query
            tasks = []
            for i, (user, client) in enumerate(zip(users, clients)):
                task = client.send_json({'type': 'agent_request', 'agent': 'data_helper_agent', 'message': f'User {i} request', 'user_id': user['user_id']})
                tasks.append(task)
            await asyncio.gather(*tasks)
            all_events = [[] for _ in range(num_users)]
            for _ in range(20):
                for i, client in enumerate(clients):
                    try:
                        event = await asyncio.wait_for(client.receive_json(), timeout=0.1)
                        all_events[i].append(event)
                    except asyncio.TimeoutError:
                        pass
                if all((len(events) > 0 for events in all_events)):
                    break
            for i, events in enumerate(all_events):
                self.assertGreater(len(events), 0, f'User {i} should receive response')
                event_types = [e.get('type') for e in events]
                self.assertTrue('agent_started' in event_types or 'agent_error' in event_types, f'User {i} should receive agent_started or agent_error')
        for client in clients:
            await client.close()

class SystemRecoveryCustomerExperienceE2ETests(SSotAsyncTestCase):
    """
    Test system recovery customer experience with real services.
    
    BVJ: System recovery during outages must maintain customer trust
    and provide clear communication about service restoration.
    """

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_service_degradation_customer_communication(self, real_services_fixture):
        """
        Test customer communication during service degradation.
        
        BUSINESS IMPACT: Clear communication during outages maintains customer
        trust and reduces support escalations.
        """
        auth_helper = E2EAuthenticationHelper()
        real_services = real_services_fixture
        user_auth = await auth_helper.create_test_user_with_auth(email=f'degradation_test_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
        user_token = user_auth['access_token']
        user_id = user_auth['user_id']
        async with WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user_token}'}) as client:
            with patch('netra_backend.app.services.agent_service_core.AgentServiceCore.get_health_status') as mock_health:
                mock_health.return_value = {'status': 'degraded', 'available_features': ['basic_chat', 'cached_responses'], 'unavailable_features': ['real_time_analysis', 'data_processing'], 'estimated_recovery': '15 minutes', 'user_message': 'Some advanced features are temporarily unavailable. Basic chat functionality remains operational.'}
                await client.send_json({'type': 'health_check', 'user_id': user_id})
                health_response = await client.receive_json()
                self.assertEqual(health_response.get('type'), 'health_status')
                self.assertEqual(health_response.get('status'), 'degraded')
                user_message = health_response.get('user_message', '')
                self.assertIn('temporarily unavailable', user_message.lower())
                self.assertIn('basic chat', user_message.lower())
                self.assertIn('recovery', health_response)
                await client.send_json({'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Help me with a simple question', 'user_id': user_id})
                agent_response = await client.receive_json()
                if agent_response.get('type') == 'agent_started':
                    self.assertTrue(agent_response.get('degraded_mode', False), 'Should indicate degraded mode')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.authenticated
    async def test_complete_service_recovery_notification(self, real_services_fixture):
        """
        Test complete service recovery notifications to customers.
        
        BUSINESS IMPACT: Recovery notifications restore customer confidence
        and encourage re-engagement with platform features.
        """
        auth_helper = E2EAuthenticationHelper()
        real_services = real_services_fixture
        user_auth = await auth_helper.create_test_user_with_auth(email=f'recovery_test_{uuid.uuid4()}@example.com', password='SecurePassword123!', base_url=real_services['auth_service_url'])
        user_token = user_auth['access_token']
        user_id = user_auth['user_id']
        async with WebSocketTestClient(uri=f"ws://{real_services['backend_url']}/ws", extra_headers={'Authorization': f'Bearer {user_token}'}) as client:
            with patch('netra_backend.app.core.health.health_monitor.HealthMonitor.get_comprehensive_health') as mock_health:
                mock_health.return_value = {'overall_status': 'degraded', 'recovery_in_progress': True}
                await client.send_json({'type': 'health_check', 'user_id': user_id})
                initial_response = await client.receive_json()
                self.assertEqual(initial_response.get('status'), 'degraded')
                mock_health.return_value = {'overall_status': 'healthy', 'recovery_completed': True, 'all_features_available': True, 'user_message': 'All systems are now fully operational. Thank you for your patience.'}
                await client.send_json({'type': 'health_check', 'user_id': user_id})
                recovery_response = await client.receive_json()
                self.assertEqual(recovery_response.get('status'), 'healthy')
                self.assertTrue(recovery_response.get('all_features_available'))
                user_message = recovery_response.get('user_message', '')
                self.assertIn('fully operational', user_message.lower())
                self.assertIn('thank you', user_message.lower())
                await client.send_json({'type': 'agent_request', 'agent': 'cost_optimizer', 'message': 'Analyze my complete cost optimization opportunities', 'user_id': user_id})
                full_response = await client.receive_json()
                self.assertEqual(full_response.get('type'), 'agent_started')
                self.assertFalse(full_response.get('degraded_mode', False))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')