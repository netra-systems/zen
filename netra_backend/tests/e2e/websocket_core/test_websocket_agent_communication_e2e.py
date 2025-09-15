"""
Test WebSocket Agent Communication E2E - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Real-time agent communication and user experience
- Value Impact: Enables live agent feedback and responsive user interactions
- Strategic Impact: Core foundation for competitive AI chat experience

CRITICAL REQUIREMENTS:
- Tests real WebSocket connections with authentication
- Validates all 5 critical agent events are sent
- Ensures message delivery and user isolation
- No mocks - uses real WebSocket infrastructure
"""
import asyncio
import pytest
import json
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.websocket import WebSocketTestHelper
from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.handlers import WebSocketHandler
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, get_websocket_manager
from netra_backend.app.core.registry.universal_registry import get_global_registry

class WebSocketAgentCommunicationE2ETests(SSotBaseTestCase):
    """
    End-to-end WebSocket agent communication tests.
    
    Tests critical real-time communication that delivers business value:
    - Agent execution with live WebSocket events
    - User isolation in multi-user WebSocket environment
    - Event delivery reliability and ordering
    - Authentication and security in WebSocket context
    - Performance under realistic load
    """

    def __init__(self):
        """Initialize WebSocket agent communication test suite."""
        super().__init__()
        self.env = get_env()
        self.websocket_helper = WebSocketTestHelper()
        self.test_prefix = f'ws_agent_e2e_{uuid.uuid4().hex[:8]}'
        self.websocket_url = self.env.get('WEBSOCKET_URL', 'ws://localhost:8000/ws')
        self.required_agent_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

    def setup_websocket_auth(self, user_suffix: str='default') -> E2EWebSocketAuthHelper:
        """Set up WebSocket authentication helper."""
        return E2EWebSocketAuthHelper(environment=self.env.get('TEST_ENV', 'test'))

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_agent_execution_with_websocket_events(self):
        """
        Test complete agent execution with all required WebSocket events.
        
        BUSINESS CRITICAL: Agent events enable real-time user experience.
        Missing events make the system appear unresponsive to users.
        """
        ws_auth = self.setup_websocket_auth('agent_execution')
        try:
            websocket = await ws_auth.connect_authenticated_websocket(timeout=15.0)
            test_message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Help me understand my system performance', 'thread_id': f'thread_{uuid.uuid4().hex[:8]}', 'request_id': f'req_{uuid.uuid4().hex[:8]}'}
            await websocket.send(json.dumps(test_message))
            received_events = []
            agent_completed = False
            timeout_seconds = 30.0
            start_time = datetime.now()
            while not agent_completed and (datetime.now() - start_time).total_seconds() < timeout_seconds:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    received_events.append({'event': event, 'timestamp': datetime.now(), 'order': len(received_events)})
                    if event.get('type') == 'agent_completed':
                        agent_completed = True
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError as e:
                    pytest.fail(f'Received invalid JSON from WebSocket: {e}')
            assert agent_completed, f"Agent did not complete within {timeout_seconds}s. Events: {[e['event']['type'] for e in received_events]}"
            event_types = [event['event']['type'] for event in received_events]
            missing_events = []
            for required_event in self.required_agent_events:
                if required_event not in event_types:
                    missing_events.append(required_event)
            assert len(missing_events) == 0, f'CRITICAL: Missing required agent events: {missing_events}. Received: {event_types}'
            event_order_validation = self._validate_event_ordering(received_events)
            assert event_order_validation.is_valid, f'Event ordering invalid: {event_order_validation.error_message}'
            for event_record in received_events:
                event = event_record['event']
                event_type = event.get('type')
                assert 'timestamp' in event, f'Event {event_type} missing timestamp'
                assert 'data' in event, f'Event {event_type} missing data field'
                if event_type == 'agent_started':
                    assert 'agent_type' in event['data'], 'agent_started missing agent_type'
                    assert 'request_id' in event['data'], 'agent_started missing request_id'
                elif event_type == 'agent_thinking':
                    assert 'thought_process' in event['data'] or 'thinking_status' in event['data'], 'agent_thinking missing thought content'
                elif event_type in ['tool_executing', 'tool_completed']:
                    assert 'tool_name' in event['data'], f'{event_type} missing tool_name'
                elif event_type == 'agent_completed':
                    assert 'result' in event['data'] or 'response' in event['data'], 'agent_completed missing result/response'
                    assert 'execution_time' in event['data'], 'agent_completed missing execution_time'
            await websocket.close()
        except Exception as e:
            pytest.fail(f'WebSocket agent communication test failed: {e}')

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_websocket_isolation(self):
        """
        Test user isolation in multi-user WebSocket environment.
        
        BUSINESS CRITICAL: User isolation prevents data leakage between customers.
        One user must never see another user's agent responses.
        """
        user1_auth = self.setup_websocket_auth('isolation_user1')
        user2_auth = self.setup_websocket_auth('isolation_user2')
        try:
            user1_ws = await user1_auth.connect_authenticated_websocket(timeout=15.0)
            user2_ws = await user2_auth.connect_authenticated_websocket(timeout=15.0)
            user1_message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'User 1 confidential request about financial data', 'thread_id': f'user1_thread_{uuid.uuid4().hex[:8]}', 'request_id': f'user1_req_{uuid.uuid4().hex[:8]}', 'user_context': {'user_id': 'user_1_sensitive'}}
            user2_message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'User 2 confidential request about customer database', 'thread_id': f'user2_thread_{uuid.uuid4().hex[:8]}', 'request_id': f'user2_req_{uuid.uuid4().hex[:8]}', 'user_context': {'user_id': 'user_2_sensitive'}}
            await asyncio.gather(user1_ws.send(json.dumps(user1_message)), user2_ws.send(json.dumps(user2_message)))
            user1_events = []
            user2_events = []
            collection_timeout = 30.0
            start_time = datetime.now()
            both_completed = {'user1': False, 'user2': False}
            while not all(both_completed.values()) and (datetime.now() - start_time).total_seconds() < collection_timeout:
                try:
                    user1_event_raw = await asyncio.wait_for(user1_ws.recv(), timeout=1.0)
                    user1_event = json.loads(user1_event_raw)
                    user1_events.append(user1_event)
                    if user1_event.get('type') == 'agent_completed':
                        both_completed['user1'] = True
                except asyncio.TimeoutError:
                    pass
                try:
                    user2_event_raw = await asyncio.wait_for(user2_ws.recv(), timeout=1.0)
                    user2_event = json.loads(user2_event_raw)
                    user2_events.append(user2_event)
                    if user2_event.get('type') == 'agent_completed':
                        both_completed['user2'] = True
                except asyncio.TimeoutError:
                    pass
            assert both_completed['user1'], f'User 1 did not receive agent completion. Events: {len(user1_events)}'
            assert both_completed['user2'], f'User 2 did not receive agent completion. Events: {len(user2_events)}'
            user1_all_text = ' '.join((json.dumps(event).lower() for event in user1_events))
            user2_all_text = ' '.join((json.dumps(event).lower() for event in user2_events))
            user2_sensitive_terms = ['user_2_sensitive', 'customer database', user2_message['thread_id'], user2_message['request_id']]
            for sensitive_term in user2_sensitive_terms:
                assert sensitive_term.lower() not in user1_all_text, f"User 1 received User 2's data: '{sensitive_term}' found in User 1's events"
            user1_sensitive_terms = ['user_1_sensitive', 'financial data', user1_message['thread_id'], user1_message['request_id']]
            for sensitive_term in user1_sensitive_terms:
                assert sensitive_term.lower() not in user2_all_text, f"User 2 received User 1's data: '{sensitive_term}' found in User 2's events"
            assert user1_message['thread_id'] in user1_all_text, 'User 1 did not receive their own thread data'
            assert user2_message['thread_id'] in user2_all_text, 'User 2 did not receive their own thread data'
            await user1_ws.close()
            await user2_ws.close()
        except Exception as e:
            pytest.fail(f'Multi-user isolation test failed: {e}')

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_reliability_and_reconnection(self):
        """
        Test WebSocket reliability and reconnection handling.
        
        BUSINESS CRITICAL: Connection failures must not lose user data.
        System must handle reconnections gracefully without data loss.
        """
        ws_auth = self.setup_websocket_auth('reliability')
        try:
            websocket = await ws_auth.connect_authenticated_websocket(timeout=15.0)
            initial_message = {'type': 'agent_request', 'agent': 'data_analyzer', 'message': 'Analyze system performance for reliability test', 'thread_id': f'reliability_thread_{uuid.uuid4().hex[:8]}', 'request_id': f'reliability_req_{uuid.uuid4().hex[:8]}'}
            await websocket.send(json.dumps(initial_message))
            initial_events = []
            for _ in range(3):
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    initial_events.append(event)
                except asyncio.TimeoutError:
                    break
            await websocket.close(code=1000, reason='Simulated interruption')
            await asyncio.sleep(2.0)
            reconnected_websocket = await ws_auth.connect_authenticated_websocket(timeout=15.0)
            status_message = {'type': 'status_check', 'thread_id': initial_message['thread_id'], 'request_id': initial_message['request_id']}
            await reconnected_websocket.send(json.dumps(status_message))
            remaining_events = []
            agent_completed = False
            timeout_start = datetime.now()
            while not agent_completed and (datetime.now() - timeout_start).total_seconds() < 20.0:
                try:
                    event_data = await asyncio.wait_for(reconnected_websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    remaining_events.append(event)
                    if event.get('type') == 'agent_completed':
                        agent_completed = True
                except asyncio.TimeoutError:
                    break
            all_events = initial_events + remaining_events
            all_event_types = [event['type'] for event in all_events]
            assert 'agent_completed' in all_event_types, f'Agent completion lost during reconnection. Events: {all_event_types}'
            event_type_counts = {}
            for event_type in all_event_types:
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            for event_type in ['agent_started', 'agent_completed']:
                if event_type in event_type_counts:
                    assert event_type_counts[event_type] <= 2, f'Event {event_type} duplicated {event_type_counts[event_type]} times after reconnection'
            thread_consistency = True
            request_consistency = True
            for event in all_events:
                if 'data' in event and isinstance(event['data'], dict):
                    event_thread = event['data'].get('thread_id')
                    event_request = event['data'].get('request_id')
                    if event_thread and event_thread != initial_message['thread_id']:
                        thread_consistency = False
                    if event_request and event_request != initial_message['request_id']:
                        request_consistency = False
            assert thread_consistency, 'Thread ID inconsistency detected after reconnection'
            assert request_consistency, 'Request ID inconsistency detected after reconnection'
            await reconnected_websocket.close()
        except Exception as e:
            pytest.fail(f'WebSocket reliability test failed: {e}')

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_performance_under_load(self):
        """
        Test WebSocket performance under realistic load.
        
        BUSINESS CRITICAL: Poor performance impacts user experience.
        System must handle multiple concurrent users efficiently.
        """
        concurrent_users = 5
        user_auths = []
        for i in range(concurrent_users):
            auth = self.setup_websocket_auth(f'load_user_{i}')
            user_auths.append(auth)
        try:
            connection_start = datetime.now()
            websockets_list = await asyncio.gather(*[auth.connect_authenticated_websocket(timeout=15.0) for auth in user_auths])
            connection_time = (datetime.now() - connection_start).total_seconds()
            assert connection_time < 10.0, f'Concurrent connections too slow: {connection_time:.2f}s for {concurrent_users} users'
            agent_requests = []
            for i, websocket in enumerate(websockets_list):
                message = {'type': 'agent_request', 'agent': 'triage_agent', 'message': f'Load test request from user {i}', 'thread_id': f'load_thread_{i}_{uuid.uuid4().hex[:8]}', 'request_id': f'load_req_{i}_{uuid.uuid4().hex[:8]}'}
                agent_requests.append((websocket, message))
            send_start = datetime.now()
            await asyncio.gather(*[ws.send(json.dumps(msg)) for ws, msg in agent_requests])
            send_time = (datetime.now() - send_start).total_seconds()
            assert send_time < 5.0, f'Concurrent message sending too slow: {send_time:.2f}s'
            user_completions = [False] * concurrent_users
            response_times = [None] * concurrent_users
            user_events = [[] for _ in range(concurrent_users)]
            collection_start = datetime.now()
            timeout_seconds = 45.0
            while not all(user_completions) and (datetime.now() - collection_start).total_seconds() < timeout_seconds:
                for user_idx, websocket in enumerate(websockets_list):
                    if user_completions[user_idx]:
                        continue
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        event = json.loads(event_data)
                        user_events[user_idx].append(event)
                        if event.get('type') == 'agent_completed':
                            user_completions[user_idx] = True
                            response_times[user_idx] = (datetime.now() - collection_start).total_seconds()
                    except asyncio.TimeoutError:
                        continue
            completed_users = sum(user_completions)
            assert completed_users >= int(concurrent_users * 0.8), f'Too many users failed to complete: {completed_users}/{concurrent_users}'
            successful_response_times = [t for t in response_times if t is not None]
            if successful_response_times:
                avg_response_time = sum(successful_response_times) / len(successful_response_times)
                max_response_time = max(successful_response_times)
                assert avg_response_time < 30.0, f'Average response time too slow: {avg_response_time:.2f}s'
                assert max_response_time < 60.0, f'Maximum response time too slow: {max_response_time:.2f}s'
            for user_idx in range(concurrent_users):
                if user_completions[user_idx]:
                    user_event_types = [e['type'] for e in user_events[user_idx]]
                    core_events = ['agent_started', 'agent_completed']
                    missing_core = [e for e in core_events if e not in user_event_types]
                    assert len(missing_core) == 0, f'User {user_idx} missing core events: {missing_core}'
            await asyncio.gather(*[ws.close() for ws in websockets_list], return_exceptions=True)
        except Exception as e:
            pytest.fail(f'WebSocket load test failed: {e}')

    def _validate_event_ordering(self, received_events: List[Dict[str, Any]]) -> Any:
        """Validate that events are received in logical order."""
        event_types = [event['event']['type'] for event in received_events]
        ordering_rules = [('agent_started should come before agent_thinking', 'agent_started', 'agent_thinking'), ('agent_thinking should come before tool_executing', 'agent_thinking', 'tool_executing'), ('tool_executing should come before tool_completed', 'tool_executing', 'tool_completed'), ('agent_completed should be last', 'agent_completed', None)]
        errors = []
        for rule_name, first_event, second_event in ordering_rules:
            if second_event is None:
                if first_event in event_types:
                    first_idx = event_types.index(first_event)
                    if first_idx != len(event_types) - 1:
                        errors.append(f'{rule_name}: {first_event} not at end (position {first_idx}/{len(event_types)})')
            elif first_event in event_types and second_event in event_types:
                first_idx = event_types.index(first_event)
                second_idx = event_types.index(second_event)
                if first_idx >= second_idx:
                    errors.append(f'{rule_name}: {first_event}({first_idx}) should come before {second_event}({second_idx})')

        class ValidationResult:

            def __init__(self, is_valid: bool, error_message: str=''):
                self.is_valid = is_valid
                self.error_message = error_message
        if errors:
            return ValidationResult(False, '; '.join(errors))
        else:
            return ValidationResult(True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')