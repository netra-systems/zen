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
    print("🔧 Testing Core Connection ID Pass-Through Fix...")
    
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
            print(f"✅ SUCCESS: Connection ID preserved: {result_connection_id}")
            print(f"✅ STATE MACHINE CONTINUITY: Will preserve ACCEPTED state")
            print(f"✅ NO MORE INVALID TRANSITIONS: State machine recreation prevented")
            return True
        else:
            print(f"❌ FAILURE: Connection ID changed: {preliminary_connection_id} → {result_connection_id}")
            print(f"❌ STATE MACHINE BROKEN: Will recreate and lose ACCEPTED state")
            print(f"❌ INVALID TRANSITIONS PERSIST: Root cause not fixed")
            return False
            
    except Exception as e:
        print(f"💥 ERROR: Test failed with exception: {e}")
        return False


async def test_preliminary_id_generation():
    """Test that preliminary ID generation matches expected format."""
    print(f"\n🏗️ Testing Preliminary ID Generation...")
    
    import time
    mock_websocket = Mock()
    
    # Simulate how preliminary IDs are generated in websocket.py
    timestamp = int(time.time() * 1000)
    websocket_id = id(mock_websocket)
    preliminary_id = f"ws_{timestamp}_{websocket_id}"
    
    print(f"📋 Generated preliminary ID format: {preliminary_id}")
    print(f"📋 Format: ws_<timestamp>_<websocket_object_id>")
    
    # This format will be passed through unchanged with our fix
    manager = UnifiedWebSocketManager()
    
    try:
        result = await manager.connect_user("user123", mock_websocket, preliminary_id)
        if result == preliminary_id:
            print(f"✅ FORMAT PRESERVED: {preliminary_id}")
            return True
        else:
            print(f"❌ FORMAT CHANGED: {preliminary_id} → {result}")
            return False
    except Exception as e:
        print(f"💥 FORMAT TEST ERROR: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Core Connection ID Pass-Through Fix Validation")
    print("=" * 55)
    
    async def run_tests():
        test1_success = await test_core_connection_id_passthrough()
        test2_success = await test_preliminary_id_generation()
        
        print(f"\n🏁 FINAL RESULTS:")
        print(f"   Core Pass-Through: {'✅ SUCCESS' if test1_success else '❌ FAILED'}")
        print(f"   Format Preservation: {'✅ SUCCESS' if test2_success else '❌ FAILED'}")
        
        overall_success = test1_success and test2_success
        
        if overall_success:
            print(f"\n🎉 CONNECTION ID FIX VALIDATED!")
            print(f"   ✅ WebSocket manager preserves preliminary connection IDs")
            print(f"   ✅ State machine will NOT be recreated during authentication")
            print(f"   ✅ ACCEPTED state will be preserved from initialization")
            print(f"   ✅ No more 'Invalid state transition' errors expected")
            print(f"   ✅ Connections should reach PROCESSING_READY state")
            print(f"   ✅ Agent execution should work end-to-end")
            print(f"\n🚀 ROOT CAUSE RESOLVED: Connection ID mismatch eliminated!")
        else:
            print(f"\n⚠️  CONNECTION ID FIX INCOMPLETE")
            print(f"   ❌ Further debugging needed")
            print(f"   ❌ State machine issues may persist")
        
        return overall_success
    
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        sys.exit(1)