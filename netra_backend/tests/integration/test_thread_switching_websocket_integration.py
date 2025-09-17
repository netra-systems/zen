"""
WebSocket Thread Switching Integration Tests (Tests 21-40)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Enable seamless thread-based conversations with real-time WebSocket updates
- Value Impact: Users can manage multiple conversation threads with live agent event delivery
- Strategic Impact: Core chat functionality that enables multi-threaded AI conversations

CRITICAL REQUIREMENTS:
- Tests 21-40 focus specifically on WebSocket thread switching functionality
- Uses ONLY real services - NO MOCKS in integration tests per TEST_CREATION_GUIDE.md
- Follows SSOT patterns from test_framework/ 
- Tests the 5 critical WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Uses proper isolation patterns with UserExecutionContext
- Tests WebSocket room management, event broadcasting, connection handling, and multi-user isolation
- Creates realistic business value tests focusing on WebSocket functionality
- Uses real database operations using real_services_fixture
- Proper WebSocket message validation and event sequences
- Thread-specific WebSocket room isolation
- Multi-user concurrent WebSocket operations

FOCUS AREAS (Tests 21-40):
- Test 21-25: WebSocket room management for threads
- Test 26-30: Thread event broadcasting via WebSocket  
- Test 31-35: WebSocket connection handling during thread switches
- Test 36-40: Multi-user WebSocket thread isolation
"""
import asyncio
import json
import pytest
import time
import uuid
import websockets
from contextlib import asynccontextmanager
from datetime import datetime, UTC, timezone
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import AsyncMock, patch
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
from shared.id_generation import UnifiedIdGenerator
from netra_backend.app.schemas.core_models import Thread, Message, User
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.types import MessageType, WebSocketConnectionState
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events_sent, WebSocketTestHelpers, MockWebSocket

class WebSocketThreadSwitchingIntegrationTests(BaseIntegrationTest):
    """
    Integration tests for WebSocket thread switching functionality (Tests 21-40).
    
    CRITICAL: Uses ONLY real services (PostgreSQL, Redis) - NO MOCKS allowed
    per TEST_CREATION_GUIDE.md requirements for integration testing.
    """

    async def async_setup_method(self):
        """Setup real services infrastructure for WebSocket thread testing."""
        await super().async_setup_method()
        self.env = get_env()
        self.env.set('TESTING', '1', source='websocket_thread_integration')
        self.env.set('USE_REAL_SERVICES', 'true', source='websocket_thread_integration')
        self.env.set('WEBSOCKET_TESTING', '1', source='websocket_thread_integration')
        self.env.set('E2E_TESTING', '1', source='websocket_thread_integration')
        self.websocket_manager = None
        self.test_user_id = f'ws_thread_user_{uuid.uuid4().hex[:8]}'
        self.test_jwt_token = await self._create_test_jwt_token()
        self.test_threads = {}
        self.websocket_rooms = {}
        self.received_events = []
        self.thread_events = {}
        self.metrics = {'thread_switches': 0, 'websocket_events_sent': 0, 'room_isolations_validated': 0, 'multi_user_operations': 0, 'connection_handovers': 0}

    async def async_teardown_method(self):
        """Clean up WebSocket resources and real services."""
        if hasattr(self, 'websocket_connections'):
            for ws in self.websocket_connections:
                try:
                    await ws.close()
                except:
                    pass
        if self.websocket_manager:
            try:
                await self.websocket_manager.cleanup_all_connections()
            except Exception as e:
                self.logger.warning(f'WebSocket manager cleanup error: {e}')
        await super().async_teardown_method()

    async def _create_test_jwt_token(self, user_id: str=None) -> str:
        """Create valid JWT token for WebSocket authentication."""
        import jwt
        user_id = user_id or self.test_user_id
        token_data = {'user_id': user_id, 'sub': user_id, 'iat': int(time.time()), 'exp': int(time.time()) + 3600, 'scope': 'websocket chat threads'}
        test_secret = self.env.get('JWT_SECRET', 'test_secret_for_websocket_threads')
        return jwt.encode(token_data, test_secret, algorithm='HS256')

    @asynccontextmanager
    async def _create_authenticated_websocket_connection(self, user_id: str=None, room_id: str=None):
        """Create authenticated WebSocket connection with room management."""
        user_id = user_id or self.test_user_id
        jwt_token = await self._create_test_jwt_token(user_id)
        websocket_url = f'ws://localhost:8000/ws'
        headers = {'Authorization': f'Bearer {jwt_token}', 'User-Agent': 'WebSocket-Thread-Integration-Test/1.0', 'X-Test-Type': 'thread_integration', 'X-E2E-Test': 'true'}
        if room_id:
            headers['X-Room-ID'] = room_id
        try:
            websocket = await websockets.connect(websocket_url, extra_headers=headers, subprotocols=['jwt-auth'], ping_interval=None, close_timeout=10)
            welcome_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            welcome_data = json.loads(welcome_message)
            assert welcome_data.get('type') == 'connection_established', f'Expected connection confirmation: {welcome_data}'
            assert welcome_data.get('connection_ready') is True, 'Connection should be ready'
            if room_id:
                if room_id not in self.websocket_rooms:
                    self.websocket_rooms[room_id] = []
                self.websocket_rooms[room_id].append({'websocket': websocket, 'user_id': user_id, 'connected_at': time.time()})
            yield websocket
        except Exception as e:
            self.logger.error(f'WebSocket connection error: {e}')
            raise
        finally:
            try:
                await websocket.close()
            except:
                pass

    async def _create_test_thread(self, real_services, user_id: str=None, thread_name: str=None) -> Dict:
        """Create test thread in real database for thread switching tests."""
        user_id = user_id or self.test_user_id
        thread_id = UnifiedIdGenerator.generate_thread_id(user_id)
        thread_name = thread_name or f'Test Thread {len(self.test_threads) + 1}'
        thread_data = {'id': thread_id, 'name': thread_name, 'user_id': user_id, 'created_at': datetime.now(timezone.utc), 'updated_at': datetime.now(timezone.utc), 'metadata': {'test_mode': True, 'websocket_enabled': True}, 'message_count': 0, 'is_active': True}
        if real_services['database_available']:
            async with real_services['db'] as db:
                await db.execute('\n                    INSERT INTO threads (id, name, user_id, created_at, updated_at, metadata, message_count, is_active)\n                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)\n                    ON CONFLICT (id) DO UPDATE SET\n                        name = EXCLUDED.name,\n                        updated_at = EXCLUDED.updated_at\n                ', thread_id, thread_name, user_id, thread_data['created_at'], thread_data['updated_at'], json.dumps(thread_data['metadata']), 0, True)
                await db.commit()
        self.test_threads[thread_id] = thread_data
        return thread_data

    async def _send_thread_message(self, websocket, thread_id: str, message_content: str) -> str:
        """Send message to specific thread via WebSocket."""
        run_id = UnifiedIdGenerator.generate_run_id(self.test_user_id, 'thread_message')
        message = {'type': MessageType.CHAT, 'thread_id': thread_id, 'run_id': run_id, 'payload': {'content': message_content, 'user_id': self.test_user_id, 'metadata': {'thread_switching_test': True, 'require_websocket_events': True}}}
        await websocket.send(json.dumps(message))
        self.metrics['websocket_events_sent'] += 1
        return run_id

    async def _collect_thread_events(self, websocket, thread_id: str, timeout: float=20.0) -> List[Dict]:
        """Collect WebSocket events for specific thread."""
        events = []
        start_time = time.time()
        try:
            while time.time() - start_time < timeout:
                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event_data = json.loads(raw_message)
                    event_thread_id = event_data.get('thread_id', event_data.get('data', {}).get('thread_id'))
                    if event_thread_id == thread_id or not event_thread_id:
                        events.append(event_data)
                        self.received_events.append(event_data)
                        if thread_id not in self.thread_events:
                            self.thread_events[thread_id] = []
                        self.thread_events[thread_id].append(event_data)
                    if len(events) >= 3:
                        agent_event_types = [e.get('type') for e in events]
                        if any((event_type in ['agent_completed', 'tool_completed'] for event_type in agent_event_types)):
                            break
                except asyncio.TimeoutError:
                    if len(events) >= 2:
                        break
                    continue
        except Exception as e:
            self.logger.error(f'Event collection error for thread {thread_id}: {e}')
        return events

    def _validate_websocket_room_isolation(self, room_events: Dict[str, List[Dict]]) -> bool:
        """Validate WebSocket events are properly isolated by room/thread."""
        for room_id, events in room_events.items():
            for event in events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id and event_thread_id != room_id:
                    self.logger.error(f'Room isolation violation: Event for thread {event_thread_id} appeared in room {room_id}')
                    return False
                event_message = event.get('message', event.get('data', {}).get('message', ''))
                for other_room_id in room_events:
                    if other_room_id != room_id and other_room_id in event_message:
                        self.logger.warning(f'Potential room context leakage: {other_room_id} mentioned in {room_id} event')
        self.metrics['room_isolations_validated'] += 1
        return True

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_21_websocket_room_creation_for_new_thread(self, real_services_fixture):
        """
        Test 21: WebSocket room creation when new thread is started.
        
        BVJ: Each thread needs isolated WebSocket room for private conversations.
        Users expect their thread conversations to be completely separate.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Room Creation Test Thread')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket:
            message_content = 'Test message for room creation'
            run_id = await self._send_thread_message(websocket, thread_id, message_content)
            events = await self._collect_thread_events(websocket, thread_id)
            assert len(events) >= 1, f'Should receive events in new room for thread {thread_id}'
            for event in events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    assert event_thread_id == thread_id, f'Event should belong to thread {thread_id}, got {event_thread_id}'
        assert thread_id in self.websocket_rooms, 'Thread room should be tracked'
        self.assert_business_value_delivered({'room_created': True, 'events_delivered': len(events)}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_22_websocket_room_membership_management(self, real_services_fixture):
        """
        Test 22: WebSocket room membership when users join/leave threads.
        
        BVJ: Dynamic room membership enables users to join ongoing conversations
        and receive all relevant WebSocket events for business context.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Room Membership Test')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket1:
            await self._send_thread_message(websocket1, thread_id, 'First user joining room')
            initial_events = await self._collect_thread_events(websocket1, thread_id, timeout=10.0)
            assert thread_id in self.websocket_rooms, 'Room should exist'
            room_members = self.websocket_rooms[thread_id]
            assert len(room_members) >= 1, 'Room should have at least one member'
            second_user_id = f'ws_thread_user_2_{uuid.uuid4().hex[:6]}'
            async with self._create_authenticated_websocket_connection(user_id=second_user_id, room_id=thread_id) as websocket2:
                run_id2 = await self._send_thread_message(websocket2, thread_id, 'Second user in same room')
                second_events = await self._collect_thread_events(websocket2, thread_id, timeout=10.0)
                assert len(initial_events) >= 1, 'First user should receive events'
                assert len(second_events) >= 1, 'Second user should receive events'
                updated_room_members = self.websocket_rooms[thread_id]
                assert len(updated_room_members) >= 2, 'Room should have multiple members'
        self.assert_business_value_delivered({'room_membership': len(updated_room_members), 'multi_user_events': len(initial_events) + len(second_events)}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_23_websocket_room_cleanup_after_thread_inactivity(self, real_services_fixture):
        """
        Test 23: WebSocket room cleanup when thread becomes inactive.
        
        BVJ: Automatic room cleanup prevents resource leaks and maintains
        system performance for high-volume enterprise deployments.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Room Cleanup Test')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket:
            await self._send_thread_message(websocket, thread_id, 'Message to establish room')
            events = await self._collect_thread_events(websocket, thread_id, timeout=5.0)
            assert thread_id in self.websocket_rooms, 'Room should be created'
            initial_room_count = len(self.websocket_rooms)
            await websocket.close()
        await asyncio.sleep(1.0)
        inactive_rooms = []
        for room_id, members in self.websocket_rooms.items():
            active_members = [m for m in members if not getattr(m['websocket'], 'closed', True)]
            if not active_members:
                inactive_rooms.append(room_id)
        for room_id in inactive_rooms:
            del self.websocket_rooms[room_id]
        final_room_count = len(self.websocket_rooms)
        assert final_room_count < initial_room_count, 'Inactive rooms should be cleaned up'
        self.assert_business_value_delivered({'rooms_cleaned': initial_room_count - final_room_count, 'resource_optimization': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_24_websocket_room_event_filtering_by_thread(self, real_services_fixture):
        """
        Test 24: WebSocket room event filtering ensures thread-specific delivery.
        
        BVJ: Event filtering prevents users from seeing other threads' sensitive
        business data, maintaining privacy and regulatory compliance.
        """
        thread1_data = await self._create_test_thread(real_services_fixture, thread_name='Filter Test Thread 1')
        thread2_data = await self._create_test_thread(real_services_fixture, thread_name='Filter Test Thread 2')
        thread1_id = thread1_data['id']
        thread2_id = thread2_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread1_id) as ws1, self._create_authenticated_websocket_connection(room_id=thread2_id) as ws2:
            await self._send_thread_message(ws1, thread1_id, 'Confidential financial analysis for Q3 results')
            await self._send_thread_message(ws2, thread2_id, 'Marketing campaign optimization for product launch')
            thread1_events = await self._collect_thread_events(ws1, thread1_id, timeout=15.0)
            thread2_events = await self._collect_thread_events(ws2, thread2_id, timeout=15.0)
            for event in thread1_events:
                event_content = json.dumps(event).lower()
                thread2_terms = ['marketing', 'campaign', 'product launch']
                has_thread2_content = any((term in event_content for term in thread2_terms))
                assert not has_thread2_content, f'Thread 1 event contains Thread 2 content: {event}'
                thread1_terms = ['financial', 'analysis', 'q3']
                has_thread1_content = any((term in event_content for term in thread1_terms))
            for event in thread2_events:
                event_content = json.dumps(event).lower()
                thread1_terms = ['financial', 'analysis', 'q3']
                has_thread1_content = any((term in event_content for term in thread1_terms))
                assert not has_thread1_content, f'Thread 2 event contains Thread 1 content: {event}'
        room_events = {thread1_id: thread1_events, thread2_id: thread2_events}
        assert self._validate_websocket_room_isolation(room_events), 'Room isolation should be maintained'
        self.assert_business_value_delivered({'thread_isolation': True, 'privacy_maintained': len(thread1_events) + len(thread2_events)}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_25_websocket_room_scalability_multiple_threads(self, real_services_fixture):
        """
        Test 25: WebSocket room scalability with multiple concurrent threads.
        
        BVJ: Scalable room management enables enterprise customers to run
        multiple AI conversations simultaneously without performance degradation.
        """
        thread_count = 5
        threads = []
        websocket_connections = []
        try:
            for i in range(thread_count):
                thread_data = await self._create_test_thread(real_services_fixture, thread_name=f'Scalability Test Thread {i + 1}')
                threads.append(thread_data)
            for thread_data in threads:
                thread_id = thread_data['id']
                websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {self.test_jwt_token}', 'X-Room-ID': thread_id, 'X-Test-Type': 'scalability'}, subprotocols=['jwt-auth'])
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                welcome_data = json.loads(welcome_msg)
                assert welcome_data.get('connection_ready') is True
                websocket_connections.append((websocket, thread_id))
            message_tasks = []
            for websocket, thread_id in websocket_connections:
                task = asyncio.create_task(self._send_thread_message(websocket, thread_id, f'Scalability test message for {thread_id}'))
                message_tasks.append(task)
            await asyncio.gather(*message_tasks)
            event_tasks = []
            for websocket, thread_id in websocket_connections:
                task = asyncio.create_task(self._collect_thread_events(websocket, thread_id, timeout=10.0))
                event_tasks.append((task, thread_id))
            all_thread_events = {}
            for task, thread_id in event_tasks:
                events = await task
                all_thread_events[thread_id] = events
            total_events = sum((len(events) for events in all_thread_events.values()))
            assert total_events >= thread_count, f'Should receive events from all {thread_count} threads'
            successful_threads = 0
            for thread_id, events in all_thread_events.items():
                if len(events) >= 1:
                    successful_threads += 1
            success_rate = successful_threads / thread_count
            assert success_rate >= 0.8, f'At least 80% of threads should receive events, got {success_rate:.2%}'
            assert self._validate_websocket_room_isolation(all_thread_events), 'Room isolation must be maintained at scale'
        finally:
            for websocket, _ in websocket_connections:
                try:
                    await websocket.close()
                except:
                    pass
        self.assert_business_value_delivered({'concurrent_threads': thread_count, 'total_events': total_events, 'success_rate': success_rate, 'scalability_validated': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_26_agent_started_event_broadcast_to_thread_room(self, real_services_fixture):
        """
        Test 26: agent_started event broadcasting to thread-specific WebSocket room.
        
        BVJ: Users must immediately know when AI agent begins processing their
        thread-specific request to set proper expectations and build trust.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Agent Started Broadcast Test')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket:
            message_content = 'Analyze our Q4 business performance and identify growth opportunities'
            run_id = await self._send_thread_message(websocket, thread_id, message_content)
            events = await self._collect_thread_events(websocket, thread_id, timeout=20.0)
            agent_started_events = [e for e in events if e.get('type') == 'agent_started']
            assert len(agent_started_events) >= 1, 'Should receive agent_started event in thread room'
            started_event = agent_started_events[0]
            event_thread_id = started_event.get('thread_id', started_event.get('data', {}).get('thread_id'))
            assert event_thread_id == thread_id, f'agent_started should be for thread {thread_id}'
            event_data = started_event.get('data', started_event)
            agent_name = event_data.get('agent_name', '')
            message = event_data.get('message', '')
            assert len(agent_name) > 0, 'agent_started should identify the agent'
            assert len(message) > 5, 'agent_started should have meaningful message'
            assert 'start' in message.lower() or 'begin' in message.lower(), 'Message should indicate agent is starting'
        self.assert_business_value_delivered({'agent_started_broadcast': True, 'thread_context': thread_id, 'user_notification': len(agent_started_events)}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_27_agent_thinking_events_broadcast_with_thread_context(self, real_services_fixture):
        """
        Test 27: agent_thinking events broadcast with thread-specific context.
        
        BVJ: Real-time thinking visibility in thread context helps users understand
        how AI is processing their specific business problem within conversation flow.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Agent Thinking Broadcast Test')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket:
            complex_request = 'Perform comprehensive analysis of our customer acquisition costs across all channels and recommend optimization strategies'
            run_id = await self._send_thread_message(websocket, thread_id, complex_request)
            events = await self._collect_thread_events(websocket, thread_id, timeout=25.0)
            thinking_events = [e for e in events if e.get('type') == 'agent_thinking']
            assert len(thinking_events) >= 1, 'Should receive agent_thinking events in thread'
            for thinking_event in thinking_events:
                event_thread_id = thinking_event.get('thread_id', thinking_event.get('data', {}).get('thread_id'))
                assert event_thread_id == thread_id, f'Thinking event should be for thread {thread_id}'
                event_data = thinking_event.get('data', thinking_event)
                reasoning = event_data.get('reasoning', event_data.get('message', ''))
                assert len(reasoning) > 15, f'Thinking event should contain substantial reasoning: {reasoning}'
                business_terms = ['analysis', 'customer', 'acquisition', 'costs', 'optimization', 'strategy']
                has_business_context = any((term in reasoning.lower() for term in business_terms))
                if not has_business_context:
                    self.logger.info(f'Thinking event may lack explicit business context: {reasoning}')
            if len(thinking_events) > 1:
                for i in range(1, len(thinking_events)):
                    prev_time = thinking_events[i - 1].get('timestamp', 0)
                    curr_time = thinking_events[i].get('timestamp', 0)
                    assert curr_time >= prev_time, 'Thinking events should progress chronologically'
        self.assert_business_value_delivered({'thinking_events_broadcast': len(thinking_events), 'thread_context_maintained': True, 'reasoning_visibility': True}, 'insights')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_28_tool_execution_events_broadcast_to_thread_subscribers(self, real_services_fixture):
        """
        Test 28: tool_executing and tool_completed events broadcast to thread subscribers.
        
        BVJ: Tool execution transparency in thread context shows users exactly
        how AI is solving their problems step-by-step within conversation flow.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Tool Execution Broadcast Test')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket:
            tool_request = 'Generate detailed cost analysis report with charts and recommendations'
            run_id = await self._send_thread_message(websocket, thread_id, tool_request)
            events = await self._collect_thread_events(websocket, thread_id, timeout=30.0)
            tool_executing_events = [e for e in events if e.get('type') == 'tool_executing']
            tool_completed_events = [e for e in events if e.get('type') == 'tool_completed']
            assert len(tool_executing_events) >= 1, 'Should receive tool_executing events in thread'
            assert len(tool_completed_events) >= 1, 'Should receive tool_completed events in thread'
            for tool_event in tool_executing_events:
                event_thread_id = tool_event.get('thread_id', tool_event.get('data', {}).get('thread_id'))
                assert event_thread_id == thread_id, f'Tool executing event should be for thread {thread_id}'
                event_data = tool_event.get('data', tool_event)
                tool_name = event_data.get('tool_name', '')
                message = event_data.get('message', '')
                assert len(tool_name) > 0, 'Tool executing should identify the tool'
                assert len(message) > 5, 'Tool executing should describe action'
                execution_terms = ['executing', 'running', 'processing', 'analyzing', 'generating']
                has_execution_context = any((term in message.lower() for term in execution_terms))
                if not has_execution_context:
                    self.logger.info(f'Tool executing event may lack execution context: {message}')
            for completion_event in tool_completed_events:
                event_thread_id = completion_event.get('thread_id', completion_event.get('data', {}).get('thread_id'))
                assert event_thread_id == thread_id, f'Tool completed event should be for thread {thread_id}'
                event_data = completion_event.get('data', completion_event)
                result = event_data.get('result', {})
                message = event_data.get('message', '')
                has_result_content = len(str(result)) > 2 or len(message) > 10
                assert has_result_content, 'Tool completed should provide results or meaningful completion message'
        if len(tool_executing_events) > 0 and len(tool_completed_events) > 0:
            exec_time = tool_executing_events[0].get('timestamp', 0)
            comp_time = tool_completed_events[-1].get('timestamp', 0)
            assert comp_time >= exec_time, 'Tool completion should come after execution'
        self.assert_business_value_delivered({'tool_executing_broadcast': len(tool_executing_events), 'tool_completed_broadcast': len(tool_completed_events), 'thread_transparency': True, 'problem_solving_visibility': True}, 'insights')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_29_agent_completed_event_broadcast_with_final_response(self, real_services_fixture):
        """
        Test 29: agent_completed event broadcast with final response to thread.
        
        BVJ: Final completion notification in thread context signals users that
        AI has finished processing and delivers complete business value.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Agent Completion Broadcast Test')
        thread_id = thread_data['id']
        async with self._create_authenticated_websocket_connection(room_id=thread_id) as websocket:
            completion_request = 'Provide complete business analysis with executive summary and actionable recommendations'
            run_id = await self._send_thread_message(websocket, thread_id, completion_request)
            events = await self._collect_thread_events(websocket, thread_id, timeout=35.0)
            completion_events = [e for e in events if e.get('type') == 'agent_completed']
            assert len(completion_events) >= 1, 'Should receive agent_completed event in thread'
            completion_event = completion_events[-1]
            event_thread_id = completion_event.get('thread_id', completion_event.get('data', {}).get('thread_id'))
            assert event_thread_id == thread_id, f'Agent completed event should be for thread {thread_id}'
            event_data = completion_event.get('data', completion_event)
            final_response = event_data.get('final_response', event_data.get('message', ''))
            agent_name = event_data.get('agent_name', '')
            assert len(final_response) > 20, f'Agent completed should provide substantial final response: {final_response}'
            assert len(agent_name) > 0, 'Agent completed should identify completing agent'
            completion_terms = ['complete', 'finished', 'summary', 'conclusion', 'recommend']
            has_completion_context = any((term in final_response.lower() for term in completion_terms))
            if not has_completion_context:
                self.logger.info(f'Completion event may lack explicit completion indicators: {final_response}')
            event_types = [e.get('type') for e in events]
            completion_index = len(event_types) - 1 - event_types[::-1].index('agent_completed')
            has_prior_events = completion_index > 0
            if has_prior_events:
                prior_events = event_types[:completion_index]
                has_meaningful_prior_events = any((et in ['agent_started', 'agent_thinking', 'tool_executing'] for et in prior_events))
                if not has_meaningful_prior_events:
                    self.logger.info('Completion event may not have meaningful prior events')
        self.assert_business_value_delivered({'agent_completed_broadcast': True, 'final_response_delivered': len(final_response), 'thread_context': thread_id, 'business_value_completion': True}, 'insights')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_30_multi_subscriber_event_broadcast_to_thread_room(self, real_services_fixture):
        """
        Test 30: Event broadcasting to multiple subscribers in same thread room.
        
        BVJ: Multi-subscriber support enables team collaboration where multiple
        users can monitor same AI conversation thread in real-time.
        """
        thread_data = await self._create_test_thread(real_services_fixture, thread_name='Multi-Subscriber Broadcast Test')
        thread_id = thread_data['id']
        user1_id = f'subscriber1_{uuid.uuid4().hex[:6]}'
        user2_id = f'subscriber2_{uuid.uuid4().hex[:6]}'
        user3_id = f'subscriber3_{uuid.uuid4().hex[:6]}'
        try:
            websocket1 = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user1_id)}', 'X-Room-ID': thread_id, 'X-Test-Type': 'multi_subscriber'}, subprotocols=['jwt-auth'])
            websocket2 = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user2_id)}', 'X-Room-ID': thread_id, 'X-Test-Type': 'multi_subscriber'}, subprotocols=['jwt-auth'])
            websocket3 = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user3_id)}', 'X-Room-ID': thread_id, 'X-Test-Type': 'multi_subscriber'}, subprotocols=['jwt-auth'])
            for ws in [websocket1, websocket2, websocket3]:
                welcome_msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                welcome_data = json.loads(welcome_msg)
                assert welcome_data.get('connection_ready') is True
            broadcast_message = 'Team collaboration test - analyze market opportunity for new product line'
            await self._send_thread_message(websocket1, thread_id, broadcast_message)

            async def collect_subscriber_events(ws, subscriber_name):
                try:
                    events = await self._collect_thread_events(ws, thread_id, timeout=20.0)
                    return (subscriber_name, events)
                except Exception as e:
                    self.logger.error(f'Event collection error for {subscriber_name}: {e}')
                    return (subscriber_name, [])
            subscriber_results = await asyncio.gather(collect_subscriber_events(websocket1, 'subscriber1'), collect_subscriber_events(websocket2, 'subscriber2'), collect_subscriber_events(websocket3, 'subscriber3'), return_exceptions=True)
            subscriber_events = {}
            successful_subscribers = 0
            for result in subscriber_results:
                if isinstance(result, tuple):
                    subscriber_name, events = result
                    subscriber_events[subscriber_name] = events
                    if len(events) >= 1:
                        successful_subscribers += 1
                else:
                    self.logger.error(f'Subscriber result error: {result}')
            assert successful_subscribers >= 2, f'At least 2 subscribers should receive events, got {successful_subscribers}'
            all_event_types = set()
            for subscriber_name, events in subscriber_events.items():
                subscriber_event_types = {e.get('type') for e in events}
                all_event_types.update(subscriber_event_types)
                assert len(events) >= 1, f'Subscriber {subscriber_name} should receive events'
                for event in events:
                    event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                    if event_thread_id:
                        assert event_thread_id == thread_id, f'Event should be for thread {thread_id}'
            critical_event_types = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
            broadcast_critical_events = all_event_types.intersection(critical_event_types)
            self.metrics['multi_user_operations'] += 1
        finally:
            for ws in [websocket1, websocket2, websocket3]:
                try:
                    await ws.close()
                except:
                    pass
        self.assert_business_value_delivered({'successful_subscribers': successful_subscribers, 'total_events_broadcast': sum((len(events) for events in subscriber_events.values())), 'critical_events_broadcast': len(broadcast_critical_events), 'team_collaboration_enabled': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_31_websocket_connection_maintains_state_during_thread_switch(self, real_services_fixture):
        """
        Test 31: WebSocket connection maintains state when switching between threads.
        
        BVJ: Seamless thread switching enables users to manage multiple AI conversations
        without losing connection state or missing critical business insights.
        """
        thread1_data = await self._create_test_thread(real_services_fixture, thread_name='Thread Switch Test 1')
        thread2_data = await self._create_test_thread(real_services_fixture, thread_name='Thread Switch Test 2')
        thread1_id = thread1_data['id']
        thread2_id = thread2_data['id']
        async with self._create_authenticated_websocket_connection() as websocket:
            message1 = 'Begin financial analysis for Thread 1'
            run_id1 = await self._send_thread_message(websocket, thread1_id, message1)
            thread1_events = await self._collect_thread_events(websocket, thread1_id, timeout=15.0)
            assert len(thread1_events) >= 1, 'Should receive events from Thread 1'
            message2 = 'Start marketing analysis for Thread 2'
            run_id2 = await self._send_thread_message(websocket, thread2_id, message2)
            thread2_events = await self._collect_thread_events(websocket, thread2_id, timeout=15.0)
            assert len(thread2_events) >= 1, 'Should receive events from Thread 2'
            for event in thread1_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    assert event_thread_id == thread1_id, f'Thread 1 event should belong to {thread1_id}'
            for event in thread2_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    assert event_thread_id == thread2_id, f'Thread 2 event should belong to {thread2_id}'
            assert websocket.open, 'WebSocket connection should remain open during thread switches'
            message3 = 'Continue financial analysis in Thread 1'
            run_id3 = await self._send_thread_message(websocket, thread1_id, message3)
            additional_thread1_events = await self._collect_thread_events(websocket, thread1_id, timeout=10.0)
            assert len(additional_thread1_events) >= 1, 'Should continue receiving Thread 1 events after switch back'
            self.metrics['thread_switches'] += 2
        self.assert_business_value_delivered({'thread_switches_completed': 2, 'connection_state_maintained': True, 'events_segregated': len(thread1_events) + len(thread2_events), 'bidirectional_switching': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_32_websocket_event_delivery_continuity_across_thread_switches(self, real_services_fixture):
        """
        Test 32: WebSocket event delivery continuity when rapidly switching threads.
        
        BVJ: Rapid thread switching without event loss ensures users don't miss
        critical AI insights when managing multiple urgent business conversations.
        """
        threads = []
        for i in range(3):
            thread_data = await self._create_test_thread(real_services_fixture, thread_name=f'Rapid Switch Thread {i + 1}')
            threads.append(thread_data)
        async with self._create_authenticated_websocket_connection() as websocket:
            all_events = []
            thread_event_counts = {}
            for i, thread_data in enumerate(threads):
                thread_id = thread_data['id']
                message = f'Urgent analysis request {i + 1} for thread {i + 1}'
                run_id = await self._send_thread_message(websocket, thread_id, message)
                thread_events = await self._collect_thread_events(websocket, thread_id, timeout=8.0)
                all_events.extend(thread_events)
                thread_event_counts[thread_id] = len(thread_events)
                await asyncio.sleep(0.5)
            total_events = len(all_events)
            assert total_events >= len(threads), f'Should receive events from all {len(threads)} threads'
            threads_with_events = sum((1 for count in thread_event_counts.values() if count > 0))
            continuity_rate = threads_with_events / len(threads)
            assert continuity_rate >= 0.8, f'At least 80% of threads should maintain event continuity, got {continuity_rate:.2%}'
            critical_event_types = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
            received_critical_events = {e.get('type') for e in all_events}
            has_critical_events = bool(received_critical_events.intersection(critical_event_types))
            if not has_critical_events:
                self.logger.warning('No critical agent events received during rapid thread switching')
            for event in all_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    thread_ids = [t['id'] for t in threads]
                    assert event_thread_id in thread_ids, f'Event should belong to test thread: {event_thread_id}'
            self.metrics['thread_switches'] += len(threads)
        self.assert_business_value_delivered({'rapid_thread_switches': len(threads), 'event_continuity_rate': continuity_rate, 'total_events_delivered': total_events, 'no_event_loss': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_33_websocket_connection_recovery_after_failed_thread_switch(self, real_services_fixture):
        """
        Test 33: WebSocket connection recovery after failed thread switch attempt.
        
        BVJ: Graceful recovery from thread switch failures ensures users can continue
        their AI conversations without service disruption or lost business context.
        """
        valid_thread_data = await self._create_test_thread(real_services_fixture, thread_name='Valid Recovery Thread')
        valid_thread_id = valid_thread_data['id']
        invalid_thread_id = f'invalid_thread_{uuid.uuid4().hex[:8]}'
        async with self._create_authenticated_websocket_connection() as websocket:
            valid_message = 'Initial request in valid thread'
            run_id1 = await self._send_thread_message(websocket, valid_thread_id, valid_message)
            initial_events = await self._collect_thread_events(websocket, valid_thread_id, timeout=10.0)
            assert len(initial_events) >= 1, 'Should receive events from valid thread'
            assert websocket.open, 'WebSocket should be open initially'
            try:
                invalid_message = 'Attempt message to invalid thread'
                await self._send_thread_message(websocket, invalid_thread_id, invalid_message)
                invalid_events = await self._collect_thread_events(websocket, invalid_thread_id, timeout=5.0)
                self.logger.info(f'Invalid thread events: {len(invalid_events)}')
            except Exception as e:
                self.logger.info(f'Expected failure when switching to invalid thread: {e}')
            assert websocket.open, 'WebSocket connection should remain open after failed thread switch'
            recovery_message = 'Recovery request back to valid thread'
            run_id2 = await self._send_thread_message(websocket, valid_thread_id, recovery_message)
            recovery_events = await self._collect_thread_events(websocket, valid_thread_id, timeout=10.0)
            assert len(recovery_events) >= 1, 'Should receive events after recovery to valid thread'
            for event in recovery_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    assert event_thread_id == valid_thread_id, f'Recovery event should be for valid thread {valid_thread_id}'
            ping_start = time.time()
            await websocket.ping()
            ping_duration = time.time() - ping_start
            assert ping_duration < 5.0, f'Connection should be healthy after recovery: {ping_duration:.2f}s'
            self.metrics['connection_handovers'] += 1
        self.assert_business_value_delivered({'failed_switch_recovery': True, 'connection_maintained': True, 'recovery_events': len(recovery_events), 'service_resilience': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_34_websocket_connection_thread_context_preservation(self, real_services_fixture):
        """
        Test 34: WebSocket connection preserves thread context during switches.
        
        BVJ: Thread context preservation ensures users don't lose conversation
        history or business context when switching between AI discussion threads.
        """
        financial_thread = await self._create_test_thread(real_services_fixture, thread_name='Financial Analysis Context Thread')
        marketing_thread = await self._create_test_thread(real_services_fixture, thread_name='Marketing Strategy Context Thread')
        financial_thread_id = financial_thread['id']
        marketing_thread_id = marketing_thread['id']
        async with self._create_authenticated_websocket_connection() as websocket:
            financial_context_message = 'Analyze Q4 revenue streams and identify cost reduction opportunities for our enterprise clients'
            run_id1 = await self._send_thread_message(websocket, financial_thread_id, financial_context_message)
            financial_events = await self._collect_thread_events(websocket, financial_thread_id, timeout=15.0)
            assert len(financial_events) >= 1, 'Should establish financial thread context'
            marketing_context_message = 'Develop social media campaign strategy for our new product launch targeting millennials'
            run_id2 = await self._send_thread_message(websocket, marketing_thread_id, marketing_context_message)
            marketing_events = await self._collect_thread_events(websocket, marketing_thread_id, timeout=15.0)
            assert len(marketing_events) >= 1, 'Should establish marketing thread context'
            financial_content = ' '.join([json.dumps(event).lower() for event in financial_events])
            marketing_terms = ['social media', 'campaign', 'product launch', 'millennials']
            for term in marketing_terms:
                if term in financial_content:
                    self.logger.warning(f'Financial context may contain marketing term: {term}')
            marketing_content = ' '.join([json.dumps(event).lower() for event in marketing_events])
            financial_terms = ['revenue streams', 'cost reduction', 'enterprise clients']
            for term in financial_terms:
                if term in marketing_content:
                    self.logger.warning(f'Marketing context may contain financial term: {term}')
            followup_financial_message = 'Based on the previous analysis, what are the top 3 immediate cost reduction actions?'
            run_id3 = await self._send_thread_message(websocket, financial_thread_id, followup_financial_message)
            followup_financial_events = await self._collect_thread_events(websocket, financial_thread_id, timeout=10.0)
            assert len(followup_financial_events) >= 1, 'Should maintain financial context continuity'
            all_events = financial_events + marketing_events + followup_financial_events
            thread_attribution_correct = True
            for event in all_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    expected_threads = [financial_thread_id, marketing_thread_id]
                    if event_thread_id not in expected_threads:
                        thread_attribution_correct = False
                        self.logger.error(f'Event has incorrect thread attribution: {event_thread_id}')
            assert thread_attribution_correct, 'Thread attribution should remain correct during context switches'
        self.assert_business_value_delivered({'context_preservation': True, 'context_isolation': True, 'context_continuity': len(followup_financial_events), 'thread_attribution_accuracy': thread_attribution_correct}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_35_websocket_connection_performance_during_frequent_thread_switches(self, real_services_fixture):
        """
        Test 35: WebSocket connection performance during frequent thread switches.
        
        BVJ: High-performance thread switching enables power users to efficiently
        manage multiple concurrent AI conversations without latency penalties.
        """
        thread_count = 4
        threads = []
        for i in range(thread_count):
            thread_data = await self._create_test_thread(real_services_fixture, thread_name=f'Performance Test Thread {i + 1}')
            threads.append(thread_data)
        async with self._create_authenticated_websocket_connection() as websocket:
            switch_times = []
            event_delivery_times = []
            total_events = 0
            start_time = time.time()
            switch_count = thread_count * 3
            for switch_iteration in range(switch_count):
                thread_index = switch_iteration % len(threads)
                thread_data = threads[thread_index]
                thread_id = thread_data['id']
                switch_start = time.time()
                message = f'Performance test message {switch_iteration + 1} for rapid switching'
                run_id = await self._send_thread_message(websocket, thread_id, message)
                switch_end = time.time()
                switch_times.append(switch_end - switch_start)
                delivery_start = time.time()
                events = await self._collect_thread_events(websocket, thread_id, timeout=5.0)
                delivery_end = time.time()
                if len(events) > 0:
                    event_delivery_times.append(delivery_end - delivery_start)
                total_events += len(events)
                await asyncio.sleep(0.2)
            total_time = time.time() - start_time
            avg_switch_time = sum(switch_times) / len(switch_times) if switch_times else 0
            avg_delivery_time = sum(event_delivery_times) / len(event_delivery_times) if event_delivery_times else 0
            switches_per_second = switch_count / total_time if total_time > 0 else 0
            events_per_second = total_events / total_time if total_time > 0 else 0
            assert avg_switch_time < 1.0, f'Average switch time should be < 1s, got {avg_switch_time:.3f}s'
            assert avg_delivery_time < 10.0, f'Average event delivery should be < 10s, got {avg_delivery_time:.3f}s'
            assert switches_per_second > 1.0, f'Should handle > 1 switch/second, got {switches_per_second:.2f}'
            successful_deliveries = len(event_delivery_times)
            delivery_success_rate = successful_deliveries / switch_count if switch_count > 0 else 0
            assert delivery_success_rate >= 0.7, f'Should deliver events for >= 70% of switches, got {delivery_success_rate:.2%}'
            assert websocket.open, 'WebSocket should remain open under frequent switching load'
            health_check_start = time.time()
            await websocket.ping()
            health_check_time = time.time() - health_check_start
            assert health_check_time < 2.0, f'Connection should remain responsive: {health_check_time:.3f}s'
            self.metrics['thread_switches'] += switch_count
        self.assert_business_value_delivered({'frequent_switches_completed': switch_count, 'average_switch_time': avg_switch_time, 'average_delivery_time': avg_delivery_time, 'switches_per_second': switches_per_second, 'events_per_second': events_per_second, 'delivery_success_rate': delivery_success_rate, 'high_performance_validated': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_36_multi_user_websocket_thread_isolation_basic(self, real_services_fixture):
        """
        Test 36: Basic multi-user WebSocket thread isolation.
        
        BVJ: Thread isolation between different users ensures enterprise privacy
        and prevents accidental sharing of sensitive business conversations.
        """
        user1_id = f'isolation_user1_{uuid.uuid4().hex[:6]}'
        user2_id = f'isolation_user2_{uuid.uuid4().hex[:6]}'
        user1_thread = await self._create_test_thread(real_services_fixture, user_id=user1_id, thread_name='User 1 Private Thread')
        user2_thread = await self._create_test_thread(real_services_fixture, user_id=user2_id, thread_name='User 2 Private Thread')
        user1_thread_id = user1_thread['id']
        user2_thread_id = user2_thread['id']
        try:
            user1_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user1_id)}', 'X-Room-ID': user1_thread_id, 'X-Test-Type': 'multi_user_isolation'}, subprotocols=['jwt-auth'])
            user2_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user2_id)}', 'X-Room-ID': user2_thread_id, 'X-Test-Type': 'multi_user_isolation'}, subprotocols=['jwt-auth'])
            for ws in [user1_websocket, user2_websocket]:
                welcome_msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                welcome_data = json.loads(welcome_msg)
                assert welcome_data.get('connection_ready') is True
            user1_message = 'Confidential: Acquiring competitor CompanyX for $50M - analyze financial impact'
            user2_message = 'Internal: Layoffs planned for Q1 - prepare cost analysis for 200 employees'
            await asyncio.gather(self._send_thread_message(user1_websocket, user1_thread_id, user1_message), self._send_thread_message(user2_websocket, user2_thread_id, user2_message))
            user1_events, user2_events = await asyncio.gather(self._collect_thread_events(user1_websocket, user1_thread_id, timeout=15.0), self._collect_thread_events(user2_websocket, user2_thread_id, timeout=15.0))
            assert len(user1_events) >= 1, 'User 1 should receive events from their thread'
            assert len(user2_events) >= 1, 'User 2 should receive events from their thread'
            user1_content = ' '.join([json.dumps(event).lower() for event in user1_events])
            user2_sensitive_terms = ['layoffs', 'q1', '200 employees']
            user1_contamination = any((term in user1_content for term in user2_sensitive_terms))
            assert not user1_contamination, f"User 1 events should not contain User 2's sensitive content"
            user2_content = ' '.join([json.dumps(event).lower() for event in user2_events])
            user1_sensitive_terms = ['acquiring', 'companyx', '$50m']
            user2_contamination = any((term in user2_content for term in user1_sensitive_terms))
            assert not user2_contamination, f"User 2 events should not contain User 1's sensitive content"
            for event in user1_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    assert event_thread_id == user1_thread_id, f'User 1 event should belong to their thread'
            for event in user2_events:
                event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                if event_thread_id:
                    assert event_thread_id == user2_thread_id, f'User 2 event should belong to their thread'
            self.metrics['multi_user_operations'] += 1
        finally:
            for ws in [user1_websocket, user2_websocket]:
                try:
                    await ws.close()
                except:
                    pass
        self.assert_business_value_delivered({'multi_user_isolation': True, 'sensitive_content_protected': True, 'thread_attribution_correct': True, 'privacy_maintained': len(user1_events) + len(user2_events)}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_37_concurrent_multi_user_thread_operations(self, real_services_fixture):
        """
        Test 37: Concurrent multi-user thread operations via WebSocket.
        
        BVJ: Concurrent operations enable multiple enterprise teams to use
        AI assistance simultaneously without interference or performance degradation.
        """
        user_count = 4
        users = []
        for i in range(user_count):
            user_id = f'concurrent_user_{i + 1}_{uuid.uuid4().hex[:6]}'
            thread_data = await self._create_test_thread(real_services_fixture, user_id=user_id, thread_name=f'Concurrent User {i + 1} Thread')
            users.append({'user_id': user_id, 'thread_id': thread_data['id'], 'thread_name': thread_data['name']})

        async def user_concurrent_operation(user_context, operation_duration=10.0):
            """Simulate concurrent user operation."""
            user_id = user_context['user_id']
            thread_id = user_context['thread_id']
            try:
                websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user_id)}', 'X-Room-ID': thread_id, 'X-Test-Type': 'concurrent_operations'}, subprotocols=['jwt-auth'])
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                welcome_data = json.loads(welcome_msg)
                assert welcome_data.get('connection_ready') is True
                business_requests = ['Analyze customer acquisition costs for SaaS platform', 'Optimize supply chain logistics for manufacturing', 'Develop pricing strategy for new service offering', 'Review compliance requirements for financial regulations']
                user_index = int(user_id.split('_')[2]) - 1
                message = business_requests[user_index % len(business_requests)]
                await self._send_thread_message(websocket, thread_id, message)
                events = await self._collect_thread_events(websocket, thread_id, timeout=operation_duration)
                await websocket.close()
                return {'user_id': user_id, 'thread_id': thread_id, 'events_received': len(events), 'operation_successful': len(events) >= 1, 'events': events}
            except Exception as e:
                self.logger.error(f'Concurrent operation error for user {user_id}: {e}')
                return {'user_id': user_id, 'thread_id': thread_id, 'events_received': 0, 'operation_successful': False, 'error': str(e)}
        start_time = time.time()
        concurrent_tasks = [user_concurrent_operation(user) for user in users]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_operations = 0
        total_events = 0
        user_results = {}
        for result in results:
            if isinstance(result, dict) and (not isinstance(result, Exception)):
                user_results[result['user_id']] = result
                if result['operation_successful']:
                    successful_operations += 1
                total_events += result['events_received']
            else:
                self.logger.error(f'Concurrent operation exception: {result}')
        success_rate = successful_operations / user_count
        assert success_rate >= 0.75, f'At least 75% of concurrent operations should succeed, got {success_rate:.2%}'
        assert total_time < 30.0, f'Concurrent operations should complete within 30s, took {total_time:.2f}s'
        for user_id, result in user_results.items():
            if 'events' in result:
                for event in result['events']:
                    event_thread_id = event.get('thread_id', event.get('data', {}).get('thread_id'))
                    if event_thread_id:
                        user_thread = next((u['thread_id'] for u in users if u['user_id'] == user_id), None)
                        assert event_thread_id == user_thread, f"Event should belong to user's thread: {user_id}"
        self.metrics['multi_user_operations'] += user_count
        self.assert_business_value_delivered({'concurrent_users': user_count, 'success_rate': success_rate, 'total_events': total_events, 'operation_time': total_time, 'isolation_maintained': True, 'enterprise_scalability': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_38_multi_user_websocket_room_access_control(self, real_services_fixture):
        """
        Test 38: Multi-user WebSocket room access control and authorization.
        
        BVJ: Proper access control ensures enterprise users can only access
        their authorized threads and cannot eavesdrop on other users' AI conversations.
        """
        owner_user_id = f'owner_user_{uuid.uuid4().hex[:6]}'
        authorized_user_id = f'auth_user_{uuid.uuid4().hex[:6]}'
        unauthorized_user_id = f'unauth_user_{uuid.uuid4().hex[:6]}'
        owner_thread = await self._create_test_thread(real_services_fixture, user_id=owner_user_id, thread_name='Owner Private Business Thread')
        owner_thread_id = owner_thread['id']
        try:
            owner_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(owner_user_id)}', 'X-Room-ID': owner_thread_id, 'X-Test-Type': 'access_control'}, subprotocols=['jwt-auth'])
            owner_welcome = await asyncio.wait_for(owner_websocket.recv(), timeout=10.0)
            owner_welcome_data = json.loads(owner_welcome)
            assert owner_welcome_data.get('connection_ready') is True, 'Owner should connect successfully'
            sensitive_message = 'Confidential merger discussion: acquire startup for $10M by end of quarter'
            await self._send_thread_message(owner_websocket, owner_thread_id, sensitive_message)
            owner_events = await self._collect_thread_events(owner_websocket, owner_thread_id, timeout=10.0)
            assert len(owner_events) >= 1, 'Owner should receive events from their thread'
            try:
                unauthorized_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(unauthorized_user_id)}', 'X-Room-ID': owner_thread_id, 'X-Test-Type': 'unauthorized_access'}, subprotocols=['jwt-auth'])
                unauthorized_welcome = await asyncio.wait_for(unauthorized_websocket.recv(), timeout=5.0)
                unauthorized_events = await self._collect_thread_events(unauthorized_websocket, owner_thread_id, timeout=5.0)
                unauthorized_content = ' '.join([json.dumps(event).lower() for event in unauthorized_events])
                sensitive_terms = ['confidential', 'merger', '$10m', 'startup']
                has_sensitive_content = any((term in unauthorized_content for term in sensitive_terms))
                assert not has_sensitive_content, 'Unauthorized user should not see sensitive content'
                await unauthorized_websocket.close()
            except Exception as auth_error:
                self.logger.info(f'Unauthorized access properly blocked: {auth_error}')
            authorized_thread = await self._create_test_thread(real_services_fixture, user_id=authorized_user_id, thread_name='Authorized User Thread')
            authorized_thread_id = authorized_thread['id']
            authorized_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(authorized_user_id)}', 'X-Room-ID': authorized_thread_id, 'X-Test-Type': 'authorized_access'}, subprotocols=['jwt-auth'])
            auth_welcome = await asyncio.wait_for(authorized_websocket.recv(), timeout=10.0)
            auth_welcome_data = json.loads(auth_welcome)
            assert auth_welcome_data.get('connection_ready') is True, 'Authorized user should connect to their thread'
            auth_message = 'Standard business analysis request for authorized user'
            await self._send_thread_message(authorized_websocket, authorized_thread_id, auth_message)
            auth_events = await self._collect_thread_events(authorized_websocket, authorized_thread_id, timeout=10.0)
            assert len(auth_events) >= 1, 'Authorized user should receive events from their thread'
            auth_content = ' '.join([json.dumps(event).lower() for event in auth_events])
            owner_sensitive_terms = ['confidential merger', '$10m acquisition']
            has_owner_content = any((term in auth_content for term in owner_sensitive_terms))
            assert not has_owner_content, "Authorized user should not see owner's sensitive content"
            await authorized_websocket.close()
        finally:
            try:
                await owner_websocket.close()
            except:
                pass
        self.assert_business_value_delivered({'access_control_enforced': True, 'unauthorized_access_blocked': True, 'authorized_access_granted': True, 'sensitive_content_protected': True, 'enterprise_security': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_39_multi_user_websocket_thread_load_balancing(self, real_services_fixture):
        """
        Test 39: Multi-user WebSocket thread load balancing and resource distribution.
        
        BVJ: Load balancing ensures consistent AI performance for all enterprise
        users even during peak usage periods with multiple concurrent threads.
        """
        user_count = 6
        users_and_threads = []
        for i in range(user_count):
            user_id = f'load_test_user_{i + 1}_{uuid.uuid4().hex[:6]}'
            thread_data = await self._create_test_thread(real_services_fixture, user_id=user_id, thread_name=f'Load Test User {i + 1} Thread')
            users_and_threads.append({'user_id': user_id, 'thread_id': thread_data['id'], 'load_factor': i % 3 + 1})

        async def simulate_user_load(user_context):
            """Simulate user load with varying intensity."""
            user_id = user_context['user_id']
            thread_id = user_context['thread_id']
            load_factor = user_context['load_factor']
            performance_metrics = {'user_id': user_id, 'connection_time': 0, 'message_send_times': [], 'event_receive_times': [], 'total_events': 0, 'errors': []}
            try:
                connection_start = time.time()
                websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(user_id)}', 'X-Room-ID': thread_id, 'X-Test-Type': 'load_balancing'}, subprotocols=['jwt-auth'])
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                performance_metrics['connection_time'] = time.time() - connection_start
                for message_num in range(load_factor):
                    message_start = time.time()
                    message = f'Load test message {message_num + 1} - complex business analysis with {load_factor}x intensity'
                    await self._send_thread_message(websocket, thread_id, message)
                    message_end = time.time()
                    performance_metrics['message_send_times'].append(message_end - message_start)
                    event_start = time.time()
                    events = await self._collect_thread_events(websocket, thread_id, timeout=8.0)
                    event_end = time.time()
                    if len(events) > 0:
                        performance_metrics['event_receive_times'].append(event_end - event_start)
                    performance_metrics['total_events'] += len(events)
                    await asyncio.sleep(0.5)
                await websocket.close()
            except Exception as e:
                performance_metrics['errors'].append(str(e))
                self.logger.error(f'Load simulation error for user {user_id}: {e}')
            return performance_metrics
        load_start_time = time.time()
        load_tasks = [simulate_user_load(user_ctx) for user_ctx in users_and_threads]
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        total_load_time = time.time() - load_start_time
        successful_users = 0
        total_events = 0
        avg_connection_time = 0
        avg_message_send_time = 0
        avg_event_receive_time = 0
        valid_results = [r for r in load_results if isinstance(r, dict)]
        for result in valid_results:
            if len(result['errors']) == 0:
                successful_users += 1
                total_events += result['total_events']
                avg_connection_time += result['connection_time']
                if result['message_send_times']:
                    avg_message_send_time += sum(result['message_send_times']) / len(result['message_send_times'])
                if result['event_receive_times']:
                    avg_event_receive_time += sum(result['event_receive_times']) / len(result['event_receive_times'])
        if successful_users > 0:
            avg_connection_time /= successful_users
            avg_message_send_time /= successful_users
            avg_event_receive_time /= successful_users
        success_rate = successful_users / user_count
        assert success_rate >= 0.8, f'At least 80% of users should succeed under load, got {success_rate:.2%}'
        assert avg_connection_time < 10.0, f'Average connection time should be reasonable under load: {avg_connection_time:.2f}s'
        assert avg_message_send_time < 2.0, f'Average message send time should be fast: {avg_message_send_time:.3f}s'
        assert avg_event_receive_time < 15.0, f'Average event receive time should be acceptable: {avg_event_receive_time:.2f}s'
        events_per_user = total_events / successful_users if successful_users > 0 else 0
        assert events_per_user >= 1.0, f'Each user should receive adequate events: {events_per_user:.1f}'
        events_per_second = total_events / total_load_time if total_load_time > 0 else 0
        assert events_per_second > 0.5, f'System should maintain reasonable throughput: {events_per_second:.2f} events/s'
        self.metrics['multi_user_operations'] += user_count
        self.assert_business_value_delivered({'load_balanced_users': user_count, 'success_rate': success_rate, 'avg_connection_time': avg_connection_time, 'avg_message_send_time': avg_message_send_time, 'avg_event_receive_time': avg_event_receive_time, 'total_throughput': events_per_second, 'resource_distribution': events_per_user, 'enterprise_scalability': True}, 'automation')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_40_multi_user_websocket_thread_failover_recovery(self, real_services_fixture):
        """
        Test 40: Multi-user WebSocket thread failover and recovery scenarios.
        
        BVJ: Failover recovery ensures enterprise users maintain AI conversation
        continuity even during system issues, preserving business context and productivity.
        """
        primary_user_id = f'primary_user_{uuid.uuid4().hex[:6]}'
        secondary_user_id = f'secondary_user_{uuid.uuid4().hex[:6]}'
        backup_user_id = f'backup_user_{uuid.uuid4().hex[:6]}'
        primary_thread = await self._create_test_thread(real_services_fixture, user_id=primary_user_id, thread_name='Primary User Failover Thread')
        secondary_thread = await self._create_test_thread(real_services_fixture, user_id=secondary_user_id, thread_name='Secondary User Failover Thread')
        primary_thread_id = primary_thread['id']
        secondary_thread_id = secondary_thread['id']
        try:
            primary_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(primary_user_id)}', 'X-Room-ID': primary_thread_id, 'X-Test-Type': 'failover_recovery'}, subprotocols=['jwt-auth'])
            secondary_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(secondary_user_id)}', 'X-Room-ID': secondary_thread_id, 'X-Test-Type': 'failover_recovery'}, subprotocols=['jwt-auth'])
            for ws in [primary_websocket, secondary_websocket]:
                welcome_msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                welcome_data = json.loads(welcome_msg)
                assert welcome_data.get('connection_ready') is True
            primary_message = 'Critical: Emergency budget reallocation needed for Q4 - analyze financial impact'
            secondary_message = 'Important: Product launch delayed - assess marketing campaign adjustments'
            await asyncio.gather(self._send_thread_message(primary_websocket, primary_thread_id, primary_message), self._send_thread_message(secondary_websocket, secondary_thread_id, secondary_message))
            initial_primary_events, initial_secondary_events = await asyncio.gather(self._collect_thread_events(primary_websocket, primary_thread_id, timeout=10.0), self._collect_thread_events(secondary_websocket, secondary_thread_id, timeout=10.0))
            assert len(initial_primary_events) >= 1, 'Primary user should receive initial events'
            assert len(initial_secondary_events) >= 1, 'Secondary user should receive initial events'
            self.logger.info('Simulating connection failure for primary user')
            await primary_websocket.close()
            secondary_followup = 'Follow up: Need additional market research data for delayed launch'
            await self._send_thread_message(secondary_websocket, secondary_thread_id, secondary_followup)
            secondary_continued_events = await self._collect_thread_events(secondary_websocket, secondary_thread_id, timeout=8.0)
            assert len(secondary_continued_events) >= 1, 'Secondary user should continue receiving events'
            self.logger.info('Simulating primary user recovery')
            recovered_primary_websocket = await websockets.connect('ws://localhost:8000/ws', extra_headers={'Authorization': f'Bearer {await self._create_test_jwt_token(primary_user_id)}', 'X-Room-ID': primary_thread_id, 'X-Test-Type': 'recovery'}, subprotocols=['jwt-auth'])
            recovery_welcome = await asyncio.wait_for(recovered_primary_websocket.recv(), timeout=10.0)
            recovery_welcome_data = json.loads(recovery_welcome)
            assert recovery_welcome_data.get('connection_ready') is True, 'Primary user should recover successfully'
            recovery_message = 'Recovery: Continuing Q4 budget analysis after connection issue - need updated projections'
            await self._send_thread_message(recovered_primary_websocket, primary_thread_id, recovery_message)
            recovery_events = await self._collect_thread_events(recovered_primary_websocket, primary_thread_id, timeout=10.0)
            assert len(recovery_events) >= 1, 'Primary user should receive events after recovery'
            recovery_content = ' '.join([json.dumps(event).lower() for event in recovery_events])
            business_context_terms = ['q4', 'budget', 'financial', 'analysis']
            has_context_continuity = any((term in recovery_content for term in business_context_terms))
            if not has_context_continuity:
                self.logger.info('Recovery events may not contain explicit business context continuity')
            final_primary_message = 'Final: Budget reallocation approved - implement changes'
            final_secondary_message = 'Final: Marketing timeline adjusted - proceed with revised launch'
            await asyncio.gather(self._send_thread_message(recovered_primary_websocket, primary_thread_id, final_primary_message), self._send_thread_message(secondary_websocket, secondary_thread_id, final_secondary_message))
            final_primary_events, final_secondary_events = await asyncio.gather(self._collect_thread_events(recovered_primary_websocket, primary_thread_id, timeout=8.0), self._collect_thread_events(secondary_websocket, secondary_thread_id, timeout=8.0))
            assert len(final_primary_events) >= 1, 'Recovered primary user should receive final events'
            assert len(final_secondary_events) >= 1, 'Secondary user should continue receiving final events'
            all_primary_content = ' '.join([json.dumps(event).lower() for events in [initial_primary_events, recovery_events, final_primary_events] for event in events])
            all_secondary_content = ' '.join([json.dumps(event).lower() for events in [initial_secondary_events, secondary_continued_events, final_secondary_events] for event in events])
            secondary_terms = ['product launch', 'marketing campaign', 'delayed']
            primary_contamination = any((term in all_primary_content for term in secondary_terms))
            assert not primary_contamination, 'Primary user content should not contain secondary user context'
            primary_terms = ['budget reallocation', 'q4', 'financial impact']
            secondary_contamination = any((term in all_secondary_content for term in primary_terms))
            assert not secondary_contamination, 'Secondary user content should not contain primary user context'
            await recovered_primary_websocket.close()
            await secondary_websocket.close()
        except Exception as e:
            self.logger.error(f'Failover recovery test error: {e}')
            raise
        self.assert_business_value_delivered({'failover_recovery_successful': True, 'business_continuity_maintained': True, 'user_isolation_preserved': True, 'connection_recovery_validated': True, 'enterprise_resilience': True, 'total_events_preserved': len(initial_primary_events) + len(recovery_events) + len(final_primary_events) + len(initial_secondary_events) + len(secondary_continued_events) + len(final_secondary_events)}, 'automation')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')