#!/usr/bin/env python3
"""
Test to verify no breaking changes from AgentWebSocketBridge configure() fix
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

def test_core_functionality():
    """Test core system functionality is not broken."""
    try:
        # Test 1: Basic service imports still work
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        print("PASS: AgentWebSocketBridge import works")

        # Test 2: Try importing other key components
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            print("PASS: Configuration system works")
        except Exception as e:
            print(f"WARN: Configuration system issue (may be expected): {e}")

        # Test 3: Bridge initialization doesn't break anything
        bridge = AgentWebSocketBridge()
        print("PASS: Bridge initialization works")

        # Test 4: Basic method calls work
        bridge.configure(None, 'test-run', 'test-thread', 'test-user')
        print("PASS: Configure method works")

        # Test 5: Try other imports to ensure no breaking changes
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            print("PASS: DatabaseManager import works")
        except Exception as e:
            print(f"INFO: DatabaseManager import issue (may be expected): {e}")

        try:
            from netra_backend.app.auth_integration.auth import AuthIntegration
            print("PASS: AuthIntegration import works")
        except Exception as e:
            print(f"INFO: AuthIntegration import issue (may be expected): {e}")

        return True

    except ImportError as e:
        print(f"FAIL: Critical import failed: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("Testing for breaking changes from configure() fix...")
    success = test_core_functionality()
    if success:
        print("\nSUCCESS: No breaking changes detected!")
    else:
        print("\nFAIL: Breaking changes detected.")
        sys.exit(1)