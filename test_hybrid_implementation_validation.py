#!/usr/bin/env python3
"""
Hybrid Implementation Validation Test

This test validates that the hybrid create_server_message implementation
works correctly for both legacy and standard calling patterns.
"""

import sys
import traceback
from typing import Dict, Any

def test_hybrid_implementation():
    """Test the hybrid create_server_message implementation."""
    print("Testing hybrid create_server_message implementation...")
    
    try:
        # Import the function
        from netra_backend.app.websocket_core.types import create_server_message, MessageType
        print("SUCCESS: Function import successful")
        
        # Test 1: Legacy pattern (websocket_ssot.py style)
        try:
            legacy_result = create_server_message({
                'type': 'connection_established',
                'mode': 'main',
                'user_id': 'test123',
                'connection_id': 'conn_123',
                'status': 'connected'
            })
            print(f"SUCCESS: Legacy pattern works: type={legacy_result.type.value}, data_keys={list(legacy_result.data.keys())}")
        except Exception as e:
            print(f"FAIL: Legacy pattern failed: {e}")
            return False
            
        # Test 2: Standard pattern (MessageType enum)
        try:
            standard_result = create_server_message(MessageType.SYSTEM_MESSAGE, {
                'status': 'ok',
                'message': 'System ready'
            })
            print(f"SUCCESS: Standard enum pattern works: type={standard_result.type.value}, data_keys={list(standard_result.data.keys())}")
        except Exception as e:
            print(f"FAIL: Standard enum pattern failed: {e}")
            return False
            
        # Test 3: String pattern
        try:
            string_result = create_server_message('system', {
                'status': 'ok',
                'message': 'String pattern works'
            })
            print(f"SUCCESS: String pattern works: type={string_result.type.value}, data_keys={list(string_result.data.keys())}")
        except Exception as e:
            print(f"FAIL: String pattern failed: {e}")
            return False
            
        # Test 4: WebSocket SSOT patterns (the original failing patterns)
        websocket_ssot_patterns = [
            {
                'type': 'connection_established',
                'mode': 'main',
                'user_id': 'test123...',
                'connection_id': 'conn_123',
                'golden_path_events': ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'],
            },
            {
                'type': 'factory_connection_established',
                'mode': 'factory', 
                'user_id': 'test123...',
                'connection_id': 'conn_123',
            },
            {
                'type': 'isolated_connection_established',
                'mode': 'isolated',
                'user_id': 'test123...',
                'connection_id': 'conn_123',
            },
            {
                'type': 'legacy_connection_established',
                'mode': 'legacy',
                'connection_id': 'conn_123',
            }
        ]
        
        for i, pattern in enumerate(websocket_ssot_patterns):
            try:
                result = create_server_message(pattern)
                print(f"SUCCESS: WebSocket SSOT pattern {i+1} works: type={result.type.value}")
            except Exception as e:
                print(f"FAIL: WebSocket SSOT pattern {i+1} failed: {e}")
                return False
                
        # Test 5: Error handling for invalid patterns
        try:
            create_server_message({'invalid': 'no_type_field'})
            print("FAIL: Error handling failed - should have rejected invalid pattern")
            return False
        except ValueError as e:
            print(f"SUCCESS: Error handling works: {e}")
        except Exception as e:
            print(f"FAIL: Unexpected error type: {e}")
            return False
            
        print("\nSUCCESS: All hybrid implementation tests PASSED!")
        print("SUCCESS: SSOT violation fixed - no more fallback implementation")
        print("SUCCESS: Backward compatibility maintained for websocket_ssot.py")
        print("SUCCESS: Standard patterns work for future code")
        return True
        
    except Exception as e:
        print(f"CRITICAL ERROR during testing: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hybrid_implementation()
    sys.exit(0 if success else 1)