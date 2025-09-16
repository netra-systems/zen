"""Test WebSocket Core Unified Emitter - Core Functionality Tests

Business Value Justification (BVJ):
- Segment: Platform/All Users (Free -> Enterprise)
- Business Goal: Protect $500K+ ARR WebSocket event emission functionality
- Value Impact: Ensures WebSocket emitter creates proper events, handles user contexts, and maintains isolation
- Revenue Impact: Prevents chat event delivery failures that would degrade user experience

This test suite focuses on the core functionality of the WebSocket unified emitter:

1. Event creation and formatting
2. User context handling and isolation
3. Critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
4. Error handling and recovery
5. Factory pattern compliance

These tests validate the business-critical event emission that powers real-time chat.
"""
import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ConnectionID, WebSocketID
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

class MockWebSocketManager:
    """Simple WebSocket manager mock for testing emitter."""

    def __init__(self):
        self.sent_messages = []
        self.user_connections = {}

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """Mock send to user."""
        self.sent_messages.append({'user_id': user_id, 'message': message, 'timestamp': datetime.now(timezone.utc)})
        return True

    async def has_connection(self, connection_id: str) -> bool:
        """Mock connection check."""
        return connection_id in self.user_connections

    def get_sent_messages(self) -> List[dict]:
        """Get all sent messages."""
        return self.sent_messages.copy()

    def clear_messages(self):
        """Clear sent messages."""
        self.sent_messages.clear()

@pytest.mark.unit
class TestUnifiedWebSocketEmitterCore(SSotAsyncTestCase):
    """Test core functionality of UnifiedWebSocketEmitter."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.mock_manager = MockWebSocketManager()
        self.user_context = UserExecutionContext(user_id='test_user_001', thread_id='thread_001', run_id='run_001', websocket_client_id='ws_client_001')
        self.emitter = UnifiedWebSocketEmitter.create_for_user(user_context=self.user_context, websocket_manager=self.mock_manager)

    async def asyncTearDown(self):
        """Clean up test environment."""
        await super().asyncTearDown()

    def test_emitter_factory_creation(self):
        """Test emitter creation via factory method."""
        self.assertIsNotNone(self.emitter)
        self.assertEqual(self.emitter.user_context.user_id, 'test_user_001')
        self.assertEqual(self.emitter.user_context.thread_id, 'thread_001')

    async def test_agent_started_event(self):
        """Test agent_started event emission."""
        await self.emitter.emit_agent_started(agent_id='test_agent_001', message='Starting analysis of your request...')
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 1)
        event = messages[0]
        self.assertEqual(event['user_id'], 'test_user_001')
        self.assertEqual(event['message']['type'], 'agent_started')
        self.assertEqual(event['message']['data']['agent_id'], 'test_agent_001')
        self.assertIn('Starting analysis', event['message']['data']['message'])

    async def test_agent_thinking_event(self):
        """Test agent_thinking event emission."""
        await self.emitter.emit_agent_thinking(thought='Processing your data requirements...', reasoning_step='data_analysis')
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 1)
        event = messages[0]
        self.assertEqual(event['message']['type'], 'agent_thinking')
        self.assertIn('Processing your data', event['message']['data']['thought'])
        self.assertEqual(event['message']['data']['reasoning_step'], 'data_analysis')

    async def test_tool_executing_event(self):
        """Test tool_executing event emission."""
        await self.emitter.emit_tool_executing(tool_name='data_analyzer', parameters={'dataset': 'user_metrics', 'timeframe': '30d'})
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 1)
        event = messages[0]
        self.assertEqual(event['message']['type'], 'tool_executing')
        self.assertEqual(event['message']['data']['tool_name'], 'data_analyzer')
        self.assertIn('dataset', event['message']['data']['parameters'])

    async def test_tool_completed_event(self):
        """Test tool_completed event emission."""
        result_data = {'success': True, 'metrics': {'total_records': 1500, 'avg_engagement': 0.73}}
        await self.emitter.emit_tool_completed(tool_name='data_analyzer', result=result_data, execution_time_ms=2500)
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 1)
        event = messages[0]
        self.assertEqual(event['message']['type'], 'tool_completed')
        self.assertEqual(event['message']['data']['tool_name'], 'data_analyzer')
        self.assertTrue(event['message']['data']['result']['success'])
        self.assertEqual(event['message']['data']['execution_time_ms'], 2500)

    async def test_agent_completed_event(self):
        """Test agent_completed event emission."""
        final_response = {'summary': 'Analysis complete: Found 3 optimization opportunities', 'recommendations': ['Optimize database queries', 'Implement caching', 'Add monitoring']}
        await self.emitter.emit_agent_completed(agent_id='test_agent_001', final_response=final_response, total_execution_time_ms=5000)
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 1)
        event = messages[0]
        self.assertEqual(event['message']['type'], 'agent_completed')
        self.assertEqual(event['message']['data']['agent_id'], 'test_agent_001')
        self.assertIn('optimization opportunities', event['message']['data']['final_response']['summary'])
        self.assertEqual(event['message']['data']['total_execution_time_ms'], 5000)

    async def test_complete_agent_workflow_events(self):
        """Test complete sequence of agent workflow events."""
        self.mock_manager.clear_messages()
        await self.emitter.emit_agent_started('workflow_agent', 'Starting workflow')
        await self.emitter.emit_agent_thinking('Analyzing requirements', 'planning')
        await self.emitter.emit_tool_executing('requirement_analyzer', {'input': 'test'})
        await self.emitter.emit_tool_completed('requirement_analyzer', {'result': 'analysis_done'})
        await self.emitter.emit_agent_completed('workflow_agent', {'final': 'complete'})
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 5)
        event_types = [msg['message']['type'] for msg in messages]
        expected_sequence = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        self.assertEqual(event_types, expected_sequence)
        for message in messages:
            self.assertEqual(message['user_id'], 'test_user_001')

    async def test_user_context_isolation(self):
        """Test that emitters maintain user context isolation."""
        user2_context = UserExecutionContext(user_id='test_user_002', thread_id='thread_002', run_id='run_002', websocket_client_id='ws_client_002')
        emitter2 = UnifiedWebSocketEmitter.create_for_user(user_context=user2_context, websocket_manager=self.mock_manager)
        self.mock_manager.clear_messages()
        await self.emitter.emit_agent_started('agent1', 'User 1 agent started')
        await emitter2.emit_agent_started('agent2', 'User 2 agent started')
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 2)
        user1_messages = [msg for msg in messages if msg['user_id'] == 'test_user_001']
        user2_messages = [msg for msg in messages if msg['user_id'] == 'test_user_002']
        self.assertEqual(len(user1_messages), 1)
        self.assertEqual(len(user2_messages), 1)
        self.assertIn('User 1 agent', user1_messages[0]['message']['data']['message'])
        self.assertIn('User 2 agent', user2_messages[0]['message']['data']['message'])

    async def test_emitter_error_handling(self):
        """Test emitter error handling scenarios."""
        failing_manager = MockWebSocketManager()

        async def failing_send(user_id: str, message: dict) -> bool:
            raise Exception('Connection failed')
        failing_manager.send_to_user = failing_send
        failing_emitter = UnifiedWebSocketEmitter.create_for_user(user_context=self.user_context, websocket_manager=failing_manager)
        try:
            result = await failing_emitter.emit_agent_started('test_agent', 'test message')
            self.assertFalse(result)
        except Exception:
            self.fail('Emitter should handle errors gracefully')

    def test_event_data_validation(self):
        """Test that events contain required fields."""
        emitter = UnifiedWebSocketEmitter.create_for_user(user_context=self.user_context, websocket_manager=self.mock_manager)
        event_data = emitter._create_base_event('test_event', {'test': 'data'})
        self.assertIn('type', event_data)
        self.assertIn('data', event_data)
        self.assertIn('timestamp', event_data)
        self.assertIn('user_id', event_data['data'])
        self.assertIn('thread_id', event_data['data'])
        self.assertEqual(event_data['type'], 'test_event')
        self.assertEqual(event_data['data']['user_id'], 'test_user_001')

@pytest.mark.unit
class TestWebSocketEmitterWithRealScenarios(SSotAsyncTestCase):
    """Test emitter with realistic usage scenarios."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.mock_manager = MockWebSocketManager()

    async def test_multiple_concurrent_agents(self):
        """Test multiple agents for same user working concurrently."""
        user_context = UserExecutionContext(user_id='multi_agent_user', thread_id='multi_thread', run_id='multi_run', websocket_client_id='multi_ws')
        emitter1 = UnifiedWebSocketEmitter.create_for_user(user_context=user_context, websocket_manager=self.mock_manager)
        emitter2 = UnifiedWebSocketEmitter.create_for_user(user_context=user_context, websocket_manager=self.mock_manager)
        await asyncio.gather(emitter1.emit_agent_started('data_agent', 'Analyzing data'), emitter2.emit_agent_started('report_agent', 'Generating report'), emitter1.emit_agent_thinking('Processing metrics', 'data_analysis'), emitter2.emit_agent_thinking('Formatting results', 'report_generation'))
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 4)
        for message in messages:
            self.assertEqual(message['user_id'], 'multi_agent_user')

    async def test_high_frequency_events(self):
        """Test handling of high-frequency event emission."""
        user_context = UserExecutionContext(user_id='high_freq_user', thread_id='high_freq_thread', run_id='high_freq_run', websocket_client_id='high_freq_ws')
        emitter = UnifiedWebSocketEmitter.create_for_user(user_context=user_context, websocket_manager=self.mock_manager)
        tasks = []
        for i in range(20):
            task = emitter.emit_agent_thinking(f'Processing step {i}', f'step_{i}')
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.fail(f'High frequency event failed: {result}')
        messages = self.mock_manager.get_sent_messages()
        self.assertEqual(len(messages), 20)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')