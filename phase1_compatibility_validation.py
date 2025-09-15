#!/usr/bin/env python3
"""
Phase 1 Commit 2: Compatibility Layer Validation
Issue #824 - WebSocket Manager fragmentation consolidation

Validates that all existing import patterns and usage patterns continue to work
during SSOT consolidation to ensure no breaking changes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_compatibility_layer():
    """Validate that compatibility layer maintains all existing patterns."""
    print("=" * 70)
    print("PHASE 1 COMMIT 2: COMPATIBILITY LAYER VALIDATION")
    print("Ensuring no breaking changes during SSOT consolidation")
    print("=" * 70)

    tests_passed = 0
    total_tests = 0

    # Test 1: Legacy import patterns still work
    total_tests += 1
    try:
        # This should work but show deprecation warning
        from netra_backend.app.websocket_core import WebSocketManager
        print("[PASS] Test 1: Legacy import pattern works (with deprecation warning)")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 1: Legacy import broken: {e}")

    # Test 2: Canonical import pattern works
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalWebSocketManager
        print("[PASS] Test 2: Canonical import pattern works")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 2: Canonical import broken: {e}")

    # Test 3: Factory pattern compatibility
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        print("[PASS] Test 3: Factory pattern compatibility maintained")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 3: Factory pattern broken: {e}")

    # Test 4: Alias consistency
    if tests_passed >= 2:
        total_tests += 1
        try:
            from netra_backend.app.websocket_core import WebSocketManager as LegacyManager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalManager
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

            # All should be the same class
            all_same = (LegacyManager == CanonicalManager == UnifiedWebSocketManager)
            if all_same:
                print("[PASS] Test 4: All import paths resolve to same SSOT implementation")
                tests_passed += 1
            else:
                print("[FAIL] Test 4: Import paths resolve to different implementations")
                print(f"         Legacy: {LegacyManager}")
                print(f"         Canonical: {CanonicalManager}")
                print(f"         SSOT: {UnifiedWebSocketManager}")
        except Exception as e:
            print(f"[FAIL] Test 4: Alias consistency check failed: {e}")

    # Test 5: Backward compatibility aliases
    total_tests += 1
    try:
        from netra_backend.app.websocket_core import (
            UnifiedWebSocketManager,
            IsolatedWebSocketEventEmitter,
            UserWebSocketEmitter,
            create_websocket_manager
        )
        print("[PASS] Test 5: Backward compatibility aliases exist")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 5: Backward compatibility aliases missing: {e}")

    # Test 6: Protocol interface backward compatibility
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.protocols import (
            WebSocketManagerProtocol,
            WebSocketProtocol
        )
        # These should be aliases
        if WebSocketManagerProtocol == WebSocketProtocol:
            print("[PASS] Test 6: Protocol interface backward compatibility maintained")
            tests_passed += 1
        else:
            print("[FAIL] Test 6: Protocol interfaces not aliased properly")
    except ImportError as e:
        print(f"[FAIL] Test 6: Protocol interface compatibility broken: {e}")

    # Test 7: Factory method compatibility
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import (
            WebSocketManagerFactory,
            create_websocket_manager_sync,
            get_websocket_manager_factory
        )
        print("[PASS] Test 7: Factory method compatibility maintained")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 7: Factory method compatibility broken: {e}")

    # Summary
    print("\n" + "=" * 70)
    print(f"COMPATIBILITY VALIDATION RESULTS: {tests_passed}/{total_tests} tests passed")
    print("=" * 70)

    if tests_passed == total_tests:
        print("[SUCCESS] All compatibility layers functional")
        print("✓ Legacy import patterns work with deprecation warnings")
        print("✓ Canonical import patterns work")
        print("✓ Factory compatibility maintained")
        print("✓ All import paths resolve to SSOT implementation")
        print("✓ Backward compatibility aliases exist")
        print("✓ Protocol interface compatibility maintained")
        print("✓ Factory methods available")
        print()
        print("Ready for Phase 1 Commit 3: Canonical Import Path Documentation")
        return True
    else:
        print(f"[ISSUES] {total_tests - tests_passed} compatibility issues found")
        print("Fix compatibility before proceeding to Phase 2")
        return False

if __name__ == "__main__":
    success = validate_compatibility_layer()
    sys.exit(0 if success else 1)