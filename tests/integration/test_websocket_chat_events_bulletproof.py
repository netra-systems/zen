"""MISSION CRITICAL INTEGRATION TEST: WebSocket Chat Event Flow

Business Value: $500K+ ARR - Real-time chat interaction and agent visibility
CHAT IS KING - THIS TEST MUST PASS.

Tests the complete WebSocket event flow for chat interactions:
1. All required agent events per spec
2. Event ordering and timing
3. Message correlation and deduplication
4. Error recovery and resilience
5. Performance under load

NO MOCKS - Uses real WebSocket connections and services.
"""
import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import threading
import pytest
from loguru import logger
import websockets
from websockets import WebSocketException
from shared.isolated_environment import IsolatedEnvironment
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine, enhance_tool_dispatcher_with_notifications

class WebSocketEventValidator:
    """Validates WebSocket events against specification requirements."""
    REQUIRED_EVENTS = {'agent_started': {'critical': True, 'description': 'User must know agent is processing'}, 'agent_thinking': {'critical': True, 'description': 'Real-time reasoning visibility'}, 'tool_executing': {'critical': True, 'description': 'Tool usage transparency'}, 'tool_completed': {'critical': True, 'description': 'Tool results display'}, 'agent_completed': {'critical': True, 'description': 'User must know when done'}, 'partial_result': {'critical': False, 'description': 'Streaming response UX'}, 'final_report': {'critical': False, 'description': 'Comprehensive summary'}}
    EVENT_SEQUENCES = [['agent_started', 'agent_thinking'], ['tool_executing', 'tool_completed'], ['agent_started', 'agent_completed']]
    MAX_EVENT_DELAYS = {'agent_started': 500, 'agent_thinking': 1000, 'tool_executing': 2000, 'agent_completed': 30000}

    def __init__(self):
        self.events: List[Dict] = []
        self.event_times: Dict[str, float] = {}
        self.validation_errors: List[str] = []

    def add_event(self, event: Dict) -> None:
        """Add an event for validation."""
        event_type = event.get('type')
        timestamp = time.time()
        self.events.append({'event': event, 'timestamp': timestamp, 'type': event_type})
        if event_type not in self.event_times:
            self.event_times[event_type] = []
        self.event_times[event_type].append(timestamp)
        logger.debug(f'Event received: {event_type} at {timestamp}')

    def validate_required_events(self) -> bool:
        """Validate all critical required events are present."""
        received_types = {e['type'] for e in self.events}
        for event_type, config in self.REQUIRED_EVENTS.items():
            if config['critical'] and event_type not in received_types:
                self.validation_errors.append(f"Missing critical event: {event_type} - {config['description']}")
        return len(self.validation_errors) == 0

    def validate_event_ordering(self) -> bool:
        """Validate events follow correct ordering."""
        event_sequence = [e['type'] for e in self.events]
        for required_seq in self.EVENT_SEQUENCES:
            seq_indices = []
            for event in required_seq:
                try:
                    idx = event_sequence.index(event)
                    seq_indices.append(idx)
                except ValueError:
                    continue
            if len(seq_indices) == len(required_seq):
                if seq_indices != sorted(seq_indices):
                    self.validation_errors.append(f'Invalid event ordering: {required_seq} not in correct order')
        return len(self.validation_errors) == 0

    def validate_event_timing(self, start_time: float) -> bool:
        """Validate events occur within timing constraints."""
        for event_type, max_delay in self.MAX_EVENT_DELAYS.items():
            if event_type in self.event_times:
                first_occurrence = min(self.event_times[event_type])
                delay = (first_occurrence - start_time) * 1000
                if delay > max_delay:
                    self.validation_errors.append(f'Event {event_type} delayed by {delay:.0f}ms (max: {max_delay}ms)')
        return len(self.validation_errors) == 0

    def validate_event_pairing(self) -> bool:
        """Validate paired events (e.g., tool_executing/tool_completed)."""
        event_counts = {}
        for event in self.events:
            event_type = event['type']
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        executing_count = event_counts.get('tool_executing', 0)
        completed_count = event_counts.get('tool_completed', 0)
        if executing_count != completed_count:
            self.validation_errors.append(f'Unpaired tool events: {executing_count} executing, {completed_count} completed')
        return len(self.validation_errors) == 0

    def get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report."""
        received_types = {e['type'] for e in self.events}
        critical_events = {k for k, v in self.REQUIRED_EVENTS.items() if v['critical']}
        return {'total_events': len(self.events), 'unique_event_types': len(received_types), 'received_types': list(received_types), 'critical_events_received': list(critical_events & received_types), 'critical_events_missing': list(critical_events - received_types), 'validation_errors': self.validation_errors, 'is_valid': len(self.validation_errors) == 0}

class WebSocketChatClient:
    """Simulates a frontend WebSocket client for chat interactions."""

    def __init__(self, client_id: str=None):
        self.client_id = client_id or f'test_client_{uuid.uuid4().hex[:8]}'
        self.websocket = None
        self.connected = False
        self.validator = WebSocketEventValidator()
        self.messages_sent = []
        self.messages_received = []
        self.errors = []

    async def connect(self, url: str, token: str) -> bool:
        """Connect to WebSocket server with authentication."""
        try:
            ws_url = f'{url}?jwt={token}'
            self.websocket = await websockets.connect(ws_url, subprotocols=[f'jwt.{token}'], ping_interval=10, ping_timeout=5)
            self.connected = True
            logger.info(f'Client {self.client_id} connected to WebSocket')
            asyncio.create_task(self._listen_for_messages())
            return True
        except Exception as e:
            logger.error(f'WebSocket connection failed: {e}')
            self.errors.append({'phase': 'connection', 'error': str(e)})
            return False

    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.messages_received.append(data)
                    self.validator.add_event(data)
                    event_type = data.get('type')
                    if event_type in WebSocketEventValidator.REQUIRED_EVENTS:
                        logger.info(f'Client {self.client_id} received: {event_type}')
                except json.JSONDecodeError:
                    logger.warning(f'Invalid JSON received: {message[:100]}')
        except websockets.exceptions.ConnectionClosed:
            logger.info(f'Client {self.client_id} connection closed')
            self.connected = False
        except Exception as e:
            logger.error(f'Error in message listener: {e}')
            self.errors.append({'phase': 'listening', 'error': str(e)})

    async def send_chat_message(self, content: str, thread_id: str=None) -> Dict[str, Any]:
        """Send a chat message and track response events."""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        message_id = f'msg_{uuid.uuid4().hex[:8]}'
        thread_id = thread_id or f'thread_{uuid.uuid4().hex[:8]}'
        message = {'type': 'user_message', 'payload': {'content': content, 'thread_id': thread_id, 'message_id': message_id, 'timestamp': datetime.utcnow().isoformat(), 'client_id': self.client_id}}
        try:
            start_time = time.time()
            await self.websocket.send(json.dumps(message))
            self.messages_sent.append(message)
            logger.info(f'Client {self.client_id} sent message: {message_id}')
            timeout = 30
            while time.time() - start_time < timeout:
                completed_events = [e for e in self.validator.events if e['type'] == 'agent_completed']
                if completed_events:
                    elapsed = time.time() - start_time
                    logger.info(f'Message processing completed in {elapsed:.2f}s')
                    self.validator.validate_required_events()
                    self.validator.validate_event_ordering()
                    self.validator.validate_event_timing(start_time)
                    self.validator.validate_event_pairing()
                    return {'success': True, 'message_id': message_id, 'processing_time': elapsed, 'validation_report': self.validator.get_validation_report()}
                await asyncio.sleep(0.1)
            return {'success': False, 'error': 'Timeout waiting for agent_completed', 'message_id': message_id, 'validation_report': self.validator.get_validation_report()}
        except Exception as e:
            logger.error(f'Error sending message: {e}')
            return {'success': False, 'error': str(e)}

    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info(f'Client {self.client_id} disconnected')

class WebSocketChatIntegrationTest:
    """Comprehensive WebSocket chat integration tests."""

    def __init__(self):
        self.ws_manager = WebSocketManager()
        self.agent_registry = AgentRegistry()
        self.clients: List[WebSocketChatClient] = []

    async def setup(self):
        """Set up test environment."""
        self.agent_registry.set_websocket_manager(self.ws_manager)
        if hasattr(self.agent_registry.tool_dispatcher, '_websocket_enhanced'):
            logger.info('Tool dispatcher properly enhanced with WebSocket notifications')
        else:
            logger.error('CRITICAL: Tool dispatcher not enhanced!')

    async def test_single_message_flow(self, token: str) -> Dict[str, Any]:
        """Test single message flow with all required events."""
        client = WebSocketChatClient()
        self.clients.append(client)
        ws_url = 'ws://localhost:8080/ws'
        connected = await client.connect(ws_url, token)
        if not connected:
            return {'success': False, 'error': 'Connection failed'}
        result = await client.send_chat_message('Test message for WebSocket event validation')
        await client.disconnect()
        return result

    async def test_concurrent_messages(self, token: str, num_messages: int=5) -> Dict[str, Any]:
        """Test multiple concurrent messages from single client."""
        client = WebSocketChatClient()
        self.clients.append(client)
        ws_url = 'ws://localhost:8080/ws'
        connected = await client.connect(ws_url, token)
        if not connected:
            return {'success': False, 'error': 'Connection failed'}
        tasks = []
        for i in range(num_messages):
            task = client.send_chat_message(f'Concurrent message {i}')
            tasks.append(task)
            await asyncio.sleep(0.1)
        results = await asyncio.gather(*tasks)
        successful = sum((1 for r in results if r.get('success')))
        await client.disconnect()
        return {'success': successful == num_messages, 'total': num_messages, 'successful': successful, 'results': results}

    async def test_message_deduplication(self, token: str) -> Dict[str, Any]:
        """Test that duplicate messages are properly handled."""
        client = WebSocketChatClient()
        self.clients.append(client)
        ws_url = 'ws://localhost:8080/ws'
        await client.connect(ws_url, token)
        message_id = f'dup_test_{uuid.uuid4().hex[:8]}'
        message = {'type': 'user_message', 'payload': {'content': 'Test deduplication', 'message_id': message_id, 'timestamp': datetime.utcnow().isoformat()}}
        await client.websocket.send(json.dumps(message))
        await asyncio.sleep(0.5)
        await client.websocket.send(json.dumps(message))
        await asyncio.sleep(3)
        agent_started_events = [e for e in client.validator.events if e['type'] == 'agent_started']
        await client.disconnect()
        return {'success': len(agent_started_events) == 1, 'agent_started_count': len(agent_started_events), 'total_events': len(client.validator.events)}

    async def test_websocket_reconnection(self, token: str) -> Dict[str, Any]:
        """Test WebSocket reconnection and message continuity."""
        client = WebSocketChatClient()
        self.clients.append(client)
        ws_url = 'ws://localhost:8080/ws'
        await client.connect(ws_url, token)
        result1 = await client.send_chat_message('Message before disconnect')
        await client.websocket.close()
        await asyncio.sleep(1)
        await client.connect(ws_url, token)
        result2 = await client.send_chat_message('Message after reconnect')
        await client.disconnect()
        return {'success': result1.get('success') and result2.get('success'), 'before_disconnect': result1, 'after_reconnect': result2}

    async def test_error_recovery(self, token: str) -> Dict[str, Any]:
        """Test error recovery and resilience."""
        client = WebSocketChatClient()
        self.clients.append(client)
        ws_url = 'ws://localhost:8080/ws'
        await client.connect(ws_url, token)
        try:
            await client.websocket.send('INVALID JSON {[}')
        except:
            pass
        await asyncio.sleep(0.5)
        result = await client.send_chat_message('Valid message after error')
        await client.disconnect()
        return {'success': result.get('success'), 'recovered': client.connected, 'result': result}

class WebSocketEventStressTest:
    """Stress test for high volume WebSocket events."""

    async def test_event_storm(self, token: str, num_clients: int=10, messages_per_client: int=5):
        """Test system under high event load."""
        clients = []
        for i in range(num_clients):
            client = WebSocketChatClient(f'stress_client_{i}')
            connected = await client.connect('ws://localhost:8080/ws', token)
            if connected:
                clients.append(client)
            await asyncio.sleep(0.05)
        logger.info(f'Connected {len(clients)} clients for stress test')
        all_tasks = []
        for client in clients:
            for j in range(messages_per_client):
                task = client.send_chat_message(f'Stress test message {j}')
                all_tasks.append(task)
                await asyncio.sleep(0.01)
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        for client in clients:
            await client.disconnect()
        successful = sum((1 for r in results if isinstance(r, dict) and r.get('success')))
        failed = len(results) - successful
        validation_errors = []
        for r in results:
            if isinstance(r, dict) and 'validation_report' in r:
                report = r['validation_report']
                if not report['is_valid']:
                    validation_errors.extend(report['validation_errors'])
        return {'total_messages': len(results), 'successful': successful, 'failed': failed, 'success_rate': successful / len(results) * 100 if results else 0, 'validation_errors': validation_errors[:10]}

@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_chat_events_complete_flow():
    """Test complete WebSocket chat event flow."""
    test = WebSocketChatIntegrationTest()
    await test.setup()
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(user_id='test_user', email='test@netra.ai')
    result = await test.test_single_message_flow(token)
    assert result['success'], f"Chat flow failed: {result.get('error')}"
    report = result['validation_report']
    assert report['is_valid'], f"Validation errors: {report['validation_errors']}"
    assert len(report['critical_events_missing']) == 0, f"Missing critical events: {report['critical_events_missing']}"

@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_concurrent_messages():
    """Test concurrent message handling."""
    test = WebSocketChatIntegrationTest()
    await test.setup()
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(user_id='test_user', email='test@netra.ai')
    result = await test.test_concurrent_messages(token, num_messages=5)
    assert result['success'], f"Concurrent messages failed: {result['successful']}/{result['total']}"

@pytest.mark.asyncio
@pytest.mark.mission_critical
async def test_websocket_deduplication():
    """Test message deduplication."""
    test = WebSocketChatIntegrationTest()
    await test.setup()
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(user_id='test_user', email='test@netra.ai')
    result = await test.test_message_deduplication(token)
    assert result['success'], f"Deduplication failed: {result['agent_started_count']} agent_started events"

@pytest.mark.asyncio
@pytest.mark.stress
async def test_websocket_event_storm():
    """Stress test with high volume of events."""
    stress_test = WebSocketEventStressTest()
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper()
    token = auth_helper.create_test_jwt_token(user_id='test_user', email='test@netra.ai')
    result = await stress_test.test_event_storm(token, num_clients=5, messages_per_client=3)
    logger.info(f'Stress test results: {json.dumps(result, indent=2)}')
    assert result['success_rate'] >= 80, f"Too many failures: {result['failed']}/{result['total_messages']}"
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')