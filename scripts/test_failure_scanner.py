#!/usr/bin/env python
"""
Quick test failure scanner - identifies failing tests efficiently
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def scan_test_failures():
    """Quickly scan for test failures"""
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "categories": defaultdict(list),
        "summary": {},
        "priority_failures": []
    }
    
    # Test paths to scan in priority order
    test_paths = [
        # Critical paths first
        ("app/tests/core", "Critical - Core functionality"),
        ("app/tests/routes", "Critical - API endpoints"),
        ("app/tests/services/test_security_service.py", "Critical - Security"),
        ("app/tests/services/database", "Critical - Database"),
        
        # High priority
        ("app/tests/agents", "High - Agent system"),
        ("app/tests/websocket", "High - WebSocket"),
        ("app/tests/services", "High - Services"),
        
        # Medium priority
        ("app/tests/integration", "Medium - Integration"),
        ("app/tests/models", "Medium - Models"),
        
        # Low priority
        ("app/tests/utils", "Low - Utilities"),
    ]
    
    print("Scanning for test failures...")
    print("=" * 60)
    
    total_tests = 0
    total_failures = 0
    
    for test_path, category in test_paths:
        full_path = PROJECT_ROOT / test_path
        if not full_path.exists():
            continue
            
        print(f"\nScanning {category}: {test_path}")
        print("-" * 40)
        
        # Run pytest with minimal output
        cmd = [
            sys.executable, "-m", "pytest",
            str(full_path),
            "--tb=no",
            "-q",
            "--no-header",
            "--no-summary",
            "-rN",  # Show only test names, no output
            "--maxfail=50",  # Stop after 50 failures to speed up
            "--timeout=5",  # 5 second timeout per test
            "--disable-warnings"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Overall timeout
                cwd=PROJECT_ROOT
            )
            
            # Parse output for failures
            lines = result.stdout.split('\n')
            
            # Count tests
            test_count = 0
            failure_count = 0
            failures = []
            
            for line in lines:
                if '::' in line:
                    test_count += 1
                    if 'FAILED' in line:
                        failure_count += 1
                        # Extract test name
                        match = re.search(r'([\w/\\\.]+::\S+)', line)
                        if match:
                            test_name = match.group(1)
                            failures.append(test_name)
                            
                            # Add to priority failures if critical/high
                            if "Critical" in category or "High" in category:
                                results["priority_failures"].append({
                                    "test": test_name,
                                    "category": category
                                })
                    elif 'ERROR' in line:
                        failure_count += 1
                        match = re.search(r'([\w/\\\.]+::\S+)', line)
                        if match:
                            failures.append(match.group(1))
            
            # Check summary line
            summary_match = re.search(r'(\d+) failed.*(\d+) passed', result.stdout)
            if summary_match:
                failure_count = int(summary_match.group(1))
            
            total_tests += test_count
            total_failures += failure_count
            
            # Store results
            results["categories"][category] = {
                "path": test_path,
                "total": test_count,
                "failures": failure_count,
                "failed_tests": failures[:10]  # First 10 failures
            }
            
            # Print summary for this category
            if failure_count > 0:
                print(f"  [FAIL] {failure_count}/{test_count} tests failed")
                for i, test in enumerate(failures[:5], 1):
                    print(f"     {i}. {test}")
                if len(failures) > 5:
                    print(f"     ... and {len(failures) - 5} more")
            else:
                print(f"  [PASS] All {test_count} tests passed")
                
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] Skipping remaining tests in {test_path}")
        except Exception as e:
            print(f"  [ERROR] Scanning {test_path}: {e}")
    
    # Generate summary
    results["summary"] = {
        "total_tests": total_tests,
        "total_failures": total_failures,
        "failure_rate": (total_failures / total_tests * 100) if total_tests > 0 else 0,
        "categories_scanned": len(results["categories"]),
        "priority_failure_count": len(results["priority_failures"])
    }
    
    # Save results
    output_file = PROJECT_ROOT / "test_reports" / "failure_scan.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Total tests scanned: {total_tests}")
    print(f"Total failures found: {total_failures}")
    print(f"Failure rate: {results['summary']['failure_rate']:.1f}%")
    print(f"Priority failures: {len(results['priority_failures'])}")
    print(f"\nDetailed results saved to: {output_file}")
    
    # List priority failures
    if results["priority_failures"]:
        print("\n" + "=" * 60)
        print("PRIORITY FAILURES (Critical/High)")
        print("=" * 60)
        for i, failure in enumerate(results["priority_failures"][:20], 1):
            print(f"{i:3}. [{failure['category'].split(' - ')[0]:8}] {failure['test']}")
    
    return results

if __name__ == "__main__":
    results = scan_test_failures()
    sys.exit(0 if results["summary"]["total_failures"] == 0 else 1)