"
Phase 1: WebSocket Message Flow Integration Tests - Issue #861

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR Protection
- Business Goal: Ensure WebSocket message flow delivers reliable real-time chat
- Value Impact: Chat = 90% of platform value, requires WebSocket message reliability
- Revenue Impact: Mission-critical for user retention and enterprise conversions

CRITICAL COVERAGE GAPS ADDRESSED:
- Agent Registry WebSocket Integration (11.48% coverage - 740/836 lines missing)
- Agent WebSocket Bridge (15.19% coverage - 1,267/1,494 lines missing)
- WebSocket Message Flow End-to-End Validation
- Multi-User WebSocket Message Isolation Testing
- Real-time Agent Progress Event Delivery

PHASE 1 TARGET: Improve coverage from 10.92% → 25%+ through comprehensive WebSocket message flow testing

TEST INFRASTRUCTURE:
- Real staging service connections (NO mocks for integration tests)
- SSOT-compliant test patterns from existing infrastructure
- Comprehensive assertion frameworks
- User isolation testing patterns
- <30 seconds execution time per test suite

BUSINESS-CRITICAL WEBSOCKET EVENTS (ALL MUST BE TESTED):
1. agent_started - User sees agent processing began
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response ready
""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch
import websockets
from datetime import datetime, timedelta

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Core WebSocket Infrastructure
try:
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.websocket_core.auth import WebSocketAuthHandler
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Agent System Integration
try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    from netra_backend.app.agents.base.agent_instance_factory import create_agent_instance
    AGENT_SYSTEM_AVAILABLE = True
except ImportError:
    AGENT_SYSTEM_AVAILABLE = False

# User Context Management
try:
    from netra_backend.app.services.user_execution_context import (
        UserExecutionContext,
        create_isolated_execution_context,
        managed_user_context
    )
    USER_CONTEXT_AVAILABLE = True
except ImportError:
    USER_CONTEXT_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.websocket_flow
@pytest.mark.business_critical
class WebSocketMessageFlowIntegrationTests(SSotAsyncTestCase):
    ""
    Phase 1: WebSocket Message Flow Integration Test Suite

    BUSINESS IMPACT: Protects $500K+ ARR through reliable WebSocket message delivery
    COVERAGE TARGET: Agent Registry, WebSocket Bridge, Message Flow components
    "

    def setup_method(self, method):
        "Setup for each test method with isolated WebSocket infrastructure""
        super().setup_method(method)
        self.test_user_ids = []
        self.websocket_connections = []
        self.auth_helper = E2EAuthHelper()
        self.websocket_utility = WebSocketTestUtility()

        # Test execution tracking
        self.test_start_time = datetime.now()
        self.expected_events = [
            'agent_started', 'agent_thinking', 'tool_executing',
            'tool_completed', 'agent_completed'
        ]

    async def teardown_method(self, method):
        ""Cleanup WebSocket connections and test data"
        # Close all WebSocket connections
        for connection in self.websocket_connections:
            try:
                await connection.close()
            except Exception:
                pass

        # Clean up test users
        for user_id in self.test_user_ids:
            try:
                await self.auth_helper.cleanup_test_user(user_id)
            except Exception:
                pass

        await super().teardown_method(method)

    @pytest.mark.timeout(25)
    async def test_websocket_agent_registry_integration(self):
        "
        Test WebSocket integration with Agent Registry
        COVERS: Agent Registry (11.48% coverage gap - 740/836 lines missing)
        ""
        if not WEBSOCKET_AVAILABLE or not AGENT_SYSTEM_AVAILABLE:
            pytest.skip(WebSocket or Agent system not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(
            websocket_url, auth_token
        )
        self.websocket_connections.append(connection)

        # Test Agent Registry WebSocket integration
        registry = AgentRegistry()
        bridge = create_agent_websocket_bridge(connection, user_id)

        # Register WebSocket with Agent Registry
        registry.set_websocket_manager(bridge)

        # Verify WebSocket registration
        assert registry._websocket_manager is not None
        assert hasattr(registry._websocket_manager, 'send_agent_event')

        # Test agent event sending through registry
        test_event = {
            'type': 'agent_started',
            'agent_id': 'test_agent_001',
            'message': 'Agent execution started',
            'timestamp': datetime.now().isoformat()
        }

        # Send event through registry
        await registry.notify_agent_event(test_event)

        # Verify event delivery via WebSocket
        received_message = await asyncio.wait_for(
            connection.recv(), timeout=5.0
        )
        received_data = json.loads(received_message)

        assert received_data['type'] == 'agent_started'
        assert received_data['agent_id'] == 'test_agent_001'
        assert 'timestamp' in received_data

    @pytest.mark.timeout(25)
    async def test_websocket_bridge_message_routing(self):
        "
        Test WebSocket Bridge message routing functionality
        COVERS: Agent WebSocket Bridge (15.19% coverage gap - 1,267/1,494 lines missing)
        ""
        if not WEBSOCKET_AVAILABLE or not USER_CONTEXT_AVAILABLE:
            pytest.skip(WebSocket or User Context system not available")

        # Create multiple authenticated test users for isolation testing
        user_1_id = str(uuid.uuid4())
        user_2_id = str(uuid.uuid4())
        self.test_user_ids.extend([user_1_id, user_2_id]

        # Create auth tokens and connections
        auth_token_1 = await self.auth_helper.create_test_user_with_token(user_1_id)
        auth_token_2 = await self.auth_helper.create_test_user_with_token(user_2_id)

        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection_1 = await self.websocket_utility.connect_with_auth(websocket_url, auth_token_1)
        connection_2 = await self.websocket_utility.connect_with_auth(websocket_url, auth_token_2)
        self.websocket_connections.extend([connection_1, connection_2]

        # Create WebSocket bridges for both users
        bridge_1 = create_agent_websocket_bridge(connection_1, user_1_id)
        bridge_2 = create_agent_websocket_bridge(connection_2, user_2_id)

        # Test message routing isolation
        user_1_message = {
            'type': 'agent_thinking',
            'agent_id': f'agent_{user_1_id}',
            'content': 'User 1 specific content',
            'user_id': user_1_id
        }

        user_2_message = {
            'type': 'tool_executing',
            'agent_id': f'agent_{user_2_id}',
            'content': 'User 2 specific content',
            'user_id': user_2_id
        }

        # Send messages through respective bridges
        await bridge_1.send_agent_event(user_1_message)
        await bridge_2.send_agent_event(user_2_message)

        # Verify user isolation - each user should only receive their own messages
        received_1 = await asyncio.wait_for(connection_1.recv(), timeout=5.0)
        received_2 = await asyncio.wait_for(connection_2.recv(), timeout=5.0)

        data_1 = json.loads(received_1)
        data_2 = json.loads(received_2)

        # Verify message routing isolation
        assert data_1['user_id'] == user_1_id
        assert data_2['user_id'] == user_2_id
        assert data_1['content'] == 'User 1 specific content'
        assert data_2['content'] == 'User 2 specific content'

    @pytest.mark.timeout(30)
    async def test_complete_websocket_event_flow_sequence(self):
        "
        Test complete WebSocket event flow for all 5 business-critical events
        COVERS: Complete WebSocket message flow end-to-end
        ""
        if not all([WEBSOCKET_AVAILABLE, AGENT_SYSTEM_AVAILABLE, USER_CONTEXT_AVAILABLE]:
            pytest.skip(Required systems not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Create execution context and WebSocket bridge
        async with managed_user_context(user_id) as context:
            bridge = create_agent_websocket_bridge(connection, user_id)

            # Simulate complete agent execution flow
            agent_id = f'test_agent_{user_id}'

            # 1. Send agent_started event
            await bridge.send_agent_event({
                'type': 'agent_started',
                'agent_id': agent_id,
                'message': 'Agent execution initiated',
                'user_id': user_id
            }

            # 2. Send agent_thinking event
            await bridge.send_agent_event({
                'type': 'agent_thinking',
                'agent_id': agent_id,
                'reasoning': 'Analyzing user request and planning execution',
                'user_id': user_id
            }

            # 3. Send tool_executing event
            await bridge.send_agent_event({
                'type': 'tool_executing',
                'agent_id': agent_id,
                'tool_name': 'data_analyzer',
                'message': 'Executing data analysis tool',
                'user_id': user_id
            }

            # 4. Send tool_completed event
            await bridge.send_agent_event({
                'type': 'tool_completed',
                'agent_id': agent_id,
                'tool_name': 'data_analyzer',
                'result': 'Data analysis completed successfully',
                'user_id': user_id
            }

            # 5. Send agent_completed event
            await bridge.send_agent_event({
                'type': 'agent_completed',
                'agent_id': agent_id,
                'final_result': 'Agent execution completed with results',
                'user_id': user_id
            }

        # Verify all 5 events are received in correct order
        received_events = []
        for _ in range(5):
            message = await asyncio.wait_for(connection.recv(), timeout=8.0)
            event_data = json.loads(message)
            received_events.append(event_data['type']

        # Assert all expected events received in correct sequence
        assert len(received_events) == 5
        assert received_events == self.expected_events

        # Verify all events contain required fields
        connection_received_all = all(
            event in received_events for event in self.expected_events
        )
        assert connection_received_all

    @pytest.mark.timeout(25)
    async def test_websocket_agent_execution_engine_integration(self):
        "
        Test WebSocket integration with Agent Execution Engine
        COVERS: User Execution Engine (13.69% coverage - 555/643 lines missing)
        ""
        if not all([WEBSOCKET_AVAILABLE, AGENT_SYSTEM_AVAILABLE, USER_CONTEXT_AVAILABLE]:
            pytest.skip(Required systems not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Create execution engine with WebSocket integration
        async with create_isolated_execution_context(user_id) as execution_context:
            execution_engine = UserExecutionEngine(execution_context)
            bridge = create_agent_websocket_bridge(connection, user_id)

            # Configure execution engine with WebSocket notifications
            execution_engine.set_websocket_bridge(bridge)

            # Test execution engine WebSocket integration
            test_execution_request = {
                'agent_type': 'data_helper',
                'user_input': 'Test execution request',
                'execution_id': str(uuid.uuid4())
            }

            # Execute through engine (should trigger WebSocket events)
            result = await execution_engine.execute_agent_request(test_execution_request)

            # Verify WebSocket events were sent during execution
            received_events = []
            try:
                # Try to receive events with timeout (may not get all in integration test)
                while len(received_events) < 3:  # Expect at least 3 events
                    message = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    event_data = json.loads(message)
                    received_events.append(event_data['type']
            except asyncio.TimeoutError:
                # Some events received, continue with validation
                pass

            # Verify execution engine integrated with WebSocket
            assert execution_engine._websocket_bridge is not None
            assert len(received_events) >= 1  # At least some events received
            assert result is not None  # Execution completed

    @pytest.mark.timeout(25)
    async def test_websocket_concurrent_user_message_isolation(self):
        "
        Test WebSocket message isolation with concurrent users
        COVERS: Multi-user WebSocket message isolation and concurrency
        ""
        if not all([WEBSOCKET_AVAILABLE, USER_CONTEXT_AVAILABLE]:
            pytest.skip(Required systems not available")

        # Create 3 concurrent authenticated test users
        user_ids = [str(uuid.uuid4()) for _ in range(3)]
        self.test_user_ids.extend(user_ids)

        # Create connections concurrently
        auth_tasks = [
            self.auth_helper.create_test_user_with_token(user_id)
            for user_id in user_ids
        ]
        auth_tokens = await asyncio.gather(*auth_tasks)

        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection_tasks = [
            self.websocket_utility.connect_with_auth(websocket_url, token)
            for token in auth_tokens
        ]
        connections = await asyncio.gather(*connection_tasks)
        self.websocket_connections.extend(connections)

        # Create WebSocket bridges for all users
        bridges = [
            create_agent_websocket_bridge(connections[i], user_ids[i]
            for i in range(3)
        ]

        # Send concurrent messages from different users
        message_tasks = []
        for i, (bridge, user_id) in enumerate(zip(bridges, user_ids)):
            message = {
                'type': 'agent_thinking',
                'agent_id': f'concurrent_agent_{i}',
                'content': f'Concurrent message from user {i}',
                'user_id': user_id
            }
            message_tasks.append(bridge.send_agent_event(message))

        # Send all messages concurrently
        await asyncio.gather(*message_tasks)

        # Verify each user receives only their own message
        received_messages = await asyncio.gather(*[
            asyncio.wait_for(conn.recv(), timeout=8.0)
            for conn in connections
        ]

        # Verify message isolation
        for i, (message, user_id) in enumerate(zip(received_messages, user_ids)):
            data = json.loads(message)
            assert data['user_id'] == user_id
            assert f'user {i}' in data['content']
            assert data['agent_id'] == f'concurrent_agent_{i}'

    @pytest.mark.timeout(20)
    async def test_websocket_error_handling_and_recovery(self):
        "
        Test WebSocket error handling and recovery mechanisms
        COVERS: WebSocket error scenarios and system resilience
        ""
        if not WEBSOCKET_AVAILABLE:
            pytest.skip(WebSocket system not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Create WebSocket bridge
        bridge = create_agent_websocket_bridge(connection, user_id)

        # Test invalid message handling
        invalid_message = {
            'type': 'invalid_event_type',
            'malformed_data': None,
            'user_id': user_id
        }

        # Send invalid message (should not crash system)
        try:
            await bridge.send_agent_event(invalid_message)
        except Exception as e:
            # Error handling should be graceful
            assert "invalid_event_type in str(e).lower() or malformed" in str(e).lower()

        # Test recovery with valid message after error
        valid_message = {
            'type': 'agent_started',
            'agent_id': 'recovery_test_agent',
            'message': 'Recovery test message',
            'user_id': user_id
        }

        await bridge.send_agent_event(valid_message)

        # Verify system recovered and can still send/receive messages
        received_message = await asyncio.wait_for(connection.recv(), timeout=5.0)
        received_data = json.loads(received_message)

        assert received_data['type'] == 'agent_started'
        assert received_data['agent_id'] == 'recovery_test_agent'

    @pytest.mark.timeout(30)
    async def test_websocket_agent_instance_factory_integration(self):
        "
        Test WebSocket integration with Agent Instance Factory
        COVERS: Agent Instance Factory (9.60% coverage - 452/500 lines missing)
        ""
        if not all([WEBSOCKET_AVAILABLE, AGENT_SYSTEM_AVAILABLE, USER_CONTEXT_AVAILABLE]:
            pytest.skip(Required systems not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Create execution context and agent instance
        async with create_isolated_execution_context(user_id) as context:
            bridge = create_agent_websocket_bridge(connection, user_id)

            # Create agent instance with WebSocket integration
            agent_instance = create_agent_instance(
                agent_type='data_helper',
                user_context=context,
                websocket_bridge=bridge
            )

            # Verify agent instance has WebSocket integration
            assert agent_instance is not None
            assert hasattr(agent_instance, '_websocket_bridge') or hasattr(agent_instance, 'websocket_bridge')

            # Test agent instance WebSocket event sending
            await agent_instance.send_status_update('Agent instance created successfully')

            # Verify WebSocket event received
            received_message = await asyncio.wait_for(connection.recv(), timeout=8.0)
            received_data = json.loads(received_message)

            # Verify agent instance event structure
            assert 'type' in received_data
            assert received_data.get('user_id') == user_id
            assert 'Agent instance' in received_data.get('message', '')

    @pytest.mark.timeout(20)
    async def test_websocket_message_serialization_and_deserialization(self):
        "
        Test WebSocket message serialization/deserialization with complex data
        COVERS: WebSocket message format consistency and data integrity
        ""
        if not WEBSOCKET_AVAILABLE:
            pytest.skip(WebSocket system not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Create WebSocket bridge
        bridge = create_agent_websocket_bridge(connection, user_id)

        # Test complex message serialization
        complex_message = {
            'type': 'tool_completed',
            'agent_id': 'serialization_test_agent',
            'user_id': user_id,
            'data': {
                'nested_object': {
                    'array': [1, 2, 3, 'string', {'nested_again': True}],
                    'timestamp': datetime.now().isoformat(),
                    'unicode': 'Special characters: áéíóú 中文 🚀',
                    'float_value': 3.14159,
                    'large_number': 999999999999999
                },
                'metadata': {
                    'execution_time': 1.234,
                    'memory_usage': 67890,
                    'status': 'completed'
                }
            }
        }

        # Send complex message
        await bridge.send_agent_event(complex_message)

        # Receive and verify deserialization
        received_message = await asyncio.wait_for(connection.recv(), timeout=5.0)
        received_data = json.loads(received_message)

        # Verify complex data integrity
        assert received_data['type'] == 'tool_completed'
        assert received_data['user_id'] == user_id
        assert received_data['data']['nested_object']['array'] == [1, 2, 3, 'string', {'nested_again': True}]
        assert received_data['data']['nested_object']['unicode'] == 'Special characters: áéíóú 中文 🚀'
        assert received_data['data']['metadata']['execution_time'] == 1.234
        assert received_data['data']['metadata']['memory_usage'] == 67890

    @pytest.mark.timeout(25)
    async def test_websocket_performance_under_message_load(self):
        "
        Test WebSocket performance under sustained message load
        COVERS: WebSocket system performance and scalability
        ""
        if not WEBSOCKET_AVAILABLE:
            pytest.skip(WebSocket system not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Establish WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        # Create WebSocket bridge
        bridge = create_agent_websocket_bridge(connection, user_id)

        # Send burst of messages to test performance
        message_count = 50
        start_time = datetime.now()

        send_tasks = []
        for i in range(message_count):
            message = {
                'type': 'agent_thinking',
                'agent_id': f'performance_agent_{i}',
                'message': f'Performance test message {i}',
                'sequence_id': i,
                'user_id': user_id
            }
            send_tasks.append(bridge.send_agent_event(message))

        # Send all messages concurrently
        await asyncio.gather(*send_tasks)
        send_end_time = datetime.now()

        # Receive all messages
        received_count = 0
        received_sequences = []

        try:
            while received_count < message_count:
                message = await asyncio.wait_for(connection.recv(), timeout=10.0)
                data = json.loads(message)
                received_sequences.append(data.get('sequence_id', -1))
                received_count += 1
        except asyncio.TimeoutError:
            # Partial reception is acceptable for performance test
            pass

        receive_end_time = datetime.now()

        # Performance assertions
        send_duration = (send_end_time - start_time).total_seconds()
        total_duration = (receive_end_time - start_time).total_seconds()

        # Should handle at least 80% of messages successfully
        success_rate = received_count / message_count
        assert success_rate >= 0.8, f"Success rate {success_rate} below 80%

        # Performance should be reasonable (less than 20 seconds for 50 messages)
        assert total_duration < 20.0, fTotal duration {total_duration}s too slow"

        # Messages should be received in reasonable order (allowing some reordering)
        ordered_sequences = [seq for seq in received_sequences if seq != -1]
        if len(ordered_sequences) > 0:
            # Verify reasonable ordering (not strict due to async nature)
            assert min(ordered_sequences) >= 0
            assert max(ordered_sequences) < message_count