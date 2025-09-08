#!/usr/bin/env python3
"""Debug script to test message size calculation."""

import json
import sys
import os

# Add the netra_backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

# Create a simple test to debug the size issue
huge_payload = {"enormous_data": "x" * (11 * 1024 * 1024)}  # 11MB

# Simulate what WebSocketMessage.model_dump() would return
message_data = {
    "type": "agent_response_complete",
    "payload": huge_payload,
    "user_id": "user_123",
    "timestamp": 1234567890.0,
    "message_id": "test-id",
    "thread_id": None
}

message_json = json.dumps(message_data)
original_data = message_json.encode('utf-8')
original_size = len(original_data)

max_size_bytes = 10 * 1024 * 1024  # 10MB

print(f'Payload size: {len(huge_payload["enormous_data"]):,} bytes')
print(f'Message size: {original_size:,} bytes')
print(f'Max allowed size: {max_size_bytes:,} bytes')
print(f'Exceeds limit: {original_size > max_size_bytes}')
print(f'Difference: {original_size - max_size_bytes:,} bytes')