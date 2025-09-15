#!/usr/bin/env python3
"""
Quick SSOT WebSocket Manager validation test.
"""

def test_ssot_consolidation():
    """Test that SSOT consolidation is working correctly."""
    print("[TEST] Testing WebSocket Manager SSOT Consolidation...")

    # Test 1: Import from consolidated module should work
    try:
        from netra_backend.app.websocket_core.websocket_manager import (
            create_websocket_manager,
            WebSocketManagerFactory,
            get_websocket_manager,
            MAX_CONNECTIONS_PER_USER
        )
        print("[PASS] All SSOT imports successful")
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False

    # Test 2: Factory module should no longer exist
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        print("[FAIL] SSOT VIOLATION: websocket_manager_factory still importable")
        return False
    except ImportError:
        print("[PASS] websocket_manager_factory successfully eliminated")

    # Test 3: Check that connection limits constant is available
    from netra_backend.app.websocket_core.unified_manager import MAX_CONNECTIONS_PER_USER
    print(f"[PASS] MAX_CONNECTIONS_PER_USER = {MAX_CONNECTIONS_PER_USER}")

    # Test 4: Test manager creation
    try:
        # This should work without warnings now
        manager = get_websocket_manager()
        print(f"[PASS] WebSocket manager creation successful: {type(manager).__name__}")
    except Exception as e:
        print(f"[FAIL] Manager creation error: {e}")
        return False

    # Test 5: Test legacy function compatibility
    try:
        manager_legacy = create_websocket_manager()
        print(f"[PASS] Legacy create_websocket_manager compatibility: {type(manager_legacy).__name__}")
    except Exception as e:
        print(f"[FAIL] Legacy compatibility error: {e}")
        return False

    print("\n[SUCCESS] All SSOT WebSocket Manager consolidation tests passed!")
    return True

if __name__ == "__main__":
    success = test_ssot_consolidation()
    exit(0 if success else 1)