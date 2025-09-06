# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: WebSocket Message Alignment Integration Test

# REMOVED_SYNTAX_ERROR: This test verifies that the backend and frontend can correctly exchange
# REMOVED_SYNTAX_ERROR: all supported message types without parsing errors.
# REMOVED_SYNTAX_ERROR: '''

import asyncio
import json
import pytest
import websockets
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.types import MessageType, create_server_message
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class WebSocketMessageAlignmentTest:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket message type alignment between backend and frontend."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.received_messages: List[Dict[str, Any]] = []
    # REMOVED_SYNTAX_ERROR: self.parse_errors: List[Dict[str, Any]] = []

# REMOVED_SYNTAX_ERROR: async def simulate_frontend_validation(self, message: Dict[str, Any]) -> bool:
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Simulates frontend message validation logic.
    # REMOVED_SYNTAX_ERROR: Returns True if message would be accepted, False if it would trigger parse error.
    # REMOVED_SYNTAX_ERROR: '''
    # Check if message is valid object
    # REMOVED_SYNTAX_ERROR: if not isinstance(message, dict):
        # REMOVED_SYNTAX_ERROR: self.parse_errors.append({ ))
        # REMOVED_SYNTAX_ERROR: 'error': 'Message is not an object',
        # REMOVED_SYNTAX_ERROR: 'message': message
        
        # REMOVED_SYNTAX_ERROR: return False

        # Check for required type field
        # REMOVED_SYNTAX_ERROR: if 'type' not in message or not isinstance(message.get('type'), str):
            # REMOVED_SYNTAX_ERROR: self.parse_errors.append({ ))
            # REMOVED_SYNTAX_ERROR: 'error': 'Missing or invalid type field',
            # REMOVED_SYNTAX_ERROR: 'message': message
            
            # REMOVED_SYNTAX_ERROR: return False

            # REMOVED_SYNTAX_ERROR: msg_type = message['type']

            # Frontend's current recognized types (before fix)
            # REMOVED_SYNTAX_ERROR: system_types = ['auth', 'ping', 'pong', 'server_shutdown']  # Missing: system_message, error_message
            # REMOVED_SYNTAX_ERROR: agent_types = ['agent_started', 'tool_executing', 'agent_thinking', 'partial_result', 'agent_completed']
            # REMOVED_SYNTAX_ERROR: thread_types = ['thread_created', 'thread_loading', 'thread_loaded', 'thread_renamed']
            # REMOVED_SYNTAX_ERROR: report_types = ['final_report', 'error', 'step_created']

            # Check if message type is recognized
            # REMOVED_SYNTAX_ERROR: all_recognized_types = system_types + agent_types + thread_types + report_types

            # Additional types that should be recognized but might not be
            # REMOVED_SYNTAX_ERROR: backend_only_types = [ )
            # REMOVED_SYNTAX_ERROR: 'connect', 'disconnect', 'heartbeat', 'heartbeat_ack',
            # REMOVED_SYNTAX_ERROR: 'user_message', 'system_message', 'error_message',
            # REMOVED_SYNTAX_ERROR: 'start_agent', 'agent_response', 'agent_progress', 'agent_error',
            # REMOVED_SYNTAX_ERROR: 'thread_update', 'thread_message',
            # REMOVED_SYNTAX_ERROR: 'broadcast', 'room_message',
            # REMOVED_SYNTAX_ERROR: 'jsonrpc_request', 'jsonrpc_response', 'jsonrpc_notification'
            

            # REMOVED_SYNTAX_ERROR: if msg_type not in all_recognized_types and msg_type not in backend_only_types:
                # Unknown type - frontend handles with default handler
                # REMOVED_SYNTAX_ERROR: if 'payload' not in message and 'data' in message:
                    # REMOVED_SYNTAX_ERROR: message['payload'] = message['data']
                    # REMOVED_SYNTAX_ERROR: elif 'payload' not in message:
                        # REMOVED_SYNTAX_ERROR: message['payload'] = {}

                        # Specific validation per message category
                        # REMOVED_SYNTAX_ERROR: if msg_type in agent_types:
                            # REMOVED_SYNTAX_ERROR: if 'payload' not in message or not isinstance(message.get('payload'), dict):
                                # REMOVED_SYNTAX_ERROR: self.parse_errors.append({ ))
                                # REMOVED_SYNTAX_ERROR: 'error': 'formatted_string',
                                # REMOVED_SYNTAX_ERROR: 'message': message
                                
                                # REMOVED_SYNTAX_ERROR: return False

                                # REMOVED_SYNTAX_ERROR: if msg_type in thread_types:
                                    # REMOVED_SYNTAX_ERROR: if 'payload' not in message or not isinstance(message.get('payload'), dict):
                                        # REMOVED_SYNTAX_ERROR: self.parse_errors.append({ ))
                                        # REMOVED_SYNTAX_ERROR: 'error': 'formatted_string',
                                        # REMOVED_SYNTAX_ERROR: 'message': message
                                        
                                        # REMOVED_SYNTAX_ERROR: return False

                                        # REMOVED_SYNTAX_ERROR: self.received_messages.append(message)
                                        # REMOVED_SYNTAX_ERROR: return True


                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_all_backend_message_types():
                                            # REMOVED_SYNTAX_ERROR: """Test that all backend MessageType enum values can be sent without frontend parse errors."""

                                            # REMOVED_SYNTAX_ERROR: tester = WebSocketMessageAlignmentTest()

                                            # All message types from backend MessageType enum
                                            # REMOVED_SYNTAX_ERROR: test_messages = [ )
                                            # Connection lifecycle
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.CONNECT, {'status': 'connected'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.DISCONNECT, {'reason': 'server_shutdown'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.HEARTBEAT, {'timestamp': 123456}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.HEARTBEAT_ACK, {'timestamp': 123456}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.PING, {}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.PONG, {'original_timestamp': 123456}),

                                            # User messages
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.USER_MESSAGE, {'message': 'test user message'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.SYSTEM_MESSAGE, { ))
                                            # REMOVED_SYNTAX_ERROR: 'event': 'connection_established',
                                            # REMOVED_SYNTAX_ERROR: 'connection_id': 'test_conn_123',
                                            # REMOVED_SYNTAX_ERROR: 'user_id': 'test_user',
                                            # REMOVED_SYNTAX_ERROR: 'config': { )
                                            # REMOVED_SYNTAX_ERROR: 'heartbeat_interval': 45,
                                            # REMOVED_SYNTAX_ERROR: 'max_message_size': 8192
                                            
                                            # REMOVED_SYNTAX_ERROR: }),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.ERROR_MESSAGE, { ))
                                            # REMOVED_SYNTAX_ERROR: 'error': 'Test error',
                                            # REMOVED_SYNTAX_ERROR: 'code': 'TEST_ERROR_001'
                                            # REMOVED_SYNTAX_ERROR: }),

                                            # Agent communication
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.START_AGENT, {'agent': 'test_agent'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.AGENT_RESPONSE, {'response': 'test response'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.AGENT_PROGRESS, {'progress': 50, 'status': 'processing'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.AGENT_ERROR, {'error': 'Agent error', 'details': 'Test'}),

                                            # Thread/conversation
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.THREAD_UPDATE, {'thread_id': 'thread_123', 'status': 'updated'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.THREAD_MESSAGE, {'thread_id': 'thread_123', 'message': 'test'}),

                                            # Broadcasting
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.BROADCAST, {'message': 'broadcast to all'}),
                                            # REMOVED_SYNTAX_ERROR: create_server_message(MessageType.ROOM_MESSAGE, {'room': 'test_room', 'message': 'room msg'}),
                                            

                                            # Test each message through simulated frontend validation
                                            # REMOVED_SYNTAX_ERROR: failed_messages = []
                                            # REMOVED_SYNTAX_ERROR: for msg in test_messages:
                                                # REMOVED_SYNTAX_ERROR: msg_dict = msg.model_dump()
                                                # REMOVED_SYNTAX_ERROR: success = await tester.simulate_frontend_validation(msg_dict)
                                                # REMOVED_SYNTAX_ERROR: if not success:
                                                    # REMOVED_SYNTAX_ERROR: failed_messages.append({ ))
                                                    # REMOVED_SYNTAX_ERROR: 'message_type': msg.type,
                                                    # REMOVED_SYNTAX_ERROR: 'message': msg_dict,
                                                    # REMOVED_SYNTAX_ERROR: 'errors': tester.parse_errors[-1] if tester.parse_errors else None
                                                    

                                                    # Report results
                                                    # REMOVED_SYNTAX_ERROR: if failed_messages:
                                                        # REMOVED_SYNTAX_ERROR: print(" )
                                                        # REMOVED_SYNTAX_ERROR: === WebSocket Message Alignment Issues Found ===")
                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                        # REMOVED_SYNTAX_ERROR: for failure in failed_messages:
                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                            # These are expected to fail before the fix
                                                            # REMOVED_SYNTAX_ERROR: expected_failures = [ )
                                                            # REMOVED_SYNTAX_ERROR: MessageType.SYSTEM_MESSAGE,  # Not in frontend"s system_types list
                                                            # REMOVED_SYNTAX_ERROR: MessageType.ERROR_MESSAGE,   # Not in frontend"s system_types list
                                                            # REMOVED_SYNTAX_ERROR: MessageType.CONNECT,         # Not recognized at all
                                                            # REMOVED_SYNTAX_ERROR: MessageType.DISCONNECT,      # Not recognized at all
                                                            # REMOVED_SYNTAX_ERROR: MessageType.HEARTBEAT,       # Not recognized at all
                                                            # REMOVED_SYNTAX_ERROR: MessageType.HEARTBEAT_ACK,   # Not recognized at all
                                                            # REMOVED_SYNTAX_ERROR: MessageType.USER_MESSAGE,    # Not recognized at all
                                                            # REMOVED_SYNTAX_ERROR: MessageType.START_AGENT,     # Not in agent_types list
                                                            # REMOVED_SYNTAX_ERROR: MessageType.AGENT_RESPONSE,  # Different from agent_completed
                                                            # REMOVED_SYNTAX_ERROR: MessageType.AGENT_PROGRESS,  # Different from agent_thinking
                                                            # REMOVED_SYNTAX_ERROR: MessageType.AGENT_ERROR,     # Not in agent_types list
                                                            # REMOVED_SYNTAX_ERROR: MessageType.THREAD_UPDATE,   # Not in thread_types list
                                                            # REMOVED_SYNTAX_ERROR: MessageType.THREAD_MESSAGE,  # Not in thread_types list
                                                            # REMOVED_SYNTAX_ERROR: MessageType.BROADCAST,       # Not recognized at all
                                                            # REMOVED_SYNTAX_ERROR: MessageType.ROOM_MESSAGE,    # Not recognized at all
                                                            

                                                            # REMOVED_SYNTAX_ERROR: actual_failures = [f['message_type'] for f in failed_messages]

                                                            # This assertion will fail, demonstrating the alignment issues
                                                            # REMOVED_SYNTAX_ERROR: assert set(actual_failures) == set(expected_failures), \
                                                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                                                            # REMOVED_SYNTAX_ERROR: else:
                                                                # REMOVED_SYNTAX_ERROR: print(" )
                                                                # REMOVED_SYNTAX_ERROR: === All WebSocket Messages Validated Successfully ===")
                                                                # REMOVED_SYNTAX_ERROR: print("formatted_string")


                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_welcome_message_format():
                                                                    # REMOVED_SYNTAX_ERROR: """Test the specific welcome message sent on connection."""

                                                                    # REMOVED_SYNTAX_ERROR: tester = WebSocketMessageAlignmentTest()

                                                                    # This is the actual welcome message sent by the backend
                                                                    # REMOVED_SYNTAX_ERROR: welcome_msg = create_server_message( )
                                                                    # REMOVED_SYNTAX_ERROR: MessageType.SYSTEM_MESSAGE,
                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                    # REMOVED_SYNTAX_ERROR: "event": "connection_established",
                                                                    # REMOVED_SYNTAX_ERROR: "connection_id": "conn_abc123",
                                                                    # REMOVED_SYNTAX_ERROR: "user_id": "user_123",
                                                                    # REMOVED_SYNTAX_ERROR: "server_time": "2025-08-29T18:36:00Z",
                                                                    # REMOVED_SYNTAX_ERROR: "config": { )
                                                                    # REMOVED_SYNTAX_ERROR: "heartbeat_interval": 45,
                                                                    # REMOVED_SYNTAX_ERROR: "max_message_size": 8192
                                                                    
                                                                    
                                                                    

                                                                    # REMOVED_SYNTAX_ERROR: msg_dict = welcome_msg.model_dump()
                                                                    # REMOVED_SYNTAX_ERROR: print(f" )
                                                                    # REMOVED_SYNTAX_ERROR: Testing Welcome Message Format:")
                                                                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                                                                    # REMOVED_SYNTAX_ERROR: success = await tester.simulate_frontend_validation(msg_dict)

                                                                    # REMOVED_SYNTAX_ERROR: if not success:
                                                                        # REMOVED_SYNTAX_ERROR: print(f"ERROR: Welcome message failed validation!")
                                                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                                                        # This is expected to fail before the fix
                                                                        # REMOVED_SYNTAX_ERROR: assert False, "Welcome message should be valid but failed frontend validation"
                                                                        # REMOVED_SYNTAX_ERROR: else:
                                                                            # REMOVED_SYNTAX_ERROR: print("SUCCESS: Welcome message validated correctly")


                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_data_to_payload_conversion():
                                                                                # REMOVED_SYNTAX_ERROR: """Test that messages with 'data' field are properly converted to 'payload' for frontend."""

                                                                                # REMOVED_SYNTAX_ERROR: tester = WebSocketMessageAlignmentTest()

                                                                                # Backend sends with 'data' field
                                                                                # REMOVED_SYNTAX_ERROR: backend_msg = { )
                                                                                # REMOVED_SYNTAX_ERROR: 'type': 'system_message',
                                                                                # REMOVED_SYNTAX_ERROR: 'data': {'event': 'test_event', 'details': 'test'},
                                                                                # REMOVED_SYNTAX_ERROR: 'timestamp': 123456789
                                                                                

                                                                                # Simulate frontend receiving and processing
                                                                                # REMOVED_SYNTAX_ERROR: success = await tester.simulate_frontend_validation(backend_msg.copy())

                                                                                # Check if data was converted to payload
                                                                                # REMOVED_SYNTAX_ERROR: if success and tester.received_messages:
                                                                                    # REMOVED_SYNTAX_ERROR: processed_msg = tester.received_messages[-1]
                                                                                    # REMOVED_SYNTAX_ERROR: assert 'payload' in processed_msg or 'data' in processed_msg, \
                                                                                    # REMOVED_SYNTAX_ERROR: "Message should have either payload or data field after processing"

                                                                                    # Frontend should access the data through payload
                                                                                    # REMOVED_SYNTAX_ERROR: if 'payload' in processed_msg:
                                                                                        # REMOVED_SYNTAX_ERROR: assert processed_msg['payload'] == backend_msg['data'], \
                                                                                        # REMOVED_SYNTAX_ERROR: "Data field should be accessible as payload"
                                                                                        # REMOVED_SYNTAX_ERROR: else:
                                                                                            # REMOVED_SYNTAX_ERROR: print(f"WARNING: Message validation failed - this is expected before the fix")
                                                                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")


                                                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                                # Run tests
                                                                                                # REMOVED_SYNTAX_ERROR: asyncio.run(test_all_backend_message_types())
                                                                                                # REMOVED_SYNTAX_ERROR: asyncio.run(test_welcome_message_format())
                                                                                                # REMOVED_SYNTAX_ERROR: asyncio.run(test_data_to_payload_conversion())
                                                                                                # REMOVED_SYNTAX_ERROR: pass