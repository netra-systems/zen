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
    
    # Integration golden path tests in netra_backend (key ones to focus on)
    critical_integration_tests = [
        "netra_backend/tests/integration/golden_path/test_service_dependency_integration.py",
        "netra_backend/tests/integration/golden_path/test_complete_golden_path_integration.py",
        "netra_backend/tests/integration/golden_path/test_user_authentication_flows.py",
        "netra_backend/tests/integration/golden_path/test_agent_execution_database_integration.py",
        "netra_backend/tests/integration/golden_path/test_websocket_real_connection_integration.py"
    ]
    
    # Key business value tests
    business_critical_tests = [
        "netra_backend/tests/integration/golden_path/test_business_value_delivery_validation_enhanced.py",
        "netra_backend/tests/integration/golden_path/test_golden_path_service_boundaries.py",
        "netra_backend/tests/integration/golden_path/test_authentication_real_services_integration.py"
    ]
    
    print("=" * 80)
    print("RUNNING INTEGRATION GOLDEN PATH TESTS WITHOUT DOCKER")
    print("Mode: Fast failure, integration tests focus")
    print("=" * 80)
    
    failed_tests = []
    passed_tests = []
    
    # Run critical integration tests first
    print("\n[PHASE 1] Running Critical Integration Golden Path Tests")
    print("-" * 50)
    
    for test_file in critical_integration_tests:
        if not Path(test_file).exists():
            print(f"⚠️  SKIP: {test_file} (file not found)")
            continue
            
        print(f"\n🔍 Running: {test_file}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v", "--tb=short", "--maxfail=1",
            "--no-header", "--no-summary", "--no-docker"
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
    
    # Run business critical tests
    print("\n[PHASE 2] Running Business Critical Golden Path Tests")
    print("-" * 50)
    
    for test_file in business_critical_tests:
        if not Path(test_file).exists():
            print(f"⚠️  SKIP: {test_file} (file not found)")
            continue
            
        print(f"\n🔍 Running: {test_file}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v", "--tb=short", "--maxfail=1",
            "--no-header", "--no-summary", "--no-docker"
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