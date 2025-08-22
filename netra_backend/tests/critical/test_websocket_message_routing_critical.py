"""CRITICAL: WebSocket Message Routing to Agent Service Tests

This is the most critical test suite - it ensures WebSocket messages actually reach
the agent service. Without this, the entire system appears to work but agents never
receive messages, causing complete silent failure.

ROOT CAUSE: The unified WebSocket system was validating messages but never forwarding
them to agent_service.handle_websocket_message(), causing total system failure.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest
from fastapi import WebSocket

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.websocket.connection import ConnectionInfo

from netra_backend.app.websocket.unified.message_handlers import (
    MessageHandler,
    MessageProcessor,
)

class TestCriticalMessageRoutingToAgentService:
    """CRITICAL: Tests that messages MUST reach agent service or system fails silently."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket with app state containing agent service."""
        ws = Mock(spec=WebSocket)
        ws.app = Mock()
        ws.app.state = Mock()
        ws.app.state.agent_service = AsyncMock(spec=AgentService)
        ws.app.state.agent_service.handle_websocket_message = AsyncMock()
        return ws
    
    @pytest.fixture
    def connection_info(self, mock_websocket):
        """Create connection info with user metadata."""
        conn = Mock(spec=ConnectionInfo)
        conn.connection_id = str(uuid.uuid4())
        conn.websocket = mock_websocket
        conn.metadata = {"user_id": "test_user_123"}
        conn.connected_at = datetime.now()
        return conn
    
    @pytest.fixture
    def message_processor(self):
        """Create message processor with mocked dependencies."""
        manager = Mock()
        manager.rate_limiter = Mock()
        manager.rate_limiter.is_rate_limited = Mock(return_value=False)
        manager.error_handler = Mock()
        
        handler = Mock(spec=MessageHandler)
        handler.is_ping_message = Mock(return_value=False)
        handler.validate_message = Mock(return_value=True)
        
        processor = MessageProcessor(manager, handler)
        return processor
    
    @pytest.mark.asyncio
    async def test_01_user_message_must_reach_agent_service(self, message_processor, connection_info):
        """Test 1: user_message type MUST be forwarded to agent service."""
        message = {
            "type": "user_message",
            "payload": {"content": "Analyze our costs", "references": []}
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            result = await message_processor.process_with_rate_limiting(connection_info, message)
            
            # CRITICAL ASSERTION: Agent service MUST be called
            agent_service = connection_info.websocket.app.state.agent_service
            agent_service.handle_websocket_message.assert_called_once()
            
            # Verify correct parameters
            call_args = agent_service.handle_websocket_message.call_args
            assert call_args[0][0] == "test_user_123"  # user_id
            assert json.loads(call_args[0][1]) == message  # message as JSON string
            assert call_args[0][2] == mock_session  # db_session
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_02_start_agent_message_must_reach_agent_service(self, message_processor, connection_info):
        """Test 2: start_agent type MUST be forwarded to agent service."""
        message = {
            "type": "start_agent",
            "payload": {"user_request": "Start optimization", "thread_id": "thread_456"}
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_processor.process_with_rate_limiting(connection_info, message)
            
            agent_service = connection_info.websocket.app.state.agent_service
            agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_03_missing_user_id_prevents_agent_processing(self, message_processor, connection_info):
        """Test 3: Missing user_id in connection MUST prevent agent processing."""
        connection_info.metadata = {}  # No user_id
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            result = await message_processor.process_with_rate_limiting(connection_info, message)
            
            # Should NOT call agent service without user_id
            agent_service = connection_info.websocket.app.state.agent_service
            agent_service.handle_websocket_message.assert_not_called()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_04_missing_agent_service_logs_error(self, message_processor, connection_info):
        """Test 4: Missing agent service in app state MUST log error."""
        # Remove agent service from app state
        del connection_info.websocket.app.state.agent_service
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        with patch('app.websocket.unified.message_handlers.logger') as mock_logger:
            result = await message_processor.process_with_rate_limiting(connection_info, message)
            
            # Must log error about missing agent service
            mock_logger.error.assert_called()
            error_msg = mock_logger.error.call_args[0][0]
            assert "agent service not found" in error_msg.lower()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_05_database_error_handled_gracefully(self, message_processor, connection_info):
        """Test 5: Database errors during agent processing MUST be handled."""
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            with patch('app.websocket.unified.message_handlers.logger') as mock_logger:
                result = await message_processor.process_with_rate_limiting(connection_info, message)
                
                # Should log the error
                mock_logger.error.assert_called()
                assert "Error forwarding message to agent service" in str(mock_logger.error.call_args)
                assert result is False
    
    @pytest.mark.asyncio
    async def test_06_agent_service_exception_logged(self, message_processor, connection_info):
        """Test 6: Agent service exceptions MUST be logged for debugging."""
        message = {"type": "user_message", "payload": {"content": "Crash test"}}
        
        # Make agent service throw exception
        agent_service = connection_info.websocket.app.state.agent_service
        agent_service.handle_websocket_message.side_effect = Exception("Agent crashed")
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            with patch('app.websocket.unified.message_handlers.logger') as mock_logger:
                result = await message_processor.process_with_rate_limiting(connection_info, message)
                
                # Must log the agent crash
                mock_logger.error.assert_called()
                assert "Agent crashed" in str(mock_logger.error.call_args)
                assert result is False
    
    @pytest.mark.asyncio
    async def test_07_message_json_serialization_correct(self, message_processor, connection_info):
        """Test 7: Messages MUST be correctly serialized to JSON for agent service."""
        message = {
            "type": "user_message",
            "payload": {
                "content": "Test with special chars: 'quotes' \"double\" \n newline",
                "references": ["file1.txt", "data.json"]
            }
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_processor.process_with_rate_limiting(connection_info, message)
            
            agent_service = connection_info.websocket.app.state.agent_service
            call_args = agent_service.handle_websocket_message.call_args
            
            # Verify JSON serialization preserved the message
            message_str = call_args[0][1]
            parsed = json.loads(message_str)
            assert parsed == message
    
    @pytest.mark.asyncio
    async def test_08_rate_limited_messages_not_forwarded(self, message_processor, connection_info):
        """Test 8: Rate limited messages MUST NOT reach agent service."""
        # Set rate limiter to block
        message_processor.manager.rate_limiter.is_rate_limited.return_value = True
        
        message = {"type": "user_message", "payload": {"content": "Spam"}}
        
        result = await message_processor.process_with_rate_limiting(connection_info, message)
        
        # Should NOT forward to agent when rate limited
        agent_service = connection_info.websocket.app.state.agent_service
        agent_service.handle_websocket_message.assert_not_called()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_09_ping_messages_not_forwarded_to_agent(self, message_processor, connection_info):
        """Test 9: Ping messages MUST NOT be forwarded to agent service."""
        message_processor.handler.is_ping_message.return_value = True
        message_processor.handler.handle_ping_message = AsyncMock()
        
        message = {"type": "ping"}
        
        await message_processor.process_with_rate_limiting(connection_info, message)
        
        # Ping should be handled but not forwarded
        message_processor.handler.handle_ping_message.assert_called_once()
        agent_service = connection_info.websocket.app.state.agent_service
        agent_service.handle_websocket_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_10_invalid_messages_not_forwarded(self, message_processor, connection_info):
        """Test 10: Invalid messages MUST NOT reach agent service."""
        from netra_backend.app.websocket.unified.types import WebSocketValidationError
        
        # Make validation fail
        message_processor.handler.validate_message.return_value = WebSocketValidationError(
            message="Invalid message format", code="INVALID_FORMAT"
        )
        
        message = {"invalid": "structure"}
        
        result = await message_processor.process_with_rate_limiting(connection_info, message)
        
        # Invalid messages should not be forwarded
        agent_service = connection_info.websocket.app.state.agent_service
        agent_service.handle_websocket_message.assert_not_called()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_11_concurrent_messages_all_forwarded(self, message_processor, connection_info):
        """Test 11: Concurrent messages MUST all be forwarded to agent service."""
        messages = [
            {"type": "user_message", "payload": {"content": f"Message {i}"}}
            for i in range(5)
        ]
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Process all messages concurrently
            results = await asyncio.gather(*[
                message_processor.process_with_rate_limiting(connection_info, msg)
                for msg in messages
            ])
            
            # All should succeed
            assert all(results)
            
            # Agent service should be called 5 times
            agent_service = connection_info.websocket.app.state.agent_service
            assert agent_service.handle_websocket_message.call_count == 5
    
    @pytest.mark.asyncio
    async def test_12_message_logging_includes_type(self, message_processor, connection_info):
        """Test 12: Message forwarding MUST log message type for debugging."""
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            with patch('app.websocket.unified.message_handlers.logger') as mock_logger:
                await message_processor.process_with_rate_limiting(connection_info, message)
                
                # Should log the message type
                info_calls = mock_logger.info.call_args_list
                assert any("user_message" in str(call) for call in info_calls)
    
    @pytest.mark.asyncio
    async def test_13_null_payload_handled_safely(self, message_processor, connection_info):
        """Test 13: Null payload MUST be handled without crashing."""
        message = {"type": "user_message", "payload": None}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Should not crash
            result = await message_processor.process_with_rate_limiting(connection_info, message)
            
            # Agent service should still be called (let it handle null)
            agent_service = connection_info.websocket.app.state.agent_service
            agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_14_empty_message_type_forwarded(self, message_processor, connection_info):
        """Test 14: Empty message type should still be forwarded (let agent decide)."""
        message = {"type": "", "payload": {"content": "Test"}}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_processor.process_with_rate_limiting(connection_info, message)
            
            # Should forward even with empty type (agent will handle)
            agent_service = connection_info.websocket.app.state.agent_service
            agent_service.handle_websocket_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_15_thread_context_preserved_in_message(self, message_processor, connection_info):
        """Test 15: Thread context in message MUST be preserved when forwarding."""
        thread_id = str(uuid.uuid4())
        message = {
            "type": "user_message",
            "payload": {
                "content": "Continue conversation",
                "thread_id": thread_id,
                "references": ["previous_message.txt"]
            }
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_processor.process_with_rate_limiting(connection_info, message)
            
            agent_service = connection_info.websocket.app.state.agent_service
            call_args = agent_service.handle_websocket_message.call_args
            
            # Verify thread_id preserved
            forwarded_msg = json.loads(call_args[0][1])
            assert forwarded_msg["payload"]["thread_id"] == thread_id
    
    @pytest.mark.asyncio
    async def test_16_websocket_disconnect_during_forward_handled(self, message_processor, connection_info):
        """Test 16: WebSocket disconnect during forwarding MUST be handled."""
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        # Simulate disconnect during agent processing
        from starlette.websockets import WebSocketDisconnect
        agent_service = connection_info.websocket.app.state.agent_service
        agent_service.handle_websocket_message.side_effect = WebSocketDisconnect()
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            with patch('app.websocket.unified.message_handlers.logger') as mock_logger:
                result = await message_processor.process_with_rate_limiting(connection_info, message)
                
                # Should handle disconnect gracefully
                mock_logger.error.assert_called()
                assert result is False
    
    @pytest.mark.asyncio
    async def test_17_database_session_always_created(self, message_processor, connection_info):
        """Test 17: Database session MUST always be created for agent processing."""
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_processor.process_with_rate_limiting(connection_info, message)
            
            # Verify DB session was created
            mock_db.assert_called_once()
            mock_db.return_value.__aenter__.assert_called_once()
            mock_db.return_value.__aexit__.assert_called_once()
            
            # Verify session passed to agent
            agent_service = connection_info.websocket.app.state.agent_service
            call_args = agent_service.handle_websocket_message.call_args
            assert call_args[0][2] == mock_session
    
    @pytest.mark.asyncio
    async def test_18_user_id_extraction_from_metadata(self, message_processor, connection_info):
        """Test 18: User ID MUST be correctly extracted from connection metadata."""
        # Test various user_id formats
        test_user_ids = [
            "simple_user",
            "user@example.com",
            str(uuid.uuid4()),
            "user_with_numbers_123",
            "CamelCaseUser"
        ]
        
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        for user_id in test_user_ids:
            connection_info.metadata = {"user_id": user_id}
            connection_info.websocket.app.state.agent_service.handle_websocket_message.reset_mock()
            
            with patch('app.db.postgres.get_async_db') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_db.return_value.__aexit__ = AsyncMock()
                
                await message_processor.process_with_rate_limiting(connection_info, message)
                
                # Verify correct user_id passed
                agent_service = connection_info.websocket.app.state.agent_service
                call_args = agent_service.handle_websocket_message.call_args
                assert call_args[0][0] == user_id
    
    @pytest.mark.asyncio
    async def test_19_message_stats_updated_correctly(self, message_processor, connection_info):
        """Test 19: Message statistics MUST be updated for monitoring."""
        initial_stats = message_processor.get_stats()
        
        # Process successful message
        message = {"type": "user_message", "payload": {"content": "Test"}}
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await message_processor.process_with_rate_limiting(connection_info, message)
        
        updated_stats = message_processor.get_stats()
        
        # Stats must be incremented
        assert updated_stats["received"] == initial_stats["received"] + 1
        assert updated_stats["validated"] == initial_stats["validated"] + 1
    
    @pytest.mark.asyncio
    async def test_20_critical_end_to_end_message_flow(self, message_processor, connection_info):
        """Test 20: CRITICAL END-TO-END - Message must flow from WebSocket to agent execution."""
        # This is the most important test - simulates full flow
        
        # Setup a more complete mock agent service
        mock_supervisor = AsyncMock()
        mock_supervisor.run = AsyncMock(return_value="Agent response: Cost analysis complete")
        
        mock_message_handler = AsyncMock()
        mock_message_handler.handle_user_message = AsyncMock()
        
        agent_service = connection_info.websocket.app.state.agent_service
        agent_service.supervisor = mock_supervisor
        agent_service.message_handler = mock_message_handler
        
        # Simulate real frontend message structure
        frontend_message = {
            "type": "user_message",
            "payload": {
                "content": "@Netra analyze our GPU costs for last month",
                "references": [],
                # Note: No thread_id on first message
            }
        }
        
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Process the message
            result = await message_processor.process_with_rate_limiting(connection_info, frontend_message)
            
            # CRITICAL ASSERTIONS
            assert result is True, "Message processing must succeed"
            
            # 1. Agent service must be called
            agent_service.handle_websocket_message.assert_called_once()
            
            # 2. Correct user_id must be passed
            call_args = agent_service.handle_websocket_message.call_args
            assert call_args[0][0] == "test_user_123"
            
            # 3. Message must be valid JSON
            message_str = call_args[0][1]
            parsed = json.loads(message_str)
            assert parsed == frontend_message
            
            # 4. DB session must be provided
            assert call_args[0][2] == mock_session
            
            # 5. Message content must be preserved exactly
            assert parsed["payload"]["content"] == "@Netra analyze our GPU costs for last month"
            
            print("✅ CRITICAL TEST PASSED: Message successfully routed from WebSocket to Agent Service!")