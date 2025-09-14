#!/usr/bin/env python3
"""
Immediate Unit Test Failure Remediation Validation Script

This script validates the immediate fixes applied for the Five Whys root cause:
- SSOT WebSocket Manager consolidation
- Performance threshold adjustments for concurrent execution
- Resource contention elimination

Run this script to validate that the fixes are working correctly.
"""

import subprocess
import sys
import time
import os

def run_command(cmd, description):
    """Run a command and capture output."""
    print(f"\n=== {description} ===")
    print(f"Command: {cmd}")
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd="/Users/anthony/Desktop/netra-apex"
        )
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Duration: {duration:.2f}s")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0, duration, result.stdout, result.stderr
        
    except Exception as e:
        print(f"Error running command: {e}")
        return False, 0, "", str(e)

def main():
    """Run validation tests for immediate fixes."""
    print("Starting Immediate Unit Test Failure Remediation Validation")
    print("=" * 60)
    
    # Test 1: Validate SSOT consolidation by checking import warnings
    success1, duration1, stdout1, stderr1 = run_command(
        'python3 -c "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager; print(\'SSOT import successful\')"',
        "Test 1: SSOT WebSocket Manager Import Validation"
    )
    
    # Test 2: Run the specific failing test individually to ensure it passes
    success2, duration2, stdout2, stderr2 = run_command(
        'python3 -m pytest netra_backend/tests/unit/agent_execution/test_context_validation.py::TestContextValidation::test_context_validation_performance_reasonable -v --tb=short',
        "Test 2: Individual Performance Test Validation"
    )
    
    # Test 3: Run a small subset of tests to validate concurrent behavior
    success3, duration3, stdout3, stderr3 = run_command(
        'python3 -m pytest netra_backend/tests/unit/agent_execution/test_context_validation.py -v --tb=short --timeout=120',
        "Test 3: Context Validation Test Suite"
    )
    
    # Test 4: Quick smoke test of unified test runner
    success4, duration4, stdout4, stderr4 = run_command(
        'python3 tests/unified_test_runner.py --category unit --pattern "test_context_validation_performance_reasonable" --no-coverage --timeout 180',
        "Test 4: Unified Test Runner Smoke Test"
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    tests = [
        ("SSOT Import Validation", success1, duration1),
        ("Individual Performance Test", success2, duration2), 
        ("Context Validation Suite", success3, duration3),
        ("Unified Test Runner", success4, duration4)
    ]
    
    total_success = 0
    for name, success, duration in tests:
        status = "PASS" if success else "FAIL"
        print(f"{name:<30} {status:<6} ({duration:.2f}s)")
        if success:
            total_success += 1
    
    print(f"\nResults: {total_success}/{len(tests)} tests passed")
    
    if total_success == len(tests):
        print("\n✅ ALL IMMEDIATE FIXES VALIDATED SUCCESSFULLY")
        print("The unit test failure remediation is working correctly.")
        return True
    else:
        print(f"\n❌ {len(tests) - total_success} TESTS FAILED")
        print("Additional remediation steps may be needed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)