"""
Comprehensive WebSocket Type Validation Tests

This test suite validates WebSocket message types and payload consistency between
frontend TypeScript and backend Python implementations, focusing on type mismatches
and validation failures that cause build and runtime errors.

Test Categories:
1. Type Consistency - Frontend vs backend message type alignment
2. Runtime Validation - Invalid message handling and edge cases  
3. Payload Structure - Field validation and serialization issues
4. Message Routing - Type-based routing and handler selection
5. Protocol Compliance - WebSocket protocol adherence

These tests should FAIL initially to reproduce the actual type validation issues
causing frontend build errors and runtime WebSocket communication problems.

BVJ: Consistent types = fewer runtime errors = better user experience
"""
import pytest
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.schemas.registry import WebSocketMessageType, AgentStatus, WebSocketMessage, BaseWebSocketPayload, UserMessagePayload, AgentUpdatePayload, StartAgentPayload, CreateThreadPayload, SwitchThreadPayload, DeleteThreadPayload, AgentCompletedPayload, StopAgentPayload

@pytest.fixture
def frontend_websocket_types():
    """Mock frontend WebSocket types extracted from TypeScript enums"""
    return {'START_AGENT': 'start_agent', 'USER_MESSAGE': 'user_message', 'CHAT_MESSAGE': 'chat_message', 'STOP_AGENT': 'stop_agent', 'CREATE_THREAD': 'create_thread', 'SWITCH_THREAD': 'switch_thread', 'DELETE_THREAD': 'delete_thread', 'RENAME_THREAD': 'rename_thread', 'LIST_THREADS': 'list_threads', 'GET_THREAD_HISTORY': 'get_thread_history', 'PING': 'ping', 'PONG': 'pong', 'AGENT_STARTED': 'agent_started', 'AGENT_COMPLETED': 'agent_completed', 'AGENT_STOPPED': 'agent_stopped', 'AGENT_ERROR': 'agent_error', 'AGENT_UPDATE': 'agent_update', 'AGENT_LOG': 'agent_log', 'AGENT_THINKING': 'agent_thinking', 'AGENT_FALLBACK': 'agent_fallback', 'TOOL_STARTED': 'tool_started', 'TOOL_COMPLETED': 'tool_completed', 'TOOL_CALL': 'tool_call', 'TOOL_RESULT': 'tool_result', 'TOOL_EXECUTING': 'tool_executing', 'SUBAGENT_STARTED': 'subagent_started', 'SUBAGENT_COMPLETED': 'subagent_completed', 'SUB_AGENT_UPDATE': 'sub_agent_update', 'THREAD_HISTORY': 'thread_history', 'THREAD_CREATED': 'thread_created', 'THREAD_UPDATED': 'thread_updated', 'THREAD_DELETED': 'thread_deleted', 'THREAD_LOADED': 'thread_loaded', 'THREAD_RENAMED': 'thread_renamed', 'STEP_CREATED': 'step_created', 'PARTIAL_RESULT': 'partial_result', 'FINAL_REPORT': 'final_report', 'STREAM_CHUNK': 'stream_chunk', 'STREAM_COMPLETE': 'stream_complete', 'GENERATION_PROGRESS': 'generation_progress', 'GENERATION_COMPLETE': 'generation_complete', 'GENERATION_ERROR': 'generation_error', 'BATCH_COMPLETE': 'batch_complete', 'ERROR': 'error', 'CONNECTION_ESTABLISHED': 'connection_established'}

@pytest.fixture
def backend_websocket_types():
    """Backend WebSocket types from Python enum"""
    return {member.name: member.value for member in WebSocketMessageType}

@pytest.fixture
def sample_websocket_messages():
    """Sample WebSocket messages with various payload types"""
    return {'user_message': {'type': 'user_message', 'payload': {'text': 'Hello, agent!', 'thread_id': 'thread_123', 'timestamp': '2025-01-23T10:00:00Z'}, 'sender': 'user_456', 'timestamp': '2025-01-23T10:00:00Z'}, 'agent_update': {'type': 'agent_update', 'payload': {'agent_id': 'agent_789', 'status': 'executing', 'progress': 0.5, 'message': 'Processing request...', 'metadata': {'step': 'analysis'}}, 'timestamp': '2025-01-23T10:01:00Z'}, 'start_agent': {'type': 'start_agent', 'payload': {'agent_type': 'chat', 'config': {'model': 'gpt-4'}, 'thread_id': 'thread_123'}}, 'invalid_type': {'type': 'unknown_message_type', 'payload': {'data': 'test'}}, 'missing_payload': {'type': 'user_message'}, 'malformed_json': '{"type": "user_message", "payload": {"text": "incomplete...'}

def test_frontend_backend_message_type_alignment(frontend_websocket_types, backend_websocket_types):
    """
    Test that frontend and backend WebSocket message types are aligned.
    Should FAIL initially if there are mismatches between TypeScript and Python enums.
    """
    frontend_values = set(frontend_websocket_types.values())
    backend_values = set(backend_websocket_types.values())
    missing_in_backend = frontend_values - backend_values
    missing_in_frontend = backend_values - frontend_values
    if missing_in_backend or missing_in_frontend:
        error_msg = []
        if missing_in_backend:
            error_msg.append(f'Missing in backend: {missing_in_backend}')
        if missing_in_frontend:
            error_msg.append(f'Missing in frontend: {missing_in_frontend}')
        pytest.fail(f"FRONTEND-BACKEND TYPE MISMATCH DETECTED: {' | '.join(error_msg)}")
    assert frontend_values == backend_values, 'Frontend and backend message types must match exactly'

def test_enum_value_consistency():
    """
    Test that enum values are consistent and don't have duplicates or conflicts.
    Should FAIL if there are inconsistencies in enum definitions.
    """
    all_values = list(WebSocketMessageType)
    value_strings = [msg_type.value for msg_type in all_values]
    duplicates = []
    seen = set()
    for value in value_strings:
        if value in seen:
            duplicates.append(value)
        seen.add(value)
    assert len(duplicates) == 0, f'DUPLICATE MESSAGE TYPE VALUES DETECTED: {duplicates}'
    for value in value_strings:
        assert isinstance(value, str), f'Message type must be string: {value}'
        assert value == value.lower(), f'Message type must be lowercase: {value}'
        assert ' ' not in value, f'Message type cannot contain spaces: {value}'
        assert value.replace('_', '').replace('-', '').isalnum(), f'Invalid characters in message type: {value}'

def test_agent_status_enum_consistency():
    """
    Test AgentStatus enum consistency between frontend and backend.
    Should FAIL if agent status values don't match.
    """
    frontend_agent_statuses = {'IDLE': 'idle', 'INITIALIZING': 'initializing', 'ACTIVE': 'active', 'THINKING': 'thinking', 'PLANNING': 'planning', 'EXECUTING': 'executing', 'RUNNING': 'running', 'WAITING': 'waiting', 'PAUSED': 'paused', 'COMPLETED': 'completed', 'FAILED': 'failed', 'ERROR': 'error', 'CANCELLED': 'cancelled', 'SHUTDOWN': 'shutdown'}
    backend_agent_statuses = {status.name: status.value for status in AgentStatus}
    frontend_set = set(frontend_agent_statuses.values())
    backend_set = set(backend_agent_statuses.values())
    missing_in_backend = frontend_set - backend_set
    missing_in_frontend = backend_set - frontend_set
    if missing_in_backend or missing_in_frontend:
        pytest.fail(f'AGENT STATUS MISMATCH: Backend missing: {missing_in_backend}, Frontend missing: {missing_in_frontend}')

def test_payload_structure_type_consistency():
    """
    Test that payload structures are consistent between frontend and backend.
    Should FAIL if payload field types don't match expected structures.
    """
    user_msg = {'text': 'Hello world', 'thread_id': 'thread_123', 'timestamp': '2025-01-23T10:00:00Z'}
    try:
        payload = UserMessagePayload(**user_msg)
        assert payload.text == 'Hello world'
    except Exception as e:
        pytest.fail(f'UserMessagePayload validation failed: {e}')
    invalid_user_msg = {'message': 'Hello world', 'thread': 'thread_123'}
    with pytest.raises(Exception):
        UserMessagePayload(**invalid_user_msg)
    agent_update = {'agent_id': 'agent_123', 'status': 'executing', 'progress': 0.75, 'message': 'Processing...'}
    try:
        payload = AgentUpdatePayload(**agent_update)
        assert payload.agent_id == 'agent_123'
        assert payload.status == 'executing'
    except Exception as e:
        pytest.fail(f'AgentUpdatePayload validation failed: {e}')

def test_message_type_validation_function_consistency():
    """
    Test that message type validation functions work consistently.
    Should FAIL if validation functions are inconsistent or missing.
    """

    def frontend_is_valid_websocket_message_type(value: str) -> bool:
        frontend_values = ['start_agent', 'user_message', 'chat_message', 'stop_agent', 'agent_started', 'agent_completed', 'agent_update', 'error']
        return value in frontend_values

    def backend_is_valid_websocket_message_type(value: str) -> bool:
        try:
            WebSocketMessageType(value)
            return True
        except ValueError:
            return False
    valid_types = ['user_message', 'agent_update', 'start_agent']
    for msg_type in valid_types:
        frontend_result = frontend_is_valid_websocket_message_type(msg_type)
        backend_result = backend_is_valid_websocket_message_type(msg_type)
        if frontend_result != backend_result:
            pytest.fail(f"VALIDATION INCONSISTENCY for '{msg_type}': Frontend={frontend_result}, Backend={backend_result}")
    invalid_types = ['invalid_type', 'unknown_message', '']
    for msg_type in invalid_types:
        frontend_result = frontend_is_valid_websocket_message_type(msg_type)
        backend_result = backend_is_valid_websocket_message_type(msg_type)
        assert not frontend_result, f'Frontend should reject invalid type: {msg_type}'
        assert not backend_result, f'Backend should reject invalid type: {msg_type}'

def test_invalid_message_type_handling(sample_websocket_messages):
    """
    Test handling of invalid message types at runtime.
    Should FAIL if invalid types are not properly rejected.
    """
    invalid_msg = sample_websocket_messages['invalid_type']
    with pytest.raises((ValueError, TypeError)):
        WebSocketMessage(type=invalid_msg['type'], payload=invalid_msg['payload'])
    with pytest.raises((ValueError, TypeError)):
        WebSocketMessage(type='', payload={'data': 'test'})
    with pytest.raises((ValueError, TypeError)):
        WebSocketMessage(type=None, payload={'data': 'test'})

def test_missing_payload_field_validation(sample_websocket_messages):
    """
    Test validation of missing required payload fields.
    Should FAIL if required fields are missing and not caught.
    """
    missing_payload_msg = sample_websocket_messages['missing_payload']
    with pytest.raises((ValueError, TypeError, KeyError)):
        WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload=None)
    with pytest.raises((ValueError, TypeError)):
        UserMessagePayload(thread_id='thread_123')
    with pytest.raises((ValueError, TypeError)):
        AgentUpdatePayload(status='executing', message='Test')

def test_payload_type_coercion_issues():
    """
    Test type coercion issues that can cause runtime errors.
    Should FAIL if type coercion is not handled properly.
    """
    problematic_payloads = [{'agent_id': 12345, 'status': 'executing', 'progress': '0.5', 'message': 'Test'}, {'text': 12345, 'thread_id': 'thread_123'}, {'thread_id': None, 'title': 'New Thread'}]
    for payload_data in problematic_payloads:
        with pytest.raises((ValueError, TypeError)):
            if 'agent_id' in payload_data:
                AgentUpdatePayload(**payload_data)
            elif 'text' in payload_data:
                UserMessagePayload(**payload_data)
            elif 'title' in payload_data:
                CreateThreadPayload(**payload_data)

def test_large_payload_handling():
    """
    Test handling of unusually large payloads.
    Should FAIL if large payloads cause memory or processing issues.
    """
    large_text = 'x' * (1024 * 1024)
    large_metadata = {f'key_{i}': f'value_{i}' * 1000 for i in range(1000)}
    try:
        large_payload = UserMessagePayload(text=large_text, thread_id='thread_123')
        assert len(large_payload.text) == len(large_text)
    except Exception as e:
        pytest.fail(f'Failed to handle large text payload: {e}')
    try:
        large_agent_payload = AgentUpdatePayload(agent_id='agent_123', status='executing', message='Processing', metadata=large_metadata)
        assert len(large_agent_payload.metadata) == 1000
    except Exception as e:
        pytest.fail(f'Failed to handle large metadata payload: {e}')

def test_malformed_json_handling(sample_websocket_messages):
    """
    Test handling of malformed JSON in WebSocket messages.
    Should FAIL if malformed JSON is not properly handled.
    """
    malformed_json = sample_websocket_messages['malformed_json']
    with pytest.raises((json.JSONDecodeError, ValueError)):
        json.loads(malformed_json)
    malformed_cases = ['{"type": "user_message"', '{"type": "user_message", "payload": }', '{"type": "user_message", "payload": {"text":}}', 'not json at all', '{"type": "user_message", "payload": {"text": "unterminated string}']
    for malformed in malformed_cases:
        with pytest.raises((json.JSONDecodeError, ValueError)):
            json.loads(malformed)

def test_message_serialization_consistency(sample_websocket_messages):
    """
    Test that messages serialize and deserialize consistently.
    Should FAIL if serialization/deserialization is not symmetric.
    """
    valid_msg = sample_websocket_messages['user_message']
    ws_msg = WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload=valid_msg['payload'], sender=valid_msg.get('sender'), timestamp=valid_msg.get('timestamp'))
    serialized = ws_msg.model_dump()
    try:
        deserialized = WebSocketMessage(**serialized)
        assert deserialized.type == ws_msg.type
        assert deserialized.payload == ws_msg.payload
        assert deserialized.sender == ws_msg.sender
    except Exception as e:
        pytest.fail(f'Message serialization/deserialization failed: {e}')

def test_json_serialization_edge_cases():
    """
    Test JSON serialization edge cases that can cause issues.
    Should FAIL if edge cases are not handled properly.
    """
    edge_case_payloads = [{'text': 'Message with "quotes" and \'apostrophes\''}, {'text': 'Message with\nnewlines\tand\ttabs'}, {'text': 'Message with unicode: [U+1F680] [U+00F1] [U+00A9]  infinity '}, {'text': 'Message with escaped chars: \\n \\t \\"'}, {'metadata': {'nested': {'deeply': {'nested': 'value'}}}}, {'array_field': [1, 'two', {'three': 3}, None]}, {'timestamp': datetime.now(timezone.utc).isoformat()}]
    for payload in edge_case_payloads:
        try:
            json_str = json.dumps(payload)
            deserialized = json.loads(json_str)
            assert deserialized == payload or str(deserialized) == str(payload)
        except Exception as e:
            pytest.fail(f'JSON serialization failed for payload {payload}: {e}')

def test_timestamp_serialization_consistency():
    """
    Test timestamp serialization consistency between frontend and backend.
    Should FAIL if timestamp formats are inconsistent.
    """
    timestamp_formats = [datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'), datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), '2025-01-23T10:00:00.000Z', '2025-01-23T10:00:00+00:00']
    for ts_format in timestamp_formats:
        try:
            msg = WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload={'text': 'Test', 'thread_id': 'thread_123'}, timestamp=ts_format)
            serialized = msg.model_dump()
            WebSocketMessage(**serialized)
        except Exception as e:
            pytest.fail(f"Timestamp format '{ts_format}' caused error: {e}")

def test_null_and_undefined_handling():
    """
    Test handling of null/undefined values from frontend.
    Should FAIL if null/undefined values cause unexpected errors.
    """
    null_scenarios = [{'type': 'user_message', 'payload': None}, {'type': 'user_message', 'payload': {'text': None, 'thread_id': 'thread_123'}}, {'type': 'user_message', 'payload': {'text': 'Hello', 'thread_id': None}}, {'type': 'agent_update', 'payload': {'agent_id': 'agent_123', 'status': None}}, {'type': 'user_message', 'payload': {'text': '', 'thread_id': 'thread_123'}}]
    for scenario in null_scenarios:
        try:
            WebSocketMessage(**scenario)
        except (ValueError, TypeError) as e:
            assert 'required' in str(e).lower() or 'none' in str(e).lower() or 'null' in str(e).lower()
        except Exception as e:
            pytest.fail(f'Unexpected error handling null scenario {scenario}: {e}')

def test_unicode_and_encoding_issues():
    """
    Test handling of unicode and encoding issues in messages.
    Should FAIL if unicode causes encoding/decoding errors.
    """
    unicode_test_cases = [{'text': '[U+1F680] Rocket emoji test'}, {'text': '[U+00D1]o[U+00F1]o ni[U+00F1]o - Spanish characters'}, {'text': '[U+4E2D][U+6587][U+6D4B][U+8BD5] - Chinese characters'}, {'text': 'Pucck[U+0438][U+0439] tekct - Russian text'}, {'text': ' CELEBRATION: [U+1F38A][U+1F388] Multiple emojis  FIRE: [U+1F4AF] LIGHTNING: '}, {'text': 'Math symbols:  infinity  [U+2211] [U+2206] [U+222B]  !=   <=   >= '}, {'text': 'Control chars: \x00\x01\x02\x03'}]
    for test_case in unicode_test_cases:
        try:
            payload = UserMessagePayload(text=test_case['text'], thread_id='thread_123')
            msg = WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload=payload.model_dump())
            json_str = json.dumps(msg.model_dump(), ensure_ascii=False)
            parsed_back = json.loads(json_str)
            assert parsed_back['payload']['text'] == test_case['text']
        except Exception as e:
            pytest.fail(f"Unicode handling failed for '{test_case['text']}': {e}")

def test_concurrent_message_validation():
    """
    Test message validation under concurrent access.
    Should FAIL if validation is not thread-safe.
    """
    import threading
    import time
    results = []
    errors = []

    def validate_message(msg_id: int):
        try:
            msg = WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload={'text': f'Message {msg_id}', 'thread_id': f'thread_{msg_id}'})
            results.append(msg_id)
            time.sleep(0.01)
        except Exception as e:
            errors.append((msg_id, str(e)))
    threads = []
    for i in range(10):
        thread = threading.Thread(target=validate_message, args=(i,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        pytest.fail(f'Concurrent validation errors: {errors}')
    assert len(results) == 10, f'Expected 10 successful validations, got {len(results)}'

def test_memory_leak_prevention():
    """
    Test that repeated message creation/validation doesn't leak memory.
    Should FAIL if there are memory leaks in validation logic.
    """
    import gc
    import psutil
    import os
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    messages = []
    for i in range(1000):
        try:
            msg = WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload={'text': f'Test message {i}' * 100, 'thread_id': f'thread_{i}', 'metadata': {f'key_{j}': f'value_{j}' for j in range(10)}})
            messages.append(msg)
        except Exception as e:
            pytest.fail(f'Failed to create message {i}: {e}')
    messages.clear()
    gc.collect()
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    if memory_increase > 100 * 1024 * 1024:
        pytest.fail(f'Potential memory leak detected: {memory_increase / (1024 * 1024):.2f}MB increase')

def test_websocket_protocol_compliance():
    """
    Test WebSocket protocol compliance for message structure.
    Should FAIL if messages don't comply with WebSocket standards.
    """
    required_fields = ['type', 'payload']
    optional_fields = ['sender', 'timestamp']
    valid_msg = WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload={'text': 'Hello', 'thread_id': 'thread_123'})
    msg_dict = valid_msg.model_dump()
    for field in required_fields:
        assert field in msg_dict, f"Required field '{field}' missing from message"
    try:
        json_str = json.dumps(msg_dict)
        parsed_back = json.loads(json_str)
        assert parsed_back == msg_dict
    except Exception as e:
        pytest.fail(f'Message not JSON serializable: {e}')
    MAX_MESSAGE_SIZE = 64 * 1024
    if len(json_str.encode('utf-8')) > MAX_MESSAGE_SIZE:
        pytest.fail(f'Message too large: {len(json_str)} bytes > {MAX_MESSAGE_SIZE} bytes')

def test_heartbeat_ping_pong_protocol():
    """
    Test ping/pong heartbeat protocol implementation.
    Should FAIL if ping/pong handling is incorrect.
    """
    ping_msg = WebSocketMessage(type=WebSocketMessageType.PING, payload={'timestamp': datetime.now(timezone.utc).isoformat()})
    pong_msg = WebSocketMessage(type=WebSocketMessageType.PONG, payload={'timestamp': datetime.now(timezone.utc).isoformat()})
    try:
        ping_dict = ping_msg.model_dump()
        pong_dict = pong_msg.model_dump()
        assert ping_dict['type'] == 'ping'
        assert pong_dict['type'] == 'pong'
    except Exception as e:
        pytest.fail(f'Ping/pong protocol validation failed: {e}')

def test_error_message_protocol():
    """
    Test error message protocol compliance.
    Should FAIL if error messages don't follow standard format.
    """
    error_payload = {'error_code': 'VALIDATION_ERROR', 'error_message': 'Invalid message type', 'details': {'field': 'type', 'value': 'unknown_type'}, 'timestamp': datetime.now(timezone.utc).isoformat()}
    try:
        error_msg = WebSocketMessage(type=WebSocketMessageType.ERROR, payload=error_payload)
        error_dict = error_msg.model_dump()
        payload = error_dict['payload']
        required_error_fields = ['error_code', 'error_message']
        for field in required_error_fields:
            if field not in payload:
                pytest.fail(f'Error message missing required field: {field}')
    except Exception as e:
        pytest.fail(f'Error message protocol validation failed: {e}')

@pytest.mark.asyncio
async def test_message_handler_type_routing():
    """
    Test that message handlers receive correctly typed messages.
    Should FAIL if type routing is incorrect.
    """
    handled_messages = []

    async def mock_handler(message: WebSocketMessage):
        handled_messages.append(message)
    test_messages = [WebSocketMessage(type=WebSocketMessageType.USER_MESSAGE, payload={'text': 'Hello', 'thread_id': 'thread_123'}), WebSocketMessage(type=WebSocketMessageType.START_AGENT, payload={'agent_type': 'chat', 'thread_id': 'thread_123'}), WebSocketMessage(type=WebSocketMessageType.STOP_AGENT, payload={'reason': 'user_requested'})]
    for msg in test_messages:
        try:
            await mock_handler(msg)
        except Exception as e:
            pytest.fail(f'Message handler failed for type {msg.type}: {e}')
    assert len(handled_messages) == len(test_messages)
    handled_types = [msg.type for msg in handled_messages]
    expected_types = [msg.type for msg in test_messages]
    assert handled_types == expected_types, 'Message type routing failed'

@pytest.mark.asyncio
async def test_async_message_validation_performance():
    """
    Test performance of async message validation.
    Should FAIL if async validation is too slow.
    """
    import time

    async def validate_async_message(msg_data: Dict[str, Any]) -> bool:
        """Simulate async validation"""
        try:
            WebSocketMessage(**msg_data)
            await asyncio.sleep(0.001)
            return True
        except:
            return False
    test_data = [{'type': 'user_message', 'payload': {'text': f'Message {i}', 'thread_id': 'thread_123'}} for i in range(100)]
    start_time = time.time()
    tasks = [validate_async_message(msg) for msg in test_data]
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    duration = end_time - start_time
    if duration > 2.0:
        pytest.fail(f'Async validation too slow: {duration:.2f}s for {len(test_data)} messages')
    assert all(results), f'Some messages failed validation: {sum((1 for r in results if not r))} failures'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')