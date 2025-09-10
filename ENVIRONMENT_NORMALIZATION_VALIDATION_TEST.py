#!/usr/bin/env python3
"""
Environment Normalization and Test Context Detection Validation

This script demonstrates that the bug fixes work correctly by testing
the specific scenarios that were failing before the fix.
"""

import sys
import os

# Add the project root to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


def test_environment_normalization():
    """Test that environment normalization works correctly."""
    print("Testing Environment Normalization...")
    
    env = get_env()
    
    # Test cases that were failing before the fix
    test_cases = [
        ("dev", "development"),
        ("local", "development"), 
        ("prod", "production"),
        ("STAGING", "staging"),
        ("", "development")  # Default case
    ]
    
    for input_env, expected_env in test_cases:
        env.reset_to_original()
        env.enable_isolation()
        
        # Clear test context to avoid interference (like the fixed tests do)
        env.set("PYTEST_CURRENT_TEST", "", "validation")
        env.delete("PYTEST_CURRENT_TEST", "validation")
        env.set("TESTING", "false", "validation")
        env.set("TEST_MODE", "false", "validation")
        
        if input_env:
            env.set("ENVIRONMENT", input_env, "validation")
        else:
            env.delete("ENVIRONMENT", "validation")
        
        backend_env = BackendEnvironment()
        actual_env = backend_env.get_environment()
        
        status = "✅ PASS" if actual_env == expected_env else "❌ FAIL"
        print(f"  {status} '{input_env}' → '{actual_env}' (expected: '{expected_env}')")
        
        if actual_env != expected_env:
            return False
    
    return True


def test_context_detection():
    """Test that test context detection works correctly."""
    print("\nTesting Test Context Detection...")
    
    env = get_env()
    
    # Test cases for context detection
    test_cases = [
        {
            "name": "no_test_indicators",
            "vars": {"ENVIRONMENT": "development"},
            "expected": False
        },
        {
            "name": "testing_flag_true", 
            "vars": {"TESTING": "true"},
            "expected": True
        },
        {
            "name": "environment_test",
            "vars": {"ENVIRONMENT": "test"},
            "expected": True
        }
    ]
    
    for case in test_cases:
        env.reset_to_original()
        env.enable_isolation()
        
        # For cases expecting False, clear pytest indicators
        if not case["expected"]:
            env.set("PYTEST_CURRENT_TEST", "", "validation")
            env.delete("PYTEST_CURRENT_TEST", "validation")
            env.set("TESTING", "false", "validation")
            env.set("TEST_MODE", "false", "validation")
        
        # Set test case variables
        for key, value in case["vars"].items():
            env.set(key, value, "validation")
        
        is_test_context = env._is_test_context()
        
        status = "✅ PASS" if is_test_context == case["expected"] else "❌ FAIL"
        print(f"  {status} {case['name']}: {is_test_context} (expected: {case['expected']})")
        
        if is_test_context != case["expected"]:
            return False
    
    return True


def main():
    """Run all validation tests."""
    print("Environment Detection Bug Fix Validation")
    print("=" * 50)
    
    normalization_passed = test_environment_normalization()
    context_detection_passed = test_context_detection()
    
    print("\n" + "=" * 50)
    if normalization_passed and context_detection_passed:
        print("🎉 ALL TESTS PASSED - Bug fixes working correctly!")
        print("\nThe following issues are now resolved:")
        print("- Environment aliases properly normalize (dev → development)")
        print("- Test context detection respects isolation boundaries")
        print("- BackendEnvironment uses SSOT environment detection")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Bug fixes need review")
        return 1


if __name__ == "__main__":
    exit(main())