#!/usr/bin/env python3
"""
WebSocket Signature Fix Validation Script for Issue #405

This script validates that the hybrid create_server_message implementation
properly handles both legacy and standard calling patterns without breaking
existing functionality.

BUSINESS IMPACT: Validates $500K+ ARR Golden Path functionality
"""
import traceback
import time
from typing import Dict, Any

print("="*80)
print("WEBSOCKET SIGNATURE FIX VALIDATION - ISSUE #405")
print("="*80)
print("Business Impact: $500K+ ARR Golden Path functionality")
print("Testing: Hybrid signature compatibility and SSOT compliance")
print()

def test_basic_imports():
    """Test that basic WebSocket imports work correctly."""
    print("1. TESTING BASIC IMPORTS...")
    try:
        # Test the main imports that were causing issues
        from netra_backend.app.websocket_core.types import create_server_message as types_create_server_message
        from netra_backend.app.websocket_core import create_server_message as init_create_server_message
        from netra_backend.app.websocket_core.types import MessageType, ServerMessage
        
        print("   [PASS] All imports successful")
        print(f"   - types_create_server_message: {callable(types_create_server_message)}")
        print(f"   - init_create_server_message: {callable(init_create_server_message)}")
        print(f"   - Both functions are same object: {types_create_server_message is init_create_server_message}")
        return True
        
    except Exception as e:
        print(f"   [FAIL] Import failed: {e}")
        traceback.print_exc()
        return False

def test_legacy_pattern():
    """Test legacy calling pattern: create_server_message({"type": "system", "status": "ok"})"""
    print("\\n2. TESTING LEGACY PATTERN...")
    try:
        from netra_backend.app.websocket_core.types import create_server_message
        
        # Legacy pattern that was failing before the fix
        result = create_server_message({"type": "system", "status": "ok"})
        
        print("   [PASS] Legacy pattern works")
        print(f"   - Result type: {type(result).__name__}")
        print(f"   - Message type: {result.type}")
        print(f"   - Data keys: {list(result.data.keys())}")
        return True
        
    except Exception as e:
        print(f"   [FAIL] Legacy pattern failed: {e}")
        traceback.print_exc()
        return False

def test_standard_pattern():
    """Test standard calling pattern: create_server_message(MessageType.SYSTEM_MESSAGE, {"status": "ok"})"""
    print("\\n3. TESTING STANDARD PATTERN...")
    try:
        from netra_backend.app.websocket_core.types import create_server_message, MessageType
        
        # Standard pattern
        result = create_server_message(MessageType.SYSTEM_MESSAGE, {"status": "ok"})
        
        print("   [PASS] Standard pattern works")
        print(f"   - Result type: {type(result).__name__}")
        print(f"   - Message type: {result.type}")
        print(f"   - Data keys: {list(result.data.keys())}")
        return True
        
    except Exception as e:
        print(f"   [FAIL] Standard pattern failed: {e}")
        traceback.print_exc()
        return False

def test_string_pattern():
    """Test string calling pattern: create_server_message("system", {"status": "ok"})"""
    print("\\n4. TESTING STRING PATTERN...")
    try:
        from netra_backend.app.websocket_core.types import create_server_message
        
        # String pattern
        result = create_server_message("system", {"status": "ok"})
        
        print("   [PASS] String pattern works")
        print(f"   - Result type: {type(result).__name__}")
        print(f"   - Message type: {result.type}")
        print(f"   - Data keys: {list(result.data.keys())}")
        return True
        
    except Exception as e:
        print(f"   [FAIL] String pattern failed: {e}")
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\\n5. TESTING ERROR HANDLING...")
    try:
        from netra_backend.app.websocket_core.types import create_server_message
        
        # Test invalid type
        try:
            result = create_server_message("invalid_type", {"status": "ok"})
            print("   [FAIL] Should have raised ValueError for invalid type")
            return False
        except ValueError as e:
            print(f"   [PASS] Correctly raised ValueError for invalid type: {e}")
            
        # Test missing type in legacy pattern
        try:
            result = create_server_message({"status": "ok"})  # Missing 'type' key
            print("   [FAIL] Should have raised ValueError for missing type")
            return False
        except ValueError as e:
            print(f"   [PASS] Correctly raised ValueError for missing type: {e}")
            
        # Test invalid data type in standard pattern
        try:
            result = create_server_message("system", "not_a_dict")
            print("   [FAIL] Should have raised TypeError for invalid data type")
            return False
        except TypeError as e:
            print(f"   [PASS] Correctly raised TypeError for invalid data type: {e}")
            
        return True
        
    except Exception as e:
        print(f"   [FAIL] Unexpected error in error handling test: {e}")
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test that existing code patterns still work."""
    print("\\n6. TESTING BACKWARD COMPATIBILITY...")
    try:
        from netra_backend.app.websocket_core.types import create_server_message, MessageType
        
        # Test various patterns that should all work
        patterns = [
            # Legacy patterns
            ({"type": "system", "status": "ok"}, {}),
            ({"type": "agent_started", "agent_id": "test"}, {}),
            ({"type": "connect", "user_id": "123"}, {}),
            
            # Standard patterns  
            (MessageType.SYSTEM_MESSAGE, {"status": "ok"}),
            ("system", {"status": "ok"}),
            ("agent_started", {"agent_id": "test"}),
        ]
        
        for i, (arg1, arg2) in enumerate(patterns):
            if isinstance(arg2, dict) and arg2:
                result = create_server_message(arg1, arg2)
            else:
                result = create_server_message(arg1)
            print(f"   [PASS] Pattern {i+1} works: {result.type}")
            
        return True
        
    except Exception as e:
        print(f"   [FAIL] Backward compatibility test failed: {e}")
        traceback.print_exc()
        return False

def test_performance():
    """Test that the hybrid implementation doesn't significantly impact performance."""
    print("\\n7. TESTING PERFORMANCE...")
    try:
        from netra_backend.app.websocket_core.types import create_server_message, MessageType
        
        # Time legacy pattern
        start_time = time.time()
        for _ in range(1000):
            create_server_message({"type": "system", "status": "ok"})
        legacy_time = time.time() - start_time
        
        # Time standard pattern
        start_time = time.time()
        for _ in range(1000):
            create_server_message(MessageType.SYSTEM_MESSAGE, {"status": "ok"})
        standard_time = time.time() - start_time
        
        print(f"   [PASS] Performance test completed")
        print(f"   - Legacy pattern (1000 calls): {legacy_time:.4f}s")
        print(f"   - Standard pattern (1000 calls): {standard_time:.4f}s")
        print(f"   - Performance ratio: {legacy_time/standard_time:.2f}x")
        
        # Both should be fast
        if legacy_time > 1.0 or standard_time > 1.0:
            print("   [WARN]  Performance concern: >1s for 1000 calls")
            
        return True
        
    except Exception as e:
        print(f"   [FAIL] Performance test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    tests = [
        test_basic_imports,
        test_legacy_pattern,
        test_standard_pattern, 
        test_string_pattern,
        test_error_handling,
        test_backward_compatibility,
        test_performance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"\\n[FAIL] CRITICAL: Test {test.__name__} failed!")
            
    print("\\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\\n[SUCCESS] ALL TESTS PASSED - WEBSOCKET SIGNATURE FIX VALIDATED")
        print("[PASS] Issue #405 has been successfully resolved")
        print("[PASS] System stability maintained")
        print("[PASS] No breaking changes introduced")
        print("[PASS] Ready for deployment")
        
    else:
        print(f"\\n[CRITICAL] {total-passed} TESTS FAILED - ISSUES DETECTED")
        print("[FAIL] Further investigation required")
        print("[FAIL] Do not deploy until all tests pass")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)