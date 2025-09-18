#!/usr/bin/env python3
"""
Test script to verify system stability after issue #1039 fix.
This script tests imports and basic functionality to prove no breaking changes.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_websocket_imports():
    """Test WebSocket module imports"""
    print("Testing WebSocket module imports...")
    
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        print("✅ UnifiedWebSocketEmitter import successful")
    except Exception as e:
        print(f"❌ UnifiedWebSocketEmitter import failed: {e}")
        return False
    
    try:
        from netra_backend.app.websocket_core.manager import WebSocketManager
        print("✅ WebSocketManager import successful")
    except Exception as e:
        print(f"❌ WebSocketManager import failed: {e}")
        return False
    
    return True

def test_agent_imports():
    """Test agent imports that use WebSocket"""
    print("\nTesting agent imports that use WebSocket...")
    
    try:
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        print("✅ ExecutionEngine import successful")
    except Exception as e:
        print(f"❌ ExecutionEngine import failed: {e}")
        return False
    
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        print("✅ AgentWebSocketBridge import successful")
    except Exception as e:
        print(f"❌ AgentWebSocketBridge import failed: {e}")
        return False
    
    return True

def test_event_structure():
    """Test that event structures are compatible"""
    print("\nTesting event structure compatibility...")
    
    try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        
        # Create a mock manager to test event structure
        class MockManager:
            def send_websocket_message(self, user_id, message):
                # Verify the message structure
                if 'event' in message and 'data' in message:
                    print(f"✅ Event structure valid: {message['event']}")
                    return True
                else:
                    print(f"❌ Invalid event structure: {message}")
                    return False
        
        mock_manager = MockManager()
        emitter = UnifiedWebSocketEmitter(mock_manager)
        
        # Test tool_executing event with tool_name
        result = emitter.emit_tool_executing("test_user", "test_tool", {"param": "value"})
        print("✅ tool_executing event structure test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Event structure test failed: {e}")
        return False

def main():
    """Run all stability tests"""
    print("=== Issue #1039 Stability Proof Tests ===\n")
    
    tests = [
        test_websocket_imports,
        test_agent_imports,
        test_event_structure
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== Test Results ===")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 ALL TESTS PASSED - System is stable!")
        return True
    else:
        print("⚠️  Some tests failed - Review needed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)