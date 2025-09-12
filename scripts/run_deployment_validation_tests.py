#!/usr/bin/env python3
"""
Deployment Validation Test Runner for Issue #128
Executes the comprehensive test plan to validate WebSocket fixes deployment

Usage:
    python run_deployment_validation_tests.py --phase pre-deployment
    python run_deployment_validation_tests.py --phase deployment-readiness  
    python run_deployment_validation_tests.py --phase post-deployment
    python run_deployment_validation_tests.py --phase all
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

def run_command(command, description, expect_failure=False):
    """Run a command and return success/failure status"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        duration = time.time() - start_time
        
        print(f"Duration: {duration:.2f}s")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Determine success based on expectations
        if expect_failure:
            if result.returncode != 0:
                print("✅ EXPECTED FAILURE - This confirms the deployment gap exists")
                return True  # Expected failure = success for our test plan
            else:
                print("❌ UNEXPECTED SUCCESS - This suggests deployment may already be active")
                return False
        else:
            if result.returncode == 0:
                print("✅ SUCCESS - Test passed as expected")
                return True
            else:
                print("❌ FAILURE - Test failed unexpectedly") 
                return False
                
    except Exception as e:
        duration = time.time() - start_time
        print(f"Duration: {duration:.2f}s")
        print(f"❌ ERROR running command: {e}")
        return False

def run_phase_1_pre_deployment():
    """Phase 1: Pre-deployment validation (expects failures proving deployment gap)"""
    print("\n" + "="*80)
    print("PHASE 1: PRE-DEPLOYMENT VALIDATION")
    print("Expected: Some tests FAIL (proving deployment gap exists)")
    print("="*80)
    
    tests = [
        {
            "command": "python -m pytest tests/unit/deployment_validation/test_websocket_timeout_config_gap.py -v",
            "description": "WebSocket timeout config gap validation",
            "expect_failure": True  # Expected to fail before deployment
        },
        {
            "command": "python -m pytest tests/integration/deployment_validation/test_staging_websocket_baseline.py -v", 
            "description": "Staging WebSocket baseline performance",
            "expect_failure": False  # This documents current state, shouldn't fail
        },
        {
            "command": "python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_streaming_partial_results_real -v --tb=short --timeout=120",
            "description": "P1 Critical Test 023 (should timeout before deployment)",
            "expect_failure": True  # Expected to timeout before deployment
        },
        {
            "command": "python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_critical_event_delivery_real -v --tb=short --timeout=60",
            "description": "P1 Critical Test 025 (should timeout before deployment)", 
            "expect_failure": True  # Expected to timeout before deployment
        }
    ]
    
    results = []
    for test in tests:
        success = run_command(
            test["command"], 
            test["description"],
            test.get("expect_failure", False)
        )
        results.append(success)
        
    return results

def run_phase_2_deployment_readiness():
    """Phase 2: Deployment readiness validation (should all pass)"""
    print("\n" + "="*80)
    print("PHASE 2: DEPLOYMENT READINESS VALIDATION") 
    print("Expected: All tests PASS (fixes are ready for deployment)")
    print("="*80)
    
    tests = [
        {
            "command": "python -m pytest tests/unit/deployment_validation/test_circuit_breaker_readiness.py -v",
            "description": "Circuit breaker implementation readiness",
            "expect_failure": False
        },
        {
            "command": "python -m pytest tests/unit/deployment_validation/test_asyncio_selector_optimization.py -v",
            "description": "Asyncio selector optimization validation",
            "expect_failure": False
        }
    ]
    
    results = []
    for test in tests:
        success = run_command(
            test["command"],
            test["description"], 
            test.get("expect_failure", False)
        )
        results.append(success)
        
    return results

def run_phase_3_post_deployment():
    """Phase 3: Post-deployment validation (should all pass after deployment)"""
    print("\n" + "="*80)
    print("PHASE 3: POST-DEPLOYMENT VALIDATION")
    print("Expected: All tests PASS (fixes are now active in staging)")
    print("="*80)
    
    tests = [
        {
            "command": "python -m pytest tests/integration/deployment_validation/test_websocket_performance_post_deployment.py -v",
            "description": "WebSocket performance improvement validation",
            "expect_failure": False
        },
        {
            "command": "python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_streaming_partial_results_real -v --tb=short --timeout=120",
            "description": "P1 Critical Test 023 (should now PASS after deployment)",
            "expect_failure": False
        },
        {
            "command": "python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_critical_event_delivery_real -v --tb=short --timeout=60", 
            "description": "P1 Critical Test 025 (should now PASS after deployment)",
            "expect_failure": False
        },
        {
            "command": "python -m pytest tests/e2e/staging/test_priority1_critical.py -v --tb=short",
            "description": "Full P1 test suite (should achieve 100% pass rate)",
            "expect_failure": False
        }
    ]
    
    results = []
    for test in tests:
        success = run_command(
            test["command"],
            test["description"],
            test.get("expect_failure", False)
        )
        results.append(success)
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Run deployment validation tests for Issue #128")
    parser.add_argument(
        "--phase", 
        choices=["pre-deployment", "deployment-readiness", "post-deployment", "all"],
        default="all",
        help="Which phase of testing to run"
    )
    
    args = parser.parse_args()
    
    print("Issue #128 WebSocket Connectivity Deployment Validation Test Runner")
    print("=" * 80)
    print(f"Phase: {args.phase}")
    print(f"Working Directory: {Path.cwd()}")
    print("=" * 80)
    
    all_results = []
    
    if args.phase in ["pre-deployment", "all"]:
        phase1_results = run_phase_1_pre_deployment()
        all_results.extend(phase1_results)
    
    if args.phase in ["deployment-readiness", "all"]:
        phase2_results = run_phase_2_deployment_readiness() 
        all_results.extend(phase2_results)
    
    if args.phase in ["post-deployment", "all"]:
        phase3_results = run_phase_3_post_deployment()
        all_results.extend(phase3_results)
    
    # Summary
    print("\n" + "="*80)
    print("DEPLOYMENT VALIDATION TEST SUMMARY")
    print("="*80)
    
    total_tests = len(all_results)
    passed_tests = sum(all_results)
    failed_tests = total_tests - passed_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    if args.phase == "pre-deployment":
        print("\nPRE-DEPLOYMENT INTERPRETATION:")
        print("- Some failures are EXPECTED (documenting current deployment gap)")
        print("- P1 tests should fail due to WebSocket timeouts")
        print("- Config gap test should fail (optimized timeouts not active)")
        print("- This proves deployment is needed")
        
    elif args.phase == "deployment-readiness":
        print("\nDEPLOYMENT-READINESS INTERPRETATION:")
        print("- All tests should PASS (fixes are implemented and ready)")
        print("- Circuit breaker implementation is complete")
        print("- Asyncio optimizations are implemented")
        print("- Code is ready for deployment to staging")
        
    elif args.phase == "post-deployment":
        print("\nPOST-DEPLOYMENT INTERPRETATION:")
        print("- All tests should PASS (fixes are now active in staging)")
        print("- P1 tests should achieve 100% pass rate")
        print("- WebSocket performance should be dramatically improved")
        print("- Issue #128 should be completely resolved")
    
    if failed_tests > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()