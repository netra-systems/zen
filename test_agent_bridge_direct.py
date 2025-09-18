#!/usr/bin/env python3
"""
Direct test of AgentWebSocketBridge configure() method to validate the fix works.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

def test_configure_method():
    """Test both calling patterns for the configure method."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

        # Test 1: Import successful
        print("PASS: Import successful")

        # Test 2: Basic instantiation
        bridge = AgentWebSocketBridge()
        print("PASS: Bridge instantiation successful")

        # Test 3: WebSocket pattern (positional arguments)
        try:
            bridge.configure(None, 'run123', 'thread456', 'user789')
            print("PASS: WebSocket pattern works (positional arguments)")
        except Exception as e:
            print(f"FAIL: WebSocket pattern failed: {e}")
            return False

        # Test 4: Legacy pattern (keyword argument)
        try:
            bridge.configure(connection_pool=None)
            print("PASS: Legacy pattern works (keyword argument)")
        except Exception as e:
            print(f"FAIL: Legacy pattern failed: {e}")
            return False

        # Test 5: Mixed pattern
        try:
            bridge.configure(None, run_id='run789', thread_id='thread789', user_id='user789')
            print("PASS: Mixed pattern works (positional + keyword)")
        except Exception as e:
            print(f"FAIL: Mixed pattern failed: {e}")
            return False

        return True

    except ImportError as e:
        print(f"FAIL: Import failed: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("Testing AgentWebSocketBridge configure() method fix...")
    success = test_configure_method()
    if success:
        print("\nSUCCESS: All tests passed! The configure() fix works correctly.")
    else:
        print("\nFAIL: Some tests failed. The fix needs attention.")
        sys.exit(1)