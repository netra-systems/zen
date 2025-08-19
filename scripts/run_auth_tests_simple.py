#!/usr/bin/env python3
"""Simple Real Auth Integration Test Runner

Business Value: Validates auth service integration before deployment.
Prevents auth failures in production that cause 100% service downtime.

This script runs all real auth integration tests to ensure:
1. Auth service integration works correctly 
2. Database state is validated properly
3. At least 20 auth tests use real service calls
"""

import subprocess
import sys
import os
from pathlib import Path


def run_auth_integration_tests():
    """Run real auth integration tests"""
    print("Running Real Auth Integration Tests")
    print("=" * 50)
    
    project_root = Path(__file__).parent.parent
    
    # List of real auth test files
    test_files = [
        "app/tests/auth_integration/test_real_auth_integration.py",
        "app/tests/unit/test_real_auth_service_integration.py", 
        "app/tests/critical/test_real_auth_integration_critical.py",
        "app/tests/auth_integration/test_real_user_session_management.py"
    ]
    
    # Check which test files exist
    existing_files = []
    for test_file in test_files:
        full_path = project_root / test_file
        if full_path.exists():
            existing_files.append(str(full_path))
            print(f"Found: {test_file}")
        else:
            print(f"Missing: {test_file}")
    
    if not existing_files:
        print("No real auth test files found!")
        return False
    
    print(f"\nRunning {len(existing_files)} test files...")
    
    # Run tests
    total_passed = 0
    total_failed = 0
    
    for test_file in existing_files:
        print(f"\nTesting: {Path(test_file).name}")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                test_file, 
                "-v",
                "--tb=short",
                f"--rootdir={project_root}"
            ], 
            cwd=project_root,
            capture_output=True,
            text=True
            )
            
            if result.returncode == 0:
                print(f"PASSED: {Path(test_file).name}")
                # Count test methods
                test_count = result.stdout.count("PASSED")
                total_passed += test_count
                print(f"  {test_count} test methods passed")
            else:
                print(f"FAILED: {Path(test_file).name}")
                print("Error output:")
                print(result.stderr)
                total_failed += 1
                
        except Exception as e:
            print(f"ERROR running {Path(test_file).name}: {e}")
            total_failed += 1
    
    # Generate summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Total test methods passed: {total_passed}")
    print(f"Failed test files: {total_failed}")
    print(f"Success criteria (20+ tests): {'MET' if total_passed >= 20 else 'NOT MET'}")
    
    success = total_failed == 0 and total_passed >= 20
    
    if success:
        print("\nSUCCESS: All real auth integration tests passed!")
    else:
        print("\nFAILURE: Some tests failed or insufficient test coverage")
    
    return success


if __name__ == "__main__":
    success = run_auth_integration_tests()
    sys.exit(0 if success else 1)