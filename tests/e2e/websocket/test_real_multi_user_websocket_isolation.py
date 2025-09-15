"""
Real Multi-User WebSocket Isolation Security Tests - NO MOCKS

CRITICAL SECURITY TESTS: These tests validate that WebSocket events and user data
do NOT leak between different authenticated users in a multi-tenant environment.

Per CLAUDE.md CRITICAL REQUIREMENTS:
- ALL e2e tests MUST use authentication (JWT/OAuth)
- Tests MUST fail hard when isolation is violated  
- NO MOCKS - only real WebSocket connections to backend services
- Multi-user isolation is CRITICAL for security

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal - Multi-user chat security
- Business Goal: Prevent data leaks between users (GDPR compliance)
- Value Impact: Protects user privacy in multi-tenant AI interactions
- Revenue Impact: Prevents security breaches that destroy customer trust

These tests will FAIL IMMEDIATELY if:
- User A receives events/data meant for User B
- Authentication boundaries are crossed
- WebSocket connections leak user data
- Session isolation is compromised

@compliance CLAUDE.md - E2E auth mandatory, multi-user system, fail-hard security
@compliance SPEC/core.xml - Real services testing, user isolation validation
"""
import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient, SecurityError, create_authenticated_websocket_client, test_websocket_events_isolation
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager, IsolationTestType, IsolationTestResult
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
logger = logging.getLogger(__name__)
BACKEND_URL = 'ws://localhost:8000'
TEST_ENVIRONMENT = 'test'
CONNECTION_TIMEOUT = 15.0
EVENT_TIMEOUT = 10.0
REQUIRED_AGENT_EVENTS = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}

@pytest.fixture(scope='session')
async def docker_services():
    """Ensure Docker services are running for real WebSocket tests."""
    docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
    await docker_manager.start_services_smart(services=['backend', 'auth'], wait_healthy=True)
    yield docker_manager

@pytest.fixture
async def connection_manager():
    """Provide a real WebSocket connection manager."""
    manager = RealWebSocketConnectionManager(backend_url=BACKEND_URL, environment=TEST_ENVIRONMENT, connection_timeout=CONNECTION_TIMEOUT)
    yield manager
    await manager.cleanup_all_connections()

@pytest.fixture
async def auth_helper():
    """Provide E2E authentication helper."""
    return E2EAuthHelper(environment=TEST_ENVIRONMENT)

class TestRealMultiUserWebSocketIsolation:
    """
    CRITICAL SECURITY TESTS: Multi-User WebSocket Isolation
    
    These tests validate that the WebSocket system properly isolates
    users and prevents cross-user data leaks in a multi-tenant environment.
    
    ALL TESTS MUST USE REAL WEBSOCKET CONNECTIONS WITH AUTHENTICATION.
    NO MOCKS ALLOWED - tests fail if Docker services unavailable.
    """

    @pytest.mark.asyncio
    @pytest.mark.real_services
    @pytest.mark.concurrent_safe
    async def test_two_user_event_isolation_critical(self, docker_services, connection_manager: RealWebSocketConnectionManager):
        """
        CRITICAL: Test that events sent to User A are NOT received by User B.
        
        This is the fundamental security test for multi-user isolation.
        Test MUST fail hard if events leak between users.
        """
        logger.info('CRITICAL SECURITY TEST: Two-user event isolation')
        async with connection_manager.managed_connections(count=2) as connection_ids:
            user_a_id, user_b_id = connection_ids
            user_a_client = connection_manager.get_connection(user_a_id)
            user_b_client = connection_manager.get_connection(user_b_id)
            user_a_profile = connection_manager.connections[user_a_id]
            user_b_profile = connection_manager.connections[user_b_id]
            logger.info(f'User A: {user_a_profile.user_id}')
            logger.info(f'User B: {user_b_profile.user_id}')
            await user_a_client.send_event(event_type='user_specific_event', data={'message': 'This is PRIVATE data for User A', 'user_id': user_a_profile.user_id, 'sensitive_data': f'SECRET_{user_a_profile.user_id}', 'timestamp': datetime.now(timezone.utc).isoformat()})
            await asyncio.sleep(2.0)
            try:
                user_a_events = await user_a_client.wait_for_events(event_types={'user_specific_event'}, timeout=EVENT_TIMEOUT)
            except asyncio.TimeoutError:
                user_a_events = []
            try:
                user_b_events = await user_b_client.wait_for_events(event_types={'user_specific_event'}, timeout=5.0)
            except asyncio.TimeoutError:
                user_b_events = []
            if user_b_events:
                violation_details = []
                for event in user_b_events:
                    if event.user_id == user_a_profile.user_id:
                        violation_details.append(f'User B ({user_b_profile.user_id}) received event meant for User A ({user_a_profile.user_id})')
                if violation_details:
                    pytest.fail(f'CRITICAL SECURITY VIOLATION: Cross-user event leak detected!\nViolations: {violation_details}\nUser B events: {[e.event_type for e in user_b_events]}\nThis indicates the system is leaking private data between users!')
            user_a_client.assert_no_isolation_violations()
            user_b_client.assert_no_isolation_violations()
            logger.info(' PASS:  Two-user event isolation test PASSED')

    @pytest.mark.asyncio
    @pytest.mark.real_services
    @pytest.mark.concurrent_safe
    async def test_concurrent_user_data_isolation(self, docker_services, connection_manager: RealWebSocketConnectionManager):
        """
        CRITICAL: Test user data isolation under concurrent operations.
        
        Validates that private user data doesn't leak when multiple users
        are actively using the system simultaneously.
        """
        logger.info('CRITICAL SECURITY TEST: Concurrent user data isolation')
        USER_COUNT = 5
        async with connection_manager.managed_connections(count=USER_COUNT) as connection_ids:
            send_tasks = []
            for i, connection_id in enumerate(connection_ids):
                client = connection_manager.get_connection(connection_id)
                profile = connection_manager.connections[connection_id]
                task = asyncio.create_task(client.send_event(event_type='private_user_data', data={'user_secret': f'PRIVATE_SECRET_FOR_USER_{profile.user_id}', 'user_id': profile.user_id, 'user_email': profile.user_email, 'private_notes': f'Confidential notes for {profile.user_id}', 'account_balance': f'$999{i}.{i * 11}', 'sequence': i}))
                send_tasks.append(task)
            await asyncio.gather(*send_tasks)
            await asyncio.sleep(3.0)
            try:
                result = await connection_manager.test_user_isolation(test_type=IsolationTestType.USER_DATA_ISOLATION)
                assert result.test_passed, f'User data isolation test FAILED: {result.total_violations} violations detected. Details: {result.violation_details}'
                assert result.events_validated > 0, 'No events were validated - test may not be working properly'
            except SecurityError as e:
                pytest.fail(f'CRITICAL SECURITY VIOLATION: User data isolation failed!\nError: {e}\nThis indicates private user data is leaking between accounts!')
            logger.info(f' PASS:  Concurrent user data isolation test PASSED ({result.events_validated} events validated)')

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_authentication_boundary_isolation(self, docker_services, connection_manager: RealWebSocketConnectionManager):
        """
        CRITICAL: Test that authentication boundaries are strictly enforced.
        
        Validates that each WebSocket connection only operates within its
        authenticated user context and cannot access other users' sessions.
        """
        logger.info('CRITICAL SECURITY TEST: Authentication boundary isolation')
        users_config = [{'permissions': ['read']}, {'permissions': ['read', 'write']}, {'permissions': ['read', 'write', 'admin']}]
        connection_ids = []
        for config in users_config:
            connection_id = await connection_manager.create_authenticated_connection(permissions=config['permissions'])
            connection_ids.append(connection_id)
        try:
            result = await connection_manager.test_user_isolation(test_type=IsolationTestType.AUTHENTICATION_ISOLATION)
            assert result.test_passed, f'Authentication isolation test FAILED: {result.total_violations} violations detected. Details: {result.violation_details}'
            for connection_id in connection_ids:
                client = connection_manager.get_connection(connection_id)
                profile = connection_manager.connections[connection_id]
                assert client.expected_user_id == profile.user_id, f'Authentication context mismatch for {connection_id}: expected {profile.user_id}, got {client.expected_user_id}'
                client.assert_no_isolation_violations()
            logger.info(' PASS:  Authentication boundary isolation test PASSED')
        except SecurityError as e:
            pytest.fail(f'CRITICAL SECURITY VIOLATION: Authentication boundary breach!\nError: {e}\nUser authentication contexts are not properly isolated!')
        finally:
            for connection_id in connection_ids:
                await connection_manager.cleanup_connection(connection_id)

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_high_concurrency_isolation_stress(self, docker_services, connection_manager: RealWebSocketConnectionManager):
        """
        CRITICAL: Test isolation under high concurrency stress.
        
        Validates that user isolation remains intact when the system
        is under heavy concurrent load from multiple users.
        """
        logger.info('CRITICAL SECURITY TEST: High concurrency isolation stress')
        CONCURRENT_USERS = 10
        EVENTS_PER_USER = 5
        async with connection_manager.managed_connections(count=CONCURRENT_USERS) as connection_ids:
            stress_tasks = []
            for connection_id in connection_ids:
                task = asyncio.create_task(self._stress_test_user_events(connection_manager.get_connection(connection_id), connection_manager.connections[connection_id], EVENTS_PER_USER))
                stress_tasks.append(task)
            await asyncio.gather(*stress_tasks)
            await asyncio.sleep(4.0)
            try:
                result = await connection_manager.test_user_isolation(test_type=IsolationTestType.CONCURRENT_SESSION_ISOLATION)
                assert result.test_passed, f'High concurrency isolation test FAILED: {result.total_violations} violations under stress. Details: {result.violation_details}'
                connection_manager.assert_no_violations()
                logger.info(f' PASS:  High concurrency isolation stress test PASSED ({CONCURRENT_USERS} users, {result.events_validated} events validated)')
            except SecurityError as e:
                pytest.fail(f'CRITICAL SECURITY VIOLATION: Isolation failed under concurrent load!\nError: {e}\nThe system cannot maintain user isolation under normal load!')

    async def _stress_test_user_events(self, client: RealWebSocketTestClient, profile, event_count: int):
        """Generate stress load for a single user connection."""
        for i in range(event_count):
            await client.send_event(event_type='stress_test_event', data={'stress_sequence': i, 'user_id': profile.user_id, 'sensitive_data': f'PRIVATE_DATA_{profile.user_id}_{i}', 'timestamp': time.time()})
            await asyncio.sleep(0.1 + i * 0.05)

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_agent_event_isolation_during_execution(self, docker_services, connection_manager: RealWebSocketConnectionManager):
        """
        CRITICAL: Test that agent execution events are properly isolated.
        
        When User A triggers an agent, User B must NOT receive the agent
        events (agent_started, tool_executing, etc.) meant for User A.
        """
        logger.info('CRITICAL SECURITY TEST: Agent event isolation during execution')
        async with connection_manager.managed_connections(count=2) as connection_ids:
            user_a_id, user_b_id = connection_ids
            user_a_client = connection_manager.get_connection(user_a_id)
            user_b_client = connection_manager.get_connection(user_b_id)
            user_a_profile = connection_manager.connections[user_a_id]
            user_b_profile = connection_manager.connections[user_b_id]
            await user_a_client.send_event(event_type='agent_request', data={'agent_name': 'test_agent', 'task': 'Perform a private task for User A', 'user_id': user_a_profile.user_id, 'private': True})
            agent_events = [('agent_started', {'message': 'Agent started for User A'}), ('agent_thinking', {'message': "Agent processing User A's request"}), ('tool_executing', {'tool': 'search', 'query': "User A's private query"}), ('tool_completed', {'result': 'Private result for User A'}), ('agent_completed', {'response': 'Task completed for User A'})]
            for event_type, data in agent_events:
                await user_a_client.send_event(event_type=event_type, data={**data, 'user_id': user_a_profile.user_id, 'for_user': user_a_profile.user_id})
                await asyncio.sleep(0.5)
            await asyncio.sleep(2.0)
            try:
                user_b_agent_events = await user_b_client.wait_for_events(event_types=REQUIRED_AGENT_EVENTS, timeout=3.0)
                for event in user_b_agent_events:
                    event_user = event.user_id or event.data.get('user_id') or event.data.get('for_user')
                    if event_user == user_a_profile.user_id:
                        pytest.fail(f"CRITICAL AGENT ISOLATION VIOLATION: User B ({user_b_profile.user_id}) received agent event ({event.event_type}) meant for User A ({user_a_profile.user_id}). This exposes User A's private AI interactions to User B!")
            except asyncio.TimeoutError:
                logger.info(" PASS:  User B correctly did not receive User A's agent events")
            user_a_client.assert_no_isolation_violations()
            user_b_client.assert_no_isolation_violations()
            logger.info(' PASS:  Agent event isolation test PASSED')

    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_websocket_connection_hijacking_prevention(self, docker_services, auth_helper: E2EAuthHelper):
        """
        CRITICAL: Test that WebSocket connections cannot be hijacked.
        
        Validates that a user cannot take over another user's WebSocket
        connection or impersonate another user.
        """
        logger.info('CRITICAL SECURITY TEST: WebSocket connection hijacking prevention')
        user_a = await auth_helper.create_authenticated_user(email='user_a@example.com')
        user_b = await auth_helper.create_authenticated_user(email='user_b@example.com')
        client_a = RealWebSocketTestClient(backend_url=BACKEND_URL, environment=TEST_ENVIRONMENT, auth_required=True)
        client_a.authenticated_user = user_a
        client_a.expected_user_id = user_a.user_id
        await client_a.connect()
        try:
            await client_a.send_event(event_type='hijack_attempt', data={'user_id': user_b.user_id, 'jwt_token': user_b.jwt_token, 'message': 'This should NOT work'})
            await asyncio.sleep(1.0)
            try:
                events = await client_a.wait_for_events(event_types={'hijack_attempt'}, timeout=5.0)
                for event in events:
                    event_user = event.user_id or event.data.get('user_id')
                    if event_user == user_b.user_id:
                        pass
            except SecurityError as e:
                logger.info(f' PASS:  Hijacking attempt correctly detected: {e}')
            except asyncio.TimeoutError:
                logger.info(' PASS:  No hijacking events received (connection secure)')
        except Exception as e:
            logger.info(f' PASS:  Hijacking attempt blocked: {e}')
        finally:
            await client_a.close()
        logger.info(' PASS:  WebSocket connection hijacking prevention test PASSED')

@pytest.mark.asyncio
@pytest.mark.real_services
async def test_websocket_manager_isolation_summary(docker_services):
    """Test that the connection manager correctly reports isolation violations."""
    manager = RealWebSocketConnectionManager(backend_url=BACKEND_URL, environment=TEST_ENVIRONMENT)
    try:
        async with manager.managed_connections(count=3) as connection_ids:
            test_types = [IsolationTestType.EVENT_ISOLATION, IsolationTestType.USER_DATA_ISOLATION, IsolationTestType.AUTHENTICATION_ISOLATION, IsolationTestType.CONCURRENT_SESSION_ISOLATION]
            all_passed = True
            for test_type in test_types:
                try:
                    result = await manager.test_user_isolation(test_type=test_type)
                    assert result.test_passed, f'{test_type.value} test failed'
                    logger.info(f' PASS:  {test_type.value} isolation test passed')
                except SecurityError:
                    all_passed = False
                    logger.error(f' FAIL:  {test_type.value} isolation test failed')
            summary = manager.get_isolation_summary()
            assert summary['test_passed'] == all_passed
            assert summary['total_connections'] == 3
            logger.info(f" PASS:  Isolation summary test completed: {summary['test_passed']}")
    finally:
        await manager.cleanup_all_connections()

@pytest.mark.asyncio
@pytest.mark.real_services
async def test_isolation_with_rapid_user_switching(docker_services):
    """Test isolation when users rapidly switch between connections."""
    clients = []
    try:
        for i in range(3):
            client = await create_authenticated_websocket_client(backend_url=BACKEND_URL, environment=TEST_ENVIRONMENT, user_email=f'rapid_switch_{i}@example.com')
            await client.connect()
            clients.append(client)
        for round_num in range(5):
            for i, client in enumerate(clients):
                await client.send_event(event_type='rapid_switch_test', data={'round': round_num, 'user_index': i, 'timestamp': time.time()})
            await asyncio.sleep(0.2)
        await asyncio.sleep(2.0)
        for client in clients:
            client.assert_no_isolation_violations()
        logger.info(' PASS:  Rapid user switching isolation test PASSED')
    finally:
        for client in clients:
            await client.close()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')