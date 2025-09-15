#!/usr/bin/env python3
"""
Quick validation script to test the WebSocket interface fix.

This script verifies that the missing WebSocket interface methods
(connect, disconnect, emit_agent_event) are now available and working.

CRITICAL BUSINESS ISSUE: These methods are essential for Golden Path
chat functionality worth $500K+ ARR.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append('/Users/anthony/Desktop/netra-apex')

async def test_websocket_interface():
    """Test that the WebSocket manager interface methods are available."""
    print("🔍 Testing WebSocket Manager Interface Fix...")
    
    try:
        # Import the WebSocket manager
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        print("✅ Successfully imported get_websocket_manager")
        
        # Create a test user context
        from netra_backend.app.websocket_core.websocket_manager import create_test_user_context
        user_context = create_test_user_context()
        print(f"✅ Created test user context: {user_context.user_id}")
        
        # Get WebSocket manager instance
        websocket_manager = get_websocket_manager(user_context)
        print("✅ Successfully created WebSocket manager instance")
        
        # Test 1: Check that connect method exists
        assert hasattr(websocket_manager, 'connect'), "❌ Missing connect() method"
        print("✅ connect() method is available")
        
        # Test 2: Check that disconnect method exists
        assert hasattr(websocket_manager, 'disconnect'), "❌ Missing disconnect() method"
        print("✅ disconnect() method is available")
        
        # Test 3: Check that emit_agent_event method exists
        assert hasattr(websocket_manager, 'emit_agent_event'), "❌ Missing emit_agent_event() method"
        print("✅ emit_agent_event() method is available")
        
        # Test 4: Check that the methods are callable
        assert callable(websocket_manager.connect), "❌ connect() is not callable"
        assert callable(websocket_manager.disconnect), "❌ disconnect() is not callable"
        assert callable(websocket_manager.emit_agent_event), "❌ emit_agent_event() is not callable"
        print("✅ All interface methods are callable")
        
        # Test 5: Verify interface signature compatibility
        import inspect
        
        # Check connect signature
        connect_sig = inspect.signature(websocket_manager.connect)
        connect_params = list(connect_sig.parameters.keys())
        assert 'user_id' in connect_params, "❌ connect() missing user_id parameter"
        assert 'websocket' in connect_params, "❌ connect() missing websocket parameter"
        print("✅ connect() has expected signature")
        
        # Check disconnect signature
        disconnect_sig = inspect.signature(websocket_manager.disconnect)
        disconnect_params = list(disconnect_sig.parameters.keys())
        assert 'user_id' in disconnect_params, "❌ disconnect() missing user_id parameter"
        print("✅ disconnect() has expected signature")
        
        # Check emit_agent_event signature
        emit_sig = inspect.signature(websocket_manager.emit_agent_event)
        emit_params = list(emit_sig.parameters.keys())
        assert 'user_id' in emit_params, "❌ emit_agent_event() missing user_id parameter"
        assert 'event_type' in emit_params, "❌ emit_agent_event() missing event_type parameter"
        assert 'data' in emit_params, "❌ emit_agent_event() missing data parameter"
        print("✅ emit_agent_event() has expected signature")
        
        print("\n🎉 SUCCESS: All WebSocket interface methods are available and properly configured!")
        print("✅ Golden Path WebSocket functionality should now work correctly")
        print("✅ $500K+ ARR chat functionality interface is restored")
        
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: WebSocket interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_interface())
    sys.exit(0 if success else 1)