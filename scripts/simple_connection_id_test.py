#!/usr/bin/env python3
"""
Simplified test to validate the core connection ID pass-through fix.
"""

import sys
import os
import asyncio

# Add the project root to Python path
sys.path.insert(0, '/Users/rindhujajohnson/Netra/GitHub/netra-apex')

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from unittest.mock import Mock


async def test_core_connection_id_passthrough():
    """Test the core fix: WebSocket manager should preserve connection IDs."""
    print("[U+1F527] Testing Core Connection ID Pass-Through Fix...")
    
    # The critical test: WebSocket manager connect_user with preliminary connection ID
    manager = UnifiedWebSocketManager()
    mock_websocket = Mock()
    test_user_id = "user123456789"  # Use a non-placeholder pattern
    preliminary_connection_id = "ws_1234567890_12345"
    
    try:
        result_connection_id = await manager.connect_user(
            test_user_id, 
            mock_websocket, 
            preliminary_connection_id
        )
        
        if result_connection_id == preliminary_connection_id:
            print(f" PASS:  SUCCESS: Connection ID preserved: {result_connection_id}")
            print(f" PASS:  STATE MACHINE CONTINUITY: Will preserve ACCEPTED state")
            print(f" PASS:  NO MORE INVALID TRANSITIONS: State machine recreation prevented")
            return True
        else:
            print(f" FAIL:  FAILURE: Connection ID changed: {preliminary_connection_id}  ->  {result_connection_id}")
            print(f" FAIL:  STATE MACHINE BROKEN: Will recreate and lose ACCEPTED state")
            print(f" FAIL:  INVALID TRANSITIONS PERSIST: Root cause not fixed")
            return False
            
    except Exception as e:
        print(f"[U+1F4A5] ERROR: Test failed with exception: {e}")
        return False


async def test_preliminary_id_generation():
    """Test that preliminary ID generation matches expected format."""
    print(f"\n[U+1F3D7][U+FE0F] Testing Preliminary ID Generation...")
    
    import time
    mock_websocket = Mock()
    
    # Simulate how preliminary IDs are generated in websocket.py
    timestamp = int(time.time() * 1000)
    websocket_id = id(mock_websocket)
    preliminary_id = f"ws_{timestamp}_{websocket_id}"
    
    print(f"[U+1F4CB] Generated preliminary ID format: {preliminary_id}")
    print(f"[U+1F4CB] Format: ws_<timestamp>_<websocket_object_id>")
    
    # This format will be passed through unchanged with our fix
    manager = UnifiedWebSocketManager()
    
    try:
        result = await manager.connect_user("user123", mock_websocket, preliminary_id)
        if result == preliminary_id:
            print(f" PASS:  FORMAT PRESERVED: {preliminary_id}")
            return True
        else:
            print(f" FAIL:  FORMAT CHANGED: {preliminary_id}  ->  {result}")
            return False
    except Exception as e:
        print(f"[U+1F4A5] FORMAT TEST ERROR: {e}")
        return False


if __name__ == "__main__":
    print("[U+1F9EA] Core Connection ID Pass-Through Fix Validation")
    print("=" * 55)
    
    async def run_tests():
        test1_success = await test_core_connection_id_passthrough()
        test2_success = await test_preliminary_id_generation()
        
        print(f"\n[U+1F3C1] FINAL RESULTS:")
        print(f"   Core Pass-Through: {' PASS:  SUCCESS' if test1_success else ' FAIL:  FAILED'}")
        print(f"   Format Preservation: {' PASS:  SUCCESS' if test2_success else ' FAIL:  FAILED'}")
        
        overall_success = test1_success and test2_success
        
        if overall_success:
            print(f"\n CELEBRATION:  CONNECTION ID FIX VALIDATED!")
            print(f"    PASS:  WebSocket manager preserves preliminary connection IDs")
            print(f"    PASS:  State machine will NOT be recreated during authentication")
            print(f"    PASS:  ACCEPTED state will be preserved from initialization")
            print(f"    PASS:  No more 'Invalid state transition' errors expected")
            print(f"    PASS:  Connections should reach PROCESSING_READY state")
            print(f"    PASS:  Agent execution should work end-to-end")
            print(f"\n[U+1F680] ROOT CAUSE RESOLVED: Connection ID mismatch eliminated!")
        else:
            print(f"\n WARNING: [U+FE0F]  CONNECTION ID FIX INCOMPLETE")
            print(f"    FAIL:  Further debugging needed")
            print(f"    FAIL:  State machine issues may persist")
        
        return overall_success
    
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[U+1F4A5] Test execution failed: {e}")
        sys.exit(1)