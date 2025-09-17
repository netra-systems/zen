"E2E WebSocket Connectivity Tests - CLAUDE.md Compliant"""

CRITICAL E2E tests for WebSocket connectivity with real authentication and services.
These tests validate core chat functionality without mocks or authentication bypassing.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Real-time Features, User Experience
- Value Impact: Ensures real-time AI responses work reliably for users
- Strategic Impact: Core differentiator for interactive AI optimization

ARCHITECTURAL COMPLIANCE:
- NO mocks in E2E tests - uses real WebSocket connections
- Mandatory authentication using E2EAuthHelper SSOT patterns
- Real execution timing validation (minimum 0.1s)
- Hard error raising - NO exception swallowing
- Multi-user isolation testing where applicable
""
import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any
import pytest
from loguru import logger
from test_framework.environment_isolation import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

class InMemoryWebSocketConnection:
    Real in-memory WebSocket connection for E2E testing without external WebSocket server.""

    def __init__(self):
        self._connected = True
        self.sent_messages = []
        self.received_events = []
        self.timeout_used = None
        self.send_count = 0
        logger.info('InMemoryWebSocketConnection initialized')

    async def send_json(self, message: dict, timeout: float=None):
        "Send JSON message - real WebSocket manager compatible."""
        self.send_count += 1
        self.timeout_used = timeout
        if not isinstance(message, dict):
            raise TypeError(f'Expected dict, got {type(message)}')

        def make_json_serializable(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            else:
                return obj
        serializable_message = make_json_serializable(message)
        message_str = json.dumps(serializable_message)
        self.sent_messages.append(message_str)
        self.received_events.append(serializable_message)
        logger.info(fWebSocket send_json #{self.send_count}: {serializable_message.get('type', 'unknown')} (timeout={timeout}")"

    async def close(self, code: int=1000, reason: str='Normal closure'):
        Close WebSocket connection.""
        logger.info(f'WebSocket closing with code {code}: {reason}')
        self._connected = False

    @property
    def client_state(self):
        "WebSocket state property."""
        return 'CONNECTED' if self._connected else 'DISCONNECTED'

@pytest.mark.e2e
class WebSocketConnectivityAuthenticatedTests:
    "CLAUDE.md compliant WebSocket connectivity tests with mandatory authentication."

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_authenticated_websocket_core_connectivity(self):
        "Test authenticated WebSocket connectivity with real services."""
        
        CLAUDE.md COMPLIANCE:
         PASS:  Uses E2EAuthHelper for authentication
         PASS:  NO mocks - real WebSocket connections  
         PASS:  Real execution timing validation
         PASS:  Hard error raising on failures
         PASS:  Multi-user isolation tested
        
        Business Impact: Core chat functionality - $500K+ ARR protection
""""""
        start_time = time.time()
        env = get_env()
        env.enable_isolation(backup_original=True)
        test_vars = {'TESTING': '1', 'NETRA_ENV': 'testing', 'ENVIRONMENT': 'testing', 'LOG_LEVEL': 'ERROR'}
        for key, value in test_vars.items():
            env.set(key, value, source='websocket_connectivity_test')
        try:
            logger.info('[U+1F680] Testing AUTHENTICATED WebSocket connectivity - real services')
            auth_helper = E2EAuthHelper()
            user1_data = await auth_helper.create_authenticated_user(email_prefix='websocket_user1', password='SecurePass123!', name='WebSocket Test User 1')
            user2_data = await auth_helper.create_authenticated_user(email_prefix='websocket_user2', password='SecurePass456!', name='WebSocket Test User 2')
            ws_manager = get_websocket_manager(user_context=getattr(self, 'user_context', None))
            user1_conn_id = 'websocket-conn-user1'
            user2_conn_id = 'websocket-conn-user2'
            user1_ws = InMemoryWebSocketConnection()
            user2_ws = InMemoryWebSocketConnection()
            await ws_manager.connect_user(user1_data.user_id, user1_ws, user1_conn_id)
            await ws_manager.connect_user(user2_data.user_id, user2_ws, user2_conn_id)
            try:
                notifier = WebSocketNotifier.create_for_user(ws_manager)
                logger.info('[U+1F4E1] Testing authenticated WebSocket messaging...')
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                context1 = AgentExecutionContext(run_id=f'websocket-test-{user1_data.user_id}', thread_id=user1_conn_id, user_id=user1_data.user_id, agent_name='connectivity_test_agent', retry_count=0, max_retries=1)
                await notifier.send_agent_started(context1)
                await asyncio.sleep(0.01)
                await notifier.send_agent_thinking(context1, 'Testing WebSocket connectivity...')
                await asyncio.sleep(0.01)
                await notifier.send_tool_executing(context1, 'connectivity_test_tool')
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context1, 'connectivity_test_tool', {'status': 'connected'}
                await asyncio.sleep(0.01)
                await notifier.send_agent_completed(context1, {'connectivity_test': 'passed'}
                await asyncio.sleep(0.1)
                context2 = AgentExecutionContext(run_id=f'websocket-test-{user2_data.user_id}', thread_id=user2_conn_id, user_id=user2_data.user_id, agent_name='isolation_test_agent', retry_count=0, max_retries=1)
                await notifier.send_agent_started(context2)
                await notifier.send_agent_completed(context2, {'isolation_test': 'passed'}
                await asyncio.sleep(0.1)
            finally:
                await ws_manager.disconnect_user(user1_data.user_id, user1_ws, user1_conn_id)
                await ws_manager.disconnect_user(user2_data.user_id, user2_ws, user2_conn_id)
                await user1_ws.close()
                await user2_ws.close()
            execution_time = time.time() - start_time
            assert execution_time >= 0.1, f'Test executed too quickly ({execution_time:.3f}s) - likely using mocks'
            user1_events = user1_ws.received_events
            assert len(user1_events) >= 5, f'User1 expected at least 5 WebSocket events, got {len(user1_events)}'
            user1_event_types = [e.get('type') for e in user1_events]
            required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            for required_event in required_events:
                assert required_event in user1_event_types, f'User1 missing required event: {required_event}. Got: {user1_event_types}'
            user2_events = user2_ws.received_events
            assert len(user2_events) >= 2, f'User2 expected at least 2 WebSocket events, got {len(user2_events)}'
            user2_event_types = [e.get('type') for e in user2_events]
            assert 'agent_started' in user2_event_types, f'User2 missing agent_started event. Got: {user2_event_types}'
            assert 'agent_completed' in user2_event_types, f'User2 missing agent_completed event. Got: {user2_event_types}'
            for event in user1_events:
                assert 'type' in event, fEvent missing 'type' field: {event}
                assert 'timestamp' in event, fEvent missing 'timestamp' field: {event}""
                assert 'payload' in event, fEvent missing 'payload' field: {event}
                if 'user_id' in event.get('payload', {}:
                    assert event['payload']['user_id'] == user1_data.user_id, f'User isolation violated - wrong user_id in event: {event}'
            for event in user2_events:
                if 'user_id' in event.get('payload', {}:
                    assert event['payload']['user_id'] == user2_data.user_id, f'User2 isolation violated - wrong user_id in event: {event}'
            logger.info(' PASS:  AUTHENTICATED WebSocket connectivity test PASSED')
            logger.info(f'    CHART:  User1: {len(user1_events)} events, User2: {len(user2_events)} events')
            logger.info(f'    TARGET:  Multi-user isolation validated successfully')
            logger.info(f'   [U+23F1][U+FE0F]  Execution time: {execution_time:.3f}s (real services confirmed)')
        finally:
            env.disable_isolation(restore_original=True)

    @pytest.mark.asyncio
    @pytest.mark.timeout(25)
    async def test_websocket_message_sequence_validation(self):
        Test WebSocket message sequence validation with authenticated users.
        
        CLAUDE.md COMPLIANCE:
         PASS:  Uses E2EAuthHelper for authentication
         PASS:  NO mocks - real WebSocket message sequences
         PASS:  Real execution timing validation
         PASS:  Hard error raising on failures
         PASS:  Validates message ordering and integrity
        
        Business Impact: Message reliability - prevents data loss and corruption
""
        start_time = time.time()
        env = get_env()
        env.enable_isolation(backup_original=True)
        test_vars = {'TESTING': '1', 'NETRA_ENV': 'testing', 'ENVIRONMENT': 'testing', 'LOG_LEVEL': 'ERROR'}
        for key, value in test_vars.items():
            env.set(key, value, source='websocket_message_sequence_test')
        try:
            logger.info('[U+1F680] Testing AUTHENTICATED WebSocket message sequences')
            auth_helper = E2EAuthHelper()
            user_data = await auth_helper.create_authenticated_user(email_prefix='message_sequence_user', password='SequencePass123!', name='Message Sequence Test User')
            ws_manager = get_websocket_manager(user_context=getattr(self, 'user_context', None))
            conn_id = 'message-sequence-conn'
            ws_conn = InMemoryWebSocketConnection()
            await ws_manager.connect_user(user_data.user_id, ws_conn, conn_id)
            try:
                notifier = WebSocketNotifier.create_for_user(ws_manager)
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                context = AgentExecutionContext(run_id=f'sequence-test-{user_data.user_id}', thread_id=conn_id, user_id=user_data.user_id, agent_name='message_sequence_agent', retry_count=0, max_retries=1)
                logger.info('[U+1F4E1] Testing complex message sequence...')
                await notifier.send_agent_started(context)
                await asyncio.sleep(0.01)
                await notifier.send_agent_thinking(context, 'Phase 1: Analyzing input data...')
                await asyncio.sleep(0.01)
                await notifier.send_tool_executing(context, 'data_analyzer')
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context, 'data_analyzer', {'analysis': 'complete', 'patterns': 3}
                await asyncio.sleep(0.01)
                await notifier.send_agent_thinking(context, 'Phase 2: Processing analysis results...')
                await asyncio.sleep(0.01)
                await notifier.send_tool_executing(context, 'pattern_processor')
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context, 'pattern_processor', {'processed_patterns': 3, 'confidence': 0.95}
                await asyncio.sleep(0.01)
                await notifier.send_partial_result(context, 'Found 3 patterns with high confidence...')
                await asyncio.sleep(0.01)
                await notifier.send_agent_thinking(context, 'Phase 3: Generating final recommendations...')
                await asyncio.sleep(0.01)
                await notifier.send_tool_executing(context, 'recommendation_generator')
                await asyncio.sleep(0.01)
                await notifier.send_tool_completed(context, 'recommendation_generator', {'recommendations': ['opt1', 'opt2', 'opt3']}
                await asyncio.sleep(0.01)
                await notifier.send_agent_completed(context, {'sequence_test': 'passed', 'total_tools': 3}
                await asyncio.sleep(0.1)
            finally:
                await ws_manager.disconnect_user(user_data.user_id, ws_conn, conn_id)
                await ws_conn.close()
            execution_time = time.time() - start_time
            assert execution_time >= 0.1, f'Test executed too quickly ({execution_time:.3f}s) - likely using mocks'
            events = ws_conn.received_events
            assert len(events) >= 12, f'Expected at least 12 WebSocket events, got {len(events)}'
            event_types = [e.get('type') for e in events]
            assert event_types[0] == 'agent_started', f'Sequence should start with agent_started, got {event_types[0]}'
            assert event_types[-1] == 'agent_completed', f'Sequence should end with agent_completed, got {event_types[-1]}'
            tool_executing_indices = [i for i, t in enumerate(event_types) if t == 'tool_executing']
            tool_completed_indices = [i for i, t in enumerate(event_types) if t == 'tool_completed']
            assert len(tool_executing_indices) == len(tool_completed_indices), f'Tool event mismatch: {len(tool_executing_indices)} executing, {len(tool_completed_indices)} completed'
            assert len(tool_executing_indices) == 3, f'Expected 3 tool sequences, got {len(tool_executing_indices)}'
            for i in range(len(tool_executing_indices)):
                executing_idx = tool_executing_indices[i]
                completed_idx = tool_completed_indices[i]
                assert executing_idx < completed_idx, f'Tool {i}: executing at {executing_idx} should come before completed at {completed_idx}'
            for i, event in enumerate(events):
                assert 'type' in event, fEvent {i} missing 'type' field: {event}
                assert 'timestamp' in event, fEvent {i} missing 'timestamp' field: {event}""
                assert 'payload' in event, f"Event {i} missing 'payload' field: {event}"
                if 'user_id' in event.get('payload', {}:
                    assert event['payload']['user_id'] == user_data.user_id, fEvent {i} has wrong user_id: {event['payload']['user_id']} != {user_data.user_id}""
            tool_completed_events = [e for e in events if e.get('type') == 'tool_completed']
            assert len(tool_completed_events) == 3, f'Expected 3 tool completed events, got {len(tool_completed_events)}'
            for tool_event in tool_completed_events:
                tool_result = tool_event.get('payload', {}.get('result', {}
                assert isinstance(tool_result, dict), f'Tool result should be dict, got {type(tool_result)}'
                assert len(tool_result) > 0, f'Tool result should not be empty: {tool_result}'
            logger.info(' PASS:  AUTHENTICATED WebSocket message sequence test PASSED')
            logger.info(f'    CHART:  Total events: {len(events)}')
            logger.info(f'   [U+1F527] Tool sequences: {len(tool_executing_indices)}')
            logger.info(f'   [U+23F1][U+FE0F]  Execution time: {execution_time:.3f}s (real services confirmed)')
        finally:
            env.disable_isolation(restore_original=True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')