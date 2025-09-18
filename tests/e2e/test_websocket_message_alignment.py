'''
'''
WebSocket Message Alignment Integration Test

This test verifies that the backend and frontend can correctly exchange
all supported message types without parsing errors.
'''
'''

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


class WebSocketMessageAlignmentTest:
    "Test WebSocket message type alignment between backend and frontend."""

    def __init__(self):
        pass
        self.received_messages: List[Dict[str, Any]] = []
        self.parse_errors: List[Dict[str, Any]] = []

    async def simulate_frontend_validation(self, message: Dict[str, Any) -> bool:
        '''
        '''
        Simulates frontend message validation logic.
        Returns True if message would be accepted, False if it would trigger parse error.
        '''
        '''
    # Check if message is valid object
        if not isinstance(message, dict):
        self.parse_errors.append({)
        'error': 'Message is not an object',
        'message': message
        
        return False

        # Check for required type field
        if 'type' not in message or not isinstance(message.get('type'), str):
        self.parse_errors.append({)
        'error': 'Missing or invalid type field',
        'message': message
            
        return False

        msg_type = message['type']

            # Frontend's current recognized types (before fix)'
        system_types = ['auth', 'ping', 'pong', 'server_shutdown']  # Missing: system_message, error_message
        agent_types = ['agent_started', 'tool_executing', 'agent_thinking', 'partial_result', 'agent_completed']
        thread_types = ['thread_created', 'thread_loading', 'thread_loaded', 'thread_renamed']
        report_types = ['final_report', 'error', 'step_created']

            # Check if message type is recognized
        all_recognized_types = system_types + agent_types + thread_types + report_types

            # Additional types that should be recognized but might not be
        backend_only_types = ]
        'connect', 'disconnect', 'heartbeat', 'heartbeat_ack',
        'user_message', 'system_message', 'error_message',
        'start_agent', 'agent_response', 'agent_progress', 'agent_error',
        'thread_update', 'thread_message',
        'broadcast', 'room_message',
        'jsonrpc_request', 'jsonrpc_response', 'jsonrpc_notification'
            

        if msg_type not in all_recognized_types and msg_type not in backend_only_types:
                # Unknown type - frontend handles with default handler
        if 'payload' not in message and 'data' in message:
        message['payload'] = message['data']
        elif 'payload' not in message:
        message['payload'] = {}

                        # Specific validation per message category
        if msg_type in agent_types:
        if 'payload' not in message or not isinstance(message.get('payload'), dict):
        self.parse_errors.append({)
        'error': 'formatted_string',
        'message': message
                                
        return False

        if msg_type in thread_types:
        if 'payload' not in message or not isinstance(message.get('payload'), dict):
        self.parse_errors.append({)
        'error': 'formatted_string',
        'message': message
                                        
        return False

        self.received_messages.append(message)
        return True


@pytest.mark.asyncio
    async def test_all_backend_message_types():
        ""Test that all backend MessageType enum values can be sent without frontend parse errors."


tester = WebSocketMessageAlignmentTest()

                                            All message types from backend MessageType enum
test_messages = ]
                                            # Connection lifecycle
create_server_message(MessageType.CONNECT, {'status': 'connected'),
create_server_message(MessageType.DISCONNECT, {'reason': 'server_shutdown'),
create_server_message(MessageType.HEARTBEAT, {'timestamp': 123456),
create_server_message(MessageType.HEARTBEAT_ACK, {'timestamp': 123456),
create_server_message(MessageType.PING, {),
create_server_message(MessageType.PONG, {'original_timestamp': 123456),

                                            # User messages
create_server_message(MessageType.USER_MESSAGE, {'message': 'test user message'),
create_server_message(MessageType.SYSTEM_MESSAGE, )
'event': 'connection_established',
'connection_id': 'test_conn_123',
'user_id': 'test_user',
'config': }
'heartbeat_interval': 45,
'max_message_size': 8192
                                            
},
create_server_message(MessageType.ERROR_MESSAGE, )
'error': 'Test error',
'code': 'TEST_ERROR_001'
},

                                            # Agent communication
create_server_message(MessageType.START_AGENT, {'agent': 'test_agent'),
create_server_message(MessageType.AGENT_RESPONSE, {'response': 'test response'),
create_server_message(MessageType.AGENT_PROGRESS, {'progress': 50, 'status': 'processing'),
create_server_message(MessageType.AGENT_ERROR, {'error': 'Agent error', 'details': 'Test'),

                                            # Thread/conversation
create_server_message(MessageType.THREAD_UPDATE, {'thread_id': 'thread_123', 'status': 'updated'),
create_server_message(MessageType.THREAD_MESSAGE, {'thread_id': 'thread_123', 'message': 'test'),

                                            # Broadcasting
create_server_message(MessageType.BROADCAST, {'message': 'broadcast to all'),
create_server_message(MessageType.ROOM_MESSAGE, {'room': 'test_room', 'message': 'room msg'),
                                            

                                            # Test each message through simulated frontend validation
failed_messages = []
for msg in test_messages:
    msg_dict = msg.model_dump()

success = await tester.simulate_frontend_validation(msg_dict)
if not success:
    failed_messages.append({)

'message_type': msg.type,
'message': msg_dict,
'errors': tester.parse_errors[-1] if tester.parse_errors else None
                                                    

                                                    # Report results
if failed_messages:
    print(")"

=== WebSocket Message Alignment Issues Found ===)
print()
for failure in failed_messages:
    print(formatted_string)

print("")
print(formatted_string)

                                                            # These are expected to fail before the fix
expected_failures = ]
MessageType.SYSTEM_MESSAGE,  # Not in frontends system_types list
MessageType.ERROR_MESSAGE,   # Not in frontend"s system_types list"
MessageType.CONNECT,         # Not recognized at all
MessageType.DISCONNECT,      # Not recognized at all
MessageType.HEARTBEAT,       # Not recognized at all
MessageType.HEARTBEAT_ACK,   # Not recognized at all
MessageType.USER_MESSAGE,    # Not recognized at all
MessageType.START_AGENT,     # Not in agent_types list
MessageType.AGENT_RESPONSE,  # Different from agent_completed
MessageType.AGENT_PROGRESS,  # Different from agent_thinking
MessageType.AGENT_ERROR,     # Not in agent_types list
MessageType.THREAD_UPDATE,   # Not in thread_types list
MessageType.THREAD_MESSAGE,  # Not in thread_types list
MessageType.BROADCAST,       # Not recognized at all
MessageType.ROOM_MESSAGE,    # Not recognized at all
                                                            

actual_failures = [f['message_type'] for f in failed_messages]

                                                            # This assertion will fail, demonstrating the alignment issues
assert set(actual_failures) == set(expected_failures), \
formatted_string
else:
    print()

=== All WebSocket Messages Validated Successfully ===)
print(formatted_string"")


@pytest.mark.asyncio
    async def test_welcome_message_format():
        Test the specific welcome message sent on connection.""


tester = WebSocketMessageAlignmentTest()

                                                                    # This is the actual welcome message sent by the backend
welcome_msg = create_server_message( )
MessageType.SYSTEM_MESSAGE,
}
event: connection_established,
connection_id: "conn_abc123,"
user_id": user_123,"
server_time: 2025-8-29T18:36:00Z,
config": }"
heartbeat_interval: 45,
max_message_size: 8192""
                                                                    
                                                                    
                                                                    

msg_dict = welcome_msg.model_dump()
print(f" )"
Testing Welcome Message Format:)
print(formatted_string)""

success = await tester.simulate_frontend_validation(msg_dict)

if not success:
    print(f"ERROR: Welcome message failed validation!)"

print(formatted_string)""
                                                                        # This is expected to fail before the fix
assert False, "Welcome message should be valid but failed frontend validation"
else:
    print(SUCCESS: Welcome message validated correctly)""



@pytest.mark.asyncio
    async def test_data_to_payload_conversion():
        "Test that messages with 'data' field are properly converted to 'payload' for frontend."""


tester = WebSocketMessageAlignmentTest()

                                                                                # Backend sends with 'data' field
backend_msg = {
'type': 'system_message',
'data': {'event': 'test_event', 'details': 'test'},
'timestamp': 123456789
                                                                                

                                                                                # Simulate frontend receiving and processing
success = await tester.simulate_frontend_validation(backend_msg.copy())

                                                                                # Check if data was converted to payload
if success and tester.received_messages:
    processed_msg = tester.received_messages[-1]

assert 'payload' in processed_msg or 'data' in processed_msg, \
Message should have either payload or data field after processing""

                                                                                    # Frontend should access the data through payload
if 'payload' in processed_msg:
    assert processed_msg['payload'] == backend_msg['data'], \

Data field should be accessible as payload
else:
    print(fWARNING: Message validation failed - this is expected before the fix")"

print()""


if __name__ == __main__":"
                                                                                                # Run tests
asyncio.run(test_all_backend_message_types())
asyncio.run(test_welcome_message_format())
asyncio.run(test_data_to_payload_conversion())
pass

))))))))))))))))))))
}