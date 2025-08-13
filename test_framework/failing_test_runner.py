#!/usr/bin/env python
"""
Failing Test Runner - Handles execution of failing tests and retry logic
Manages running specific failing tests and tracking their resolution
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).parent.parent


def run_failing_tests(failing_tests: Dict, max_fixes: int = None, backend_only: bool = False, frontend_only: bool = False) -> int:
    """Run only the currently failing tests."""
    total_failures = 0
    fixed_count = 0
    
    # Run backend failing tests
    if not frontend_only and failing_tests["backend"]["count"] > 0:
        print(f"\n[FAILING TESTS] Running {failing_tests['backend']['count']} failing backend tests...")
        
        for failure in failing_tests["backend"]["failures"][:max_fixes]:
            test_spec = f"{failure['test_path']}::{failure['test_name']}"
            print(f"  Testing: {test_spec}")
            
            cmd = [sys.executable, "-m", "pytest", test_spec, "-xvs"]
            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✓ FIXED: {failure['test_name']}")
                fixed_count += 1
            else:
                print(f"    ✗ Still failing: {failure['test_name']}")
                total_failures += 1
    
    # Run frontend failing tests  
    if not backend_only and failing_tests["frontend"]["count"] > 0:
        print(f"\n[FAILING TESTS] Running {failing_tests['frontend']['count']} failing frontend tests...")
        
        for failure in failing_tests["frontend"]["failures"][:max_fixes]:
            print(f"  Testing: {failure['test_path']} - {failure['test_name']}")
            
            # Run specific Jest test
            cmd = ["npm", "test", "--", failure["test_path"], "--testNamePattern", failure["test_name"]]
            result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✓ FIXED: {failure['test_name']}")
                fixed_count += 1
            else:
                print(f"    ✗ Still failing: {failure['test_name']}")
                total_failures += 1
    
    print(f"\n[SUMMARY] Fixed {fixed_count} tests, {total_failures} still failing")
    return total_failures


def run_specific_failing_test(test_path: str, test_name: str, test_type: str = "backend") -> bool:
    """Run a specific failing test and return whether it passes."""
    if test_type == "backend":
        if "::" not in test_path:
            test_spec = f"{test_path}::{test_name}"
        else:
            test_spec = test_path
        
        cmd = [sys.executable, "-m", "pytest", test_spec, "-xvs"]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
    elif test_type == "frontend":
        cmd = ["npm", "test", "--", test_path, "--testNamePattern", test_name]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", capture_output=True, text=True)
    
    else:
        return False
    
    return result.returncode == 0


def batch_run_failing_tests(failing_tests: list, batch_size: int = 5) -> Dict:
    """Run failing tests in batches to avoid overwhelming the system."""
    results = {
        "total": len(failing_tests),
        "fixed": 0,
        "still_failing": 0,
        "batches": []
    }
    
    for i in range(0, len(failing_tests), batch_size):
        batch = failing_tests[i:i + batch_size]
        batch_results = {
            "batch_id": i // batch_size + 1,
            "tests": [],
            "fixed": 0,
            "still_failing": 0
        }
        
        print(f"\n[BATCH {batch_results['batch_id']}] Running {len(batch)} tests...")
        
        for test in batch:
            test_passed = run_specific_failing_test(
                test["test_path"], 
                test["test_name"], 
                test.get("test_type", "backend")
            )
            
            test_result = {
                "test_name": test["test_name"],
                "test_path": test["test_path"],
                "passed": test_passed
            }
            
            batch_results["tests"].append(test_result)
            
            if test_passed:
                batch_results["fixed"] += 1
                results["fixed"] += 1
                print(f"    ✓ FIXED: {test['test_name']}")
            else:
                batch_results["still_failing"] += 1
                results["still_failing"] += 1
                print(f"    ✗ Still failing: {test['test_name']}")
        
        results["batches"].append(batch_results)
        
        print(f"[BATCH {batch_results['batch_id']} COMPLETE] Fixed: {batch_results['fixed']}, Still failing: {batch_results['still_failing']}")
    
    return results


def retry_flaky_tests(flaky_tests: list, retry_count: int = 3) -> Dict:
    """Retry flaky tests multiple times to confirm they're stable."""
    results = {
        "total": len(flaky_tests),
        "stabilized": 0,
        "still_flaky": 0,
        "tests": []
    }
    
    for test in flaky_tests:
        print(f"\n[FLAKY TEST] Retrying {test['test_name']} {retry_count} times...")
        
        passes = 0
        failures = 0
        
        for attempt in range(retry_count):
            print(f"  Attempt {attempt + 1}/{retry_count}...")
            
            test_passed = run_specific_failing_test(
                test["test_path"],
                test["test_name"],
                test.get("test_type", "backend")
            )
            
            if test_passed:
                passes += 1
            else:
                failures += 1
        
        # Consider stabilized if it passes more than 80% of the time
        stability_ratio = passes / retry_count
        is_stabilized = stability_ratio >= 0.8
        
        test_result = {
            "test_name": test["test_name"],
            "test_path": test["test_path"],
            "passes": passes,
            "failures": failures,
            "stability_ratio": stability_ratio,
            "stabilized": is_stabilized
        }
        
        results["tests"].append(test_result)
        
        if is_stabilized:
            results["stabilized"] += 1
            print(f"    ✓ STABILIZED: {test['test_name']} ({passes}/{retry_count} passes)")
        else:
            results["still_flaky"] += 1
            print(f"    ✗ Still flaky: {test['test_name']} ({passes}/{retry_count} passes)")
    
    return results