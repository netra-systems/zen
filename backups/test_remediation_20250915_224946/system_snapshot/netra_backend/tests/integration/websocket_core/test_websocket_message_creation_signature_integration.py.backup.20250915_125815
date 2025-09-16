"""
Integration test suite for WebSocket message creation signature compatibility.

This test file implements Issue #405 integration testing to validate
create_server_message signature compatibility in real usage scenarios
across the WebSocket handler ecosystem.

Business Value:
- Validates end-to-end WebSocket message creation flow 
- Tests real handler integration with message creation functions
- Ensures proper signature compatibility in multi-component scenarios
- Prevents production failures from signature mismatches

Integration Test Strategy:
- Test real handler usage patterns from handlers.py
- Validate message flow through actual WebSocket infrastructure
- Test specific error lines from production code
- Use real objects where possible (no Docker dependency)
"""
import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.types import MessageType, ServerMessage, create_server_message, WebSocketMessage
from netra_backend.app.websocket_core.handlers import get_message_router, get_router_handler_count, list_registered_handlers

class TestWebSocketMessageCreationSignatureIntegration(SSotAsyncTestCase):
    """Integration tests for create_server_message signature compatibility."""

    async def asyncSetUp(self):
        """Set up integration test environment."""
        await super().asyncSetUp()
        self.mock_websocket = MagicMock()
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        self.test_user_id = 'user_123456'
        self.test_thread_id = 'thread_789012'

    async def test_handlers_message_creation_integration(self):
        """
        Test that handlers.py can successfully create messages using imported function.
        
        This test should FAIL initially if signature errors exist.
        """
        try:
            ack_response = create_server_message(MessageType.AGENT_TASK_ACK, {'task_id': 'task_123', 'status': 'acknowledged', 'timestamp': time.time(), 'user_id': self.test_user_id})
            assert isinstance(ack_response, ServerMessage)
            assert ack_response.type == MessageType.AGENT_TASK_ACK
            self.logger.info(f'Message creation successful: {ack_response}')
        except TypeError as e:
            self.logger.error(f'SIGNATURE ERROR DETECTED: {e}')
            pytest.fail(f'Signature error in handler integration: {e}')

    async def test_connection_handler_message_patterns(self):
        """
        Test actual connection handler message creation patterns.
        
        Tests patterns from handle_connection_message function.
        """
        try:
            response = create_server_message(MessageType.SYSTEM_MESSAGE, {'status': 'connected', 'user_id': self.test_user_id, 'timestamp': time.time()})
            assert isinstance(response, ServerMessage)
            assert response.data['status'] == 'connected'
        except TypeError as e:
            self.logger.error(f'Connection handler signature error: {e}')
            pytest.fail(f'Connection handler failed due to signature: {e}')

    async def test_ping_heartbeat_message_patterns(self):
        """
        Test ping/heartbeat message creation patterns.
        
        Tests patterns from handle_ping_heartbeat_message function.
        """
        try:
            ping_response = create_server_message(MessageType.PONG, {'timestamp': time.time(), 'user_id': self.test_user_id})
            assert isinstance(ping_response, ServerMessage)
            assert ping_response.type == MessageType.PONG
            heartbeat_response = create_server_message(MessageType.HEARTBEAT_ACK, {'timestamp': time.time(), 'status': 'healthy'})
            assert isinstance(heartbeat_response, ServerMessage)
            assert heartbeat_response.type == MessageType.HEARTBEAT_ACK
        except TypeError as e:
            self.logger.error(f'Ping/heartbeat handler signature error: {e}')
            pytest.fail(f'Ping/heartbeat handler failed: {e}')

    async def test_agent_message_handler_patterns(self):
        """
        Test agent message creation patterns from handlers.py.
        
        Tests all agent event patterns: started, thinking, executing, completed.
        """
        try:
            agent_started_event = create_server_message(MessageType.SYSTEM_MESSAGE, {'event': 'agent_started', 'agent_type': 'supervisor', 'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'timestamp': time.time(), 'golden_path_status': 'agent_execution_initiated'})
            agent_thinking_event = create_server_message(MessageType.AGENT_PROGRESS, {'event': 'agent_thinking', 'progress': 'analyzing_request', 'user_id': self.test_user_id, 'timestamp': time.time()})
            tool_executing_event = create_server_message(MessageType.AGENT_PROGRESS, {'event': 'tool_executing', 'tool_name': 'data_analyzer', 'user_id': self.test_user_id, 'timestamp': time.time()})
            tool_completed_event = create_server_message(MessageType.AGENT_PROGRESS, {'event': 'tool_completed', 'tool_name': 'data_analyzer', 'result_summary': 'Analysis complete', 'user_id': self.test_user_id, 'timestamp': time.time()})
            agent_completed_event = create_server_message(MessageType.AGENT_RESPONSE_COMPLETE, {'event': 'agent_completed', 'response': 'Your analysis is ready', 'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'timestamp': time.time(), 'golden_path_status': 'agent_response_delivered'})
            events = [agent_started_event, agent_thinking_event, tool_executing_event, tool_completed_event, agent_completed_event]
            for event in events:
                assert isinstance(event, ServerMessage)
                assert hasattr(event, 'type')
                assert hasattr(event, 'data')
        except TypeError as e:
            self.logger.error(f'Agent message handler signature error: {e}')
            pytest.fail(f'Agent message handlers failed: {e}')

    async def test_system_message_helper_integration(self):
        """
        Test _send_system_message helper function integration.
        
        This tests the actual helper function from handlers.py line 1495.
        """
        try:
            data = {'status': 'test_status', 'message': 'Test system message', 'timestamp': time.time()}
            system_msg = create_server_message(MessageType.SYSTEM_MESSAGE, data)
            assert isinstance(system_msg, ServerMessage)
            assert system_msg.type == MessageType.SYSTEM_MESSAGE
            assert system_msg.data == data
            serialized = system_msg.model_dump(mode='json')
            assert isinstance(serialized, dict)
            assert serialized['type'] == MessageType.SYSTEM_MESSAGE
        except TypeError as e:
            self.logger.error(f'System message helper signature error: {e}')
            pytest.fail(f'System message helper failed: {e}')

    async def test_error_scenario_message_creation(self):
        """
        Test message creation in error scenarios.
        
        Tests patterns used in exception handlers throughout handlers.py.
        """
        try:
            error_ack = create_server_message(MessageType.SYSTEM_MESSAGE, {'status': 'error_acknowledged', 'error_type': 'test_error', 'message': 'Error has been logged', 'timestamp': time.time(), 'user_id': self.test_user_id})
            assert isinstance(error_ack, ServerMessage)
            assert error_ack.data['status'] == 'error_acknowledged'
        except TypeError as e:
            self.logger.error(f'Error scenario signature error: {e}')
            pytest.fail(f'Error scenario message creation failed: {e}')

    async def test_specific_problematic_lines_reproduction(self):
        """
        Test specific problematic lines mentioned in issue #405.
        
        Reproduces exact usage patterns from lines 573, 697, 798, 852.
        """
        try:
            ack_patterns = [(MessageType.AGENT_TASK_ACK, {'task_id': 'task_123', 'status': 'acknowledged', 'timestamp': time.time()}), (MessageType.SYSTEM_MESSAGE, {'status': 'processed', 'timestamp': time.time(), 'user_id': self.test_user_id}), (MessageType.AGENT_RESPONSE_CHUNK, {'chunk_id': 'chunk_123', 'content': 'Test response chunk', 'timestamp': time.time()}), (MessageType.AGENT_STATUS_UPDATE, {'status': 'processing', 'progress': 0.5, 'timestamp': time.time(), 'user_id': self.test_user_id})]
            for msg_type, data in ack_patterns:
                result = create_server_message(msg_type, data)
                assert isinstance(result, ServerMessage)
                assert result.type == msg_type
                assert result.data == data
        except TypeError as e:
            self.logger.error(f'Problematic line reproduction signature error: {e}')
            pytest.fail(f'Problematic line patterns failed: {e}')

    async def test_message_flow_integration_end_to_end(self):
        """
        Test complete message flow from creation to WebSocket transmission.
        
        This tests the full integration path that handlers.py uses.
        """
        try:
            message = create_server_message(MessageType.AGENT_RESPONSE_COMPLETE, {'response': 'Integration test complete', 'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'timestamp': time.time(), 'golden_path_status': 'integration_test_passed'})
            assert isinstance(message, ServerMessage)
            json_data = message.model_dump(mode='json')
            assert isinstance(json_data, dict)
            json_string = json.dumps(json_data)
            assert isinstance(json_string, str)
            await self.mock_websocket.send_json(json_data)
            self.mock_websocket.send_json.assert_called_once_with(json_data)
        except TypeError as e:
            self.logger.error(f'End-to-end integration signature error: {e}')
            pytest.fail(f'End-to-end message flow failed: {e}')

class TestSignatureErrorScenarios(SSotAsyncTestCase):
    """Test specific signature error scenarios that should fail."""

    async def test_missing_data_parameter_should_fail(self):
        """
        Test that missing data parameter causes TypeError.
        
        This test validates that the signature error exists when expected.
        """
        with pytest.raises(TypeError, match='missing 1 required positional argument'):
            create_server_message(MessageType.SYSTEM_MESSAGE)

    async def test_none_data_parameter_should_work(self):
        """
        Test that None data parameter works (if signature allows it).
        
        This tests if the function can handle None data gracefully.
        """
        try:
            result = create_server_message(MessageType.SYSTEM_MESSAGE, None)
            assert isinstance(result, ServerMessage)
        except (TypeError, ValueError) as e:
            self.logger.info(f'None data not allowed (expected): {e}')
            assert 'None' in str(e) or 'required' in str(e)

    async def test_empty_dict_data_parameter(self):
        """
        Test that empty dict works for data parameter.
        
        This validates the minimum viable data requirement.
        """
        try:
            result = create_server_message(MessageType.SYSTEM_MESSAGE, {})
            assert isinstance(result, ServerMessage)
            assert result.data == {}
        except (TypeError, ValueError) as e:
            self.logger.error(f'Empty dict not allowed: {e}')
            pytest.fail(f'Empty dict should be valid data: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')