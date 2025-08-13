#!/usr/bin/env python3
"""Run performance tests for the Netra platform."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List


def run_performance_tests(output_file: Path) -> int:
    """Run performance-specific tests and generate results."""
    
    results = {
        "test_type": "performance",
        "timestamp": time.time(),
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "performance_issues": []
        }
    }
    
    # Define performance test patterns
    performance_tests = [
        "test_websocket_production_realistic",
        "test_concurrent_user_load",
        "test_database_repository_critical",
        "test_agent_service_critical",
        "test_clickhouse.*performance",
        "test_redis_manager_operations",
        "test_llm_manager_provider_switching"
    ]
    
    print("=" * 60)
    print("RUNNING PERFORMANCE TESTS")
    print("=" * 60)
    
    for test_pattern in performance_tests:
        print(f"\nRunning performance test: {test_pattern}")
        
        test_result = {
            "name": test_pattern,
            "status": "pending",
            "duration": 0,
            "metrics": {}
        }
        
        start_time = time.time()
        
        # Run pytest with performance markers
        cmd = [
            sys.executable, "-m", "pytest",
            "-k", test_pattern,
            "--tb=short",
            "-v",
            "--json-report",
            "--json-report-file=temp_perf_result.json"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test
            )
            
            test_result["duration"] = time.time() - start_time
            
            if result.returncode == 0:
                test_result["status"] = "passed"
                results["summary"]["passed"] += 1
                print(f"  ✅ Passed in {test_result['duration']:.2f}s")
            else:
                test_result["status"] = "failed"
                results["summary"]["failed"] += 1
                print(f"  ❌ Failed in {test_result['duration']:.2f}s")
                
                # Check for performance issues
                if "timeout" in result.stderr.lower():
                    results["summary"]["performance_issues"].append({
                        "test": test_pattern,
                        "issue": "timeout",
                        "duration": test_result["duration"]
                    })
            
            # Try to load detailed results if available
            temp_result_file = Path("temp_perf_result.json")
            if temp_result_file.exists():
                try:
                    with open(temp_result_file, "r") as f:
                        detailed_results = json.load(f)
                        test_result["details"] = detailed_results
                except:
                    pass
                temp_result_file.unlink()
                
        except subprocess.TimeoutExpired:
            test_result["status"] = "timeout"
            test_result["duration"] = 300
            results["summary"]["failed"] += 1
            results["summary"]["performance_issues"].append({
                "test": test_pattern,
                "issue": "hard_timeout",
                "duration": 300
            })
            print(f"  ⏱️ Timeout after 300s")
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            results["summary"]["failed"] += 1
            print(f"  🔥 Error: {e}")
        
        results["tests"].append(test_result)
        results["summary"]["total"] += 1
    
    # Calculate performance metrics
    total_duration = sum(t["duration"] for t in results["tests"])
    avg_duration = total_duration / len(results["tests"]) if results["tests"] else 0
    
    results["summary"]["total_duration"] = total_duration
    results["summary"]["average_duration"] = avg_duration
    results["summary"]["success_rate"] = (
        results["summary"]["passed"] / results["summary"]["total"] * 100
        if results["summary"]["total"] > 0 else 0
    )
    
    # Save results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Average Duration: {avg_duration:.2f}s")
    
    if results["summary"]["performance_issues"]:
        print(f"\n⚠️ Performance Issues Detected: {len(results['summary']['performance_issues'])}")
        for issue in results["summary"]["performance_issues"]:
            print(f"  - {issue['test']}: {issue['issue']} ({issue['duration']:.2f}s)")
    
    return 0 if results["summary"]["failed"] == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Run performance tests")
    parser.add_argument("--output", required=True, help="Output JSON file for results")
    
    args = parser.parse_args()
    
    return run_performance_tests(Path(args.output))


if __name__ == "__main__":
    sys.exit(main())