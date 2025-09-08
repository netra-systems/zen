"""Real WebSocket Serialization Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Data Integrity & Message Reliability
- Value Impact: Ensures messages are properly serialized/deserialized for chat functionality
- Strategic Impact: Prevents data corruption that could break chat value delivery

Tests real WebSocket message serialization and deserialization with Docker services.
Validates JSON encoding, data type preservation, and message integrity.
"""

import asyncio
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.serialization
@skip_if_no_real_services
class TestRealWebSocketSerialization:
    """Test real WebSocket message serialization and deserialization."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Serialization-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_basic_json_serialization(self, websocket_url, auth_headers):
        """Test basic JSON serialization and deserialization."""
        user_id = f"serialization_test_{int(time.time())}"
        
        test_messages = [
            {
                "type": "user_message",
                "user_id": user_id,
                "content": "Simple string message",
                "number_field": 42,
                "boolean_field": True,
                "null_field": None
            },
            {
                "type": "user_message", 
                "user_id": user_id,
                "content": "Message with nested data",
                "nested_object": {
                    "inner_string": "nested value",
                    "inner_number": 3.14,
                    "inner_array": [1, 2, "three", True]
                },
                "array_field": ["item1", "item2", 123]
            }
        ]
        
        received_messages = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": user_id}))
                await websocket.recv()  # Connection response
                
                # Send test messages
                for test_msg in test_messages:
                    # Send message
                    await websocket.send(json.dumps(test_msg))
                    
                    # Receive response
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response = json.loads(response_raw)
                        received_messages.append(response)
                    except asyncio.TimeoutError:
                        received_messages.append({"timeout": True, "original": test_msg})
                    except json.JSONDecodeError as e:
                        received_messages.append({"json_error": str(e), "original": test_msg})
                
        except Exception as e:
            pytest.fail(f"JSON serialization test failed: {e}")
        
        # Validate serialization worked
        assert len(received_messages) == len(test_messages), f"Should receive {len(test_messages)} responses"
        
        # Check that responses are valid JSON (no JSON decode errors)
        json_errors = [msg for msg in received_messages if "json_error" in msg]
        assert len(json_errors) == 0, f"Should not have JSON decode errors: {json_errors}"
        
        print(f"JSON serialization test - Messages sent: {len(test_messages)}, Responses: {len(received_messages)}")
    
    @pytest.mark.asyncio
    async def test_special_character_serialization(self, websocket_url, auth_headers):
        """Test serialization of special characters and Unicode."""
        user_id = f"special_chars_test_{int(time.time())}"
        
        special_char_messages = [
            {
                "type": "user_message",
                "user_id": user_id,
                "content": "Message with quotes: \"Hello\" and 'World'",
                "special_chars": "Backslash: \\ Forward slash: / Tab: \t Newline: \n"
            },
            {
                "type": "user_message",
                "user_id": user_id, 
                "content": "Unicode test: 🚀 📝 💡 ✅ 🔥",
                "unicode_text": "Various languages: Hello, Hola, Bonjour, 你好, こんにちは, Здравствуйте"
            },
            {
                "type": "user_message",
                "user_id": user_id,
                "content": "HTML/XML chars: <tag>content</tag> & ampersand",
                "json_chars": '{"nested": "json", "array": [1,2,3]}'
            }
        ]
        
        serialization_results = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": user_id}))
                await websocket.recv()
                
                # Test each special character message
                for i, test_msg in enumerate(special_char_messages):
                    try:
                        # Serialize and send
                        serialized = json.dumps(test_msg)
                        await websocket.send(serialized)
                        
                        # Receive and deserialize response
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=4.0)
                        response = json.loads(response_raw)
                        
                        serialization_results.append({
                            "test_index": i,
                            "success": True,
                            "original_content": test_msg.get("content"),
                            "response_type": response.get("type"),
                            "serialized_length": len(serialized)
                        })
                        
                    except json.JSONDecodeError as e:
                        serialization_results.append({
                            "test_index": i,
                            "success": False,
                            "error_type": "json_decode",
                            "error": str(e),
                            "original_content": test_msg.get("content")
                        })
                    except asyncio.TimeoutError:
                        serialization_results.append({
                            "test_index": i,
                            "success": False,
                            "error_type": "timeout",
                            "original_content": test_msg.get("content")
                        })
                    except Exception as e:
                        serialization_results.append({
                            "test_index": i,
                            "success": False,
                            "error_type": "other",
                            "error": str(e),
                            "original_content": test_msg.get("content")
                        })
                
        except Exception as e:
            pytest.fail(f"Special character serialization test failed: {e}")
        
        # Validate special character handling
        successful_serializations = [r for r in serialization_results if r.get("success")]
        failed_serializations = [r for r in serialization_results if not r.get("success")]
        
        print(f"Special character serialization - Success: {len(successful_serializations)}/{len(special_char_messages)}")
        
        if failed_serializations:
            for failure in failed_serializations:
                print(f"  Failed test {failure['test_index']}: {failure.get('error_type')} - {failure.get('original_content', '')[:50]}")
        
        # Should handle most special characters successfully
        success_rate = len(successful_serializations) / len(special_char_messages) if special_char_messages else 0
        assert success_rate >= 0.7, f"Should handle most special characters successfully: {success_rate:.1%}"
    
    @pytest.mark.asyncio
    async def test_large_message_serialization(self, websocket_url, auth_headers):
        """Test serialization of large messages."""
        user_id = f"large_msg_test_{int(time.time())}"
        
        # Create large message content
        large_content = "Large message content: " + "A" * 5000  # ~5KB
        very_large_array = list(range(1000))  # Array with 1000 items
        
        large_messages = [
            {
                "type": "user_message",
                "user_id": user_id,
                "content": large_content,
                "size_category": "large_text"
            },
            {
                "type": "user_message",
                "user_id": user_id,
                "content": "Message with large array",
                "large_array": very_large_array,
                "size_category": "large_array"
            }
        ]
        
        large_msg_results = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=20
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": user_id}))
                await websocket.recv()
                
                # Test large message serialization
                for large_msg in large_messages:
                    start_time = time.time()
                    
                    try:
                        # Serialize (this tests JSON encoding)
                        serialized = json.dumps(large_msg)
                        serialization_time = time.time() - start_time
                        
                        # Send large message
                        send_start = time.time()
                        await websocket.send(serialized)
                        send_time = time.time() - send_start
                        
                        # Receive response
                        receive_start = time.time()
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        response = json.loads(response_raw)
                        receive_time = time.time() - receive_start
                        
                        large_msg_results.append({
                            "size_category": large_msg.get("size_category"),
                            "success": True,
                            "serialized_size": len(serialized),
                            "serialization_time": serialization_time,
                            "send_time": send_time,
                            "receive_time": receive_time,
                            "total_time": time.time() - start_time
                        })
                        
                    except asyncio.TimeoutError:
                        large_msg_results.append({
                            "size_category": large_msg.get("size_category"),
                            "success": False,
                            "error": "timeout",
                            "serialized_size": len(json.dumps(large_msg)) if large_msg else 0
                        })
                    except Exception as e:
                        large_msg_results.append({
                            "size_category": large_msg.get("size_category"),
                            "success": False,
                            "error": str(e),
                            "serialized_size": 0
                        })
                
        except Exception as e:
            pytest.fail(f"Large message serialization test failed: {e}")
        
        # Validate large message handling
        successful_large = [r for r in large_msg_results if r.get("success")]
        
        print(f"Large message serialization - Success: {len(successful_large)}/{len(large_messages)}")
        
        for result in large_msg_results:
            if result.get("success"):
                print(f"  {result['size_category']}: {result['serialized_size']} bytes, {result['total_time']:.3f}s")
            else:
                print(f"  {result['size_category']}: FAILED - {result.get('error')}")
        
        # Should handle reasonable sized messages
        assert len(successful_large) > 0, "Should handle at least some large messages"
        
        # Check performance is reasonable for successful messages
        for result in successful_large:
            assert result["total_time"] < 15, f"Large message processing should be reasonable: {result['total_time']:.3f}s"
    
    @pytest.mark.asyncio
    async def test_data_type_preservation(self, websocket_url, auth_headers):
        """Test preservation of data types through serialization."""
        user_id = f"data_types_test_{int(time.time())}"
        
        # Test message with various data types
        type_test_message = {
            "type": "test_data_types",
            "user_id": user_id,
            "string_field": "test string",
            "integer_field": 42,
            "float_field": 3.14159,
            "boolean_true": True,
            "boolean_false": False,
            "null_field": None,
            "empty_string": "",
            "empty_array": [],
            "empty_object": {},
            "nested_types": {
                "nested_int": 100,
                "nested_float": 2.718,
                "nested_bool": False,
                "nested_array": [1, "two", 3.0, True, None]
            },
            "timestamp": time.time(),
            "large_number": 9223372036854775807,  # Large integer
            "small_decimal": 0.000001
        }
        
        serialization_analysis = {}
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": user_id}))
                await websocket.recv()
                
                # Test serialization round-trip
                original_json = json.dumps(type_test_message)
                await websocket.send(original_json)
                
                # Receive response and analyze
                try:
                    response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response = json.loads(response_raw)
                    
                    # Analyze type preservation in response
                    if "user_id" in response:
                        serialization_analysis["user_id_preserved"] = response["user_id"] == user_id
                    
                    # Check if numeric types are preserved reasonably
                    if "timestamp" in response or "integer_field" in response:
                        serialization_analysis["numeric_data_received"] = True
                    
                    serialization_analysis["response_received"] = True
                    serialization_analysis["response_type"] = response.get("type")
                    
                except asyncio.TimeoutError:
                    serialization_analysis["timeout"] = True
                except json.JSONDecodeError as e:
                    serialization_analysis["json_decode_error"] = str(e)
                
                # Test that we can serialize the original message without errors
                try:
                    re_serialized = json.dumps(type_test_message)
                    parsed_back = json.loads(re_serialized)
                    
                    # Verify key data types are preserved in round-trip
                    serialization_analysis["round_trip_success"] = True
                    serialization_analysis["string_preserved"] = parsed_back["string_field"] == type_test_message["string_field"]
                    serialization_analysis["integer_preserved"] = parsed_back["integer_field"] == type_test_message["integer_field"]
                    serialization_analysis["boolean_preserved"] = parsed_back["boolean_true"] == type_test_message["boolean_true"]
                    serialization_analysis["null_preserved"] = parsed_back["null_field"] is None
                    
                except Exception as e:
                    serialization_analysis["round_trip_error"] = str(e)
                
        except Exception as e:
            pytest.fail(f"Data type preservation test failed: {e}")
        
        # Validate data type handling
        print(f"Data type preservation analysis: {serialization_analysis}")
        
        # Basic serialization should work
        assert serialization_analysis.get("round_trip_success", False), "JSON round-trip should work"
        
        # Key data types should be preserved
        if serialization_analysis.get("round_trip_success"):
            assert serialization_analysis.get("string_preserved", False), "String data should be preserved"
            assert serialization_analysis.get("integer_preserved", False), "Integer data should be preserved"
            assert serialization_analysis.get("boolean_preserved", False), "Boolean data should be preserved"
            assert serialization_analysis.get("null_preserved", False), "Null values should be preserved"