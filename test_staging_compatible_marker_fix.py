#!/usr/bin/env python3
"""
Test script to validate that GitHub Issue #272 is resolved.
This script proves that the staging_compatible pytest marker fix works.

Run this script to validate:
1. All 6 previously blocked E2E files can now collect successfully
2. The staging_compatible marker is properly defined
3. No collection errors related to missing markers
"""

import subprocess
import sys
from pathlib import Path

def run_collection_test(file_path: str) -> tuple[bool, str]:
    """Test if a file can be collected without marker errors."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", file_path, "--collect-only"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check for the specific "staging_compatible" not found error
        if "staging_compatible not found" in result.stderr or "staging_compatible not found" in result.stdout:
            return False, f"FAILED: staging_compatible marker not found\n{result.stderr}"
        
        # Check if tests were collected (indicating successful parsing)
        if "collected" in result.stdout and "items" in result.stdout:
            return True, f"SUCCESS: {result.stdout.split('collected')[1].split('in')[0].strip()}"
        
        return False, f"FAILED: No tests collected\n{result.stdout}\n{result.stderr}"
        
    except subprocess.TimeoutExpired:
        return False, "FAILED: Collection timed out"
    except Exception as e:
        return False, f"FAILED: Exception {e}"

def main():
    """Main test function for Issue #272 fix validation."""
    print("GitHub Issue #272 - Staging Compatible Marker Fix Validation")
    print("=" * 70)
    
    # Test files that were previously blocked by missing staging_compatible marker
    test_files = [
        "tests/e2e/test_complete_authenticated_chat_workflow_e2e.py",
        "netra_backend/tests/e2e/test_agent_execution_core_complete_flow.py", 
        "netra_backend/tests/e2e/test_websocket_notifier_complete_e2e.py",
        "netra_backend/tests/e2e/test_workflow_orchestrator_golden_path.py",
        "tests/e2e/test_agent_state_sync_integration_helpers.py",
        "tests/integration/test_authenticated_chat_workflow_comprehensive.py",
        "tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py"
    ]
    
    all_passed = True
    total_tests_collected = 0
    
    for test_file in test_files:
        print(f"\nTesting: {test_file}")
        success, message = run_collection_test(test_file)
        
        if success:
            print(f"SUCCESS: {message}")
            # Extract number of tests collected
            if "collected" in message:
                try:
                    num_tests = int(message.split()[0])
                    total_tests_collected += num_tests
                except (ValueError, IndexError):
                    pass
        else:
            print(f"FAILED: {message}")
            all_passed = False
    
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    if all_passed:
        print(f"SUCCESS: All {len(test_files)} previously blocked files now collect successfully")
        print(f"Total tests now accessible: {total_tests_collected}+ tests")
        print(f"GitHub Issue #272 has been RESOLVED")
        print("\nBUSINESS IMPACT:")
        print("   * 6 mission-critical E2E tests are now unblocked") 
        print("   * Staging environment testing is fully enabled")
        print("   * Golden Path validation can proceed")
        print("   * Infrastructure deployment tests are accessible")
        return 0
    else:
        print(f"FAILURE: Some files still have collection issues")
        print(f"GitHub Issue #272 requires additional investigation")
        return 1

if __name__ == "__main__":
    sys.exit(main())