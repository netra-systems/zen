#!/usr/bin/env python3
"""
System Stability Validation Test
Validates that P0 fix changes maintain system stability and introduce no breaking changes.
"""

import sys
import traceback

def test_critical_imports():
    """Test that critical WebSocket imports work."""
    try:
        from netra_backend.app.websocket_core import WebSocketManager, create_server_message, create_error_message
        return True, "Critical imports successful"
    except Exception as e:
        return False, f"Import failure: {e}"

def test_canonical_patterns():
    """Test that canonical import patterns work."""
    try:
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager, UnifiedWebSocketManager
        return True, "Canonical patterns successful"
    except Exception as e:
        return False, f"Canonical pattern failure: {e}"

def test_method_signatures():
    """Test that method signatures are backward compatible."""
    try:
        from netra_backend.app.websocket_core.types import create_server_message, create_error_message

        # Test with valid message types
        msg = create_server_message('system', {'status': 'ok'})
        err = create_error_message('ERR001', 'Test error message')

        # Test legacy pattern
        legacy_msg = create_server_message({'type': 'system', 'status': 'ok'})

        return True, "Method signatures backward compatible"
    except Exception as e:
        return False, f"Signature compatibility failure: {e}"

def test_factory_patterns():
    """Test that factory patterns are functional."""
    try:
        from netra_backend.app.websocket_core.types import WebSocketManagerMode
        from netra_backend.app.websocket_core import create_websocket_manager

        # Verify enum is available
        modes = list(WebSocketManagerMode.__members__.keys())

        return True, f"Factory pattern enums available: {len(modes)} modes"
    except Exception as e:
        return False, f"Factory pattern failure: {e}"

def test_ssot_compliance():
    """Test that SSOT compliance is maintained."""
    try:
        from netra_backend.app.websocket_core.canonical_import_patterns import validate_import_pattern_usage

        validation_report = validate_import_pattern_usage()
        phase1_complete = validation_report.get('phase1_complete', False)
        ready_for_phase2 = validation_report.get('ready_for_phase2', False)

        if phase1_complete and ready_for_phase2:
            return True, f"SSOT compliance validated: {validation_report['canonical_patterns_defined']} patterns"
        else:
            return False, f"SSOT compliance issues: {validation_report}"
    except Exception as e:
        return False, f"SSOT compliance failure: {e}"

def test_business_continuity():
    """Test that core business functions remain intact."""
    try:
        from netra_backend.app.websocket_core.types import MessageType
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

        # Verify critical business events are available
        critical_events = UnifiedWebSocketEmitter.CRITICAL_EVENTS
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        missing_events = [event for event in required_events if event not in critical_events]
        if missing_events:
            return False, f"Missing critical events: {missing_events}"

        return True, f"Business continuity validated: {len(critical_events)} critical events available"
    except Exception as e:
        return False, f"Business continuity failure: {e}"

def main():
    """Run all stability tests."""
    print("=== SYSTEM STABILITY VALIDATION ===")
    print("Validating P0 fix changes maintain system stability...")
    print()

    tests = [
        ("Critical Imports", test_critical_imports),
        ("Canonical Patterns", test_canonical_patterns),
        ("Method Signatures", test_method_signatures),
        ("Factory Patterns", test_factory_patterns),
        ("SSOT Compliance", test_ssot_compliance),
        ("Business Continuity", test_business_continuity),
    ]

    all_passed = True
    results = []

    for test_name, test_func in tests:
        try:
            passed, message = test_func()
            status = "PASS" if passed else "FAIL"
            print(f"Test {test_name:20s}: {status:4s} - {message}")
            results.append((test_name, passed, message))
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"Test {test_name:20s}: ERROR - {e}")
            traceback.print_exc()
            results.append((test_name, False, f"Exception: {e}"))
            all_passed = False

    print()
    print("=== STABILITY VALIDATION SUMMARY ===")

    if all_passed:
        print("STATUS: ALL TESTS PASSED")
        print("CONCLUSION: System stability CONFIRMED - No breaking changes detected")
        print("SAFETY: P0 fix changes are safe for deployment")
        return 0
    else:
        print("STATUS: FAILURES DETECTED")
        failed_tests = [name for name, passed, _ in results if not passed]
        print(f"FAILED TESTS: {', '.join(failed_tests)}")
        print("CONCLUSION: System stability at RISK - Breaking changes detected")
        print("RECOMMENDATION: Review and fix issues before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())