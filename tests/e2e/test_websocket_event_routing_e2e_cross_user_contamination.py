""""""
WebSocket Event Routing E2E Cross-User Contamination Tests - DESIGNED TO FAIL

This comprehensive E2E test suite is designed to FAIL initially to expose critical cross-user
message contamination vulnerabilities in production-like scenarios. The tests use real 
authentication flows, WebSocket connections, and multi-user concurrent operations to simulate
actual production conditions where data leakage can occur.

CRITICAL E2E VIOLATIONS TO EXPOSE:
    1. Real authenticated users receiving messages intended for other users
2. WebSocket message routing failures under concurrent multi-user load
3. Session context bleeding between different authenticated user sessions
4. Agent execution results being delivered to wrong users

Business Value Justification:
    - Segment: Enterprise/Production - Multi-User Security & Data Privacy
- Business Goal: Customer Trust & Data Protection Compliance
- Value Impact: Prevents customer data breaches and regulatory violations
- Strategic Impact: Essential for enterprise deployment and customer confidence

IMPORTANT: These tests use REAL AUTHENTICATION and REAL WEBSOCKET CONNECTIONS.
They are designed to FAIL until comprehensive type safety and isolation fixes are implemented.
Success would indicate production-ready multi-user security.
""""""
import asyncio
import json
import uuid
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import pytest
import websockets
import aiohttp
from shared.types import UserID, ThreadID, RunID, RequestID, ensure_user_id, ensure_thread_id, ensure_request_id, StronglyTypedUserExecutionContext
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.staging_config import StagingTestConfig

@dataclass
class UserTestSession:
    "Represents a complete user test session with auth and WebSocket."""
    user_id: UserID
    email: str
    jwt_token: str
    websocket_connection: Optional[websockets.ServerConnection] = None
    thread_id: Optional[ThreadID] = None
    received_messages: List[Dict[str, Any]] = field(default_factory=list)
    sent_messages: List[Dict[str, Any]] = field(default_factory=list)
    auth_context: Optional[Dict[str, Any]] = None
    connection_id: Optional[str] = None

    def add_received_message(self, message: Dict[str, Any):
        "Track received message with timestamp."
        message_with_meta = {**message, '_received_at': time.time(), '_user_id': str(self.user_id)}
        self.received_messages.append(message_with_meta)

    def add_sent_message(self, message: Dict[str, Any):
        "Track sent message with timestamp."
        message_with_meta = {**message, '_sent_at': time.time(), '_user_id': str(self.user_id)}
        self.sent_messages.append(message_with_meta)

@pytest.mark.e2e
class WebSocketE2ECrossUserContaminationTests(SSotBaseTestCase):
    pass
""""""
    E2E tests to expose cross-user message contamination in production scenarios.
    
    CRITICAL: These tests use real authentication and WebSocket connections.
    They should FAIL until comprehensive isolation fixes are implemented.
""

    async def asyncSetUp(self):
        Set up complete E2E test environment with real authentication.""
        await super().asyncSetUp()
        self.auth_helper = E2EAuthHelper(E2EAuthConfig())
        self.user_sessions: Dict[str, UserTestSession] = {}
        await self._setup_authenticated_users()
        self.contamination_incidents: List[Dict[str, Any]] = []
        self.performance_metrics = {'connection_times': [], 'message_latencies': [], 'auth_validation_times': []}

    async def _setup_authenticated_users(self):
        Set up multiple authenticated user sessions.""
        user_configs = [('alice', 'alice.enterprise@example.com', 'EnterpriseAlice123!'), ('bob', 'bob.business@example.com', 'BusinessBob456!'), ('charlie', 'charlie.customer@example.com', 'CustomerCharlie789!')]
        for username, email, password in user_configs:
            user_id = ensure_user_id(f'{username}-{uuid.uuid4()}')
            auth_start_time = time.time()
            auth_result = await self.auth_helper.authenticate_user(email, password)
            auth_time = time.time() - auth_start_time
            self.performance_metrics['auth_validation_times'].append(auth_time)
            session = UserTestSession(user_id=user_id, email=email, jwt_token=auth_result['jwt_token'], auth_context=auth_result)
            self.user_sessions[username] = session

    async def _establish_websocket_connections(self):
        "Establish authenticated WebSocket connections for all users."""
        connection_tasks = []
        for username, session in self.user_sessions.items():
            task = self._connect_user_websocket(username, session)
            connection_tasks.append(task)
        await asyncio.gather(*connection_tasks)

    async def _connect_user_websocket(self, username: str, session: UserTestSession):
        "Connect a user's WebSocket with authentication.'"
        websocket_url = self.auth_helper.config.websocket_url
        headers = {'Authorization': f'Bearer {session.jwt_token}', 'X-User-ID': str(session.user_id)}
        try:
            connection_start_time = time.time()
            session.websocket_connection = await websockets.connect(websocket_url, extra_headers=headers, timeout=10)
            connection_time = time.time() - connection_start_time
            self.performance_metrics['connection_times'].append(connection_time)
            asyncio.create_task(self._listen_for_messages(username, session))
        except Exception as e:
            self.fail(f'Failed to establish WebSocket connection for {username}: {e}')

    async def _listen_for_messages(self, username: str, session: UserTestSession):
        "Listen for messages on user's WebSocket connection.'"
        try:
            async for raw_message in session.websocket_connection:
                try:
                    message = json.loads(raw_message)
                    session.add_received_message(message)
                    await self._check_message_contamination(username, session, message)
                except json.JSONDecodeError:
                    session.add_received_message({'type': 'malformed', 'raw_content': raw_message, 'error': 'json_decode_error')
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.fail(f'Error listening for messages for {username}: {e}')

    async def _check_message_contamination(self, username: str, session: UserTestSession, message: Dict[str, Any):
        Check if a message shows signs of cross-user contamination.""
        other_users = [name for name in self.user_sessions.keys() if name != username]
        message_str = json.dumps(message).lower()
        for other_username in other_users:
            other_session = self.user_sessions[other_username]
            if str(other_session.user_id).lower() in message_str:
                self.contamination_incidents.append({'type': 'user_id_contamination', 'receiving_user': username, 'foreign_user_id': str(other_session.user_id), 'message': message, 'timestamp': time.time()}
            if other_session.email.lower() in message_str:
                self.contamination_incidents.append({'type': 'email_contamination', 'receiving_user': username, 'foreign_email': other_session.email, 'message': message, 'timestamp': time.time()}

    async def test_authenticated_cross_user_message_contamination(self):
        
        CRITICAL FAILURE TEST: Test cross-user message contamination with real authentication.
        
        SCENARIO: Multiple authenticated users connected simultaneously
        RISK: Messages intended for one authenticated user reach another
""
        await self._establish_websocket_connections()
        await asyncio.sleep(1)
        user_messages = {'alice': {'type': 'agent_completed', 'data': {'result': f'ALICE_ENTERPRISE_PRIVATE_KEY_{uuid.uuid4()}', 'user_context': 'enterprise_admin_access', 'sensitive_data': {'api_keys': ['alice_key_1', 'alice_key_2'], 'account_balance': '$1,0,0'}}}, 'bob': {'type': 'agent_completed', 'data': {'result': f'BOB_BUSINESS_CONFIDENTIAL_{uuid.uuid4()}', 'user_context': 'business_manager_access', 'sensitive_data': {'client_list': ['client_a', 'client_b'], 'revenue_data': '$500,0'}}}, 'charlie': {'type': 'agent_completed', 'data': {'result': f'CHARLIE_CUSTOMER_PERSONAL_{uuid.uuid4()}', 'user_context': 'customer_basic_access', 'sensitive_data': {'personal_info': {'ssn': '123-45-6789'}, 'purchase_history': ['item1', 'item2']}}}}
        send_tasks = []
        for username, message in user_messages.items():
            session = self.user_sessions[username]
            task = self._send_authenticated_message(session, message)
            send_tasks.append((username, task))
        send_results = await asyncio.gather(*[task for _, task in send_tasks], return_exceptions=True)
        await asyncio.sleep(2)
        await self._analyze_cross_user_contamination(user_messages)

    async def _send_authenticated_message(self, session: UserTestSession, message: Dict[str, Any):
        Send message via authenticated backend API.""
        backend_url = self.auth_helper.config.backend_url
        headers = {'Authorization': f'Bearer {session.jwt_token}', 'Content-Type': 'application/json'}
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(f'{backend_url}/api/v1/websocket/send-to-user', headers=headers, json={'user_id': str(session.user_id), 'message': message} as response:
                if response.status not in [200, 201, 202]:
                    self.fail(f'Failed to send message via API: {response.status}')
        session.add_sent_message(message)

    async def _analyze_cross_user_contamination(self, expected_messages: Dict[str, Dict[str, Any)):
        "Analyze received messages for cross-user contamination."""
        contamination_errors = []
        for username, session in self.user_sessions.items():
            expected_content = json.dumps(expected_messages[username].lower()
            for received_message in session.received_messages:
                received_content = json.dumps(received_message).lower()
                for other_username, other_expected in expected_messages.items():
                    if other_username != username:
                        other_content_markers = [str(other_expected['data']['result'].lower(), other_expected['data']['user_context'].lower()]
                        for marker in other_content_markers:
                            if marker in received_content:
                                contamination_errors.append(f"CRITICAL CONTAMINATION: User {username} received content intended for {other_username}: marker '{marker}' found)"
        for incident in self.contamination_incidents:
            contamination_errors.append(fREAL-TIME CONTAMINATION: {incident['type']} - {incident['receiving_user']} received foreign data")"
        if contamination_errors:
            self.fail(f'CRITICAL CONTAMINATION DETECTED: {len(contamination_errors)} incidents: ' + '; '.join(contamination_errors))

    async def test_concurrent_agent_execution_result_contamination(self):
    """"""
        CRITICAL FAILURE TEST: Test agent execution result contamination.
        
        SCENARIO: Multiple users trigger agent executions simultaneously
        RISK: Agent results intended for one user delivered to another
""""""
        await self._establish_websocket_connections()
        agent_requests = {'alice': {'type': 'start_agent', 'data': {'agent_type': 'DataAnalyzerAgent', 'query': 'Analyze enterprise revenue data for Q4', 'context': {'department': 'finance', 'level': 'executive'}}}, 'bob': {'type': 'start_agent', 'data': {'agent_type': 'CustomerInsightAgent', 'query': 'Generate customer satisfaction report', 'context': {'department': 'marketing', 'level': 'manager'}}}, 'charlie': {'type': 'start_agent', 'data': {'agent_type': 'PersonalAssistantAgent', 'query': 'Help me plan my vacation', 'context': {'department': 'personal', 'level': 'customer'}}}}
        execution_tasks = []
        for username, request in agent_requests.items():
            session = self.user_sessions[username]
            task = self._execute_agent_request(session, request)
            execution_tasks.append((username, task))
        await asyncio.gather(*[task for _, task in execution_tasks)
        await asyncio.sleep(5)
        await self._analyze_agent_result_contamination(agent_requests)

    async def _execute_agent_request(self, session: UserTestSession, request: Dict[str, Any):
        Execute agent request via authenticated WebSocket.""
        if session.websocket_connection:
            authenticated_request = {**request, 'user_id': str(session.user_id), 'jwt_token': session.jwt_token}
            await session.websocket_connection.send(json.dumps(authenticated_request))
            session.add_sent_message(authenticated_request)

    async def _analyze_agent_result_contamination(self, original_requests: Dict[str, Dict[str, Any)):
        Analyze agent execution results for cross-user contamination.""
        result_contamination_errors = []
        for username, session in self.user_sessions.items():
            user_request_context = original_requests[username]['data']['context']
            for received_message in session.received_messages:
                if received_message.get('type') in ['agent_completed', 'agent_result', 'tool_completed']:
                    message_content = json.dumps(received_message).lower()
                    for other_username, other_request in original_requests.items():
                        if other_username != username:
                            other_context = other_request['data']['context']
                            context_markers = [other_context.get('department', '').lower(), other_context.get('level', '').lower()]
                            for marker in context_markers:
                                if marker and marker in message_content:
                                    result_contamination_errors.append(fAGENT RESULT CONTAMINATION: User {username} received agent result with {other_username}'s context marker '{marker}'")'"
        if result_contamination_errors:
            self.fail(f'CRITICAL AGENT CONTAMINATION: {len(result_contamination_errors)} incidents: ' + '; '.join(result_contamination_errors))

    async def test_thread_context_isolation_under_load(self):
    """"""
        CRITICAL FAILURE TEST: Test thread context isolation under concurrent load.
        
        SCENARIO: Users have multiple conversation threads simultaneously
        RISK: Thread contexts mix between users or between different threads
""""""
        await self._establish_websocket_connections()
        user_threads = {}
        for username, session in self.user_sessions.items():
            session.thread_id = ensure_thread_id(f'main-thread-{username}-{uuid.uuid4()}')
            user_threads[username] = [ensure_thread_id(f'thread1-{username}-{uuid.uuid4()}'), ensure_thread_id(f'thread2-{username}-{uuid.uuid4()}'), ensure_thread_id(f'thread3-{username}-{uuid.uuid4()}')]
        thread_messages = {}
        send_tasks = []
        for username, threads in user_threads.items():
            session = self.user_sessions[username]
            thread_messages[username] = {}
            for i, thread_id in enumerate(threads):
                message = {'type': 'user_message', 'data': {'content': f'{username}_thread_{i}_message_{uuid.uuid4()}', 'thread_context': f'{username}_private_context_{i}', 'thread_id': str(thread_id)}}
                thread_messages[username][str(thread_id)] = message
                task = self._send_thread_message(session, thread_id, message)
                send_tasks.append((username, str(thread_id), task))
        await asyncio.gather(*[task for _, _, task in send_tasks)
        await asyncio.sleep(3)
        await self._analyze_thread_isolation(thread_messages)

    async def _send_thread_message(self, session: UserTestSession, thread_id: ThreadID, message: Dict[str, Any):
        Send message to specific thread.""
        backend_url = self.auth_helper.config.backend_url
        headers = {'Authorization': f'Bearer {session.jwt_token}', 'Content-Type': 'application/json'}
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(f'{backend_url}/api/v1/websocket/send-to-thread', headers=headers, json={'thread_id': str(thread_id), 'message': message} as response:
                if response.status not in [200, 201, 202]:
                    self.fail(f'Failed to send thread message: {response.status}')

    async def _analyze_thread_isolation(self, expected_thread_messages: Dict[str, Dict[str, Dict[str, Any))):
        Analyze thread message isolation.""
        isolation_errors = []
        for username, session in self.user_sessions.items():
            user_expected_threads = expected_thread_messages[username]
            for received_message in session.received_messages:
                received_content = json.dumps(received_message).lower()
                for other_username, other_threads in expected_thread_messages.items():
                    if other_username != username:
                        for thread_id, expected_message in other_threads.items():
                            other_context = expected_message['data']['thread_context'].lower()
                            if other_context in received_content:
                                isolation_errors.append(fTHREAD ISOLATION VIOLATION: User {username} received message with {other_username}'s thread context '{other_context}'")'"
        if isolation_errors:
            self.fail(f'CRITICAL THREAD ISOLATION FAILURES: {len(isolation_errors)} violations: ' + '; '.join(isolation_errors))

    async def test_session_cleanup_data_persistence_leak(self):
    """"""
        CRITICAL FAILURE TEST: Test data persistence after session cleanup.
        
        SCENARIO: User disconnects and reconnects, another user connects in between
        RISK: Previous user's data persists and leaks to subsequent user'
""""""
        await self._establish_websocket_connections()
        alice_session = self.user_sessions['alice']
        sensitive_message = {'type': 'user_data_storage', 'data': {'sensitive_content': f'ALICE_PRIVATE_DATA_{uuid.uuid4()}', 'user_session_info': 'alice_personal_details'}}
        await self._send_authenticated_message(alice_session, sensitive_message)
        await asyncio.sleep(1)
        await alice_session.websocket_connection.close()
        alice_session.websocket_connection = None
        await asyncio.sleep(0.5)
        await self._connect_user_websocket('charlie', self.user_sessions['charlie')
        await asyncio.sleep(1)
        await self._connect_user_websocket('alice', alice_session)
        await asyncio.sleep(2)
        charlie_session = self.user_sessions['charlie']
        for message in charlie_session.received_messages:
            message_content = json.dumps(message).lower()
            if 'alice_private_data' in message_content or 'alice_personal_details' in message_content:
                self.fail(CRITICAL SESSION LEAK: Charlie received Alice's data after Alice's disconnection)
        for message in alice_session.received_messages:
            message_content = json.dumps(message).lower()
            if 'charlie' in message_content:
                self.fail("CRITICAL SESSION CONTAMINATION: Alice received Charlie's data after reconnection)'"

    def test_multi_user_performance_impact_analysis(self):
        pass
        Test performance impact under multi-user scenarios.
        
        Poor performance under multi-user load often indicates shared resource
        contention that can also manifest as data leakage vulnerabilities.
""
        avg_connection_time = sum(self.performance_metrics['connection_times'] / max(len(self.performance_metrics['connection_times'], 1)
        avg_auth_time = sum(self.performance_metrics['auth_validation_times'] / max(len(self.performance_metrics['auth_validation_times'], 1)
        self.test_metrics.record_custom('avg_connection_time', avg_connection_time)
        self.test_metrics.record_custom('avg_auth_time', avg_auth_time)
        self.test_metrics.record_custom('total_contamination_incidents', len(self.contamination_incidents))
        if avg_connection_time > 5.0:
            self.test_metrics.record_custom('performance_warning', 'Connection time >"5s" - possible resource contention')
        if avg_auth_time > 2.0:
            self.test_metrics.record_custom('performance_warning', 'Auth time >"2s" - possible shared state issues')
        self.test_metrics.record_custom('contamination_incidents_detected', self.contamination_incidents)

    async def asyncTearDown(self):
        Clean up all WebSocket connections and resources.""
        for session in self.user_sessions.values():
            if session.websocket_connection:
                try:
                    await session.websocket_connection.close()
                except Exception:
                    pass
        await super().asyncTearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
""""

)))))))))))))))))))))))