#!/usr/bin/env python3
"""Test Failure Tracker - Continuously run tests and track failures."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional
import re


class TestFailureTracker:
    """Track test failures and manage continuous test execution."""
    
    def __init__(self):
        self.failures_dir = Path("test_failures")
        self.failures_dir.mkdir(exist_ok=True)
        self.failed_tests: Set[str] = set()
        self.session_report = self.failures_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.iteration = 0
        
    def extract_failures_from_output(self, output: str) -> List[Dict]:
        """Extract test failures from pytest output."""
        failures = []
        
        # Pattern for failed tests
        failed_pattern = r"FAILED ([\w/\\\.]+::\S+)"
        error_pattern = r"ERROR ([\w/\\\.]+::\S+)"
        
        for match in re.finditer(failed_pattern, output):
            failures.append({
                "test": match.group(1),
                "type": "FAILED"
            })
            
        for match in re.finditer(error_pattern, output):
            failures.append({
                "test": match.group(1),
                "type": "ERROR"
            })
            
        # Also extract from summary
        if "ERRORS" in output or "FAILURES" in output:
            lines = output.split('\n')
            in_summary = False
            for line in lines:
                if "short test summary info" in line:
                    in_summary = True
                elif in_summary:
                    if line.startswith("FAILED "):
                        test_name = line.replace("FAILED ", "").split(" - ")[0].strip()
                        failures.append({
                            "test": test_name,
                            "type": "FAILED"
                        })
                    elif line.startswith("ERROR "):
                        test_name = line.replace("ERROR ", "").split(" - ")[0].strip()
                        failures.append({
                            "test": test_name,
                            "type": "ERROR"
                        })
                        
        return failures
    
    def run_tests(self, skip_tests: Optional[Set[str]] = None) -> Dict:
        """Run tests, optionally skipping known failures."""
        self.iteration += 1
        print(f"\n{'='*60}")
        print(f"Test Iteration #{self.iteration}")
        print(f"{'='*60}")
        
        # Build command
        cmd = ["python", "unified_test_runner.py", "--category", "integration", 
               "--no-coverage", "--fast-fail"]
        
        # Add skip patterns if we have failures to skip
        if skip_tests:
            # Create a temporary pytest marker file
            skip_file = Path("pytest_skip_markers.txt")
            with open(skip_file, "w") as f:
                for test in skip_tests:
                    # Convert test path to deselect pattern
                    f.write(f"--deselect={test}\n")
            print(f"Skipping {len(skip_tests)} known failures")
        
        # Run tests
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        duration = time.time() - start_time
        
        # Parse output for failures
        combined_output = result.stdout + result.stderr
        failures = self.extract_failures_from_output(combined_output)
        
        # Update tracked failures
        for failure in failures:
            self.failed_tests.add(failure["test"])
        
        # Save results
        iteration_result = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "return_code": result.returncode,
            "new_failures": failures,
            "total_known_failures": list(self.failed_tests),
            "skipped_count": len(skip_tests) if skip_tests else 0
        }
        
        # Save to session report
        self.save_iteration_result(iteration_result)
        
        # Print summary
        print(f"\nIteration #{self.iteration} Summary:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Return Code: {result.returncode}")
        print(f"  New Failures Found: {len(failures)}")
        print(f"  Total Known Failures: {len(self.failed_tests)}")
        
        if failures:
            print("\nNew failures detected:")
            for failure in failures:
                print(f"  - {failure['type']}: {failure['test']}")
        
        return iteration_result
    
    def save_iteration_result(self, result: Dict):
        """Save iteration result to session report."""
        # Load existing session data
        session_data = []
        if self.session_report.exists():
            with open(self.session_report, 'r') as f:
                session_data = json.load(f)
        
        # Append new result
        session_data.append(result)
        
        # Save updated data
        with open(self.session_report, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Also save current failure list
        failures_file = self.failures_dir / "current_failures.json"
        with open(failures_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_failures": len(self.failed_tests),
                "failures": list(self.failed_tests)
            }, f, indent=2)
    
    def run_continuous(self, max_iterations: int = 10):
        """Run tests continuously until no new failures found or max iterations."""
        print("Starting continuous test failure detection...")
        print(f"Max iterations: {max_iterations}")
        
        no_new_failures_count = 0
        
        for i in range(max_iterations):
            previous_failure_count = len(self.failed_tests)
            
            # Run tests, skipping known failures after first iteration
            skip_tests = self.failed_tests if i > 0 else None
            result = self.run_tests(skip_tests)
            
            # Check if we found new failures
            new_failure_count = len(self.failed_tests) - previous_failure_count
            
            if new_failure_count == 0:
                no_new_failures_count += 1
                print(f"\nNo new failures found (streak: {no_new_failures_count})")
                
                if no_new_failures_count >= 2:
                    print("\nNo new failures in 2 consecutive runs. Stopping.")
                    break
            else:
                no_new_failures_count = 0
                print(f"\nFound {new_failure_count} new failures")
            
            # Add delay between iterations
            if i < max_iterations - 1:
                print("\nWaiting 2 seconds before next iteration...")
                time.sleep(2)
        
        # Final summary
        print(f"\n{'='*60}")
        print("FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total iterations: {self.iteration}")
        print(f"Total unique failures found: {len(self.failed_tests)}")
        print(f"Session report saved to: {self.session_report}")
        
        if self.failed_tests:
            print("\nAll failures:")
            for test in sorted(self.failed_tests):
                print(f"  - {test}")
        
        return list(self.failed_tests)


def main():
    """Main entry point."""
    tracker = TestFailureTracker()
    failures = tracker.run_continuous(max_iterations=10)
    
    # Create todo list for fixing
    if failures:
        print(f"\n{'='*60}")
        print("Creating fix tasks for all failures...")
        print(f"{'='*60}")
        
        # Save failures for sub-agent processing
        fix_tasks_file = Path("test_failures/fix_tasks.json")
        with open(fix_tasks_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "failures": failures,
                "status": "pending_fixes"
            }, f, indent=2)
        
        print(f"Fix tasks saved to: {fix_tasks_file}")
        print(f"Total tasks to process: {len(failures)}")
    else:
        print("\nNo failures found! All tests passing.")
    
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())