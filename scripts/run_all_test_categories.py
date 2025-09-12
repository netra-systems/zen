#!/usr/bin/env python3
"""Run all test categories individually and collect failures."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re


def run_category(category: str, timeout: int = 60) -> Dict:
    """Run a single test category with timeout."""
    print(f"\n{'='*60}")
    print(f"Running {category} tests (timeout: {timeout}s)")
    print(f"{'='*60}")
    
    cmd = ["python", "unified_test_runner.py", 
           "--category", category, 
           "--no-coverage", 
           "--fast-fail"]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        success = result.returncode == 0
        status = "PASSED" if success else "FAILED"
        output = result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        success = False
        status = "TIMEOUT"
        output = f"Test category '{category}' timed out after {timeout} seconds"
        
    except Exception as e:
        duration = time.time() - start_time
        success = False
        status = "ERROR"
        output = f"Error running category '{category}': {str(e)}"
    
    print(f"  Status: {status}")
    print(f"  Duration: {duration:.2f}s")
    
    # Extract failures from output
    failures = []
    if not success and output:
        failed_pattern = r"FAILED ([\w/\\\.]+::\S+)"
        error_pattern = r"ERROR ([\w/\\\.]+::\S+)"
        
        for match in re.finditer(failed_pattern, output):
            failures.append({
                "test": match.group(1),
                "type": "FAILED",
                "category": category
            })
            
        for match in re.finditer(error_pattern, output):
            failures.append({
                "test": match.group(1),
                "type": "ERROR",
                "category": category
            })
    
    if failures:
        print(f"  Failures found: {len(failures)}")
        for failure in failures[:5]:  # Show first 5
            print(f"    - {failure['type']}: {failure['test']}")
        if len(failures) > 5:
            print(f"    ... and {len(failures) - 5} more")
    
    return {
        "category": category,
        "status": status,
        "success": success,
        "duration": duration,
        "failures": failures,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main entry point."""
    # Categories to test
    categories = [
        ("database", 60),
        ("unit", 30),  # Shorter timeout for hanging unit tests
        ("integration", 60),
        ("api", 60),
        ("smoke", 30),
        ("core", 60),
    ]
    
    results = []
    all_failures = []
    
    print("Starting comprehensive test run...")
    print(f"Testing {len(categories)} categories")
    
    for category, timeout in categories:
        result = run_category(category, timeout)
        results.append(result)
        all_failures.extend(result["failures"])
        
        # Small delay between categories
        time.sleep(2)
    
    # Save results
    report_dir = Path("test_failures")
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "categories_tested": len(categories),
            "total_failures": len(all_failures),
            "results": results,
            "all_failures": all_failures
        }, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    
    print(f"Categories Tested: {len(categories)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total Failures Found: {len(all_failures)}")
    
    print("\nCategory Results:")
    for result in results:
        status_emoji = " PASS: " if result["success"] else " FAIL: "
        print(f"  {status_emoji} {result['category']:15} {result['status']:10} ({result['duration']:.2f}s) - {len(result['failures'])} failures")
    
    if all_failures:
        print(f"\nUnique Failures: {len(set(f['test'] for f in all_failures))}")
        print("\nTop Failures:")
        for failure in all_failures[:10]:
            print(f"  - [{failure['category']}] {failure['type']}: {failure['test']}")
    
    print(f"\nReport saved to: {report_file}")
    
    return 0 if not all_failures else 1


if __name__ == "__main__":
    sys.exit(main())