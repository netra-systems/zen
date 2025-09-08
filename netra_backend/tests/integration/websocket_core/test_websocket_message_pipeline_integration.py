"""
Integration tests for WebSocket Message Pipeline - Testing end-to-end message flow.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Reliable real-time message delivery for AI chat
- Value Impact: Ensures users receive complete AI responses without message loss
- Strategic Impact: Core infrastructure for chat business value - validates complete message pipeline

These integration tests validate the complete message pipeline from user input
through agent processing to WebSocket delivery, ensuring reliable chat functionality.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestUtility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.message_buffer import MessageBuffer
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketMessagePipelineIntegration(BaseIntegrationTest):
    """Integration tests for complete WebSocket message pipeline."""
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.fixture
    async def message_buffer(self):
        """Create message buffer for testing."""
        return MessageBuffer(max_buffer_size=100, max_age_seconds=300)
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def sample_user_context(self):
        """Create sample user execution context."""
        return {
            "user_id": "test_user_123",
            "thread_id": "thread_456",
            "session_id": "session_789",
            "subscription_tier": "enterprise"
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_message_flow_user_to_agent(self, real_services_fixture, websocket_utility, 
                                                      websocket_manager, sample_user_context):
        """Test complete message flow from user input to agent response."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create user context
        context = UserExecutionContext(
            user_id=sample_user_context["user_id"],
            thread_id=sample_user_context["thread_id"],
            session_data={"tier": "enterprise"}
        )
        UserExecutionContext.set_context(sample_user_context["user_id"], context)
        
        # Create mock WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        
        # Add connection to manager
        connection = await websocket_manager.create_connection(
            connection_id="test_conn_123",
            user_id=sample_user_context["user_id"],
            websocket=mock_websocket,
            metadata={"test": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Create user message
        user_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Analyze my cloud costs for optimization opportunities",
                "thread_id": sample_user_context["thread_id"],
                "context": {"urgent": True}
            },
            user_id=sample_user_context["user_id"],
            thread_id=sample_user_context["thread_id"]
        )
        
        # Send message through pipeline
        await websocket_manager.handle_message(
            user_id=sample_user_context["user_id"],
            websocket=mock_websocket,
            message=user_message
        )
        
        # Verify message was processed
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) > 0
        
        # Should receive acknowledgment
        ack_message = next((msg for msg in sent_messages if "message_received" in str(msg)), None)
        assert ack_message is not None
        
        # Verify database persistence
        # In real integration, would check thread/message storage
        await asyncio.sleep(0.1)  # Allow async processing
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_event_pipeline_delivery(self, real_services_fixture, websocket_utility,
                                                websocket_manager, sample_user_context):
        """Test delivery of all critical agent events through pipeline."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Setup connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="agent_event_conn",
            user_id=sample_user_context["user_id"],
            websocket=mock_websocket,
            metadata={"agent_test": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Critical agent events that must be delivered
        critical_events = [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_THINKING,
            MessageType.TOOL_EXECUTING, 
            MessageType.TOOL_COMPLETED,
            MessageType.AGENT_COMPLETED
        ]
        
        # Send each critical event through pipeline
        for event_type in critical_events:
            event_message = WebSocketMessage(
                message_type=event_type,
                payload={
                    "agent_name": "cost_optimizer",
                    "status": "processing",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": f"Event {event_type.value} for business value"
                },
                user_id=sample_user_context["user_id"],
                thread_id=sample_user_context["thread_id"]
            )
            
            await websocket_manager.send_to_user(
                user_id=sample_user_context["user_id"],
                message=event_message
            )
            
            # Small delay to ensure proper ordering
            await asyncio.sleep(0.01)
        
        # Verify all events were delivered
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) >= len(critical_events)
        
        # Verify each critical event was delivered
        delivered_event_types = []
        for msg in sent_messages:
            if hasattr(msg, 'message_type'):
                delivered_event_types.append(msg.message_type)
            elif isinstance(msg, dict) and 'type' in msg:
                delivered_event_types.append(MessageType(msg['type']))
        
        for critical_event in critical_events:
            assert critical_event in delivered_event_types, f"Critical event {critical_event} was not delivered"
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_message_buffering_during_disconnection(self, real_services_fixture, websocket_utility,
                                                         websocket_manager, message_buffer, sample_user_context):
        """Test message buffering when connection is temporarily lost."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="buffer_test_conn",
            user_id=sample_user_context["user_id"],
            websocket=mock_websocket
        )
        await websocket_manager.add_connection(connection)
        
        # Simulate connection loss
        await websocket_manager.remove_connection(connection.connection_id)
        
        # Send messages while disconnected (should be buffered)
        buffered_messages = []
        for i in range(3):
            message = WebSocketMessage(
                message_type=MessageType.AGENT_THINKING,
                payload={
                    "status": f"Processing step {i+1}",
                    "progress": (i+1) * 33
                },
                user_id=sample_user_context["user_id"],
                thread_id=sample_user_context["thread_id"]
            )
            buffered_messages.append(message)
            
            # Buffer message (in real system, this would be automatic)
            await message_buffer.buffer_message(sample_user_context["user_id"], message)
        
        # Verify messages are buffered
        retrieved_messages = await message_buffer.get_buffered_messages(sample_user_context["user_id"])
        assert len(retrieved_messages) == 3
        
        # Reconnect
        new_websocket = await websocket_utility.create_mock_websocket()
        new_connection = await websocket_manager.create_connection(
            connection_id="buffer_test_conn_new", 
            user_id=sample_user_context["user_id"],
            websocket=new_websocket
        )
        await websocket_manager.add_connection(new_connection)
        
        # Simulate buffer restoration (would happen automatically in real system)
        for buffered_msg in retrieved_messages:
            await websocket_manager.send_to_user(
                user_id=sample_user_context["user_id"],
                message=buffered_msg.message
            )
        
        # Verify messages were delivered after reconnection
        sent_messages = new_websocket.sent_messages
        assert len(sent_messages) >= 3
        
        # Cleanup
        await websocket_manager.remove_connection(new_connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_message_isolation(self, real_services_fixture, websocket_utility,
                                               websocket_manager):
        """Test message isolation between multiple users."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create multiple user connections
        users = [
            {"user_id": "user_1", "connection_id": "conn_1"},
            {"user_id": "user_2", "connection_id": "conn_2"},
            {"user_id": "user_3", "connection_id": "conn_3"}
        ]
        
        connections = {}
        websockets = {}
        
        for user in users:
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=user["connection_id"],
                user_id=user["user_id"],
                websocket=websocket
            )
            await websocket_manager.add_connection(connection)
            
            connections[user["user_id"]] = connection
            websockets[user["user_id"]] = websocket
        
        # Send targeted messages to specific users
        for i, user in enumerate(users):
            message = WebSocketMessage(
                message_type=MessageType.AGENT_COMPLETED,
                payload={
                    "result": f"Personalized result for {user['user_id']}",
                    "user_specific_data": f"data_{i}",
                    "confidential": True
                },
                user_id=user["user_id"],
                thread_id=f"thread_{user['user_id']}"
            )
            
            await websocket_manager.send_to_user(
                user_id=user["user_id"],
                message=message
            )
        
        # Verify message isolation - each user only receives their messages
        for user in users:
            user_websocket = websockets[user["user_id"]]
            sent_messages = user_websocket.sent_messages
            
            # Should have received at least one message
            assert len(sent_messages) >= 1
            
            # Verify received messages are for correct user
            for msg in sent_messages:
                if hasattr(msg, 'user_id'):
                    assert msg.user_id == user["user_id"]
                elif isinstance(msg, dict) and 'user_id' in msg:
                    assert msg['user_id'] == user["user_id"]
                # Message should contain user-specific content
                msg_str = str(msg)
                assert user["user_id"] in msg_str
        
        # Cleanup
        for connection in connections.values():
            await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_ordering_preservation(self, real_services_fixture, websocket_utility,
                                                websocket_manager, sample_user_context):
        """Test preservation of message ordering through pipeline."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Setup connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="ordering_test_conn",
            user_id=sample_user_context["user_id"],
            websocket=mock_websocket
        )
        await websocket_manager.add_connection(connection)
        
        # Send sequence of ordered messages
        ordered_messages = []
        for i in range(10):
            message = WebSocketMessage(
                message_type=MessageType.AGENT_THINKING,
                payload={
                    "sequence": i,
                    "content": f"Step {i} of analysis",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                user_id=sample_user_context["user_id"],
                thread_id=sample_user_context["thread_id"]
            )
            ordered_messages.append(message)
            
            await websocket_manager.send_to_user(
                user_id=sample_user_context["user_id"],
                message=message
            )
            
            # Small delay to ensure ordering
            await asyncio.sleep(0.005)
        
        # Verify ordering preserved
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) >= len(ordered_messages)
        
        # Extract sequence numbers from sent messages
        received_sequences = []
        for msg in sent_messages:
            if hasattr(msg, 'payload') and 'sequence' in msg.payload:
                received_sequences.append(msg.payload['sequence'])
            elif isinstance(msg, dict) and 'payload' in msg and 'sequence' in msg['payload']:
                received_sequences.append(msg['payload']['sequence'])
        
        # Verify sequences are in order
        assert len(received_sequences) == len(ordered_messages)
        assert received_sequences == sorted(received_sequences)
        assert received_sequences == list(range(10))
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_large_message_handling(self, real_services_fixture, websocket_utility,
                                         websocket_manager, sample_user_context):
        """Test handling of large messages through pipeline."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Setup connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="large_msg_conn",
            user_id=sample_user_context["user_id"], 
            websocket=mock_websocket
        )
        await websocket_manager.add_connection(connection)
        
        # Create large message payload (simulating comprehensive agent result)
        large_payload = {
            "analysis_result": {
                "detailed_report": "This is a comprehensive analysis report. " * 1000,  # Large text
                "data_points": [{"metric": f"metric_{i}", "value": i * 1.5} for i in range(500)],  # Large array
                "recommendations": [f"Recommendation {i}: Optimize resource usage in area {i}" for i in range(100)]
            },
            "metadata": {
                "processing_time_seconds": 45.7,
                "confidence_score": 0.95,
                "cost_impact_analysis": "Detailed cost impact analysis text. " * 200
            }
        }
        
        large_message = WebSocketMessage(
            message_type=MessageType.AGENT_COMPLETED,
            payload=large_payload,
            user_id=sample_user_context["user_id"],
            thread_id=sample_user_context["thread_id"]
        )
        
        # Send large message
        await websocket_manager.send_to_user(
            user_id=sample_user_context["user_id"],
            message=large_message
        )
        
        # Allow processing time
        await asyncio.sleep(0.1)
        
        # Verify large message was delivered successfully
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) >= 1
        
        # Find the large message in sent messages
        large_msg_delivered = None
        for msg in sent_messages:
            if hasattr(msg, 'payload') and 'analysis_result' in str(msg.payload):
                large_msg_delivered = msg
                break
            elif isinstance(msg, dict) and 'analysis_result' in str(msg):
                large_msg_delivered = msg
                break
        
        assert large_msg_delivered is not None
        
        # Verify content integrity
        if hasattr(large_msg_delivered, 'payload'):
            payload = large_msg_delivered.payload
        else:
            payload = large_msg_delivered.get('payload', {})
        
        assert 'analysis_result' in payload
        assert 'detailed_report' in payload['analysis_result']
        assert len(payload['analysis_result']['data_points']) == 500
        assert len(payload['analysis_result']['recommendations']) == 100
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_propagation(self, real_services_fixture, websocket_utility,
                                           websocket_manager, sample_user_context):
        """Test propagation of error messages through pipeline."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Setup connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="error_test_conn",
            user_id=sample_user_context["user_id"],
            websocket=mock_websocket
        )
        await websocket_manager.add_connection(connection)
        
        # Send error message
        error_message = WebSocketMessage(
            message_type=MessageType.ERROR,
            payload={
                "error_type": "agent_execution_failed",
                "error_code": "E001",
                "message": "Agent encountered an error during cost analysis",
                "details": {
                    "original_request": "Analyze my cloud costs",
                    "failure_point": "data_retrieval",
                    "retry_suggested": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            user_id=sample_user_context["user_id"],
            thread_id=sample_user_context["thread_id"]
        )
        
        # Send error through pipeline
        await websocket_manager.send_to_user(
            user_id=sample_user_context["user_id"],
            message=error_message
        )
        
        # Verify error message was delivered
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) >= 1
        
        # Find error message
        error_msg_delivered = None
        for msg in sent_messages:
            if hasattr(msg, 'message_type') and msg.message_type == MessageType.ERROR:
                error_msg_delivered = msg
                break
            elif isinstance(msg, dict) and msg.get('type') == 'error':
                error_msg_delivered = msg
                break
        
        assert error_msg_delivered is not None
        
        # Verify error details preserved
        if hasattr(error_msg_delivered, 'payload'):
            payload = error_msg_delivered.payload
        else:
            payload = error_msg_delivered.get('payload', {})
        
        assert payload['error_type'] == "agent_execution_failed"
        assert payload['error_code'] == "E001" 
        assert 'details' in payload
        assert payload['details']['retry_suggested'] is True
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)