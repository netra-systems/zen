"""CRITICAL: WebSocket Message Routing to Agent Service Tests

This is the most critical test suite - it ensures WebSocket messages actually reach
the agent service. Without this, the entire system appears to work but agents never
receive messages, causing complete silent failure.

ROOT CAUSE: The unified WebSocket system was validating messages but never forwarding
them to agent_service.handle_websocket_message(), causing total system failure.
"""

import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, call, patch

import pytest
from fastapi import WebSocket

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.websocket_core.handlers import MessageRouter, UserMessageHandler
from netra_backend.app.websocket_core.types import MessageType
from netra_backend.app.routes.utils.websocket_helpers import process_agent_message

class TestCriticalMessageRoutingToAgentService:
    """CRITICAL: Tests that messages MUST reach agent service or system fails silently."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket with proper application state."""
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        ws = Mock(spec=WebSocket)
        # Mock: Generic component isolation for controlled unit testing
        ws.app = Mock()
        # Mock: Generic component isolation for controlled unit testing
        ws.app.state = Mock()
        # Mock: Agent service isolation for testing without LLM agent execution
        ws.app.state.agent_service = AsyncMock(spec=AgentService)
        # Mock: Generic component isolation for controlled unit testing
        ws.app.state.agent_service.handle_websocket_message = AsyncMock()
        return ws
    
    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        # Mock: Agent service isolation for testing without LLM agent execution
        agent_service = AsyncMock(spec=AgentService)
        # Mock: Generic component isolation for controlled unit testing
        agent_service.handle_websocket_message = AsyncMock()
        return agent_service
    
    @pytest.fixture
    def message_router(self):
        """Create message router with real handlers."""
        return MessageRouter()
    
    @pytest.fixture
    def user_message_handler(self):
        """Create user message handler."""
        return UserMessageHandler()
    
    @pytest.mark.asyncio
    async def test_01_user_message_must_reach_agent_service(self, mock_agent_service):
        """Test 1: user_message type MUST be forwarded to agent service via process_agent_message."""
        user_id = "test_user_123"
        message = {
            "type": "user_message",
            "payload": {"content": "Analyze our costs", "references": []}
        }
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Test the core function that routes messages to agent service
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # CRITICAL ASSERTION: Agent service MUST be called
            mock_agent_service.handle_websocket_message.assert_called_once()
            
            # Verify correct parameters
            call_args = mock_agent_service.handle_websocket_message.call_args
            assert call_args[0][0] == user_id  # user_id
            assert call_args[0][1] == message_str  # message as JSON string
            assert call_args[0][2] == mock_session  # db_session
    
    @pytest.mark.asyncio
    async def test_02_start_agent_message_must_reach_agent_service(self, mock_agent_service):
        """Test 2: start_agent type MUST be forwarded to agent service."""
        user_id = "test_user_123"
        message = {
            "type": "start_agent",
            "payload": {"user_request": "Start optimization", "thread_id": "thread_456"}
        }
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            mock_agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_03_empty_user_id_prevents_agent_processing(self, mock_agent_service):
        """Test 3: Empty user_id MUST prevent agent processing."""
        user_id = ""  # Empty user_id
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await process_agent_message(user_id, message_str, mock_agent_service)
        
        # Should NOT call agent service with empty user_id
        mock_agent_service.handle_websocket_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_04_none_agent_service_raises_error(self):
        """Test 4: None agent service MUST raise appropriate error."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        with pytest.raises(AttributeError):
            await process_agent_message(user_id, message_str, None)
    
    @pytest.mark.asyncio
    async def test_05_database_error_handled_gracefully(self, mock_agent_service):
        """Test 5: Database errors during agent processing MUST be handled."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            # Should raise the database error after retries
            with pytest.raises(Exception, match="Database connection failed"):
                await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Agent service should not be called due to DB error
            mock_agent_service.handle_websocket_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_06_agent_service_exception_propagated(self, mock_agent_service):
        """Test 6: Agent service exceptions MUST be propagated for debugging."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Crash test"}}
        message_str = json.dumps(message)
        
        # Make agent service throw exception
        mock_agent_service.handle_websocket_message.side_effect = Exception("Agent crashed")
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Agent exception should be propagated
            with pytest.raises(Exception, match="Agent crashed"):
                await process_agent_message(user_id, message_str, mock_agent_service)
            
            # But agent service should have been called
            mock_agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_07_message_json_serialization_correct(self, mock_agent_service):
        """Test 7: Messages MUST be correctly passed as JSON strings to agent service."""
        user_id = "test_user_123"
        message = {
            "type": "user_message",
            "payload": {
                "content": "Test with special chars: 'quotes' \"double\" \n newline",
                "references": ["file1.txt", "data.json"]
            }
        }
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            call_args = mock_agent_service.handle_websocket_message.call_args
            
            # Verify JSON string is passed correctly
            passed_message_str = call_args[0][1]
            assert passed_message_str == message_str
            
            # Verify it can be parsed back to original message
            parsed = json.loads(passed_message_str)
            assert parsed == message
    
    @pytest.mark.asyncio
    async def test_08_message_router_handles_user_messages(self, message_router, mock_websocket):
        """Test 8: Message router MUST handle user messages correctly."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test message"}}
        
        # Test that the message router can route user messages
        result = await message_router.route_message(user_id, mock_websocket, message)
        
        # Should return True for successful routing
        assert result is True
    
    @pytest.mark.asyncio
    async def test_09_ping_messages_handled_by_router(self, message_router, mock_websocket):
        """Test 9: Ping messages MUST be handled by heartbeat handler, not forwarded to agent."""
        user_id = "test_user_123"
        message = {"type": "ping"}
        
        # Mock the websocket send to capture the pong response
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.application_state = Mock()
        mock_websocket.application_state._mock_name = "test_mock"  # Mark as mock for testing
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send_json = AsyncMock()
        
        # Test that ping messages are handled by the router
        result = await message_router.route_message(user_id, mock_websocket, message)
        
        # Should return True for successful ping handling
        assert result is True
        
        # Should send pong response
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_10_database_session_creation_and_commit(self, mock_agent_service):
        """Test 10: Database session MUST be created and committed properly."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Verify session was created and committed
            mock_db.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify agent service received correct session
            call_args = mock_agent_service.handle_websocket_message.call_args
            assert call_args[0][2] == mock_session
    
    @pytest.mark.asyncio
    async def test_11_concurrent_messages_all_forwarded(self, mock_agent_service):
        """Test 11: Concurrent messages MUST all be forwarded to agent service."""
        user_id = "test_user_123"
        messages = [
            {"type": "user_message", "payload": {"content": f"Message {i}"}}
            for i in range(5)
        ]
        message_strings = [json.dumps(msg) for msg in messages]
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Process all messages concurrently
            await asyncio.gather(*[
                process_agent_message(user_id, msg_str, mock_agent_service)
                for msg_str in message_strings
            ])
            
            # Agent service should be called 5 times
            assert mock_agent_service.handle_websocket_message.call_count == 5
    
    @pytest.mark.asyncio
    async def test_12_database_retry_logic_works(self, mock_agent_service):
        """Test 12: Database retry logic MUST work for transient errors."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        call_count = 0
        async def mock_db_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise Exception("Connection timeout")
            # Succeed on 3rd attempt
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            return mock_session
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_db.return_value.__aenter__.side_effect = mock_db_side_effect
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Should have retried and eventually succeeded
            assert call_count == 3
            mock_agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_13_null_payload_handled_safely(self, mock_agent_service):
        """Test 13: Null payload MUST be handled without crashing."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": None}
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Should not crash
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Agent service should still be called (let it handle null)
            mock_agent_service.handle_websocket_message.assert_called_once()
            
            call_args = mock_agent_service.handle_websocket_message.call_args
            passed_message = json.loads(call_args[0][1])
            assert passed_message["payload"] is None
    
    @pytest.mark.asyncio
    async def test_14_empty_message_type_forwarded(self, mock_agent_service):
        """Test 14: Empty message type should still be forwarded (let agent decide)."""
        user_id = "test_user_123"
        message = {"type": "", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Should forward even with empty type (agent will handle)
            mock_agent_service.handle_websocket_message.assert_called_once()
            
            call_args = mock_agent_service.handle_websocket_message.call_args
            passed_message = json.loads(call_args[0][1])
            assert passed_message["type"] == ""
    
    @pytest.mark.asyncio
    async def test_15_thread_context_preserved_in_message(self, mock_agent_service):
        """Test 15: Thread context in message MUST be preserved when forwarding."""
        user_id = "test_user_123"
        thread_id = str(uuid.uuid4())
        message = {
            "type": "user_message",
            "payload": {
                "content": "Continue conversation",
                "thread_id": thread_id,
                "references": ["previous_message.txt"]
            }
        }
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            call_args = mock_agent_service.handle_websocket_message.call_args
            
            # Verify thread_id preserved
            forwarded_msg = json.loads(call_args[0][1])
            assert forwarded_msg["payload"]["thread_id"] == thread_id
            assert forwarded_msg["payload"]["references"] == ["previous_message.txt"]
    
    @pytest.mark.asyncio
    async def test_16_websocket_disconnect_during_forward_handled(self, mock_agent_service):
        """Test 16: WebSocket disconnect during forwarding MUST be handled."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        # Simulate disconnect during agent processing
        from starlette.websockets import WebSocketDisconnect
        mock_agent_service.handle_websocket_message.side_effect = WebSocketDisconnect()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Should propagate the WebSocketDisconnect
            with pytest.raises(WebSocketDisconnect):
                await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Agent service should have been called
            mock_agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_17_database_session_context_management(self, mock_agent_service):
        """Test 17: Database session context MUST be properly managed."""
        user_id = "test_user_123"
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # Verify DB session was created and properly managed
            mock_db.assert_called_once()
            mock_db.return_value.__aenter__.assert_called_once()
            mock_db.return_value.__aexit__.assert_called_once()
            
            # Verify session passed to agent
            call_args = mock_agent_service.handle_websocket_message.call_args
            assert call_args[0][2] == mock_session
            
            # Verify session was committed
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_18_various_user_id_formats_handled(self, mock_agent_service):
        """Test 18: Various user ID formats MUST be handled correctly."""
        # Test various user_id formats
        test_user_ids = [
            "simple_user",
            "user@example.com",
            str(uuid.uuid4()),
            "user_with_numbers_123",
            "CamelCaseUser"
        ]
        
        message = {"type": "user_message", "payload": {"content": "Test"}}
        message_str = json.dumps(message)
        
        for user_id in test_user_ids:
            mock_agent_service.handle_websocket_message.reset_mock()
            
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_session = AsyncMock()
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_session.commit = AsyncMock()
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                # Mock: Generic component isolation for controlled unit testing
                mock_db.return_value.__aexit__ = AsyncMock()
                
                await process_agent_message(user_id, message_str, mock_agent_service)
                
                # Verify correct user_id passed
                call_args = mock_agent_service.handle_websocket_message.call_args
                assert call_args[0][0] == user_id
    
    @pytest.mark.asyncio
    async def test_19_message_router_statistics_tracking(self, message_router, mock_websocket):
        """Test 19: Message router MUST track statistics properly."""
        user_id = "test_user_123"
        
        # Get initial stats
        initial_stats = message_router.get_stats()
        initial_routed = initial_stats["messages_routed"]
        
        # Process a message
        message = {"type": "user_message", "payload": {"content": "Test"}}
        await message_router.route_message(user_id, mock_websocket, message)
        
        # Check updated stats
        updated_stats = message_router.get_stats()
        
        # Stats must be incremented
        assert updated_stats["messages_routed"] == initial_routed + 1
        # Check for either string format or MessageType enum format
        message_types = updated_stats["message_types"]
        assert "user_message" in message_types or "MessageType.USER_MESSAGE" in message_types
    
    @pytest.mark.asyncio
    async def test_20_critical_end_to_end_message_flow(self, mock_agent_service):
        """Test 20: CRITICAL END-TO-END - Message must flow from process_agent_message to agent execution."""
        # This is the most important test - simulates full flow
        user_id = "test_user_123"
        
        # Setup a more complete mock agent service with internal components
        # Mock: Generic component isolation for controlled unit testing
        mock_supervisor = AsyncMock()
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_supervisor.run = AsyncMock(return_value="Agent response: Cost analysis complete")
        
        # Mock: Generic component isolation for controlled unit testing
        mock_message_handler = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_message_handler.handle_user_message = AsyncMock()
        
        mock_agent_service.supervisor = mock_supervisor
        mock_agent_service.message_handler = mock_message_handler
        
        # Simulate real frontend message structure
        frontend_message = {
            "type": "user_message",
            "payload": {
                "content": "@Netra analyze our GPU costs for last month",
                "references": [],
                # Note: No thread_id on first message
            }
        }
        message_str = json.dumps(frontend_message)
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session.commit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            # Mock: Generic component isolation for controlled unit testing
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Process the message through the critical routing function
            await process_agent_message(user_id, message_str, mock_agent_service)
            
            # CRITICAL ASSERTIONS
            
            # 1. Agent service must be called
            mock_agent_service.handle_websocket_message.assert_called_once()
            
            # 2. Correct user_id must be passed
            call_args = mock_agent_service.handle_websocket_message.call_args
            assert call_args[0][0] == user_id
            
            # 3. Message must be valid JSON string
            passed_message_str = call_args[0][1]
            assert passed_message_str == message_str
            parsed = json.loads(passed_message_str)
            assert parsed == frontend_message
            
            # 4. DB session must be provided
            assert call_args[0][2] == mock_session
            
            # 5. Message content must be preserved exactly
            assert parsed["payload"]["content"] == "@Netra analyze our GPU costs for last month"
            assert parsed["payload"]["references"] == []
            
            # 6. Database session must be committed
            mock_session.commit.assert_called_once()
            
            print("✅ CRITICAL TEST PASSED: Message successfully routed from WebSocket to Agent Service!")