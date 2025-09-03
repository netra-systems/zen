#!/usr/bin/env python
"""
TEAM ECHO Authentication Test Suite Runner
===========================================
Runs all 15 authentication and user journey test files
with comprehensive reporting.
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import json

# Define the 15 test files to run
TEST_FILES = [
    "test_staging_auth_cross_service_validation.py",
    "test_auth_state_consistency.py",
    "test_jwt_secret_hard_requirements.py",
    "test_jwt_secret_synchronization_simple.py",
    "test_jwt_sync_ascii.py",
    "test_pre_post_deployment_jwt_verification.py",
    "test_backend_login_endpoint_fix.py",
    "test_staging_endpoints_direct.py",
    "test_staging_websocket_agent_events.py",
    "test_token_refresh_active_chat.py",
    "test_presence_detection_critical.py",
    "test_chat_responsiveness_under_load.py",
    "test_memory_leak_prevention_comprehensive.py",
    "test_tool_progress_bulletproof.py",
    "test_comprehensive_compliance_validation.py"
]

def run_test_file(test_file, test_dir="tests/mission_critical"):
    """Run a single test file and return results."""
    full_path = Path(test_dir) / test_file
    
    print(f"\n{'='*80}")
    print(f"Running: {test_file}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    cmd = [
        sys.executable, "-m", "pytest",
        str(full_path),
        "-v", "--tb=short",
        "--json-report",
        f"--json-report-file=test_results/{test_file}.json",
        "--timeout=120",
        "-x"  # Stop on first failure
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per file
        )
        
        duration = time.time() - start_time
        
        # Parse output for test counts
        passed = result.stdout.count(" PASSED")
        failed = result.stdout.count(" FAILED")
        skipped = result.stdout.count(" SKIPPED")
        
        return {
            "file": test_file,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": duration,
            "return_code": result.returncode,
            "success": result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        return {
            "file": test_file,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration": 300,
            "return_code": -1,
            "success": False,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "file": test_file,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration": 0,
            "return_code": -1,
            "success": False,
            "error": str(e)
        }

def main():
    """Main test runner."""
    print("=" * 80)
    print("TEAM ECHO AUTHENTICATION TEST SUITE")
    print("Running 15 Critical Authentication & User Journey Tests")
    print("=" * 80)
    
    # Create results directory
    Path("test_results").mkdir(exist_ok=True)
    
    # Run all tests
    results = []
    total_start = time.time()
    
    for test_file in TEST_FILES:
        result = run_test_file(test_file)
        results.append(result)
        
        # Print immediate summary
        status = "PASSED" if result["success"] else "FAILED"
        print(f"{status} - {test_file}")
        print(f"  Tests: {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped")
        print(f"  Duration: {result['duration']:.2f}s")
    
    total_duration = time.time() - total_start
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("FINAL TEST SUMMARY REPORT")
    print("=" * 80)
    
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    successful_files = sum(1 for r in results if r["success"])
    
    print(f"\nFiles Executed: {len(TEST_FILES)}")
    print(f"Files Passed: {successful_files}/{len(TEST_FILES)}")
    print(f"\nTotal Tests:")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Skipped: {total_skipped}")
    print(f"\nTotal Duration: {total_duration:.2f}s")
    print(f"Average per file: {total_duration/len(TEST_FILES):.2f}s")
    
    # Save detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_files": len(TEST_FILES),
            "successful_files": successful_files,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_duration": total_duration
        },
        "details": results
    }
    
    with open("test_results/auth_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: test_results/auth_test_report.json")
    
    # Exit with appropriate code
    sys.exit(0 if successful_files == len(TEST_FILES) else 1)

if __name__ == "__main__":
    main()