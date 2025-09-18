#!/usr/bin/env python3
"""
Direct integration test for AgentWebSocketBridge factory initialization
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

def test_factory_initialization():
    """Test factory initialization patterns work correctly."""
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge

        print("PASS: Factory imports successful")

        # Test 1: Basic factory function
        bridge1 = create_agent_websocket_bridge()
        assert isinstance(bridge1, AgentWebSocketBridge), "Factory should return AgentWebSocketBridge instance"
        print("PASS: Factory function creates bridge instance")

        # Test 2: Direct constructor
        bridge2 = AgentWebSocketBridge()
        assert isinstance(bridge2, AgentWebSocketBridge), "Constructor should return AgentWebSocketBridge instance"
        print("PASS: Direct constructor works")

        # Test 3: Configure after creation
        bridge2.configure(None, 'test-run', 'test-thread', 'test-user')
        print("PASS: Configure works after creation")

        # Test 4: Different instances are independent
        assert bridge1 is not bridge2, "Different instances should be independent"
        print("PASS: Factory creates independent instances")

        return True

    except ImportError as e:
        print(f"FAIL: Import failed: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("Testing AgentWebSocketBridge factory initialization...")
    success = test_factory_initialization()
    if success:
        print("\nSUCCESS: Factory initialization tests passed!")
    else:
        print("\nFAIL: Factory initialization tests failed.")
        sys.exit(1)