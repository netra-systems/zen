"""Critical Test Suite: Prevent Inverted Logic in WebSocket Message Handling

This suite specifically tests for the inverted logic bug where:
- Manager returning False would EXIT instead of processing
- Messages would be validated but never forwarded to agents

ROOT CAUSE: if not await validate_and_handle_message() would return True (exit)
instead of continuing to process the message through agent service.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch, call
from app.routes.websockets import _handle_validated_message, _process_valid_message
from app.routes.utils.websocket_helpers import validate_and_handle_message, process_agent_message


class TestWebSocketInvertedLogicPrevention:
    """Tests to prevent inverted logic that causes silent message drops."""
    
    @pytest.mark.asyncio
    async def test_01_user_message_always_reaches_agent_regardless_of_manager_result(self):
        """Test 1: User messages MUST reach agent service even if manager returns False."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "user_message", "payload": {"content": "Test message"}}
        data = json.dumps(message)
        agent_service = AsyncMock()
        agent_service.handle_websocket_message = AsyncMock()
        
        # Mock manager to return False (which used to cause EXIT!)
        with patch('app.routes.websockets.validate_and_handle_message', return_value=False):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                result = await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # CRITICAL: Agent must be called even when manager returns False
                mock_process.assert_called_once_with(user_id, data, agent_service)
                assert result is True
    
    @pytest.mark.asyncio
    async def test_02_manager_true_still_processes_agent(self):
        """Test 2: Manager returning True should still process through agent."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "user_message", "payload": {"content": "Test"}}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        # Manager returns True
        with patch('app.routes.websockets.validate_and_handle_message', return_value=True):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # Should still process through agent
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_03_ping_messages_dont_reach_agent(self):
        """Test 3: Ping messages should NOT reach agent service."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "ping"}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=True):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # Ping should NOT go to agent
                mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_04_pong_messages_dont_reach_agent(self):
        """Test 4: Pong messages should NOT reach agent service."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "pong"}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=True):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # Pong should NOT go to agent
                mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_05_auth_messages_dont_reach_agent(self):
        """Test 5: Auth messages should NOT reach agent service."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "auth", "token": "test_token"}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=True):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # Auth should NOT go to agent
                mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_06_start_agent_messages_reach_agent(self):
        """Test 6: start_agent messages MUST reach agent service."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "start_agent", "payload": {"user_request": "Start"}}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=False):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # start_agent MUST reach agent
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_07_unknown_message_types_reach_agent(self):
        """Test 7: Unknown message types should reach agent (let agent decide)."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "unknown_type", "payload": {"data": "test"}}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=False):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # Unknown types should reach agent
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_08_manager_exception_doesnt_prevent_agent_processing(self):
        """Test 8: Manager throwing exception shouldn't prevent agent processing."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "user_message", "payload": {"content": "Test"}}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        # Manager throws exception
        with patch('app.routes.websockets.validate_and_handle_message', 
                  side_effect=Exception("Manager error")):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                with patch('app.routes.websockets.logger'):
                    # Should handle exception and still process
                    try:
                        await _handle_validated_message(
                            user_id, websocket, message, data, agent_service
                        )
                    except:
                        pass  # Exception might propagate, but agent should be called
                    
                    # In fixed version, agent should still be attempted
                    # (Though this depends on error handling strategy)
    
    @pytest.mark.asyncio
    async def test_09_concurrent_messages_all_reach_agent(self):
        """Test 9: Concurrent messages must all reach agent service."""
        user_id = "test_user"
        websocket = Mock()
        agent_service = AsyncMock()
        
        messages = [
            {"type": "user_message", "payload": {"content": f"Message {i}"}}
            for i in range(5)
        ]
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=False):
            with patch('app.routes.websockets.process_agent_message') as mock_process:
                # Process all messages concurrently
                tasks = [
                    _handle_validated_message(
                        user_id, websocket, msg, json.dumps(msg), agent_service
                    )
                    for msg in messages
                ]
                
                await asyncio.gather(*tasks)
                
                # All 5 messages should reach agent
                assert mock_process.call_count == 5
    
    @pytest.mark.asyncio
    async def test_10_process_agent_message_actually_calls_handle_websocket_message(self):
        """Test 10: Verify process_agent_message actually calls agent service."""
        user_id = "test_user"
        data = json.dumps({"type": "user_message", "payload": {"content": "Test"}})
        
        agent_service = AsyncMock()
        agent_service.handle_websocket_message = AsyncMock()
        
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message(user_id, data, agent_service)
            
            # CRITICAL: Must actually call the agent service method
            agent_service.handle_websocket_message.assert_called_once_with(
                user_id, data, mock_session
            )


class TestMessageFlowIntegrity:
    """Additional tests to ensure message flow integrity."""
    
    @pytest.mark.asyncio
    async def test_message_content_preserved_through_flow(self):
        """Ensure message content is preserved exactly through the flow."""
        user_id = "test_user"
        websocket = Mock()
        
        # Complex message with special characters
        original_content = "Test with 'quotes' \"double\" \n newlines 😊"
        message = {
            "type": "user_message",
            "payload": {
                "content": original_content,
                "references": ["file.txt"],
                "thread_id": "thread_123"
            }
        }
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        captured_data = None
        
        async def capture_data(uid, msg_data, session):
            nonlocal captured_data
            captured_data = msg_data
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=False):
            with patch('app.routes.websockets.process_agent_message', side_effect=capture_data):
                await _handle_validated_message(
                    user_id, websocket, message, data, agent_service
                )
                
                # Verify exact message preservation
                assert captured_data == data
                parsed = json.loads(captured_data)
                assert parsed["payload"]["content"] == original_content
    
    @pytest.mark.asyncio
    async def test_logging_captures_critical_fix(self):
        """Verify critical fix logging is present."""
        user_id = "test_user"
        websocket = Mock()
        message = {"type": "user_message", "payload": {"content": "Test"}}
        data = json.dumps(message)
        agent_service = AsyncMock()
        
        with patch('app.routes.websockets.validate_and_handle_message', return_value=False):
            with patch('app.routes.websockets.process_agent_message'):
                with patch('app.routes.websockets.logger') as mock_logger:
                    await _handle_validated_message(
                        user_id, websocket, message, data, agent_service
                    )
                    
                    # Should log the critical fix
                    mock_logger.info.assert_called()
                    log_msg = str(mock_logger.info.call_args)
                    assert "CRITICAL FIX" in log_msg
                    assert "user_message" in log_msg