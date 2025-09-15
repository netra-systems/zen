"""
WebSocket Event Routing Multi-User Integration Tests - DESIGNED TO FAIL

This comprehensive integration test suite is designed to FAIL initially to expose critical
multi-user data leakage vulnerabilities in WebSocket event routing. The tests simulate
realistic multi-user scenarios where string-based IDs enable cross-user contamination.

CRITICAL INTEGRATION VIOLATIONS TO EXPOSE:
1. Multiple users connected simultaneously with overlapping string IDs
2. Message routing confusion between user sessions
3. Thread context bleeding between different user conversations
4. Connection state corruption affecting multiple users

Business Value Justification:
- Segment: Platform/Internal - Multi-User Security & Isolation  
- Business Goal: System Security & User Privacy Protection
- Value Impact: Prevents sensitive user data from leaking to other users
- Strategic Impact: Essential for production multi-user deployment

IMPORTANT: These tests are designed to FAIL until proper type safety and user isolation
fixes are implemented. Success would indicate the vulnerabilities have been resolved.
"""
import asyncio
import uuid
import json
import time
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import websockets
from shared.types import UserID, ThreadID, RunID, RequestID, WebSocketID, ConnectionID, ensure_user_id, ensure_thread_id, ensure_request_id, StronglyTypedUserExecutionContext, StronglyTypedWebSocketEvent
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.utils import extract_user_info_from_message

class TestWebSocketMultiUserDataLeakageIntegration(SSotBaseTestCase):
    """
    Integration tests to expose multi-user data leakage vulnerabilities.
    
    CRITICAL: These tests simulate realistic multi-user scenarios and should FAIL
    until proper type safety and isolation fixes are implemented.
    """

    async def asyncSetUp(self):
        """Set up multi-user test environment."""
        await super().asyncSetUp()
        self.user_1_id = ensure_user_id(f'user-1-{uuid.uuid4()}')
        self.user_2_id = ensure_user_id(f'user-2-{uuid.uuid4()}')
        self.user_3_id = ensure_user_id(f'user-3-{uuid.uuid4()}')
        self.user_1_thread = ensure_thread_id(f'thread-user1-{uuid.uuid4()}')
        self.user_2_thread = ensure_thread_id(f'thread-user2-{uuid.uuid4()}')
        self.user_3_thread = ensure_thread_id(f'thread-user3-{uuid.uuid4()}')
        self.user_1_request = ensure_request_id(f'req-user1-{uuid.uuid4()}')
        self.user_2_request = ensure_request_id(f'req-user2-{uuid.uuid4()}')
        self.user_3_request = ensure_request_id(f'req-user3-{uuid.uuid4()}')
        self.websocket_manager = UnifiedWebSocketManager()
        self.user_1_websocket = MagicMock()
        self.user_2_websocket = MagicMock()
        self.user_3_websocket = MagicMock()
        self.user_1_messages = []
        self.user_2_messages = []
        self.user_3_messages = []
        self._setup_message_tracking()

    def _setup_message_tracking(self):
        """Set up message tracking to detect cross-user leakage."""

        async def track_user_1_message(*args, **kwargs):
            self.user_1_messages.append(args)

        async def track_user_2_message(*args, **kwargs):
            self.user_2_messages.append(args)

        async def track_user_3_message(*args, **kwargs):
            self.user_3_messages.append(args)
        self.user_1_websocket.send = track_user_1_message
        self.user_2_websocket.send = track_user_2_message
        self.user_3_websocket.send = track_user_3_message

    async def test_concurrent_user_connections_id_collision_vulnerability(self):
        """
        CRITICAL FAILURE TEST: Test ID collision vulnerability with concurrent users.
        
        SCENARIO: Multiple users connect simultaneously with similar string-based IDs
        RISK: String-based ID generation may create collisions, causing cross-user mixing
        """
        connection_tasks = []
        for i, (user_id, websocket, request_id) in enumerate([(self.user_1_id, self.user_1_websocket, self.user_1_request), (self.user_2_id, self.user_2_websocket, self.user_2_request), (self.user_3_id, self.user_3_websocket, self.user_3_request)]):
            task = self.websocket_manager.add_connection(str(user_id), websocket, str(request_id))
            connection_tasks.append(task)
        connection_ids = await asyncio.gather(*connection_tasks)
        unique_connection_ids = set(connection_ids)
        if len(unique_connection_ids) != len(connection_ids):
            self.fail('CRITICAL VULNERABILITY: Connection ID collision detected - users mixed')
        for i, conn_id in enumerate(connection_ids):
            if not conn_id or conn_id in [connection_ids[j] for j in range(len(connection_ids)) if j != i]:
                self.fail(f'VULNERABILITY: User {i + 1} connection ID collision or generation failure')

    async def test_thread_association_cross_contamination(self):
        """
        CRITICAL FAILURE TEST: Test thread association contamination between users.
        
        SCENARIO: Users update thread associations concurrently
        RISK: String-based IDs may cause thread associations to cross-contaminate
        """
        conn_1 = await self.websocket_manager.add_connection(str(self.user_1_id), self.user_1_websocket, str(self.user_1_request))
        conn_2 = await self.websocket_manager.add_connection(str(self.user_2_id), self.user_2_websocket, str(self.user_2_request))
        result_1 = self.websocket_manager.update_connection_thread(conn_1, str(self.user_1_thread))
        result_2 = self.websocket_manager.update_connection_thread(conn_2, str(self.user_2_thread))
        user_1_message = {'type': 'agent_completed', 'data': {'private_result': f'CONFIDENTIAL_DATA_FOR_USER_1_{uuid.uuid4()}'}}
        user_2_message = {'type': 'agent_completed', 'data': {'private_result': f'CONFIDENTIAL_DATA_FOR_USER_2_{uuid.uuid4()}'}}
        await self.websocket_manager.send_to_thread(str(self.user_1_thread), user_1_message)
        await self.websocket_manager.send_to_thread(str(self.user_2_thread), user_2_message)
        user_1_received_data = [str(msg) for msg in self.user_1_messages]
        user_2_received_data = [str(msg) for msg in self.user_2_messages]
        for data in user_1_received_data:
            if 'USER_2' in data:
                self.fail("CRITICAL LEAK: User 1 received User 2's confidential data")
        for data in user_2_received_data:
            if 'USER_1' in data:
                self.fail("CRITICAL LEAK: User 2 received User 1's confidential data")

    async def test_high_frequency_message_routing_isolation_failure(self):
        """
        CRITICAL FAILURE TEST: Test message isolation under high-frequency routing.
        
        SCENARIO: Rapid message sending to multiple users simultaneously
        RISK: String-based routing may mix messages under load
        """
        connections = {}
        for user_id, websocket, request_id in [(self.user_1_id, self.user_1_websocket, self.user_1_request), (self.user_2_id, self.user_2_websocket, self.user_2_request), (self.user_3_id, self.user_3_websocket, self.user_3_request)]:
            conn_id = await self.websocket_manager.add_connection(str(user_id), websocket, str(request_id))
            connections[str(user_id)] = conn_id
        message_count = 50
        sent_messages = {str(self.user_1_id): [], str(self.user_2_id): [], str(self.user_3_id): []}
        tasks = []
        for i in range(message_count):
            for user_id in [self.user_1_id, self.user_2_id, self.user_3_id]:
                user_specific_data = f'USER_{user_id}_MESSAGE_{i}_{uuid.uuid4()}'
                message = {'type': 'agent_thinking', 'data': {'content': user_specific_data}}
                sent_messages[str(user_id)].append(user_specific_data)
                task = self.websocket_manager.send_to_user(str(user_id), message)
                tasks.append((str(user_id), task))
        await asyncio.gather(*[task for _, task in tasks])
        self._analyze_message_distribution_for_leaks(sent_messages)

    def _analyze_message_distribution_for_leaks(self, sent_messages: Dict[str, List[str]]):
        """Analyze received messages for cross-user leakage."""
        received_messages = {str(self.user_1_id): [str(msg) for msg in self.user_1_messages], str(self.user_2_id): [str(msg) for msg in self.user_2_messages], str(self.user_3_id): [str(msg) for msg in self.user_3_messages]}
        for receiving_user_id, received in received_messages.items():
            for message_content in received:
                for sending_user_id, sent_list in sent_messages.items():
                    if sending_user_id != receiving_user_id:
                        for sent_content in sent_list:
                            if sent_content in message_content:
                                self.fail(f'CRITICAL LEAK: User {receiving_user_id} received message intended for User {sending_user_id}: {sent_content}')

    async def test_async_context_bleeding_between_user_sessions(self):
        """
        CRITICAL FAILURE TEST: Test async context bleeding between user sessions.
        
        SCENARIO: Concurrent async operations on behalf of different users
        RISK: Async context may leak between users, causing data contamination
        """
        user_1_context = StronglyTypedUserExecutionContext(user_id=self.user_1_id, thread_id=self.user_1_thread, request_id=self.user_1_request, session_data={'sensitive_key': 'user_1_secret_token'})
        user_2_context = StronglyTypedUserExecutionContext(user_id=self.user_2_id, thread_id=self.user_2_thread, request_id=self.user_2_request, session_data={'sensitive_key': 'user_2_secret_token'})

        async def user_1_operation():
            """Simulate User 1's operation with sensitive context"""
            await asyncio.sleep(0.1)
            current_context = user_1_context
            if current_context.user_id != self.user_1_id:
                raise ValueError('User 1 context corrupted')
            message = {'type': 'user_data_request', 'data': {'user_secret': current_context.session_data['sensitive_key']}}
            await self.websocket_manager.send_to_user(str(self.user_1_id), message)
            return 'user_1_operation_complete'

        async def user_2_operation():
            """Simulate User 2's operation with sensitive context"""
            await asyncio.sleep(0.1)
            current_context = user_2_context
            if current_context.user_id != self.user_2_id:
                raise ValueError('User 2 context corrupted')
            message = {'type': 'user_data_request', 'data': {'user_secret': current_context.session_data['sensitive_key']}}
            await self.websocket_manager.send_to_user(str(self.user_2_id), message)
            return 'user_2_operation_complete'
        results = await asyncio.gather(user_1_operation(), user_2_operation(), return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                if 'context corrupted' in str(result):
                    self.fail(f'CRITICAL VULNERABILITY: Async context corruption detected for user {i + 1}')
        user_1_received = [str(msg) for msg in self.user_1_messages]
        user_2_received = [str(msg) for msg in self.user_2_messages]
        for msg in user_1_received:
            if 'user_2_secret_token' in msg:
                self.fail("CRITICAL LEAK: User 1 received User 2's secret token")
        for msg in user_2_received:
            if 'user_1_secret_token' in msg:
                self.fail("CRITICAL LEAK: User 2 received User 1's secret token")

    async def test_connection_state_corruption_multi_user_impact(self):
        """
        CRITICAL FAILURE TEST: Test connection state corruption affecting multiple users.
        
        SCENARIO: Connection state changes affect other users' connections
        RISK: Shared state or string-based IDs cause state corruption across users
        """
        user_connections = {}
        for user_id, websocket, request_id in [(self.user_1_id, self.user_1_websocket, self.user_1_request), (self.user_2_id, self.user_2_websocket, self.user_2_request), (self.user_3_id, self.user_3_websocket, self.user_3_request)]:
            conn_id = await self.websocket_manager.add_connection(str(user_id), websocket, str(request_id))
            user_connections[str(user_id)] = conn_id
        user_1_new_thread = ensure_thread_id(f'new-thread-user1-{uuid.uuid4()}')
        update_result = self.websocket_manager.update_connection_thread(user_connections[str(self.user_1_id)], str(user_1_new_thread))
        test_messages = [(str(self.user_2_id), {'type': 'test', 'data': 'user_2_test'}), (str(self.user_3_id), {'type': 'test', 'data': 'user_3_test'})]
        for user_id, message in test_messages:
            await self.websocket_manager.send_to_user(user_id, message)
        if not self.user_2_messages:
            self.fail("CORRUPTION: User 2 connection affected by User 1's thread update")
        if not self.user_3_messages:
            self.fail("CORRUPTION: User 3 connection affected by User 1's thread update")

    async def test_error_isolation_between_user_sessions(self):
        """
        CRITICAL FAILURE TEST: Verify errors in one user's session don't affect others.
        
        SCENARIO: One user's connection encounters an error
        RISK: Error handling may affect other users' active sessions
        """
        conn_1 = await self.websocket_manager.add_connection(str(self.user_1_id), self.user_1_websocket, str(self.user_1_request))
        conn_2 = await self.websocket_manager.add_connection(str(self.user_2_id), self.user_2_websocket, str(self.user_2_request))
        self.user_1_websocket.send = AsyncMock(side_effect=Exception('Connection error'))
        error_message = {'type': 'test', 'data': 'should_fail'}
        with pytest.raises(Exception):
            await self.websocket_manager.send_to_user(str(self.user_1_id), error_message)
        success_message = {'type': 'test', 'data': 'should_succeed'}
        try:
            await self.websocket_manager.send_to_user(str(self.user_2_id), success_message)
        except Exception as e:
            self.fail(f"ISOLATION FAILURE: User 2 connection affected by User 1's error: {e}")
        if not self.user_2_messages:
            self.fail("ISOLATION FAILURE: User 2 did not receive message after User 1's error")

    async def test_connection_churn_data_leakage_stress(self):
        """
        CRITICAL FAILURE TEST: Stress test connection churn for data leakage.
        
        SCENARIO: Rapid connection/disconnection cycles with message sending
        RISK: Connection reuse or ID reuse may cause message misrouting
        """
        iterations = 20
        leaked_messages = []
        for i in range(iterations):
            temp_user_id = ensure_user_id(f'temp-user-{i}-{uuid.uuid4()}')
            temp_websocket = MagicMock()
            temp_messages = []

            async def track_temp_message(*args, **kwargs):
                temp_messages.append(args)
            temp_websocket.send = track_temp_message
            conn_id = await self.websocket_manager.add_connection(str(temp_user_id), temp_websocket, f'req-{i}')
            unique_content = f'TEMP_USER_{i}_PRIVATE_DATA_{uuid.uuid4()}'
            message = {'type': 'test', 'data': {'private': unique_content}}
            await self.websocket_manager.send_to_user(str(temp_user_id), message)
            await self.websocket_manager.remove_connection(conn_id)
            all_other_messages = [str(msg) for msg in self.user_1_messages] + [str(msg) for msg in self.user_2_messages] + [str(msg) for msg in self.user_3_messages]
            for other_message in all_other_messages:
                if unique_content in other_message:
                    leaked_messages.append(f'Iteration {i}: {unique_content} leaked to persistent user')
        if leaked_messages:
            self.fail(f'CRITICAL LEAKS DETECTED: {len(leaked_messages)} messages leaked: {leaked_messages}')

    def test_multi_user_performance_degradation_symptoms(self):
        """
        Test for performance symptoms that might indicate underlying isolation issues.
        
        Poor performance under multi-user load often indicates shared state or locking issues
        that can also cause data leakage vulnerabilities.
        """
        start_time = time.time()
        user_count = 10
        messages_per_user = 50
        total_operations = user_count * messages_per_user
        setup_time = time.time() - start_time
        self.test_metrics.record_custom('multi_user_setup_time', setup_time)
        self.test_metrics.record_custom('simulated_user_count', user_count)
        self.test_metrics.record_custom('messages_per_user', messages_per_user)
        self.test_metrics.record_custom('total_simulated_operations', total_operations)
        if setup_time > 5.0:
            self.test_metrics.record_custom('performance_warning', 'Setup took >5s - possible shared state issues')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')