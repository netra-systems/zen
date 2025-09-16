#!/usr/bin/env python3
"""Temporary script to test import integrity for Issue #1176 validation"""

def test_factory_imports():
    """Test that new factory classes import correctly"""
    try:
        from netra_backend.app.factories import websocket_bridge_factory
        print("✅ Factory import: OK")

        # Test specific classes exist
        assert hasattr(websocket_bridge_factory, 'WebSocketBridgeFactory')
        assert hasattr(websocket_bridge_factory, 'WebSocketConnectionBridge')
        assert hasattr(websocket_bridge_factory, 'WebSocketEventBridge')
        print("✅ Factory classes available: OK")

    except Exception as e:
        print(f"❌ Factory import failed: {e}")
        return False
    return True

def test_backward_compatibility():
    """Test backward compatibility import path"""
    try:
        from netra_backend.app.services import websocket_bridge_factory
        print("✅ Backward compatibility import: OK")

        # Verify it has the same classes
        assert hasattr(websocket_bridge_factory, 'WebSocketBridgeFactory')
        print("✅ Backward compatibility classes: OK")

    except Exception as e:
        print(f"❌ Backward compatibility failed: {e}")
        return False
    return True

def test_websocket_manager():
    """Test existing WebSocket manager still imports"""
    try:
        from netra_backend.app.websocket_core.manager import WebSocketManager
        print("✅ WebSocket manager import: OK")
    except Exception as e:
        print(f"❌ WebSocket manager import failed: {e}")
        return False
    return True

def test_app_state_contracts():
    """Test app state contracts import"""
    try:
        from netra_backend.app.core.app_state_contracts import validate_app_state_contracts
        print("✅ App state contracts import: OK")
    except Exception as e:
        print(f"❌ App state contracts import failed: {e}")
        return False
    return True

if __name__ == "__main__":
    print("=== Issue #1176 Import Integrity Validation ===")

    all_passed = True
    all_passed &= test_factory_imports()
    all_passed &= test_backward_compatibility()
    all_passed &= test_websocket_manager()
    all_passed &= test_app_state_contracts()

    if all_passed:
        print("\n🎉 ALL IMPORT TESTS PASSED - No breaking changes detected!")
    else:
        print("\n💥 IMPORT FAILURES DETECTED - Breaking changes introduced!")

    exit(0 if all_passed else 1)