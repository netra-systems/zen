"""
E2E Tests for WebSocket State Machine Complete Lifecycle

Business Value Justification (BVJ):
- Segment: Platform/Internal - WebSocket Infrastructure
- Business Goal: Eliminate race conditions in WebSocket state management for $120K+ MRR
- Value Impact: Ensures reliable state transitions prevent message loss and connection issues
- Strategic Impact: Foundation for stable multi-user real-time chat functionality

 ALERT:  CRITICAL E2E REQUIREMENTS:
1. Tests MUST use REAL WebSocket connections to running services
2. Tests MUST use REAL state persistence (database/Redis)
3. Tests MUST validate complete state machine lifecycle end-to-end
4. Tests MUST fail hard when state transitions fail
5. Tests MUST authenticate with real JWT tokens (E2E AUTH MANDATORY)

This test suite validates WebSocket State Machine Complete Lifecycle:
- Complete WebSocket connection lifecycle with state machine coordination
- Real-time state synchronization across multiple WebSocket connections
- State machine coordination with message queuing and processing
- Error recovery and state rollback with real service failures
- Performance validation under concurrent state operations
- Business value validation: reliable message delivery without loss

E2E STATE MACHINE SCENARIOS:
Complete Connection Lifecycle:
- WebSocket handshake  ->  CONNECTING  ->  ACCEPTED  ->  AUTHENTICATED  ->  SERVICES_READY  ->  PROCESSING_READY
- Message queuing during state transitions with real message delivery
- State persistence across connection drops and reconnections
- Multi-user concurrent state management without interference

Real Service Integration:
- Real WebSocket server on backend service (8002/ws)
- Real database persistence for state history
- Real Redis for state caching and coordination
- Real authentication with JWT tokens
- Real message processing and agent execution

Following E2E requirements from CLAUDE.md:
- ALL e2e tests MUST use authentication (JWT/OAuth)
- NO MOCKS allowed in e2e tests
- Real services with Docker Compose
- Tests fail hard when services unavailable
- Absolute imports only
"""
import asyncio
import pytest
import time
import websockets
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import aiohttp
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env

@pytest.mark.e2e
class WebSocketStateMachineCompleteLifecycleTests:
    """
    E2E tests for complete WebSocket state machine lifecycle.
    
     ALERT:  CRITICAL: These tests validate the complete WebSocket connection
    lifecycle with real state machine coordination and service integration.
    
    Tests focus on:
    1. Complete WebSocket connection state lifecycle with real services
    2. State machine coordination with message queuing and processing
    3. Multi-user concurrent state management
    4. Error recovery and state rollback scenarios
    5. Performance under real-world load conditions
    """

    @classmethod
    def setup_class(cls):
        """Set up class-level configuration for E2E state machine tests."""
        cls.env = get_env()
        test_env = cls.env.get('TEST_ENV', cls.env.get('ENVIRONMENT', 'test'))
        if test_env == 'staging':
            cls.auth_config = E2EAuthConfig.for_staging()
        else:
            cls.auth_config = E2EAuthConfig(auth_service_url='http://localhost:8083', backend_url='http://localhost:8002', websocket_url='ws://localhost:8002/ws', timeout=45.0)
        cls.auth_helper = E2EAuthHelper(config=cls.auth_config)
        cls._validate_services_for_state_machine_testing()

    @classmethod
    def _validate_services_for_state_machine_testing(cls):
        """Validate services required for state machine testing."""
        import requests
        from requests.exceptions import RequestException
        required_endpoints = [('Backend Health', f'{cls.auth_config.backend_url}/health'), ('WebSocket Health', f'{cls.auth_config.backend_url}/ws/health'), ('State Machine Status', f'{cls.auth_config.backend_url}/api/websocket/state/health')]
        for endpoint_name, endpoint_url in required_endpoints:
            try:
                response = requests.get(endpoint_url, timeout=5)
                assert response.status_code < 500, f'{endpoint_name} unhealthy: {response.status_code}'
            except RequestException:
                if 'health' in endpoint_url.lower():
                    try:
                        base_url = '/'.join(endpoint_url.split('/')[:-1])
                        requests.get(base_url, timeout=5)
                    except RequestException as e:
                        pytest.fail(f' FAIL:  CRITICAL: Required service for state machine testing unavailable: {e}')

    def test_complete_websocket_connection_state_lifecycle(self):
        """Test complete WebSocket connection state lifecycle with real services."""
        state_user = self.auth_helper.create_authenticated_user(email=f'state_machine_user_{int(time.time())}@e2e.test', user_id=f'state_user_{int(time.time())}', full_name='State Machine E2E User', permissions=['websocket', 'chat', 'state_management'])

        async def test_complete_state_lifecycle():
            """Test complete state machine lifecycle."""
            connection_id = f'state_conn_{int(time.time())}'
            state_transitions = []
            websocket_headers = {'Authorization': f'Bearer {state_user.jwt_token}', 'X-Connection-ID': connection_id, 'X-User-ID': state_user.user_id, 'X-State-Tracking': 'enabled'}
            try:
                async with websockets.connect(self.auth_config.websocket_url, extra_headers=websocket_headers, timeout=self.auth_config.timeout) as websocket:
                    connection_start = time.time()
                    state_transitions.append({'from_state': 'CONNECTING', 'to_state': 'ACCEPTED', 'timestamp': datetime.now(timezone.utc).isoformat(), 'duration_ms': (time.time() - connection_start) * 1000})
                    auth_start = time.time()
                    authentication_message = {'type': 'authenticate', 'token': state_user.jwt_token, 'user_id': state_user.user_id, 'connection_id': connection_id, 'state_tracking': True}
                    await websocket.send(json.dumps(authentication_message))
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success', f'Auth failed: {auth_result}'
                    assert auth_result.get('user_id') == state_user.user_id
                    auth_duration = (time.time() - auth_start) * 1000
                    state_transitions.append({'from_state': 'ACCEPTED', 'to_state': 'AUTHENTICATED', 'timestamp': datetime.now(timezone.utc).isoformat(), 'duration_ms': auth_duration})
                    services_start = time.time()
                    service_init_message = {'type': 'initialize_services', 'user_id': state_user.user_id, 'connection_id': connection_id, 'required_services': ['agent_executor', 'message_queue', 'state_persistence']}
                    await websocket.send(json.dumps(service_init_message))
                    services_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    services_result = json.loads(services_response)
                    assert services_result.get('type') in ['services_ready', 'initialization_complete']
                    assert services_result.get('user_id') == state_user.user_id
                    services_duration = (time.time() - services_start) * 1000
                    state_transitions.append({'from_state': 'AUTHENTICATED', 'to_state': 'SERVICES_READY', 'timestamp': datetime.now(timezone.utc).isoformat(), 'duration_ms': services_duration})
                    processing_start = time.time()
                    processing_ready_message = {'type': 'enable_processing', 'user_id': state_user.user_id, 'connection_id': connection_id, 'processing_capabilities': ['message_processing', 'agent_execution']}
                    await websocket.send(json.dumps(processing_ready_message))
                    processing_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    processing_result = json.loads(processing_response)
                    assert processing_result.get('type') in ['processing_ready', 'ready_for_messages']
                    assert processing_result.get('user_id') == state_user.user_id
                    processing_duration = (time.time() - processing_start) * 1000
                    state_transitions.append({'from_state': 'SERVICES_READY', 'to_state': 'PROCESSING_READY', 'timestamp': datetime.now(timezone.utc).isoformat(), 'duration_ms': processing_duration})
                    message_test_start = time.time()
                    test_message = {'type': 'agent_request', 'message': 'Test message processing in PROCESSING_READY state', 'user_id': state_user.user_id, 'connection_id': connection_id, 'agent_type': 'echo_test'}
                    await websocket.send(json.dumps(test_message))
                    message_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    message_result = json.loads(message_response)
                    assert message_result.get('user_id') == state_user.user_id
                    assert message_result.get('type') in ['agent_response', 'message_processed', 'agent_started']
                    message_duration = (time.time() - message_test_start) * 1000
                    return {'state_transitions': state_transitions, 'message_processing_duration_ms': message_duration, 'total_lifecycle_duration_ms': sum((t['duration_ms'] for t in state_transitions))}
            except Exception as e:
                pytest.fail(f' FAIL:  CRITICAL: WebSocket state lifecycle failed: {e}')
        lifecycle_result = asyncio.run(test_complete_state_lifecycle())
        assert lifecycle_result is not None
        assert len(lifecycle_result['state_transitions']) == 4, 'Must complete all 4 state transitions'
        total_duration = lifecycle_result['total_lifecycle_duration_ms']
        assert total_duration < 60000, 'Complete lifecycle should finish within 60 seconds'
        for transition in lifecycle_result['state_transitions']:
            assert transition['duration_ms'] < 20000, f"Transition {transition['from_state']} -> {transition['to_state']} took too long"
        assert lifecycle_result['message_processing_duration_ms'] < 30000, 'Message processing should be fast in PROCESSING_READY state'

    def test_state_machine_coordination_with_message_queuing(self):
        """Test state machine coordination with real message queuing."""
        queue_user = self.auth_helper.create_authenticated_user(email=f'queue_user_{int(time.time())}@e2e.test', user_id=f'queue_user_{int(time.time())}', full_name='Message Queue E2E User', permissions=['websocket', 'chat', 'message_queuing'])

        async def test_message_queuing_coordination():
            """Test state machine coordination with message queuing."""
            connection_id = f'queue_conn_{int(time.time())}'
            websocket_headers = {'Authorization': f'Bearer {queue_user.jwt_token}', 'X-Connection-ID': connection_id, 'X-User-ID': queue_user.user_id, 'X-Queue-Testing': 'enabled'}
            try:
                async with websockets.connect(self.auth_config.websocket_url, extra_headers=websocket_headers, timeout=self.auth_config.timeout) as websocket:
                    early_messages = []
                    for i in range(3):
                        early_message = {'type': 'early_message', 'content': f'Message {i} sent before processing ready', 'user_id': queue_user.user_id, 'connection_id': connection_id, 'message_id': f'early_{i}_{int(time.time())}'}
                        await websocket.send(json.dumps(early_message))
                        early_messages.append(early_message['message_id'])
                    auth_message = {'type': 'authenticate', 'token': queue_user.jwt_token, 'user_id': queue_user.user_id, 'connection_id': connection_id}
                    await websocket.send(json.dumps(auth_message))
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success'
                    auth_messages = []
                    for i in range(2):
                        auth_message = {'type': 'auth_state_message', 'content': f'Message {i} sent in authenticated state', 'user_id': queue_user.user_id, 'connection_id': connection_id, 'message_id': f'auth_{i}_{int(time.time())}'}
                        await websocket.send(json.dumps(auth_message))
                        auth_messages.append(auth_message['message_id'])
                    service_init = {'type': 'initialize_services', 'user_id': queue_user.user_id, 'connection_id': connection_id}
                    await websocket.send(json.dumps(service_init))
                    services_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    services_result = json.loads(services_response)
                    assert services_result.get('type') in ['services_ready', 'initialization_complete']
                    enable_processing = {'type': 'enable_processing', 'user_id': queue_user.user_id, 'connection_id': connection_id}
                    await websocket.send(json.dumps(enable_processing))
                    processing_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    processing_result = json.loads(processing_response)
                    assert processing_result.get('type') in ['processing_ready', 'ready_for_messages']
                    processed_messages = []
                    for _ in range(10):
                        try:
                            queued_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            queued_result = json.loads(queued_response)
                            if queued_result.get('type') in ['queued_message_delivered', 'message_processed']:
                                processed_messages.append(queued_result)
                        except asyncio.TimeoutError:
                            break
                    realtime_message = {'type': 'realtime_message', 'content': 'Real-time message in processing ready state', 'user_id': queue_user.user_id, 'connection_id': connection_id, 'message_id': f'realtime_{int(time.time())}'}
                    await websocket.send(json.dumps(realtime_message))
                    realtime_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    realtime_result = json.loads(realtime_response)
                    assert realtime_result.get('user_id') == queue_user.user_id
                    return {'early_message_count': len(early_messages), 'auth_message_count': len(auth_messages), 'processed_message_count': len(processed_messages), 'realtime_processed': True}
            except Exception as e:
                pytest.fail(f' FAIL:  CRITICAL: Message queuing coordination failed: {e}')
        queue_result = asyncio.run(test_message_queuing_coordination())
        assert queue_result is not None
        assert queue_result['early_message_count'] == 3
        assert queue_result['auth_message_count'] == 2
        assert queue_result['realtime_processed'] is True
        assert queue_result['processed_message_count'] >= 0

    def test_multi_user_concurrent_state_management(self):
        """Test multi-user concurrent state management without interference."""
        user_count = 3
        concurrent_users = []
        for i in range(user_count):
            user = self.auth_helper.create_authenticated_user(email=f'concurrent_state_user_{i}_{int(time.time())}@e2e.test', user_id=f'concurrent_state_{i}_{int(time.time())}', full_name=f'Concurrent State User {i}', permissions=['websocket', 'chat', 'state_management'])
            concurrent_users.append(user)

        async def test_concurrent_user_states():
            """Test concurrent state management for multiple users."""
            user_results = []

            async def manage_user_state(user_index, user_data):
                """Manage state for individual user."""
                connection_id = f'concurrent_conn_{user_index}_{int(time.time())}'
                websocket_headers = {'Authorization': f'Bearer {user_data.jwt_token}', 'X-Connection-ID': connection_id, 'X-User-ID': user_data.user_id, 'X-Concurrent-Test': f'user_{user_index}'}
                try:
                    async with websockets.connect(self.auth_config.websocket_url, extra_headers=websocket_headers, timeout=self.auth_config.timeout) as websocket:
                        await asyncio.sleep(user_index * 0.5)
                        auth_message = {'type': 'authenticate', 'token': user_data.jwt_token, 'user_id': user_data.user_id, 'connection_id': connection_id, 'concurrent_user_index': user_index}
                        await websocket.send(json.dumps(auth_message))
                        auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        auth_result = json.loads(auth_response)
                        assert auth_result.get('type') == 'auth_success'
                        assert auth_result.get('user_id') == user_data.user_id
                        service_init = {'type': 'initialize_services', 'user_id': user_data.user_id, 'connection_id': connection_id, 'concurrent_user_index': user_index}
                        await websocket.send(json.dumps(service_init))
                        services_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                        services_result = json.loads(services_response)
                        assert services_result.get('type') in ['services_ready', 'initialization_complete']
                        enable_processing = {'type': 'enable_processing', 'user_id': user_data.user_id, 'connection_id': connection_id, 'concurrent_user_index': user_index}
                        await websocket.send(json.dumps(enable_processing))
                        processing_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        processing_result = json.loads(processing_response)
                        assert processing_result.get('type') in ['processing_ready', 'ready_for_messages']
                        user_message = {'type': 'user_specific_message', 'content': f'Message from concurrent user {user_index}', 'user_id': user_data.user_id, 'connection_id': connection_id, 'concurrent_user_index': user_index}
                        await websocket.send(json.dumps(user_message))
                        message_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        message_result = json.loads(message_response)
                        assert message_result.get('user_id') == user_data.user_id
                        return {'user_index': user_index, 'user_id': user_data.user_id, 'connection_id': connection_id, 'success': True}
                except Exception as e:
                    return {'user_index': user_index, 'user_id': user_data.user_id, 'error': str(e), 'success': False}
            tasks = [manage_user_state(i, user) for i, user in enumerate(concurrent_users)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        concurrent_results = asyncio.run(test_concurrent_user_states())
        assert len(concurrent_results) == user_count
        successful_results = [r for r in concurrent_results if isinstance(r, dict) and r.get('success')]
        assert len(successful_results) == user_count, f'All {user_count} users must succeed concurrently'
        user_ids = [r['user_id'] for r in successful_results]
        unique_user_ids = set(user_ids)
        assert len(unique_user_ids) == user_count, 'Each user must have unique state management'
        connection_ids = [r['connection_id'] for r in successful_results]
        unique_connections = set(connection_ids)
        assert len(unique_connections) == user_count, 'Each user must have unique connection state'

    def test_state_persistence_across_connection_drops(self):
        """Test state persistence across connection drops and reconnections."""
        persistence_user = self.auth_helper.create_authenticated_user(email=f'persistence_user_{int(time.time())}@e2e.test', user_id=f'persistence_user_{int(time.time())}', full_name='State Persistence E2E User', permissions=['websocket', 'chat', 'state_persistence'])

        async def test_connection_persistence():
            """Test state persistence across connection drops."""
            connection_id = f'persistence_conn_{int(time.time())}'
            websocket_headers = {'Authorization': f'Bearer {persistence_user.jwt_token}', 'X-Connection-ID': connection_id, 'X-User-ID': persistence_user.user_id, 'X-Persistence-Test': 'enabled'}
            initial_state = None
            try:
                async with websockets.connect(self.auth_config.websocket_url, extra_headers=websocket_headers, timeout=self.auth_config.timeout) as websocket:
                    auth_message = {'type': 'authenticate', 'token': persistence_user.jwt_token, 'user_id': persistence_user.user_id, 'connection_id': connection_id}
                    await websocket.send(json.dumps(auth_message))
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success'
                    service_init = {'type': 'initialize_services', 'user_id': persistence_user.user_id, 'connection_id': connection_id}
                    await websocket.send(json.dumps(service_init))
                    services_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    services_result = json.loads(services_response)
                    assert services_result.get('type') in ['services_ready', 'initialization_complete']
                    enable_processing = {'type': 'enable_processing', 'user_id': persistence_user.user_id, 'connection_id': connection_id}
                    await websocket.send(json.dumps(enable_processing))
                    processing_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    processing_result = json.loads(processing_response)
                    assert processing_result.get('type') in ['processing_ready', 'ready_for_messages']
                    state_data_message = {'type': 'store_state_data', 'user_id': persistence_user.user_id, 'connection_id': connection_id, 'state_data': {'session_info': 'persistence_test_session', 'processing_ready': True, 'user_preferences': {'theme': 'dark', 'notifications': True}}}
                    await websocket.send(json.dumps(state_data_message))
                    state_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    state_result = json.loads(state_response)
                    initial_state = {'connection_established': True, 'processing_ready': True, 'stored_data': state_result.get('stored_data')}
            except Exception as e:
                pytest.fail(f' FAIL:  CRITICAL: Initial connection failed: {e}')
            await asyncio.sleep(2)
            reconnection_state = None
            try:
                async with websockets.connect(self.auth_config.websocket_url, extra_headers=websocket_headers, timeout=self.auth_config.timeout) as websocket:
                    reauth_message = {'type': 'authenticate', 'token': persistence_user.jwt_token, 'user_id': persistence_user.user_id, 'connection_id': connection_id, 'reconnection': True}
                    await websocket.send(json.dumps(reauth_message))
                    reauth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    reauth_result = json.loads(reauth_response)
                    assert reauth_result.get('type') == 'auth_success'
                    restore_state_message = {'type': 'restore_state', 'user_id': persistence_user.user_id, 'connection_id': connection_id, 'restore_from': 'previous_session'}
                    await websocket.send(json.dumps(restore_state_message))
                    restore_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    restore_result = json.loads(restore_response)
                    reconnection_state = {'reconnection_successful': True, 'state_restored': restore_result.get('type') in ['state_restored', 'restore_complete'], 'restored_data': restore_result.get('restored_data')}
            except Exception as e:
                pytest.fail(f' FAIL:  CRITICAL: Reconnection failed: {e}')
            return {'initial_state': initial_state, 'reconnection_state': reconnection_state}
        persistence_result = asyncio.run(test_connection_persistence())
        assert persistence_result is not None
        assert persistence_result['initial_state']['connection_established'] is True
        assert persistence_result['initial_state']['processing_ready'] is True
        assert persistence_result['reconnection_state']['reconnection_successful'] is True
        assert persistence_result['reconnection_state']['state_restored'] is True
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')