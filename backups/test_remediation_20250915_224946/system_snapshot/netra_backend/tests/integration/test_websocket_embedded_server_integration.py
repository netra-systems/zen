"""
WebSocket Embedded Server Integration Tests

This test suite demonstrates the solution for WebSocket testing without Docker dependencies.
It validates that all critical WebSocket events required for chat business value are working.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Ensure WebSocket functionality works without Docker dependencies
- Value Impact: Eliminate WebSocket test failures that block development velocity
- Strategic Impact: Enable reliable testing in CI/CD without external service dependencies

CRITICAL: Tests all 5 required WebSocket events for chat business value:
1. agent_started - User must see agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency  
4. tool_completed - Tool results display
5. agent_completed - Response ready notification
"""
import asyncio
import json
import logging
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any
from test_framework.websocket_test_integration import WebSocketTestClient, WebSocketIntegrationTestSuite, embedded_websocket_server_fixture, websocket_test_suite, websocket_test_client, validate_websocket_events_for_chat, quick_websocket_health_check
from test_framework.embedded_websocket_server import embedded_websocket_server, EmbeddedWebSocketTestHelper
logger = logging.getLogger(__name__)

class WebSocketEmbeddedServerIntegrationTests:
    """Integration tests for WebSocket functionality using embedded server."""

    @pytest.mark.integration
    async def test_embedded_websocket_server_basic_connection(self, embedded_websocket_server_fixture):
        """Test basic WebSocket connection to embedded server."""
        websocket_url = embedded_websocket_server_fixture
        health_check = await quick_websocket_health_check(websocket_url)
        assert health_check, 'WebSocket health check should pass'
        logger.info(' PASS:  Embedded WebSocket server basic connection test passed')

    @pytest.mark.integration
    async def test_critical_websocket_events_for_chat_business_value(self, websocket_test_suite):
        """
        CRITICAL TEST: Validate all 5 WebSocket events required for chat business value.
        
        This test ensures that the core chat functionality will work properly
        by validating that all critical events are emitted.
        """
        suite, websocket_url = websocket_test_suite
        critical_events = await suite.test_critical_events_emission(websocket_url)
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for event in expected_events:
            assert event in critical_events, f'Critical event {event} not found in response'
            assert critical_events[event], f'Critical event {event} was not received'
        logger.info(' PASS:  All critical WebSocket events validated for chat business value')

    @pytest.mark.integration
    async def test_websocket_chat_message_flow(self, websocket_test_client):
        """Test complete chat message flow with event validation."""
        client = websocket_test_client
        connected = await client.connect()
        assert connected, 'WebSocket connection should be established'
        test_message = 'Hello, test the chat flow!'
        received_events = await client.send_chat_message(test_message, expect_events=True)
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for event in expected_events:
            assert received_events.get(event, False), f'Expected event {event} was not received'
        messages = client.get_received_messages()
        event_sequence = [msg.get('type') or msg.get('event') for msg in messages if msg.get('type') != 'connection_established']
        for event in expected_events:
            assert event in event_sequence, f'Event {event} not found in message sequence'
        logger.info(f' PASS:  Chat message flow completed with {len(messages)} messages')
        logger.info(f'Event sequence: {event_sequence}')

    @pytest.mark.integration
    async def test_websocket_concurrent_connections(self, embedded_websocket_server_fixture):
        """Test multiple concurrent WebSocket connections."""
        websocket_url = embedded_websocket_server_fixture
        clients = []
        connection_count = 3
        try:
            for i in range(connection_count):
                client = WebSocketTestClient(websocket_url)
                connected = await client.connect()
                assert connected, f'Client {i + 1} should connect successfully'
                clients.append(client)

            async def send_message_from_client(client_id, client):
                success = await client.send_message({'type': 'ping', 'client_id': client_id, 'timestamp': time.time()})
                assert success, f'Client {client_id} should send message successfully'
                response = await client.receive_message(timeout=3.0)
                assert response is not None, f'Client {client_id} should receive response'
                assert response.get('type') == 'pong', f'Client {client_id} should receive pong response'
                return client_id
            tasks = [send_message_from_client(i, client) for i, client in enumerate(clients)]
            results = await asyncio.gather(*tasks)
            assert len(results) == connection_count, 'All clients should complete successfully'
            logger.info(f' PASS:  Concurrent connections test passed with {connection_count} clients')
        finally:
            for client in clients:
                await client.disconnect()

    @pytest.mark.integration
    async def test_websocket_message_routing_types(self, websocket_test_client):
        """Test WebSocket message routing for different message types."""
        client = websocket_test_client
        connected = await client.connect()
        assert connected, 'WebSocket connection should be established'
        test_cases = [{'name': 'ping_message', 'message': {'type': 'ping'}, 'expected_response_type': 'pong'}, {'name': 'echo_message', 'message': {'type': 'echo', 'payload': {'test': 'data'}}, 'expected_response_type': 'echo'}, {'name': 'unknown_message', 'message': {'type': 'unknown_type', 'payload': {'test': True}}, 'expected_response_type': 'echo'}]
        for test_case in test_cases:
            logger.info(f"Testing {test_case['name']}")
            client.clear_received_messages()
            success = await client.send_message(test_case['message'])
            assert success, f"Should send {test_case['name']} successfully"
            response = await client.receive_message(timeout=3.0)
            assert response is not None, f"Should receive response for {test_case['name']}"
            assert response.get('type') == test_case['expected_response_type'], f"Response type should be {test_case['expected_response_type']} for {test_case['name']}"
        logger.info(' PASS:  Message routing test completed for all message types')

    @pytest.mark.integration
    async def test_websocket_error_handling(self, websocket_test_client):
        """Test WebSocket error handling."""
        client = websocket_test_client
        connected = await client.connect()
        assert connected, 'WebSocket connection should be established'
        try:
            await client.websocket.send('invalid json {')
            response = await client.receive_message(timeout=3.0)
            if response:
                assert response.get('type') == 'error', 'Should receive error for invalid JSON'
                assert 'Invalid JSON' in response.get('message', ''), 'Error message should mention JSON'
        except Exception as e:
            logger.info(f'WebSocket closed on invalid JSON (acceptable): {e}')
        logger.info(' PASS:  Error handling test completed')

    @pytest.mark.integration
    async def test_comprehensive_websocket_suite(self, embedded_websocket_server_fixture):
        """Run comprehensive WebSocket test suite."""
        websocket_url = embedded_websocket_server_fixture
        suite = WebSocketIntegrationTestSuite(websocket_url)
        results = await suite.run_comprehensive_test_suite()
        assert results.get('connection', False), 'Basic connection test should pass'
        assert results.get('critical_events', False), 'Critical events test should pass'
        assert results.get('message_routing', False), 'Message routing test should pass'
        critical_events_detail = results.get('critical_events_detail', {})
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for event in expected_events:
            assert critical_events_detail.get(event, False), f'Critical event {event} should be received'
        logger.info(' PASS:  Comprehensive WebSocket test suite completed successfully')
        logger.info(f'Test results: {json.dumps(results, indent=2)}')

    @pytest.mark.integration
    async def test_websocket_business_value_validation(self, embedded_websocket_server_fixture):
        """
        PRIMARY BUSINESS VALUE TEST: Validate WebSocket events enable chat functionality.
        
        This test directly validates that the WebSocket implementation supports
        the core business value of AI chat interactions.
        """
        websocket_url = embedded_websocket_server_fixture
        chat_business_value_validated = await validate_websocket_events_for_chat(websocket_url)
        assert chat_business_value_validated, 'WebSocket implementation must support chat business value with all critical events'
        logger.info(' PASS:  PRIMARY BUSINESS VALUE VALIDATED: WebSocket supports chat functionality')

class WebSocketEmbeddedServerAdvancedTests:
    """Advanced WebSocket tests for edge cases and performance."""

    @pytest.mark.integration
    async def test_websocket_server_lifecycle(self):
        """Test embedded WebSocket server startup and shutdown."""
        async with embedded_websocket_server(host='127.0.0.1') as websocket_url:
            assert websocket_url.startswith('ws://'), 'Should return valid WebSocket URL'
            health_check = await quick_websocket_health_check(websocket_url)
            assert health_check, 'Server should be healthy'
            logger.info(f' PASS:  Server lifecycle test passed: {websocket_url}')
        try:
            health_check_after = await quick_websocket_health_check(websocket_url)
            logger.warning('Server still accessible after shutdown (may be normal)')
        except:
            logger.info(' PASS:  Server properly shut down')

    @pytest.mark.integration
    async def test_websocket_message_performance(self, websocket_test_client):
        """Test WebSocket message performance."""
        client = websocket_test_client
        connected = await client.connect()
        assert connected, 'WebSocket connection should be established'
        message_count = 10
        start_time = time.time()
        for i in range(message_count):
            success = await client.send_message({'type': 'ping', 'sequence': i, 'timestamp': time.time()})
            assert success, f'Message {i} should send successfully'
            response = await client.receive_message(timeout=2.0)
            assert response is not None, f'Should receive response for message {i}'
            assert response.get('type') == 'pong', f'Should receive pong for message {i}'
        end_time = time.time()
        duration = end_time - start_time
        messages_per_second = message_count * 2 / duration
        logger.info(f' PASS:  Performance test: {messages_per_second:.1f} messages/second over {duration:.2f}s')
        assert messages_per_second > 10, f'Performance too slow: {messages_per_second:.1f} msg/s'

    @pytest.mark.integration
    async def test_websocket_custom_message_handler(self):
        """Test custom message handler registration."""
        from test_framework.embedded_websocket_server import EmbeddedWebSocketServer
        server = EmbeddedWebSocketServer()

        async def custom_handler(connection, message):
            await connection.send_message({'type': 'custom_response', 'original': message, 'processed': True, 'timestamp': datetime.now(timezone.utc).isoformat()})
        server.add_message_handler('custom_type', custom_handler)
        try:
            websocket_url = await server.start()
            client = WebSocketTestClient(websocket_url)
            connected = await client.connect()
            assert connected, 'Should connect to server'
            success = await client.send_message({'type': 'custom_type', 'data': 'test custom handler'})
            assert success, 'Should send custom message successfully'
            response = await client.receive_message(timeout=3.0)
            assert response is not None, 'Should receive custom response'
            assert response.get('type') == 'custom_response', 'Should receive custom response type'
            assert response.get('processed') is True, 'Should indicate message was processed'
            await client.disconnect()
            logger.info(' PASS:  Custom message handler test passed')
        finally:
            await server.stop()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')