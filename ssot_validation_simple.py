#!/usr/bin/env python3
"""Simple SSOT WebSocket Manager validation script for Phase 1"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_ssot_phase1():
    """Validate current SSOT status for WebSocket Manager."""
    print("=" * 60)
    print("SSOT WEBSOCKET MANAGER PHASE 1 VALIDATION")
    print("=" * 60)

    tests_passed = 0
    total_tests = 0

    # Test 1: Protocol exists
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.protocols import (
            WebSocketProtocolValidator,
            WebSocketManagerProtocol
        )
        print("[PASS] Test 1: WebSocketManagerProtocol interface exists")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 1: Protocol import failed: {e}")

    # Test 2: SSOT implementation exists
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
        print("[PASS] Test 2: UnifiedWebSocketManager SSOT implementation exists")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 2: SSOT implementation import failed: {e}")

    # Test 3: Canonical import path works
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        print("[PASS] Test 3: Canonical import path works")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 3: Canonical import failed: {e}")

    # Test 4: Factory compatibility exists
    total_tests += 1
    try:
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
        print("[PASS] Test 4: Factory compatibility layer exists")
        tests_passed += 1
    except ImportError as e:
        print(f"[FAIL] Test 4: Factory import failed: {e}")

    # Test 5: Protocol validation works (if all above passed)
    if tests_passed == total_tests:
        total_tests += 1
        try:
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create proper test context
            id_manager = UnifiedIDManager()
            user_id = "ssot_test_" + id_manager.generate_id()[:8]
            thread_id = id_manager.generate_thread_id()
            run_id = id_manager.generate_run_id(thread_id)
            request_id = id_manager.generate_id()

            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                agent_context={'test': True}
            )
            context._legitimate_patterns = {'ssot_test'}

            manager = UnifiedWebSocketManager(user_context=context)
            validation = WebSocketProtocolValidator.validate_manager_protocol(manager)

            if validation['compliant']:
                print("[PASS] Test 5: Protocol compliance validation")
                print(f"        Compliance: {validation['summary']['compliance_percentage']}%")
                tests_passed += 1
            else:
                print("[FAIL] Test 5: Protocol compliance issues")
                print(f"        Missing: {validation['missing_methods']}")
                print(f"        Invalid: {validation['invalid_signatures']}")

        except Exception as e:
            print(f"[FAIL] Test 5: Protocol validation failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print(f"PHASE 1 VALIDATION RESULTS: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)

    if tests_passed == total_tests:
        print("[SUCCESS] Phase 1 interface standardization is COMPLETE")
        print("Ready for Phase 2: Import Unification")
        return True
    else:
        print(f"[PARTIAL] {tests_passed}/{total_tests} tests passed - work needed")
        print("Phase 1 interface standardization requires attention")
        return False

if __name__ == "__main__":
    success = validate_ssot_phase1()
    sys.exit(0 if success else 1)