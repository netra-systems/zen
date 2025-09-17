#!/usr/bin/env python3
"""
Script to run e2e golden path tests against GCP staging
without Docker dependencies, using fast failure mode.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run golden path tests with fast failure and report results"""
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Key golden path tests to run in order of importance
    critical_tests = [
        "tests/e2e/test_golden_path_complete_flow.py",
        "tests/e2e/test_authentication_golden_path_complete.py", 
        "tests/e2e/test_golden_path_auth_e2e.py",
        "tests/e2e/test_golden_path_websocket_auth_staging.py",
        "tests/e2e/test_golden_path_execution_engine_staging.py"
    ]
    
    # Mission critical tests
    mission_critical_tests = [
        "tests/mission_critical/test_golden_path_websocket_authentication.py",
        "tests/mission_critical/test_websocket_ssot_golden_path_validation.py",
        "tests/mission_critical/test_golden_path_integration_coverage.py"
    ]
    
    print("=" * 80)
    print("RUNNING E2E GOLDEN PATH TESTS AGAINST GCP STAGING")
    print("Mode: Fast failure, no Docker dependencies")
    print("=" * 80)
    
    failed_tests = []
    passed_tests = []
    
    # Run critical e2e tests first
    print("\n[PHASE 1] Running Critical E2E Golden Path Tests")
    print("-" * 50)
    
    for test_file in critical_tests:
        if not Path(test_file).exists():
            print(f"⚠️  SKIP: {test_file} (file not found)")
            continue
            
        print(f"\n🔍 Running: {test_file}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v", "--tb=short", "--maxfail=1",
            "--no-header", "--no-summary"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ PASSED: {test_file}")
                passed_tests.append(test_file)
            else:
                print(f"❌ FAILED: {test_file}")
                print("STDOUT:")
                print(result.stdout[-1500:])  # Last 1500 chars
                print("STDERR:")
                print(result.stderr[-1500:])  # Last 1500 chars
                failed_tests.append((test_file, result.stdout, result.stderr))
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {test_file} (300s)")
            failed_tests.append((test_file, "TIMEOUT", "Test exceeded 300 second limit"))
        except Exception as e:
            print(f"💥 ERROR: {test_file} - {str(e)}")
            failed_tests.append((test_file, "EXCEPTION", str(e)))
    
    # Run mission critical tests
    print("\n[PHASE 2] Running Mission Critical Golden Path Tests")
    print("-" * 50)
    
    for test_file in mission_critical_tests:
        if not Path(test_file).exists():
            print(f"⚠️  SKIP: {test_file} (file not found)")
            continue
            
        print(f"\n🔍 Running: {test_file}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v", "--tb=short", "--maxfail=1",
            "--no-header", "--no-summary"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ PASSED: {test_file}")
                passed_tests.append(test_file)
            else:
                print(f"❌ FAILED: {test_file}")
                print("STDOUT:")
                print(result.stdout[-1500:])  # Last 1500 chars
                print("STDERR:")
                print(result.stderr[-1500:])  # Last 1500 chars
                failed_tests.append((test_file, result.stdout, result.stderr))
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {test_file} (300s)")
            failed_tests.append((test_file, "TIMEOUT", "Test exceeded 300 second limit"))
        except Exception as e:
            print(f"💥 ERROR: {test_file} - {str(e)}")
            failed_tests.append((test_file, "EXCEPTION", str(e)))
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("GOLDEN PATH TEST RESULTS SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ PASSED TESTS ({len(passed_tests)}):")
    for test in passed_tests:
        print(f"   - {test}")
    
    print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
    for test, stdout, stderr in failed_tests:
        print(f"   - {test}")
    
    if failed_tests:
        print(f"\n🚨 CRITICAL: {len(failed_tests)} Golden Path tests are failing!")
        print("This indicates issues with the $500K+ ARR chat functionality.")
        print("\nDETAILED FAILURE ANALYSIS:")
        print("-" * 50)
        
        for i, (test, stdout, stderr) in enumerate(failed_tests, 1):
            print(f"\n[FAILURE {i}] {test}")
            print("=" * 60)
            
            # Try to extract key error information
            if "TIMEOUT" in stdout:
                print("ERROR TYPE: Test execution timeout (>300s)")
            elif "EXCEPTION" in stdout:
                print(f"ERROR TYPE: Exception - {stderr}")
            else:
                # Look for common error patterns
                if "ConnectionError" in stderr or "ConnectionError" in stdout:
                    print("ERROR TYPE: Connection failure to staging environment")
                elif "AuthenticationError" in stderr or "AuthenticationError" in stdout:
                    print("ERROR TYPE: Authentication failure in staging")
                elif "TimeoutError" in stderr or "TimeoutError" in stdout:
                    print("ERROR TYPE: Network timeout or service unavailability")
                elif "ImportError" in stderr or "ImportError" in stdout:
                    print("ERROR TYPE: Import/dependency issues")
                else:
                    print("ERROR TYPE: Unknown failure")
                
                # Show last part of stderr for key error info
                if stderr.strip():
                    print("\nKEY ERROR OUTPUT:")
                    error_lines = stderr.strip().split('\n')[-10:]  # Last 10 lines
                    for line in error_lines:
                        if line.strip():
                            print(f"  {line}")
    else:
        print(f"\n🎉 SUCCESS: All {len(passed_tests)} Golden Path tests are passing!")
        print("The $500K+ ARR chat functionality appears to be operational.")
    
    print("\n" + "=" * 80)
    return len(failed_tests)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)