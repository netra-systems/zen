"""
Integration Test: WebSocket Event Emission Integration

PURPOSE: Test WebSocket event structure in realistic agent execution scenarios
REPRODUCES: Issue #1021 - Business fields buried in 'data' wrapper 

EXPECTED FAILURE: These tests should FAIL until structural issue is resolved
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
import json
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestWebSocketEventEmissionIntegration(SSotAsyncTestCase):
    """Integration test for WebSocket event emission during agent execution"""

    def setup_method(self, method):
        """Set up integration test environment"""
        super().setup_method(method)
        self.websocket_manager = UnifiedWebSocketManager()
        self.test_user_id = 'integration_user_456'
        self.mock_websocket = AsyncMock()
        self.websocket_manager._connections = {self.test_user_id: {'websocket': self.mock_websocket, 'last_heartbeat': datetime.now(timezone.utc), 'status': 'active'}}
        self.agent_registry = AgentRegistry()
        self.agent_registry.set_websocket_manager(self.websocket_manager)

    async def test_agent_execution_event_structure_integration(self):
        """
        Test event structure during complete agent execution flow
        EXPECTED FAILURE: Events should have business fields at top level
        """
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.agent_type = 'DataAnalysisAgent'
        mock_agent.run_id = 'integration_run_789'
        captured_messages = []

        async def capture_send_to_user(user_id, message):
            """Capture sent messages for structure validation"""
            captured_messages.append(message)
        with patch.object(self.websocket_manager, 'send_to_user', side_effect=capture_send_to_user), patch.object(self.websocket_manager, 'is_connection_active', return_value=True):
            await self.websocket_manager.emit_critical_event(self.test_user_id, 'agent_started', {'agent_type': 'DataAnalysisAgent', 'run_id': 'integration_run_789', 'user_id': self.test_user_id, 'request_summary': 'Analyze customer data trends for Q3'})
            await self.websocket_manager.emit_critical_event(self.test_user_id, 'agent_thinking', {'thinking_content': 'I need to gather customer data from the last quarter and identify key trends...', 'step_number': 1, 'total_steps': 4, 'run_id': 'integration_run_789'})
            await self.websocket_manager.emit_critical_event(self.test_user_id, 'tool_executing', {'tool_name': 'CustomerDataRetriever', 'tool_description': 'Retrieving Q3 customer metrics', 'parameters': {'quarter': 'Q3', 'metrics': ['growth', 'churn', 'ltv']}, 'execution_id': 'tool_exec_123'})
            await self.websocket_manager.emit_critical_event(self.test_user_id, 'tool_completed', {'tool_name': 'CustomerDataRetriever', 'execution_id': 'tool_exec_123', 'result': {'growth_rate': 12.5, 'churn_rate': 4.2, 'avg_ltv': 850.75}, 'execution_time_ms': 1850, 'status': 'success'})
            await self.websocket_manager.emit_critical_event(self.test_user_id, 'agent_completed', {'response': 'Q3 Analysis Complete: Customer growth at 12.5%, churn stable at 4.2%, average LTV increased to $850.75. Recommend focusing on premium segment expansion.', 'run_id': 'integration_run_789', 'execution_time_ms': 8500, 'tools_used': ['CustomerDataRetriever', 'TrendAnalyzer'], 'status': 'completed'})
        self.assertEqual(len(captured_messages), 5, 'Should have captured 5 event messages')
        agent_started_msg = captured_messages[0]
        self.validate_message_structure(agent_started_msg, 'agent_started', ['agent_type', 'run_id', 'user_id', 'request_summary'])
        agent_thinking_msg = captured_messages[1]
        self.validate_message_structure(agent_thinking_msg, 'agent_thinking', ['thinking_content', 'step_number', 'total_steps', 'run_id'])
        tool_executing_msg = captured_messages[2]
        self.validate_message_structure(tool_executing_msg, 'tool_executing', ['tool_name', 'tool_description', 'parameters', 'execution_id'])
        tool_completed_msg = captured_messages[3]
        self.validate_message_structure(tool_completed_msg, 'tool_completed', ['tool_name', 'execution_id', 'result', 'execution_time_ms', 'status'])
        agent_completed_msg = captured_messages[4]
        self.validate_message_structure(agent_completed_msg, 'agent_completed', ['response', 'run_id', 'execution_time_ms', 'tools_used', 'status'])

    def validate_message_structure(self, message, expected_type, required_fields):
        """
        Validate message has correct structure with business fields at top level
        UPDATED: Messages should now have correct structure (Issue #1021 resolved)
        """
        print(f'Validating {expected_type} message structure: {message}')
        self.assertEqual(message.get('type'), expected_type, f"Event type should be '{expected_type}' at top level")
        for field in required_fields:
            self.assertIn(field, message, f"Field '{field}' should be at top level of {expected_type} message")
        if 'data' in message and isinstance(message['data'], dict):
            for field in required_fields:
                if field in message['data']:
                    self.fail(f"Business field '{field}' should not be buried in 'data' wrapper for {expected_type}")

    async def test_real_time_event_structure_validation(self):
        """
        Test real-time event emission structure matches frontend expectations
        EXPECTED FAILURE: Current structure incompatible with frontend parsing
        """
        events_to_test = [('agent_started', {'agent_type': 'TrendAnalysisAgent', 'run_id': 'realtime_123', 'user_message': 'What are the current market trends?', 'estimated_duration': 15000}), ('agent_thinking', {'thinking_content': "I'll analyze current market data and identify key trends...", 'confidence_level': 0.85, 'processing_stage': 'data_retrieval'}), ('tool_executing', {'tool_name': 'MarketDataAPI', 'real_time': True, 'estimated_completion': 3000})]
        captured_events = []

        async def capture_event(user_id, message):
            captured_events.append(message)
        with patch.object(self.websocket_manager, 'send_to_user', side_effect=capture_event), patch.object(self.websocket_manager, 'is_connection_active', return_value=True):
            for event_type, event_data in events_to_test:
                await self.websocket_manager.emit_critical_event(self.test_user_id, event_type, event_data)
        for i, (expected_type, expected_data) in enumerate(events_to_test):
            captured_event = captured_events[i]
            self.assertEqual(captured_event.get('type'), expected_type)
            for key, value in expected_data.items():
                self.assertIn(key, captured_event, f"Field '{key}' should be at top level for frontend access")
                self.assertEqual(captured_event[key], value, f"Field '{key}' value should be preserved")

    async def test_multi_user_event_structure_isolation(self):
        """
        Test event structure consistency across multiple users
        EXPECTED FAILURE: Structure issues may affect multi-user scenarios
        """
        user_ids = ['user_001', 'user_002', 'user_003']
        for user_id in user_ids:
            self.websocket_manager._connections[user_id] = {'websocket': AsyncMock(), 'last_heartbeat': datetime.now(timezone.utc), 'status': 'active'}
        all_captured_messages = {}

        async def capture_by_user(user_id, message):
            if user_id not in all_captured_messages:
                all_captured_messages[user_id] = []
            all_captured_messages[user_id].append(message)
        with patch.object(self.websocket_manager, 'send_to_user', side_effect=capture_by_user), patch.object(self.websocket_manager, 'is_connection_active', return_value=True):
            for i, user_id in enumerate(user_ids):
                await self.websocket_manager.emit_critical_event(user_id, 'agent_started', {'agent_type': f'Agent_{i + 1}', 'run_id': f'run_{user_id}_{i}', 'user_specific_data': f'data_for_{user_id}', 'priority': 'high' if i == 0 else 'normal'})
        for user_id in user_ids:
            self.assertIn(user_id, all_captured_messages, f'Should have captured message for {user_id}')
            messages = all_captured_messages[user_id]
            self.assertEqual(len(messages), 1, f'Should have 1 message for {user_id}')
            message = messages[0]
            self.assertEqual(message.get('type'), 'agent_started')
            self.assertIn('agent_type', message, 'agent_type should be at top level for all users')
            self.assertIn('run_id', message, 'run_id should be at top level for all users')
            self.assertIn('user_specific_data', message, 'user_specific_data should be at top level for all users')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')